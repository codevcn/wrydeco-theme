from __future__ import annotations

import asyncio
import html
import traceback
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from .browser import AmazonBrowser, json_ready
from .config import Settings
from .content import validate_content
from .errors import ContentValidationError, NeedsAttention, PriceValidationError, ShopifyError
from .events import EventCallback, emit
from .io_utils import atomic_write_json, load_json
from .manifest import Manifest, ProductJob
from .media import rehost_images
from .pricing import infer_wood_finish_deltas, money, normalize_name, preset_variants
from .shopify import ShopifyClient, ShopifyConfig
from .state import ProductWorkspace


def _product_settings(job: ProductJob) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "status": "ACTIVE", "vendor": "Wrydeco", "tags": ["source_amazon"],
        "product_type": "", "metafields": [], "publication_ids": [],
        "channels": ["Online Store", "Point of Sale", "Inbox"],
        "author_info": "gid://shopify/Metaobject/195646947385",
        "product_material": "wood", "wood_type": "wood", "bought_amount": 12,
    }
    defaults.update(job.overrides)
    if isinstance(defaults.get("tags"), str):
        defaults["tags"] = [item.strip() for item in defaults["tags"].split(",") if item.strip()]
    if isinstance(defaults.get("channels"), str):
        defaults["channels"] = [item.strip() for item in defaults["channels"].split(",") if item.strip()]
    return defaults


def _metafields_for_product(snapshot: dict[str, Any], content: dict[str, str], job: ProductJob,
                            settings: dict[str, Any], definitions: dict[tuple[str, str], str] | None = None,
                            rich_description: str = "") -> list[dict[str, str]]:
    existing = {(item.get("namespace"), item.get("key")): item
                for item in (snapshot.get("metafields") or {}).get("nodes", [])}
    generated: dict[tuple[str, str], dict[str, str]] = {}
    values: dict[str, tuple[Any, str]] = {
        "seo_product_title": (content["seo_product_title"], "single_line_text_field"),
        "amazon_link": (job.amazon_url, "url"),
        "rich_description": (rich_description or '<div class="description-root"></div>', "multi_line_text_field"),
    }
    for key, default_type in (("author_info", "metaobject_reference"), ("product_material", "single_line_text_field"),
                              ("wood_type", "single_line_text_field"), ("bought_amount", "number_integer")):
        if settings.get(key) is not None:
            values[key] = (settings[key], default_type)
    for key, (value, default_type) in values.items():
        matched = next((item for (namespace, existing_key), item in existing.items() if existing_key == key), None)
        definition = None
        if definitions:
            definition = (("custom", key), definitions.get(("custom", key)))
            if not definition[1]:
                definition = next((item for item in definitions.items() if item[0][1] == key), None)
        namespace = (matched.get("namespace", "custom") if matched else
                     (definition[0][0] if definition else "custom"))
        field_type = (matched.get("type", default_type) if matched else
                      (definition[1] if definition else default_type))
        generated[(namespace, key)] = {"namespace": namespace, "key": key, "type": field_type, "value": str(value)}
    for item in settings.get("metafields", []):
        normalized = dict(item)
        normalized.setdefault("namespace", "custom")
        generated[(normalized["namespace"], normalized["key"])] = normalized
    return list(generated.values())


def _build_rich_description(uploaded: list[dict[str, str]], title: str) -> str:
    escaped_alt = html.escape(title, quote=True)
    images = [
        f'<img alt="{escaped_alt}" src="https://via.placeholder.com/800" '
        f'data-src="{html.escape(item["url"], quote=True)}">'
        for item in uploaded
    ]
    return '<div class="description-root">' + " ".join(images) + "</div>"


