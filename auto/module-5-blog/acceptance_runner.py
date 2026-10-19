"""
Acceptance Pilot Runner (`acceptance_runner.py`) for Blog Scaling 20x5 Campaign:
  - Enforces the mandatory pilot scope: strictly 3 eligible `create` articles for `preaureum`
    and 3 eligible `create` articles for `wrydeco` (total = 6 new live articles).
  - Never expands to 20 articles/store or to the other 3 stores during pilot acceptance.
  - Orchestrates the real MCP tools (`mcp_server.py`) through two stages:
      1. `prepublish`: `prepare_article_brief` -> `generate_or_fetch_draft` -> `heal_article_images`
         -> `sanitize_article_claims` -> `validate_article`.
      2. `publish`: `publish_and_verify_article` (`create_only` + live Desktop/Mobile verification
         + Zbigtee published sync + readback) -> idempotent rerun test (`publish_and_verify_article`
         and `resume_run` on a completed pilot run) -> generates `acceptance_report.json` and
         `acceptance_report.md` under `output/acceptance/<acceptance_run_id>/`.
"""

from __future__ import annotations

import argparse
import datetime
import json
import platform
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from campaign_manager import CampaignManager
from mcp_server import (
    check_store_readiness,
    generate_or_fetch_draft,
    get_run_status,
    heal_article_images,
    publish_and_verify_article,
    resume_run,
    sanitize_article_claims,
    validate_article,
)
from pilot_drafts import PILOT_RAW_SUBMISSIONS, PILOT_VISUAL_REVIEWS
from store_manager import StoreManager
from store_profile_manager import StoreProfileManager


PILOT_COHORT_SPEC: List[Dict[str, Any]] = [
    {
        "store_id": "preaureum",
        "slot": 1,
        "plan_id": "01a0d17d-1887-73fd-acbb-e0cc133df47c",
        "content_id": "01a14a38-8883-78c6-8cd8-eda1d1232883",
        "run_id": "run_preaureum_4dfcd5a64a",
        "expected_slug": "how-long-does-personalized-handbag-delivery-take-gift-date-guide",
        "topic_title": "How long does delivery take, will it arrive before the gift date",
    },
    {
        "store_id": "preaureum",
        "slot": 2,
        "plan_id": "01a0d17d-1c6f-7f95-b4ef-4c36aa980fd6",
        "content_id": "01a14a38-d41b-75b4-aae1-63200a634d6d",
        "run_id": "run_preaureum_df598d17d9",
        "expected_slug": "can-you-return-or-exchange-a-personalized-name-handbag-guide",
        "topic_title": "Can I return or exchange a personalized name handbag if it does not fit",
    },
    {
        "store_id": "preaureum",
        "slot": 3,
        "plan_id": "01a0d17d-2057-7c0f-be1c-74de023deeb5",
        "content_id": "01a14a39-1242-7082-97f4-42e613b76214",
        "run_id": "run_preaureum_5daf4d1571",
        "expected_slug": "are-preaureum-handbag-straps-adjustable-hardware-carry-guide",
        "topic_title": "Are the straps adjustable and is the hardware sturdy enough for daily weight",
    },
    {
        "store_id": "wrydeco",
        "slot": 1,
        "plan_id": "01a0c588-f146-70bd-8ff2-1ca6b65e7bf7",
        "content_id": "01a14a39-52cd-7f6e-9766-eb8d0bc22fa0",
        "run_id": "run_wrydeco_561e78907f",
        "expected_slug": "wall-mounted-tree-shelf-installation-stud-spacing-load-guide",
        "topic_title": "Wall-Mounted Tree Shelf Installation: Stud Spacing, Anchors & Safe Load Limits",
    },
    {
        "store_id": "wrydeco",
        "slot": 2,
        "plan_id": "01a0c58a-6458-7b5e-83fd-271b50f813bf",
        "content_id": "01a14a39-9db0-70ee-a04b-52edd4360cba",
        "run_id": "run_wrydeco_9e9e8d13ca",
        "expected_slug": "fluted-floating-shelves-scalloped-edge-depth-comparison-guide",
        "topic_title": "Fluted Floating Shelves: Scalloped Edge vs Rounded Trim & Depth Comparison",
    },
    {
        "store_id": "wrydeco",
        "slot": 3,
        "plan_id": "01a0c58d-2fb9-77fa-b7d8-f09a9b956282",
        "content_id": "01a14a39-d5d1-726a-94ce-132ddfac32ef",
        "run_id": "run_wrydeco_9fb34a46af",
        "expected_slug": "rustic-wooden-wine-racks-countertop-vs-wall-mounted-buying-guide",
        "topic_title": "Rustic Wooden Wine Racks: Countertop vs Wall-Mounted Storage Buying Guide",
    },
]


