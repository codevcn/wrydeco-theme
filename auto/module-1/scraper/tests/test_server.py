import json
from pathlib import Path

import pytest

from scraper.manifest import parse_manifest_payload
from scraper.server import _dashboard_url, _render_doc_content, create_app, validate_run_options
from scraper.server_control import register_server_process, unregister_server_process
from scraper.store import OrchestratorStore, QueueConflict


MANIFEST = {
    "products": [{
        "amazon_url": "https://www.amazon.com/dp/B000000000",
        "shopify_product_id": "10344740683833",
        "mode": "auto",
        "overrides": {"product_type": "storage-cabinet", "tags": ["source_amazon"], "status": "ACTIVE"},
    }]
}


def valid_content():
    seo_description = (
        "Explore a sculptural profile with open tier composition, flowing outline, and gallery-inspired "
        "presence as a distinctive focal point for refined interiors."
    )
    return {
        "title": "Sculptural Profile Console with Flowing Outline Detail",
        "seo_product_title": "Open Tier Composition Console with Layered Silhouette",
        "seo_title": "Sculptural Profile Statement Console Design | Wrydeco",
        "seo_description": seo_description,
        "handle": "a" * 50,
        "description_html": (
            '<div class="wrydeco-product-description"><p>A sculptural profile and open tier composition '
            "give this console a flowing outline and layered silhouette.</p></div>"
        ),
    }


def package_root(tmp_path: Path) -> Path:
    root = tmp_path / "scraper"
    (root / "input").mkdir(parents=True)
    (root / "input" / "products.json").write_text(json.dumps(MANIFEST), encoding="utf-8")
    (root / "AGENT_PROMPT.md").write_text("Write factual content.", encoding="utf-8")
    (root / "CONTENT_TASK_PROMPT.md").write_text("Process one queued task.", encoding="utf-8")
    (root / "content.schema.json").write_text("{}", encoding="utf-8")
    (root / "product_types.json").write_text(json.dumps({
        "source": "docs/collections.md",
        "product_types": ["storage-cabinet", "console-table"],
    }), encoding="utf-8")
    (root / ".env").write_text("STORE_ADMIN_ACCESS_TOKEN=top-secret\n", encoding="utf-8")
    return root


def headers(csrf: str):
    return {"Origin": "http://localhost", "X-CSRF-Token": csrf}


def test_manifest_payload_and_run_options_are_validated(tmp_path):
    manifest = parse_manifest_payload(MANIFEST, tmp_path / "products.json")
    assert manifest.products[0].asin == "B000000000"
    assert validate_run_options({"headless": True, "amazon_postal_code": "10001", "max_combinations": 42}) == {
        "headless": True, "dry_run": False, "amazon_postal_code": "10001", "max_combinations": 42,
    }
    with pytest.raises(ValueError):
        validate_run_options({"max_combinations": 101})


def test_bootstrap_exposes_agent_state_but_no_secret_or_manual_mcp_config(tmp_path):
    root = package_root(tmp_path)
    app = create_app(root, store=OrchestratorStore(root))
    response = app.test_client().get("/api/bootstrap")
    payload = response.get_json()
    assert payload["agent"]["status"] == "disabled"
    assert "mcp_config" not in payload
    assert "top-secret" not in response.get_data(as_text=True)
    assert "ANTIGRAVITY_COMMAND_JSON" not in response.get_data(as_text=True)
    assert "prompt" not in payload


