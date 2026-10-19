"""
Local Stdio MCP Server (`mcp_server.py`) for Multi-Store Blog Scaling & Publishing.

Implements Section 12 of `docs/ANTIGRAVITY_IMPLEMENTATION_PLAN_BLOG_SCALING_20_ARTICLES.md`:
  - Uses `mcp.server.mcpserver.MCPServer` over `stdio`.
  - Directs all logging strictly to `sys.stderr` so `stdout` stays clean for JSON-RPC.
  - Redacts all secrets (`access_token`, `client_secret`, proxy credentials, Zbigtee session tokens)
    via `redact_sensitive_data()` before returning any tool output.
  - Exposes all 18 standardized tools with unified envelope and stable error codes.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

# Configure logging strictly to stderr so stdout is never polluted
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[mcp-blog-server] %(asctime)s %(levelname)s: %(message)s",
)
logger = logging.getLogger("mcp_blog_server")

from mcp.server.mcpserver import MCPServer

from article_fact_auditor import ArticleFactAuditor
from article_image_service import ArticleImageService
from campaign_manager import CampaignManager, DEFAULT_CAMPAIGN_ID
from html_postprocessor import HtmlPostProcessor, PostProcessedArticle
from pipeline import BlogSyncPipeline, compute_ready_digest
from proxy_manager import ProxyBlockedError, redact_sensitive_data
from shopify_catalog_service import ShopifyCatalogService
from store_manager import DATA_DIR, StoreManager
from store_profile_manager import StoreProfileConflictError, StoreProfileManager, StoreProfileValidationError
from zbigtee_ui_operator import ZbigteeUiOperator

OUTPUT_DIR = MODULE_DIR / "output"
mcp = MCPServer("wrydeco-blog-scaling-mcp")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _envelope(
    *,
    ok: bool,
    store_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    run_id: Optional[str] = None,
    state: str = "READY",
    stage: str = "IDLE",
    error_code: Optional[str] = None,
    retryable: bool = False,
    summary: str = "",
    findings: Optional[List[Dict[str, Any]]] = None,
    artifact_paths: Optional[Dict[str, str]] = None,
    next_actions: Optional[List[str]] = None,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = {
        "ok": bool(ok),
        "store_id": store_id,
        "campaign_id": campaign_id,
        "run_id": run_id,
        "state": state,
        "stage": stage,
        "error_code": error_code,
        "retryable": bool(retryable),
        "summary": summary,
        "findings": findings or [],
        "artifact_paths": artifact_paths or {},
        "checked_at": _now_iso(),
        "next_actions": next_actions or [],
        "data": data or {},
    }
    return redact_sensitive_data(payload)


def _error_envelope(
    exc: Exception,
    *,
    store_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    run_id: Optional[str] = None,
    stage: str = "ERROR",
    default_code: str = "INTERNAL_ERROR",
) -> Dict[str, Any]:
    msg = redact_sensitive_data(str(exc))
    code = default_code
    retryable = False
    state = "ERROR"

    if isinstance(exc, ProxyBlockedError) or "PROXY" in msg.upper():
        code = "PROXY_BLOCKED"
        state = "BLOCKED_PROXY"
        retryable = True
    elif isinstance(exc, StoreProfileConflictError) or "PROFILE_REVISION_CONFLICT" in msg:
        code = "PROFILE_INVALID"
        state = "BLOCKED_PROFILE"
        retryable = True
    elif isinstance(exc, StoreProfileValidationError):
        code = "PROFILE_INVALID"
        state = "BLOCKED_PROFILE"
    elif isinstance(exc, KeyError) and "Store" in msg:
        code = "INVALID_STORE"
    elif "AUTH_REQUIRED" in msg or isinstance(exc, PermissionError):
        code = "AUTH_REQUIRED"
        retryable = True
    elif "PLAN_NOT_CREATE" in msg:
        code = "PLAN_NOT_CREATE"
    elif "STALE_VALIDATION" in msg:
        code = "STALE_VALIDATION"
        retryable = True
    elif "BLOG" in msg.upper() and "NOT FOUND" in msg.upper():
        code = "BLOG_NOT_FOUND"

    return _envelope(
        ok=False,
        store_id=store_id,
        campaign_id=campaign_id,
        run_id=run_id,
        state=state,
        stage=stage,
        error_code=code,
        retryable=retryable,
        summary=msg,
        findings=[{"severity": "error", "code": code, "message": msg}],
        next_actions=[f"Resolve {code}: {msg}"],
    )


# ---------------------------------------------------------------------------
# 1. Store & Profile Tools
# ---------------------------------------------------------------------------
@mcp.tool()
def list_stores() -> Dict[str, Any]:
    """List all configured Shopify stores, public domains, destination blogs, and editorial profile status (no secrets)."""
    try:
        sm = StoreManager(data_dir=DATA_DIR)
        pm = StoreProfileManager(data_dir=DATA_DIR, store_manager=sm)
        proxy_summary = sm.proxy_manager.get_config(auto_bootstrap=False).to_dict(mask_secrets=True)

        stores_out: List[Dict[str, Any]] = []
        for s in sm.list_stores():
            prof_summary = {}
            try:
                prof = pm.get_profile(s.id)
                val = pm.validate_profile(s.id, prof)
                prof_summary = {
                    "profile_status": prof.get("profile_status"),
                    "profile_revision": prof.get("profile_revision"),
                    "valid": val.get("valid", False),
                    "ready_for_Prompt": val.get("ready_for_Prompt", False),
                }
            except Exception as exc:
                prof_summary = {"profile_status": "missing", "error": str(exc)}

            stores_out.append(
                {
                    "store_id": s.id,
                    "name": s.name,
                    "shop_domain": s.normalized_shop,
                    "public_domain": s.resolved_public_domain,
                    "default_blog_handle": s.default_blog_handle,
                    "default_blog_id": s.default_blog_id,
                    "zbigtee_project_id": s.zbigtee_project_id,
                    "zbigtee_domain": s.zbigtee_domain,
                    "editorial_profile": prof_summary,
                }
            )

        return _envelope(
            ok=True,
            state="READY",
            stage="LIST_STORES",
            summary=f"Found {len(stores_out)} configured stores.",
            data={
                "active_store_id": sm.get_active_store_id(),
                "proxy": proxy_summary,
                "stores": stores_out,
            },
            next_actions=["Call check_store_readiness(store_id) or get_store_profile(store_id)."],
        )
    except Exception as exc:
        return _error_envelope(exc, stage="LIST_STORES")


@mcp.tool()
def get_store_profile(store_id: str, revision: Optional[int] = None) -> Dict[str, Any]:
    """Get the sanitized runtime Editorial Profile, structured rules, and policy unknowns for a specific store."""
    try:
        sm = StoreManager(data_dir=DATA_DIR)
        store = sm.get_store(store_id)
        pm = StoreProfileManager(data_dir=DATA_DIR, store_manager=sm)
        full_profile = pm.get_profile(store.id)
        if revision is not None and int(full_profile.get("profile_revision") or 0) != int(revision):
            return _envelope(
                ok=False,
                store_id=store.id,
                state="BLOCKED_PROFILE",
                stage="GET_STORE_PROFILE",
                error_code="STALE_VALIDATION",
                retryable=True,
                summary=(
                    f"Requested profile_revision={revision} does not match active "
                    f"profile_revision={full_profile.get('profile_revision')}."
                ),
                data={"current_profile_revision": full_profile.get("profile_revision")},
                next_actions=["Re-fetch get_store_profile(store_id) without a stale revision pin."],
            )
        runtime_bundle = pm.get_runtime_profile(store.id)
        validation = pm.validate_profile(store.id, full_profile)
        return _envelope(
            ok=bool(validation.get("valid")),
            store_id=store.id,
            state="READY" if validation.get("ready_for_Prompt") else "BLOCKED_PROFILE",
            stage="GET_STORE_PROFILE",
            error_code=None if validation.get("valid") else "PROFILE_INVALID",
            summary=(
                f"Loaded store profile for '{store.id}' (revision {full_profile.get('profile_revision')}, "
                f"status={full_profile.get('profile_status')})."
            ),
            artifact_paths={"profile_path": f"data/store_profiles/{store.id}.json"},
            data={
                "runtime_profile": runtime_bundle,
                "validation": validation,
            },
            next_actions=["Use runtime_profile rules when preparing briefs or auditing claims."],
        )
    except Exception as exc:
        return _error_envelope(exc, store_id=store_id, stage="GET_STORE_PROFILE")


@mcp.tool()
def validate_store_profile(
    store_id: str,
    profile_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Validate a store's Editorial Profile against the JSON schema and semantic conflict rules without saving."""
    try:
        sm = StoreManager(data_dir=DATA_DIR)
        store = sm.get_store(store_id)
        pm = StoreProfileManager(data_dir=DATA_DIR, store_manager=sm)
        target = profile_data if isinstance(profile_data, dict) and profile_data else pm.get_profile(store.id)
        val = pm.validate_profile(store.id, target)
        ok = bool(val.get("valid"))
        return _envelope(
            ok=ok,
            store_id=store.id,
            state="READY" if val.get("ready_for_Prompt") else "BLOCKED_PROFILE",
            stage="VALIDATE_STORE_PROFILE",
            error_code=None if ok else "PROFILE_INVALID",
            summary=f"Profile validation for '{store.id}': valid={ok}, ready={val.get('ready_for_Prompt')}.",
            findings=[
                {"severity": "error", "code": "PROFILE_INVALID", "message": e}
                for e in (val.get("errors") or [])
            ]
            + [
                {"severity": "warning", "code": "POLICY_CONFLICT", "message": w}
                for w in (val.get("warnings") or [])
            ],
            data=val,
        )
    except Exception as exc:
        return _error_envelope(exc, store_id=store_id, stage="VALIDATE_STORE_PROFILE")