def _build_final_variants(pricing: dict[str, Any], snapshot: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]], dict[str, str]]:
    variants = pricing.get("variants") or []
    if not variants:
        raise PriceValidationError("No price-verified variants are available.")
    option_names = [str(item["name"]) for item in (pricing.get("option_types") or [])]
    if not option_names:
        option_names = [item["name"] for item in variants[0]["options"]]
    wood_option = next((item for item in snapshot.get("options", []) if normalize_name(item.get("name")) == "wood finish"), None)
    wood_deltas: dict[str, Decimal] = {}
    if wood_option:
        if len(option_names) + 1 > 3:
            raise PriceValidationError("Amazon options plus existing Wood Finish exceed Shopify's three-option limit.")
        wood_deltas = infer_wood_finish_deltas((snapshot.get("variants") or {}).get("nodes", []))
        option_names.append(wood_option["name"])
    final: list[dict[str, Any]] = []
    for variant in variants:
        base = money(variant.get("verified_total", money(pricing["base_price"]) + money(variant["additional_price"])))
        if wood_deltas:
            for finish, delta in wood_deltas.items():
                final.append({"options": [*variant["options"], {"name": wood_option["name"], "value": finish}],
                              "price": money(base + delta)})
        else:
            final.append({"options": variant["options"], "price": base})
    keys = [tuple((item["name"], item["value"]) for item in variant["options"]) for variant in final]
    if len(keys) != len(set(keys)):
        raise PriceValidationError("Duplicate final Shopify variant combinations were produced.")
    return option_names, final, {key: str(value) for key, value in wood_deltas.items()}


