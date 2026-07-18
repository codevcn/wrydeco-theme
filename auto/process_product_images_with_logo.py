"""
Download crawled product-gallery images, add a local logo, upload the
watermarked images to Shopify Content > Files, then replace each
assets.product_media_gallery.images[*].source_url in the crawl JSON.

Expected project layout (defaults):

    .env
    configs/config.json
    data/**/*.json
    process_product_images_with_logo.py

Minimal configs/config.json example:

    {
      "logo_add": {
        "local_file_path": "assets/logo.png",
        "size": {"width": 220, "height": 90},
        "position": "bottom-right",
        "margin": 24
      },
      "shopify": {
        "store_domain": "your-store.myshopify.com"
      }
    }

Required .env value:

    STORE_ADMIN_ACCESS_TOKEN=shpat_...

The store domain is also required because an Admin API access token alone does
not identify the store. It can be supplied through one of these .env keys:

    SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
    STORE_DOMAIN=your-store.myshopify.com
    SHOP_DOMAIN=your-store.myshopify.com

Alternatively, put it in config.json under shopify.store_domain,
store.domain, or store_domain.

Dependencies:

    pip install Pillow requests

Usage:

    python process_product_images_with_logo.py
    python process_product_images_with_logo.py --json data/B0H6FGXKZ7.json
    python process_product_images_with_logo.py --force
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import logging
import mimetypes
import os
import re
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, Sequence
from urllib.parse import urlparse

import requests
from PIL import Image, ImageOps, UnidentifiedImageError


LOGGER = logging.getLogger("product-image-logo-uploader")
DEFAULT_API_VERSION = "2026-07"
DEFAULT_POSITION = "bottom-right"
DEFAULT_MARGIN = 24
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_SHOPIFY_READY_TIMEOUT_SECONDS = 180


class AppError(RuntimeError):
    """Raised for a user-actionable processing error."""


@dataclass(frozen=True)
class LogoSettings:
    path: Path
    width: int | None
    height: int | None
    position: str | Mapping[str, int]
    margin_x: int
    margin_y: int


@dataclass(frozen=True)
class ShopifySettings:
    store_domain: str
    access_token: str
    api_version: str
    ready_timeout_seconds: int


@dataclass(frozen=True)
class EncodedImage:
    content: bytes
    filename: str
    mime_type: str
    width: int
    height: int


class ShopifyClient:
    STAGED_UPLOADS_MUTATION = """
    mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
      stagedUploadsCreate(input: $input) {
        stagedTargets {
          url
          resourceUrl
          parameters { name value }
        }
        userErrors { field message }
      }
    }
    """

    FILE_CREATE_MUTATION = """
    mutation fileCreate($files: [FileCreateInput!]!) {
      fileCreate(files: $files) {
        files {
          id
          fileStatus
          alt
          ... on MediaImage {
            image { url width height }
          }
        }
        userErrors { field message code }
      }
    }
    """

    FILE_STATUS_QUERY = """
    query fileStatus($id: ID!) {
      node(id: $id) {
        ... on MediaImage {
          id
          fileStatus
          alt
          image { url width height }
        }
      }
    }
    """

    def __init__(self, settings: ShopifySettings, session: requests.Session) -> None:
        self.settings = settings
        self.session = session
        self.endpoint = (
            f"https://{settings.store_domain}/admin/api/"
            f"{settings.api_version}/graphql.json"
        )

    def graphql(self, query: str, variables: Mapping[str, Any]) -> dict[str, Any]:
        response = self.session.post(
            self.endpoint,
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": self.settings.access_token,
            },
            json={"query": query, "variables": variables},
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        try:
            payload = response.json()
        except ValueError as exc:
            raise AppError(
                f"Shopify returned a non-JSON response: {response.text[:500]}"
            ) from exc

        if payload.get("errors"):
            raise AppError(
                "Shopify GraphQL error: "
                + json.dumps(payload["errors"], ensure_ascii=False)
            )

        data = payload.get("data")
        if not isinstance(data, dict):
            raise AppError("Shopify GraphQL response does not contain a data object.")
        return data

    def upload_image(self, image: EncodedImage, alt_text: str | None) -> str:
        """Upload one image to Shopify Files and return its final CDN URL."""
        staged_data = self.graphql(
            self.STAGED_UPLOADS_MUTATION,
            {
                "input": [
                    {
                        "filename": image.filename,
                        "mimeType": image.mime_type,
                        "httpMethod": "POST",
                        "resource": "IMAGE",
                    }
                ]
            },
        )["stagedUploadsCreate"]

        staged_errors = staged_data.get("userErrors") or []
        if staged_errors:
            raise AppError(
                "stagedUploadsCreate failed: "
                + json.dumps(staged_errors, ensure_ascii=False)
            )

        targets = staged_data.get("stagedTargets") or []
        if len(targets) != 1:
            raise AppError(
                f"Expected one staged upload target, received {len(targets)}."
            )

        target = targets[0]
        upload_url = target.get("url")
        resource_url = target.get("resourceUrl")
        if not upload_url or not resource_url:
            raise AppError("Shopify staged upload target is missing url/resourceUrl.")

        form_fields = {
            item["name"]: item["value"]
            for item in (target.get("parameters") or [])
            if item.get("name") is not None
        }

        upload_response = self.session.post(
            upload_url,
            data=form_fields,
            files={"file": (image.filename, image.content, image.mime_type)},
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
        if upload_response.status_code not in {200, 201, 204}:
            raise AppError(
                "Staged binary upload failed with HTTP "
                f"{upload_response.status_code}: {upload_response.text[:500]}"
            )

        file_create_data = self.graphql(
            self.FILE_CREATE_MUTATION,
            {
                "files": [
                    {
                        "alt": alt_text or image.filename,
                        "contentType": "IMAGE",
                        "originalSource": resource_url,
                        "filename": image.filename,
                    }
                ]
            },
        )["fileCreate"]

        create_errors = file_create_data.get("userErrors") or []
        if create_errors:
            raise AppError(
                "fileCreate failed: "
                + json.dumps(create_errors, ensure_ascii=False)
            )

        created_files = file_create_data.get("files") or []
        if len(created_files) != 1 or not created_files[0].get("id"):
            raise AppError("Shopify did not return the created image file ID.")

        created = created_files[0]
        file_id = created["id"]
        initial_url = ((created.get("image") or {}).get("url"))
        if created.get("fileStatus") == "READY" and initial_url:
            return initial_url

        return self._wait_until_ready(file_id)

    def _wait_until_ready(self, file_id: str) -> str:
        deadline = time.monotonic() + self.settings.ready_timeout_seconds
        sleep_seconds = 1.5
        last_status: str | None = None

        while time.monotonic() < deadline:
            data = self.graphql(self.FILE_STATUS_QUERY, {"id": file_id})
            node = data.get("node")
            if not isinstance(node, dict):
                raise AppError(f"Shopify file node disappeared: {file_id}")

            last_status = node.get("fileStatus")
            image_url = ((node.get("image") or {}).get("url"))
            if last_status == "READY" and image_url:
                return image_url
            if last_status == "FAILED":
                raise AppError(f"Shopify failed to process uploaded file {file_id}.")

            time.sleep(sleep_seconds)
            sleep_seconds = min(sleep_seconds * 1.35, 6.0)

        raise AppError(
            "Timed out waiting for Shopify to process file "
            f"{file_id}; last status={last_status!r}."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Add a logo to crawled product-gallery images, upload them to "
            "Shopify Files, and update their source_url values."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/config.json"),
        help="Config JSON path (default: configs/config.json).",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help=".env path (default: .env).",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Folder containing crawl JSON files (default: data).",
    )
    parser.add_argument(
        "--json",
        type=Path,
        action="append",
        dest="json_files",
        help=(
            "Process a specific crawl JSON file. Repeat for multiple files. "
            "Without this option, every JSON file under data/ is processed."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Process source_url values that already point to Shopify CDN.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create a timestamped backup before changing a JSON file.",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep generated local watermarked images in .watermarked/.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO).",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as exc:
        raise AppError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AppError(f"Invalid JSON in {path}: {exc}") from exc


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")
    with temporary_path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())
    os.replace(temporary_path, path)


def create_backup(path: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = path.with_name(f"{path.stem}.backup-{timestamp}{path.suffix}")
    shutil.copy2(path, backup_path)
    return backup_path


def load_env_file(path: Path) -> dict[str, str]:
    """Load a small, standard KEY=VALUE .env file without another dependency."""
    if not path.exists():
        raise AppError(f".env file not found: {path}")

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            LOGGER.debug("Ignoring .env line %d without '='.", line_number)
            continue

        key, raw_value = line.split("=", 1)
        key = key.strip()
        value = raw_value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def first_nonempty(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def nested_get(data: Mapping[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def normalize_store_domain(value: str) -> str:
    candidate = value.strip()
    if "://" not in candidate:
        candidate = "https://" + candidate
    parsed = urlparse(candidate)
    domain = (parsed.netloc or parsed.path).strip().strip("/").lower()
    if not domain:
        raise AppError(f"Invalid Shopify store domain: {value!r}")
    return domain


def resolve_path(raw_path: str, config_path: Path) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path

    candidates = [Path.cwd() / path, config_path.parent / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def parse_positive_int(value: Any, label: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise AppError(f"{label} must be an integer; received {value!r}.") from exc
    if result <= 0:
        raise AppError(f"{label} must be greater than zero; received {result}.")
    return result


def parse_nonnegative_int(value: Any, label: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise AppError(f"{label} must be an integer; received {value!r}.") from exc
    if result < 0:
        raise AppError(f"{label} cannot be negative; received {result}.")
    return result


def parse_logo_size(value: Any) -> tuple[int | None, int | None]:
    width: Any = None
    height: Any = None

    if isinstance(value, Mapping):
        width = value.get("width")
        height = value.get("height")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        if len(value) != 2:
            raise AppError("logo_add.size list must contain exactly [width, height].")
        width, height = value
    elif isinstance(value, str):
        match = re.fullmatch(r"\s*(\d+)\s*[xX,]\s*(\d+)\s*", value)
        if match:
            width, height = match.groups()
        elif value.strip().isdigit():
            width = height = value.strip()
        else:
            raise AppError(
                "logo_add.size string must look like '220x90' or be an integer."
            )
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        width = height = value
    else:
        raise AppError(
            "logo_add.size must be an object, [width, height], 'WIDTHxHEIGHT', "
            "or a positive integer."
        )

    parsed_width = parse_positive_int(width, "logo_add.size.width") if width else None
    parsed_height = (
        parse_positive_int(height, "logo_add.size.height") if height else None
    )
    if parsed_width is None and parsed_height is None:
        raise AppError("logo_add.size must provide width, height, or both.")
    return parsed_width, parsed_height


def parse_margin(value: Any) -> tuple[int, int]:
    if value is None:
        return DEFAULT_MARGIN, DEFAULT_MARGIN
    if isinstance(value, Mapping):
        x = parse_nonnegative_int(value.get("x", DEFAULT_MARGIN), "logo_add.margin.x")
        y = parse_nonnegative_int(value.get("y", DEFAULT_MARGIN), "logo_add.margin.y")
        return x, y
    margin = parse_nonnegative_int(value, "logo_add.margin")
    return margin, margin


def load_settings(
    config_path: Path, env_path: Path
) -> tuple[LogoSettings, ShopifySettings]:
    config = load_json(config_path)
    if not isinstance(config, Mapping):
        raise AppError(f"Config root must be a JSON object: {config_path}")

    logo_config = config.get("logo_add")
    if not isinstance(logo_config, Mapping):
        raise AppError("configs/config.json must contain a logo_add object.")

    raw_logo_path = logo_config.get("local_file_path")
    if not isinstance(raw_logo_path, str) or not raw_logo_path.strip():
        raise AppError("logo_add.local_file_path is required.")
    logo_path = resolve_path(raw_logo_path, config_path)
    if not logo_path.is_file():
        raise AppError(f"Logo image not found: {logo_path}")

    width, height = parse_logo_size(logo_config.get("size"))
    raw_position = logo_config.get("position", DEFAULT_POSITION)
    if not isinstance(raw_position, (str, Mapping)):
        raise AppError("logo_add.position must be a string or an {x, y} object.")
    margin_x, margin_y = parse_margin(logo_config.get("margin"))

    env_values = load_env_file(env_path)
    access_token = first_nonempty(
        os.environ.get("STORE_ADMIN_ACCESS_TOKEN"),
        env_values.get("STORE_ADMIN_ACCESS_TOKEN"),
    )
    if not access_token:
        raise AppError(
            "STORE_ADMIN_ACCESS_TOKEN is missing from the environment/.env file."
        )

    store_domain = first_nonempty(
        os.environ.get("SHOPIFY_STORE_DOMAIN"),
        os.environ.get("STORE_DOMAIN"),
        os.environ.get("SHOP_DOMAIN"),
        env_values.get("SHOPIFY_STORE_DOMAIN"),
        env_values.get("STORE_DOMAIN"),
        env_values.get("SHOP_DOMAIN"),
        nested_get(config, "shopify", "store_domain"),
        nested_get(config, "store", "domain"),
        config.get("store_domain"),
    )
    if not store_domain:
        raise AppError(
            "A Shopify store domain is required. Add SHOPIFY_STORE_DOMAIN="
            "your-store.myshopify.com to .env, or set shopify.store_domain "
            "in configs/config.json."
        )

    api_version = first_nonempty(
        os.environ.get("SHOPIFY_API_VERSION"),
        env_values.get("SHOPIFY_API_VERSION"),
        nested_get(config, "shopify", "api_version"),
        DEFAULT_API_VERSION,
    )
    ready_timeout_raw = first_nonempty(
        os.environ.get("SHOPIFY_FILE_READY_TIMEOUT_SECONDS"),
        env_values.get("SHOPIFY_FILE_READY_TIMEOUT_SECONDS"),
    )
    ready_timeout = (
        parse_positive_int(
            ready_timeout_raw, "SHOPIFY_FILE_READY_TIMEOUT_SECONDS"
        )
        if ready_timeout_raw
        else DEFAULT_SHOPIFY_READY_TIMEOUT_SECONDS
    )

    return (
        LogoSettings(
            path=logo_path,
            width=width,
            height=height,
            position=raw_position,
            margin_x=margin_x,
            margin_y=margin_y,
        ),
        ShopifySettings(
            store_domain=normalize_store_domain(store_domain),
            access_token=access_token,
            api_version=api_version or DEFAULT_API_VERSION,
            ready_timeout_seconds=ready_timeout,
        ),
    )


def discover_json_files(data_dir: Path, explicit: Sequence[Path] | None) -> list[Path]:
    if explicit:
        files = [path.resolve() for path in explicit]
    else:
        if not data_dir.is_dir():
            raise AppError(f"Data directory not found: {data_dir}")
        files = sorted(
            path.resolve()
            for path in data_dir.rglob("*.json")
            if "debug" not in {part.lower() for part in path.parts}
            and ".backup-" not in path.name
            and not path.name.startswith(".")
        )

    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise AppError("JSON file(s) not found: " + ", ".join(missing))
    if not files:
        raise AppError("No crawl JSON files were found to process.")
    return files


def get_gallery_images(payload: MutableMapping[str, Any]) -> list[MutableMapping[str, Any]]:
    try:
        images = payload["assets"]["product_media_gallery"]["images"]
    except (KeyError, TypeError) as exc:
        raise AppError(
            "JSON is missing assets.product_media_gallery.images."
        ) from exc

    if not isinstance(images, list):
        raise AppError("assets.product_media_gallery.images must be an array.")

    valid_images: list[MutableMapping[str, Any]] = []
    for index, image in enumerate(images, start=1):
        if not isinstance(image, MutableMapping):
            LOGGER.warning("Skipping gallery item %d because it is not an object.", index)
            continue
        valid_images.append(image)
    return valid_images


def is_shopify_cdn_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host == "cdn.shopify.com" or host.endswith(".cdn.shopify.com")


def create_http_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/150.0.0.0 Safari/537.36"
            ),
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,"
            "image/*,*/*;q=0.8",
        }
    )
    return session


def download_image(session: requests.Session, url: str) -> tuple[bytes, str | None]:
    response = session.get(url, timeout=DEFAULT_TIMEOUT_SECONDS)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip()
    if content_type and not content_type.startswith("image/"):
        raise AppError(
            f"URL returned {content_type!r}, not an image: {url}"
        )
    if not response.content:
        raise AppError(f"Downloaded image is empty: {url}")
    return response.content, content_type or None


def resize_logo(logo: Image.Image, width: int | None, height: int | None) -> Image.Image:
    original_width, original_height = logo.size
    if width is None:
        assert height is not None
        width = max(1, round(original_width * (height / original_height)))
    elif height is None:
        height = max(1, round(original_height * (width / original_width)))
    return logo.resize((width, height), Image.Resampling.LANCZOS)


def calculate_position(
    canvas_size: tuple[int, int],
    logo_size: tuple[int, int],
    position: str | Mapping[str, int],
    margin_x: int,
    margin_y: int,
) -> tuple[int, int]:
    canvas_width, canvas_height = canvas_size
    logo_width, logo_height = logo_size

    if isinstance(position, Mapping):
        try:
            x = int(position.get("x", 0))
            y = int(position.get("y", 0))
        except (TypeError, ValueError) as exc:
            raise AppError("Custom logo_add.position x/y must be integers.") from exc
    else:
        normalized = position.strip().lower().replace("_", "-").replace(" ", "-")
        aliases = {
            "top": "top-center",
            "left": "center-left",
            "right": "center-right",
            "bottom": "bottom-center",
            "middle": "center",
            "middle-center": "center",
        }
        normalized = aliases.get(normalized, normalized)
        allowed = {
            "top-left",
            "top-center",
            "top-right",
            "center-left",
            "center",
            "center-right",
            "bottom-left",
            "bottom-center",
            "bottom-right",
        }
        if normalized not in allowed:
            raise AppError(
                "Unsupported logo_add.position. Use top-left, top-center, "
                "top-right, center-left, center, center-right, bottom-left, "
                "bottom-center, bottom-right, or {x, y}."
            )

        vertical, horizontal = (
            ("center", "center")
            if normalized == "center"
            else normalized.split("-", 1)
        )

        if horizontal == "left":
            x = margin_x
        elif horizontal == "right":
            x = canvas_width - logo_width - margin_x
        else:
            x = (canvas_width - logo_width) // 2

        if vertical == "top":
            y = margin_y
        elif vertical == "bottom":
            y = canvas_height - logo_height - margin_y
        else:
            y = (canvas_height - logo_height) // 2

    max_x = max(0, canvas_width - logo_width)
    max_y = max(0, canvas_height - logo_height)
    return max(0, min(x, max_x)), max(0, min(y, max_y))


def extension_for_format(image_format: str | None, source_url: str) -> str:
    normalized = (image_format or "").upper()
    mapping = {
        "JPEG": ".jpg",
        "JPG": ".jpg",
        "PNG": ".png",
        "WEBP": ".webp",
        "TIFF": ".tif",
    }
    if normalized in mapping:
        return mapping[normalized]

    suffix = Path(urlparse(source_url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    return ".png"


def mime_for_extension(extension: str) -> str:
    if extension == ".jpg":
        return "image/jpeg"
    if extension == ".png":
        return "image/png"
    if extension == ".webp":
        return "image/webp"
    if extension in {".tif", ".tiff"}:
        return "image/tiff"
    return mimetypes.guess_type("image" + extension)[0] or "image/png"


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return cleaned or "product"


def add_logo_to_image(
    product_bytes: bytes,
    source_url: str,
    logo_original: Image.Image,
    settings: LogoSettings,
    filename_prefix: str,
    image_index: int,
) -> EncodedImage:
    try:
        with Image.open(BytesIO(product_bytes)) as opened:
            image_format = opened.format
            product = ImageOps.exif_transpose(opened).convert("RGBA")
            source_info = copy.deepcopy(opened.info)
            source_exif = opened.getexif()
    except (UnidentifiedImageError, OSError) as exc:
        raise AppError(f"Pillow cannot decode product image: {source_url}") from exc

    logo = resize_logo(
        logo_original.copy().convert("RGBA"), settings.width, settings.height
    )

    available_width = max(1, product.width - (settings.margin_x * 2))
    available_height = max(1, product.height - (settings.margin_y * 2))
    if logo.width > available_width or logo.height > available_height:
        scale = min(available_width / logo.width, available_height / logo.height)
        if scale <= 0:
            raise AppError(
                f"Configured logo cannot fit product image {product.width}x{product.height}."
            )
        resized_to = (
            max(1, round(logo.width * scale)),
            max(1, round(logo.height * scale)),
        )
        LOGGER.warning(
            "Logo is larger than available canvas; scaling it down to %sx%s.",
            *resized_to,
        )
        logo = logo.resize(resized_to, Image.Resampling.LANCZOS)

    x, y = calculate_position(
        product.size,
        logo.size,
        settings.position,
        settings.margin_x,
        settings.margin_y,
    )
    product.alpha_composite(logo, dest=(x, y))

    extension = extension_for_format(image_format, source_url)
    # Shopify's image pipeline works best with common web image formats.
    if extension in {".tif", ".tiff"}:
        extension = ".png"

    output = BytesIO()
    save_kwargs: dict[str, Any] = {}
    icc_profile = source_info.get("icc_profile")
    if icc_profile:
        save_kwargs["icc_profile"] = icc_profile

    if extension == ".jpg":
        output_image = product.convert("RGB")
        save_kwargs.update(quality=100, subsampling=0, optimize=True)
        if source_exif:
            try:
                source_exif[274] = 1  # EXIF orientation is already applied.
                save_kwargs["exif"] = source_exif.tobytes()
            except Exception:  # noqa: BLE001 - EXIF must never break the upload.
                LOGGER.debug("Could not preserve EXIF metadata.", exc_info=True)
        output_image.save(output, format="JPEG", **save_kwargs)
    elif extension == ".webp":
        product.save(output, format="WEBP", lossless=True, method=6, **save_kwargs)
    else:
        extension = ".png"
        product.save(output, format="PNG", compress_level=6, **save_kwargs)

    digest = hashlib.sha256(output.getvalue()).hexdigest()[:12]
    filename = (
        f"{safe_filename(filename_prefix)}-gallery-{image_index:03d}-"
        f"logo-{digest}{extension}"
    )
    return EncodedImage(
        content=output.getvalue(),
        filename=filename,
        mime_type=mime_for_extension(extension),
        width=product.width,
        height=product.height,
    )


def process_json_file(
    json_path: Path,
    logo_original: Image.Image,
    logo_settings: LogoSettings,
    shopify: ShopifyClient,
    session: requests.Session,
    force: bool,
    make_backup: bool,
    keep_temp: bool,
) -> tuple[int, int, int]:
    payload = load_json(json_path)
    if not isinstance(payload, MutableMapping):
        raise AppError(f"JSON root must be an object: {json_path}")

    images = get_gallery_images(payload)
    if make_backup:
        backup_path = create_backup(json_path)
        LOGGER.info("Backup created: %s", backup_path)

    identifier = first_nonempty(payload.get("asin"), json_path.stem) or json_path.stem
    temp_output_dir = json_path.parent / ".watermarked"
    if keep_temp:
        temp_output_dir.mkdir(parents=True, exist_ok=True)

    processed = 0
    skipped = 0
    failed = 0

    for fallback_index, image_entry in enumerate(images, start=1):
        display_index = image_entry.get("index") or fallback_index
        source_url = image_entry.get("source_url")
        if not isinstance(source_url, str) or not source_url.strip():
            failed += 1
            LOGGER.error(
                "%s image %s: source_url is missing or invalid.",
                json_path.name,
                display_index,
            )
            continue
        source_url = source_url.strip()

        if is_shopify_cdn_url(source_url) and not force:
            skipped += 1
            LOGGER.info(
                "%s image %s: already points to Shopify CDN; skipped.",
                json_path.name,
                display_index,
            )
            continue

        LOGGER.info(
            "%s image %s: downloading %s",
            json_path.name,
            display_index,
            source_url,
        )

        try:
            product_bytes, _ = download_image(session, source_url)
            encoded = add_logo_to_image(
                product_bytes=product_bytes,
                source_url=source_url,
                logo_original=logo_original,
                settings=logo_settings,
                filename_prefix=identifier,
                image_index=fallback_index,
            )

            if keep_temp:
                local_path = temp_output_dir / encoded.filename
                local_path.write_bytes(encoded.content)
                LOGGER.info("Watermarked local copy: %s", local_path)

            alt_text = image_entry.get("alt_text")
            if not isinstance(alt_text, str):
                alt_text = None

            shopify_url = shopify.upload_image(encoded, alt_text)
            image_entry["source_url"] = shopify_url
            atomic_write_json(json_path, payload)
            processed += 1
            LOGGER.info(
                "%s image %s: uploaded and source_url updated: %s",
                json_path.name,
                display_index,
                shopify_url,
            )
        except (requests.RequestException, AppError, OSError) as exc:
            failed += 1
            LOGGER.error(
                "%s image %s failed: %s",
                json_path.name,
                display_index,
                exc,
            )

    # Ensure formatting is normalized even when every item was skipped.
    atomic_write_json(json_path, payload)
    return processed, skipped, failed


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        logo_settings, shopify_settings = load_settings(
            args.config.resolve(), args.env_file.resolve()
        )
        json_files = discover_json_files(args.data_dir.resolve(), args.json_files)

        with Image.open(logo_settings.path) as logo_file:
            logo_original = logo_file.convert("RGBA").copy()

        session = create_http_session()
        shopify = ShopifyClient(shopify_settings, session)

        LOGGER.info("Logo: %s", logo_settings.path)
        LOGGER.info(
            "Logo size: width=%s height=%s; position=%s; margin=%sx%s",
            logo_settings.width,
            logo_settings.height,
            logo_settings.position,
            logo_settings.margin_x,
            logo_settings.margin_y,
        )
        LOGGER.info("Shopify store: %s", shopify_settings.store_domain)
        LOGGER.info("JSON files to process: %d", len(json_files))

        total_processed = 0
        total_skipped = 0
        total_failed = 0

        for json_path in json_files:
            LOGGER.info("Processing JSON: %s", json_path)
            try:
                processed, skipped, failed = process_json_file(
                    json_path=json_path,
                    logo_original=logo_original,
                    logo_settings=logo_settings,
                    shopify=shopify,
                    session=session,
                    force=args.force,
                    make_backup=not args.no_backup,
                    keep_temp=args.keep_temp,
                )
            except AppError as exc:
                LOGGER.error("Could not process %s: %s", json_path, exc)
                total_failed += 1
                continue

            total_processed += processed
            total_skipped += skipped
            total_failed += failed

        LOGGER.info(
            "Finished. Updated=%d, skipped=%d, failed=%d",
            total_processed,
            total_skipped,
            total_failed,
        )
        return 1 if total_failed else 0

    except (AppError, OSError, UnidentifiedImageError) as exc:
        LOGGER.error("Fatal error: %s", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
