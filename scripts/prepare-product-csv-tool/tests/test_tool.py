from __future__ import annotations

import ast
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from io import BytesIO
import json
from pathlib import Path
import sqlite3
import sys
from unittest.mock import Mock

import pytest
from PIL import Image

TOOL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL))
from wry_csv.common import ROOT, Invalid, read_json, write_json
from wry_csv.content import THRESHOLDS, compare_content, content_fingerprints, evidence_context
from wry_csv.exporter import (AEO, AUTHOR, MATERIAL, ROOM, STYLE, DEFAULTS, build_csv, load_manifest,
                              prepare, render_rows, serialize, template_headers, verify_csv)
from wry_csv.cli import main
from wry_csv.media import fetch_image, image_info
from wry_csv.shopify import Admin, stage


@pytest.fixture
def batch(tmp_path):
    image_paths = []
    for index, color in enumerate(("red", "blue", "green")):
        path = tmp_path / f"image-{index}.png"
        Image.new("RGB", (12, 10), color).save(path)
        image_paths.append(path)
    product = {
        "id": "SP01", "handle": "handcrafted-rustic-solid-wood-side-table-modern-homes",
        "category": "Furniture > Tables > Accent Tables > End Tables", "collection": "side-tables",
        "type": "side-tables", "tags": ["side-tables"], "author_handle": "khoi-hoang",
        "interior_style": ["Japandi", "Mid-Century", "Organic Modern"], "room_type": ["Living Room", "Bedroom"],
        "images": [{"path": str(p), "alt": f"Side table view {index+1}", "url": f"https://cdn.example.com/{p.name}"} for index, p in enumerate(image_paths)],
        "variants": [{"options": [{"name": "Size", "value": size}], "price": price, "source_ref": f"price.png row {index+1}"}
                     for index, (size, price) in enumerate((("40x30", "2083"), ("47x32", "2500.50")))],
        "evidence": {"source": {
            "title": "Handcrafted Rustic Solid Wood Side Table for Modern Homes",
            "bullets": ["Solid wood construction with practical storage and a warm finish.", "Organic grain is confirmed by supplier.",
                        "Offered for bedrooms and modern living spaces."], "aplus_text": ""},
            "visual": {"target_identity": "side table", "evidence_ids": [str(image_paths[0]), str(image_paths[1])],
                       "design_keywords": ["rustic", "sculptural profile", "open tier composition"],
                       "shape_keywords": ["organic", "rounded shelf edges", "asymmetrical silhouette"]}},
        "content": {
            "title": "Handcrafted Rustic Solid Wood Side Table for Modern Homes",
            "seo_product_title": "Handcrafted Rustic Solid Wood Side Table for Modern Homes",
            "seo_title": "Rustic Solid Wood Side Table for Modern Homes | Wrydeco",
            "seo_description": "Explore the handcrafted rustic solid wood side table with organic grain, practical storage, and a warm finish for bedrooms and modern living spaces today.",
            "handle": "handcrafted-rustic-solid-wood-side-table-modern-homes",
            "description_html": '<div class="wrydeco-product-description"><p>A rustic organic side table with practical storage.</p></div>',
            "aeo": {
                "overview": {"text": (
                    "This side table has a sculptural profile and an asymmetrical silhouette with rounded shelf edges. "
                    "Its open tier composition creates a clearly defined outline when viewed from different angles. "
                    "The design connects the visible parts of the table through a distinctive arrangement of its tiers. "
                    "Consider the outline when planning its relationship with other furniture in your room. "
                    "The supplied product information identifies this piece as a side table, while the gallery provides a closer view of its shape and visible structure."),
                    "evidence_ids": ["source:title", "visual:1", "visual:2", "visual:4", "visual:5"]},
                "summary": [],
                "faq": [
                    {"question": "What shape does this table have?", "answer": "This side table has an asymmetrical silhouette with rounded shelf edges and a sculptural profile. These details describe the visible shape shown in the gallery and explain how its outline is composed.", "evidence_ids": ["visual:1", "visual:4", "visual:5"]},
                    {"question": "What defines the table's design?", "answer": "The design is defined by a sculptural profile and an open tier composition. The visible parts connect through a distinctive arrangement, bringing attention to the table's overall outline and the relationship between its tiers.", "evidence_ids": ["visual:1", "visual:2"]},
                    {"question": "What product type is this piece?", "answer": "The supplied product information identifies this piece as a side table. Its sculptural profile and rounded shelf edges describe the particular design of this model, so the shape can be considered alongside the stated product type.", "evidence_ids": ["source:title", "visual:1", "visual:4"]},
                ]}},
    }
    manifest = {"version": 1, "shop": "wrydeco.myshopify.com", "currency": "USD", "products": [product]}
    snapshot = {"shop": manifest["shop"], "currency": "USD", "collected_at": datetime.now(timezone.utc).isoformat(),
                "definitions": {"interior_style": {"type": "list.single_line_text_field", "choices": ["Rustic", "Japandi", "Mid-Century", "Organic Modern"]},
                                "room_type": {"type": "list.single_line_text_field", "choices": ["Living Room", "Bedroom"]},
                                "product_material": {"type": "single_line_text_field"},
                                "author_info": {"type": "metaobject_reference"},
                                "aeo_html": {"type": "multi_line_text_field"},
                                "wood_type": {"type": "single_line_text_field"},
                                "seo_product_title": {"type": "single_line_text_field"}},
                "authors": [{"handle": "khoi-hoang", "id": "gid://shopify/Metaobject/1"}],
                "collections": [{"handle": "side-tables", "ruleSet": {"appliedDisjunctively": False,
                                    "rules": [{"column": "TYPE", "relation": "EQUALS", "condition": "side-tables"}]}}],
                "categories": {product["category"]: "gid://shopify/TaxonomyCategory/fake"},
                "occupied_skus": [], "occupied_handles": []}
    # Header-only fixture is derived from the pinned contract, not the renderer.
    template = tmp_path / "template.csv"
    import csv
    with template.open("w", encoding="utf-8", newline="") as stream:
        csv.writer(stream, lineterminator="\n").writerow(read_json(TOOL / "native_contract.json")["headers"])
    return manifest, snapshot, template


