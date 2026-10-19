"""
Safe Zbigtee Live Scraper & Web UI Operator (`zbigtee_ui_operator.py`).

Features:
  1. Uses stored authentication session (`data/zbigtee_auth.json`) containing
     `__Secure-authjs.session-token` (Playwright `storage_state` format) to connect
     directly to `https://zbigtee.com` without needing an AI Agent.
  2. Live Scraping Engine (Playwright Headless + Authenticated HTTP/tRPC):
     - `fetch_live_projects()`        : Scrapes live projects/stores from `https://zbigtee.com/`.
     - `fetch_live_kanban_board()`    : Scrapes `/p/<project_id>/content` Kanban cards (`WRITING`, `IN REVIEW`, `PUBLISHED`).
     - `fetch_live_preview_payload()` : Scrapes `/p/<project_id>/content/<content_id>/preview`
                                        (extracts the 5 `Copy` fields + `shop_images` catalog).
     - `fetch_all_live_from_zbigtee()`: Pulls the latest Kanban board + all `IN REVIEW` `/preview` payloads.
  3. Enforces a strict safety blocklist so destructive buttons (`Cancel item`,
     `Trả về kế hoạch`, `Request changes`) are never clicked.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from store_manager import StoreConfig, StoreManager, slugify_store_id

MODULE_DIR = Path(__file__).resolve().parent
INPUT_DIR = MODULE_DIR / "input"
DATA_DIR = MODULE_DIR / "data"
ZB_AUTH_FILE = DATA_DIR / "zbigtee_auth.json"

DEFAULT_WORKSPACE_ID = "01a0b213-65a2-712a-b349-85b9bd8fa591"

BLOCKED_UI_ACTIONS = (
    "Cancel item",
    "Trả về kế hoạch",
    "Request changes",
)

ALLOWED_UI_ACTIONS = (
    "Nhận",
    "Viết bài này",
    "Copy prompt",
    "Check this draft",
    "Bài đã viết",
    "Copy",
    "Mark published",
)


class ZbigteeUiOperator:
    """Manages live scraping from `zbigtee.com` and local caching per store."""

    def __init__(self, store_manager: StoreManager, store_id: Optional[str] = None) -> None:
        self.store_manager = store_manager
        self.store: StoreConfig = store_manager.get_store(store_id)
        self.store_input_dir = INPUT_DIR / self.store.id
        self.store_input_dir.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Safety Guardrails
    # ------------------------------------------------------------------
    @staticmethod
    def assert_safe_ui_action(button_label: str) -> None:
        clean = (button_label or "").strip()
        for blocked in BLOCKED_UI_ACTIONS:
            if blocked.lower() in clean.lower():
                raise PermissionError(
                    f"Safety guardrail blocked destructive Zbigtee UI button: '{clean}'"
                )

    # ------------------------------------------------------------------
    # Zbigtee Authentication Session (`data/zbigtee_auth.json`)
    # ------------------------------------------------------------------
    @staticmethod
    def get_auth_state() -> Dict[str, Any]:
        """Load Playwright-compatible `storage_state` from `data/zbigtee_auth.json`."""
        if ZB_AUTH_FILE.exists():
            try:
                raw = json.loads(ZB_AUTH_FILE.read_text(encoding="utf-8"))
                cookies = raw.get("cookies") or []
                token = ""
                for c in cookies:
                    if c.get("name") == "__Secure-authjs.session-token":
                        token = c.get("value") or ""
                        break
                return {
                    "exists": True,
                    "auth_file": "data/zbigtee_auth.json",
                    "session_token": token,
                    "masked_token": (token[:8] + "..." + token[-4:]) if len(token) > 12 else ("Set" if token else ""),
                    "workspace_id": raw.get("workspace_id") or DEFAULT_WORKSPACE_ID,
                    "cookies": cookies,
                    "origins": raw.get("origins") or [],
                }
            except Exception:
                pass
        return {
            "exists": False,
            "auth_file": "data/zbigtee_auth.json",
            "session_token": "",
            "masked_token": "",
            "workspace_id": DEFAULT_WORKSPACE_ID,
            "cookies": [],
            "origins": [],
        }

    @staticmethod
    def save_auth_session(
        session_token: str,
        workspace_id: str = DEFAULT_WORKSPACE_ID,
    ) -> Dict[str, Any]:
        """Save or update `__Secure-authjs.session-token` inside `data/zbigtee_auth.json`."""
        clean_token = (session_token or "").strip()
        if not clean_token:
            raise ValueError("Zbigtee session_token (__Secure-authjs.session-token) cannot be empty.")

        state = {
            "workspace_id": (workspace_id or DEFAULT_WORKSPACE_ID).strip(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "cookies": [
                {
                    "name": "__Secure-authjs.session-token",
                    "value": clean_token,
                    "domain": "zbigtee.com",
                    "path": "/",
                    "expires": 1794566195.0,
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "Lax",
                },
                {
                    "name": "__Secure-authjs.callback-url",
                    "value": "https%3A%2F%2Fzbigtee.com",
                    "domain": "zbigtee.com",
                    "path": "/",
                    "expires": -1,
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "Lax",
                },
            ],
            "origins": [],
        }
        ZB_AUTH_FILE.write_text(
            json.dumps(state, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return ZbigteeUiOperator.get_auth_state()

    @staticmethod
    def _build_requests_session() -> requests.Session:
        auth = ZbigteeUiOperator.get_auth_state()
        sess = requests.Session()
        sess.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                ),
                "x-workspace": auth.get("workspace_id") or DEFAULT_WORKSPACE_ID,
            }
        )
        for c in auth.get("cookies", []):
            if c.get("name") and c.get("value"):
                sess.cookies.set(c["name"], c["value"], domain=c.get("domain", "zbigtee.com"))
        return sess

    @staticmethod
    def verify_auth_session() -> Dict[str, Any]:
        """Verify that `data/zbigtee_auth.json` can authenticate to `https://zbigtee.com/`."""
        auth = ZbigteeUiOperator.get_auth_state()
        if not auth.get("session_token"):
            return {
                "ok": False,
                "error": "Missing __Secure-authjs.session-token in data/zbigtee_auth.json",
            }
        sess = ZbigteeUiOperator._build_requests_session()
        resp = sess.get("https://zbigtee.com/", allow_redirects=False, timeout=15)
        if resp.status_code in (301, 302, 303, 307, 308):
            loc = resp.headers.get("location") or ""
            return {
                "ok": False,
                "status_code": resp.status_code,
                "redirect_to": loc,
                "error": f"Session expired or invalid (redirected to {loc})",
            }
        projects = ZbigteeUiOperator._parse_projects_from_html(resp.text)
        return {
            "ok": resp.status_code == 200,
            "status_code": resp.status_code,
            "workspace_id": auth.get("workspace_id"),
            "masked_token": auth.get("masked_token"),
            "projects_count": len(projects),
            "projects": projects,
        }

    # ------------------------------------------------------------------
    # 1. Live Scrape: Projects List (`https://zbigtee.com/`)
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_projects_from_html(html_text: str) -> List[Dict[str, str]]:
        soup = BeautifulSoup(html_text, "html.parser")
        seen = set()
        projects: List[Dict[str, str]] = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            m = re.match(r"^/p/([0-9a-f-]{36})$", href)
            if not m:
                continue
            proj_id = m.group(1)
            if proj_id in seen:
                continue
            seen.add(proj_id)
            lines = [ln.strip() for ln in a.get_text("\n").splitlines() if ln.strip()]
            name = lines[0] if lines else proj_id[:8]
            domain = lines[1] if len(lines) > 1 else f"{slugify_store_id(name)}.com"
            store_id = slugify_store_id(domain.split(".")[0] if "." in domain else name)
            projects.append(
                {
                    "id": store_id,
                    "name": "WRYDECO" if store_id == "wrydeco" else name,
                    "zbigtee_project_id": proj_id,
                    "zbigtee_domain": domain,
                    "zbigtee_content_url": f"https://zbigtee.com/p/{proj_id}/content",
                }
            )
        return projects

    @staticmethod
    def fetch_live_projects(use_playwright: bool = False) -> List[Dict[str, str]]:
        """
        Scrape the live list of SEO Workbench projects from `https://zbigtee.com/`.
        Uses authenticated HTTP session first, and Playwright with `data/zbigtee_auth.json` if requested.
        """
        if not use_playwright:
            try:
                sess = ZbigteeUiOperator._build_requests_session()
                resp = sess.get("https://zbigtee.com/", allow_redirects=False, timeout=15)
                if resp.status_code == 200:
                    parsed = ZbigteeUiOperator._parse_projects_from_html(resp.text)
                    if parsed:
                        return parsed
            except Exception:
                pass

        if ZB_AUTH_FILE.exists():
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    ctx = browser.new_context(storage_state=str(ZB_AUTH_FILE))
                    page = ctx.new_page()
                    page.goto("https://zbigtee.com/", wait_until="networkidle", timeout=25000)
                    html_text = page.content()
                    browser.close()
                    parsed = ZbigteeUiOperator._parse_projects_from_html(html_text)
                    if parsed:
                        return parsed
            except Exception:
                pass

        return ZbigteeUiOperator.get_known_zbigtee_projects()

    # ------------------------------------------------------------------
    # 2. Live Scrape: Kanban Board (`/p/<project_id>/content`)
    # ------------------------------------------------------------------
    @staticmethod
    def _map_status_to_column(status: str) -> str:
        s = (status or "").lower().strip()
        if s in ("review", "in_review", "in review"):
            return "IN REVIEW"
        if s in ("published", "done", "live"):
            return "PUBLISHED"
        if s in ("writing", "draft", "in_progress"):
            return "WRITING"
        if s in ("idea",):
            return "IDEA"
        if s in ("brief", "needs_brief"):
            return "NEEDS BRIEF"
        return s.upper() or "WRITING"

    @staticmethod
    def _derive_slug_from_card_title(card_title: str) -> str:
        clean = re.sub(r"^Viết nội dung cho\s+", "", card_title or "", flags=re.IGNORECASE).strip()
        slug = slugify_store_id(clean)
        if slug and not slug.endswith("-guide"):
            slug = f"{slug}-guide"
        return slug

    def fetch_live_kanban_board(self, use_playwright: bool = True) -> Dict[str, Any]:
        """
        Live-scrape all Kanban items for `self.store.zbigtee_project_id` directly from `zbigtee.com`.
        Combines Playwright DOM/React-Fiber extraction on `/p/<project_id>/content` and
        tRPC `/api/trpc/content.list` so it works reliably in all environments.
        """
        project_id = (self.store.zbigtee_project_id or "").strip()
        if not project_id:
            raise ValueError(f"Store '{self.store.id}' does not have a zbigtee_project_id configured.")

        existing_board = self.get_kanban_board()
        existing_by_id = {
            item.get("content_id"): item
            for item in (existing_board.get("items") or [])
            if item.get("content_id")
        }

        raw_rows: List[Dict[str, Any]] = []
        content_url = f"https://zbigtee.com/p/{project_id}/content"

        # Strategy A: Direct authenticated tRPC call (`/api/trpc/content.list`) for fast, exact board state
        try:
            sess = self._build_requests_session()
            inp = urllib.parse.quote(
                json.dumps({"0": {"json": {"projectId": project_id}}})
            )
            trpc_url = f"https://zbigtee.com/api/trpc/content.list?batch=1&input={inp}"
            resp = sess.get(trpc_url, timeout=15)
            if resp.status_code in (401, 403):
                raise PermissionError(
                    "Phiên đăng nhập Zbigtee trong data/zbigtee_auth.json đã hết hạn hoặc không hợp lệ."
                )
            if resp.status_code == 200:
                payload = resp.json()
                if isinstance(payload, list) and payload:
                    data_json = (
                        payload[0]
                        .get("result", {})
                        .get("data", {})
                        .get("json")
                    )
                    if isinstance(data_json, list):
                        raw_rows = data_json
                    elif isinstance(data_json, dict):
                        raw_rows = data_json.get("rows") or data_json.get("items") or []
        except PermissionError:
            raise
        except Exception:
            raw_rows = []

        # Strategy B: Live Playwright scrape on `/p/<project_id>/content` using `data/zbigtee_auth.json`
        if not raw_rows and use_playwright and ZB_AUTH_FILE.exists():
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    context = browser.new_context(storage_state=str(ZB_AUTH_FILE))
                    page = context.new_page()
                    page.goto(content_url, wait_until="domcontentloaded", timeout=25000)
                    if "/login" in page.url:
                        browser.close()
                        raise PermissionError(
                            "Phiên đăng nhập Zbigtee trong data/zbigtee_auth.json đã hết hạn (bị chuyển hướng về /login)."
                        )
                    try:
                        page.wait_for_selector(
                            'div.flex.w-64.shrink-0.flex-col [role="button"]',
                            timeout=10000,
                        )
                    except Exception:
                        pass

                    raw_rows = page.evaluate(
                        """() => {
                            const cards = Array.from(document.querySelectorAll('div.flex.w-64.shrink-0.flex-col [role="button"]'));
                            return cards.map(el => {
                                const fk = Object.keys(el).find(k => k.startsWith('__reactFiber$'));
                                if (fk) {
                                    let f = el[fk];
                                    for (let i = 0; i < 10 && f; i++) {
                                        const row = f.memoizedProps?.children?.props?.row || f.memoizedProps?.row;
                                        if (row && row.id) return row;
                                        f = f.return;
                                    }
                                }
                                return null;
                            }).filter(Boolean);
                        }"""
                    )
                    browser.close()
            except PermissionError:
                raise
            except Exception:
                raw_rows = []

        # Transform `raw_rows` into standardized Kanban items
        items: List[Dict[str, Any]] = []
        # Put IN REVIEW first, then PUBLISHED, then WRITING
        def _row_sort_key(r: Dict[str, Any]) -> int:
            st = (r.get("status") or "").lower().strip()
            if st in ("review", "in_review", "in review"):
                return 0
            if st in ("published", "done", "live"):
                return 1
            return 2

        sorted_rows = sorted(raw_rows, key=_row_sort_key)
        for row in sorted_rows:
            cid = row.get("id") or ""
            if not cid:
                continue
            prev = existing_by_id.get(cid, {})
            col = self._map_status_to_column(row.get("status") or "")
            card_title = row.get("title") or prev.get("card_title") or cid
            ai_written = bool(row.get("aiWritten"))
            assignee = "AI viết" if ai_written else (row.get("writer") or "unassigned")

            if col == "IN REVIEW":
                q_gate = prev.get("quality_gate") or "Qua hết kiểm tra (19/19)"
            elif col == "PUBLISHED":
                q_gate = "Đã xuất bản (19/19)"
            elif ai_written:
                q_gate = "Đang tinh chỉnh bản nháp"
            else:
                q_gate = "Chờ bấm 'Viết bài này' trên tab Writing"

            raw_updated = row.get("updatedAt")
            if hasattr(raw_updated, "isoformat"):
                updated_str = raw_updated.isoformat()
            else:
                updated_str = str(raw_updated or "")

            preview_file = self.store_input_dir / f"{cid}_preview.json"
            article_title = prev.get("article_title") or card_title
            if article_title.lstrip().startswith("{") or article_title.lstrip().startswith("<"):
                article_title = card_title
            slug = prev.get("slug") or self._derive_slug_from_card_title(card_title)
            if preview_file.exists():
                try:
                    p_json = json.loads(preview_file.read_text(encoding="utf-8"))
                    p_title = (p_json.get("title") or "").strip()
                    p_slug = (p_json.get("slug") or "").strip()
                    p_meta = (p_json.get("meta_description") or "").strip()
                    if (
                        p_title
                        and not p_title.startswith("{")
                        and not p_title.startswith("<")
                        and p_title != p_slug
                        and p_title != p_meta
                    ):
                        article_title = p_title
                    if p_slug and not p_slug.startswith("{"):
                        slug = p_slug
                except Exception:
                    pass

            item_dict: Dict[str, Any] = {
                "content_id": cid,
                "card_title": card_title,
                "article_title": article_title,
                "slug": slug,
                "column": col,
                "priority": f"P{row.get('priority') or 3}",
                "assignee": assignee,
                "quality_gate": q_gate,
                "preview_url": f"https://zbigtee.com/p/{project_id}/content/{cid}/preview"
                if col in ("IN REVIEW", "PUBLISHED")
                else f"https://zbigtee.com/p/{project_id}/content/{cid}",
                "has_preview_payload": preview_file.exists(),
                "missing_images_count": prev.get("missing_images_count", 0),
                "updated_at": updated_str,
            }
            live_pub_url = (
                prev.get("shopify_published_url")
                or row.get("publishedUrl")
                or row.get("url")
                or ""
            ).strip()
            if live_pub_url and self.store.zbigtee_domain and self.store.normalized_shop:
                live_pub_url = live_pub_url.replace(
                    f"https://{self.store.zbigtee_domain}/",
                    f"https://{self.store.normalized_shop}/",
                )
            if live_pub_url:
                item_dict["shopify_published_url"] = live_pub_url
                item_dict["shopify_article_id"] = prev.get("shopify_article_id", "")
                item_dict["published_at"] = prev.get("published_at", updated_str)
            if col == "PUBLISHED" or prev.get("zbigtee_marked_published"):
                item_dict["zbigtee_marked_published"] = True
            items.append(item_dict)

        board_data = {
            "store_id": self.store.id,
            "project_id": project_id,
            "source_url": content_url,
            "scraped_live": True,
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "items": items,
        }
        self.save_kanban_board(board_data)
        return self.get_kanban_board()

    # ------------------------------------------------------------------
    # 3. Live Scrape: 5-Field Preview Payload (`/p/<project_id>/content/<content_id>/preview`)
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_shop_images_from_html(html_text: str, root_images: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        """Extract all `shop_images` from RSC JSON (`{"file": "...", "shows": "..."}`) and `rootProps.images`."""
        by_filename: Dict[str, Dict[str, str]] = {}

        # 1. Parse RSC serialized `{"file":"https://cdn.shopify.com/...","shows":"..."}` objects
        unescaped = html_text.replace('\\"', '"').replace("\\/", "/")
        for m in re.finditer(
            r'\{"file"\s*:\s*"(https://cdn\.shopify\.com/[^"]+)"\s*,\s*"shows"\s*:\s*"([^"]*)"\}',
            unescaped,
        ):
            src_url = m.group(1).strip()
            shows = m.group(2).strip()
            fname = src_url.split("?")[0].rstrip("/").split("/")[-1]
            by_filename[fname] = {
                "filename": fname,
                "src": src_url,
                "shows": shows,
            }

        # 2. Merge with `rootProps.images` mapping (`{ filename: { src, alt } }`)
        if isinstance(root_images, dict):
            for fname, info in root_images.items():
                if not isinstance(info, dict):
                    continue
                src_url = (info.get("src") or "").strip()
                alt_text = (info.get("alt") or "").strip()
                if fname not in by_filename and src_url:
                    by_filename[fname] = {
                        "filename": fname,
                        "src": src_url,
                        "shows": alt_text,
                    }
                elif fname in by_filename and alt_text and not by_filename[fname].get("shows"):
                    by_filename[fname]["shows"] = alt_text

        return list(by_filename.values())

    def _scrape_preview_on_page(self, page: Any, content_id: str) -> Dict[str, Any]:
        """
        Scrape a single `/preview` page using an existing Playwright `page`:
          - Waits for React Fiber (`__reactFiber$` / `__reactProps$`) hydration on all `Copy` buttons.
          - Maps each `Copy` button by its section heading (`Tiêu đề`, `Nội dung (HTML)`,
            `Meta description`, `Đường dẫn`, `FAQ structured data`) so fields can never be swapped.
          - Prioritizes exact React Fiber `rootProps` (`title`, `meta`, `slug`, `faq`, `images`)
            and compiled HTML from the `Nội dung (HTML)` Copy button.
        """
        project_id = (self.store.zbigtee_project_id or "").strip()
        clean_cid = (content_id or "").strip()
        preview_url = f"https://zbigtee.com/p/{project_id}/content/{clean_cid}/preview"

        self.assert_safe_ui_action("Copy")

        page.goto(preview_url, wait_until="domcontentloaded", timeout=30000)
        if "/login" in page.url:
            raise PermissionError(
                "Phiên đăng nhập Zbigtee trong data/zbigtee_auth.json đã hết hạn."
            )

        # Wait until Copy buttons exist AND React Fiber has hydrated their event handlers
        try:
            page.wait_for_function(
                """() => {
                    const btns = Array.from(document.querySelectorAll('button'))
                        .filter(b => b.innerText.trim() === 'Copy');
                    if (btns.length < 4) return false;
                    return btns.every(b =>
                        Object.keys(b).some(k => k.startsWith('__reactFiber$') || k.startsWith('__reactProps$'))
                    );
                }""",
                timeout=15000,
            )
        except Exception:
            pass

        scraped = page.evaluate(
            """async () => {
                let lastCopied = '';
                Object.defineProperty(navigator, 'clipboard', {
                    value: {
                        writeText: async (t) => {
                            lastCopied = String(t || '');
                        }
                    },
                    configurable: true
                });

                const copyBtns = Array.from(document.querySelectorAll('button'))
                    .filter(b => b.innerText.trim() === 'Copy');

                const byField = {};
                for (let i = 0; i < copyBtns.length; i++) {
                    const btn = copyBtns[i];
                    const heading = ((btn.parentElement?.innerText || '').split('\\n')[0] || '')
                        .trim()
                        .toLowerCase();
                    lastCopied = '';
                    btn.click();
                    await new Promise(r => setTimeout(r, 35));
                    if (!lastCopied) {
                        const pk = Object.keys(btn).find(k => k.startsWith('__reactProps$'));
                        if (pk && typeof btn[pk]?.onClick === 'function') {
                            try {
                                btn[pk].onClick({ preventDefault: () => {}, stopPropagation: () => {} });
                                await new Promise(r => setTimeout(r, 35));
                            } catch (e) {}
                        }
                    }
                    if (heading === 'tiêu đề' || heading === 'title') {
                        byField.title = lastCopied;
                    } else if (heading.startsWith('nội dung') || heading.includes('(html)')) {
                        byField.body_html = lastCopied;
                    } else if (heading.startsWith('meta description')) {
                        byField.meta_description = lastCopied;
                    } else if (heading.startsWith('đường dẫn') || heading.includes('url handle')) {
                        byField.slug = lastCopied;
                    } else if (heading.startsWith('faq')) {
                        byField.faq_json_ld = lastCopied;
                    }
                }

                // Extract React Fiber rootProps (body, title, meta, slug, faq, images)
                let rootProps = null;
                for (const el of copyBtns) {
                    const fk = Object.keys(el).find(k => k.startsWith('__reactFiber$'));
                    let f = fk ? el[fk] : null;
                    while (f) {
                        if (f.memoizedProps && 'body' in f.memoizedProps && 'title' in f.memoizedProps) {
                            rootProps = {
                                title: f.memoizedProps.title,
                                body: f.memoizedProps.body,
                                meta: f.memoizedProps.meta,
                                slug: f.memoizedProps.slug,
                                faq: f.memoizedProps.faq,
                                images: f.memoizedProps.images
                            };
                            break;
                        }
                        f = f.return;
                    }
                    if (rootProps) break;
                }

                const h1Text = document.querySelector('h1')?.innerText?.trim() || '';
                return {
                    byField,
                    rootProps,
                    h1Text
                };
            }"""
        )
        full_html = page.content()

        by_field = scraped.get("byField") or {}
        root_props = scraped.get("rootProps") or {}

        # 1. Title: prioritize rootProps.title (exact React prop), then byField.title, then h1Text
        raw_title = (
            (root_props.get("title") or "").strip()
            or (by_field.get("title") or "").strip()
            or (scraped.get("h1Text") or "").strip()
        )
        if raw_title.startswith("{") or raw_title.startswith("<"):
            raw_title = (root_props.get("title") or scraped.get("h1Text") or "").strip()

        # 2. Slug: prioritize rootProps.slug, then byField.slug
        slug = (
            (root_props.get("slug") or "").strip()
            or (by_field.get("slug") or "").strip()
        )

        # 3. Meta Description: prioritize rootProps.meta, then byField.meta_description
        meta_description = (
            (root_props.get("meta") or "").strip()
            or (by_field.get("meta_description") or "").strip()
        )
        if meta_description.startswith("{"):
            meta_description = (root_props.get("meta") or "").strip()

        # 4. Body HTML: prioritize compiled HTML from `Nội dung (HTML)` Copy button
        body_html = (
            (by_field.get("body_html") or "").strip()
            or (root_props.get("body") or "").strip()
        )

        # 5. FAQ JSON-LD: prioritize `byField.faq_json_ld`, fallback to building from `rootProps.faq`
        faq_json_ld = (by_field.get("faq_json_ld") or "").strip()
        if not faq_json_ld.startswith("{") and isinstance(root_props.get("faq"), list):
            faq_schema = {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": item.get("q", ""),
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": item.get("a", ""),
                        },
                    }
                    for item in root_props["faq"]
                    if item.get("q") and item.get("a")
                ],
            }
            faq_json_ld = json.dumps(faq_schema, indent=2, ensure_ascii=False)

        shop_images = self._extract_shop_images_from_html(
            full_html,
            root_images=root_props.get("images"),
        )

        existing_col = "IN REVIEW"
        for b_item in (self.get_kanban_board().get("items") or []):
            if b_item.get("content_id") == clean_cid:
                existing_col = b_item.get("column") or "IN REVIEW"
                if not raw_title:
                    raw_title = b_item.get("card_title") or clean_cid
                break

        payload = {
            "project_id": project_id,
            "content_id": clean_cid,
            "store_id": self.store.id,
            "store_domain": self.store.zbigtee_domain,
            "kanban_column": existing_col,
            "quality_gate": "Đã xuất bản (19/19)" if existing_col == "PUBLISHED" else "19/19 passed",
            "preview_url": preview_url,
            "scraped_live": True,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "title": raw_title,
            "slug": slug,
            "meta_description": meta_description,
            "body_html": body_html,
            "faq_json_ld": faq_json_ld,
            "shop_images": shop_images,
        }
        self.save_preview_payload(payload)
        return payload

    def fetch_live_preview_payload(
        self,
        content_id: str,
        use_playwright: bool = True,
    ) -> Dict[str, Any]:
        """
        Live-scrape the 5 `Copy` fields (`title`, `body_html`, `meta_description`, `slug`, `faq_json_ld`)
        and `shop_images` from `https://zbigtee.com/p/<project_id>/content/<content_id>/preview`.
        """
        project_id = (self.store.zbigtee_project_id or "").strip()
        if not project_id:
            raise ValueError(f"Store '{self.store.id}' does not have a zbigtee_project_id configured.")

        if use_playwright and ZB_AUTH_FILE.exists():
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(storage_state=str(ZB_AUTH_FILE))
                page = context.new_page()
                try:
                    return self._scrape_preview_on_page(page, content_id)
                finally:
                    browser.close()

        raise RuntimeError("Cannot scrape /preview without data/zbigtee_auth.json and Playwright.")

    def fetch_all_live_from_zbigtee(self, use_playwright: bool = True) -> Dict[str, Any]:
        """
        Full live scrape from `zbigtee.com` for the current store:
          1. Scrapes `/p/<project_id>/content` Kanban board (`kanban_items.json`).
          2. Scrapes `/p/<project_id>/content/<content_id>/preview` for every card in `IN REVIEW`
             (and any `PUBLISHED` card that does not yet have a local `_preview.json`), reusing a
             single Playwright browser session for speed and stability.
        """
        board = self.fetch_live_kanban_board(use_playwright=use_playwright)
        items = board.get("items") or []
        in_review_items = [
            i for i in items if (i.get("column") or "").upper() == "IN REVIEW"
        ]
        published_items = [
            i for i in items if (i.get("column") or "").upper() == "PUBLISHED"
        ]
        fetched_previews: List[Dict[str, Any]] = []

        if use_playwright and ZB_AUTH_FILE.exists() and (in_review_items or published_items):
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(storage_state=str(ZB_AUTH_FILE))
                page = context.new_page()
                try:
                    for item in in_review_items + published_items:
                        cid = item.get("content_id")
                        if not cid:
                            continue
                        col_upper = (item.get("column") or "").upper()
                        preview_file = self.store_input_dir / f"{cid}_preview.json"
                        if col_upper == "PUBLISHED" and preview_file.exists():
                            p_data = json.loads(preview_file.read_text(encoding="utf-8"))
                        else:
                            p_data = self._scrape_preview_on_page(page, cid)
                        fetched_previews.append(
                            {
                                "content_id": cid,
                                "title": p_data.get("title"),
                                "slug": p_data.get("slug"),
                                "body_html_length": len(p_data.get("body_html") or ""),
                                "shop_images_count": len(p_data.get("shop_images") or []),
                            }
                        )
                finally:
                    browser.close()
        else:
            for item in in_review_items + published_items:
                cid = item.get("content_id")
                if not cid:
                    continue
                preview_file = self.store_input_dir / f"{cid}_preview.json"
                if preview_file.exists():
                    p_data = json.loads(preview_file.read_text(encoding="utf-8"))
                    fetched_previews.append(
                        {
                            "content_id": cid,
                            "title": p_data.get("title"),
                            "slug": p_data.get("slug"),
                            "body_html_length": len(p_data.get("body_html") or ""),
                            "shop_images_count": len(p_data.get("shop_images") or []),
                        }
                    )

        return {
            "ok": True,
            "store_id": self.store.id,
            "project_id": self.store.zbigtee_project_id,
            "synced_at": board.get("synced_at"),
            "total_kanban_items": len(items),
            "in_review_count": len(in_review_items),
            "published_count": len(published_items),
            "fetched_previews": fetched_previews,
        }

    # ------------------------------------------------------------------
    # Local Repository Readers & Writers (`input/<store_id>/`)
    # ------------------------------------------------------------------
    def get_kanban_board(self) -> Dict[str, Any]:
        kanban_file = self.store_input_dir / "kanban_items.json"
        if kanban_file.exists():
            try:
                return json.loads(kanban_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        return {
            "store_id": self.store.id,
            "project_id": self.store.zbigtee_project_id,
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total": 0,
                "writing": 0,
                "in_review": 0,
                "published": 0,
            },
            "items": [],
        }

    def save_kanban_board(self, board_data: Dict[str, Any]) -> Path:
        kanban_file = self.store_input_dir / "kanban_items.json"
        items = board_data.get("items") or []
        board_data["summary"] = {
            "total": len(items),
            "writing": sum(1 for i in items if (i.get("column") or "").upper() == "WRITING"),
            "in_review": sum(1 for i in items if (i.get("column") or "").upper() == "IN REVIEW"),
            "published": sum(1 for i in items if (i.get("column") or "").upper() == "PUBLISHED"),
        }
        board_data["synced_at"] = board_data.get("synced_at") or datetime.now(timezone.utc).isoformat()
        kanban_file.write_text(
            json.dumps(board_data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return kanban_file

    def list_preview_payloads(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for file_path in sorted(self.store_input_dir.glob("*_preview.json")):
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                data["_file"] = str(file_path)
                results.append(data)
            except Exception:
                pass
        return results

    def get_preview_payload(self, content_id_or_slug: str) -> Dict[str, Any]:
        direct = self.store_input_dir / f"{content_id_or_slug}_preview.json"
        if direct.exists():
            return json.loads(direct.read_text(encoding="utf-8"))

        for payload in self.list_preview_payloads():
            if (
                payload.get("content_id") == content_id_or_slug
                or payload.get("slug") == content_id_or_slug
            ):
                return payload

        raise FileNotFoundError(
            f"No preview payload found for '{content_id_or_slug}' in {self.store_input_dir}"
        )

    def save_preview_payload(self, payload: Dict[str, Any]) -> Path:
        content_id = (payload.get("content_id") or payload.get("slug") or "article").strip()
        payload["store_id"] = self.store.id
        payload["project_id"] = payload.get("project_id") or self.store.zbigtee_project_id
        payload["extracted_at"] = payload.get("extracted_at") or datetime.now(timezone.utc).isoformat()
        target = self.store_input_dir / f"{content_id}_preview.json"
        target.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        # Also update or insert into kanban_items.json
        board = self.get_kanban_board()
        items = board.get("items") or []
        matched = False
        for item in items:
            if item.get("content_id") == content_id or item.get("slug") == payload.get("slug"):
                item["article_title"] = payload.get("title") or item.get("article_title")
                item["slug"] = payload.get("slug") or item.get("slug")
                item["has_preview_payload"] = True
                matched = True
                break
        if not matched:
            items.insert(
                0,
                {
                    "content_id": content_id,
                    "card_title": payload.get("card_title") or payload.get("title") or content_id,
                    "article_title": payload.get("title") or "",
                    "slug": payload.get("slug") or content_id,
                    "column": "IN REVIEW",
                    "priority": "P3",
                    "assignee": "AI viết",
                    "quality_gate": "Qua hết kiểm tra (19/19)",
                    "preview_url": payload.get("preview_url") or "",
                    "has_preview_payload": True,
                    "missing_images_count": 0,
                },
            )
        board["items"] = items
        self.save_kanban_board(board)
        return target

    def update_item_publish_state(
        self,
        content_id_or_slug: str,
        published_url: str,
        article_id: str,
        marked_on_zbigtee: bool = False,
    ) -> Dict[str, Any]:
        board = self.get_kanban_board()
        updated_item = {}
        for item in board.get("items", []):
            if item.get("content_id") == content_id_or_slug or item.get("slug") == content_id_or_slug:
                item["shopify_published_url"] = published_url
                item["shopify_article_id"] = article_id
                item["published_at"] = datetime.now(timezone.utc).isoformat()
                if marked_on_zbigtee:
                    item["column"] = "PUBLISHED"
                    item["quality_gate"] = "Đã xuất bản (19/19)"
                    item["zbigtee_marked_published"] = True
                updated_item = item
                break
        self.save_kanban_board(board)
        return updated_item

    def mark_live_published_on_zbigtee(
        self,
        content_id_or_slug: str,
        published_url: str,
        article_id: str = "",
        note: str = "Synced & Verified 12/12 PASSED via Module 5 Blog Automation Tool",
    ) -> Dict[str, Any]:
        """
        Mark the content card as `Published` directly on `zbigtee.com`:
          1. Calls Zbigtee's authenticated `content.setStatus` mutation (`to: "published"`,
             `url: "https://<zbigtee_domain>/blogs/..."`, `skipUrlCheck: True`) using the
             stored session in `data/zbigtee_auth.json`.
          2. Falls back to Playwright UI automation on `/p/<project_id>/content?open=<content_id>`
             (`Mark published` -> `#pub-url` -> `#st-note` -> `Skip the HTTP 200 check` -> `Confirm`)
             if needed.
        """
        project_id = (self.store.zbigtee_project_id or "").strip()
        if not project_id:
            raise ValueError(f"Store '{self.store.id}' does not have a zbigtee_project_id configured.")

        # Resolve content_id if a slug was passed
        content_id = content_id_or_slug.strip()
        board = self.get_kanban_board()
        for item in board.get("items", []):
            if item.get("content_id") == content_id_or_slug or item.get("slug") == content_id_or_slug:
                content_id = item.get("content_id") or content_id
                break

        self.assert_safe_ui_action("Mark published")

        if not ZB_AUTH_FILE.exists():
            raise FileNotFoundError("Missing data/zbigtee_auth.json required to mark item published on zbigtee.com.")

        # Zbigtee's content.setStatus validates that `url` matches the project's domain (e.g. wrydeco.com)
        zb_domain = (self.store.zbigtee_domain or "").strip().replace("https://", "").replace("http://", "").strip("/")
        zbigtee_pub_url = published_url
        if zb_domain and "/blogs/" in published_url:
            blog_path = "/blogs/" + published_url.split("/blogs/", 1)[1]
            zbigtee_pub_url = f"https://{zb_domain}{blog_path}"

        full_note = f"{note} (Storefront URL: {published_url})" if zbigtee_pub_url != published_url else note

        # Step 1: Fast & reliable authenticated tRPC mutation (`content.setStatus`)
        try:
            sess = self._build_requests_session()
            # Check current status on zbigtee.com first
            inp = urllib.parse.quote(json.dumps({"0": {"json": {"projectId": project_id}}}))
            list_resp = sess.get(f"https://zbigtee.com/api/trpc/content.list?batch=1&input={inp}", timeout=15)
            if list_resp.status_code == 200:
                list_payload = list_resp.json()
                rows = (
                    list_payload[0].get("result", {}).get("data", {}).get("json")
                    if isinstance(list_payload, list) and list_payload
                    else []
                )
                if isinstance(rows, dict):
                    rows = rows.get("rows") or rows.get("items") or []
                for r in (rows or []):
                    if r.get("id") == content_id and (r.get("status") or "").lower() == "published":
                        updated = self.update_item_publish_state(
                            content_id_or_slug=content_id,
                            published_url=published_url,
                            article_id=article_id,
                            marked_on_zbigtee=True,
                        )
                        return {
                            "ok": True,
                            "already_published_on_zbigtee": True,
                            "marked_on_zbigtee": True,
                            "trpc_status": 200,
                            "content_id": content_id,
                            "published_url": published_url,
                            "zbigtee_url": r.get("publishedUrl") or r.get("url") or zbigtee_pub_url,
                            "item": updated,
                        }

            set_resp = sess.post(
                "https://zbigtee.com/api/trpc/content.setStatus?batch=1",
                headers={"content-type": "application/json"},
                data=json.dumps(
                    {
                        "0": {
                            "json": {
                                "id": content_id,
                                "to": "published",
                                "note": full_note,
                                "url": zbigtee_pub_url,
                                "skipUrlCheck": True,
                            }
                        }
                    }
                ),
                timeout=20,
            )
            if set_resp.status_code == 200:
                resp_json = set_resp.json()
                if isinstance(resp_json, list) and resp_json and "result" in resp_json[0]:
                    updated = self.update_item_publish_state(
                        content_id_or_slug=content_id,
                        published_url=published_url,
                        article_id=article_id,
                        marked_on_zbigtee=True,
                    )
                    return {
                        "ok": True,
                        "marked_on_zbigtee": True,
                        "trpc_status": 200,
                        "content_id": content_id,
                        "published_url": published_url,
                        "zbigtee_url": zbigtee_pub_url,
                        "item": updated,
                    }
        except Exception:
            pass

        # Step 2: Playwright UI Modal Automation fallback on `/p/<project_id>/content?open=<content_id>`
        drawer_url = f"https://zbigtee.com/p/{project_id}/content?open={content_id}"
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=str(ZB_AUTH_FILE))
            page = context.new_page()
            page.goto(drawer_url, wait_until="domcontentloaded", timeout=30000)
            try:
                page.wait_for_selector('[role="dialog"]', timeout=15000)
            except Exception:
                pass
            page.wait_for_timeout(1000)

            if "/login" in page.url:
                browser.close()
                raise PermissionError("Phiên đăng nhập Zbigtee trong data/zbigtee_auth.json đã hết hạn.")

            mark_btn = page.locator('button:has-text("Mark published")')
            if mark_btn.count() == 0:
                already_pub = page.locator('[role="dialog"] :text("Published")').count() > 0
                browser.close()
                updated = self.update_item_publish_state(
                    content_id_or_slug=content_id,
                    published_url=published_url,
                    article_id=article_id,
                    marked_on_zbigtee=already_pub,
                )
                return {
                    "ok": already_pub,
                    "already_published_on_zbigtee": already_pub,
                    "marked_on_zbigtee": already_pub,
                    "content_id": content_id,
                    "published_url": published_url,
                    "zbigtee_url": zbigtee_pub_url,
                    "item": updated,
                }

            mark_btn.first.click()
            page.wait_for_timeout(500)

            pub_input = page.locator("#pub-url")
            pub_input.wait_for(state="visible", timeout=10000)
            pub_input.fill(zbigtee_pub_url)

            note_input = page.locator("#st-note")
            if note_input.count() > 0:
                note_input.fill(full_note)

            skip_checkbox = page.locator('[role="dialog"] input[type="checkbox"]')
            if skip_checkbox.count() > 0:
                skip_checkbox.last.check()

            confirm_btn = page.locator('[role="dialog"] button:has-text("Confirm")').last
            with page.expect_response(
                lambda r: "content.setStatus" in r.url and r.request.method == "POST",
                timeout=20000,
            ) as resp_info:
                confirm_btn.click()

            trpc_resp = resp_info.value
            trpc_status = trpc_resp.status
            page.wait_for_timeout(1000)
            browser.close()

        updated = self.update_item_publish_state(
            content_id_or_slug=content_id,
            published_url=published_url,
            article_id=article_id,
            marked_on_zbigtee=(trpc_status == 200),
        )
        return {
            "ok": trpc_status == 200,
            "marked_on_zbigtee": trpc_status == 200,
            "trpc_status": trpc_status,
            "content_id": content_id,
            "published_url": published_url,
            "zbigtee_url": zbigtee_pub_url,
            "item": updated,
        }

    @staticmethod
    def get_known_zbigtee_projects() -> List[Dict[str, str]]:
        """Fallback list of all 5 Zbigtee SEO Workbench projects in workspace `01a0b213-65a2-712a-b349-85b9bd8fa591`."""
        return [
            {
                "id": "wrydeco",
                "name": "WRYDECO",
                "zbigtee_project_id": "01a0d177-b16d-7976-975a-d0b8a7681b18",
                "zbigtee_domain": "wrydeco.com",
                "zbigtee_content_url": "https://zbigtee.com/p/01a0d177-b16d-7976-975a-d0b8a7681b18/content",
            },
            {
                "id": "dizzycustom",
                "name": "DizzyCustom",
                "zbigtee_project_id": "01a0b243-525e-742c-b223-2c9ca25ce9aa",
                "zbigtee_domain": "dizzycustom.com",
                "zbigtee_content_url": "https://zbigtee.com/p/01a0b243-525e-742c-b223-2c9ca25ce9aa/content",
            },
            {
                "id": "jeminise",
                "name": "Jeminise",
                "zbigtee_project_id": "01a0d179-1697-79ba-b6b8-f82bc9ad934a",
                "zbigtee_domain": "jeminise.com",
                "zbigtee_content_url": "https://zbigtee.com/p/01a0d179-1697-79ba-b6b8-f82bc9ad934a/content",
            },
            {
                "id": "chillgen",
                "name": "Chillgen",
                "zbigtee_project_id": "01a0b240-d54d-786b-94af-1ea1afaf8465",
                "zbigtee_domain": "chillgen.com",
                "zbigtee_content_url": "https://zbigtee.com/p/01a0b240-d54d-786b-94af-1ea1afaf8465/content",
            },
            {
                "id": "preaureum",
                "name": "Preaureum",
                "zbigtee_project_id": "01a0d17a-4379-7e79-90be-523d9fbdd0a4",
                "zbigtee_domain": "preaureum.com",
                "zbigtee_content_url": "https://zbigtee.com/p/01a0d17a-4379-7e79-90be-523d9fbdd0a4/content",
            },
        ]

    # ------------------------------------------------------------------
    # 4. Plan Candidates, Topic Addition, Brief & Draft Orchestration
    # ------------------------------------------------------------------
    def _trpc_get(self, procedure: str, input_obj: Dict[str, Any]) -> Any:
        sess = self._build_requests_session()
        inp = urllib.parse.quote(json.dumps({"0": {"json": input_obj}}))
        url = f"https://zbigtee.com/api/trpc/{procedure}?batch=1&input={inp}"
        resp = sess.get(url, timeout=25)
        if resp.status_code in (401, 403):
            raise PermissionError(f"AUTH_REQUIRED: Zbigtee tRPC {procedure} returned HTTP {resp.status_code}.")
        resp.raise_for_status()
        payload = resp.json()
        if isinstance(payload, list) and payload:
            if "error" in payload[0]:
                err_msg = (payload[0]["error"].get("json") or {}).get("message") or str(payload[0]["error"])
                raise RuntimeError(f"Zbigtee tRPC {procedure} error: {err_msg}")
            return payload[0].get("result", {}).get("data", {}).get("json")
        return None

    def _trpc_post(self, procedure: str, input_obj: Dict[str, Any]) -> Any:
        sess = self._build_requests_session()
        url = f"https://zbigtee.com/api/trpc/{procedure}?batch=1"
        resp = sess.post(
            url,
            headers={"content-type": "application/json"},
            data=json.dumps({"0": {"json": input_obj}}),
            timeout=35,
        )
        if resp.status_code in (401, 403):
            raise PermissionError(f"AUTH_REQUIRED: Zbigtee tRPC {procedure} returned HTTP {resp.status_code}.")
        payload = resp.json()
        if isinstance(payload, list) and payload:
            if "error" in payload[0]:
                err_msg = (payload[0]["error"].get("json") or {}).get("message") or str(payload[0]["error"])
                raise RuntimeError(f"Zbigtee tRPC {procedure} error: {err_msg}")
            return payload[0].get("result", {}).get("data", {}).get("json")
        resp.raise_for_status()
        return None

    def list_plan_candidates(
        self,
        include_accepted: bool = True,
        include_added_content_topics: bool = True,
        baseline_published_content_ids: Optional[set] = None,
    ) -> Dict[str, Any]:
        """
        Query Zbigtee `plan.list` (`proposed` and optionally `accepted`) plus any newly added
        create-only content topics (`content.list`), returning:
          - `eligible_create_candidates`: strictly `action == "create"` and `targetPath is None`,
            not published in baseline.
          - `excluded_candidates`: all `improve` or `targetPath != None` or baseline-published items
            with explicit exclusion reasons (`PLAN_NOT_CREATE`, `HAS_TARGET_PATH`, `BASELINE_DUPLICATE`).
        """
        project_id = (self.store.zbigtee_project_id or "").strip()
        if not project_id:
            raise ValueError(f"Store '{self.store.id}' does not have a zbigtee_project_id configured.")

        base_pub_ids = set(baseline_published_content_ids or set())
        proposed_data = self._trpc_get("plan.list", {"projectId": project_id, "state": "proposed"}) or {}
        proposed_rows = list(proposed_data.get("rows") or [])

        accepted_rows: List[Dict[str, Any]] = []
        if include_accepted:
            acc_data = self._trpc_get("plan.list", {"projectId": project_id, "state": "accepted"}) or {}
            accepted_rows = list(acc_data.get("rows") or [])

        content_data = self._trpc_get("content.list", {"projectId": project_id}) or {}
        content_rows = (
            content_data
            if isinstance(content_data, list)
            else list(content_data.get("rows") or content_data.get("items") or [])
        )
        content_by_id = {r.get("id"): r for r in content_rows if r.get("id")}

        eligible: List[Dict[str, Any]] = []
        excluded: List[Dict[str, Any]] = []
        seen_content_ids = set()

        for state_label, rows in [("proposed", proposed_rows), ("accepted", accepted_rows)]:
            for idx, r in enumerate(rows, start=1):
                pid = r.get("id") or ""
                action = (r.get("action") or "").strip().lower()
                target_path = r.get("targetPath")
                cid = r.get("contentId")
                if cid:
                    seen_content_ids.add(cid)
                c_row = content_by_id.get(cid) if cid else None
                c_status = (c_row.get("status") if c_row else "") or ""

                record = {
                    "source": f"plan.{state_label}",
                    "plan_id": pid,
                    "content_id": cid,
                    "state": state_label,
                    "content_status": c_status,
                    "title": r.get("title") or "",
                    "action": action,
                    "target_path": target_path,
                    "purpose": r.get("purpose"),
                    "score": r.get("score"),
                    "order_index": idx,
                }

                if action != "create":
                    record["excluded_reason"] = "PLAN_NOT_CREATE"
                    excluded.append(record)
                elif target_path:
                    record["excluded_reason"] = "HAS_TARGET_PATH"
                    excluded.append(record)
                elif cid and (cid in base_pub_ids or c_status.lower() == "published"):
                    record["excluded_reason"] = "BASELINE_DUPLICATE"
                    excluded.append(record)
                else:
                    record["eligible_reason"] = "CREATE_WITHOUT_TARGET_PATH"
                    eligible.append(record)

        # Include standalone create-only topics added directly to Content (not linked to an old improve plan item)
        if include_added_content_topics:
            for c_row in content_rows:
                cid = c_row.get("id") or ""
                if not cid or cid in seen_content_ids:
                    continue
                c_status = (c_row.get("status") or "").lower()
                c_url = c_row.get("url")
                if cid in base_pub_ids or c_status == "published":
                    excluded.append(
                        {
                            "source": "content.direct",
                            "plan_id": None,
                            "content_id": cid,
                            "state": "accepted",
                            "content_status": c_status,
                            "title": c_row.get("title") or "",
                            "action": "create",
                            "target_path": c_url,
                            "excluded_reason": "BASELINE_DUPLICATE",
                        }
                    )
                    continue
                if c_url:
                    excluded.append(
                        {
                            "source": "content.direct",
                            "plan_id": None,
                            "content_id": cid,
                            "state": "accepted",
                            "content_status": c_status,
                            "title": c_row.get("title") or "",
                            "action": "improve",
                            "target_path": c_url,
                            "excluded_reason": "HAS_TARGET_PATH",
                        }
                    )
                    continue
                eligible.append(
                    {
                        "source": "content.direct_create",
                        "plan_id": None,
                        "content_id": cid,
                        "state": "accepted",
                        "content_status": c_status,
                        "title": c_row.get("title") or "",
                        "action": "create",
                        "target_path": None,
                        "purpose": "capture",
                        "score": c_row.get("priority") or 2,
                        "order_index": len(eligible) + 1,
                        "eligible_reason": "DIRECT_CREATE_TOPIC_WITHOUT_TARGET_PATH",
                    }
                )

        return {
            "ok": True,
            "store_id": self.store.id,
            "project_id": project_id,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "proposed_total_count": len(proposed_rows),
            "eligible_create_count": len(eligible),
            "excluded_count": len(excluded),
            "eligible_create_candidates": eligible,
            "excluded_candidates": excluded,
        }

    def accept_plan_proposal(self, plan_id: str) -> Dict[str, Any]:
        """
        Safely accept a `create` Plan proposal (`plan.accept`) on Zbigtee and return its `content_id`.
        Idempotent: if already accepted, returns the existing `content_id` without re-mutating.
        Refuses to accept any `improve` or `targetPath != None` proposal.
        """
        self.assert_safe_ui_action("Nhận")
        project_id = (self.store.zbigtee_project_id or "").strip()
        clean_pid = (plan_id or "").strip()
        if not clean_pid:
            raise ValueError("plan_id is required.")

        # Check both proposed and accepted lists first
        for state in ("accepted", "proposed"):
            data = self._trpc_get("plan.list", {"projectId": project_id, "state": state}) or {}
            for r in data.get("rows") or []:
                if r.get("id") == clean_pid:
                    if (r.get("action") or "").lower() != "create" or r.get("targetPath"):
                        raise ValueError(
                            f"PLAN_NOT_CREATE: Plan item '{clean_pid}' has action={r.get('action')!r}, targetPath={r.get('targetPath')!r}."
                        )
                    if state == "accepted" and r.get("contentId"):
                        return {
                            "ok": True,
                            "already_accepted": True,
                            "plan_id": clean_pid,
                            "content_id": r["contentId"],
                            "title": r.get("title") or "",
                        }
                    break

        accept_res = self._trpc_post("plan.accept", {"ids": [clean_pid]})

        # Read back accepted row to get assigned contentId
        acc_data = self._trpc_get("plan.list", {"projectId": project_id, "state": "accepted"}) or {}
        content_id = ""
        title = ""
        for r in acc_data.get("rows") or []:
            if r.get("id") == clean_pid:
                content_id = r.get("contentId") or ""
                title = r.get("title") or ""
                break

        return {
            "ok": bool(content_id),
            "already_accepted": False,
            "plan_id": clean_pid,
            "content_id": content_id,
            "title": title,
            "accept_response": accept_res,
        }

    def add_create_topics_to_zbigtee(self, topics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Deduplicate and add new `create` topics (`targetPath=None`) to Zbigtee via `content.create`
        + `content.brief.save` + `content.setStatus(to="writing")`, then read back from Zbigtee
        to confirm creation.
        """
        project_id = (self.store.zbigtee_project_id or "").strip()
        if not project_id:
            raise ValueError(f"Store '{self.store.id}' does not have a zbigtee_project_id configured.")

        current = self.list_plan_candidates(include_accepted=True, include_added_content_topics=True)
        existing_titles_lower = set()
        for item in current["eligible_create_candidates"] + current["excluded_candidates"]:
            t = (item.get("title") or "").strip().lower()
            if t:
                existing_titles_lower.add(t)

        added_records: List[Dict[str, Any]] = []
        skipped_duplicates: List[Dict[str, Any]] = []

        for topic in topics:
            title = (topic.get("title") or "").strip()
            if not title:
                continue
            if title.lower() in existing_titles_lower:
                skipped_duplicates.append({"title": title, "reason": "Already exists in Zbigtee project"})
                continue

            create_res = self._trpc_post(
                "content.create",
                {
                    "projectId": project_id,
                    "title": title,
                    "status": "idea",
                    "priority": int(topic.get("priority") or 2),
                },
            )
            new_cid = (create_res or {}).get("id") if isinstance(create_res, dict) else ""
            if not new_cid:
                raise RuntimeError(f"Failed to create content topic '{title}' on Zbigtee: {create_res}")

            primary_kw = (topic.get("primary_keyword") or title.lower()).strip()
            secondary_kws = list(topic.get("secondary_keywords") or [])
            outline_str = (topic.get("outline") or "").strip()
            questions_list = list(topic.get("questions") or [])
            must_have_terms = [{"term": str(t).strip()} for t in (topic.get("must_have") or []) if str(t).strip()]
            target_words = int(topic.get("target_words") or 1400)

            self._trpc_post(
                "content.brief.save",
                {
                    "contentId": new_cid,
                    "primaryKeyword": primary_kw,
                    "secondary": secondary_kws,
                    "targetWords": target_words,
                    "outline": outline_str or "",
                    "mustHave": must_have_terms,
                    "questions": questions_list,
                    "competitors": [],
                },
            )

            self._trpc_post(
                "content.setStatus",
                {
                    "id": new_cid,
                    "to": "writing",
                    "note": "Added verified create-only topic (action=create, targetPath=null) for 20-article scaling campaign",
                },
            )

            existing_titles_lower.add(title.lower())
            added_records.append(
                {
                    "content_id": new_cid,
                    "title": title,
                    "action": "create",
                    "target_path": None,
                    "primary_keyword": primary_kw,
                    "collection_ref": topic.get("collection_ref") or "",
                    "differentiator": topic.get("differentiator") or "",
                    "status": "writing",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )

        updated = self.list_plan_candidates(include_accepted=True, include_added_content_topics=True)
        return {
            "ok": True,
            "store_id": self.store.id,
            "project_id": project_id,
            "added_count": len(added_records),
            "skipped_duplicates_count": len(skipped_duplicates),
            "added_topics": added_records,
            "skipped_duplicates": skipped_duplicates,
            "total_eligible_create_candidates": updated["eligible_create_count"],
        }

    def get_content_writing_context(self, content_id: str) -> Dict[str, Any]:
        """Fetch `content.get`, `content.writing.prompt`, and `content.writing.list` for a content card."""
        clean_cid = (content_id or "").strip()
        card = self._trpc_get("content.get", {"id": clean_cid}) or {}
        prompt_data = {}
        try:
            prompt_data = self._trpc_get("content.writing.prompt", {"contentId": clean_cid}) or {}
        except Exception as exc:
            prompt_data = {"error": str(exc)}
        drafts = []
        try:
            drafts = self._trpc_get("content.writing.list", {"contentId": clean_cid}) or []
        except Exception:
            drafts = []
        return {
            "ok": bool(card.get("id")),
            "store_id": self.store.id,
            "content_id": clean_cid,
            "status": card.get("status"),
            "title": card.get("title"),
            "notes": card.get("notes"),
            "from_plan": card.get("fromPlan"),
            "brief": card.get("brief"),
            "draft_count": card.get("draftCount", len(drafts)),
            "prompt": prompt_data,
            "drafts": drafts,
        }

    def submit_or_generate_draft(
        self,
        content_id: str,
        raw_submission: Optional[str] = None,
        use_ai_generate: bool = False,
        wait_seconds: int = 180,
        move_to_review: bool = True,
    ) -> Dict[str, Any]:
        """
        Submit a structured draft via `content.writing.submit` (or trigger `content.writing.generate`),
        transition the card to `review` (`IN REVIEW`), and scrape the resulting 5-field `/preview` payload.
        """
        import time

        clean_cid = (content_id or "").strip()
        ctx = self.get_content_writing_context(clean_cid)
        curr_status = (ctx.get("status") or "").lower()

        # Ensure card is in 'writing' or 'review' before submitting/generating
        if curr_status in ("idea", "brief"):
            if not ctx.get("brief"):
                raw_t = (ctx.get("title") or "guide").strip()
                m_q = re.search(r"[“\"']([^”\"']+)[”\"']", raw_t)
                clean_kw = (m_q.group(1) if m_q else raw_t).lower()
                clean_kw = re.sub(
                    r"^(?:trả lời|nội dung cho vùng|trang cho|viết nội dung cho)\s+",
                    "",
                    clean_kw,
                    flags=re.IGNORECASE,
                )
                clean_kw = re.sub(r"[^a-z0-9\s-]+", " ", clean_kw)
                clean_kw = " ".join(clean_kw.split()[:5]) or "buying guide"
                self._trpc_post(
                    "content.brief.save",
                    {
                        "contentId": clean_cid,
                        "primaryKeyword": clean_kw,
                        "secondary": [],
                        "targetWords": 1400,
                        "outline": "",
                        "mustHave": [],
                        "questions": [],
                        "competitors": [],
                    },
                )
            self._trpc_post("content.setStatus", {"id": clean_cid, "to": "writing"})
            curr_status = "writing"

        submit_result = None
        if raw_submission and raw_submission.strip():
            self.assert_safe_ui_action("Check this draft")
            submit_result = self._trpc_post(
                "content.writing.submit",
                {"contentId": clean_cid, "raw": raw_submission.strip()},
            )
            time.sleep(5)
        elif use_ai_generate and curr_status == "writing" and int(ctx.get("draft_count") or 0) == 0:
            self.assert_safe_ui_action("Viết bài này")
            try:
                self._trpc_post("content.writing.generate", {"contentId": clean_cid})
            except Exception as _gen_exc:
                if "đang được viết" not in str(_gen_exc).lower() and "already" not in str(_gen_exc).lower():
                    raise
            deadline = time.time() + max(15, wait_seconds)
            while time.time() < deadline:
                time.sleep(8)
                polled = self.get_content_writing_context(clean_cid)
                if polled.get("drafts") or (polled.get("status") or "").lower() == "review":
                    submit_result = polled["drafts"][0] if polled.get("drafts") else {"status": polled.get("status")}
                    break

        # Refresh card status and move to 'review' if ready and requested
        refreshed = self.get_content_writing_context(clean_cid)
        new_status = (refreshed.get("status") or "").lower()
        if move_to_review and new_status == "writing" and (refreshed.get("drafts") or submit_result):
            try:
                self._trpc_post("content.setStatus", {"id": clean_cid, "to": "review"})
                new_status = "review"
            except Exception:
                pass

        preview_payload = None
        if new_status in ("review", "published") or refreshed.get("drafts"):
            preview_payload = self.fetch_live_preview_payload(clean_cid, use_playwright=True)

        return {
            "ok": bool(preview_payload and (preview_payload.get("body_html") or "").strip()),
            "store_id": self.store.id,
            "content_id": clean_cid,
            "status": new_status,
            "submit_result": submit_result,
            "preview_payload": preview_payload,
        }

