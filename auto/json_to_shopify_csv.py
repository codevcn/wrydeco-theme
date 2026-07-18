"""Convert Amazon crawl JSON files into a Shopify product-import CSV.

Product mapping rules implemented by this script:
- Every object in ``color_swatches`` becomes one separate Shopify product.
- The product title comes from the top-level ``product.title`` field.
- Every finite ``customization_types`` object becomes a Shopify variant option.
- Its ``type`` becomes the option name and its ``options`` become option values.
- Customization options may be either legacy strings or crawl-schema objects
  containing ``value`` and ``increase_amount``.
- A variant price is the color swatch base price plus the ``increase_amount``
  of every selected customization option. Legacy bracketed surcharges remain
  supported for backwards compatibility.
- ``Product Category`` comes from the top-level ``product_category`` field.
- ``Product Type`` comes from the top-level ``product_type`` field.
- The vendor is always ``Wrydeco`` and the only product tag is ``source_amazon``.
- The ``wood_type`` metafield is populated from the swatch attribute whose key is
  ``material``.
- For any customization type whose lowercase name contains ``size``, the first
  option is discarded before Shopify variants are generated.
- SEO data comes from the top-level ``extra_fields`` object: ``seo_product_title``,
  ``page_title``, ``meta_description`` and ``url_slug``.
- Products are generated with ``Status=active`` and ``Published=true``.

Text-input customizations such as "Note to seller" are not valid Shopify
variant dimensions and are skipped. Shopify theme code or a line-item property
should be used for those inputs instead.

The generated CSV extends the supplied Shopify product export with the
``custom.rich_description`` product metafield.
"""

from __future__ import annotations

import argparse
import csv
import html
import itertools
import json
import random
import re
import sys
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Sequence


SHOPIFY_HEADERS: list[str] = [
    "Handle",
    "Title",
    "Body (HTML)",
    "Vendor",
    "Product Category",
    "Type",
    "Tags",
    "Published",
    "Option1 Name",
    "Option1 Value",
    "Option1 Linked To",
    "Option2 Name",
    "Option2 Value",
    "Option2 Linked To",
    "Option3 Name",
    "Option3 Value",
    "Option3 Linked To",
    "Variant SKU",
    "Variant Grams",
    "Variant Inventory Tracker",
    "Variant Inventory Qty",
    "Variant Inventory Policy",
    "Variant Fulfillment Service",
    "Variant Price",
    "Variant Compare At Price",
    "Variant Requires Shipping",
    "Variant Taxable",
    "Unit Price Total Measure",
    "Unit Price Total Measure Unit",
    "Unit Price Base Measure",
    "Unit Price Base Measure Unit",
    "Variant Barcode",
    "Image Src",
    "Image Position",
    "Image Alt Text",
    "Gift Card",
    "SEO Title",
    "SEO Description",
    "amazon_link (product.metafields.custom.amazon_link)",
    "Author Info (product.metafields.custom.author_info)",
    "Product Material (product.metafields.custom.product_material)",
    "SEO Product Title (product.metafields.custom.seo_product_title)",
    "Size Guide (product.metafields.custom.size_guide)",
    "Wood Type (product.metafields.custom.wood_type)",
    "Rich Description (product.metafields.custom.rich_description)",
    "Số lượt đánh giá sản phẩm (product.metafields.reviews.rating_count)",
    "Sản phẩm bổ sung (product.metafields.shopify--discovery--product_recommendation.complementary_products)",
    "Sản phẩm liên quan (product.metafields.shopify--discovery--product_recommendation.related_products)",
    "Cài đặt sản phẩm liên quan (product.metafields.shopify--discovery--product_recommendation.related_products_display)",
    "Đẩy mạnh tìm kiếm sản phẩm (product.metafields.shopify--discovery--product_search_boost.queries)",
    "Variant Image",
    "Variant Weight Unit",
    "Variant Tax Code",
    "Cost per item",
    "Status",
]

# Examples supported:
#   [+ $10,499.00]
#   [- $100]
#   [+$850.00]
#   [+ USD 125.50]
SURCHARGE_PATTERN = re.compile(
    r"\[\s*(?P<sign>[+-])\s*(?:(?P<currency>[A-Z]{3})\s*)?\$?\s*"
    r"(?P<amount>\d[\d,]*(?:\.\d+)?)\s*\]",
    flags=re.IGNORECASE,
)

