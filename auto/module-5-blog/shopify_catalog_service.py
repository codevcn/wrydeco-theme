"""
Shopify Catalog, Blog & Storefront Evidence Service (`shopify_catalog_service.py`).

Enforces mandatory rules:
  - Every GraphQL Admin API, Storefront HTML, and Shopify CDN request MUST pass through
    `StoreManager.proxy_manager.get_shopify_requests_session(...)`.
  - Never exposes Admin tokens, Client Secrets, or Proxy passwords in returned payloads.
  - Provides cursor-paginated blog/article listing, product/variant/media evidence lookup,
    and live storefront URL verification.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from proxy_manager import redact_sensitive_data
from store_manager import DATA_DIR, StoreConfig, StoreManager, slugify_store_id


class ShopifyCatalogService:
    """Queries Shopify Admin GraphQL API and Storefront pages strictly via ProxyManager."""

    def __init__(self, store_manager: Optional[StoreManager] = None) -> None:
        self.store_manager = store_manager or StoreManager(data_dir=DATA_DIR)

    def _graphql(
        self,
        store: StoreConfig,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        shop_domain = store.normalized_shop
        sess = self.store_manager.proxy_manager.get_shopify_requests_session(
            target_shop_domain=shop_domain
        )
        token = self.store_manager.get_valid_access_token(store.id, force_refresh=False)

        headers = {
            "X-Shopify-Access-Token": token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        resp = sess.post(
            store.graphql_endpoint,
            json={"query": query, "variables": variables or {}},
            headers=headers,
            timeout=30,
        )
        if resp.status_code == 401:
            token = self.store_manager.get_valid_access_token(store.id, force_refresh=True)
            headers["X-Shopify-Access-Token"] = token
            resp = sess.post(
                store.graphql_endpoint,
                json={"query": query, "variables": variables or {}},
                headers=headers,
                timeout=30,
            )

        resp.raise_for_status()
        payload = resp.json()
        if payload.get("errors"):
            raise RuntimeError(
                f"Shopify GraphQL error on {shop_domain}: {redact_sensitive_data(payload['errors'])}"
            )
        return payload.get("data") or {}

    def list_blogs(self, store_id: str) -> Dict[str, Any]:
        """Return all blogs on the store with cursor pagination."""
        store = self.store_manager.get_store(store_id)
        blogs: List[Dict[str, Any]] = []
        cursor: Optional[str] = None

        query = """
        query ListAllBlogs($after: String) {
          blogs(first: 50, after: $after) {
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              id
              handle
              title
            }
          }
        }
        """
        while True:
            data = self._graphql(store, query, {"after": cursor})
            b_conn = data.get("blogs") or {}
            for node in b_conn.get("nodes") or []:
                blogs.append(
                    {
                        "id": node.get("id"),
                        "handle": node.get("handle"),
                        "title": node.get("title"),
                        "storefront_url": f"{store.resolved_public_domain.rstrip('/')}/blogs/{node.get('handle')}",
                    }
                )
            page_info = b_conn.get("pageInfo") or {}
            if page_info.get("hasNextPage") and page_info.get("endCursor"):
                cursor = page_info["endCursor"]
            else:
                break

        return {
            "ok": True,
            "store_id": store.id,
            "shop_domain": store.normalized_shop,
            "default_blog_handle": store.default_blog_handle,
            "default_blog_id": store.default_blog_id,
            "blogs_count": len(blogs),
            "blogs": blogs,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "proxy_used": self.store_manager.proxy_manager.get_config(auto_bootstrap=False).masked_summary,
        }

    def list_existing_articles(
        self,
        store_id: str,
        blog_handle: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Paginate all articles across all blogs (or a single blog_handle) on the store."""
        store = self.store_manager.get_store(store_id)
        blogs_res = self.list_blogs(store.id)
        target_blogs = blogs_res["blogs"]
        if blog_handle:
            clean_bh = blog_handle.strip().lower()
            target_blogs = [b for b in target_blogs if (b.get("handle") or "").lower() == clean_bh]

        all_articles: List[Dict[str, Any]] = []
        article_query = """
        query PaginateBlogArticles($blogId: ID!, $after: String) {
          blog(id: $blogId) {
            id
            handle
            title
            articles(first: 100, after: $after) {
              pageInfo {
                hasNextPage
                endCursor
              }
              nodes {
                id
                title
                handle
                isPublished
                publishedAt
                createdAt
                updatedAt
                summary
                tags
                author {
                  name
                }
                image {
                  url
                  altText
                  width
                  height
                }
              }
            }
          }
        }
        """

        base_dom = store.resolved_public_domain.rstrip("/")
        for b in target_blogs:
            a_cursor: Optional[str] = None
            while True:
                data = self._graphql(store, article_query, {"blogId": b["id"], "after": a_cursor})
                blog_node = data.get("blog") or {}
                a_conn = blog_node.get("articles") or {}
                for art in a_conn.get("nodes") or []:
                    handle = art.get("handle") or ""
                    all_articles.append(
                        {
                            "article_id": art.get("id"),
                            "blog_id": b["id"],
                            "blog_handle": b["handle"],
                            "blog_title": b["title"],
                            "title": art.get("title"),
                            "handle": handle,
                            "is_published": bool(art.get("isPublished")),
                            "published_at": art.get("publishedAt"),
                            "created_at": art.get("createdAt"),
                            "updated_at": art.get("updatedAt"),
                            "author": (art.get("author") or {}).get("name") or "",
                            "tags": list(art.get("tags") or []),
                            "image": art.get("image"),
                            "public_url": f"{base_dom}/blogs/{b['handle']}/{handle}",
                        }
                    )
                p_info = a_conn.get("pageInfo") or {}
                if p_info.get("hasNextPage") and p_info.get("endCursor"):
                    a_cursor = p_info["endCursor"]
                else:
                    break

        return {
            "ok": True,
            "store_id": store.id,
            "shop_domain": store.normalized_shop,
            "total_articles": len(all_articles),
            "articles": all_articles,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "proxy_used": self.store_manager.proxy_manager.get_config(auto_bootstrap=False).masked_summary,
        }

    def _normalize_product_node(self, store: StoreConfig, node: Dict[str, Any]) -> Dict[str, Any]:
        base_dom = store.resolved_public_domain.rstrip("/")
        handle = (node.get("handle") or "").strip()
        status = (node.get("status") or "").upper()
        published_at = node.get("publishedAt")
        online_store_url = node.get("onlineStoreUrl") or (f"{base_dom}/products/{handle}" if handle else "")

        # Extract media images
        media_items: List[Dict[str, Any]] = []
        for m in ((node.get("media") or {}).get("nodes")) or []:
            m_type = m.get("mediaContentType") or ""
            m_status = m.get("status") or ""
            img_obj = m.get("image") or (m.get("preview") or {}).get("image") or {}
            img_url = (img_obj.get("url") or "").strip()
            if img_url:
                media_items.append(
                    {
                        "media_id": m.get("id") or "",
                        "media_content_type": m_type,
                        "status": m_status,
                        "alt": (m.get("alt") or img_obj.get("altText") or "").strip(),
                        "url": img_url,
                        "width": int(img_obj.get("width") or 0),
                        "height": int(img_obj.get("height") or 0),
                    }
                )

        # Fallback to featuredMedia / images if media connection was empty
        if not media_items and node.get("featuredMedia"):
            fm = node["featuredMedia"]
            img_obj = (fm.get("preview") or {}).get("image") or {}
            if img_obj.get("url"):
                media_items.append(
                    {
                        "media_id": fm.get("id") or "",
                        "media_content_type": fm.get("mediaContentType") or "IMAGE",
                        "status": fm.get("status") or "READY",
                        "alt": (fm.get("alt") or img_obj.get("altText") or "").strip(),
                        "url": img_obj["url"],
                        "width": int(img_obj.get("width") or 0),
                        "height": int(img_obj.get("height") or 0),
                    }
                )

        variants: List[Dict[str, Any]] = []
        for v in ((node.get("variants") or {}).get("nodes")) or []:
            v_img = v.get("image") or {}
            variants.append(
                {
                    "variant_id": v.get("id") or "",
                    "title": v.get("title") or "",
                    "sku": v.get("sku") or "",
                    "price": str(v.get("price") or ""),
                    "compare_at_price": str(v.get("compareAtPrice") or "") if v.get("compareAtPrice") else None,
                    "available_for_sale": bool(v.get("availableForSale", True)),
                    "selected_options": [
                        {"name": o.get("name"), "value": o.get("value")}
                        for o in (v.get("selectedOptions") or [])
                    ],
                    "image": (
                        {
                            "id": v_img.get("id") or "",
                            "url": v_img.get("url") or "",
                            "alt": v_img.get("altText") or "",
                            "width": int(v_img.get("width") or 0),
                            "height": int(v_img.get("height") or 0),
                        }
                        if v_img.get("url")
                        else None
                    ),
                }
            )

        price_range = node.get("priceRangeV2") or {}
        min_p = (price_range.get("minVariantPrice") or {}).get("amount")
        max_p = (price_range.get("maxVariantPrice") or {}).get("amount")
        currency = (price_range.get("minVariantPrice") or {}).get("currencyCode") or "USD"

        description_html = node.get("descriptionHtml") or ""
        description_text = BeautifulSoup(description_html, "html.parser").get_text(" ", strip=True) if description_html else (node.get("description") or "")

        is_published_online = bool(status == "ACTIVE" and (published_at or online_store_url))

        return {
            "product_id": node.get("id") or "",
            "legacy_resource_id": str(node.get("legacyResourceId") or ""),
            "title": node.get("title") or "",
            "handle": handle,
            "status": status,
            "published_at": published_at,
            "is_published_online": is_published_online,
            "online_store_url": online_store_url,
            "storefront_url": f"{base_dom}/products/{handle}" if handle else "",
            "vendor": node.get("vendor") or "",
            "product_type": node.get("productType") or "",
            "tags": list(node.get("tags") or []),
            "total_inventory": node.get("totalInventory"),
            "price_range": {
                "min": str(min_p) if min_p is not None else "",
                "max": str(max_p) if max_p is not None else "",
                "currency": currency,
            },
            "options": [
                {"id": opt.get("id"), "name": opt.get("name"), "values": list(opt.get("values") or [])}
                for opt in (node.get("options") or [])
            ],
            "description_html": description_html,
            "description_text": description_text[:2500],
            "variants_count": len(variants),
            "variants": variants,
            "media_count": len(media_items),
            "media": media_items,
            "collections": [
                {"id": c.get("id"), "handle": c.get("handle"), "title": c.get("title")}
                for c in (((node.get("collections") or {}).get("nodes")) or [])
            ],
        }

    def search_products(
        self,
        store_id: str,
        query: str = "",
        collection_handle: str = "",
        limit: int = 20,
        active_only: bool = True,
    ) -> Dict[str, Any]:
        """Search verified products and their variants/media from Shopify Admin GraphQL via Proxy."""
        store = self.store_manager.get_store(store_id)
        first_n = max(1, min(int(limit or 20), 50))

        product_fields = """
          id
          legacyResourceId
          title
          handle
          status
          publishedAt
          onlineStoreUrl
          vendor
          productType
          tags
          totalInventory
          description
          descriptionHtml
          priceRangeV2 {
            minVariantPrice { amount currencyCode }
            maxVariantPrice { amount currencyCode }
          }
          options {
            id
            name
            values
          }
          collections(first: 10) {
            nodes {
              id
              handle
              title
            }
          }
          variants(first: 30) {
            nodes {
              id
              title
              sku
              price
              compareAtPrice
              availableForSale
              selectedOptions { name value }
              image { id url altText width height }
            }
          }
          media(first: 25) {
            nodes {
              id
              mediaContentType
              status
              alt
              ... on MediaImage {
                image { url altText width height }
              }
              preview {
                image { url altText width height }
              }
            }
          }
        """

        nodes: List[Dict[str, Any]] = []
        if collection_handle and collection_handle.strip():
            col_q = f"""
            query ProductsByCollection($handle: String!, $first: Int!) {{
              collectionByHandle(handle: $handle) {{
                id
                handle
                title
                products(first: $first) {{
                  nodes {{
                    {product_fields}
                  }}
                }}
              }}
            }}
            """
            data = self._graphql(
                store,
                col_q,
                {"handle": collection_handle.strip(), "first": first_n},
            )
            col_node = data.get("collectionByHandle") or {}
            nodes = ((col_node.get("products") or {}).get("nodes")) or []
        else:
            q_parts: List[str] = []
            if active_only:
                q_parts.append("status:active")
            if query and query.strip():
                q_parts.append(query.strip())
            search_str = " ".join(q_parts) if q_parts else "status:active"

            prod_q = f"""
            query SearchStoreProducts($first: Int!, $query: String) {{
              products(first: $first, query: $query) {{
                nodes {{
                  {product_fields}
                }}
              }}
            }}
            """
            data = self._graphql(store, prod_q, {"first": first_n, "query": search_str})
            nodes = ((data.get("products") or {}).get("nodes")) or []

        products = [self._normalize_product_node(store, n) for n in nodes]
        if active_only:
            products = [p for p in products if p.get("status") == "ACTIVE"]

        return {
            "ok": True,
            "store_id": store.id,
            "shop_domain": store.normalized_shop,
            "query": query,
            "collection_handle": collection_handle,
            "count": len(products),
            "products": products,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "proxy_used": self.store_manager.proxy_manager.get_config(auto_bootstrap=False).masked_summary,
        }

    def get_product_evidence(
        self,
        store_id: str,
        product_id_or_handle: str,
        verify_live_url: bool = True,
    ) -> Dict[str, Any]:
        """
        Fetch full product, variant, option, and media evidence for a single product
        by handle, URL, numeric ID, or GraphQL GID, and optionally verify its live storefront URL via Proxy.
        """
        store = self.store_manager.get_store(store_id)
        raw_ref = (product_id_or_handle or "").strip()
        if not raw_ref:
            raise ValueError("product_id_or_handle must be non-empty.")

        # Extract handle if a full /products/<handle> URL was passed
        if "/products/" in raw_ref:
            parsed = urlparse(raw_ref)
            raw_ref = parsed.path.split("/products/")[-1].strip("/").split("?")[0]

        product_fields = """
          id
          legacyResourceId
          title
          handle
          status
          publishedAt
          onlineStoreUrl
          vendor
          productType
          tags
          totalInventory
          description
          descriptionHtml
          priceRangeV2 {
            minVariantPrice { amount currencyCode }
            maxVariantPrice { amount currencyCode }
          }
          options {
            id
            name
            values
          }
          collections(first: 15) {
            nodes {
              id
              handle
              title
            }
          }
          variants(first: 60) {
            nodes {
              id
              title
              sku
              price
              compareAtPrice
              availableForSale
              selectedOptions { name value }
              image { id url altText width height }
            }
          }
          media(first: 50) {
            nodes {
              id
              mediaContentType
              status
              alt
              ... on MediaImage {
                image { url altText width height }
              }
              preview {
                image { url altText width height }
              }
            }
          }
        """

        node: Optional[Dict[str, Any]] = None
        if raw_ref.startswith("gid://shopify/Product/"):
            q = f"""
            query GetProductById($id: ID!) {{
              product(id: $id) {{
                {product_fields}
              }}
            }}
            """
            node = self._graphql(store, q, {"id": raw_ref}).get("product")
        elif raw_ref.isdigit():
            gid = f"gid://shopify/Product/{raw_ref}"
            q = f"""
            query GetProductById($id: ID!) {{
              product(id: $id) {{
                {product_fields}
              }}
            }}
            """
            node = self._graphql(store, q, {"id": gid}).get("product")
        else:
            q = f"""
            query GetProductByHandle($handle: String!) {{
              productByHandle(handle: $handle) {{
                {product_fields}
              }}
            }}
            """
            node = self._graphql(store, q, {"handle": raw_ref}).get("productByHandle")

        if not node:
            return {
                "ok": False,
                "store_id": store.id,
                "requested": product_id_or_handle,
                "error": f"Product '{product_id_or_handle}' not found on store '{store.id}'.",
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

        product = self._normalize_product_node(store, node)
        live_check: Dict[str, Any] = {}
        if verify_live_url and product.get("storefront_url"):
            url_res = self.verify_storefront_urls(store.id, [product["storefront_url"]])
            if url_res.get("results"):
                live_check = url_res["results"][0]
                product["storefront_http_status"] = live_check.get("http_status", 0)
                product["storefront_live_ok"] = bool(live_check.get("ok"))

        return {
            "ok": True,
            "store_id": store.id,
            "shop_domain": store.normalized_shop,
            "product": product,
            "live_storefront_check": live_check,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "proxy_used": self.store_manager.proxy_manager.get_config(auto_bootstrap=False).masked_summary,
        }

    def verify_storefront_urls(self, store_id: str, urls: List[str]) -> Dict[str, Any]:
        """Verify live HTTP status, final URL, canonical URL, and title for storefront URLs via Proxy."""
        store = self.store_manager.get_store(store_id)
        sess = self.store_manager.proxy_manager.get_shopify_requests_session(
            target_shop_domain=store.normalized_shop
        )
        base_dom = store.resolved_public_domain.rstrip("/")
        now_iso = datetime.now(timezone.utc).isoformat()

        results: List[Dict[str, Any]] = []
        for raw_u in urls or []:
            u = (raw_u or "").strip()
            if not u:
                continue
            if u.startswith("/"):
                u = f"{base_dom}{u}"
            resp = None
            last_exc = None
            for attempt in range(3):
                try:
                    resp = sess.get(u, timeout=20, allow_redirects=True)
                    if resp.status_code < 500:
                        break
                    time.sleep(1.5)
                except Exception as exc:
                    last_exc = exc
                    time.sleep(1.5)

            if resp is not None:
                canonical = ""
                title = ""
                if "text/html" in (resp.headers.get("Content-Type") or ""):
                    soup = BeautifulSoup(resp.text, "html.parser")
                    if soup.title and soup.title.string:
                        title = soup.title.string.strip()
                    can_tag = soup.find("link", rel=lambda v: v and "canonical" in str(v).lower())
                    if can_tag and can_tag.get("href"):
                        canonical = str(can_tag.get("href")).strip()
                ok = 200 <= resp.status_code < 400
                results.append(
                    {
                        "requested_url": raw_u,
                        "resolved_url": u,
                        "final_url": resp.url,
                        "http_status": int(resp.status_code),
                        "ok": ok,
                        "title": title,
                        "canonical_url": canonical,
                        "checked_at": now_iso,
                    }
                )
            else:
                results.append(
                    {
                        "requested_url": raw_u,
                        "resolved_url": u,
                        "final_url": "",
                        "http_status": 0,
                        "ok": False,
                        "title": "",
                        "canonical_url": "",
                        "error": redact_sensitive_data(str(last_exc)),
                        "checked_at": now_iso,
                    }
                )

        return {
            "ok": all(r.get("ok") for r in results) if results else True,
            "store_id": store.id,
            "checked_count": len(results),
            "results": results,
            "checked_at": now_iso,
            "proxy_used": self.store_manager.proxy_manager.get_config(auto_bootstrap=False).masked_summary,
        }
