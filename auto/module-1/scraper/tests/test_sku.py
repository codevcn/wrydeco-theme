from copy import deepcopy

import pytest

from scraper.errors import ShopifyError
from scraper.sku import build_sku_plan, clean_option, finish_code, load_rules, size_code
from scraper.sku_service import verify_and_repair


def variant(size='65"W x 60"H x 10"D', finish="Natural"):
    return {"options": [{"name": "Choose Size", "value": size},
                        {"name": "Wood Finish", "value": finish}]}


def plan(rows, **kwargs):
    return build_sku_plan(rows, tags=["source_amazon", "scraper_tool"],
                          asin="B0HB4TTLJY", handle="organic-fluid-console", **kwargs)


@pytest.mark.parametrize("label,code", [
    ('65"Wx65"Hx7"D - Recommended', 'W65H65D7'),
    ("30''W x 30''H x 22''D (Best Selling)", 'W30H30D22'),
    ("16'' x 12''", '16X12'), ('W72 x H38 x D15', 'W72H38D15'),
    ('14"H x 12"W - Most Popular', 'H14W12'),
    ("47''Wx 30''H x 16''D (Popular size)", 'W47H30D16'),
    ("59''Wx 30''H x 16''D (Best size)", 'W59H30D16'),
    ("71''Wx 30''H x 16''D (Best for office)", 'W71H30D16'),
    ('10.5"W x 10-12"D', 'W10P5D10T12'),
    ('65cm W x 60cm H', 'W65H60CM'), ('Custom Larger Size', 'CUST'),
])
def test_sizes_are_parsed_without_guessing_units(label, code):
    assert size_code(label) == code


@pytest.mark.parametrize("label,code", [
    ("Natural (Recommended)", "NAT"), ("Dark Warm Wood - best-selling", "DK-WARM"),
    ("Cool Dark Wood", "CD-WOOD"), ("Walnut [Most Popular]", "WAL"),
    ("Champagne Oak", "CHA-OA"), ("Mystic", "MYS"), ("Red", "RD"),
    ("Same as Main Image Color", "IMG"),
])
def test_finishes_are_always_abbreviated(label, code):
    assert finish_code(label) == code
    assert len(code) <= 7


def test_marketing_cleanup_has_word_boundaries_and_keeps_source():
    row = variant('65"W - best-selling', 'Popularis Walnut')
    before = deepcopy(row)
    result = plan([row])
    assert row == before
    assert clean_option("Popularis Walnut") == "Popularis Walnut"
    assert result["variants"][0]["components"][0]["cleaned"] == '65"W'
    assert clean_option('47"W (Most Popular Size)') == '47"W'
    assert clean_option('Walnut (Highly Recommended Finish)') == 'Walnut'
    assert clean_option('Yes, It will be a bit LARGER (no more than 5")') == 'Yes, It will be a bit LARGER (no more than 5")'


def test_size_with_mixed_units_is_not_silently_converted():
    with pytest.raises(ShopifyError, match="mixes units"):
        size_code('65"W x 60cm H')


def test_prefix_comes_from_tags_and_registry_is_extensible():
    rows = [variant()]
    assert plan(rows)["prefix"] == "amz"
    rules = load_rules()
    rules["prefix_rules"].insert(0, {"tag_contains": "etsy", "prefix": "etsy", "identity": "handle"})
    for tags, prefix in [([], "wry"), (["AMAZON_import"], "amz"), (["source_etsy"], "etsy")]:
        result = build_sku_plan(rows, tags=tags, asin="B0HB4TTLJY", handle="organic-fluid-console", rules=rules)
        assert result["prefix"] == prefix


def test_collision_is_regenerated_and_case_insensitive():
    rows = [variant()]
    first = plan(rows)["variants"][0]["sku"]
    second = plan(rows, occupied=[first.upper()])["variants"][0]
    assert second["sku"] != first
    assert second["sku"].endswith("-02")
    assert second["collisions_resolved"] == 1


def test_same_dimensions_with_extra_options_remain_unique():
    rows = [variant(), variant()]
    rows[0]["options"].append({"name": "Installation", "value": "No, I will install it myself"})
    rows[1]["options"].append({"name": "Installation", "value": "Yes, I need on-site installation"})
    codes = [row["sku"] for row in plan(rows)["variants"]]
    assert len(set(codes)) == 2


def test_retry_and_reordering_preserve_skus_and_long_codes_are_bounded():
    rows = [variant('89"W x 80"H x 10-12"D', "Cool Dark Wood"), variant('Custom Larger Size', "Champagne Oak")]
    first = plan(rows)
    reordered = plan(list(reversed(rows)), previous=first)
    assert [r["sku"] for r in reordered["variants"]] == list(reversed([r["sku"] for r in first["variants"]]))
    assert all(r["preserved"] for r in reordered["variants"])
    assert all(len(r["sku"]) <= 40 for r in first["variants"])


def test_more_than_99_variants_and_duplicate_existing_skus():
    rows = [variant(f'{index}"W', "Natural") for index in range(1, 102)]
    first = plan(rows)
    assert first["variants"][-1]["sku"].endswith("-101")
    assert len({r["sku"] for r in first["variants"]}) == 101
    existing = [{"selectedOptions": row["options"], "sku": first["variants"][0]["sku"]} for row in rows]
    assert len({r["sku"] for r in plan(rows, existing=existing)["variants"]}) == 101


def test_empty_marketing_only_value_fails_closed():
    with pytest.raises(ShopifyError, match="no factual value"):
        plan([variant("Recommended")])


class FakeSkuClient:
    def __init__(self, rows, codes=None):
        self.live = [{"id": str(i), "selectedOptions": row["options"], "sku": (codes or {}).get(i, "")}
                     for i, row in enumerate(rows)]
        self.owners = {}
        self.updates = []

    def read_variants(self, _):
        return deepcopy(self.live)

    def variant_sku_owners(self, *args):
        return self.owners

    def update_variant_skus(self, _, updates):
        self.updates.append(updates)
        for row in self.live:
            row["sku"] = next((u["sku"] for u in updates if u["id"] == row["id"]), row["sku"])


def verify(client, result, saved):
    return verify_and_repair(client, "123", result, tags=["source_amazon"], asin="B0HB4TTLJY",
                              handle="organic-fluid-console", save=lambda p: saved.append(p))


def test_read_after_write_repairs_external_collision_and_is_idempotent():
    rows = [variant()]
    result = plan(rows)
    client = FakeSkuClient(rows)
    client.owners = {result["variants"][0]["sku"].casefold(): ["other-variant"]}
    saved = []
    verified = verify(client, result, saved)
    assert verified["verified"] and verified["plan"]["variants"][0]["sku"].endswith("-02")
    assert saved and len(client.updates) == 1
    verify(client, verified["plan"], saved)
    assert len(client.updates) == 1


def test_verification_does_not_assign_skus_by_list_position():
    client = FakeSkuClient([variant('70"W')])
    with pytest.raises(ShopifyError, match="differ from"):
        verify(client, plan([variant()]), [])


def test_verification_rejects_a_shopify_write_that_was_not_persisted():
    client = FakeSkuClient([variant()])
    client.update_variant_skus = lambda *_: None
    with pytest.raises(ShopifyError, match="did not converge"):
        verify(client, plan([variant()]), [])
