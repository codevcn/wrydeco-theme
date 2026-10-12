from copy import deepcopy
import json

import pytest

from scraper.aeo import build_input, validate_and_render
from scraper.aeo.shopify_adapter import apply_html
from scraper.errors import ContentValidationError, ShopifyError
from scraper.io_utils import atomic_write_json, load_json
from scraper.manifest import parse_manifest_payload
from scraper.store import OrchestratorStore, ClaimError
from scraper.tests.test_queue import make_root, queue_product, prime_visual, content
from scraper.tests.test_sku_apply import setup_apply


def draft():
    return {
        "overview": {"text": (
            "This side table brings a sculptural profile and an asymmetrical silhouette to an accent arrangement. "
            "Its rounded shelf edges and open tier composition create a clearly defined outline when viewed from different angles. "
            "The design combines a stacked outline with a balanced visual rhythm, making the visible structure the focus of the piece. "
            "Consider the outline when planning its relationship with other furniture in your room. "
            "The product information identifies this piece as a side table, while the gallery provides a closer view of its distinctive shape and composition."
        ), "evidence_ids": ["source:title", "visual:0", "visual:1", "visual:2", "visual:3", "visual:4", "visual:5"]},
        "summary": [{"label": "Design", "value": "Sculptural profile", "evidence_ids": ["visual:0"]}],
        "faq": [
            {"question": "What shape does this table have?", "answer": (
                "This side table has an asymmetrical silhouette with rounded shelf edges and a stacked outline. "
                "These details describe the visible shape shown in the gallery and help explain how its profile is composed."
            ), "evidence_ids": ["visual:3", "visual:4", "visual:5"]},
            {"question": "What defines the table's design?", "answer": (
                "The design is defined by a sculptural profile and an open tier composition. "
                "A balanced visual rhythm connects the visible parts of the table, bringing attention to its overall outline and the arrangement of its tiers."
            ), "evidence_ids": ["visual:0", "visual:1", "visual:2"]},
            {"question": "What product type is this piece?", "answer": (
                "The product information identifies this piece as a side table. "
                "Its sculptural profile and rounded shelf edges describe the particular design of this model, so the shape should be considered alongside the stated product type."
            ), "evidence_ids": ["source:title", "visual:0", "visual:3"]},
        ],
    }


def context():
    return build_input({"asin": "B000000000", "product_type": "side-table"},
                       {"title": "Sculptural Profile Side Table", "bullets": []},
                       {"variants": [{"options": [{"name": "Size", "value": '40\'\'Wx 30\'\'H x 16\'\'D (Popular size)'},
                                                    {"name": "Finish", "value": "Walnut"}]},
                                     {"options": [{"name": "Size", "value": '47\'\'Wx 32\'\'H x 20\'\'D'}]}]},
                       {"design_keywords": ["sculptural profile", "open tier composition", "balanced visual rhythm"],
                        "shape_keywords": ["rounded shelf edges", "asymmetrical silhouette", "stacked outline"]})


def test_render_is_deterministic_plain_html_and_input_is_public():
    ctx = context()
    result = validate_and_render(ctx, draft())
    assert result["valid"] and result["faq_count"] == 3
    assert result["html"] == validate_and_render(ctx, draft())["html"]
    assert result["html"].count('<div class="aeo-faq-item">') == 3
    assert "evidence_ids" not in result["html"] and "script" not in result["html"]
    assert "Popular" not in json.dumps(ctx)
    other = build_input({"asin": "B000000001"}, {}, {}, {})
    assert ctx["input_digest"] != other["input_digest"]


@pytest.mark.parametrize("case", ["missing_refs", "few_faq", "duplicate", "html", "unsupported_question", "material", "axes", "mixed", "unit", "weighted", "tiers"])
def test_invalid_claims_and_shapes_are_rejected(case):
    value = draft()
    if case == "missing_refs": value["summary"][0]["evidence_ids"] = ["not-a-fact"]
    if case == "few_faq": value["faq"] = value["faq"][:2]
    if case == "duplicate": value["faq"][1]["question"] = value["faq"][0]["question"]
    if case == "html": value["summary"][0]["value"] = '<script>alert(1)</script>'
    if case == "unsupported_question": value["faq"][0]["question"] = "Does its waterproof coating protect the table?"
    if case == "material": value["summary"] = [{"label": "Design", "value": "Solid walnut wood", "evidence_ids": ["option:1"]}]
    if case == "weighted": value["summary"][0]["value"] = "Weighted foundation"
    if case == "tiers": value["summary"][0]["value"] = "Single-tier structure"
    if case in {"axes", "mixed", "unit"}:
        text = {"axes": "30 inches wide", "mixed": "40 inches wide, 32 inches high, 16 inches deep", "unit": "40 cm wide"}[case]
        value["summary"] = [{"label": "Dimensions", "value": text, "evidence_ids": ["option:0", "option:2"]}]
    with pytest.raises(ContentValidationError, match="aeo"):
        validate_and_render(context(), value)


