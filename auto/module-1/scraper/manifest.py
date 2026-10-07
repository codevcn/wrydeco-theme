from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .errors import ManifestError
from .io_utils import load_json


ASIN_RE = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:[/?]|$)", re.IGNORECASE)


@dataclass(frozen=True)
class ProductJob:
    amazon_url: str
    shopify_product_id: str
    asin: str
    mode: str
    preset: dict[str, str] | None
    overrides: dict[str, Any]


@dataclass(frozen=True)
class Manifest:
    path: Path
    products: tuple[ProductJob, ...]
    digest: str


def extract_asin(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ManifestError(f"Invalid Amazon URL: {url!r}")
    if parsed.hostname != "amazon.com" and not parsed.hostname.endswith(".amazon.com"):
        raise ManifestError(f"URL is not an amazon.com product URL: {url!r}")
    match = ASIN_RE.search(parsed.path)
    if not match:
        raise ManifestError(f"Could not extract a 10-character ASIN from: {url!r}")
    return match.group(1).upper()


def parse_manifest_payload(payload: Any, path: Path) -> Manifest:
    path = path.resolve()
    if not isinstance(payload, dict) or not isinstance(payload.get("products"), list):
        raise ManifestError("Manifest root must contain a products array.")
    jobs: list[ProductJob] = []
    seen_asins: set[str] = set()
    seen_products: set[str] = set()
    for index, item in enumerate(payload["products"]):
        if not isinstance(item, dict):
            raise ManifestError(f"products[{index}] must be an object.")
        amazon_url = str(item.get("amazon_url", "")).strip()
        product_id = str(item.get("shopify_product_id", "")).strip()
        if not product_id.isdigit():
            raise ManifestError(f"products[{index}].shopify_product_id must be numeric.")
        asin = extract_asin(amazon_url)
        if asin in seen_asins or product_id in seen_products:
            raise ManifestError(f"Duplicate ASIN or Shopify product ID at products[{index}].")
        seen_asins.add(asin)
        seen_products.add(product_id)
        mode = str(item.get("mode", "auto")).strip().lower()
        if mode not in {"auto", "dynamic", "preset"}:
            raise ManifestError(f"products[{index}].mode must be auto, dynamic, or preset.")
        preset = item.get("preset")
        if mode == "preset" and not isinstance(preset, dict):
            raise ManifestError(f"products[{index}].preset is required in preset mode.")
        if preset is not None:
            if not isinstance(preset, dict):
                raise ManifestError(f"products[{index}].preset is required in preset mode.")
            if not preset.get("furniture_type") or not preset.get("price_tier"):
                raise ManifestError(f"products[{index}].preset is incomplete.")
        overrides = item.get("overrides") or {}
        if not isinstance(overrides, dict):
            raise ManifestError(f"products[{index}].overrides must be an object.")
        jobs.append(ProductJob(amazon_url, product_id, asin, mode, preset, overrides))
    if not jobs:
        raise ManifestError("Manifest contains no products.")
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return Manifest(path, tuple(jobs), hashlib.sha256(canonical).hexdigest()[:12])


def load_manifest(path: Path) -> Manifest:
    path = path.resolve()
    return parse_manifest_payload(load_json(path), path)