TEXT_INPUT_MARKERS = {
    "text input",
    "text area",
    "textarea",
    "free text",
    "customer text",
}

AUTHOR_INFO_VALUES: tuple[str, ...] = (
    "gid://shopify/Metaobject/195647275065", # nhien-le
    "gid://shopify/Metaobject/194643296313", # alex-nguyen
    "gid://shopify/Metaobject/194643198009", # khoi-hoang
    "gid://shopify/Metaobject/195646947385", # nhan-pham
    "gid://shopify/Metaobject/194643165241", # lam-nguyen
    "gid://shopify/Metaobject/195647701049", # son-tran
)

# Add exact customization type names here to omit them from the Shopify CSV.
# Matching is case-insensitive and ignores surrounding/repeated whitespace.
IGNORE_CUSTOMIZATION_TYPE: list[str] = [
    "Note to seller (Optional)",
    "Add On-Site Installation"
]

PRODUCT_VENDOR = "Wrydeco"
PRODUCT_TAG = "source_amazon"
PRODUCT_IMAGE_LIMIT = 7


@dataclass(frozen=True)
class VariantValue:
    display_value: str
    raw_value: str
    surcharge: Decimal


@dataclass(frozen=True)
class VariantOption:
    name: str
    values: tuple[VariantValue, ...]


@dataclass
class Settings:
    vendor: str = ""
    product_category: str = ""
    product_type: str = ""
    tags: tuple[str, ...] = ("source_amazon",)
    published: bool = True
    status: str = "active"
    inventory_policy: str = "continue"
    fulfillment_service: str = "manual"
    requires_shipping: bool = True
    taxable: bool = True
    weight_unit: str = "kg"
    variant_grams: int = 0
    inventory_qty: int = 0
    sku_prefix: str = "AMZ"
    assign_first_image_to_variants: bool = True
    option_type_overrides: dict[str, str] | None = None
    include_option_types: tuple[str, ...] = ()
    exclude_option_types: tuple[str, ...] = ()
    extra_tags_from_attributes: bool = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert Amazon crawl JSON into Shopify's product CSV format."
    )
    parser.add_argument(
        "--input",
        default="data",
        help="A crawl JSON file or a directory containing crawl JSON files (default: data).",
    )
    parser.add_argument(
        "--output-dir",
        "--output",
        dest="output_dir",
        default="output",
        help=(
            "Directory where each CSV is written (default: output). "
            "Every CSV is named after its source JSON file, e.g. B0H6FGXKZ7.json "
            "-> B0H6FGXKZ7.csv."
        ),
    )
    parser.add_argument(
        "--config",
        default="configs/config.json",
        help="Optional config file containing a shopify_csv object.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Stop immediately when an input file is invalid; otherwise skip it with a warning.",
    )
    return parser.parse_args()


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def bool_csv(value: bool) -> str:
    return "true" if value else "false"


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return slug or "product"


def normalize_url_slug(value: Any) -> str:
    """Normalize ``extra_fields.url_slug`` into a Shopify Handle base.

    The crawl JSON should normally contain only the slug. For resilience, this
    also accepts a full URL or a value prefixed with ``products/``.
    """
    raw = clean_text(value)
    if not raw:
        return ""

    raw = re.sub(r"(?i)^https?://[^/]+/?", "", raw)
    raw = raw.split("?", 1)[0].split("#", 1)[0].strip("/")
    if raw.casefold().startswith("products/"):
        raw = raw[len("products/") :]
    return slugify(raw)


def parse_decimal(value: Any, *, field_name: str) -> Decimal:
    if value is None or value == "":
        raise ValueError(f"Missing numeric field: {field_name}")
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, AttributeError) as exc:
        raise ValueError(f"Invalid decimal for {field_name}: {value!r}") from exc


def money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"


def extract_surcharge(raw_option: str) -> Decimal:
    total = Decimal("0")
    for match in SURCHARGE_PATTERN.finditer(raw_option):
        amount = Decimal(match.group("amount").replace(",", ""))
        if match.group("sign") == "-":
            amount = -amount
        total += amount
    return total


