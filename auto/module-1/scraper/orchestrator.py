from __future__ import annotations

import asyncio
import threading
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .browser import AmazonBrowser, json_ready
from .config import Settings
from .content import validate_content
from .errors import ContentValidationError, ImageEvidenceError, NeedsAttention, PriceValidationError, ShopifyError
from .io_utils import atomic_write_json, load_json
from .manifest import ProductJob, load_manifest
from .media import prepare_gallery_evidence, rehost_images
from .pipeline import _build_final_variants, _build_rich_description, _metafields_for_product, _product_settings
from .pricing import preset_variants
from .shopify import ShopifyClient, ShopifyConfig
from .store import OrchestratorStore


def settings_for_run(package_root: Path, options: dict[str, Any]) -> Settings:
    return Settings(
        env_path=package_root / ".env",
        profile_dir=package_root / ".runtime" / "browser-profile",
        runs_dir=package_root / "runs",
        logo_path=package_root / "assets" / "logo.png",
        headless=bool(options.get("headless", True)),
        max_combinations=int(options.get("max_combinations", 100)),
        amazon_postal_code=str(options.get("amazon_postal_code", "10001")),
    )


class CrawlService:
    def __init__(self, store: OrchestratorStore):
        self.store = store

    def _browser_event(self, run_id: str, product_id: str, asin: str):
        def callback(event: dict[str, Any]) -> None:
            payload = dict(event)
            event_type = str(payload.pop("event", "crawl_progress"))
            payload.pop("run_id", None)
            payload.setdefault("asin", asin)
            self.store.event(event_type, run_id=run_id, product_id=product_id, source="crawler", **payload)
        return callback

    async def run(self, run_id: str) -> None:
        run = self.store.run_record(run_id)
        manifest = load_manifest(Path(run["manifest_snapshot_path"]))
        jobs = {item.asin: item for item in manifest.products}
        settings = settings_for_run(self.store.package_root, run["options"])
        browser: AmazonBrowser | None = None
        try:
            for product in self.store.products_for_run(run_id):
                if product["status"] not in {"pending", "crawling", "crawled", "price_verified"}:
                    continue
                job = jobs[product["asin"]]
                workspace = self.store.workspace(product)
                source_path = workspace / "source.json"
                pricing_path = workspace / "pricing.json"
                try:
                    if not source_path.exists() or not pricing_path.exists():
                        self.store.set_product_status(product["id"], "crawling", source="crawler")
                        if browser is None:
                            browser = await AmazonBrowser(settings, self._browser_event(run_id, product["id"], product["asin"])).__aenter__()
                        else:
                            browser.event_callback = self._browser_event(run_id, product["id"], product["asin"])
                        result = await browser.crawl(job.amazon_url, workspace / "evidence", job.mode)
                        atomic_write_json(source_path, result.source)
                        self.store.set_product_status(product["id"], "crawled", source="crawler")
                        pricing = result.pricing
                        if pricing.get("mode") != "dynamic":
                            if not job.preset:
                                raise PriceValidationError(
                                    "Dynamic customization was not found and no preset override was provided."
                                )
                            base, variants = preset_variants(job.preset["furniture_type"], job.preset["price_tier"])
                            pricing = {
                                "mode": "preset", "base_price": base,
                                "option_types": [{"name": "Size"}], "variants": variants,
                                "verified_all": True,
                            }
                        atomic_write_json(pricing_path, json_ready(pricing))
                    current_status = self.store.product(product["id"])["status"]
                    if current_status == "pending":
                        self.store.set_product_status(product["id"], "crawling", source="crawler")
                        current_status = "crawling"
                    if current_status == "crawling":
                        self.store.set_product_status(product["id"], "crawled", source="crawler")
                    gallery_manifest = workspace / "evidence" / "gallery" / "manifest.json"
                    if not gallery_manifest.is_file():
                        source_payload = load_json(source_path)
                        try:
                            manifest_payload = prepare_gallery_evidence(
                                list(source_payload.get("gallery_images") or []), workspace / "evidence"
                            )
                        except Exception as exc:
                            raise ImageEvidenceError(str(exc)) from exc
                        self.store.event(
                            "image_evidence_ready", run_id=run_id, product_id=product["id"],
                            source="crawler", asin=product["asin"],
                            image_count=len(manifest_payload["images"]),
                            message=f"Prepared {len(manifest_payload['images'])} sanitized gallery images for Agent review.",
                        )
                    self.store.set_product_status(product["id"], "price_verified", source="crawler")
                    self.store.enqueue_content(product["id"])
                except (NeedsAttention, PriceValidationError, ImageEvidenceError) as exc:
                    atomic_write_json(workspace / "report.json", {
                        "status": "needs_attention", "error": str(exc), "error_type": type(exc).__name__,
                    })
                    self.store.set_product_status(
                        product["id"], "needs_attention", error=str(exc), error_type=type(exc).__name__, source="crawler"
                    )
                except Exception as exc:
                    atomic_write_json(workspace / "report.json", {
                        "status": "failed", "error": str(exc), "error_type": type(exc).__name__,
                        "traceback": traceback.format_exc(),
                    })
                    self.store.set_product_status(
                        product["id"], "failed", error=str(exc), error_type=type(exc).__name__, source="crawler"
                    )
        finally:
            if browser is not None:
                await browser.__aexit__(None, None, None)
        self.store.set_run_crawl_status(run_id, "complete", message="Crawler finished; content tasks are queued.")


