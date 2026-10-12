from copy import deepcopy

import pytest

from scraper.errors import PriceValidationError
from scraper.pipeline import _build_final_variants
from scraper.variant_options import clean_pricing_options


def pricing_for(*values):
    return {
        "base_price": "100.00", "verified_all": True,
        "option_types": [{"name": "Select size", "options": [
            {"value": value, "dom_index": index, "group_index": 2}
            for index, (value, _) in enumerate(values)
        ]}],
        "variants": [{
            "options": [{"name": "Select size", "value": value}],
            "selection": [{"value": value, "dom_index": index, "group_index": 2}],
            "additional_price": "0.00", "verified_total": price,
        } for index, (value, price) in enumerate(values)],
    }


@pytest.mark.parametrize("suffix", ["(Popular size)", "(Best size)", "(Best for office)",
                                    "- Recommended", "[BEST SELLING]", "(Most Popular Size)"])
def test_crawled_values_cleaned_without_changing_prices_or_dom_identity(suffix):
    raw_value = f"47''Wx 30''H x 16''D {suffix}"
    source = pricing_for((raw_value, "350.00"))
    original = deepcopy(source)
    result = clean_pricing_options(source)
    assert source == original
    variant = result["variants"][0]
    assert variant["options"][0]["value"] == "47''Wx 30''H x 16''D"
    assert variant["options"][0]["source_value"] == raw_value
    assert variant["selection"][0] == {
        "value": "47''Wx 30''H x 16''D", "source_value": raw_value,
        "dom_index": 0, "group_index": 2,
    }
    assert variant["verified_total"] == "350.00"
    assert result["option_types"][0]["options"][0]["value"] == variant["options"][0]["value"]
    assert clean_pricing_options(result) == result


def test_same_cleaned_combination_same_price_merges_and_retains_evidence():
    result = clean_pricing_options(pricing_for(("Walnut (Popular)", "100"), ("Walnut", "100.00")))
    assert len(result["variants"]) == len(result["option_types"][0]["options"]) == 1
    variant = result["variants"][0]
    assert variant["options"][0]["value"] == "Walnut"
    assert [row["selection"][0]["dom_index"] for row in variant["merged_sources"]] == [0, 1]
    assert len(result["option_types"][0]["options"][0]["source_options"]) == 2


def test_different_prices_after_cleanup_fail_closed():
    with pytest.raises(PriceValidationError, match="different prices"):
        clean_pricing_options(pricing_for(("Walnut (Popular)", "100"), ("Walnut", "125")))


def test_empty_value_after_cleanup_fails_closed():
    with pytest.raises(PriceValidationError, match="no value"):
        clean_pricing_options(pricing_for(("Recommended", "100")))


def test_real_attributes_and_substrings_are_not_marketing():
    value = "Popularis Custom size - No, I will assemble it myself"
    assert clean_pricing_options(pricing_for((value, "100")))["variants"][0]["options"][0]["value"] == value


def test_cached_pricing_is_cleaned_before_shopify_payload():
    _, variants, _ = _build_final_variants(pricing_for(("59''Wx 30''H x 16''D (Best size)", "725")), {})
    assert variants[0]["options"][0]["value"] == "59''Wx 30''H x 16''D"
    assert str(variants[0]["price"]) == "725.00"


def test_cached_collision_with_different_prices_is_rejected():
    with pytest.raises(PriceValidationError, match="different prices"):
        _build_final_variants(pricing_for(("Custom size (Recommended)", "100"), ("Custom size", "125")), {})
