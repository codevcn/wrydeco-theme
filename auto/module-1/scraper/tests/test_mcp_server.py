import json

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from scraper.manifest import parse_manifest_payload
from scraper.mcp_server import create_mcp_server
from scraper.store import OrchestratorStore


def valid_content():
    return {
        "title": "Sculptural Profile Side Table with Rounded Shelf Edges",
        "seo_product_title": "Open Tier Composition Table with Asymmetrical Silhouette",
        "seo_title": "Sculptural Side Table with Rounded Shelf Profile | Wrydeco",
        "seo_description": "Explore a sculptural profile side table with rounded shelf edges, an open tier composition, and an asymmetrical silhouette designed as a distinctive accent.",
        "handle": "sculptural-profile-side-table-rounded-shelf-edges-design",
        "description_html": '<div class="wrydeco-product-description"><p>A sculptural profile with rounded shelf edges creates an open tier composition and asymmetrical silhouette.</p></div>',
    }


def queued_store(tmp_path):
    root = tmp_path / "scraper"
    root.mkdir()
    (root / "AGENT_PROMPT.md").write_text("Use evidence only.", encoding="utf-8")
    (root / "content.schema.json").write_text(json.dumps({"type": "object"}), encoding="utf-8")
    store = OrchestratorStore(root)
    payload = {"products": [{"amazon_url": "https://www.amazon.com/dp/B000000000", "shopify_product_id": "123", "mode": "auto"}]}
    manifest = parse_manifest_payload(payload, root / "input.json")
    run = store.create_run(manifest, payload, {"dry_run": True})
    product = next(iter(run["products"].values()))
    for status in ("crawling", "crawled", "price_verified"):
        store.set_product_status(product["id"], status)
    workspace = store.workspace(store.product(product["id"]))
    (workspace / "source.json").write_text(json.dumps({
        "title": "Sculptural Profile Side Table with Rounded Shelf Edges Open Tier Composition",
        "bullets": [valid_content()["seo_description"]],
        "aplus_text": "Verified A+ text remains available as factual evidence.",
        "aplus_images": ["https://example.test/aplus-hero.jpg"],
        "aplus_html": '<div><img src="https://example.test/aplus-hero.jpg"></div>',
    }), encoding="utf-8")
    (workspace / "pricing.json").write_text(json.dumps({"base_price": "100.00"}), encoding="utf-8")
    (workspace / "evidence" / "page.txt").write_text("product evidence", encoding="utf-8")
    gallery = workspace / "evidence" / "gallery"
    gallery.mkdir()
    for filename in ("001.jpg", "002.jpg", "contact-sheet.jpg"):
        (gallery / filename).write_bytes(b"image")
    aplus = workspace / "evidence" / "aplus"
    aplus.mkdir()
    (aplus / "hero.jpg").write_bytes(b"a-plus-image")
    store.enqueue_content(product["id"])
    return root, store, product


@pytest.mark.asyncio
async def test_mcp_lists_contract_and_processes_task(tmp_path):
    root, store, product = queued_store(tmp_path)
    server = create_mcp_server(root, store)
    tools = {tool.name for tool in await server.list_tools()}
    assert tools == {
        "queue_status", "claim_next_content_task", "get_content_context", "list_evidence", "read_evidence",
        "claim_expected_content_task", "write_visual_analysis",
        "write_content_draft", "validate_content_draft", "finalize_content", "renew_content_lease",
        "release_content_task", "report_content_progress",
    }
    resources = {str(resource.uri) for resource in await server.list_resources()}
    assert {
        "wrydeco://queue/status", "wrydeco://content/schema", "wrydeco://content/rules",
        "wrydeco://visual-analysis/schema",
    } <= resources
    assert {prompt.name for prompt in await server.list_prompts()} == {"process_content_queue"}

    claim_result = await server.call_tool("claim_next_content_task", {})
    claim = claim_result.structured_content
    assert claim["task_id"] == product["id"]
    token = claim["claim_token"]
    context = (await server.call_tool("get_content_context", {"task_id": product["id"], "claim_token": token})).structured_content
    assert "Sculptural Profile" in context["source"]["title"]
    assert context["visual_analysis_schema"]["required"] == [
        "task_id", "source_digest", "target_identity", "evidence_ids",
        "design_keywords", "shape_keywords",
    ]
    assert context["source"]["aplus_text"].startswith("Verified A+")
    assert "aplus_images" not in context["source"]
    assert "aplus_html" not in context["source"]
    evidence = (await server.call_tool("list_evidence", {"task_id": product["id"], "claim_token": token})).structured_content
    evidence_ids = {item["evidence_id"] for item in evidence["result"]}
    assert "page.txt" in evidence_ids
    assert "aplus/hero.jpg" not in evidence_ids
    with pytest.raises(ToolError):
        await server.call_tool("read_evidence", {
            "task_id": product["id"], "claim_token": token, "evidence_id": "aplus/hero.jpg",
        })
    read = await server.call_tool(
        "read_evidence",
        {"task_id": product["id"], "claim_token": token, "evidence_id": "page.txt"},
    )
    assert read.structured_content is None
    text_payload = json.loads(read.content[0].text)
    assert text_payload["text"] == "product evidence"
    for evidence_id in ("gallery/contact-sheet.jpg", "gallery/001.jpg", "gallery/002.jpg"):
        image = await server.call_tool("read_evidence", {
            "task_id": product["id"], "claim_token": token, "evidence_id": evidence_id,
        })
        assert image.structured_content is None
        assert image.content[0].type == "image"
        assert image.content[0].mime_type == "image/jpeg"
    await server.call_tool("write_visual_analysis", {
        "task_id": product["id"], "claim_token": token,
        "analysis": {
            "task_id": product["id"], "source_digest": context["source_digest"],
            "target_identity": "side table",
            "evidence_ids": ["gallery/contact-sheet.jpg", "gallery/001.jpg", "gallery/002.jpg"],
            "design_keywords": ["sculptural profile", "open tier composition", "balanced visual rhythm"],
            "shape_keywords": ["rounded shelf edges", "asymmetrical silhouette", "stacked outline"],
        },
    })

    await server.call_tool("write_content_draft", {"task_id": product["id"], "claim_token": token, "content": valid_content()})
    validation = (await server.call_tool("validate_content_draft", {"task_id": product["id"], "claim_token": token})).structured_content
    assert validation["valid"] is True
    finalized = (await server.call_tool("finalize_content", {"task_id": product["id"], "claim_token": token})).structured_content
    assert finalized["state"] == "ready"
    assert store.queue_status()["apply"]["queued"] == 1