def normalized(batch, tmp_path):
    manifest, snapshot, template = batch
    products, report = prepare(manifest, tmp_path, snapshot, require_urls=True)
    assert report["valid"], report
    return products, snapshot, template


def good_fetch(url):
    return {"url": url, "http_status": 200, "mime": "image/png", "width": 12, "height": 10}


def test_native_round_trip_and_image_only_rows(batch, tmp_path):
    products, snapshot, template = normalized(batch, tmp_path)
    output = tmp_path / "result.csv"
    result = build_csv(output, products, template, snapshot, fetcher=good_fetch)
    assert result["ready_for_import"] and result["columns"] == 71
    assert (result["products"], result["variants"], result["images"]) == (1, 2, 3)
    import csv
    with output.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0][STYLE] == "Japandi\nMid-Century\nOrganic Modern"
    assert rows[0][ROOM] == "Living Room\nBedroom"
    assert rows[0][MATERIAL] == "wood" and rows[0][AUTHOR] == "khoi-hoang"
    assert rows[0]["Status"] == "active"
    assert rows[0]["Published"] == "false"
    for row in rows[:2]:
        assert all(row[key] == value for key, value in DEFAULTS.items())
    assert rows[1]["Published"] == rows[1]["Status"] == rows[1][AEO] == ""
    assert {k for k, v in rows[2].items() if v} == {"Handle", "Image Src", "Image Position", "Image Alt Text"}
    assert [r["Variant Price"] for r in rows[:2]] == ["2083", "2500.50"]
    assert b"\r" not in output.read_bytes()


@pytest.mark.parametrize("field,value", [
    ("Variant Fulfillment Service", ""), ("Variant Inventory Policy", ""),
    ("Variant Weight Unit", ""), ("Variant Grams", "0"),
    ("Variant Requires Shipping", "TRUE"), ("Variant Taxable", "TRUE"),
    ("Variant Inventory Tracker", "shopify"), ("Variant Inventory Qty", ""),
    ("Published", "FALSE"), ("Gift Card", "FALSE"), ("Status", ""), ("Status", "draft"),
    (MATERIAL, ""), ("Product Category", ""), ("Tags", ""),
    (STYLE, '["Rustic"]'), (ROOM, '["Living Room"]'), (ROOM, 'Living Room\\nBedroom'),
    (AUTHOR, "gid://shopify/Metaobject/1"),
])
def test_regressions_rejected_by_independent_reader(batch, tmp_path, field, value):
    products, snapshot, template = normalized(batch, tmp_path)
    headers = template_headers(template)
    rows = render_rows(products, headers)
    rows[0][field] = value
    path = tmp_path / "bad.csv"
    path.write_bytes(serialize(headers, rows))
    report = verify_csv(path, template, online=False)
    assert not report["valid"] and any(e["field"] == field for e in report["errors"])


