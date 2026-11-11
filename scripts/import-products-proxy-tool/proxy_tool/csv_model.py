from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path


PRODUCT_META_RE = re.compile(
    r"\(product\.metafields\.([^.()]+)\.([^)]+)\)",
    re.IGNORECASE,
)

VARIANT_META_RE = re.compile(
    r"\(variant\.metafields\.([^.()]+)\.([^)]+)\)",
    re.IGNORECASE,
)

SKU_RE = re.compile(
    r"^(AMZ|WRY)-.+-\d{2}$",
    re.IGNORECASE,
)


ALIASES = {
    "handle": ["Handle", "URL handle"],
    "title": ["Title"],
    "body": ["Body (HTML)", "Description"],
    "vendor": ["Vendor"],
    "category": ["Product Category", "Product category"],
    "type": ["Type"],
    "tags": ["Tags"],
    "published": [
        "Published",
        "Published on online store",
    ],
    "status": ["Status"],
    "seo_title": ["SEO Title", "SEO title"],
    "seo_description": [
        "SEO Description",
        "SEO description",
    ],
    "sku": ["Variant SKU", "SKU"],
    "grams": [
        "Variant Grams",
        "Weight value (grams)",
    ],
    "price": ["Variant Price", "Price"],
    "compare_price": [
        "Variant Compare At Price",
        "Compare-at price",
    ],
    "inventory_tracker": [
        "Variant Inventory Tracker",
        "Inventory tracker",
    ],
    "inventory_qty": [
        "Variant Inventory Qty",
        "Inventory quantity",
    ],
    "inventory_policy": [
        "Variant Inventory Policy",
        "Continue selling when out of stock",
    ],
    "fulfillment": [
        "Variant Fulfillment Service",
        "Fulfillment service",
    ],
    "requires_shipping": [
        "Variant Requires Shipping",
        "Requires shipping",
    ],
    "taxable": [
        "Variant Taxable",
        "Charge tax",
    ],
    "barcode": [
        "Variant Barcode",
        "Barcode",
        "Barcodes",
    ],
    "cost": ["Cost per item"],
    "image_src": ["Image Src", "Image URL"],
    "image_position": [
        "Image Position",
        "Image position",
    ],
    "image_alt": [
        "Image Alt Text",
        "Image alt text",
    ],
    "variant_image": [
        "Variant Image",
        "Variant image URL",
    ],
    "packed_length": [
        "Variant Packed Length",
        "Variant packed length",
    ],
    "packed_width": [
        "Variant Packed Width",
        "Variant packed width",
    ],
    "packed_height": [
        "Variant Packed Height",
        "Variant packed height",
    ],
}


def pick(row: dict[str, str], key: str) -> str:
    for column in ALIASES[key]:
        value = (row.get(column) or "").strip()

        if value:
            return value

    return ""


def first_nonblank(
    rows: list[dict[str, str]],
    key: str,
) -> str:
    for row in rows:
        value = pick(row, key)

        if value:
            return value

    return ""


def parse_bool(value: str) -> bool | None:
    if not value:
        return None

    normalized = value.strip().lower()

    if normalized in {
        "true",
        "yes",
        "1",
        "continue",
    }:
        return True

    if normalized in {
        "false",
        "no",
        "0",
        "deny",
    }:
        return False

    return None


def parse_float(value: str) -> float | None:
    if not value:
        return None

    try:
        return float(value)
    except ValueError:
        return None


def parse_int(value: str) -> int | None:
    if not value:
        return None

    try:
        return int(float(value))
    except ValueError:
        return None


def csv_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)

    return digest.hexdigest()


@dataclass
class MetafieldValue:
    namespace: str
    key: str
    value: str


@dataclass
class ImageRecord:
    url: str
    position: int
    alt: str = ""


@dataclass
class VariantRecord:
    sku: str
    options: list[tuple[str, str]]
    price: str = ""
    compare_at_price: str = ""
    grams: float | None = None
    inventory_tracked: bool = False
    inventory_qty: int | None = None
    inventory_policy: str = "DENY"
    fulfillment_service: str = ""
    requires_shipping: bool | None = None
    taxable: bool | None = None
    barcode: str = ""
    cost: str = ""
    variant_image: str = ""
    packed_length: float | None = None
    packed_width: float | None = None
    packed_height: float | None = None
    metafields: list[MetafieldValue] = field(
        default_factory=list
    )