class ShopifyApplyService:
    def __init__(self, store: OrchestratorStore):
        self.store = store

    def _event(self, product: dict[str, Any], event_type: str, **payload: Any) -> None:
        self.store.event(
            event_type, run_id=product["run_id"], product_id=product["id"],
            source="shopify", asin=product["asin"], **payload,
        )

    def _media_event(self, product: dict[str, Any]):
        def callback(event: dict[str, Any]) -> None:
            payload = dict(event)
            event_type = str(payload.pop("event", "media_progress"))
            payload.pop("run_id", None)
            payload.pop("asin", None)
            self._event(product, event_type, **payload)
        return callback

    def apply_product(self, product: dict[str, Any]) -> dict[str, Any]:
        run = self.store.run_record(product["run_id"])
        options = run["options"]
        workspace = self.store.workspace(product)
        content = validate_content(workspace / "content.json")
        if options.get("dry_run"):
            report = {"status": "dry_run_complete", "content": content}
            atomic_write_json(workspace / "report.json", report)
            return report

        settings = settings_for_run(self.store.package_root, options)
        job = ProductJob(
            product["amazon_url"], product["shopify_product_id"], product["asin"],
            product["mode"], product["preset"], product["overrides"],
        )
        client = ShopifyClient(ShopifyConfig.from_env(settings.env_path))
        snapshot_path = workspace / "shopify_before.json"
        snapshot = load_json(snapshot_path) if snapshot_path.exists() else client.snapshot_product(job.shopify_product_id)
        if not snapshot_path.exists():
            atomic_write_json(snapshot_path, snapshot)

        pricing = load_json(workspace / "pricing.json")
        option_names, variants, wood = _build_final_variants(pricing, snapshot)
        source = load_json(workspace / "source.json")
        gallery_urls = source.get("gallery_images") or []
        if not gallery_urls:
            raise ShopifyError("No verified gallery media is available for replacement.")

        gallery_checkpoint = workspace / "uploaded_gallery.json"
        uploaded_gallery = rehost_images(
            client, gallery_urls, settings.logo_path, workspace, content["title"],
            load_json(gallery_checkpoint) if gallery_checkpoint.exists() else [],
            event_callback=self._media_event(product), asin=product["asin"],
        )
        rich_checkpoint = workspace / "uploaded_rich.json"
        uploaded_rich = rehost_images(
            client, source.get("aplus_images") or [], settings.logo_path, workspace, content["title"],
            load_json(rich_checkpoint) if rich_checkpoint.exists() else [],
            prefix="rich", add_logo=False, event_callback=self._media_event(product), asin=product["asin"],
        )
        rich_description = _build_rich_description(uploaded_rich, content["title"])
        product_settings = _product_settings(job)
        product_settings["metafields"] = _metafields_for_product(
            snapshot, content, job, product_settings, client.product_metafield_definitions(), rich_description
        )
        final_config = {
            "job": asdict(job), "content": content, "pricing": pricing,
            "option_names": option_names, "variants": json_ready(variants),
            "wood_finish_surcharges": wood, "uploaded_media": uploaded_gallery,
            "uploaded_rich": uploaded_rich, "settings": product_settings,
        }
        atomic_write_json(workspace / "final_config.json", final_config)

        old_media_ids = [item["id"] for item in (snapshot.get("media") or {}).get("nodes", [])]
        progress_path = workspace / "apply_progress.json"
        progress = load_json(progress_path) if progress_path.exists() else {}
        if not progress.get("product_set"):
            self._event(product, "shopify_stage", stage="product_set")
            shopify_product = client.product_set(
                job.shopify_product_id, content, option_names, variants, final_config["settings"]
            )
            progress.update({"product_set": True, "product": shopify_product})
            atomic_write_json(progress_path, progress)
        else:
            shopify_product = progress.get("product") or {"id": snapshot["id"]}
        if not progress.get("new_media_ids"):
            self._event(product, "shopify_stage", stage="media_attach")
            progress["new_media_ids"] = client.attach_media(
                job.shopify_product_id, uploaded_gallery, old_media_ids
            )
            atomic_write_json(progress_path, progress)
        new_media_ids = progress["new_media_ids"]
        if not progress.get("media_verified"):
            self._event(product, "shopify_stage", stage="media_verify")
            client.verify_media(job.shopify_product_id, new_media_ids)
            progress["media_verified"] = True
            atomic_write_json(progress_path, progress)
        if not progress.get("old_media_deleted"):
            self._event(product, "shopify_stage", stage="old_media_cleanup")
            client.delete_media(job.shopify_product_id, old_media_ids)
            progress["old_media_deleted"] = True
            atomic_write_json(progress_path, progress)
        if not progress.get("metafields_set"):
            self._event(product, "shopify_stage", stage="metafields")
            client.set_metafields(job.shopify_product_id, final_config["settings"].get("metafields", []))
            progress["metafields_set"] = True
            atomic_write_json(progress_path, progress)
        if not progress.get("published"):
            self._event(product, "shopify_stage", stage="publications")
            channels = final_config["settings"].get("channels")
            if channels is not None:
                client.sync_publications(job.shopify_product_id, list(channels))
            else:
                client.publish(job.shopify_product_id, final_config["settings"].get("publication_ids", []))
            progress["published"] = True
            atomic_write_json(progress_path, progress)
        report = {"status": "applied", "product": shopify_product, "new_media_ids": new_media_ids}
        atomic_write_json(workspace / "report.json", report)
        return report


