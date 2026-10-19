"""
Modular Multi-Store Shopify GraphQL Publisher (`shopify_publisher.py`).

Publishes or updates `PostProcessedArticle` objects to the selected store's
Shopify Blog via GraphQL Admin API (`articleCreate` / `articleUpdate` + `metafieldsSet`)
with strict `create_only` protection, full cursor pagination, strict blog resolution,
no silent hero image dropping, and post-mutation API readback verification.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Set

import requests

from html_postprocessor import PostProcessedArticle
from store_manager import StoreConfig, StoreManager


class ShopifyPublisher:
    """Handles idempotent blog article creation and updates for any configured StoreConfig."""

    def __init__(self, store_manager: StoreManager, store_id: Optional[str] = None) -> None:
        self.store_manager = store_manager
        self.store: StoreConfig = store_manager.get_store(store_id)

    def _graphql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        sess = self.store_manager.proxy_manager.get_shopify_requests_session(
            target_shop_domain=self.store.normalized_shop
        )
        token = self.store_manager.get_valid_access_token(self.store.id)
        resp = sess.post(
            self.store.graphql_endpoint,
            json={"query": query, "variables": variables or {}},
            headers={
                "X-Shopify-Access-Token": token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=35,
        )
        if resp.status_code == 401:
            # Token expired -> force refresh via OAuth client_credentials and retry once
            token = self.store_manager.get_valid_access_token(self.store.id, force_refresh=True)
            resp = sess.post(
                self.store.graphql_endpoint,
                json={"query": query, "variables": variables or {}},
                headers={
                    "X-Shopify-Access-Token": token,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=35,
            )
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("errors"):
            raise RuntimeError(
                f"Shopify GraphQL errors ({self.store.normalized_shop}): {payload['errors']}"
            )
        return payload.get("data") or {}

    def list_blogs(self) -> List[Dict[str, str]]:
        data = self._graphql(
            """
            query ListBlogs {
              blogs(first: 50) {
                nodes {
                  id
                  handle
                  title
                }
              }
            }
            """
        )
        blogs = (data.get("blogs") or {}).get("nodes") or []
        self.store.blogs_cache = [
            {"id": b["id"], "handle": b["handle"], "title": b["title"]} for b in blogs
        ]
        self.store_manager.save_store(self.store.to_dict())
        return self.store.blogs_cache

    def resolve_blog(
        self,
        blog_id_or_handle: Optional[str] = None,
        allow_fallback: bool = False,
    ) -> Dict[str, str]:
        """
        Resolve target Shopify blog by GID or handle.
        By default (`allow_fallback=False`), raises `RuntimeError("BLOG_NOT_FOUND: ...")`
        if the requested/default blog does not exist on the store instead of silently
        falling back to `blogs[0]`.
        """
        blogs = self.store.blogs_cache or self.list_blogs()
        if not blogs:
            raise RuntimeError(
                f"BLOG_NOT_FOUND: No blogs found on Shopify store '{self.store.normalized_shop}'."
            )

        target = (
            blog_id_or_handle
            or self.store.default_blog_id
            or self.store.default_blog_handle
            or ""
        ).strip()

        if not target:
            if allow_fallback:
                return blogs[0]
            raise RuntimeError(
                f"BLOG_NOT_FOUND: Store '{self.store.id}' has no default_blog_handle or default_blog_id configured."
            )

        for b in blogs:
            if b["id"] == target or b["handle"].lower() == target.lower():
                return b

        # Refresh once from API in case a blog was recently created or cache is stale
        blogs = self.list_blogs()
        for b in blogs:
            if b["id"] == target or b["handle"].lower() == target.lower():
                return b

        if allow_fallback and blogs:
            return blogs[0]

        available = ", ".join(f"{b['handle']} ({b['id']})" for b in blogs)
        raise RuntimeError(
            f"BLOG_NOT_FOUND: Target blog '{target}' does not exist on store '{self.store.id}' "
            f"({self.store.normalized_shop}). Available blogs: [{available}]"
        )

    def find_article_by_handle(self, blog_id: str, handle: str) -> Optional[Dict[str, Any]]:
        """Find an article by handle within `blog_id` using full cursor pagination."""
        query = """
        query FindBlogArticle($blogId: ID!, $cursor: String) {
          blog(id: $blogId) {
            id
            handle
            title
            articles(first: 100, after: $cursor) {
              pageInfo {
                hasNextPage
                endCursor
              }
              nodes {
                id
                title
                handle
                publishedAt
                isPublished
                summary
                tags
                author {
                  name
                }
                image {
                  url
                  altText
                }
              }
            }
          }
        }
        """
        cursor: Optional[str] = None
        target_handle = (handle or "").strip().lower()
        while True:
            data = self._graphql(query, {"blogId": blog_id, "cursor": cursor})
            blog_node = data.get("blog") or {}
            conn = blog_node.get("articles") or {}
            articles = conn.get("nodes") or []
            for art in articles:
                if (art.get("handle") or "").strip().lower() == target_handle:
                    return art
            page_info = conn.get("pageInfo") or {}
            if page_info.get("hasNextPage") and page_info.get("endCursor"):
                cursor = page_info["endCursor"]
            else:
                break
        return None

    def find_article_across_blogs(
        self, handle: str, article_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Search across all blogs on the store with cursor pagination for an article matching `article_id` or `handle`."""
        blogs = self.list_blogs()
        target_handle = (handle or "").strip().lower()
        target_id = (article_id or "").strip()

        query = """
        query FindArticleInBlog($blogId: ID!, $cursor: String) {
          blog(id: $blogId) {
            id
            handle
            title
            articles(first: 100, after: $cursor) {
              pageInfo {
                hasNextPage
                endCursor
              }
              nodes {
                id
                title
                handle
                body
                summary
                publishedAt
                isPublished
                tags
                author {
                  name
                }
                image {
                  url
                  altText
                }
                seoTitle: metafield(namespace: "global", key: "title_tag") {
                  value
                }
                seoDescription: metafield(namespace: "global", key: "description_tag") {
                  value
                }
              }
            }
          }
        }
        """
        for b in blogs:
            cursor: Optional[str] = None
            while True:
                data = self._graphql(query, {"blogId": b["id"], "cursor": cursor})
                blog_node = data.get("blog") or {}
                conn = blog_node.get("articles") or {}
                articles = conn.get("nodes") or []
                for art in articles:
                    art_id = (art.get("id") or "").strip()
                    art_handle = (art.get("handle") or "").strip().lower()
                    if (target_id and art_id == target_id) or (
                        target_handle and art_handle == target_handle
                    ):
                        return {
                            "blog_id": b["id"],
                            "blog_handle": b["handle"],
                            "blog_title": b["title"],
                            "article_id": art_id,
                            "title": art.get("title") or "",
                            "handle": art.get("handle") or "",
                            "body_html": art.get("body") or "",
                            "summary": art.get("summary") or "",
                            "published_at": art.get("publishedAt"),
                            "is_published": bool(
                                art.get("isPublished")
                                if art.get("isPublished") is not None
                                else art.get("publishedAt")
                            ),
                            "tags": list(art.get("tags") or []),
                            "author": (art.get("author") or {}).get("name") or "",
                            "featured_image": {
                                "url": (art.get("image") or {}).get("url") or "",
                                "altText": (art.get("image") or {}).get("altText") or "",
                            },
                            "seo_title": (art.get("seoTitle") or {}).get("value")
                            or art.get("title")
                            or "",
                            "seo_description": (art.get("seoDescription") or {}).get("value")
                            or art.get("summary")
                            or "",
                        }
                page_info = conn.get("pageInfo") or {}
                if page_info.get("hasNextPage") and page_info.get("endCursor"):
                    cursor = page_info["endCursor"]
                else:
                    break
        return None

    def readback_article(self, article_id: str) -> Dict[str, Any]:
        """Read back an article directly by GID via GraphQL Admin API after creation/update."""
        query = """
        query ReadbackArticle($id: ID!) {
          article(id: $id) {
            id
            title
            handle
            body
            summary
            publishedAt
            isPublished
            tags
            blog {
              id
              handle
              title
            }
            author {
              name
            }
            image {
              url
              altText
            }
            seoTitle: metafield(namespace: "global", key: "title_tag") {
              value
            }
            seoDescription: metafield(namespace: "global", key: "description_tag") {
              value
            }
          }
        }
        """
        data = self._graphql(query, {"id": article_id})
        art = data.get("article")
        if not art:
            return {"ok": False, "article_id": article_id, "error": "Article not found on readback"}
        blog = art.get("blog") or {}
        body_html = art.get("body") or ""
        return {
            "ok": True,
            "article_id": art.get("id") or article_id,
            "title": art.get("title") or "",
            "handle": art.get("handle") or "",
            "blog_id": blog.get("id") or "",
            "blog_handle": blog.get("handle") or "",
            "is_published": bool(
                art.get("isPublished") if art.get("isPublished") is not None else art.get("publishedAt")
            ),
            "published_at": art.get("publishedAt"),
            "summary": art.get("summary") or "",
            "body_length": len(body_html),
            "author": (art.get("author") or {}).get("name") or "",
            "image": art.get("image"),
            "seo_title": (art.get("seoTitle") or {}).get("value") or "",
            "seo_description": (art.get("seoDescription") or {}).get("value") or "",
        }

    def delete_article(self, article_id: str) -> bool:
        """Delete an article by ID (only used in explicit editor blog-move mode, never in create_only campaigns)."""
        if not article_id:
            return False
        mutation = """
        mutation DeleteArticle($id: ID!) {
          articleDelete(id: $id) {
            deletedArticleId
            userErrors {
              field
              message
            }
          }
        }
        """
        try:
            res = self._graphql(mutation, {"id": article_id})
            del_id = ((res.get("articleDelete") or {}).get("deletedArticleId")) or ""
            return bool(del_id)
        except Exception:
            return False

    def set_seo_metafields(self, owner_id: str, seo_title: str, seo_description: str) -> None:
        mutation = """
        mutation SetArticleSeoMetafields($metafields: [MetafieldsSetInput!]!) {
          metafieldsSet(metafields: $metafields) {
            metafields {
              id
              namespace
              key
              value
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        metafields_input = []
        if seo_title:
            metafields_input.append(
                {
                    "ownerId": owner_id,
                    "namespace": "global",
                    "key": "title_tag",
                    "type": "single_line_text_field",
                    "value": seo_title,
                }
            )
        if seo_description:
            metafields_input.append(
                {
                    "ownerId": owner_id,
                    "namespace": "global",
                    "key": "description_tag",
                    "type": "single_line_text_field",
                    "value": seo_description,
                }
            )
        if not metafields_input:
            return
        res = self._graphql(mutation, {"metafields": metafields_input})
        u_errs = ((res.get("metafieldsSet") or {}).get("userErrors")) or []
        if u_errs:
            raise RuntimeError(f"Shopify metafieldsSet userErrors: {u_errs}")

    def _is_image_url_alive(
        self,
        url: str,
        sess: Optional[requests.Session] = None,
        alive_cache: Optional[Dict[str, bool]] = None,
    ) -> bool:
        """Check whether an image URL returns HTTP 200 through the mandatory Shopify Proxy."""
        if not url or not url.startswith(("http://", "https://")):
            return False
        if alive_cache is not None and url in alive_cache:
            return alive_cache[url]
        if sess is None:
            sess = self.store_manager.proxy_manager.get_shopify_requests_session(
                target_shop_domain=self.store.normalized_shop
            )
        is_alive = False
        try:
            r = sess.head(url, timeout=10, allow_redirects=True)
            if r.status_code == 200:
                is_alive = True
            elif r.status_code in (403, 405):
                r_get = sess.get(url, stream=True, timeout=10, allow_redirects=True)
                is_alive = r_get.status_code == 200
                r_get.close()
        except requests.RequestException:
            is_alive = False

        if alive_cache is not None:
            alive_cache[url] = is_alive
        return is_alive

    def resolve_live_shopify_images(self, article: PostProcessedArticle) -> None:
        """
        Verify and heal article inline and featured images using `ArticleImageService`
        backed by verified live catalog products on the target store (zero hardcoded filenames).
        """
        from article_image_service import ArticleImageService

        img_service = ArticleImageService(
            store_manager=self.store_manager,
            store_id=self.store.id,
        )
        healed_html, healed_hero, manifest = img_service.heal_and_enrich_article_images(
            article_title=article.title,
            handle=article.handle,
            content_id=article.content_id,
            body_html=article.body_html,
            featured_image=article.featured_image,
        )
        manifest_path = img_service.save_media_manifest(manifest)
        article.body_html = healed_html
        article.featured_image = healed_hero
        article.body_image_count = manifest.body_image_count
        article.media_manifest_path = manifest_path
        for rep in manifest.replaced_or_removed:
            act = rep.get("action") or "updated"
            new_src = rep.get("new_src") or ""
            article.resolved_missing_images.append(f"{act}: {new_src}".strip(": "))

    def publish_article(
        self,
        article: PostProcessedArticle,
        blog_id_or_handle: Optional[str] = None,
        is_published: bool = True,
        tags: Optional[List[str]] = None,
        previous_handle: Optional[str] = None,
        publish_mode: str = "upsert",
        owned_article_id: Optional[str] = None,
        protected_article_ids: Optional[Set[str]] = None,
        protected_handles: Optional[Set[str]] = None,
        heal_images: bool = True,
    ) -> Dict[str, Any]:
        """
        Publish or update an article on Shopify:
          - `publish_mode="create_only"`: Never overwrites existing baseline articles.
            If `owned_article_id` is provided (from the same campaign run fixing its own created article),
            updates only that `owned_article_id` after verifying it is not in `protected_article_ids`.
            If a handle collision with a pre-existing article is detected, raises `BASELINE_DUPLICATE`.
          - `publish_mode="upsert"`: Legacy/editor mode that updates by handle or creates if new,
            still protecting `protected_article_ids` if supplied.
        """
        if heal_images:
            self.resolve_live_shopify_images(article)

        blog = self.resolve_blog(blog_id_or_handle, allow_fallback=False)
        blog_id = blog["id"]
        blog_handle = blog["handle"]

        protected_ids = {pid.strip() for pid in (protected_article_ids or set()) if pid}
        protected_h = {ph.strip().lower() for ph in (protected_handles or set()) if ph}

        lookup_handle = (previous_handle or article.handle).strip()
        existing = self.find_article_by_handle(blog_id, article.handle)
        if not existing and lookup_handle.lower() != article.handle.lower():
            existing = self.find_article_by_handle(blog_id, lookup_handle)

        existing_across = self.find_article_across_blogs(
            article.handle, article_id=owned_article_id
        )

        # Enforce `create_only` and baseline protection rules
        target_update_id: Optional[str] = None
        existing_in_other_blog: Optional[Dict[str, Any]] = None

        if publish_mode == "create_only":
            if owned_article_id:
                if owned_article_id in protected_ids:
                    raise RuntimeError(
                        f"BASELINE_DUPLICATE: owned_article_id '{owned_article_id}' is a protected baseline article and cannot be modified."
                    )
                target_update_id = owned_article_id
            else:
                if article.handle.strip().lower() in protected_h:
                    raise RuntimeError(
                        f"BASELINE_DUPLICATE: Handle '{article.handle}' belongs to a protected baseline article on store '{self.store.id}'."
                    )
                if existing:
                    raise RuntimeError(
                        f"BASELINE_DUPLICATE: Article with handle '{article.handle}' already exists in blog '{blog_handle}' ({existing.get('id')}) during create_only mode."
                    )
                if existing_across:
                    raise RuntimeError(
                        f"BASELINE_DUPLICATE: Article with handle '{article.handle}' already exists in blog '{existing_across.get('blog_handle')}' ({existing_across.get('article_id')}) during create_only mode."
                    )
        else:
            # In upsert / update_owned mode, still block overwriting protected_article_ids if specified
            if existing:
                if existing["id"] in protected_ids:
                    raise RuntimeError(
                        f"BASELINE_DUPLICATE: Article '{existing['id']}' ({article.handle}) is protected and cannot be overwritten."
                    )
                target_update_id = existing["id"]
            elif existing_across and existing_across.get("blog_id") != blog_id:
                if existing_across.get("article_id") in protected_ids:
                    raise RuntimeError(
                        f"BASELINE_DUPLICATE: Article '{existing_across.get('article_id')}' is protected and cannot be moved."
                    )
                existing_in_other_blog = existing_across

        if not article.featured_image or not (article.featured_image.get("url") or "").strip():
            raise RuntimeError(
                f"PUBLISH_FAILED: Featured hero image is required before publishing '{article.handle}'."
            )

        article_input: Dict[str, Any] = {
            "title": article.title,
            "handle": article.handle,
            "body": article.body_html,
            "summary": article.summary,
            "author": {"name": article.author},
            "isPublished": bool(is_published),
            "image": {
                "url": article.featured_image["url"].strip(),
                "altText": (article.featured_image.get("altText") or article.title).strip(),
            },
        }
        if tags is not None:
            article_input["tags"] = [t.strip() for t in tags if t and t.strip()]

        if target_update_id:
            mutation = """
            mutation UpdateArticle($id: ID!, $article: ArticleUpdateInput!) {
              articleUpdate(id: $id, article: $article) {
                article {
                  id
                  title
                  handle
                  publishedAt
                  isPublished
                  summary
                  tags
                  image {
                    url
                    altText
                  }
                }
                userErrors {
                  field
                  message
                }
              }
            }
            """
            res = self._graphql(mutation, {"id": target_update_id, "article": article_input})
            op_result = res.get("articleUpdate") or {}
            action = "updated_owned" if publish_mode == "create_only" else "updated"
        else:
            create_inp = dict(article_input)
            create_inp["blogId"] = blog_id
            mutation = """
            mutation CreateArticle($article: ArticleCreateInput!) {
              articleCreate(article: $article) {
                article {
                  id
                  title
                  handle
                  publishedAt
                  isPublished
                  summary
                  tags
                  image {
                    url
                    altText
                  }
                }
                userErrors {
                  field
                  message
                }
              }
            }
            """
            res = self._graphql(mutation, {"article": create_inp})
            op_result = res.get("articleCreate") or {}
            action = "created"

        user_errors = op_result.get("userErrors") or []
        if user_errors:
            # Never silently strip `image` and publish without a hero image!
            raise RuntimeError(f"PUBLISH_FAILED: Shopify article {action} userErrors: {user_errors}")

        saved_article = op_result.get("article") or {}
        article_id = saved_article.get("id")
        if not article_id:
            raise RuntimeError(
                f"PUBLISH_OUTCOME_UNKNOWN: Shopify {action} returned no article ID for '{article.handle}'."
            )
        final_handle = saved_article.get("handle") or article.handle

        # Only in explicit non-create_only mode when moving an article across blogs
        moved_from_blog = None
        if (
            publish_mode != "create_only"
            and article_id
            and existing_in_other_blog
            and existing_in_other_blog.get("article_id")
        ):
            if self.delete_article(existing_in_other_blog["article_id"]):
                moved_from_blog = existing_in_other_blog.get("blog_handle")
                action = f"moved ({moved_from_blog} → {blog_handle})"

        self.set_seo_metafields(article_id, article.seo_title, article.seo_description)
        readback = self.readback_article(article_id)
        metaobject_sync = self.sync_blog_extra_config_metaobject(blog_handle, final_handle)

        myshopify_url = f"https://{self.store.normalized_shop}/blogs/{blog_handle}/{final_handle}"
        public_base = self.store.resolved_public_domain.rstrip("/")
        public_url = f"{public_base}/blogs/{blog_handle}/{final_handle}"

        proxy_cfg = self.store_manager.proxy_manager.get_config()
        return {
            "ok": True,
            "action": action,
            "publish_mode": publish_mode,
            "moved_from_blog": moved_from_blog,
            "store_id": self.store.id,
            "store_name": self.store.name,
            "shop_domain": self.store.normalized_shop,
            "blog_id": blog_id,
            "blog_handle": blog_handle,
            "blog_title": blog.get("title"),
            "article_id": article_id,
            "title": saved_article.get("title") or article.title,
            "handle": final_handle,
            "is_published": bool(
                saved_article.get("isPublished")
                if saved_article.get("isPublished") is not None
                else is_published
            ),
            "published_at": saved_article.get("publishedAt"),
            "tags": list(saved_article.get("tags") or (tags or [])),
            "myshopify_url": myshopify_url,
            "public_url": public_url,
            "image": saved_article.get("image") or readback.get("image"),
            "readback": readback,
            "metaobject_sync": metaobject_sync,
            "proxy_used": proxy_cfg.masked_summary,
            "proxy_fingerprint": proxy_cfg.config_fingerprint,
        }

    def sync_blog_extra_config_metaobject(self, blog_handle: str, article_handle: str) -> Dict[str, Any]:
        """
        If the store uses a `blog_extra_config` metaobject to curate homepage blog cards
        (`homepage_post_handles`) and unified journal listings (`all_blog_handles`),
        prepend the newly published `article_handle` and ensure `blog_handle` is included.
        """
        query = """
        query GetBlogExtraConfig {
          metaobjects(type: "blog_extra_config", first: 5) {
            nodes {
              id
              handle
              fields {
                key
                value
              }
            }
          }
        }
        """
        try:
            data = self._graphql(query)
        except Exception as exc:
            return {"updated": False, "reason": str(exc)}

        nodes = ((data.get("metaobjects") or {}).get("nodes")) or []
        if not nodes:
            return {"updated": False, "reason": "no_blog_extra_config_metaobject"}

        node = nodes[0]
        metaobject_id = node.get("id")
        fields_map = {
            f.get("key"): (f.get("value") or "")
            for f in (node.get("fields") or [])
            if f.get("key")
        }

        raw_home = [
            h.strip() for h in fields_map.get("homepage_post_handles", "").split(",") if h.strip()
        ]
        new_home = [article_handle] + [
            h for h in raw_home if h.lower() != article_handle.lower()
        ]

        raw_blogs = [
            b.strip() for b in fields_map.get("all_blog_handles", "").split(",") if b.strip()
        ]
        new_blogs = [blog_handle] + [b for b in raw_blogs if b.lower() != blog_handle.lower()]

        mutation = """
        mutation UpdateBlogExtraConfig($id: ID!, $metaobject: MetaobjectUpdateInput!) {
          metaobjectUpdate(id: $id, metaobject: $metaobject) {
            metaobject {
              id
              handle
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        variables = {
            "id": metaobject_id,
            "metaobject": {
                "fields": [
                    {"key": "homepage_post_handles", "value": ",".join(new_home)},
                    {"key": "all_blog_handles", "value": ",".join(new_blogs)},
                ]
            },
        }
        try:
            res = self._graphql(mutation, variables)
            u_errs = ((res.get("metaobjectUpdate") or {}).get("userErrors")) or []
            if u_errs:
                return {"updated": False, "userErrors": u_errs}
            return {
                "updated": True,
                "metaobject_id": metaobject_id,
                "homepage_post_handles": new_home[:4],
                "all_blog_handles": new_blogs,
            }
        except Exception as exc:
            return {"updated": False, "reason": str(exc)}
