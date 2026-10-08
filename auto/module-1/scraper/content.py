from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .errors import ContentValidationError
from .io_utils import load_json


_WORD_RE = re.compile(r"[a-z0-9]+")
_GENERIC_TITLE_WORDS = {
    "a", "accent", "and", "for", "from", "home", "in", "of", "the", "to", "with",
    "cabinet", "console", "decor", "display", "entryway", "furniture", "hallway", "living",
    "piece", "product", "room", "shelf", "sofa", "storage", "table", "unit",
}
_GROUNDING_TERMS = {
    "adjustable", "boho", "cabinet", "door", "doors", "drawer", "drawers", "engineered wood",
    "farmhouse", "foldable", "glass", "industrial", "led", "lower shelf", "mahogany", "mdf",
    "metal", "mid-century", "minimalist", "modern", "oak", "outdoor", "pine", "storage", "teak",
    "walnut", "waterproof", "wheel", "wheels",
}

VISUAL_KEYWORD_FIELDS = ("design_keywords", "shape_keywords")
VISUAL_ANALYSIS_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Wrydeco gallery visual analysis",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "task_id",
        "source_digest",
        "target_identity",
        "evidence_ids",
        "design_keywords",
        "shape_keywords",
    ],
    "properties": {
        "task_id": {
            "type": "string",
            "description": "Copy task.task_id from get_content_context exactly.",
        },
        "source_digest": {
            "type": "string",
            "description": "Copy source_digest from get_content_context exactly.",
        },
        "target_identity": {
            "type": "string",
            "minLength": 3,
            "maxLength": 120,
            "description": "Identify the product using source.title and product_type, not scene props.",
        },
        "evidence_ids": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": {"type": "string", "pattern": "^gallery/"},
            "description": "Only gallery image IDs actually read through read_evidence.",
        },
        "design_keywords": {
            "type": "array",
            "minItems": 2,
            "maxItems": 6,
            "uniqueItems": True,
            "items": {"type": "string", "minLength": 1, "maxLength": 80},
        },
        "shape_keywords": {
            "type": "array",
            "minItems": 2,
            "maxItems": 6,
            "uniqueItems": True,
            "items": {"type": "string", "minLength": 1, "maxLength": 80},
        },
    },
    "keyword_rules": {
        "allowed": ["design", "shape", "silhouette", "visible structure", "geometric detail"],
        "forbidden_visual_inferences": [
            "material", "wood species", "color", "finish", "dimensions", "scale",
            "durability", "manufacturing method", "certification", "unsupported function",
        ],
        "phrase_word_count": "1-6 words per keyword",
    },
}
_VISUAL_BLOCKED_TERMS = {
    # Materials and construction claims are not safe visual inferences.
    "wood", "wooden", "oak", "pine", "teak", "walnut", "mahogany", "mdf", "metal",
    "steel", "iron", "brass", "copper", "aluminum", "aluminium", "glass", "marble", "stone",
    "concrete", "travertine", "ceramic", "rattan", "bamboo", "veneer", "plywood", "resin",
    "leather", "fabric", "velvet", "plastic", "acrylic", "engineered", "solid wood",
    # Colors and finishes can be customized on the storefront PDP.
    "black", "white", "brown", "beige", "cream", "gray", "grey", "red", "blue", "green",
    "yellow", "orange", "pink", "purple", "gold", "silver", "bronze", "ivory", "taupe", "tan",
    "navy", "charcoal", "espresso", "honey", "cherry", "natural", "warm", "dark", "light",
    "finish", "finished", "stained", "painted", "lacquered",
    # Unsupported performance/manufacturing assertions.
    "durable", "handmade", "handcrafted", "waterproof", "scratch-resistant", "certified",
}
_MEASUREMENT_RE = re.compile(
    r"(?:\b\d+(?:\.\d+)?\b|\b(?:inch|inches|cm|mm|meter|metre|feet|foot|ft|wide|width|"
    r"high|height|deep|depth|large|small|compact|oversized|tall|short)\b)",
    re.I,
)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_BOILERPLATE_WORDS = {"key", "features", "details", "overview", "wrydeco", "product", "description"}


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


