#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script upload ảnh sản phẩm lên Shopify Admin > Content > Files.
- Tự động kiểm tra và làm mới Access Token nếu hết hạn bằng Client ID & Client Secret.
- Đổi tên tệp (filename) và tạo Alt Text chuẩn hóa theo tiêu chuẩn SEO của Wrydeco.
- Theo dõi tiến độ qua file manifest để tránh upload trùng lặp.
- Xuất file kết quả ánh xạ (Mapping JSON & CSV) để phục vụ tạo file CSV import sản phẩm.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import mimetypes
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ShopifyImageUploader")

# Đường dẫn mặc định
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_ENV_PATH = BASE_DIR / "auto" / "module-1" / ".media.env"
DEFAULT_OUTPUT_JSON = BASE_DIR / "todo" / "scripts" / "uploaded_images_mapping.json"
DEFAULT_OUTPUT_CSV = BASE_DIR / "todo" / "scripts" / "uploaded_images_mapping.csv"
DEFAULT_MANIFEST = BASE_DIR / "todo" / "scripts" / "upload_manifest.json"


@dataclass
class ShopifyConfig:
    store_domain: str
    access_token: str
    client_id: str
    client_secret: str
    api_version: str = "2024-07"
    timeout_seconds: int = 60
    ready_timeout_seconds: int = 180


def load_env_file(path: Path) -> Dict[str, str]:
    """Đọc file .env đơn giản dạng KEY=VALUE."""
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy file cấu hình: {path}")

    env_data: Dict[str, str] = {}
    content = path.read_text(encoding="utf-8-sig")
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            env_data[key] = val
    return env_data


def update_env_token(path: Path, new_token: str) -> None:
    """Cập nhật Access Token mới vào file .env khi token cũ hết hạn."""
    if not path.is_file():
        return

    content = path.read_text(encoding="utf-8-sig")
    pattern = r"^(STORE_ADMIN_ACCESS_TOKEN\s*=\s*)['\"].*?['\"]"
    replacement = f"\\g<1>'{new_token}'"

    if re.search(pattern, content, flags=re.MULTILINE):
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    else:
        new_content = content + f"\nSTORE_ADMIN_ACCESS_TOKEN='{new_token}'\n"

    path.write_text(new_content, encoding="utf-8")
    logger.info(f"Đã cập nhật Access Token mới vào file {path.name}")


