#!/usr/bin/env python3
"""Point the crawl workflow at a new Amazon product, then archive old outputs.

The new Amazon product URL is passed as a command-line argument (the
``move_to_new_link.cmd`` wrapper holds it), not hard-coded here.

Running this script does two things:

1. Rewrites every crawl spec (``crawl.md`` and ``crawl-one-color-swatch-only.md``)
   so each reference to the current Amazon ASIN (the product slug in
   ``https://www.amazon.com/dp/<ASIN>``) is replaced with the ASIN of the new
   URL. Because the ASIN is a distinctive 10-character token, this updates the
   product URL, the ``/crawl/<ASIN>/`` paths, the ``<ASIN>.json`` filenames and
   every JSON example at once. Each file is rewritten against its own current
   ASIN, so they may start from different slugs.
2. Moves every file from ``data/`` and ``output/`` into ``warehouse/`` so the
   working folders are clean before the next product is crawled. Name
   collisions in the warehouse are resolved with a timestamped suffix, so
   nothing is ever overwritten.

Usage (normally through the .cmd wrapper):

    python move_to_new_link.py https://www.amazon.com/dp/B0H6FHL19T
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent

# Crawl specs whose Amazon ASIN references are reset to the new product.
CRAWL_MD_FILES = ("crawl.md", "crawl-one-color-swatch-only.md")

# Source directories whose files are archived, and the archive destination.
ARCHIVE_SOURCE_DIRS = ("data", "output")
WAREHOUSE_DIR = "warehouse"

ASIN_PATTERN = re.compile(r"^[A-Z0-9]{10}$")
DP_URL_PATTERN = re.compile(r"amazon\.com/dp/([A-Z0-9]{10})")


class AppError(RuntimeError):
    """Raised for a user-actionable error."""


def extract_asin_from_url(url: str) -> str:
    """Return the 10-character ASIN found in an Amazon product URL."""
    cleaned = (url or "").strip()
    if not cleaned:
        raise AppError("The new Amazon URL is empty; pass it as an argument.")

    match = DP_URL_PATTERN.search(cleaned)
    asin = match.group(1) if match else cleaned

    if not ASIN_PATTERN.fullmatch(asin):
        raise AppError(
            f"Could not read a 10-character ASIN from the new URL: {url!r}. "
            "Use a link such as https://www.amazon.com/dp/B0H6FHL19T."
        )
    return asin


def detect_current_asin(text: str, source_name: str) -> str:
    """Return the single ASIN currently referenced by a crawl spec's product URL."""
    asins = {match.group(1) for match in DP_URL_PATTERN.finditer(text)}
    if not asins:
        raise AppError(
            f"No amazon.com/dp/<ASIN> URL was found in {source_name}; "
            "cannot determine the current product slug."
        )
    if len(asins) > 1:
        raise AppError(
            f"{source_name} references multiple product ASINs "
            f"({', '.join(sorted(asins))}); resolve this manually before running."
        )
    return next(iter(asins))


def rewrite_markdown(md_path: Path, new_asin: str) -> int:
    """Replace every occurrence of the file's current ASIN with new_asin.

    Returns the number of occurrences replaced. Missing files are skipped with a
    message so a spec that does not exist yet does not abort the whole run.
    """
    if not md_path.is_file():
        print(f"Skipping {md_path.name}: file does not exist.")
        return 0

    text = md_path.read_text(encoding="utf-8")
    current_asin = detect_current_asin(text, md_path.name)

    if current_asin == new_asin:
        print(f"{md_path.name}: already targets {new_asin}; no ASIN changes needed.")
        return 0

    occurrences = text.count(current_asin)
    updated = text.replace(current_asin, new_asin)
    md_path.write_text(updated, encoding="utf-8")
    print(
        f"{md_path.name}: replaced {occurrences} occurrence(s) of "
        f"{current_asin} -> {new_asin}."
    )
    return occurrences


def _unique_destination(directory: Path, name: str) -> Path:
    """Return a non-colliding path inside ``directory`` for ``name``."""
    candidate = directory / name
    if not candidate.exists():
        return candidate

    source = Path(name)
    stem, suffix = source.stem, source.suffix
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    counter = 1
    while True:
        candidate = directory / f"{stem}.{timestamp}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def archive_processed_files(base_dir: Path) -> int:
    """Move every entry from the source directories into the warehouse directory."""
    warehouse = base_dir / WAREHOUSE_DIR
    warehouse.mkdir(parents=True, exist_ok=True)

    moved = 0
    for source_name in ARCHIVE_SOURCE_DIRS:
        source_dir = base_dir / source_name
        if not source_dir.is_dir():
            print(f"Skipping {source_name}/: directory does not exist.")
            continue
        for entry in sorted(source_dir.iterdir()):
            if entry.resolve() == warehouse.resolve():
                continue
            destination = _unique_destination(warehouse, entry.name)
            shutil.move(str(entry), str(destination))
            moved += 1
            print(f"Archived {entry} -> {destination}")
    return moved


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reset the Amazon product slug in the crawl specs, then archive "
            "data/ and output/ into warehouse/."
        )
    )
    parser.add_argument(
        "new_url",
        help="The new Amazon product URL, e.g. https://www.amazon.com/dp/B0H6FHL19T.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        new_asin = extract_asin_from_url(args.new_url)
        print(f"New product ASIN: {new_asin}")

        for file_name in CRAWL_MD_FILES:
            rewrite_markdown(SCRIPT_DIR / file_name, new_asin)

        moved = archive_processed_files(SCRIPT_DIR)
        print(
            f"Archived {moved} file(s) from "
            f"{'/'.join(ARCHIVE_SOURCE_DIRS)} into {WAREHOUSE_DIR}/."
        )
        return 0
    except AppError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