def validate_content_grounding(
    payload_or_path: dict[str, Any] | Path,
    source_or_path: dict[str, Any] | Path,
) -> dict[str, str]:
    """Validate storefront copy against the scraped product evidence.

    This deliberately uses conservative lexical checks rather than trying to
    infer facts.  It is a fail-closed guard after the Agent's semantic work:
    headings must retain distinctive source identity, and high-risk feature,
    material, and style terms may not appear unless the source contains them.
    """
    content = validate_content(payload_or_path)
    source = load_json(source_or_path) if isinstance(source_or_path, Path) else source_or_path
    if not isinstance(source, dict):
        raise ContentValidationError("source.json must contain an object for factual validation.")
    source_parts = [str(source.get("title") or "")]
    bullets = source.get("bullets")
    if isinstance(bullets, list):
        source_parts.extend(str(item) for item in bullets if isinstance(item, str))
    source_parts.append(str(source.get("aplus_text") or ""))
    source_text = unicodedata.normalize("NFKC", " ".join(source_parts)).casefold()
    if not source_text.strip():
        raise ContentValidationError("Source evidence has no title or product facts for factual validation.")

    source_words = set(_WORD_RE.findall(source_text))
    distinctive = source_words - _GENERIC_TITLE_WORDS
    heading_text = " ".join((content["title"], content["seo_product_title"])).casefold()
    heading_words = set(_WORD_RE.findall(heading_text))
    if len(distinctive) >= 2 and len(distinctive & heading_words) < 2:
        raise ContentValidationError(
            "title and seo_product_title must preserve at least two distinctive facts from the Amazon source title."
        )

    generated_text = unicodedata.normalize("NFKC", " ".join(content.values())).casefold()
    for term in sorted(_GROUNDING_TERMS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(term)}\b", generated_text) and not re.search(
            rf"\b{re.escape(term)}\b", source_text
        ):
            raise ContentValidationError(f"Unsupported factual term in content: {term}")

    source_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", source_text))
    generated_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", generated_text))
    unsupported_numbers = generated_numbers - source_numbers
    if unsupported_numbers:
        raise ContentValidationError(
            "Content contains numeric claims absent from source evidence: " + ", ".join(sorted(unsupported_numbers))
        )
    return content


def source_digest(source_or_path: dict[str, Any] | Path) -> str:
    source = load_json(source_or_path) if isinstance(source_or_path, Path) else source_or_path
    if not isinstance(source, dict):
        raise ContentValidationError("source.json must contain an object.")
    canonical = json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_visual_analysis(
    payload_or_path: dict[str, Any] | Path,
    *,
    expected_task_id: str,
    expected_source_digest: str,
    allowed_evidence_ids: set[str] | None = None,
) -> dict[str, Any]:
    payload = load_json(payload_or_path) if isinstance(payload_or_path, Path) else payload_or_path
    if not isinstance(payload, dict):
        raise ContentValidationError("visual_analysis.json must contain an object.")
    if str(payload.get("task_id") or "") != expected_task_id:
        raise ContentValidationError("visual_analysis task_id does not match the claimed task.")
    if str(payload.get("source_digest") or "") != expected_source_digest:
        raise ContentValidationError("visual_analysis source_digest is stale or incorrect.")
    target = str(payload.get("target_identity") or "").strip()
    if len(target) < 3 or len(target) > 120:
        raise ContentValidationError("visual_analysis target_identity must be 3-120 characters.")
    evidence_ids = payload.get("evidence_ids")
    if not isinstance(evidence_ids, list) or not evidence_ids:
        raise ContentValidationError("visual_analysis must cite image evidence IDs.")
    normalized_evidence: list[str] = []
    for raw in evidence_ids:
        evidence_id = str(raw).strip()
        if not evidence_id or evidence_id in normalized_evidence:
            continue
        if allowed_evidence_ids is not None and evidence_id not in allowed_evidence_ids:
            raise ContentValidationError(f"visual_analysis cites unread image evidence: {evidence_id}")
        normalized_evidence.append(evidence_id)
    if not normalized_evidence:
        raise ContentValidationError("visual_analysis must cite at least one read image.")

    result: dict[str, Any] = {
        "task_id": expected_task_id,
        "source_digest": expected_source_digest,
        "target_identity": target,
        "evidence_ids": normalized_evidence,
    }
    for field in VISUAL_KEYWORD_FIELDS:
        values = payload.get(field)
        if not isinstance(values, list) or not 2 <= len(values) <= 6:
            raise ContentValidationError(f"{field} must contain 2-6 visual keyword phrases.")
        cleaned: list[str] = []
        for raw in values:
            phrase = " ".join(str(raw).strip().split())
            if not phrase or len(phrase.split()) > 6:
                raise ContentValidationError(f"{field} entries must contain 1-6 words.")
            folded = unicodedata.normalize("NFKC", phrase).casefold()
            if _MEASUREMENT_RE.search(folded):
                raise ContentValidationError(f"Visual keyword may not infer dimensions or scale: {phrase}")
            blocked = next(
                (term for term in sorted(_VISUAL_BLOCKED_TERMS, key=len, reverse=True)
                 if re.search(rf"\b{re.escape(term)}\b", folded)),
                None,
            )
            if blocked:
                raise ContentValidationError(
                    f"Visual keyword may not infer material, color, finish, or performance ({blocked}): {phrase}"
                )
            if folded not in {item.casefold() for item in cleaned}:
                cleaned.append(phrase)
        if len(cleaned) < 2:
            raise ContentValidationError(f"{field} must contain at least two distinct phrases.")
        result[field] = cleaned
    return result


