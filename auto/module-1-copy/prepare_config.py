from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PREPARE_PATH = SCRIPT_DIR / "config.prepare.json"
CONFIG_PATH = SCRIPT_DIR / "config.json"


class PrepareError(RuntimeError):
    """Raised when config.prepare.json cannot be merged into config.json."""


def load_json(path: Path) -> Any:
    if not path.is_file():
        raise PrepareError(f"Không tìm thấy file JSON: {path}")

    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise PrepareError(
            f"File JSON không hợp lệ ({path.name}) tại dòng {exc.lineno}, "
            f"cột {exc.colno}: {exc.msg}"
        ) from exc
    except OSError as exc:
        raise PrepareError(f"Không thể đọc file {path}: {exc}") from exc


def deep_merge(base: Any, override: Any) -> Any:
    """
    Ghi đè các field của override lên base.

    - Nếu cả hai đều là JSON object, merge đệ quy để các field không được
      khai báo trong override vẫn được giữ nguyên trong base.
    - Nếu field của override là null (None) thì bỏ qua field đó, giữ nguyên
      giá trị tương ứng trong base.
    - Mọi giá trị khác (string, number, bool, array) sẽ ghi đè trực tiếp.
    """
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, override_value in override.items():
            if override_value is None:
                # Field null trong override: giữ nguyên giá trị bên base.
                continue
            if key in merged:
                merged[key] = deep_merge(merged[key], override_value)
            else:
                merged[key] = override_value
        return merged

    return override


def atomic_write_json(path: Path, payload: Any) -> None:
    """Ghi JSON UTF-8 một cách atomic để tránh làm hỏng file khi gặp lỗi."""
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
            json.dump(payload, temp_file, ensure_ascii=False, indent=2)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_path = Path(temp_file.name)

        os.replace(temp_path, path)
    except OSError as exc:
        raise PrepareError(f"Không thể ghi file {path}: {exc}") from exc
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def main() -> int:
    try:
        prepare_data = load_json(PREPARE_PATH)
        config_data = load_json(CONFIG_PATH)

        if not isinstance(prepare_data, dict):
            raise PrepareError(
                f"Nội dung gốc của {PREPARE_PATH.name} phải là một JSON object."
            )
        if not isinstance(config_data, dict):
            raise PrepareError(
                f"Nội dung gốc của {CONFIG_PATH.name} phải là một JSON object."
            )

        merged = deep_merge(config_data, prepare_data)
        atomic_write_json(CONFIG_PATH, merged)

        print(
            f"Đã copy các field từ {PREPARE_PATH.name} vào {CONFIG_PATH.name} "
            "và giữ nguyên các field không được khai báo trong "
            f"{PREPARE_PATH.name}."
        )
        return 0

    except PrepareError as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
