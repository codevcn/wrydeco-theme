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

3. Real Amazon images are downloaded and uploaded through:

       POST https://vnote.io.vn/api/upload-image

4. Amazon URLs are replaced with the returned Vnote `image_url`.

5. The `src` attribute of EVERY <img> is always replaced with:

       IMAGE_PLACEHOLDER_URL

6. Special case:
   If the real Amazon image exists ONLY in `src`:

       src="AMAZON_REAL_IMAGE"

   then after upload it becomes:

       src="IMAGE_PLACEHOLDER_URL"
       data-src="VNOTE_IMAGE_URL"

7. Amazon placeholder images such as grey-pixel.gif are not uploaded when
   the real image already exists in data-src or another source attribute.

8. Final validation scans every <img> tag again.

   If Amazon URLs are still present:
   - config is NOT modified
   - remaining URLs are appended to amazon-links-left.txt

9. If upload to Vnote fails:
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

    python replace_amazon_rich_images.py \
        --upload-url http://localhost:8000/api/upload-image
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import mimetypes
import re
from datetime import datetime
from pathlib import Path
from typing import Any, MutableMapping
from urllib.parse import urlparse

import requests

from handle_images import (
    AppError,
    atomic_write_json,
    create_backup,
    create_http_session,
    download_image,
    first_nonempty,
    load_json,
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
# Vnote upload API
# ------------------------------------------------------------

DEFAULT_UPLOAD_IMAGE_URL = (
    "https://vnote.io.vn/api/upload-image"
)

UPLOAD_TIMEOUT_SECONDS = 60

MAX_UPLOAD_BYTES = 10 * 1024 * 1024

SUPPORTED_UPLOAD_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
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
}


# ============================================================
# CLI
# ============================================================


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Upload Amazon images found inside <img> tags "
            "to Vnote, replace Amazon URLs with Vnote URLs, "
            "and force every img src to IMAGE_PLACEHOLDER_URL."
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
        "--upload-url",
        default=DEFAULT_UPLOAD_IMAGE_URL,
        help=(
            "Image upload API endpoint. Default: "
            f"{DEFAULT_UPLOAD_IMAGE_URL}"
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

    therefore its new Vnote URL must be placed into data-src
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
    # data-src = already Vnote URL
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
    Determine image extension and MIME type accepted
    by /api/upload-image.
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
                "by /api/upload-image. "
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
                "by /api/upload-image. "
                "Supported: JPG, PNG, WEBP, GIF. "
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
# VNOTE UPLOAD
# ============================================================


def upload_image_via_api(
    session: requests.Session,
    upload_url: str,
    content: bytes,
    filename: str,
    mime_type: str,
    tag: str,
) -> str:
    """
    Upload one image through Vnote API.

    POST /api/upload-image

    multipart/form-data:

        image = file
        tag   = string

    Expected JSON:

        {
            "image_url": "https://..."
        }
    """

    if len(content) > MAX_UPLOAD_BYTES:

        raise AppError(
            (
                "Image exceeds the API 10MB limit: "
                f"{filename} "
                f"("
                f"{len(content) / (1024 * 1024):.2f} MB"
                f")"
            )
        )

    response = session.post(
        upload_url,
        files={
            "image": (
                filename,
                content,
                mime_type,
            )
        },
        data={
            "tag": tag,
        },
        headers={
            "Accept": "application/json",
        },
        timeout=UPLOAD_TIMEOUT_SECONDS,
    )

    try:

        response.raise_for_status()

    except requests.HTTPError as exc:

        body = response.text.strip()

        if len(body) > 1000:
            body = (
                body[:1000]
                + "..."
            )

        raise AppError(
            (
                "Upload API returned HTTP "
                f"{response.status_code}: "
                f"{body or '<empty response>'}"
            )
        ) from exc

    try:

        payload = response.json()

    except ValueError as exc:

        raise AppError(
            (
                "Upload API did not return valid JSON: "
                f"{response.text[:1000]!r}"
            )
        ) from exc

    image_url = (
        payload.get("image_url")
        if isinstance(payload, dict)
        else None
    )

    if (
        not isinstance(
            image_url,
            str,
        )
        or not image_url.strip()
    ):
        raise AppError(
            (
                "Upload API response is missing "
                "a non-empty 'image_url'."
            )
        )

    image_url = (
        image_url.strip()
    )

    normalize_http_url(
        image_url,
        (
            "image_url returned "
            "by upload API"
        ),
    )

    return image_url


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

        upload_url = (
            normalize_http_url(
                args.upload_url,
                "--upload-url",
            )
        )

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
            "Upload API: %s",
            upload_url,
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
            "image/gif;q=0.9,"
            "*/*;q=0.1"
        )

        # Amazon URL -> Vnote URL

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

                tag_value = (
                    safe_filename(
                        f"{identifier}"
                        f"-rich-"
                        f"{display_index:03d}"
                    )
                )

                public_url = (
                    upload_image_via_api(
                        session=session,
                        upload_url=upload_url,
                        content=content,
                        filename=filename,
                        mime_type=mime_type,
                        tag=tag_value,
                    )
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
                    "Upload to Vnote failed; "
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
            #   data-src="VNOTE_REAL.jpg"
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