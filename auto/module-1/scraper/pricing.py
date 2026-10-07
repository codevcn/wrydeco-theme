from __future__ import annotations

import itertools
import re
import unicodedata
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Iterable, Mapping, Sequence

from .config import DEFAULT_OPTION_TYPES, IGNORE_TYPES, SIZE_CONFIG
from .errors import PriceValidationError

CENT = Decimal("0.01")
MONEY_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _normalize_price_text(text: Any) -> str:
    """Normalize prices rendered as separate Amazon DOM spans.

    Amazon's visible ``.a-price`` text can be returned by Playwright as
    ``+$800 . 00`` because the whole, decimal and fraction are separate
    elements.  Treat whitespace around numeric separators as presentation
    whitespace, while leaving all other text intact for the strict parsers.
    """
    normalized = " ".join(str(text or "").replace("\xa0", " ").split())
    return re.sub(r"(?<=\d)\s*([,.])\s*(?=\d)", r"\1", normalized)


def money(value: Any) -> Decimal:
    try:
        return Decimal(str(value).replace(",", "").strip()).quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise PriceValidationError(f"Invalid money value: {value!r}") from exc


def normalize_name(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip().rstrip(":").strip()
    return text.casefold()


def is_ignored_type(name: str, ignored: Iterable[str] = IGNORE_TYPES) -> bool:
    normalized = normalize_name(name)
    return normalized in {normalize_name(value) for value in ignored}


def parse_base_price(text: str, currency: str = "USD") -> Decimal:
    normalized = _normalize_price_text(text)
    if re.search(r"\d\s*[-–—]\s*(?:\$|USD)?\s*\d", normalized, re.I):
        raise PriceValidationError(f"Price range is not accepted: {normalized!r}")
    if currency == "USD" and re.search(r"(?:€|£|¥|₫|₹|CAD|AUD|EUR|GBP|VND|INR)", normalized, re.I):
        raise PriceValidationError(f"Non-USD price is not accepted: {normalized!r}")
    values = MONEY_RE.findall(normalized)
    if len(values) != 1:
        raise PriceValidationError(f"Expected one base price, found {len(values)} in {normalized!r}")
    return money(values[0])


def parse_additional_price(text: str, *, option: str = "", type_name: str = "") -> tuple[Decimal, bool]:
    normalized = _normalize_price_text(text)
    if not normalized:
        return Decimal("0.00"), False
    if re.search(r"(?:€|£|¥|₫|₹|CAD|AUD|EUR|GBP|VND|INR)", normalized, re.I):
        raise PriceValidationError(f"Wrong currency for {type_name}/{option}: {normalized!r}")
    if re.search(r"\d\s*[-–—]\s*(?:\$|USD)?\s*\d", normalized, re.I):
        raise PriceValidationError(f"Price range for {type_name}/{option}: {normalized!r}")
    match = re.fullmatch(r"\s*([+-])\s*(?:USD\s*)?\$?\s*(\d[\d,]*(?:\.\d+)?)\s*", normalized, re.I)
    if not match:
        raise PriceValidationError(
            f"Additional price must have an explicit + or - for {type_name}/{option}: {normalized!r}"
        )
    value = money(match.group(2))
    return (-value if match.group(1) == "-" else value), True


def remove_default_option(type_name: str, options: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    copied = [dict(option) for option in options]
    if len(copied) <= 1:
        raise PriceValidationError(f'Type "{type_name}" has too few options to remove a default.')
    zero = [
        option for option in copied
        if money(option.get("additional_price", 0)) == Decimal("0.00")
        and not bool(option.get("has_explicit_price"))
    ]
    if len(zero) == 1:
        target = zero[0]
    elif len(zero) > 1:
        target = next((option for option in zero if int(option.get("dom_index", -1)) == 0), None)
        if target is None:
            raise PriceValidationError(f'Cannot safely determine the default option for "{type_name}".')
    else:
        raise PriceValidationError(f'Cannot safely determine the default option for "{type_name}".')
    return [option for option in copied if option is not target]


def build_combinations(option_types: Sequence[Mapping[str, Any]], max_combinations: int = 100) -> list[dict[str, Any]]:
    if not option_types:
        raise PriceValidationError("No customization option types were found.")
    if len(option_types) > 3:
        raise PriceValidationError("Shopify supports at most three option types, including Wood Finish.")
    option_lists = [list(group["options"]) for group in option_types]
    total = 1
    for options in option_lists:
        total *= len(options)
    if total > max_combinations:
        raise PriceValidationError(f"Combination safety cap exceeded: {total} > {max_combinations}.")
    result = []
    for chosen in itertools.product(*option_lists):
        result.append({
            "options": [
                {"name": str(group["name"]), "value": str(option["value"])}
                for group, option in zip(option_types, chosen)
            ],
            "additional_price": money(sum((money(option.get("additional_price", 0)) for option in chosen), Decimal(0))),
            "selection": [dict(option) for option in chosen],
        })
    return result


def verify_total(base_price: Any, additional_price: Any, observed_total: Any, tolerance: Decimal = CENT) -> Decimal:
    expected = money(money(base_price) + money(additional_price))
    observed = money(observed_total)
    if abs(expected - observed) > tolerance:
        raise PriceValidationError(f"Price verification failed: expected {expected}, observed {observed}.")
    return expected


def preset_variants(furniture_type: str, price_tier: str) -> tuple[Decimal, list[dict[str, Any]]]:
    furniture = SIZE_CONFIG.get(str(furniture_type).lower())
    tier = furniture.get(str(price_tier).upper()) if furniture else None
    if not tier or len(tier) != 4:
        raise PriceValidationError(f"Unknown or invalid preset {furniture_type}/{price_tier}.")
    seen: set[str] = set()
    options = []
    for index, (value, raw_price) in enumerate(tier):
        price = money(raw_price)
        if price <= 0 or value in seen:
            raise PriceValidationError("Preset prices must be positive and option values unique.")
        seen.add(value)
        options.append({"options": [{"name": "Size", "value": value}], "additional_price": price, "dom_index": index})
    return Decimal("0.00"), options


def infer_wood_finish_deltas(variants: Sequence[Mapping[str, Any]], wood_name: str = "Wood Finish") -> dict[str, Decimal]:
    if not variants:
        raise PriceValidationError("Cannot infer Wood Finish pricing without existing variants.")
    grouped: dict[tuple[tuple[str, str], ...], dict[str, Decimal]] = {}
    all_finishes: set[str] = set()
    for variant in variants:
        selections = variant.get("selectedOptions") or variant.get("selected_options") or []
        finish = None
        other: list[tuple[str, str]] = []
        for selected in selections:
            name = str(selected.get("name", ""))
            value = str(selected.get("value", ""))
            if normalize_name(name) == normalize_name(wood_name):
                finish = value
            else:
                other.append((normalize_name(name), value))
        if not finish:
            raise PriceValidationError("A Shopify variant is missing Wood Finish.")
        all_finishes.add(finish)
        grouped.setdefault(tuple(sorted(other)), {})[finish] = money(variant.get("price"))
    if not grouped or any(set(prices) != all_finishes for prices in grouped.values()):
        raise PriceValidationError("Insufficient paired variants to infer Wood Finish prices.")
    candidates = list(grouped.values())
    inferred: dict[str, list[Decimal]] = {finish: [] for finish in all_finishes}
    for prices in candidates:
        base = min(prices.values())
        for finish in all_finishes:
            inferred[finish].append(money(prices[finish] - base))
    result = {}
    for finish, values in inferred.items():
        if max(values) - min(values) > CENT:
            raise PriceValidationError(f'Inconsistent Wood Finish surcharge for "{finish}".')
        result[finish] = money(sum(values, Decimal(0)) / Decimal(len(values)))
    return result


def uses_default_removal(type_name: str) -> bool:
    return normalize_name(type_name) in {normalize_name(value) for value in DEFAULT_OPTION_TYPES}

