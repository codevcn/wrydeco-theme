import asyncio
import json
from types import SimpleNamespace

from scraper.manifest import parse_manifest_payload
from scraper.orchestrator import CrawlService
from scraper.store import OrchestratorStore


def test_crawler_is_sequential_and_enqueues_each_product_immediately(tmp_path, monkeypatch):
    root = tmp_path / "scraper"
    root.mkdir()
    store = OrchestratorStore(root)
    payload = {"products": [
        {"amazon_url": f"https://www.amazon.com/dp/B00000000{index}", "shopify_product_id": str(100 + index), "mode": "auto"}
        for index in range(3)
    ]}
    manifest = parse_manifest_payload(payload, root / "manifest.json")
    run = store.create_run(manifest, payload, {"dry_run": True, "headless": True})
    assert store.claim_next_crawl_run() == run["id"]
    observations = []

    class FakeBrowser:
        instances = 0

        def __init__(self, settings, callback):
            FakeBrowser.instances += 1
            self.event_callback = callback

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def crawl(self, url, evidence, mode):
            observations.append(store.queue_status()["content"].get("queued", 0))
            return SimpleNamespace(
                source={"title": url, "gallery_images": ["https://example.com/image.jpg"], "aplus_images": []},
                pricing={
                    "mode": "dynamic", "base_price": "100.00", "verified_all": True,
                    "option_types": [{"name": "Size"}],
                    "variants": [{
                        "options": [{"name": "Size", "value": "Small"}],
                        "additional_price": "0.00", "verified_total": "100.00",
                    }],
                },
            )

    monkeypatch.setattr("scraper.orchestrator.AmazonBrowser", FakeBrowser)

    def fake_gallery_evidence(urls, evidence_dir, **_kwargs):
        gallery = evidence_dir / "gallery"
        gallery.mkdir(parents=True, exist_ok=True)
        (gallery / "001.jpg").write_bytes(b"fixture-image")
        (gallery / "contact-sheet.jpg").write_bytes(b"fixture-contact-sheet")
        manifest = {
            "images": [{"evidence_id": "gallery/001.jpg", "source_url": urls[0]}],
            "contact_sheet": "gallery/contact-sheet.jpg",
            "failures": [],
        }
        (gallery / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return manifest

    monkeypatch.setattr("scraper.orchestrator.prepare_gallery_evidence", fake_gallery_evidence)
    asyncio.run(CrawlService(store).run(run["id"]))

    assert observations == [0, 1, 2]
    assert FakeBrowser.instances == 1
    assert store.queue_status()["content"]["queued"] == 3
    assert store.get_run(run["id"])["crawl_status"] == "complete"
