from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
PRODUCT_MARKDOWN_PATH = SCRIPT_DIR / "product.md"
HANDLE_IMAGES_CMD_PATH = SCRIPT_DIR / "handle_images.cmd"

PLACEHOLDER_PATTERN = re.compile(r"{{\s*([A-Za-z0-9_.-]+)\s*}}")


class RunError(RuntimeError):
    """Raised when the local product generation workflow cannot continue."""


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RunError(f"Không tìm thấy file JSON: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise RunError(
            f"File JSON không hợp lệ tại dòng {exc.lineno}, cột {exc.colno}: {exc.msg}"
        ) from exc
    except OSError as exc:
        raise RunError(f"Không thể đọc file {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise RunError(f"Nội dung gốc của {path.name} phải là một JSON object.")

    return data


def resolve_path(data: Mapping[str, Any], field_path: str) -> Any:
    """Resolve a dot-separated field path from a mapping."""
    current: Any = data

    for part in field_path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise KeyError(field_path)
        current = current[part]

    return current


def resolve_placeholder(config: Mapping[str, Any], placeholder: str) -> Any:
    """
    Resolve placeholders against config.json.

    Existing product.md placeholders such as {{product_id}} are resolved from
    config["product"]. Dot notation such as {{product.product_id}} is also
    supported for future templates.
    """
    if "." in placeholder:
        return resolve_path(config, placeholder)

    product = config.get("product")
    if isinstance(product, Mapping) and placeholder in product:
        return product[placeholder]

    if placeholder in config:
        return config[placeholder]

    raise KeyError(placeholder)


def format_placeholder_value(placeholder: str, value: Any) -> str:
    """Convert one config value into text suitable for product.md."""
    field_name = placeholder.rsplit(".", maxsplit=1)[-1]

    if field_name == "product_description":
        if not isinstance(value, list):
            raise RunError(
                "Field product.product_description phải là một mảng để có thể join."
            )

        invalid_indexes = [
            index for index, item in enumerate(value) if not isinstance(item, str)
        ]
        if invalid_indexes:
            indexes = ", ".join(str(index) for index in invalid_indexes)
            raise RunError(
                "Mọi item trong product.product_description phải là string. "
                f"Item không hợp lệ tại index: {indexes}."
            )

        # A blank line between items keeps the source description readable in
        # the Markdown code block in product.md.
        return "\n\n".join(item.strip() for item in value)

    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)

    return str(value)


def render_product_markdown(template: str, config: Mapping[str, Any]) -> str:
    placeholders = set(PLACEHOLDER_PATTERN.findall(template))
    if not placeholders:
        print("Không tìm thấy placeholder nào trong product.md; giữ nguyên nội dung file.")
        return template

    replacements: dict[str, str] = {}
    missing_fields: list[str] = []

    for placeholder in sorted(placeholders):
        try:
            value = resolve_placeholder(config, placeholder)
            replacements[placeholder] = format_placeholder_value(placeholder, value)
        except KeyError:
            missing_fields.append(placeholder)

    if missing_fields:
        fields = ", ".join(missing_fields)
        raise RunError(
            "Không tìm thấy field tương ứng cho các placeholder sau trong "
            f"config.json: {fields}"
        )

    rendered = PLACEHOLDER_PATTERN.sub(
        lambda match: replacements[match.group(1)],
        template,
    )

    unresolved = sorted(set(PLACEHOLDER_PATTERN.findall(rendered)))
    if unresolved:
        raise RunError(
            "Vẫn còn placeholder chưa được thay thế: " + ", ".join(unresolved)
        )

    return rendered


def atomic_write_text(path: Path, content: str) -> None:
    """Write UTF-8 text atomically to avoid leaving a partially written file."""
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)

        os.replace(temp_path, path)
    except OSError as exc:
        raise RunError(f"Không thể ghi file {path}: {exc}") from exc
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def run_handle_images_cmd(path: Path) -> int:
    if not path.is_file():
        raise RunError(f"Không tìm thấy file cần chạy ở bước cuối: {path}")

    if os.name != "nt":
        raise RunError(
            "handle_images.cmd chỉ chạy trực tiếp trên Windows. "
            "Hãy chạy workflow này bằng Python trên Windows."
        )

    command = [
        os.environ.get("COMSPEC", "cmd.exe"),
        "/d",
        "/s",
        "/c",
        f'call "{path}"',
    ]

    print(f"Đang chạy: {path.name}")
    try:
        completed = subprocess.run(
            command,
            cwd=SCRIPT_DIR,
            check=False,
        )
    except OSError as exc:
        raise RunError(f"Không thể chạy {path.name}: {exc}") from exc

    return completed.returncode


def main() -> int:
    try:
        config = load_json(CONFIG_PATH)

        if not PRODUCT_MARKDOWN_PATH.is_file():
            raise RunError(f"Không tìm thấy file Markdown: {PRODUCT_MARKDOWN_PATH}")

        try:
            template = PRODUCT_MARKDOWN_PATH.read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise RunError(
                f"Không thể đọc file {PRODUCT_MARKDOWN_PATH}: {exc}"
            ) from exc

        rendered = render_product_markdown(template, config)
        atomic_write_text(PRODUCT_MARKDOWN_PATH, rendered)
        print(f"Đã thay toàn bộ placeholder trong: {PRODUCT_MARKDOWN_PATH.name}")

        exit_code = run_handle_images_cmd(HANDLE_IMAGES_CMD_PATH)
        if exit_code != 0:
            print(
                f"{HANDLE_IMAGES_CMD_PATH.name} kết thúc với mã lỗi {exit_code}.",
                file=sys.stderr,
            )
        return exit_code

    except RunError as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
