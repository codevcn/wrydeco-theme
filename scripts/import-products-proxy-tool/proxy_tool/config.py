from __future__ import annotations

import ipaddress
import os
import socket
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .errors import ConfigError

TOOL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]

PROXY_ENV = TOOL_ROOT / ".proxy.env"
ADMIN_ENV = REPO_ROOT / "admin" / ".env"

STATE_DIR = TOOL_ROOT / "state"
LOG_DIR = TOOL_ROOT / "logs"
REPORT_DIR = TOOL_ROOT / "reports"
VENDOR_WINDIVERT = TOOL_ROOT / "vendor" / "windivert"

DEFAULT_STORE = "wrydeco.myshopify.com"
DEFAULT_API_VERSION = "2026-10"
DEFAULT_GATE_HOST = "127.0.0.1"
DEFAULT_GATE_PORT = 18765


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise ConfigError(f"Required environment file not found: {path}")

    result: dict[str, str] = {}

    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()

        if not line or line.startswith("#"):
            continue

        if line.lower().startswith("export "):
            line = line[7:].lstrip()

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {"'", '"'}
        ):
            value = value[1:-1]

        result[key] = value

    return result


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default

    normalized = value.strip().lower()

    if normalized in {"1", "true", "yes", "on"}:
        return True

    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ConfigError(f"Invalid boolean value: {value!r}")


@dataclass(frozen=True)
class ProxyConfig:
    scheme: str
    host: str
    port: int
    username: str | None
    password: str | None
    timeout_seconds: float
    country_code: str
    city: str | None
    region: str | None
    isp: str | None

    @classmethod
    def load(cls) -> "ProxyConfig":
        env = load_env_file(PROXY_ENV)

        if not parse_bool(env.get("PROXY_ENABLED"), default=True):
            raise ConfigError("PROXY_ENABLED is false. Refusing to run.")

        scheme = (env.get("PROXY_SCHEME") or "").strip().lower()
        host = (env.get("PROXY_HOST") or "").strip()
        port_text = (env.get("PROXY_PORT") or "").strip()
        username = env.get("PROXY_USERNAME") or None
        password = env.get("PROXY_PASSWORD") or None

        if not (scheme and host and port_text):
            url = (
                env.get("HTTPS_PROXY")
                or env.get("https_proxy")
                or env.get("ALL_PROXY")
                or env.get("all_proxy")
                or env.get("HTTP_PROXY")
                or env.get("http_proxy")
            )

            if not url:
                raise ConfigError(
                    "Proxy host/scheme/port are incomplete and no proxy URL is available."
                )

            parsed = urlsplit(url)

            scheme = scheme or parsed.scheme.lower()
            host = host or (parsed.hostname or "")
            port_text = port_text or (
                str(parsed.port) if parsed.port is not None else ""
            )

            if username is None and parsed.username is not None:
                username = unquote(parsed.username)

            if password is None and parsed.password is not None:
                password = unquote(parsed.password)

        if scheme == "socks5h":
            scheme = "socks5"

        if scheme not in {"http", "https", "socks5"}:
            raise ConfigError(
                f"Unsupported PROXY_SCHEME {scheme!r}. "
                "Supported: http, https, socks5."
            )

        if not host:
            raise ConfigError("PROXY_HOST is empty.")

        try:
            port = int(port_text)
        except ValueError as exc:
            raise ConfigError("PROXY_PORT must be an integer.") from exc

        if not (1 <= port <= 65535):
            raise ConfigError("PROXY_PORT must be between 1 and 65535.")

        country = (env.get("PROXY_COUNTRY_CODE") or "").strip().upper()

        if len(country) != 2:
            raise ConfigError(
                "PROXY_COUNTRY_CODE must contain a two-letter country code."
            )

        try:
            timeout = float(env.get("PROXY_TIMEOUT_SECONDS") or "15")
        except ValueError as exc:
            raise ConfigError(
                "PROXY_TIMEOUT_SECONDS must be numeric."
            ) from exc

        return cls(
            scheme=scheme,
            host=host,
            port=port,
            username=username,
            password=password,
            timeout_seconds=max(2.0, timeout),
            country_code=country,
            city=(env.get("PROXY_CITY") or "").strip() or None,
            region=(env.get("PROXY_REGION") or "").strip() or None,
            isp=(env.get("PROXY_ISP") or "").strip() or None,
        )

    def secret_values(self) -> list[str]:
        values = []

        if self.username:
            values.append(self.username)

        if self.password:
            values.append(self.password)

        return values

    def resolve_ipv4(self) -> list[str]:
        try:
            ip = ipaddress.ip_address(self.host)
            if ip.version == 4:
                return [str(ip)]

            raise ConfigError(
                "v1 requires an IPv4 upstream proxy transport. "
                "The configured proxy host is IPv6-only."
            )
        except ValueError:
            pass

        try:
            answers = socket.getaddrinfo(
                self.host,
                self.port,
                family=socket.AF_INET,
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror as exc:
            raise ConfigError(
                "Unable to resolve upstream proxy hostname before lockdown."
            ) from exc

        addresses: list[str] = []

        for answer in answers:
            ip = answer[4][0]
            if ip not in addresses:
                addresses.append(ip)

        if not addresses:
            raise ConfigError(
                "Proxy hostname did not resolve to any IPv4 address. "
                "v1 intentionally requires an IPv4 upstream transport."
            )

        return addresses


@dataclass(frozen=True)
class ShopifyConfig:
    store: str
    token: str
    api_version: str = DEFAULT_API_VERSION

    @classmethod
    def load(cls) -> "ShopifyConfig":
        env = load_env_file(ADMIN_ENV)

        token_keys = [
            "SHOPIFY_ADMIN_TOKEN",
            "SHOPIFY_ADMIN_ACCESS_TOKEN",
            "SHOPIFY_ACCESS_TOKEN",
            "SHOPIFY_ADMIN_API_ACCESS_TOKEN",
            "SHOPIFY_API_ACCESS_TOKEN",
        ]

        token = next(
            (
                env[key].strip()
                for key in token_keys
                if env.get(key, "").strip()
            ),
            "",
        )

        if not token:
            raise ConfigError(
                "No Shopify Admin access token was found in admin/.env."
            )

        store = (
            env.get("SHOPIFY_STORE")
            or env.get("SHOPIFY_SHOP")
            or env.get("SHOPIFY_STORE_DOMAIN")
            or DEFAULT_STORE
        ).strip()

        store = store.removeprefix("https://").removeprefix("http://")
        store = store.rstrip("/")

        if store != DEFAULT_STORE:
            raise ConfigError(
                f"Configured Shopify store is {store!r}, "
                f"but this tool is locked to {DEFAULT_STORE!r}."
            )

        return cls(
            store=store,
            token=token,
        )

    def secret_values(self) -> list[str]:
        return [self.token]


def ensure_runtime_dirs() -> None:
    for path in (STATE_DIR, LOG_DIR, REPORT_DIR):
        path.mkdir(parents=True, exist_ok=True)