"""
Mandatory Shopify Proxy Manager & Stability Gate (`proxy_manager.py`).

Enforces the strict rule:
  - Every HTTP/GraphQL (`requests`) and Storefront Browser (`Playwright`) session between
    this tool and Shopify MUST be routed through the configured proxy (`data/proxy.json`).
  - Default credentials can be explicitly seeded via `reset_to_default_docs()` from
    `docs/proxy-credentials.md` into `data/proxy.json`, but normal runtime/campaign reads
    (`get_config(auto_bootstrap=False)`) fail-closed if `data/proxy.json` is missing or invalid.
  - If the proxy is unconfigured, unreachable, or unstable, ALL connections between the
    tool and Shopify are immediately blocked (`ProxyBlockedError`) with zero direct fallback.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote

import requests

MODULE_DIR = Path(__file__).resolve().parent
DATA_DIR = MODULE_DIR / "data"
DOCS_DIR = MODULE_DIR / "docs"
PROXY_CONFIG_FILE = DATA_DIR / "proxy.json"
DEFAULT_PROXY_DOC = DOCS_DIR / "proxy-credentials.md"

_SECRET_KEYS = {
    "password",
    "client_secret",
    "admin_token",
    "session_token",
    "cookie_header",
    "raw_cookie_header",
    "access_token",
    "x-shopify-access-token",
}

_SECRET_VALUE_PATTERNS = [
    re.compile(r"shpat_[A-Za-z0-9_]{10,}"),
    re.compile(r"shpss_[A-Za-z0-9_]{10,}"),
    re.compile(r"__Secure-better-auth\.session_token=[^;\s\"']+"),
]


def redact_sensitive_data(value: Any) -> Any:
    """Recursively redact secrets, tokens, passwords, and cookies from dicts/lists/strings."""
    if isinstance(value, dict):
        cleaned: Dict[str, Any] = {}
        for k, v in value.items():
            key_lower = str(k).strip().lower()
            if key_lower in _SECRET_KEYS:
                if isinstance(v, str) and v.strip():
                    cleaned[k] = "***REDACTED***"
                else:
                    cleaned[k] = ""
            else:
                cleaned[k] = redact_sensitive_data(v)
        return cleaned
    if isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]
    if isinstance(value, str):
        out = value
        for pat in _SECRET_VALUE_PATTERNS:
            out = pat.sub("***REDACTED***", out)
        # Also mask http://user:pass@host:port URLs if present
        out = re.sub(
            r"(https?://[^:/\s]+:)([^@/\s]+)(@)",
            r"\1***REDACTED***\3",
            out,
        )
        return out
    return value


class ProxyBlockedError(RuntimeError):
    """Raised when any Shopify connection is attempted while the proxy is unconfigured or unstable."""


@dataclass
class ProxyConfig:
    scheme: str = "http"
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""
    enabled: bool = True
    last_check: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_configured(self) -> bool:
        return bool(self.host.strip() and int(self.port or 0) > 0)

    @property
    def server_url(self) -> str:
        clean_scheme = (self.scheme or "http").strip().lower()
        return f"{clean_scheme}://{self.host.strip()}:{int(self.port)}"

    @property
    def formatted_proxy_url(self) -> str:
        clean_scheme = (self.scheme or "http").strip().lower()
        host = self.host.strip()
        port = int(self.port or 0)
        user = self.username.strip()
        pwd = self.password.strip()
        if user and pwd:
            return f"{clean_scheme}://{quote(user, safe='')}:{quote(pwd, safe='')}@{host}:{port}"
        return f"{clean_scheme}://{host}:{port}"

    @property
    def config_fingerprint(self) -> str:
        if not self.is_configured:
            return "unconfigured"
        raw = f"{self.scheme.strip().lower()}://{self.username.strip()}@{self.host.strip().lower()}:{int(self.port or 0)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    @property
    def masked_summary(self) -> str:
        if not self.is_configured:
            return "Unconfigured"
        user_part = f"{self.username[:4]}***@" if self.username else ""
        return f"{self.scheme}://{user_part}{self.host}:{self.port}"

    def to_dict(self, mask_secrets: bool = False) -> Dict[str, Any]:
        data = asdict(self)
        data["is_configured"] = self.is_configured
        data["server_url"] = self.server_url if self.is_configured else ""
        data["masked_summary"] = self.masked_summary
        data["config_fingerprint"] = self.config_fingerprint
        data["config_file"] = "data/proxy.json"
        if mask_secrets and data.get("password"):
            pwd = data["password"]
            data["password_masked"] = f"{pwd[:3]}...{pwd[-3:]}" if len(pwd) > 6 else "***"
            data["password"] = ""
        else:
            data["password_masked"] = ""
        return data

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "ProxyConfig":
        port_raw = raw.get("port") or 0
        try:
            port_val = int(str(port_raw).strip())
        except ValueError:
            port_val = 0
        return cls(
            scheme=(raw.get("scheme") or "http").strip().lower() or "http",
            host=(raw.get("host") or raw.get("ip") or "").strip(),
            port=port_val,
            username=(raw.get("username") or "").strip(),
            password=(raw.get("password") or "").strip(),
            enabled=True,  # Mandatory rule: proxy is always required for Shopify
            last_check=dict(raw.get("last_check") or {}),
        )


class ProxyManager:
    """Manages proxy credentials, proactive stability testing, and mandatory Shopify session wrapping."""

    # In-memory cache of the most recent verified stability check to avoid redundant probes
    # within the same multi-step pipeline run (TTL = 45 seconds).
    _last_verified_ts: float = 0.0
    _last_verified_key: str = ""
    _last_verified_ok: bool = False
    _VERIFIED_TTL_SECONDS: float = 45.0

    def __init__(
        self,
        data_dir: Path = DATA_DIR,
        proxy_doc_path: Path = DEFAULT_PROXY_DOC,
        auto_bootstrap: bool = False,
    ) -> None:
        self.data_dir = data_dir
        self.proxy_file = self.data_dir / "proxy.json"
        self.proxy_doc_path = proxy_doc_path
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if auto_bootstrap and not self.proxy_file.exists():
            self._bootstrap_from_docs()

    @classmethod
    def invalidate_Verification_cache(cls) -> None:
        cls._last_verified_ts = 0.0
        cls._last_verified_key = ""
        cls._last_verified_ok = False

    def _parse_docs_credentials(self) -> Dict[str, Any]:
        """Parse default proxy credentials from `docs/proxy-credentials.md`."""
        result: Dict[str, Any] = {
            "scheme": "http",
            "host": "185.124.63.174",
            "port": 55031,
            "username": "",
            "password": "",
            "enabled": True,
        }
        if not self.proxy_doc_path.exists():
            return result

        for line in self.proxy_doc_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            clean = line.strip()
            if not clean or ":" not in clean:
                continue
            k, v = clean.split(":", 1)
            key = k.strip().lower()
            val = v.strip().strip("'").strip('"')
            if key in ("ip", "host"):
                result["host"] = val
            elif key == "port":
                try:
                    result["port"] = int(val)
                except ValueError:
                    pass
            elif key in ("username", "user"):
                result["username"] = val
            elif key in ("password", "pass"):
                result["password"] = val
            elif key in ("scheme", "protocol", "type"):
                result["scheme"] = val.lower()
        return result

    def _bootstrap_from_docs(self) -> ProxyConfig:
        raw = self._parse_docs_credentials()
        cfg = ProxyConfig.from_dict(raw)
        self._write_config(cfg)
        return cfg

    def _write_config(self, cfg: ProxyConfig) -> None:
        payload = asdict(cfg)
        payload["is_configured"] = cfg.is_configured
        payload["server_url"] = cfg.server_url if cfg.is_configured else ""
        payload["masked_summary"] = cfg.masked_summary
        payload["config_fingerprint"] = cfg.config_fingerprint
        payload["config_file"] = "data/proxy.json"
        self.proxy_file.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def get_config(self, auto_bootstrap: bool = False) -> ProxyConfig:
        """
        Read `data/proxy.json`.
        By default (`auto_bootstrap=False`), fails closed by returning an unconfigured `ProxyConfig`
        if `data/proxy.json` is missing, unreadable, or incomplete—never silently falling back to docs.
        """
        if not self.proxy_file.exists():
            if auto_bootstrap:
                return self._bootstrap_from_docs()
            return ProxyConfig(enabled=True)
        try:
            raw = json.loads(self.proxy_file.read_text(encoding="utf-8"))
            cfg = ProxyConfig.from_dict(raw)
            if not cfg.is_configured and auto_bootstrap:
                cfg = self._bootstrap_from_docs()
            return cfg
        except Exception:
            if auto_bootstrap:
                return self._bootstrap_from_docs()
            return ProxyConfig(enabled=True)

    def save_config(self, raw_data: Dict[str, Any]) -> ProxyConfig:
        existing = asdict(self.get_config(auto_bootstrap=False))
        for k in ("scheme", "host", "ip", "port", "username", "password"):
            if k in raw_data and raw_data[k] is not None:
                val = raw_data[k]
                if k == "password" and isinstance(val, str) and ("..." in val or "***" in val):
                    continue
                if k == "ip":
                    existing["host"] = str(val).strip()
                else:
                    existing[k] = val
        existing["enabled"] = True
        cfg = ProxyConfig.from_dict(existing)
        self._write_config(cfg)
        self.invalidate_Verification_cache()
        return cfg

    def reset_to_default_docs(self) -> ProxyConfig:
        self.invalidate_Verification_cache()
        return self._bootstrap_from_docs()

    def get_redacted_report(self, report: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Return a sanitized proxy status summary safe for MCP, logs, and reports."""
        cfg = self.get_config(auto_bootstrap=False)
        src = report if isinstance(report, dict) else (cfg.last_check or {})
        return {
            "ok": bool(src.get("ok", False)),
            "stable": bool(src.get("stable", False)),
            "scheme": cfg.scheme,
            "host": cfg.host,
            "port": cfg.port,
            "masked_summary": cfg.masked_summary,
            "config_fingerprint": cfg.config_fingerprint,
            "exit_ip": str(src.get("exit_ip") or ""),
            "ip_matches_host": bool(src.get("ip_matches_host", False)),
            "avg_latency_ms": int(src.get("avg_latency_ms") or 0),
            "probes_total": int(src.get("probes_total") or 0),
            "probes_passed": int(src.get("probes_passed") or 0),
            "shopify_status_code": int(src.get("shopify_status_code") or 0),
            "checked_at": str(src.get("checked_at") or ""),
            "error": redact_sensitive_data(str(src.get("error") or "")),
        }

    def build_raw_requests_session(self, cfg: Optional[ProxyConfig] = None) -> requests.Session:
        """
        Create a `requests.Session` strictly bound to `cfg.formatted_proxy_url`
        with `trust_env = False` so OS environment variables can never bypass it.
        """
        proxy_cfg = cfg or self.get_config(auto_bootstrap=False)
        if not proxy_cfg.is_configured:
            raise ProxyBlockedError(
                "Chặn kết nối Shopify: Proxy chưa được cấu hình (thiếu IP/Host hoặc Port trong data/proxy.json)."
            )
        sess = requests.Session()
        sess.trust_env = False
        proxy_url = proxy_cfg.formatted_proxy_url
        sess.proxies = {
            "http": proxy_url,
            "https": proxy_url,
        }
        sess.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                )
            }
        )
        return sess

    def check_stability(
        self,
        target_shop_domain: str = "wrydeco.myshopify.com",
        probes: int = 2,
        timeout: int = 12,
        override_config: Optional[Dict[str, Any]] = None,
        persist_last_check: bool = True,
    ) -> Dict[str, Any]:
        """
        Actively verify proxy stability:
          1. Checks exit IP via `https://api.ipify.org?format=json` (fallback `https://ipv4.icanhazip.com`).
          2. Runs `probes` consecutive HTTPS requests through the proxy to Shopify (`https://<shop>/password`
             or `https://cdn.shopify.com`) to measure latency, jitter, and 100% packet delivery.
          3. Marks the proxy as STABLE only if exit IP is confirmed AND all Shopify probes succeed
             with average latency <= 8000 ms.
        """
        cfg = ProxyConfig.from_dict(override_config) if override_config else self.get_config(auto_bootstrap=False)
        checked_at = datetime.now(timezone.utc).isoformat()

        if not cfg.is_configured:
            report = {
                "ok": False,
                "stable": False,
                "checked_at": checked_at,
                "host": cfg.host,
                "port": cfg.port,
                "masked_summary": cfg.masked_summary,
                "config_fingerprint": cfg.config_fingerprint,
                "exit_ip": "",
                "ip_matches_host": False,
                "probes_total": probes,
                "probes_passed": 0,
                "avg_latency_ms": 0,
                "latencies_ms": [],
                "shopify_status_code": 0,
                "error": "Proxy thiếu thông tin IP/Host hoặc Port trong data/proxy.json.",
            }
            if persist_last_check and not override_config and self.proxy_file.exists():
                cfg.last_check = report
                self._write_config(cfg)
            self.invalidate_Verification_cache()
            return report

        sess = self.build_raw_requests_session(cfg)
        exit_ip = ""
        ip_error = ""

        # Step 1: Verify Exit IP through proxy
        ip_endpoints = [
            "https://api.ipify.org?format=json",
            "https://ipv4.icanhazip.com",
        ]
        for ep in ip_endpoints:
            try:
                r_ip = sess.get(ep, timeout=timeout)
                if r_ip.status_code == 200:
                    if "json" in ep:
                        exit_ip = (r_ip.json().get("ip") or "").strip()
                    else:
                        exit_ip = r_ip.text.strip()
                    if exit_ip:
                        break
                elif r_ip.status_code == 407:
                    ip_error = "Proxy Authentication Required (HTTP 407) — Sai username hoặc password của Proxy."
                    break
            except Exception as exc:
                ip_error = redact_sensitive_data(str(exc))

        if not exit_ip:
            report = {
                "ok": False,
                "stable": False,
                "checked_at": checked_at,
                "host": cfg.host,
                "port": cfg.port,
                "masked_summary": cfg.masked_summary,
                "config_fingerprint": cfg.config_fingerprint,
                "exit_ip": "",
                "ip_matches_host": False,
                "probes_total": probes,
                "probes_passed": 0,
                "avg_latency_ms": 0,
                "latencies_ms": [],
                "shopify_status_code": 0,
                "error": f"Không thể kết nối qua Proxy ({cfg.host}:{cfg.port}): {ip_error or 'Connection failed'}",
            }
            if persist_last_check and not override_config and self.proxy_file.exists():
                cfg.last_check = report
                self._write_config(cfg)
            self.invalidate_Verification_cache()
            return report

        # Step 2: Run consecutive stability probes to Shopify
        clean_shop = (target_shop_domain or "wrydeco.myshopify.com").strip()
        if not clean_shop.endswith(".myshopify.com") and "." not in clean_shop:
            clean_shop = f"{clean_shop}.myshopify.com"
        shopify_probe_url = f"https://{clean_shop}/password"

        latencies: list[int] = []
        passed_probes = 0
        last_status = 0
        probe_error = ""

        for _ in range(max(1, probes)):
            t0 = time.perf_counter()
            try:
                resp = sess.get(shopify_probe_url, timeout=timeout, allow_redirects=False)
                if resp.status_code in (502, 503, 504):
                    time.sleep(0.5)
                    t0 = time.perf_counter()
                    resp = sess.get(shopify_probe_url, timeout=timeout, allow_redirects=False)
                elapsed_ms = int(round((time.perf_counter() - t0) * 1000))
                last_status = resp.status_code
                if 200 <= resp.status_code < 500 and resp.status_code != 407:
                    passed_probes += 1
                    latencies.append(elapsed_ms)
                else:
                    probe_error = f"Shopify probe trả về HTTP {resp.status_code}"
            except Exception as exc:
                probe_error = redact_sensitive_data(str(exc))

        avg_latency = int(round(sum(latencies) / len(latencies))) if latencies else 0
        is_stable = (
            bool(exit_ip)
            and passed_probes == max(1, probes)
            and avg_latency <= 15000
        )

        error_msg = ""
        if not is_stable:
            error_msg = (
                probe_error
                or f"Proxy không ổn định ({passed_probes}/{probes} probes thành công, độ trễ TB {avg_latency}ms)."
            )

        report = {
            "ok": is_stable,
            "stable": is_stable,
            "checked_at": checked_at,
            "host": cfg.host,
            "port": cfg.port,
            "scheme": cfg.scheme,
            "masked_summary": cfg.masked_summary,
            "config_fingerprint": cfg.config_fingerprint,
            "exit_ip": exit_ip,
            "ip_matches_host": (exit_ip == cfg.host),
            "target_shopify_url": shopify_probe_url,
            "probes_total": max(1, probes),
            "probes_passed": passed_probes,
            "avg_latency_ms": avg_latency,
            "latencies_ms": latencies,
            "shopify_status_code": last_status,
            "error": error_msg,
        }

        if not override_config:
            if persist_last_check and self.proxy_file.exists():
                cfg.last_check = report
                self._write_config(cfg)
            if is_stable:
                ProxyManager._last_verified_ts = time.monotonic()
                ProxyManager._last_verified_key = cfg.formatted_proxy_url
                ProxyManager._last_verified_ok = True
            else:
                self.invalidate_Verification_cache()

        return report

    def ensure_shopify_proxy_ready(
        self,
        target_shop_domain: str = "wrydeco.myshopify.com",
        force_check: bool = False,
    ) -> ProxyConfig:
        """
        Mandatory Gate called before EVERY Shopify communication (`requests` or `Playwright`).
        Raises `ProxyBlockedError` if the proxy is unconfigured or fails the stability check.
        Never falls back to `docs/proxy-credentials.md` when `data/proxy.json` is missing/invalid.
        """
        cfg = self.get_config(auto_bootstrap=False)
        if not cfg.is_configured:
            raise ProxyBlockedError(
                "Chặn kết nối Shopify: Chưa cấu hình Proxy hợp lệ trong data/proxy.json (bắt buộc mọi phiên giao tiếp với Shopify phải đi qua Proxy)."
            )

        now = time.monotonic()
        cache_valid = (
            not force_check
            and ProxyManager._last_verified_ok
            and ProxyManager._last_verified_key == cfg.formatted_proxy_url
            and (now - ProxyManager._last_verified_ts) < ProxyManager._VERIFIED_TTL_SECONDS
        )
        if cache_valid:
            return cfg

        report = self.check_stability(
            target_shop_domain=target_shop_domain,
            probes=1,
            timeout=12,
            persist_last_check=False,
        )
        if not report.get("stable"):
            raise ProxyBlockedError(
                f"Chặn kết nối tới Shopify vì Proxy ({cfg.host}:{cfg.port}) không ổn định: {report.get('error') or 'Kiểm tra độ ổn định thất bại'}"
            )
        return cfg

    def get_shopify_requests_session(
        self,
        target_shop_domain: str = "wrydeco.myshopify.com",
        force_check: bool = False,
    ) -> requests.Session:
        """
        Verify proxy stability first, then return a `requests.Session` bound to the proxy.
        Blocks immediately with `ProxyBlockedError` if the proxy is unstable.
        """
        cfg = self.ensure_shopify_proxy_ready(
            target_shop_domain=target_shop_domain,
            force_check=force_check,
        )
        return self.build_raw_requests_session(cfg)

    def get_playwright_proxy(
        self,
        target_shop_domain: str = "wrydeco.myshopify.com",
        force_check: bool = False,
    ) -> Dict[str, str]:
        """
        Verify proxy stability first, then return Playwright's `proxy` dictionary
        (`{"server": "...", "username": "...", "password": "..."}`).
        Blocks immediately with `ProxyBlockedError` if the proxy is unstable.
        """
        cfg = self.ensure_shopify_proxy_ready(
            target_shop_domain=target_shop_domain,
            force_check=force_check,
        )
        pw_proxy: Dict[str, str] = {"server": cfg.server_url}
        if cfg.username:
            pw_proxy["username"] = cfg.username
        if cfg.password:
            pw_proxy["password"] = cfg.password
        return pw_proxy
