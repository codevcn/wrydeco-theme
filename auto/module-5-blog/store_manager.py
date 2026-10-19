"""
Modular Multi-Store Configuration & Credentials Manager (`store_manager.py`).

Each store has its own isolated credentials configuration file in
`data/stores/<store_id>.json` and is indexed in `data/stores.json`.
Also links each store to its Store Editorial Profile (`data/store_profiles/<store_id>.json`).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from proxy_manager import ProxyManager, redact_sensitive_data

MODULE_DIR = Path(__file__).resolve().parent
DATA_DIR = MODULE_DIR / "data"
STORES_DIR = DATA_DIR / "stores"
REGISTRY_FILE = DATA_DIR / "stores.json"

_KNOWN_STORE_KEYS = {
    "id",
    "name",
    "zbigtee_project_id",
    "zbigtee_domain",
    "shopify_shop",
    "public_domain",
    "api_version",
    "client_id",
    "client_secret",
    "admin_token",
    "storefront_password",
    "default_blog_handle",
    "default_blog_id",
    "default_author",
    "blogs_cache",
    "notes",
    "config_file",
    "editorial_profile_file",
    "extra_fields",
    "normalized_shop",
    "is_configured",
    "resolved_public_domain",
    "client_secret_masked",
    "admin_token_masked",
}


def normalize_shop_domain(shop: str) -> str:
    """Normalize a Shopify shop handle or URL into `<handle>.myshopify.com`."""
    raw = (shop or "").strip().strip("'").strip('"')
    if not raw:
        return ""

    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.netloc or parsed.path).replace("/admin", "").strip("/")

    if host == "admin.shopify.com":
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] == "store":
            return f"{parts[1]}.myshopify.com"

    if host.endswith(".myshopify.com"):
        return host.lower()

    if "." in host:
        handle = host.split(".")[0]
        return f"{handle}.myshopify.com".lower()

    return f"{host}.myshopify.com".lower()


def slugify_store_id(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug or "store"


@dataclass
class StoreConfig:
    id: str
    name: str
    zbigtee_project_id: str = ""
    zbigtee_domain: str = ""
    shopify_shop: str = ""
    public_domain: str = ""
    api_version: str = "2026-07"
    client_id: str = ""
    client_secret: str = ""
    admin_token: str = ""
    storefront_password: str = ""
    default_blog_handle: str = "buying-guides"
    default_blog_id: str = ""
    default_author: str = "Editorial Team"
    blogs_cache: List[Dict[str, str]] = field(default_factory=list)
    notes: str = ""
    config_file: str = ""
    editorial_profile_file: str = ""
    extra_fields: Dict[str, Any] = field(default_factory=dict)

    @property
    def normalized_shop(self) -> str:
        return normalize_shop_domain(self.shopify_shop)

    @property
    def is_configured(self) -> bool:
        shop = self.normalized_shop
        has_token = bool(self.admin_token and len(self.admin_token.strip()) >= 20)
        has_oauth = bool(self.client_id.strip() and self.client_secret.strip())
        return bool(shop and (has_token or has_oauth))

    @property
    def graphql_endpoint(self) -> str:
        shop = self.normalized_shop
        if not shop:
            raise ValueError(f"Store '{self.name}' ({self.id}) has no shopify_shop configured.")
        version = (self.api_version or "2026-07").strip()
        return f"https://{shop}/admin/api/{version}/graphql.json"

    @property
    def resolved_public_domain(self) -> str:
        if self.public_domain and self.public_domain.strip():
            dom = self.public_domain.strip().rstrip("/")
            return dom if "://" in dom else f"https://{dom}"
        if self.normalized_shop:
            return f"https://{self.normalized_shop}"
        if self.zbigtee_domain:
            return f"https://{self.zbigtee_domain.strip().rstrip('/')}"
        return ""

    def to_dict(self, mask_secrets: bool = False) -> Dict[str, Any]:
        data = asdict(self)
        extra = data.pop("extra_fields", None) or {}
        for k, v in extra.items():
            if k not in data:
                data[k] = v
        data["normalized_shop"] = self.normalized_shop
        data["is_configured"] = self.is_configured
        data["resolved_public_domain"] = self.resolved_public_domain
        if not data.get("config_file"):
            data["config_file"] = f"stores/{self.id}.json"
        if not data.get("editorial_profile_file"):
            data["editorial_profile_file"] = f"store_profiles/{self.id}.json"
        if mask_secrets:
            if data.get("client_secret"):
                sec = data["client_secret"]
                data["client_secret_masked"] = f"{sec[:8]}...{sec[-4:]}" if len(sec) > 12 else "***"
                data["client_secret"] = ""
            else:
                data["client_secret_masked"] = ""
            if data.get("admin_token"):
                tok = data["admin_token"]
                data["admin_token_masked"] = f"{tok[:8]}...{tok[-4:]}" if len(tok) > 12 else "***"
                data["admin_token"] = ""
            else:
                data["admin_token_masked"] = ""
        return data

    def to_redacted_summary(self) -> Dict[str, Any]:
        """Return a strictly secret-free summary suitable for MCP responses and public reports."""
        return {
            "id": self.id,
            "name": self.name,
            "zbigtee_project_id": self.zbigtee_project_id,
            "zbigtee_domain": self.zbigtee_domain,
            "shopify_shop": self.shopify_shop,
            "normalized_shop": self.normalized_shop,
            "public_domain": self.public_domain,
            "resolved_public_domain": self.resolved_public_domain,
            "api_version": self.api_version,
            "is_configured": self.is_configured,
            "has_admin_token": bool(self.admin_token and len(self.admin_token.strip()) >= 20),
            "has_oauth_credentials": bool(self.client_id.strip() and self.client_secret.strip()),
            "default_blog_handle": self.default_blog_handle,
            "default_blog_id": self.default_blog_id,
            "default_author": self.default_author,
            "blogs_cache": list(self.blogs_cache or []),
            "notes": self.notes,
            "config_file": self.config_file or f"stores/{self.id}.json",
            "editorial_profile_file": self.editorial_profile_file or f"store_profiles/{self.id}.json",
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "StoreConfig":
        store_id = slugify_store_id(raw.get("id") or raw.get("name") or "store")
        extra_fields = dict(raw.get("extra_fields") or {})
        for k, v in raw.items():
            if k not in _KNOWN_STORE_KEYS:
                extra_fields[k] = v
        return cls(
            id=store_id,
            name=raw.get("name") or store_id.upper(),
            zbigtee_project_id=str(raw.get("zbigtee_project_id") or "").strip(),
            zbigtee_domain=str(raw.get("zbigtee_domain") or "").strip(),
            shopify_shop=str(raw.get("shopify_shop") or "").strip(),
            public_domain=str(raw.get("public_domain") or "").strip(),
            api_version=str(raw.get("api_version") or "2026-07").strip() or "2026-07",
            client_id=str(raw.get("client_id") or "").strip(),
            client_secret=str(raw.get("client_secret") or "").strip(),
            admin_token=str(raw.get("admin_token") or "").strip(),
            storefront_password=str(raw.get("storefront_password") or "").strip(),
            default_blog_handle=str(raw.get("default_blog_handle") or "buying-guides").strip() or "buying-guides",
            default_blog_id=str(raw.get("default_blog_id") or "").strip(),
            default_author=str(raw.get("default_author") or "Editorial Team").strip() or "Editorial Team",
            blogs_cache=list(raw.get("blogs_cache") or []),
            notes=str(raw.get("notes") or "").strip(),
            config_file=str(raw.get("config_file") or f"stores/{store_id}.json").strip(),
            editorial_profile_file=str(
                raw.get("editorial_profile_file") or f"store_profiles/{store_id}.json"
            ).strip(),
            extra_fields=extra_fields,
        )


class StoreManager:
    """Manages per-store credential files and master store registry."""

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.data_dir = data_dir
        self.stores_dir = self.data_dir / "stores"
        self.registry_file = self.data_dir / "stores.json"
        self.proxy_manager = ProxyManager(data_dir=self.data_dir, auto_bootstrap=False)
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.stores_dir.mkdir(parents=True, exist_ok=True)
        if not self.registry_file.exists():
            self._bootstrap_default_stores()

    def _bootstrap_default_stores(self) -> None:
        """Seed WRYDECO (from admin/.env if available) and DizzyCustom when initializing a fresh directory."""
        admin_env = MODULE_DIR.parent.parent / "admin" / ".env"
        env_map: Dict[str, str] = {}
        if admin_env.exists():
            for line in admin_env.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env_map[k.strip()] = v.strip().strip("'").strip('"')

        wrydeco = StoreConfig(
            id="wrydeco",
            name="WRYDECO",
            zbigtee_project_id="01a0d177-b16d-7976-975a-d0b8a7681b18",
            zbigtee_domain="wrydeco.com",
            shopify_shop=env_map.get("SHOPIFY_SHOP", "wrydeco.myshopify.com"),
            public_domain="https://wrydeco.myshopify.com",
            api_version=env_map.get("SHOPIFY_API_VERSION", "2026-07"),
            client_id=env_map.get("SHOPIFY_CLIENT_ID", ""),
            client_secret=env_map.get("SHOPIFY_CLIENT_SECRET", ""),
            admin_token=env_map.get("SHOPIFY_ADMIN_TOKEN", ""),
            storefront_password="123456",
            default_blog_handle="buying-guides",
            default_blog_id="gid://shopify/Blog/108369313849",
            default_author="WRYDECO Studio",
            blogs_cache=[
                {
                    "id": "gid://shopify/Blog/108369313849",
                    "handle": "buying-guides",
                    "title": "Buying Guides",
                }
            ],
            notes="Pre-seeded WRYDECO Shopify store configuration",
        )
        dizzy = StoreConfig(
            id="dizzycustom",
            name="DizzyCustom",
            zbigtee_project_id="01a0b243-525e-742c-b223-2c9ca25ce9aa",
            zbigtee_domain="dizzycustom.com",
            shopify_shop="",
            public_domain="https://dizzycustom.com",
            api_version="2026-07",
            default_blog_handle="news",
            default_author="DizzyCustom Editorial",
            notes="Synced from Zbigtee workspace (awaiting Shopify credentials in Settings)",
        )
        self._write_store_file(wrydeco)
        self._write_store_file(dizzy)
        self._save_registry_payload(
            {
                "active_store_id": "wrydeco",
                "zbigtee_workspace_id": "01a0b213-65a2-712a-b349-85b9bd8fa591",
                "stores": [wrydeco.to_dict(), dizzy.to_dict()],
            }
        )

    def _load_registry_payload(self) -> Dict[str, Any]:
        if not self.registry_file.exists():
            self._bootstrap_default_stores()
        try:
            return json.loads(self.registry_file.read_text(encoding="utf-8"))
        except Exception:
            self._bootstrap_default_stores()
            return json.loads(self.registry_file.read_text(encoding="utf-8"))

    def _save_registry_payload(self, payload: Dict[str, Any]) -> None:
        self.registry_file.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _write_store_file(self, store: StoreConfig) -> Path:
        target = self.stores_dir / f"{store.id}.json"
        store_dict = store.to_dict()
        target.write_text(
            json.dumps(store_dict, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return target

    def list_stores(self) -> List[StoreConfig]:
        payload = self._load_registry_payload()
        configs: List[StoreConfig] = []
        seen_ids = set()

        for item in payload.get("stores", []):
            sid = slugify_store_id(item.get("id") or item.get("name") or "")
            per_store_file = self.stores_dir / f"{sid}.json"
            if per_store_file.exists():
                try:
                    file_data = json.loads(per_store_file.read_text(encoding="utf-8"))
                    cfg = StoreConfig.from_dict(file_data)
                except Exception:
                    cfg = StoreConfig.from_dict(item)
            else:
                cfg = StoreConfig.from_dict(item)
                self._write_store_file(cfg)
            configs.append(cfg)
            seen_ids.add(cfg.id)

        # Also pick up any standalone JSON files dropped into data/stores/*.json
        for file_path in sorted(self.stores_dir.glob("*.json")):
            sid = file_path.stem.lower()
            if sid not in seen_ids:
                try:
                    cfg = StoreConfig.from_dict(json.loads(file_path.read_text(encoding="utf-8")))
                    configs.append(cfg)
                    seen_ids.add(cfg.id)
                except Exception:
                    pass

        return configs

    def get_active_store_id(self) -> str:
        payload = self._load_registry_payload()
        active_id = payload.get("active_store_id", "wrydeco")
        stores = self.list_stores()
        if any(s.id == active_id for s in stores):
            return active_id
        return stores[0].id if stores else "wrydeco"

    def set_active_store(self, store_id: str) -> StoreConfig:
        store = self.get_store(store_id)
        payload = self._load_registry_payload()
        payload["active_store_id"] = store.id
        self._save_registry_payload(payload)
        return store

    def get_store(self, store_id_or_path: Optional[str] = None) -> StoreConfig:
        """
        Retrieve a StoreConfig by ID (e.g. 'wrydeco') or by explicit JSON file path.
        If None is passed, returns the currently active store.
        """
        if not store_id_or_path:
            store_id_or_path = self.get_active_store_id()

        candidate_path = Path(store_id_or_path)
        if candidate_path.suffix.lower() == ".json" and candidate_path.exists():
            return StoreConfig.from_dict(json.loads(candidate_path.read_text(encoding="utf-8")))

        target_id = slugify_store_id(store_id_or_path)
        for store in self.list_stores():
            if store.id == target_id or store.zbigtee_project_id == store_id_or_path:
                return store

        raise KeyError(f"Store '{store_id_or_path}' not found in data/stores.json")

    def redacted_store_summary(self, store_id: Optional[str] = None) -> Dict[str, Any]:
        """Return a redacted store summary without any secrets or tokens."""
        store = self.get_store(store_id)
        return store.to_redacted_summary()

    def save_store(self, raw_data: Dict[str, Any], set_active: bool = False) -> StoreConfig:
        """Create or update a store configuration and sync both per-store file & registry."""
        store_id = slugify_store_id(
            raw_data.get("id") or raw_data.get("name") or raw_data.get("zbigtee_domain") or "store"
        )
        existing: Optional[StoreConfig] = None
        try:
            existing = self.get_store(store_id)
        except KeyError:
            existing = None

        merged = existing.to_dict() if existing else {}
        for k, v in raw_data.items():
            if v is not None:
                if k in ("client_secret", "admin_token") and isinstance(v, str) and ("..." in v or "***" in v):
                    continue
                merged[k] = v
        merged["id"] = store_id

        store = StoreConfig.from_dict(merged)
        self._write_store_file(store)

        payload = self._load_registry_payload()
        stores_list = self.list_stores()
        updated_list = []
        found = False
        for s in stores_list:
            if s.id == store.id:
                updated_list.append(store.to_dict())
                found = True
            else:
                updated_list.append(s.to_dict())
        if not found:
            updated_list.append(store.to_dict())

        payload["stores"] = updated_list
        if set_active:
            payload["active_store_id"] = store.id
        self._save_registry_payload(payload)
        return store

    def delete_store(self, store_id: str) -> bool:
        target_id = slugify_store_id(store_id)
        per_store_file = self.stores_dir / f"{target_id}.json"
        if per_store_file.exists():
            per_store_file.unlink()

        payload = self._load_registry_payload()
        before = len(payload.get("stores", []))
        payload["stores"] = [
            s for s in payload.get("stores", []) if slugify_store_id(s.get("id", "")) != target_id
        ]
        if payload.get("active_store_id") == target_id:
            remaining = payload["stores"]
            payload["active_store_id"] = remaining[0]["id"] if remaining else ""
        self._save_registry_payload(payload)
        return len(payload["stores"]) < before

    def get_valid_access_token(self, store_id: Optional[str] = None, force_refresh: bool = False) -> str:
        """
        Ensure the store has a valid Shopify Admin API token (`shpat_...`).
        Mandatory rule: All connections to Shopify MUST pass through the verified Proxy.
        """
        store = self.get_store(store_id)
        shop_domain = store.normalized_shop
        if not shop_domain:
            raise ValueError(f"Store '{store.name}' ({store.id}) is missing Shopify domain (*.myshopify.com).")

        sess = self.proxy_manager.get_shopify_requests_session(target_shop_domain=shop_domain)

        if store.admin_token and not force_refresh:
            try:
                url = f"https://{shop_domain}/admin/api/{store.api_version}/shop.json"
                resp = sess.get(
                    url,
                    headers={
                        "X-Shopify-Access-Token": store.admin_token,
                        "Accept": "application/json",
                    },
                    timeout=20,
                )
                if resp.ok:
                    return store.admin_token
            except requests.RequestException:
                pass

        if not store.client_id or not store.client_secret:
            if store.admin_token:
                return store.admin_token
            raise ValueError(
                f"Store '{store.name}' ({store.id}) requires either a valid Admin Token or Client ID + Client Secret."
            )

        oauth_url = f"https://{shop_domain}/admin/oauth/access_token"
        resp = sess.post(
            oauth_url,
            data={
                "grant_type": "client_credentials",
                "client_id": store.client_id,
                "client_secret": store.client_secret,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            timeout=25,
        )
        if not resp.ok:
            raise RuntimeError(
                f"OAuth token exchange failed for {shop_domain} (HTTP {resp.status_code}): {redact_sensitive_data(resp.text)}"
            )

        token_data = resp.json()
        new_token = (token_data.get("access_token") or "").strip()
        if not new_token:
            raise RuntimeError(f"OAuth response did not include access_token: {redact_sensitive_data(token_data)}")

        store.admin_token = new_token
        self.save_store(store.to_dict())
        return new_token

    def test_connection_and_fetch_blogs(self, store_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate OAuth / Admin Token connection for a store via mandatory Proxy, fetch shop metadata
        and all Shopify Blog categories (`blogs(first: 50)`), and update `blogs_cache`.
        """
        store = self.get_store(store_id)
        shop_domain = store.normalized_shop
        sess = self.proxy_manager.get_shopify_requests_session(target_shop_domain=shop_domain)
        token = self.get_valid_access_token(store.id, force_refresh=False)

        query = """
        query FetchShopAndBlogs {
          shop {
            id
            name
            myshopifyDomain
            primaryDomain {
              url
              host
            }
          }
          blogs(first: 50) {
            nodes {
              id
              handle
              title
            }
          }
        }
        """
        resp = sess.post(
            store.graphql_endpoint,
            json={"query": query},
            headers={
                "X-Shopify-Access-Token": token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=25,
        )
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("errors"):
            raise RuntimeError(f"GraphQL error on {shop_domain}: {payload['errors']}")

        data = payload.get("data") or {}
        shop_info = data.get("shop") or {}
        blogs = (data.get("blogs") or {}).get("nodes") or []

        store.blogs_cache = [
            {"id": b["id"], "handle": b["handle"], "title": b["title"]} for b in blogs
        ]
        if blogs:
            matched = next(
                (b for b in blogs if b["handle"] == store.default_blog_handle),
                blogs[0],
            )
            store.default_blog_handle = matched["handle"]
            store.default_blog_id = matched["id"]

        self.save_store(store.to_dict())
        proxy_cfg = self.proxy_manager.get_config(auto_bootstrap=False)
        return {
            "ok": True,
            "store_id": store.id,
            "shop_id": shop_info.get("id"),
            "shop_name": shop_info.get("name"),
            "myshopify_domain": shop_info.get("myshopifyDomain") or shop_domain,
            "primary_domain": (shop_info.get("primaryDomain") or {}).get("url"),
            "blogs": store.blogs_cache,
            "default_blog_handle": store.default_blog_handle,
            "default_blog_id": store.default_blog_id,
            "proxy_used": proxy_cfg.masked_summary,
            "proxy_exit_ip": (proxy_cfg.last_check or {}).get("exit_ip", proxy_cfg.host),
        }
