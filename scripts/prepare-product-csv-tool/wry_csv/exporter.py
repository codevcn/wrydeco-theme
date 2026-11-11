from __future__ import annotations

from collections import Counter
from copy import deepcopy
import csv
from datetime import datetime, timezone
from decimal import Decimal
from io import StringIO
from pathlib import Path
import re
from typing import Any

from .common import ROOT, TOOL, SHOP, Invalid, read_json, require, resolve_file, sha256, atomic_write
from .content import build_sku_plan, check_content, compare_content
from .media import inspect_local, verify_urls
from scraper.errors import ScraperError

STYLE = "Interior Style (product.metafields.custom.interior_style)"
ROOM = "Room Type (product.metafields.custom.room_type)"
MATERIAL = "Product Material (product.metafields.custom.product_material)"
AUTHOR = "Author Info (product.metafields.custom.author_info)"
SEO_PRODUCT = "SEO product title (product.metafields.custom.seo_product_title)"
AEO = "Product AEO HTML (product.metafields.custom.aeo_html)"
DEFAULT_PRODUCT_STATUS = "active"
DEFAULTS = {"Variant Grams": "0.0", "Variant Inventory Tracker": "", "Variant Inventory Qty": "0",
            "Variant Inventory Policy": "deny", "Variant Fulfillment Service": "manual",
            "Variant Requires Shipping": "true", "Variant Taxable": "true", "Variant Weight Unit": "kg"}
VARIANT_FIELDS = {*DEFAULTS, "Variant SKU", "Variant Price", "Variant Compare At Price", "Variant Barcodes",
                  "Variant Image", "Variant Tax Code", "Cost per item", "Variant Packed Length",
                  "Variant Packed Width", "Variant Packed Height", "Variant Packed Dimension Unit",
                  *(f"Option{i} Value" for i in range(1, 4)),
                  "Unit Price Total Measure", "Unit Price Total Measure Unit", "Unit Price Base Measure", "Unit Price Base Measure Unit"}
IMAGE_FIELDS = {"Image Src", "Image Position", "Image Alt Text"}
STYLES = {"Rustic", "Japandi", "Mid-Century", "Organic Modern"}
ROOMS = {"Living Room", "Bedroom", "Kitchen & Dining", "Home Office & Library", "Nursery & Kids' Room", "Entryway & Hallway", "Bathroom"}
SKU_RE = re.compile(r"(?:AMZ|WRY)-[A-Z0-9][A-Z0-9-]*-\d{2}", re.I)


def template_headers(template: Path) -> list[str]:
    require(template.is_file(), f"Canonical template missing: {template}")
    with template.open(encoding="utf-8-sig", newline="") as stream:
        headers = next(csv.reader(stream), [])
    expected = read_json(TOOL / "native_contract.json")["headers"]
    require(headers == expected, "Template schema drift: expected the approved 71 headers in exact order; review native_contract.json")
    return headers


def money(value: Any, label: str, zero: bool = False) -> str:
    require(isinstance(value, str) and bool(re.fullmatch(r"\d+(?:\.\d{1,2})?", value)),
            f"{label}: use exact plain decimal string with at most 2 fractional digits")
    amount = Decimal(value)
    require(amount.is_finite() and (amount >= 0 if zero else amount > 0), f"{label}: price must be positive")
    return format(amount, "f")


def string_list(value: Any, choices: set[str], label: str) -> list[str]:
    require(isinstance(value, list) and value and all(isinstance(v, str) and v in choices for v in value),
            f"{label}: nonempty array of exact approved choices required")
    require(len(value) == len(set(value)), f"{label}: duplicate choice")
    return value


def load_manifest(path: Path) -> dict:
    manifest = read_json(path)
    require(manifest.get("version") == 1 and manifest.get("shop") == SHOP, "Manifest version/shop mismatch")
    require(manifest.get("currency") == "USD", "This tool's price precision contract currently supports verified USD only")
    require(isinstance(manifest.get("products"), list) and manifest["products"], "Manifest needs products")
    require(set(manifest) == {"version", "shop", "currency", "products"}, "Manifest contains missing/unknown top-level keys")
    return manifest