def strip_surcharge(raw_option: str) -> str:
    value = SURCHARGE_PATTERN.sub("", raw_option)
    return clean_text(value)


def customization_type_name(customization: dict[str, Any]) -> str:
    """Return the crawl customization type name across schema revisions."""
    return clean_text(customization.get("type") or customization.get("name"))


def customization_option_value(option: Any) -> str:
    """Extract the visible option label from a crawl option object or legacy string."""
    if isinstance(option, dict):
        return clean_text(
            option.get("value")
            or option.get("label")
            or option.get("name")
            or option.get("id")
        )
    return clean_text(option)


def parse_increase_amount(value: Any, *, field_name: str) -> Decimal:
    """Parse a crawl ``increase_amount`` as a direct currency-unit amount.

    Examples: 10499 -> 10499.00, "$850.00" -> 850.00. The crawl JSON stores
    these values in USD units, not cents, so no division by 100 is performed.
    """
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, bool):
        raise ValueError(f"Invalid surcharge for {field_name}: {value!r}")
    if isinstance(value, (int, float, Decimal)):
        return parse_decimal(value, field_name=field_name)

    raw = clean_text(value)
    normalized = re.sub(r"(?i)\bUSD\b", "", raw)
    normalized = (
        normalized.replace("$", "")
        .replace(",", "")
        .replace("[", "")
        .replace("]", "")
        .strip()
    )
    return parse_decimal(normalized, field_name=field_name)


def is_text_input_customization(customization: dict[str, Any]) -> bool:
    options = customization.get("options") or []
    normalized_options = {
        customization_option_value(option).casefold()
        for option in options
        if customization_option_value(option)
    }
    type_name = customization_type_name(customization).casefold()

    if normalized_options and normalized_options.issubset(TEXT_INPUT_MARKERS):
        return True

    # A note/custom-text field with no finite values cannot become a Shopify variant option.
    text_type_markers = ("note to seller", "text input", "free text", "customer note")
    return any(marker in type_name for marker in text_type_markers)


def get_attribute_value(attributes: dict[str, Any], *keys: str) -> str:
    by_key = attributes.get("by_key") or {}
    for key in keys:
        value = by_key.get(key)
        if isinstance(value, dict):
            candidate = value.get("value") or value.get("raw_value")
        else:
            candidate = value
        if clean_text(candidate):
            return clean_text(candidate)

    for item in attributes.get("items") or []:
        if clean_text(item.get("key")) in keys:
            return clean_text(item.get("value") or item.get("raw_value"))
    return ""


def load_settings(config_path: Path) -> Settings:
    if not config_path.exists():
        return Settings(option_type_overrides={})

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read config file {config_path}: {exc}") from exc

    raw = config.get("shopify_csv") or {}
    tags = raw.get("tags", ["source_amazon"])
    if isinstance(tags, str):
        tags = [part.strip() for part in tags.split(",") if part.strip()]

    return Settings(
        vendor=clean_text(raw.get("vendor")),
        product_category=clean_text(raw.get("product_category")),
        product_type=clean_text(raw.get("type", "")),
        tags=tuple(clean_text(tag) for tag in tags if clean_text(tag)),
        published=bool(raw.get("published", True)),
        status=clean_text(raw.get("status", "active")) or "active",
        inventory_policy=clean_text(raw.get("inventory_policy", "continue")) or "continue",
        fulfillment_service=clean_text(raw.get("fulfillment_service", "manual")) or "manual",
        requires_shipping=bool(raw.get("requires_shipping", True)),
        taxable=bool(raw.get("taxable", True)),
        weight_unit=clean_text(raw.get("weight_unit", "kg")) or "kg",
        variant_grams=int(raw.get("variant_grams", 0)),
        inventory_qty=int(raw.get("inventory_qty", 0)),
        sku_prefix=clean_text(raw.get("sku_prefix", "AMZ")) or "AMZ",
        assign_first_image_to_variants=bool(
            raw.get("assign_first_image_to_variants", True)
        ),
        option_type_overrides={
            clean_text(key).casefold(): clean_text(value)
            for key, value in (raw.get("option_type_overrides") or {}).items()
            if clean_text(key) and clean_text(value)
        },
        include_option_types=tuple(
            clean_text(value).casefold()
            for value in raw.get("include_option_types", [])
            if clean_text(value)
        ),
        exclude_option_types=tuple(
            clean_text(value).casefold()
            for value in raw.get("exclude_option_types", [])
            if clean_text(value)
        ),
        extra_tags_from_attributes=bool(raw.get("extra_tags_from_attributes", False)),
    )


