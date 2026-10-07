from __future__ import annotations

import re
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .errors import ContentValidationError
from .io_utils import load_json


class _SafeHTML(HTMLParser):
    allowed = {"div", "p", "br", "strong", "em", "ul", "ol", "li", "h2", "h3", "span"}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in self.allowed:
            raise ContentValidationError(f"Disallowed HTML tag: {tag}")
        for name, value in attrs:
            if name != "class" or value is None or not re.fullmatch(r"[a-zA-Z0-9_ -]+", value):
                raise ContentValidationError(f"Disallowed HTML attribute: {name}")


def _require_length(label: str, value: str, low: int, high: int) -> None:
    if not low <= len(value) <= high:
        raise ContentValidationError(f"{label} must be {low}-{high} characters; got {len(value)}.")


def validate_content(payload_or_path: dict[str, Any] | Path) -> dict[str, str]:
    payload = load_json(payload_or_path) if isinstance(payload_or_path, Path) else payload_or_path
    if not isinstance(payload, dict):
        raise ContentValidationError("content.json must contain an object.")
    aliases = {
        "title": ("title", "product_title"),
        "description_html": ("description_html", "descriptionHtml", "html_description"),
        "seo_product_title": ("seo_product_title",),
        "seo_title": ("seo_title", "seoTitle"),
        "seo_description": ("seo_description", "seoDescription"),
        "handle": ("handle",),
    }
    result: dict[str, str] = {}
    for key, choices in aliases.items():
        value = next((payload.get(choice) for choice in choices if payload.get(choice) is not None), None)
        if not isinstance(value, str) or not value.strip():
            raise ContentValidationError(f"Missing non-empty content field: {key}")
        result[key] = value.strip()
    _require_length("title", result["title"], 50, 70)
    _require_length("seo_product_title", result["seo_product_title"], 50, 70)
    if "wrydeco" in result["seo_product_title"].casefold() or "|" in result["seo_product_title"]:
        raise ContentValidationError("seo_product_title must not contain Wrydeco or '|'.")
    _require_length("seo_title", result["seo_title"], 50, 60)
    if not result["seo_title"].endswith(" | Wrydeco"):
        raise ContentValidationError("seo_title must end with ' | Wrydeco'.")
    _require_length("seo_description", result["seo_description"], 150, 160)
    if not re.match(r"^(Explore|Shop the)\b", result["seo_description"]) or not result["seo_description"].endswith("."):
        raise ContentValidationError("seo_description must start with Explore/Shop the and end with a period.")
    _require_length("handle", result["handle"], 50, 60)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", result["handle"]):
        raise ContentValidationError("handle must be lowercase ASCII kebab-case.")
    html = result["description_html"]
    if not re.match(r'^<div\s+class=["\']wrydeco-product-description["\']>', html):
        raise ContentValidationError("description_html must use the wrydeco-product-description wrapper.")
    if re.search(r"<(?:script|style|iframe)\b|\bon\w+\s*=", html, re.I):
        raise ContentValidationError("description_html contains unsafe markup.")
    parser = _SafeHTML()
    try:
        parser.feed(html)
        parser.close()
    except ContentValidationError:
        raise
    except Exception as exc:
        raise ContentValidationError(f"Invalid description HTML: {exc}") from exc
    return result

