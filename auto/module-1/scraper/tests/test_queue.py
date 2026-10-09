import json
import threading
from datetime import datetime, timedelta, timezone

import pytest

from scraper.manifest import parse_manifest_payload
from scraper.errors import ContentValidationError
from scraper.store import ClaimError, OrchestratorStore, QueueConflict


def content(kind="sculptural"):
    if kind == "architectural":
        return {
            "title": "Architectural Frame Accent Stand with Offset Curved Supports",
            "seo_product_title": "Offset Frame Accent Stand with Layered Geometric Profile",
            "seo_title": "Architectural Accent Stand with Offset Frame | Wrydeco",
            "seo_description": "Explore an architectural frame accent stand with offset curved supports, a layered geometric profile, and an airy structural composition for expressive rooms.",
            "handle": "architectural-frame-accent-stand-offset-curved-supports",
            "description_html": '<div class="wrydeco-product-description"><p>An architectural frame uses offset curved supports and a layered geometric profile for an airy structural composition.</p></div>',
        }
    return {
        "title": "Sculptural Profile Side Table with Rounded Shelf Edges",
        "seo_product_title": "Open Tier Composition Table with Asymmetrical Silhouette",
        "seo_title": "Sculptural Side Table with Rounded Shelf Profile | Wrydeco",
        "seo_description": "Explore a sculptural profile side table with rounded shelf edges, an open tier composition, and an asymmetrical silhouette designed as a distinctive accent.",
        "handle": "sculptural-profile-side-table-rounded-shelf-edges-design",
        "description_html": '<div class="wrydeco-product-description"><p>A sculptural profile with rounded shelf edges creates an open tier composition and asymmetrical silhouette.</p></div>',
    }


def make_root(tmp_path):
    root = tmp_path / "scraper"
    root.mkdir()
    (root / "AGENT_PROMPT.md").write_text("Only factual content.", encoding="utf-8")
    (root / "content.schema.json").write_text("{}", encoding="utf-8")
    return root


def create_run(store, asin="B000000000", shopify_id="123", *, dry_run=False):
    payload = {"products": [{"amazon_url": f"https://www.amazon.com/dp/{asin}", "shopify_product_id": shopify_id, "mode": "auto"}]}
    manifest = parse_manifest_payload(payload, store.package_root / f"{asin}.json")
    run = store.create_run(manifest, payload, {"dry_run": dry_run})
    return run, next(iter(run["products"].values()))


def queue_product(store, product, kind="sculptural"):
    workspace = store.workspace(store.product(product["id"]))
    payload = content(kind)
    (workspace / "source.json").write_text(json.dumps({
        "title": payload["title"] + " " + payload["seo_product_title"],
        "bullets": [payload["seo_description"]],
        "aplus_text": "",
    }), encoding="utf-8")
    gallery = workspace / "evidence" / "gallery"
    gallery.mkdir(parents=True)
    for filename in ("001.jpg", "002.jpg", "contact-sheet.jpg"):
        (gallery / filename).write_bytes(b"image")
    store.set_product_status(product["id"], "crawling")
    store.set_product_status(product["id"], "crawled")
    store.set_product_status(product["id"], "price_verified")
    store.enqueue_content(product["id"])


def prime_visual(store, product, claim, kind="sculptural"):
    context = store.content_context(product["id"], claim["claim_token"])
    for evidence_id in ("gallery/contact-sheet.jpg", "gallery/001.jpg", "gallery/002.jpg"):
        store.evidence_path(product["id"], claim["claim_token"], evidence_id)
    if kind == "architectural":
        design = ["architectural frame", "layered geometric profile", "airy structural composition"]
        shape = ["offset curved supports", "open frame rhythm", "stepped outline"]
    else:
        design = ["sculptural profile", "open tier composition", "balanced visual rhythm"]
        shape = ["rounded shelf edges", "asymmetrical silhouette", "stacked outline"]
    store.write_visual_analysis(product["id"], claim["claim_token"], {
        "task_id": product["id"], "source_digest": context["source_digest"],
        "target_identity": "side table", "evidence_ids": [
            "gallery/contact-sheet.jpg", "gallery/001.jpg", "gallery/002.jpg"
        ], "design_keywords": design, "shape_keywords": shape,
    })


def test_state_machine_rejects_invalid_transition(tmp_path):
    store = OrchestratorStore(make_root(tmp_path))
    _, product = create_run(store)
    with pytest.raises(QueueConflict, match="pending -> applied"):
        store.set_product_status(product["id"], "applied")


def test_fifo_across_runs_and_atomic_concurrent_claim(tmp_path):
    store = OrchestratorStore(make_root(tmp_path))
    _, first = create_run(store, "B000000000", "123")
    _, second = create_run(store, "B000000001", "124")
    queue_product(store, first)
    queue_product(store, second)
    barrier = threading.Barrier(2)
    results = []

    def claim(worker):
        barrier.wait()
        results.append(store.claim_next_content(worker))

    threads = [threading.Thread(target=claim, args=(name,)) for name in ("one", "two")]
    [thread.start() for thread in threads]
    [thread.join() for thread in threads]
    claimed = [item for item in results if item]
    assert len(claimed) == 2
    assert {item["task_id"] for item in claimed} == {first["id"], second["id"]}
    first_claim = next(item for item in claimed if item["task_id"] == first["id"])
    assert first_claim["product"]["asin"] == "B000000000"