def test_dashboard_has_agent_startup_toast_and_event_log_scroll_control():
    html = (Path(__file__).parents[1] / "web" / "templates" / "index.html").read_text(encoding="utf-8")
    assert 'id="agent-startup-toast"' in html
    assert 'id="log-scroll-bottom"' in html
    assert 'id="event-log"' in html and 'tabindex="0"' in html
    assert 'id="open-prompts"' in html
    assert 'id="prompts-modal"' in html
    assert 'id="agent-prompt-editor"' in html
    assert 'id="content-task-prompt-editor"' in html
    assert 'id="save-prompts"' in html
    assert 'id="open-agent-sessions"' in html
    assert 'id="agent-cleanup-count"' in html
    assert 'id="agent-sessions-modal"' in html
    assert 'id="agent-sessions-list"' in html
    assert 'id="page-scroll-top"' in html
    assert 'id="page-scroll-bottom"' in html
    assert 'id="page-view-log"' in html
    assert 'id="product-type-modal"' in html
    assert 'id="check-agent"' in html
    assert 'id="agent-status-tooltip"' in html
    assert 'id="manifest-row-count"' in html

    js = (Path(__file__).parents[1] / "web" / "static" / "dashboard.js").read_text(encoding="utf-8")
    assert "handleMultiValuePaste" in js
    assert 'amazonUrlInput.addEventListener("paste"' in js
    assert 'shopifyIdInput.addEventListener("paste"' in js
    assert "manifest-row-count" in js
    assert "product-index" in js


def test_product_types_are_loaded_from_dedicated_json(tmp_path):
    root = package_root(tmp_path)
    client = create_app(root, store=OrchestratorStore(root)).test_client()
    bootstrap = client.get("/api/bootstrap").get_json()
    assert bootstrap["product_types"] == ["storage-cabinet", "console-table"]
    response = client.get("/api/product-types")
    assert response.status_code == 200
    assert response.get_json() == {
        "product_types": ["storage-cabinet", "console-table"],
        "source": "product_types.json",
    }


def test_agent_session_cleanup_lifecycle_keeps_current_and_removes_acknowledged_metadata(tmp_path):
    root = package_root(tmp_path)
    store = OrchestratorStore(root)
    first = store.create_agent_session("session-old")
    store.update_agent_session(first["id"], "ready", conversation_id="conversation-old", num_turns=3)
    store.create_agent_turn(first["id"], "bootstrap")
    store.event("agent_log", source="antigravity", session_id=first["id"], message="old event")

    second = store.create_agent_session("session-current")
    store.update_agent_session(second["id"], "ready", conversation_id="conversation-current", num_turns=1)

    sessions = {item["id"]: item for item in store.list_agent_sessions()}
    assert sessions[first["id"]]["cleanup_status"] == "pending_cleanup"
    assert sessions[first["id"]]["recorded_turns"] == 1
    assert sessions[second["id"]]["cleanup_status"] == "current"
    with pytest.raises(QueueConflict, match="pending_cleanup"):
        store.acknowledge_agent_cleanup(second["id"])

    result = store.acknowledge_agent_cleanup(first["id"])
    assert result["conversation_id"] == "conversation-old"
    assert result["deleted_events"] >= 1
    assert [item["id"] for item in store.list_agent_sessions()] == [second["id"]]
    with pytest.raises(KeyError):
        store.agent_session(first["id"])


def test_agent_session_cleanup_api_opens_tui_and_requires_manual_acknowledgement(tmp_path, monkeypatch):
    root = package_root(tmp_path)
    store = OrchestratorStore(root)
    old = store.create_agent_session("session-old")
    store.update_agent_session(old["id"], "stopped", conversation_id="conversation-old")
    current = store.create_agent_session("session-current")
    store.update_agent_session(current["id"], "ready", conversation_id="conversation-current")
    opened = {}

    def fake_open(project_root, conversation_id, *, executable):
        opened.update(project_root=project_root, conversation_id=conversation_id, executable=executable)
        return 4242

    monkeypatch.setattr("scraper.server._open_antigravity_cleanup_terminal", fake_open)
    runtime = FakeAgentRuntime(ready=False)
    app = create_app(root, store=store, agent_runtime=runtime)
    client = app.test_client()
    bootstrap = client.get("/api/bootstrap").get_json()
    csrf = bootstrap["csrf_token"]
    assert bootstrap["agent_sessions"][0]["id"] == current["id"]

    listed = client.get("/api/agent/sessions").get_json()
    assert listed["pending_cleanup"] == 1
    launched = client.post(
        f"/api/agent/sessions/{old['id']}/open-cleanup", json={}, headers=headers(csrf)
    )
    assert launched.status_code == 200
    assert launched.get_json()["terminal_pid"] == 4242
    assert opened["project_root"] == root.parent
    assert opened["conversation_id"] == "conversation-old"
    assert opened["executable"] == "agy"

    cannot_remove_current = client.post(
        f"/api/agent/sessions/{current['id']}/acknowledge-cleanup", json={}, headers=headers(csrf)
    )
    assert cannot_remove_current.status_code == 400
    acknowledged = client.post(
        f"/api/agent/sessions/{old['id']}/acknowledge-cleanup", json={}, headers=headers(csrf)
    )
    assert acknowledged.status_code == 200
    assert acknowledged.get_json()["deleted"] is True
    assert client.get("/api/agent/sessions").get_json()["pending_cleanup"] == 0


