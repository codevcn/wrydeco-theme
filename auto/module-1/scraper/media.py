from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw, ImageOps

from .errors import ScraperError
from .events import EventCallback, emit
from .io_utils import atomic_write_bytes, atomic_write_json
from .shopify import ShopifyClient


BLOCKED_IMAGE_METADATA_TERMS = ("amazon", "wazaro", "preaureum")


def _assert_image_metadata_sanitized(content: bytes) -> None:
    """Fail closed if a newly encoded asset still exposes source text metadata."""
    with Image.open(io.BytesIO(content)) as image:
        fields: list[str] = []
        fields.extend(str(value) for value in image.getexif().values())
        fields.extend(str(value) for value in image.info.values() if isinstance(value, (str, bytes)))
    metadata_text = " ".join(fields).casefold()
    found = [term for term in BLOCKED_IMAGE_METADATA_TERMS if term in metadata_text]
    if found:
        raise ScraperError("Sanitized image still contains blocked metadata: " + ", ".join(found))


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
    # Re-encoding decoded pixels without carrying source EXIF/IPTC/XMP removes
    # marketplace and supplier metadata instead of maintaining a fragile list
    # of individual metadata keys.
    output.save(encoded, format="JPEG", quality=92, optimize=True, progressive=True, exif=b"")
    content = encoded.getvalue()
    _assert_image_metadata_sanitized(content)
    return content, "image/jpeg"


def prepare_gallery_evidence(
    urls: list[str], evidence_dir: Path, *, maximum: int = 8,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Persist sanitized, bounded gallery pixels for grounded Agent inspection."""
    gallery_dir = evidence_dir / "gallery"
    gallery_dir.mkdir(parents=True, exist_ok=True)
    client = session or requests.Session()
    images: list[dict[str, Any]] = []
    decoded: list[Image.Image] = []
    failures: list[dict[str, str]] = []
    for index, url in enumerate(urls[:maximum], 1):
        try:
            content, _ = prepare_image(url, Path("."), add_logo=False, session=client)
            with Image.open(io.BytesIO(content)) as source:
                normalized = ImageOps.exif_transpose(source).convert("RGB")
                normalized.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                encoded = io.BytesIO()
                normalized.save(encoded, format="JPEG", quality=88, optimize=True, progressive=True, exif=b"")
                saved = encoded.getvalue()
                _assert_image_metadata_sanitized(saved)
                filename = f"{index:03d}.jpg"
                atomic_write_bytes(gallery_dir / filename, saved)
                images.append({
                    "evidence_id": f"gallery/{filename}", "source_url": url,
                    "width": normalized.width, "height": normalized.height,
                    "sha256": hashlib.sha256(saved).hexdigest(),
                })
                decoded.append(normalized.copy())
        except Exception as exc:
            failures.append({"source_url": url, "error": str(exc)[:500]})
    if not decoded:
        raise ScraperError("No verified gallery image could be saved as visual evidence.")

    tile_width, tile_height = 420, 420
    columns = 2
    rows = (len(decoded) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * tile_width, rows * (tile_height + 28)), "white")
    draw = ImageDraw.Draw(sheet)
    for index, image in enumerate(decoded, 1):
        thumb = image.copy()
        thumb.thumbnail((tile_width - 20, tile_height - 20), Image.Resampling.LANCZOS)
        x = ((index - 1) % columns) * tile_width + (tile_width - thumb.width) // 2
        y_base = ((index - 1) // columns) * (tile_height + 28)
        y = y_base + (tile_height - thumb.height) // 2
        sheet.paste(thumb, (x, y))
        draw.text((x + 4, y_base + tile_height + 4), f"Gallery {index:03d}", fill="black")
    sheet_bytes = io.BytesIO()
    sheet.save(sheet_bytes, format="JPEG", quality=86, optimize=True, progressive=True, exif=b"")
    contact = sheet_bytes.getvalue()
    _assert_image_metadata_sanitized(contact)
    atomic_write_bytes(gallery_dir / "contact-sheet.jpg", contact)
    manifest = {
        "images": images,
        "contact_sheet": "gallery/contact-sheet.jpg",
        "failures": failures,
    }
    atomic_write_json(gallery_dir / "manifest.json", manifest)
    return manifest


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