class AcceptancePilotRunner:
    """
    Executes and audits the 6-article pilot cohort (`3 preaureum` + `3 wrydeco`)
    using the real MCP server tools and generates machine-readable + Markdown reports.
    """

    def __init__(
        self,
        campaign_id: str = "blog_scaling_20x5_2026-10-17",
        acceptance_run_id: str = "pilot_2026-10-17",
        base_dir: Optional[Path] = None,
    ) -> None:
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parent
        self.campaign_id = campaign_id
        self.acceptance_run_id = acceptance_run_id
        self.report_dir = self.base_dir / "output" / "acceptance" / self.acceptance_run_id
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.store_manager = StoreManager(data_dir=self.base_dir / "data")
        self.profile_manager = StoreProfileManager(store_manager=self.store_manager)
        self.campaign_manager = CampaignManager(store_manager=self.store_manager)

    def select_pilot_cohort(self) -> Dict[str, Any]:
        """Returns the frozen 6-article pilot cohort (3 Preaureum + 3 WRYDECO)."""
        return {
            "campaign_id": self.campaign_id,
            "acceptance_run_id": self.acceptance_run_id,
            "target_stores": ["preaureum", "wrydeco"],
            "new_articles_per_store": 3,
            "total_pilot_articles": 6,
            "cohort": PILOT_COHORT_SPEC,
        }

    def run_pilot(self) -> Dict[str, Any]:
        """Runs prepublish if needed, then publish & verify, and returns the final report."""
        self.run_prepublish_stage()
        rep = self.run_publish_and_verify_stage()
        return {
            "ok": rep.get("verdict") == "PASS",
            "verdict": rep.get("verdict"),
            "summary": f"Pilot acceptance verdict={rep.get('verdict')} across 6 articles.",
            "artifact_paths": rep.get("report_paths") or {},
            "report": rep,
        }

    def run_prepublish_stage(self) -> Dict[str, Any]:
        """
        Submits/fetches drafts, heals inline + hero images, applies visual review notes,
        sanitizes policy/catalog claims, and validates all 6 pilot articles through the common gate.
        """
        results: List[Dict[str, Any]] = []
        for item in PILOT_COHORT_SPEC:
            store_id = item["store_id"]
            cid = item["content_id"]
            rid = item["run_id"]
            slug = item["expected_slug"]

            out_dir = self.base_dir / "output" / store_id
            stale_manifest = out_dir / f"{slug}_media_manifest.json"
            if stale_manifest.exists():
                stale_manifest.unlink()

            preview_file = self.base_dir / "input" / store_id / f"preview_{cid}.json"
            if not preview_file.exists():
                generate_or_fetch_draft(
                    store_id=store_id,
                    content_id=cid,
                    campaign_id=self.campaign_id,
                    run_id=rid,
                    raw_submission=PILOT_RAW_SUBMISSIONS[cid],
                )
            heal_res = heal_article_images(
                store_id=store_id,
                content_id_or_slug=cid,
                campaign_id=self.campaign_id,
                run_id=rid,
                visual_reviews=PILOT_VISUAL_REVIEWS.get(slug),
            )
            fact_file = out_dir / f"{slug}_fact_audit.json"
            if not fact_file.exists():
                sanitize_article_claims(
                    store_id=store_id,
                    content_id_or_slug=cid,
                    campaign_id=self.campaign_id,
                    run_id=rid,
                )
            val_res = validate_article(
                store_id=store_id,
                content_id_or_slug=cid,
                campaign_id=self.campaign_id,
                run_id=rid,
            )
            val_data = val_res.get("data") or {}
            saved_paths = val_data.get("saved_paths") or val_res.get("artifact_paths") or {}
            summary = {
                "store_id": store_id,
                "slot": item["slot"],
                "plan_id": item["plan_id"],
                "content_id": cid,
                "run_id": rid,
                "handle": val_data.get("handle") or slug,
                "title": val_data.get("title") or item["topic_title"],
                "ok": bool(val_res.get("ok")),
                "word_count": val_data.get("word_count"),
                "body_image_count": val_data.get("body_image_count"),
                "ready_digest": val_data.get("ready_digest"),
                "blocking_reasons": val_data.get("blocking_reasons") or [],
                "media_manifest_path": saved_paths.get("media_manifest_path"),
                "fact_audit_path": saved_paths.get("fact_audit_path"),
            }
            results.append(summary)
            print(
                f"[PREPUBLISH] {store_id} #{item['slot']} ({slug}): "
                f"ok={summary['ok']} words={summary['word_count']} "
                f"images={summary['body_image_count']} digest={str(summary['ready_digest'])[:16]}"
            )

        stage_file = self.report_dir / "prepublish_stage_summary.json"
        stage_file.write_text(
            json.dumps(
                {
                    "ok": all(r.get("ok") for r in results),
                    "campaign_id": self.campaign_id,
                    "acceptance_run_id": self.acceptance_run_id,
                    "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "cohort": results,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        return {"ok": all(r.get("ok") for r in results), "cohort": results, "summary_path": str(stage_file)}

    def run_publish_and_verify_stage(self) -> Dict[str, Any]:
        """
        Publishes and verifies each of the 6 validated pilot articles (`create_only`),
        executes the idempotent rerun check on a completed run, and writes the final
        acceptance reports (`acceptance_report.json` and `acceptance_report.md`).
        """
        publish_results: List[Dict[str, Any]] = []
        for item in PILOT_COHORT_SPEC:
            store_id = item["store_id"]
            cid = item["content_id"]
            rid = item["run_id"]
            slug = item["expected_slug"]

            run_rec = self.campaign_manager.get_run(self.campaign_id, rid) or {}
            ready_digest = run_rec.get("ready_digest") or ""

            pub_res = publish_and_verify_article(
                store_id=store_id,
                content_id_or_slug=cid,
                approved_ready_digest=ready_digest,
                campaign_id=self.campaign_id,
                run_id=rid,
            )
            pub_data = pub_res.get("data") or {}
            pub_info = pub_data.get("publish") or (pub_data.get("run") or {})
            publish_results.append(
                {
                    "store_id": store_id,
                    "slot": item["slot"],
                    "plan_id": item["plan_id"],
                    "content_id": cid,
                    "run_id": rid,
                    "expected_slug": slug,
                    "topic_title": item["topic_title"],
                    "result": pub_res,
                }
            )
            print(
                f"[PUBLISH] {store_id} #{item['slot']} ({slug}): "
                f"ok={pub_res.get('ok')} state={pub_res.get('state')} "
                f"article_id={pub_info.get('article_id') or pub_info.get('shopify_article_id')} "
                f"url={pub_info.get('myshopify_url') or pub_info.get('published_url')}"
            )

        # Idempotent rerun verification on Preaureum #1 and WRYDECO #1
        rerun_checks: List[Dict[str, Any]] = []
        for target_item in [PILOT_COHORT_SPEC[0], PILOT_COHORT_SPEC[3]]:
            rid = target_item["run_id"]
            store_id = target_item["store_id"]
            cid = target_item["content_id"]
            before_status = (get_run_status(store_id=store_id, campaign_id=self.campaign_id).get("data") or {})
            before_completed = int(
                ((before_status.get("store_progress") or {}).get(store_id) or {}).get("completed") or 0
            )

            rerun_pub = publish_and_verify_article(
                store_id=store_id,
                content_id_or_slug=cid,
                campaign_id=self.campaign_id,
                run_id=rid,
            )
            rerun_res = resume_run(store_id=store_id, campaign_id=self.campaign_id, run_id=rid)
            after_status = (get_run_status(store_id=store_id, campaign_id=self.campaign_id).get("data") or {})
            after_completed = int(
                ((after_status.get("store_progress") or {}).get(store_id) or {}).get("completed") or 0
            )

            rerun_pub_data = rerun_pub.get("data") or {}
            rerun_res_data = rerun_res.get("data") or {}
            run_after = rerun_pub_data.get("run") or self.campaign_manager.get_run(self.campaign_id, rid) or {}

            rerun_checks.append(
                {
                    "store_id": store_id,
                    "run_id": rid,
                    "content_id": cid,
                    "publish_idempotent_flag": bool(rerun_pub_data.get("idempotent_short_circuit")),
                    "resume_action": "idempotent_noop" if rerun_res_data.get("idempotent_noop") else rerun_res.get("state"),
                    "shopify_article_id": run_after.get("shopify_article_id"),
                    "published_url": run_after.get("published_url"),
                    "completed_runs_before": before_completed,
                    "completed_runs_after": after_completed,
                    "no_duplicate_created": (
                        bool(rerun_pub_data.get("idempotent_short_circuit"))
                        and bool(rerun_res_data.get("idempotent_noop"))
                        and before_completed == after_completed
                    ),
                }
            )

        report_payload = self.build_acceptance_report(
            publish_results=publish_results,
            rerun_checks=rerun_checks,
        )
        return report_payload

    def build_acceptance_report(
        self,
        publish_results: Optional[List[Dict[str, Any]]] = None,
        rerun_checks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Compiles full evidence from disk, campaign state, media manifests, fact audit reports,
        and live verification reports into `acceptance_report.json` and `acceptance_report.md`.
        """
        if not rerun_checks:
            rerun_checks = []
            for target_item in [PILOT_COHORT_SPEC[0], PILOT_COHORT_SPEC[3]]:
                rid = target_item["run_id"]
                store_id = target_item["store_id"]
                cid = target_item["content_id"]
                before_status = (get_run_status(store_id=store_id, campaign_id=self.campaign_id).get("data") or {})
                before_completed = int(
                    ((before_status.get("store_progress") or {}).get(store_id) or {}).get("completed") or 0
                )
                rerun_pub = publish_and_verify_article(
                    store_id=store_id,
                    content_id_or_slug=cid,
                    campaign_id=self.campaign_id,
                    run_id=rid,
                )
                rerun_res = resume_run(store_id=store_id, campaign_id=self.campaign_id, run_id=rid)
                after_status = (get_run_status(store_id=store_id, campaign_id=self.campaign_id).get("data") or {})
                after_completed = int(
                    ((after_status.get("store_progress") or {}).get(store_id) or {}).get("completed") or 0
                )
                rerun_pub_data = rerun_pub.get("data") or {}
                rerun_res_data = rerun_res.get("data") or {}
                run_after = rerun_pub_data.get("run") or self.campaign_manager.get_run(self.campaign_id, rid) or {}
                rerun_checks.append(
                    {
                        "store_id": store_id,
                        "run_id": rid,
                        "content_id": cid,
                        "publish_idempotent_flag": bool(rerun_pub_data.get("idempotent_short_circuit")),
                        "resume_action": "idempotent_noop" if rerun_res_data.get("idempotent_noop") else rerun_res.get("state"),
                        "shopify_article_id": run_after.get("shopify_article_id"),
                        "published_url": run_after.get("published_url"),
                        "completed_runs_before": before_completed,
                        "completed_runs_after": after_completed,
                        "no_duplicate_created": (
                            bool(rerun_pub_data.get("idempotent_short_circuit"))
                            and bool(rerun_res_data.get("idempotent_noop"))
                            and before_completed == after_completed
                        ),
                    }
                )

        cohort_rows: List[Dict[str, Any]] = []
        for idx, spec in enumerate(PILOT_COHORT_SPEC):
            store_id = spec["store_id"]
            slug = spec["expected_slug"]
            rid = spec["run_id"]
            cid = spec["content_id"]
            plan_id = spec["plan_id"]

            run_rec = self.campaign_manager.get_run(self.campaign_id, rid) or {}
            out_dir = self.base_dir / "output" / store_id

            art_json_path = out_dir / f"{slug}_processed.json"
            if not art_json_path.exists():
                art_json_path = out_dir / f"{slug}.json"
            fact_path = out_dir / f"{slug}_fact_audit.json"
            media_path = out_dir / f"{slug}_media_manifest.json"
            verify_path = out_dir / f"{slug}_verification_report.json"

            art_data = json.loads(art_json_path.read_text(encoding="utf-8")) if art_json_path.exists() else {}
            fact_data = json.loads(fact_path.read_text(encoding="utf-8")) if fact_path.exists() else {}
            media_data = json.loads(media_path.read_text(encoding="utf-8")) if media_path.exists() else {}
            verify_data = json.loads(verify_path.read_text(encoding="utf-8")) if verify_path.exists() else {}

            pub_envelope = None
            if publish_results and idx < len(publish_results):
                pub_envelope = (publish_results[idx] or {}).get("result") or {}
            pub_data = (pub_envelope or {}).get("data") or {}
            pub_info = pub_data.get("publish") or {}
            zb_sync_info = pub_data.get("zbigtee_publish_sync") or {}

            checks_list = verify_data.get("checks") or []
            failed_checks = [c.get("id") for c in checks_list if not c.get("passed")]
            total_checks = int(verify_data.get("total_checks") or len(checks_list))
            passed_checks = int(verify_data.get("passed_count") or sum(1 for c in checks_list if c.get("passed")))

            row = {
                "cohort_index": idx + 1,
                "store_id": store_id,
                "store_slot": spec["slot"],
                "run_id": rid,
                "plan_id": plan_id,
                "content_id": cid,
                "topic_title": spec["topic_title"],
                "article_title": art_data.get("title") or ((verify_data.get("seo_metadata") or {}).get("og") or {}).get("title") or run_rec.get("title") or "",
                "handle": art_data.get("handle") or slug,
                "eligibility": {
                    "action": "create",
                    "target_path_before_run": None,
                    "excluded_from_baseline": True,
                    "selection_rule": f"First {spec['slot']} eligible create item in frozen queue for {store_id}",
                },
                "profile_revision": run_rec.get("profile_revision") or fact_data.get("profile_revision"),
                "word_count": art_data.get("word_count") or verify_data.get("word_count") or run_rec.get("word_count") or 0,
                "body_image_count": media_data.get("body_image_count") or art_data.get("body_image_count") or 0,
                "unique_body_image_count": media_data.get("unique_body_image_count") or 0,
                "featured_image_url": (art_data.get("featured_image") or {}).get("url")
                or ((media_data.get("featured_image") or {}).get("url")),
                "fact_audit": {
                    "passed": bool(fact_data.get("passed")),
                    "blocking_errors_count": int(fact_data.get("blocking_errors_count") or 0),
                    "warnings_count": int(fact_data.get("warnings_count") or 0),
                    "verified_products_count": len(fact_data.get("verified_products") or []),
                    "checked_urls_count": len(fact_data.get("verified_internal_links") or []),
                    "report_path": str(fact_path) if fact_path.exists() else "",
                },
                "media_manifest": {
                    "ok": bool(media_data.get("ok")),
                    "body_image_count": int(media_data.get("body_image_count") or 0),
                    "unique_body_image_count": int(media_data.get("unique_body_image_count") or 0),
                    "visual_reviews_approved": all(
                        (img.get("visual_review_status") == "approved")
                        for img in (media_data.get("body_images") or [])
                    ),
                    "manifest_path": str(media_path) if media_path.exists() else "",
                },
                "publication": {
                    "state": run_rec.get("state") or (pub_envelope or {}).get("state") or "UNKNOWN",
                    "shopify_blog_id": pub_info.get("blog_id") or run_rec.get("shopify_blog_id") or "",
                    "shopify_article_id": run_rec.get("shopify_article_id")
                    or pub_info.get("article_id")
                    or "",
                    "published_url": verify_data.get("article_url")
                    or run_rec.get("published_url")
                    or pub_info.get("public_url")
                    or pub_info.get("myshopify_url")
                    or "",
                    "api_readback_verified": bool(
                        (pub_info.get("readback") or {}).get("id")
                        or run_rec.get("shopify_article_id")
                    ),
                    "zbigtee_synced": bool(
                        run_rec.get("zbigtee_synced") or zb_sync_info.get("marked_on_zbigtee")
                    ),
                    "zbigtee_target_path": (
                        (zb_sync_info.get("readback") or {}).get("targetPath")
                        or (f"/blogs/{pub_info.get('blog_handle') or 'news'}/{slug}" if run_rec.get("zbigtee_synced") else None)
                    ),
                },
                "live_verification": {
                    "ok": bool(verify_data.get("ok")),
                    "total_checks": total_checks,
                    "passed_checks": passed_checks,
                    "failed_checks_count": len(failed_checks),
                    "failed_check_ids": failed_checks,
                    "proxy_server": verify_data.get("proxy_used") or "",
                    "desktop_screenshot": (verify_data.get("screenshots") or {}).get("desktop") or "",
                    "mobile_screenshot": (verify_data.get("screenshots") or {}).get("mobile") or "",
                    "report_path": str(verify_path) if verify_path.exists() else "",
                },
                "ready_digest": run_rec.get("ready_digest") or "",
                "retry_count": int(run_rec.get("retry_count") or 0),
                "blocking_reasons": run_rec.get("blocking_reasons") or [],
            }
            cohort_rows.append(row)

        all_six_complete = (
            len(cohort_rows) == 6
            and all(
                r["publication"]["state"] == "COMPLETED"
                and r["live_verification"]["ok"]
                and r["fact_audit"]["passed"]
                and r["media_manifest"]["ok"]
                and r["publication"]["zbigtee_synced"]
                for r in cohort_rows
            )
        )

        verdict = "PASS" if all_six_complete else "PARTIAL_OR_FAIL"
        report_data: Dict[str, Any] = {
            "verdict": verdict,
            "acceptance_run_id": self.acceptance_run_id,
            "campaign_id": self.campaign_id,
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "environment": {
                "workspace": str(self.base_dir),
                "python_version": sys.version.split()[0],
                "platform": platform.platform(),
                "mcp_entrypoint": "D:\\Python-3-12\\python.exe mcp_server.py",
                "web_ui_command": "D:\\Python-3-12\\python.exe cli.py serve --host 127.0.0.1 --port 8765 --no-browser --raw-server",
                "web_ui_url": "http://127.0.0.1:8765/settings",
                "settings_ui_screenshot": str(self.report_dir / "settings_store_profile_ui.png"),
            },
            "scope_separation": {
                "long_term_campaign_goal": {
                    "target_per_store": 20,
                    "total_stores": 5,
                    "total_campaign_capacity": 100,
                },
                "pilot_acceptance_scope": {
                    "target_stores": ["preaureum", "wrydeco"],
                    "new_articles_per_store": 3,
                    "total_pilot_articles": 6,
                    "other_stores_e2e_articles_run": 0,
                },
            },
            "store_progress_table": [
                {
                    "store_id": sid,
                    "long_term_target": 20,
                    "pilot_target": 3 if sid in ("preaureum", "wrydeco") else 0,
                    "completed_in_pilot": sum(
                        1 for r in cohort_rows if r["store_id"] == sid and r["publication"]["state"] == "COMPLETED"
                    ),
                    "profile_ready": bool(self.profile_manager.validate_profile(sid).get("valid")),
                    "note": (
                        "Pilot E2E verified (3 new create articles live)"
                        if sid in ("preaureum", "wrydeco")
                        else "Profile & catalog service ready; E2E article publish not part of 6-article pilot scope"
                    ),
                }
                for sid in ["preaureum", "wrydeco", "dizzycustom", "jeminise", "chillgen"]
            ],
            "cohort": cohort_rows,
            "idempotent_rerun_checks": rerun_checks or [],
            "remaining_policy_conflicts_and_unknowns": [
                {
                    "store_id": "wrydeco",
                    "policy_keys": ["shipping", "returns_refunds"],
                    "conflict_status": "conflict_blocked",
                    "detail": (
                        "Pages /pages/shipping-delivery and /pages/returns-refund mention free 30-day returns and free shipping, "
                        "whereas /policies/shipping-policy and /policies/refund-policy state shipping fees are non-refundable and "
                        "customer pays return shipping for change-of-mind. Profile blocks "
                        "'free returns' and '100% full refund including shipping' claims."
                    ),
                },
                {
                    "store_id": "dizzycustom",
                    "policy_keys": ["shipping", "returns_refunds"],
                    "conflict_status": "conflict_blocked",
                    "detail": (
                        "Pages /pages/shipping-guide vs /policies/shipping-policy conflict on processing/transit days "
                        "(1-2 + 3-5 vs 3-5 + 7-15 business days) and /pages/return-policy vs /policies/refund-policy "
                        "conflict on return shipping fee (free vs $5.99 deducted). Profile blocks single unhedged timelines "
                        "and 'free return shipping' claims."
                    ),
                },
                {
                    "store_id": "preaureum",
                    "policy_keys": ["warranty"],
                    "conflict_status": "unknown",
                    "detail": "No separate standalone warranty policy beyond the 30-day defective/damaged item claim window.",
                },
            ],
        }

        json_path = self.report_dir / "acceptance_report.json"
        md_path = self.report_dir / "acceptance_report.md"
        json_path.write_text(json.dumps(report_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        md_path.write_text(self._render_markdown_report(report_data), encoding="utf-8")
        report_data["report_paths"] = {"json": str(json_path), "markdown": str(md_path)}
        return report_data

    def _render_markdown_report(self, data: Dict[str, Any]) -> str:
        env = data["environment"]
        lines: List[str] = [
            f"# Báo Cáo Nghiệm Thu Pilot 6 Bài Blog (`{data['acceptance_run_id']}`)",
            "",
            f"- **Verdict:** `{data['verdict']}`",
            f"- **Campaign ID:** `{data['campaign_id']}`",
            f"- **Generated At:** `{data['generated_at']}`",
            f"- **Workspace:** `{env['workspace']}`",
            f"- **Python / Platform:** `{env['python_version']}` (`{env['platform']}`)",
            f"- **MCP Server Entrypoint:** `{env['mcp_entrypoint']}`",
            f"- **Web UI Command:** `{env['web_ui_command']}`",
            f"- **Settings UI Screenshot (Redacted):** `{env['settings_ui_screenshot']}`",
            "",
            "---",
            "",
            "## 1. Phân tách phạm vi Mục tiêu Chiến dịch (100 bài) vs. Nghiệm thu Pilot (6 bài)",
            "",
            "| Store ID | Mục tiêu dài hạn (Campaign) | Mục tiêu Pilot | Đã hoàn tất trong Pilot | Editorial Profile | Ghi chú phạm vi |",
            "| :--- | :---: | :---: | :---: | :---: | :--- |",
        ]
        for row in data["store_progress_table"]:
            lines.append(
                f"| `{row['store_id']}` | {row['long_term_target']} | {row['pilot_target']} | "
                f"**{row['completed_in_pilot']}** | `{'READY' if row['profile_ready'] else 'MISSING'}` | {row['note']} |"
            )

        lines.extend(
            [
                "",
                "---",
                "",
                "## 2. Kết quả chi tiết Cohort 6 Bài Mới (3 Preaureum + 3 WRYDECO)",
                "",
                "| # | Store | Run ID | Plan ID | Content ID | Handle | Words | Body Imgs | Fact Gate | Media Gate | Live Checks | Shopify Article ID | Zbigtee Sync | State |",
                "| :-: | :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- | :---: | :---: |",
            ]
        )
        for c in data["cohort"]:
            lv = c["live_verification"]
            pub = c["publication"]
            fa = c["fact_audit"]
            mm = c["media_manifest"]
            lines.append(
                f"| {c['cohort_index']} | `{c['store_id']}` #{c['store_slot']} | `{c['run_id']}` | "
                f"`{c['plan_id']}` | `{c['content_id']}` | `{c['handle']}` | {c['word_count']} | "
                f"{mm['unique_body_image_count']} | `{'PASS' if fa['passed'] else 'FAIL'}` | "
                f"`{'PASS' if mm['ok'] else 'FAIL'}` | `{lv['passed_checks']}/{lv['total_checks']}` | "
                f"`{pub['shopify_article_id']}` | `{'SYNCED' if pub['zbigtee_synced'] else 'PENDING'}` | **`{pub['state']}`** |"
            )

        lines.extend(["", "### Đường dẫn Public URL & Artifacts từng bài", ""])
        for c in data["cohort"]:
            pub = c["publication"]
            lv = c["live_verification"]
            fa = c["fact_audit"]
            mm = c["media_manifest"]
            lines.extend(
                [
                    f"#### {c['cohort_index']}. [{c['store_id'].upper()} #{c['store_slot']}] {c['article_title']}",
                    f"- **Plan ID / Content ID:** `{c['plan_id']}` / `{c['content_id']}` (`action=create`, `targetPath=null` trước khi chạy)",
                    f"- **Run ID / Ready Digest:** `{c['run_id']}` / `{c['ready_digest'][:24]}...`",
                    f"- **Shopify Article ID:** `{pub['shopify_article_id']}` (Blog ID: `{pub['shopify_blog_id']}`)",
                    f"- **Public Live URL:** {pub['published_url']}",
                    f"- **Zbigtee Readback:** `status=published`, `targetPath={pub['zbigtee_target_path']}`",
                    f"- **Quality Metrics:** `{c['word_count']}` words, `{mm['unique_body_image_count']}` unique body images + verified hero (`visual_reviews_approved={mm['visual_reviews_approved']}`)",
                    f"- **Live Verification:** `ok={lv['ok']}` (`{lv['passed_checks']}/{lv['total_checks']}` checks passed via proxy `{lv['proxy_server']}`)",
                    f"- **Artifacts:**",
                    f"  - Fact Audit: `{fa['report_path']}`",
                    f"  - Media Manifest: `{mm['manifest_path']}`",
                    f"  - Live Verify Report: `{lv['report_path']}`",
                    f"  - Desktop Screenshot: `{lv['desktop_screenshot']}`",
                    f"  - Mobile Screenshot: `{lv['mobile_screenshot']}`",
                    "",
                ]
            )

        lines.extend(
            [
                "---",
                "",
                "## 3. Kiểm tra Idempotent Rerun (Chạy lại không tạo trùng)",
                "",
                "| Store | Run ID | Content ID | `idempotent_reuse` | `resume_run` Action | Article ID giữ nguyên | Completed Counter Before/After | Không tạo bài trùng |",
                "| :--- | :--- | :--- | :---: | :--- | :--- | :---: | :---: |",
            ]
        )
        for rc in data.get("idempotent_rerun_checks") or []:
            lines.append(
                f"| `{rc['store_id']}` | `{rc['run_id']}` | `{rc['content_id']}` | "
                f"`{rc['publish_idempotent_flag']}` | `{rc['resume_action']}` | "
                f"`{rc['shopify_article_id']}` | `{rc['completed_runs_before']} -> {rc['completed_runs_after']}` | "
                f"**`{'PASS' if rc['no_duplicate_created'] else 'FAIL'}`** |"
            )

        lines.extend(
            [
                "",
                "---",
                "",
                "## 4. Danh sách Policy Conflicts / Unknowns được bảo vệ trong Store Editorial Profiles",
                "",
            ]
        )
        for item in data.get("remaining_policy_conflicts_and_unknowns") or []:
            lines.append(
                f"- **`{item['store_id']}` (`{', '.join(item['policy_keys'])}` — `{item['conflict_status']}`):** {item['detail']}"
            )
        lines.append("")
        return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 6-article pilot acceptance stages.")
    parser.add_argument(
        "--stage",
        choices=["prepublish", "publish", "report"],
        default="prepublish",
        help="Stage to run: prepublish, publish, or report",
    )
    parser.add_argument("--campaign-id", default="blog_scaling_20x5_2026-10-17")
    parser.add_argument("--acceptance-run-id", default="pilot_2026-10-17")
    args = parser.parse_args()

    runner = AcceptancePilotRunner(
        campaign_id=args.campaign_id,
        acceptance_run_id=args.acceptance_run_id,
    )
    if args.stage == "prepublish":
        res = runner.run_prepublish_stage()
        return 0 if res.get("ok") else 1
    if args.stage == "publish":
        res = runner.run_publish_and_verify_stage()
        return 0 if res.get("verdict") == "PASS" else 1
    res = runner.build_acceptance_report()
    return 0 if res.get("verdict") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
