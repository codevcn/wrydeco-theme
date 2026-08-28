import csv
import json
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path


DEFAULT_CONFIG_PATH = Path(__file__).with_name("update_config.json")
HANDLE_COLUMN = "Handle"
DEFAULT_UPDATE_FIELDS = {
    "Title": "Final H1 / Product Title",
    "SEO Title": "Final SEO Title",
    "SEO Description": "Final Meta Description",
}


def read_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return reader.fieldnames, list(reader)


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)


def clean(value):
    return str(value or "").strip()


def require_config(config):
    required = [
        "csv_file_path_to_update",
        "ref_seo_product_file_path",
    ]
    missing = [key for key in required if key not in config]
    if missing:
        raise ValueError(f"Missing required config field(s): {', '.join(missing)}")

    update_entire_csv = config.get("update_entire_csv", False)
    if not isinstance(update_entire_csv, bool):
        raise ValueError("update_entire_csv must be a boolean when provided.")
    if update_entire_csv:
        return []

    if "handles_in_csv_to_update" not in config:
        raise ValueError("Missing required config field(s): handles_in_csv_to_update")

    handles = config["handles_in_csv_to_update"]
    if not isinstance(handles, list):
        raise ValueError("handles_in_csv_to_update must be a list of product handles.")
    handles = [clean(handle) for handle in handles if clean(handle)]
    if not handles:
        raise ValueError("handles_in_csv_to_update is empty. Add at least one handle before running.")
    if len(handles) != len(set(handles)):
        raise ValueError("handles_in_csv_to_update contains duplicate handles.")

    return handles


def unique_handles_from_target(product_indexes):
    handles = list(product_indexes.keys())
    if not handles:
        raise ValueError("Target CSV does not contain any product handles.")
    return handles


def first_product_row_indexes(rows):
    indexes = {}
    for index, row in enumerate(rows):
        handle = clean(row.get(HANDLE_COLUMN))
        if handle and handle not in indexes:
            indexes[handle] = index
    return indexes


def index_seo_rows(rows):
    indexed = {}
    for row in rows:
        handle = clean(row.get(HANDLE_COLUMN))
        if handle:
            indexed[handle] = row
    return indexed


def validate_columns(product_fieldnames, seo_fieldnames, update_fields):
    missing_product_columns = [column for column in [HANDLE_COLUMN, *update_fields.keys()] if column not in product_fieldnames]
    missing_seo_columns = [column for column in [HANDLE_COLUMN, *update_fields.values()] if column not in seo_fieldnames]
    if missing_product_columns:
        raise ValueError(f"Target CSV missing column(s): {', '.join(missing_product_columns)}")
    if missing_seo_columns:
        raise ValueError(f"Reference seo-product CSV missing column(s): {', '.join(missing_seo_columns)}")


def build_report_rows(handles, product_rows, product_indexes, seo_by_handle, update_fields):
    report_rows = []
    for handle in handles:
        product_index = product_indexes[handle]
        product_row = product_rows[product_index]
        seo_row = seo_by_handle[handle]
        changed_fields = []
        for product_column, seo_column in update_fields.items():
            old_value = product_row.get(product_column, "")
            new_value = seo_row.get(seo_column, "")
            if old_value != new_value:
                changed_fields.append(product_column)
            report_rows.append(
                {
                    "Handle": handle,
                    "Product Row Number": product_index + 2,
                    "Field": product_column,
                    "Reference Field": seo_column,
                    "Old Value": old_value,
                    "New Value": new_value,
                    "Changed": "YES" if old_value != new_value else "NO",
                }
            )
        report_rows.append(
            {
                "Handle": handle,
                "Product Row Number": product_index + 2,
                "Field": "SUMMARY",
                "Reference Field": "",
                "Old Value": "",
                "New Value": "",
                "Changed": f"{len(changed_fields)} FIELD(S): {', '.join(changed_fields) if changed_fields else 'NONE'}",
            }
        )
    return report_rows


def apply_updates(rows, handles, product_indexes, seo_by_handle, update_fields):
    for handle in handles:
        product_row = rows[product_indexes[handle]]
        seo_row = seo_by_handle[handle]
        for product_column, seo_column in update_fields.items():
            product_row[product_column] = seo_row.get(seo_column, "")


def assert_only_allowed_changes(before_rows, after_rows, allowed_row_indexes, allowed_fields):
    allowed_fields = set(allowed_fields)
    allowed_row_indexes = set(allowed_row_indexes)
    unexpected = []
    for index, (before, after) in enumerate(zip(before_rows, after_rows)):
        for field, before_value in before.items():
            after_value = after.get(field, "")
            if before_value == after_value:
                continue
            if index in allowed_row_indexes and field in allowed_fields:
                continue
            unexpected.append(
                {
                    "Row Number": index + 2,
                    "Handle": after.get(HANDLE_COLUMN) or before.get(HANDLE_COLUMN),
                    "Field": field,
                    "Before": before_value,
                    "After": after_value,
                }
            )
    return unexpected