def test_prompts_api_reads_and_saves_only_fixed_prompt_files(tmp_path):
    root = package_root(tmp_path)
    client = create_app(root, store=OrchestratorStore(root)).test_client()
    csrf = client.get("/api/bootstrap").get_json()["csrf_token"]

    loaded = client.get("/api/prompts")
    assert loaded.status_code == 200
    assert loaded.get_json()["prompts"] == {
        "agent_prompt": "Write factual content.",
        "content_task_prompt": "Process one queued task.",
    }
    saved = client.put("/api/prompts", json={"prompts": {
        "agent_prompt": "Updated agent prompt.",
        "content_task_prompt": "Updated task prompt.\r\nSecond line.",
    }}, headers=headers(csrf))
    assert saved.status_code == 200
    assert saved.get_json()["restart_required"] is True
    assert (root / "AGENT_PROMPT.md").read_text(encoding="utf-8") == "Updated agent prompt.\n"
    assert (root / "CONTENT_TASK_PROMPT.md").read_text(encoding="utf-8") == "Updated task prompt.\nSecond line.\n"

    rejected = client.put("/api/prompts", json={"prompts": {
        "agent_prompt": "",
        "content_task_prompt": "Still valid",
    }}, headers=headers(csrf))
    assert rejected.status_code == 400
    assert (root / "AGENT_PROMPT.md").read_text(encoding="utf-8") == "Updated agent prompt.\n"


def test_dashboard_url_and_server_registration(tmp_path):
    assert _dashboard_url("127.0.0.1", 5000) == "http://127.0.0.1:5000"
    assert _dashboard_url("0.0.0.0", 5001) == "http://127.0.0.1:5001"
    assert _dashboard_url("::1", 5002) == "http://[::1]:5002"
    record = register_server_process(tmp_path, "127.0.0.1", 5000)
    payload = json.loads(record.read_text(encoding="utf-8"))
    assert payload["pid"] > 0
    assert payload["port"] == 5000
    unregister_server_process(record)
    assert not record.exists()


def test_docs_api_lists_only_markdown_and_text_and_blocks_traversal(tmp_path):
    root = package_root(tmp_path)
    docs = root / "docs"
    (docs / "nested").mkdir(parents=True)
    (docs / "guide.md").write_text("# Guide\n\nHello", encoding="utf-8")
    (docs / "notes.TXT").write_text("Plain notes", encoding="utf-8")
    (docs / "nested" / "more.md").write_text("More docs", encoding="utf-8")
    (docs / "ignored.json").write_text("{}", encoding="utf-8")
    (root / "outside.md").write_text("secret", encoding="utf-8")
    client = create_app(root, store=OrchestratorStore(root)).test_client()

    listing = client.get("/api/docs")
    assert listing.status_code == 200
    assert [item["path"] for item in listing.get_json()["documents"]] == ["guide.md", "nested/more.md", "notes.TXT"]
    content = client.get("/api/docs/content", query_string={"path": "guide.md"})
    assert content.status_code == 200
    assert content.get_json()["content"] == "# Guide\n\nHello"
    assert content.get_json()["format"] == "markdown"
    assert content.get_json()["rendered_html"] == "<h1>Guide</h1>\n<p>Hello</p>\n"
    plain = client.get("/api/docs/content", query_string={"path": "notes.TXT"}).get_json()
    assert plain["format"] == "text"
    assert plain["rendered_html"] == '<pre class="docs-plain-text">Plain notes</pre>'
    assert client.get("/api/docs/content", query_string={"path": "ignored.json"}).status_code == 400
    assert client.get("/api/docs/content", query_string={"path": "../outside.md"}).status_code == 400