class RunCoordinator:
    def __init__(self, store: OrchestratorStore, readiness_gate: threading.Event | None = None):
        self.store = store
        self.crawler = CrawlService(store)
        self.shopify = ShopifyApplyService(store)
        self.readiness_gate = readiness_gate
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    def _wait_until_ready(self) -> bool:
        if self.readiness_gate is None:
            return True
        while not self._stop.is_set():
            if self.readiness_gate.wait(0.5):
                return True
        return False

    def start(self, *, crawler: bool = True, apply: bool = True) -> None:
        self.store.recover()
        if crawler:
            self._start_thread("scraper-crawler", self._crawl_loop)
        if apply:
            self._start_thread("scraper-shopify", self._apply_loop)

    def _start_thread(self, name: str, target: Any) -> None:
        if any(thread.name == name and thread.is_alive() for thread in self._threads):
            return
        thread = threading.Thread(target=target, daemon=True, name=name)
        self._threads.append(thread)
        thread.start()

    def stop(self) -> None:
        self._stop.set()
        with self.store._condition:
            self.store._condition.notify_all()
        for thread in self._threads:
            thread.join(timeout=3)

    def _crawl_loop(self) -> None:
        while not self._stop.is_set():
            if not self._wait_until_ready():
                return
            run_id = self.store.claim_next_crawl_run()
            if not run_id:
                self.store.wait_for_change(0.5)
                continue
            try:
                asyncio.run(self.crawler.run(run_id))
            except Exception as exc:
                self.store.event(
                    "crawler_error", run_id=run_id, source="crawler", message=str(exc),
                    error_type=type(exc).__name__,
                )
                self.store.set_run_crawl_status(run_id, "interrupted", message=f"Crawler failed: {exc}")

    def _apply_loop(self) -> None:
        while not self._stop.is_set():
            if not self._wait_until_ready():
                return
            product = self.store.claim_next_apply()
            if not product:
                self.store.wait_for_change(0.5)
                continue
            try:
                report = self.shopify.apply_product(product)
                self.store.finish_apply(product["id"], str(report["status"]))
            except ContentValidationError as exc:
                atomic_write_json(self.store.workspace(product) / "report.json", {
                    "status": "failed", "error": str(exc), "error_type": type(exc).__name__,
                })
                self.store.finish_apply(
                    product["id"], "failed", error=str(exc), error_type=type(exc).__name__
                )
            except (NeedsAttention, ShopifyError) as exc:
                atomic_write_json(self.store.workspace(product) / "report.json", {
                    "status": "needs_attention", "error": str(exc), "error_type": type(exc).__name__,
                })
                self.store.finish_apply(
                    product["id"], "needs_attention", error=str(exc), error_type=type(exc).__name__
                )
            except Exception as exc:
                atomic_write_json(self.store.workspace(product) / "report.json", {
                    "status": "needs_attention", "error": str(exc), "error_type": type(exc).__name__,
                    "traceback": traceback.format_exc(),
                })
                self.store.finish_apply(
                    product["id"], "needs_attention", error=str(exc), error_type=type(exc).__name__
                )
