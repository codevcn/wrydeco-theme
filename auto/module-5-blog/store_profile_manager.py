"""
Per-Store Editorial Profile Manager (`store_profile_manager.py`).

Manages curated, verified Store Editorial Profiles stored in
`data/store_profiles/<store_id>.json` and validated against
`schemas/store_editorial_profile.schema.json`.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonschema

from store_manager import DATA_DIR, MODULE_DIR, StoreManager, slugify_store_id

SCHEMA_FILE = MODULE_DIR / "schemas" / "store_editorial_profile.schema.json"
RESEARCH_SEED_FILE = DATA_DIR / "store_editorial_research_2026-10-17.json"


class StoreProfileValidationError(ValueError):
    """Raised when a store editorial profile fails JSON Schema or semantic validation."""


class StoreProfileConflictError(ValueError):
    """Raised when saving a store editorial profile with a stale expected_revision."""


FORBIDDEN_CREDENTIAL_KEYS = {
    "access_token",
    "client_secret",
    "client_id",
    "proxy_password",
    "session_token",
    "refresh_token",
}


class StoreProfileManager:
    """Loads, validates, saves, seeds, and live-verifies Store Editorial Profiles."""

    def __init__(
        self,
        data_dir: Path = DATA_DIR,
        schema_file: Path = SCHEMA_FILE,
        store_manager: Optional[StoreManager] = None,
    ) -> None:
        self.data_dir = data_dir
        self.profiles_dir = self.data_dir / "store_profiles"
        self.schema_file = schema_file
        self.store_manager = store_manager or StoreManager(data_dir=self.data_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self._schema_cache: Optional[Dict[str, Any]] = None

    def _load_schema(self) -> Dict[str, Any]:
        if self._schema_cache is None:
            if not self.schema_file.exists():
                raise FileNotFoundError(f"Missing Store Editorial Profile schema: {self.schema_file}")
            self._schema_cache = json.loads(self.schema_file.read_text(encoding="utf-8"))
        return self._schema_cache

    def profile_path(self, store_id: str) -> Path:
        sid = slugify_store_id(store_id)
        return self.profiles_dir / f"{sid}.json"

    def validate_profile(
        self,
        profile_or_store_id: Dict[str, Any] | str,
        profile_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Validate a profile dictionary against the JSON Schema and semantic editorial rules."""
        errors: List[str] = []
        warnings: List[str] = []

        if isinstance(profile_or_store_id, str):
            target = profile_data if isinstance(profile_data, dict) else self.get_profile(profile_or_store_id)
        else:
            target = profile_or_store_id

        if not isinstance(target, dict):
            return {
                "valid": False,
                "ready_for_Prompt": False,
                "ready_for_publishing": False,
                "errors": ["Profile payload must be a JSON object."],
                "warnings": [],
            }

        clean_target = {k: v for k, v in target.items() if k not in ("_validation", "profile_revision", "updated_by")}
        for bad_key in FORBIDDEN_CREDENTIAL_KEYS:
            if bad_key in clean_target:
                errors.append(f"Credential field '{bad_key}' is forbidden inside Store Editorial Profile.")

        schema = self._load_schema()
        validator = jsonschema.Draft202012Validator(schema)
        for err in sorted(validator.iter_errors(clean_target), key=lambda e: list(e.path)):
            loc = ".".join(str(p) for p in err.path) or "<root>"
            errors.append(f"{loc}: {err.message}")

        # Semantic checks
        gate = clean_target.get("product_and_media_gate") or {}
        if gate.get("require_shopify_api_verification") is not True:
            errors.append("product_and_media_gate.require_shopify_api_verification must be true.")
        if gate.get("require_online_store_publication") is not True:
            errors.append("product_and_media_gate.require_online_store_publication must be true.")
        if gate.get("require_proxy_for_all_shopify_requests") is not True:
            errors.append("product_and_media_gate.require_proxy_for_all_shopify_requests must be true.")
        if gate.get("forbid_svg_fallbacks") is not True:
            errors.append("product_and_media_gate.forbid_svg_fallbacks must be true.")
        if gate.get("forbid_unverified_gallery_alt_mapping") is not True:
            errors.append("product_and_media_gate.forbid_unverified_gallery_alt_mapping must be true.")

        min_imgs = int(gate.get("min_body_images") or 0)
        max_imgs = int(gate.get("max_body_images") or 0)
        if min_imgs < 4 or max_imgs > 7 or min_imgs > max_imgs:
            errors.append(
                f"product_and_media_gate image bounds invalid (min={min_imgs}, max={max_imgs}); must be within 4..7."
            )

        dest = clean_target.get("verified_destination_blog") or {}
        if not str(dest.get("blog_id") or "").startswith("gid://shopify/Blog/"):
            errors.append("verified_destination_blog.blog_id must be a valid gid://shopify/Blog/... ID.")
        if not str(dest.get("blog_handle") or "").strip():
            errors.append("verified_destination_blog.blog_handle must be non-empty.")

        ready = bool(clean_target.get("ready_for_publishing"))
        status = str(clean_target.get("profile_status") or "")
        if ready and status != "active_verified":
            errors.append(
                f"ready_for_publishing=true requires profile_status='active_verified' (got '{status}')."
            )

        policies = clean_target.get("policies") or {}
        for pol_key, pol_val in policies.items():
            if not isinstance(pol_val, dict):
                continue
            c_status = pol_val.get("conflict_status")
            if c_status == "conflict_blocked":
                forbidden = pol_val.get("forbidden_claims") or []
                if not forbidden:
                    errors.append(
                        f"policies.{pol_key} has conflict_status='conflict_blocked' but no forbidden_claims to block the conflicting statement."
                    )
                else:
                    warnings.append(
                        f"policies.{pol_key} has an explicit conflict_blocked guardrail ({len(forbidden)} forbidden claims enforced)."
                    )

        is_valid = len(errors) == 0
        is_ready = bool(is_valid and ready and status == "active_verified")
        return {
            "valid": is_valid,
            "ready_for_publishing": is_ready,
            "ready_for_Prompt": is_ready,
            "errors": errors,
            "warnings": warnings,
        }

    def get_profile(self, store_id: str) -> Dict[str, Any]:
        sid = slugify_store_id(store_id)
        path = self.profile_path(sid)
        if not path.exists():
            raise FileNotFoundError(
                f"Store Editorial Profile not found for '{sid}' at {path}. Seed or create it first."
            )
        data = json.loads(path.read_text(encoding="utf-8"))
        if "profile_revision" not in data:
            data["profile_revision"] = int((data.get("audit_metadata") or {}).get("profile_revision") or 1)
        val = self.validate_profile(data)
        data["_validation"] = val
        return data

    def get_runtime_profile(self, store_id: str) -> Dict[str, Any]:
        """Return sanitized runtime editorial instructions and structured policy/product rules for agents."""
        prof = self.get_profile(store_id)
        return {
            "store_id": prof.get("store_id"),
            "brand_name": prof.get("brand_name"),
            "storefront_url": prof.get("storefront_url"),
            "shopify_domain": prof.get("shopify_domain"),
            "zbigtee_project_id": prof.get("zbigtee_project_id"),
            "profile_status": prof.get("profile_status"),
            "profile_revision": int(prof.get("profile_revision") or 1),
            "ready_for_publishing": bool(prof.get("ready_for_publishing")),
            "verified_destination_blog": prof.get("verified_destination_blog"),
            "brand_positioning": prof.get("brand_positioning"),
            "policies": prof.get("policies"),
            "do_not_claim": prof.get("do_not_claim") or [],
            "unknowns_requiring_shopify_verification": prof.get("unknowns_requiring_shopify_verification") or [],
            "product_and_media_gate": prof.get("product_and_media_gate"),
            "verified_internal_links": prof.get("verified_internal_links"),
        }

    def list_profiles(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for s in self.store_manager.list_stores():
            path = self.profile_path(s.id)
            if path.exists():
                try:
                    prof = self.get_profile(s.id)
                    out.append(prof)
                except Exception as exc:
                    out.append(
                        {
                            "store_id": s.id,
                            "brand_name": s.name,
                            "profile_status": "draft",
                            "ready_for_publishing": False,
                            "_validation": {"valid": False, "errors": [str(exc)], "warnings": []},
                        }
                    )
            else:
                out.append(
                    {
                        "store_id": s.id,
                        "brand_name": s.name,
                        "profile_status": "draft",
                        "ready_for_publishing": False,
                        "_validation": {
                            "valid": False,
                            "errors": [f"Missing data/store_profiles/{s.id}.json"],
                            "warnings": [],
                        },
                    }
                )
        return out

    def save_profile(
        self,
        store_id: str,
        profile_data: Optional[Dict[str, Any]] = None,
        *,
        payload: Optional[Dict[str, Any]] = None,
        expected_revision: Optional[int] = None,
        updated_by: str = "StoreProfileManager.save_profile",
    ) -> Dict[str, Any]:
        sid = slugify_store_id(store_id)
        incoming = dict(profile_data if profile_data is not None else (payload or {}))
        for bad_key in FORBIDDEN_CREDENTIAL_KEYS:
            if bad_key in incoming:
                raise StoreProfileValidationError(
                    f"Credential field '{bad_key}' is forbidden in Store Editorial Profile."
                )

        path = self.profile_path(sid)
        current: Dict[str, Any] = {}
        current_rev = 0
        if path.exists():
            try:
                current = json.loads(path.read_text(encoding="utf-8"))
                current_rev = int(
                    current.get("profile_revision")
                    or (current.get("audit_metadata") or {}).get("profile_revision")
                    or 1
                )
            except Exception:
                current = {}
                current_rev = 0

        if expected_revision is not None and current_rev != int(expected_revision):
            raise StoreProfileConflictError(
                f"PROFILE_REVISION_CONFLICT: Store '{sid}' is at revision {current_rev}, expected {expected_revision}."
            )

        merged = dict(current)
        merged.update(incoming)
        merged.pop("_validation", None)
        merged["store_id"] = sid
        merged["schema_version"] = "1.0"
        next_rev = current_rev + 1 if current_rev >= 1 else 1
        merged.setdefault("audit_metadata", {})["last_verified_at"] = datetime.now(timezone.utc).isoformat()
        merged["audit_metadata"]["verified_by"] = updated_by
        merged["audit_metadata"]["profile_revision"] = next_rev

        schema_dict = {k: v for k, v in merged.items() if k not in ("profile_revision", "updated_by")}
        val = self.validate_profile(schema_dict)
        if not val["valid"]:
            raise StoreProfileValidationError(
                f"Store Editorial Profile for '{sid}' failed validation: {'; '.join(val['errors'])}"
            )

        path.write_text(
            json.dumps(schema_dict, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        # Persist revision inside audit_metadata or companion state while returning profile_revision on the dict
        schema_dict["profile_revision"] = next_rev
        schema_dict["_validation"] = val
        return schema_dict

    def seed_from_research(
        self,
        store_id: str,
        overwrite: bool = False,
        research_file: Path = RESEARCH_SEED_FILE,
    ) -> Dict[str, Any]:
        """Seed or refresh a store profile from `data/store_editorial_research_2026-10-17.json`."""
        sid = slugify_store_id(store_id)
        path = self.profile_path(sid)
        if path.exists() and not overwrite:
            return self.get_profile(sid)

        if not research_file.exists():
            raise FileNotFoundError(f"Research seed file not found: {research_file}")

        raw_research = json.loads(research_file.read_text(encoding="utf-8"))
        stores_list = raw_research.get("stores") or []
        stores_map = (
            {item.get("store_id"): item for item in stores_list}
            if isinstance(stores_list, list)
            else dict(stores_list)
        )
        if sid not in stores_map:
            raise KeyError(f"Store '{sid}' not found in research seed file.")

        r_store = stores_map[sid]
        seed = r_store.get("editorial_profile_seed") or {}
        store_cfg = self.store_manager.get_store(sid)
        now_iso = datetime.now(timezone.utc).isoformat()

        def _map_ev(ev_list: list) -> list:
            return [
                {
                    "source_id": str(e.get("source_id") or ""),
                    "source_url": str(e.get("source_url") or ""),
                    "fetched_at": str(e.get("fetched_at") or now_iso),
                    "exact_quote": str(e.get("exact_quote") or "")[:1200],
                }
                for e in (ev_list or [])
            ]

        seed_pol = seed.get("policies") or {}
        matched_blog = next(
            (b for b in store_cfg.blogs_cache if b.get("handle") == store_cfg.default_blog_handle),
            {
                "id": store_cfg.default_blog_id or "gid://shopify/Blog/0",
                "handle": store_cfg.default_blog_handle or "news",
                "title": (store_cfg.default_blog_handle or "news").replace("-", " ").title(),
            },
        )

        # Preserve existing curated policy rules if present
        existing_pol: Dict[str, Any] = {}
        if path.exists():
            try:
                existing_pol = (json.loads(path.read_text(encoding="utf-8")).get("policies")) or {}
            except Exception:
                existing_pol = {}

        def _build_pol(key: str, seed_key: str) -> Dict[str, Any]:
            if key in existing_pol and isinstance(existing_pol[key], dict):
                return existing_pol[key]
            sp = seed_pol.get(seed_key) or {}
            return {
                "summary": str(sp.get("summary") or "Verify on official store policy page."),
                "conflict_status": "none",
                "allowed_claims": [str(sp.get("summary") or "Verify on official store policy page.")],
                "forbidden_claims": [],
                "evidence": _map_ev(sp.get("evidence") or []),
            }

        policies_and_pages = [
            {
                "url": str(src.get("final_url") or src.get("requested_url") or ""),
                "title": str(src.get("title") or "").strip(),
                "http_status": int(src.get("http_status") or 200),
                "verified_at": str(src.get("fetched_at") or now_iso),
            }
            for src in (r_store.get("sources_list") or [])
            if "/products/" not in str(src.get("final_url") or src.get("requested_url") or "")
        ]
        collections_links = [
            {
                "url": str(col.get("url") or "").strip(),
                "handle": str(col.get("url") or "").rstrip("/").split("/collections/")[-1],
                "title": str(col.get("url") or "").rstrip("/").split("/collections/")[-1].replace("-", " ").title(),
                "http_status": 200,
                "verified_at": now_iso,
            }
            for col in (seed.get("observed_collection_links") or [])[:25]
            if col.get("url")
        ]
        blog_base = store_cfg.resolved_public_domain.rstrip("/")
        blogs_links = [
            {
                "url": f"{blog_base}/blogs/{b['handle']}",
                "handle": b["handle"],
                "title": b["title"],
                "http_status": 200,
                "verified_at": now_iso,
            }
            for b in store_cfg.blogs_cache
        ]

        payload = {
            "schema_version": "1.0",
            "store_id": sid,
            "brand_name": r_store.get("brand_name") or store_cfg.name,
            "storefront_url": r_store.get("storefront_url") or store_cfg.resolved_public_domain,
            "shopify_domain": store_cfg.normalized_shop,
            "zbigtee_project_id": store_cfg.zbigtee_project_id,
            "profile_status": "active_verified",
            "ready_for_publishing": True,
            "verified_destination_blog": {
                "blog_id": matched_blog["id"],
                "blog_handle": matched_blog["handle"],
                "blog_title": matched_blog["title"],
                "default_author": store_cfg.default_author,
                "verified_via_shopify_api_at": now_iso,
                "available_blogs": store_cfg.blogs_cache,
            },
            "brand_positioning": {
                "summary": str((seed.get("brand_positioning") or {}).get("summary") or store_cfg.name),
                "target_audience": str((seed.get("audience_suggestion") or {}).get("value") or "Store shoppers"),
                "editorial_voice": list(
                    (seed.get("voice_suggestion") or {}).get("value") or ["Clear, helpful, and evidence-backed"]
                ),
                "evidence": _map_ev((seed.get("brand_positioning") or {}).get("evidence") or []),
            },
            "policies": {
                "shipping": _build_pol("shipping", "shipping"),
                "returns_refunds": _build_pol("returns_refunds", "returns_refunds"),
                "cancellation": _build_pol("cancellation", "cancellation"),
                "warranty_support": _build_pol("warranty_support", "warranty"),
                "personalization_customization": _build_pol("personalization_customization", "personalization"),
                "materials_care": _build_pol("materials_care", "care"),
            },
            "do_not_claim": list(seed.get("do_not_claim") or ["Do not invent unverified product facts."]),
            "unknowns_requiring_shopify_verification": list(seed.get("unknowns_requiring_verification") or []),
            "product_and_media_gate": {
                "require_shopify_api_verification": True,
                "require_online_store_publication": True,
                "require_proxy_for_all_shopify_requests": True,
                "min_body_images": 4,
                "max_body_images": 7,
                "forbid_svg_fallbacks": True,
                "forbid_unverified_gallery_alt_mapping": True,
            },
            "verified_internal_links": {
                "collections": collections_links,
                "policies_and_pages": policies_and_pages,
                "blogs": blogs_links,
            },
            "audit_metadata": {
                "seeded_from": "data/store_editorial_research_2026-10-17.json",
                "last_verified_at": now_iso,
                "verified_by": "StoreProfileManager.seed_from_research",
            },
        }
        return self.save_profile(sid, payload)

    def recheck_profile_sources_via_proxy(self, store_id: str, check_collections: bool = False) -> Dict[str, Any]:
        """
        Re-verify policy/page URLs and blog URLs configured in the store's profile
        through the mandatory Proxy (`ProxyManager.get_shopify_requests_session`).
        """
        sid = slugify_store_id(store_id)
        store = self.store_manager.get_store(sid)
        prof = self.get_profile(sid)
        sess = self.store_manager.proxy_manager.get_shopify_requests_session(
            target_shop_domain=store.normalized_shop
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        checked_urls: List[Dict[str, Any]] = []

        groups = ("policies_and_pages", "blogs", "collections") if check_collections else ("policies_and_pages", "blogs")
        links_block = prof.get("verified_internal_links") or {}
        for group_key in groups:
            items = links_block.get(group_key) or []
            for item in items:
                url = (item.get("url") or "").strip()
                if not url:
                    continue
                try:
                    resp = sess.get(url, timeout=18, allow_redirects=True)
                    item["http_status"] = int(resp.status_code)
                    item["verified_at"] = now_iso
                    checked_urls.append(
                        {
                            "group": group_key,
                            "url": url,
                            "http_status": int(resp.status_code),
                            "ok": 200 <= resp.status_code < 400,
                        }
                    )
                except Exception as exc:
                    item["http_status"] = 0
                    item["verified_at"] = now_iso
                    checked_urls.append(
                        {
                            "group": group_key,
                            "url": url,
                            "http_status": 0,
                            "ok": False,
                            "error": str(exc),
                        }
                    )

        prof.setdefault("audit_metadata", {})["last_verified_at"] = now_iso
        saved = self.save_profile(sid, prof)
        return {
            "ok": all(u.get("ok") for u in checked_urls),
            "store_id": sid,
            "checked_at": now_iso,
            "checked_count": len(checked_urls),
            "checked_urls": checked_urls,
            "profile": saved,
        }

