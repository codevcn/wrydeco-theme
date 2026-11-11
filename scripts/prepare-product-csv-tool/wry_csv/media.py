from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import ipaddress
from pathlib import Path
import socket
from urllib.parse import urljoin, urlparse

from PIL import Image
import requests

from .common import Invalid, require, sha256

MAX_IMAGE = 20 * 1024 * 1024


def image_info(data: bytes) -> dict:
    require(0 < len(data) <= MAX_IMAGE, "Image must be nonempty and at most 20 MiB")
    try:
        with Image.open(BytesIO(data)) as picture:
            fmt = picture.format
            width, height = picture.size
            picture.verify()
        with Image.open(BytesIO(data)) as picture:
            picture.load()
        require(fmt in {"PNG", "JPEG", "WEBP", "GIF"}, "Supported images: PNG, JPEG, WEBP, GIF")
        require(width * height <= 25_000_000, "Image exceeds 25 megapixels")
        return {"sha256": sha256(data), "bytes": len(data), "width": width, "height": height,
                "mime": Image.MIME[fmt], "extension": {"JPEG": "jpg"}.get(fmt, fmt.lower())}
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise Invalid("Image cannot be fully decoded") from exc


def public_url(url: str) -> None:
    parts = urlparse(url)
    require(parts.scheme == "https" and parts.hostname and not parts.username and not parts.password
            and not parts.fragment and parts.port in {None, 443}, "Image URL must be public HTTPS without credentials")
    try:
        addresses = socket.getaddrinfo(parts.hostname, 443, type=socket.SOCK_STREAM)
        require(addresses and all(ipaddress.ip_address(item[4][0]).is_global for item in addresses),
                "Image URL resolves to a non-public address")
    except socket.gaierror as exc:
        raise Invalid("Image URL DNS lookup failed") from exc


def fetch_image(url: str) -> dict:
    # No Admin session, token, cookies or Authorization header is reused here.
    try:
        current = url
        with requests.Session() as session:
            for _ in range(5):
                public_url(current)
                with session.get(current, timeout=(10, 45), stream=True, allow_redirects=False) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        current = urljoin(current, response.headers.get("Location", ""))
                        continue
                    require(response.status_code == 200, f"Image GET returned HTTP {response.status_code}")
                    require(response.headers.get("Content-Type", "").lower().startswith("image/"),
                            "Image GET returned a non-image Content-Type")
                    chunks, size = [], 0
                    for chunk in response.iter_content(64 * 1024):
                        size += len(chunk)
                        require(size <= MAX_IMAGE, "Downloaded image exceeds 20 MiB")
                        chunks.append(chunk)
                    return {"url": url, "http_status": 200, **image_info(b"".join(chunks))}
        raise Invalid("Too many image redirects")
    except requests.RequestException as exc:
        raise Invalid("Public image GET failed (network/TLS/timeout)") from exc


def verify_urls(urls: list[str], fetcher=fetch_image) -> dict:
    unique = list(dict.fromkeys(urls))
    def check(url):
        try:
            return url, fetcher(url), None
        except Exception as exc:
            return url, None, str(exc)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(check, unique))
    return {"checked": len(unique), "results": [result for _, result, error in results if not error],
            "errors": [{"url": url, "error": error} for url, _, error in results if error]}


def inspect_local(path: Path) -> dict:
    require(path.is_file(), f"Missing gallery image: {path}")
    require(path.stat().st_size <= MAX_IMAGE, f"Gallery image is too large: {path.name}")
    return image_info(path.read_bytes())