def test_real_dimension_format_accepts_same_tuple_and_unitless_axes():
    for text in ("40 inches wide, 30 inches high, 16 inches deep", "40 W x 30 H x 16 D"):
        value = draft()
        value["summary"] = [{"label": "Dimensions", "value": text, "evidence_ids": ["option:0"]}]
        assert validate_and_render(context(), value)["valid"]


class MetafieldClient:
    def __init__(self, current=None, race=False, missing=False):
        self.current, self.race, self.missing = current, race, missing
        self.writes = []
        self.definitions = 0
    def read_aeo_metafield(self, _): return deepcopy(self.current)
    def ensure_aeo_definition(self): self.definitions += 1
    def write_aeo_metafield(self, _, value, digest):
        self.writes.append((value, digest))
        if self.race:
            self.current = {"type": "multi_line_text_field", "value": "Human edit", "compareDigest": "human"}
            raise ShopifyError("compareDigest mismatch")
        if not self.missing:
            self.current = {"type": "multi_line_text_field", "value": value, "compareDigest": "new"}


def test_empty_write_and_retry_are_idempotent_and_cas_guarded():
    client = MetafieldClient()
    assert apply_html(client, "1", "<p>AEO</p>")["status"] == "written"
    assert client.writes == [("<p>AEO</p>", None)]
    assert apply_html(client, "1", "<p>AEO</p>")["status"] == "verified"
    assert len(client.writes) == 1
    blank = MetafieldClient({"type": "multi_line_text_field", "value": " ", "compareDigest": "old"})
    apply_html(blank, "1", "new")
    assert blank.writes == [("new", "old")]


def test_existing_and_concurrent_human_content_are_preserved():
    client = MetafieldClient({"type": "multi_line_text_field", "value": "Old AEO"})
    assert apply_html(client, "1", "new")["status"] == "preserved"
    assert client.writes == [] and client.definitions == 0
    race = MetafieldClient(race=True)
    assert apply_html(race, "1", "new")["value"] == "Human edit"
    assert len(race.writes) == 1


def test_type_conflict_and_failed_readback_stop_product():
    client = MetafieldClient({"type": "json", "value": "{}"})
    with pytest.raises(ShopifyError, match="type"):
        apply_html(client, "1", "new")
    assert client.writes == []
    with pytest.raises(ShopifyError, match="converge"):
        apply_html(MetafieldClient(missing=True), "1", "new")


def new_aeo_task(root):
    store = OrchestratorStore(root)
    payload = {"products": [{"amazon_url": "https://www.amazon.com/dp/B000000000", "shopify_product_id": "123", "mode": "auto"}]}
    manifest = parse_manifest_payload(payload, root / "input.json")
    run = store.create_run(manifest, payload, {"aeo_version": 1, "dry_run": True})
    product = next(iter(run["products"].values()))
    queue_product(store, product)
    claim = store.claim_next_content("test-agent")
    prime_visual(store, product, claim)
    store.content_context(product["id"], claim["claim_token"])
    value = content()
    value["aeo"] = draft()
    store.write_content_draft(product["id"], claim["claim_token"], value)
    return store, product, claim


def test_new_run_prompt_is_frozen_and_context_contains_contract(tmp_path):
    root = make_root(tmp_path)
    store, product, claim = new_aeo_task(root)
    ctx = store.content_context(product["id"], claim["claim_token"])
    assert ctx["aeo"]["required"] and "aeo" in ctx["schema"]["required"]
    (root / "aeo").mkdir()
    (root / "aeo" / "PROMPT.md").write_text("Changed later", encoding="utf-8")
    assert store.content_context(product["id"], claim["claim_token"])["aeo"]["prompt"] == ctx["aeo"]["prompt"]