def discover_json_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    if not input_path.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    files: list[Path] = []
    for path in sorted(input_path.rglob("*.json")):
        lower_name = path.name.casefold()
        if ".backup-" in lower_name or lower_name in {"config.json", "package.json"}:
            continue
        files.append(path)
    return files


def load_crawl_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read JSON {path}: {exc}") from exc

    if not isinstance(data.get("product"), dict):
        raise ValueError(f"{path} is not a crawl result: missing product object")
    if not isinstance(data.get("color_swatches"), list):
        raise ValueError(f"{path} is not a crawl result: missing color_swatches array")
    return data


def build_body_html(product: dict[str, Any]) -> str:
    """Return Shopify Body HTML from ``product.about_this_item``.

    The post-crawl workflow stores the rewritten description as one HTML string.
    Older crawl files store ``about_this_item`` as a list of plain-text bullets.
    Both forms are supported without iterating over individual string characters.
    """
    description = product.get("about_this_item")

    if isinstance(description, str):
        return description.strip()

    if isinstance(description, list):
        bullets = [clean_text(item) for item in description]
        bullets = [item for item in bullets if item]
        if not bullets:
            return ""
        list_items = "".join(f"<li>{html.escape(item)}</li>" for item in bullets)
        return f"<ul>{list_items}</ul>"

    return ""


def build_seo_description(product: dict[str, Any], title: str) -> str:
    """Build a safe fallback SEO description for legacy JSON files.

    Normal JSON files should provide ``extra_fields.meta_description``. This
    fallback supports both the legacy list format and the new HTML-string format.
    """
    description = product.get("about_this_item")

    if isinstance(description, list):
        bullets = [clean_text(item) for item in description]
        candidate = next((item for item in bullets if item), title)
        return candidate[:320].rstrip()

    if isinstance(description, str):
        plain_text = re.sub(r"<[^>]+>", " ", description)
        plain_text = clean_text(html.unescape(plain_text))
        return (plain_text or title)[:320].rstrip()

    return title[:320].rstrip()


def build_rich_description(data: dict[str, Any]) -> str:
    """Build the rich description from A+ Content image ``source_url`` values."""
    aplus_images = (
        data.get("assets", {})
        .get("aplus_content", {})
        .get("images", [])
    )

    image_tags: list[str] = []
    for image in aplus_images:
        if not isinstance(image, dict):
            continue
        source_url = clean_text(image.get("source_url"))
        if not source_url:
            continue
        image_tags.append(
            f'<img src="{html.escape(source_url, quote=True)}">'
        )

    return f'<div class="description-root">{"".join(image_tags)}</div>'


def collect_image_records(data: dict[str, Any], title: str) -> list[dict[str, str]]:
    """Collect at most seven gallery images using only each image's source_url."""
    gallery = (
        data.get("assets", {})
        .get("product_media_gallery", {})
        .get("images", [])
    )
    records: list[dict[str, str]] = []
    seen: set[str] = set()

    sorted_gallery = sorted(
        (item for item in gallery if isinstance(item, dict)),
        key=lambda item: int(item.get("index") or 0),
    )
    for item in sorted_gallery:
        url = clean_text(item.get("source_url"))
        if not url or url in seen:
            continue
        seen.add(url)
        records.append(
            {
                "url": url,
                "alt": clean_text(item.get("alt_text")) or title,
            }
        )
        if len(records) == PRODUCT_IMAGE_LIMIT:
            break
    return records


def option_type_is_included(type_name: str, settings: Settings) -> bool:
    folded = type_name.casefold()
    if settings.include_option_types and folded not in settings.include_option_types:
        return False
    if folded in settings.exclude_option_types:
        return False
    return True


