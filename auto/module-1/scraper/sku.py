"""Deterministic, tag-routed SKU planning; no Shopify mutations or AI calls."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable

from .errors import ShopifyError
from .io_utils import load_json

RULES_PATH = Path(__file__).with_name("sku_rules.json")


def load_rules() -> dict[str, Any]:
    return load_json(RULES_PATH)


def _ascii(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()


def clean_option(value: str, rules: dict[str, Any] | None = None) -> str:
    rules = rules or load_rules()
    text = unicodedata.normalize("NFKC", str(value))
    text = re.sub(r"[‐‑–—]", "-", text)
    patterns = [(r"(?<!\w)" + r"[\s_-]+".join(re.escape(word) for word in phrase.split())
                 + r"(?:[\s_-]+(?:sizes?|finish(?:es)?|colou?rs?|options?))?(?!\w)")
                for phrase in sorted(rules["marketing_phrases"], key=len, reverse=True)]
    # Match once from left to right: removing "Popular Size" first must not
    # strand "Most" from the longer phrase "Most Popular Size".
    if patterns:
        text = re.sub("|".join(patterns), "", text, flags=re.I)
    text = re.sub(r"\([\s\-|,;:]*\)|\[[\s\-|,;:]*\]", "", text)
    text = re.sub(r"\s+", " ", text).strip(" -|,;:")
    if text.count("(") != text.count(")"):
        text = text.strip("()").strip(" -|,;:")
    if text.count("[") != text.count("]"):
        text = text.strip("[]").strip(" -|,;:")
    return text


def _words(value: str) -> list[str]:
    return re.findall(r"[A-Z0-9]+", _ascii(value).upper())


def _digest(value: str, width: int = 4) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:width].upper()


def _bounded(value: str, maximum: int) -> str:
    if len(value) <= maximum:
        return value
    return value[:maximum - 5].rstrip("-") + "-" + _digest(value)


def abbreviate(value: str, maximum: int = 7) -> str:
    # Unknown finishes always become abbreviations, including short words.
    words = _words(value)
    if not words:
        raise ShopifyError("An option contains no usable SKU characters after marketing cleanup.")
    code = "-".join(word[:min(3, max(1, len(word) - 1))] for word in words)
    return _bounded(code, maximum)


def finish_code(value: str, rules: dict[str, Any] | None = None) -> str:
    rules = rules or load_rules()
    cleaned = clean_option(value, rules)
    cleaned = re.sub(r"^(?:option|color|finish)\s*\d+\s*[-:]\s*", "", cleaned, flags=re.I)
    key = " ".join(_words(cleaned)).lower()
    return rules["finish_codes"].get(key) or abbreviate(cleaned)


def size_code(value: str, rules: dict[str, Any] | None = None) -> str:
    text = clean_option(value, rules)
    if re.search(r"\bcustom\b", text, re.I):
        return "CUST"
    # Preserve explicit units; do not silently convert cm/feet to inches.
    units = [code for pattern, code in ((r"(?<![a-z])(?:cm|centimeters?)(?![a-z])", "CM"),
                                       (r"(?<![a-z])(?:mm|millimeters?)(?![a-z])", "MM"),
                                       (r"(?<![a-z])(?:ft|feet|foot)(?![a-z])", "FT"))
             if re.search(pattern, text, re.I)]
    if len(units) > 1:
        raise ShopifyError("Size mixes units; provide a consistent dimension label.")
    unit = units[0] if units else ""
    if unit and re.search(r"[\"″]|(?<![a-z])inches?(?![a-z])", text, re.I):
        raise ShopifyError("Size mixes units; provide a consistent dimension label.")
    text = re.sub(r"\b(width|height|depth|length|diameter)\b",
                  lambda m: m[0][0].upper(), text, flags=re.I)
    text = re.sub(r"(?<![a-z])(?:inches?|cm|centimeters?|mm|millimeters?|ft|feet|foot)(?![a-z])", "", text, flags=re.I)
    text = re.sub(r"[\s\"'′″]", "", text).upper().replace("×", "X").replace("*", "X")
    number = r"\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?"
    after = list(re.finditer(rf"({number})([WHLD])", text))
    before = list(re.finditer(rf"([WHLD])({number})", text))
    matches = after if len(after) >= len(before) else before
    if matches:
        def dimension(match: re.Match) -> str:
            amount, axis = match.groups() if matches is after else tuple(reversed(match.groups()))
            return axis + amount.replace(".", "P").replace("-", "T")
        code = "".join(dimension(match) for match in matches)
        # Reject partial parsing rather than dropping an unrecognized dimension.
        remainder = text
        for match in reversed(matches):
            remainder = remainder[:match.start()] + remainder[match.end():]
        if remainder.strip("X,;:/()"):
            code = "-".join(_words(text))
    elif re.fullmatch(rf"{number}(?:X{number})*", text):
        code = text.replace(".", "P").replace("-", "T")
    else:
        code = abbreviate(text, 12)
    return _bounded(code + unit, 16)


def option_key(options: list[dict[str, str]]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((" ".join(o["name"].split()).casefold(),
                         " ".join(o["value"].split()).casefold()) for o in options))


def route_prefix(tags: str | list[str], rules: dict[str, Any]) -> dict[str, str]:
    values = tags.split(",") if isinstance(tags, str) else tags
    for rule in rules["prefix_rules"]:
        if any(rule["tag_contains"].casefold() in str(tag).casefold() for tag in values):
            return rule
    return rules["default_prefix"]


def _components(options: list[dict[str, str]], rules: dict[str, Any]) -> tuple[list[str], list[dict[str, str]]]:
    finishes, sizes, extras, audit = [], [], [], []
    for option in options:
        name, raw = option["name"], option["value"]
        cleaned = clean_option(raw, rules)
        if not cleaned:
            raise ShopifyError(f"Option {name!r} has no factual value after marketing cleanup.")
        if re.search(r"finish|colou?r", name, re.I):
            code = finish_code(cleaned, rules)
            finishes.append(code)
        elif re.search(r"size|width|height|depth|length|dimension", name, re.I):
            code = size_code(cleaned, rules)
            sizes.append(code)
        elif name.casefold() == "title" and cleaned.casefold() == "default title":
            code = "DEFA"
            extras.append(code)
        else:
            key = " ".join(_words(cleaned)).lower()
            code = rules["extra_codes"].get(key) or abbreviate(cleaned, 8)
            extras.append(code)
        audit.append({"name": name, "original": raw, "cleaned": cleaned, "code": code})
    return [*(finishes or ["NA"]), *(sizes or ["NA"]), *extras], audit


def _base(prefix: str, identity: str, components: list[str], maximum: int, suffix: str) -> str:
    head = f"{prefix}-{identity}-"
    budget = maximum - len(head) - len(suffix) - 1
    if budget < 6:
        raise ShopifyError("SKU prefix/identity leaves insufficient room for variant attributes.")
    # Never cut the prefix, ASIN, or uniqueness suffix.
    return head + _bounded("-".join(components), budget) + "-" + suffix


def build_sku_plan(variants: list[dict[str, Any]], *, tags: str | list[str], asin: str,
                   handle: str, existing: list[dict[str, Any]] = (),
                   occupied: Iterable[str] = (), previous: dict[str, Any] | None = None,
                   rules: dict[str, Any] | None = None) -> dict[str, Any]:
    rules = rules or load_rules()
    route = route_prefix(tags, rules)
    prefix = route["prefix"]
    if route["identity"] not in {"asin", "handle"}:
        raise ShopifyError("Unsupported SKU identity strategy; register asin or handle.")
    if not re.fullmatch(r"[a-zA-Z0-9]+", prefix):
        raise ShopifyError("SKU prefix must be alphanumeric.")
    identity = asin.upper() if route["identity"] == "asin" else "".join(word[:3] for word in _words(handle)[:2])
    if not identity or (route["identity"] == "asin" and not re.fullmatch(r"[A-Z0-9]{10}", identity)):
        raise ShopifyError("SKU source identity is missing or invalid.")
    maximum = int(rules["max_length"])
    used = {str(s).casefold() for s in occupied if s}
    prior = {option_key(row["options"]): row for row in (previous or {}).get("variants", [])}
    current = {option_key(row["selectedOptions"]): row.get("sku", "") for row in existing}
    entries, reserved = [], set(used)
    keys = [option_key(row["options"]) for row in variants]
    if not variants or len(keys) != len(set(keys)):
        raise ShopifyError("SKU planning requires nonempty, unique variant option combinations.")
    # Reserve surviving old codes before allocating new indices, even if order changed.
    kept = {}
    for row in variants:
        key = option_key(row["options"])
        components, audit = _components(row["options"], rules)
        candidate = prior.get(key, {}).get("sku") or current.get(key) or ""
        suffix = candidate.rsplit("-", 1)[-1]
        valid = (suffix.isdigit() and int(suffix) > 0 and len(candidate) <= maximum
                 and candidate.casefold() == _base(prefix, identity, components, maximum, suffix).casefold()
                 and candidate.casefold() not in reserved)
        if valid:
            kept[key] = candidate
            reserved.add(candidate.casefold())
    allocated_indices = {int(value.rsplit("-", 1)[-1]) for value in kept.values()}
    next_index = 1
    for row in variants:
        key = option_key(row["options"])
        components, audit = _components(row["options"], rules)
        candidate = kept.get(key)
        collisions = 0
        if not candidate:
            index = next_index
            while True:
                if index in allocated_indices:
                    index += 1
                    continue
                candidate = _base(prefix, identity, components, maximum, f"{index:02d}")
                if candidate.casefold() not in reserved:
                    break
                index += 1
                collisions += 1
            reserved.add(candidate.casefold())
            allocated_indices.add(index)
            next_index = index + 1
        entries.append({"options": row["options"], "sku": candidate, "components": audit,
                        "preserved": key in kept, "collisions_resolved": collisions})
    return {"rules_version": rules["version"], "prefix": prefix, "identity": identity,
            "max_length": maximum, "variants": entries}
