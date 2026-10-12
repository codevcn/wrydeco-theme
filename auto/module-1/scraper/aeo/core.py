from __future__ import annotations

import hashlib
import html
import json
import re
from typing import Any

from ..errors import ContentValidationError
from ..sku import clean_option

SUMMARY_LABELS = {"Product type", "Design", "Configuration", "Primary use", "Placement", "Dimensions", "Visual style"}
RESTRICTED = {
    "solid wood", "engineered wood", "mdf", "walnut", "oak", "pine", "teak", "mahogany", "metal",
    "handmade", "handcrafted", "artisan", "sustainable", "eco-friendly", "reclaimed", "waterproof",
    "water-resistant", "outdoor", "uv-resistant", "scratch-resistant", "oil finish", "lacquer",
    "protective coating", "joinery", "screws", "anchors", "hardware included", "weight capacity",
    "load capacity", "warranty", "shipping", "delivery", "returns", "certified", "durable",
    "made-to-order", "customization", "storage", "drawer", "drawers", "lower shelf",
    "black", "white", "brown", "beige", "gray", "grey", "red", "blue", "green", "gold", "silver",
    "weighted", "reinforced", "single-tier", "two-tier", "three-tier", "solid display surface",
}


def _dimensions(text: str) -> set[tuple[str, str, str]]:
    pattern = (r"(?<![\d.])(\d+(?:\.\d+)?)\s*[-]?\s*"
               r"(inches?|in|cm|mm|ft|feet|foot|[\"'′″]+)?\s*[-]?\s*"
               r"(width|wide|height|high|depth|deep|length|long|w|h|d|l)(?![a-wyz])")
    result = set()
    for number, unit, axis in re.findall(pattern, text.casefold()):
        unit = "in" if unit.startswith("in") or re.search(r"[\"'′″]", unit) else ("ft" if unit in {"feet", "foot", "ft"} else unit)
        result.add((number, axis[0], unit))
    return result