def snapshot_check(snapshot: dict, manifest: dict) -> None:
    require(snapshot.get("shop") == SHOP and snapshot.get("currency") == manifest["currency"], "Store/currency snapshot mismatch")
    collected = datetime.fromisoformat(snapshot["collected_at"])
    require(collected.tzinfo is not None, "Store snapshot timestamp needs timezone")
    age = (datetime.now(timezone.utc) - collected).total_seconds()
    require(-300 <= age <= 86400, "Store snapshot is stale; run snapshot again (24 hour limit)")
    for key in ("interior_style", "room_type"):
        definition = snapshot["definitions"].get(key, {})
        require(definition.get("type") == "list.single_line_text_field" and definition.get("choices"),
                f"Snapshot needs current list choices for custom.{key}")
    require(snapshot["definitions"].get("product_material", {}).get("type") == "single_line_text_field",
            "Snapshot custom.product_material must be single_line_text_field")
    for key, field_type in (("author_info", "metaobject_reference"), ("aeo_html", "multi_line_text_field"),
                            ("wood_type", "single_line_text_field"), ("seo_product_title", "single_line_text_field")):
        require(snapshot["definitions"].get(key, {}).get("type") == field_type,
                f"Snapshot custom.{key} has an incompatible/missing definition")


def collection_check(product: dict, snapshot: dict) -> None:
    matches = [c for c in snapshot["collections"] if c["handle"] == product["collection"]]
    require(len(matches) == 1 and matches[0].get("ruleSet"), f"{product['id']}: target must be an existing smart collection")
    rule_set = matches[0]["ruleSet"]
    results = []
    for rule in rule_set["rules"]:
        column, relation, condition = rule["column"], rule["relation"], rule["condition"]
        if column in {"TYPE", "TAG"} and relation == "EQUALS":
            results.append(product["type"] == condition if column == "TYPE" else condition in product["tags"])
        elif column == "VARIANT_PRICE" and relation in {"GREATER_THAN", "LESS_THAN", "EQUALS"}:
            threshold = Decimal(condition)
            prices = [Decimal(v["price"]) for v in product["variants"]]
            # Shopify smart collections match when any variant satisfies the rule.
            results.append(any(p > threshold if relation == "GREATER_THAN" else p < threshold
                               if relation == "LESS_THAN" else p == threshold for p in prices))
        else:
            raise Invalid(f"{product['id']}: unsupported collection rule {column}/{relation}; resolve before build")
    require(results and (any(results) if rule_set["appliedDisjunctively"] else all(results)),
            f"{product['id']}: Type/Tags/prices do not satisfy target collection")


