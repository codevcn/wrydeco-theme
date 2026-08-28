import csv
import hashlib
import html
import re
from pathlib import Path


PRODUCT_EXPORT = Path("todo/SEO/products_export_1.csv")
SEO_PRODUCT = Path("todo/TAM/results/seo-product.csv")
REPORT = Path("todo/SEO/products_duplicate_description_rewrite_report.csv")

DESC_COLUMN = "Body (HTML)"


STOPWORDS = {
    "and",
    "the",
    "for",
    "with",
    "wood",
    "wooden",
    "solid",
    "natural",
    "handcrafted",
    "handmade",
    "custom",
    "unique",
    "premium",
    "product",
    "branch",
    "tree",
}


def clean_space(value=""):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def strip_html(value=""):
    text = re.sub(r"<script[\s\S]*?</script>", " ", str(value or ""), flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return clean_space(text)


def normalize_body(value=""):
    return clean_space(value).replace("\ufeff", "")


def digest(value):
    return hashlib.sha1(normalize_body(value).encode("utf-8")).hexdigest()[:12]


def words(value):
    return [
        token
        for token in re.findall(r"[a-z0-9]+", str(value or "").lower())
        if len(token) >= 3 and token not in STOPWORDS
    ]


def product_rows_by_handle(rows):
    products = {}
    for index, row in enumerate(rows):
        handle = clean_space(row.get("Handle"))
        if not handle:
            continue
        if handle not in products:
            products[handle] = {
                "first_row_index": index,
                "handle": handle,
                "title": clean_space(row.get("Title")),
                "type": clean_space(row.get("Type")),
                "category": clean_space(row.get("Product Category")),
                "tags": clean_space(row.get("Tags")),
                "seo_title": clean_space(row.get("SEO Title")),
                "seo_description": clean_space(row.get("SEO Description")),
                "body": "",
                "body_row_indexes": [],
            }
        body = row.get(DESC_COLUMN) or ""
        if body.strip():
            products[handle]["body_row_indexes"].append(index)
            if not products[handle]["body"]:
                products[handle]["body"] = body
    return products


def load_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return reader.fieldnames, list(reader)


def group_duplicate_bodies(products):
    groups = {}
    for product in products.values():
        body = normalize_body(product["body"])
        if not body:
            continue
        groups.setdefault(digest(body), []).append(product)
    duplicate_groups = [group for group in groups.values() if len(group) > 1]
    duplicate_groups.sort(key=lambda group: (-len(group), group[0]["handle"]))
    return duplicate_groups


def keeper_score(product, group_body):
    body_text = strip_html(group_body).lower()
    data_text = " ".join(
        [
            product["title"],
            product["handle"].replace("-", " "),
            product["type"],
            product["category"],
            product["tags"],
            product["seo_title"],
            product["seo_description"],
        ]
    )
    tokens = set(words(data_text))
    score = sum(1 for token in tokens if token in body_text)
    title = product["title"].lower()
    if title and title in body_text:
        score += 20
    handle_words = product["handle"].replace("-", " ").lower()
    if handle_words and handle_words in body_text:
        score += 8
    return score


def choose_keeper(group):
    group_body = group[0]["body"]
    return max(
        group,
        key=lambda product: (
            keeper_score(product, group_body),
            -product["first_row_index"],
        ),
    )


def text_or_na(value):
    value = clean_space(value)
    return value if value else ""


def safe_intro(value):
    intro = clean_space(value)
    replacements = {
        "wood wood furniture": "wood furniture",
        "wood wood floor sculpture": "wood floor sculpture",
        "wood wood display shelf": "wood display shelf",
        "wood wood bookshelf": "wood bookshelf",
        "wood wood bookcase": "wood bookcase",
        "wood wood wine rack": "wood wine rack",
        "wood wood accent table": "wood accent table",
        "in a unused": "in an unused",
        "in a entryway": "in an entryway",
    }
    for old, new in replacements.items():
        intro = re.sub(re.escape(old), new, intro, flags=re.I)
    return intro


def material_note(product, seo):
    source = " ".join([product["title"], product["handle"], seo.get("Final Intro Description", "")]).lower()
    if "solid oak" in source:
        return "Solid oak wood is referenced in the current product data."
    if "oak wood" in source:
        return "Oak wood is referenced in the current product data."
    if "live edge" in source:
        return "Live-edge wood character is referenced in the current product data."
    if "driftwood" in source:
        return "Driftwood-style wood character is referenced in the current product data."
    if "natural wood" in source:
        return "Natural wood character is referenced in the current product data."
    if "solid wood" in source:
        return "Solid wood is referenced in the current product data."
    return ""


def placement_note(product, seo):
    source = " ".join([product["title"], product["handle"], seo.get("Final H1 / Product Title", "")]).lower()
    if "wall-mounted" in source or "wall mounted" in source or "floating" in source:
        return (
            "Plan the wall span, shelf projection, and installation requirements before ordering. "
            "Do not assume mounting hardware, wall compatibility, or load capacity unless those details are confirmed for the exact product."
        )
    if "corner" in source:
        return (
            "Measure both walls of the corner, nearby trim, outlets, and walking clearance before choosing a size. "
            "Confirm the final installation requirements for the exact product."
        )
    if "bed" in source or "headboard" in source:
        return (
            "Compare the listed size options with the bedroom layout, mattress plan, access path, and assembly requirements before ordering."
        )
    if "wine rack" in source:
        return (
            "Check the listed dimensions, mounting type, bottle clearance, and glass-holder clearance before choosing a configuration."
        )
    if "coffee table" in source or "end table" in source or "nightstand" in source:
        return (
            "Compare the listed dimensions with sofa height, walking clearance, and the room's seating layout before ordering."
        )
    if "floor sculpture" in source:
        return (
            "Review the listed height, footprint, sight lines, and placement conditions before choosing a display location."
        )
    return "Use the listed dimensions, available finish options, and product gallery to confirm fit before ordering."


def split_values(value):
    return [clean_space(part) for part in str(value or "").split(";") if clean_space(part)]


def build_description(product, seo):
    final_title = clean_space(seo.get("Final H1 / Product Title")) or product["title"]
    intro = safe_intro(seo.get("Final Intro Description") or "")
    differentiator = clean_space(seo.get("Verified Differentiator"))
    sizes = split_values(seo.get("Size Options"))
    finishes = split_values(seo.get("Finish Options"))
    material = material_note(product, seo)
    placement = placement_note(product, seo)
    missing = split_values(seo.get("Missing Facts Before Full PDP Rewrite"))

    details = []
    if differentiator:
        details.append(("Design focus", differentiator))
    if material:
        details.append(("Material note", material))
    if sizes:
        details.append(("Available sizes", "; ".join(sizes)))
    if finishes:
        details.append(("Available finishes", "; ".join(finishes)))
    if product["type"]:
        details.append(("Product type", product["type"]))

    detail_items = "\n".join(
        f"    <li><strong>{html.escape(label)}:</strong> {html.escape(value)}</li>" for label, value in details
    )
    if not detail_items:
        detail_items = (
            "    <li>Use the product title, listed options, and gallery to confirm the exact design before ordering.</li>"
        )

    verification = ""
    if missing:
        readable = ", ".join(missing)
        verification = (
            "\n  <h2>Before You Order</h2>\n"
            f"  <p>For final purchase decisions, confirm product-specific details such as {html.escape(readable)} through the latest Wrydeco product information or customer support. These details should not be assumed from imagery alone.</p>"
        )

    return clean_space(
        f"""
<div class="wrydeco-product-description">
  <p>{html.escape(intro)}</p>
  <h2>Product Details</h2>
  <ul>
{detail_items}
  </ul>
  <h2>Planning Your Space</h2>
  <p>{html.escape(placement)}</p>{verification}
</div>
"""
    )


def main():
    fieldnames, rows = load_csv(PRODUCT_EXPORT)
    seo_fieldnames, seo_rows = load_csv(SEO_PRODUCT)
    if DESC_COLUMN not in fieldnames:
        raise SystemExit(f"Missing required column: {DESC_COLUMN}")

    original_rows = [row.copy() for row in rows]
    products = product_rows_by_handle(rows)
    seo_by_handle = {clean_space(row.get("Handle")): row for row in seo_rows if clean_space(row.get("Handle"))}

    duplicate_groups = group_duplicate_bodies(products)
    report_rows = []
    changed_handles = []

    for group_index, group in enumerate(duplicate_groups, start=1):
        keeper = choose_keeper(group)
        for product in group:
            action = "KEEP_ORIGINAL" if product["handle"] == keeper["handle"] else "REWRITE_BODY_HTML"
            old_body = product["body"]
            new_body = old_body
            if action == "REWRITE_BODY_HTML":
                seo = seo_by_handle.get(product["handle"])
                if not seo:
                    raise SystemExit(f"Missing seo-product row for handle: {product['handle']}")
                new_body = build_description(product, seo)
                for row_index in product["body_row_indexes"]:
                    rows[row_index][DESC_COLUMN] = new_body
                changed_handles.append(product["handle"])

            report_rows.append(
                {
                    "Duplicate Group": f"DESC-{group_index:02d}",
                    "Action": action,
                    "Handle": product["handle"],
                    "Title": product["title"],
                    "Keeper Handle": keeper["handle"],
                    "Old Body Characters": len(old_body),
                    "New Body Characters": len(new_body),
                    "Body Row Indexes": "; ".join(str(index + 1) for index in product["body_row_indexes"]),
                }
            )

    for before, after in zip(original_rows, rows):
        for field in fieldnames:
            if field == DESC_COLUMN:
                continue
            if before.get(field) != after.get(field):
                raise SystemExit(f"Unexpected change outside {DESC_COLUMN}: {field}")

    with PRODUCT_EXPORT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)

    report_fieldnames = [
        "Duplicate Group",
        "Action",
        "Handle",
        "Title",
        "Keeper Handle",
        "Old Body Characters",
        "New Body Characters",
        "Body Row Indexes",
    ]
    with REPORT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=report_fieldnames, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(report_rows)

    _, updated_rows = load_csv(PRODUCT_EXPORT)
    updated_products = product_rows_by_handle(updated_rows)
    updated_duplicate_groups = group_duplicate_bodies(updated_products)

    print(f"Duplicate groups before: {len(duplicate_groups)}")
    print(f"Products in duplicate groups before: {sum(len(group) for group in duplicate_groups)}")
    print(f"Descriptions rewritten: {len(changed_handles)}")
    print(f"Duplicate groups after: {len(updated_duplicate_groups)}")
    print(f"Products in duplicate groups after: {sum(len(group) for group in updated_duplicate_groups)}")
    print(f"Report: {REPORT}")


if __name__ == "__main__":
    main()