def test_claim_token_lease_release_and_finalize(tmp_path):
    store = OrchestratorStore(make_root(tmp_path), lease_seconds=60)
    _, product = create_run(store)
    queue_product(store, product)
    claim = store.claim_next_content("agent")
    with pytest.raises(ClaimError):
        store.write_content_draft(product["id"], "wrong-token", content())
    renewed = store.renew_content_lease(product["id"], claim["claim_token"])
    assert renewed["lease_expires_at"]
    prime_visual(store, product, claim)
    store.write_content_draft(product["id"], claim["claim_token"], content())
    result = store.finalize_content(product["id"], claim["claim_token"])
    assert result["state"] == "ready"
    workspace = store.workspace(store.product(product["id"]))
    assert (workspace / "content.json").is_file()
    assert not (workspace / "content.temp.json").exists()
    assert store.queue_status()["apply"]["queued"] == 1


def test_expired_lease_returns_to_queue(tmp_path):
    store = OrchestratorStore(make_root(tmp_path))
    _, product = create_run(store)
    queue_product(store, product)
    store.claim_next_content("agent")
    expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    with store.transaction(immediate=True) as connection:
        connection.execute("UPDATE content_tasks SET lease_expires_at=? WHERE product_id=?", (expired, product["id"]))
    assert store.claim_next_content("next-agent")["task_id"] == product["id"]


def test_reconcile_valid_orphan_content_but_never_retries_shopify_error(tmp_path):
    store = OrchestratorStore(make_root(tmp_path))
    _, product = create_run(store)
    queue_product(store, product)
    workspace = store.workspace(store.product(product["id"]))
    claim = store.claim_next_content("recovery-agent")
    prime_visual(store, product, claim)
    store.write_content_draft(product["id"], claim["claim_token"], content())
    (workspace / "content.temp.json").replace(workspace / "content.json")
    store.recover()
    assert store.queue_status()["apply"]["queued"] == 1
    store.claim_next_apply()
    store.finish_apply(product["id"], "needs_attention", error="mutation failed")
    store.recover()
    task = store.product_status(store.product(product["id"]))
    assert task["status"] == "needs_attention"
    assert task["apply_task"]["state"] == "needs_attention"


def test_recover_applied_product_rebuilds_fingerprints_without_uniqueness_scan(tmp_path, monkeypatch):
    store = OrchestratorStore(make_root(tmp_path))
    _, product = create_run(store, dry_run=True)
    queue_product(store, product)
    claim = store.claim_next_content("recovery-agent")
    prime_visual(store, product, claim)
    store.write_content_draft(product["id"], claim["claim_token"], content())
    store.finalize_content(product["id"], claim["claim_token"])
    store.claim_next_apply()
    store.finish_apply(product["id"], "dry_run_complete")
    with store.transaction(immediate=True) as connection:
        connection.execute("DELETE FROM content_fingerprints WHERE product_id=?", (product["id"],))

    def unexpected_collision_scan(*_args, **_kwargs):
        raise AssertionError("final products must not rerun cross-product uniqueness during recovery")

    monkeypatch.setattr(store, "_content_collisions", unexpected_collision_scan)
    store.recover()

    with store._connect() as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM content_fingerprints WHERE product_id=? AND active=1",
            (product["id"],),
        ).fetchone()[0]
    assert count == 6


def test_duplicate_open_product_is_rejected_and_closed_product_is_reusable(tmp_path):
    store = OrchestratorStore(make_root(tmp_path))
    _, product = create_run(store)
    with pytest.raises(QueueConflict, match="already open"):
        create_run(store)
    store.set_product_status(product["id"], "cancelled")
    run, _ = create_run(store)
    assert run["id"]


def test_events_are_monotonic_and_cursor_safe(tmp_path):
    store = OrchestratorStore(make_root(tmp_path))
    first = store.event("first", message="one")
    second = store.event("second", message="two")
    events = store.events_after(first)
    assert [event["id"] for event in events] == [second]


def test_event_queries_are_bounded_and_recent_events_keep_display_order(tmp_path):
    store = OrchestratorStore(make_root(tmp_path))
    event_ids = [store.event(f"event-{index}") for index in range(8)]

    assert [event["id"] for event in store.events_after(0, limit=3)] == event_ids[:3]
    assert [event["id"] for event in store.recent_events(limit=3)] == event_ids[-3:]


def test_shopify_dispatcher_claims_only_one_task_at_a_time(tmp_path):
    store = OrchestratorStore(make_root(tmp_path))
    _, first = create_run(store, "B000000000", "123", dry_run=True)
    _, second = create_run(store, "B000000001", "124", dry_run=True)
    for product, kind in ((first, "sculptural"), (second, "architectural")):
        queue_product(store, product, kind)
        claim = store.claim_next_content(f"agent-{product['asin']}")
        prime_visual(store, product, claim, kind)
        store.write_content_draft(product["id"], claim["claim_token"], content(kind))
        store.finalize_content(product["id"], claim["claim_token"])

    claimed_first = store.claim_next_apply()
    assert claimed_first["id"] == first["id"]
    assert store.claim_next_apply() is None
    store.finish_apply(first["id"], "dry_run_complete")
    assert store.claim_next_apply()["id"] == second["id"]


