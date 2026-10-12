"""Clean sale labels after price verification, retaining source evidence."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .errors import PriceValidationError
from .pricing import money, normalize_name
from .sku import clean_option, load_rules


def _clean_value(option: dict[str, Any], rules: dict[str, Any]) -> None:
    original = str(option["value"])
    cleaned = clean_option(original, rules)
    if not cleaned:
        raise PriceValidationError(f"Option has no value after marketing cleanup: {original!r}")
    if cleaned != original:
        option.setdefault("source_value", original)
    option["value"] = cleaned


def clean_variant_values(variants: list[dict[str, Any]], *, price_key: str,
                         rules: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Merge equivalent combinations only when their verified prices agree."""
    rules = rules or load_rules()
    unique: dict[tuple[tuple[str, str], ...], dict[str, Any]] = {}
    for source in variants:
        variant = deepcopy(source)
        for option in variant["options"]:
            _clean_value(option, rules)
        for selected in variant.get("selection", []):
            _clean_value(selected, rules)
        key = tuple(sorted((normalize_name(item["name"]), normalize_name(item["value"]))
                           for item in variant["options"]))
        previous = unique.get(key)
        if previous is None:
            unique[key] = variant
        else:
            if money(previous[price_key]) != money(variant[price_key]):
                raise PriceValidationError(
                    f"Marketing cleanup creates duplicate options with different prices: {key!r}"
                )
            # Keep every source combination, including DOM indices and ASINs.
            if "merged_sources" not in previous:
                previous["merged_sources"] = [deepcopy(previous)]
            previous["merged_sources"].append(deepcopy(source))
    return list(unique.values())


def clean_pricing_options(pricing: dict[str, Any]) -> dict[str, Any]:
    """Only call after all original DOM selections have been price-verified."""
    cleaned = deepcopy(pricing)
    rules = load_rules()
    cleaned["variants"] = clean_variant_values(cleaned["variants"], price_key="verified_total", rules=rules)
    for group in cleaned.get("option_types", []):
        unique: dict[str, dict[str, Any]] = {}
        for source in group["options"]:
            option = deepcopy(source)
            _clean_value(option, rules)
            key = normalize_name(option["value"])
            if key in unique:
                previous = unique[key]
                if "source_options" not in previous:
                    previous["source_options"] = [deepcopy(previous)]
                previous["source_options"].append(deepcopy(source))
            else:
                unique[key] = option
        group["options"] = list(unique.values())
    return cleaned
