from __future__ import annotations

import html
from decimal import Decimal
from typing import Any

from .errors import PriceValidationError
from .manifest import ProductJob
from .pricing import infer_wood_finish_deltas, money, normalize_name


def _product_settings(job: ProductJob) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "status": "ACTIVE", "vendor": "Wrydeco", "tags": ["source_amazon"],
        "product_type": "", "metafields": [], "publication_ids": [],
        "channels": ["Online Store", "Point of Sale", "Inbox"],
        "author_info": "gid://shopify/Metaobject/195646947385",
        "product_material": "wood", "wood_type": "wood", "bought_amount": 12,
    }
    defaults.update(job.overrides)
    if isinstance(defaults.get("tags"), str):
        defaults["tags"] = [item.strip() for item in defaults["tags"].split(",") if item.strip()]
    if isinstance(defaults.get("channels"), str):
        defaults["channels"] = [item.strip() for item in defaults["channels"].split(",") if item.strip()]
    return defaults


def _metafields_for_product(snapshot: dict[str, Any], content: dict[str, str], job: ProductJob,
                            settings: dict[str, Any], definitions: dict[tuple[str, str], str] | None = None,
                            rich_description: str = "") -> list[dict[str, str]]:
    existing = {(item.get("namespace"), item.get("key")): item
                for item in (snapshot.get("metafields") or {}).get("nodes", [])}
    generated: dict[tuple[str, str], dict[str, str]] = {}
    values: dict[str, tuple[Any, str]] = {
        "seo_product_title": (content["seo_product_title"], "single_line_text_field"),
        "amazon_link": (job.amazon_url, "url"),
        "rich_description": (rich_description or '<div class="description-root"></div>', "multi_line_text_field"),
    }
    for key, default_type in (("author_info", "metaobject_reference"), ("product_material", "single_line_text_field"),
                              ("wood_type", "single_line_text_field"), ("bought_amount", "number_integer")):
        if settings.get(key) is not None:
            values[key] = (settings[key], default_type)
    for key, (value, default_type) in values.items():
        matched = next((item for (namespace, existing_key), item in existing.items() if existing_key == key), None)
        definition = None
        if definitions:
            definition = (("custom", key), definitions.get(("custom", key)))
            if not definition[1]:
                definition = next((item for item in definitions.items() if item[0][1] == key), None)
        namespace = (matched.get("namespace", "custom") if matched else
                     (definition[0][0] if definition else "custom"))
        field_type = (matched.get("type", default_type) if matched else
                      (definition[1] if definition else default_type))
        generated[(namespace, key)] = {"namespace": namespace, "key": key, "type": field_type, "value": str(value)}
    for item in settings.get("metafields", []):
        normalized = dict(item)
        normalized.setdefault("namespace", "custom")
        generated[(normalized["namespace"], normalized["key"])] = normalized
    return list(generated.values())


def _build_rich_description(uploaded: list[dict[str, str]], title: str) -> str:
    escaped_alt = html.escape(title, quote=True)
    images = [
        f'<img alt="{escaped_alt}" src="https://via.placeholder.com/800" '
        f'data-src="{html.escape(item["url"], quote=True)}">'
        for item in uploaded
    ]
    return '<div class="description-root">' + " ".join(images) + "</div>"


def _build_final_variants(pricing: dict[str, Any], snapshot: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]], dict[str, str]]:
    variants = pricing.get("variants") or []
    if not variants:
        raise PriceValidationError("No price-verified variants are available.")
    option_names = [str(item["name"]) for item in (pricing.get("option_types") or [])]
    if not option_names:
        option_names = [item["name"] for item in variants[0]["options"]]
    wood_option = next((item for item in snapshot.get("options", []) if normalize_name(item.get("name")) == "wood finish"), None)
    wood_deltas: dict[str, Decimal] = {}
    if wood_option:
        if len(option_names) + 1 > 3:
            raise PriceValidationError("Amazon options plus existing Wood Finish exceed Shopify's three-option limit.")
        wood_deltas = infer_wood_finish_deltas((snapshot.get("variants") or {}).get("nodes", []))
        option_names.append(wood_option["name"])
    final: list[dict[str, Any]] = []
    for variant in variants:
        base = money(variant.get("verified_total", money(pricing["base_price"]) + money(variant["additional_price"])))
        if wood_deltas:
            for finish, delta in wood_deltas.items():
                final.append({"options": [*variant["options"], {"name": wood_option["name"], "value": finish}],
                              "price": money(base + delta)})
        else:
            final.append({"options": variant["options"], "price": base})
    keys = [tuple((item["name"], item["value"]) for item in variant["options"]) for variant in final]
    if len(keys) != len(set(keys)):
        raise PriceValidationError("Duplicate final Shopify variant combinations were produced.")
    return option_names, final, {key: str(value) for key, value in wood_deltas.items()}
