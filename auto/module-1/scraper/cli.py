from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .config import PACKAGE_ROOT
from .io_utils import load_json
from .manifest import load_manifest
from .orchestrator import RunCoordinator
from .store import OrchestratorStore


def _resolve_manifest(path: Path) -> Path:
    candidates = [path, PACKAGE_ROOT / path]
    if path.parts and path.parts[0].casefold() == "scraper":
        candidates.append(PACKAGE_ROOT / Path(*path.parts[1:]))
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return path.resolve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m scraper", description="Amazon–Shopify queue scraper")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="Crawl a manifest and enqueue content tasks; do not wait for an Agent")
    run.add_argument("--manifest", type=Path, default=PACKAGE_ROOT / "input" / "products.json")
    run.add_argument("--headless", action="store_true")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--max-combinations", type=int, default=100)
    run.add_argument("--amazon-postal-code", default="10001")

    serve_parser = commands.add_parser("serve", help="Run Dashboard, crawler coordinator, and Shopify dispatcher")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=5000)

    commands.add_parser("mcp", help="Run the Wrydeco content queue MCP server over stdio")
    commands.add_parser("worker", help="Run only the sequential Shopify dispatcher")
    commands.add_parser("stop-servers", help="Stop every registered Dashboard server for this scraper workspace")
    status = commands.add_parser("status", help="Print run and queue status without mutating anything")
    status.add_argument("--limit", type=int, default=20)
    return parser


def _run_once(args: argparse.Namespace) -> int:
    manifest_path = _resolve_manifest(args.manifest)
    manifest = load_manifest(manifest_path)
    payload = load_json(manifest_path)
    options = {
        "headless": bool(args.headless),
        "dry_run": bool(args.dry_run),
        "max_combinations": int(args.max_combinations),
        "amazon_postal_code": str(args.amazon_postal_code),
    }
    if not 1 <= options["max_combinations"] <= 100:
        raise ValueError("max_combinations must be between 1 and 100.")
    store = OrchestratorStore(PACKAGE_ROOT)
    run = store.create_run(manifest, payload, options)
    coordinator = RunCoordinator(store)
    coordinator.start(crawler=True, apply=False)
    try:
        while True:
            current = store.get_run(run["id"])
            if current["crawl_status"] in {"complete", "interrupted"}:
                print(json.dumps(current, ensure_ascii=False, indent=2))
                failed = any(item["status"] in {"failed", "needs_attention"} for item in current["products"].values())
                return 1 if current["crawl_status"] == "interrupted" or failed else 0
            time.sleep(0.25)
    finally:
        coordinator.stop()


def _worker() -> int:
    store = OrchestratorStore(PACKAGE_ROOT)
    coordinator = RunCoordinator(store)
    coordinator.start(crawler=False, apply=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        return 0
    finally:
        coordinator.stop()


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "run":
        return _run_once(args)
    if args.command == "serve":
        from .server import serve
        serve(args.host, args.port)
        return 0
    if args.command == "mcp":
        from .mcp_server import run_mcp_server
        run_mcp_server()
        return 0
    if args.command == "worker":
        return _worker()
    if args.command == "stop-servers":
        from .server_control import stop_registered_servers
        result = stop_registered_servers(PACKAGE_ROOT)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result["failed"] else 0
    if args.command == "status":
        store = OrchestratorStore(PACKAGE_ROOT)
        print(json.dumps({"queue": store.queue_status(), "runs": store.list_runs(args.limit)}, ensure_ascii=False, indent=2))
        return 0
    return 2
