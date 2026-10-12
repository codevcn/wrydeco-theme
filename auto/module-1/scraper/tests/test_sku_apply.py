from copy import deepcopy
from types import SimpleNamespace

from scraper.io_utils import atomic_write_json, load_json
from scraper.orchestrator import ShopifyApplyService
from scraper.tests.test_content import valid_payload


def setup_apply(tmp_path, monkeypatch, *, dry_run=False, resumed=False):
    workspace = tmp_path / "product"
    workspace.mkdir()
    atomic_write_json(workspace / "content.json", valid_payload())
    atomic_write_json(workspace / "source.json", {"gallery_images": ["https://example.test/image.jpg"]})
    atomic_write_json(workspace / "pricing.json", {"base_price": "99", "option_types": [{"name": "Size"}],
                      "variants": [{"options": [{"name": "Size", "value": '65"W - Recommended'}],
                                    "additional_price": "0", "verified_total": "99"}]})
    if resumed:
        atomic_write_json(workspace / "apply_progress.json", {"product_set": True, "product": {"id": "123"}})
    class Client:
        def __init__(self):
            self.live = [{"id": "v1", "sku": "", "selectedOptions": [{"name": "Size", "value": '65"W - Recommended'}]}]
            self.stages = []
        def snapshot_product(self, _):
            return {"id": "123", "handle": "old-handle", "variants": {"nodes": deepcopy(self.live)},
                    "options": [], "metafields": {"nodes": []}, "media": {"nodes": [{"id": "old"}]}}
        def read_variants(self, _):
            return deepcopy(self.live)
        def variant_sku_owners(self, *args):
            return {}
        def product_set(self, _, content, options, variants, settings):
            self.stages.append("product_set")
            self.live[0]["sku"] = variants[0]["sku"]
            self.live[0]["selectedOptions"] = [{"name": item["name"], "value": item["value"]}
                                               for item in variants[0]["options"]]
            return {"id": "123"}
        def update_variant_skus(self, _, updates):
            self.stages.append("sku_repair")
            self.live[0]["sku"] = updates[0]["sku"]
        def product_metafield_definitions(self):
            return {}
        def attach_media(self, *args):
            self.stages.append("media_attach")
            return ["new"]
        def verify_media(self, *args): pass
        def delete_media(self, *args): self.stages.append("old_media_delete")
        def set_metafields(self, *args): pass
        def sync_publications(self, *args): pass
    fake = Client()
    monkeypatch.setattr("scraper.orchestrator.ShopifyClient", lambda _: fake)
    monkeypatch.setattr("scraper.orchestrator.ShopifyConfig.from_env", lambda _: None)
    monkeypatch.setattr("scraper.orchestrator.rehost_images", lambda *a, **kw: [{"id": "file", "url": "https://cdn.test/a.jpg"}])
    store = SimpleNamespace(package_root=tmp_path, workspace=lambda _: workspace,
                            run_record=lambda _: {"options": {"dry_run": dry_run}}, event=lambda *a, **kw: None)
    product = {"id": "task", "run_id": "run", "asin": "B000000000", "amazon_url": "https://amazon.com/dp/B000000000",
               "shopify_product_id": "123", "mode": "auto", "preset": None,
               "overrides": {"tags": ["source_amazon"]}}
    return ShopifyApplyService(store), product, fake, workspace


def test_full_apply_has_skus_before_product_set_and_checkpoint_before_media(tmp_path, monkeypatch):
    service, product, fake, workspace = setup_apply(tmp_path, monkeypatch)
    result = service.apply_product(product)
    assert result["sku_verified"] and result["sku_count"] == 1
    assert fake.live[0]["sku"] == "amz-B000000000-NA-W65-01"
    assert fake.live[0]["selectedOptions"] == [{"name": "Size", "value": '65"W'}]
    assert fake.stages == ["product_set", "media_attach", "old_media_delete"]
    assert load_json(workspace / "apply_progress.json")["sku_verified"]
    assert load_json(workspace / "final_config.json")["variants"][0]["sku"] == fake.live[0]["sku"]


def test_resumed_pre_sku_checkpoint_repairs_without_replaying_product_set(tmp_path, monkeypatch):
    service, product, fake, workspace = setup_apply(tmp_path, monkeypatch, resumed=True)
    service.apply_product(product)
    assert fake.stages[0] == "sku_repair"
    assert "product_set" not in fake.stages
    assert fake.live[0]["selectedOptions"][0]["value"] == '65"W - Recommended'


def test_resumed_checkpoint_uses_saved_options_even_if_pricing_changed(tmp_path, monkeypatch):
    service, product, fake, workspace = setup_apply(tmp_path, monkeypatch, resumed=True)
    atomic_write_json(workspace / "final_config.json", {
        "option_names": ["Size"], "variants": [{
            "options": [{"name": "Size", "value": '65"W - Recommended'}], "price": "99",
        }],
    })
    pricing = load_json(workspace / "pricing.json")
    pricing["variants"][0]["options"][0]["value"] = '65"W'
    atomic_write_json(workspace / "pricing.json", pricing)
    service.apply_product(product)
    assert fake.stages[0] == "sku_repair"
    assert "product_set" not in fake.stages
    assert load_json(workspace / "final_config.json")["variants"][0]["options"][0]["value"] == '65"W - Recommended'


def test_dry_run_outputs_plan_without_any_shopify_mutation(tmp_path, monkeypatch):
    service, product, fake, workspace = setup_apply(tmp_path, monkeypatch, dry_run=True)
    result = service.apply_product(product)
    assert result["status"] == "dry_run_complete" and result["sku_plan"]["variants"]
    assert fake.stages == [] and fake.live[0]["sku"] == ""
    assert not (workspace / "apply_progress.json").exists()
