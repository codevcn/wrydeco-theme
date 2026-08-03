"""
upload.images.py:
Script nhận vào đường dẫn thư mục ảnh của 1 sản phẩm cụ thể (ví dụ: `python upload.images.py "media/images/8355804676153"`),
quét và upload toàn bộ ảnh trong thư mục đó lên Shopify Store ở mục Content > Files thông qua GraphQL API,
và cập nhật toàn bộ danh sách URL ảnh public (CDN) nhận được vào field `products.images_file_paths_to_add_into_csv`
của đúng sản phẩm đang xử lý trong file cấu hình (config.images.json hoặc config.json).
"""

from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import os
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

import requests

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
LOGGER = logging.getLogger("upload.images")

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_TIMEOUT_SECONDS = 60
READY_TIMEOUT_SECONDS = 180
MEDIA_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".avif", ".tif", ".tiff",
    ".mp4", ".mov", ".avi", ".mkv", ".webm"
}


class AppError(RuntimeError):
    """Lỗi xử lý trong ứng dụng."""


def load_env_credentials() -> tuple[str, str, str]:
    """
    Đọc thông tin cấu hình từ .env hoặc .media.env.
    Trả về bộ 3: (store_domain, access_token, api_version)
    """
    env_paths = [SCRIPT_DIR / ".env", SCRIPT_DIR / ".media.env"]
    env_data: dict[str, str] = {}

    for ep in env_paths:
        if ep.exists():
            for line in ep.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k and v and k not in env_data:
                        env_data[k] = v

    store_domain = env_data.get("SHOPIFY_SHOP") or env_data.get("SHOPIFY_STORE_DOMAIN") or env_data.get("STORE_DOMAIN")
    access_token = env_data.get("SHOPIFY_ADMIN_TOKEN") or env_data.get("STORE_ADMIN_ACCESS_TOKEN")
    api_version = env_data.get("SHOPIFY_API_VERSION", "2026-07")

    if not store_domain:
        raise AppError("Không tìm thấy tên miền store (SHOPIFY_SHOP / SHOPIFY_STORE_DOMAIN) trong file .env hoặc .media.env")
    if not access_token:
        raise AppError("Không tìm thấy Admin Access Token (SHOPIFY_ADMIN_TOKEN / STORE_ADMIN_ACCESS_TOKEN) trong file .env hoặc .media.env")

    # Chuẩn hóa store domain
    store_domain = store_domain.strip().lower()
    if "://" in store_domain:
        store_domain = urlparse(store_domain).netloc

    return store_domain, access_token, api_version


