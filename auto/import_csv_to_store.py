#!/usr/bin/env python3
"""Import a Shopify product CSV into a Shopify store through the Admin GraphQL API.

Shopify does not expose a public endpoint that runs the native "Import products
by CSV" flow, so this script reproduces that behaviour programmatically:

1. Parse the CSV produced by ``json_to_shopify_csv.py`` and group rows by Handle.
2. For every product, build one ``productSet`` mutation containing the product
   fields, its options, every variant and every gallery image, then create it as
   a brand-new product. This importer NEVER overwrites or updates a product that
   already exists: if a product with the same handle is already in the store, it
   is skipped untouched.
3. Assign the product metafields (``custom.*`` etc.) using the type declared by
   the matching metafield definition already present in the destination store.
4. Publish the product to the store's sales channels, matching the CSV
   ``Published`` column.
5. On a clean import (no failures), move every file from ``data/`` and
   ``output/`` into ``warehouse/`` so processed inputs/outputs are archived out
   of the working folders. Disable with ``--no-archive``.

All Shopify credentials are read from ``.env`` using the ``IMPORT_`` prefix so
this importer never touches the media-processing / dev-store credentials:

    IMPORT_STORE_ADMIN_ACCESS_TOKEN=shpat_...
    IMPORT_SHOPIFY_STORE_DOMAIN=your-store.myshopify.com

Optionally, when no admin token is provided, a token is requested with:

    IMPORT_SHOPIFY_CLIENT_ID=...
    IMPORT_SHOPIFY_CLIENT_SECRET=...

Dependencies:

    pip install requests

Usage:

    python import_csv_to_store.py                      # import every CSV in output/
    python import_csv_to_store.py --csv output/B0H6FGXKZ7.csv
    python import_csv_to_store.py --dry-run
    python import_csv_to_store.py --no-publish --draft
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlparse

import requests


LOGGER = logging.getLogger("csv-to-shopify-importer")
SCRIPT_DIR = Path(__file__).resolve().parent
ENV_PREFIX = "IMPORT_"
DEFAULT_API_VERSION = "2026-07"
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_CSV = "output"
MAX_OPTIONS = 3

# After a clean import, the processed inputs/outputs are archived here.
ARCHIVE_SOURCE_DIRS = ("data", "output")
WAREHOUSE_DIR = "warehouse"

# Metafield definition types this importer can set directly from a CSV string.
# Reference/metaobject/rich-text types need specially-formatted values (GIDs or
# JSON) that a flat CSV cannot express, so they are skipped with a warning.
DIRECT_METAFIELD_TYPES = {
    "single_line_text_field",
    "multi_line_text_field",
    "url",
    "number_integer",
    "number_decimal",
    "boolean",
    "money",
    "date",
    "date_time",
    "color",
    "json",
    "rating",
    "dimension",
    "volume",
    "weight",
}

METAFIELD_HEADER_PATTERN = re.compile(
    r"\(\s*product\.metafields\.(?P<namespace>[^.\s]+)\.(?P<key>[^.)\s]+)\s*\)"
)


class AppError(RuntimeError):
    """Raised for a user-actionable import error."""


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


@dataclass(frozen=True)
class ShopifySettings:
    store_domain: str
    access_token: str
    api_version: str


@dataclass
class VariantRow:
    # Each tuple is (option name, option value). Names are resolved once the
    # whole product has been read, because option names only appear on the first
    # CSV row of a product.
    option_values: list[tuple[str, str]]
    sku: str = ""
    price: str = ""
    compare_at_price: str = ""
    barcode: str = ""
    inventory_policy: str = "DENY"
    tracked: bool = False
    requires_shipping: bool = True
    taxable: bool = True
    grams: int = 0
    cost: str = ""


@dataclass
class ImageRow:
    url: str
    position: int
    alt: str = ""


@dataclass
class ProductRecord:
    handle: str
    title: str = ""
    body_html: str = ""
    vendor: str = ""
    product_type: str = ""
    category: str = ""
    tags: list[str] = field(default_factory=list)
    status: str = "ACTIVE"
    published: bool = True
    seo_title: str = ""
    seo_description: str = ""
    option_names: list[str] = field(default_factory=list)
    variants: list[VariantRow] = field(default_factory=list)
    images: list[ImageRow] = field(default_factory=list)
    metafields: list[tuple[str, str, str]] = field(default_factory=list)


class ShopifyClient:
    PRODUCT_BY_HANDLE_QUERY = """
    query productByHandle($identifier: ProductIdentifierInput!) {
      productByIdentifier(identifier: $identifier) {
        id
        handle
      }
    }
    """

    PRODUCT_SET_MUTATION = """
    mutation productSet($input: ProductSetInput!) {
      productSet(input: $input, synchronous: true) {
        product {
          id
          handle
          variants(first: 100) { nodes { id sku } }
        }
        userErrors { field message code }
      }
    }
    """

    METAFIELDS_SET_MUTATION = """
    mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
      metafieldsSet(metafields: $metafields) {
        metafields { id namespace key }
        userErrors { field message code }
      }
    }
    """

    METAFIELD_DEFINITIONS_QUERY = """
    query metafieldDefinitions($cursor: String) {
      metafieldDefinitions(first: 250, ownerType: PRODUCT, after: $cursor) {
        nodes { namespace key type { name } }
        pageInfo { hasNextPage endCursor }
      }
    }
    """

    PUBLICATIONS_QUERY = """
    query publications {
      publications(first: 50) {
        nodes { id name }
      }
    }
    """

    PUBLISH_MUTATION = """
    mutation publishablePublish($id: ID!, $input: [PublicationInput!]!) {
      publishablePublish(id: $id, input: $input) {
        userErrors { field message }
      }
    }
    """

    def __init__(self, settings: ShopifySettings, session: requests.Session) -> None:
        self.settings = settings
        self.session = session
        self.endpoint = (
            f"https://{settings.store_domain}/admin/api/"
            f"{settings.api_version}/graphql.json"
        )

    def graphql(self, query: str, variables: Mapping[str, Any]) -> dict[str, Any]:
        response = self.session.post(
            self.endpoint,
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": self.settings.access_token,
            },
            json={"query": query, "variables": variables},
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        try:
            payload = response.json()
        except ValueError as exc:
            raise AppError(
                f"Shopify returned a non-JSON response: {response.text[:500]}"
            ) from exc

        if payload.get("errors"):
            raise AppError("Shopify GraphQL error: " + _dump(payload["errors"]))

        data = payload.get("data")
        if not isinstance(data, dict):
            raise AppError("Shopify GraphQL response does not contain a data object.")
        return data

    def find_product_id(self, handle: str) -> str | None:
        data = self.graphql(
            self.PRODUCT_BY_HANDLE_QUERY, {"identifier": {"handle": handle}}
        )
        product = data.get("productByIdentifier")
        if isinstance(product, dict):
            return product.get("id")
        return None

    def product_set(self, product_input: Mapping[str, Any]) -> dict[str, Any]:
        data = self.graphql(self.PRODUCT_SET_MUTATION, {"input": product_input})
        result = data.get("productSet") or {}
        errors = result.get("userErrors") or []
        if errors:
            raise AppError("productSet failed: " + _dump(errors))
        product = result.get("product")
        if not isinstance(product, dict) or not product.get("id"):
            raise AppError("productSet did not return the created product.")
        return product

    def set_metafields(self, metafields: Sequence[Mapping[str, Any]]) -> list[str]:
        data = self.graphql(
            self.METAFIELDS_SET_MUTATION, {"metafields": list(metafields)}
        )
        result = data.get("metafieldsSet") or {}
        return [_dump(error) for error in (result.get("userErrors") or [])]

    def load_metafield_definitions(self) -> dict[tuple[str, str], str]:
        definitions: dict[tuple[str, str], str] = {}
        cursor: str | None = None
        while True:
            data = self.graphql(self.METAFIELD_DEFINITIONS_QUERY, {"cursor": cursor})
            block = data.get("metafieldDefinitions") or {}
            for node in block.get("nodes") or []:
                namespace = node.get("namespace")
                key = node.get("key")
                type_name = (node.get("type") or {}).get("name")
                if namespace and key and type_name:
                    definitions[(namespace, key)] = type_name
            page_info = block.get("pageInfo") or {}
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")
        return definitions

    def load_publication_ids(self) -> list[str]:
        data = self.graphql(self.PUBLICATIONS_QUERY, {})
        block = data.get("publications") or {}
        return [
            node["id"]
            for node in block.get("nodes") or []
            if isinstance(node, dict) and node.get("id")
        ]

    def publish(self, product_id: str, publication_ids: Sequence[str]) -> list[str]:
        if not publication_ids:
            return []
        data = self.graphql(
            self.PUBLISH_MUTATION,
            {
                "id": product_id,
                "input": [{"publicationId": pid} for pid in publication_ids],
            },
        )
        result = data.get("publishablePublish") or {}
        return [_dump(error) for error in (result.get("userErrors") or [])]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import a Shopify product CSV into a store via the Admin GraphQL API."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(DEFAULT_CSV),
        help=(
            "A CSV file, or a directory to import every *.csv from "
            f"(default: {DEFAULT_CSV})."
        ),
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help=".env path holding IMPORT_* credentials (default: .env).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Import at most N products (0 = all).",
    )
    parser.add_argument(
        "--only-handle",
        action="append",
        dest="only_handles",
        help="Import only the given Handle. Repeat for several handles.",
    )
    parser.add_argument(
        "--draft",
        action="store_true",
        help="Force every product to DRAFT status regardless of the CSV.",
    )
    parser.add_argument(
        "--no-publish",
        action="store_true",
        help="Do not publish products to the store's sales channels.",
    )
    parser.add_argument(
        "--no-metafields",
        action="store_true",
        help="Skip assigning product metafields.",
    )
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help=(
            "Do not move the processed data/ and output/ files into warehouse/ "
            "after a successful import."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate the CSV without calling Shopify.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO).",
    )
    return parser.parse_args()


def load_env_file(path: Path) -> dict[str, str]:
    """Load a KEY=VALUE .env file without an extra dependency."""
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            LOGGER.debug("Ignoring .env line %d without '='.", line_number)
            continue

        key, raw_value = line.split("=", 1)
        key = key.strip()
        value = raw_value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def env_value(env_values: Mapping[str, str], name: str) -> str:
    """Read a prefixed value from the real environment first, then the .env file."""
    prefixed = f"{ENV_PREFIX}{name}"
    candidate = os.environ.get(prefixed) or env_values.get(prefixed)
    return candidate.strip() if isinstance(candidate, str) else ""


def normalize_store_domain(value: str) -> str:
    candidate = value.strip()
    if "://" not in candidate:
        candidate = "https://" + candidate
    parsed = urlparse(candidate)
    domain = (parsed.netloc or parsed.path).strip().strip("/").lower()
    if not domain:
        raise AppError(f"Invalid Shopify store domain: {value!r}")
    return domain


def exchange_client_credentials(
    session: requests.Session,
    store_domain: str,
    client_id: str,
    client_secret: str,
) -> str:
    url = f"https://{store_domain}/admin/oauth/access_token"
    response = session.post(
        url,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    if not response.ok:
        raise AppError(
            "Client-credentials token request failed with HTTP "
            f"{response.status_code}: {response.text[:500]}"
        )
    token = (response.json() or {}).get("access_token")
    if not token:
        raise AppError("Client-credentials exchange did not return an access_token.")
    return token


def load_settings(env_path: Path, session: requests.Session) -> ShopifySettings:
    env_values = load_env_file(env_path)

    store_domain_raw = env_value(env_values, "SHOPIFY_STORE_DOMAIN") or env_value(
        env_values, "STORE_DOMAIN"
    )
    if not store_domain_raw:
        raise AppError(
            "A destination store domain is required. Add "
            f"{ENV_PREFIX}SHOPIFY_STORE_DOMAIN=your-store.myshopify.com to .env."
        )
    store_domain = normalize_store_domain(store_domain_raw)

    api_version = env_value(env_values, "SHOPIFY_API_VERSION") or DEFAULT_API_VERSION

    access_token = env_value(env_values, "STORE_ADMIN_ACCESS_TOKEN")
    if not access_token:
        client_id = env_value(env_values, "SHOPIFY_CLIENT_ID")
        client_secret = env_value(env_values, "SHOPIFY_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise AppError(
                "Missing credentials. Provide "
                f"{ENV_PREFIX}STORE_ADMIN_ACCESS_TOKEN, or "
                f"{ENV_PREFIX}SHOPIFY_CLIENT_ID + {ENV_PREFIX}SHOPIFY_CLIENT_SECRET, "
                "in .env."
            )
        LOGGER.info("No admin token found; requesting one via client credentials.")
        access_token = exchange_client_credentials(
            session, store_domain, client_id, client_secret
        )

    return ShopifySettings(
        store_domain=store_domain,
        access_token=access_token,
        api_version=api_version,
    )


def as_bool(value: str) -> bool:
    return (value or "").strip().lower() in {"true", "1", "yes", "y"}


def as_int(value: str, default: int = 0) -> int:
    try:
        return int(float((value or "").strip()))
    except (TypeError, ValueError):
        return default


def normalize_status(value: str) -> str:
    status = (value or "").strip().lower()
    return {"active": "ACTIVE", "draft": "DRAFT", "archived": "ARCHIVED"}.get(
        status, "ACTIVE"
    )


def normalize_inventory_policy(value: str) -> str:
    return "CONTINUE" if (value or "").strip().lower() == "continue" else "DENY"


def metafield_columns(headers: Sequence[str]) -> list[tuple[str, str, str]]:
    """Return (header, namespace, key) for every metafield CSV column."""
    columns: list[tuple[str, str, str]] = []
    for header in headers:
        match = METAFIELD_HEADER_PATTERN.search(header)
        if match:
            columns.append((header, match.group("namespace"), match.group("key")))
    return columns


def discover_csv_files(path: Path) -> list[Path]:
    """Return the CSV file(s) to import from a file or a directory path."""
    if path.is_file():
        return [path]
    if path.is_dir():
        files = sorted(
            csv_path
            for csv_path in path.glob("*.csv")
            if csv_path.is_file() and not csv_path.name.startswith(".")
        )
        if not files:
            raise AppError(f"No .csv files were found in directory: {path}")
        return files
    raise AppError(f"CSV path not found: {path}")


def parse_csv_files(
    files: Sequence[Path], only_handles: Iterable[str] | None
) -> list[ProductRecord]:
    """Parse every CSV file and return the combined products, de-duplicated by handle."""
    combined: list[ProductRecord] = []
    seen_handles: set[str] = set()

    for csv_path in files:
        for record in parse_csv(csv_path, only_handles):
            if record.handle in seen_handles:
                LOGGER.warning(
                    "Duplicate handle '%s' found in %s; keeping the first occurrence.",
                    record.handle,
                    csv_path.name,
                )
                continue
            seen_handles.add(record.handle)
            combined.append(record)

    return combined


def parse_csv(path: Path, only_handles: Iterable[str] | None) -> list[ProductRecord]:
    if not path.is_file():
        raise AppError(f"CSV file not found: {path}")

    only = {handle.strip() for handle in only_handles or [] if handle.strip()}

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise AppError(f"CSV file is empty: {path}")
        meta_columns = metafield_columns(list(reader.fieldnames))
        rows = list(reader)

    records: dict[str, ProductRecord] = {}
    order: list[str] = []

    for row in rows:
        handle_value = (row.get("Handle") or "").strip()
        if not handle_value:
            continue
        if only and handle_value not in only:
            continue

        record = records.get(handle_value)
        if record is None:
            record = ProductRecord(handle=handle_value)
            records[handle_value] = record
            order.append(handle_value)

        _apply_row(record, row, meta_columns)

    for record in records.values():
        _finalize_record(record)

    return [records[handle] for handle in order]


def _apply_row(
    record: ProductRecord,
    row: Mapping[str, str],
    meta_columns: Sequence[tuple[str, str, str]],
) -> None:
    title = (row.get("Title") or "").strip()
    is_product_header_row = bool(title)

    if is_product_header_row:
        record.title = title
        record.body_html = row.get("Body (HTML)") or ""
        record.vendor = (row.get("Vendor") or "").strip()
        record.product_type = (row.get("Type") or "").strip()
        record.category = (row.get("Product Category") or "").strip()
        tags_value = (row.get("Tags") or "").strip()
        record.tags = [tag.strip() for tag in tags_value.split(",") if tag.strip()]
        record.status = normalize_status(row.get("Status", ""))
        record.published = as_bool(row.get("Published", ""))
        record.seo_title = (row.get("SEO Title") or "").strip()
        record.seo_description = (row.get("SEO Description") or "").strip()

        # Option names are only present on the first (product header) row.
        for index in range(1, MAX_OPTIONS + 1):
            name = (row.get(f"Option{index} Name") or "").strip()
            if name:
                record.option_names.append(name)

        for header, namespace, key in meta_columns:
            value = (row.get(header) or "").strip()
            if value:
                record.metafields.append((namespace, key, value))

    # Variant rows carry a price; image-only rows do not.
    price = (row.get("Variant Price") or "").strip()
    if price:
        option_values: list[tuple[str, str]] = []
        for index in range(1, MAX_OPTIONS + 1):
            value = (row.get(f"Option{index} Value") or "").strip()
            if value:
                # Store the positional index; the real name is resolved later.
                option_values.append((str(index), value))
        record.variants.append(
            VariantRow(
                option_values=option_values,
                sku=(row.get("Variant SKU") or "").strip(),
                price=price,
                compare_at_price=(row.get("Variant Compare At Price") or "").strip(),
                barcode=(row.get("Variant Barcode") or "").strip(),
                inventory_policy=normalize_inventory_policy(
                    row.get("Variant Inventory Policy", "")
                ),
                tracked=bool((row.get("Variant Inventory Tracker") or "").strip()),
                requires_shipping=as_bool(row.get("Variant Requires Shipping", "true")),
                taxable=as_bool(row.get("Variant Taxable", "true")),
                grams=as_int(row.get("Variant Grams", "0")),
                cost=(row.get("Cost per item") or "").strip(),
            )
        )

    image_src = (row.get("Image Src") or "").strip()
    if image_src:
        record.images.append(
            ImageRow(
                url=image_src,
                position=as_int(row.get("Image Position", "0")),
                alt=(row.get("Image Alt Text") or "").strip(),
            )
        )


def _finalize_record(record: ProductRecord) -> None:
    # Resolve each variant's positional option index to the real option name.
    for variant in record.variants:
        resolved: list[tuple[str, str]] = []
        for position_str, value in variant.option_values:
            position = int(position_str)
            if position <= len(record.option_names):
                resolved.append((record.option_names[position - 1], value))
        # Single-variant products have no finite option; Shopify needs a default.
        if not resolved:
            resolved.append(("Title", "Default Title"))
        variant.option_values = resolved

    if not record.option_names:
        record.option_names = ["Title"]

    # De-duplicate and order gallery images by their CSV position.
    seen: set[str] = set()
    unique_images: list[ImageRow] = []
    for image in sorted(record.images, key=lambda item: item.position):
        if image.url in seen:
            continue
        seen.add(image.url)
        unique_images.append(image)
    record.images = unique_images


def build_product_input(record: ProductRecord, force_draft: bool) -> dict[str, Any]:
    # No ``id`` is ever set: this always creates a brand-new product.
    product_input: dict[str, Any] = {
        "handle": record.handle,
        "title": record.title or record.handle,
        "status": "DRAFT" if force_draft else record.status,
    }
    if record.body_html:
        product_input["descriptionHtml"] = record.body_html
    if record.vendor:
        product_input["vendor"] = record.vendor
    if record.product_type:
        product_input["productType"] = record.product_type
    if record.tags:
        product_input["tags"] = record.tags
    if record.seo_title or record.seo_description:
        product_input["seo"] = {
            "title": record.seo_title,
            "description": record.seo_description,
        }
    # Shopify's category input expects a taxonomy GID, which a flat CSV string
    # cannot provide, so only pass it when it is already a GID.
    if record.category.startswith("gid://"):
        product_input["category"] = record.category

    # Build product options from the distinct variant values, preserving order.
    option_values: dict[str, list[str]] = {name: [] for name in record.option_names}
    for variant in record.variants:
        for name, value in variant.option_values:
            bucket = option_values.setdefault(name, [])
            if value not in bucket:
                bucket.append(value)
    product_input["productOptions"] = [
        {"name": name, "values": [{"name": value} for value in values]}
        for name, values in option_values.items()
        if values
    ]

    product_input["variants"] = [
        build_variant_input(variant) for variant in record.variants
    ]

    if record.images:
        product_input["files"] = [
            {
                "originalSource": image.url,
                "contentType": "IMAGE",
                "alt": image.alt or record.title,
            }
            for image in record.images
        ]

    return product_input


def build_variant_input(variant: VariantRow) -> dict[str, Any]:
    variant_input: dict[str, Any] = {
        "optionValues": [
            {"optionName": name, "name": value}
            for name, value in variant.option_values
        ],
        "price": variant.price,
        "taxable": variant.taxable,
        "inventoryPolicy": variant.inventory_policy,
    }
    if variant.compare_at_price:
        variant_input["compareAtPrice"] = variant.compare_at_price
    if variant.barcode:
        variant_input["barcode"] = variant.barcode

    inventory_item: dict[str, Any] = {
        "tracked": variant.tracked,
        "requiresShipping": variant.requires_shipping,
    }
    if variant.sku:
        inventory_item["sku"] = variant.sku
    if variant.cost:
        inventory_item["cost"] = variant.cost
    if variant.grams > 0:
        inventory_item["measurement"] = {
            "weight": {"unit": "GRAMS", "value": float(variant.grams)}
        }
    variant_input["inventoryItem"] = inventory_item
    return variant_input


def build_metafield_inputs(
    record: ProductRecord,
    owner_id: str,
    definitions: Mapping[tuple[str, str], str],
    warnings: list[str],
) -> list[dict[str, Any]]:
    metafields: list[dict[str, Any]] = []
    for namespace, key, value in record.metafields:
        type_name = definitions.get((namespace, key))
        if not type_name:
            warnings.append(
                f"{record.handle}: no metafield definition for "
                f"{namespace}.{key}; skipped."
            )
            continue
        if type_name not in DIRECT_METAFIELD_TYPES:
            warnings.append(
                f"{record.handle}: metafield {namespace}.{key} has type "
                f"'{type_name}' that needs a GID/JSON value; skipped."
            )
            continue
        metafields.append(
            {
                "ownerId": owner_id,
                "namespace": namespace,
                "key": key,
                "type": type_name,
                "value": value,
            }
        )
    return metafields


def import_products(
    client: ShopifyClient,
    records: Sequence[ProductRecord],
    *,
    force_draft: bool,
    do_publish: bool,
    do_metafields: bool,
) -> tuple[int, int, int, list[str]]:
    warnings: list[str] = []
    created = 0
    skipped = 0
    failed = 0

    definitions: dict[tuple[str, str], str] = {}
    if do_metafields:
        LOGGER.info("Loading product metafield definitions...")
        definitions = client.load_metafield_definitions()
        LOGGER.info("Found %d product metafield definitions.", len(definitions))

    publication_ids: list[str] = []
    if do_publish:
        try:
            publication_ids = client.load_publication_ids()
            LOGGER.info("Found %d sales-channel publication(s).", len(publication_ids))
        except (AppError, requests.RequestException) as exc:
            warnings.append(
                f"Could not load publications; products stay unpublished: {exc}"
            )

    for record in records:
        LOGGER.info(
            "Importing '%s' (%s): %d variant(s), %d image(s)",
            record.title or record.handle,
            record.handle,
            len(record.variants),
            len(record.images),
        )
        try:
            # Never overwrite: a handle already in the store is left untouched.
            existing_id = client.find_product_id(record.handle)
            if existing_id:
                skipped += 1
                LOGGER.warning(
                    "Skipped %s: a product with this handle already exists (%s); "
                    "not overwriting.",
                    record.handle,
                    existing_id,
                )
                continue

            product_input = build_product_input(record, force_draft)
            product = client.product_set(product_input)
            product_id = product["id"]
            created += 1

            if do_metafields:
                metafields = build_metafield_inputs(
                    record, product_id, definitions, warnings
                )
                if metafields:
                    for error in client.set_metafields(metafields):
                        warnings.append(f"{record.handle}: metafield error: {error}")

            should_publish = (
                do_publish
                and record.published
                and not force_draft
                and record.status == "ACTIVE"
            )
            if should_publish and publication_ids:
                for error in client.publish(product_id, publication_ids):
                    warnings.append(f"{record.handle}: publish error: {error}")

            LOGGER.info("Done: %s", product_id)
        except (AppError, requests.RequestException) as exc:
            failed += 1
            LOGGER.error("Failed to import %s: %s", record.handle, exc)

    return created, skipped, failed, warnings


def _unique_destination(directory: Path, name: str) -> Path:
    """Return a non-colliding path inside ``directory`` for ``name``."""
    candidate = directory / name
    if not candidate.exists():
        return candidate

    source = Path(name)
    stem, suffix = source.stem, source.suffix
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    counter = 1
    while True:
        candidate = directory / f"{stem}.{timestamp}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def archive_processed_files(base_dir: Path) -> tuple[int, list[str]]:
    """Move every file from the source directories into the warehouse directory.

    Called only after a clean import so processed inputs/outputs are moved out of
    the working folders. Name collisions in the warehouse are resolved with a
    timestamped suffix, so nothing is ever overwritten.
    """
    warnings: list[str] = []
    warehouse = base_dir / WAREHOUSE_DIR
    warehouse.mkdir(parents=True, exist_ok=True)

    moved = 0
    for source_name in ARCHIVE_SOURCE_DIRS:
        source_dir = base_dir / source_name
        if not source_dir.is_dir():
            continue
        for entry in sorted(source_dir.iterdir()):
            if entry.resolve() == warehouse.resolve():
                continue
            destination = _unique_destination(warehouse, entry.name)
            try:
                shutil.move(str(entry), str(destination))
                moved += 1
                LOGGER.info("Archived %s -> %s", entry, destination)
            except OSError as exc:
                warnings.append(f"Could not archive {entry}: {exc}")
    return moved, warnings


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        csv_files = discover_csv_files(args.csv.resolve())
        records = parse_csv_files(csv_files, args.only_handles)
        if not records:
            raise AppError("No products were found in the CSV(s).")
        if args.limit and args.limit > 0:
            records = records[: args.limit]

        LOGGER.info("CSV source: %s", args.csv)
        LOGGER.info("CSV file(s): %d", len(csv_files))
        LOGGER.info("Products to import: %d", len(records))

        if args.dry_run:
            for record in records:
                LOGGER.info(
                    "[dry-run] %s | %s | variants=%d images=%d metafields=%d",
                    record.handle,
                    record.title,
                    len(record.variants),
                    len(record.images),
                    len(record.metafields),
                )
            LOGGER.info("Dry run complete; no Shopify calls were made.")
            return 0

        session = requests.Session()
        session.headers.update(
            {"User-Agent": "wrydeco-csv-importer/1.0", "Accept": "application/json"}
        )
        settings = load_settings(args.env_file.resolve(), session)
        LOGGER.info("Destination store: %s", settings.store_domain)
        LOGGER.info("API version: %s", settings.api_version)

        client = ShopifyClient(settings, session)
        created, skipped, failed, warnings = import_products(
            client,
            records,
            force_draft=args.draft,
            do_publish=not args.no_publish,
            do_metafields=not args.no_metafields,
        )

        LOGGER.info(
            "Finished. Created=%d, skipped(existing)=%d, failed=%d",
            created,
            skipped,
            failed,
        )

        # A clean import archives the processed data/ and output/ files.
        if failed:
            LOGGER.warning(
                "Skipping archive because %d product(s) failed; "
                "the data/ and output/ files are left in place.",
                failed,
            )
        elif args.no_archive:
            LOGGER.info("Archiving disabled via --no-archive.")
        else:
            moved, archive_warnings = archive_processed_files(SCRIPT_DIR)
            warnings.extend(archive_warnings)
            LOGGER.info(
                "Archived %d file(s) into %s/",
                moved,
                (SCRIPT_DIR / WAREHOUSE_DIR),
            )

        if warnings:
            LOGGER.warning("Warnings: %d", len(warnings))
            for warning in warnings:
                LOGGER.warning("- %s", warning)
        return 1 if failed else 0

    except AppError as exc:
        LOGGER.error("Fatal error: %s", exc)
        return 2
    except requests.RequestException as exc:
        LOGGER.error("Network error talking to Shopify: %s", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