@dataclass
class ProductRecord:
    handle: str
    title: str
    description_html: str
    vendor: str
    category: str
    product_type: str
    tags: list[str]
    status: str
    published: bool | None
    seo_title: str
    seo_description: str
    variants: list[VariantRecord]
    images: list[ImageRecord]
    metafields: list[MetafieldValue]

    @property
    def has_packed_dimensions(self) -> bool:
        return any(
            v.packed_length is not None
            or v.packed_width is not None
            or v.packed_height is not None
            for v in self.variants
        )


@dataclass
class CsvCatalog:
    path: Path
    sha256: str
    products: list[ProductRecord]


def metafields_from_row(
    row: dict[str, str],
    pattern: re.Pattern,
) -> list[MetafieldValue]:
    output = []

    for column, raw_value in row.items():
        value = (raw_value or "").strip()

        if not value:
            continue

        match = pattern.search(column)

        if not match:
            continue

        output.append(
            MetafieldValue(
                namespace=match.group(1),
                key=match.group(2),
                value=value,
            )
        )

    return output


def merge_metafields(
    values: list[MetafieldValue],
) -> list[MetafieldValue]:
    merged: dict[tuple[str, str], MetafieldValue] = {}

    for item in values:
        merged[
            (
                item.namespace,
                item.key,
            )
        ] = item

    return list(merged.values())


def sanitize_sku_piece(value: str) -> str:
    value = re.sub(
        r"[^A-Za-z0-9]+",
        "-",
        value.strip().upper(),
    )
    value = value.strip("-")
    return value or "NA"


def detect_color_size(
    options: list[tuple[str, str]],
) -> tuple[str, str]:
    color = "NA"
    size = "NA"

    for name, value in options:
        lowered = name.casefold()

        if "color" in lowered or "colour" in lowered:
            color = sanitize_sku_piece(value)

        if "size" in lowered:
            size = sanitize_sku_piece(value)

    return color, size


def generate_missing_skus(
    product: ProductRecord,
) -> None:
    for index, variant in enumerate(
        product.variants,
        start=1,
    ):
        if variant.sku:
            continue

        color, size = detect_color_size(variant.options)

        variant.sku = (
            f"WRY-"
            f"{sanitize_sku_piece(product.handle)}-"
            f"{color}-"
            f"{size}-"
            f"{index:02d}"
        )


def parse_product(
    handle: str,
    rows: list[dict[str, str]],
) -> ProductRecord:
    option_names = []

    for i in range(1, 4):
        names = [
            (row.get(f"Option{i} Name") or "").strip()
            for row in rows
        ]

        name = next(
            (x for x in names if x),
            "",
        )

        option_names.append(name)

    variants = []

    for row in rows:
        sku = pick(row, "sku")
        price = pick(row, "price")

        raw_option_values = [
            (row.get(f"Option{i} Value") or "").strip()
            for i in range(1, 4)
        ]

        has_variant_data = bool(
            sku
            or price
            or any(raw_option_values)
            or pick(row, "grams")
            or pick(row, "inventory_qty")
            or pick(row, "variant_image")
        )

        if not has_variant_data:
            continue

        options = []

        for name, value in zip(
            option_names,
            raw_option_values,
        ):
            if value:
                options.append(
                    (
                        name or "Option",
                        value,
                    )
                )

        variants.append(
            VariantRecord(
                sku=sku,
                options=options,
                price=price,
                compare_at_price=pick(
                    row,
                    "compare_price",
                ),
                grams=parse_float(
                    pick(row, "grams")
                ),
                inventory_tracked=bool(
                    pick(
                        row,
                        "inventory_tracker",
                    )
                ),
                inventory_qty=parse_int(
                    pick(row, "inventory_qty")
                ),
                inventory_policy=(
                    "CONTINUE"
                    if parse_bool(
                        pick(
                            row,
                            "inventory_policy",
                        )
                    )
                    else "DENY"
                ),
                fulfillment_service=pick(
                    row,
                    "fulfillment",
                ),
                requires_shipping=parse_bool(
                    pick(
                        row,
                        "requires_shipping",
                    )
                ),
                taxable=parse_bool(
                    pick(row, "taxable")
                ),
                barcode=pick(row, "barcode"),
                cost=pick(row, "cost"),
                variant_image=pick(
                    row,
                    "variant_image",
                ),
                packed_length=parse_float(
                    pick(row, "packed_length")
                ),
                packed_width=parse_float(
                    pick(row, "packed_width")
                ),
                packed_height=parse_float(
                    pick(row, "packed_height")
                ),
                metafields=merge_metafields(
                    metafields_from_row(
                        row,
                        VARIANT_META_RE,
                    )
                ),
            )
        )

    if len(variants) == 1 and not variants[0].options:
        variants[0].options = [
            ("Title", "Default Title")
        ]

    images_by_url: dict[str, ImageRecord] = {}

    fallback_position = 1

    for row in rows:
        url = pick(row, "image_src")

        if not url:
            continue

        position = (
            parse_int(
                pick(row, "image_position")
            )
            or fallback_position
        )

        fallback_position += 1

        if url not in images_by_url:
            images_by_url[url] = ImageRecord(
                url=url,
                position=position,
                alt=pick(row, "image_alt"),
            )

    for variant in variants:
        if (
            variant.variant_image
            and variant.variant_image not in images_by_url
        ):
            images_by_url[
                variant.variant_image
            ] = ImageRecord(
                url=variant.variant_image,
                position=fallback_position,
            )
            fallback_position += 1

    product_metafields = []

    for row in rows:
        product_metafields.extend(
            metafields_from_row(
                row,
                PRODUCT_META_RE,
            )
        )

    tags_text = first_nonblank(rows, "tags")

    return ProductRecord(
        handle=handle,
        title=first_nonblank(rows, "title"),
        description_html=first_nonblank(
            rows,
            "body",
        ),
        vendor=first_nonblank(rows, "vendor"),
        category=first_nonblank(
            rows,
            "category",
        ),
        product_type=first_nonblank(
            rows,
            "type",
        ),
        tags=[
            tag.strip()
            for tag in tags_text.split(",")
            if tag.strip()
        ],
        status=(
            first_nonblank(rows, "status")
            or "draft"
        ).upper(),
        published=parse_bool(
            first_nonblank(
                rows,
                "published",
            )
        ),
        seo_title=first_nonblank(
            rows,
            "seo_title",
        ),
        seo_description=first_nonblank(
            rows,
            "seo_description",
        ),
        variants=variants,
        images=sorted(
            images_by_url.values(),
            key=lambda x: x.position,
        ),
        metafields=merge_metafields(
            product_metafields
        ),
    )