class ShopifyUploader:
    STAGED_UPLOADS_MUTATION = """
    mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
      stagedUploadsCreate(input: $input) {
        stagedTargets {
          url
          resourceUrl
          parameters { name value }
        }
        userErrors { field message }
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
          ... on MediaImage {
            image { url width height }
          }
          ... on Video {
            sources { url format mimeType }
          }
        }
        userErrors { field message code }
      }
    }
    """

    FILE_STATUS_QUERY = """
    query fileStatus($id: ID!) {
      node(id: $id) {
        ... on MediaImage {
          id
          fileStatus
          alt
          image { url width height }
        }
        ... on Video {
          id
          fileStatus
          alt
          sources { url format mimeType }
        }
      }
    }
    """

    @staticmethod
    def _extract_url_from_node(node: dict[str, Any]) -> str | None:
        if "image" in node and node["image"]:
            return node["image"].get("url")
        if "sources" in node and node["sources"]:
            for src in node["sources"]:
                if src.get("format", "").upper() == "MP4":
                    return src.get("url")
            return node["sources"][0].get("url")
        return None

    def __init__(self, store_domain: str, access_token: str, api_version: str) -> None:
        self.store_domain = store_domain
        self.access_token = access_token
        self.endpoint = f"https://{store_domain}/admin/api/{api_version}/graphql.json"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "*/*"
        })

    def graphql(self, query: str, variables: Mapping[str, Any]) -> dict[str, Any]:
        resp = self.session.post(
            self.endpoint,
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": self.access_token,
            },
            json={"query": query, "variables": variables},
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        payload = resp.json()

        if payload.get("errors"):
            raise AppError("Shopify GraphQL error: " + json.dumps(payload["errors"], ensure_ascii=False))

        data = payload.get("data")
        if not isinstance(data, dict):
            raise AppError("Shopify GraphQL response không chứa object 'data'.")
        return data

    def upload_local_file(self, file_path: Path, alt_text: str | None = None) -> str:
        """
        Upload 1 file ảnh local lên mục Content > Files của Shopify.
        Trả về URL CDN public của ảnh.
        """
        if not file_path.is_file():
            raise AppError(f"File không tồn tại trên hệ thống: {file_path}")

        filename = file_path.name
        mime_type, _ = mimetypes.guess_type(str(file_path))
        ext = file_path.suffix.lower()
        if not mime_type:
            if ext in {".jpg", ".jpeg"}:
                mime_type = "image/jpeg"
            elif ext == ".png":
                mime_type = "image/png"
            elif ext == ".webp":
                mime_type = "image/webp"
            elif ext == ".gif":
                mime_type = "image/gif"
            elif ext == ".mp4":
                mime_type = "video/mp4"
            elif ext == ".webm":
                mime_type = "video/webm"
            elif ext == ".mov":
                mime_type = "video/quicktime"
            else:
                mime_type = "application/octet-stream"

        is_video = (mime_type and mime_type.startswith("video/")) or ext in {".mp4", ".mov", ".avi", ".mkv", ".webm"}
        resource_type = "VIDEO" if is_video else "IMAGE"

        content = file_path.read_bytes()

        # Bước 1: Yêu cầu Shopify tạo url staged upload
        staged_data = self.graphql(
            self.STAGED_UPLOADS_MUTATION,
            {
                "input": [
                    {
                        "filename": filename,
                        "mimeType": mime_type,
                        "httpMethod": "POST",
                        "resource": resource_type,
                    }
                ]
            },
        )["stagedUploadsCreate"]

        if staged_errors := staged_data.get("userErrors"):
            raise AppError("stagedUploadsCreate thất bại: " + json.dumps(staged_errors, ensure_ascii=False))

        targets = staged_data.get("stagedTargets") or []
        if not targets:
            raise AppError("Không nhận được staged target từ Shopify.")

        target = targets[0]
        upload_url = target.get("url")
        resource_url = target.get("resourceUrl")
        if not upload_url or not resource_url:
            raise AppError("Staged target thiếu url hoặc resourceUrl.")

        form_fields = {
            item["name"]: item["value"]
            for item in (target.get("parameters") or [])
            if item.get("name") is not None
        }

        # Bước 2: Upload binary lên Cloud Storage của Shopify (staged URL)
        upload_resp = self.session.post(
            upload_url,
            data=form_fields,
            files={"file": (filename, content, mime_type)},
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
        if upload_resp.status_code not in {200, 201, 204}:
            raise AppError(f"Upload file binary thất bại (HTTP {upload_resp.status_code}): {upload_resp.text[:500]}")

        # Bước 3: Đăng ký file vào hệ thống Shopify Files
        file_create_data = self.graphql(
            self.FILE_CREATE_MUTATION,
            {
                "files": [
                    {
                        "alt": alt_text or filename,
                        "contentType": resource_type,
                        "originalSource": resource_url,
                        "filename": filename,
                    }
                ]
            },
        )["fileCreate"]

        if create_errors := file_create_data.get("userErrors"):
            raise AppError("fileCreate thất bại: " + json.dumps(create_errors, ensure_ascii=False))

        created_files = file_create_data.get("files") or []
        if not created_files or not created_files[0].get("id"):
            raise AppError("Không lấy được ID của file vừa tạo trong hệ thống Shopify.")

        created = created_files[0]
        file_id = created["id"]
        initial_url = self._extract_url_from_node(created)
        if created.get("fileStatus") == "READY" and initial_url:
            return initial_url

        # Bước 4: Chờ file được xử lý xong (READY) để lấy URL chính thức
        return self._wait_until_ready(file_id)

    def _wait_until_ready(self, file_id: str) -> str:
        deadline = time.monotonic() + READY_TIMEOUT_SECONDS
        sleep_sec = 1.5

        while time.monotonic() < deadline:
            data = self.graphql(self.FILE_STATUS_QUERY, {"id": file_id})
            node = data.get("node")
            if not isinstance(node, dict):
                raise AppError(f"Không tìm thấy thông tin file ID trên Shopify: {file_id}")

            status = node.get("fileStatus")
            url = self._extract_url_from_node(node)
            if status == "READY" and url:
                return url
            if status == "FAILED":
                raise AppError(f"Shopify báo lỗi (FAILED) khi xử lý file ảnh {file_id}.")

            time.sleep(sleep_sec)
            sleep_sec = min(sleep_sec * 1.5, 5.0)

        raise AppError(f"Hết thời gian chờ (Timeout) Shopify xử lý file {file_id}.")


def is_already_cdn_url(path_str: str) -> bool:
    """Kiểm tra xem chuỗi đã là một URL hợp lệ hay chưa."""
    ps = path_str.strip().lower()
    return ps.startswith("http://") or ps.startswith("https://") or "cdn.shopify.com" in ps


def is_matching_product(prod: dict[str, Any], target_dir: Path, config_dir: Path) -> bool:
    """Kiểm tra xem product trong config có khớp với folder path đang xử lý hay không."""
    # 1. Khớp theo field đường dẫn folder
    for key in ["images_folder_path_to_add_into_csv", "images_folder_path", "images_folder"]:
        val = prod.get(key)
        if val and isinstance(val, str) and val.strip():
            p = Path(val.strip())
            if not p.is_absolute():
                p = (config_dir / p).resolve()
            if p == target_dir or p.resolve() == target_dir.resolve():
                return True

    # 2. Khớp theo ID sản phẩm hoặc handle bằng tên folder (ví dụ: media/images/8355804676153 -> folder name là 8355804676153)
    prod_id = str(prod.get("id", "")).strip()
    prod_handle = str(prod.get("handle", "")).strip()
    if prod_id and target_dir.name == prod_id:
        return True
    if prod_handle and target_dir.name == prod_handle:
        return True

    # 3. Khớp nếu trong mảng `images_file_paths_to_add_into_csv` đang chứa đúng folder path này
    img_field = prod.get("images_file_paths_to_add_into_csv")
    if isinstance(img_field, list) and len(img_field) == 1 and isinstance(img_field[0], str):
        p = Path(img_field[0].strip())
        if not p.is_absolute():
            p = (config_dir / p).resolve()
        if p == target_dir or p.resolve() == target_dir.resolve():
            return True

    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Upload ảnh từ 1 folder path cụ thể của 1 sản phẩm (ví dụ: `python upload.images.py \"media/images/8355804676153\"`)."
    )
    parser.add_argument(
        "folder_path",
        type=str,
        help="Đường dẫn thư mục ảnh của sản phẩm cần upload (ví dụ: media/images/8355804676153)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Đường dẫn đến file cấu hình (mặc định ưu tiên config.images.json rồi đến config.json)",
    )
    args = parser.parse_args()

    # Xác định file config
    config_path: Path | None = args.config
    if not config_path:
        if (SCRIPT_DIR / "config.images.json").exists():
            config_path = SCRIPT_DIR / "config.images.json"
        elif (SCRIPT_DIR / "config.json").exists():
            config_path = SCRIPT_DIR / "config.json"
        else:
            config_path = SCRIPT_DIR / "config.images.json"

    # Chuẩn hóa folder path đầu vào
    target_folder = Path(args.folder_path)
    if not target_folder.is_absolute():
        if (SCRIPT_DIR / target_folder).exists():
            target_folder = (SCRIPT_DIR / target_folder).resolve()
        else:
            target_folder = target_folder.resolve()

    if not target_folder.is_dir():
        LOGGER.error("KHÔNG TÌM THẤY THƯ MỤC ẢNH: '%s'", args.folder_path)
        return 1

    try:
        store_domain, access_token, api_version = load_env_credentials()
        LOGGER.info("Kết nối store Shopify: %s (API %s)", store_domain, api_version)
        uploader = ShopifyUploader(store_domain, access_token, api_version)
    except Exception as exc:
        LOGGER.error("Lỗi cấu hình xác thực: %s", exc)
        return 1

    # Tìm toàn bộ các file media (ảnh/video) trong thư mục (sắp xếp alphabet)
    image_files = sorted([
        f for f in target_folder.iterdir()
        if f.is_file() and f.suffix.lower() in MEDIA_EXTENSIONS
    ], key=lambda x: x.name.lower())

    LOGGER.info("=== ĐANG XỬ LÝ FOLDER SẢN PHẨM: '%s' ===", target_folder.name)

    if not image_files:
        LOGGER.warning("Thư mục '%s' RỖNG (không tìm thấy file ảnh hợp lệ nào).", args.folder_path)
        return 0

    LOGGER.info("Tìm thấy %d file ảnh trong '%s'. Đang chuẩn bị upload...", len(image_files), args.folder_path)

    # Đọc config để tìm sản phẩm khớp và danh sách URL cũ (idempotent)
    config_data = {}
    products = []
    matched_products = []

    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as f:
                config_data = json.load(f)
            products = config_data.get("products") or []
            if isinstance(products, list):
                for prod in products:
                    if isinstance(prod, dict) and is_matching_product(prod, target_folder, config_path.parent):
                        matched_products.append(prod)
        except Exception as exc:
            LOGGER.warning("Không thể đọc file config '%s': %s", config_path.name, exc)

    # Lấy danh sách URL đã có từ sản phẩm matched đầu tiên
    current_urls = []
    if matched_products:
        current_urls = matched_products[0].get("images_file_paths_to_add_into_csv") or []
        if not isinstance(current_urls, list):
            current_urls = []

    new_cdn_urls = []
    uploaded_count = 0
    skipped_url_count = 0
    failed_count = 0

    prod_handle_hint = matched_products[0].get("handle", "") if matched_products else ""

    for idx, img_file in enumerate(image_files):
        # Kiểm tra ảnh đã từng được upload lên CDN chưa
        existing_url = next((u for u in current_urls if isinstance(u, str) and img_file.name.lower() in u.lower() and is_already_cdn_url(u)), None)
        if existing_url:
            LOGGER.info("  [%d/%d] Bỏ qua (đã có trên CDN): %s -> %s", idx + 1, len(image_files), img_file.name, existing_url)
            new_cdn_urls.append(existing_url)
            skipped_url_count += 1
            continue

        LOGGER.info("  [%d/%d] Đang upload: %s ...", idx + 1, len(image_files), img_file.name)
        try:
            alt_text = f"Review photo for {prod_handle_hint}" if prod_handle_hint else img_file.stem
            cdn_url = uploader.upload_local_file(img_file, alt_text=alt_text)
            LOGGER.info("  [%d/%d] => THÀNH CÔNG! CDN URL: %s", idx + 1, len(image_files), cdn_url)
            new_cdn_urls.append(cdn_url)
            uploaded_count += 1
        except Exception as exc:
            LOGGER.error("  [%d/%d] => LỖI UPLOAD '%s': %s", idx + 1, len(image_files), img_file.name, exc)
            failed_count += 1

    # Cập nhật vào config cho đúng sản phẩm đang xử lý
    modified = False
    if matched_products:
        for prod in matched_products:
            prod_id = prod.get("id", "N/A")
            if prod.get("images_file_paths_to_add_into_csv") != new_cdn_urls:
                prod["images_file_paths_to_add_into_csv"] = new_cdn_urls
                modified = True
            # Đảm bảo field folder path cũng chính xác
            if not prod.get("images_folder_path_to_add_into_csv"):
                prod["images_folder_path_to_add_into_csv"] = args.folder_path
                modified = True
            LOGGER.info("🎯 Đã cập nhật %d URL ảnh vào sản phẩm ID %s trong '%s'", len(new_cdn_urls), prod_id, config_path.name)
    else:
        LOGGER.warning("⚠️ Không tìm thấy sản phẩm nào trong '%s' khớp với folder '%s'. Đã upload thành công %d ảnh nhưng không lưu vào config.", config_path.name, args.folder_path, len(new_cdn_urls))

    if modified and config_path.exists():
        try:
            with config_path.open("w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            LOGGER.info("✅ Đã lưu thành công các thay đổi vào file '%s'.", config_path.name)
        except Exception as exc:
            LOGGER.error("Lỗi khi ghi file '%s': %s", config_path.name, exc)
            return 1

    LOGGER.info("--------------------------------------------------")
    LOGGER.info("TỔNG KẾT XỬ LÝ FOLDER SẢN PHẨM '%s':", target_folder.name)
    LOGGER.info("  - Tổng số file ảnh tìm thấy: %d", len(image_files))
    LOGGER.info("  - Đã upload mới           : %d", uploaded_count)
    LOGGER.info("  - Đã có trên CDN (Bỏ qua) : %d", skipped_url_count)
    LOGGER.info("  - Upload lỗi              : %d", failed_count)
    LOGGER.info("--------------------------------------------------")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