def validate_visual_keyword_usage(content: dict[str, str], visual: dict[str, Any]) -> None:
    phrases = [
        str(value).casefold()
        for field in VISUAL_KEYWORD_FIELDS
        for value in visual.get(field, [])
        if isinstance(value, str) and value.strip()
    ]
    headings = f"{content['title']} {content['seo_product_title']}".casefold()
    description = _HTML_TAG_RE.sub(" ", content["description_html"]).casefold()
    seo = f"{content['seo_title']} {content['seo_description']}".casefold()
    if not any(phrase in headings for phrase in phrases):
        raise ContentValidationError("title or seo_product_title must use an approved visual keyword.")
    if sum(1 for phrase in phrases if phrase in description) < 2:
        raise ContentValidationError("description_html must use at least two approved visual keywords.")
    if not any(phrase in seo for phrase in phrases):
        raise ContentValidationError("seo_title or seo_description must use an approved visual keyword.")


def normalize_content_field(field: str, value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold()
    if field == "description_html":
        text = _HTML_TAG_RE.sub(" ", text)
    if field == "seo_title":
        text = re.sub(r"\s*\|\s*wrydeco\s*$", "", text)
    words = [word for word in _WORD_RE.findall(text) if not (field == "description_html" and word in _BOILERPLATE_WORDS)]
    return " ".join(words)


def _token_shingles(value: str, size: int = 3) -> set[tuple[str, ...]]:
    tokens = value.split()
    if len(tokens) < size:
        return {tuple(tokens)} if tokens else set()
    return {tuple(tokens[index:index + size]) for index in range(len(tokens) - size + 1)}


def content_fingerprints(content: dict[str, str]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for field, value in content.items():
        normalized = normalize_content_field(field, value)
        output[field] = {
            "normalized": normalized,
            "sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            "tokens": sorted(set(normalized.split())),
            "shingles": sorted(" ".join(shingle) for shingle in _token_shingles(normalized)),
        }
    return output


def content_similarity(field: str, left: str, right: str) -> float:
    left_normalized = normalize_content_field(field, left)
    right_normalized = normalize_content_field(field, right)
    if not left_normalized or not right_normalized:
        return 0.0
    if left_normalized == right_normalized:
        return 1.0
    sequence = SequenceMatcher(None, left_normalized, right_normalized, autojunk=False).ratio()
    left_tokens, right_tokens = set(left_normalized.split()), set(right_normalized.split())
    token_score = len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))
    left_shingles, right_shingles = _token_shingles(left_normalized), _token_shingles(right_normalized)
    shingle_score = len(left_shingles & right_shingles) / max(1, len(left_shingles | right_shingles))
    return max(sequence, token_score, shingle_score)

