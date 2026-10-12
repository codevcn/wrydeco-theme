from pathlib import Path

import pytest

from scraper.errors import ShopifyError
from scraper.shopify import ShopifyClient, ShopifyConfig


class Response:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.text = "response"

    def json(self):
        return self._payload


class Session:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return next(self.responses)


def config(tmp_path):
    env = tmp_path / ".env"
    env.write_text("STORE_ADMIN_ACCESS_TOKEN=old\n", encoding="utf-8")
    return ShopifyConfig("shop.myshopify.com", "old", "id", "secret", "2026-01", 1, env)


def test_401_refreshes_and_retries(tmp_path):
    session = Session([
        Response(401, {}), Response(200, {"access_token": "new"}), Response(200, {"data": {"shop": {"id": "1"}}}),
    ])
    client = ShopifyClient(config(tmp_path), session)
    assert client.graphql("query { shop { id } }")["shop"]["id"] == "1"
    assert "STORE_ADMIN_ACCESS_TOKEN='new'" in (tmp_path / ".env").read_text(encoding="utf-8")
    assert len(session.calls) == 3


def test_partial_mutation_failure_stops(tmp_path):
    session = Session([Response(200, {"data": {"metafieldsSet": {
        "metafields": [], "userErrors": [{"field": ["metafields", "0"], "message": "invalid"}]
    }}})])
    client = ShopifyClient(config(tmp_path), session)
    with pytest.raises(ShopifyError):
        client.set_metafields("123", [{"namespace": "custom", "key": "x", "type": "single_line_text_field", "value": "y"}])


def test_staged_upload_file_create_and_ready(tmp_path):
    session = Session([
        Response(200, {"data": {"stagedUploadsCreate": {"stagedTargets": [{
            "url": "https://upload.example", "resourceUrl": "https://resource.example/image",
            "parameters": [{"name": "key", "value": "value"}],
        }], "userErrors": []}}}),
        Response(204, {}),
        Response(200, {"data": {"fileCreate": {"files": [{"id": "gid://shopify/MediaImage/1",
                                                               "fileStatus": "UPLOADED", "image": None}],
                                                       "userErrors": []}}}),
        Response(200, {"data": {"node": {"id": "gid://shopify/MediaImage/1", "fileStatus": "READY",
                                              "image": {"url": "https://cdn.shopify.com/image.jpg"}}}}),
    ])
    client = ShopifyClient(config(tmp_path), session)
    result = client.stage_image(b"jpeg", "image.jpg", "image/jpeg", "Alt")
    assert result["url"] == "https://cdn.shopify.com/image.jpg"
    assert len(session.calls) == 4


def test_media_attach_filters_existing_ids(tmp_path):
    session = Session([
        Response(200, {"data": {"productUpdate": {"product": {"id": "gid://shopify/Product/123"}, "userErrors": []}}}),
        Response(200, {"data": {"product": {"media": {"nodes": [
            {"id": "old", "status": "READY"}, {"id": "new", "status": "UPLOADED"}
        ], "pageInfo": {"hasNextPage": False, "endCursor": None}}}}}),
    ])
    client = ShopifyClient(config(tmp_path), session)
    assert client.attach_media("123", [{"url": "https://cdn/image.jpg", "alt": "Alt"}], ["old"]) == ["new"]


def test_products_by_amazon_asins_normalizes_urls_and_paginates(tmp_path):
    session = Session([
        Response(200, {"data": {"products": {
            "nodes": [{
                "id": "gid://shopify/Product/111", "title": "First", "handle": "first",
                "amazonLink": {"value": "https://www.amazon.com/dp/B0H7H28CFG/ref=abc?th=1"},
            }, {
                "id": "gid://shopify/Product/999", "title": "Ignored", "handle": "ignored",
                "amazonLink": {"value": "not-a-valid-amazon-url"},
            }],
            "pageInfo": {"hasNextPage": True, "endCursor": "page-2"},
        }}}),
        Response(200, {"data": {"products": {
            "nodes": [{
                "id": "gid://shopify/Product/222", "title": "Second", "handle": "second",
                "amazonLink": {"value": "https://amazon.com/gp/product/B000000000?tag=source"},
            }],
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        }}}),
    ])
    client = ShopifyClient(config(tmp_path), session)
    matches = client.products_by_amazon_asins({"b0h7h28cfg", "B000000000", "B111111111"})

    assert matches["B0H7H28CFG"][0]["shopify_product_id"] == "111"
    assert matches["B0H7H28CFG"][0]["amazon_url"].endswith("/ref=abc?th=1")
    assert matches["B000000000"][0]["shopify_product_id"] == "222"
    assert matches["B111111111"] == []
    assert session.calls[1][1]["json"]["variables"]["after"] == "page-2"


def test_product_set_sends_sku_and_inventory_tracking_together(tmp_path):
    session = Session([Response(200, {"data": {"productSet": {"product": {"id": "123"}, "userErrors": []}}})])
    client = ShopifyClient(config(tmp_path), session)
    client.product_set("123", {"title": "Title", "handle": "handle", "description_html": "<p>Text</p>",
                               "seo_title": "SEO", "seo_description": "Description"}, ["Size"],
                       [{"options": [{"name": "Size", "value": "Large"}], "price": "99", "sku": "amz-B000000000-NA-LAR-01"}], {})
    variant = session.calls[0][1]["json"]["variables"]["input"]["variants"][0]
    assert variant["sku"] == "amz-B000000000-NA-LAR-01"
    assert variant["inventoryItem"] == {"tracked": False}


def test_sku_bulk_update_uses_inventory_item_and_chunks_at_250(tmp_path):
    session = Session([Response(200, {"data": {"productVariantsBulkUpdate": {"userErrors": []}}}) for _ in range(2)])
    client = ShopifyClient(config(tmp_path), session)
    client.update_variant_skus("123", [{"id": str(i), "sku": f"SKU-{i}"} for i in range(251)])
    calls = [call[1]["json"]["variables"]["variants"] for call in session.calls]
    assert [len(batch) for batch in calls] == [250, 1]
    assert calls[0][0] == {"id": "0", "inventoryItem": {"sku": "SKU-0"}}


def test_sku_owners_paginate_and_exclude_only_the_target_product(tmp_path):
    session = Session([
        Response(200, {"data": {"productVariants": {"nodes": [
            {"id": "own", "sku": "AMZ-B000000000-NAT-01", "product": {"id": "gid://shopify/Product/123"}},
            {"id": "other", "sku": "AMZ-B000000000-NAT-01", "product": {"id": "gid://shopify/Product/456"}},
        ], "pageInfo": {"hasNextPage": True, "endCursor": "next"}}}}),
        Response(200, {"data": {"productVariants": {"nodes": [
            {"id": "other2", "sku": "amz-B000000000-WAL-02", "product": {"id": "gid://shopify/Product/789"}},
        ], "pageInfo": {"hasNextPage": False, "endCursor": None}}}}),
    ])
    result = ShopifyClient(config(tmp_path), session).variant_sku_owners("amz", "B000000000", "123")
    assert result == {"amz-b000000000-nat-01": ["other"], "amz-b000000000-wal-02": ["other2"]}
    assert session.calls[1][1]["json"]["variables"]["after"] == "next"

