"""
Campaign & Article Run State Manager (`campaign_manager.py`).

Manages the 5-store 20-articles/store scaling campaign and the 6-article pilot acceptance cohort
(3 new `create` articles on `preaureum` + 3 new `create` articles on `wrydeco`), enforcing:
  - Explicit separation between the 100-article campaign capability and the 6-article pilot scope.
  - Strict `action == "create"` and `targetPath == None` eligibility filtering.
  - Baseline protection (`protected_article_ids` and `protected_handles`) so historical articles
    are never overwritten or counted toward new campaign progress.
  - Full state machine tracking (`DISCOVERED` -> ... -> `COMPLETED`) and append-only redacted
    audit journaling (`audit_log.jsonl`).
  - Idempotent reservation and completion counting (each `shopify_article_id` increments the
    store's completed counter at most once).
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from proxy_manager import redact_sensitive_data
from store_manager import DATA_DIR, StoreManager, slugify_store_id

CAMPAIGNS_DIR = DATA_DIR / "campaigns"
DEFAULT_BASELINE_ID = "baseline_2026-10-17"
DEFAULT_CAMPAIGN_ID = "blog_scaling_20x5_2026-10-17"

ALL_CAMPAIGN_STORES = ("wrydeco", "dizzycustom", "jeminise", "chillgen", "preaureum")
PILOT_COHORT_STORES = ("preaureum", "wrydeco")

VALID_RUN_STATES = {
    "DISCOVERED",
    "ELIGIBLE",
    "RESERVED",
    "BRIEF_READY",
    "DRAFT_READY",
    "FACTS_REVIEWED",
    "MEDIA_REVIEWED",
    "PREPUBLISH_READY",
    "SHOPIFY_CREATED",
    "LIVE_VERIFIED",
    "ZBIGTEE_SYNCED",
    "COMPLETED",
    # Error / blocked states
    "BLOCKED_PROFILE",
    "BLOCKED_PROXY",
    "BLOCKED_FACTS",
    "BLOCKED_MEDIA",
    "PUBLISH_OUTCOME_UNKNOWN",
    "LIVE_FAILED",
    "ZBIGTEE_SYNC_PENDING",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_plan_topic_title(raw_title: str) -> str:
    """
    Convert Zbigtee Vietnamese wrapper labels (e.g., `Trả lời “...”`, `Nội dung cho vùng “...”`,
    `Trang cho “...”`, `Viết nội dung cho ...`) into clean English topic strings.
    """
    text = (raw_title or "").strip()
    m_quote = re.search(r"[“\"']([^”\"']+)[”\"']", text)
    if m_quote and any(
        prefix in text.lower()
        for prefix in ("trả lời", "nội dung cho vùng", "trang cho", "viết nội dung")
    ):
        extracted = m_quote.group(1).strip()
        if extracted:
            return extracted[0].upper() + extracted[1:]
    text = re.sub(
        r"^(?:Trả lời|Nội dung cho vùng|Trang cho|Viết nội dung cho)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" “”\"'")
    return (text[0].upper() + text[1:]) if text else raw_title


class CampaignManager:
    """Manages campaign manifests, per-article run state files, and redacted audit logs."""

    def __init__(
        self,
        store_manager: Optional[StoreManager] = None,
        campaigns_dir: Optional[Path] = None,
    ) -> None:
        self.store_manager = store_manager or StoreManager()
        self.campaigns_dir = Path(campaigns_dir) if campaigns_dir else CAMPAIGNS_DIR
        self.campaigns_dir.mkdir(parents=True, exist_ok=True)

    def _campaign_dir(self, campaign_id: str) -> Path:
        safe_id = re.sub(r"[^a-zA-Z0-9._-]+", "_", (campaign_id or DEFAULT_CAMPAIGN_ID).strip())
        d = self.campaigns_dir / safe_id
        (d / "articles").mkdir(parents=True, exist_ok=True)
        return d

    def _state_file(self, campaign_id: str) -> Path:
        return self._campaign_dir(campaign_id) / "campaign_state.json"

    def _audit_log_file(self, campaign_id: str) -> Path:
        return self._campaign_dir(campaign_id) / "audit_log.jsonl"

    def _article_run_file(self, campaign_id: str, store_id: str, run_id: str) -> Path:
        safe_store = slugify_store_id(store_id)
        safe_run = re.sub(r"[^a-zA-Z0-9._-]+", "_", run_id.strip())
        return self._campaign_dir(campaign_id) / "articles" / f"{safe_store}__{safe_run}.json"

    def append_audit_log(
        self,
        campaign_id: str,
        action: str,
        store_id: str = "",
        run_id: str = "",
        stage: str = "",
        outcome: str = "ok",
        error_code: str = "",
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        record = {
            "timestamp": _utc_now_iso(),
            "campaign_id": campaign_id,
            "store_id": store_id,
            "run_id": run_id,
            "action": action,
            "stage": stage,
            "outcome": outcome,
            "error_code": error_code,
            "detail": redact_sensitive_data(detail or {}),
        }
        log_file = self._audit_log_file(campaign_id)
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def load_baseline_manifest(self, baseline_id: str = DEFAULT_BASELINE_ID) -> Dict[str, Any]:
        b_path = self.campaigns_dir / baseline_id / "baseline_manifest.json"
        if b_path.exists():
            try:
                return json.loads(b_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"baseline_id": baseline_id, "stores": {}}

    def get_protected_baseline_sets(
        self, store_id: str, baseline_id: str = DEFAULT_BASELINE_ID
    ) -> Tuple[Set[str], Set[str], Set[str]]:
        """
        Return `(protected_article_ids, protected_handles, baseline_published_content_ids)`
        for `store_id` from the baseline manifest.
        """
        sid = slugify_store_id(store_id)
        baseline = self.load_baseline_manifest(baseline_id)
        s_data = (baseline.get("stores") or {}).get(sid) or {}
        shop_data = s_data.get("shopify") or {}
        zb_data = s_data.get("zbigtee") or {}

        protected_ids: Set[str] = set()
        protected_handles: Set[str] = set()
        published_content_ids: Set[str] = set()

        for pid in (s_data.get("protected_existing_article_ids") or []) + (
            shop_data.get("protected_existing_article_ids") or []
        ):
            if pid:
                protected_ids.add(str(pid).strip())

        for ph in shop_data.get("protected_existing_handles") or []:
            if ph:
                protected_handles.add(str(ph).strip().lower())

        for blog in shop_data.get("blogs") or []:
            for art in blog.get("articles") or []:
                if art.get("id"):
                    protected_ids.add(str(art["id"]).strip())
                if art.get("article_id"):
                    protected_ids.add(str(art["article_id"]).strip())
                if art.get("handle"):
                    protected_handles.add(str(art["handle"]).strip().lower())

        for row in (zb_data.get("content_rows") or []) + (zb_data.get("content_items") or []):
            if (row.get("status") or "").lower() == "published" and row.get("id"):
                published_content_ids.add(str(row["id"]).strip())

        class _ProtectedBaselineSets(dict):
            """Supports both `prot_ids, prot_handles, pub_cids = ...` and `.get(...)` dict access."""

            def __iter__(self):
                yield self["protected_article_ids"]
                yield self["protected_handles"]
                yield self["protected_content_ids"]

        return _ProtectedBaselineSets(
            protected_article_ids=protected_ids,
            protected_handles=protected_handles,
            protected_content_ids=published_content_ids,
        )

    def prepare_campaign(
        self,
        campaign_id: str = DEFAULT_CAMPAIGN_ID,
        store_ids: Optional[List[str]] = None,
        mode: str = "pilot_acceptance",
        target_per_store: int = 20,
        pilot_per_store: int = 3,
        baseline_id: str = DEFAULT_BASELINE_ID,
    ) -> Dict[str, Any]:
        """
        Initialize or load the campaign state file without mutating any Zbigtee Plan or Shopify articles.
        Explicitly tracks both the 20-articles/store campaign goal and the 3+3 pilot acceptance cohort.
        """
        state_path = self._state_file(campaign_id)
        if state_path.exists():
            existing = json.loads(state_path.read_text(encoding="utf-8"))
            self.append_audit_log(
                campaign_id=campaign_id,
                action="prepare_campaign_loaded_existing",
                stage="campaign_init",
                detail={"mode": existing.get("mode")},
            )
            return existing

        selected_stores = [
            slugify_store_id(s) for s in (store_ids or list(ALL_CAMPAIGN_STORES)) if s
        ]
        baseline = self.load_baseline_manifest(baseline_id)
        stores_state: Dict[str, Any] = {}

        for sid in ALL_CAMPAIGN_STORES:
            prot_ids, prot_handles, pub_cids = self.get_protected_baseline_sets(sid, baseline_id)
            b_store = (baseline.get("stores") or {}).get(sid) or {}
            b_zb = b_store.get("zbigtee") or {}
            is_pilot_store = sid in PILOT_COHORT_STORES
            stores_state[sid] = {
                "store_id": sid,
                "enabled_in_campaign": sid in selected_stores,
                "is_pilot_cohort_store": is_pilot_store,
                "campaign_target_new_articles": target_per_store,
                "pilot_target_new_articles": pilot_per_store if is_pilot_store else 0,
                "baseline_shopify_articles_count": len(prot_ids),
                "baseline_zbigtee_published_count": len(pub_cids),
                "baseline_zbigtee_create_proposals_count": int(
                    b_zb.get("create_proposals_count")
                    or b_zb.get("plan_proposed_create_count")
                    or 0
                ),
                "protected_article_ids": sorted(prot_ids),
                "protected_handles": sorted(prot_handles),
                "baseline_published_content_ids": sorted(pub_cids),
                "completed_new_article_ids": [],
                "completed_new_count": 0,
                "runs": [],
            }

        campaign_state = {
            "campaign_id": campaign_id,
            "baseline_id": baseline_id,
            "mode": mode,
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
            "campaign_goal": {
                "stores_count": len(ALL_CAMPAIGN_STORES),
                "new_articles_per_store": target_per_store,
                "total_new_articles_target": len(ALL_CAMPAIGN_STORES) * target_per_store,
            },
            "pilot_acceptance_scope": {
                "cohort_stores": list(PILOT_COHORT_STORES),
                "new_articles_per_store": pilot_per_store,
                "total_pilot_articles": len(PILOT_COHORT_STORES) * pilot_per_store,
                "other_stores_e2e_articles": 0,
            },
            "stores": stores_state,
            "pilot_cohort": {
                "frozen": False,
                "preaureum": [],
                "wrydeco": [],
            },
        }
        self.save_campaign_state(campaign_id, campaign_state)
        self.append_audit_log(
            campaign_id=campaign_id,
            action="prepare_campaign_created",
            stage="campaign_init",
            detail={
                "mode": mode,
                "selected_stores": selected_stores,
                "target_per_store": target_per_store,
                "pilot_per_store": pilot_per_store,
            },
        )
        return campaign_state

    def get_campaign_state(self, campaign_id: str = DEFAULT_CAMPAIGN_ID) -> Dict[str, Any]:
        state_path = self._state_file(campaign_id)
        if not state_path.exists():
            return self.prepare_campaign(campaign_id=campaign_id)
        return json.loads(state_path.read_text(encoding="utf-8"))

    def get_campaign_status(
        self,
        campaign_id: str = DEFAULT_CAMPAIGN_ID,
        store_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        state = self.get_campaign_state(campaign_id)
        out: Dict[str, Any] = dict(state)
        if store_id:
            sid = slugify_store_id(store_id)
            out["filtered_store_id"] = sid
            out["store_summary"] = (state.get("stores") or {}).get(sid)
        if run_id:
            out["run"] = self.get_run(campaign_id, run_id)
        return out

    def save_campaign_state(self, campaign_id: str, state: Dict[str, Any]) -> None:
        state["updated_at"] = _utc_now_iso()
        state_path = self._state_file(campaign_id)
        state_path.write_text(
            json.dumps(redact_sensitive_data(state), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def reserve_or_get_run(
        self,
        campaign_id: str,
        store_id: str,
        plan_id: Optional[str] = "",
        content_id: Optional[str] = "",
        title: str = "",
        action: str = "create",
        target_path: Optional[str] = None,
        cohort_slot: Optional[int] = None,
        profile_revision: Optional[int] = None,
        **extra_kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Idempotently reserve or retrieve an article run for `(store_id, plan_id/content_id)`.
        Blocks any item where `action != "create"` or `target_path` is non-empty.
        """
        sid = slugify_store_id(store_id)
        clean_pid = (plan_id or "").strip()
        clean_cid = (content_id or "").strip()
        if (action or "").strip().lower() != "create" or target_path:
            raise ValueError(
                f"PLAN_NOT_CREATE: Cannot reserve non-create item (action={action!r}, target_path={target_path!r})."
            )

        prot_ids, _, pub_cids = self.get_protected_baseline_sets(sid)
        if clean_cid and clean_cid in pub_cids:
            raise ValueError(
                f"BASELINE_DUPLICATE: Content ID '{clean_cid}' was already published before baseline."
            )

        # Check existing runs in this campaign for idempotent match
        articles_dir = self._campaign_dir(campaign_id) / "articles"
        for fpath in sorted(articles_dir.glob(f"{sid}__*.json")):
            try:
                r_data = json.loads(fpath.read_text(encoding="utf-8"))
                if (clean_pid and r_data.get("plan_id") == clean_pid) or (
                    clean_cid and r_data.get("content_id") == clean_cid
                ):
                    return r_data
            except Exception:
                pass

        key_seed = clean_pid or clean_cid or slugify_store_id(title)
        short_hash = hashlib.sha256(f"{sid}:{key_seed}".encode("utf-8")).hexdigest()[:10]
        run_id = f"run_{sid}_{short_hash}"

        run_data: Dict[str, Any] = {
            "run_id": run_id,
            "campaign_id": campaign_id,
            "store_id": sid,
            "cohort_slot": cohort_slot,
            "plan_id": clean_pid,
            "content_id": clean_cid,
            "raw_topic_title": title,
            "clean_topic_title": clean_plan_topic_title(title),
            "action": "create",
            "target_path": None,
            "profile_revision": profile_revision or 1,
            "idempotency_key": f"{campaign_id}:{sid}:{key_seed}",
            "state": "RESERVED",
            "stage": "reservation",
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
            "protected_article_ids_count": len(prot_ids),
            "brief": None,
            "ready_digest": "",
            "shopify_article_id": "",
            "shopify_url": "",
            "public_url": "",
            "zbigtee_synced": False,
            "retry_count": 0,
            "history": [
                {
                    "timestamp": _utc_now_iso(),
                    "state": "RESERVED",
                    "note": "Reserved eligible create-only article item.",
                }
            ],
            "artifact_paths": {},
            "findings": [],
        }
        self.save_run(campaign_id, run_data)

        c_state = self.get_campaign_state(campaign_id)
        store_entry = c_state["stores"].setdefault(sid, {})
        runs_list = store_entry.setdefault("runs", [])
        if run_id not in runs_list:
            runs_list.append(run_id)
        self.save_campaign_state(campaign_id, c_state)

        self.append_audit_log(
            campaign_id=campaign_id,
            action="reserve_run",
            store_id=sid,
            run_id=run_id,
            stage="reservation",
            detail={"plan_id": clean_pid, "content_id": clean_cid, "title": title},
        )
        return run_data

    def get_run(
        self,
        campaign_id: str,
        store_or_run_id: str,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if run_id is not None:
            fpath = self._article_run_file(campaign_id, store_or_run_id, run_id)
            if fpath.exists():
                return json.loads(fpath.read_text(encoding="utf-8"))
            target_run_id = run_id
        else:
            target_run_id = store_or_run_id

        articles_dir = self._campaign_dir(campaign_id) / "articles"
        for fpath in sorted(articles_dir.glob("*.json")):
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                if data.get("run_id") == target_run_id:
                    return data
            except Exception:
                pass
        raise FileNotFoundError(
            f"Run '{target_run_id}' not found in campaign '{campaign_id}'."
        )

    def find_run(
        self,
        campaign_id: str,
        store_id: str,
        run_or_item_id: str,
    ) -> Optional[Dict[str, Any]]:
        sid = slugify_store_id(store_id)
        direct = self._article_run_file(campaign_id, sid, run_or_item_id)
        if direct.exists():
            return json.loads(direct.read_text(encoding="utf-8"))
        articles_dir = self._campaign_dir(campaign_id) / "articles"
        for fpath in sorted(articles_dir.glob(f"{sid}__*.json")):
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                if run_or_item_id in (
                    data.get("run_id"),
                    data.get("plan_id"),
                    data.get("content_id"),
                    data.get("handle"),
                ):
                    return data
            except Exception:
                pass
        return None

    def save_run(self, campaign_id: str, run_data: Dict[str, Any]) -> str:
        run_data["updated_at"] = _utc_now_iso()
        fpath = self._article_run_file(
            campaign_id, run_data["store_id"], run_data["run_id"]
        )
        fpath.write_text(
            json.dumps(redact_sensitive_data(run_data), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return str(fpath)

    def transition_run_state(
        self,
        campaign_id: str,
        store_or_run_id: str = "",
        run_id: str = "",
        new_state: str = "",
        stage: str = "",
        note: str = "",
        updates: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = "",
        *,
        to_state: str = "",
        summary: str = "",
        artifact_updates: Optional[Dict[str, Any]] = None,
        metadata_updates: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        resolved_run_id = run_id or store_or_run_id
        resolved_state = (new_state or to_state).strip()
        resolved_note = note or summary
        resolved_err = error_code or ""
        if resolved_state not in VALID_RUN_STATES:
            raise ValueError(f"Invalid run state '{resolved_state}'.")

        run_data = self.get_run(campaign_id, resolved_run_id)
        sid = run_data["store_id"]
        run_data["state"] = resolved_state
        run_data["stage"] = stage
        if resolved_err:
            run_data["last_error_code"] = resolved_err
        elif resolved_state in ("COMPLETED", "PREPUBLISH_READY", "DRAFT_READY"):
            run_data["last_error_code"] = ""

        merged_updates: Dict[str, Any] = {}
        if updates:
            merged_updates.update(updates)
        if metadata_updates:
            merged_updates.update(metadata_updates)
        if artifact_updates:
            merged_updates.setdefault("artifact_paths", {}).update(artifact_updates)

        for k, v in merged_updates.items():
            if k == "artifact_paths" and isinstance(v, dict):
                run_data.setdefault("artifact_paths", {}).update(v)
            else:
                run_data[k] = v

        run_data.setdefault("history", []).append(
            {
                "timestamp": _utc_now_iso(),
                "state": resolved_state,
                "stage": stage,
                "error_code": resolved_err,
                "note": resolved_note,
            }
        )
        self.save_run(campaign_id, run_data)

        # If COMPLETED with a valid new shopify_article_id, increment store completed counter idempotently
        if resolved_state == "COMPLETED" and run_data.get("shopify_article_id"):
            self._record_completed_article_id(
                campaign_id,
                sid,
                run_data["shopify_article_id"],
            )

        self.append_audit_log(
            campaign_id=campaign_id,
            action=f"state_transition:{resolved_state}",
            store_id=sid,
            run_id=resolved_run_id,
            stage=stage,
            outcome="error" if resolved_err else "ok",
            error_code=resolved_err,
            detail={"note": resolved_note},
        )
        return run_data

    def _record_completed_article_id(
        self, campaign_id: str, store_id: str, shopify_article_id: str
    ) -> None:
        sid = slugify_store_id(store_id)
        art_id = (shopify_article_id or "").strip()
        if not art_id:
            return
        prot_ids, _, _ = self.get_protected_baseline_sets(sid)
        if art_id in prot_ids:
            return
        c_state = self.get_campaign_state(campaign_id)
        s_entry = c_state["stores"].setdefault(sid, {})
        comp_list: List[str] = s_entry.setdefault("completed_new_article_ids", [])
        if art_id not in comp_list:
            comp_list.append(art_id)
        s_entry["completed_new_count"] = len(comp_list)
        s_entry["completed_new_articles"] = len(comp_list)
        self.save_campaign_state(campaign_id, c_state)
