import os
import sys
import json
from pathlib import Path
from urllib.parse import urlparse
import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r"d:\D-Jobs\ae-B6\Shopify\stores\main\wrydeco\wrydeco-app")
load_dotenv(BASE_DIR / "admin" / ".env")
load_dotenv(BASE_DIR / ".env.shopify", override=False)

SHOPIFY_SHOP = os.getenv("SHOPIFY_SHOP", "wrydeco.myshopify.com").strip().strip('"')
SHOPIFY_ADMIN_TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN", "").strip().strip('"')
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-07").strip().strip('"')
SHOPIFY_CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID", "").strip().strip('"')
SHOPIFY_CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET", "").strip().strip('"')


def normalize_shop_domain(shop: str) -> str:
    parsed = urlparse(shop if "://" in shop else f"https://{shop}")
    host = parsed.netloc or parsed.path
    host = host.replace("/admin", "").strip("/")
    if host == "admin.shopify.com":
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] == "store":
            return f"{parts[1]}.myshopify.com"
    if host.endswith(".myshopify.com"):
        return host
    return f"{host}.myshopify.com"


def get_valid_token(shop_domain: str) -> str:
    if SHOPIFY_ADMIN_TOKEN:
        r = requests.get(
            f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}/shop.json",
            headers={"X-Shopify-Access-Token": SHOPIFY_ADMIN_TOKEN, "Accept": "application/json"},
            timeout=30,
        )
        if r.ok:
            return SHOPIFY_ADMIN_TOKEN
    # Fallback to client_credentials exchange
    r = requests.post(
        f"https://{shop_domain}/admin/oauth/access_token",
        data={
            "grant_type": "client_credentials",
            "client_id": SHOPIFY_CLIENT_ID,
            "client_secret": SHOPIFY_CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def graphql_query(shop_domain: str, api_ver: str, token: str, query: str, variables=None):
    url = f"https://{shop_domain}/admin/api/{api_ver}/graphql.json"
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    r = requests.post(
        url,
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": token,
        },
        json=payload,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def main():
    shop = normalize_shop_domain(SHOPIFY_SHOP)
    api_ver = SHOPIFY_API_VERSION
    token = get_valid_token(shop)
    print(f"Connected to {shop} (API {api_ver})")

    check_query = """
    query {
      metafieldDefinitions(first: 50, ownerType: PRODUCT, namespace: "custom") {
        nodes {
          id
          name
          namespace
          key
          type {
            name
          }
          validations {
            name
            value
          }
          access {
            storefront
          }
          capabilities {
            adminFilterable {
              enabled
            }
            smartCollectionCondition {
              enabled
            }
          }
        }
      }
    }
    """
    res = graphql_query(shop, api_ver, token, check_query)
    existing_nodes = res.get("data", {}).get("metafieldDefinitions", {}).get("nodes", [])
    existing_by_key = {node["key"]: node for node in existing_nodes}
    print(f"Existing product metafield definitions in 'custom': {list(existing_by_key.keys())}")

    definitions_to_create = [
        {
            "name": "Room Type",
            "namespace": "custom",
            "key": "room_type",
            "description": "Assigned residential spaces (Living Room, Bedroom, Bathroom, etc.) for storefront room filtering.",
            "ownerType": "PRODUCT",
            "type": "list.single_line_text_field",
            "pin": True,
            "access": {
                "storefront": "PUBLIC_READ"
            },
            "capabilities": {
                "adminFilterable": {"enabled": True},
                "smartCollectionCondition": {"enabled": True}
            },
            "validations": [
                {
                    "name": "choices",
                    "value": json.dumps([
                        "Living Room",
                        "Bedroom",
                        "Kitchen & Dining",
                        "Home Office & Library",
                        "Nursery & Kids' Room",
                        "Entryway & Hallway",
                        "Bathroom"
                    ])
                }
            ]
        },
        {
            "name": "Interior Style",
            "namespace": "custom",
            "key": "interior_style",
            "description": "Official interior design styles (Rustic, Japandi, Mid-Century, Organic Modern) for storefront filtering.",
            "ownerType": "PRODUCT",
            "type": "list.single_line_text_field",
            "pin": True,
            "access": {
                "storefront": "PUBLIC_READ"
            },
            "capabilities": {
                "adminFilterable": {"enabled": True},
                "smartCollectionCondition": {"enabled": True}
            },
            "validations": [
                {
                    "name": "choices",
                    "value": json.dumps([
                        "Rustic",
                        "Japandi",
                        "Mid-Century",
                        "Organic Modern"
                    ])
                }
            ]
        }
    ]

    create_mutation = """
    mutation CreateMetafieldDefinition($definition: MetafieldDefinitionInput!) {
      metafieldDefinitionCreate(definition: $definition) {
        createdDefinition {
          id
          name
          namespace
          key
          type {
            name
          }
          access {
            storefront
          }
          capabilities {
            adminFilterable {
              enabled
            }
            smartCollectionCondition {
              enabled
            }
          }
          validations {
            name
            value
          }
        }
        userErrors {
          field
          message
          code
        }
      }
    }
    """

    for defn in definitions_to_create:
        key = defn["key"]
        if key in existing_by_key:
            print(f"[SKIP] Metafield definition custom.{key} already exists: {existing_by_key[key]['id']}")
            continue

        print(f"Creating metafield definition custom.{key}...")
        out = graphql_query(shop, api_ver, token, create_mutation, {"definition": defn})
        if "errors" in out:
            print(f"[ERROR] GraphQL top-level error for custom.{key}: {json.dumps(out['errors'], indent=2)}")
            sys.exit(1)

        payload = out.get("data", {}).get("metafieldDefinitionCreate", {})
        user_errors = payload.get("userErrors", [])
        if user_errors:
            print(f"[ERROR] userErrors for custom.{key}: {json.dumps(user_errors, indent=2)}")
            sys.exit(1)

        created = payload.get("createdDefinition")
        print(f"[SUCCESS] Created custom.{key}: {json.dumps(created, indent=2)}")


if __name__ == "__main__":
    main()
