import json

import pytest

from scraper.manifest import load_manifest
from scraper.store import OrchestratorStore


def test_manifest_snapshot_and_sqlite_state(tmp_path):
    root = tmp_path / "scraper"
    root.mkdir()
    path = tmp_path / "products.json"
    payload = {"products": [{"amazon_url": "https://www.amazon.com/dp/B000000000", "shopify_product_id": "123", "mode": "auto"}]}
    path.write_text(json.dumps(payload), encoding="utf-8")
    manifest = load_manifest(path)
    store = OrchestratorStore(root)
    run = store.create_run(manifest, payload, {"dry_run": True})
    product = next(iter(run["products"].values()))
    store.set_product_status(product["id"], "crawling")
    store.set_product_status(product["id"], "crawled")
    assert store.get_run(run["id"])["products"]["B000000000"]["status"] == "crawled"
    assert json.loads((root / "runs" / run["id"] / "manifest.json").read_text(encoding="utf-8")) == payload


def test_duplicate_manifest_rejected(tmp_path):
    path = tmp_path / "products.json"
    product = {"amazon_url": "https://www.amazon.com/dp/B000000000", "shopify_product_id": "123"}
    path.write_text(json.dumps({"products": [product, product]}), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(path)
