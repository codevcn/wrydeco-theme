from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import sys
import time
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

import requests


# =========================================================
# UTF-8 OUTPUT
# =========================================================

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

LOGGER = logging.getLogger("upload.images")


# =========================================================
# CONSTANTS
# =========================================================

SCRIPT_DIR = Path(__file__).resolve().parent

DEFAULT_TIMEOUT_SECONDS = 60
READY_TIMEOUT_SECONDS = 180

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".bmp",
    ".avif",
    ".tif",
    ".tiff",
}


# =========================================================
# ERROR
# =========================================================

class AppError(RuntimeError):
    """Lỗi xử lý trong ứng dụng."""


# =========================================================
# LOAD SHOPIFY CREDENTIALS
# =========================================================

def load_env_credentials() -> tuple[str, str, str]:
    """
    Đọc Shopify credentials từ:

    1. .env
    2. .media.env

    Các biến hỗ trợ:

    Store:
        SHOPIFY_SHOP
        SHOPIFY_STORE_DOMAIN
        STORE_DOMAIN

    Access Token:
        SHOPIFY_ADMIN_TOKEN
        STORE_ADMIN_ACCESS_TOKEN

    API version:
        SHOPIFY_API_VERSION

    Return:
        (store_domain, access_token, api_version)
    """

    env_paths = [
        SCRIPT_DIR / ".env",
        SCRIPT_DIR / ".media.env",
    ]

    env_data: dict[str, str] = {}

    for env_path in env_paths:
        if not env_path.exists():
            continue

        for line in env_path.read_text(
            encoding="utf-8-sig"
        ).splitlines():

            line = line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)

            key = key.strip()
            value = value.strip().strip("'\"")

            # File đọc trước sẽ được ưu tiên
            if key and value and key not in env_data:
                env_data[key] = value

    store_domain = (
        env_data.get("SHOPIFY_SHOP")
        or env_data.get("SHOPIFY_STORE_DOMAIN")
        or env_data.get("STORE_DOMAIN")
    )

    access_token = (
        env_data.get("SHOPIFY_ADMIN_TOKEN")
        or env_data.get("STORE_ADMIN_ACCESS_TOKEN")
    )

    api_version = env_data.get(
        "SHOPIFY_API_VERSION",
        "2026-07",
    )

    if not store_domain:
        raise AppError(
            "Không tìm thấy Shopify Store Domain trong "
            ".env hoặc .media.env. "
            "Hãy khai báo SHOPIFY_SHOP / "
            "SHOPIFY_STORE_DOMAIN / STORE_DOMAIN."
        )

    if not access_token:
        raise AppError(
            "Không tìm thấy Shopify Admin Access Token trong "
            ".env hoặc .media.env. "
            "Hãy khai báo SHOPIFY_ADMIN_TOKEN hoặc "
            "STORE_ADMIN_ACCESS_TOKEN."
        )

    # Chuẩn hóa domain
    store_domain = store_domain.strip().lower()

    if "://" in store_domain:
        store_domain = urlparse(store_domain).netloc

    # Loại bỏ slash cuối nếu có
    store_domain = store_domain.rstrip("/")

    return (
        store_domain,
        access_token,
        api_version,
    )


# =========================================================
# SHOPIFY UPLOADER
# =========================================================

