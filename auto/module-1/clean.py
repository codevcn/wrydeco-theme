from __future__ import annotations

import shutil
import sys
from pathlib import Path


KEEP_CONTENT = [
    "assets/",
    ".env",
	"clean.cmd",
    "clean.py",
	"config.json",
	"get_product.py",
	"handle_images.cmd",
	"handle_images.py",
	"handled_products.json",
	"product.md",
	"product.template.md",
	"prompt.txt",
	"run.cmd",
	"run.py",
	"script.js",
	"script-timing.js",
	"temp.html",
	"todo.md",
    "prepare_config.cmd",
    "prepare_config.py",
    "config.prepare.json",
    "toast.cmd"
]


def normalize_keep_names(items: list[str]) -> set[str]:
    """
    Convert entries such as 'data/' to root-level names such as 'data'.
    Comparison is case-insensitive for better compatibility with Windows.
    """
    return {
        item.rstrip("/\\").casefold()
        for item in items
        if item.rstrip("/\\")
    }


def resolve_target_directory() -> Path:
    """
    Usage:
        python cleanup_folder.py
            -> clean the directory containing cleanup_folder.py

        python cleanup_folder.py "C:\\path\\to\\run.cmd"
            -> clean the directory containing the supplied CMD file
    """
    if len(sys.argv) > 2:
        raise ValueError(
            'Usage: python cleanup_folder.py ["path/to/file.cmd"]'
        )

    if len(sys.argv) == 2:
        cmd_path = Path(sys.argv[1]).expanduser().resolve()

        if not cmd_path.is_file():
            raise FileNotFoundError(f"CMD file does not exist: {cmd_path}")

        if cmd_path.suffix.casefold() not in {".cmd", ".bat"}:
            raise ValueError(f"Expected a .cmd or .bat file: {cmd_path}")

        return cmd_path.parent

    return Path(__file__).resolve().parent


def validate_target_directory(target_dir: Path) -> None:
    if not target_dir.exists():
        raise FileNotFoundError(f"Target directory does not exist: {target_dir}")

    if not target_dir.is_dir():
        raise NotADirectoryError(f"Target path is not a directory: {target_dir}")

    # Prevent accidental deletion of a drive root such as C:\ or /.
    if target_dir == Path(target_dir.anchor):
        raise RuntimeError(f"Refusing to clean a filesystem root: {target_dir}")


def delete_entry(path: Path) -> None:
    """
    Delete a root-level file, symlink, or directory.
    Symlinks are unlinked instead of following their targets.
    """
    if path.is_symlink() or path.is_file():
        path.unlink()
        return

    if path.is_dir():
        shutil.rmtree(path)
        return

    # Handle unusual filesystem entries.
    path.unlink()


def main() -> int:
    target_dir = resolve_target_directory()
    validate_target_directory(target_dir)

    keep_names = normalize_keep_names(KEEP_CONTENT)
    deleted: list[str] = []
    failed: list[tuple[str, str]] = []

    print(f"Cleaning directory: {target_dir}")
    print(f"Keeping: {', '.join(KEEP_CONTENT)}")

    for entry in target_dir.iterdir():
        if entry.name.casefold() in keep_names:
            print(f"[KEEP]   {entry.name}")
            continue

        try:
            delete_entry(entry)
            deleted.append(entry.name)
            print(f"[DELETE] {entry.name}")
        except Exception as exc:
            failed.append((entry.name, str(exc)))
            print(f"[ERROR]  {entry.name}: {exc}", file=sys.stderr)

    print()
    print(f"Deleted: {len(deleted)} item(s)")

    if failed:
        print(f"Failed: {len(failed)} item(s)", file=sys.stderr)
        return 1

    print("Cleanup completed successfully.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        raise SystemExit(1)
