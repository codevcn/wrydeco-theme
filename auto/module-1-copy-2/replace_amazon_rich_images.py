"""
Replace Amazon hotlinked images inside product.product_rich_description.

FLOW:

1. Parse all <img> tags inside product.product_rich_description.

2. Find Amazon image URLs in attributes such as:
   - data-src
   - data-original
   - data-lazy-src
   - data-lazy
   - data-image
   - data-image-src
   - srcset
   - data-srcset
   - other attributes inside <img>
   - src

3. Real Amazon images are downloaded and uploaded to Shopify Content > Files
   using Admin GraphQL:

       stagedUploadsCreate -> staged binary upload -> fileCreate

   Credentials/store settings are read ONLY from `.media.env` next to
   this script. If Shopify returns HTTP 401, the script uses the client ID
   and client secret from that file to request a fresh access token, saves it
   back to STORE_ADMIN_ACCESS_TOKEN, and retries the GraphQL call once.

4. Amazon URLs are replaced with the final Shopify CDN image URL after
   Shopify reports fileStatus=READY.

5. The `src` attribute of EVERY <img> is always replaced with:

       IMAGE_PLACEHOLDER_URL

6. Special case:
   If the real Amazon image exists ONLY in `src`:

       src="AMAZON_REAL_IMAGE"

   then after upload it becomes:

       src="IMAGE_PLACEHOLDER_URL"
       data-src="SHOPIFY_CDN_IMAGE_URL"

7. Amazon placeholder images such as grey-pixel.gif are not uploaded when
   the real image already exists in data-src or another source attribute.

8. Final validation scans every <img> tag again.

   If Amazon URLs are still present:
   - config is NOT modified
   - remaining URLs are appended to amazon-links-left.txt

9. If upload to Shopify Files fails:
   - config is NOT modified
   - failed Amazon URLs are appended to amazon-links-left.txt

10. amazon-links-left.txt:
    - lives in the same directory as this Python script
    - automatically created if it does not exist
    - opened with append mode "a"
    - existing logs are NEVER overwritten


Usage:

    python replace_amazon_rich_images.py

Optional:

    python replace_amazon_rich_images.py --no-backup
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import mimetypes
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, MutableMapping
from urllib.parse import urlparse

import requests

from handle_images import (
    AppError,
    EncodedImage,
    ShopifyClient,
    ShopifySettings,
    atomic_write_json,
    create_backup,
    create_http_session,
    download_image,
    first_nonempty,
    load_env_file,
    load_json,
    normalize_store_domain,
    parse_positive_int,
    safe_filename,
)


# ============================================================
# BASIC CONFIG
# ============================================================

LOGGER = logging.getLogger(
    "amazon-rich-description-image-rehoster"
)

SCRIPT_DIR = Path(__file__).resolve().parent


# ------------------------------------------------------------
# IMPORTANT:
# Set your placeholder image URL here.
#
# EVERY <img src="..."> will be replaced by this URL.
# ------------------------------------------------------------

IMAGE_PLACEHOLDER_URL = "https://via.placeholder.com/800"


# ------------------------------------------------------------
# Shopify Content > Files
# ------------------------------------------------------------

MEDIA_ENV_PATH = SCRIPT_DIR / ".media.env"
DEFAULT_SHOPIFY_API_VERSION = "2026-07"
DEFAULT_SHOPIFY_READY_TIMEOUT_SECONDS = 180
DEFAULT_SHOPIFY_HTTP_TIMEOUT_SECONDS = 60

# Shopify image files are limited to 20 MB. Resolution limits are
# enforced by Shopify during processing (currently max 20 MP).
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

SUPPORTED_UPLOAD_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/heic",
}


# ------------------------------------------------------------
# Log file for Amazon URLs that could not be removed
# ------------------------------------------------------------

AMAZON_LINKS_LEFT_LOG_PATH = (
    SCRIPT_DIR / "amazon-links-left.txt"
)


# ============================================================
# REGEX
# ============================================================

IMG_TAG_RE = re.compile(
    r"<img\b[^>]*>",
    re.IGNORECASE | re.DOTALL,
)


ATTR_RE = re.compile(
    r"(?P<name>[^\s=/>]+)"
    r"(?P<eq>\s*=\s*)"
    r"(?P<quote>[\"'])"
    r"(?P<value>.*?)"
    r"(?P=quote)",
    re.IGNORECASE | re.DOTALL,
)


HTTP_URL_RE = re.compile(
    r"https?://[^\s\"'<>]+",
    re.IGNORECASE,
)


# These are common attributes that may contain the real image.
#
# `src` is intentionally NOT included because the final `src`
# must always become IMAGE_PLACEHOLDER_URL.

SOURCE_ATTR_NAMES = {
    "data-src",
    "data-original",
    "data-lazy-src",
    "data-lazy",
    "data-image",
    "data-image-src",
    "srcset",
    "data-srcset",
}


_KNOWN_IMAGE_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".heic",
}


# ============================================================
# CLI
# ============================================================


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Upload Amazon images found inside <img> tags "
            "to Shopify Content > Files, replace Amazon URLs with "
            "Shopify CDN URLs, and force every img src to "
            "IMAGE_PLACEHOLDER_URL."
        )
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=SCRIPT_DIR / "config.prepare.json",
        help=(
            "Config JSON path. Default: "
            "config.prepare.json next to this script."
        ),
    )

    parser.add_argument(
        "--no-backup",
        action="store_true",
        help=(
            "Do not create a timestamped backup "
            "before changing config."
        ),
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=[
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
        ],
        help="Logging verbosity. Default: INFO",
    )

    return parser.parse_args()


# ============================================================
# URL HELPERS
# ============================================================


def normalize_http_url(
    value: str,
    label: str,
) -> str:
    """
    Validate and normalize an HTTP/HTTPS URL.
    """

    url = value.strip()

    parsed = urlparse(url)

    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
    ):
        raise AppError(
            f"Invalid {label}: {value!r}"
        )

    return url


def is_amazon_image_url(
    url: str,
) -> bool:
    """
    Return True if the URL appears to be an Amazon-hosted
    image/CDN URL.
    """

    parsed = urlparse(url.strip())

    if parsed.scheme.lower() not in {
        "http",
        "https",
    }:
        return False

    host = (
        parsed.hostname or ""
    ).lower().rstrip(".")

    if not host:
        return False

    # Examples:
    #
    # m.media-amazon.com
    # images-na.ssl-images-amazon.com
    # images-eu.ssl-images-amazon.com
    # images.amazon.com

    amazon_image_suffixes = (
        "media-amazon.com",
        "ssl-images-amazon.com",
        "images-amazon.com",
    )

    if any(
        host == suffix
        or host.endswith("." + suffix)
        for suffix in amazon_image_suffixes
    ):
        return True

    # Extra safety for Amazon image/media subdomains.

    if (
        host == "amazon.com"
        or host.endswith(".amazon.com")
    ):
        if (
            "image" in host
            or "media" in host
        ):
            return True

    return False


def amazon_urls_in_value(
    value: str,
) -> list[str]:
    """
    Extract Amazon image URLs from an attribute value.
    """

    urls: list[str] = []

    for match in HTTP_URL_RE.finditer(value):
        url = match.group(0)

        if is_amazon_image_url(url):
            urls.append(url)

    return urls


# ============================================================
# HTML ATTRIBUTE HELPERS
# ============================================================


def get_attributes(
    tag: str,
) -> list[re.Match[str]]:
    """
    Return all quoted HTML attributes from one <img> tag.
    """

    return list(
        ATTR_RE.finditer(tag)
    )


def get_attribute_value(
    tag: str,
    attribute_name: str,
) -> str | None:
    """
    Get one attribute value from an <img> tag.
    """

    wanted = attribute_name.lower()

    for match in get_attributes(tag):
        if (
            match.group("name").lower()
            == wanted
        ):
            return match.group("value")

    return None


# ============================================================
# FIND REAL AMAZON SOURCES
# ============================================================


def source_amazon_urls(
    tag: str,
) -> tuple[list[str], bool]:
    """
    Determine which Amazon URLs should actually be uploaded
    for one <img> tag.

    Priority:

        non-src source attributes
            ↓
        src

    If there is a real image in data-src / srcset / etc.,
    Amazon src is treated as a placeholder and is NOT uploaded.

    Returns:

        (
            amazon_urls_to_upload,
            src_only
        )

    src_only=True means:

        the real image only existed in src

    therefore its new Shopify CDN URL must be placed into data-src
    before src becomes IMAGE_PLACEHOLDER_URL.
    """

    attrs = get_attributes(tag)

    preferred_urls: list[str] = []

    has_non_src_image_source = False

    for attr in attrs:
        name = (
            attr.group("name")
            .lower()
        )

        value = attr.group("value")

        if name == "src":
            continue

        # Find ALL Amazon URLs in non-src attributes.
        preferred_urls.extend(
            amazon_urls_in_value(value)
        )

        # Detect whether another real source already exists.
        if (
            name in SOURCE_ATTR_NAMES
            and HTTP_URL_RE.search(value)
        ):
            has_non_src_image_source = True

    # Remove duplicates while keeping order.

    preferred_urls = list(
        dict.fromkeys(
            preferred_urls
        )
    )

    # If a real Amazon image exists outside src,
    # use that instead of src.

    if preferred_urls:
        return (
            preferred_urls,
            False,
        )

    # Example:
    #
    # src = Amazon grey-pixel.gif
    # data-src = already Shopify CDN URL
    #
    # Do NOT upload Amazon src.

    if has_non_src_image_source:
        return (
            [],
            False,
        )

    # No other image source exists.
    # Check src.

    src_value = (
        get_attribute_value(
            tag,
            "src",
        )
        or ""
    )

    src_urls = list(
        dict.fromkeys(
            amazon_urls_in_value(
                src_value
            )
        )
    )

    if src_urls:
        return (
            src_urls,
            True,
        )

    return (
        [],
        False,
    )


# ============================================================
# HTML REPLACEMENT
# ============================================================


def replace_urls_in_attribute_values(
    tag: str,
    url_map: dict[str, str],
) -> str:
    """
    Replace uploaded Amazon URLs inside every quoted attribute
    EXCEPT `src`.

    `src` is handled separately because every src must become:

        IMAGE_PLACEHOLDER_URL
    """

    parts: list[str] = []

    cursor = 0

    for match in get_attributes(tag):

        parts.append(
            tag[
                cursor:
                match.start()
            ]
        )

        name = match.group("name")

        # Do NOT replace src here.
        if name.lower() == "src":
            parts.append(
                match.group(0)
            )

        else:
            value = match.group(
                "value"
            )

            new_value = HTTP_URL_RE.sub(
                lambda url_match: (
                    url_map.get(
                        url_match.group(0),
                        url_match.group(0),
                    )
                ),
                value,
            )

            parts.append(
                f"{name}"
                f"{match.group('eq')}"
                f"{match.group('quote')}"
                f"{new_value}"
                f"{match.group('quote')}"
            )

        cursor = match.end()

    parts.append(
        tag[cursor:]
    )

    return "".join(parts)


def set_or_add_attribute(
    tag: str,
    name: str,
    value: str,
) -> str:
    """
    Replace an existing quoted attribute or add it
    if it does not exist.
    """

    wanted = name.lower()

    for match in get_attributes(tag):

        if (
            match.group("name").lower()
            == wanted
        ):
            quote = match.group(
                "quote"
            )

            replacement = (
                f"{match.group('name')}"
                f"{match.group('eq')}"
                f"{quote}"
                f"{value}"
                f"{quote}"
            )

            return (
                tag[:match.start()]
                + replacement
                + tag[match.end():]
            )

    # Attribute not found → add it.

    insert_at = tag.rfind(">")

    if insert_at < 0:
        return tag

    prefix = tag[:insert_at]

    suffix = tag[insert_at:]

    # Handle:
    #
    # <img ... />

    if prefix.endswith("/"):
        prefix = (
            prefix[:-1]
            .rstrip()
        )

        return (
            f'{prefix} '
            f'{name}="{value}" />'
        )

    return (
        f'{prefix} '
        f'{name}="{value}"'
        f'{suffix}'
    )


# ============================================================
# FINAL AMAZON VALIDATION
# ============================================================


def find_amazon_urls_in_img_tags(
    html: str,
) -> list[str]:
    """
    Scan all attributes of all <img> tags.

    Return every Amazon URL still present.
    """

    leftovers: list[str] = []

    for tag_match in IMG_TAG_RE.finditer(
        html
    ):
        tag = tag_match.group(0)

        for attr in get_attributes(
            tag
        ):
            leftovers.extend(
                amazon_urls_in_value(
                    attr.group("value")
                )
            )

    # Unique while preserving order.

    return list(
        dict.fromkeys(
            leftovers
        )
    )


# ============================================================
# AMAZON LEFTOVER LOG
# ============================================================


def append_amazon_links_left(
    urls: list[str],
    *,
    config_path: Path,
    reason: str,
) -> None:
    """
    Append problematic / remaining Amazon URLs to:

        amazon-links-left.txt

    The file is stored next to this Python script.

    IMPORTANT:

        mode = "a"

    Therefore:

    - file is created automatically if missing
    - previous log content is preserved
    - new logs are appended to the bottom
    """

    if not urls:
        return

    # Remove duplicates while preserving order.

    unique_urls = list(
        dict.fromkeys(
            urls
        )
    )

    timestamp = (
        datetime.now()
        .astimezone()
        .isoformat(
            timespec="seconds"
        )
    )

    lines = [
        (
            f"[{timestamp}] "
            "Amazon URL(s) left/problematic"
        ),
        f"Config: {config_path}",
        f"Reason: {reason}",
        f"Count: {len(unique_urls)}",
    ]

    for url in unique_urls:
        lines.append(
            f"- {url}"
        )

    lines.append(
        "-" * 80
    )

    try:

        # ====================================================
        # APPEND MODE
        # ====================================================
        #
        # "a" means:
        #
        # - create if file doesn't exist
        # - append if file already exists
        # - NEVER overwrite previous content
        #
        # ====================================================

        with AMAZON_LINKS_LEFT_LOG_PATH.open(
            "a",
            encoding="utf-8",
            newline="\n",
        ) as handle:

            handle.write(
                "\n".join(lines)
                + "\n"
            )

        LOGGER.warning(
            (
                "Appended %d Amazon URL(s) "
                "to %s"
            ),
            len(unique_urls),
            AMAZON_LINKS_LEFT_LOG_PATH,
        )

    except OSError as exc:

        # Do not hide the original upload /
        # validation error if writing the log fails.

        LOGGER.error(
            (
                "Could not append Amazon URLs "
                "to %s: %s"
            ),
            AMAZON_LINKS_LEFT_LOG_PATH,
            exc,
        )


# ============================================================
# IMAGE FORMAT
# ============================================================


def guess_extension_and_mime(
    content_type: str | None,
    url: str,
) -> tuple[str, str]:
    """
    Determine an image extension and MIME type accepted by Shopify Files.
    """

    normalized_type = (
        content_type or ""
    ).split(
        ";",
        1,
    )[0].strip().lower()

    type_to_extension = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/pjpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/heic": ".heic",
    }

    extension = (
        type_to_extension.get(
            normalized_type
        )
    )

    # Fall back to URL suffix.

    if not extension:

        suffix = Path(
            urlparse(url).path
        ).suffix.lower()

        if (
            suffix
            in _KNOWN_IMAGE_SUFFIXES
        ):
            extension = (
                ".jpg"
                if suffix == ".jpeg"
                else suffix
            )

    # Normalize MIME.

    if normalized_type in {
        "image/jpg",
        "image/pjpeg",
    }:
        mime_type = "image/jpeg"

    elif (
        normalized_type
        in SUPPORTED_UPLOAD_MIME_TYPES
    ):
        mime_type = normalized_type

    elif extension:

        mime_type = (
            mimetypes.guess_type(
                "image" + extension
            )[0]
            or ""
        )

        if mime_type == "image/jpg":
            mime_type = "image/jpeg"

    else:
        raise AppError(
            (
                "Downloaded image format is not supported "
                "by Shopify Files. "
                f"Content-Type={content_type!r}, "
                f"URL={url}"
            )
        )

    if (
        not extension
        or mime_type
        not in SUPPORTED_UPLOAD_MIME_TYPES
    ):
        raise AppError(
            (
                "Downloaded image format is not supported "
                "by Shopify Files. "
                "Supported: JPG, PNG, WEBP, GIF, HEIC. "
                f"Content-Type={content_type!r}, "
                f"URL={url}"
            )
        )

    return (
        extension,
        mime_type,
    )


# ============================================================
# CONFIG
# ============================================================


def get_rich_description(
    payload: MutableMapping[str, Any],
) -> str:
    """
    Read:

        product.product_rich_description
    """

    try:

        product = payload["product"]

        rich_description = (
            product[
                "product_rich_description"
            ]
        )

    except (
        KeyError,
        TypeError,
    ) as exc:

        raise AppError(
            (
                "config is missing "
                "product.product_rich_description."
            )
        ) from exc

    if not isinstance(
        product,
        MutableMapping,
    ):
        raise AppError(
            "product must be a JSON object."
        )

    if not isinstance(
        rich_description,
        str,
    ):
        raise AppError(
            (
                "product.product_rich_description "
                "must be a string."
            )
        )

    return rich_description


# ============================================================
# SHOPIFY SETTINGS
# ============================================================


def load_shopify_settings(
    env_path: Path = MEDIA_ENV_PATH,
) -> ShopifySettings:
    """
    Read Shopify upload settings ONLY from `.media.env` next to this script.

    Required for normal API calls:
        STORE_ADMIN_ACCESS_TOKEN
        SHOPIFY_STORE_DOMAIN

    Required for automatic token renewal after HTTP 401:
        STORE_ADMIN_CLIENT_ID
        STORE_ADMIN_CLIENT_SECRET

    Optional:
        SHOPIFY_API_VERSION
        SHOPIFY_FILE_READY_TIMEOUT_SECONDS

    Client-credentials access tokens are short-lived. If Shopify returns
    HTTP 401, this script requests a new access token using the client ID and
    client secret, writes the new token back to `.media.env`, then retries the
    failed GraphQL request once.
    """

    env_values = load_env_file(env_path)

    access_token = first_nonempty(
        env_values.get("STORE_ADMIN_ACCESS_TOKEN")
    )
    if not access_token:
        raise AppError(
            "STORE_ADMIN_ACCESS_TOKEN is missing from "
            f"{env_path.name}."
        )

    store_domain = first_nonempty(
        env_values.get("SHOPIFY_STORE_DOMAIN")
    )
    if not store_domain:
        raise AppError(
            "SHOPIFY_STORE_DOMAIN is missing from "
            f"{env_path.name}."
        )

    api_version = first_nonempty(
        env_values.get("SHOPIFY_API_VERSION"),
        DEFAULT_SHOPIFY_API_VERSION,
    )

    ready_timeout_raw = first_nonempty(
        env_values.get("SHOPIFY_FILE_READY_TIMEOUT_SECONDS")
    )
    ready_timeout = (
        parse_positive_int(
            ready_timeout_raw,
            "SHOPIFY_FILE_READY_TIMEOUT_SECONDS",
        )
        if ready_timeout_raw
        else DEFAULT_SHOPIFY_READY_TIMEOUT_SECONDS
    )

    return ShopifySettings(
        store_domain=normalize_store_domain(store_domain),
        access_token=access_token,
        api_version=api_version or DEFAULT_SHOPIFY_API_VERSION,
        ready_timeout_seconds=ready_timeout,
    )




# ============================================================
# SHOPIFY ACCESS TOKEN AUTO-RENEWAL
# ============================================================


def load_shopify_client_credentials(
    env_path: Path = MEDIA_ENV_PATH,
) -> tuple[str | None, str | None]:
    """Read client ID/secret used only when a token must be renewed."""

    env_values = load_env_file(env_path)

    return (
        first_nonempty(env_values.get("STORE_ADMIN_CLIENT_ID")),
        first_nonempty(env_values.get("STORE_ADMIN_CLIENT_SECRET")),
    )


def update_env_access_token(
    env_path: Path,
    new_access_token: str,
) -> None:
    """
    Atomically replace STORE_ADMIN_ACCESS_TOKEN in `.media.env`.

    Existing comments/order are preserved. If the key doesn't exist, it is
    appended. The previous quote style (' or ") is preserved when possible.
    """

    if not env_path.exists():
        raise AppError(f"Env file not found while saving refreshed token: {env_path}")

    try:
        original = env_path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise AppError(f"Could not read {env_path} to save refreshed token: {exc}") from exc

    lines = original.splitlines(keepends=True)
    key = "STORE_ADMIN_ACCESS_TOKEN"
    key_re = re.compile(
        rf"^(?P<prefix>\s*(?:export\s+)?{re.escape(key)}\s*=\s*)(?P<value>.*?)(?P<newline>\r?\n)?$"
    )

    replaced = False
    output: list[str] = []

    for line in lines:
        match = key_re.match(line)
        if not match:
            output.append(line)
            continue

        old_value = (match.group("value") or "").strip()
        quote = ""
        if len(old_value) >= 2 and old_value[0] == old_value[-1] and old_value[0] in {"'", '"'}:
            quote = old_value[0]

        newline = match.group("newline") or ""
        output.append(
            f"{match.group('prefix')}{quote}{new_access_token}{quote}{newline}"
        )
        replaced = True

    if not replaced:
        if original and not original.endswith(("\n", "\r")):
            output.append("\n")
        output.append(f"{key}='{new_access_token}'\n")

    updated = "".join(output)
    temp_path = env_path.with_name(env_path.name + ".tmp")

    try:
        temp_path.write_text(updated, encoding="utf-8", newline="")
        os.replace(temp_path, env_path)
    except OSError as exc:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise AppError(f"Could not persist refreshed Shopify token to {env_path}: {exc}") from exc


def request_new_shopify_access_token(
    session: requests.Session,
    *,
    store_domain: str,
    client_id: str,
    client_secret: str,
) -> tuple[str, int | None, str | None]:
    """Request a fresh Shopify Admin API token via Client Credentials Grant."""

    token_url = f"https://{store_domain}/admin/oauth/access_token"

    try:
        response = session.post(
            token_url,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=DEFAULT_SHOPIFY_HTTP_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise AppError(f"Could not request a new Shopify access token: {exc}") from exc

    if response.status_code < 200 or response.status_code >= 300:
        body = (response.text or "").strip().replace("\n", " ")[:500]
        raise AppError(
            "Shopify access-token renewal failed with HTTP "
            f"{response.status_code}: {body or '<empty response>'}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise AppError(
            "Shopify access-token endpoint returned non-JSON data: "
            f"{response.text[:500]}"
        ) from exc

    access_token = first_nonempty(payload.get("access_token"))
    if not access_token:
        raise AppError("Shopify access-token response did not contain access_token.")

    expires_in_raw = payload.get("expires_in")
    expires_in: int | None = None
    if expires_in_raw is not None:
        try:
            expires_in = int(expires_in_raw)
        except (TypeError, ValueError):
            expires_in = None

    scope = first_nonempty(payload.get("scope"))
    return access_token, expires_in, scope


class AutoRenewShopifyClient(ShopifyClient):
    """
    Shopify Files client that renews an expired/invalid token once on HTTP 401.

    The renewal request uses STORE_ADMIN_CLIENT_ID and
    STORE_ADMIN_CLIENT_SECRET from `.media.env`. After renewal, the new token
    is persisted back to STORE_ADMIN_ACCESS_TOKEN and used for the retry.
    """

    def __init__(
        self,
        settings: ShopifySettings,
        session: requests.Session,
        *,
        env_path: Path,
        client_id: str | None,
        client_secret: str | None,
    ) -> None:
        super().__init__(settings, session)
        self.env_path = env_path
        self.client_id = client_id
        self.client_secret = client_secret

    def _renew_access_token(self) -> None:
        if not self.client_id or not self.client_secret:
            raise AppError(
                "Shopify returned HTTP 401, but automatic token renewal cannot run because "
                "STORE_ADMIN_CLIENT_ID and/or STORE_ADMIN_CLIENT_SECRET is missing from "
                f"{self.env_path.name}."
            )

        LOGGER.warning(
            "Shopify Admin API returned HTTP 401. Requesting a new access token via client credentials."
        )

        new_token, expires_in, scope = request_new_shopify_access_token(
            self.session,
            store_domain=self.settings.store_domain,
            client_id=self.client_id,
            client_secret=self.client_secret,
        )

        # Persist first so the next process starts with the fresh token.
        update_env_access_token(self.env_path, new_token)

        self.settings = ShopifySettings(
            store_domain=self.settings.store_domain,
            access_token=new_token,
            api_version=self.settings.api_version,
            ready_timeout_seconds=self.settings.ready_timeout_seconds,
        )

        details: list[str] = []
        if expires_in is not None:
            details.append(f"expires_in={expires_in}s")
        if scope:
            details.append(f"scope={scope}")

        LOGGER.info(
            "Shopify access token renewed and saved to %s%s.",
            self.env_path.name,
            f" ({', '.join(details)})" if details else "",
        )

    def graphql(
        self,
        query: str,
        variables: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Execute GraphQL, renew on the first HTTP 401, then retry once."""

        for attempt in range(2):
            response = self.session.post(
                self.endpoint,
                headers={
                    "Content-Type": "application/json",
                    "X-Shopify-Access-Token": self.settings.access_token,
                },
                json={"query": query, "variables": variables},
                timeout=DEFAULT_SHOPIFY_HTTP_TIMEOUT_SECONDS,
            )

            if response.status_code == 401 and attempt == 0:
                self._renew_access_token()
                continue

            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                body = (response.text or "").strip().replace("\n", " ")[:500]
                raise AppError(
                    "Shopify Admin GraphQL request failed with HTTP "
                    f"{response.status_code}: {body or '<empty response>'}"
                ) from exc

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

        raise AppError("Shopify authentication failed after renewing the access token once.")


# ============================================================
# MAIN
# ============================================================


def main() -> int:

    args = parse_args()

    logging.basicConfig(
        level=getattr(
            logging,
            args.log_level,
        ),
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:

        # ----------------------------------------------------
        # Resolve config
        # ----------------------------------------------------

        config_path = (
            args.config.resolve()
        )

        shopify_settings = load_shopify_settings()
        (
            shopify_client_id,
            shopify_client_secret,
        ) = load_shopify_client_credentials()

        # IMAGE_PLACEHOLDER_URL is mandatory.

        placeholder_url = (
            normalize_http_url(
                IMAGE_PLACEHOLDER_URL,
                (
                    "IMAGE_PLACEHOLDER_URL "
                    "(set this variable near "
                    "the top of the script)"
                ),
            )
        )

        # ----------------------------------------------------
        # Load JSON
        # ----------------------------------------------------

        payload = load_json(
            config_path
        )

        if not isinstance(
            payload,
            MutableMapping,
        ):
            raise AppError(
                (
                    "Config root must be "
                    "a JSON object: "
                    f"{config_path}"
                )
            )

        rich_description = (
            get_rich_description(
                payload
            )
        )

        # ----------------------------------------------------
        # Parse img tags
        # ----------------------------------------------------

        img_tags = [
            match.group(0)
            for match
            in IMG_TAG_RE.finditer(
                rich_description
            )
        ]

        if not img_tags:

            LOGGER.info(
                (
                    "No <img> tag found in "
                    "product.product_rich_description; "
                    "nothing to do."
                )
            )

            return 0

        # ----------------------------------------------------
        # Collect Amazon images
        # ----------------------------------------------------

        amazon_urls: list[str] = []

        # Which img tags had the real Amazon image only in src?

        src_only_tag_indexes: set[int] = set()

        # Map tag index -> its source Amazon URLs.

        tag_source_urls: dict[
            int,
            list[str],
        ] = {}

        for index, tag in enumerate(
            img_tags
        ):

            (
                urls,
                src_only,
            ) = source_amazon_urls(
                tag
            )

            if urls:

                tag_source_urls[
                    index
                ] = urls

                amazon_urls.extend(
                    urls
                )

                if src_only:
                    src_only_tag_indexes.add(
                        index
                    )

        # Unique URLs only.

        amazon_urls = list(
            dict.fromkeys(
                amazon_urls
            )
        )

        LOGGER.info(
            "Config: %s",
            config_path,
        )

        LOGGER.info(
            "Shopify store: %s",
            shopify_settings.store_domain,
        )

        LOGGER.info(
            "Shopify Admin API version: %s",
            shopify_settings.api_version,
        )

        LOGGER.info(
            "IMAGE_PLACEHOLDER_URL: %s",
            placeholder_url,
        )

        LOGGER.info(
            (
                "Found %d <img> tag(s); "
                "%d unique real Amazon "
                "image URL(s) to upload."
            ),
            len(img_tags),
            len(amazon_urls),
        )

        # ----------------------------------------------------
        # Build image identifier
        # ----------------------------------------------------

        product = payload[
            "product"
        ]

        identifier = safe_filename(
            first_nonempty(
                product.get(
                    "product_id"
                ),
                product.get(
                    "product_title"
                ),
                config_path.stem,
            )
            or "rich"
        )

        # ----------------------------------------------------
        # HTTP session
        # ----------------------------------------------------

        session = (
            create_http_session()
        )

        session.headers["Accept"] = (
            "image/jpeg,"
            "image/png,"
            "image/webp,"
            "image/gif,"
            "image/heic;q=0.9,"
            "*/*;q=0.1"
        )

        shopify_client = AutoRenewShopifyClient(
            shopify_settings,
            session,
            env_path=MEDIA_ENV_PATH,
            client_id=shopify_client_id,
            client_secret=shopify_client_secret,
        )

        # Amazon URL -> Shopify CDN URL

        url_to_public: dict[
            str,
            str,
        ] = {}

        failed_urls: list[str] = []

        # ----------------------------------------------------
        # DOWNLOAD + UPLOAD
        # ----------------------------------------------------

        for (
            display_index,
            source_url,
        ) in enumerate(
            amazon_urls,
            start=1,
        ):

            try:

                LOGGER.info(
                    (
                        "Image %d: "
                        "downloading %s"
                    ),
                    display_index,
                    source_url,
                )

                (
                    content,
                    content_type,
                ) = download_image(
                    session,
                    source_url,
                )

                (
                    extension,
                    mime_type,
                ) = guess_extension_and_mime(
                    content_type,
                    source_url,
                )

                digest = (
                    hashlib
                    .sha256(content)
                    .hexdigest()[:12]
                )

                filename = (
                    f"{identifier}"
                    f"-rich-"
                    f"{display_index:03d}"
                    f"-{digest}"
                    f"{extension}"
                )

                if len(content) > MAX_UPLOAD_BYTES:
                    raise AppError(
                        "Image exceeds Shopify's 20 MB image-file limit: "
                        f"{filename} "
                        f"({len(content) / (1024 * 1024):.2f} MB)"
                    )

                product_title = first_nonempty(
                    product.get("product_title")
                )
                alt_text = (
                    f"{product_title} rich description image {display_index}"
                    if product_title
                    else filename
                )

                public_url = shopify_client.upload_image(
                    EncodedImage(
                        content=content,
                        filename=filename,
                        mime_type=mime_type,
                        width=0,
                        height=0,
                    ),
                    alt_text=alt_text,
                )

                normalize_http_url(
                    public_url,
                    "Shopify CDN URL returned after file upload",
                )

                url_to_public[
                    source_url
                ] = public_url

                LOGGER.info(
                    (
                        "Image %d: "
                        "uploaded -> %s"
                    ),
                    display_index,
                    public_url,
                )

            except (
                requests.RequestException,
                AppError,
                OSError,
            ) as exc:

                failed_urls.append(
                    source_url
                )

                LOGGER.error(
                    (
                        "Image %d failed "
                        "(%s): %s"
                    ),
                    display_index,
                    source_url,
                    exc,
                )

        # ----------------------------------------------------
        # UPLOAD FAILURE
        # ----------------------------------------------------

        if failed_urls:

            # ================================================
            # APPEND failed URLs to amazon-links-left.txt
            # ================================================

            append_amazon_links_left(
                failed_urls,
                config_path=config_path,
                reason=(
                    "Upload to Shopify Files failed; "
                    "config was not modified, "
                    "so these Amazon URL(s) "
                    "remain in the rich description."
                ),
            )

            raise AppError(
                (
                    "One or more Amazon images "
                    "could not be uploaded. "
                    "Config was not modified. "
                    "Failed URL(s):\n- "
                    + "\n- ".join(
                        failed_urls
                    )
                )
            )

        # ----------------------------------------------------
        # REPLACE HTML
        # ----------------------------------------------------

        current_img_index = -1

        def replace_img(
            tag_match: re.Match[str],
        ) -> str:

            nonlocal current_img_index

            current_img_index += 1

            tag = (
                tag_match.group(0)
            )

            # -----------------------------------------------
            # Replace Amazon URLs in non-src attributes
            # -----------------------------------------------

            tag = (
                replace_urls_in_attribute_values(
                    tag,
                    url_to_public,
                )
            )

            # -----------------------------------------------
            # If real Amazon image existed only in src:
            #
            # OLD:
            #
            # <img src="amazon-real.jpg">
            #
            # NEW:
            #
            # <img
            #   src="PLACEHOLDER"
            #   data-src="SHOPIFY_CDN_REAL.jpg"
            # >
            # -----------------------------------------------

            if (
                current_img_index
                in src_only_tag_indexes
            ):

                urls = tag_source_urls.get(
                    current_img_index,
                    [],
                )

                if urls:

                    first_source_url = (
                        urls[0]
                    )

                    uploaded_url = (
                        url_to_public[
                            first_source_url
                        ]
                    )

                    tag = (
                        set_or_add_attribute(
                            tag,
                            "data-src",
                            uploaded_url,
                        )
                    )

            # -----------------------------------------------
            # REQUIRED:
            #
            # EVERY img src = IMAGE_PLACEHOLDER_URL
            # -----------------------------------------------

            tag = set_or_add_attribute(
                tag,
                "src",
                placeholder_url,
            )

            return tag

        updated_rich_description = (
            IMG_TAG_RE.sub(
                replace_img,
                rich_description,
            )
        )

        # ----------------------------------------------------
        # FINAL VALIDATION
        # ----------------------------------------------------

        leftovers = (
            find_amazon_urls_in_img_tags(
                updated_rich_description
            )
        )

        if leftovers:

            # ================================================
            # APPEND remaining URLs to amazon-links-left.txt
            # ================================================

            append_amazon_links_left(
                leftovers,
                config_path=config_path,
                reason=(
                    "Final validation found "
                    "Amazon URL(s) still present "
                    "inside <img> tag(s); "
                    "config was not modified."
                ),
            )

            raise AppError(
                (
                    "Amazon hotlink validation failed. "
                    "Config was not modified. "
                    "Amazon URL(s) still present "
                    "inside <img> tag(s):\n- "
                    + "\n- ".join(
                        leftovers
                    )
                )
            )

        # ----------------------------------------------------
        # Nothing changed
        # ----------------------------------------------------

        if (
            updated_rich_description
            == rich_description
        ):

            LOGGER.info(
                (
                    "No rich-description change "
                    "required; config left untouched."
                )
            )

            return 0

        # ----------------------------------------------------
        # Backup
        # ----------------------------------------------------

        if not args.no_backup:

            backup_path = (
                create_backup(
                    config_path
                )
            )

            LOGGER.info(
                "Backup created: %s",
                backup_path,
            )

        # ----------------------------------------------------
        # Save config
        # ----------------------------------------------------

        product[
            "product_rich_description"
        ] = updated_rich_description

        atomic_write_json(
            config_path,
            payload,
        )

        LOGGER.info(
            (
                "Updated "
                "product.product_rich_description "
                "in %s. "
                "Uploaded=%d; "
                "remaining Amazon hotlinks "
                "in <img>=0."
            ),
            config_path.name,
            len(url_to_public),
        )

        return 0

    except (
        AppError,
        OSError,
    ) as exc:

        LOGGER.error(
            "Fatal error: %s",
            exc,
        )

        return 2


# ============================================================
# ENTRY POINT
# ============================================================


if __name__ == "__main__":
    raise SystemExit(
        main()
    )