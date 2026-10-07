"""
Module: metadata_sanitizer.py
Tự động rà soát và thay thế các từ khóa nhãn hiệu bên thứ ba ("amazon", "wazaro", "preaureum")
thành "Wrydeco" (case-insensitive, có ranh giới từ \b) trong toàn bộ các lớp metadata hình ảnh:
- File nhị phân (Binary metadata: EXIF, XMP, IPTC, PNG text chunks)
- Web / Shopify Upload metadata (alt_text, filename)
- Thuộc tính thẻ HTML (alt, title trong thẻ <img>)
"""

from __future__ import annotations

import copy
import logging
import re
from io import BytesIO
from typing import Any

from PIL import ExifTags, Image, ImageOps, PngImagePlugin, UnidentifiedImageError

LOGGER = logging.getLogger("metadata-sanitizer")

# Khớp case-insensitive với ranh giới từ \b
RE_TARGET_BRANDS = re.compile(r"\b(amazon|wazaro|preaureum)\b", re.IGNORECASE)
RE_TARGET_BRANDS_BYTES = re.compile(rb"\b(amazon|wazaro|preaureum)\b", re.IGNORECASE)

REPLACEMENT_BRAND = "Wrydeco"
REPLACEMENT_BRAND_BYTES = b"Wrydeco"


def sanitize_text(text: str) -> str:
    """Thay thế các từ khóa thương hiệu nguồn trong chuỗi văn bản thành 'Wrydeco'."""
    if not text or not isinstance(text, str):
        return text
    return RE_TARGET_BRANDS.sub(REPLACEMENT_BRAND, text)


def sanitize_bytes(data: bytes) -> bytes:
    """Thay thế các từ khóa thương hiệu nguồn trong dữ liệu bytes thành 'Wrydeco'."""
    if not data or not isinstance(data, (bytes, bytearray)):
        return data
    return RE_TARGET_BRANDS_BYTES.sub(REPLACEMENT_BRAND_BYTES, bytes(data))


def contains_target_brands(data: str | bytes) -> bool:
    """Kiểm tra xem chuỗi văn bản hoặc bytes có chứa bất kỳ từ khóa nào cần thay thế không."""
    if isinstance(data, str):
        return bool(RE_TARGET_BRANDS.search(data))
    if isinstance(data, (bytes, bytearray)):
        return bool(RE_TARGET_BRANDS_BYTES.search(bytes(data)))
    return False


def sanitize_exif(exif: Image.Exif) -> tuple[Image.Exif, bool]:
    """
    Rà soát và khử toàn bộ từ khóa nguồn trong EXIF tags và các sub-IFDs.
    Trả về: (exif_đã_làm_sạch, boolean_có_thay_đổi_không)
    """
    if not exif:
        return exif, False

    changed = False

    def clean_ifd_dict(ifd_dict: Any) -> bool:
        local_changed = False
        for tag_id, val in list(ifd_dict.items()):
            if isinstance(val, str):
                new_val = sanitize_text(val)
                if new_val != val:
                    ifd_dict[tag_id] = new_val
                    local_changed = True
            elif isinstance(val, bytes):
                # Thử decode UTF-8 nếu là text bytes
                try:
                    decoded = val.decode("utf-8")
                    new_decoded = sanitize_text(decoded)
                    if new_decoded != decoded:
                        ifd_dict[tag_id] = new_decoded.encode("utf-8")
                        local_changed = True
                except UnicodeDecodeError:
                    # Nếu là raw binary, thử thay thế trực tiếp ở tầng byte
                    new_val_bytes = sanitize_bytes(val)
                    if new_val_bytes != val:
                        ifd_dict[tag_id] = new_val_bytes
                        local_changed = True
        return local_changed

    # 1. Rà soát Root IFD
    if clean_ifd_dict(exif):
        changed = True

    # 2. Rà soát Sub-IFDs
    sub_ifds = [
        getattr(ExifTags.IFD, "Exif", None),
        getattr(ExifTags.IFD, "GPSInfo", None),
        getattr(ExifTags.IFD, "Makernote", None),
        getattr(ExifTags.IFD, "Interop", None),
    ]

    for ifd_id in sub_ifds:
        if ifd_id is None:
            continue
        try:
            sub_dict = exif.get_ifd(ifd_id)
            if sub_dict and clean_ifd_dict(sub_dict):
                changed = True
        except Exception as exc:
            LOGGER.debug("Could not read or clean sub-IFD %s: %s", ifd_id, exc)

    return exif, changed