def customization_type_is_ignored(type_name: str) -> bool:
    """Return True when a type matches IGNORE_CUSTOMIZATION_TYPE."""
    normalized_name = clean_text(type_name).casefold()
    ignored_names = {
        clean_text(ignored_name).casefold()
        for ignored_name in IGNORE_CUSTOMIZATION_TYPE
        if clean_text(ignored_name)
    }
    return normalized_name in ignored_names


def build_variant_options(
    swatch: dict[str, Any], settings: Settings
) -> tuple[list[VariantOption], list[str]]:
    variant_options: list[VariantOption] = []
    warnings: list[str] = []

    for customization_index, customization in enumerate(
        swatch.get("customization_types") or [], start=1
    ):
        if not isinstance(customization, dict):
            warnings.append(
                f"Skipped customization #{customization_index}: expected an object"
            )
            continue

        raw_name = customization_type_name(customization)
        if not raw_name:
            warnings.append("Skipped a customization type with no name")
            continue
        if customization_type_is_ignored(raw_name):
            warnings.append(
                f"Ignored customization type from IGNORE_CUSTOMIZATION_TYPE: {raw_name}"
            )
            continue
        if not option_type_is_included(raw_name, settings):
            warnings.append(f"Excluded customization type: {raw_name}")
            continue
        if is_text_input_customization(customization):
            warnings.append(
                f"Skipped text-input customization '{raw_name}'; use a line-item property in the Shopify theme"
            )
            continue

        option_name = (settings.option_type_overrides or {}).get(
            raw_name.casefold(), raw_name
        )
        values: list[VariantValue] = []
        seen_values: set[str] = set()

        indexed_options = list(enumerate(customization.get("options") or [], start=1))
        if "size" in raw_name.casefold() and indexed_options:
            removed_index, removed_option = indexed_options.pop(0)
            removed_label = customization_option_value(removed_option) or f"#{removed_index}"
            warnings.append(
                f"Removed first size option '{removed_label}' from '{raw_name}'"
            )

        for option_index, raw_option in indexed_options:
            if isinstance(raw_option, dict):
                if raw_option.get("available") is False or raw_option.get("disabled") is True:
                    option_label = customization_option_value(raw_option) or f"#{option_index}"
                    warnings.append(
                        f"Skipped unavailable option '{option_label}' in '{raw_name}'"
                    )
                    continue

                raw_value = customization_option_value(raw_option)
                display_value = strip_surcharge(raw_value)
                increase_amount = raw_option.get("increase_amount")
                if increase_amount is None or increase_amount == "":
                    # Some older crawl files embed the surcharge in the visible label.
                    surcharge = extract_surcharge(raw_value)
                else:
                    surcharge = parse_increase_amount(
                        increase_amount,
                        field_name=(
                            f"customization_types[{customization_index}]."
                            f"options[{option_index}].increase_amount"
                        ),
                    )
            else:
                # Backwards compatibility with the original string-option schema.
                raw_value = clean_text(raw_option)
                display_value = strip_surcharge(raw_value)
                surcharge = extract_surcharge(raw_value)

            if not display_value:
                warnings.append(
                    f"Skipped an empty option value in customization '{raw_name}'"
                )
                continue

            folded_value = display_value.casefold()
            if folded_value in seen_values:
                warnings.append(
                    f"Skipped duplicate option value '{display_value}' in '{raw_name}'"
                )
                continue
            seen_values.add(folded_value)
            values.append(
                VariantValue(
                    display_value=display_value,
                    raw_value=raw_value,
                    surcharge=surcharge,
                )
            )

        if values:
            variant_options.append(
                VariantOption(name=option_name, values=tuple(values))
            )
        else:
            warnings.append(
                f"Skipped customization '{raw_name}' because it has no usable finite options"
            )

    if len(variant_options) > 3:
        names = ", ".join(option.name for option in variant_options)
        raise ValueError(
            "Shopify CSV supports only Option1, Option2 and Option3, but this "
            f"product has {len(variant_options)} finite customization types: {names}. "
            "Use shopify_csv.include_option_types or exclude_option_types in configs/config.json."
        )

    return variant_options, warnings


