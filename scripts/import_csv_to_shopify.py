import argparse
import csv
import os
import sys
from pathlib import Path
from urllib.parse import quote, urlparse

import requests
from dotenv import load_dotenv
from requests import HTTPError


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
DEFAULT_CSV_FILE = SCRIPT_DIR / "products_to_import.csv"
TRACK_QUANTITY_COLUMNS = (
    "Variant Inventory Tracker",
    "Track Quantity",
    "Variant Track Quantity",
)
QUANTITY_COLUMNS = (
    "Variant Inventory Qty",
    "Variant Quantity",
    "Quantity",
    "Variant Inventory Quantity",
)

load_dotenv(SCRIPT_DIR / ".env")
load_dotenv(ROOT_DIR / ".env.shopify", override=False)


def clean(value: object) -> str:
    return str(value or "").strip()


def normalize_shop(shop_value: str) -> str:
    shop_value = clean(shop_value).strip('"')

    if not shop_value:
        raise RuntimeError("Missing SHOPIFY_SHOP in scripts/.env")

    if shop_value.startswith(("http://", "https://")):
        parsed = urlparse(shop_value)

        if parsed.netloc == "admin.shopify.com":
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) >= 2 and parts[0] == "store":
                return parts[1]

        host = parsed.netloc
    else:
        host = shop_value

    host = host.replace(".myshopify.com", "").strip("/")

    if "." in host:
        raise RuntimeError(
            "SHOPIFY_SHOP must be your Shopify store handle, not the storefront custom domain. "
            "Use the value before .myshopify.com, or the value shown in admin.shopify.com/store/{shop}."
        )

    return host


SHOPIFY_SHOP = ""
SHOPIFY_API_VERSION = clean(os.getenv("SHOPIFY_API_VERSION", "2026-07")).strip('"')
SHOPIFY_ADMIN_TOKEN = clean(
    os.getenv("SHOPIFY_ADMIN_TOKEN") or os.getenv("SHOPIFY_ACCESS_TOKEN")
).strip('"')
SHOPIFY_CLIENT_ID = clean(os.getenv("SHOPIFY_CLIENT_ID")).strip('"')
SHOPIFY_CLIENT_SECRET = clean(os.getenv("SHOPIFY_CLIENT_SECRET")).strip('"')
ACCESS_TOKEN = ""


def get_access_token() -> str:
    if SHOPIFY_ADMIN_TOKEN:
        try:
            validate_access_token(SHOPIFY_ADMIN_TOKEN)
            print("SHOPIFY_ADMIN_TOKEN is valid.")
            return SHOPIFY_ADMIN_TOKEN
        except (RuntimeError, HTTPError) as error:
            if not SHOPIFY_CLIENT_ID or not SHOPIFY_CLIENT_SECRET:
                raise

            print("SHOPIFY_ADMIN_TOKEN skipped:", error)
            print("Requesting a token with SHOPIFY_CLIENT_ID + SHOPIFY_CLIENT_SECRET instead.")

    if not SHOPIFY_CLIENT_ID or not SHOPIFY_CLIENT_SECRET:
        raise RuntimeError(
            "Missing token config. Provide SHOPIFY_ADMIN_TOKEN or "
            "SHOPIFY_CLIENT_ID + SHOPIFY_CLIENT_SECRET in scripts/.env."
        )

    url = f"https://{SHOPIFY_SHOP}.myshopify.com/admin/oauth/access_token"
    response = requests.post(
        url,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        data={
            "grant_type": "client_credentials",
            "client_id": SHOPIFY_CLIENT_ID,
            "client_secret": SHOPIFY_CLIENT_SECRET,
        },
        timeout=30,
    )

    if not response.ok:
        print("Failed to get access token")
        print("Status:", response.status_code)
        print("Response:", response.text)
        response.raise_for_status()

    payload = response.json()
    token = payload.get("access_token")

    if not token:
        raise RuntimeError(f"No access_token in response: {payload}")

    print("Access token acquired.")
    print("Scope:", payload.get("scope"))
    print("Expires in:", payload.get("expires_in"))

    return token