def sanitize_image_info(info: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """
    Rà soát và khử từ khóa nguồn trong image.info (XMP, comments, PNG text chunks).
    Trả về: (info_đã_làm_sạch, boolean_có_thay_đổi_không)
    """
    if not info:
        return info, False

    changed = False
    cleaned_info = copy.deepcopy(info)

    # 1. XMP metadata
    for xmp_key in ["xmp", "XML:com.adobe.xmp"]:
        if xmp_key in cleaned_info:
            xmp_val = cleaned_info[xmp_key]
            if isinstance(xmp_val, bytes):
                new_xmp = sanitize_bytes(xmp_val)
                if new_xmp != xmp_val:
                    cleaned_info[xmp_key] = new_xmp
                    changed = True
            elif isinstance(xmp_val, str):
                new_xmp = sanitize_text(xmp_val)
                if new_xmp != xmp_val:
                    cleaned_info[xmp_key] = new_xmp
                    changed = True

    # 2. Các text keys/values khác (như Comment, Description, Author)
    for key, val in list(cleaned_info.items()):
        if key in ["icc_profile", "exif", "photoshop", "xmp", "XML:com.adobe.xmp"]:
            continue
        if isinstance(val, str):
            new_val = sanitize_text(val)
            if new_val != val:
                cleaned_info[key] = new_val
                changed = True
        elif isinstance(val, bytes):
            try:
                decoded = val.decode("utf-8")
                new_decoded = sanitize_text(decoded)
                if new_decoded != decoded:
                    cleaned_info[key] = new_decoded.encode("utf-8")
                    changed = True
            except UnicodeDecodeError:
                pass

    return cleaned_info, changed


def sanitize_image_bytes(image_bytes: bytes, filename: str | None = None) -> tuple[bytes, bool]:
    """
    Rà soát toàn diện file ảnh nhị phân:
    - Nếu metadata sạch: Trả về nguyên bản (image_bytes, False) -> Zero-recompression, giữ 100% chất lượng.
    - Nếu metadata có chứa từ khóa: Khử metadata và xuất lại ảnh với chất lượng cao nhất -> (cleaned_bytes, True).
    """
    if not image_bytes:
        return image_bytes, False

    try:
        with Image.open(BytesIO(image_bytes)) as opened:
            image_format = opened.format
            raw_exif = opened.getexif()
            raw_info = copy.deepcopy(opened.info)

            # Rà soát xem có cần thay đổi không
            cleaned_exif, exif_changed = sanitize_exif(raw_exif) if raw_exif else (None, False)
            cleaned_info, info_changed = sanitize_image_info(raw_info)

            if not (exif_changed or info_changed):
                return image_bytes, False

            # Cần tái tạo lại file với metadata đã làm sạch
            output = BytesIO()
            save_kwargs: dict[str, Any] = {}

            icc_profile = cleaned_info.get("icc_profile")
            if icc_profile:
                save_kwargs["icc_profile"] = icc_profile

            if image_format == "JPEG":
                # Bảo toàn orientation EXIF và các tag khác
                if cleaned_exif:
                    try:
                        save_kwargs["exif"] = cleaned_exif.tobytes()
                    except Exception as exc:
                        LOGGER.debug("Could not encode sanitized EXIF: %s", exc)

                if "xmp" in cleaned_info:
                    save_kwargs["xmp"] = cleaned_info["xmp"]

                save_kwargs.update(quality=100, subsampling=0, optimize=True)

                # Chuyển RGBA sang RGB nếu là JPEG
                out_img = opened.convert("RGB") if opened.mode in ("RGBA", "P") else opened
                out_img.save(output, format="JPEG", **save_kwargs)

            elif image_format == "PNG":
                save_kwargs["optimize"] = True
                png_info = PngImagePlugin.PngInfo()
                for k, v in cleaned_info.items():
                    if isinstance(v, str) and k not in ["icc_profile"]:
                        png_info.add_text(k, v)
                save_kwargs["pnginfo"] = png_info

                if cleaned_exif:
                    try:
                        save_kwargs["exif"] = cleaned_exif.tobytes()
                    except Exception as exc:
                        LOGGER.debug("Could not encode sanitized EXIF to PNG: %s", exc)

                opened.save(output, format="PNG", **save_kwargs)

            elif image_format == "WEBP":
                save_kwargs.update(lossless=True, method=6)
                if cleaned_exif:
                    try:
                        save_kwargs["exif"] = cleaned_exif.tobytes()
                    except Exception as exc:
                        LOGGER.debug("Could not encode sanitized EXIF to WEBP: %s", exc)
                if "xmp" in cleaned_info:
                    save_kwargs["xmp"] = cleaned_info["xmp"]

                opened.save(output, format="WEBP", **save_kwargs)

            else:
                # Định dạng khác
                if cleaned_exif:
                    try:
                        save_kwargs["exif"] = cleaned_exif.tobytes()
                    except Exception:
                        pass
                opened.save(output, format=image_format, **save_kwargs)

            cleaned_bytes = output.getvalue()
            LOGGER.info(
                "Image %s metadata sanitized successfully (size: %d -> %d bytes).",
                filename or "<unnamed>",
                len(image_bytes),
                len(cleaned_bytes),
            )
            return cleaned_bytes, True

    except (UnidentifiedImageError, OSError) as exc:
        LOGGER.warning("Could not parse image bytes for metadata sanitization: %s", exc)
        return image_bytes, False


def sanitize_html_img_attributes(html_text: str) -> str:
    """
    Rà soát và thay thế các từ khóa thương hiệu trong thuộc tính alt="..." và title="..." của thẻ <img>.
    Ví dụ: <img alt="PREAUREUM Tree Bookshelf" ...> -> <img alt="Wrydeco Tree Bookshelf" ...>
    """
    if not html_text or not isinstance(html_text, str):
        return html_text

    def replace_attr_value(match: re.Match[str]) -> str:
        attr_name = match.group(1)
        quote = match.group(2)
        val = match.group(3)
        cleaned_val = sanitize_text(val)
        return f"{attr_name}={quote}{cleaned_val}{quote}"

    # Khớp alt="..." hoặc title="..." (hỗ trợ cả nháy đơn và nháy kép)
    pattern = re.compile(r"""\b(alt|title)=(["'])(.*?)\2""", re.IGNORECASE | re.DOTALL)
    return pattern.sub(replace_attr_value, html_text)
