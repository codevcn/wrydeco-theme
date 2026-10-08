from scraper.manifest import ProductJob
from scraper.pipeline import _build_rich_description, _metafields_for_product


def test_store_metafield_definitions_override_generic_defaults():
    job = ProductJob("https://www.amazon.com/dp/B000000000", "123", "B000000000", "auto", None, {})
    content = {"seo_product_title": "A" * 50}
    definitions = {
        ("custom", "seo_product_title"): "single_line_text_field",
        ("custom", "amazon_link"): "single_line_text_field",
        ("custom", "rich_description"): "single_line_text_field",
    }
    fields = _metafields_for_product({}, content, job, {}, definitions, "<div>rich</div>")
    assert {item["key"]: item["type"] for item in fields} == {
        "seo_product_title": "single_line_text_field",
        "amazon_link": "single_line_text_field",
        "rich_description": "single_line_text_field",
    }


def test_rich_description_uses_rehosted_urls_only():
    rich = _build_rich_description([{"url": "https://cdn.shopify.com/a.jpg"}], 'A "Title"')
    assert 'src="https://via.placeholder.com/800"' in rich
    assert 'data-src="https://cdn.shopify.com/a.jpg"' in rich
    assert 'alt="A &quot;Title&quot;"' in rich