def make_subset_rows(rows, handles):
    handle_set = set(handles)
    return [row for row in rows if clean(row.get(HANDLE_COLUMN)) in handle_set]


def write_qa_report(path, qa):
    lines = [f"{key}: {value}" for key, value in qa.items()]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONFIG_PATH
    config = read_json(config_path)
    handles = require_config(config)
    update_entire_csv = config.get("update_entire_csv", False)

    csv_file_path = Path(config["csv_file_path_to_update"])
    seo_file_path = Path(config["ref_seo_product_file_path"])
    output_dir = Path(config.get("output_dir", "todo/SEO/update_outputs"))
    dry_run = bool(config.get("dry_run", True))
    update_fields = config.get("update_fields") or DEFAULT_UPDATE_FIELDS

    product_fieldnames, product_rows = read_csv(csv_file_path)
    seo_fieldnames, seo_rows = read_csv(seo_file_path)
    validate_columns(product_fieldnames, seo_fieldnames, update_fields)

    product_indexes = first_product_row_indexes(product_rows)
    seo_by_handle = index_seo_rows(seo_rows)
    if update_entire_csv:
        handles = unique_handles_from_target(product_indexes)

    missing_in_target = [handle for handle in handles if handle not in product_indexes]
    missing_in_ref = [handle for handle in handles if handle not in seo_by_handle]
    if missing_in_target or missing_in_ref:
        details = []
        if missing_in_target:
            details.append(f"Missing in target CSV: {', '.join(missing_in_target)}")
        if missing_in_ref:
            details.append(f"Missing in reference seo-product CSV: {', '.join(missing_in_ref)}")
        raise ValueError(" | ".join(details))

    before_rows = deepcopy(product_rows)
    report_rows = build_report_rows(handles, product_rows, product_indexes, seo_by_handle, update_fields)
    apply_updates(product_rows, handles, product_indexes, seo_by_handle, update_fields)

    allowed_indexes = [product_indexes[handle] for handle in handles]
    unexpected_changes = assert_only_allowed_changes(before_rows, product_rows, allowed_indexes, update_fields.keys())
    if unexpected_changes:
        unexpected_path = output_dir / "unexpected_changes.csv"
        write_csv(unexpected_path, list(unexpected_changes[0].keys()), unexpected_changes)
        raise ValueError(f"Unexpected non-whitelisted changes detected. See {unexpected_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scope = ("entire_csv_" if update_entire_csv else "handles_") + str(len(handles))
    run_dir = output_dir / f"{timestamp}_{scope}_{'dry_run' if dry_run else 'apply'}"
    report_path = run_dir / "update_report.csv"
    qa_path = run_dir / "qa_report.txt"
    import_csv_path = run_dir / "shopify_import.csv"

    write_csv(report_path, list(report_rows[0].keys()), report_rows)
    write_csv(import_csv_path, product_fieldnames, make_subset_rows(product_rows, handles))

    if not dry_run:
        write_csv(csv_file_path, product_fieldnames, product_rows)

    qa = {
        "config": config_path,
        "target_csv": csv_file_path,
        "reference_seo_product_csv": seo_file_path,
        "dry_run": dry_run,
        "update_entire_csv": update_entire_csv,
        "requested_handles": len(handles),
        "target_rows_total": len(product_rows),
        "import_rows_for_requested_handles": len(make_subset_rows(product_rows, handles)),
        "fields_updated": ", ".join(update_fields.keys()),
        "product_type_changed": "NO",
        "body_html_changed": "NO",
        "unexpected_non_whitelisted_changes": len(unexpected_changes),
        "update_report": report_path,
        "shopify_import_csv": import_csv_path,
    }
    write_qa_report(qa_path, qa)

    print(f"Mode: {'DRY RUN' if dry_run else 'APPLY'}")
    print(f"Update entire CSV: {'YES' if update_entire_csv else 'NO'}")
    print(f"Handles: {len(handles)}")
    print(f"Fields updated: {', '.join(update_fields.keys())}")
    print("Product Type changed: NO")
    print("Body (HTML) changed: NO")
    print(f"Update report: {report_path}")
    print(f"Shopify import CSV: {import_csv_path}")
    print(f"QA report: {qa_path}")
    if dry_run:
        print("No changes were written to the target CSV because dry_run is true.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