class ShopifyUploader:

    # -----------------------------------------------------
    # STEP 1:
    # Xin staged upload URL
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # STEP 3:
    # Tạo file trong Shopify Content > Files
    # -----------------------------------------------------

    FILE_CREATE_MUTATION = """
    mutation fileCreate($files: [FileCreateInput!]!) {
      fileCreate(files: $files) {
        files {
          id
          fileStatus
          alt

          ... on MediaImage {
            image {
              url
              width
              height
            }
          }
        }

        userErrors {
          field
          message
          code
        }
      }
    }
    """

    # -----------------------------------------------------
    # STEP 4:
    # Check fileStatus
    # -----------------------------------------------------

    FILE_STATUS_QUERY = """
    query fileStatus($id: ID!) {
      node(id: $id) {

        ... on MediaImage {
          id
          fileStatus
          alt

          image {
            url
            width
            height
          }
        }
      }
    }
    """

    # -----------------------------------------------------

    def __init__(
        self,
        store_domain: str,
        access_token: str,
        api_version: str,
    ) -> None:

        self.store_domain = store_domain
        self.access_token = access_token

        self.endpoint = (
            f"https://{store_domain}"
            f"/admin/api/{api_version}"
            f"/graphql.json"
        )

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent":
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64)",

            "Accept": "*/*",
        })

    # =====================================================
    # GRAPHQL
    # =====================================================

    def graphql(
        self,
        query: str,
        variables: Mapping[str, Any],
    ) -> dict[str, Any]:

        response = self.session.post(
            self.endpoint,

            headers={
                "Content-Type": "application/json",
                "X-Shopify-Access-Token":
                    self.access_token,
            },

            json={
                "query": query,
                "variables": variables,
            },

            timeout=DEFAULT_TIMEOUT_SECONDS,
        )

        response.raise_for_status()

        payload = response.json()

        if payload.get("errors"):
            raise AppError(
                "Shopify GraphQL error: "
                + json.dumps(
                    payload["errors"],
                    ensure_ascii=False,
                )
            )

        data = payload.get("data")

        if not isinstance(data, dict):
            raise AppError(
                "Shopify GraphQL response "
                "không chứa object 'data'."
            )

        return data

    # =====================================================
    # EXTRACT PUBLIC URL
    # =====================================================

    @staticmethod
    def _extract_url_from_node(
        node: dict[str, Any],
    ) -> str | None:

        image = node.get("image")

        if isinstance(image, dict):
            url = image.get("url")

            if url:
                return str(url)

        return None

    # =====================================================
    # UPLOAD 1 LOCAL IMAGE
    # =====================================================

    def upload_local_image(
        self,
        file_path: Path,
        alt_text: str | None = None,
    ) -> str:
        """
        Upload một ảnh local lên:

            Shopify Admin
                >
            Content
                >
            Files

        Sau khi Shopify xử lý READY,
        return public CDN URL.
        """

        if not file_path.is_file():
            raise AppError(
                f"File không tồn tại: {file_path}"
            )

        filename = file_path.name
        extension = file_path.suffix.lower()

        # -------------------------------------------------
        # MIME TYPE
        # -------------------------------------------------

        mime_type, _ = mimetypes.guess_type(
            str(file_path)
        )

        if not mime_type:

            if extension in {".jpg", ".jpeg"}:
                mime_type = "image/jpeg"

            elif extension == ".png":
                mime_type = "image/png"

            elif extension == ".webp":
                mime_type = "image/webp"

            elif extension == ".gif":
                mime_type = "image/gif"

            elif extension == ".bmp":
                mime_type = "image/bmp"

            elif extension == ".avif":
                mime_type = "image/avif"

            elif extension in {".tif", ".tiff"}:
                mime_type = "image/tiff"

            else:
                mime_type = "application/octet-stream"

        # =================================================
        # STEP 1
        #
        # Yêu cầu Shopify cấp staged upload URL
        # =================================================

        staged_data = self.graphql(
            self.STAGED_UPLOADS_MUTATION,
            {
                "input": [
                    {
                        "filename": filename,
                        "mimeType": mime_type,
                        "httpMethod": "POST",
                        "resource": "IMAGE",
                        "fileSize": str(
                            file_path.stat().st_size
                        ),
                    }
                ]
            },
        )["stagedUploadsCreate"]

        staged_errors = (
            staged_data.get("userErrors")
            or []
        )

        if staged_errors:
            raise AppError(
                "stagedUploadsCreate thất bại: "
                + json.dumps(
                    staged_errors,
                    ensure_ascii=False,
                )
            )

        targets = (
            staged_data.get("stagedTargets")
            or []
        )

        if not targets:
            raise AppError(
                "Không nhận được staged target "
                "từ Shopify."
            )

        target = targets[0]

        upload_url = target.get("url")
        resource_url = target.get("resourceUrl")

        if not upload_url:
            raise AppError(
                "Staged target thiếu upload URL."
            )

        if not resource_url:
            raise AppError(
                "Staged target thiếu resourceUrl."
            )

        form_fields = {
            item["name"]: item["value"]

            for item in (
                target.get("parameters")
                or []
            )

            if item.get("name") is not None
        }

        # =================================================
        # STEP 2
        #
        # Upload binary file lên staged storage
        # =================================================

        with file_path.open("rb") as file_handle:

            upload_response = self.session.post(
                upload_url,

                data=form_fields,

                files={
                    "file": (
                        filename,
                        file_handle,
                        mime_type,
                    )
                },

                timeout=DEFAULT_TIMEOUT_SECONDS,
            )

        if upload_response.status_code not in {
            200,
            201,
            204,
        }:

            raise AppError(
                "Upload binary thất bại "
                f"(HTTP {upload_response.status_code}): "
                f"{upload_response.text[:500]}"
            )

        # =================================================
        # STEP 3
        #
        # Đăng ký staged file vào Shopify Files
        # =================================================

        file_create_data = self.graphql(
            self.FILE_CREATE_MUTATION,
            {
                "files": [
                    {
                        "alt": (
                            alt_text
                            or filename
                        ),
                        "contentType": "IMAGE",
                        "originalSource":
                            resource_url,
                    }
                ]
            },
        )["fileCreate"]

        create_errors = (
            file_create_data.get("userErrors")
            or []
        )

        if create_errors:
            raise AppError(
                "fileCreate thất bại: "
                + json.dumps(
                    create_errors,
                    ensure_ascii=False,
                )
            )

        created_files = (
            file_create_data.get("files")
            or []
        )

        if not created_files:
            raise AppError(
                "Shopify không trả về "
                "thông tin file vừa tạo."
            )

        created = created_files[0]

        file_id = created.get("id")

        if not file_id:
            raise AppError(
                "Không lấy được Shopify File ID."
            )

        # Nếu Shopify xử lý xong ngay
        initial_url = (
            self._extract_url_from_node(
                created
            )
        )

        if (
            created.get("fileStatus") == "READY"
            and initial_url
        ):
            return initial_url

        # =================================================
        # STEP 4
        #
        # Chờ Shopify xử lý file READY
        # =================================================

        return self._wait_until_ready(
            file_id
        )

    # =====================================================
    # WAIT READY
    # =====================================================

    def _wait_until_ready(
        self,
        file_id: str,
    ) -> str:

        deadline = (
            time.monotonic()
            + READY_TIMEOUT_SECONDS
        )

        sleep_seconds = 1.5

        while time.monotonic() < deadline:

            data = self.graphql(
                self.FILE_STATUS_QUERY,
                {
                    "id": file_id
                },
            )

            node = data.get("node")

            if not isinstance(node, dict):
                raise AppError(
                    "Không tìm thấy Shopify File ID: "
                    f"{file_id}"
                )

            status = node.get("fileStatus")

            public_url = (
                self._extract_url_from_node(
                    node
                )
            )

            if (
                status == "READY"
                and public_url
            ):
                return public_url

            if status == "FAILED":
                raise AppError(
                    "Shopify báo FAILED khi "
                    f"xử lý file {file_id}."
                )

            time.sleep(sleep_seconds)

            sleep_seconds = min(
                sleep_seconds * 1.5,
                5.0,
            )

        raise AppError(
            "Timeout khi chờ Shopify "
            f"xử lý file {file_id}."
        )


