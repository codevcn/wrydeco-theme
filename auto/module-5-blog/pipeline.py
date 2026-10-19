"""
Modular Multi-Store End-to-End Blog Pipeline (`pipeline.py`).

Orchestrates:
  1. Selecting / loading the target store's credentials (`StoreConfig`) and Editorial Profile (`StoreProfileManager`).
  2. Loading the 5 Zbigtee `/preview` fields for the target article (`ZbigteeUiOperator`).
  3. Post-processing HTML structure, cleaning LaTeX/Vietnamese markers, and synchronizing visible FAQ with JSON-LD (`HtmlPostProcessor`).
  4. Healing, enriching, and deduplicating 4–7 verified product body images + featured hero image via `ArticleImageService`.
  5. Auditing and sanitizing policy/material/product/link claims via `ArticleFactAuditor`.
  6. Enforcing a common pre-publish final gate (`audit_prepublish` + `run_common_final_gate`) across CLI, Web UI, and MCP Server.
  7. Publishing to the selected Shopify store (`ShopifyPublisher`) with `create_only` baseline protection and API readback.
  8. Running live Desktop & Mobile Playwright verification (`verify_published_article`) BEFORE marking Zbigtee published.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from article_fact_auditor import ArticleFactAuditor
from article_image_service import ArticleImageService
from html_postprocessor import (
    VIETNAMESE_ERROR_MARKERS,
    HtmlPostProcessor,
    PostProcessedArticle,
    build_editorial_scoped_css,
)
from proxy_manager import ProxyBlockedError
from shopify_catalog_service import ShopifyCatalogService
from shopify_publisher import ShopifyPublisher
from store_manager import StoreManager
from store_profile_manager import StoreProfileManager
from verify_live import verify_published_article
from zbigtee_ui_operator import ZbigteeUiOperator


def compute_ready_digest(store_id: str, article: PostProcessedArticle) -> str:
    payload = json.dumps(
        {
            "store_id": store_id,
            "handle": article.handle,
            "title": article.title,
            "summary": article.summary,
            "seo_title": article.seo_title,
            "seo_description": article.seo_description,
            "featured_image_url": (article.featured_image or {}).get("url") or "",
            "body_html": article.body_html,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class BlogSyncPipeline:
    """Modular pipeline that operates on any store configured in `StoreManager`."""

    def __init__(
        self,
        store_manager: Optional[StoreManager] = None,
        store_id: Optional[str] = None,
    ) -> None:
        self.store_manager = store_manager or StoreManager()
        self.store = self.store_manager.get_store(store_id)
        self.profile_manager = StoreProfileManager(store_manager=self.store_manager)
        self.catalog_service = ShopifyCatalogService(store_manager=self.store_manager)
        self.fact_auditor = ArticleFactAuditor(
            store_manager=self.store_manager,
            profile_manager=self.profile_manager,
            catalog_service=self.catalog_service,
        )
        self.image_service = ArticleImageService(
            store_manager=self.store_manager,
            store_id=self.store.id,
            catalog_service=self.catalog_service,
        )
        self.zbigtee = ZbigteeUiOperator(self.store_manager, self.store.id)
        self.postprocessor = HtmlPostProcessor(self.store)
        self.publisher = ShopifyPublisher(self.store_manager, self.store.id)

    def audit_prepublish(
        self,
        processed: PostProcessedArticle,
        raw_payload: Optional[Dict[str, Any]] = None,
        sanitize_claims: bool = True,
        heal_images: bool = True,
        min_word_count: int = 900,
        verify_live_urls: bool = True,
    ) -> Dict[str, Any]:
        """
        Common pre-publish gate shared by CLI, Web UI, Campaign Runner, and MCP Server:
          1. Verifies mandatory Proxy readiness.
          2. Heals and enriches inline product images (4–7 body images + featured hero) via `ArticleImageService`.
          3. Sanitizes and audits policy/material/catalog/link claims via `ArticleFactAuditor`.
          4. Refreshes counts/warnings and computes `ready_digest`.
        """
        self.store_manager.proxy_manager.ensure_shopify_proxy_ready(
            target_shop_domain=self.store.normalized_shop
        )

        shop_images = list((raw_payload or {}).get("shop_images") or [])
        manifest_dict: Optional[Dict[str, Any]] = None
        manifest_path = processed.media_manifest_path

        out_dir = Path(__file__).resolve().parent / "output" / self.store.id
        out_dir.mkdir(parents=True, exist_ok=True)
        existing_manifest_file = out_dir / f"{processed.handle}_media_manifest.json"
        existing_html_file = out_dir / f"{processed.handle}_processed.html"
        if not existing_html_file.exists():
            existing_html_file = out_dir / f"{processed.handle}.html"
        existing_json_file = out_dir / f"{processed.handle}_processed.json"
        if not existing_json_file.exists():
            existing_json_file = out_dir / f"{processed.handle}.json"

        reused_healed = False
        if heal_images and existing_manifest_file.exists() and existing_html_file.exists():
            try:
                cached_manifest = json.loads(existing_manifest_file.read_text(encoding="utf-8"))
                if cached_manifest.get("ok") and 4 <= int(cached_manifest.get("unique_body_image_count") or 0) <= 7:
                    processed.body_html = existing_html_file.read_text(encoding="utf-8")
                    hero_mf = cached_manifest.get("featured_image")
                    if isinstance(hero_mf, dict) and hero_mf.get("url"):
                        processed.featured_image = {
                            "url": hero_mf["url"],
                            "altText": hero_mf.get("alt_text") or processed.title,
                        }
                    elif existing_json_file.exists():
                        cached_art = json.loads(existing_json_file.read_text(encoding="utf-8"))
                        if isinstance(cached_art.get("featured_image"), dict) and cached_art["featured_image"].get("url"):
                            processed.featured_image = cached_art["featured_image"]
                    processed.body_image_count = int(cached_manifest.get("body_image_count") or 0)
                    processed.media_manifest_path = str(existing_manifest_file)
                    manifest_path = str(existing_manifest_file)
                    manifest_dict = cached_manifest
                    reused_healed = True
            except Exception:
                reused_healed = False

        if heal_images and not reused_healed:
            healed_html, healed_hero, manifest = self.image_service.heal_and_enrich_article_images(
                article_title=processed.title,
                handle=processed.handle,
                content_id=processed.content_id,
                body_html=processed.body_html,
                featured_image=processed.featured_image,
                shop_images=shop_images,
            )
            manifest_path = self.image_service.save_media_manifest(manifest)
            processed.body_html = healed_html
            processed.featured_image = healed_hero
            processed.body_image_count = manifest.body_image_count
            processed.media_manifest_path = manifest_path
            manifest_dict = json.loads(Path(manifest_path).read_text(encoding="utf-8"))

        applied_claim_edits: List[Dict[str, str]] = []
        fact_audit_path = out_dir / f"{processed.handle}_fact_audit.json"
        reused_fact = False
        if reused_healed and fact_audit_path.exists():
            try:
                cached_fact = json.loads(fact_audit_path.read_text(encoding="utf-8"))
                if cached_fact.get("passed") is True and int(cached_fact.get("blocking_errors_count") or 0) == 0:
                    fact_report_dict = cached_fact
                    reused_fact = True
            except Exception:
                reused_fact = False

        if not reused_fact:
            if sanitize_claims:
                san_res = self.fact_auditor.sanitize_article_claims(
                    store_id=self.store.id,
                    title=processed.title,
                    handle=processed.handle,
                    body_html=processed.body_html,
                    summary=processed.summary,
                    seo_title=processed.seo_title,
                    seo_description=processed.seo_description,
                    content_id=processed.content_id,
                    verify_live_urls=verify_live_urls,
                )
                processed.body_html = san_res["body_html"]
                processed.summary = san_res["summary"]
                processed.seo_description = san_res["seo_description"]
                applied_claim_edits = san_res.get("applied_edits") or []
                fact_report_dict = san_res["report"]
            else:
                fact_report = self.fact_auditor.audit_article(
                    store_id=self.store.id,
                    title=processed.title,
                    handle=processed.handle,
                    body_html=processed.body_html,
                    summary=processed.summary,
                    seo_title=processed.seo_title,
                    seo_description=processed.seo_description,
                    content_id=processed.content_id,
                    verify_live_urls=verify_live_urls,
                )
                fact_report_dict = fact_report.to_dict()

            # Save fact audit report
            fact_audit_path.write_text(
                json.dumps(fact_report_dict, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

        self.postprocessor.refresh_warnings_and_counts(processed)
        saved_paths = self.postprocessor.save_processed_article(processed)
        saved_paths["fact_audit_path"] = str(fact_audit_path)
        if manifest_path:
            saved_paths["media_manifest_path"] = manifest_path

        blocking_reasons: List[str] = []
        if processed.warnings:
            blocking_reasons.extend(processed.warnings)
        if not fact_report_dict.get("passed"):
            for err in fact_report_dict.get("blocking_errors") or []:
                blocking_reasons.append(f"{err.get('code')}: {err.get('message')}")
        if manifest_dict and not manifest_dict.get("ok"):
            blocking_reasons.extend(manifest_dict.get("errors") or [])
        if processed.word_count < min_word_count:
            blocking_reasons.append(
                f"CONTENT_TOO_SHORT: Article has {processed.word_count} words; minimum required is {min_word_count}."
            )

        ready_digest = compute_ready_digest(self.store.id, processed)
        ok = len(blocking_reasons) == 0
        return {
            "ok": ok,
            "store_id": self.store.id,
            "content_id": processed.content_id,
            "handle": processed.handle,
            "title": processed.title,
            "word_count": processed.word_count,
            "body_image_count": processed.body_image_count,
            "ready_digest": ready_digest if ok else "",
            "applied_claim_edits": applied_claim_edits,
            "blocking_reasons": blocking_reasons,
            "fact_audit": fact_report_dict,
            "media_manifest": manifest_dict,
            "saved_paths": saved_paths,
        }

    def postprocess_only(self, content_id_or_slug: str) -> Dict[str, Any]:
        raw_payload = self.zbigtee.get_preview_payload(content_id_or_slug)
        processed: PostProcessedArticle = self.postprocessor.process_preview_payload(raw_payload)
        audit_res = None
        if self.store.is_configured:
            try:
                audit_res = self.audit_prepublish(
                    processed, raw_payload=raw_payload, sanitize_claims=True, heal_images=True
                )
            except ProxyBlockedError:
                raise
            except Exception:
                pass
        saved_paths = self.postprocessor.save_processed_article(processed)
        return {
            "ok": True,
            "store_id": self.store.id,
            "store_name": self.store.name,
            "article": processed.to_dict(),
            "prepublish_audit": audit_res,
            "saved_paths": saved_paths,
        }

    def sync_and_publish(
        self,
        content_id_or_slug: str,
        blog_id_or_handle: Optional[str] = None,
        verify: bool = True,
        publish_mode: str = "upsert",
        owned_article_id: Optional[str] = None,
        protected_article_ids: Optional[Set[str]] = None,
        protected_handles: Optional[Set[str]] = None,
        min_word_count: int = 900,
        approved_ready_digest: Optional[str] = None,
    ) -> Dict[str, Any]:
        # Mandatory Proxy Gate: block immediately if proxy is unconfigured or unstable
        self.store_manager.proxy_manager.ensure_shopify_proxy_ready(
            target_shop_domain=self.store.normalized_shop
        )

        raw_payload = self.zbigtee.get_preview_payload(content_id_or_slug)
        processed = self.postprocessor.process_preview_payload(raw_payload)

        audit_res = self.audit_prepublish(
            processed,
            raw_payload=raw_payload,
            sanitize_claims=True,
            heal_images=True,
            min_word_count=min_word_count,
        )
        saved_paths = audit_res["saved_paths"]

        if not audit_res["ok"]:
            reason_summary = " | ".join(audit_res["blocking_reasons"])
            raise ValueError(
                f"CHẶN CỔNG PRE-PUBLISH — Đã dừng đồng bộ cho bài '{processed.title}' ({processed.handle}): {reason_summary}"
            )

        if approved_ready_digest and approved_ready_digest.strip():
            if audit_res.get("ready_digest") != approved_ready_digest.strip():
                raise ValueError(
                    f"STALE_VALIDATION: Approved ready_digest '{approved_ready_digest}' does not match current ready_digest '{audit_res.get('ready_digest')}'."
                )

        publish_res = self.publisher.publish_article(
            processed,
            blog_id_or_handle=blog_id_or_handle,
            is_published=True,
            publish_mode=publish_mode,
            owned_article_id=owned_article_id,
            protected_article_ids=protected_article_ids,
            protected_handles=protected_handles,
            heal_images=False,  # already healed and audited in audit_prepublish
        )

        live_article_url = publish_res.get("public_url") or publish_res["myshopify_url"]
        # Resilient public URL check: if custom public_url returns 404 (e.g. wrydeco custom domain does not route /blogs),
        # fallback to myshopify_url for live verification and reporting so publication succeeds
        if publish_res.get("public_url") and publish_res.get("myshopify_url"):
            try:
                sess = self.store_manager.proxy_manager.get_shopify_requests_session(self.store.normalized_shop)
                r_pub = sess.get(publish_res["public_url"], timeout=8, allow_redirects=True)
                if r_pub.status_code == 404:
                    live_article_url = publish_res["myshopify_url"]
            except Exception:
                pass
        verification_report = None
        if verify:
            verification_report = verify_published_article(
                self.store_manager,
                self.store.id,
                live_article_url,
                expected_handle=publish_res["handle"],
                expected_title=processed.title,
                min_word_count=min_word_count,
            )

        live_ok = bool(verification_report and verification_report.get("ok")) if verify else True
        zbigtee_publish_sync = None

        if verify and live_ok:
            try:
                zbigtee_publish_sync = self.zbigtee.mark_live_published_on_zbigtee(
                    content_id_or_slug=content_id_or_slug,
                    published_url=live_article_url,
                    article_id=publish_res.get("article_id") or "",
                    note=(
                        f"Synced & Verified Live ({verification_report['passed_count']}/{verification_report['total_checks']} checks passed) via Module 5 Tool"
                    ),
                )
            except Exception as exc:
                self.zbigtee.update_item_publish_state(
                    content_id_or_slug=content_id_or_slug,
                    published_url=live_article_url,
                    article_id=publish_res.get("article_id") or "",
                    marked_on_zbigtee=False,
                )
                zbigtee_publish_sync = {"ok": False, "error": str(exc)}
        else:
            # Never mark Zbigtee published if verification was skipped or failed
            self.zbigtee.update_item_publish_state(
                content_id_or_slug=content_id_or_slug,
                published_url=live_article_url,
                article_id=publish_res.get("article_id") or "",
                marked_on_zbigtee=False,
            )
            if not verify:
                zbigtee_publish_sync = {
                    "ok": False,
                    "skipped": True,
                    "reason": "Live verification required before marking Zbigtee published.",
                }

        zbigtee_ok = bool(zbigtee_publish_sync and zbigtee_publish_sync.get("ok"))
        overall_ok = bool(publish_res.get("ok") and live_ok and (zbigtee_ok if verify else True))
        terminal_state = (
            "COMPLETED"
            if (verify and live_ok and zbigtee_ok)
            else (
                "LIVE_FAILED"
                if (verify and not live_ok)
                else ("ZBIGTEE_SYNC_PENDING" if (verify and live_ok and not zbigtee_ok) else "SHOPIFY_CREATED")
            )
        )

        return {
            "ok": overall_ok,
            "state": terminal_state,
            "store_id": self.store.id,
            "store_name": self.store.name,
            "processed": {
                "title": processed.title,
                "handle": processed.handle,
                "summary": processed.summary,
                "featured_image": processed.featured_image,
                "faq_items_count": processed.faq_items_count,
                "word_count": processed.word_count,
                "body_image_count": processed.body_image_count,
                "media_manifest_path": processed.media_manifest_path,
                "resolved_missing_images": processed.resolved_missing_images,
                "generated_svg_diagrams": processed.generated_svg_diagrams,
                "warnings": processed.warnings,
            },
            "prepublish_audit": audit_res,
            "saved_paths": saved_paths,
            "publish": publish_res,
            "verification": verification_report,
            "zbigtee_publish_sync": zbigtee_publish_sync,
        }

    def get_article_editor_data(
        self, content_id_or_slug: str, fetch_live_shopify: bool = False
    ) -> Dict[str, Any]:
        """Return comprehensive editor fields (local preview/processed + optional live Shopify article state)."""
        raw_payload = self.zbigtee.get_preview_payload(content_id_or_slug)
        content_id = raw_payload.get("content_id") or content_id_or_slug
        slug = (raw_payload.get("slug") or "").strip()

        proc_path = Path(__file__).resolve().parent / "output" / self.store.id / f"{slug}_processed.json"
        if proc_path.exists():
            try:
                proc_dict = json.loads(proc_path.read_text(encoding="utf-8"))
            except Exception:
                proc_dict = self.postprocessor.process_preview_payload(raw_payload).to_dict()
        else:
            proc_dict = self.postprocessor.process_preview_payload(raw_payload).to_dict()

        live_article = None
        if fetch_live_shopify and self.store.is_configured:
            self.store_manager.proxy_manager.ensure_shopify_proxy_ready(
                target_shop_domain=self.store.normalized_shop
            )
            live_article = self.publisher.find_article_across_blogs(
                proc_dict.get("handle") or slug
            )

        inferred_blog_handle = (
            (live_article or {}).get("blog_handle") or proc_dict.get("blog_handle") or ""
        )
        if not inferred_blog_handle:
            rep_path = (
                Path(__file__).resolve().parent
                / "output"
                / self.store.id
                / f"{slug}_verification_report.json"
            )
            if rep_path.exists():
                try:
                    rep_data = json.loads(rep_path.read_text(encoding="utf-8"))
                    art_url = rep_data.get("article_url") or ""
                    if "/blogs/" in art_url:
                        inferred_blog_handle = (
                            art_url.split("/blogs/", 1)[1].split("/", 1)[0].strip()
                        )
                except Exception:
                    pass

        editor_fields = {
            "content_id": content_id,
            "title": (live_article or {}).get("title")
            or proc_dict.get("title")
            or raw_payload.get("title")
            or "",
            "handle": (live_article or {}).get("handle") or proc_dict.get("handle") or slug,
            "previous_handle": (live_article or {}).get("handle")
            or proc_dict.get("handle")
            or slug,
            "blog_handle": inferred_blog_handle
            or self.store.default_blog_handle
            or "buying-guides",
            "default_blog_handle": self.store.default_blog_handle or "buying-guides",
            "blogs": list(self.store.blogs_cache or []),
            "author": (live_article or {}).get("author")
            or proc_dict.get("author")
            or self.store.default_author
            or f"{self.store.name} Studio",
            "is_published": (live_article or {}).get(
                "is_published", proc_dict.get("is_published", True)
            ),
            "tags": (live_article or {}).get("tags") or proc_dict.get("tags") or [],
            "summary": (live_article or {}).get("summary")
            or proc_dict.get("summary")
            or raw_payload.get("meta_description")
            or "",
            "seo_title": (live_article or {}).get("seo_title")
            or proc_dict.get("seo_title")
            or proc_dict.get("title")
            or "",
            "seo_description": (live_article or {}).get("seo_description")
            or proc_dict.get("seo_description")
            or raw_payload.get("meta_description")
            or "",
            "featured_image_url": ((live_article or {}).get("featured_image") or {}).get("url")
            or (proc_dict.get("featured_image") or {}).get("url")
            or "",
            "featured_image_alt": ((live_article or {}).get("featured_image") or {}).get("altText")
            or (proc_dict.get("featured_image") or {}).get("altText")
            or "",
            "body_html": (live_article or {}).get("body_html")
            or proc_dict.get("body_html")
            or raw_payload.get("body_html")
            or "",
            "shop_images": list(raw_payload.get("shop_images") or []),
            "live_article_found": bool(live_article),
            "live_article_id": (live_article or {}).get("article_id") or "",
        }
        return {
            "ok": True,
            "store_id": self.store.id,
            "store_name": self.store.name,
            "editor": editor_fields,
        }

    def update_article_comprehensive(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive Blog Post Update with common pre-publish gate enforcement when `push_to_shopify` is enabled.
        """
        from bs4 import BeautifulSoup

        content_id = (payload.get("content_id") or "").strip()
        raw_payload = self.zbigtee.get_preview_payload(content_id)

        title = (payload.get("title") or raw_payload.get("title") or "").strip()
        handle = (payload.get("handle") or raw_payload.get("slug") or "").strip()
        previous_handle = (payload.get("previous_handle") or raw_payload.get("slug") or handle).strip()
        blog_handle = (payload.get("blog_handle") or self.store.default_blog_handle or "").strip()
        author = (
            payload.get("author") or self.store.default_author or f"{self.store.name} Studio"
        ).strip()
        is_published = bool(payload.get("is_published", True))

        raw_tags = payload.get("tags")
        if isinstance(raw_tags, str):
            tags_list = [t.strip() for t in raw_tags.split(",") if t.strip()]
        elif isinstance(raw_tags, list):
            tags_list = [str(t).strip() for t in raw_tags if str(t).strip()]
        else:
            tags_list = []

        summary = (payload.get("summary") or "").strip()
        seo_title = (payload.get("seo_title") or title).strip()
        seo_description = (payload.get("seo_description") or summary[:160]).strip()
        featured_url = (payload.get("featured_image_url") or "").strip()
        featured_alt = (payload.get("featured_image_alt") or title).strip()
        body_html = (payload.get("body_html") or "").strip()

        save_local = bool(payload.get("save_local", True))
        push_shopify = bool(payload.get("push_to_shopify", payload.get("push_shopify", True)))
        verify = bool(payload.get("verify", False))
        publish_mode = str(payload.get("publish_mode") or "upsert")

        if "<style>" not in body_html:
            body_html = f"{build_editorial_scoped_css(self.store.id)}\n\n{body_html}"

        raw_faq = raw_payload.get("faq_json_ld")
        faq_json_str = (
            json.dumps(raw_faq, ensure_ascii=False)
            if isinstance(raw_faq, dict)
            else str(raw_faq or "").strip()
        )
        if "application/ld+json" not in body_html and faq_json_str:
            body_html = f'{body_html}\n\n<script type="application/ld+json">\n{faq_json_str}\n</script>'

        soup = BeautifulSoup(body_html, "html.parser")
        processed = PostProcessedArticle(
            store_id=self.store.id,
            content_id=raw_payload.get("content_id") or content_id or handle,
            title=title,
            handle=handle,
            summary=summary,
            body_html=body_html,
            seo_title=seo_title,
            seo_description=seo_description,
            author=author,
            featured_image={"url": featured_url, "altText": featured_alt},
            faq_items_count=len(soup.select(".m5-faq-item")),
            resolved_missing_images=[],
            generated_svg_diagrams=[],
            warnings=[],
        )
        self.postprocessor.refresh_warnings_and_counts(processed)

        saved_paths = {}
        if save_local:
            raw_payload["title"] = title
            raw_payload["slug"] = handle
            raw_payload["meta_description"] = seo_description or summary
            raw_payload["body_html"] = body_html
            if featured_url:
                raw_payload["featured_image"] = {"url": featured_url, "altText": featured_alt}

            input_file = (
                Path(__file__).resolve().parent
                / "input"
                / self.store.id
                / f"{processed.content_id}_preview.json"
            )
            if input_file.exists():
                input_file.write_text(
                    json.dumps(raw_payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )

            saved_paths = self.postprocessor.save_processed_article(processed)

        publish_res = None
        verification_report = None
        zbigtee_publish_sync = None
        audit_res = None

        if push_shopify:
            audit_res = self.audit_prepublish(
                processed,
                raw_payload=raw_payload,
                sanitize_claims=True,
                heal_images=True,
            )
            saved_paths = audit_res["saved_paths"]
            if not audit_res["ok"]:
                reason_summary = " | ".join(audit_res["blocking_reasons"])
                raise ValueError(
                    f"CHẶN CỔNG PRE-PUBLISH — Đã dừng cập nhật lên Shopify cho bài '{processed.title}' ({processed.handle}): {reason_summary}"
                )

            publish_res = self.publisher.publish_article(
                processed,
                blog_id_or_handle=blog_handle,
                is_published=is_published,
                tags=tags_list,
                previous_handle=previous_handle,
                publish_mode=publish_mode,
                heal_images=False,
            )

            if verify and is_published:
                verification_report = verify_published_article(
                    self.store_manager,
                    self.store.id,
                    publish_res["myshopify_url"],
                    expected_handle=publish_res["handle"],
                    expected_title=processed.title,
                )

            if is_published and verify and verification_report and verification_report.get("ok"):
                try:
                    zbigtee_publish_sync = self.zbigtee.mark_live_published_on_zbigtee(
                        content_id_or_slug=processed.content_id,
                        published_url=publish_res["myshopify_url"],
                        article_id=publish_res.get("article_id") or "",
                        note="Updated, Verified & Synced via Module 5 Comprehensive Editor",
                    )
                except Exception as exc:
                    self.zbigtee.update_item_publish_state(
                        content_id_or_slug=processed.content_id,
                        published_url=publish_res["myshopify_url"],
                        article_id=publish_res.get("article_id") or "",
                        marked_on_zbigtee=False,
                    )
                    zbigtee_publish_sync = {"ok": False, "error": str(exc)}
            else:
                self.zbigtee.update_item_publish_state(
                    content_id_or_slug=processed.content_id,
                    published_url=publish_res["myshopify_url"],
                    article_id=publish_res.get("article_id") or "",
                    marked_on_zbigtee=False,
                )

        overall_ok = True
        if push_shopify and verify and is_published:
            overall_ok = bool(verification_report and verification_report.get("ok"))

        return {
            "ok": overall_ok,
            "store_id": self.store.id,
            "store_name": self.store.name,
            "article": processed.to_dict(),
            "prepublish_audit": audit_res,
            "saved_paths": saved_paths,
            "publish": publish_res,
            "verification": verification_report,
            "zbigtee_publish_sync": zbigtee_publish_sync,
        }
