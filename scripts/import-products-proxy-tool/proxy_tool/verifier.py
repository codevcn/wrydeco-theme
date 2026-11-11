from __future__ import annotations

import ipaddress
import json
import socket
import time
from dataclasses import dataclass

import httpx

from .config import ProxyConfig
from .errors import VerificationError
from .system import (
    connection_key,
    snapshot_connections,
)


@dataclass
class VerificationResult:
    exit_ip: str
    country_code: str
    city: str | None
    direct_tcp_blocked: bool
    ipv6_blocked: bool
    udp_dns_blocked: bool
    process_egress_clean: bool

    def as_dict(self) -> dict:
        return {
            "exit_ip": self.exit_ip,
            "country_code": self.country_code,
            "city": self.city,
            "direct_tcp_blocked": self.direct_tcp_blocked,
            "ipv6_blocked": self.ipv6_blocked,
            "udp_dns_blocked": self.udp_dns_blocked,
            "process_egress_clean": self.process_egress_clean,
        }


def normalize_text(value: str | None) -> str:
    return " ".join((value or "").strip().casefold().split())


def direct_tcp_is_blocked() -> bool:
    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    )
    sock.settimeout(1.5)

    try:
        sock.connect(("1.1.1.1", 443))
        return False
    except OSError:
        return True
    finally:
        sock.close()


def direct_ipv6_is_blocked() -> bool:
    sock = socket.socket(
        socket.AF_INET6,
        socket.SOCK_STREAM,
    )
    sock.settimeout(1.5)

    try:
        sock.connect(
            ("2606:4700:4700::1111", 443, 0, 0)
        )
        return False
    except OSError:
        return True
    finally:
        sock.close()


def build_dns_query() -> bytes:
    transaction = b"\x4a\x7b"
    flags = b"\x01\x00"
    counts = (
        b"\x00\x01"
        b"\x00\x00"
        b"\x00\x00"
        b"\x00\x00"
    )

    question = (
        b"\x07example"
        b"\x03com"
        b"\x00"
        b"\x00\x01"
        b"\x00\x01"
    )

    return transaction + flags + counts + question


def udp_dns_is_blocked() -> bool:
    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM,
    )
    sock.settimeout(1.5)

    try:
        sock.sendto(
            build_dns_query(),
            ("8.8.8.8", 53),
        )

        try:
            sock.recvfrom(2048)
            return False
        except socket.timeout:
            return True

    except OSError:
        return True
    finally:
        sock.close()


def public_identity(
    local_proxy_url: str,
    timeout: float,
) -> tuple[str, str, str | None]:
    with httpx.Client(
        proxy=local_proxy_url,
        timeout=timeout,
        trust_env=False,
        follow_redirects=True,
    ) as client:

        ip_response = client.get(
            "https://api.ipify.org?format=json"
        )
        ip_response.raise_for_status()

        exit_ip = ip_response.json()["ip"]

        try:
            ipaddress.ip_address(exit_ip)
        except ValueError as exc:
            raise VerificationError(
                "Public IP provider returned an invalid address."
            ) from exc

        geo_errors = []

        for url, parser in [
            (
                "https://ipapi.co/json/",
                lambda data: (
                    data.get("country_code"),
                    data.get("city"),
                ),
            ),
            (
                "https://ipwho.is/",
                lambda data: (
                    data.get("country_code"),
                    data.get("city"),
                ),
            ),
        ]:
            try:
                response = client.get(url)
                response.raise_for_status()

                data = response.json()
                country, city = parser(data)

                if country:
                    return (
                        exit_ip,
                        str(country).upper(),
                        str(city) if city else None,
                    )

            except Exception as exc:
                geo_errors.append(type(exc).__name__)

        raise VerificationError(
            "No independent geolocation provider returned usable data."
        )


def validate_process_egress(
    baseline: list[dict],
    gate_pid: int,
    proxy_ips: list[str],
    proxy_port: int,
) -> tuple[bool, list[dict]]:
    baseline_keys = {
        connection_key(row)
        for row in baseline
    }

    current = snapshot_connections()

    violations = []

    for row in current:
        if str(row.get("State", "")).lower() != "established":
            continue

        key = connection_key(row)

        if key in baseline_keys:
            continue

        remote = str(row.get("RemoteAddress", ""))

        try:
            parsed = ipaddress.ip_address(remote)

            if parsed.is_loopback:
                continue

        except ValueError:
            continue

        pid = int(row.get("OwningProcess", 0) or 0)
        port = int(row.get("RemotePort", 0) or 0)

        if (
            pid == gate_pid
            and remote in proxy_ips
            and port == proxy_port
        ):
            continue

        violations.append(
            {
                "RemoteAddress": remote,
                "RemotePort": port,
                "OwningProcess": pid,
                "ProcessName": row.get("ProcessName"),
            }
        )

    return not violations, violations


def verify(
    proxy_config: ProxyConfig,
    local_proxy_url: str,
    baseline_connections: list[dict],
    gate_pid: int,
    proxy_ips: list[str],
    relax_city: bool = False,
) -> VerificationResult:

    exit_ip, country, city = public_identity(
        local_proxy_url,
        timeout=proxy_config.timeout_seconds,
    )

    if country.upper() != proxy_config.country_code.upper():
        raise VerificationError(
            "Proxy exit country mismatch: "
            f"expected {proxy_config.country_code}, "
            f"observed {country}."
        )

    if proxy_config.city and not relax_city:
        if normalize_text(city) != normalize_text(
            proxy_config.city
        ):
            raise VerificationError(
                "Proxy exit city mismatch: "
                f"expected {proxy_config.city!r}, "
                f"observed {city!r}. "
                "Use --relax-city only if the operator accepts "
                "geolocation-database city differences."
            )

    tcp_blocked = direct_tcp_is_blocked()
    ipv6_blocked = direct_ipv6_is_blocked()
    dns_blocked = udp_dns_is_blocked()

    if not tcp_blocked:
        raise VerificationError(
            "DIRECT TCP LEAK: 1.1.1.1:443 was reachable."
        )

    if not ipv6_blocked:
        raise VerificationError(
            "IPV6 LEAK: direct IPv6 Internet connection succeeded."
        )

    if not dns_blocked:
        raise VerificationError(
            "DNS LEAK: direct UDP DNS response was received."
        )

    clean, violations = validate_process_egress(
        baseline_connections,
        gate_pid=gate_pid,
        proxy_ips=proxy_ips,
        proxy_port=proxy_config.port,
    )

    if not clean:
        raise VerificationError(
            "Direct process egress was detected: "
            + json.dumps(
                violations,
                ensure_ascii=False,
            )
        )

    return VerificationResult(
        exit_ip=exit_ip,
        country_code=country,
        city=city,
        direct_tcp_blocked=tcp_blocked,
        ipv6_blocked=ipv6_blocked,
        udp_dns_blocked=dns_blocked,
        process_egress_clean=clean,
    )