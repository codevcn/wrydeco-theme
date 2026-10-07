from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .config import DEFAULT_ENV_PATH, PACKAGE_ROOT, Settings
from .manifest import load_manifest
from .pipeline import Pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m scraper", description="Amazon to Shopify scraper")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="Run or resume a manifest")
    run.add_argument("--manifest", type=Path, default=PACKAGE_ROOT / "input" / "products.json")
    run.add_argument("--env", type=Path, default=DEFAULT_ENV_PATH)
    run.add_argument("--headless", action="store_true")
    run.add_argument("--dry-run", action="store_true", help="Crawl and validate content without changing Shopify")
    run.add_argument("--max-combinations", type=int, default=100)
    run.add_argument("--amazon-postal-code", default="10001", help="US delivery ZIP used to render offers/customization")
    serve_parser = subparsers.add_parser("serve", help="Run the local scraper dashboard")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=5000)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "run":
        manifest_path = args.manifest
        if not manifest_path.exists():
            if (PACKAGE_ROOT / manifest_path).exists():
                manifest_path = PACKAGE_ROOT / manifest_path
            elif manifest_path.parts and manifest_path.parts[0] == "scraper" and (PACKAGE_ROOT / Path(*manifest_path.parts[1:])).exists():
                manifest_path = PACKAGE_ROOT / Path(*manifest_path.parts[1:])
        manifest = load_manifest(manifest_path)
        settings = Settings(env_path=args.env.resolve(), headless=args.headless, max_combinations=args.max_combinations,
                            amazon_postal_code=args.amazon_postal_code)
        summary = asyncio.run(Pipeline(manifest, settings, dry_run=args.dry_run).run())
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 1 if summary["failed"] or summary["needs_attention"] else 0
    if args.command == "serve":
        from .server import serve
        serve(args.host, args.port)
        return 0
    return 2