def validate_access_token(token: str) -> None:
    if token.startswith("shpat_") and len(token) < 30:
        raise RuntimeError(
            "SHOPIFY_ADMIN_TOKEN looks incomplete. "
            "Paste the full token, or remove SHOPIFY_ADMIN_TOKEN to use client credentials."
        )

    url = f"https://{SHOPIFY_SHOP}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/shop.json"
    response = requests.get(
        url,
        headers={
            "Accept": "application/json",
            "X-Shopify-Access-Token": token,
        },
        timeout=30,
    )

    if not response.ok:
        response.raise_for_status()


def shopify_rest(method: str, path: str, payload: dict | None = None) -> dict:
    url = f"https://{SHOPIFY_SHOP}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/{path}"
    response = requests.request(
        method,
        url,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Shopify-Access-Token": ACCESS_TOKEN,
        },
        json=payload,
        timeout=30,
    )

    if not response.ok:
        print("REST request failed")
        print("Method:", method)
        print("URL:", url)
        print("Status:", response.status_code)
        print("Response:", response.text)
        response.raise_for_status()

    if not response.text:
        return {}

    return response.json()


def option_key(option1: str, option2: str, option3: str = "") -> tuple[str, str, str]:
    return (clean(option1), clean(option2), clean(option3))


def first_column_value(row: dict, columns: tuple[str, ...]) -> str:
    for column in columns:
        value = clean(row.get(column))
        if value:
            return value

    return ""


def wants_tracking(value: str) -> bool:
    normalized = clean(value).lower()
    return normalized in {"1", "true", "yes", "y", "on", "shopify"}


def parse_quantity(value: str, line_number: int, handle: str) -> int | None:
    value = clean(value)

    if not value:
        return None

    try:
        return int(float(value))
    except ValueError as error:
        raise RuntimeError(
            f"Invalid quantity '{value}' for handle '{handle}' at CSV line {line_number}"
        ) from error