@mcp.tool()
def save_store_profile(
    store_id: str,
    updates: Dict[str, Any],
    expected_revision: Optional[int] = None,
) -> Dict[str, Any]:
    """Save updates to a single store's Editorial Profile with optimistic concurrency control (`expected_revision`)."""
    try:
        sm = StoreManager(data_dir=DATA_DIR)
        store = sm.get_store(store_id)
        pm = StoreProfileManager(data_dir=DATA_DIR, store_manager=sm)
        saved = pm.save_profile(
            store_id=store.id,
            payload=updates,
            expected_revision=expected_revision,
            updated_by="mcp_save_store_profile",
        )
        val = pm.validate_profile(store.id, saved)
        return _envelope(
            ok=True,
            store_id=store.id,
            state="READY" if val.get("ready_for_Prompt") else "BLOCKED_PROFILE",
            stage="SAVE_STORE_PROFILE",
            summary=f"Saved profile for '{store.id}' at revision {saved.get('profile_revision')}.",
            artifact_paths={"profile_path": f"data/store_profiles/{store.id}.json"},
            data={
                "profile_revision": saved.get("profile_revision"),
                "profile_status": saved.get("profile_status"),
                "validation": val,
            },
        )
    except Exception as exc:
        return _error_envelope(exc, store_id=store_id, stage="SAVE_STORE_PROFILE")


@mcp.tool()
def check_store_readiness(store_id: str) -> Dict[str, Any]:
    """Check Proxy, Shopify OAuth/GraphQL identity, destination blog, Editorial Profile, and Zbigtee session readiness."""
    try:
        sm = StoreManager(data_dir=DATA_DIR)
        store = sm.get_store(store_id)
        pm = StoreProfileManager(data_dir=DATA_DIR, store_manager=sm)
        svc = ShopifyCatalogService(sm)
        zb = ZbigteeUiOperator(sm, store.id)

        proxy_cfg = sm.proxy_manager.get_config(auto_bootstrap=False)
        if not proxy_cfg.is_configured:
            return _envelope(
                ok=False,
                store_id=store.id,
                state="BLOCKED_PROXY",
                stage="CHECK_STORE_READINESS",
                error_code="PROXY_BLOCKED",
                retryable=True,
                summary="Mandatory Shopify proxy is not configured or disabled.",
            )

        prof = pm.get_profile(store.id)
        prof_val = pm.validate_profile(store.id, prof)
        blogs_res = svc.list_blogs(store.id)
        blogs = blogs_res.get("blogs") or []
        blog_handles = [b.get("handle") for b in blogs]
        dest_blog_ok = bool(store.default_blog_handle and store.default_blog_handle in blog_handles)

        zb_auth = zb.get_auth_state()
        zb_ok = bool(zb_auth.get("exists") and zb_auth.get("session_token") and store.zbigtee_project_id)

        all_ok = bool(
            proxy_cfg.is_configured
            and prof_val.get("ready_for_Prompt")
            and dest_blog_ok
            and zb_ok
        )
        err_code = None
        if not prof_val.get("ready_for_Prompt"):
            err_code = "PROFILE_INVALID"
        elif not dest_blog_ok:
            err_code = "BLOG_NOT_FOUND"
        elif not zb_ok:
            err_code = "AUTH_REQUIRED"

        return _envelope(
            ok=all_ok,
            store_id=store.id,
            state="READY" if all_ok else ("BLOCKED_PROFILE" if err_code == "PROFILE_INVALID" else "ERROR"),
            stage="CHECK_STORE_READINESS",
            error_code=err_code,
            summary=(
                f"Readiness for '{store.id}': ok={all_ok} "
                f"(proxy={proxy_cfg.masked_summary}, blog={store.default_blog_handle}, "
                f"profile_rev={prof.get('profile_revision')})."
            ),
            data={
                "proxy": proxy_cfg.to_dict(mask_secrets=True),
                "shop_domain": store.normalized_shop,
                "public_domain": store.resolved_public_domain,
                "default_blog_handle": store.default_blog_handle,
                "default_blog_id": store.default_blog_id,
                "available_blogs": blogs,
                "destination_blog_ok": dest_blog_ok,
                "profile_validation": prof_val,
                "zbigtee_ready": zb_ok,
                "zbigtee_project_id": store.zbigtee_project_id,
            },
        )
    except Exception as exc:
        return _error_envelope(exc, store_id=store_id, stage="CHECK_STORE_READINESS")