def prepare(manifest: dict, base: Path, snapshot: dict, checkpoint: dict | None = None,
            history: Path | None = None, require_urls: bool = False, prior_reports: list[Path] = ()) -> tuple[list[dict], dict]:
    snapshot_check(snapshot, manifest)
    products = deepcopy(manifest["products"])
    errors, content_reports, ids, handles = [], [], set(), set()
    occupied = {s.casefold() for s in snapshot.get("occupied_skus", [])}
    existing_handles = set(snapshot.get("occupied_handles", []))
    image_cache = {}
    for product in products:
        pid = product.get("id", "<missing id>")
        try:
            require(set(product) <= {"id", "handle", "approved_handle", "approved_artwork_title", "collection", "category", "type", "tags", "author_handle", "material", "interior_style", "room_type", "evidence", "variants", "images", "content", "asin"},
                    "Unknown product keys; unsupported fields must not be silently dropped")
            require(isinstance(pid, str) and pid and pid not in ids, "Product IDs must be unique")
            ids.add(pid)
            handle = product["handle"]
            require(bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", handle)), "Handle must be ASCII kebab-case")
            require(handle not in handles and handle not in existing_handles, "Handle already exists in batch/store")
            handles.add(handle)
            require(product["category"] in snapshot["categories"], "Category breadcrumb was not verified against Shopify taxonomy")
            require(isinstance(product["tags"], list) and product["tags"] and
                    all(isinstance(t, str) and t.strip() == t and t and not re.search(r"[,\r\n]", t) for t in product["tags"]),
                    "Tags must be a nonempty array of individual tags")
            require(product["type"].strip(), "Product type required")
            require(product.get("material", "wood") == "wood", "Current approved material convention is wood")
            require(product["author_handle"] in {a["handle"] for a in snapshot["authors"]}, "Unknown author handle (do not use a GID)")
            string_list(product["interior_style"], set(snapshot["definitions"]["interior_style"]["choices"]) & STYLES, "Interior Style")
            string_list(product["room_type"], set(snapshot["definitions"]["room_type"]["choices"]) & ROOMS, "Room Type")
            require(product["interior_style"] in [["Rustic"], ["Japandi", "Mid-Century", "Organic Modern"]],
                    "Interior Style does not follow the branch-classification policy")
            variants = product["variants"]
            require(variants and len(variants) <= 99, "Need 1–99 variants for two-digit SKU indices")
            axes = [o["name"] for o in variants[0]["options"]]
            require(1 <= len(axes) <= 3 and len(axes) == len(set(axes)), "Need 1–3 distinct option axes")
            tuples = set()
            for i, variant in enumerate(variants):
                require([o["name"] for o in variant["options"]] == axes, f"Variant {i+1}: option axes/order changed")
                values = tuple(o["value"] for o in variant["options"])
                require(all(isinstance(v, str) and v.strip() == v and v and not re.search(r"[\r\n]", v) for v in [*axes, *values]),
                        "Option names/values must be nonempty plain strings")
                require(tuple(v.casefold() for v in values) not in tuples, "Duplicate option tuple")
                tuples.add(tuple(v.casefold() for v in values))
                variant["price"] = money(variant["price"], f"Variant {i+1}", zero=variant.get("zero_price_confirmed") is True)
                require(isinstance(variant.get("source_ref"), str) and variant["source_ref"].strip(), "Each variant needs its screenshot/row source_ref")
                require(set(variant) <= {"options", "price", "source_ref", "sku", "image_index", "zero_price_confirmed", "fields"}, "Unknown variant keys")
                overrides = variant.get("fields", {})
                require(set(overrides) <= VARIANT_FIELDS - {"Variant SKU", "Variant Price", "Variant Image"} - {f"Option{i} Value" for i in range(1,4)}, "Unknown/owned variant field override")
            collection_check(product, snapshot)
            images = product["images"]
            require(images and len(images) <= 250, "Need 1–250 gallery images")
            hashes, gallery_paths = set(), []
            for image in images:
                require(set(image) <= {"path", "alt", "url"}, "Unknown image keys")
                path = resolve_file(image["path"], base)
                require(isinstance(image["alt"], str) and 0 < len(image["alt"]) <= 512, "Image alt text required (max 512 chars)")
                info = image_cache.setdefault(str(path), None)
                if info is None:
                    info = image_cache[str(path)] = inspect_local(path)
                require(info["sha256"] not in hashes, "Duplicate gallery bytes; deduplicate input")
                hashes.add(info["sha256"])
                gallery_paths.append(image["path"])
                image["local"] = {"path": str(path), **info}
                record = (checkpoint or {}).get("files", {}).get(info["sha256"], {})
                if record:
                    require(record.get("shop") == SHOP and record.get("sha256") == info["sha256"], "Image checkpoint file/shop mismatch")
                    if record.get("state") == "ready":
                        require(bool(record.get("id")) and bool(record.get("url")), "READY checkpoint needs actual file ID and URL")
                        if image.get("url"):
                            require(image["url"] == record.get("url"), "Manifest image URL conflicts with checkpoint")
                        image["url"] = record["url"]
                    elif require_urls:
                        raise Invalid("Image checkpoint is not READY; resume stage")
                if require_urls:
                    require(image.get("url"), f"No real URL for {path.name}; run stage or supply verified public URL")
            actual, content_report = check_content(product, gallery_paths)
            product["content"] = actual
            content_reports.append(content_report)
            supplied = [v.get("sku") for v in variants]
            require(all(supplied) or not any(supplied), "Supply every SKU or let the tool generate all SKUs")
            previous = {"variants": [{"options": v["options"], "sku": v["sku"]} for v in variants]} if all(supplied) else None
            plan = build_sku_plan(variants, tags=product["tags"], asin=product.get("asin", ""), handle=handle,
                                  occupied=occupied, previous=previous)
            for variant, planned in zip(variants, plan["variants"]):
                if variant.get("sku"):
                    require(variant["sku"].casefold() == planned["sku"].casefold(), "Supplied SKU does not follow taxonomy or collides")
                code = planned["sku"].upper()
                require(18 <= len(code) <= 40 and SKU_RE.fullmatch(code), "SKU must use store taxonomy, 18–40 chars, two-digit index")
                variant["sku"] = code
                occupied.add(code.casefold())
                if variant.get("image_index") is not None:
                    require(type(variant["image_index"]) is int and 1 <= variant["image_index"] <= len(images), "Invalid variant image_index")
        except (KeyError, TypeError, ValueError, OSError, ScraperError) as exc:
            errors.append({"product": pid, "error": str(exc)})
    if errors:
        return [], {"valid": False, "errors": errors}
    comparisons = compare_content(products, content_reports, history, prior_reports)
    return products, {"valid": not comparisons["collisions"], "errors": [], "content": content_reports, **comparisons}


def render_rows(products: list[dict], headers: list[str]) -> list[dict[str, str]]:
    rows = []
    for product in products:
        content = product["content"]
        product_rows = []
        for i, variant in enumerate(product["variants"]):
            row = dict.fromkeys(headers, "")
            row.update(Handle=product["handle"])
            row.update(DEFAULTS)
            row.update(variant.get("fields", {}))
            require(all(isinstance(v, str) for v in row.values()), "Variant field overrides must be strings")
            row.update({"Variant SKU": variant["sku"], "Variant Price": variant["price"]})
            for axis, option in enumerate(variant["options"], 1):
                row[f"Option{axis} Value"] = option["value"]
                if i == 0:
                    row[f"Option{axis} Name"] = option["name"]
            if variant.get("image_index") is not None:
                row["Variant Image"] = product["images"][variant["image_index"] - 1].get("url", "")
            if i == 0:
                row.update({"Title": content["title"], "Body (HTML)": content["description_html"], "Vendor": "Wrydeco",
                            "Product Category": product["category"], "Type": product["type"], "Tags": ", ".join(product["tags"]),
                            "Published": "false", "Gift Card": "false", "Status": DEFAULT_PRODUCT_STATUS, "SEO Title": content["seo_title"],
                            "SEO Description": content["seo_description"], SEO_PRODUCT: content["seo_product_title"], AEO: content["aeo_html"],
                            STYLE: "\n".join(product["interior_style"]), ROOM: "\n".join(product["room_type"]),
                            MATERIAL: "wood", AUTHOR: product["author_handle"], "Wood Type (product.metafields.custom.wood_type)": "wood"})
            product_rows.append(row)
        for i, image in enumerate(product["images"]):
            if i >= len(product_rows):
                product_rows.append({**dict.fromkeys(headers, ""), "Handle": product["handle"]})
            product_rows[i].update({"Image Src": image.get("url", ""), "Image Position": str(i + 1), "Image Alt Text": image["alt"]})
        rows.extend(product_rows)
    return rows


def serialize(headers: list[str], rows: list[dict]) -> bytes:
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, headers, lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def verify_csv(path: Path, template: Path, *, expected: list[dict] | None = None,
               snapshot: dict | None = None, online: bool = True, fetcher=None) -> dict:
    headers = template_headers(template)
    errors = []
    def error(row, field, message):
        errors.append({"record": row, "field": field, "error": message})
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
        parsed = list(csv.reader(StringIO(text, newline=""), strict=True))
    except (UnicodeError, csv.Error) as exc:
        return {"valid": False, "ready_for_import": False, "errors": [{"error": str(exc)}]}
    if not parsed or parsed[0] != headers:
        actual = parsed[0] if parsed else []
        error(1, "headers", f"Expected exact 71-column template; got {len(actual)}. Missing: {sorted(set(headers)-set(actual))}; extra: {sorted(set(actual)-set(headers))}")
    if "\r" in text:
        error(0, "encoding", "Use LF line endings, including embedded lists")
    actual_headers = parsed[0] if parsed else []
    rows = []
    for i, cells in enumerate(parsed[1:], 2):
        if len(cells) != len(actual_headers):
            error(i, "columns", f"Expected {len(actual_headers)} cells, got {len(cells)}")
        rows.append(dict(zip(actual_headers, cells)))
    if not rows:
        error(0, "products", "CSV has no product rows")
    current, closed, axes, tuples, seen_skus, galleries, products, variants = None, set(), [], set(), set(), {}, 0, 0
    variant_counts = Counter()
    parent_fields = set(headers) - VARIANT_FIELDS - IMAGE_FIELDS - {"Handle"}
    for i, row in enumerate(rows, 2):
        get = lambda field: row.get(field, "")
        handle = get("Handle")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", handle):
            error(i, "Handle", "Missing or invalid handle")
        if handle != current:
            if current is not None:
                closed.add(current)
            if handle in closed:
                error(i, "Handle", "Product rows are not contiguous")
            current, tuples = handle, set()
            products += 1
            axes = [get(f"Option{n} Name") for n in range(1, 4)]
            if not axes[0] or any(axes[n] and not axes[n-1] for n in (1, 2)):
                error(i, "Options", "Option names must be contiguous from Option1")
            for field in ("Title", "Body (HTML)", "Vendor", "Product Category", "Type", "Tags", "SEO Title", "SEO Description", AEO, SEO_PRODUCT, AUTHOR):
                if not get(field).strip():
                    error(i, field, "Required product field is blank")
            for field, value in {"Published": "false", "Gift Card": "false", "Status": DEFAULT_PRODUCT_STATUS, MATERIAL: "wood"}.items():
                if get(field) != value:
                    error(i, field, f"Expected native WRYDECO default {value!r}")
            category = get("Product Category")
            if not category or category == "Uncategorized" or (snapshot and category not in snapshot["categories"]):
                error(i, "Product Category", "Missing or unverified taxonomy category")
            if get(AUTHOR).startswith("gid:") or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", get(AUTHOR)):
                error(i, AUTHOR, "Use an existing author handle, matching native template")
            if snapshot and get(AUTHOR) not in {a["handle"] for a in snapshot["authors"]}:
                error(i, AUTHOR, "Author does not exist in store snapshot")
            for field, choices, key in ((STYLE, STYLES, "interior_style"), (ROOM, ROOMS, "room_type")):
                values = get(field).split("\n")
                allowed = set(snapshot["definitions"][key]["choices"]) if snapshot else choices
                if not get(field) or get(field).startswith("[") or any(v not in allowed for v in values) or len(values) != len(set(values)):
                    error(i, field, "Use exact choices separated by real LF characters, not JSON or literal \\n")
        else:
            for field in parent_fields:
                if get(field):
                    error(i, field, "Product fields belong only on first product row")
        is_variant = any(get(f) for f in VARIANT_FIELDS)
        if is_variant:
            variants += 1
            variant_counts[handle] += 1
            for field in DEFAULTS:
                value = get(field)
                if field == "Variant Inventory Policy":
                    valid = value in {"deny", "continue"}
                elif field == "Variant Inventory Qty":
                    valid = bool(re.fullmatch(r"-?\d+", value))
                elif field == "Variant Grams":
                    valid = bool(re.fullmatch(r"\d+\.\d+", value))
                else:
                    valid = value == DEFAULTS[field]
                if not valid:
                    error(i, field, f"Invalid/missing native value; default {DEFAULTS[field]!r}")
            sku = get("Variant SKU")
            if not SKU_RE.fullmatch(sku) or not 18 <= len(sku) <= 40 or sku.casefold() in seen_skus:
                error(i, "Variant SKU", "Invalid taxonomy/length or duplicate SKU")
            seen_skus.add(sku.casefold())
            try:
                money(get("Variant Price"), "Variant Price", zero=True)
            except Invalid as exc:
                error(i, "Variant Price", str(exc))
            for field in ("Variant Compare At Price", "Cost per item"):
                if get(field):
                    try:
                        money(get(field), field, zero=True)
                    except Invalid as exc:
                        error(i, field, str(exc))
            for field in ("Variant Packed Length", "Variant Packed Width", "Variant Packed Height", "Unit Price Total Measure", "Unit Price Base Measure"):
                if get(field) and not re.fullmatch(r"\d+(?:\.\d+)?", get(field)):
                    error(i, field, "Use a nonnegative plain decimal")
            values = tuple(get(f"Option{n} Value") for n in range(1, 4))
            if any(bool(name) != bool(value) for name, value in zip(axes, values)) or values in tuples:
                error(i, "Options", "Missing/extra option values or duplicate tuple")
            tuples.add(values)
        elif set(k for k, v in row.items() if v) - IMAGE_FIELDS - {"Handle"}:
            error(i, "row", "Image-only rows may contain only Handle and image fields")
        if get("Image Src"):
            gallery = galleries.setdefault(handle, [])
            if get("Image Position") != str(len(gallery)+1) or get("Image Src") in gallery:
                error(i, "Image Position", "Gallery positions must be contiguous and URLs unique per product")
            gallery.append(get("Image Src"))
            if not 0 < len(get("Image Alt Text")) <= 512:
                error(i, "Image Alt Text", "Missing/overlong image alt")
        elif get("Image Position") or get("Image Alt Text"):
            error(i, "Image Src", "Image metadata without a URL")
    for i, row in enumerate(rows, 2):
        if row.get("Variant Image") and row["Variant Image"] not in galleries.get(row.get("Handle"), []):
            error(i, "Variant Image", "Variant image must be one of this product's gallery URLs")
    for handle in {r.get("Handle") for r in rows}:
        if handle not in galleries:
            error(0, "Image Src", f"Product {handle} has no gallery")
        if not variant_counts[handle]:
            error(0, "Variant SKU", f"Product {handle} has no complete variant")
    if expected is not None:
        if len(rows) != len(expected):
            error(0, "round_trip", "CSV record count differs from manifest plan")
        for i, (row, planned) in enumerate(zip(rows, expected), 2):
            for field in headers:
                if row.get(field, "") != planned[field]:
                    error(i, field, "Saved CSV differs from manifest plan")
    urls = [url for gallery in galleries.values() for url in gallery]
    media = verify_urls(urls, **({"fetcher": fetcher} if fetcher else {})) if online else {"checked": 0, "skipped": True, "errors": []}
    errors.extend({"record": 0, "field": "Image Src", **e} for e in media["errors"])
    return {"valid": not errors, "ready_for_import": not errors and online and expected is not None,
            "template_sha256": sha256(template.read_bytes()), "csv_sha256": sha256(raw),
            "columns": len(actual_headers), "products": products, "variants": variants,
            "images": sum(map(len, galleries.values())), "unique_images": len(set(urls)),
            "manifest_compared": expected is not None, "media": media, "errors": errors}


def build_csv(output: Path, products: list[dict], template: Path, snapshot: dict, fetcher=None) -> dict:
    headers = template_headers(template)
    rows = render_rows(products, headers)
    # Validate the actual serialized file before replacing a final output.
    candidate = output.with_name(output.name + ".candidate")
    require(not candidate.exists(), f"Unresolved candidate already exists: {candidate}")
    try:
        atomic_write(candidate, serialize(headers, rows))
        report = verify_csv(candidate, template, expected=rows, snapshot=snapshot, fetcher=fetcher)
        if report["ready_for_import"]:
            require(not output.exists(), f"Output already exists; choose a new output path: {output}")
            candidate.replace(output)
        return report
    finally:
        candidate.unlink(missing_ok=True)