def test_queue_finalizes_generated_html_and_dashboard_manual_roundtrip(tmp_path):
    store, product, claim = new_aeo_task(make_root(tmp_path))
    assert store.validate_content_draft(product["id"], claim["claim_token"])["aeo_html"]
    store.release_content(product["id"], claim["claim_token"], "Dashboard test")
    task = store.content_task(product["id"])
    assert task["valid"] and task["aeo_required"] and task["aeo_preview_html"]
    edited = deepcopy(task["content"])
    edited["aeo"]["summary"][0]["value"] = "Sculptural profile & open tier composition"
    store.save_manual_draft(product["id"], edited)
    store.finalize_manual_content(product["id"])
    workspace = store.workspace(store.product(product["id"]))
    final = load_json(workspace / "content.json")
    assert "&amp;" in final["aeo_html"]
    assert load_json(workspace / "aeo_validation.json")["valid"]
    assert (workspace / "aeo.html").read_text(encoding="utf-8") == final["aeo_html"]
    assert store.queue_status()["apply"]["queued"] == 1


@pytest.mark.parametrize("dry_run", [False, True])
def test_apply_flow_writes_only_aeo_metafield_and_retry_preserves_changes(tmp_path, monkeypatch, dry_run):
    service, product, client, workspace = setup_apply(tmp_path, monkeypatch, dry_run=dry_run)
    service.store.run_record = lambda _: {"options": {"dry_run": dry_run, "aeo_version": 1}}
    source = {"title": "Sculptural Profile Side Table", "gallery_images": ["https://example.test/image.jpg"]}
    atomic_write_json(workspace / "source.json", source)
    atomic_write_json(workspace / "visual_analysis.json", {"design_keywords": ["sculptural profile", "open tier composition", "balanced visual rhythm"],
                                                        "shape_keywords": ["rounded shelf edges", "asymmetrical silhouette", "stacked outline"]})
    value = load_json(workspace / "content.json")
    value["aeo"] = draft()
    atomic_write_json(workspace / "content.json", value)
    metafield = MetafieldClient()
    client.read_aeo_metafield = metafield.read_aeo_metafield
    client.ensure_aeo_definition = metafield.ensure_aeo_definition
    client.write_aeo_metafield = metafield.write_aeo_metafield
    result = service.apply_product(product)
    if dry_run:
        assert metafield.writes == [] and client.stages == []
    else:
        assert result["aeo_verified"] and result["aeo_status"] == "written"
        assert metafield.writes[0][0].startswith('<div class="wrydeco-product-aeo">')
        metafield.current["value"] = "Human change after publication"
        again = service.apply_product(product)
        assert again["aeo_status"] == "preserved" and len(metafield.writes) == 1
        assert client.stages.count("product_set") == 1


def test_new_run_missing_aeo_fails_before_shopify_mutation(tmp_path, monkeypatch):
    service, product, client, workspace = setup_apply(tmp_path, monkeypatch)
    service.store.run_record = lambda _: {"options": {"aeo_version": 1}}
    with pytest.raises(ContentValidationError, match="aeo"):
        service.apply_product(product)
    assert client.stages == []


def test_visual_changes_require_new_aeo_context_read(tmp_path):
    store, product, claim = new_aeo_task(make_root(tmp_path))
    prime_visual(store, product, claim)
    value = content()
    value["aeo"] = draft()
    with pytest.raises(ClaimError, match="context"):
        store.write_content_draft(product["id"], claim["claim_token"], value)
    ctx = store.content_context(product["id"], claim["claim_token"])
    assert any(fact["kind"] == "approved_visual" for fact in ctx["aeo"]["input"]["facts"])
    store.write_content_draft(product["id"], claim["claim_token"], value)


def test_invalid_aeo_keeps_evidence_and_terminal_failure_does_not_block_next_product(tmp_path):
    store, product, claim = new_aeo_task(make_root(tmp_path))
    value = content()
    value["aeo"] = draft()
    value["aeo"]["faq"] = value["aeo"]["faq"][:2]
    store.write_content_draft(product["id"], claim["claim_token"], value)
    with pytest.raises(ContentValidationError, match="3–8"):
        store.validate_content_draft(product["id"], claim["claim_token"])
    workspace = store.workspace(store.product(product["id"]))
    assert not load_json(workspace / "aeo_validation.json")["valid"]
    assert (workspace / "aeo_input.json").exists() and (workspace / "content.temp.json").exists()
    store.fail_content_automation(product["id"], "AEO insufficient evidence", terminal=True)
    assert store.product(product["id"])["status"] == "needs_attention"
    from scraper.tests.test_queue import create_run
    _, next_product = create_run(store, "B000000001", "124")
    queue_product(store, next_product, "architectural")
    assert store.claim_next_content("next-agent")["task_id"] == next_product["id"]
    assert store.queue_status()["apply"].get("queued", 0) == 0
