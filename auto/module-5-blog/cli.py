"""
Command-Line Interface (`cli.py`) for the Multi-Store Blog Automation Tool.

Usage examples:
  python -m auto.module-5-blog serve --port 8765
  python auto/module-5-blog/cli.py stores
  python auto/module-5-blog/cli.py test-store --store wrydeco
  python auto/module-5-blog/cli.py postprocess --store wrydeco --article tree-bookcase-guide
  python auto/module-5-blog/cli.py sync --store wrydeco --article tree-bookcase-guide --blog buying-guides
  python auto/module-5-blog/cli.py verify --store wrydeco --url https://wrydeco.myshopify.com/blogs/buying-guides/tree-bookcase-guide
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from pipeline import BlogSyncPipeline
from store_manager import StoreManager
from verify_live import verify_published_article


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Multi-Store Zbigtee x Shopify Blog Automation Tool (Module 5)"
    )
    sub = parser.add_subparsers(dest="command", required=False)

    # serve
    p_serve = sub.add_parser(
        "serve",
        help="Start the local Multi-Store Web UI via wrapper (opens browser tab & press 'q' to stop)",
    )
    p_serve.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    p_serve.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765)")
    p_serve.add_argument("--no-browser", action="store_true", help="Do not open browser tab on startup")
    p_serve.add_argument(
        "--raw-server",
        action="store_true",
        help="Internal flag: run raw HTTP server directly without wrapper",
    )

    # stores
    sub.add_parser("stores", help="List all configured stores and their status")

    # test-store
    p_test = sub.add_parser("test-store", help="Test OAuth connection and fetch blogs for a store")
    p_test.add_argument("--store", default=None, help="Store ID or path to store JSON config")

    # fetch-zbigtee
    p_fetch = sub.add_parser(
        "fetch-zbigtee",
        help="Live-scrape Kanban board and IN REVIEW /preview payloads directly from zbigtee.com",
    )
    p_fetch.add_argument("--store", default=None, help="Store ID or path to store JSON config")

    # postprocess
    p_post = sub.add_parser("postprocess", help="Post-process a Zbigtee preview payload into clean HTML")
    p_post.add_argument("--store", default=None, help="Store ID or path to store JSON config")
    p_post.add_argument("--article", default="01a0fb95-71df-79a0-83d4-83f747201ef5", help="Content ID or slug")

    # sync
    p_sync = sub.add_parser("sync", help="Post-process, publish to Shopify store, and verify live")
    p_sync.add_argument("--store", default=None, help="Store ID or path to store JSON config")
    p_sync.add_argument("--article", default="01a0fb95-71df-79a0-83d4-83f747201ef5", help="Content ID or slug")
    p_sync.add_argument("--blog", default=None, help="Target Shopify blog handle or GID")
    p_sync.add_argument("--no-verify", action="store_true", help="Skip Playwright live verification")

    # verify
    p_ver = sub.add_parser("verify", help="Run Playwright live verification on a published Shopify article URL")
    p_ver.add_argument("--store", default=None, help="Store ID or path to store JSON config")
    p_ver.add_argument(
        "--url",
        default="https://wrydeco.myshopify.com/blogs/buying-guides/tree-bookcase-guide",
        help="Full URL of the published article",
    )
    p_ver.add_argument("--handle", default="tree-bookcase-guide", help="Article slug/handle")

    # mcp-serve
    sub.add_parser("mcp-serve", help="Run the local stdio MCP Server (mcp_server.py) for Antigravity")

    args = parser.parse_args()
    cmd = args.command or "serve"

    if cmd == "mcp-serve":
        from mcp_server import run_stdio_server

        run_stdio_server()
        return

    sm = StoreManager()

    if cmd == "serve":
        host = getattr(args, "host", "127.0.0.1")
        port = getattr(args, "port", 8765)
        raw_server = getattr(args, "raw_server", False)
        no_browser = getattr(args, "no_browser", False)

        if raw_server:
            from web_app import serve_web_app

            serve_web_app(host=host, port=port)
        else:
            from server_wrapper import run_wrapped_server

            code = run_wrapped_server(host=host, port=port, open_browser=not no_browser)
            sys.exit(code)
        return

    if cmd == "stores":
        active = sm.get_active_store_id()
        out = {
            "active_store_id": active,
            "stores": [s.to_dict(mask_secrets=True) for s in sm.list_stores()],
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    if cmd == "test-store":
        res = sm.test_connection_and_fetch_blogs(args.store)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    if cmd == "fetch-zbigtee":
        from zbigtee_ui_operator import ZbigteeUiOperator

        zb = ZbigteeUiOperator(sm, args.store)
        res = zb.fetch_all_live_from_zbigtee(use_playwright=True)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    if cmd == "postprocess":
        pipe = BlogSyncPipeline(sm, args.store)
        res = pipe.postprocess_only(args.article)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    if cmd == "sync":
        from campaign_manager import CampaignManager

        pipe = BlogSyncPipeline(sm, args.store)
        cm = CampaignManager(store_manager=sm)
        protected = cm.get_protected_baseline_sets(pipe.store.id)
        res = pipe.sync_and_publish(
            args.article,
            blog_id_or_handle=args.blog,
            verify=not args.no_verify,
            publish_mode="create_only",
            protected_article_ids=protected.get("protected_article_ids"),
            protected_handles=protected.get("protected_handles"),
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    if cmd == "verify":
        res = verify_published_article(sm, args.store, args.url, expected_handle=args.handle)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return


if __name__ == "__main__":
    main()

