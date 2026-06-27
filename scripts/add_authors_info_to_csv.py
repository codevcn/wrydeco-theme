#!/usr/bin/env python3
"""
Gắn ngẫu nhiên thông tin tác giả từ file JSON vào từng sản phẩm
trong file CSV sản phẩm Shopify.

Quy tắc:
- Mỗi sản phẩm được xác định bằng cột "Handle".
- Một tác giả có thể được dùng cho nhiều sản phẩm.
- Nếu một sản phẩm có nhiều dòng CSV do variant hoặc ảnh bổ sung,
  tác giả chỉ được ghi ở dòng đầu tiên của sản phẩm đó.
- File CSV đầu vào không bị sửa trực tiếp; kết quả được ghi sang file mới.
"""

import csv
import json
import random
import sys
from pathlib import Path
from typing import Any


# ============================================================
# CẤU HÌNH ĐƯỜNG DẪN — CHỈNH SỬA TẠI ĐÂY
# ============================================================

JSON_PATH = Path(r"./authors_sample.json")
CSV_PATH = Path(r"./products_export_1.csv")
OUTPUT_CSV_PATH = Path(r"./products_with_authors.csv")


# ============================================================
# CẤU HÌNH XỬ LÝ
# ============================================================

# Đặt một số nguyên, ví dụ 2026, nếu muốn kết quả random giống nhau
# trong mọi lần chạy. Đặt None để mỗi lần chạy có thể cho kết quả khác.
RANDOM_SEED: int | None = None

# True: ghi đè dữ liệu author hiện có ở dòng đầu tiên của sản phẩm.
# False: chỉ điền khi cả 3 cột author đang trống.
OVERWRITE_EXISTING_AUTHOR = True

# Shopify thường chỉ cần product metafields ở dòng đầu tiên của mỗi Handle.
# Nên giữ True để tránh lặp dữ liệu trên các dòng variant/ảnh bổ sung.
AUTHOR_ONLY_ON_FIRST_PRODUCT_ROW = True


# ============================================================
# TÊN CỘT SHOPIFY CSV
# ============================================================

HANDLE_COLUMN = "Handle"

AUTHOR_NAME_COLUMN = (
    "Author name (product.metafields.custom.author_name)"
)
AUTHOR_BIO_COLUMN = (
    "Author bio (product.metafields.custom.author_bio)"
)
AUTHOR_IMAGE_URL_COLUMN = (
    "Author image URL (product.metafields.custom.author_image_url)"
)

AUTHOR_COLUMNS = [
    AUTHOR_NAME_COLUMN,
    AUTHOR_BIO_COLUMN,
    AUTHOR_IMAGE_URL_COLUMN,
]

REQUIRED_AUTHOR_KEYS = [
    "author_name",
    "author_bio",
    "author_image_url",
]


def load_authors(json_path: Path) -> list[dict[str, str]]:
    """Đọc và kiểm tra danh sách tác giả từ file JSON."""
    if not json_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy file JSON: {json_path}")

    with json_path.open("r", encoding="utf-8-sig") as file:
        data: Any = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("JSON phải là một object ở cấp cao nhất.")

    authors = data.get("authors")

    if not isinstance(authors, list) or not authors:
        raise ValueError(
            'JSON phải chứa key "authors" và giá trị phải là một '
            "danh sách không rỗng."
        )

    validated_authors: list[dict[str, str]] = []

    for index, author in enumerate(authors, start=1):
        if not isinstance(author, dict):
            raise ValueError(
                f"Author thứ {index} phải là một object JSON."
            )

        missing_keys = [
            key for key in REQUIRED_AUTHOR_KEYS if key not in author
        ]
        if missing_keys:
            raise ValueError(
                f"Author thứ {index} thiếu field: "
                f"{', '.join(missing_keys)}"
            )

        normalized_author: dict[str, str] = {}

        for key in REQUIRED_AUTHOR_KEYS:
            value = author[key]

            if value is None:
                value = ""

            if not isinstance(value, str):
                raise ValueError(
                    f'Field "{key}" của author thứ {index} phải là chuỗi.'
                )

            normalized_author[key] = value.strip()

        if not normalized_author["author_name"]:
            raise ValueError(
                f'Field "author_name" của author thứ {index} không được trống.'
            )

        validated_authors.append(normalized_author)

    return validated_authors


def read_shopify_csv(
    csv_path: Path,
) -> tuple[list[dict[str, str]], list[str]]:
    """Đọc toàn bộ CSV Shopify và trả về rows cùng danh sách cột."""
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


def author_fields_are_empty(row: dict[str, str]) -> bool:
    """Kiểm tra cả ba cột author trên một dòng có đang trống không."""
    return all(not (row.get(column) or "").strip() for column in AUTHOR_COLUMNS)


def set_author_fields(
    row: dict[str, str],
    author: dict[str, str],
) -> None:
    """Gắn dữ liệu một tác giả vào một dòng CSV."""
    row[AUTHOR_NAME_COLUMN] = author["author_name"]
    row[AUTHOR_BIO_COLUMN] = author["author_bio"]
    row[AUTHOR_IMAGE_URL_COLUMN] = author["author_image_url"]


def clear_author_fields(row: dict[str, str]) -> None:
    """Làm trống author metafields trên dòng variant/ảnh phụ."""
    for column in AUTHOR_COLUMNS:
        row[column] = ""


def assign_authors_to_products(
    rows: list[dict[str, str]],
    authors: list[dict[str, str]],
) -> tuple[int, int, int]:
    """
    Chọn ngẫu nhiên tác giả cho từng Handle.

    Trả về:
    - số sản phẩm đã gặp;
    - số sản phẩm đã được gắn/cập nhật author;
    - số dòng bị bỏ qua vì thiếu Handle.
    """
    assigned_by_handle: dict[str, dict[str, str]] = {}
    first_row_seen: set[str] = set()

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

            selected_author = random.choice(authors)
            assigned_by_handle[handle] = selected_author

            should_write = (
                OVERWRITE_EXISTING_AUTHOR
                or author_fields_are_empty(row)
            )

            if should_write:
                set_author_fields(row, selected_author)
                updated_product_count += 1

        elif AUTHOR_ONLY_ON_FIRST_PRODUCT_ROW:
            # Không lặp lại product metafields ở các dòng variant/ảnh phụ.
            # Chỉ xóa khi chế độ ghi đè đang bật, tránh xóa dữ liệu ngoài ý muốn.
            if OVERWRITE_EXISTING_AUTHOR:
                clear_author_fields(row)
        else:
            selected_author = assigned_by_handle[handle]
            set_author_fields(row, selected_author)

    return product_count, updated_product_count, skipped_rows


def write_shopify_csv(
    output_path: Path,
    rows: list[dict[str, str]],
    fieldnames: list[str],
) -> None:
    """Ghi CSV kết quả với UTF-8 BOM để Excel đọc tiếng Việt tốt hơn."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_fieldnames = list(fieldnames)

    for column in AUTHOR_COLUMNS:
        if column not in output_fieldnames:
            output_fieldnames.append(column)

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

    authors = load_authors(JSON_PATH)
    rows, fieldnames = read_shopify_csv(CSV_PATH)

    product_count, updated_count, skipped_rows = assign_authors_to_products(
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
    print(f"- Số author trong JSON: {len(authors)}")
    print(f"- Số sản phẩm theo Handle: {product_count}")
    print(f"- Số sản phẩm đã gắn/cập nhật author: {updated_count}")
    print(f"- Số dòng bị bỏ qua do thiếu Handle: {skipped_rows}")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
        print(f"Lỗi: {error}", file=sys.stderr)
        raise SystemExit(1)
