import os
import csv
import time
import sys
from typing import Any, Dict, List, Optional
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

load_dotenv(SCRIPT_DIR / ".env")
load_dotenv(ROOT_DIR / ".env.shopify", override=False)


def clean(value: str | None) -> str:
    return (value or "").strip().strip('"').strip("'")


def normalize_shop_domain(shop_value: str) -> str:
    shop_value = clean(shop_value)

    if not shop_value:
        raise RuntimeError("Missing SHOPIFY_SHOP in scripts/.env")

    parsed = urlparse(shop_value if "://" in shop_value else f"https://{shop_value}")
    host = parsed.netloc or parsed.path
    host = host.replace("/admin", "").strip("/")

    if host == "admin.shopify.com":
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] == "store":
            return f"{parts[1]}.myshopify.com"

    if host.endswith(".myshopify.com"):
        return host

    if "." in host:
        raise RuntimeError(
            "SHOPIFY_SHOP must be your Shopify store handle or .myshopify.com domain, "
            "not the storefront custom domain."
        )

    return f"{host}.myshopify.com"


API_VERSION = clean(os.getenv("SHOPIFY_API_VERSION", "2026-07")).strip('"')
SHOPIFY_CLIENT_ID = clean(os.getenv("SHOPIFY_CLIENT_ID"))
SHOPIFY_CLIENT_SECRET = clean(os.getenv("SHOPIFY_CLIENT_SECRET"))

# An toàn hơn: batch nhỏ để tránh GraphQL cost/rate-limit và dễ debug.
DELETE_BATCH_SIZE = 20

# Lấy 100 files mỗi lần. Shopify GraphQL connection hỗ trợ phân trang bằng cursor.
QUERY_PAGE_SIZE = 100

REQUIRED_FILE_SCOPES_MESSAGE = (
    "Missing Shopify Files access scopes. This script needs read_files to list files "
    "and write_files to delete them. Update the app scopes in Shopify Admin/Partner app, "
    "reinstall or re-authorize the app, then get a fresh access token."
)


FILES_QUERY = """
query GetFiles($first: Int!, $after: String) {
  files(first: $first, after: $after) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      __typename
      id
      alt
      createdAt
      updatedAt
      fileStatus
    }
  }
}
"""


FILE_DELETE_MUTATION = """
mutation DeleteFiles($fileIds: [ID!]!) {
  fileDelete(fileIds: $fileIds) {
    deletedFileIds
    userErrors {
      field
      message
      code
    }
  }
}
"""


class ShopifyAccessDeniedError(RuntimeError):
    pass


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"Missing env var: {name}", file=sys.stderr)
        sys.exit(1)
    return clean(value)


def request_client_credentials_token(shop_domain: str) -> str:
    if not SHOPIFY_CLIENT_ID:
        raise RuntimeError("Missing SHOPIFY_CLIENT_ID in scripts/.env")

    if not SHOPIFY_CLIENT_SECRET:
        raise RuntimeError("Missing SHOPIFY_CLIENT_SECRET in scripts/.env")

    response = requests.post(
        f"https://{shop_domain}/admin/oauth/access_token",
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
        raise RuntimeError(f"Failed to request access token: {response.status_code} {response.text}")

    payload = response.json()
    token = payload.get("access_token")

    if not token:
        raise RuntimeError(f"No access_token in response: {payload}")

    print("Access token acquired with client credentials.")
    print("Scope:", payload.get("scope"))
    return token


def graphql_request(
    endpoint: str,
    token: str,
    query: str,
    variables: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    response = requests.post(
        endpoint,
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": token,
        },
        json={
            "query": query,
            "variables": variables or {},
        },
        timeout=60,
    )

    try:
        payload = response.json()
    except Exception:
        raise RuntimeError(f"Non-JSON response: {response.status_code} {response.text}")

    if response.status_code >= 400:
        raise RuntimeError(f"HTTP {response.status_code}: {payload}")

    if "errors" in payload:
        errors = payload["errors"]
        if any(error.get("extensions", {}).get("code") == "ACCESS_DENIED" for error in errors):
            raise ShopifyAccessDeniedError(f"{REQUIRED_FILE_SCOPES_MESSAGE} Shopify response: {errors}")

        raise RuntimeError(f"GraphQL errors: {errors}")

    throttle = payload.get("extensions", {}).get("cost", {}).get("throttleStatus", {})
    currently_available = throttle.get("currentlyAvailable")

    # Nghỉ nhẹ nếu bucket GraphQL còn thấp.
    if isinstance(currently_available, (int, float)) and currently_available < 100:
        time.sleep(2)

    return payload


def fetch_all_files(endpoint: str, token: str) -> List[Dict[str, Any]]:
    all_files: List[Dict[str, Any]] = []
    after: Optional[str] = None

    while True:
        payload = graphql_request(
            endpoint=endpoint,
            token=token,
            query=FILES_QUERY,
            variables={
                "first": QUERY_PAGE_SIZE,
                "after": after,
            },
        )

        files_conn = payload["data"]["files"]
        nodes = files_conn["nodes"]
        page_info = files_conn["pageInfo"]

        all_files.extend(nodes)

        print(f"Fetched {len(all_files)} files...")

        if not page_info["hasNextPage"]:
            break

        after = page_info["endCursor"]
        time.sleep(0.4)

    return all_files


def export_files_csv(files: List[Dict[str, Any]], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "__typename",
                "alt",
                "fileStatus",
                "createdAt",
                "updatedAt",
            ],
        )
        writer.writeheader()

        for item in files:
            writer.writerow({
                "id": item.get("id", ""),
                "__typename": item.get("__typename", ""),
                "alt": item.get("alt", ""),
                "fileStatus": item.get("fileStatus", ""),
                "createdAt": item.get("createdAt", ""),
                "updatedAt": item.get("updatedAt", ""),
            })