def schema() -> dict[str, Any]:
    evidence = {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string"}}
    def item(properties):
        return {"type": "object", "additionalProperties": False,
                "required": list(properties), "properties": properties}
    text = {"type": "string", "minLength": 1}
    return item({
        "overview": item({"text": text, "evidence_ids": evidence}),
        "summary": {"type": "array", "maxItems": 7, "items": item({
            "label": {"enum": sorted(SUMMARY_LABELS)}, "value": text, "evidence_ids": evidence})},
        "faq": {"type": "array", "minItems": 3, "maxItems": 8, "items": item({
            "question": text, "answer": text, "evidence_ids": evidence})},
    })


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def build_input(identity: dict[str, Any], source: dict[str, Any], pricing: dict[str, Any],
                visual: dict[str, Any]) -> dict[str, Any]:
    """Compile public evidence; no credentials, raw HTML, A+ images or store policies."""
    facts = []
    def add(identifier, text, kind):
        text = " ".join(str(text or "").split())
        if text:
            facts.append({"id": identifier, "text": text, "kind": kind})
    add("source:title", source.get("title"), "source_text")
    add("identity:product_type", identity.get("product_type"), "identity")
    for i, value in enumerate(source.get("bullets") or []):
        add(f"source:bullet:{i}", value, "source_text")
    add("source:aplus", str(source.get("aplus_text") or "")[:12000], "source_text")
    values = {}
    for variant in pricing.get("variants") or []:
        for option in variant.get("options") or []:
            key = (str(option["name"]), clean_option(str(option["value"])))
            if key[1]:
                values.setdefault(key, None)
    for i, (name, value) in enumerate(values):
        add(f"option:{i}", f"{name}: {value}", "verified_option")
    phrases = list(dict.fromkeys([*(visual.get("design_keywords") or []), *(visual.get("shape_keywords") or [])]))
    for i, value in enumerate(phrases):
        add(f"visual:{i}", value, "approved_visual")
    result = {"version": 1, "identity": {key: identity.get(key) for key in ("asin", "product_type")}, "facts": facts}
    result["input_digest"] = _digest(result)
    return result


def _text(value: Any, field: str, low: int = 1, high: int = 2000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContentValidationError(f"aeo.{field}: nonempty text is required.")
    text = " ".join(value.split())
    if re.search(r"<[^>]*>|https?://", text, re.I):
        raise ContentValidationError(f"aeo.{field}: use plain text without HTML or URLs.")
    words = re.findall(r"\b[\w]+(?:[-'][\w]+)*\b", text)
    if not low <= len(words) <= high:
        raise ContentValidationError(f"aeo.{field}: expected {low}–{high} words; got {len(words)}.")
    return text


def _refs(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value or any(not isinstance(v, str) or not v for v in value):
        raise ContentValidationError(f"aeo.{field}: nonempty evidence_ids are required.")
    return list(dict.fromkeys(value))


def normalize_draft(draft: Any) -> dict[str, Any]:
    """Validate output shape/lengths independently of product evidence."""
    if not isinstance(draft, dict) or set(draft) != {"overview", "summary", "faq"}:
        raise ContentValidationError("aeo: expected exactly overview, summary and faq.")
    overview = draft["overview"]
    if not isinstance(overview, dict) or set(overview) != {"text", "evidence_ids"}:
        raise ContentValidationError("aeo.overview: expected text and evidence_ids.")
    result = {"overview": {"text": _text(overview["text"], "overview", 80, 140),
                           "evidence_ids": _refs(overview["evidence_ids"], "overview")}, "summary": [], "faq": []}
    summary = draft["summary"]
    if not isinstance(summary, list) or len(summary) > 7:
        raise ContentValidationError("aeo.summary: expected at most seven attributes.")
    labels = set()
    for i, entry in enumerate(summary):
        if not isinstance(entry, dict) or set(entry) != {"label", "value", "evidence_ids"}:
            raise ContentValidationError(f"aeo.summary[{i}]: invalid attribute shape.")
        label = entry["label"]
        if label not in SUMMARY_LABELS or label in labels:
            raise ContentValidationError(f"aeo.summary[{i}]: invalid or duplicate label.")
        labels.add(label)
        result["summary"].append({"label": label, "value": _text(entry["value"], f"summary[{i}]", 1, 60),
                                  "evidence_ids": _refs(entry["evidence_ids"], f"summary[{i}]")})
    faq = draft["faq"]
    if not isinstance(faq, list) or not 3 <= len(faq) <= 8:
        raise ContentValidationError("aeo.faq: expected 3–8 useful, evidence-supported FAQs.")
    questions = set()
    for i, entry in enumerate(faq):
        if not isinstance(entry, dict) or set(entry) != {"question", "answer", "evidence_ids"}:
            raise ContentValidationError(f"aeo.faq[{i}]: invalid question shape.")
        question = _text(entry["question"], f"faq[{i}].question", 3, 30)
        key = " ".join(re.findall(r"\w+", question.casefold()))
        if key in questions:
            raise ContentValidationError(f"aeo.faq[{i}]: duplicate question.")
        questions.add(key)
        result["faq"].append({"question": question, "answer": _text(entry["answer"], f"faq[{i}].answer", 30, 80),
                              "evidence_ids": _refs(entry["evidence_ids"], f"faq[{i}]")})
    return result


def render_html(draft: dict[str, Any]) -> str:
    esc = html.escape
    parts = ['<div class="wrydeco-product-aeo"><h2>Product Overview</h2>',
             f'<p>{esc(draft["overview"]["text"])}</p>']
    if draft["summary"]:
        parts.append('<ul class="aeo-product-summary">')
        for item in draft["summary"]:
            parts.append(f'<li><strong>{esc(item["label"])}:</strong> {esc(item["value"])}</li>')
        parts.append('</ul>')
    parts.append('<h2>Product FAQ</h2>')
    for item in draft["faq"]:
        parts.append(f'<div class="aeo-faq-item"><h3>{esc(item["question"])}</h3><p>{esc(item["answer"])}</p></div>')
    return "".join(parts) + '</div>'


def validate_and_render(context: dict[str, Any], draft: Any) -> dict[str, Any]:
    normalized = normalize_draft(draft)
    facts = {item["id"]: item for item in context["facts"]}
    passages = [("overview", normalized["overview"]["text"], normalized["overview"]["evidence_ids"])]
    passages += [(f"summary[{i}]", item["value"], item["evidence_ids"]) for i, item in enumerate(normalized["summary"])]
    passages += [(f"faq[{i}]", item["question"] + " " + item["answer"], item["evidence_ids"]) for i, item in enumerate(normalized["faq"])]
    for field, text, refs in passages:
        missing = set(refs) - facts.keys()
        if missing:
            raise ContentValidationError(f"aeo.{field}: unknown evidence IDs: {sorted(missing)}")
        nonvisual = " ".join(facts[ref]["text"] for ref in refs if facts[ref]["kind"] != "approved_visual").casefold()
        folded = text.casefold()
        for term in RESTRICTED:
            pattern = rf"(?<!\w){re.escape(term)}(?!\w)"
            if re.search(pattern, folded) and not re.search(pattern, nonvisual):
                raise ContentValidationError(f"aeo.{field}: unsupported claim '{term}' in cited evidence.")
        numbers = set(re.findall(r"\d+(?:\.\d+)?", text))
        if numbers - set(re.findall(r"\d+(?:\.\d+)?", nonvisual)):
            raise ContentValidationError(f"aeo.{field}: numeric claim absent from cited text/options.")
        measured = _dimensions(folded)
        supported = _dimensions(nonvisual)
        if any(not any(n == number and a == axis and (not unit or u == unit) for n, a, u in supported)
               for number, axis, unit in measured):
            raise ContentValidationError(f"aeo.{field}: dimension axis/value/unit does not match cited evidence.")
        if measured and not any(all(any(n == number and a == axis and (not unit or u == unit)
                                        for n, a, u in _dimensions(facts[ref]["text"]))
                                    for number, axis, unit in measured)
                                for ref in refs if facts[ref]["kind"] != "approved_visual"):
            # A complete W/H/D tuple must belong to a single option/source fact.
            if len({axis for _, axis, _ in measured}) > 1:
                raise ContentValidationError(f"aeo.{field}: do not mix dimensions from different variants.")
        for unit, source_pattern in ((r"\b(?:cm|centimet(?:er|re)s?)\b", r"\b(?:cm|centimet(?:er|re)s?)\b"),
                                     (r"\b(?:mm|millimet(?:er|re)s?)\b", r"\b(?:mm|millimet(?:er|re)s?)\b"),
                                     (r"\b(?:inches|inch)\b", r"\b(?:inches|inch)\b|[\"'′″]"),
                                     (r"\b(?:feet|foot|ft)\b", r"\b(?:feet|foot|ft)\b")):
            if re.search(unit, folded) and not re.search(source_pattern, nonvisual):
                raise ContentValidationError(f"aeo.{field}: unsupported measurement unit.")
        for claim in re.findall(r"\b(?:solid|engineered|reclaimed)\s+(?:[a-z]+\s+)?wood\b|\b(?:oak|walnut|pine|teak)\s+wood\b", folded):
            source_text = " ".join(facts[ref]["text"] for ref in refs if facts[ref]["kind"] == "source_text").casefold()
            if claim not in source_text:
                raise ContentValidationError(f"aeo.{field}: construction claim requires cited source text: {claim}")
    return {"draft": normalized, "html": render_html(normalized), "input_digest": context["input_digest"],
            "faq_count": len(normalized["faq"]), "valid": True}