class Pipeline:
    def __init__(self, manifest: Manifest, settings: Settings, *, dry_run: bool = False,
                 event_callback: EventCallback | None = None):
        self.manifest = manifest
        self.settings = settings
        self.dry_run = dry_run
        self.event_callback = event_callback

    def _event(self, event: str, **payload: Any) -> None:
        emit(self.event_callback, event, run_id=self.manifest.digest, **payload)

    async def run(self) -> dict[str, Any]:
        summary = {"run_id": self.manifest.digest, "applied": [], "waiting_for_content": [],
                   "failed": [], "needs_attention": [], "skipped": []}
        browser: AmazonBrowser | None = None
        self._event("pipeline_started", products=len(self.manifest.products), dry_run=self.dry_run)
        try:
            for job in self.manifest.products:
                workspace = ProductWorkspace.create(self.settings.runs_dir, self.manifest.digest, job.asin)
                status = workspace.state().get("status")
                print(f"[{job.asin}] resume status: {status}")
                self._event("product_status", asin=job.asin, status=status)
                if status == "applied":
                    summary["skipped"].append(job.asin)
                    continue
                try:
                    if not workspace.path("source.json").exists() or not workspace.path("pricing.json").exists():
                        if browser is None:
                            browser = await AmazonBrowser(self.settings, self.event_callback).__aenter__()
                        result = await browser.crawl(job.amazon_url, workspace.path("evidence"), job.mode)
                        workspace.write("source.json", result.source)
                        workspace.set_status("crawled")
                        pricing = result.pricing
                        if pricing.get("mode") != "dynamic":
                            preset = job.preset
                            if not preset:
                                raise PriceValidationError("Dynamic customization was not found and no preset override was provided.")
                            base, variants = preset_variants(preset["furniture_type"], preset["price_tier"])
                            pricing = {"mode": "preset", "base_price": base, "option_types": [{"name": "Size"}],
                                       "variants": variants, "verified_all": True}
                        workspace.write("pricing.json", json_ready(pricing))
                        workspace.set_status("price_verified")
                        print(f"[{job.asin}] price verification complete")
                        self._event("product_status", asin=job.asin, status="price_verified")
                    content_path = workspace.path("content.json")
                    if not content_path.exists():
                        workspace.write("content.request.json", {
                            "instructions": "Read source.json and evidence, then create content.json matching scraper/content.schema.json.",
                            "source": "source.json", "schema": str((Path(__file__).parent / "content.schema.json").resolve()),
                        })
                        summary["waiting_for_content"].append(job.asin)
                        print(f"[{job.asin}] waiting for content.json")
                        self._event("product_status", asin=job.asin, status="waiting_for_content")
                        continue
                    content = validate_content(content_path)
                    workspace.set_status("content_ready")
                    self._event("product_status", asin=job.asin, status="content_ready")
                    if self.dry_run:
                        self._event("product_status", asin=job.asin, status="content_ready")
                        summary["skipped"].append(job.asin)
                        continue
                    client = ShopifyClient(ShopifyConfig.from_env(self.settings.env_path))
                    snapshot_path = workspace.path("shopify_before.json")
                    if snapshot_path.exists():
                        snapshot = load_json(snapshot_path)
                    else:
                        snapshot = client.snapshot_product(job.shopify_product_id)
                        workspace.write("shopify_before.json", snapshot)
                    pricing = load_json(workspace.path("pricing.json"))
                    option_names, variants, wood = _build_final_variants(pricing, snapshot)
                    source = load_json(workspace.path("source.json"))
                    urls = source.get("gallery_images") or []
                    if not urls:
                        raise ShopifyError("No verified gallery media is available for replacement.")
                    upload_checkpoint = load_json(workspace.path("uploaded_gallery.json")) if workspace.path("uploaded_gallery.json").exists() else []
                    self._event("shopify_stage", asin=job.asin, stage="gallery_upload")
                    uploaded = rehost_images(
                        client, urls, self.settings.logo_path, workspace.root, content["title"], upload_checkpoint,
                        event_callback=self.event_callback, asin=job.asin,
                    )
                    rich_urls = source.get("aplus_images") or []
                    rich_checkpoint = load_json(workspace.path("uploaded_rich.json")) if workspace.path("uploaded_rich.json").exists() else []
                    uploaded_rich = rehost_images(client, rich_urls, self.settings.logo_path, workspace.root, content["title"],
                                                   rich_checkpoint, prefix="rich", add_logo=False,
                                                   event_callback=self.event_callback, asin=job.asin)
                    rich_description = _build_rich_description(uploaded_rich, content["title"])
                    product_settings = _product_settings(job)
                    definitions = client.product_metafield_definitions()
                    product_settings["metafields"] = _metafields_for_product(
                        snapshot, content, job, product_settings, definitions, rich_description
                    )
                    final_config = {
                        "job": asdict(job), "content": content, "pricing": pricing, "option_names": option_names,
                        "variants": json_ready(variants), "wood_finish_surcharges": wood,
                        "uploaded_media": uploaded, "uploaded_rich": uploaded_rich, "settings": product_settings,
                    }
                    workspace.write("final_config.json", final_config)
                    old_media_ids = [item["id"] for item in (snapshot.get("media") or {}).get("nodes", [])]
                    progress_path = workspace.path("apply_progress.json")
                    progress = load_json(progress_path) if progress_path.exists() else {}
                    if not progress.get("product_set"):
                        self._event("shopify_stage", asin=job.asin, stage="product_set")
                        product = client.product_set(job.shopify_product_id, content, option_names, variants, final_config["settings"])
                        progress.update({"product_set": True, "product": product})
                        workspace.write("apply_progress.json", progress)
                    else:
                        product = progress.get("product") or {"id": snapshot["id"]}
                    if not progress.get("new_media_ids"):
                        self._event("shopify_stage", asin=job.asin, stage="media_attach")
                        progress["new_media_ids"] = client.attach_media(job.shopify_product_id, uploaded, old_media_ids)
                        workspace.write("apply_progress.json", progress)
                    new_media_ids = progress["new_media_ids"]
                    if not progress.get("media_verified"):
                        self._event("shopify_stage", asin=job.asin, stage="media_verify")
                        client.verify_media(job.shopify_product_id, new_media_ids)
                        progress["media_verified"] = True
                        workspace.write("apply_progress.json", progress)
                    if not progress.get("old_media_deleted"):
                        self._event("shopify_stage", asin=job.asin, stage="old_media_cleanup")
                        client.delete_media(job.shopify_product_id, old_media_ids)
                        progress["old_media_deleted"] = True
                        workspace.write("apply_progress.json", progress)
                    if not progress.get("metafields_set"):
                        self._event("shopify_stage", asin=job.asin, stage="metafields")
                        client.set_metafields(job.shopify_product_id, final_config["settings"].get("metafields", []))
                        progress["metafields_set"] = True
                        workspace.write("apply_progress.json", progress)
                    if not progress.get("published"):
                        self._event("shopify_stage", asin=job.asin, stage="publications")
                        publication_ids = final_config["settings"].get("publication_ids", [])
                        channels = final_config["settings"].get("channels")
                        if channels is not None:
                            client.sync_publications(job.shopify_product_id, list(channels))
                        else:
                            client.publish(job.shopify_product_id, publication_ids)
                        progress["published"] = True
                        workspace.write("apply_progress.json", progress)
                    workspace.write("report.json", {"status": "applied", "product": product, "new_media_ids": new_media_ids})
                    workspace.set_status("applied")
                    self._mark_handled(job, workspace)
                    summary["applied"].append(job.asin)
                    self._event("product_status", asin=job.asin, status="applied")
                except NeedsAttention as exc:
                    workspace.write("report.json", {"status": "needs_attention", "error": str(exc)})
                    workspace.set_status("needs_attention", error=str(exc))
                    summary["needs_attention"].append({"asin": job.asin, "error": str(exc), "error_type": type(exc).__name__})
                    self._event("product_status", asin=job.asin, status="needs_attention", error=str(exc), error_type=type(exc).__name__)
                except ShopifyError as exc:
                    workspace.write("report.json", {"status": "needs_attention", "error": str(exc)})
                    workspace.set_status("needs_attention", error=str(exc))
                    summary["needs_attention"].append({"asin": job.asin, "error": str(exc), "error_type": type(exc).__name__})
                    self._event("product_status", asin=job.asin, status="needs_attention", error=str(exc), error_type=type(exc).__name__)
                except ContentValidationError as exc:
                    workspace.write("report.json", {"status": "failed", "error": str(exc),
                                                       "error_type": type(exc).__name__})
                    workspace.set_status("failed", error=str(exc), error_type=type(exc).__name__)
                    summary["failed"].append({"asin": job.asin, "error": str(exc),
                                              "error_type": type(exc).__name__})
                    self._event("product_status", asin=job.asin, status="failed", error=str(exc),
                                error_type=type(exc).__name__)
                except Exception as exc:
                    workspace.write("report.json", {"status": "failed", "error": str(exc),
                                                       "error_type": type(exc).__name__, "traceback": traceback.format_exc()})
                    workspace.set_status("failed", error=str(exc), error_type=type(exc).__name__)
                    summary["failed"].append({"asin": job.asin, "error": str(exc),
                                              "error_type": type(exc).__name__})
                    self._event("product_status", asin=job.asin, status="failed", error=str(exc),
                                error_type=type(exc).__name__)
        finally:
            if browser is not None:
                await browser.__aexit__(None, None, None)
        self._event("pipeline_finished", summary=summary)
        return summary

    def _mark_handled(self, job: ProductJob, workspace: ProductWorkspace) -> None:
        path = Path(__file__).parent / "handled_products.json"
        payload = load_json(path) if path.exists() else {"products": []}
        if isinstance(payload, list):
            payload = {"products": payload}
        products = payload.setdefault("products", [])
        if not any(str(item.get("asin", "")) == job.asin for item in products if isinstance(item, dict)):
            products.append({"asin": job.asin, "shopify_product_id": job.shopify_product_id,
                             "run_id": self.manifest.digest, "report": str(workspace.path("report.json"))})
            atomic_write_json(path, payload)