def test_docs_markdown_renderer_supports_rich_content_and_escapes_source_html():
    kind, rendered = _render_doc_content(
        ".md",
        "# Heading\n\n| Name | Value |\n| --- | ---: |\n| Price | **$42** |\n\n<script>alert('x')</script>",
    )
    assert kind == "markdown"
    assert "<h1>Heading</h1>" in rendered
    assert "<table>" in rendered and "<strong>$42</strong>" in rendered
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered


class FakeAgentRuntime:
    def __init__(self, ready=False):
        self.ready = ready
        self.restarts = 0

    def is_ready(self):
        return self.ready

    def state(self):
        return {"status": "ready" if self.ready else "initializing", "ready": self.ready, "message": "test"}

    def restart(self):
        self.restarts += 1
        return self.state()

    def health_check(self):
        return {"active": True, "drift_seconds": 1, "agent": self.state()}


def test_mutations_are_gated_until_agent_is_ready_but_restart_remains_available(tmp_path):
    root = package_root(tmp_path)
    runtime = FakeAgentRuntime()
    app = create_app(root, store=OrchestratorStore(root), agent_runtime=runtime)
    client = app.test_client()
    csrf = client.get("/api/bootstrap").get_json()["csrf_token"]
    blocked = client.put("/api/manifest", json=MANIFEST, headers=headers(csrf))
    assert blocked.status_code == 503
    assert blocked.get_json()["code"] == "agent_not_ready"
    restarted = client.post("/api/agent/restart", json={}, headers=headers(csrf))
    assert restarted.status_code == 202
    assert runtime.restarts == 1
    runtime.ready = True
    assert client.put("/api/manifest", json=MANIFEST, headers=headers(csrf)).status_code == 200
    checked = client.post("/api/agent/health-check", json={}, headers=headers(csrf))
    assert checked.status_code == 200
    assert checked.get_json()["active"] is True


def test_api_requires_csrf_and_origin_then_creates_uuid_run(tmp_path):
    root = package_root(tmp_path)
    store = OrchestratorStore(root)
    app = create_app(root, store=store)
    client = app.test_client()
    bootstrap = client.get("/api/bootstrap").get_json()
    assert client.put("/api/manifest", json=MANIFEST).status_code == 403
    assert client.put("/api/manifest", json=MANIFEST, headers={
        "Origin": "https://evil.example", "X-CSRF-Token": bootstrap["csrf_token"],
    }).status_code == 403
    saved = client.put("/api/manifest", json=MANIFEST, headers=headers(bootstrap["csrf_token"]))
    assert saved.status_code == 200
    created = client.post("/api/runs", json={"manifest": MANIFEST, "options": {"dry_run": True}}, headers=headers(bootstrap["csrf_token"]))
    assert created.status_code == 201
    payload = created.get_json()
    assert len(payload["id"]) == 32
    assert payload["id"] != payload["manifest_digest"]