def test_missing_column_wrong_order_and_parent_repetition(batch, tmp_path):
    products, _, template = normalized(batch, tmp_path)
    headers = template_headers(template)
    rows = render_rows(products, headers)
    rows[1]["Status"] = "active"
    path = tmp_path / "bad.csv"
    path.write_bytes(serialize(headers, rows))
    assert any(e["field"] == "Status" for e in verify_csv(path, template, online=False)["errors"])
    path.write_bytes(serialize(list(reversed(headers)), rows))
    assert not verify_csv(path, template, online=False)["valid"]
    path.write_bytes(serialize([h for h in headers if h != MATERIAL], [{k:v for k,v in r.items() if k != MATERIAL} for r in rows]))
    assert not verify_csv(path, template, online=False)["valid"]


def test_missing_or_404_media_never_produces_final_output(batch, tmp_path):
    products, snapshot, template = normalized(batch, tmp_path)
    def fail(url):
        raise Invalid("Image GET returned HTTP 404")
    output = tmp_path / "never.csv"
    report = build_csv(output, products, template, snapshot, fetcher=fail)
    assert not report["valid"] and not output.exists() and report["media"]["checked"] == 3
    assert not output.with_name(output.name + ".candidate").exists()
    del batch[0]["products"][0]["images"][0]["url"]
    _, report = prepare(batch[0], tmp_path, snapshot, require_urls=True)
    assert not report["valid"]


def test_mutated_price_and_image_order_are_detected_against_manifest(batch, tmp_path):
    products, _, template = normalized(batch, tmp_path)
    headers = template_headers(template)
    planned = render_rows(products, headers)
    tampered = deepcopy(planned)
    tampered[0]["Variant Price"] = "9999"
    tampered[0]["Image Src"], tampered[1]["Image Src"] = tampered[1]["Image Src"], tampered[0]["Image Src"]
    path = tmp_path / "tampered.csv"
    path.write_bytes(serialize(headers, tampered))
    result = verify_csv(path, template, expected=planned, fetcher=good_fetch)
    assert not result["valid"] and any(e["field"] == "Variant Price" for e in result["errors"])


@pytest.mark.parametrize("mutation", ["duplicate_variant", "ambiguous_price", "bad_choice", "bad_author", "bad_category", "unread_image", "unsupported_fact", "bad_aeo", "unknown_key", "occupied_handle", "stale_snapshot"])
def test_batch_gates(batch, tmp_path, mutation):
    manifest, snapshot, _ = batch
    product = manifest["products"][0]
    if mutation == "duplicate_variant": product["variants"].append(deepcopy(product["variants"][0]))
    if mutation == "ambiguous_price": product["variants"][0]["price"] = "2,083"
    if mutation == "bad_choice": product["room_type"] = ["Office"]
    if mutation == "bad_author": product["author_handle"] = "missing-author"
    if mutation == "bad_category": product["category"] = "Uncategorized"
    if mutation == "unread_image": product["evidence"]["visual"]["evidence_ids"] = ["unread.jpg"]
    if mutation == "unsupported_fact": product["content"]["description_html"] = '<div class="wrydeco-product-description"><p>Rustic organic waterproof table.</p></div>'
    if mutation == "bad_aeo": product["content"]["aeo"]["overview"]["evidence_ids"] = ["fake:id"]
    if mutation == "unknown_key": product["Google Shopping"] = "unwanted"
    if mutation == "occupied_handle": snapshot["occupied_handles"] = [product["handle"]]
    if mutation == "stale_snapshot": snapshot["collected_at"] = (datetime.now(timezone.utc)-timedelta(days=2)).isoformat()
    try:
        _, report = prepare(manifest, tmp_path, snapshot)
        assert not report["valid"]
    except Invalid:
        assert mutation == "stale_snapshot"


def test_short_artwork_title_handle_and_missing_history(batch, tmp_path):
    manifest, snapshot, template = batch
    product = manifest["products"][0]
    product["approved_artwork_title"] = product["content"]["title"] = "The Golden Bough"
    product["approved_handle"] = product["handle"] = product["content"]["handle"] = "the-golden-bough"
    products, report = prepare(manifest, tmp_path, snapshot)
    assert report["valid"] and not report["historical_coverage"]["complete_catalog"]
    assert len(report["content"][0]["exceptions"]) == 2
    assert render_rows(products, template_headers(template))[0]["Title"] == "The Golden Bough"


