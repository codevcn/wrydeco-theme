#!/usr/bin/env python3
import csv
import sys
from pathlib import Path

KEEP_TAG = "except-inactive"
INACTIVE_STATUS = "draft"
ACTIVE_STATUS = "active"

def parse_tags(tags_text: str) -> set[str]:
    return {tag.strip() for tag in (tags_text or "").split(",") if tag.strip()}

def is_product_main_row(row: dict) -> bool:
    return any((row.get(col, "") or "").strip() for col in ("Title", "Tags", "Published", "Status"))

def set_products_inactive_except_tag(input_csv: str, output_csv: str | None = None) -> None:
    input_path = Path(input_csv)

    if output_csv is None:
        output_path = input_path.with_name(f"{input_path.stem}_inactive_except{input_path.suffix}")
    else:
        output_path = Path(output_csv)

    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    required_columns = {"Handle", "Tags", "Published", "Status"}
    missing = required_columns - set(fieldnames)
    if missing:
        raise ValueError(f"CSV thiếu các cột bắt buộc: {sorted(missing)}")

    keep_active_handles = {
        row["Handle"].strip()
        for row in rows
        if row.get("Handle", "").strip()
        and KEEP_TAG in parse_tags(row.get("Tags", ""))
    }

    if len(keep_active_handles) != 1:
        raise ValueError(
            f"Tìm thấy {len(keep_active_handles)} product có tag {KEEP_TAG!r}: "
            f"{sorted(keep_active_handles)}. Dừng để tránh sửa nhầm."
        )

    changed_to_inactive = 0
    kept_active = 0

    for row in rows:
        handle = row.get("Handle", "").strip()

        if not handle or not is_product_main_row(row):
            continue

        if handle in keep_active_handles:
            row["Status"] = ACTIVE_STATUS
            row["Published"] = "true"
            kept_active += 1
        else:
            row["Status"] = INACTIVE_STATUS
            row["Published"] = "false"
            changed_to_inactive += 1

    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done: {output_path}")
    print(f"Changed to inactive/draft: {changed_to_inactive}")
    print(f"Kept active: {kept_active}")
    print(f"Kept active handle: {next(iter(keep_active_handles))}")

if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        print("Usage: python set_products_inactive_except_tag.py input.csv [output.csv]")
        sys.exit(1)

    set_products_inactive_except_tag(
        input_csv=sys.argv[1],
        output_csv=sys.argv[2] if len(sys.argv) == 3 else None,
    )