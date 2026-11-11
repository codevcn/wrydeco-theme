from __future__ import annotations

import argparse
import asyncio
import base64
import ipaddress
import json
import os
import ssl
import struct
from pathlib import Path
from urllib.parse import urlsplit

from .config import (
    DEFAULT_GATE_HOST,
    DEFAULT_GATE_PORT,
    ProxyConfig,
)
from .errors import ProxyError
from .system import atomic_json


MAX_HEADER = 64 * 1024


async def read_http_headers(
    reader: asyncio.StreamReader,
) -> bytes:
    try:
        data = await reader.readuntil(b"\r\n\r\n")
    except asyncio.LimitOverrunError as exc:
        raise ProxyError("HTTP proxy header exceeded limit.") from exc
    except asyncio.IncompleteReadError as exc:
        raise ProxyError("Incomplete proxy request.") from exc

    if len(data) > MAX_HEADER:
        raise ProxyError("HTTP proxy header exceeded limit.")

    return data


def basic_auth(config: ProxyConfig) -> str | None:
    if config.username is None:
        return None

    raw = f"{config.username}:{config.password or ''}".encode()
    return base64.b64encode(raw).decode("ascii")


async def read_proxy_response_headers(
    reader: asyncio.StreamReader,
) -> bytes:
    data = await read_http_headers(reader)

    first = data.split(b"\r\n", 1)[0].decode(
        "iso-8859-1",
        errors="replace",
    )

    parts = first.split()

    if len(parts) < 2:
        raise ProxyError("Invalid upstream proxy response.")

    try:
        status = int(parts[1])
    except ValueError as exc:
        raise ProxyError("Invalid upstream proxy status.") from exc

    if status != 200:
        raise ProxyError(
            f"Upstream proxy CONNECT failed with HTTP {status}."
        )

    return data


class UpstreamConnector:
    def __init__(
        self,
        config: ProxyConfig,
        pinned_ips: list[str],
    ):
        self.config = config
        self.pinned_ips = pinned_ips
        self._index = 0

    def next_ip(self) -> str:
        if not self.pinned_ips:
            raise ProxyError("No pinned upstream proxy IPv4 address.")

        value = self.pinned_ips[self._index % len(self.pinned_ips)]
        self._index += 1
        return value

    async def _connect_proxy(self):
        last_error = None

        for _ in range(len(self.pinned_ips)):
            ip = self.next_ip()

            try:
                if self.config.scheme == "https":
                    context = ssl.create_default_context()

                    return await asyncio.wait_for(
                        asyncio.open_connection(
                            host=ip,
                            port=self.config.port,
                            ssl=context,
                            server_hostname=self.config.host,
                        ),
                        timeout=self.config.timeout_seconds,
                    )

                return await asyncio.wait_for(
                    asyncio.open_connection(
                        host=ip,
                        port=self.config.port,
                    ),
                    timeout=self.config.timeout_seconds,
                )

            except Exception as exc:
                last_error = exc

        raise ProxyError(
            "Unable to connect to the pinned upstream proxy endpoint."
        ) from last_error

    async def open_tunnel(
        self,
        target_host: str,
        target_port: int,
    ):
        if self.config.scheme in {"http", "https"}:
            return await self._http_connect(
                target_host,
                target_port,
            )

        return await self._socks5_connect(
            target_host,
            target_port,
        )

    async def _http_connect(
        self,
        target_host: str,
        target_port: int,
    ):
        reader, writer = await self._connect_proxy()

        target = (
            f"[{target_host}]:{target_port}"
            if ":" in target_host
            else f"{target_host}:{target_port}"
        )

        lines = [
            f"CONNECT {target} HTTP/1.1",
            f"Host: {target}",
            "Proxy-Connection: Keep-Alive",
        ]

        auth = basic_auth(self.config)

        if auth:
            lines.append(f"Proxy-Authorization: Basic {auth}")

        payload = ("\r\n".join(lines) + "\r\n\r\n").encode(
            "iso-8859-1"
        )

        writer.write(payload)
        await writer.drain()

        try:
            await read_proxy_response_headers(reader)
        except Exception:
            writer.close()
            await writer.wait_closed()
            raise

        return reader, writer

    async def _socks5_connect(
        self,
        target_host: str,
        target_port: int,
    ):
        reader, writer = await self._connect_proxy()

        methods = [0x00]

        if self.config.username is not None:
            methods.append(0x02)

        writer.write(
            bytes([0x05, len(methods), *methods])
        )
        await writer.drain()

        response = await reader.readexactly(2)

        if response[0] != 0x05 or response[1] == 0xFF:
            raise ProxyError(
                "SOCKS5 upstream rejected authentication methods."
            )

        if response[1] == 0x02:
            username = (self.config.username or "").encode()
            password = (self.config.password or "").encode()

            if len(username) > 255 or len(password) > 255:
                raise ProxyError(
                    "SOCKS5 credentials exceed protocol limits."
                )

            writer.write(
                bytes([0x01, len(username)])
                + username
                + bytes([len(password)])
                + password
            )
            await writer.drain()

            auth_response = await reader.readexactly(2)

            if auth_response != b"\x01\x00":
                raise ProxyError(
                    "SOCKS5 username/password authentication failed."
                )

        try:
            parsed_ip = ipaddress.ip_address(target_host)

            if parsed_ip.version == 4:
                address = b"\x01" + parsed_ip.packed
            else:
                address = b"\x04" + parsed_ip.packed

        except ValueError:
            encoded = target_host.encode("idna")

            if len(encoded) > 255:
                raise ProxyError(
                    "SOCKS5 destination hostname is too long."
                )

            # ATYP DOMAIN => DNS resolution happens at upstream proxy.
            address = b"\x03" + bytes([len(encoded)]) + encoded

        writer.write(
            b"\x05\x01\x00"
            + address
            + struct.pack("!H", target_port)
        )
        await writer.drain()

        head = await reader.readexactly(4)

        if head[0] != 0x05 or head[1] != 0x00:
            raise ProxyError(
                f"SOCKS5 CONNECT failed with code {head[1]}."
            )

        atyp = head[3]

        if atyp == 0x01:
            await reader.readexactly(4)
        elif atyp == 0x04:
            await reader.readexactly(16)
        elif atyp == 0x03:
            size = (await reader.readexactly(1))[0]
            await reader.readexactly(size)
        else:
            raise ProxyError("Invalid SOCKS5 response address type.")

        await reader.readexactly(2)

        return reader, writer