def chunk_list(items: List[str], size: int) -> List[List[str]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def delete_files(endpoint: str, token: str, file_ids: List[str]) -> None:
    total_deleted = 0
    total_errors = 0

    batches = chunk_list(file_ids, DELETE_BATCH_SIZE)

    for index, batch in enumerate(batches, start=1):
        print(f"Deleting batch {index}/{len(batches)} — {len(batch)} files")

        payload = graphql_request(
            endpoint=endpoint,
            token=token,
            query=FILE_DELETE_MUTATION,
            variables={
                "fileIds": batch,
            },
        )

        result = payload["data"]["fileDelete"]
        deleted_ids = result.get("deletedFileIds") or []
        user_errors = result.get("userErrors") or []

        total_deleted += len(deleted_ids)
        total_errors += len(user_errors)

        if user_errors:
            print("User errors:")
            for err in user_errors:
                print(f"- code={err.get('code')} field={err.get('field')} message={err.get('message')}")

        print(f"Deleted so far: {total_deleted}")
        time.sleep(1)

    print("Done.")
    print(f"Deleted files: {total_deleted}")
    print(f"Errors: {total_errors}")


def main() -> None:
    shop = normalize_shop_domain(required_env("SHOPIFY_SHOP"))
    token = clean(os.getenv("SHOPIFY_ADMIN_TOKEN"))

    endpoint = f"https://{shop}/admin/api/{API_VERSION}/graphql.json"

    print(f"Store: {shop}")
    print(f"API version: {API_VERSION}")

    try:
        if not token:
            token = request_client_credentials_token(shop)

        files = fetch_all_files(endpoint, token)
    except ShopifyAccessDeniedError as error:
        print("")
        print("ACCESS DENIED")
        print(error)
        print("")
        print("Current client-credentials token may not include read_files/write_files.")
        print("After updating scopes, run get_access_token.cmd again to verify the new token scope.")
        sys.exit(1)
    except Exception as error:
        if not SHOPIFY_CLIENT_ID or not SHOPIFY_CLIENT_SECRET:
            raise

        print("Initial request failed:", error)
        print("Retrying with SHOPIFY_CLIENT_ID + SHOPIFY_CLIENT_SECRET.")
        token = request_client_credentials_token(shop)
        try:
            files = fetch_all_files(endpoint, token)
        except ShopifyAccessDeniedError as scope_error:
            print("")
            print("ACCESS DENIED")
            print(scope_error)
            print("")
            print("The fresh client-credentials token still does not include read_files/write_files.")
            print("Update/reinstall app scopes, then rerun this script.")
            sys.exit(1)

    print(f"Total files found: {len(files)}")

    export_path = "shopify_files_before_delete.csv"
    export_files_csv(files, export_path)
    print(f"Exported file list to: {export_path}")

    if not files:
        print("No files to delete.")
        return

    delete_confirmation = os.getenv("DELETE_ALL_SHOPIFY_FILES", "").strip()

    if delete_confirmation != "YES":
        print("")
        print("DRY RUN ONLY. No files were deleted.")
        print("Review shopify_files_before_delete.csv first.")
        print("")
        print("To actually delete all files, run again with:")
        print("DELETE_ALL_SHOPIFY_FILES=YES")
        return

    file_ids = [item["id"] for item in files if item.get("id")]

    print("")
    print("WARNING: You are about to permanently delete all Shopify Files.")
    print(f"Files to delete: {len(file_ids)}")
    print("")

    delete_files(endpoint, token, file_ids)


if __name__ == "__main__":
    main()
