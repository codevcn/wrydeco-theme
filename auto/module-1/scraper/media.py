from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageOps

from .errors import ScraperError
from .events import EventCallback, emit
from .shopify import ShopifyClient


def prepare_image(url: str, logo_path: Path, *, add_logo: bool = True, logo_width: int = 140, margin: int = 5,
                  session: requests.Session | None = None) -> tuple[bytes, str]:
    client = session or requests.Session()
    response = client.get(url, timeout=60)
    if response.status_code >= 400:
        raise ScraperError(f"Image download failed with HTTP {response.status_code}: {url}")
    try:
        source = ImageOps.exif_transpose(Image.open(io.BytesIO(response.content))).convert("RGB")
        logo = Image.open(logo_path).convert("RGBA") if add_logo else None
    except Exception as exc:
        raise ScraperError(f"Could not decode source image or logo: {url}") from exc
    output = source
    if logo is not None:
        width = min(logo_width, max(40, source.width // 4))
        height = max(1, round(logo.height * width / logo.width))
        logo = logo.resize((width, height), Image.Resampling.LANCZOS)
        overlay = Image.new("RGBA", source.size, (0, 0, 0, 0))
        overlay.alpha_composite(logo, (max(0, source.width - width - margin), max(0, source.height - height - margin)))
        output = Image.alpha_composite(source.convert("RGBA"), overlay).convert("RGB")
    encoded = io.BytesIO()
    output.save(encoded, format="JPEG", quality=92, optimize=True, progressive=True, exif=b"")
    return encoded.getvalue(), "image/jpeg"


def rehost_images(client: ShopifyClient, urls: list[str], logo_path: Path, workspace: Path,
                  title: str, checkpoint: list[dict[str, str]] | None = None, *, prefix: str = "gallery",
                  add_logo: bool = True, event_callback: EventCallback | None = None,
                  asin: str = "") -> list[dict[str, str]]:
    uploaded = list(checkpoint or [])
    completed = {item["source"] for item in uploaded}
    for index, url in enumerate(urls, 1):
        if url in completed:
            emit(event_callback, "media_progress", asin=asin, kind=prefix, current=index,
                 total=len(urls), cached=True)
            continue
        content, mime = prepare_image(url, logo_path, add_logo=add_logo)
        digest = hashlib.sha256(content).hexdigest()[:12]
        filename = f"{workspace.name}-{prefix}-{index:03d}-{digest}.jpg"
        item = client.stage_image(content, filename, mime, title)
        uploaded.append({"source": url, "id": item["id"], "url": item["url"], "alt": title})
        from .io_utils import atomic_write_json
        atomic_write_json(workspace / f"uploaded_{prefix}.json", uploaded)
        emit(event_callback, "media_progress", asin=asin, kind=prefix, current=index,
             total=len(urls), cached=False)
    return uploaded