def test_multi_product_rows_and_batch_duplicates(batch, tmp_path):
    products, snapshot, template = normalized(batch, tmp_path)
    second = deepcopy(products[0])
    second["id"] = "SP02"
    second["handle"] = "a-different-product-handle"
    for i, variant in enumerate(second["variants"], 1):
        variant["sku"] = f"WRY-SECIND-NAT-40X30-{i:02d}"
    rows = render_rows([products[0], second], template_headers(template))
    assert [row["Status"] for row in rows if row["Title"]] == ["active", "active"]
    assert all(row["Status"] == "" for row in rows if not row["Title"])
    path = tmp_path / "multi.csv"
    path.write_bytes(serialize(template_headers(template), rows))
    result = verify_csv(path, template, expected=rows, snapshot=snapshot, fetcher=good_fetch)
    assert result["products"] == 2 and result["variants"] == 4 and result["images"] == 6
    reports = [{"fingerprints": content_fingerprints(p["content"])} for p in [products[0], second]]
    assert compare_content([products[0], second], reports, None)["collisions"]


def test_history_is_read_only_and_detects_collisions(batch, tmp_path):
    products, report = prepare(batch[0], tmp_path, batch[1])
    path = tmp_path / "history.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE content_fingerprints(product_id,field,normalized_text,sha256,active)")
        fp = report["content"][0]["fingerprints"]["title"]
        db.execute("INSERT INTO content_fingerprints VALUES(?,?,?,?,1)", ("prior", "title", fp["normalized"], fp["sha256"]))
    before = path.read_bytes()
    compared = compare_content(products, report["content"], path)
    assert compared["collisions"] and compared["historical_coverage"]["records"] == 1
    assert path.read_bytes() == before


def test_thresholds_match_module1():
    tree = ast.parse((ROOT / "auto/module-1/scraper/store.py").read_text(encoding="utf-8"))
    method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_content_collisions")
    assignment = next(n for n in method.body if isinstance(n, ast.Assign))
    assert ast.literal_eval(assignment.value) == THRESHOLDS


def test_image_download_rejects_404_and_html_and_corrupt_bytes(monkeypatch):
    import wry_csv.media as media
    monkeypatch.setattr(media, "public_url", lambda url: None)
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    session = Mock()
    session.__enter__ = Mock(return_value=session)
    session.__exit__ = Mock(return_value=False)
    session.get.return_value = response
    monkeypatch.setattr(media.requests, "Session", lambda: session)
    response.status_code = 404
    with pytest.raises(Invalid, match="404"): fetch_image("https://cdn.example.com/missing.png")
    response.status_code = 200
    response.headers = {"Content-Type": "text/html"}
    with pytest.raises(Invalid, match="Content-Type"): fetch_image("https://cdn.example.com/html.png")
    response.headers = {"Content-Type": "image/png"}
    response.iter_content.return_value = [b"not an image"]
    with pytest.raises(Invalid, match="decoded"): fetch_image("https://cdn.example.com/fake.png")


def test_stage_checkpoints_real_id_before_poll_and_resumes_without_create(batch, tmp_path, monkeypatch):
    products, _, _ = normalized(batch, tmp_path)
    for image in products[0]["images"]:
        image.pop("url")
    checkpoint = {"files": {}}
    path = tmp_path / "checkpoint.json"
    admin = Mock()
    def graphql(query, variables):
        if "stagedUploadsCreate" in query:
            return {"stagedUploadsCreate": {"stagedTargets": [{"url": "https://upload.example.com", "resourceUrl": "https://upload.example.com/file", "parameters": []}], "userErrors": []}}
        assert "fileCreate" in query and variables["files"][0]["duplicateResolutionMode"] == "RAISE_ERROR"
        return {"fileCreate": {"files": [{"id": "gid://shopify/MediaImage/1"}], "userErrors": []}}
    admin.graphql.side_effect = graphql
    def interrupted(file_id):
        saved = read_json(path)
        assert next(iter(saved["files"].values()))["id"] == file_id
        raise Invalid("Interrupted processing")
    admin.wait_file.side_effect = interrupted
    import wry_csv.shopify as shopify
    monkeypatch.setattr(shopify, "public_url", lambda url: None)
    monkeypatch.setattr(shopify.requests, "post", lambda *a, **k: Mock(status_code=201))
    with pytest.raises(Invalid, match="Interrupted"):
        stage(products, checkpoint, path, admin, fetcher=good_fetch)
    products[0]["images"] = products[0]["images"][:1]
    admin.graphql.reset_mock()
    admin.wait_file.side_effect = None
    admin.wait_file.return_value = {"id": "gid://shopify/MediaImage/1", "url": "https://cdn.example.com/actual.png"}
    stage(products, read_json(path), path, admin, fetcher=good_fetch)
    admin.graphql.assert_not_called()
    assert next(iter(read_json(path)["files"].values()))["state"] == "ready"


