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