# ---------------------------------------------------------------------------
# 2. Plan Candidates, Campaign & Topic Orchestration Tools
# ---------------------------------------------------------------------------
@mcp.tool()
def list_plan_candidates(
    store_id: str,
    include_accepted: bool = True,
    include_added_content_topics: bool = True,
) -> Dict[str, Any]:
    """List Zbigtee Plan proposals for a store, separating eligible `create` (`targetPath=null`) from excluded items."""
    try:
        sm = StoreManager(data_dir=DATA_DIR)
        store = sm.get_store(store_id)
        cm = CampaignManager(store_manager=sm)
        protected = cm.get_protected_baseline_sets(store.id)
        zb = ZbigteeUiOperator(sm, store.id)
        res = zb.list_plan_candidates(
            include_accepted=include_accepted,
            include_added_content_topics=include_added_content_topics,
            baseline_published_content_ids=protected.get("protected_content_ids") or set(),
        )
        return _envelope(
            ok=True,
            store_id=store.id,
            state="READY",
            stage="LIST_PLAN_CANDIDATES",
            summary=(
                f"Store '{store.id}' has {res['eligible_create_count']} eligible create-only candidates "
                f"and {res['excluded_count']} excluded items."
            ),
            data=res,
        )
    except Exception as exc:
        return _error_envelope(exc, store_id=store_id, stage="LIST_PLAN_CANDIDATES")


@mcp.tool()
def prepare_campaign(
    campaign_id: str = DEFAULT_CAMPAIGN_ID,
    store_ids: Optional[List[str]] = None,
    target_per_store: int = 20,
) -> Dict[str, Any]:
    """Initialize or load a create-only campaign manifest linked to the protected baseline without mutating articles."""
    try:
        sm = StoreManager(data_dir=DATA_DIR)
        cm = CampaignManager(store_manager=sm)
        cid = (campaign_id or DEFAULT_CAMPAIGN_ID).strip()
        manifest = cm.prepare_campaign(
            campaign_id=cid,
            store_ids=store_ids,
            target_per_store=target_per_store,
        )
        return _envelope(
            ok=True,
            campaign_id=cid,
            state="READY",
            stage="PREPARE_CAMPAIGN",
            summary=f"Campaign '{cid}' prepared across {len(manifest.get('stores') or {})} stores (mode=create_only).",
            artifact_paths={
                "campaign_manifest": f"data/campaigns/{cid}/campaign_manifest.json",
                "baseline_manifest": str(manifest.get("baseline_manifest_path") or ""),
            },
            data=manifest,
        )
    except Exception as exc:
        return _error_envelope(exc, campaign_id=campaign_id, stage="PREPARE_CAMPAIGN")


