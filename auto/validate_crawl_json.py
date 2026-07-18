#!/usr/bin/env python3
"""Validate WRYDECO Amazon crawl JSON files.

Usage:
    python validate_crawl_json.py                 # validate every JSON in ./data
    python validate_crawl_json.py path/to/product.json
    python validate_crawl_json.py path/to/folder

Exit codes:
    0 = every JSON file is valid
    1 = schema validation failed
    2 = file/JSON parsing error or no JSON files found

The validator uses only Python's standard library.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = "data"

ASIN_PATTERN = re.compile(r"^[A-Z0-9]{10}$")
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SCHEMA_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
VALID_CRAWL_STATUSES = {"completed", "partial", "blocked", "failed"}


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str
    actual: Any = None

    def render(self) -> str:
        actual_text = ""
        if self.actual is not None:
            preview = repr(self.actual)
            if len(preview) > 180:
                preview = preview[:177] + "..."
            actual_text = f" | actual={preview}"
        return f"{self.path}: {self.message}{actual_text}"


class CrawlJsonValidator:
    def __init__(self) -> None:
        self.errors: list[ValidationIssue] = []
        # Set once crawl_metadata.status is read; a completed crawl must expose a
        # concrete price so json_to_shopify_csv.py can build a variant price.
        self.crawl_completed: bool = False

    def error(self, path: str, message: str, actual: Any = None) -> None:
        self.errors.append(ValidationIssue(path, message, actual))

    def require_key(self, obj: Any, key: str, path: str) -> Any:
        if not isinstance(obj, dict):
            self.error(path, "expected object before reading required field", obj)
            return None
        if key not in obj:
            self.error(f"{path}.{key}", "required field is missing")
            return None
        return obj[key]

    def expect_type(
        self,
        value: Any,
        expected: type | tuple[type, ...],
        path: str,
        *,
        nullable: bool = False,
    ) -> bool:
        if value is None and nullable:
            return True

        # bool is a subclass of int in Python; reject it for numeric fields
        # unless bool is itself an accepted type for this field.
        expected_types = expected if isinstance(expected, tuple) else (expected,)
        if (
            any(t in (int, float) for t in expected_types)
            and bool not in expected_types
            and isinstance(value, bool)
        ):
            self.error(path, "expected number, got boolean", value)
            return False

        if not isinstance(value, expected):
            names = " or ".join(t.__name__ for t in expected_types)
            if nullable:
                names += " or null"
            self.error(path, f"expected {names}, got {type(value).__name__}", value)
            return False
        return True

    def expect_non_empty_string(
        self,
        value: Any,
        path: str,
        *,
        nullable: bool = False,
    ) -> bool:
        if value is None and nullable:
            return True
        if not self.expect_type(value, str, path, nullable=nullable):
            return False
        if not value.strip():
            self.error(path, "string must not be empty", value)
            return False
        return True

    def expect_url(
        self,
        value: Any,
        path: str,
        *,
        nullable: bool = False,
    ) -> bool:
        if value is None and nullable:
            return True
        if not self.expect_non_empty_string(value, path, nullable=nullable):
            return False
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            self.error(path, "expected an absolute HTTP/HTTPS URL", value)
            return False
        return True

    def validate(self, data: Any) -> list[ValidationIssue]:
        self.errors = []
        self.crawl_completed = False
        if not isinstance(data, dict):
            self.error("$", "top-level JSON value must be an object", data)
            return self.errors

        self.validate_top_level(data)
        return self.errors

    def validate_top_level(self, data: dict[str, Any]) -> None:
        product_type = self.require_key(data, "product_type", "$")
        product_category = self.require_key(data, "product_category", "$")
        schema_version = self.require_key(data, "schema_version", "$")
        asin = self.require_key(data, "asin", "$")
        source_url = self.require_key(data, "source_url", "$")
        crawl_metadata = self.require_key(data, "crawl_metadata", "$")
        product = self.require_key(data, "product", "$")
        assets = self.require_key(data, "assets", "$")
        color_swatches = self.require_key(data, "color_swatches", "$")
        extra_fields = self.require_key(data, "extra_fields", "$")

        self.expect_non_empty_string(product_type, "$.product_type")
        self.expect_non_empty_string(product_category, "$.product_category")

        if self.expect_non_empty_string(schema_version, "$.schema_version"):
            if not SCHEMA_VERSION_PATTERN.fullmatch(schema_version):
                self.error(
                    "$.schema_version",
                    "expected semantic version format such as 1.2.0",
                    schema_version,
                )

        if self.expect_non_empty_string(asin, "$.asin"):
            if not ASIN_PATTERN.fullmatch(asin):
                self.error("$.asin", "expected a 10-character uppercase Amazon ASIN", asin)

        self.expect_url(source_url, "$.source_url")

        self.validate_crawl_metadata(crawl_metadata, "$.crawl_metadata")
        self.validate_product(product, "$.product")
        self.validate_assets(assets, "$.assets")
        self.validate_color_swatches(color_swatches, "$.color_swatches")
        self.validate_extra_fields(extra_fields, "$.extra_fields")

        # The workflow explicitly requires extra_fields to be appended at the end.
        if list(data.keys()) and list(data.keys())[-1] != "extra_fields":
            self.error(
                "$.extra_fields",
                'field must be the final top-level field in the JSON object',
                list(data.keys())[-1],
            )

    def validate_crawl_metadata(self, value: Any, path: str) -> None:
        if not self.expect_type(value, dict, path):
            return

        crawled_at = self.require_key(value, "crawled_at", path)
        status = self.require_key(value, "status", path)
        marketplace = self.require_key(value, "marketplace", path)
        delivery_country = self.require_key(value, "delivery_country", path)
        delivery_zip_code = self.require_key(value, "delivery_zip_code", path)
        display_currency = self.require_key(value, "display_currency", path)
        location_applied = self.require_key(value, "location_applied", path)
        currency_verified = self.require_key(value, "currency_verified", path)
        errors = self.require_key(value, "errors", path)
        warnings = self.require_key(value, "warnings", path)

        self.expect_non_empty_string(crawled_at, f"{path}.crawled_at", nullable=True)

        if self.expect_non_empty_string(status, f"{path}.status"):
            if status not in VALID_CRAWL_STATUSES:
                self.error(
                    f"{path}.status",
                    f"expected one of {sorted(VALID_CRAWL_STATUSES)}",
                    status,
                )
            self.crawl_completed = status == "completed"

        self.expect_non_empty_string(marketplace, f"{path}.marketplace")
        self.expect_non_empty_string(delivery_country, f"{path}.delivery_country")
        self.expect_non_empty_string(delivery_zip_code, f"{path}.delivery_zip_code")
        self.expect_non_empty_string(display_currency, f"{path}.display_currency")
        self.expect_type(location_applied, bool, f"{path}.location_applied")
        self.expect_type(currency_verified, bool, f"{path}.currency_verified")
        self.validate_string_list(errors, f"{path}.errors")
        self.validate_string_list(warnings, f"{path}.warnings")

        if status == "completed":
            if location_applied is not True:
                self.error(
                    f"{path}.location_applied",
                    "must be true when crawl status is completed",
                    location_applied,
                )
            if currency_verified is not True:
                self.error(
                    f"{path}.currency_verified",
                    "must be true when crawl status is completed",
                    currency_verified,
                )
            if display_currency != "USD":
                self.error(
                    f"{path}.display_currency",
                    'must be "USD" when crawl status is completed',
                    display_currency,
                )

    def validate_product(self, value: Any, path: str) -> None:
        if not self.expect_type(value, dict, path):
            return

        title = self.require_key(value, "title", path)
        base_price = self.require_key(value, "base_price", path)
        description = self.require_key(value, "about_this_item", path)
        product_attributes = self.require_key(value, "product_attributes", path)

        if self.expect_non_empty_string(title, f"{path}.title"):
            if not 50 <= len(title) <= 70:
                self.error(
                    f"{path}.title",
                    "SEO product title must contain 50 to 70 characters",
                    f"{len(title)} characters",
                )

        if self.expect_non_empty_string(description, f"{path}.about_this_item"):
            lowered = description.lower()
            if "<div" not in lowered or "dm-tabs__rte" not in lowered:
                self.error(
                    f"{path}.about_this_item",
                    'expected an HTML string containing a root element with class "dm-tabs__rte"',
                )

        self.validate_money(base_price, f"{path}.base_price")
        self.validate_product_attributes(product_attributes, f"{path}.product_attributes")

    def validate_money(self, value: Any, path: str) -> None:
        if not self.expect_type(value, dict, path):
            return

        amount = self.require_key(value, "amount", path)
        currency = self.require_key(value, "currency", path)
        formatted = self.require_key(value, "formatted", path)
        raw_text = self.require_key(value, "raw_text", path)

        if amount is None:
            # A completed crawl must carry a concrete price; the CSV converter
            # cannot build a variant price from a null amount.
            if self.crawl_completed:
                self.error(
                    f"{path}.amount",
                    "must not be null when crawl status is completed",
                )
        elif self.expect_type(amount, (int, float), f"{path}.amount"):
            if amount < 0:
                self.error(f"{path}.amount", "must be greater than or equal to 0", amount)

        self.expect_non_empty_string(currency, f"{path}.currency", nullable=True)
        self.expect_non_empty_string(formatted, f"{path}.formatted", nullable=True)
        self.expect_non_empty_string(raw_text, f"{path}.raw_text", nullable=True)

    def validate_product_attributes(self, value: Any, path: str) -> None:
        if not self.expect_type(value, dict, path):
            return

        items = self.require_key(value, "items", path)
        by_key = self.require_key(value, "by_key", path)

        item_keys: list[str] = []
        if self.expect_type(items, list, f"{path}.items"):
            for index, item in enumerate(items):
                item_path = f"{path}.items[{index}]"
                key = self.validate_attribute(item, item_path)
                if key:
                    item_keys.append(key)

            duplicates = sorted({key for key in item_keys if item_keys.count(key) > 1})
            for key in duplicates:
                self.error(
                    f"{path}.items",
                    f'duplicate attribute key "{key}"',
                )

        if self.expect_type(by_key, dict, f"{path}.by_key"):
            for key, item in by_key.items():
                key_path = f"{path}.by_key[{json.dumps(key)}]"
                validated_key = self.validate_attribute(item, key_path)
                if validated_key and validated_key != key:
                    self.error(
                        f"{key_path}.key",
                        f'must match dictionary key "{key}"',
                        validated_key,
                    )

            for key in item_keys:
                if key not in by_key:
                    self.error(
                        f"{path}.by_key.{key}",
                        "missing attribute that exists in items",
                    )

    def validate_attribute(self, value: Any, path: str) -> str | None:
        if not self.expect_type(value, dict, path):
            return None

        key = self.require_key(value, "key", path)
        label = self.require_key(value, "label", path)
        attr_value = self.require_key(value, "value", path)
        raw_value = self.require_key(value, "raw_value", path)

        key_is_valid = self.expect_non_empty_string(key, f"{path}.key")
        self.expect_non_empty_string(label, f"{path}.label")
        self.expect_type(attr_value, (str, int, float, bool), f"{path}.value", nullable=True)
        self.expect_type(raw_value, (str, int, float, bool), f"{path}.raw_value", nullable=True)

        return key if key_is_valid else None

    def validate_assets(self, value: Any, path: str) -> None:
        if not self.expect_type(value, dict, path):
            return

        gallery = self.require_key(value, "product_media_gallery", path)
        aplus = self.require_key(value, "aplus_content", path)
        product_videos = self.require_key(value, "product_videos", path)

        # Only the product media gallery must expose a distinct large image per
        # thumbnail; a duplicate here means the crawl captured the same large
        # image for several thumbnails (see the mandatory per-thumbnail click
        # procedure in crawl.md).
        self.validate_media_group(
            gallery, f"{path}.product_media_gallery", check_duplicate_urls=True
        )
        self.validate_media_group(aplus, f"{path}.aplus_content")
        self.validate_video_list(product_videos, f"{path}.product_videos")

    def validate_media_group(
        self, value: Any, path: str, *, check_duplicate_urls: bool = False
    ) -> None:
        if not self.expect_type(value, dict, path):
            return
        images = self.require_key(value, "images", path)
        videos = self.require_key(value, "videos", path)
        self.validate_image_list(
            images, f"{path}.images", check_duplicate_urls=check_duplicate_urls
        )
        self.validate_video_list(videos, f"{path}.videos")

    def validate_image_list(
        self, value: Any, path: str, *, check_duplicate_urls: bool = False
    ) -> None:
        if not self.expect_type(value, list, path):
            return

        seen_indexes: set[int] = set()
        # Maps a normalized URL to the image path that first used it, so a
        # duplicate report can point at the earlier occurrence.
        seen_source_urls: dict[str, str] = {}
        seen_resolved_urls: dict[str, str] = {}
        for index, image in enumerate(value):
            image_path = f"{path}[{index}]"
            if not self.expect_type(image, dict, image_path):
                continue

            media_index = self.require_key(image, "index", image_path)
            source_url = self.require_key(image, "source_url", image_path)
            resolved_url = self.require_key(image, "resolved_url", image_path)
            thumbnail_url = self.require_key(image, "thumbnail_url", image_path)
            alt_text = self.require_key(image, "alt_text", image_path)

            if self.expect_type(media_index, int, f"{image_path}.index"):
                if media_index < 1:
                    self.error(f"{image_path}.index", "must be at least 1", media_index)
                if media_index in seen_indexes:
                    self.error(f"{image_path}.index", "duplicate media index", media_index)
                seen_indexes.add(media_index)

            self.expect_url(source_url, f"{image_path}.source_url", nullable=True)
            self.expect_url(resolved_url, f"{image_path}.resolved_url", nullable=True)
            self.expect_url(thumbnail_url, f"{image_path}.thumbnail_url", nullable=True)
            self.expect_type(alt_text, str, f"{image_path}.alt_text", nullable=True)

            if check_duplicate_urls:
                self.check_duplicate_image_url(
                    source_url, f"{image_path}.source_url", seen_source_urls
                )
                self.check_duplicate_image_url(
                    resolved_url, f"{image_path}.resolved_url", seen_resolved_urls
                )

    def check_duplicate_image_url(
        self, value: Any, path: str, seen: dict[str, str]
    ) -> None:
        """Flag a gallery image URL already used by an earlier gallery image.

        Only non-empty string URLs are compared; ``null`` values are ignored so
        several images may legitimately leave a URL unset.
        """
        if not isinstance(value, str):
            return
        normalized = value.strip()
        if not normalized:
            return
        if normalized in seen:
            self.error(
                path,
                f"duplicate gallery image URL also used by {seen[normalized]}; "
                "each thumbnail must resolve to a distinct large image",
                normalized,
            )
        else:
            seen[normalized] = path

    def validate_video_list(self, value: Any, path: str) -> None:
        if not self.expect_type(value, list, path):
            return

        seen_indexes: set[int] = set()
        for index, video in enumerate(value):
            video_path = f"{path}[{index}]"
            if not self.expect_type(video, dict, video_path):
                continue

            media_index = self.require_key(video, "index", video_path)
            title = self.require_key(video, "title", video_path)
            source_url = self.require_key(video, "source_url", video_path)
            mp4_url = self.require_key(video, "mp4_url", video_path)
            hls_url = self.require_key(video, "hls_url", video_path)
            poster_url = self.require_key(video, "poster_url", video_path)

            if self.expect_type(media_index, int, f"{video_path}.index"):
                if media_index < 1:
                    self.error(f"{video_path}.index", "must be at least 1", media_index)
                if media_index in seen_indexes:
                    self.error(f"{video_path}.index", "duplicate media index", media_index)
                seen_indexes.add(media_index)

            self.expect_type(title, str, f"{video_path}.title", nullable=True)
            self.expect_url(source_url, f"{video_path}.source_url", nullable=True)
            self.expect_url(mp4_url, f"{video_path}.mp4_url", nullable=True)
            self.expect_url(hls_url, f"{video_path}.hls_url", nullable=True)
            self.expect_url(poster_url, f"{video_path}.poster_url", nullable=True)

    def validate_color_swatches(self, value: Any, path: str) -> None:
        if not self.expect_type(value, list, path):
            return
        if not value:
            self.error(path, "must contain at least one color swatch")
            return

        seen_asins: set[str] = set()
        for index, swatch in enumerate(value):
            swatch_path = f"{path}[{index}]"
            if not self.expect_type(swatch, dict, swatch_path):
                continue

            name = self.require_key(swatch, "name", swatch_path)
            asin = self.require_key(swatch, "asin", swatch_path)
            product_url = self.require_key(swatch, "product_url", swatch_path)
            swatch_image_url = self.require_key(swatch, "swatch_image_url", swatch_path)
            availability = self.require_key(swatch, "availability", swatch_path)
            base_price = self.require_key(swatch, "base_price", swatch_path)
            product_attributes = self.require_key(swatch, "product_attributes", swatch_path)
            customization_types = self.require_key(swatch, "customization_types", swatch_path)

            self.expect_non_empty_string(name, f"{swatch_path}.name", nullable=True)

            if self.expect_non_empty_string(asin, f"{swatch_path}.asin", nullable=True):
                if not ASIN_PATTERN.fullmatch(asin):
                    self.error(
                        f"{swatch_path}.asin",
                        "expected a 10-character uppercase Amazon ASIN",
                        asin,
                    )
                if asin in seen_asins:
                    self.error(f"{swatch_path}.asin", "duplicate swatch ASIN", asin)
                seen_asins.add(asin)

            self.expect_url(product_url, f"{swatch_path}.product_url", nullable=True)
            self.expect_url(swatch_image_url, f"{swatch_path}.swatch_image_url", nullable=True)
            self.expect_type(availability, bool, f"{swatch_path}.availability", nullable=True)
            self.validate_money(base_price, f"{swatch_path}.base_price")
            self.validate_product_attributes(
                product_attributes,
                f"{swatch_path}.product_attributes",
            )
            self.validate_customization_types(
                customization_types,
                f"{swatch_path}.customization_types",
            )

    def validate_customization_types(self, value: Any, path: str) -> None:
        if not self.expect_type(value, list, path):
            return

        seen_type_names: set[str] = set()
        for index, customization in enumerate(value):
            custom_path = f"{path}[{index}]"
            if not self.expect_type(customization, dict, custom_path):
                continue

            type_name = self.require_key(customization, "type", custom_path)
            options = self.require_key(customization, "options", custom_path)

            if self.expect_non_empty_string(type_name, f"{custom_path}.type"):
                folded = type_name.casefold().strip()
                if folded in seen_type_names:
                    self.error(f"{custom_path}.type", "duplicate customization type", type_name)
                seen_type_names.add(folded)

            self.validate_customization_options(options, f"{custom_path}.options")

    def validate_customization_options(self, value: Any, path: str) -> None:
        if not self.expect_type(value, list, path):
            return

        seen_values: set[str] = set()
        for index, option in enumerate(value):
            option_path = f"{path}[{index}]"
            if not self.expect_type(option, dict, option_path):
                continue

            option_value = self.require_key(option, "value", option_path)
            increase_amount = self.require_key(option, "increase_amount", option_path)

            if self.expect_non_empty_string(option_value, f"{option_path}.value", nullable=True):
                folded = option_value.casefold().strip()
                if folded in seen_values:
                    self.error(f"{option_path}.value", "duplicate option value", option_value)
                seen_values.add(folded)

            self.validate_increase_amount(
                increase_amount, f"{option_path}.increase_amount"
            )

            for optional_boolean in ("available", "disabled", "selected", "is_default"):
                if optional_boolean in option:
                    self.expect_type(
                        option[optional_boolean],
                        bool,
                        f"{option_path}.{optional_boolean}",
                        nullable=True,
                    )

    def validate_increase_amount(self, value: Any, path: str) -> None:
        """Validate a customization surcharge.

        ``crawl.md`` documents ``increase_amount`` as ``string | null`` (for
        example ``"$850.00"``), and ``json_to_shopify_csv.py`` accepts either a
        number or a currency-formatted string. This mirrors that contract:
        ``null``/empty means no surcharge, numbers must be non-negative, and a
        string must parse to a non-negative amount after currency formatting is
        removed.
        """
        if value is None:
            return

        if isinstance(value, bool):
            self.error(path, "expected a number or currency string, got boolean", value)
            return

        if isinstance(value, (int, float)):
            if value < 0:
                self.error(path, "must be greater than or equal to 0", value)
            return

        if not isinstance(value, str):
            self.error(
                path,
                f"expected string, number or null, got {type(value).__name__}",
                value,
            )
            return

        raw = value.strip()
        if not raw:
            # An empty string is treated as "no surcharge" by the converter.
            return

        normalized = re.sub(r"(?i)\bUSD\b", "", raw)
        normalized = (
            normalized.replace("$", "")
            .replace(",", "")
            .replace("[", "")
            .replace("]", "")
            .strip()
        )
        try:
            amount = float(normalized)
        except ValueError:
            self.error(
                path,
                "string must be a currency amount such as \"$850.00\"",
                value,
            )
            return
        if amount < 0:
            self.error(path, "must be greater than or equal to 0", value)

    def validate_extra_fields(self, value: Any, path: str) -> None:
        if not self.expect_type(value, dict, path):
            return

        seo_product_title = self.require_key(value, "seo_product_title", path)
        page_title = self.require_key(value, "page_title", path)
        meta_description = self.require_key(value, "meta_description", path)
        url_slug = self.require_key(value, "url_slug", path)

        self.expect_non_empty_string(seo_product_title, f"{path}.seo_product_title")

        if self.expect_non_empty_string(page_title, f"{path}.page_title"):
            if not 50 <= len(page_title) <= 60:
                self.error(
                    f"{path}.page_title",
                    "must contain 50 to 60 characters",
                    f"{len(page_title)} characters",
                )

        if self.expect_non_empty_string(meta_description, f"{path}.meta_description"):
            if not 150 <= len(meta_description) <= 160:
                self.error(
                    f"{path}.meta_description",
                    "must contain 150 to 160 characters",
                    f"{len(meta_description)} characters",
                )

        if self.expect_non_empty_string(url_slug, f"{path}.url_slug"):
            if not 50 <= len(url_slug) <= 60:
                self.error(
                    f"{path}.url_slug",
                    "must contain 50 to 60 characters",
                    f"{len(url_slug)} characters",
                )
            if not SLUG_PATTERN.fullmatch(url_slug):
                self.error(
                    f"{path}.url_slug",
                    "must use lowercase letters, digits, and single hyphens only",
                    url_slug,
                )

    def validate_string_list(self, value: Any, path: str) -> None:
        if not self.expect_type(value, list, path):
            return
        for index, item in enumerate(value):
            self.expect_type(item, str, f"{path}[{index}]")


def discover_json_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path] if input_path.suffix.lower() == ".json" else []
    if input_path.is_dir():
        # Skip timestamped backups and debug folders so a re-run does not
        # validate the intermediate files produced by the other scripts.
        return sorted(
            path
            for path in input_path.rglob("*.json")
            if path.is_file()
            and ".backup-" not in path.name
            and not path.name.startswith(".")
            and "debug" not in {part.lower() for part in path.parts}
        )
    return []


def validate_file(path: Path) -> tuple[bool, list[ValidationIssue]]:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return False, [ValidationIssue("$", f"file not found: {path}")]
    except PermissionError:
        return False, [ValidationIssue("$", f"permission denied: {path}")]
    except UnicodeDecodeError as exc:
        return False, [ValidationIssue("$", f"file is not valid UTF-8: {exc}")]
    except json.JSONDecodeError as exc:
        json_path = f"$ (line {exc.lineno}, column {exc.colno})"
        return False, [ValidationIssue(json_path, f"invalid JSON syntax: {exc.msg}")]

    validator = CrawlJsonValidator()
    issues = validator.validate(data)
    return not issues, issues


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate WRYDECO Amazon crawl JSON schema and SEO fields."
    )
    parser.add_argument(
        "input",
        type=Path,
        nargs="?",
        default=None,
        help=(
            "A crawl JSON file or a directory containing JSON files "
            f"(default: the ./{DEFAULT_INPUT} folder next to this script)."
        ),
    )
    return parser.parse_args()


def resolve_input_path(raw_input: Path | None) -> Path:
    """Resolve the CLI input, defaulting to the script's ./data folder.

    When no argument is given, ``./data`` next to this script is used so the
    validator runs plug-and-play regardless of the current working directory.
    """
    if raw_input is not None:
        return raw_input.expanduser().resolve()
    return (SCRIPT_DIR / DEFAULT_INPUT).resolve()


def main() -> int:
    args = parse_args()
    input_path = resolve_input_path(args.input)

    if not input_path.exists():
        print(f"ERROR: input path does not exist: {input_path}", file=sys.stderr)
        return 2

    json_files = discover_json_files(input_path)

    if not json_files:
        print(f"ERROR: no JSON files found at {input_path}", file=sys.stderr)
        return 2

    invalid_count = 0
    for path in json_files:
        valid, issues = validate_file(path)
        if valid:
            print(f"PASS: {path}")
            continue

        invalid_count += 1
        print(f"FAIL: {path}")
        for issue in issues:
            print(f"  - {issue.render()}")

    if invalid_count:
        print(
            f"\nValidation failed: {invalid_count}/{len(json_files)} file(s) invalid.",
            file=sys.stderr,
        )
        return 1

    print(f"\nValidation passed: {len(json_files)} file(s) valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