def build_tags(
    data: dict[str, Any], swatch: dict[str, Any], settings: Settings
) -> str:
    """Return the single fixed product tag required for Amazon-source products."""
    del data, swatch, settings
    return PRODUCT_TAG


def choose_author_info() -> str:
    return random.choice(AUTHOR_INFO_VALUES)


def resolve_product_type(data: dict[str, Any], settings: Settings) -> str:
    """Return Product Type only from the JSON top-level product_type field."""
    del settings
    return clean_text(data.get("product_type"))


def resolve_product_category(data: dict[str, Any]) -> str:
    """Return Shopify Product Category from the crawl JSON top-level field."""
    return clean_text(data.get("product_category"))


def empty_row() -> dict[str, str]:
    return {header: "" for header in SHOPIFY_HEADERS}


def build_product_rows(
    data: dict[str, Any],
    swatch: dict[str, Any],
    settings: Settings,
    *,
    append_asin_to_handle: bool,
) -> tuple[list[dict[str, str]], list[str]]:
    product = data["product"]
    title = clean_text(product.get("title"))
    if not title:
        raise ValueError("product.title is empty")

    asin = clean_text(swatch.get("asin") or data.get("asin"))
    if not asin:
        raise ValueError(f"Product '{title}' has no ASIN")

    extra_fields_raw = data.get("extra_fields")
    extra_fields = extra_fields_raw if isinstance(extra_fields_raw, dict) else {}
    seo_product_title = clean_text(extra_fields.get("seo_product_title"))
    page_title = clean_text(extra_fields.get("page_title"))
    meta_description = clean_text(extra_fields.get("meta_description"))
    url_slug = clean_text(extra_fields.get("url_slug"))

    # Use extra_fields.url_slug as the Shopify Handle. When one JSON contains
    # multiple color swatches, each swatch becomes a separate product, so append
    # its ASIN to prevent Shopify from merging those rows into one product.
    handle_base = normalize_url_slug(url_slug) or slugify(title)
    handle = (
        f"{handle_base}-{slugify(asin)}"
        if append_asin_to_handle
        else handle_base
    )
    base_price = parse_decimal(
        (swatch.get("base_price") or {}).get("amount"),
        field_name=f"color_swatches[{asin}].base_price.amount",
    )
    currency = clean_text((swatch.get("base_price") or {}).get("currency"))
    if currency and currency.upper() != "USD":
        raise ValueError(
            f"Product {asin} uses currency {currency!r}; expected USD before Shopify import"
        )

    attributes = swatch.get("product_attributes") or product.get(
        "product_attributes", {}
    )
    vendor = PRODUCT_VENDOR
    material = get_attribute_value(attributes, "material", "product_material")
    # WRYDECO rule: the wood_type metafield uses the swatch attribute whose key
    # is exactly "material"; do not read the old "wood_type" attribute here.
    wood_type = get_attribute_value(attributes, "material")

    variant_options, warnings = build_variant_options(swatch, settings)

    if not isinstance(extra_fields_raw, dict):
        warnings.append("Top-level extra_fields is missing or is not an object")
    if not seo_product_title:
        warnings.append("extra_fields.seo_product_title is empty; product.title will be used")
    if not page_title:
        warnings.append("extra_fields.page_title is empty; product.title will be used")
    elif not 50 <= len(page_title) <= 60:
        warnings.append(
            f"extra_fields.page_title has {len(page_title)} characters; expected 50-60"
        )
    if not meta_description:
        warnings.append(
            "extra_fields.meta_description is empty; the legacy generated SEO description will be used"
        )
    elif not 150 <= len(meta_description) <= 160:
        warnings.append(
            f"extra_fields.meta_description has {len(meta_description)} characters; expected 150-160"
        )
    if not url_slug:
        warnings.append("extra_fields.url_slug is empty; product.title will be used for the Handle")
    elif not 50 <= len(normalize_url_slug(url_slug)) <= 60:
        warnings.append(
            f"extra_fields.url_slug has {len(normalize_url_slug(url_slug))} normalized characters; expected 50-60"
        )

    if variant_options:
        combinations: Iterable[tuple[VariantValue, ...]] = itertools.product(
            *(option.values for option in variant_options)
        )
    else:
        combinations = [tuple()]

    images = collect_image_records(data, title)
    first_image_url = images[0]["url"] if images else ""
    body_html = build_body_html(product)
    fallback_seo_description = build_seo_description(product, title)
    effective_seo_product_title = seo_product_title or title
    effective_page_title = page_title or title
    effective_meta_description = meta_description or fallback_seo_description
    rich_description = build_rich_description(data)
    amazon_url = clean_text(swatch.get("product_url") or data.get("source_url"))
    tags = build_tags(data, swatch, settings)
    product_category = resolve_product_category(data)
    shopify_product_type = resolve_product_type(data, settings)
    author_info = choose_author_info()

    if not product_category:
        warnings.append("Top-level product_category is empty; Shopify Product Category will be blank")
    if not shopify_product_type:
        warnings.append("Top-level product_type is empty; Shopify Product Type will be blank")
    if len(images) < PRODUCT_IMAGE_LIMIT:
        warnings.append(
            f"Only {len(images)} valid gallery source_url images were found; expected {PRODUCT_IMAGE_LIMIT}"
        )

    rows: list[dict[str, str]] = []
    for variant_index, combination in enumerate(combinations, start=1):
        row = empty_row()
        row["Handle"] = handle

        if variant_index == 1:
            row.update(
                {
                    "Title": title,
                    "Body (HTML)": body_html,
                    "Vendor": vendor,
                    "Product Category": product_category,
                    "Type": shopify_product_type,
                    "Tags": tags,
                    "Published": "true",
                    "Gift Card": "false",
                    "SEO Title": effective_page_title,
                    "SEO Description": effective_meta_description,
                    "amazon_link (product.metafields.custom.amazon_link)": amazon_url,
                    "Author Info (product.metafields.custom.author_info)": author_info,
                    "Product Material (product.metafields.custom.product_material)": material,
                    "SEO Product Title (product.metafields.custom.seo_product_title)": effective_seo_product_title,
                    "Wood Type (product.metafields.custom.wood_type)": wood_type,
                    "Rich Description (product.metafields.custom.rich_description)": rich_description,
                    "Status": "active",
                }
            )

        if variant_options:
            for option_index, (option, selected_value) in enumerate(
                zip(variant_options, combination), start=1
            ):
                if variant_index == 1:
                    row[f"Option{option_index} Name"] = option.name
                row[f"Option{option_index} Value"] = selected_value.display_value
        else:
            if variant_index == 1:
                row["Option1 Name"] = "Title"
            row["Option1 Value"] = "Default Title"

        surcharge_total = sum(
            (selected.surcharge for selected in combination), Decimal("0")
        )
        variant_price = base_price + surcharge_total
        if variant_price < 0:
            raise ValueError(
                f"Calculated a negative price for {asin}, variant {variant_index}"
            )

        row.update(
            {
                "Variant SKU": f"{settings.sku_prefix}-{asin}-{variant_index:03d}",
                "Variant Grams": str(settings.variant_grams),
                "Variant Inventory Tracker": "",
                "Variant Inventory Qty": str(settings.inventory_qty),
                "Variant Inventory Policy": settings.inventory_policy,
                "Variant Fulfillment Service": settings.fulfillment_service,
                "Variant Price": money(variant_price),
                "Variant Requires Shipping": bool_csv(settings.requires_shipping),
                "Variant Taxable": bool_csv(settings.taxable),
                "Variant Image": (
                    first_image_url
                    if settings.assign_first_image_to_variants
                    else ""
                ),
                "Variant Weight Unit": settings.weight_unit,
            }
        )

        # Shopify permits product image fields on variant rows. Attach images in
        # their original order, then append image-only rows if images outnumber variants.
        if variant_index <= len(images):
            image = images[variant_index - 1]
            row["Image Src"] = image["url"]
            row["Image Position"] = str(variant_index)
            row["Image Alt Text"] = image["alt"]

        rows.append(row)

    # Add remaining images as image-only rows while retaining the same Handle.
    for image_position in range(len(rows) + 1, len(images) + 1):
        image = images[image_position - 1]
        row = empty_row()
        row["Handle"] = handle
        row["Image Src"] = image["url"]
        row["Image Position"] = str(image_position)
        row["Image Alt Text"] = image["alt"]
        rows.append(row)

    return rows, warnings