# =========================================================
# RESOLVE INPUT FOLDER
# =========================================================

def resolve_folder_path(
    raw_folder_path: str,
) -> Path:
    """
    Nhận 1 local folder path.

    Nếu relative path:
    - ưu tiên relative với thư mục chứa script
    - nếu không tồn tại thì resolve theo working directory
    """

    raw_folder_path = (
        raw_folder_path
        .strip()
        .strip('"')
        .strip("'")
    )

    if not raw_folder_path:
        raise AppError(
            "Folder path đang rỗng."
        )

    folder_path = Path(
        raw_folder_path
    )

    if not folder_path.is_absolute():

        script_relative = (
            SCRIPT_DIR
            / folder_path
        )

        if script_relative.exists():
            folder_path = (
                script_relative.resolve()
            )

        else:
            folder_path = (
                folder_path.resolve()
            )

    if not folder_path.exists():
        raise AppError(
            "Không tìm thấy folder: "
            f"{folder_path}"
        )

    if not folder_path.is_dir():
        raise AppError(
            "Path không phải folder: "
            f"{folder_path}"
        )

    return folder_path


# =========================================================
# GET IMAGES IN FOLDER
# =========================================================

def get_image_files(
    folder_path: Path,
) -> list[Path]:
    """
    Lấy toàn bộ ảnh nằm trực tiếp trong folder.

    KHÔNG recursive vào folder con.

    File được sort alphabet theo filename.
    """

    image_files = [
        file_path

        for file_path
        in folder_path.iterdir()

        if (
            file_path.is_file()
            and
            file_path.suffix.lower()
            in IMAGE_EXTENSIONS
        )
    ]

    image_files.sort(
        key=lambda path:
            path.name.lower()
    )

    return image_files