def test_uncertain_create_is_not_blindly_retried(batch, tmp_path):
    products, _, _ = normalized(batch, tmp_path)
    image = products[0]["images"][0]
    image.pop("url")
    products[0]["images"] = [image]
    checkpoint = {"files": {image["local"]["sha256"]: {"state": "creating", "filename": "known.png", "sha256": image["local"]["sha256"], "shop": "wrydeco.myshopify.com"}}}
    admin = Mock()
    admin.find_file.return_value = []
    with pytest.raises(Invalid, match="Uncertain"):
        stage(products, checkpoint, tmp_path / "cp.json", admin, fetcher=good_fetch)
    admin.graphql.assert_not_called()


def test_cli_full_workflow_without_writes(batch, tmp_path, monkeypatch):
    manifest, snapshot, template = batch
    mp, sp = tmp_path / "manifest.json", tmp_path / "store.json"
    write_json(mp, manifest)
    write_json(sp, snapshot)
    common = ["--manifest", str(mp), "--snapshot", str(sp), "--template", str(template), "--history", str(tmp_path / "absent.sqlite3")]
    report = tmp_path / "report.json"
    assert main(["check", *common, "--report", str(report)]) == 0
    assert not read_json(report)["ready_for_import"]
    # Patch at the HTTP boundary: build and verify still run their real serializers/readers.
    import wry_csv.exporter as exporter
    monkeypatch.setattr(exporter, "verify_urls", lambda urls, **kw: {"checked": len(set(urls)), "results": [good_fetch(u) for u in set(urls)], "errors": []})
    output = tmp_path / "final.csv"
    assert main(["build", *common, "--out", str(output), "--report", str(report)]) == 0
    assert read_json(report)["ready_for_import"]
    assert main(["verify", *common, "--csv", str(output), "--report", str(report)]) == 0
    assert read_json(report)["ready_for_import"]
    assert main(["verify", "--template", str(template), "--csv", str(output), "--offline", "--report", str(report)]) == 0
    assert not read_json(report)["ready_for_import"]


