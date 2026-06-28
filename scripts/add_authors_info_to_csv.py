#!/usr/bin/env python3
"""
Gắn ngẫu nhiên một Product Author metaobject entry cho từng sản phẩm
trong file CSV Shopify.

Quy tắc:
- Mỗi sản phẩm được xác định bằng cột "Handle".
- Mỗi sản phẩm nhận đúng một author reference ngẫu nhiên.
- Reference được ghi vào product metafield:
  "Author Info (product.metafields.custom.author_info)".
- Vì metafield trên Shopify được cấu hình là danh sách metaobject references,
  CSV vẫn có thể chứa một handle duy nhất, ví dụ: ngoc-vo.
- Dữ liệu chỉ được ghi ở dòng đầu tiên của mỗi Handle.
- Toàn bộ các cột author cũ custom.author_name, custom.author_bio và
  custom.author_image_url bị xóa khỏi file kết quả.
- File CSV đầu vào không bị sửa; kết quả được ghi sang file mới.

File JSON hiện tại vẫn có thể dùng nguyên cấu trúc cũ. Mỗi author có thể:
1. Khai báo "metaobject_handle" rõ ràng — khuyến nghị; hoặc
2. Chỉ có "author_name" — script tự tạo handle dạng ngoc-vo.

Ví dụ JSON khuyến nghị:
{
  "authors": [
    {"author_name": "Ngoc Vo", "metaobject_handle": "ngoc-vo"},
    {"author_name": "Kiet Phac", "metaobject_handle": "kiet-phac"},
    {"author_name": "Alex Nguyen", "metaobject_handle": "alex-nguyen"}
  ]
}
"""

import csv
import json
import random
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


# ============================================================
# CẤU HÌNH ĐƯỜNG DẪN — CHỈNH SỬA TẠI ĐÂY
# ============================================================

JSON_PATH = Path(r"./authors_sample.json")
CSV_PATH = Path(r"./products_export_1.csv")
OUTPUT_CSV_PATH = Path(r"./products_with_author_metaobjects.csv")


# ============================================================
# CẤU HÌNH XỬ LÝ
# ============================================================

# Đặt một số nguyên, ví dụ 2026, để mỗi lần chạy cho cùng kết quả random.
# Đặt None để mỗi lần chạy có thể phân bổ author khác nhau.
RANDOM_SEED: int | None = None

# True: luôn thay giá trị Author Info hiện có bằng một author ngẫu nhiên mới.
# False: giữ reference hiện có ở dòng đầu tiên; chỉ điền khi đang trống.
OVERWRITE_EXISTING_AUTHOR_REFERENCE = True

# Product metafield chỉ nên nằm ở dòng đầu tiên của mỗi Handle.
AUTHOR_ONLY_ON_FIRST_PRODUCT_ROW = True


# ============================================================
# TÊN CỘT SHOPIFY CSV
# ============================================================

HANDLE_COLUMN = "Handle"

AUTHOR_REFERENCE_COLUMN = (
    "Author Info (product.metafields.custom.author_info)"
)

# Các namespace/key author cũ cần xóa hoàn toàn khỏi header và mọi dòng.
OLD_AUTHOR_METAFIELD_KEYS = {
    "product.metafields.custom.author_name",
    "product.metafields.custom.author_bio",
    "product.metafields.custom.author_image_url",
}