@mcp.tool()
def add_plan_topics(store_id: str, topics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Deduplicate and add new `create` (`targetPath=null`) topics to a store's Zbigtee project and verify creation."""
    try:
        sm = StoreManager(data_dir=DATA_DIR)
        store = sm.get_store(store_id)
        zb = ZbigteeUiOperator(sm, store.id)
        res = zb.add_create_topics_to_zbigtee(topics)
        return _envelope(
            ok=True,
            store_id=store.id,
            state="READY",
            stage="ADD_PLAN_TOPICS",
            summary=(
                f"Added {res['added_count']} new create topics to '{store.id}' "
                f"(skipped {res['skipped_duplicates_count']} duplicates; total eligible create: "
                f"{res['total_eligible_create_candidates']})."
            ),
            data=res,
        )
    except Exception as exc:
        return _error_envelope(exc, store_id=store_id, stage="ADD_PLAN_TOPICS")


@mcp.tool()
def prepare_article_brief(
    store_id: str,
    plan_id: str = "",
    content_id: str = "",
    campaign_id: str = DEFAULT_CAMPAIGN_ID,
    collection_handle: str = "",
    query: str = "",
) -> Dict[str, Any]:
    """
    Reserve an eligible `create` item in the campaign, accept the Plan proposal on Zbigtee if needed,
    and assemble the Editorial Profile revision + verified Shopify catalog product/media evidence brief.
    """
    try:
        sm = StoreManager(data_dir=DATA_DIR)
        store = sm.get_store(store_id)
        pm = StoreProfileManager(data_dir=DATA_DIR, store_manager=sm)
        cm = CampaignManager(store_manager=sm)
        svc = ShopifyCatalogService(sm)
        zb = ZbigteeUiOperator(sm, store.id)

        runtime_prof = pm.get_runtime_profile(store.id)
        prof_val = pm.validate_profile(store.id)
        if not prof_val.get("ready_for_Prompt"):
            return _envelope(
                ok=False,
                store_id=store.id,
                campaign_id=campaign_id,
                state="BLOCKED_PROFILE",
                stage="PREPARE_ARTICLE_BRIEF",
                error_code="PROFILE_INVALID",
                summary=f"Store '{store.id}' editorial profile is not ready.",
                data=prof_val,
            )

        resolved_cid = (content_id or "").strip()
        resolved_pid = (plan_id or "").strip()
        title = ""

        if resolved_pid and not resolved_cid:
            acc = zb.accept_plan_proposal(resolved_pid)
            resolved_cid = acc.get("content_id") or ""
            title = acc.get("title") or ""

        if not resolved_cid:
            raise ValueError("Either a valid plan_id or content_id must be provided.")

        writing_ctx = zb.get_content_writing_context(resolved_cid)
        if not title:
            title = writing_ctx.get("title") or ""

        run_rec = cm.reserve_or_get_run(
            campaign_id=campaign_id or DEFAULT_CAMPAIGN_ID,
            store_id=store.id,
            plan_id=resolved_pid or None,
            content_id=resolved_cid,
            title=title,
            action="create",
            target_path=None,
            profile_revision=int(runtime_prof.get("profile_revision") or 1),
        )

        # 1. Extract keyword and topic from title / input first
        import re as _re

        raw_t = (title or query or "buying guide").strip()
        m_q = _re.search(r"[“\"']([^”\"']+)[”\"']", raw_t)
        clean_kw = (m_q.group(1) if m_q else raw_t).lower()
        clean_kw = _re.sub(
            r"^(?:trả lời|nội dung cho vùng|trang cho|viết nội dung cho)\s+",
            "",
            clean_kw,
            flags=_re.IGNORECASE,
        )
        clean_kw = _re.sub(r"[^a-z0-9\s-]+", " ", clean_kw)
        clean_kw = " ".join(clean_kw.split()[:6]) or "buying guide"

        # 2. Map keyword and title to an existing verified collection if collection_handle not explicitly provided
        resolved_col_handle = (collection_handle or "").strip()
        if not resolved_col_handle:
            available_collections = (runtime_prof.get("verified_internal_links") or {}).get("collections") or []
            target_text = f"{clean_kw} {raw_t.lower()}"
            best_match_handle = ""
            best_match_score = 0
            generic_collections = {"all", "new-arrivals", "signature-pieces"}
            for col in available_collections:
                c_handle = (col.get("handle") or "").strip()
                if c_handle in generic_collections:
                    continue
                c_title = (col.get("title") or "").strip().lower()
                c_phrase = c_handle.replace("-", " ")
                if _re.search(r"\b" + _re.escape(c_phrase) + r"\b", target_text) or _re.search(r"\b" + _re.escape(c_title) + r"\b", target_text):
                    score = len(c_phrase)
                    if score > best_match_score:
                        best_match_score = score
                        best_match_handle = c_handle
            # Specific domain mappings
            if "wine" in target_text and "rack" in target_text:
                if "wall" in target_text:
                    best_match_handle = "wall-mounted-wine-rack"
                elif not best_match_handle:
                    best_match_handle = "wine-racks"
            if ("tree" in target_text or "branch" in target_text) and ("shelf" in target_text or "bookshelf" in target_text):
                if "wall" in target_text or "mounted" in target_text or "floating" in target_text:
                    best_match_handle = "wall-mounted-tree-bookshelves"
                elif "corner" in target_text:
                    best_match_handle = "corner-bookshelf"
                elif not best_match_handle:
                    best_match_handle = "tree-bookshelves"
            elif "bookshelf" in target_text or "bookshelves" in target_text:
                if "corner" in target_text:
                    best_match_handle = "corner-bookshelf"
                elif "standing" in target_text:
                    best_match_handle = "standing-bookshelf"
                elif "floating" in target_text:
                    best_match_handle = "floating-bookshelf"
                elif not best_match_handle:
                    best_match_handle = "tree-bookshelves"
            resolved_col_handle = best_match_handle

        # 3. Clean search query (strip generic editorial stopwords)
        search_stopwords = {
            "buying", "guide", "tips", "ideas", "fit", "review", "reviews",
            "how", "to", "choose", "choosing", "best", "for", "with", "and", "the",
            "a", "an", "what", "wood", "wooden", "natural", "trang", "cho"
        }
        kw_tokens = [w for w in clean_kw.split() if w not in search_stopwords]
        topical_search_q = (query or "").strip() or " ".join(kw_tokens) or clean_kw

        # 4. Fetch verified catalog products & media candidates strictly matching topic/collection
        products = []
        if resolved_col_handle:
            col_res = svc.search_products(
                store.id,
                collection_handle=resolved_col_handle,
                limit=8,
            )
            products = col_res.get("products") or []

        if not products and topical_search_q:
            prods_res = svc.search_products(
                store.id,
                query=topical_search_q,
                limit=8,
            )
            products = prods_res.get("products") or []

        # If full phrase returned nothing, try core tokens (e.g. "wine rack")
        if not products and len(kw_tokens) >= 2:
            prods_res = svc.search_products(
                store.id,
                query=" ".join(kw_tokens[:2]),
                limit=8,
            )
            products = prods_res.get("products") or []

        # STRICT: NEVER fallback to query="" which pollutes the brief with unrelated products!

        # 5. Ensure Zbigtee brief has verified material (images, facts, featuredProducts, csQuestions)
        existing_zb_brief = writing_ctx.get("brief") or {}
        existing_mat = (existing_zb_brief.get("material") or {}) if isinstance(existing_zb_brief, dict) else {}
        if (
            bool(topical_search_q or resolved_col_handle)
            or len(existing_mat.get("images") or []) < 6
            or (writing_ctx.get("status") or "").lower() in ("idea", "brief")
        ):
            mat_images = []
            seen_img_urls = set()
            for p in products[:6]:
                for m in (p.get("media") or [])[:3]:
                    u = (m.get("url") or "").strip()
                    if u and u not in seen_img_urls:
                        seen_img_urls.add(u)
                        mat_images.append(
                            {
                                "file": u[:290],
                                "shows": (m.get("alt") or p.get("title") or "Product image").strip()[:240],
                            }
                        )
                    if len(mat_images) >= 10:
                        break
                if len(mat_images) >= 10:
                    break

            # Verified facts for AI brief generation: Put VERIFIED CATALOG PRODUCTS FIRST
            # so they are never truncated by the brief API slice.
            verified_facts = []
            verified_facts.append("--- VERIFIED PRODUCTS IN CATALOG ---")
            for p in products[:5]:
                pr = p.get("price_range") or {}
                opts = ", ".join(
                    f"{o.get('name')}: {', '.join((o.get('values') or [])[:5])}"
                    for o in (p.get("options") or [])
                    if o.get("name") and o.get("name") != "Title"
                )
                fact_line = f"{p['title']} (/products/{p['handle']}) priced ${pr.get('min')} to ${pr.get('max')}"
                if opts:
                    fact_line += f" ({opts})"
                verified_facts.append((fact_line[:275].rstrip() + "."))

            verified_facts.append("--- ALLOWED POLICY CLAIMS ---")
            for pol_key, pol_obj in (runtime_prof.get("policies") or {}).items():
                if isinstance(pol_obj, dict):
                    for claim in (pol_obj.get("allowed_claims") or []):
                        clean_claim = str(claim or "").strip()[:280]
                        if clean_claim and clean_claim not in verified_facts:
                            verified_facts.append(clean_claim)

            verified_facts.append("--- FORBIDDEN CLAIMS (DO NOT CLAIM) ---")
            for pol_key, pol_obj in (runtime_prof.get("policies") or {}).items():
                if isinstance(pol_obj, dict):
                    for f_claim in (pol_obj.get("forbidden_claims") or []):
                        clean_f = str(f_claim or "").strip()[:280]
                        if clean_f:
                            verified_facts.append(f"DO NOT CLAIM: {clean_f}")
            for dnc in (runtime_prof.get("do_not_claim") or []):
                clean_dnc = str(dnc or "").strip()[:280]
                if clean_dnc:
                    verified_facts.append(f"DO NOT CLAIM: {clean_dnc}")

            base_dom = store.resolved_public_domain.rstrip("/")
            internal_links = [
                {
                    "url": f"{base_dom}/products/{p['handle']}",
                    "anchor": f"compare specifications for {p['title']}",
                }
                for p in products[:4]
            ]
            questions_list = [
                f"What should you check first about {clean_kw}?",
                f"How do sizes, options, and materials compare for {clean_kw}?",
                f"What delivery and return rules apply when ordering from {runtime_prof.get('brand_name') or store.name}?",
            ]
            try:
                zb._trpc_post(
                    "content.brief.save",
                    {
                        "contentId": resolved_cid,
                        "primaryKeyword": existing_zb_brief.get("primaryKeyword") or clean_kw,
                        "secondary": existing_zb_brief.get("secondary") or [clean_kw],
                        "targetWords": int(existing_zb_brief.get("targetWords") or 1400),
                        "outline": str(existing_zb_brief.get("outline") or ""),
                        "mustHave": existing_zb_brief.get("mustHave") or [{"term": clean_kw}],
                        "questions": existing_zb_brief.get("questions") or questions_list,
                        "competitors": [],
                        "internalLinks": internal_links,
                        "material": {
                            "images": mat_images,
                            "csQuestions": questions_list,
                            "verifiedFacts": verified_facts[:30],
                            "featuredProducts": [
                                {
                                    "url": f"{base_dom}/products/{p['handle']}",
                                    "name": p["title"],
                                    "why": f"${(p.get('price_range') or {}).get('min')}",
                                }
                                for p in products[:5]
                            ],
                        },
                    },
                )
                if (writing_ctx.get("status") or "").lower() in ("idea", "brief"):
                    zb._trpc_post("content.setStatus", {"id": resolved_cid, "to": "writing"})
                writing_ctx = zb.get_content_writing_context(resolved_cid)
            except Exception as _zb_exc:
                logger.warning("Non-fatal warning enriching Zbigtee brief for %s: %s", resolved_cid, _zb_exc)

        brief_payload = {
            "store_id": store.id,
            "campaign_id": campaign_id,
            "run_id": run_rec["run_id"],
            "plan_id": resolved_pid or None,
            "content_id": resolved_cid,
            "title": title,
            "profile_revision": runtime_prof.get("profile_revision"),
            "runtime_profile": runtime_prof,
            "zbigtee_brief": writing_ctx.get("brief"),
            "zbigtee_status": writing_ctx.get("status"),
            "verified_products": [
                {
                    "product_id": p["product_id"],
                    "handle": p["handle"],
                    "title": p["title"],
                    "storefront_url": p["storefront_url"],
                    "price_range": p["price_range"],
                    "options": p["options"],
                    "media_count": p["media_count"],
                    "sample_media": (p.get("media") or [])[:3],
                }
                for p in products[:6]
            ],
            "prepared_at": _now_iso(),
        }

        brief_dir = OUTPUT_DIR / store.id
        brief_dir.mkdir(parents=True, exist_ok=True)
        brief_path = brief_dir / f"{resolved_cid}_brief.json"
        brief_path.write_text(json.dumps(brief_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        updated_run = cm.transition_run_state(
            campaign_id=campaign_id or DEFAULT_CAMPAIGN_ID,
            run_id=run_rec["run_id"],
            to_state="BRIEF_READY",
            stage="PREPARE_ARTICLE_BRIEF",
            summary=f"Prepared brief for '{title}' ({resolved_cid})",
            artifact_updates={"brief_path": str(brief_path.relative_to(MODULE_DIR))},
        )

        return _envelope(
            ok=True,
            store_id=store.id,
            campaign_id=campaign_id,
            run_id=updated_run["run_id"],
            state=updated_run["state"],
            stage="PREPARE_ARTICLE_BRIEF",
            summary=f"Brief ready for '{title}' (content_id={resolved_cid}, run_id={updated_run['run_id']}).",
            artifact_paths=updated_run.get("artifact_paths") or {},
            data=brief_payload,
            next_actions=["Call generate_or_fetch_draft to submit or generate the article draft on Zbigtee."],
        )
    except Exception as exc:
        return _error_envelope(exc, store_id=store_id, campaign_id=campaign_id, stage="PREPARE_ARTICLE_BRIEF")


@mcp.tool()
def generate_or_fetch_draft(
    store_id: str,
    content_id: str,
    campaign_id: str = DEFAULT_CAMPAIGN_ID,
    run_id: str = "",
    raw_submission: str = "",
    use_ai_generate: bool = False,
) -> Dict[str, Any]:
    """
    Submit a structured draft (`raw_submission`) or trigger Zbigtee writer (`use_ai_generate`),
    move the card to `review`, and scrape the 5-field `/preview` payload into `input/<store_id>/`.
    """
    try:
        sm = StoreManager(data_dir=DATA_DIR)
        store = sm.get_store(store_id)
        zb = ZbigteeUiOperator(sm, store.id)
        cm = CampaignManager(store_manager=sm)

        res = zb.submit_or_generate_draft(
            content_id=content_id,
            raw_submission=raw_submission if raw_submission.strip() else None,
            use_ai_generate=use_ai_generate,
            move_to_review=True,
        )
        preview = res.get("preview_payload") or {}
        ok = bool(res.get("ok") and (preview.get("body_html") or "").strip())

        if run_id:
            cm.transition_run_state(
                campaign_id=campaign_id or DEFAULT_CAMPAIGN_ID,
                run_id=run_id,
                to_state="DRAFT_READY" if ok else "RESERVED",
                stage="GENERATE_OR_FETCH_DRAFT",
                summary=f"Fetched Zbigtee preview payload for {content_id} (ok={ok})",
                artifact_updates={"raw_preview_path": f"input/{store.id}/{content_id}_preview.json"},
                metadata_updates={"slug": preview.get("slug") or ""},
            )

        return _envelope(
            ok=ok,
            store_id=store.id,
            campaign_id=campaign_id,
            run_id=run_id or None,
            state="DRAFT_READY" if ok else "ERROR",
            stage="GENERATE_OR_FETCH_DRAFT",
            error_code=None if ok else "CONTENT_TOO_SHORT",
            summary=(
                f"Draft for '{preview.get('title') or content_id}' scraped from Zbigtee /preview "
                f"(slug={preview.get('slug')}, html_chars={len(preview.get('body_html') or '')})."
            ),
            artifact_paths={"raw_preview_path": f"input/{store.id}/{content_id}_preview.json"},

            data={
                "content_id": content_id,
                "status": res.get("status"),
                "title": preview.get("title"),
                "slug": preview.get("slug"),
                "meta_description": preview.get("meta_description"),
                "shop_images_count": len(preview.get("shop_images") or []),
            },
            next_actions=["Call heal_article_images, sanitize_article_claims, and validate_article."],
        )
    except Exception as exc:
        return _error_envelope(
            exc,
            store_id=store_id,
            campaign_id=campaign_id,
            run_id=run_id or None,
            stage="GENERATE_OR_FETCH_DRAFT",
        )


# ---------------------------------------------------------------------------
# 3. Catalog Evidence, Claim Sanitizer, Image Healer & Prepublish Gate Tools
# ---------------------------------------------------------------------------
@mcp.tool()
def query_store_catalog_assets(
    store_id: str,
    query: str = "",
    collection_handle: str = "",
    product_id_or_handle: str = "",
    urls: Optional[List[str]] = None,
    limit: int = 12,
) -> Dict[str, Any]:
    """Query Shopify Admin GraphQL API and Storefront via Proxy for product/variant/media evidence and live URL checks."""
    try:
        sm = StoreManager(data_dir=DATA_DIR)
        store = sm.get_store(store_id)
        svc = ShopifyCatalogService(sm)

        out_data: Dict[str, Any] = {}
        if product_id_or_handle and product_id_or_handle.strip():
            out_data["product_evidence"] = svc.get_product_evidence(store.id, product_id_or_handle.strip())
        if query.strip() or collection_handle.strip() or not out_data:
            out_data["search_results"] = svc.search_products(
                store.id,
                query=query.strip(),
                collection_handle=collection_handle.strip(),
                limit=limit,
            )
        if urls:
            out_data["url_checks"] = svc.verify_storefront_urls(store.id, urls)

        return _envelope(
            ok=True,
            store_id=store.id,
            state="READY",
            stage="QUERY_STORE_CATALOG_ASSETS",
            summary=f"Queried catalog evidence for store '{store.id}' via Proxy.",
            data=out_data,
        )
    except Exception as exc:
        return _error_envelope(exc, store_id=store_id, stage="QUERY_STORE_CATALOG_ASSETS")


@mcp.tool()
def sanitize_article_claims(
    store_id: str,
    content_id_or_slug: str,
    campaign_id: str = DEFAULT_CAMPAIGN_ID,
    run_id: str = "",
    apply_fixes: bool = True,
) -> Dict[str, Any]:
    """Audit and optionally sanitize unsupported factual/policy claims across title, meta, body HTML, and FAQ."""
    try:
        sm = StoreManager(data_dir=DATA_DIR)
        store = sm.get_store(store_id)
        pipe = BlogSyncPipeline(sm, store.id)
        raw_payload = pipe.zbigtee.get_preview_payload(content_id_or_slug)
        processed: PostProcessedArticle = pipe.postprocessor.process_preview_payload(raw_payload)

        out_dir = OUTPUT_DIR / store.id
        out_dir.mkdir(parents=True, exist_ok=True)
        existing_html_file = out_dir / f"{processed.handle}_processed.html"
        if not existing_html_file.exists():
            existing_html_file = out_dir / f"{processed.handle}.html"
        existing_json_file = out_dir / f"{processed.handle}_processed.json"
        if not existing_json_file.exists():
            existing_json_file = out_dir / f"{processed.handle}.json"
        existing_manifest_file = out_dir / f"{processed.handle}_media_manifest.json"
        if existing_html_file.exists() and existing_manifest_file.exists():
            try:
                processed.body_html = existing_html_file.read_text(encoding="utf-8")
                processed.media_manifest_path = str(existing_manifest_file)
                if existing_json_file.exists():
                    cached_art = json.loads(existing_json_file.read_text(encoding="utf-8"))
                    if isinstance(cached_art.get("featured_image"), dict) and cached_art["featured_image"].get("url"):
                        processed.featured_image = cached_art["featured_image"]
            except Exception:
                pass

        if apply_fixes:
            san_res = pipe.fact_auditor.sanitize_article_claims(
                store_id=store.id,
                title=processed.title,
                handle=processed.handle,
                body_html=processed.body_html,
                summary=processed.summary,
                seo_title=processed.seo_title,
                seo_description=processed.seo_description,
                content_id=processed.content_id,
                verify_live_urls=True,
            )
            processed.body_html = san_res["body_html"]
            processed.summary = san_res["summary"]
            processed.seo_description = san_res["seo_description"]
            report_dict = san_res["report"]
        else:
            report = pipe.fact_auditor.audit_article(
                store_id=store.id,
                title=processed.title,
                handle=processed.handle,
                body_html=processed.body_html,
                summary=processed.summary,
                seo_title=processed.seo_title,
                seo_description=processed.seo_description,
                content_id=processed.content_id,
                verify_live_urls=True,
            )
            report_dict = report.to_dict()

        out_dir = OUTPUT_DIR / store.id
        out_dir.mkdir(parents=True, exist_ok=True)
        fact_path = out_dir / f"{processed.handle}_fact_audit.json"
        fact_path.write_text(json.dumps(report_dict, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        pipe.postprocessor.refresh_warnings_and_counts(processed)
        pipe.postprocessor.save_processed_article(processed)

        ok = bool(report_dict.get("passed"))
        if run_id:
            cm = CampaignManager(store_manager=sm)
            cm.transition_run_state(
                campaign_id=campaign_id or DEFAULT_CAMPAIGN_ID,
                run_id=run_id,
                to_state="FACTS_REVIEWED" if ok else "BLOCKED_FACTS",
                stage="SANITIZE_ARTICLE_CLAIMS",
                error_code=None if ok else "FACT_UNSUPPORTED",
                summary=f"Fact audit ok={ok} (blocking={len(report_dict.get('blocking_errors') or [])})",
                artifact_updates={"fact_audit_report": str(fact_path.relative_to(MODULE_DIR))},
            )

        return _envelope(
            ok=ok,
            store_id=store.id,
            campaign_id=campaign_id,
            run_id=run_id or None,
            state="FACTS_REVIEWED" if ok else "BLOCKED_FACTS",
            stage="SANITIZE_ARTICLE_CLAIMS",
            error_code=None if ok else "FACT_UNSUPPORTED",
            summary=(
                f"Fact audit for '{processed.handle}': ok={ok}, "
                f"blocking={len(report_dict.get('blocking_errors') or [])}."
            ),
            findings=report_dict.get("findings") or [],
            artifact_paths={"fact_audit_report": str(fact_path.relative_to(MODULE_DIR))},
            data=report_dict,
        )
    except Exception as exc:
        return _error_envelope(
            exc,
            store_id=store_id,
            campaign_id=campaign_id,
            run_id=run_id or None,
            stage="SANITIZE_ARTICLE_CLAIMS",
        )


@mcp.tool()
def heal_article_images(
    store_id: str,
    content_id_or_slug: str,
    campaign_id: str = DEFAULT_CAMPAIGN_ID,
    run_id: str = "",
    extra_search_queries: Optional[List[str]] = None,
    visual_reviews: Optional[Dict[str, Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Heal and enrich article body & hero images to 4–7 context-matched, SHA-256 deduplicated catalog images,
    downloading cached copies via Proxy for visual inspection and optionally recording visual review verdicts.
    """
    try:
        sm = StoreManager(data_dir=DATA_DIR)
        store = sm.get_store(store_id)
        pipe = BlogSyncPipeline(sm, store.id)
        raw_payload = pipe.zbigtee.get_preview_payload(content_id_or_slug)
        processed: PostProcessedArticle = pipe.postprocessor.process_preview_payload(raw_payload)

        healed_html, healed_hero, manifest = pipe.image_service.heal_and_enrich_article_images(
            article_title=processed.title,
            handle=processed.handle,
            content_id=processed.content_id,
            body_html=processed.body_html,
            featured_image=processed.featured_image,
            shop_images=list(raw_payload.get("shop_images") or []),
            extra_search_queries=extra_search_queries,
        )
        manifest_path_str = pipe.image_service.save_media_manifest(manifest)
        processed.body_html = healed_html
        processed.featured_image = healed_hero
        processed.body_image_count = manifest.body_image_count
        processed.media_manifest_path = manifest_path_str
        pipe.postprocessor.refresh_warnings_and_counts(processed)
        pipe.postprocessor.save_processed_article(processed)

        manifest_data = manifest.to_dict()
        if visual_reviews:
            manifest_data = ArticleImageService.record_visual_review(
                manifest_path=manifest_path_str,
                reviews=visual_reviews,
                reviewer="antigravity_mcp_visual_review",
            )

        ok = bool(manifest_data.get("ok"))
        rel_manifest = str(Path(manifest_path_str).resolve().relative_to(MODULE_DIR.resolve()))

        if run_id:
            cm = CampaignManager(store_manager=sm)
            cm.transition_run_state(
                campaign_id=campaign_id or DEFAULT_CAMPAIGN_ID,
                run_id=run_id,
                to_state="MEDIA_REVIEWED" if ok else "BLOCKED_MEDIA",
                stage="HEAL_ARTICLE_IMAGES",
                error_code=None if ok else "INSUFFICIENT_IMAGES",
                summary=f"Media healed: {manifest_data.get('unique_body_image_count')} unique body images (ok={ok})",
                artifact_updates={"media_manifest": rel_manifest},
            )

        return _envelope(
            ok=ok,
            store_id=store.id,
            campaign_id=campaign_id,
            run_id=run_id or None,
            state="MEDIA_REVIEWED" if ok else "BLOCKED_MEDIA",
            stage="HEAL_ARTICLE_IMAGES",
            error_code=None if ok else "INSUFFICIENT_IMAGES",
            summary=(
                f"Healed images for '{processed.handle}': {manifest_data.get('unique_body_image_count')} unique body images, "
                f"hero_ok={bool(manifest_data.get('featured_image'))}."
            ),
            artifact_paths={"media_manifest": rel_manifest},
            data=manifest_data,
            next_actions=["Inspect cached images via view_file, then call validate_article."],
        )
    except Exception as exc:
        return _error_envelope(
            exc,
            store_id=store_id,
            campaign_id=campaign_id,
            run_id=run_id or None,
            stage="HEAL_ARTICLE_IMAGES",
        )


@mcp.tool()
def validate_article(
    store_id: str,
    content_id_or_slug: str,
    campaign_id: str = DEFAULT_CAMPAIGN_ID,
    run_id: str = "",
    min_word_count: int = 900,
) -> Dict[str, Any]:
    """Run the unified prepublish audit gate (profile, fact audit, image healing 4–7 images, word count >= 900, ready_digest)."""
    try:
        sm = StoreManager(data_dir=DATA_DIR)
        store = sm.get_store(store_id)
        pipe = BlogSyncPipeline(sm, store.id)
        raw_payload = pipe.zbigtee.get_preview_payload(content_id_or_slug)
        processed = pipe.postprocessor.process_preview_payload(raw_payload)
        audit_res = pipe.audit_prepublish(
            processed,
            raw_payload=raw_payload,
            sanitize_claims=True,
            heal_images=True,
            min_word_count=min_word_count,
        )
        ok = bool(audit_res.get("ok"))
        ready_digest = audit_res.get("ready_digest") or ""
        handle = audit_res.get("handle") or processed.handle

        if run_id:
            cm = CampaignManager(store_manager=sm)
            cm.transition_run_state(
                campaign_id=campaign_id or DEFAULT_CAMPAIGN_ID,
                run_id=run_id,
                to_state="PREPUBLISH_READY" if ok else "BLOCKED_FACTS",
                stage="VALIDATE_ARTICLE",
                error_code=None if ok else "FACT_UNSUPPORTED",
                summary=f"Prepublish validation ok={ok}, ready_digest={ready_digest}",
                artifact_updates=audit_res.get("saved_paths") or {},
                metadata_updates={
                    "slug": handle,
                    "ready_digest": ready_digest,
                },
            )

        return _envelope(
            ok=ok,
            store_id=store.id,
            campaign_id=campaign_id,
            run_id=run_id or None,
            state="PREPUBLISH_READY" if ok else "BLOCKED_FACTS",
            stage="VALIDATE_ARTICLE",
            error_code=None if ok else "FACT_UNSUPPORTED",
            summary=(
                f"Prepublish audit for '{handle}': ok={ok}, "
                f"words={audit_res.get('word_count')}, images={audit_res.get('body_image_count')}, "
                f"ready_digest={ready_digest}."
            ),
            findings=[
                {"severity": "error", "code": "PREPUBLISH_GATE", "message": reason}
                for reason in (audit_res.get("blocking_reasons") or [])
            ],
            artifact_paths=audit_res.get("saved_paths") or {},
            data=audit_res,
            next_actions=(
                [f"Call publish_and_verify_article with approved_ready_digest='{ready_digest}'."]
                if ok
                else ["Fix blocking_reasons before publishing."]
            ),
        )
    except Exception as exc:
        return _error_envelope(
            exc,
            store_id=store_id,
            campaign_id=campaign_id,
            run_id=run_id or None,
            stage="VALIDATE_ARTICLE",
        )


# ---------------------------------------------------------------------------
# 4. Publish, Verify, Status, Resume & Acceptance Pilot Tools
# ---------------------------------------------------------------------------
@mcp.tool()
def publish_and_verify_article(
    store_id: str,
    content_id_or_slug: str,
    approved_ready_digest: str = "",
    campaign_id: str = DEFAULT_CAMPAIGN_ID,
    run_id: str = "",
    blog_id_or_handle: str = "",
) -> Dict[str, Any]:
    """
    Publish an audited article to Shopify (`create_only` baseline protection), read back via Admin API,
    run the 16-check Desktop+Mobile Playwright live verifier via Proxy, and mark Zbigtee `published`
    ONLY if live verification passes.
    """
    try:
        sm = StoreManager(data_dir=DATA_DIR)
        store = sm.get_store(store_id)
        cm = CampaignManager(store_manager=sm)
        cid = (campaign_id or DEFAULT_CAMPAIGN_ID).strip()

        protected = cm.get_protected_baseline_sets(store.id, cid)
        existing_run = cm.get_run(cid, run_id) if run_id else None
        owned_article_id = (existing_run or {}).get("shopify_article_id")

        # Idempotent short-circuit if this exact run already completed
        if existing_run and existing_run.get("state") == "COMPLETED" and owned_article_id:
            return _envelope(
                ok=True,
                store_id=store.id,
                campaign_id=cid,
                run_id=run_id,
                state="COMPLETED",
                stage="PUBLISH_AND_VERIFY_ARTICLE",
                summary=(
                    f"Idempotent rerun: run '{run_id}' is already COMPLETED with "
                    f"article_id={owned_article_id} (no duplicate created)."
                ),
                artifact_paths=existing_run.get("artifact_paths") or {},
                data={
                    "idempotent_short_circuit": True,
                    "run": existing_run,
                },
            )

        pipe = BlogSyncPipeline(sm, store.id)
        sync_res = pipe.sync_and_publish(
            content_id_or_slug=content_id_or_slug,
            blog_id_or_handle=blog_id_or_handle or None,
            verify=True,
            publish_mode="create_only",
            owned_article_id=owned_article_id,
            protected_article_ids=protected.get("protected_article_ids"),
            protected_handles=protected.get("protected_handles"),
            approved_ready_digest=approved_ready_digest or None,
        )

        ok = bool(sync_res.get("ok"))
        terminal_state = sync_res.get("state") or ("COMPLETED" if ok else "LIVE_FAILED")
        pub_info = sync_res.get("publish") or {}
        zb_sync = sync_res.get("zbigtee_publish_sync") or {}

        if run_id:
            cm.transition_run_state(
                campaign_id=cid,
                run_id=run_id,
                to_state=(
                    terminal_state
                    if terminal_state in ("COMPLETED", "LIVE_FAILED", "ZBIGTEE_SYNC_PENDING")
                    else ("COMPLETED" if ok else "LIVE_FAILED")
                ),
                stage="PUBLISH_AND_VERIFY_ARTICLE",
                error_code=None if ok else "LIVE_VERIFY_FAILED",
                summary=f"Publish & verify finished with state={terminal_state}, ok={ok}",
                artifact_updates=(sync_res.get("saved_paths") or {}),
                metadata_updates={
                    "handle": pub_info.get("handle") or "",
                    "slug": pub_info.get("handle") or "",
                    "shopify_article_id": pub_info.get("article_id") or "",
                    "shopify_url": pub_info.get("myshopify_url") or "",
                    "public_url": pub_info.get("public_url") or "",
                    "published_url": pub_info.get("public_url") or pub_info.get("myshopify_url") or "",
                    "zbigtee_synced": bool(zb_sync.get("marked_on_zbigtee")),
                },
            )

        return _envelope(
            ok=ok,
            store_id=store.id,
            campaign_id=cid,
            run_id=run_id or None,
            state=terminal_state,
            stage="PUBLISH_AND_VERIFY_ARTICLE",
            error_code=None if ok else "LIVE_VERIFY_FAILED",
            summary=(
                f"Article '{pub_info.get('handle')}' state={terminal_state} "
                f"(id={pub_info.get('article_id')}, url={pub_info.get('public_url') or pub_info.get('myshopify_url')})."
            ),
            artifact_paths=sync_res.get("saved_paths") or {},
            data=sync_res,
        )
    except Exception as exc:
        return _error_envelope(
            exc,
            store_id=store_id,
            campaign_id=campaign_id,
            run_id=run_id or None,
            stage="PUBLISH_AND_VERIFY_ARTICLE",
            default_code="PUBLISH_FAILED",
        )


@mcp.tool()
def get_run_status(
    store_id: str = "",
    campaign_id: str = DEFAULT_CAMPAIGN_ID,
    run_id: str = "",
) -> Dict[str, Any]:
    """Read-only status check for a campaign or specific article run without mutating any state."""
    try:
        sm = StoreManager(data_dir=DATA_DIR)
        cm = CampaignManager(store_manager=sm)
        cid = (campaign_id or DEFAULT_CAMPAIGN_ID).strip()
        status = cm.get_campaign_status(cid, store_id=store_id or None, run_id=run_id or None)
        return _envelope(
            ok=True,
            store_id=store_id or None,
            campaign_id=cid,
            run_id=run_id or None,
            state=status.get("run", {}).get("state", "READY") if run_id else "READY",
            stage="GET_RUN_STATUS",
            summary=f"Status retrieved for campaign='{cid}' (run_id='{run_id or 'ALL'}').",
            data=status,
        )
    except Exception as exc:
        return _error_envelope(
            exc,
            store_id=store_id or None,
            campaign_id=campaign_id,
            run_id=run_id or None,
            stage="GET_RUN_STATUS",
        )


@mcp.tool()
def resume_run(
    store_id: str,
    campaign_id: str = DEFAULT_CAMPAIGN_ID,
    run_id: str = "",
) -> Dict[str, Any]:
    """
    Reconcile external Shopify & Zbigtee state for an interrupted or pending run (`LIVE_FAILED`,
    `ZBIGTEE_SYNC_PENDING`, `PREPUBLISH_READY`), and safely resume without creating duplicate articles.
    """
    try:
        sm = StoreManager(data_dir=DATA_DIR)
        store = sm.get_store(store_id)
        cm = CampaignManager(store_manager=sm)
        cid = (campaign_id or DEFAULT_CAMPAIGN_ID).strip()
        run = cm.get_run(cid, run_id)
        curr_state = run.get("state")

        if curr_state == "COMPLETED":
            return _envelope(
                ok=True,
                store_id=store.id,
                campaign_id=cid,
                run_id=run_id,
                state="COMPLETED",
                stage="RESUME_RUN",
                summary=f"Run '{run_id}' is already COMPLETED. No mutation performed.",
                data={"run": run, "idempotent_noop": True},
            )

        content_key = run.get("content_id") or run.get("slug") or ""
        ready_digest = run.get("ready_digest") or ""
        if not ready_digest:
            val_res = validate_article(store.id, content_key, campaign_id=cid, run_id=run_id)
            if not val_res.get("ok"):
                return val_res
            ready_digest = (val_res.get("data") or {}).get("ready_digest") or ""

        return publish_and_verify_article(
            store_id=store.id,
            content_id_or_slug=content_key,
            approved_ready_digest=ready_digest,
            campaign_id=cid,
            run_id=run_id,
        )
    except Exception as exc:
        return _error_envelope(exc, store_id=store_id, campaign_id=campaign_id, run_id=run_id, stage="RESUME_RUN")


@mcp.tool()
def run_acceptance_pilot(
    campaign_id: str = DEFAULT_CAMPAIGN_ID,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Run or inspect the 6-article Acceptance Pilot cohort (3 first eligible `create` articles for `preaureum`
    + 3 first eligible `create` articles for `wrydeco`).
    """
    try:
        from acceptance_runner import AcceptancePilotRunner

        runner = AcceptancePilotRunner(campaign_id=campaign_id or DEFAULT_CAMPAIGN_ID)
        if dry_run:
            plan = runner.select_pilot_cohort()
            return _envelope(
                ok=True,
                campaign_id=runner.campaign_id,
                state="READY",
                stage="RUN_ACCEPTANCE_PILOT_DRY_RUN",
                summary="Selected 3 Preaureum + 3 WRYDECO eligible create candidates for pilot acceptance.",
                data=plan,
            )
        report = runner.run_pilot()
        ok = bool(report.get("ok"))
        return _envelope(
            ok=ok,
            campaign_id=runner.campaign_id,
            state="COMPLETED" if ok else "LIVE_FAILED",
            stage="RUN_ACCEPTANCE_PILOT",
            error_code=None if ok else "LIVE_VERIFY_FAILED",
            summary=report.get("summary") or f"Pilot acceptance finished: ok={ok}.",
            artifact_paths=report.get("artifact_paths") or {},
            data=report,
        )
    except Exception as exc:
        return _error_envelope(exc, campaign_id=campaign_id, stage="RUN_ACCEPTANCE_PILOT")


def run_stdio_server() -> None:
    """Entrypoint to run the MCP server over stdio."""
    logger.info("Starting wrydeco-blog-scaling-mcp over stdio...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_stdio_server()
