"""
Rehost every <img> in product.product_rich_description onto the Shopify store.

For each <img> tag found in config.prepare.json -> product.product_rich_description:

    1. Read the image URL from the tag's `src` attribute.
    2. Download the image from that origin URL.
    3. Re-upload it to the store's Content > Files (Shopify CDN).
    4. Replace the `src` value with the returned Shopify CDN URL.

The point is to swap the origin URL (e.g. an Amazon media URL that may block
hotlinking) with a Shopify CDN URL that the storefront can always load.

All credentials are read only from `.media.env` located next to this script
(reusing the loader/uploader from handle_images.py). The image data itself is
re-uploaded as-is, without adding a logo.

Usage:

    python replace_amazon_rich_images.py
    python replace_amazon_rich_images.py --force
    python replace_amazon_rich_images.py --no-backup
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import mimetypes
import re
from pathlib import Path
from typing import Any, MutableMapping
from urllib.parse import urlparse

import requests

from handle_images import (
    DEFAULT_API_VERSION,
    DEFAULT_SHOPIFY_READY_TIMEOUT_SECONDS,
    MEDIA_ENV_PATH,
    AppError,
    EncodedImage,
    ShopifyClient,
    ShopifySettings,
    atomic_write_json,
    create_backup,
    create_http_session,
    download_image,
    first_nonempty,
    is_shopify_cdn_url,
    load_env_file,
    load_json,
    mime_for_extension,
    normalize_store_domain,
    parse_positive_int,
    safe_filename,
)

LOGGER = logging.getLogger("rich-description-image-rehoster")
SCRIPT_DIR = Path(__file__).resolve().parent

# Match a whole <img ...> tag and, inside it, its src="..." / src='...' value.
IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
SRC_ATTR_RE = re.compile(r"(src\s*=\s*)(\"[^\"]*\"|'[^']*')", re.IGNORECASE)

_KNOWN_IMAGE_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".tif",
    ".tiff",
    ".avif",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download every <img> src in product.product_rich_description, "
            "re-upload it to Shopify Files, and replace each src with the "
            "returned Shopify CDN URL."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=SCRIPT_DIR / "config.prepare.json",
        help=(
            "Config JSON path. By default, config.prepare.json in the same "
            "folder as this script is used."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Also rehost src values that already point to the Shopify CDN.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create a timestamped backup before changing the config.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO).",
    )
    return parser.parse_args()


def load_shopify_settings() -> ShopifySettings:
    """Read Shopify credentials only from .media.env next to this script."""
    env_path = MEDIA_ENV_PATH.resolve()
    env_values = load_env_file(env_path)

    access_token = first_nonempty(env_values.get("STORE_ADMIN_ACCESS_TOKEN"))
    if not access_token:
        raise AppError(f"STORE_ADMIN_ACCESS_TOKEN is missing from {env_path.name}.")

    store_domain = first_nonempty(
        env_values.get("SHOPIFY_STORE_DOMAIN"),
        env_values.get("STORE_DOMAIN"),
        env_values.get("SHOP_DOMAIN"),
    )
    if not store_domain:
        raise AppError(
            "A Shopify store domain is required. Add SHOPIFY_STORE_DOMAIN="
            f"your-store.myshopify.com to {env_path.name}."
        )

    api_version = first_nonempty(
        env_values.get("SHOPIFY_API_VERSION"),
        DEFAULT_API_VERSION,
    )
    ready_timeout_raw = first_nonempty(
        env_values.get("SHOPIFY_FILE_READY_TIMEOUT_SECONDS"),
    )
    ready_timeout = (
        parse_positive_int(ready_timeout_raw, "SHOPIFY_FILE_READY_TIMEOUT_SECONDS")
        if ready_timeout_raw
        else DEFAULT_SHOPIFY_READY_TIMEOUT_SECONDS
    )

    return ShopifySettings(
        store_domain=normalize_store_domain(store_domain),
        access_token=access_token,
        api_version=api_version or DEFAULT_API_VERSION,
        ready_timeout_seconds=ready_timeout,
    )


def guess_extension_and_mime(content_type: str | None, url: str) -> tuple[str, str]:
    """Pick a file extension + MIME type from the response type, else the URL."""
    normalized_type = (content_type or "").split(";", 1)[0].strip().lower()
    type_to_extension = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/pjpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/tiff": ".tif",
        "image/avif": ".avif",
    }

    extension = type_to_extension.get(normalized_type)
    if not extension:
        suffix = Path(urlparse(url).path).suffix.lower()
        if suffix in _KNOWN_IMAGE_SUFFIXES:
            extension = ".jpg" if suffix == ".jpeg" else suffix
    if not extension:
        extension = ".png"

    if normalized_type.startswith("image/"):
        mime_type = normalized_type
    else:
        mime_type = mime_for_extension(extension)
        if extension in {".gif", ".avif"}:
            mime_type = mimetypes.guess_type("image" + extension)[0] or mime_type

    return extension, mime_type


def should_rehost(url: str, force: bool) -> bool:
    """Only http(s) origins are rehosted; CDN URLs are skipped unless forced."""
    scheme = urlparse(url).scheme.lower()
    if scheme not in {"http", "https"}:
        return False
    if is_shopify_cdn_url(url) and not force:
        return False
    return True


def get_rich_description(payload: MutableMapping[str, Any]) -> str:
    try:
        product = payload["product"]
        rich_description = product["product_rich_description"]
    except (KeyError, TypeError) as exc:
        raise AppError(
            "config is missing product.product_rich_description."
        ) from exc

    if not isinstance(rich_description, str):
        raise AppError("product.product_rich_description must be a string.")
    return rich_description


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        config_path = args.config.resolve()
        shopify_settings = load_shopify_settings()

        payload = load_json(config_path)
        if not isinstance(payload, MutableMapping):
            raise AppError(f"Config root must be a JSON object: {config_path}")

        rich_description = get_rich_description(payload)
        source_urls = [
            match.group(2)[1:-1].strip()
            for tag in IMG_TAG_RE.findall(rich_description)
            for match in [SRC_ATTR_RE.search(tag)]
            if match
        ]
        rehostable = [url for url in source_urls if should_rehost(url, args.force)]

        if not rehostable:
            LOGGER.info(
                "No rehostable <img> src found in product.product_rich_description; "
                "nothing to do."
            )
            return 0

        LOGGER.info("Config: %s", config_path)
        LOGGER.info("Shopify store: %s", shopify_settings.store_domain)
        LOGGER.info(
            "Found %d <img> tag(s); %d src URL(s) to rehost.",
            len(source_urls),
            len(set(rehostable)),
        )

        if not args.no_backup:
            backup_path = create_backup(config_path)
            LOGGER.info("Backup created: %s", backup_path)

        product = payload["product"]
        identifier = safe_filename(
            first_nonempty(
                product.get("product_id"),
                product.get("product_title"),
                config_path.stem,
            )
            or "rich"
        )

        session = create_http_session()
        shopify = ShopifyClient(shopify_settings, session)

        # Cache so identical src URLs are downloaded/uploaded only once.
        url_to_cdn: dict[str, str] = {}
        processed = 0
        skipped = 0
        failed = 0
        next_index = 0

        def replace_src(tag: str) -> str:
            nonlocal processed, skipped, failed, next_index

            match = SRC_ATTR_RE.search(tag)
            if not match:
                return tag

            quoted_value = match.group(2)
            quote = quoted_value[0]
            source_url = quoted_value[1:-1].strip()

            if not should_rehost(source_url, args.force):
                skipped += 1
                LOGGER.info("Skipped (not rehostable): %s", source_url or "<empty>")
                return tag

            cdn_url = url_to_cdn.get(source_url)
            if cdn_url is None:
                next_index += 1
                display_index = next_index
                try:
                    LOGGER.info("Image %d: downloading %s", display_index, source_url)
                    content, content_type = download_image(session, source_url)
                    extension, mime_type = guess_extension_and_mime(
                        content_type, source_url
                    )
                    digest = hashlib.sha256(content).hexdigest()[:12]
                    filename = (
                        f"{identifier}-rich-{display_index:03d}-{digest}{extension}"
                    )
                    encoded = EncodedImage(
                        content=content,
                        filename=filename,
                        mime_type=mime_type,
                        width=0,
                        height=0,
                    )
                    cdn_url = shopify.upload_image(encoded, alt_text=filename)
                    url_to_cdn[source_url] = cdn_url
                    processed += 1
                    LOGGER.info(
                        "Image %d: uploaded -> %s", display_index, cdn_url
                    )
                except (requests.RequestException, AppError, OSError) as exc:
                    failed += 1
                    LOGGER.error("Image %d failed (%s): %s", display_index, source_url, exc)
                    return tag

            new_attr = f"{match.group(1)}{quote}{cdn_url}{quote}"
            return tag[: match.start()] + new_attr + tag[match.end() :]

        updated_rich_description = IMG_TAG_RE.sub(
            lambda tag_match: replace_src(tag_match.group(0)),
            rich_description,
        )

        if updated_rich_description != rich_description:
            product["product_rich_description"] = updated_rich_description
            atomic_write_json(config_path, payload)
            LOGGER.info("Updated product.product_rich_description in %s", config_path.name)
        else:
            LOGGER.info("No src value changed; config left untouched.")

        LOGGER.info(
            "Finished. Rehosted=%d, skipped=%d, failed=%d",
            processed,
            skipped,
            failed,
        )
        return 1 if failed else 0

    except (AppError, OSError) as exc:
        LOGGER.error("Fatal error: %s", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
