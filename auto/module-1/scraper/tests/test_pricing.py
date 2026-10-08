from decimal import Decimal

import pytest

from scraper.errors import PriceValidationError
from scraper.pricing import (
    build_combinations,
    infer_wood_finish_deltas,
    is_ignored_type,
    normalize_name,
    parse_additional_price,
    parse_base_price,
    remove_default_option,
    uses_default_removal,
    verify_total,
)


def test_ignore_and_normalize_type():
    assert normalize_name("  Select Width: ") == "select width"
    assert is_ignored_type("Note to seller (Optional):")


def test_default_option_removal_unique_zero():
    options = [
        {"value": "default", "additional_price": "0", "has_explicit_price": False, "dom_index": 1},
        {"value": "large", "additional_price": "10", "has_explicit_price": True, "dom_index": 0},
    ]
    assert [item["value"] for item in remove_default_option("Size", options)] == ["large"]


def test_default_option_removal_multiple_zero_uses_dom_first():
    options = [
        {"value": "first", "additional_price": 0, "has_explicit_price": False, "dom_index": 0},
        {"value": "second", "additional_price": 0, "has_explicit_price": False, "dom_index": 1},
        {"value": "paid", "additional_price": 1, "has_explicit_price": True, "dom_index": 2},
    ]
    assert [item["value"] for item in remove_default_option("Size", options)] == ["second", "paid"]


def test_select_size_uses_default_option_removal():
    assert uses_default_removal("Select size")


@pytest.mark.parametrize(("raw", "expected"), [("+ $4,000.10", "4000.10"), ("- $1.25", "-1.25"), ("+10", "10.00")])
def test_explicit_additional_price(raw, expected):
    assert parse_additional_price(raw)[0] == Decimal(expected)


def test_amazon_split_span_prices_are_parsed_without_losing_cents():
    assert parse_additional_price("+$1,600  .  00")[0] == Decimal("1600.00")
    assert parse_additional_price("+$350\n.\n00")[0] == Decimal("350.00")
    assert parse_base_price("$4,215\n.\n00") == Decimal("4215.00")


@pytest.mark.parametrize("raw", ["$10.00", "+ $10 - $20", "+ €10", "CAD +10", "abc"])
def test_ambiguous_additional_price_rejected(raw):
    with pytest.raises(PriceValidationError):
        parse_additional_price(raw)


def test_cartesian_and_total():
    groups = [
        {"name": "Size", "options": [{"value": "S", "additional_price": "1"}, {"value": "L", "additional_price": "2"}]},
        {"name": "Install", "options": [{"value": "No", "additional_price": "0"}, {"value": "Yes", "additional_price": "3"}]},
    ]
    combinations = build_combinations(groups)
    assert [item["additional_price"] for item in combinations] == [Decimal("1.00"), Decimal("4.00"), Decimal("2.00"), Decimal("5.00")]
    assert verify_total("100", "5", "105.01") == Decimal("105.00")
    with pytest.raises(PriceValidationError):
        verify_total("100", "5", "105.02")


def test_combination_cap_and_three_option_limit():
    groups = [{"name": str(index), "options": [{"value": str(value)} for value in range(5)]} for index in range(3)]
    with pytest.raises(PriceValidationError):
        build_combinations(groups, 100)
    with pytest.raises(PriceValidationError):
        build_combinations([*groups, {"name": "four", "options": [{"value": "x"}]}])


def test_infer_wood_finish_surcharges():
    variants = [
        {"price": "100", "selectedOptions": [{"name": "Size", "value": "S"}, {"name": "Wood Finish", "value": "Natural"}]},
        {"price": "125", "selectedOptions": [{"name": "Size", "value": "S"}, {"name": "Wood Finish", "value": "Dark"}]},
        {"price": "200", "selectedOptions": [{"name": "Size", "value": "L"}, {"name": "Wood Finish", "value": "Natural"}]},
        {"price": "225.01", "selectedOptions": [{"name": "Size", "value": "L"}, {"name": "Wood Finish", "value": "Dark"}]},
    ]
    assert infer_wood_finish_deltas(variants) == {"Natural": Decimal("0.00"), "Dark": Decimal("25.01")}


def test_inconsistent_wood_finish_rejected():
    variants = [
        {"price": "100", "selectedOptions": [{"name": "Size", "value": "S"}, {"name": "Wood Finish", "value": "Natural"}]},
        {"price": "125", "selectedOptions": [{"name": "Size", "value": "S"}, {"name": "Wood Finish", "value": "Dark"}]},
        {"price": "200", "selectedOptions": [{"name": "Size", "value": "L"}, {"name": "Wood Finish", "value": "Natural"}]},
        {"price": "230", "selectedOptions": [{"name": "Size", "value": "L"}, {"name": "Wood Finish", "value": "Dark"}]},
    ]
    with pytest.raises(PriceValidationError):
        infer_wood_finish_deltas(variants)


def test_incomplete_wood_finish_pair_rejected():
    variants = [
        {"price": "100", "selectedOptions": [{"name": "Size", "value": "S"}, {"name": "Wood Finish", "value": "Natural"}]},
        {"price": "125", "selectedOptions": [{"name": "Size", "value": "S"}, {"name": "Wood Finish", "value": "Dark"}]},
        {"price": "200", "selectedOptions": [{"name": "Size", "value": "L"}, {"name": "Wood Finish", "value": "Natural"}]},
    ]
    with pytest.raises(PriceValidationError):
        infer_wood_finish_deltas(variants)
