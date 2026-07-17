import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from requests import HTTPError


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

load_dotenv(SCRIPT_DIR / ".env")
load_dotenv(ROOT_DIR / ".env.shopify", override=False)

SHOPIFY_SHOP = os.getenv("SHOPIFY_SHOP", "").strip().strip('"')
SHOPIFY_ADMIN_TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN", "").strip().strip('"')
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-04").strip().strip('"')
SHOPIFY_CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID", "").strip().strip('"')
SHOPIFY_CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET", "").strip().strip('"')


def normalize_shop_domain(shop: str) -> str:
    if not shop:
        raise ValueError("Missing SHOPIFY_SHOP in scripts/.env")

    parsed = urlparse(shop if "://" in shop else f"https://{shop}")
    host = parsed.netloc or parsed.path
    host = host.replace("/admin", "").strip("/")

    if host == "admin.shopify.com":
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] == "store":
            return f"{parts[1]}.myshopify.com"

    if host.endswith(".myshopify.com"):
        return host

    if "." in host:
        raise ValueError(
            "SHOPIFY_SHOP must be your Shopify store handle or .myshopify.com domain, "
            "not the storefront custom domain. Use the value before .myshopify.com, "
            "or the value shown in admin.shopify.com/store/{shop}. For example: SHOPIFY_SHOP=236qm8-w7"
        )

    return f"{host}.myshopify.com"


def validate_admin_token(shop_domain: str, token: str) -> dict:
    if token.startswith("shpat_"):
        if len(token) < 30:
            raise ValueError(
                "SHOPIFY_ADMIN_TOKEN looks incomplete. "
                "Copy the full Admin API access token from Shopify Admin > Apps > Develop apps, "
                "or remove SHOPIFY_ADMIN_TOKEN to use SHOPIFY_CLIENT_ID + SHOPIFY_CLIENT_SECRET."
            )

    url = f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}/shop.json"
    response = requests.get(
        url,
        headers={
            "X-Shopify-Access-Token": token,
            "Accept": "application/json",
        },
        timeout=30,
    )

    if not response.ok:
        print("Admin token validation failed")
        print("Status:", response.status_code)
        print("Response:", response.text)
        response.raise_for_status()

    return response.json()


def exchange_client_credentials(shop_domain: str) -> dict:
    if not SHOPIFY_CLIENT_ID:
        raise ValueError("Missing SHOPIFY_CLIENT_ID in scripts/.env")

    if not SHOPIFY_CLIENT_SECRET:
        raise ValueError("Missing SHOPIFY_CLIENT_SECRET in scripts/.env")

    url = f"https://{shop_domain}/admin/oauth/access_token"
    response = requests.post(
        url,
        data={
            "grant_type": "client_credentials",
            "client_id": SHOPIFY_CLIENT_ID,
            "client_secret": SHOPIFY_CLIENT_SECRET,
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        timeout=30,
    )

    if not response.ok:
        print("Client credentials token request failed")
        print("Status:", response.status_code)
        print("Response:", response.text)
        response.raise_for_status()

    return response.json()


def main() -> None:
    try:
        shop_domain = normalize_shop_domain(SHOPIFY_SHOP)
        print("Shop:", shop_domain)
        print("API version:", SHOPIFY_API_VERSION)

        if SHOPIFY_ADMIN_TOKEN:
            try:
                shop_data = validate_admin_token(shop_domain, SHOPIFY_ADMIN_TOKEN)
                shop_name = shop_data.get("shop", {}).get("name", "Unknown")

                print()
                print("SHOPIFY_ADMIN_TOKEN is valid.")
                print("Store:", shop_name)
                print()
                print("Access token:")
                print(SHOPIFY_ADMIN_TOKEN)
                return
            except (ValueError, HTTPError) as error:
                if not SHOPIFY_CLIENT_ID or not SHOPIFY_CLIENT_SECRET:
                    raise

                print("SHOPIFY_ADMIN_TOKEN skipped:", error)
                print("Requesting a token with SHOPIFY_CLIENT_ID + SHOPIFY_CLIENT_SECRET instead.")

        token_data = exchange_client_credentials(shop_domain)
        access_token = token_data.get("access_token")
        scope = token_data.get("scope")

        print()
        print("Access token:")
        print(access_token)
        print()
        print("Scope:", scope)

    except Exception as error:
        print("Error:", error)
        sys.exit(1)


if __name__ == "__main__":
    main()
