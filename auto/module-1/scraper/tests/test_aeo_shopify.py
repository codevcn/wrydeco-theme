import pytest

from scraper.errors import ShopifyError
from scraper.shopify import ShopifyClient
from scraper.tests.test_shopify import Response, Session, config


def response(data):
    return Response(200, {"data": data})


def test_metafield_definition_created_once_and_read_back(tmp_path):
    session = Session([
        response({"metafieldDefinitions": {"nodes": []}}),
        response({"metafieldDefinitionCreate": {"createdDefinition": {"id": "def"}, "userErrors": []}}),
        response({"metafieldDefinitions": {"nodes": [{"id": "def", "type": {"name": "multi_line_text_field"}}]}}),
    ])
    ShopifyClient(config(tmp_path), session).ensure_aeo_definition()
    definition = session.calls[1][1]["json"]["variables"]["definition"]
    assert definition == {"name": "Product AEO HTML", "namespace": "custom", "key": "aeo_html",
                          "ownerType": "PRODUCT", "type": "multi_line_text_field"}
    assert 'namespace: "custom", key: "aeo_html"' in session.calls[0][1]["json"]["query"]


def test_incompatible_definition_is_never_changed(tmp_path):
    session = Session([response({"metafieldDefinitions": {"nodes": [{"id": "def", "type": {"name": "json"}}]}})])
    with pytest.raises(ShopifyError, match="type"):
        ShopifyClient(config(tmp_path), session).ensure_aeo_definition()
    assert len(session.calls) == 1


@pytest.mark.parametrize("digest", [None, "empty-field-digest"])
def test_single_field_write_includes_compare_digest_even_for_absent_field(tmp_path, digest):
    session = Session([response({"metafieldsSet": {"metafields": [{"id": "field"}], "userErrors": []}})])
    ShopifyClient(config(tmp_path), session).write_aeo_metafield("123", "<p>AEO</p>", digest)
    fields = session.calls[0][1]["json"]["variables"]["fields"]
    assert fields == [{"ownerId": "gid://shopify/Product/123", "namespace": "custom", "key": "aeo_html",
                       "type": "multi_line_text_field", "value": "<p>AEO</p>", "compareDigest": digest}]


def test_read_aeo_uses_only_target_product_and_field(tmp_path):
    value = {"id": "field", "type": "multi_line_text_field", "value": "<p>old</p>", "compareDigest": "digest"}
    session = Session([response({"product": {"metafield": value}})])
    assert ShopifyClient(config(tmp_path), session).read_aeo_metafield("123") == value
    query = session.calls[0][1]["json"]
    assert query["variables"] == {"id": "gid://shopify/Product/123"}
    assert 'namespace: "custom", key: "aeo_html"' in query["query"]