def parse_connect_target(value: str) -> tuple[str, int]:
    value = value.strip()

    if value.startswith("["):
        closing = value.find("]")

        if closing < 0:
            raise ProxyError("Invalid IPv6 CONNECT target.")

        host = value[1:closing]
        port = int(value[closing + 2 :])
        return host, port

    host, separator, port_text = value.rpartition(":")

    if not separator:
        raise ProxyError("CONNECT target must include a port.")

    return host, int(port_text)


async def relay(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
):
    try:
        while True:
            data = await reader.read(65536)

            if not data:
                break

            writer.write(data)
            await writer.drain()

    except (
        ConnectionError,
        asyncio.CancelledError,
    ):
        pass


async def bridge(
    a_reader: asyncio.StreamReader,
    a_writer: asyncio.StreamWriter,
    b_reader: asyncio.StreamReader,
    b_writer: asyncio.StreamWriter,
):
    first = asyncio.create_task(relay(a_reader, b_writer))
    second = asyncio.create_task(relay(b_reader, a_writer))

    done, pending = await asyncio.wait(
        {first, second},
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()

    await asyncio.gather(
        *pending,
        return_exceptions=True,
    )

    for writer in (a_writer, b_writer):
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


def rewrite_plain_http_header(
    header: bytes,
) -> tuple[str, int, bytes]:
    text = header.decode("iso-8859-1")
    lines = text.split("\r\n")

    method, target, version = lines[0].split(" ", 2)
    parsed = urlsplit(target)

    if parsed.scheme.lower() != "http" or not parsed.hostname:
        raise ProxyError(
            "Plain HTTP proxy requests must use an absolute http:// URL."
        )

    host = parsed.hostname
    port = parsed.port or 80

    path = parsed.path or "/"

    if parsed.query:
        path += "?" + parsed.query

    output = [f"{method} {path} {version}"]

    for line in lines[1:]:
        lower = line.lower()

        if lower.startswith("proxy-authorization:"):
            continue

        if lower.startswith("proxy-connection:"):
            continue

        output.append(line)

    rewritten = "\r\n".join(output).encode("iso-8859-1")

    return host, port, rewritten


async def handle_client(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    connector: UpstreamConnector,
):
    try:
        header = await read_http_headers(client_reader)

        first_line = header.split(
            b"\r\n",
            1,
        )[0].decode("iso-8859-1")

        method, target, _version = first_line.split(" ", 2)

        if method.upper() == "CONNECT":
            host, port = parse_connect_target(target)

            upstream_reader, upstream_writer = (
                await connector.open_tunnel(host, port)
            )

            client_writer.write(
                b"HTTP/1.1 200 Connection Established\r\n"
                b"Proxy-Agent: WrydecoProxyGate/0.1\r\n"
                b"\r\n"
            )
            await client_writer.drain()

        else:
            host, port, rewritten = rewrite_plain_http_header(
                header
            )

            upstream_reader, upstream_writer = (
                await connector.open_tunnel(host, port)
            )

            upstream_writer.write(rewritten)
            await upstream_writer.drain()

        await bridge(
            client_reader,
            client_writer,
            upstream_reader,
            upstream_writer,
        )

    except Exception:
        try:
            client_writer.write(
                b"HTTP/1.1 502 Bad Gateway\r\n"
                b"Connection: close\r\n"
                b"Content-Length: 0\r\n\r\n"
            )
            await client_writer.drain()
        except Exception:
            pass

        try:
            client_writer.close()
            await client_writer.wait_closed()
        except Exception:
            pass


async def run(args):
    config = ProxyConfig.load()

    pinned_ips = [
        item.strip()
        for item in args.proxy_ips.split(",")
        if item.strip()
    ]

    connector = UpstreamConnector(
        config=config,
        pinned_ips=pinned_ips,
    )

    # Smoke-test the upstream before advertising readiness.
    reader, writer = await connector.open_tunnel(
        "api.ipify.org",
        443,
    )

    writer.close()
    await writer.wait_closed()

    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, connector),
        host=args.host,
        port=args.port,
        limit=128 * 1024,
    )

    atomic_json(
        Path(args.ready_file),
        {
            "pid": os.getpid(),
            "host": args.host,
            "port": args.port,
            "ready": True,
        },
    )

    async with server:
        await server.serve_forever()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--host",
        default=DEFAULT_GATE_HOST,
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_GATE_PORT,
    )
    parser.add_argument(
        "--proxy-ips",
        required=True,
    )
    parser.add_argument(
        "--ready-file",
        required=True,
    )

    args = parser.parse_args()

    asyncio.run(run(args))


if __name__ == "__main__":
    main()