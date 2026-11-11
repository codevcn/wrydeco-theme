from __future__ import annotations

import math
import time
from typing import Iterable

import httpx

from .config import ShopifyConfig
from .errors import ShopifyError


PRODUCT_SET = """
mutation ProductSet(
  $identifier: ProductSetIdentifiers,
  $input: ProductSetInput!
) {
  productSet(
    identifier: $identifier,
    input: $input,
    synchronous: true
  ) {
    product {
      id
      handle
      title
      variants(first: 250) {
        nodes {
          id
          sku
          selectedOptions {
            name
            value
          }
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""


METAFIELDS_SET = """
mutation SetMetafields($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields {
      id
      namespace
      key
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""


PUBLICATION_MUTATION = """
mutation Publish(
  $id: ID!,
  $input: [PublicationInput!]!
) {
  publishablePublish(
    id: $id,
    input: $input
  ) {
    userErrors {
      field
      message
    }
  }
}
"""


UNPUBLICATION_MUTATION = """
mutation Unpublish(
  $id: ID!,
  $input: [PublicationInput!]!
) {
  publishableUnpublish(
    id: $id,
    input: $input
  ) {
    userErrors {
      field
      message
    }
  }
}
"""


class ShopifyClient:
    def __init__(
        self,
        config: ShopifyConfig,
        local_proxy_url: str,
        timeout: float = 30.0,
    ):
        self.config = config

        self.endpoint = (
            f"https://{config.store}"
            f"/admin/api/{config.api_version}"
            f"/graphql.json"
        )

        self.client = httpx.Client(
            proxy=local_proxy_url,
            trust_env=False,
            timeout=timeout,
            follow_redirects=False,
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": config.token,
                "User-Agent": "WrydecoCsvProxyImporter/0.1",
            },
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        self.close()

    def graphql(
        self,
        query: str,
        variables: dict | None = None,
        attempts: int = 6,
    ) -> dict:
        delay = 1.0

        for attempt in range(attempts):
            try:
                response = self.client.post(
                    self.endpoint,
                    json={
                        "query": query,
                        "variables": variables or {},
                    },
                )

                if response.status_code in {
                    429,
                    500,
                    502,
                    503,
                    504,
                }:
                    raise httpx.HTTPStatusError(
                        "Retryable Shopify response.",
                        request=response.request,
                        response=response,
                    )

                response.raise_for_status()
                payload = response.json()

                errors = payload.get("errors") or []

                if errors:
                    throttled = any(
                        (
                            error.get("extensions", {})
                            .get("code")
                            == "THROTTLED"
                        )
                        for error in errors
                    )

                    if throttled:
                        self._sleep_for_throttle(
                            payload,
                            minimum=delay,
                        )
                        delay = min(
                            16.0,
                            delay * 2,
                        )
                        continue

                    raise ShopifyError(
                        "Shopify GraphQL error: "
                        + "; ".join(
                            str(error.get("message"))
                            for error in errors
                        )
                    )

                self._pace(payload)
                return payload

            except (
                httpx.TimeoutException,
                httpx.NetworkError,
                httpx.HTTPStatusError,
            ) as exc:
                if attempt + 1 >= attempts:
                    raise ShopifyError(
                        "Shopify request failed after retries."
                    ) from exc

                time.sleep(delay)
                delay = min(16.0, delay * 2)

        raise ShopifyError("Shopify request retry loop exhausted.")

    def _sleep_for_throttle(
        self,
        payload: dict,
        minimum: float,
    ) -> None:
        throttle = (
            payload.get("extensions", {})
            .get("cost", {})
            .get("throttleStatus", {})
        )

        available = float(
            throttle.get(
                "currentlyAvailable",
                0,
            )
        )
        restore = float(
            throttle.get(
                "restoreRate",
                50,
            )
            or 50
        )

        required = max(
            1.0,
            (100.0 - available) / restore,
        )

        time.sleep(
            max(
                minimum,
                min(required, 10.0),
            )
        )

    def _pace(self, payload: dict) -> None:
        throttle = (
            payload.get("extensions", {})
            .get("cost", {})
            .get("throttleStatus", {})
        )

        if not throttle:
            return

        available = float(
            throttle.get(
                "currentlyAvailable",
                1000,
            )
        )
        restore = float(
            throttle.get(
                "restoreRate",
                50,
            )
            or 50
        )

        if available < 100:
            time.sleep(
                min(
                    max(
                        (100 - available) / restore,
                        0,
                    ),
                    5.0,
                )
            )

    def shop_identity(self) -> dict:
        payload = self.graphql(
            """
            query {
              shop {
                name
                myshopifyDomain
              }
            }
            """
        )

        return payload["data"]["shop"]

    def locations(self) -> list[dict]:
        payload = self.graphql(
            """
            query {
              locations(first: 100) {
                nodes {
                  id
                  name
                  isActive
                  fulfillsOnlineOrders
                }
              }
            }
            """
        )

        return payload["data"]["locations"]["nodes"]

    def metafield_definitions(
        self,
        owner_type: str,
    ) -> dict[tuple[str, str], str]:
        after = None
        output = {}

        while True:
            payload = self.graphql(
                """
                query Definitions(
                  $ownerType: MetafieldOwnerType!,
                  $after: String
                ) {
                  metafieldDefinitions(
                    first: 250,
                    after: $after,
                    ownerType: $ownerType
                  ) {
                    nodes {
                      namespace
                      key
                      type {
                        name
                      }
                    }
                    pageInfo {
                      hasNextPage
                      endCursor
                    }
                  }
                }
                """,
                {
                    "ownerType": owner_type,
                    "after": after,
                },
            )

            connection = payload[
                "data"
            ]["metafieldDefinitions"]

            for node in connection["nodes"]:
                output[
                    (
                        node["namespace"],
                        node["key"],
                    )
                ] = node["type"]["name"]

            page = connection["pageInfo"]

            if not page["hasNextPage"]:
                break

            after = page["endCursor"]

        return output

    def resolve_category(
        self,
        category: str,
    ) -> str | None:
        if not category:
            return None

        if category.startswith(
            "gid://shopify/TaxonomyCategory/"
        ):
            return category

        payload = self.graphql(
            """
            query ResolveCategory($search: String!) {
              taxonomy {
                categories(
                  first: 50,
                  search: $search
                ) {
                  nodes {
                    id
                    fullName
                  }
                }
              }
            }
            """,
            {
                "search": category,
            },
        )

        nodes = payload[
            "data"
        ]["taxonomy"]["categories"]["nodes"]

        normalized = (
            " ".join(
                category.casefold().split()
            )
        )

        exact = [
            node
            for node in nodes
            if " ".join(
                node["fullName"].casefold().split()
            )
            == normalized
        ]

        if len(exact) == 1:
            return exact[0]["id"]

        return None

    def find_sku_owners(
        self,
        skus: Iterable[str],
    ) -> dict[str, set[str]]:
        output: dict[str, set[str]] = {}

        values = list(skus)

        for start in range(
            0,
            len(values),
            25,
        ):
            chunk = values[
                start : start + 25
            ]

            terms = []

            for sku in chunk:
                escaped = (
                    sku.replace("\\", "\\\\")
                    .replace('"', '\\"')
                )

                terms.append(
                    f'sku:"{escaped}"'
                )

            search = " OR ".join(terms)

            payload = self.graphql(
                """
                query FindSkus($query: String!) {
                  productVariants(
                    first: 250,
                    query: $query
                  ) {
                    nodes {
                      sku
                      product {
                        handle
                      }
                    }
                  }
                }
                """,
                {
                    "query": search,
                },
            )

            for node in payload[
                "data"
            ]["productVariants"]["nodes"]:
                sku = node.get("sku")

                if not sku:
                    continue

                output.setdefault(
                    sku.casefold(),
                    set(),
                ).add(
                    node["product"]["handle"]
                )

        return output

    def product_set(
        self,
        handle: str,
        product_input: dict,
    ) -> dict:
        payload = self.graphql(
            PRODUCT_SET,
            {
                "identifier": {
                    "handle": handle,
                },
                "input": product_input,
            },
        )

        result = payload["data"]["productSet"]
        user_errors = result["userErrors"]

        if user_errors:
            raise ShopifyError(
                f"productSet({handle}) failed: "
                + "; ".join(
                    str(error["message"])
                    for error in user_errors
                )
            )

        if not result["product"]:
            raise ShopifyError(
                f"productSet({handle}) returned no product."
            )

        return result["product"]

    def set_metafields(
        self,
        values: list[dict],
    ) -> None:
        for start in range(
            0,
            len(values),
            25,
        ):
            chunk = values[
                start : start + 25
            ]

            payload = self.graphql(
                METAFIELDS_SET,
                {
                    "metafields": chunk,
                },
            )

            result = payload[
                "data"
            ]["metafieldsSet"]

            if result["userErrors"]:
                raise ShopifyError(
                    "metafieldsSet failed: "
                    + "; ".join(
                        error["message"]
                        for error in result[
                            "userErrors"
                        ]
                    )
                )

    def online_store_publication(
        self,
    ) -> str:
        payload = self.graphql(
            """
            query {
              publications(first: 50) {
                nodes {
                  id
                  catalog {
                    title
                  }
                  channels(first: 5) {
                    nodes {
                      name
                    }
                  }
                }
              }
            }
            """
        )

        nodes = payload[
            "data"
        ]["publications"]["nodes"]

        for node in nodes:
            names = []

            catalog = node.get("catalog")

            if catalog and catalog.get("title"):
                names.append(
                    catalog["title"]
                )

            for channel in (
                node.get("channels", {})
                .get("nodes", [])
            ):
                if channel.get("name"):
                    names.append(
                        channel["name"]
                    )

            if any(
                "online store"
                in name.casefold()
                for name in names
            ):
                return node["id"]

        raise ShopifyError(
            "Online Store publication could not be identified."
        )

    def set_publication(
        self,
        product_id: str,
        publication_id: str,
        published: bool,
    ) -> None:
        mutation = (
            PUBLICATION_MUTATION
            if published
            else UNPUBLICATION_MUTATION
        )

        key = (
            "publishablePublish"
            if published
            else "publishableUnpublish"
        )

        payload = self.graphql(
            mutation,
            {
                "id": product_id,
                "input": [
                    {
                        "publicationId": (
                            publication_id
                        )
                    }
                ],
            },
        )

        errors = payload[
            "data"
        ][key]["userErrors"]

        if errors:
            raise ShopifyError(
                f"{key} failed: "
                + "; ".join(
                    error["message"]
                    for error in errors
                )
            )