def read_products_from_csv(csv_file: Path) -> dict[str, dict]:
    required_columns = {"Handle", "Variant Price"}
    products: dict[str, dict] = {}

    with csv_file.open(mode="r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        columns = set(reader.fieldnames or [])
        missing_columns = required_columns - columns

        if missing_columns:
            raise RuntimeError(f"CSV missing required columns: {', '.join(sorted(missing_columns))}")

        for line_number, row in enumerate(reader, start=2):
            handle = clean(row.get("Handle"))
            if not handle:
                continue

            title = clean(row.get("Title"))
            option_names = [
                clean(row.get("Option1 Name")),
                clean(row.get("Option2 Name")),
                clean(row.get("Option3 Name")),
            ]
            option_values = option_key(
                row.get("Option1 Value", ""),
                row.get("Option2 Value", ""),
                row.get("Option3 Value", ""),
            )
            price = clean(row.get("Variant Price"))

            if not price:
                raise RuntimeError(f"Missing Variant Price for handle '{handle}' at CSV line {line_number}")

            track_quantity = wants_tracking(first_column_value(row, TRACK_QUANTITY_COLUMNS))
            quantity = parse_quantity(
                first_column_value(row, QUANTITY_COLUMNS),
                line_number,
                handle,
            )

            product = products.setdefault(
                handle,
                {
                    "handle": handle,
                    "title": "",
                    "option_names": ["", "", ""],
                    "variants": {},
                },
            )

            if title:
                product["title"] = title

            for index, option_name in enumerate(option_names):
                if option_name:
                    product["option_names"][index] = option_name

            if option_values in product["variants"]:
                raise RuntimeError(
                    "Duplicate variant option values in CSV for "
                    f"handle '{handle}': {option_values}"
                )

            product["variants"][option_values] = {
                "price": price,
                "track_quantity": track_quantity,
                "quantity": quantity,
                "line_number": line_number,
            }

    if not products:
        raise RuntimeError(f"No products found in CSV: {csv_file}")

    return products


def get_existing_product(handle: str) -> dict | None:
    data = shopify_rest("GET", f"products.json?handle={quote(handle)}&limit=1")
    products = data.get("products", [])

    if not products:
        return None

    product = products[0]

    if product.get("handle") != handle:
        return None

    return product


def build_variant_map(product: dict) -> dict[tuple[str, str, str], dict]:
    variants_by_options: dict[tuple[str, str, str], dict] = {}

    for variant in product.get("variants", []):
        key = option_key(
            variant.get("option1", ""),
            variant.get("option2", ""),
            variant.get("option3", ""),
        )

        if key in variants_by_options:
            raise RuntimeError(
                f"Store product '{product.get('handle')}' has duplicate variant options: {key}"
            )

        variants_by_options[key] = variant

    return variants_by_options


def get_primary_location_id() -> int:
    data = shopify_rest("GET", "locations.json?limit=250")
    locations = data.get("locations", [])
    active_locations = [
        location
        for location in locations
        if location.get("active", True)
    ]

    if not active_locations:
        raise RuntimeError("No active Shopify locations found for inventory updates.")

    return active_locations[0]["id"]


def build_product_update(csv_product: dict, existing_product: dict) -> dict:
    product_update = {
        "id": existing_product["id"],
    }

    if csv_product["title"]:
        product_update["title"] = csv_product["title"]

    options = []
    existing_options_by_position = {
        int(option.get("position", index + 1)): option
        for index, option in enumerate(existing_product.get("options", []))
    }

    for position, option_name in enumerate(csv_product["option_names"], start=1):
        if not option_name:
            continue

        existing_option = existing_options_by_position.get(position, {})
        option_payload = {
            "name": option_name,
            "position": position,
        }

        if existing_option.get("id"):
            option_payload["id"] = existing_option["id"]

        options.append(option_payload)

    if options:
        product_update["options"] = options

    return product_update


def update_inventory_item_tracking(inventory_item_id: int, dry_run: bool) -> bool:
    payload = {
        "inventory_item": {
            "id": inventory_item_id,
            "tracked": True,
        }
    }

    if dry_run:
        print("    DRY RUN inventory tracking update:", payload["inventory_item"])
    else:
        shopify_rest("PUT", f"inventory_items/{inventory_item_id}.json", payload)

    return True


def set_inventory_quantity(
    inventory_item_id: int,
    location_id: int,
    quantity: int,
    dry_run: bool,
) -> None:
    payload = {
        "inventory_item_id": inventory_item_id,
        "location_id": location_id,
        "available": quantity,
        "disconnect_if_necessary": True,
    }

    if dry_run:
        print("    DRY RUN inventory quantity set:", payload)
    else:
        shopify_rest("POST", "inventory_levels/set.json", payload)


def update_existing_product(
    csv_product: dict,
    location_id: int | None,
    dry_run: bool,
) -> tuple[int, int, int, list[str]]:
    handle = csv_product["handle"]
    existing_product = get_existing_product(handle)

    if not existing_product:
        raise RuntimeError(
            f"Product with handle '{handle}' does not exist on the store. "
            "Stopped because this importer is update-only."
        )

    variants_by_options = build_variant_map(existing_product)
    missing_variants = [
        variant_key
        for variant_key in csv_product["variants"]
        if variant_key not in variants_by_options
    ]

    if missing_variants:
        missing_text = ", ".join(str(key) for key in missing_variants)
        raise RuntimeError(
            f"Product '{handle}' is missing CSV variants on the store: {missing_text}. "
            "Stopped because this importer cannot create new variants."
        )

    product_update = build_product_update(csv_product, existing_product)

    print(f"Updating product '{existing_product.get('title')}' ({handle})")

    if dry_run:
        print("  DRY RUN product update:", product_update)
    else:
        shopify_rest(
            "PUT",
            f"products/{existing_product['id']}.json",
            {"product": product_update},
        )

    updated_variants = 0
    tracked_inventory_items = 0
    updated_inventory_levels = 0
    unchanged_variants = []

    for variant_key, csv_variant in csv_product["variants"].items():
        existing_variant = variants_by_options[variant_key]
        new_price = csv_variant["price"]
        old_price = clean(existing_variant.get("price"))

        if old_price == new_price:
            unchanged_variants.append(str(variant_key))
        else:
            variant_payload = {
                "id": existing_variant["id"],
                "price": new_price,
            }

            print(f"  Variant {variant_key}: {old_price} -> {new_price}")

            if dry_run:
                print("    DRY RUN variant update:", variant_payload)
            else:
                shopify_rest(
                    "PUT",
                    f"variants/{existing_variant['id']}.json",
                    {"variant": variant_payload},
                )

            updated_variants += 1

        inventory_item_id = existing_variant.get("inventory_item_id")

        if not inventory_item_id:
            raise RuntimeError(
                f"Variant {variant_key} on product '{handle}' has no inventory_item_id."
            )

        if csv_variant["track_quantity"]:
            print(f"  Variant {variant_key}: track quantity ON")
            if update_inventory_item_tracking(inventory_item_id, dry_run):
                tracked_inventory_items += 1

        if csv_variant["quantity"] is not None:
            if location_id is None:
                raise RuntimeError("A location ID is required to update inventory quantities.")

            print(f"  Variant {variant_key}: quantity -> {csv_variant['quantity']}")
            set_inventory_quantity(
                inventory_item_id,
                location_id,
                csv_variant["quantity"],
                dry_run,
            )
            updated_inventory_levels += 1

    return updated_variants, tracked_inventory_items, updated_inventory_levels, unchanged_variants


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update existing Shopify products from a CSV without creating new products or variants."
    )
    parser.add_argument(
        "--csv",
        default=str(DEFAULT_CSV_FILE),
        help="Path to the Shopify CSV file. Defaults to scripts/products_to_import.csv.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the updates without sending PUT requests.",
    )
    parser.add_argument(
        "--location-id",
        type=int,
        default=os.getenv("SHOPIFY_LOCATION_ID"),
        help=(
            "Shopify location ID used for inventory quantities. "
            "Defaults to SHOPIFY_LOCATION_ID, then the first active location."
        ),
    )

    return parser.parse_args()