# =========================================================
# MAIN
# =========================================================

def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Upload toàn bộ ảnh trong một local folder "
            "lên Shopify Content > Files và trả về "
            "danh sách public CDN URLs."
        )
    )

    parser.add_argument(
        "folder_path",
        type=str,
        help=(
            "Local folder path chứa ảnh. "
            'Ví dụ: "media/images/8355804676153" '
            'hoặc "D:\\images\\product-1"'
        ),
    )

    args = parser.parse_args()

    # =====================================================
    # LOAD FOLDER
    # =====================================================

    try:
        folder_path = resolve_folder_path(
            args.folder_path
        )

    except Exception as exc:
        LOGGER.error(
            "Lỗi folder: %s",
            exc,
        )

        return 1

    # =====================================================
    # FIND IMAGES
    # =====================================================

    image_files = get_image_files(
        folder_path
    )

    if not image_files:

        LOGGER.warning(
            "Không tìm thấy file ảnh nào trong folder: %s",
            folder_path,
        )

        # Vẫn trả về list rỗng
        print(
            json.dumps(
                [],
                ensure_ascii=False,
            )
        )

        return 0

    LOGGER.info(
        "Folder: %s",
        folder_path,
    )

    LOGGER.info(
        "Tìm thấy %d ảnh.",
        len(image_files),
    )

    # =====================================================
    # SHOPIFY CONNECTION
    # =====================================================

    try:

        (
            store_domain,
            access_token,
            api_version,
        ) = load_env_credentials()

        LOGGER.info(
            "Shopify Store: %s",
            store_domain,
        )

        LOGGER.info(
            "Shopify API Version: %s",
            api_version,
        )

        uploader = ShopifyUploader(
            store_domain,
            access_token,
            api_version,
        )

    except Exception as exc:

        LOGGER.error(
            "Lỗi Shopify configuration: %s",
            exc,
        )

        return 1

    # =====================================================
    # UPLOAD ALL IMAGES
    # =====================================================

    public_urls: list[str] = []

    failed_count = 0

    total = len(image_files)

    for index, image_path in enumerate(
        image_files,
        start=1,
    ):

        LOGGER.info(
            "[%d/%d] Upload: %s",
            index,
            total,
            image_path.name,
        )

        try:

            public_url = (
                uploader.upload_local_image(
                    image_path,
                    alt_text=image_path.stem,
                )
            )

            public_urls.append(
                public_url
            )

            LOGGER.info(
                "[%d/%d] Thành công: %s",
                index,
                total,
                public_url,
            )

        except Exception as exc:

            failed_count += 1

            LOGGER.error(
                "[%d/%d] Upload thất bại '%s': %s",
                index,
                total,
                image_path.name,
                exc,
            )

    # =====================================================
    # FINAL RESULT
    # =====================================================

    LOGGER.info(
        "----------------------------------------"
    )

    LOGGER.info(
        "Tổng ảnh: %d",
        total,
    )

    LOGGER.info(
        "Upload thành công: %d",
        len(public_urls),
    )

    LOGGER.info(
        "Upload thất bại: %d",
        failed_count,
    )

    LOGGER.info(
        "----------------------------------------"
    )

    # =====================================================
    # OUTPUT:
    # List public URLs
    # =====================================================

    print(
        json.dumps(
            public_urls,
            ensure_ascii=False,
            indent=2,
        )
    )

    # Nếu có ít nhất 1 ảnh lỗi -> exit code 1
    # nhưng những ảnh upload thành công vẫn được print ở trên.
    return (
        0
        if failed_count == 0
        else 1
    )


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    sys.exit(main())