def convert_file(
    json_path: Path, settings: Settings, strict: bool
) -> tuple[list[dict[str, str]], list[str], int]:
    """Convert one crawl JSON file into its Shopify CSV rows.

    Every JSON file is converted independently so that each one produces a
    separate CSV named after the source file.
    """
    all_rows: list[dict[str, str]] = []
    warnings: list[str] = []
    product_count = 0
    handles_seen: set[str] = set()

    try:
        data = load_crawl_json(json_path)
        swatches = data.get("color_swatches") or []
        if not swatches:
            # A crawl without swatches is still treated as one product.
            swatches = [
                {
                    "name": "Default",
                    "asin": data.get("asin"),
                    "product_url": data.get("source_url"),
                    "base_price": data.get("product", {}).get("base_price", {}),
                    "product_attributes": data.get("product", {}).get(
                        "product_attributes", {}
                    ),
                    "customization_types": [],
                }
            ]

        for swatch in swatches:
            product_rows, product_warnings = build_product_rows(
                data,
                swatch,
                settings,
                append_asin_to_handle=len(swatches) > 1,
            )
            handle = product_rows[0]["Handle"]
            if handle in handles_seen:
                raise ValueError(
                    f"Duplicate Shopify handle generated: {handle}. Check duplicate ASINs."
                )
            handles_seen.add(handle)
            all_rows.extend(product_rows)
            product_count += 1
            for warning in product_warnings:
                warnings.append(
                    f"{json_path.name} / {swatch.get('asin') or swatch.get('name')}: {warning}"
                )
    except Exception as exc:  # noqa: BLE001 - CLI should report per-file failures.
        message = f"Skipped {json_path}: {exc}"
        if strict:
            raise RuntimeError(message) from exc
        warnings.append(message)

    return all_rows, warnings, product_count