class ShopifyClient:
    """Xử lý kết nối Shopify Admin API & Quản lý Access Token tự động."""

    STAGED_UPLOADS_MUTATION = """
    mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
      stagedUploadsCreate(input: $input) {
        stagedTargets {
          url
          resourceUrl
          parameters {
            name
            value
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    FILE_CREATE_MUTATION = """
    mutation fileCreate($files: [FileCreateInput!]!) {
      fileCreate(files: $files) {
        files {
          id
          fileStatus
          alt
          createdAt
          ... on MediaImage {
            image {
              url
            }
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    FILE_STATUS_QUERY = """
    query getFileStatus($id: ID!) {
      node(id: $id) {
        ... on MediaImage {
          id
          fileStatus
          image {
            url
          }
        }
      }
    }
    """

    def __init__(self, config: ShopifyConfig, env_path: Optional[Path] = None):
        self.config = config
        self.env_path = env_path
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Wrydeco-Shopify-Image-Uploader/1.0",
                "Accept": "application/json",
            }
        )
        self.ensure_valid_token()

    def refresh_access_token(self) -> str:
        """Xin cấp Access Token mới từ Shopify OAuth bằng Client Credentials."""
        logger.warning("Access Token hết hạn hoặc không hợp lệ. Đang yêu cầu token mới từ Shopify...")
        if not self.config.client_id or not self.config.client_secret:
            raise ValueError("Thiếu STORE_ADMIN_CLIENT_ID hoặc STORE_ADMIN_CLIENT_SECRET để cấp lại token!")

        oauth_url = f"https://{self.config.store_domain}/admin/oauth/access_token"
        response = self.session.post(
            oauth_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )

        if not response.ok:
            raise RuntimeError(
                f"Yêu cầu cấp lại token thất bại [HTTP {response.status_code}]: {response.text}"
            )

        data = response.json()
        new_token = data.get("access_token")
        if not new_token:
            raise RuntimeError(f"Shopify không trả về access_token: {data}")

        self.config.access_token = new_token
        if self.env_path:
            update_env_token(self.env_path, new_token)

        logger.info("Cấp mới Access Token thành công!")
        return new_token

    def ensure_valid_token(self) -> None:
        """Kiểm tra tính hợp lệ của token hiện tại, nếu hết hạn sẽ tự làm mới."""
        check_url = f"https://{self.config.store_domain}/admin/api/{self.config.api_version}/shop.json"
        headers = {"X-Shopify-Access-Token": self.config.access_token}

        try:
            resp = self.session.get(check_url, headers=headers, timeout=15)
            if resp.status_code == 401:
                self.refresh_access_token()
            elif not resp.ok:
                logger.warning(f"Kiểm tra shop.json trả về status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"Lỗi khi kiểm tra token: {e}")
            self.refresh_access_token()

    def graphql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Gửi GraphQL query/mutation lên Shopify Admin API."""
        endpoint = f"https://{self.config.store_domain}/admin/api/{self.config.api_version}/graphql.json"
        headers = {
            "X-Shopify-Access-Token": self.config.access_token,
            "Content-Type": "application/json",
        }

        resp = self.session.post(
            endpoint,
            headers=headers,
            json={"query": query, "variables": variables or {}},
            timeout=self.config.timeout_seconds,
        )

        # Nếu token hết hạn giữa chừng (401), làm mới và retry 1 lần
        if resp.status_code == 401:
            self.refresh_access_token()
            headers["X-Shopify-Access-Token"] = self.config.access_token
            resp = self.session.post(
                endpoint,
                headers=headers,
                json={"query": query, "variables": variables or {}},
                timeout=self.config.timeout_seconds,
            )

        if not resp.ok:
            raise RuntimeError(f"GraphQL request failed [HTTP {resp.status_code}]: {resp.text}")

        result = resp.json()
        if "errors" in result and result["errors"]:
            raise RuntimeError(f"Shopify GraphQL returned errors: {json.dumps(result['errors'], ensure_ascii=False)}")

        return result.get("data", {})

    def upload_image_file(self, local_file: Path, seo_filename: str, alt_text: str) -> Tuple[str, str]:
        """
        Upload một tệp ảnh cục bộ lên Shopify Admin > Content > Files:
        1. Tạo Staged Upload target qua GraphQL mutation stagedUploadsCreate.
        2. Đẩy dữ liệu nhị phân của file lên Cloud Storage.
        3. Hoàn tất tạo file trong Shopify qua mutation fileCreate.
        4. Chờ trạng thái READY và trả về CDN URL chính thức + File ID.
        """
        file_bytes = local_file.read_bytes()
        mime_type = mimetypes.guess_type(seo_filename)[0] or "image/png"

        # 1. Khởi tạo Staged Target
        staged_res = self.graphql(
            self.STAGED_UPLOADS_MUTATION,
            {
                "input": [
                    {
                        "filename": seo_filename,
                        "mimeType": mime_type,
                        "httpMethod": "POST",
                        "resource": "IMAGE",
                    }
                ]
            },
        ).get("stagedUploadsCreate", {})

        errors = staged_res.get("userErrors") or []
        if errors:
            raise RuntimeError(f"stagedUploadsCreate thất bại: {errors}")

        targets = staged_res.get("stagedTargets") or []
        if not targets:
            raise RuntimeError("Shopify không trả về staged target.")

        target = targets[0]
        upload_url = target["url"]
        resource_url = target["resourceUrl"]
        params = {item["name"]: item["value"] for item in target.get("parameters", []) if item.get("name")}

        # 2. Upload file nhị phân lên storage của Shopify
        upload_resp = self.session.post(
            upload_url,
            data=params,
            files={"file": (seo_filename, file_bytes, mime_type)},
            timeout=self.config.timeout_seconds,
        )

        if upload_resp.status_code not in (200, 201, 204):
            raise RuntimeError(
                f"Tải binary lên storage thất bại [HTTP {upload_resp.status_code}]: {upload_resp.text[:300]}"
            )

        # 3. Tạo File trong Shopify Content > Files
        file_res = self.graphql(
            self.FILE_CREATE_MUTATION,
            {
                "files": [
                    {
                        "alt": alt_text,
                        "contentType": "IMAGE",
                        "originalSource": resource_url,
                        "filename": seo_filename,
                    }
                ]
            },
        ).get("fileCreate", {})

        f_errors = file_res.get("userErrors") or []
        if f_errors:
            raise RuntimeError(f"fileCreate thất bại: {f_errors}")

        created_files = file_res.get("files") or []
        if not created_files:
            raise RuntimeError("fileCreate không trả về file ID.")

        file_node = created_files[0]
        file_id = file_node["id"]
        direct_url = ((file_node.get("image") or {}).get("url"))

        if file_node.get("fileStatus") == "READY" and direct_url:
            return direct_url, file_id

        # 4. Chờ trạng thái READY nếu Shopify đang xử lý ảnh
        return self._wait_until_ready(file_id)

    def _wait_until_ready(self, file_id: str) -> Tuple[str, str]:
        deadline = time.monotonic() + self.config.ready_timeout_seconds
        sleep_interval = 1.5

        while time.monotonic() < deadline:
            data = self.graphql(self.FILE_STATUS_QUERY, {"id": file_id})
            node = data.get("node") or {}
            status = node.get("fileStatus")
            cdn_url = (node.get("image") or {}).get("url")

            if status == "READY" and cdn_url:
                return cdn_url, file_id
            if status == "FAILED":
                raise RuntimeError(f"Shopify xử lý file thất bại (FAILED): {file_id}")

            time.sleep(sleep_interval)
            sleep_interval = min(sleep_interval * 1.3, 5.0)

        raise TimeoutError(f"Quá thời gian chờ Shopify xử lý file: {file_id}")


# ==============================================================================
# QUY CHUẨN ĐẶT TÊN FILE VÀ ALT TEXT CHUẨN SEO CHO WRYDECO
# ==============================================================================

def generate_seo_metadata(
    collection_name: str,
    model_name: str,
    img_index: int,
    original_file_name: str,
) -> Tuple[str, str]:
    """
    Sinh tên file và Alt Text chuẩn SEO theo định hướng thương hiệu Wrydeco:
    - SEO Filename: wrydeco-{collection}-mirror-{model}-{index:02d}.{ext}
    - Alt Text: Wrydeco {Collection} Solid Wood Wall Mirror {Model} - View {index}
    """
    col_slug = "rustic" if "rustic" in collection_name.lower() else "organic"
    model_match = re.search(r"\d+", model_name)
    model_num = model_match.group(0) if model_match else "1"

    ext = Path(original_file_name).suffix.lower()
    if not ext or ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        ext = ".png"

    # Tên file tối ưu SEO
    seo_filename = f"wrydeco-{col_slug}-mirror-model-{model_num}-{img_index:02d}{ext}"

    # Alt Text tối ưu SEO
    col_title = "Rustic" if col_slug == "rustic" else "Organic"
    view_type = "Front View" if img_index == 1 else f"Angle Detail View {img_index}"
    alt_text = f"Wrydeco {col_title} Solid Wood Wall Mirror Model {model_num} - {view_type}"

    return seo_filename, alt_text


def scan_directory_for_images(input_dir: Path) -> List[Dict[str, Any]]:
    """
    Quét thư mục ảnh cục bộ theo cấu trúc:
    - Cấu trúc 1: input_dir / [Mẫu Rustic | Mẫu Organic] / [MẪU 1 | MẪU 2 ...] / *.png
    - Cấu trúc 2: input_dir / [MẪU 1 | MẪU 2 ...] / *.png
    - Cấu trúc 3: input_dir / *.png (flat)
    """
    supported_extensions = {".png", ".jpg", ".jpeg", ".webp"}
    images_to_upload: List[Dict[str, Any]] = []

    if not input_dir.is_dir():
        raise NotADirectoryError(f"Thư mục không tồn tại: {input_dir}")

    # Tìm tất cả file ảnh trong thư mục và thư mục con
    all_files = sorted(
        [p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() in supported_extensions],
        key=lambda p: (str(p.parent), p.name)
    )

    # Phân nhóm theo thư mục chứa
    dir_grouped: Dict[Path, List[Path]] = {}
    for f in all_files:
        dir_grouped.setdefault(f.parent, []).append(f)

    for parent_dir, files in dir_grouped.items():
        # Xác định collection và model từ đường dẫn
        rel_parts = parent_dir.relative_to(input_dir).parts if parent_dir != input_dir else [parent_dir.name]
        
        col_name = "Rustic"
        model_name = "Model 1"

        if len(rel_parts) >= 2:
            col_name = rel_parts[0]
            model_name = rel_parts[1]
        elif len(rel_parts) == 1:
            part = rel_parts[0]
            if "organic" in part.lower():
                col_name = "Organic"
            elif "rustic" in part.lower():
                col_name = "Rustic"
            model_name = part

        for idx, file_path in enumerate(files, start=1):
            seo_filename, alt_text = generate_seo_metadata(
                collection_name=col_name,
                model_name=model_name,
                img_index=idx,
                original_file_name=file_path.name,
            )

            images_to_upload.append({
                "collection": col_name,
                "model": model_name,
                "index": idx,
                "local_path": str(file_path.resolve()),
                "original_filename": file_path.name,
                "seo_filename": seo_filename,
                "alt_text": alt_text,
            })

    return images_to_upload


def main():
    parser = argparse.ArgumentParser(description="Upload ảnh sản phẩm lên Shopify Files với SEO metadata chuẩn.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=False,
        help="Đường dẫn tới thư mục chứa ảnh cục bộ (ví dụ thư mục tải từ Google Drive về).",
    )
    parser.add_argument(
        "--env",
        type=Path,
        default=DEFAULT_ENV_PATH,
        help=f"Đường dẫn file .media.env (mặc định: {DEFAULT_ENV_PATH}).",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=DEFAULT_OUTPUT_JSON,
        help="Đường dẫn file JSON xuất kết quả mapping.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=DEFAULT_OUTPUT_CSV,
        help="Đường dẫn file CSV xuất kết quả mapping.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Đường dẫn file lưu lịch sử upload để tránh upload trùng.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chạy thử để xem trước danh sách ảnh, tên file SEO và Alt Text mà không gọi upload thật.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bỏ qua manifest, bắt buộc upload lại toàn bộ ảnh.",
    )

    args = parser.parse_args()

    logger.info("=== KHỞI ĐỘNG SHOPIFY IMAGE UPLOADER ===")
    logger.info(f"Đọc cấu hình từ: {args.env}")

    env_data = load_env_file(args.env)
    store_domain = env_data.get("SHOPIFY_STORE_DOMAIN", "").strip()
    access_token = env_data.get("STORE_ADMIN_ACCESS_TOKEN", "").strip()
    client_id = env_data.get("STORE_ADMIN_CLIENT_ID", "").strip()
    client_secret = env_data.get("STORE_ADMIN_CLIENT_SECRET", "").strip()
    api_version = env_data.get("SHOPIFY_API_VERSION", "2024-07").strip()

    if not store_domain:
        logger.error("Thiếu SHOPIFY_STORE_DOMAIN trong .media.env!")
        sys.exit(1)

    config = ShopifyConfig(
        store_domain=store_domain,
        access_token=access_token,
        client_id=client_id,
        client_secret=client_secret,
        api_version=api_version,
    )

    client = None
    if not args.dry_run:
        client = ShopifyClient(config, env_path=args.env)
        logger.info(f"Kết nối thành công tới store: {store_domain} (API {api_version})")

    # Kiểm tra thư mục đầu vào
    input_dir = args.input_dir
    if not input_dir:
        logger.warning("Chưa cung cấp tham số --input-dir.")
        logger.info("Ví dụ: python upload_images_to_shopify.py --input-dir \"D:/path/to/mirrors\"")
        return

    logger.info(f"Quét thư mục ảnh: {input_dir}")
    image_items = scan_directory_for_images(input_dir)
    logger.info(f"Tìm thấy tổng cộng: {len(image_items)} ảnh.")

    # Đọc manifest lịch sử
    manifest: Dict[str, Dict[str, Any]] = {}
    if args.manifest.is_file() and not args.force:
        try:
            manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}

    results = []
    success_count = 0
    skipped_count = 0
    fail_count = 0

    for item in image_items:
        local_path = item["local_path"]
        seo_filename = item["seo_filename"]
        alt_text = item["alt_text"]

        # Kiểm tra xem đã upload chưa
        if local_path in manifest and not args.force:
            cached = manifest[local_path]
            logger.info(f"[BỎ QUA - ĐÃ CÓ] {seo_filename} -> {cached.get('cdn_url')}")
            item.update(cached)
            results.append(item)
            skipped_count += 1
            continue

        if args.dry_run:
            logger.info(f"[DRY-RUN] {item['original_filename']} -> {seo_filename} | Alt: {alt_text}")
            item["cdn_url"] = f"https://cdn.shopify.com/s/files/mock/{seo_filename}"
            item["file_id"] = "gid://shopify/MediaImage/mock"
            results.append(item)
            continue

        logger.info(f"[UPLOADING] {item['original_filename']} -> {seo_filename} ...")
        try:
            cdn_url, file_id = client.upload_image_file(
                local_file=Path(local_path),
                seo_filename=seo_filename,
                alt_text=alt_text,
            )
            item["cdn_url"] = cdn_url
            item["file_id"] = file_id
            manifest[local_path] = {
                "cdn_url": cdn_url,
                "file_id": file_id,
                "seo_filename": seo_filename,
                "alt_text": alt_text,
                "uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            results.append(item)
            success_count += 1
            logger.info(f"  -> Thành công: {cdn_url}")
            time.sleep(0.5)  # Tránh throttle
        except Exception as exc:
            logger.error(f"  -> Thất bại: {exc}")
            item["error"] = str(exc)
            results.append(item)
            fail_count += 1

    # Lưu manifest
    if not args.dry_run:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # Xuất kết quả mapping JSON
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Đã lưu kết quả mapping JSON: {args.output_json}")

    # Xuất kết quả mapping CSV
    if results:
        csv_headers = [
            "collection", "model", "index", "original_filename",
            "seo_filename", "alt_text", "cdn_url", "file_id", "local_path"
        ]
        with args.output_csv.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=csv_headers, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(results)
        logger.info(f"Đã lưu kết quả mapping CSV: {args.output_csv}")

    logger.info(
        f"=== HOÀN TẤT: Thành công={success_count}, Bỏ qua (đã có)={skipped_count}, Lỗi={fail_count} ==="
    )


if __name__ == "__main__":
    main()