def test_content_editor_saves_draft_finalizes_and_requeues(tmp_path):
    root = package_root(tmp_path)
    store = OrchestratorStore(root)
    manifest = parse_manifest_payload(MANIFEST, root / "input" / "products.json")
    run = store.create_run(manifest, MANIFEST, {"dry_run": True})
    product = next(iter(run["products"].values()))
    workspace = store.workspace(store.product(product["id"]))
    (workspace / "source.json").write_text(json.dumps({
        "title": valid_content()["title"] + " " + valid_content()["seo_product_title"],
        "bullets": ["Test product evidence."],
        "aplus_text": "",
    }), encoding="utf-8")
    gallery = workspace / "evidence" / "gallery"
    gallery.mkdir(parents=True)
    (gallery / "contact-sheet.jpg").write_bytes(b"contact-sheet")
    (gallery / "001.jpg").write_bytes(b"first-image")
    store.set_product_status(product["id"], "crawling")
    store.set_product_status(product["id"], "crawled")
    store.set_product_status(product["id"], "price_verified")
    store.enqueue_content(product["id"])
    claim = store.claim_expected_content("fixture-agent", product["id"])
    assert claim is not None
    context = store.content_context(product["id"], claim["claim_token"])
    store.evidence_path(product["id"], claim["claim_token"], "gallery/contact-sheet.jpg")
    store.evidence_path(product["id"], claim["claim_token"], "gallery/001.jpg")
    store.write_visual_analysis(product["id"], claim["claim_token"], {
        "task_id": product["id"],
        "source_digest": context["source_digest"],
        "target_identity": "Sculptural profile console",
        "evidence_ids": ["gallery/contact-sheet.jpg", "gallery/001.jpg"],
        "design_keywords": ["sculptural profile", "open tier composition", "layered silhouette"],
        "shape_keywords": ["flowing outline", "rounded transitions", "asymmetrical framework"],
    })
    store.release_content(product["id"], claim["claim_token"], "manual editor fixture")
    app = create_app(root, store=store)
    client = app.test_client()
    csrf = client.get("/api/bootstrap").get_json()["csrf_token"]
    endpoint = f"/api/content-tasks/{product['id']}"

    saved = client.put(endpoint + "/draft", json={"content": valid_content()}, headers=headers(csrf))
    assert saved.status_code == 200
    finalized = client.post(endpoint + "/finalize", json={}, headers=headers(csrf))
    assert finalized.status_code == 200
    assert (store.workspace(store.product(product["id"])) / "content.json").is_file()
    requeued = client.post(endpoint + "/requeue", json={}, headers=headers(csrf))
    assert requeued.status_code == 200
    assert requeued.get_json()["revision"] == 1
    assert not (store.workspace(store.product(product["id"])) / "content.json").exists()


def test_content_failure_can_be_retried_without_misrouting_to_shopify(tmp_path):
    root = package_root(tmp_path)
    store = OrchestratorStore(root)
    manifest = parse_manifest_payload(MANIFEST, root / "input" / "products.json")
    run = store.create_run(manifest, MANIFEST, {"dry_run": True})
    product = next(iter(run["products"].values()))
    workspace = store.workspace(store.product(product["id"]))
    (workspace / "source.json").write_text(json.dumps({"title": "Test product"}), encoding="utf-8")
    for status in ("crawling", "crawled", "price_verified"):
        store.set_product_status(product["id"], status)
    store.enqueue_content(product["id"])
    store.begin_content_automation_attempt(product["id"])
    store.fail_content_automation(product["id"], "Agent protocol failure", terminal=True)

    app = create_app(root, store=store)
    client = app.test_client()
    csrf = client.get("/api/bootstrap").get_json()["csrf_token"]
    response = client.post(
        f"/api/content-tasks/{product['id']}/retry", json={}, headers=headers(csrf)
    )

    assert response.status_code == 200
    assert response.get_json()["state"] == "queued"
    assert store.product(product["id"])["status"] == "content_queued"


def test_sse_cursor_skips_old_events(tmp_path):
    root = package_root(tmp_path)
    store = OrchestratorStore(root)
    first = store.event("first", message="old")
    second = store.event("second", message="new")
    app = create_app(root, store=store)
    response = app.test_client().get(f"/api/queue/events?after={first}", buffered=False)
    chunk = next(response.response).decode("utf-8")
    response.close()
    assert f"id: {second}" in chunk
    assert "second" in chunk
    assert "first" not in chunk