def write_csv(output_path: Path, rows: Sequence[dict[str, str]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # UTF-8 BOM makes the Vietnamese metafield headers open correctly in Excel
    # and remains accepted by Shopify's CSV importer.
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=SHOPIFY_HEADERS,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    config_path = Path(args.config).expanduser().resolve()

    warnings: list[str] = []
    written: list[tuple[Path, int, int, int]] = []

    try:
        settings = load_settings(config_path)
        json_files = discover_json_files(input_path)
        if not json_files:
            raise FileNotFoundError(f"No JSON files found under {input_path}")

        for json_path in json_files:
            rows, file_warnings, product_count = convert_file(
                json_path, settings, strict=args.strict
            )
            warnings.extend(file_warnings)
            if not rows:
                warnings.append(f"{json_path.name}: no Shopify rows were generated")
                continue

            # The output CSV is named after its source JSON file.
            output_path = output_dir / f"{json_path.stem}.csv"
            write_csv(output_path, rows)
            variant_count = sum(1 for row in rows if row.get("Variant Price"))
            image_count = sum(1 for row in rows if row.get("Image Src"))
            written.append((output_path, product_count, variant_count, image_count))

        if not written:
            raise RuntimeError("No Shopify product rows were generated")
    except Exception as exc:  # noqa: BLE001 - top-level CLI error reporting.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for output_path, product_count, variant_count, image_count in written:
        print(
            f"Created: {output_path} "
            f"(products={product_count}, variants={variant_count}, images={image_count})"
        )
    print(f"Files written: {len(written)}")
    print("Publishing: Status=active, Online Store Published=true")
    print(f"Vendor: {PRODUCT_VENDOR}; Tags: {PRODUCT_TAG}; Gallery image limit: {PRODUCT_IMAGE_LIMIT}")
    print(
        "Shopify Inbox: keep 'Publish new products to all sales channels' "
        "selected in the Shopify import dialog"
    )
    if warnings:
        print(f"Warnings: {len(warnings)}", file=sys.stderr)
        for warning in warnings:
            print(f"- {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
