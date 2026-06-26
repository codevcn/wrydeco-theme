from pathlib import Path
from urllib.parse import urlparse, unquote
import mimetypes
import re

import requests

# =========================
# CẤU HÌNH
# =========================
TXT_FILE = "links.txt"
OUTPUT_DIR = "media"
TIMEOUT_SECONDS = 60


def read_image_urls(txt_file: Path) -> list[str]:
    """
    Đọc các URL từ file TXT và bỏ qua dòng trống.
    Mỗi dòng không trống được xem là một URL ảnh.
    """
    if not txt_file.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {txt_file.resolve()}")

    content = txt_file.read_text(encoding="utf-8-sig")

    urls = [line.strip() for line in content.splitlines() if line.strip()]

    return urls


def sanitize_filename(filename: str) -> str:
    """
    Loại bỏ các ký tự không hợp lệ trong tên file Windows.
    """
    filename = unquote(filename)
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", filename)
    filename = filename.strip(" .")

    return filename or "image"


def get_extension(url: str, content_type: str | None) -> str:
    """
    Lấy phần mở rộng từ URL hoặc Content-Type.
    """
    url_path = urlparse(url).path
    extension = Path(unquote(url_path)).suffix.lower()

    valid_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".bmp",
        ".svg",
        ".avif",
        ".tiff",
        ".tif",
    }

    if extension in valid_extensions:
        return extension

    if content_type:
        content_type = content_type.split(";")[0].strip().lower()
        guessed_extension = mimetypes.guess_extension(content_type)

        extension_mapping = {
            ".jpe": ".jpg",
            ".jpeg": ".jpg",
        }

        if guessed_extension:
            return extension_mapping.get(
                guessed_extension,
                guessed_extension,
            )

    return ".jpg"


def get_original_filename(url: str) -> str:
    """
    Lấy tên ảnh từ URL.
    """
    url_path = unquote(urlparse(url).path)
    filename = Path(url_path).stem

    return sanitize_filename(filename)


def download_image(
    session: requests.Session,
    url: str,
    index: int,
    total: int,
    output_dir: Path,
) -> Path:
    """
    Tải một ảnh và trả về đường dẫn file đã lưu.
    """
    print(f"[{index}/{total}] Đang tải: {url}")

    response = session.get(
        url,
        timeout=TIMEOUT_SECONDS,
        stream=True,
        allow_redirects=True,
    )
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")

    # Kiểm tra sơ bộ xem response có phải hình ảnh hay không.
    if content_type and not content_type.lower().startswith("image/"):
        print(
            f"  Cảnh báo: Content-Type là '{content_type}', "
            "có thể URL không trả về ảnh trực tiếp."
        )

    extension = get_extension(url, content_type)
    original_name = get_original_filename(url)

    # Thêm số thứ tự để bảo đảm mỗi URL tạo ra một file riêng.
    filename = f"{index:04d}_{original_name}{extension}"
    output_path = output_dir / filename

    with output_path.open("wb") as file:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                file.write(chunk)

    print(f"  Đã lưu: {output_path}")

    return output_path


def main() -> None:
    txt_file = Path(TXT_FILE)
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        urls = read_image_urls(txt_file)
    except Exception as error:
        print(f"Lỗi: {error}")
        return

    if not urls:
        print("File TXT không chứa URL nào.")
        return

    print(f"Tìm thấy {len(urls)} URL ảnh.")
    print(f"Thư mục lưu ảnh: {output_dir.resolve()}")
    print("-" * 70)

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/149.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "image/avif,image/webp,image/apng,image/svg+xml," "image/*,*/*;q=0.8"
            ),
        }
    )

    successful_count = 0
    failed_urls: list[str] = []

    for index, url in enumerate(urls, start=1):
        try:
            download_image(
                session=session,
                url=url,
                index=index,
                total=len(urls),
                output_dir=output_dir,
            )
            successful_count += 1

        except requests.RequestException as error:
            print(f"  Tải thất bại: {error}")
            failed_urls.append(url)

        except OSError as error:
            print(f"  Không thể lưu file: {error}")
            failed_urls.append(url)

        except Exception as error:
            print(f"  Lỗi không xác định: {error}")
            failed_urls.append(url)

        print()

    if failed_urls:
        failed_file = output_dir / "failed_urls.txt"
        failed_file.write_text(
            "\n".join(failed_urls),
            encoding="utf-8",
        )

        print(f"Các URL lỗi đã được lưu tại: {failed_file.resolve()}")

    print("=" * 70)
    print("HOÀN THÀNH")
    print(f"Tổng URL     : {len(urls)}")
    print(f"Thành công   : {successful_count}")
    print(f"Thất bại     : {len(failed_urls)}")


if __name__ == "__main__":
    main()