@pytest.mark.asyncio
async def test_mcp_rejects_path_escape_and_returns_structured_validation_errors(tmp_path):
    root, store, product = queued_store(tmp_path)
    server = create_mcp_server(root, store)
    claim = (await server.call_tool("claim_next_content_task", {})).structured_content
    token = claim["claim_token"]
    with pytest.raises(ToolError):
        await server.call_tool("read_evidence", {"task_id": product["id"], "claim_token": token, "evidence_id": "../.env"})
    context = (await server.call_tool("get_content_context", {"task_id": product["id"], "claim_token": token})).structured_content
    for evidence_id in ("gallery/contact-sheet.jpg", "gallery/001.jpg", "gallery/002.jpg"):
        await server.call_tool("read_evidence", {"task_id": product["id"], "claim_token": token, "evidence_id": evidence_id})
    await server.call_tool("write_visual_analysis", {
        "task_id": product["id"], "claim_token": token,
        "analysis": {
            "task_id": product["id"], "source_digest": context["source_digest"],
            "target_identity": "side table",
            "evidence_ids": ["gallery/contact-sheet.jpg", "gallery/001.jpg", "gallery/002.jpg"],
            "design_keywords": ["sculptural profile", "open tier composition", "balanced visual rhythm"],
            "shape_keywords": ["rounded shelf edges", "asymmetrical silhouette", "stacked outline"],
        },
    })
    await server.call_tool("write_content_draft", {"task_id": product["id"], "claim_token": token, "content": {"title": "short"}})
    invalid = (await server.call_tool("validate_content_draft", {"task_id": product["id"], "claim_token": token})).structured_content
    assert invalid["valid"] is False
    assert invalid["errors"][0]["field"]


@pytest.mark.asyncio
async def test_mcp_expected_task_session_cannot_cross_task_boundary(tmp_path, monkeypatch):
    root, store, product = queued_store(tmp_path)
    monkeypatch.setenv("WRYDECO_EXPECTED_TASK_ID", product["id"])
    monkeypatch.setenv("WRYDECO_AGENT_SESSION_ID", "isolated-session")
    server = create_mcp_server(root, store)

    with pytest.raises(ToolError, match="does not match"):
        await server.call_tool("claim_expected_content_task", {"task_id": "another-task"})
    claim = (await server.call_tool("claim_expected_content_task", {
        "task_id": product["id"],
    })).structured_content
    with pytest.raises(ToolError, match="only its assigned"):
        await server.call_tool("get_content_context", {
            "task_id": "another-task", "claim_token": claim["claim_token"],
        })


def test_mcp_startup_does_not_interrupt_runtime_workers(tmp_path):
    root, store, product = queued_store(tmp_path)
    claim = store.claim_next_content("setup")
    context = store.content_context(product["id"], claim["claim_token"])
    for evidence_id in ("gallery/contact-sheet.jpg", "gallery/001.jpg", "gallery/002.jpg"):
        store.evidence_path(product["id"], claim["claim_token"], evidence_id)
    store.write_visual_analysis(product["id"], claim["claim_token"], {
        "task_id": product["id"], "source_digest": context["source_digest"],
        "target_identity": "side table",
        "evidence_ids": ["gallery/contact-sheet.jpg", "gallery/001.jpg", "gallery/002.jpg"],
        "design_keywords": ["sculptural profile", "open tier composition", "balanced visual rhythm"],
        "shape_keywords": ["rounded shelf edges", "asymmetrical silhouette", "stacked outline"],
    })
    store.write_content_draft(product["id"], claim["claim_token"], valid_content())
    store.finalize_content(product["id"], claim["claim_token"])
    store.claim_next_apply()
    store.set_run_crawl_status(product["run_id"], "running")

    create_mcp_server(root, store)

    current = store.get_run(product["run_id"])
    assert current["crawl_status"] == "running"
    assert current["products"][product["asin"]]["apply_task"]["state"] == "running"