def shopify_handleize(value: str) -> str:
    """Tạo handle cơ bản từ tên, phù hợp với các tên như 'Ngoc Vo'."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    handle = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value.lower()).strip("-")

    if not handle:
        raise ValueError(f"Không thể tạo metaobject handle từ tên: {value!r}")

    return handle


def load_author_references(json_path: Path) -> list[dict[str, str]]:
    """Đọc danh sách author và trả về tên cùng metaobject handle/GID."""
    if not json_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy file JSON: {json_path}")

    with json_path.open("r", encoding="utf-8-sig") as file:
        data: Any = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("JSON phải là một object ở cấp cao nhất.")

    authors = data.get("authors")
    if not isinstance(authors, list) or not authors:
        raise ValueError(
            'JSON phải chứa key "authors" với một danh sách không rỗng.'
        )

    validated: list[dict[str, str]] = []
    seen_references: set[str] = set()

    for index, author in enumerate(authors, start=1):
        if not isinstance(author, dict):
            raise ValueError(f"Author thứ {index} phải là một object JSON.")

        author_name = author.get("author_name")
        if not isinstance(author_name, str) or not author_name.strip():
            raise ValueError(
                f'Author thứ {index} phải có field "author_name" không trống.'
            )
        author_name = author_name.strip()

        explicit_handle = author.get("metaobject_handle")
        explicit_gid = author.get("metaobject_gid")

        if explicit_gid is not None:
            if not isinstance(explicit_gid, str) or not explicit_gid.strip():
                raise ValueError(
                    f'Field "metaobject_gid" của author thứ {index} '
                    "phải là chuỗi không trống."
                )
            reference = explicit_gid.strip()
            if not reference.startswith("gid://shopify/Metaobject/"):
                raise ValueError(
                    f'Metaobject GID không hợp lệ cho "{author_name}": '
                    f"{reference}"
                )
        elif explicit_handle is not None:
            if not isinstance(explicit_handle, str) or not explicit_handle.strip():
                raise ValueError(
                    f'Field "metaobject_handle" của author thứ {index} '
                    "phải là chuỗi không trống."
                )
            reference = explicit_handle.strip()
        else:
            reference = shopify_handleize(author_name)
            print(
                f'Cảnh báo: "{author_name}" chưa có metaobject_handle; '
                f'script tạm suy ra handle là "{reference}".',
                file=sys.stderr,
            )

        if reference in seen_references:
            raise ValueError(
                f'Metaobject reference bị trùng trong JSON: "{reference}".'
            )

        seen_references.add(reference)
        validated.append(
            {
                "author_name": author_name,
                "reference": reference,
            }
        )

    return validated


def read_shopify_csv(
    csv_path: Path,
) -> tuple[list[dict[str, str]], list[str]]:
    """Đọc CSV Shopify và trả về dữ liệu cùng danh sách header."""
    if not csv_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy file CSV: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError("File CSV không có dòng tiêu đề.")

        fieldnames = list(reader.fieldnames)

        if HANDLE_COLUMN not in fieldnames:
            raise ValueError(
                f'CSV phải có cột "{HANDLE_COLUMN}" để xác định sản phẩm.'
            )

        rows = [dict(row) for row in reader]

    if not rows:
        raise ValueError("File CSV không có dòng dữ liệu sản phẩm.")

    return rows, fieldnames


def is_old_author_column(column_name: str) -> bool:
    """Nhận diện cột author cũ dù phần tên hiển thị có thể khác."""
    normalized = column_name.strip().lower()
    return any(key in normalized for key in OLD_AUTHOR_METAFIELD_KEYS)


def remove_old_author_columns(
    rows: list[dict[str, str]],
    fieldnames: list[str],
) -> tuple[list[str], list[str]]:
    """Xóa hoàn toàn các cột custom.author_* cũ khỏi CSV kết quả."""
    removed_columns = [
        column for column in fieldnames if is_old_author_column(column)
    ]

    output_fieldnames = [
        column for column in fieldnames if column not in removed_columns
    ]

    for row in rows:
        for column in removed_columns:
            row.pop(column, None)

    return output_fieldnames, removed_columns


def assign_author_references(
    rows: list[dict[str, str]],
    authors: list[dict[str, str]],
) -> tuple[int, int, int]:
    """Gắn ngẫu nhiên đúng một metaobject author reference cho mỗi Handle."""
    first_row_seen: set[str] = set()
    assigned_by_handle: dict[str, str] = {}

    product_count = 0
    updated_product_count = 0
    skipped_rows = 0

    for row_number, row in enumerate(rows, start=2):
        handle = (row.get(HANDLE_COLUMN) or "").strip()

        if not handle:
            skipped_rows += 1
            print(
                f'Cảnh báo: bỏ qua dòng {row_number} vì cột '
                f'"{HANDLE_COLUMN}" đang trống.',
                file=sys.stderr,
            )
            continue

        is_first_product_row = handle not in first_row_seen

        if is_first_product_row:
            first_row_seen.add(handle)
            product_count += 1

            current_reference = (
                row.get(AUTHOR_REFERENCE_COLUMN) or ""
            ).strip()

            if (
                not OVERWRITE_EXISTING_AUTHOR_REFERENCE
                and current_reference
            ):
                selected_reference = current_reference
            else:
                selected_reference = random.choice(authors)["reference"]
                row[AUTHOR_REFERENCE_COLUMN] = selected_reference
                updated_product_count += 1

            assigned_by_handle[handle] = selected_reference

        elif AUTHOR_ONLY_ON_FIRST_PRODUCT_ROW:
            # Không lặp product metafield trên dòng variant/ảnh phụ.
            row[AUTHOR_REFERENCE_COLUMN] = ""
        else:
            row[AUTHOR_REFERENCE_COLUMN] = assigned_by_handle[handle]

    return product_count, updated_product_count, skipped_rows


def write_shopify_csv(
    output_path: Path,
    rows: list[dict[str, str]],
    fieldnames: list[str],
) -> None:
    """Ghi CSV UTF-8 BOM để Shopify/Excel đọc ổn định."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_fieldnames = list(fieldnames)
    if AUTHOR_REFERENCE_COLUMN not in output_fieldnames:
        output_fieldnames.append(AUTHOR_REFERENCE_COLUMN)

    with output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=output_fieldnames,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """Điểm bắt đầu chương trình."""
    if RANDOM_SEED is not None:
        random.seed(RANDOM_SEED)

    authors = load_author_references(JSON_PATH)
    rows, fieldnames = read_shopify_csv(CSV_PATH)

    fieldnames, removed_columns = remove_old_author_columns(
        rows,
        fieldnames,
    )

    product_count, updated_count, skipped_rows = assign_author_references(
        rows,
        authors,
    )

    write_shopify_csv(
        OUTPUT_CSV_PATH,
        rows,
        fieldnames,
    )

    print("Hoàn tất.")
    print(f"- File JSON: {JSON_PATH.resolve()}")
    print(f"- File CSV đầu vào: {CSV_PATH.resolve()}")
    print(f"- File CSV kết quả: {OUTPUT_CSV_PATH.resolve()}")
    print(f"- Số metaobject author entries: {len(authors)}")
    print(f"- Số sản phẩm theo Handle: {product_count}")
    print(f"- Số sản phẩm đã gắn/cập nhật Author Info: {updated_count}")
    print(f"- Số dòng bị bỏ qua do thiếu Handle: {skipped_rows}")

    if removed_columns:
        print("- Các cột author cũ đã bị xóa:")
        for column in removed_columns:
            print(f"  + {column}")
    else:
        print("- Không tìm thấy cột author cũ cần xóa.")

    print("- Các reference được sử dụng:")
    for author in authors:
        print(f'  + {author["author_name"]}: {author["reference"]}')


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
        print(f"Lỗi: {error}", file=sys.stderr)
        raise SystemExit(1)