def test_agent_automation_attempts_retry_then_fail_closed(tmp_path):
    store = OrchestratorStore(make_root(tmp_path))
    _, product = create_run(store)
    queue_product(store, product)
    assert store.begin_content_automation_attempt(product["id"]) == 1
    retried = store.fail_content_automation(product["id"], "invalid draft", terminal=False)
    assert retried["status"] == "content_queued"
    assert retried["content_task"]["last_agent_error"] == "invalid draft"
    assert store.begin_content_automation_attempt(product["id"]) == 2
    failed = store.fail_content_automation(product["id"], "still invalid", terminal=True)
    assert failed["status"] == "needs_attention"
    assert failed["content_task"]["state"] == "error"

    retried = store.retry_failed_content(product["id"])
    assert retried["state"] == "queued"
    assert retried["revision"] == 1
    assert retried["automation_attempts"] == 0
    assert store.product(product["id"])["status"] == "content_queued"


def test_only_claims_owned_by_failed_agent_session_are_released(tmp_path):
    store = OrchestratorStore(make_root(tmp_path))
    _, first = create_run(store, "B000000000", "123")
    _, second = create_run(store, "B000000001", "124")
    queue_product(store, first)
    queue_product(store, second)
    store.claim_next_content("server-agent:first")
    store.claim_next_content("server-agent:second")
    assert store.release_claims_for_worker("server-agent:first", "process stopped") == 1
    assert store.content_task(first["id"])["state"] == "queued"
    assert store.content_task(second["id"])["state"] == "claimed"


def test_draft_requires_current_context_image_reads_and_visual_analysis(tmp_path):
    store = OrchestratorStore(make_root(tmp_path))
    _, product = create_run(store)
    queue_product(store, product)
    claim = store.claim_next_content("isolated-agent")

    with pytest.raises(ClaimError, match="current product context"):
        store.write_content_draft(product["id"], claim["claim_token"], content())

    context = store.content_context(product["id"], claim["claim_token"])
    analysis = {
        "task_id": product["id"], "source_digest": context["source_digest"],
        "target_identity": "side table",
        "evidence_ids": ["gallery/contact-sheet.jpg", "gallery/001.jpg", "gallery/002.jpg"],
        "design_keywords": ["sculptural profile", "open tier composition", "balanced visual rhythm"],
        "shape_keywords": ["rounded shelf edges", "asymmetrical silhouette", "stacked outline"],
    }
    with pytest.raises(ClaimError, match="Required image evidence"):
        store.write_visual_analysis(product["id"], claim["claim_token"], analysis)

    for evidence_id in ("gallery/contact-sheet.jpg", "gallery/001.jpg", "gallery/002.jpg"):
        store.evidence_path(product["id"], claim["claim_token"], evidence_id)
    with pytest.raises(ClaimError, match="visual analysis"):
        store.write_content_draft(product["id"], claim["claim_token"], content())

    store.write_visual_analysis(product["id"], claim["claim_token"], analysis)
    assert store.write_content_draft(product["id"], claim["claim_token"], content())["saved"] is True


def test_exact_content_duplicate_is_rejected_across_runs(tmp_path):
    store = OrchestratorStore(make_root(tmp_path))
    _, first = create_run(store, "B000000000", "123")
    _, second = create_run(store, "B000000001", "124")

    for product in (first, second):
        queue_product(store, product)
        claim = store.claim_expected_content(f"agent-{product['asin']}", product["id"])
        prime_visual(store, product, claim)
        store.write_content_draft(product["id"], claim["claim_token"], content())
        if product["id"] == first["id"]:
            store.finalize_content(product["id"], claim["claim_token"])
        else:
            with pytest.raises(ContentValidationError, match="uniqueness collision"):
                store.finalize_content(product["id"], claim["claim_token"])
            validation = json.loads(
                (store.workspace(store.product(product["id"])) / "content_validation.json").read_text(
                    encoding="utf-8"
                )
            )
            assert validation["valid"] is False
            assert validation["collisions"][0]["conflicting_product_id"] == first["id"]


def test_source_change_invalidates_visual_grounding_before_draft_write(tmp_path):
    store = OrchestratorStore(make_root(tmp_path))
    _, product = create_run(store)
    queue_product(store, product)
    claim = store.claim_next_content("isolated-agent")
    prime_visual(store, product, claim)
    source_path = store.workspace(store.product(product["id"])) / "source.json"
    source_payload = json.loads(source_path.read_text(encoding="utf-8"))
    source_payload["title"] += " revised"
    source_path.write_text(json.dumps(source_payload), encoding="utf-8")
    with pytest.raises(ClaimError, match="source changed"):
        store.write_content_draft(product["id"], claim["claim_token"], content())
