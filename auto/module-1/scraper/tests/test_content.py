import pytest

from scraper.content import (
    content_similarity,
    validate_content,
    validate_content_grounding,
    validate_visual_analysis,
)
from scraper.errors import ContentValidationError


def valid_payload():
    return {
        "title": "Handcrafted Rustic Solid Wood Side Table for Modern Homes",
        "seo_product_title": "Handcrafted Rustic Solid Wood Side Table for Modern Homes",
        "seo_title": "Rustic Solid Wood Side Table for Modern Homes | Wrydeco",
        "seo_description": "Explore the handcrafted rustic solid wood side table with organic grain, practical storage, and a warm finish for bedrooms and modern living spaces today.",
        "handle": "handcrafted-rustic-solid-wood-side-table-modern-homes",
        "description_html": '<div class="wrydeco-product-description"><p>Safe description.</p></div>',
    }


def test_valid_content_contract():
    payload = valid_payload()
    assert validate_content(payload)["handle"] == payload["handle"]


def test_unsafe_html_rejected():
    payload = valid_payload()
    payload["description_html"] = '<div class="wrydeco-product-description"><script>alert(1)</script></div>'
    with pytest.raises(ContentValidationError):
        validate_content(payload)


def test_content_grounding_rejects_generic_or_unsupported_copy():
    source = {
        "title": "Handcrafted Sculptural Tree Branch Wood Console Table",
        "bullets": ["Rustic organic form with an elevated branch display shelf."],
        "aplus_text": "Natural wood furniture.",
    }
    payload = valid_payload()
    payload.update({
        "title": "Modern Minimalist Entryway Console Table with Storage",
        "seo_product_title": "Modern Minimalist Console Table with Storage Shelf",
        "seo_title": "Modern Minimalist Console Table for Entryway | Wrydeco",
        "handle": "modern-minimalist-console-table-with-storage-shelf-unit",
        "description_html": '<div class="wrydeco-product-description"><p>Modern storage table.</p></div>',
    })
    with pytest.raises(ContentValidationError, match="distinctive facts|Unsupported factual term"):
        validate_content_grounding(payload, source)


def test_grounding_allows_material_and_feature_facts_confirmed_by_text_source():
    payload = valid_payload()
    source = {
        "title": payload["title"],
        "bullets": ["Solid wood construction with practical storage and a warm finish."],
        "aplus_text": payload["seo_description"],
    }
    assert validate_content_grounding(payload, source)["title"] == payload["title"]


def test_visual_analysis_rejects_material_color_and_dimensions():
    base = {
        "task_id": "task", "source_digest": "digest", "target_identity": "console table",
        "evidence_ids": ["gallery/001.jpg"],
        "design_keywords": ["sculptural profile", "open frame rhythm", "layered composition"],
        "shape_keywords": ["rounded edges", "offset supports", "asymmetrical silhouette"],
    }
    assert validate_visual_analysis(
        base, expected_task_id="task", expected_source_digest="digest",
        allowed_evidence_ids={"gallery/001.jpg"},
    )["target_identity"] == "console table"
    for forbidden in ("solid wood profile", "black frame", "24 inch shelf"):
        invalid = {**base, "design_keywords": [forbidden, "open frame rhythm", "layered composition"]}
        with pytest.raises(ContentValidationError, match="Visual keyword"):
            validate_visual_analysis(
                invalid, expected_task_id="task", expected_source_digest="digest",
                allowed_evidence_ids={"gallery/001.jpg"},
            )


def test_content_similarity_detects_near_duplicate_but_ignores_html_wrapper():
    first = '<div class="wrydeco-product-description"><h3>Key Features</h3><p>Sculptural rounded profile with an open tier composition.</p></div>'
    second = '<div class="wrydeco-product-description"><p>Sculptural rounded profile with an open tier composition.</p></div>'
    assert content_similarity("description_html", first, second) > 0.9
    assert content_similarity("title", "Sculptural Rounded Side Table", "Architectural Offset Console") < 0.5