def validate_catalog(
    catalog: CsvCatalog,
    generate_skus: bool = False,
    ignore_packed_dimensions: bool = False,
) -> list[str]:
    errors = []
    seen_skus: dict[str, str] = {}

    if not catalog.products:
        errors.append("CSV contains no products.")

    for product in catalog.products:
        if not product.handle:
            errors.append("Product has an empty Handle.")
            continue

        if not product.title:
            errors.append(
                f"{product.handle}: Title is empty."
            )

        if not product.variants:
            errors.append(
                f"{product.handle}: no variants found."
            )
            continue

        if generate_skus:
            generate_missing_skus(product)

        if len(product.variants) > 250:
            errors.append(
                f"{product.handle}: {len(product.variants)} variants "
                "exceeds v1/API input limit 250."
            )

        if len(product.images) > 250:
            errors.append(
                f"{product.handle}: {len(product.images)} images "
                "exceeds v1/API input limit 250."
            )

        if (
            product.has_packed_dimensions
            and not ignore_packed_dimensions
        ):
            errors.append(
                f"{product.handle}: packed dimensions are present, "
                "but stable API 2026-10 cannot write them. "
                "Use --ignore-packed-dimensions only if intentional."
            )

        for variant in product.variants:
            if not variant.sku:
                errors.append(
                    f"{product.handle}: variant SKU is empty."
                )
                continue

            if not SKU_RE.match(variant.sku):
                errors.append(
                    f"{product.handle}: SKU {variant.sku!r} "
                    "does not follow the WRY-/AMZ- convention "
                    "with a two-digit terminal index."
                )

            normalized = variant.sku.casefold()

            if normalized in seen_skus:
                errors.append(
                    f"Duplicate SKU {variant.sku!r}: "
                    f"{seen_skus[normalized]} and "
                    f"{product.handle}."
                )
            else:
                seen_skus[normalized] = product.handle

            fulfillment = (
                variant.fulfillment_service.strip().lower()
            )

            if fulfillment not in {
                "",
                "manual",
                "shopify",
            }:
                errors.append(
                    f"{product.handle}/{variant.sku}: "
                    f"unsupported fulfillment service "
                    f"{variant.fulfillment_service!r}."
                )

    return errors


def load_catalog(path: Path) -> CsvCatalog:
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    groups: dict[str, list[dict[str, str]]] = {}

    for row in rows:
        handle = pick(row, "handle")

        if not handle:
            continue

        groups.setdefault(
            handle,
            [],
        ).append(row)

    products = [
        parse_product(handle, group)
        for handle, group in groups.items()
    ]

    return CsvCatalog(
        path=path,
        sha256=csv_sha256(path),
        products=products,
    )