def test_distinct_multi_product_manifest_passes_complete_pipeline(batch, tmp_path):
    manifest, snapshot, template = batch
    second = deepcopy(manifest["products"][0])
    second.update(id="SP02", handle="architectural-spiral-wine-rack-curved-bottle-slots-display", collection="wine-racks",
                  type="wine-racks", tags=["wine-racks"], category="Furniture > Cabinets & Storage > Wine Racks",
                  interior_style=["Rustic"])
    title = "Architectural Spiral Wine Rack with Curved Bottle Slots"
    second["content"] = {
        "title": title, "seo_product_title": title,
        "handle": second["handle"], "seo_title": "Architectural Spiral Wine Rack for Bottle Display | Wrydeco",
        "seo_description": "Explore an architectural spiral wine rack with curved bottle slots and a vertical outline, offering a distinctive arrangement for displaying a wine collection.",
        "description_html": '<div class="wrydeco-product-description"><p>An architectural spiral arrangement with curved bottle slots and a vertical outline for displaying wine bottles.</p></div>',
        "aeo": {
            "overview": {"text": (
                "This wine rack presents a spiral arrangement with curved bottle slots along a vertical outline. "
                "The architectural composition gives the displayed bottles a distinct arrangement within the visible frame. "
                "Its supplied product identity confirms that the piece is intended for wine bottles, while the gallery records the form of the bottle slots. "
                "When considering the piece for a room, compare the listed variant choices with the intended placement. "
                "The available evidence describes the product's configuration and outline without establishing a bottle capacity or additional installation requirements."),
                "evidence_ids": ["source:title", "source:bullet:0", "visual:0", "visual:1", "visual:2", "visual:3"]},
            "summary": [],
            "faq": [
                {"question": "How are the bottle slots arranged?", "answer": "The bottle slots follow a spiral arrangement along the rack's vertical outline. This configuration is visible in the gallery and describes the relationship between the curved openings and the architectural composition of the product.", "evidence_ids": ["visual:0", "visual:1", "visual:2", "visual:3"]},
                {"question": "What is the intended use of this rack?", "answer": "The rack is intended to display wine bottles, as confirmed by its supplied product identity. The visible curved bottle slots explain the configuration, while the product information should be consulted for any further specifications about the chosen variant.", "evidence_ids": ["source:title", "source:bullet:0", "visual:2"]},
                {"question": "What distinguishes the rack's visible outline?", "answer": "A vertical outline and an architectural composition distinguish the visible profile of this wine rack. The spiral arrangement connects the bottle slots visually, giving the piece a recognizable form when considered alongside other furnishings in a room.", "evidence_ids": ["visual:0", "visual:1", "visual:2", "visual:3"]},
            ]}}
    second["evidence"] = {"source": {"title": title, "bullets": ["The wine rack is intended to display wine bottles."], "aplus_text": ""},
                          "visual": {"target_identity": "wine rack", "evidence_ids": [second["images"][0]["path"]],
                                     "design_keywords": ["architectural", "spiral arrangement"],
                                     "shape_keywords": ["curved bottle slots", "vertical outline"]}}
    manifest["products"].append(second)
    snapshot["categories"][second["category"]] = "gid://shopify/TaxonomyCategory/wine-racks"
    snapshot["collections"].append({"handle": "wine-racks", "ruleSet": {"appliedDisjunctively": False,
        "rules": [{"column": "TYPE", "relation": "EQUALS", "condition": "wine-racks"}]}})
    products, report = prepare(manifest, tmp_path, snapshot, require_urls=True)
    assert report["valid"], report
    result = build_csv(tmp_path / "two-products.csv", products, template, snapshot, fetcher=good_fetch)
    assert result["ready_for_import"] and (result["products"], result["variants"], result["images"]) == (2, 4, 6)


def test_prior_handoff_fingerprints_are_compared(batch, tmp_path):
    products, report = prepare(batch[0], tmp_path, batch[1])
    path = tmp_path / "previous-build.json"
    write_json(path, {"valid": True, "manifest_compared": True, "content_validation": report})
    compared = compare_content(products, report["content"], None, [path])
    assert compared["collisions"] and compared["historical_coverage"]["prior_handoffs"][0]["records"] > 0


def test_admin_refuses_wrong_shop_before_network(tmp_path, monkeypatch):
    (tmp_path / "admin").mkdir()
    (tmp_path / "admin/.env").write_text("SHOPIFY_SHOP=other-store.myshopify.com\nSHOPIFY_ADMIN_TOKEN=do-not-send\n", encoding="utf-8")
    monkeypatch.delenv("SHOPIFY_SHOP", raising=False)
    import wry_csv.shopify as shopify
    post = Mock()
    monkeypatch.setattr(shopify.requests, "post", post)
    with pytest.raises(Invalid, match="other than WRYDECO"):
        Admin(tmp_path)
    post.assert_not_called()


def test_report_path_cannot_overwrite_manifest(batch, tmp_path):
    path = tmp_path / "manifest.json"
    write_json(path, batch[0])
    original = path.read_bytes()
    assert main(["check", "--manifest", str(path), "--report", str(path)]) == 1
    assert path.read_bytes() == original


def test_bad_external_url_blocks_all_uploads(batch, tmp_path):
    products, _, _ = normalized(batch, tmp_path)
    admin = Mock()
    products[0]["images"][0].pop("url")
    def bad(url):
        raise Invalid("Image GET returned HTTP 404")
    with pytest.raises(Invalid, match="no new Files uploads"):
        stage(products, {}, tmp_path / "checkpoint.json", admin, fetcher=bad)
    admin.graphql.assert_not_called()


def test_existing_output_is_preserved(batch, tmp_path):
    products, snapshot, template = normalized(batch, tmp_path)
    output = tmp_path / "existing.csv"
    output.write_bytes(b"keep this existing file")
    with pytest.raises(Invalid, match="Output already exists"):
        build_csv(output, products, template, snapshot, fetcher=good_fetch)
    assert output.read_bytes() == b"keep this existing file"