def main() -> int:
    global SHOPIFY_SHOP, ACCESS_TOKEN

    args = parse_args()
    csv_file = Path(args.csv).resolve()

    if not csv_file.exists():
        raise RuntimeError(f"CSV file not found: {csv_file}")

    SHOPIFY_SHOP = normalize_shop(os.getenv("SHOPIFY_SHOP", ""))
    ACCESS_TOKEN = get_access_token()

    products = read_products_from_csv(csv_file)
    needs_inventory_quantity = any(
        variant["quantity"] is not None
        for product in products.values()
        for variant in product["variants"].values()
    )
    location_id = int(args.location_id) if args.location_id else None

    if needs_inventory_quantity and location_id is None:
        location_id = get_primary_location_id()

    print("Shop:", f"{SHOPIFY_SHOP}.myshopify.com")
    print("API version:", SHOPIFY_API_VERSION)
    print("CSV:", csv_file)
    print("Mode:", "dry run" if args.dry_run else "update store")
    print("Products in CSV:", len(products))
    if location_id is not None:
        print("Inventory location ID:", location_id)
    print()

    total_updated_variants = 0
    total_tracked_inventory_items = 0
    total_updated_inventory_levels = 0
    total_unchanged_variants = 0

    for csv_product in products.values():
        (
            updated_count,
            tracked_count,
            inventory_level_count,
            unchanged_variants,
        ) = update_existing_product(csv_product, location_id, args.dry_run)
        total_updated_variants += updated_count
        total_tracked_inventory_items += tracked_count
        total_updated_inventory_levels += inventory_level_count
        total_unchanged_variants += len(unchanged_variants)

        if unchanged_variants:
            print(f"  Unchanged variants: {len(unchanged_variants)}")

    print()
    print("Done.")
    print("Updated variants:", total_updated_variants)
    print("Inventory items changed to tracked:", total_tracked_inventory_items)
    print("Inventory levels set:", total_updated_inventory_levels)
    print("Unchanged variants:", total_unchanged_variants)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print()
        print("Import failed:", error)
        raise SystemExit(1)
