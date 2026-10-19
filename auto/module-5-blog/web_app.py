"""
Local Multi-Store Web Application (`web_app.py`) — Atlassian Design System (ADS) Edition.

Provides:
  - `/`         : Full-width Jira/Confluence-inspired Multi-Store Workspace (Global Top Bar,
                  Project Sidebar, Breadcrumbs, Zbigtee Issue/Content Backlog, 5-field Inspector,
                  1-click Sync to Shopify, and 12-point Live Verification Report).
  - `/settings` : Atlassian Project & Store Credentials Administration (`data/stores/<id>.json`
                  CRUD, OAuth token exchange test & automatic Shopify Blog category fetch).
  - `/diagram`  : Interactive Swimlane Architecture Diagram (`diagram-pipeline.html`).
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, unquote, urlparse

from pipeline import BlogSyncPipeline
from store_manager import StoreManager, slugify_store_id
from store_profile_manager import StoreProfileManager, StoreProfileValidationError
from zbigtee_ui_operator import ZbigteeUiOperator

MODULE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = MODULE_DIR / "output"

ATLASSIAN_COMMON_CSS = """
  :root {
    --ds-surface: #FFFFFF;
    --ds-surface-sunken: #F7F8F9;
    --ds-surface-raised: #FFFFFF;
    --ds-surface-hovered: #F1F2F4;
    --ds-text: #172B4D;
    --ds-text-subtle: #44546F;
    --ds-text-subtlest: #626F86;
    --ds-text-brand: #0C66E4;
    --ds-border: #DCDFE4;
    --ds-border-input: #DFE1E6;
    --ds-border-focused: #0C66E4;
    --ds-bg-brand-bold: #0C66E4;
    --ds-bg-brand-bold-hover: #0055CC;
    --ds-bg-brand-subtlest: #E9F2FF;
    --ds-bg-neutral: rgba(9, 30, 66, 0.06);
    --ds-bg-neutral-hovered: rgba(9, 30, 66, 0.13);
    --ds-bg-success-subtlest: #DCFFF1;
    --ds-text-success: #216E4E;
    --ds-border-success: #BAF3DB;
    --ds-bg-warning-subtlest: #FFF7D6;
    --ds-text-warning: #7F5F01;
    --ds-border-warning: #F8E6A0;
    --ds-bg-danger-subtlest: #FFECEB;
    --ds-text-danger: #AE2E24;
    --ds-border-danger: #FFD5D2;
    --ds-shadow-raised: 0 1px 1px rgba(9, 30, 66, 0.25), 0 0 1px 1px rgba(9, 30, 66, 0.13);
  }

  * { box-sizing: border-box; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Noto Sans', 'Ubuntu', 'Droid Sans', 'Helvetica Neue', sans-serif;
    background-color: var(--ds-surface-sunken);
    color: var(--ds-text);
    font-size: 14px;
    line-height: 20px;
    margin: 0;
    -webkit-font-smoothing: antialiased;
  }

  code, pre, .ads-mono {
    font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  }

  /* Atlassian Global Top Bar */
  .ads-topbar {
    height: 56px;
    background: var(--ds-surface);
    border-bottom: 1px solid var(--ds-border);
    padding: 0 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 50;
  }

  .ads-nav-link {
    display: inline-flex;
    align-items: center;
    height: 56px;
    padding: 0 12px;
    font-size: 14px;
    font-weight: 500;
    color: var(--ds-text-subtle);
    text-decoration: none;
    border-bottom: 3px solid transparent;
    transition: color 0.15s ease, border-color 0.15s ease, background-color 0.15s ease;
  }
  .ads-nav-link:hover {
    color: var(--ds-text);
    background-color: var(--ds-surface-hovered);
  }
  .ads-nav-link.active {
    color: var(--ds-text-brand);
    border-bottom-color: var(--ds-bg-brand-bold);
    font-weight: 600;
  }

  /* Left Project Sidebar */
  .ads-sidebar {
    width: 248px;
    min-width: 248px;
    background: var(--ds-surface);
    border-right: 1px solid var(--ds-border);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }
  @media (max-width: 1024px) {
    .ads-sidebar { display: none; }
  }

  .ads-side-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    margin: 2px 8px;
    border-radius: 3px;
    font-size: 14px;
    font-weight: 500;
    color: var(--ds-text-subtle);
    text-decoration: none;
    transition: background 0.12s ease, color 0.12s ease;
  }
  .ads-side-item:hover {
    background: var(--ds-surface-hovered);
    color: var(--ds-text);
  }
  .ads-side-item.active {
    background: var(--ds-bg-brand-subtlest);
    color: var(--ds-text-brand);
    font-weight: 600;
  }

  /* Atlassian Cards & Surfaces */
  .ads-card {
    background: var(--ds-surface);
    border: 1px solid var(--ds-border);
    border-radius: 3px;
  }
  .ads-issue-card {
    background: var(--ds-surface);
    border-radius: 3px;
    box-shadow: var(--ds-shadow-raised);
    padding: 12px;
    cursor: pointer;
    border: 1.5px solid transparent;
    transition: background-color 0.12s ease, border-color 0.12s ease, box-shadow 0.12s ease;
  }
  .ads-issue-card:hover {
    background: var(--ds-surface-hovered);
  }
  .ads-issue-card.in-review {
    border-left: 3px solid var(--ds-bg-brand-bold);
  }
  .ads-issue-card.selected {
    background: #E9F2FF;
    border-color: var(--ds-bg-brand-bold);
    border-left: 4px solid var(--ds-bg-brand-bold);
    box-shadow: 0 0 0 1px rgba(12, 102, 228, 0.25);
  }

  /* Atlassian Lozenges (Status Badges) */
  .ads-lozenge {
    display: inline-flex;
    align-items: center;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 11px;
    font-weight: 700;
    line-height: 14px;
    text-transform: uppercase;
    letter-spacing: 0.02em;
    white-space: nowrap;
  }
  .ads-lozenge-neutral { background: #DCDFE4; color: #44546F; }
  .ads-lozenge-inprogress { background: #E9F2FF; color: #0055CC; }
  .ads-lozenge-inprogress-bold { background: #0C66E4; color: #FFFFFF; }
  .ads-lozenge-success { background: #DCFFF1; color: #216E4E; }
  .ads-lozenge-success-bold { background: #1F845A; color: #FFFFFF; }
  .ads-lozenge-warning { background: #FFF7D6; color: #7F5F01; }
  .ads-lozenge-danger { background: #FFECEB; color: #AE2E24; }

  /* Atlassian Buttons */
  .ads-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    height: 32px;
    padding: 0 12px;
    border-radius: 3px;
    font-size: 14px;
    font-weight: 500;
    line-height: 20px;
    border: none;
    cursor: pointer;
    text-decoration: none;
    transition: background-color 0.12s ease, color 0.12s ease;
    white-space: nowrap;
  }
  .ads-btn-primary {
    background-color: var(--ds-bg-brand-bold);
    color: #FFFFFF;
  }
  .ads-btn-primary:hover {
    background-color: var(--ds-bg-brand-bold-hover);
  }
  .ads-btn-subtle {
    background-color: var(--ds-bg-neutral);
    color: var(--ds-text);
  }
  .ads-btn-subtle:hover {
    background-color: var(--ds-bg-neutral-hovered);
  }
  .ads-btn-success {
    background-color: #1F845A;
    color: #FFFFFF;
  }
  .ads-btn-success:hover {
    background-color: #216E4E;
  }
  .ads-btn-danger-subtle {
    background-color: var(--ds-bg-danger-subtlest);
    color: var(--ds-text-danger);
  }
  .ads-btn-danger-subtle:hover {
    background-color: #FFD5D2;
  }

  /* Atlassian Inputs & Selects */
  .ads-label {
    display: block;
    font-size: 12px;
    font-weight: 600;
    color: var(--ds-text-subtle);
    margin-bottom: 4px;
  }
  .ads-input, .ads-select {
    width: 100%;
    height: 36px;
    padding: 6px 8px;
    font-size: 14px;
    color: var(--ds-text);
    background-color: #FAFBFC;
    border: 2px solid var(--ds-border-input);
    border-radius: 3px;
    transition: background-color 0.15s ease, border-color 0.15s ease;
  }
  .ads-input:hover, .ads-select:hover {
    background-color: #EBECF0;
  }
  .ads-input:focus, .ads-select:focus {
    background-color: #FFFFFF;
    border-color: var(--ds-border-focused);
    outline: none;
  }

  /* Section Kicker / Subheader */
  .ads-subhead {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--ds-text-subtlest);
  }

  /* Breadcrumb */
  .ads-breadcrumb {
    font-size: 12px;
    color: var(--ds-text-subtlest);
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 4px;
  }
  .ads-breadcrumb a {
    color: var(--ds-text-subtlest);
    text-decoration: none;
  }
  .ads-breadcrumb a:hover {
    text-decoration: underline;
    color: var(--ds-text-subtle);
  }

  /* Section Message / Banner */
  .ads-banner {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 16px;
    border-radius: 3px;
    font-size: 14px;
  }
  .ads-banner-info { background: var(--ds-bg-brand-subtlest); color: var(--ds-text); border-left: 4px solid var(--ds-bg-brand-bold); }
  .ads-banner-success { background: var(--ds-bg-success-subtlest); color: var(--ds-text); border-left: 4px solid #1F845A; }
  .ads-banner-danger { background: var(--ds-bg-danger-subtlest); color: var(--ds-text-danger); border-left: 4px solid #C9372C; }

  /* Prose inside Confluence-like Article Preview */
  .preview-prose table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }
  .preview-prose th, .preview-prose td { border: 1px solid var(--ds-border); padding: 8px 10px; text-align: left; }
  .preview-prose th { background: var(--ds-surface-sunken); font-weight: 600; color: var(--ds-text-subtle); }
  .preview-prose h2 { font-size: 18px; font-weight: 600; margin-top: 18px; margin-bottom: 8px; color: var(--ds-text); }
  .preview-prose p { margin: 8px 0; line-height: 1.65; color: var(--ds-text); }
"""


def _load_store_dashboard_state(sm: StoreManager, store_id: str) -> Dict[str, Any]:
    store = sm.get_store(store_id)
    zb = ZbigteeUiOperator(sm, store.id)
    board = zb.get_kanban_board()
    previews = zb.list_preview_payloads()

    store_out = OUTPUT_DIR / store.id
    processed_articles = []
    verification_reports = []
    if store_out.exists():
        for p in sorted(store_out.glob("*_processed.json")):
            try:
                processed_articles.append(json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                pass
        for r in sorted(store_out.glob("*_verification_report.json")):
            try:
                verification_reports.append(json.loads(r.read_text(encoding="utf-8")))
            except Exception:
                pass

    return {
        "store": store.to_dict(),
        "proxy": sm.proxy_manager.get_config().to_dict(),
        "zbigtee_auth": ZbigteeUiOperator.get_auth_state(),
        "board": board,
        "previews": previews,
        "processed_articles": processed_articles,
        "verification_reports": verification_reports,
    }


def render_dashboard_html(store: Optional[str] = None) -> str:
    sm = StoreManager()
    if store:
        try:
            sm.set_active_store(store)
        except KeyError:
            pass
    active_id = sm.get_active_store_id()
    all_stores = [s.to_dict() for s in sm.list_stores()]
    state = _load_store_dashboard_state(sm, active_id)

    state_json = json.dumps(
        {
            "active_store_id": active_id,
            "stores": all_stores,
            "state": state,
        },
        ensure_ascii=False,
    ).replace("</", "<\\/")

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Module 5 · Zbigtee × Shopify Blog Sync (Atlassian Workspace)</title>
  <script src="https://unpkg.com/@tailwindcss/browser@4"></script>
  <style>{ATLASSIAN_COMMON_CSS}</style>
</head>
<body class="min-h-screen flex flex-col">
  <!-- Atlassian Global Navigation Bar -->
  <header class="ads-topbar">
    <div class="flex items-center gap-2 h-full">
      <!-- 9-dot App Switcher Icon -->
      <button type="button" title="Atlassian App Switcher" class="w-8 h-8 rounded-[3px] flex items-center justify-center text-[#44546F] hover:bg-[#F1F2F4]">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
          <circle cx="5" cy="5" r="2"/><circle cx="12" cy="5" r="2"/><circle cx="19" cy="5" r="2"/>
          <circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/>
          <circle cx="5" cy="19" r="2"/><circle cx="12" cy="19" r="2"/><circle cx="19" cy="19" r="2"/>
        </svg>
      </button>

      <!-- Brand Logo -->
      <a href="/" class="flex items-center gap-2.5 pr-3 text-[#172B4D] font-semibold text-[15px] no-underline">
        <span class="w-7 h-7 rounded-[3px] bg-[#0C66E4] text-white flex items-center justify-center font-bold text-xs shadow-xs">
          M5
        </span>
        <span>Content Release Center</span>
      </a>

      <!-- Top Navigation Tabs -->
      <nav class="flex items-center h-full">
        <a href="/" class="ads-nav-link active">Workspace Board</a>
        <a href="/settings" class="ads-nav-link">Project Settings & Credentials</a>
        <a href="/diagram" target="_blank" class="ads-nav-link">Architecture Diagram ↗</a>
      </nav>
    </div>

    <!-- Right Context Controls: Store Switcher -->
    <div class="flex items-center gap-3">
      <span class="ads-subhead hidden sm:inline">Active Store:</span>
      <select id="storeSelector" onchange="handleSwitchStore(this.value)"
              class="ads-select !w-auto !h-8 !py-0 !px-2.5 font-medium text-[13px] cursor-pointer">
      </select>
      <button type="button" id="topFetchLiveBtn" onclick="runFetchLiveZbigtee()" class="ads-btn ads-btn-subtle">
        ↻ Fetch Live từ Zbigtee
      </button>
      <a href="/settings" class="ads-btn ads-btn-primary">+ Add / Edit Store</a>
    </div>
  </header>

  <!-- Full-Width Workspace Body (Sidebar + Full-Width Main without max-w-7xl) -->
  <div class="flex flex-1 w-full">
    <!-- Jira-style Project Sidebar -->
    <aside class="ads-sidebar">
      <div class="py-4">
        <div class="px-4 pb-3 border-b border-[#DCDFE4] mb-2">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-[3px] bg-[#E9F2FF] text-[#0C66E4] flex items-center justify-center font-bold text-sm" id="sidebarStoreAvatar">
              W
            </div>
            <div class="min-w-0">
              <div class="font-semibold text-[14px] text-[#172B4D] truncate" id="sidebarStoreName">WRYDECO</div>
              <div class="text-[11px] text-[#626F86] truncate" id="sidebarStoreDomain">Shopify Blog Project</div>
            </div>
          </div>
        </div>

        <div class="px-4 py-1.5 ads-subhead">Planning & Sync</div>
        <a href="/" class="ads-side-item active">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="18" rx="1"/><rect x="14" y="3" width="7" height="11" rx="1"/></svg>
          <span>Zbigtee Release Board</span>
        </a>
        <a href="/settings" class="ads-side-item">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c.26.604.852.997 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
          <span>Store Credentials</span>
        </a>
        <a href="/diagram" target="_blank" class="ads-side-item">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M3 12h18M3 18h18"/></svg>
          <span>10-Step Swimlane Spec</span>
        </a>

        <div class="px-4 pt-5 pb-1.5 ads-subhead">Safety Guardrails</div>
        <div class="mx-3 p-2.5 rounded-[3px] bg-[#DCFFF1] border border-[#BAF3DB] text-[12px] text-[#216E4E]">
          <div class="font-semibold">Read-Only Zbigtee Mode</div>
          <div class="mt-0.5 text-[11px] leading-4">Blocked destructive actions: Cancel item, Trả về kế hoạch, Request changes.</div>
        </div>
        <div class="mx-3 mt-2 p-2.5 rounded-[3px] bg-[#E9F2FF] border border-[#B3D4FF] text-[12px] text-[#0055CC]">
          <div class="font-semibold">Mandatory Shopify Proxy</div>
          <div class="mt-0.5 text-[11px] leading-4">All Shopify traffic routed via <code>data/proxy.json</code>. Auto-blocked if unstable.</div>
        </div>
      </div>

      <div class="p-3 border-t border-[#DCDFE4] text-[11px] text-[#626F86]">
        <div>All-in-One Local Tool</div>
        <div class="ads-mono text-[10px] mt-0.5">auto/module-5-blog/</div>
      </div>
    </aside>

    <!-- Full-Width Main Workspace (NO max-w-7xl) -->
    <main class="w-full flex-1 px-6 py-5 space-y-5 min-w-0">
      <!-- Project Header & Active Store Banner -->
      <section id="storeBanner" class="ads-card p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
      </section>

      <!-- Atlassian Section Message Toast -->
      <div id="statusToast" class="hidden"></div>

      <!-- Full-Width 12-Column Split Workspace -->
      <div class="grid grid-cols-1 xl:grid-cols-12 gap-5 items-start">
        <!-- Left Column: Jira-style Backlog / Kanban List (4 cols on XL) -->
        <div class="xl:col-span-4 space-y-3">
          <div class="ads-card p-4">
            <div class="flex items-center justify-between pb-3 mb-3 border-b border-[#DCDFE4] gap-2">
              <div>
                <div class="ads-subhead">ZBIGTEE CONTENT BACKLOG</div>
                <h2 class="text-[15px] font-semibold text-[#172B4D] mt-0.5">Danh sách bài viết trên Zbigtee</h2>
                <p class="text-[12px] text-[#626F86]" id="zbigteeProjectSub"></p>
              </div>
              <div class="flex items-center gap-1.5 shrink-0">
                <button type="button" id="btnFetchLiveZbigtee" onclick="runFetchLiveZbigtee()" class="ads-btn ads-btn-primary !h-7 !px-2.5 !text-[12px]">
                  ↻ Fetch Live từ Zbigtee
                </button>
                <span id="kanbanCountBadge" class="ads-lozenge ads-lozenge-inprogress"></span>
              </div>
            </div>
            <div id="kanbanList" class="space-y-2.5 max-h-[720px] overflow-y-auto pr-1 bg-[#F7F8F9] p-2.5 rounded-[3px] border border-[#DCDFE4]"></div>
          </div>
        </div>

        <!-- Right Column: Issue Detail / Confluence Release & Verification Inspector (8 cols on XL) -->
        <div class="xl:col-span-8 space-y-5">
          <div id="articleActionCard" class="ads-card p-5">
          </div>

          <div id="verificationCard" class="ads-card p-5">
          </div>
        </div>
      </div>
    </main>
  </div>

  <!-- Comprehensive Blog Post Update Modal (Atlassian Design System Dialog) -->
  <div id="updateArticleModal" class="hidden fixed inset-0 z-[100] bg-[#091E42]/60 backdrop-blur-[1px] flex items-center justify-center p-4 overflow-y-auto">
    <div class="ads-card w-full max-w-[1180px] max-h-[92vh] flex flex-col shadow-2xl border border-[#DCDFE4] bg-white rounded-[4px] overflow-hidden">
      <!-- Modal Header -->
      <div class="px-6 py-4 border-b border-[#DCDFE4] bg-[#F7F8F9] flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div>
          <div class="flex items-center gap-2">
            <span class="ads-subhead !text-[#0C66E4]">COMPREHENSIVE BLOG POST EDITOR</span>
            <span id="upd_live_badge" class="ads-lozenge ads-lozenge-neutral">LOCAL DRAFT</span>
          </div>
          <h2 class="text-[18px] font-semibold text-[#172B4D] mt-0.5" id="upd_modal_heading">Update Blog Post</h2>
        </div>
        <div class="flex items-center gap-2">
          <button type="button" id="btnFetchLiveEditor" onclick="reloadUpdateModalFromLiveShopify()" class="ads-btn ads-btn-subtle !h-8 !text-[12px]">
            ↻ Nạp dữ liệu đang Live trên Shopify
          </button>
          <button type="button" onclick="closeUpdateModal()" class="ads-btn ads-btn-subtle !w-8 !h-8 !p-0 text-[16px]" title="Đóng (Esc)">
            ✕
          </button>
        </div>
      </div>

      <!-- Modal Status Banner -->
      <div id="upd_modal_toast" class="hidden mx-6 mt-4 shrink-0"></div>

      <!-- Modal Scrollable Body -->
      <div class="p-6 overflow-y-auto flex-1 space-y-6">
        <input type="hidden" id="upd_content_id" />
        <input type="hidden" id="upd_previous_handle" />

        <!-- Section 1: Title, Handle, Blog Category, Visibility, Author & Tags -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div class="lg:col-span-8 space-y-4">
            <div>
              <label class="ads-label" for="upd_title">1. Article Title (Tiêu đề bài viết H1) <span class="text-[#AE2E24]">*</span></label>
              <input id="upd_title" type="text" class="ads-input font-semibold !text-[15px]" placeholder="Nhập tiêu đề bài viết..." oninput="updateSeoSerpPreview()" />
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="ads-label" for="upd_handle">URL Handle / Slug <span class="text-[#AE2E24]">*</span></label>
                <input id="upd_handle" type="text" class="ads-input ads-mono !text-[13px]" placeholder="tote-bag-for-laptop-and-water-bottle" oninput="updateSeoSerpPreview()" />
              </div>
              <div>
                <label class="ads-label" for="upd_author">Author (Tác giả)</label>
                <input id="upd_author" type="text" class="ads-input" placeholder="PREAUREUM Studio" />
              </div>
            </div>

            <div>
              <label class="ads-label" for="upd_summary">2. Excerpt / Summary (Đoạn tóm tắt ngắn hiển thị ở trang danh sách Blog)</label>
              <textarea id="upd_summary" rows="2" class="ads-input !h-auto py-2 leading-5" placeholder="Nhập đoạn trích ngắn (Excerpt)..."></textarea>
            </div>
          </div>

          <!-- Right Sidebar Box: Visibility, Target Blog & Tags -->
          <div class="lg:col-span-4 space-y-3.5 bg-[#F7F8F9] p-4 rounded-[3px] border border-[#DCDFE4]">
            <div>
              <label class="ads-label" for="upd_visibility">Visibility (Trạng thái hiển thị)</label>
              <select id="upd_visibility" class="ads-select font-semibold">
                <option value="true">● Visible (Published — Công khai)</option>
                <option value="false">○ Hidden (Draft — Ẩn / Bản nháp)</option>
              </select>
            </div>

            <div>
              <label class="ads-label" for="upd_blog_handle">Target Blog Category (Danh mục Blog)</label>
              <select id="upd_blog_handle" class="ads-select font-medium" onchange="updateSeoSerpPreview()">
              </select>
              <p class="text-[11px] text-[#626F86] mt-1 leading-4">
                Nếu đổi sang Blog khác (ví dụ <code>news</code> → <code>gift-guide</code>), hệ thống sẽ tự động chuyển bài sang Blog mới và xóa bản cũ.
              </p>
            </div>

            <div>
              <label class="ads-label" for="upd_tags">Tags (Phân cách bằng dấu phẩy)</label>
              <input id="upd_tags" type="text" class="ads-input !text-[13px]" placeholder="buying guide, tote bag, laptop bag" />
            </div>
          </div>
        </div>

        <!-- Section 2: Featured Cover Image (Ảnh bìa) -->
        <div class="p-4 rounded-[3px] border border-[#DCDFE4] bg-[#FAFBFC] space-y-3">
          <div class="flex items-center justify-between">
            <div class="ads-subhead !text-[#172B4D]">3. FEATURED COVER IMAGE (ẢNH BÌA ĐẠI DIỆN BÀI VIẾT)</div>
            <span class="text-[11px] text-[#626F86]">Click vào ảnh bên dưới để chọn nhanh từ kho ảnh sản phẩm của bài</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-12 gap-4 items-start">
            <div class="md:col-span-3 flex flex-col items-center justify-center bg-white border border-[#DCDFE4] rounded-[3px] p-2 min-h-[136px]">
              <img id="upd_hero_preview_img" src="" alt="Cover preview" class="max-h-[128px] w-auto object-contain rounded-[2px] hidden" onload="this.classList.remove('hidden'); document.getElementById('upd_hero_empty').classList.add('hidden');" onerror="this.classList.add('hidden'); document.getElementById('upd_hero_empty').classList.remove('hidden');" />
              <div id="upd_hero_empty" class="text-[12px] text-[#626F86] text-center py-6">Chưa có ảnh bìa hợp lệ</div>
            </div>

            <div class="md:col-span-9 space-y-3">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label class="ads-label" for="upd_featured_url">Featured Image URL (Shopify CDN / HTTPS) <span class="text-[#AE2E24]">*</span></label>
                  <input id="upd_featured_url" type="url" class="ads-input ads-mono !text-[12px]" placeholder="https://cdn.shopify.com/s/files/..." oninput="syncHeroPreviewFromInput()" />
                </div>
                <div>
                  <label class="ads-label" for="upd_featured_alt">Image Alt Text (Mô tả ảnh SEO)</label>
                  <input id="upd_featured_alt" type="text" class="ads-input !text-[13px]" placeholder="Mô tả alt text cho ảnh bìa..." />
                </div>
              </div>

              <div>
                <div class="text-[11px] font-semibold text-[#44546F] mb-1.5">Chọn nhanh từ Shop Images của bài viết:</div>
                <div id="upd_shop_images_strip" class="flex items-center gap-2 overflow-x-auto pb-1"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Section 3: Search Engine Listing / SEO Metafields -->
        <div class="p-4 rounded-[3px] border border-[#DCDFE4] bg-[#FAFBFC] space-y-3">
          <div class="ads-subhead !text-[#172B4D]">4. SEARCH ENGINE LISTING PREVIEW (SEO METAFIELDS · GLOBAL.TITLE_TAG & DESCRIPTION_TAG)</div>

          <!-- Google SERP Live Preview -->
          <div class="p-3 bg-white rounded-[3px] border border-[#DCDFE4]">
            <div class="text-[12px] text-[#202124] truncate" id="upd_serp_url">https://store.com › blogs › news › slug</div>
            <div class="text-[16px] text-[#1a0dab] font-medium truncate mt-0.5" id="upd_serp_title">Article SEO Title</div>
            <div class="text-[13px] text-[#4d5156] line-clamp-2 mt-0.5" id="upd_serp_desc">Article SEO meta description preview...</div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <div class="flex items-center justify-between">
                <label class="ads-label" for="upd_seo_title">SEO Page Title</label>
                <span id="upd_seo_title_count" class="text-[11px] text-[#626F86] ads-mono">0 / 70 chars</span>
              </div>
              <input id="upd_seo_title" type="text" class="ads-input" placeholder="Tiêu đề SEO..." oninput="updateSeoSerpPreview()" />
            </div>
            <div>
              <div class="flex items-center justify-between">
                <label class="ads-label" for="upd_seo_desc">SEO Meta Description</label>
                <span id="upd_seo_desc_count" class="text-[11px] text-[#626F86] ads-mono">0 / 160 chars</span>
              </div>
              <textarea id="upd_seo_desc" rows="2" class="ads-input !h-auto py-1.5 leading-5" placeholder="Mô tả SEO (khuyến nghị 120–160 ký tự)..." oninput="updateSeoSerpPreview()"></textarea>
            </div>
          </div>
        </div>

        <!-- Section 4: Article Content (Body HTML + Visual Rich Editor) -->
        <div class="space-y-2">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <label class="ads-label !mb-0">5. Article Body Content (Nội dung bài viết — Hỗ trợ sửa trực quan hoặc mã HTML)</label>
            <div class="inline-flex rounded-[3px] border border-[#DCDFE4] bg-[#F1F2F4] p-0.5">
              <button type="button" id="tabBtnVisual" onclick="switchEditorTab('visual')" class="px-3 py-1 rounded-[2px] text-[12px] font-semibold bg-white text-[#0C66E4] shadow-xs cursor-pointer">
                Visual Editor (Trực quan)
              </button>
              <button type="button" id="tabBtnHtml" onclick="switchEditorTab('html')" class="px-3 py-1 rounded-[2px] text-[12px] font-medium text-[#44546F] cursor-pointer">
                HTML Source Code
              </button>
            </div>
          </div>

          <div id="upd_body_visual" contenteditable="true" oninput="syncBodyFromVisual()"
               class="p-5 bg-white rounded-[3px] border-2 border-[#DFE1E6] focus:border-[#0C66E4] focus:outline-none max-h-[420px] min-h-[260px] overflow-y-auto preview-prose">
          </div>

          <textarea id="upd_body_html" rows="14" oninput="syncBodyFromHtml()"
                    class="hidden w-full p-3 bg-[#172B4D] text-[#F7F8F9] ads-mono text-[12px] leading-5 rounded-[3px] border-2 border-[#0C66E4] focus:outline-none">
          </textarea>
        </div>
      </div>

      <!-- Modal Footer Actions -->
      <div class="px-6 py-3.5 border-t border-[#DCDFE4] bg-[#F7F8F9] flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div class="text-[12px] text-[#626F86]">
          Guardrail: Tự động chặn nếu thiếu ảnh bìa hoặc còn sót <code>[IMAGE: ...]</code> (đã tắt render SVG).
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <button type="button" onclick="closeUpdateModal()" class="ads-btn ads-btn-subtle">
            Cancel
          </button>
          <button type="button" id="btnSaveLocalOnly" onclick="submitComprehensiveUpdate('local')" class="ads-btn ads-btn-subtle">
            💾 Lưu Bản Nháp Local
          </button>
          <button type="button" id="btnPushShopifyOnly" onclick="submitComprehensiveUpdate('shopify')" class="ads-btn ads-btn-primary">
            ☁ Update lên Shopify
          </button>
          <button type="button" id="btnPushAndVerify" onclick="submitComprehensiveUpdate('verify')" class="ads-btn ads-btn-success">
            ✓ Update lên Shopify & Verify Live (12/12)
          </button>
        </div>
      </div>
    </div>
  </div>

  <script>
    const APP_DATA = {state_json};
    let SELECTED_CONTENT_ID = new URLSearchParams(window.location.search).get('article') || '';

    function resolveInitialSelectedContentId() {{
      const items = (APP_DATA.state.board && APP_DATA.state.board.items) || [];
      const previews = APP_DATA.state.previews || [];
      if (SELECTED_CONTENT_ID && items.some(i => i.content_id === SELECTED_CONTENT_ID)) {{
        return SELECTED_CONTENT_ID;
      }}
      const firstWithPreview = items.find(i =>
        previews.some(p => p.content_id === i.content_id || (i.slug && p.slug === i.slug))
      );
      if (firstWithPreview) {{
        SELECTED_CONTENT_ID = firstWithPreview.content_id;
      }} else if (previews.length > 0) {{
        SELECTED_CONTENT_ID = previews[0].content_id;
      }} else if (items.length > 0) {{
        SELECTED_CONTENT_ID = items[0].content_id;
      }}
      return SELECTED_CONTENT_ID;
    }}

    function selectArticle(contentId) {{
      SELECTED_CONTENT_ID = contentId;
      const url = new URL(window.location.href);
      url.searchParams.set('store', APP_DATA.active_store_id);
      url.searchParams.set('article', contentId);
      window.history.replaceState(null, '', url.toString());
      renderKanbanCards(APP_DATA.state.store, (APP_DATA.state.board && APP_DATA.state.board.items) || []);
      renderActionAndVerification(APP_DATA.state.store);
    }}

    function showToast(msg, isError = false) {{
      const el = document.getElementById('statusToast');
      el.className = isError ? 'ads-banner ads-banner-danger' : 'ads-banner ads-banner-info';
      el.innerHTML = `
        <span class="font-bold">${{isError ? 'ERROR' : 'INFO'}}</span>
        <div class="flex-1">${{msg}}</div>
      `;
      el.classList.remove('hidden');
    }}

    async function handleSwitchStore(storeId) {{
      window.location.href = '/?store=' + encodeURIComponent(storeId);
    }}

    async function runFetchLiveZbigtee() {{
      showToast('Đang mở Playwright Headless + phiên đăng nhập <code>data/zbigtee_auth.json</code> để cào trực tiếp Kanban & trang /preview từ <strong>zbigtee.com</strong>...');
      const res = await fetch('/api/zbigtee/fetch-live', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ store_id: APP_DATA.active_store_id }})
      }});
      const data = await res.json();
      if (!data.ok) {{
        showToast('Lỗi cào dữ liệu từ Zbigtee: ' + (data.error || 'Unknown error'), true);
        return;
      }}
      showToast(`Đã cào trực tiếp từ <strong>zbigtee.com</strong> thành công: <strong>${{data.total_kanban_items}}</strong> thẻ Kanban (${{data.in_review_count}} In Review, ${{data.published_count || 0}} Published, đã tải ${{data.fetched_previews.length}} gói /preview)!`);
      setTimeout(() => window.location.reload(), 800);
    }}

    function renderKanbanCards(store, items) {{
      const kanbanEl = document.getElementById('kanbanList');
      if (!items.length) {{
        kanbanEl.innerHTML = `<div class="p-6 text-center text-[13px] text-[#626F86] bg-white rounded-[3px] border border-dashed border-[#DCDFE4]">Chưa có bài viết nào được đồng bộ cho store <strong>${{store.name}}</strong>. Bấm <strong>Fetch Live từ Zbigtee</strong> để cào dữ liệu mới nhất.</div>`;
        return;
      }}
      kanbanEl.innerHTML = items.map((item, idx) => {{
        const colUpper = (item.column || '').toUpperCase();
        const isReview = colUpper === 'IN REVIEW';
        const isPublished = colUpper === 'PUBLISHED';
        const isSelected = item.content_id === SELECTED_CONTENT_ID;
        const lozengeClass = isPublished
          ? 'ads-lozenge-success-bold'
          : (isReview ? 'ads-lozenge-inprogress-bold' : 'ads-lozenge-neutral');
        const issueKey = `${{(store.id || 'ZB').slice(0, 3).toUpperCase()}}-${{101 + idx}}`;
        return `
          <div onclick="selectArticle('${{item.content_id}}')" data-content-id="${{item.content_id}}" class="ads-issue-card ${{(isReview || isPublished) ? 'in-review' : ''}} ${{isSelected ? 'selected' : ''}} space-y-2">
            <div class="flex items-start justify-between gap-2">
              <div class="font-medium text-[14px] text-[#172B4D] leading-5">${{item.article_title || item.card_title}}</div>
              <div class="flex items-center gap-1 shrink-0">
                ${{isSelected ? `<span class="ads-lozenge ads-lozenge-inprogress-bold">ĐANG CHỌN</span>` : ''}}
                <span class="ads-lozenge ${{lozengeClass}}">${{item.column}}</span>
              </div>
            </div>
            <div class="flex items-center justify-between gap-2 flex-wrap text-[12px] text-[#626F86] pt-1">
              <div class="flex items-center gap-1.5 min-w-0">
                <span class="inline-flex items-center justify-center w-4 h-4 rounded-[2px] shrink-0 ${{isPublished ? 'bg-[#1F845A]' : (isReview ? 'bg-[#0C66E4]' : 'bg-[#626F86]')}} text-white text-[10px] font-bold">✓</span>
                <span class="ads-mono font-semibold text-[#44546F] whitespace-nowrap">${{issueKey}}</span>
                <span class="text-[#626F86]">·</span>
                <code class="ads-mono text-[11px] text-[#44546F] truncate">${{item.slug || '—'}}</code>
              </div>
              <div class="flex items-center gap-1.5">
                ${{(isReview || isPublished) ? `<button type="button" onclick="event.stopPropagation(); selectArticle('${{item.content_id}}'); openUpdateModal('${{item.content_id}}')" class="px-2 py-0.5 rounded-[3px] text-[11px] font-semibold bg-[#E9F2FF] text-[#0C66E4] hover:bg-[#CCE0FF] cursor-pointer">✎ Update</button>` : ''}}
                <span class="ads-lozenge ${{(isReview || isPublished) ? 'ads-lozenge-success' : 'ads-lozenge-neutral'}}">${{item.quality_gate || 'DRAFT'}}</span>
              </div>
            </div>
            ${{item.shopify_published_url ? `
              <div class="pt-1.5 border-t border-[#F1F2F4] flex items-center justify-between" onclick="event.stopPropagation()">
                <span class="ads-lozenge ads-lozenge-success">${{isPublished || item.zbigtee_marked_published ? 'PUBLISHED ON ZBIGTEE & SHOPIFY' : 'LIVE ON SHOPIFY'}}</span>
                <a href="${{item.shopify_published_url}}" target="_blank" class="text-[12px] font-medium text-[#0C66E4] hover:underline">
                  Open Storefront Article ↗
                </a>
              </div>
            ` : ''}}
          </div>
        `;
      }}).join('');
    }}

    function renderDashboard() {{
      resolveInitialSelectedContentId();

      const selector = document.getElementById('storeSelector');
      selector.innerHTML = APP_DATA.stores.map(s => {{
        const statusTag = s.is_configured ? s.normalized_shop : 'Unconfigured';
        const sel = s.id === APP_DATA.active_store_id ? 'selected' : '';
        return `<option value="${{s.id}}" ${{sel}}>${{s.name}} (${{statusTag}})</option>`;
      }}).join('');

      const store = APP_DATA.state.store;
      const proxy = APP_DATA.state.proxy || {{}};
      const proxyLastCheck = proxy.last_check || {{}};
      const zbAuth = APP_DATA.state.zbigtee_auth || {{}};
      const board = APP_DATA.state.board;
      const summary = board.summary || {{ total: 0, writing: 0, in_review: 0, published: 0 }};

      // Update Sidebar project info
      const avatarEl = document.getElementById('sidebarStoreAvatar');
      const nameEl = document.getElementById('sidebarStoreName');
      const domEl = document.getElementById('sidebarStoreDomain');
      if (avatarEl) avatarEl.textContent = (store.name || 'S').slice(0, 1).toUpperCase();
      if (nameEl) nameEl.textContent = store.name;
      if (domEl) domEl.textContent = store.normalized_shop || store.zbigtee_domain || 'Unconfigured Store';

      const banner = document.getElementById('storeBanner');
      const cfgBadge = store.is_configured
        ? `<span class="ads-lozenge ads-lozenge-success">SHOPIFY · ${{store.normalized_shop}}</span>`
        : `<span class="ads-lozenge ads-lozenge-warning">SHOPIFY CREDENTIALS REQUIRED</span>`;
      const zbBadge = zbAuth.exists
        ? `<span class="ads-lozenge ads-lozenge-inprogress">ZBIGTEE AUTH · ${{zbAuth.auth_file}} (${{zbAuth.masked_token}})</span>`
        : `<span class="ads-lozenge ads-lozenge-danger">ZBIGTEE AUTH MISSING</span>`;
      const proxyBadge = (!proxy.is_configured || proxyLastCheck.stable === false)
        ? `<a href="/settings" class="ads-lozenge ads-lozenge-danger no-underline" id="dashboardProxyBadge">SHOPIFY PROXY BLOCKED · ${{proxy.host || 'UNSET'}}:${{proxy.port || 0}}</a>`
        : `<a href="/settings" class="ads-lozenge ads-lozenge-success-bold no-underline" id="dashboardProxyBadge">SHOPIFY PROXY · ${{proxy.host}}:${{proxy.port}} ${{proxyLastCheck.avg_latency_ms ? '(' + proxyLastCheck.avg_latency_ms + 'ms)' : ''}}</a>`;

      banner.innerHTML = `
        <div class="space-y-1.5">
          <div class="ads-breadcrumb">
            <a href="/">Projects</a> <span>/</span>
            <a href="/?store=${{store.id}}">${{store.name}}</a> <span>/</span>
            <span>Blog Release Pipeline</span>
          </div>
          <div class="flex items-center gap-2 flex-wrap">
            <h1 class="text-[20px] font-semibold text-[#172B4D] tracking-tight">Store: ${{store.name}}</h1>
            ${{cfgBadge}}
            ${{proxyBadge}}
            ${{zbBadge}}
            <span class="ads-lozenge ads-lozenge-neutral ads-mono">data/${{store.config_file}}</span>
          </div>
          <p class="text-[12px] text-[#44546F]">
            Zbigtee Domain: <strong class="text-[#172B4D]">${{store.zbigtee_domain || '—'}}</strong> ·
            Project ID: <code class="ads-mono bg-[#F1F2F4] px-1.5 py-0.5 rounded-[3px] text-[#172B4D]">${{store.zbigtee_project_id || '—'}}</code> ·
            Target Blog Handle: <strong class="text-[#0C66E4]">${{store.default_blog_handle || 'buying-guides'}}</strong>
          </p>
        </div>

        <div class="flex items-center gap-2.5 flex-wrap">
          <div class="flex items-center divide-x divide-[#DCDFE4] bg-[#F7F8F9] border border-[#DCDFE4] rounded-[3px]">
            <div class="px-3.5 py-1.5 text-center">
              <div class="ads-subhead">WRITING</div>
              <div class="text-[15px] font-bold text-[#44546F] mt-0.5">${{summary.writing}}</div>
            </div>
            <div class="px-3.5 py-1.5 text-center">
              <div class="ads-subhead !text-[#0055CC]">IN REVIEW</div>
              <div class="text-[15px] font-bold text-[#0C66E4] mt-0.5">${{summary.in_review}}</div>
            </div>
            <div class="px-3.5 py-1.5 text-center">
              <div class="ads-subhead !text-[#216E4E]">PUBLISHED</div>
              <div class="text-[15px] font-bold text-[#216E4E] mt-0.5">${{summary.published}}</div>
            </div>
          </div>
          <button type="button" onclick="runFetchLiveZbigtee()" class="ads-btn ads-btn-primary">
            ↻ Fetch Live từ Zbigtee
          </button>
          <a href="/settings?edit=${{store.id}}" class="ads-btn ads-btn-subtle">
            Configure Credentials
          </a>
        </div>
      `;

      document.getElementById('zbigteeProjectSub').textContent = `Workspace: ${{store.zbigtee_domain || store.name}} (${{summary.total}} issues · Click vào thẻ để chọn bài đồng bộ)`;
      const countBadgeEl = document.getElementById('kanbanCountBadge');
      if (summary.in_review > 0) {{
        countBadgeEl.className = 'ads-lozenge ads-lozenge-inprogress';
        countBadgeEl.textContent = `${{summary.in_review}} IN REVIEW`;
      }} else if (summary.published > 0) {{
        countBadgeEl.className = 'ads-lozenge ads-lozenge-success-bold';
        countBadgeEl.textContent = `${{summary.published}} PUBLISHED`;
      }} else {{
        countBadgeEl.className = 'ads-lozenge ads-lozenge-neutral';
        countBadgeEl.textContent = `0 IN REVIEW`;
      }}

      const items = board.items || [];
      renderKanbanCards(store, items);
      renderActionAndVerification(store);
    }}

    function renderActionAndVerification(store) {{
      const actionEl = document.getElementById('articleActionCard');
      const verEl = document.getElementById('verificationCard');
      const items = (APP_DATA.state.board && APP_DATA.state.board.items) || [];
      const previews = APP_DATA.state.previews || [];
      const processedList = APP_DATA.state.processed_articles || [];
      const reports = APP_DATA.state.verification_reports || [];

      const blogs = store.blogs_cache || [];
      const blogOptions = blogs.length
        ? blogs.map(b => `<option value="${{b.handle}}" ${{b.handle === store.default_blog_handle ? 'selected' : ''}}>${{b.title}} (${{b.handle}})</option>`).join('')
        : `<option value="${{store.default_blog_handle || 'buying-guides'}}">${{store.default_blog_handle || 'buying-guides'}}</option>`;

      const selectedItem = items.find(i => i.content_id === SELECTED_CONTENT_ID) || items[0] || null;
      const preview = previews.find(p =>
        p.content_id === SELECTED_CONTENT_ID ||
        (selectedItem && selectedItem.slug && p.slug === selectedItem.slug)
      ) || (!selectedItem ? previews[0] : null);

      const proc = processedList.find(p =>
        p.content_id === SELECTED_CONTENT_ID ||
        (preview && preview.slug && p.handle === preview.slug) ||
        (selectedItem && selectedItem.slug && p.handle === selectedItem.slug)
      ) || null;

      const rep = reports.find(r =>
        (preview && preview.slug && r.expected_handle === preview.slug) ||
        (selectedItem && selectedItem.slug && r.expected_handle === selectedItem.slug)
      ) || null;

      if (!preview) {{
        if (selectedItem) {{
          actionEl.innerHTML = `
            <div class="ads-subhead">RELEASE INSPECTOR · ${{selectedItem.column}}</div>
            <h2 class="text-[16px] font-semibold text-[#172B4D] mt-1 mb-2">${{selectedItem.article_title || selectedItem.card_title}}</h2>
            <div class="text-[12px] text-[#626F86] mb-3">
              Zbigtee Content ID: <code class="ads-mono bg-[#F1F2F4] px-1.5 py-0.5 rounded-[3px] text-[#172B4D]">${{selectedItem.content_id}}</code> ·
              Trạng thái: <span class="ads-lozenge ads-lozenge-neutral">${{selectedItem.column}}</span>
            </div>
            <div class="ads-banner ads-banner-info">
              <div>Bài viết này hiện đang ở cột <strong>${{selectedItem.column}}</strong> trên Zbigtee nên chưa có gói dữ liệu <code>/preview</code> (5 trường Copy). Hãy chọn một bài ở trạng thái <strong>IN REVIEW</strong> / <strong>PUBLISHED</strong> ở danh sách bên trái, hoặc bấm <strong>Fetch Live từ Zbigtee</strong> sau khi bài viết đã sang cột <em>In review</em>.</div>
            </div>
          `;
        }} else {{
          actionEl.innerHTML = `
            <div class="ads-subhead">RELEASE INSPECTOR</div>
            <h2 class="text-[16px] font-semibold text-[#172B4D] mt-1 mb-2">Trích xuất & Đồng bộ Bài Viết lên Shopify</h2>
            <div class="ads-banner ads-banner-info">
              <div>Store <strong>${{store.name}}</strong> hiện chưa có gói dữ liệu <code>/preview</code> nào ở cột <em>In review</em>. Hãy bấm <strong>Fetch Live từ Zbigtee</strong> để cào dữ liệu mới nhất.</div>
            </div>
          `;
        }}
        verEl.innerHTML = `<div class="text-[13px] text-[#626F86]">Chưa có báo cáo kiểm thử Live cho bài viết này.</div>`;
        return;
      }}

      actionEl.innerHTML = `
        <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-[#DCDFE4]">
          <div class="space-y-1">
            <div class="flex items-center gap-2">
              <span class="ads-lozenge ads-lozenge-success-bold">QUALITY GATE 19/19 PASSED</span>
              <span class="ads-lozenge ads-lozenge-inprogress">5-FIELD PREVIEW EXTRACTED</span>
            </div>
            <h2 class="text-[18px] font-semibold text-[#172B4D] pt-0.5">${{preview.title}}</h2>
            <div class="text-[12px] text-[#626F86]">
              Target Handle: <code class="ads-mono bg-[#F1F2F4] px-1.5 py-0.5 rounded-[3px] text-[#172B4D]">${{preview.slug}}</code> ·
              Zbigtee Content ID: <code class="ads-mono bg-[#F1F2F4] px-1.5 py-0.5 rounded-[3px] text-[#172B4D]">${{preview.content_id}}</code>
            </div>
          </div>
          <div class="flex items-center gap-2 flex-wrap">
            <select id="targetBlogSelect" class="ads-select !w-auto !h-8 !py-0 !px-2.5 text-[13px] font-medium">
              ${{blogOptions}}
            </select>
            <button type="button" onclick="openUpdateModal('${{preview.content_id}}')" class="ads-btn ads-btn-subtle !border !border-[#0C66E4] !text-[#0C66E4] hover:!bg-[#E9F2FF] font-semibold">
              ✎ Update
            </button>
            <button onclick="runPostProcess('${{preview.content_id}}')" class="ads-btn ads-btn-subtle">
              1. Run HTML Post-Processor
            </button>
            <button onclick="runSyncAndPublish('${{preview.content_id}}')" class="ads-btn ads-btn-primary">
              2. Sync to ${{store.name}} & Verify Live
            </button>
          </div>
        </div>

        ${{proc ? `
          <div class="mt-4 space-y-4">
            ${{(proc.warnings || []).length > 0 ? `
              <div class="ads-banner ads-banner-danger">
                <div>
                  <div class="font-bold">⚠ CẢNH BÁO THIẾU ẢNH TRONG BÀI VIẾT — ĐÃ CHẶN ĐỒNG BỘ (KHÔNG RENDER SVG):</div>
                  <ul class="list-disc pl-5 mt-1 space-y-0.5 text-[13px]">
                    ${{(proc.warnings || []).map(w => `<li>${{w}}</li>`).join('')}}
                  </ul>
                </div>
              </div>
            ` : ''}}
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div class="p-3 rounded-[3px] bg-[#F7F8F9] border border-[#DCDFE4]">
                <div class="ads-subhead">MISSING IMAGES HEALED</div>
                <div class="text-[15px] font-semibold text-[#172B4D] mt-1">${{(proc.resolved_missing_images || []).length}} Product CDN Images</div>
              </div>
              <div class="p-3 rounded-[3px] bg-[#F7F8F9] border border-[#DCDFE4]">
                <div class="ads-subhead">IMAGE GUARDRAIL (NO SVG)</div>
                <div class="text-[15px] font-semibold ${{(proc.warnings || []).length > 0 ? 'text-[#AE2E24]' : 'text-[#216E4E]'}} mt-1">
                  ${{(proc.warnings || []).length > 0 ? `⚠ ${{proc.warnings.length}} Missing Image Warning(s)` : '✓ All Images Verified (0 SVG)'}}
                </div>
              </div>
              <div class="p-3 rounded-[3px] bg-[#F7F8F9] border border-[#DCDFE4]">
                <div class="ads-subhead">FAQ + JSON-LD SCHEMA</div>
                <div class="text-[15px] font-semibold text-[#216E4E] mt-1">${{proc.faq_items_count}} Q&A Items · 100% English</div>
              </div>
            </div>

            <details class="rounded-[3px] border border-[#DCDFE4] bg-[#F7F8F9] p-3">
              <summary class="text-[13px] font-semibold text-[#172B4D] cursor-pointer select-none">
                Confluence-Style Article Body Preview (Post-Processed HTML · Real Product Images Only)
              </summary>
              <div class="mt-3 p-5 bg-white rounded-[3px] border border-[#DCDFE4] max-h-[440px] overflow-y-auto preview-prose">
                ${{proc.body_html}}
              </div>
            </details>
          </div>
        ` : `
          <div class="mt-4 space-y-3">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div class="p-3 rounded-[3px] bg-[#F7F8F9] border border-[#DCDFE4]">
                <div class="ads-subhead">SHOP IMAGES IN CATALOG</div>
                <div class="text-[15px] font-semibold text-[#172B4D] mt-1">${{(preview.shop_images || []).length}} Product CDN Images</div>
              </div>
              <div class="p-3 rounded-[3px] bg-[#F7F8F9] border border-[#DCDFE4]">
                <div class="ads-subhead">META DESCRIPTION</div>
                <div class="text-[12px] text-[#44546F] mt-1 line-clamp-2" title="${{(preview.meta_description || '').replace(/"/g, '&quot;')}}">${{preview.meta_description || '—'}}</div>
              </div>
              <div class="p-3 rounded-[3px] bg-[#F7F8F9] border border-[#DCDFE4]">
                <div class="ads-subhead">POST-PROCESSOR STATUS</div>
                <div class="text-[12px] font-medium text-[#0C66E4] mt-1">Sẵn sàng — Bấm "1. Run HTML Post-Processor" hoặc bấm thẳng "2. Sync to ${{store.name}} & Verify Live"</div>
              </div>
            </div>
            <details class="rounded-[3px] border border-[#DCDFE4] bg-[#F7F8F9] p-3">
              <summary class="text-[13px] font-semibold text-[#172B4D] cursor-pointer select-none">
                Xem trước Nội dung Gốc từ Zbigtee (Raw Extracted HTML · ${{(preview.body_html || '').length}} chars)
              </summary>
              <div class="mt-3 p-5 bg-white rounded-[3px] border border-[#DCDFE4] max-h-[440px] overflow-y-auto preview-prose">
                ${{preview.body_html}}
              </div>
            </details>
          </div>
        `}}
      `;

      if (!rep) {{
        verEl.innerHTML = `<div class="text-[13px] text-[#626F86]">Chưa có báo cáo Verify Live cho bài <strong>${{preview.title}}</strong> (<code>${{preview.slug}}</code>). Bấm <strong>Sync to ${{store.name}} & Verify Live</strong> để xuất bản và chạy kiểm thử tự động.</div>`;
      }} else {{
        const shotSlug = rep.expected_handle || preview.slug || 'article';
        const badge = rep.ok
          ? `<span class="ads-lozenge ads-lozenge-success-bold">ALL ${{rep.passed_count}}/${{rep.total_checks}} CHECKS PASSED</span>`
          : `<span class="ads-lozenge ads-lozenge-danger">${{rep.passed_count}}/${{rep.total_checks}} CHECKS PASSED</span>`;

        verEl.innerHTML = `
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[#DCDFE4]">
            <div>
              <div class="ads-subhead">AUTOMATED PLAYWRIGHT VERIFICATION (FIX–REVIEW LOOP)</div>
              <h3 class="text-[16px] font-semibold text-[#172B4D] mt-0.5">Live Storefront Quality Gate Report</h3>
              <a href="${{rep.article_url}}" target="_blank" class="text-[12px] text-[#0C66E4] font-medium hover:underline">${{rep.article_url}} ↗</a>
            </div>
            ${{badge}}
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5 mt-4">
            ${{(rep.checks || []).map(c => `
              <div class="p-2.5 rounded-[3px] border ${{c.passed ? 'border-[#BAF3DB] bg-[#DCFFF1]/40' : 'border-[#FFD5D2] bg-[#FFECEB]'}}">
                <div class="flex items-center justify-between gap-1">
                  <span class="font-semibold text-[12px] ${{c.passed ? 'text-[#216E4E]' : 'text-[#AE2E24]'}}">
                    ${{c.passed ? '✓' : '✗'}} ${{c.label}}
                  </span>
                  <span class="ads-lozenge ${{c.passed ? 'ads-lozenge-success' : 'ads-lozenge-danger'}}">${{c.passed ? 'PASS' : 'FAIL'}}</span>
                </div>
                <div class="text-[11px] text-[#44546F] truncate mt-1 ads-mono" title="${{c.detail}}">${{c.detail}}</div>
              </div>
            `).join('')}}
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 pt-4 border-t border-[#DCDFE4]">
            <div class="bg-[#F7F8F9] p-3 rounded-[3px] border border-[#DCDFE4]">
              <div class="flex items-center justify-between mb-2">
                <span class="ads-subhead">DESKTOP VIEWPORT (1440×900)</span>
                <a href="/api/screenshots/${{store.id}}/${{shotSlug}}_live_desktop.png" target="_blank" class="text-[11px] text-[#0C66E4] font-semibold hover:underline">Full Image ↗</a>
              </div>
              <a href="/api/screenshots/${{store.id}}/${{shotSlug}}_live_desktop.png" target="_blank">
                <img src="/api/screenshots/${{store.id}}/${{shotSlug}}_live_desktop.png?t=${{Date.now()}}" class="rounded-[3px] border border-[#DCDFE4] max-h-64 w-full object-cover object-top bg-white" />
              </a>
            </div>
            <div class="bg-[#F7F8F9] p-3 rounded-[3px] border border-[#DCDFE4]">
              <div class="flex items-center justify-between mb-2">
                <span class="ads-subhead">MOBILE VIEWPORT (390×844 · OVERFLOWX = 0)</span>
                <a href="/api/screenshots/${{store.id}}/${{shotSlug}}_live_mobile.png" target="_blank" class="text-[11px] text-[#0C66E4] font-semibold hover:underline">Full Image ↗</a>
              </div>
              <a href="/api/screenshots/${{store.id}}/${{shotSlug}}_live_mobile.png" target="_blank">
                <img src="/api/screenshots/${{store.id}}/${{shotSlug}}_live_mobile.png?t=${{Date.now()}}" class="rounded-[3px] border border-[#DCDFE4] max-h-64 w-full object-cover object-top bg-white" />
              </a>
            </div>
          </div>
        `;
      }}
    }}

    async function runPostProcess(contentId) {{
      showToast('Đang chạy xử lý hậu kỳ HTML và kiểm tra ảnh CDN...');
      const res = await fetch('/api/pipeline/postprocess', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ store_id: APP_DATA.active_store_id, content_id: contentId }})
      }});
      const data = await res.json();
      if (!data.ok) {{
        showToast('Lỗi hậu kỳ: ' + (data.error || 'Unknown error'), true);
        return;
      }}
      showToast('Đã hoàn tất hậu kỳ HTML cho bài viết: ' + data.article.title);
      setTimeout(() => {{
        window.location.href = `/?store=${{encodeURIComponent(APP_DATA.active_store_id)}}&article=${{encodeURIComponent(contentId)}}`;
      }}, 600);
    }}

    async function runSyncAndPublish(contentId) {{
      const blogHandle = document.getElementById('targetBlogSelect')?.value || '';
      showToast('Đang đồng bộ bài viết lên Shopify Store, chạy kiểm thử Playwright 12/12 và đánh dấu Published trên zbigtee.com...');
      const res = await fetch('/api/pipeline/sync', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{
          store_id: APP_DATA.active_store_id,
          content_id: contentId,
          blog_handle: blogHandle,
          verify: true
        }})
      }});
      const data = await res.json();
      if (!data.ok) {{
        showToast('Lỗi đồng bộ: ' + (data.error || 'Unknown error'), true);
        return;
      }}
      const zbMsg = data.zbigtee_publish_sync?.marked_on_zbigtee
        ? ' & đã chuyển sang cột <strong>Published</strong> trên zbigtee.com'
        : '';
      showToast(`Đã ${{data.publish.action}} bài viết thành công tại <a href="${{data.publish.myshopify_url}}" target="_blank" class="underline font-bold">${{data.publish.myshopify_url}}</a>${{zbMsg}}!`);
      setTimeout(() => {{
        window.location.href = `/?store=${{encodeURIComponent(APP_DATA.active_store_id)}}&article=${{encodeURIComponent(contentId)}}`;
      }}, 900);
    }}

    let CURRENT_EDITOR_TAB = 'visual';

    function showModalToast(msg, isError = false) {{
      const el = document.getElementById('upd_modal_toast');
      if (!el) return;
      el.classList.remove('hidden');
      el.className = isError ? 'mx-6 mt-4 shrink-0 ads-banner ads-banner-danger' : 'mx-6 mt-4 shrink-0 ads-banner ads-banner-success';
      el.innerHTML = `<div class="flex-1">${{msg}}</div>`;
    }}

    function hideModalToast() {{
      const el = document.getElementById('upd_modal_toast');
      if (el) el.classList.add('hidden');
    }}

    function switchEditorTab(mode) {{
      CURRENT_EDITOR_TAB = mode;
      const visualEl = document.getElementById('upd_body_visual');
      const htmlEl = document.getElementById('upd_body_html');
      const btnVisual = document.getElementById('tabBtnVisual');
      const btnHtml = document.getElementById('tabBtnHtml');
      if (mode === 'html') {{
        htmlEl.value = visualEl.innerHTML;
        visualEl.classList.add('hidden');
        htmlEl.classList.remove('hidden');
        btnHtml.className = 'px-3 py-1 rounded-[2px] text-[12px] font-semibold bg-white text-[#0C66E4] shadow-xs cursor-pointer';
        btnVisual.className = 'px-3 py-1 rounded-[2px] text-[12px] font-medium text-[#44546F] cursor-pointer';
      }} else {{
        visualEl.innerHTML = htmlEl.value;
        htmlEl.classList.add('hidden');
        visualEl.classList.remove('hidden');
        btnVisual.className = 'px-3 py-1 rounded-[2px] text-[12px] font-semibold bg-white text-[#0C66E4] shadow-xs cursor-pointer';
        btnHtml.className = 'px-3 py-1 rounded-[2px] text-[12px] font-medium text-[#44546F] cursor-pointer';
      }}
    }}

    function syncBodyFromVisual() {{
      const visualEl = document.getElementById('upd_body_visual');
      const htmlEl = document.getElementById('upd_body_html');
      if (visualEl && htmlEl) htmlEl.value = visualEl.innerHTML;
    }}

    function syncBodyFromHtml() {{
      const visualEl = document.getElementById('upd_body_visual');
      const htmlEl = document.getElementById('upd_body_html');
      if (visualEl && htmlEl) visualEl.innerHTML = htmlEl.value;
    }}

    function syncHeroPreviewFromInput() {{
      const url = (document.getElementById('upd_featured_url')?.value || '').trim();
      const img = document.getElementById('upd_hero_preview_img');
      const empty = document.getElementById('upd_hero_empty');
      if (!url) {{
        img.classList.add('hidden');
        empty.classList.remove('hidden');
        return;
      }}
      img.src = url;
    }}

    function selectCoverFromGallery(url, altText) {{
      document.getElementById('upd_featured_url').value = url;
      if (altText && !document.getElementById('upd_featured_alt').value) {{
        document.getElementById('upd_featured_alt').value = altText;
      }}
      syncHeroPreviewFromInput();
    }}

    function updateSeoSerpPreview() {{
      const store = APP_DATA.state.store || {{}};
      const domain = store.zbigtee_domain ? `https://${{store.zbigtee_domain}}` : `https://${{store.normalized_shop || 'store.myshopify.com'}}`;
      const blogHandle = document.getElementById('upd_blog_handle')?.value || store.default_blog_handle || 'news';
      const slug = (document.getElementById('upd_handle')?.value || 'article-slug').trim();
      const title = (document.getElementById('upd_seo_title')?.value || document.getElementById('upd_title')?.value || 'Article Title').trim();
      const desc = (document.getElementById('upd_seo_desc')?.value || document.getElementById('upd_summary')?.value || '').trim();

      document.getElementById('upd_serp_url').textContent = `${{domain}} › blogs › ${{blogHandle}} › ${{slug}}`;
      document.getElementById('upd_serp_title').textContent = title;
      document.getElementById('upd_serp_desc').textContent = desc || 'Chưa có mô tả SEO (Meta Description)...';

      const seoTitleLen = (document.getElementById('upd_seo_title')?.value || '').length;
      const seoDescLen = (document.getElementById('upd_seo_desc')?.value || '').length;
      const titleCountEl = document.getElementById('upd_seo_title_count');
      const descCountEl = document.getElementById('upd_seo_desc_count');
      if (titleCountEl) {{
        titleCountEl.textContent = `${{seoTitleLen}} / 70 chars`;
        titleCountEl.className = seoTitleLen > 70 ? 'text-[11px] text-[#AE2E24] font-semibold ads-mono' : 'text-[11px] text-[#626F86] ads-mono';
      }}
      if (descCountEl) {{
        descCountEl.textContent = `${{seoDescLen}} / 160 chars`;
        descCountEl.className = (seoDescLen > 165 || seoDescLen < 50) ? 'text-[11px] text-[#E56910] font-semibold ads-mono' : 'text-[11px] text-[#216E4E] font-semibold ads-mono';
      }}
    }}

    function closeUpdateModal() {{
      const modal = document.getElementById('updateArticleModal');
      if (modal) modal.classList.add('hidden');
    }}

    async function openUpdateModal(contentId, fetchLive = false) {{
      hideModalToast();
      const modal = document.getElementById('updateArticleModal');
      modal.classList.remove('hidden');

      const targetCid = contentId || SELECTED_CONTENT_ID;
      document.getElementById('upd_content_id').value = targetCid;
      document.getElementById('upd_modal_heading').textContent = 'Đang tải dữ liệu bài viết...';

      const res = await fetch('/api/pipeline/article-editor', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{
          store_id: APP_DATA.active_store_id,
          content_id: targetCid,
          fetch_live: fetchLive
        }})
      }});
      const data = await res.json();
      if (!data.ok) {{
        showModalToast('Không thể tải dữ liệu bài viết: ' + (data.error || 'Unknown error'), true);
        return;
      }}

      const ed = data.editor;
      document.getElementById('upd_content_id').value = ed.content_id || targetCid;
      document.getElementById('upd_previous_handle').value = ed.handle || '';
      document.getElementById('upd_modal_heading').textContent = ed.title || 'Update Blog Post';

      // Populate blogs dropdown
      const blogSelect = document.getElementById('upd_blog_handle');
      const blogs = ed.blogs || [];
      const currentMainSelect = document.getElementById('targetBlogSelect')?.value;
      const activeBlogHandle = ed.blog_handle || currentMainSelect || ed.default_blog_handle || 'news';
      blogSelect.innerHTML = blogs.length
        ? blogs.map(b => `<option value="${{b.handle}}" ${{b.handle === activeBlogHandle ? 'selected' : ''}}>${{b.title}} (${{b.handle}})</option>`).join('')
        : `<option value="${{activeBlogHandle}}">${{activeBlogHandle}}</option>`;

      document.getElementById('upd_title').value = ed.title || '';
      document.getElementById('upd_handle').value = ed.handle || '';
      document.getElementById('upd_author').value = ed.author || '';
      document.getElementById('upd_summary').value = ed.summary || '';
      document.getElementById('upd_visibility').value = ed.is_published === false ? 'false' : 'true';
      document.getElementById('upd_tags').value = Array.isArray(ed.tags) ? ed.tags.join(', ') : (ed.tags || '');
      document.getElementById('upd_featured_url').value = ed.featured_image_url || '';
      document.getElementById('upd_featured_alt').value = ed.featured_image_alt || ed.title || '';
      document.getElementById('upd_seo_title').value = ed.seo_title || ed.title || '';
      document.getElementById('upd_seo_desc').value = ed.seo_description || ed.summary || '';

      const bodyHtml = ed.body_html || '';
      document.getElementById('upd_body_html').value = bodyHtml;
      document.getElementById('upd_body_visual').innerHTML = bodyHtml;
      switchEditorTab('visual');

      // Live status badge
      const badgeEl = document.getElementById('upd_live_badge');
      if (ed.live_article_id) {{
        badgeEl.className = ed.is_published === false ? 'ads-lozenge ads-lozenge-warning' : 'ads-lozenge ads-lozenge-success-bold';
        badgeEl.textContent = ed.is_published === false
          ? `HIDDEN DRAFT ON SHOPIFY (${{ed.blog_handle}})`
          : `LIVE ON SHOPIFY · BLOG: ${{ed.blog_handle.toUpperCase()}}`;
      }} else {{
        badgeEl.className = 'ads-lozenge ads-lozenge-inprogress';
        badgeEl.textContent = 'LOCAL PREVIEW & POST-PROCESSED';
      }}

      // Populate shop images strip for cover selection
      const stripEl = document.getElementById('upd_shop_images_strip');
      const shopImgs = ed.shop_images || [];
      if (shopImgs.length === 0) {{
        stripEl.innerHTML = `<span class="text-[11px] text-[#626F86]">Không có shop_images đính kèm trong gói preview.</span>`;
      }} else {{
        stripEl.innerHTML = shopImgs.map((u, idx) => {{
          const imgUrl = typeof u === 'string' ? u : (u.src || u.url || '');
          const imgAlt = (typeof u === 'object' && u) ? (u.alt || u.shows || ed.title || '') : (ed.title || '');
          const safeU = String(imgUrl).replace(/'/g, "\\'");
          const safeAlt = String(imgAlt).replace(/'/g, "\\'");
          return `
            <button type="button" onclick="selectCoverFromGallery('${{safeU}}', '${{safeAlt}}')"
                    class="shrink-0 p-1 bg-white border border-[#DCDFE4] hover:border-[#0C66E4] rounded-[3px] cursor-pointer transition"
                    title="Chọn ảnh #${{idx + 1}} làm ảnh bìa">
              <img src="${{imgUrl}}" class="h-14 w-14 object-cover rounded-[2px]" />
            </button>
          `;
        }}).join('');
      }}

      syncHeroPreviewFromInput();
      updateSeoSerpPreview();
      if (fetchLive) {{
        showModalToast('Đã nạp thành công dữ liệu đang Live trực tiếp từ Shopify Admin GraphQL!');
      }}
    }}

    async function reloadUpdateModalFromLiveShopify() {{
      const cid = document.getElementById('upd_content_id')?.value || SELECTED_CONTENT_ID;
      showModalToast('Đang truy vấn dữ liệu bài viết trực tiếp từ Shopify Store...');
      await openUpdateModal(cid, true);
    }}

    async function submitComprehensiveUpdate(mode) {{
      hideModalToast();
      if (CURRENT_EDITOR_TAB === 'visual') {{
        syncBodyFromVisual();
      }} else {{
        syncBodyFromHtml();
      }}

      const contentId = document.getElementById('upd_content_id').value;
      const previousHandle = document.getElementById('upd_previous_handle').value;
      const title = document.getElementById('upd_title').value.trim();
      const handle = document.getElementById('upd_handle').value.trim();
      const author = document.getElementById('upd_author').value.trim();
      const summary = document.getElementById('upd_summary').value.trim();
      const isPublished = document.getElementById('upd_visibility').value === 'true';
      const blogHandle = document.getElementById('upd_blog_handle').value;
      const tags = document.getElementById('upd_tags').value.trim();
      const featuredUrl = document.getElementById('upd_featured_url').value.trim();
      const featuredAlt = document.getElementById('upd_featured_alt').value.trim();
      const seoTitle = document.getElementById('upd_seo_title').value.trim();
      const seoDesc = document.getElementById('upd_seo_desc').value.trim();
      const bodyHtml = document.getElementById('upd_body_html').value;

      if (!title || !handle) {{
        showModalToast('Vui lòng nhập đầy đủ Tiêu đề (Title) và URL Handle (Slug)!', true);
        return;
      }}
      if (!featuredUrl) {{
        showModalToast('Cảnh báo: Bài viết thiếu Ảnh bìa (Featured Cover Image URL). Vui lòng nhập URL hoặc chọn ảnh từ danh sách!', true);
        return;
      }}

      const pushToShopify = (mode === 'shopify' || mode === 'verify');
      const verifyLive = (mode === 'verify');

      const actionLabel = mode === 'local'
        ? 'Đang lưu bản cập nhật vào dữ liệu Local...'
        : (mode === 'verify'
          ? 'Đang cập nhật toàn diện lên Shopify và chạy kiểm thử Playwright Live 12/12...'
          : 'Đang đẩy bản cập nhật toàn diện lên Shopify...');
      showModalToast(actionLabel, false);

      const res = await fetch('/api/pipeline/update-article', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{
          store_id: APP_DATA.active_store_id,
          content_id: contentId,
          previous_handle: previousHandle,
          title: title,
          handle: handle,
          author: author,
          summary: summary,
          is_published: isPublished,
          blog_handle: blogHandle,
          tags: tags,
          featured_image_url: featuredUrl,
          featured_image_alt: featuredAlt,
          seo_title: seoTitle,
          seo_description: seoDesc,
          body_html: bodyHtml,
          push_to_shopify: pushToShopify,
          verify: verifyLive
        }})
      }});
      const data = await res.json();
      if (!data.ok) {{
        showModalToast('Lỗi cập nhật: ' + (data.error || 'Unknown error'), true);
        return;
      }}

      if (!pushToShopify) {{
        showModalToast('✓ Đã lưu toàn bộ thay đổi vào file Local thành công!');
        showToast('Đã lưu bản nháp bài viết vào Local: ' + title);
        setTimeout(() => {{
          window.location.href = `/?store=${{encodeURIComponent(APP_DATA.active_store_id)}}&article=${{encodeURIComponent(contentId)}}`;
        }}, 700);
        return;
      }}

      const pub = data.publish || {{}};
      const movedNote = pub.moved_from_previous_blog
        ? ` (Đã tự động chuyển sang blog <strong>${{pub.blog_handle}}</strong> & xóa bản cũ ở blog <code>${{pub.moved_from_previous_blog.deleted_from_blog_handle}}</code>)`
        : '';
      showModalToast(`✓ Đã cập nhật thành công lên Shopify (${{pub.action}})${{movedNote}}: <a href="${{pub.myshopify_url}}" target="_blank" class="underline font-bold">${{pub.myshopify_url}}</a>`);
      showToast(`Đã cập nhật bài viết lên Shopify thành công: <a href="${{pub.myshopify_url}}" target="_blank" class="underline font-bold">${{pub.myshopify_url}}</a>${{movedNote}}`);
      setTimeout(() => {{
        window.location.href = `/?store=${{encodeURIComponent(APP_DATA.active_store_id)}}&article=${{encodeURIComponent(contentId)}}`;
      }}, 1100);
    }}

    renderDashboard();
  </script>
</body>
</html>"""
    return html_content


def render_settings_html() -> str:
    sm = StoreManager()
    spm = StoreProfileManager(store_manager=sm)
    active_id = sm.get_active_store_id()
    stores = [s.to_dict() for s in sm.list_stores()]
    profiles_map: Dict[str, Any] = {}
    for s in stores:
        sid = s["id"]
        try:
            profiles_map[sid] = spm.get_profile(sid)
        except Exception:
            profiles_map[sid] = None
    zb_auth = ZbigteeUiOperator.get_auth_state()
    proxy_cfg = sm.proxy_manager.get_config().to_dict()
    settings_json = json.dumps(
        {
            "active_store_id": active_id,
            "stores": stores,
            "store_profiles": profiles_map,
            "zbigtee_auth": zb_auth,
            "proxy": proxy_cfg,
        },
        ensure_ascii=False,
    )

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Project Settings · Store & Credentials Administration (Atlassian Design)</title>
  <script src="https://unpkg.com/@tailwindcss/browser@4"></script>
  <style>{ATLASSIAN_COMMON_CSS}</style>
</head>
<body class="min-h-screen flex flex-col">
  <!-- Atlassian Global Navigation Bar -->
  <header class="ads-topbar">
    <div class="flex items-center gap-2 h-full">
      <button type="button" title="Atlassian App Switcher" class="w-8 h-8 rounded-[3px] flex items-center justify-center text-[#44546F] hover:bg-[#F1F2F4]">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
          <circle cx="5" cy="5" r="2"/><circle cx="12" cy="5" r="2"/><circle cx="19" cy="5" r="2"/>
          <circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/>
          <circle cx="5" cy="19" r="2"/><circle cx="12" cy="19" r="2"/><circle cx="19" cy="19" r="2"/>
        </svg>
      </button>

      <a href="/" class="flex items-center gap-2.5 pr-3 text-[#172B4D] font-semibold text-[15px] no-underline">
        <span class="w-7 h-7 rounded-[3px] bg-[#0C66E4] text-white flex items-center justify-center font-bold text-xs shadow-xs">
          M5
        </span>
        <span>Content Release Center</span>
      </a>

      <nav class="flex items-center h-full">
        <a href="/" class="ads-nav-link">Workspace Board</a>
        <a href="/settings" class="ads-nav-link active">Project Settings & Credentials</a>
        <a href="/diagram" target="_blank" class="ads-nav-link">Architecture Diagram ↗</a>
      </nav>
    </div>

    <div class="flex items-center gap-2.5">
      <button onclick="syncFromZbigtee()" class="ads-btn ads-btn-subtle">
        ↻ Fetch Live Projects từ Zbigtee
      </button>
      <button onclick="resetFormForNewStore()" class="ads-btn ads-btn-primary">
        + Create Store Config
      </button>
    </div>
  </header>

  <div class="flex flex-1 w-full">
    <!-- Left Sidebar -->
    <aside class="ads-sidebar">
      <div class="py-4">
        <div class="px-4 pb-3 border-b border-[#DCDFE4] mb-2">
          <div class="ads-subhead">ADMINISTRATION</div>
          <div class="font-semibold text-[14px] text-[#172B4D] mt-0.5">Multi-Store Credentials</div>
          <div class="text-[11px] text-[#626F86]">Isolated JSON Configs</div>
        </div>

        <a href="/" class="ads-side-item">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="18" rx="1"/><rect x="14" y="3" width="7" height="11" rx="1"/></svg>
          <span>Zbigtee Release Board</span>
        </a>
        <a href="/settings" class="ads-side-item active">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c.26.604.852.997 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
          <span>Store Credentials & Profiles</span>
        </a>
        <a href="/diagram" target="_blank" class="ads-side-item">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M3 12h18M3 18h18"/></svg>
          <span>10-Step Swimlane Spec</span>
        </a>
      </div>

      <div class="p-3 border-t border-[#DCDFE4] text-[11px] text-[#626F86]">
        <div>Per-Store Credential & Profile Files</div>
        <div class="ads-mono text-[10px] mt-0.5">data/stores/&lt;id&gt;.json</div>
        <div class="ads-mono text-[10px] mt-0.5">data/store_profiles/&lt;id&gt;.json</div>
      </div>
    </aside>

    <!-- Full-Width Main Workspace (NO max-w-7xl) -->
    <main class="w-full flex-1 px-6 py-5 space-y-5 min-w-0">
      <div class="ads-card p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div class="ads-breadcrumb">
            <a href="/">Projects</a> <span>/</span>
            <span>Administration</span> <span>/</span>
            <span>Store, Proxy & Editorial Profile Settings</span>
          </div>
          <h1 class="text-[20px] font-semibold text-[#172B4D] tracking-tight">Quản lý Danh sách Store, Proxy Bắt Buộc, Shopify Credentials & Store Editorial Profile</h1>
          <p class="text-[13px] text-[#44546F] mt-1">
            Mỗi Store được lưu tại <code class="ads-mono bg-[#F1F2F4] px-1.5 py-0.5 rounded-[3px]">data/stores/&lt;store_id&gt;.json</code>,
            Hồ sơ biên tập & chính sách lưu tại <code class="ads-mono bg-[#F1F2F4] px-1.5 py-0.5 rounded-[3px]">data/store_profiles/&lt;store_id&gt;.json</code>,
            và cấu hình Proxy bắt buộc lưu tại <code class="ads-mono bg-[#F1F2F4] px-1.5 py-0.5 rounded-[3px]">data/proxy.json</code>.
          </p>
        </div>
        <div class="flex items-center gap-2">
          <button onclick="syncFromZbigtee()" class="ads-btn ads-btn-subtle">
            ↻ Đồng bộ danh sách Store Live từ Zbigtee
          </button>
          <button onclick="resetFormForNewStore()" class="ads-btn ads-btn-primary">
            + Thêm Store mới
          </button>
        </div>
      </div>

      <div id="settingsToast" class="hidden"></div>

      <div class="grid grid-cols-1 xl:grid-cols-12 gap-5 items-start">
        <!-- Left: Mandatory Shopify Proxy Gateway + Zbigtee Live Auth + Store Directory List (5 cols on XL) -->
        <div class="xl:col-span-5 space-y-4">
          <!-- Section 1: Mandatory Shopify Proxy Gateway -->
          <div class="ads-card p-4 space-y-3 border-l-4 border-l-[#0C66E4]" id="proxySettingsSection">
            <div class="pb-2.5 border-b border-[#DCDFE4] flex items-center justify-between gap-2 flex-wrap">
              <div>
                <div class="ads-subhead !text-[#0C66E4]">MANDATORY SHOPIFY PROXY GATEWAY</div>
                <h2 class="text-[15px] font-semibold text-[#172B4D] mt-0.5">Cấu hình Proxy bắt buộc cho Shopify (data/proxy.json)</h2>
              </div>
              <span class="ads-lozenge ads-lozenge-inprogress" id="proxyStatusBadge">CHECKING...</span>
            </div>

            <div class="p-2.5 rounded-[3px] bg-[#E9F2FF] border border-[#B3D4FF] text-[12px] text-[#172B4D]">
              <strong>Quy tắc bắt buộc:</strong> Mọi phiên giao tiếp giữa Tool và Shopify (OAuth, Admin GraphQL, CDN Image Check, Playwright Live Verify) đều đi qua Proxy này. Nếu Proxy không ổn định, <strong>toàn bộ kết nối tới Shopify sẽ bị chặn ngay lập tức</strong>.
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-12 gap-3">
              <div class="sm:col-span-3">
                <label class="ads-label">Protocol</label>
                <select id="px_scheme" class="ads-select ads-mono">
                  <option value="http">http</option>
                  <option value="https">https</option>
                  <option value="socks5">socks5</option>
                </select>
              </div>
              <div class="sm:col-span-6">
                <label class="ads-label">Proxy IP / Host <span class="text-[#AE2E24]">*</span></label>
                <input type="text" id="px_host" class="ads-input ads-mono" placeholder="185.124.63.174" />
              </div>
              <div class="sm:col-span-3">
                <label class="ads-label">Port <span class="text-[#AE2E24]">*</span></label>
                <input type="number" id="px_port" class="ads-input ads-mono" placeholder="55031" />
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="ads-label">Proxy Username</label>
                <input type="text" id="px_username" class="ads-input ads-mono" placeholder="nPMZfSl5QX0shvm" />
              </div>
              <div>
                <label class="ads-label">Proxy Password</label>
                <input type="password" id="px_password" class="ads-input ads-mono" placeholder="hKTQVcQVNAvYHXq" />
              </div>
            </div>

            <!-- Live Proxy Stability Report Box -->
            <div id="proxyMetricsBox" class="p-3 rounded-[3px] bg-[#F7F8F9] border border-[#DCDFE4] text-[12px] space-y-1">
            </div>

            <div class="flex items-center justify-between gap-2 pt-1 flex-wrap">
              <div class="flex items-center gap-1.5">
                <button type="button" id="btnCheckProxy" onclick="checkProxyStability()" class="ads-btn ads-btn-success !h-8 !text-[12px]">
                  ✓ Check Độ Ổn Định Proxy
                </button>
                <button type="button" id="btnResetProxyDefault" onclick="resetProxyFromDocs()" class="ads-btn ads-btn-subtle !h-8 !text-[12px]" title="Khôi phục từ docs/proxy-credentials.md">
                  ↺ Mặc định (docs)
                </button>
              </div>
              <button type="button" id="btnSaveProxy" onclick="saveProxyConfig()" class="ads-btn ads-btn-primary !h-8 !text-[12px]">
                Save Proxy Credentials
              </button>
            </div>
          </div>

          <!-- Section 2: Zbigtee Live Auth Session -->
          <div class="ads-card p-4 space-y-3">
            <div class="pb-2.5 border-b border-[#DCDFE4] flex items-center justify-between">
              <div>
                <div class="ads-subhead">ZBIGTEE LIVE SCRAPER AUTH</div>
                <h2 class="text-[15px] font-semibold text-[#172B4D] mt-0.5">Phiên đăng nhập Zbigtee (data/zbigtee_auth.json)</h2>
              </div>
              <span class="ads-lozenge ads-lozenge-success" id="zbAuthBadge">ACTIVE SESSION</span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="ads-label">__Secure-authjs.session-token</label>
                <input type="password" id="zb_session_token" class="ads-input ads-mono" placeholder="6050620b-..." />
              </div>
              <div>
                <label class="ads-label">Zbigtee Workspace ID</label>
                <input type="text" id="zb_workspace_id" class="ads-input ads-mono" placeholder="01a0b213-..." />
              </div>
            </div>
            <div class="flex items-center justify-between gap-2 pt-1">
              <button type="button" onclick="verifyZbigteeAuth()" class="ads-btn ads-btn-subtle !h-7 !text-[12px]">
                Verify Live Zbigtee Session
              </button>
              <button type="button" onclick="saveZbigteeAuth()" class="ads-btn ads-btn-primary !h-7 !text-[12px]">
                Save Zbigtee Auth
              </button>
            </div>
          </div>

          <!-- Section 3: Registered Stores -->
          <div class="ads-card p-4">
            <div class="pb-3 mb-3 border-b border-[#DCDFE4] flex items-center justify-between">
              <div>
                <div class="ads-subhead">REGISTERED STORES</div>
                <h2 class="text-[15px] font-semibold text-[#172B4D] mt-0.5">Danh sách Store hiện có</h2>
              </div>
              <span class="ads-lozenge ads-lozenge-inprogress">MODULAR JSON</span>
            </div>
            <div id="storesListContainer" class="space-y-2.5"></div>
          </div>
        </div>

        <!-- Right: Add / Edit Store Credentials Form + Store Editorial Profile (7 cols on XL) -->
        <div class="xl:col-span-7 space-y-5">
          <div class="ads-card p-5">
            <div class="flex items-center justify-between pb-3 mb-4 border-b border-[#DCDFE4]">
              <div>
                <div class="ads-subhead">CREDENTIAL CONFIGURATION</div>
                <h2 id="formTitle" class="text-[16px] font-semibold text-[#172B4D] mt-0.5">Thêm / Cập nhật Store Credentials</h2>
              </div>
              <span id="formConfigPath" class="ads-lozenge ads-lozenge-neutral ads-mono"></span>
            </div>

            <form id="storeForm" onsubmit="handleSaveStore(event)" class="space-y-4">
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label class="ads-label">Store ID (Slug) <span class="text-[#AE2E24]">*</span></label>
                  <input type="text" id="f_id" placeholder="vd: wrydeco" required class="ads-input ads-mono" />
                </div>
                <div>
                  <label class="ads-label">Tên Store hiển thị <span class="text-[#AE2E24]">*</span></label>
                  <input type="text" id="f_name" placeholder="vd: WRYDECO" required class="ads-input" />
                </div>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label class="ads-label">Zbigtee Domain</label>
                  <input type="text" id="f_zbigtee_domain" placeholder="vd: wrydeco.com" class="ads-input" />
                </div>
                <div>
                  <label class="ads-label">Zbigtee Project ID</label>
                  <input type="text" id="f_zbigtee_project_id" placeholder="vd: 01a0d177-b16d-..." class="ads-input ads-mono" />
                </div>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label class="ads-label">Shopify Domain (*.myshopify.com)</label>
                  <input type="text" id="f_shopify_shop" placeholder="vd: wrydeco.myshopify.com" class="ads-input ads-mono" />
                </div>
                <div>
                  <label class="ads-label">Public Storefront Domain</label>
                  <input type="text" id="f_public_domain" placeholder="vd: https://wrydeco.myshopify.com" class="ads-input ads-mono" />
                </div>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label class="ads-label">Shopify Client ID</label>
                  <input type="text" id="f_client_id" placeholder="78a8c93070c34ac4bb50ded9f393148c" class="ads-input ads-mono" />
                </div>
                <div>
                  <label class="ads-label">Shopify Client Secret</label>
                  <input type="password" id="f_client_secret" placeholder="shpss_..." class="ads-input ads-mono" />
                </div>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label class="ads-label">Admin API Access Token (shpat_...)</label>
                  <input type="password" id="f_admin_token" placeholder="Tự động cấp nếu có Client ID & Secret" class="ads-input ads-mono" />
                </div>
                <div>
                  <label class="ads-label">Storefront Password (nếu khóa)</label>
                  <input type="text" id="f_storefront_password" placeholder="vd: 123456" class="ads-input ads-mono" />
                </div>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label class="ads-label">Default Blog Handle</label>
                  <input type="text" id="f_default_blog_handle" placeholder="buying-guides" class="ads-input ads-mono" />
                </div>
                <div>
                  <label class="ads-label">Default Author</label>
                  <input type="text" id="f_default_author" placeholder="WRYDECO Studio" class="ads-input" />
                </div>
                <div>
                  <label class="ads-label">API Version</label>
                  <input type="text" id="f_api_version" value="2026-07" class="ads-input ads-mono" />
                </div>
              </div>

              <div>
                <label class="ads-label">Ghi chú cấu hình</label>
                <input type="text" id="f_notes" placeholder="Ghi chú..." class="ads-input" />
              </div>

              <div class="pt-4 flex items-center justify-between gap-3 border-t border-[#DCDFE4]">
                <button type="button" onclick="handleTestConnectionFromForm()" class="ads-btn ads-btn-success">
                  Test OAuth Connection & Fetch Blogs
                </button>
                <button type="submit" id="saveStoreBtn" class="ads-btn ads-btn-primary">
                  Save Store Configuration
                </button>
              </div>
            </form>
          </div>

          <!-- Section 4: Store Editorial Profile & Policy Fact-Guardrail Editor -->
          <div class="ads-card p-5 border-l-4 border-l-[#1F845A]" id="storeProfileSection">
            <div class="flex items-center justify-between pb-3 mb-4 border-b border-[#DCDFE4] flex-wrap gap-2">
              <div>
                <div class="ads-subhead !text-[#216E4E]">STORE EDITORIAL PROFILE & FACT AUDITOR RULES</div>
                <h2 id="profileSectionTitle" class="text-[16px] font-semibold text-[#172B4D] mt-0.5">Hồ sơ biên tập, Chính sách & Guardrails (data/store_profiles/&lt;store_id&gt;.json)</h2>
              </div>
              <div class="flex items-center gap-2">
                <span id="profileStatusBadge" class="ads-lozenge ads-lozenge-success-bold">ACTIVE VERIFIED</span>
                <span id="profileConfigPath" class="ads-lozenge ads-lozenge-neutral ads-mono">data/store_profiles/wrydeco.json</span>
              </div>
            </div>

            <div class="space-y-4">
              <div class="grid grid-cols-1 sm:grid-cols-4 gap-3">
                <div>
                  <label class="ads-label">Profile Status</label>
                  <select id="ep_profile_status" class="ads-select ads-mono">
                    <option value="active_verified">active_verified</option>
                    <option value="research_seed_not_active_settings">research_seed_not_active_settings</option>
                    <option value="draft">draft</option>
                  </select>
                </div>
                <div>
                  <label class="ads-label">Ready for Publishing</label>
                  <select id="ep_ready_for_publishing" class="ads-select ads-mono">
                    <option value="true">true (Approved)</option>
                    <option value="false">false (Blocked)</option>
                  </select>
                </div>
                <div>
                  <label class="ads-label">Verified Blog Handle</label>
                  <input type="text" id="ep_blog_handle" class="ads-input ads-mono" placeholder="buying-guides" />
                </div>
                <div>
                  <label class="ads-label">Verified Blog GID</label>
                  <input type="text" id="ep_blog_id" class="ads-input ads-mono" placeholder="gid://shopify/Blog/..." />
                </div>
              </div>

              <div>
                <label class="ads-label">Brand Positioning Summary</label>
                <textarea id="ep_brand_summary" rows="2" class="ads-input !h-auto py-1.5"></textarea>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label class="ads-label">Target Audience</label>
                  <textarea id="ep_target_audience" rows="2" class="ads-input !h-auto py-1.5"></textarea>
                </div>
                <div>
                  <label class="ads-label">Editorial Voice (1 dòng / quy tắc)</label>
                  <textarea id="ep_editorial_voice" rows="2" class="ads-input !h-auto py-1.5 ads-mono text-[12px]"></textarea>
                </div>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div class="p-3 rounded-[3px] bg-[#F7F8F9] border border-[#DCDFE4] space-y-2">
                  <div class="flex items-center justify-between">
                    <label class="ads-label !mb-0">Shipping Policy Summary</label>
                    <select id="ep_pol_shipping_conflict" class="ads-select !w-auto !h-6 !py-0 !px-1.5 text-[11px] ads-mono">
                      <option value="none">none</option>
                      <option value="conflict_blocked">conflict_blocked</option>
                      <option value="needs_review">needs_review</option>
                    </select>
                  </div>
                  <textarea id="ep_pol_shipping_summary" rows="2" class="ads-input !h-auto py-1 text-[12px]"></textarea>
                  <label class="ads-label !text-[11px]">Forbidden Shipping Claims (1 dòng / cụm từ cấm)</label>
                  <textarea id="ep_pol_shipping_forbidden" rows="2" class="ads-input !h-auto py-1 text-[11px] ads-mono"></textarea>
                </div>

                <div class="p-3 rounded-[3px] bg-[#F7F8F9] border border-[#DCDFE4] space-y-2">
                  <div class="flex items-center justify-between">
                    <label class="ads-label !mb-0">Returns & Refunds Summary</label>
                    <select id="ep_pol_returns_conflict" class="ads-select !w-auto !h-6 !py-0 !px-1.5 text-[11px] ads-mono">
                      <option value="none">none</option>
                      <option value="conflict_blocked">conflict_blocked</option>
                      <option value="needs_review">needs_review</option>
                    </select>
                  </div>
                  <textarea id="ep_pol_returns_summary" rows="2" class="ads-input !h-auto py-1 text-[12px]"></textarea>
                  <label class="ads-label !text-[11px]">Forbidden Return Claims (1 dòng / cụm từ cấm)</label>
                  <textarea id="ep_pol_returns_forbidden" rows="2" class="ads-input !h-auto py-1 text-[11px] ads-mono"></textarea>
                </div>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div class="p-3 rounded-[3px] bg-[#F7F8F9] border border-[#DCDFE4] space-y-2">
                  <label class="ads-label !mb-0">Cancellation & Warranty Summary</label>
                  <textarea id="ep_pol_cancellation_summary" rows="2" class="ads-input !h-auto py-1 text-[12px]" placeholder="Cancellation..."></textarea>
                  <textarea id="ep_pol_warranty_summary" rows="2" class="ads-input !h-auto py-1 text-[12px]" placeholder="Warranty..."></textarea>
                </div>
                <div class="p-3 rounded-[3px] bg-[#F7F8F9] border border-[#DCDFE4] space-y-2">
                  <label class="ads-label !mb-0">Personalization & Materials Care Summary</label>
                  <textarea id="ep_pol_personalization_summary" rows="2" class="ads-input !h-auto py-1 text-[12px]" placeholder="Personalization..."></textarea>
                  <textarea id="ep_pol_care_summary" rows="2" class="ads-input !h-auto py-1 text-[12px]" placeholder="Materials & Care..."></textarea>
                </div>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label class="ads-label">Do Not Claim Guardrails (1 dòng / điều cấm)</label>
                  <textarea id="ep_do_not_claim" rows="3" class="ads-input !h-auto py-1.5 text-[12px] ads-mono"></textarea>
                </div>
                <div>
                  <label class="ads-label">Unknowns Requiring Shopify API Verification (1 dòng / mục)</label>
                  <textarea id="ep_unknowns" rows="3" class="ads-input !h-auto py-1.5 text-[12px] ads-mono"></textarea>
                </div>
              </div>

              <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 rounded-[3px] bg-[#F7F8F9] border border-[#DCDFE4]">
                <div>
                  <label class="ads-label">Min Body Images</label>
                  <input type="number" id="ep_min_images" value="4" min="4" max="7" class="ads-input ads-mono" />
                </div>
                <div>
                  <label class="ads-label">Max Body Images</label>
                  <input type="number" id="ep_max_images" value="7" min="4" max="7" class="ads-input ads-mono" />
                </div>
                <div>
                  <label class="ads-label">Forbid SVG Fallbacks</label>
                  <input type="text" id="ep_forbid_svg" value="true" readonly class="ads-input ads-mono bg-[#F1F2F4]" />
                </div>
                <div>
                  <label class="ads-label">Mandatory Proxy Gate</label>
                  <input type="text" id="ep_require_proxy" value="true" readonly class="ads-input ads-mono bg-[#F1F2F4]" />
                </div>
              </div>

              <div id="profileValidationBox" class="p-3 rounded-[3px] bg-[#DCFFF1]/50 border border-[#BAF3DB] text-[12px] text-[#216E4E]">
                ✓ Store Editorial Profile hợp lệ theo JSON Schema (<code>schemas/store_editorial_profile.schema.json</code>).
              </div>

              <div class="pt-3 flex items-center justify-between gap-2 border-t border-[#DCDFE4] flex-wrap">
                <div class="flex items-center gap-2">
                  <button type="button" id="btnSeedStoreProfile" onclick="seedStoreProfileFromResearch()" class="ads-btn ads-btn-subtle !h-8 !text-[12px]">
                    ↻ Seed from Research
                  </button>
                  <button type="button" id="btnRecheckProfileSources" onclick="recheckProfileSourcesViaProxy()" class="ads-btn ads-btn-success !h-8 !text-[12px]">
                    ✓ Recheck Policy URLs via Proxy
                  </button>
                </div>
                <button type="button" id="btnSaveStoreProfile" onclick="saveStoreProfile()" class="ads-btn ads-btn-primary !h-8 !text-[12px]">
                  Save Store Editorial Profile
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>

  <script>
    const SETTINGS_DATA = {settings_json};
    let CURRENT_PROFILE_OBJ = null;

    function showToast(msg, isError = false) {{
      const el = document.getElementById('settingsToast');
      el.className = isError ? 'ads-banner ads-banner-danger' : 'ads-banner ads-banner-success';
      el.innerHTML = `
        <span class="font-bold">${{isError ? 'ERROR' : 'SUCCESS'}}</span>
        <div class="flex-1">${{msg}}</div>
      `;
      el.classList.remove('hidden');
    }}

    function initProxyForm(proxyObj) {{
      const px = proxyObj || SETTINGS_DATA.proxy || {{}};
      document.getElementById('px_scheme').value = px.scheme || 'http';
      document.getElementById('px_host').value = px.host || '';
      document.getElementById('px_port').value = px.port || '';
      document.getElementById('px_username').value = px.username || '';
      document.getElementById('px_password').value = px.password || '';
      renderProxyMetrics(px, px.last_check || {{}});
    }}

    function renderProxyMetrics(px, check) {{
      const badgeEl = document.getElementById('proxyStatusBadge');
      const boxEl = document.getElementById('proxyMetricsBox');
      const hasCheck = check && typeof check.stable === 'boolean';

      if (!px || !px.is_configured) {{
        badgeEl.className = 'ads-lozenge ads-lozenge-danger';
        badgeEl.textContent = 'UNCONFIGURED · SHOPIFY BLOCKED';
        boxEl.innerHTML = `<div class="text-[#AE2E24] font-semibold">✗ Proxy chưa được cấu hình. Mọi kết nối tới Shopify đang bị chặn.</div>`;
        return;
      }}

      if (hasCheck && check.stable) {{
        badgeEl.className = 'ads-lozenge ads-lozenge-success-bold';
        badgeEl.textContent = `PROXY STABLE · ${{px.host}}:${{px.port}}`;
        boxEl.innerHTML = `
          <div class="flex items-center justify-between text-[#216E4E] font-semibold">
            <span>✓ Proxy ổn định — Cho phép giao tiếp với Shopify</span>
            <span class="ads-mono">${{check.avg_latency_ms || 0}} ms</span>
          </div>
          <div class="grid grid-cols-2 gap-1 pt-1 text-[#44546F] border-t border-[#DCDFE4]">
            <div>Exit IP: <strong class="ads-mono text-[#172B4D]">${{check.exit_ip || px.host}}</strong></div>
            <div>Probes: <strong class="text-[#216E4E]">${{check.probes_passed}}/${{check.probes_total}} Passed</strong></div>
            <div>Shopify HTTP: <strong class="ads-mono text-[#172B4D]">${{check.shopify_status_code || 200}}</strong></div>
            <div>Checked: <span class="ads-mono text-[11px]">${{(check.checked_at || '').slice(11, 19) || 'Just now'}} UTC</span></div>
          </div>
        `;
      }} else if (hasCheck && !check.stable) {{
        badgeEl.className = 'ads-lozenge ads-lozenge-danger';
        badgeEl.textContent = `PROXY UNSTABLE · SHOPIFY BLOCKED`;
        boxEl.innerHTML = `
          <div class="text-[#AE2E24] font-semibold">✗ Proxy không ổn định — Đã chặn toàn bộ kết nối tới Shopify!</div>
          <div class="text-[11px] text-[#AE2E24] ads-mono mt-1">${{check.error || 'Connection timeout or proxy authentication failed'}}</div>
        `;
      }} else {{
        badgeEl.className = 'ads-lozenge ads-lozenge-inprogress';
        badgeEl.textContent = `CONFIGURED · ${{px.host}}:${{px.port}}`;
        boxEl.innerHTML = `
          <div class="text-[#44546F]">Proxy hiện tại: <code class="ads-mono font-semibold text-[#172B4D]">${{px.masked_summary}}</code>. Bấm <strong>Check Độ Ổn Định Proxy</strong> để kiểm tra kết nối trực tiếp tới Shopify.</div>
        `;
      }}
    }}

    function collectProxyFormPayload() {{
      return {{
        scheme: document.getElementById('px_scheme').value.trim() || 'http',
        host: document.getElementById('px_host').value.trim(),
        port: parseInt(document.getElementById('px_port').value.trim() || '0', 10),
        username: document.getElementById('px_username').value.trim(),
        password: document.getElementById('px_password').value.trim(),
      }};
    }}

    async function checkProxyStability() {{
      const formCfg = collectProxyFormPayload();
      showToast(`Đang kiểm tra độ ổn định của Proxy <strong>${{formCfg.host}}:${{formCfg.port}}</strong> tới Shopify...`);
      const res = await fetch('/api/proxy/check', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ proxy: formCfg, save: true }})
      }});
      const data = await res.json();
      SETTINGS_DATA.proxy = data.proxy || SETTINGS_DATA.proxy;
      renderProxyMetrics(SETTINGS_DATA.proxy, data.check);
      if (!data.ok || !data.check?.stable) {{
        showToast(`Proxy KHÔNG ổn định (${{formCfg.host}}:${{formCfg.port}}): ${{data.check?.error || data.error || 'Failed'}}. Mọi kết nối tới Shopify đã bị chặn!`, true);
        return;
      }}
      showToast(`Proxy <strong>${{data.check.exit_ip}}:${{formCfg.port}}</strong> hoạt động ỔN ĐỊNH (${{data.check.probes_passed}}/${{data.check.probes_total}} probes thành công, độ trễ TB <strong>${{data.check.avg_latency_ms}}ms</strong>, Shopify HTTP ${{data.check.shopify_status_code}})!`);
    }}

    async function saveProxyConfig() {{
      const formCfg = collectProxyFormPayload();
      showToast(`Đang lưu cấu hình Proxy vào <code>data/proxy.json</code> và kiểm tra độ ổn định...`);
      const res = await fetch('/api/proxy', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(formCfg)
      }});
      const data = await res.json();
      if (data.proxy) {{
        SETTINGS_DATA.proxy = data.proxy;
        initProxyForm(data.proxy);
      }}
      if (!data.ok || (data.check && !data.check.stable)) {{
        showToast(`Đã lưu cấu hình nhưng Proxy KHÔNG ổn định: ${{data.check?.error || data.error || ''}} — Mọi kết nối tới Shopify hiện bị chặn!`, true);
        return;
      }}
      showToast(`Đã lưu Proxy <strong>${{data.proxy.masked_summary}}</strong> vào <code>data/proxy.json</code> và xác nhận kết nối ổn định (${{data.check.avg_latency_ms}}ms)!`);
    }}

    async function resetProxyFromDocs() {{
      showToast('Đang khôi phục thông tin Proxy mặc định từ <code>docs/proxy-credentials.md</code>...');
      const res = await fetch('/api/proxy/reset-default', {{ method: 'POST' }});
      const data = await res.json();
      if (data.proxy) {{
        SETTINGS_DATA.proxy = data.proxy;
        initProxyForm(data.proxy);
      }}
      if (!data.ok) {{
        showToast('Lỗi khôi phục Proxy mặc định: ' + (data.error || ''), true);
        return;
      }}
      showToast(`Đã nạp Proxy mặc định <strong>${{data.proxy.masked_summary}}</strong> từ <code>docs/proxy-credentials.md</code> (Exit IP: ${{data.check?.exit_ip}}, ${{data.check?.avg_latency_ms}}ms)!`);
    }}

    function initZbigteeAuthForm() {{
      const auth = SETTINGS_DATA.zbigtee_auth || {{}};
      document.getElementById('zb_session_token').value = auth.session_token || '';
      document.getElementById('zb_workspace_id').value = auth.workspace_id || '';
    }}

    async function saveZbigteeAuth() {{
      const token = document.getElementById('zb_session_token').value.trim();
      const wsId = document.getElementById('zb_workspace_id').value.trim();
      const res = await fetch('/api/zbigtee/auth', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ session_token: token, workspace_id: wsId }})
      }});
      const data = await res.json();
      if (!data.ok) {{
        showToast('Lỗi lưu Zbigtee Auth: ' + (data.error || ''), true);
        return;
      }}
      showToast('Đã lưu phiên đăng nhập Zbigtee vào <code>data/zbigtee_auth.json</code>!');
    }}

    async function verifyZbigteeAuth() {{
      showToast('Đang kiểm tra kết nối trực tiếp tới <strong>https://zbigtee.com/</strong> bằng <code>data/zbigtee_auth.json</code>...');
      const res = await fetch('/api/zbigtee/verify-auth', {{ method: 'POST' }});
      const data = await res.json();
      if (!data.ok) {{
        showToast('Phiên Zbigtee không hợp lệ: ' + (data.error || ''), true);
        return;
      }}
      showToast(`Kết nối Zbigtee hợp lệ (HTTP ${{data.status_code}})! Tìm thấy <strong>${{data.projects_count}}</strong> Projects trực tiếp trên zbigtee.com.`);
    }}

    function renderStoresList() {{
      const container = document.getElementById('storesListContainer');
      container.innerHTML = SETTINGS_DATA.stores.map(s => {{
        const isActive = s.id === SETTINGS_DATA.active_store_id;
        const statusBadge = s.is_configured
          ? `<span class="ads-lozenge ads-lozenge-success">CONNECTED · ${{s.normalized_shop}}</span>`
          : `<span class="ads-lozenge ads-lozenge-warning">PENDING CREDENTIALS</span>`;
        const prof = (SETTINGS_DATA.store_profiles || {{}})[s.id];
        const profBadge = (prof && prof.ready_for_publishing)
          ? `<span class="ads-lozenge ads-lozenge-inprogress">PROFILE VERIFIED</span>`
          : `<span class="ads-lozenge ads-lozenge-neutral">PROFILE DRAFT</span>`;
        const blogsCount = (s.blogs_cache || []).length;

        return `
          <div class="ads-issue-card ${{isActive ? 'in-review' : ''}} space-y-2">
            <div class="flex items-center justify-between gap-2 flex-wrap">
              <div class="flex items-center gap-1.5 flex-wrap">
                <span class="font-semibold text-[14px] text-[#172B4D]">${{s.name}}</span>
                <code class="ads-lozenge ads-lozenge-neutral ads-mono">${{s.id}}</code>
                ${{statusBadge}}
                ${{profBadge}}
              </div>
              <div class="flex items-center gap-1.5">
                <button onclick="loadStoreIntoForm('${{s.id}}')" class="ads-btn ads-btn-subtle !h-7 !px-2.5 !text-[12px]">
                  Edit
                </button>
                <button onclick="testStoreById('${{s.id}}')" class="ads-btn ads-btn-primary !h-7 !px-2.5 !text-[12px]">
                  Test OAuth
                </button>
                <button onclick="deleteStoreById('${{s.id}}')" class="ads-btn ads-btn-danger-subtle !h-7 !px-2.5 !text-[12px]">
                  Delete
                </button>
              </div>
            </div>
            <div class="text-[12px] text-[#44546F] grid grid-cols-2 gap-1 pt-1 border-t border-[#F1F2F4]">
              <div>Zbigtee: <strong class="text-[#172B4D]">${{s.zbigtee_domain || '—'}}</strong></div>
              <div>File: <code class="ads-mono text-[11px]">data/${{s.config_file}}</code></div>
              <div>Default Blog: <strong class="text-[#0C66E4]">${{s.default_blog_handle}}</strong> (${{blogsCount}} cached)</div>
              <div>Profile: <code class="ads-mono text-[11px]">data/store_profiles/${{s.id}}.json</code></div>
            </div>
          </div>
        `;
      }}).join('');
    }}

    function populateProfileForm(storeId, prof) {{
      CURRENT_PROFILE_OBJ = prof || null;
      document.getElementById('profileSectionTitle').textContent = `Hồ sơ Biên tập & Chính sách: ${{storeId.toUpperCase()}}`;
      document.getElementById('profileConfigPath').textContent = `data/store_profiles/${{storeId}}.json`;

      const badge = document.getElementById('profileStatusBadge');
      const valBox = document.getElementById('profileValidationBox');
      if (!prof) {{
        badge.className = 'ads-lozenge ads-lozenge-warning';
        badge.textContent = 'MISSING PROFILE';
        valBox.className = 'p-3 rounded-[3px] bg-[#FFF7D6] border border-[#F8E6A0] text-[12px] text-[#7F5F01]';
        valBox.innerHTML = `Chưa có hồ sơ biên tập cho store <strong>${{storeId}}</strong>. Bấm <strong>Seed from Research</strong> để khởi tạo tự động.`;
        return;
      }}

      document.getElementById('ep_profile_status').value = prof.profile_status || 'active_verified';
      document.getElementById('ep_ready_for_publishing').value = prof.ready_for_publishing ? 'true' : 'false';
      const dest = prof.verified_destination_blog || {{}};
      document.getElementById('ep_blog_handle').value = dest.blog_handle || '';
      document.getElementById('ep_blog_id').value = dest.blog_id || '';

      const bp = prof.brand_positioning || {{}};
      document.getElementById('ep_brand_summary').value = bp.summary || '';
      document.getElementById('ep_target_audience').value = bp.target_audience || '';
      document.getElementById('ep_editorial_voice').value = (bp.editorial_voice || []).join('\\n');

      const pol = prof.policies || {{}};
      const ship = pol.shipping || {{}};
      const ret = pol.returns_refunds || {{}};
      const canc = pol.cancellation || {{}};
      const warr = pol.warranty_support || {{}};
      const pers = pol.personalization_customization || {{}};
      const care = pol.materials_care || {{}};

      document.getElementById('ep_pol_shipping_conflict').value = ship.conflict_status || 'none';
      document.getElementById('ep_pol_shipping_summary').value = ship.summary || '';
      document.getElementById('ep_pol_shipping_forbidden').value = (ship.forbidden_claims || []).join('\\n');

      document.getElementById('ep_pol_returns_conflict').value = ret.conflict_status || 'none';
      document.getElementById('ep_pol_returns_summary').value = ret.summary || '';
      document.getElementById('ep_pol_returns_forbidden').value = (ret.forbidden_claims || []).join('\\n');

      document.getElementById('ep_pol_cancellation_summary').value = canc.summary || '';
      document.getElementById('ep_pol_warranty_summary').value = warr.summary || '';
      document.getElementById('ep_pol_personalization_summary').value = pers.summary || '';
      document.getElementById('ep_pol_care_summary').value = care.summary || '';

      document.getElementById('ep_do_not_claim').value = (prof.do_not_claim || []).join('\\n');
      document.getElementById('ep_unknowns').value = (prof.unknowns_requiring_shopify_verification || []).join('\\n');

      const gate = prof.product_and_media_gate || {{}};
      document.getElementById('ep_min_images').value = gate.min_body_images || 4;
      document.getElementById('ep_max_images').value = gate.max_body_images || 7;

      const val = prof._validation || {{ valid: true, errors: [], warnings: [] }};
      if (val.valid && prof.ready_for_publishing) {{
        badge.className = 'ads-lozenge ads-lozenge-success-bold';
        badge.textContent = 'ACTIVE VERIFIED · READY';
        const warnText = (val.warnings || []).length ? `<div class="mt-1 text-[#7F5F01]">⚠ Guardrail Note: ${{val.warnings.join('; ')}}</div>` : '';
        valBox.className = 'p-3 rounded-[3px] bg-[#DCFFF1]/50 border border-[#BAF3DB] text-[12px] text-[#216E4E]';
        valBox.innerHTML = `<div>✓ Hồ sơ biên tập hợp lệ theo Schema (Last verified: <code>${{(prof.audit_metadata || {{}}).last_verified_at || '—'}}</code>).</div>${{warnText}}`;
      }} else {{
        badge.className = 'ads-lozenge ads-lozenge-warning';
        badge.textContent = prof.profile_status || 'DRAFT';
        valBox.className = 'p-3 rounded-[3px] bg-[#FFF7D6] border border-[#F8E6A0] text-[12px] text-[#7F5F01]';
        valBox.innerHTML = `<div>Trạng thái hồ sơ: <strong>${{prof.profile_status}}</strong>. Errors: ${{(val.errors || []).join('; ') || 'None'}}</div>`;
      }}
    }}

    function loadStoreIntoForm(storeId) {{
      const s = SETTINGS_DATA.stores.find(item => item.id === storeId);
      if (!s) return;
      document.getElementById('formTitle').textContent = 'Cập nhật Store: ' + s.name;
      document.getElementById('formConfigPath').textContent = 'data/' + (s.config_file || ('stores/' + s.id + '.json'));
      document.getElementById('f_id').value = s.id || '';
      document.getElementById('f_name').value = s.name || '';
      document.getElementById('f_zbigtee_domain').value = s.zbigtee_domain || '';
      document.getElementById('f_zbigtee_project_id').value = s.zbigtee_project_id || '';
      document.getElementById('f_shopify_shop').value = s.shopify_shop || '';
      document.getElementById('f_public_domain').value = s.public_domain || '';
      document.getElementById('f_client_id').value = s.client_id || '';
      document.getElementById('f_client_secret').value = s.client_secret || '';
      document.getElementById('f_admin_token').value = s.admin_token || '';
      document.getElementById('f_storefront_password').value = s.storefront_password || '';
      document.getElementById('f_default_blog_handle').value = s.default_blog_handle || 'buying-guides';
      document.getElementById('f_default_author').value = s.default_author || 'Editorial Team';
      document.getElementById('f_api_version').value = s.api_version || '2026-07';
      document.getElementById('f_notes').value = s.notes || '';

      const prof = (SETTINGS_DATA.store_profiles || {{}})[s.id] || null;
      populateProfileForm(s.id, prof);
    }}

    async function saveStoreProfile() {{
      const storeId = document.getElementById('f_id').value.trim();
      if (!storeId) {{
        showToast('Vui lòng chọn một Store trước khi lưu Editorial Profile!', true);
        return;
      }}
      const baseProf = CURRENT_PROFILE_OBJ ? JSON.parse(JSON.stringify(CURRENT_PROFILE_OBJ)) : {{}};
      baseProf.store_id = storeId;
      baseProf.profile_status = document.getElementById('ep_profile_status').value;
      baseProf.ready_for_publishing = document.getElementById('ep_ready_for_publishing').value === 'true';

      baseProf.verified_destination_blog = baseProf.verified_destination_blog || {{}};
      baseProf.verified_destination_blog.blog_handle = document.getElementById('ep_blog_handle').value.trim();
      baseProf.verified_destination_blog.blog_id = document.getElementById('ep_blog_id').value.trim();
      baseProf.verified_destination_blog.default_author = document.getElementById('f_default_author').value.trim() || 'Editorial Team';

      baseProf.brand_positioning = baseProf.brand_positioning || {{ evidence: [] }};
      baseProf.brand_positioning.summary = document.getElementById('ep_brand_summary').value.trim();
      baseProf.brand_positioning.target_audience = document.getElementById('ep_target_audience').value.trim();
      baseProf.brand_positioning.editorial_voice = document.getElementById('ep_editorial_voice').value.split('\\n').map(x => x.trim()).filter(Boolean);

      baseProf.policies = baseProf.policies || {{}};
      baseProf.policies.shipping = baseProf.policies.shipping || {{ allowed_claims: [], forbidden_claims: [], evidence: [] }};
      baseProf.policies.shipping.conflict_status = document.getElementById('ep_pol_shipping_conflict').value;
      baseProf.policies.shipping.summary = document.getElementById('ep_pol_shipping_summary').value.trim();
      baseProf.policies.shipping.forbidden_claims = document.getElementById('ep_pol_shipping_forbidden').value.split('\\n').map(x => x.trim()).filter(Boolean);

      baseProf.policies.returns_refunds = baseProf.policies.returns_refunds || {{ allowed_claims: [], forbidden_claims: [], evidence: [] }};
      baseProf.policies.returns_refunds.conflict_status = document.getElementById('ep_pol_returns_conflict').value;
      baseProf.policies.returns_refunds.summary = document.getElementById('ep_pol_returns_summary').value.trim();
      baseProf.policies.returns_refunds.forbidden_claims = document.getElementById('ep_pol_returns_forbidden').value.split('\\n').map(x => x.trim()).filter(Boolean);

      if (baseProf.policies.cancellation) baseProf.policies.cancellation.summary = document.getElementById('ep_pol_cancellation_summary').value.trim();
      if (baseProf.policies.warranty_support) baseProf.policies.warranty_support.summary = document.getElementById('ep_pol_warranty_summary').value.trim();
      if (baseProf.policies.personalization_customization) baseProf.policies.personalization_customization.summary = document.getElementById('ep_pol_personalization_summary').value.trim();
      if (baseProf.policies.materials_care) baseProf.policies.materials_care.summary = document.getElementById('ep_pol_care_summary').value.trim();

      baseProf.do_not_claim = document.getElementById('ep_do_not_claim').value.split('\\n').map(x => x.trim()).filter(Boolean);
      baseProf.unknowns_requiring_shopify_verification = document.getElementById('ep_unknowns').value.split('\\n').map(x => x.trim()).filter(Boolean);

      baseProf.product_and_media_gate = baseProf.product_and_media_gate || {{}};
      baseProf.product_and_media_gate.min_body_images = parseInt(document.getElementById('ep_min_images').value || '4', 10);
      baseProf.product_and_media_gate.max_body_images = parseInt(document.getElementById('ep_max_images').value || '7', 10);
      baseProf.product_and_media_gate.require_shopify_api_verification = true;
      baseProf.product_and_media_gate.require_online_store_publication = true;
      baseProf.product_and_media_gate.require_proxy_for_all_shopify_requests = true;
      baseProf.product_and_media_gate.forbid_svg_fallbacks = true;
      baseProf.product_and_media_gate.forbid_unverified_gallery_alt_mapping = true;

      const res = await fetch(`/api/stores/${{encodeURIComponent(storeId)}}/profile`, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(baseProf)
      }});
      const data = await res.json();
      if (!data.ok) {{
        showToast(`Lỗi lưu Store Editorial Profile (${{storeId}}): ${{data.error || 'Validation failed'}}`, true);
        return;
      }}
      SETTINGS_DATA.store_profiles[storeId] = data.profile;
      populateProfileForm(storeId, data.profile);
      showToast(`Đã lưu và xác thực Store Editorial Profile cho <strong>${{storeId}}</strong> tại <code>data/store_profiles/${{storeId}}.json</code>!`);
    }}

    async function seedStoreProfileFromResearch() {{
      const storeId = document.getElementById('f_id').value.trim();
      if (!storeId) return;
      showToast(`Đang nạp Store Editorial Profile từ <code>data/store_editorial_research_2026-10-17.json</code> cho <strong>${{storeId}}</strong>...`);
      const res = await fetch(`/api/stores/${{encodeURIComponent(storeId)}}/profile/seed-from-research`, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ overwrite: true }})
      }});
      const data = await res.json();
      if (!data.ok) {{
        showToast('Lỗi Seed Profile: ' + (data.error || ''), true);
        return;
      }}
      SETTINGS_DATA.store_profiles[storeId] = data.profile;
      populateProfileForm(storeId, data.profile);
      showToast(`Đã seed & xác thực Store Editorial Profile cho <strong>${{storeId}}</strong>!`);
    }}

    async function recheckProfileSourcesViaProxy() {{
      const storeId = document.getElementById('f_id').value.trim();
      if (!storeId) return;
      showToast(`Đang kiểm tra trực tiếp các URL Chính sách & Blog của <strong>${{storeId}}</strong> thông qua Proxy bắt buộc...`);
      const res = await fetch(`/api/stores/${{encodeURIComponent(storeId)}}/profile/recheck-sources`, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{}})
      }});
      const data = await res.json();
      if (!data.ok) {{
        showToast(`Kiểm tra nguồn URL cho ${{storeId}} phát hiện lỗi: ${{data.error || 'Một số URL không trả HTTP 200'}}`, true);
        return;
      }}
      SETTINGS_DATA.store_profiles[storeId] = data.profile;
      populateProfileForm(storeId, data.profile);
      showToast(`Đã xác minh trực tiếp <strong>${{data.checked_count}}</strong> URL Chính sách & Blog của <strong>${{storeId}}</strong> qua Proxy (100% HTTP 200)!`);
    }}

    function resetFormForNewStore() {{
      document.getElementById('formTitle').textContent = 'Thêm Store Mới';
      document.getElementById('formConfigPath').textContent = 'data/stores/<new_store>.json';
      document.getElementById('storeForm').reset();
      document.getElementById('f_api_version').value = '2026-07';
      document.getElementById('f_default_blog_handle').value = 'buying-guides';
    }}

    async function handleSaveStore(e) {{
      e.preventDefault();
      const payload = {{
        id: document.getElementById('f_id').value.trim(),
        name: document.getElementById('f_name').value.trim(),
        zbigtee_domain: document.getElementById('f_zbigtee_domain').value.trim(),
        zbigtee_project_id: document.getElementById('f_zbigtee_project_id').value.trim(),
        shopify_shop: document.getElementById('f_shopify_shop').value.trim(),
        public_domain: document.getElementById('f_public_domain').value.trim(),
        client_id: document.getElementById('f_client_id').value.trim(),
        client_secret: document.getElementById('f_client_secret').value.trim(),
        admin_token: document.getElementById('f_admin_token').value.trim(),
        storefront_password: document.getElementById('f_storefront_password').value.trim(),
        default_blog_handle: document.getElementById('f_default_blog_handle').value.trim(),
        default_author: document.getElementById('f_default_author').value.trim(),
        api_version: document.getElementById('f_api_version').value.trim(),
        notes: document.getElementById('f_notes').value.trim(),
      }};
      const res = await fetch('/api/stores', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(payload)
      }});
      const data = await res.json();
      if (!data.ok) {{
        showToast('Lỗi lưu Store: ' + (data.detail || data.error), true);
        return;
      }}
      showToast(`Đã lưu cấu hình Store <strong>${{data.store.name}}</strong> vào <code>data/${{data.store.config_file}}</code>!`);
      setTimeout(() => window.location.reload(), 600);
    }}

    async function testStoreById(storeId) {{
      showToast(`Đang kiểm tra kết nối OAuth (qua Proxy bắt buộc) & tải danh sách Blog cho store <strong>${{storeId}}</strong>...`);
      const res = await fetch(`/api/stores/${{encodeURIComponent(storeId)}}/test-connection`, {{ method: 'POST' }});
      const data = await res.json();
      if (!data.ok) {{
        showToast(`Kết nối thất bại (${{storeId}}): ${{data.error}}`, true);
        return;
      }}
      showToast(`Kết nối thành công tới <strong>${{data.shop_name}}</strong> (${{data.myshopify_domain}}) qua Proxy <code>${{data.proxy_used || ''}}</code>! Đã đồng bộ ${{data.blogs.length}} chuyên mục Blog.`);
      setTimeout(() => window.location.reload(), 800);
    }}

    async function handleTestConnectionFromForm() {{
      const storeId = document.getElementById('f_id').value.trim();
      if (!storeId) {{
        showToast('Vui lòng nhập Store ID và Lưu trước khi Test Connection.', true);
        return;
      }}
      await handleSaveStore(new Event('submit'));
      await testStoreById(storeId);
    }}

    async function deleteStoreById(storeId) {{
      if (!confirm(`Bạn có chắc chắn muốn xóa cấu hình của store '${{storeId}}'?`)) return;
      const res = await fetch(`/api/stores/${{encodeURIComponent(storeId)}}`, {{ method: 'DELETE' }});
      const data = await res.json();
      if (!data.ok) {{
        showToast('Không thể xóa store: ' + (data.detail || ''), true);
        return;
      }}
      showToast(`Đã xóa store <strong>${{storeId}}</strong>.`);
      setTimeout(() => window.location.reload(), 500);
    }}

    async function syncFromZbigtee() {{
      showToast('Đang cào danh sách Projects trực tiếp từ <strong>https://zbigtee.com/</strong>...');
      const res = await fetch('/api/stores/sync-zbigtee', {{ method: 'POST' }});
      const data = await res.json();
      showToast(`Đã đồng bộ trực tiếp danh sách Project từ Zbigtee (${{data.stores.length}} stores, mới thêm: ${{data.added.length}}).`);
      setTimeout(() => window.location.reload(), 600);
    }}

    initProxyForm();
    initZbigteeAuthForm();
    renderStoresList();
    const urlParams = new URLSearchParams(window.location.search);
    const editId = urlParams.get('edit') || SETTINGS_DATA.active_store_id;
    if (editId) loadStoreIntoForm(editId);
  </script>
</body>
</html>"""
    return html_content


class Module5RequestHandler(BaseHTTPRequestHandler):
    """Pure Python HTTP request handler for Multi-Store Dashboard & Settings API."""

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_html(self, html_body: str, status: int = 200) -> None:
        encoded = html_body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _read_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw else {}

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/":
            store_param = (qs.get("store") or [None])[0]
            self._send_html(render_dashboard_html(store=store_param))
            return

        if path == "/settings":
            self._send_html(render_settings_html())
            return

        if path == "/diagram":
            diag_file = MODULE_DIR / "diagram-pipeline.html"
            if diag_file.exists():
                self._send_html(diag_file.read_text(encoding="utf-8"))
            else:
                self._send_html("<h1>Diagram not found</h1>", status=404)
            return

        if path == "/api/stores":
            sm = StoreManager()
            self._send_json(
                {
                    "ok": True,
                    "active_store_id": sm.get_active_store_id(),
                    "stores": [s.to_dict(mask_secrets=False) for s in sm.list_stores()],
                }
            )
            return

        if path.startswith("/api/stores/") and path.endswith("/profile"):
            parts = [unquote(p) for p in path.split("/") if p]
            store_id = parts[2] if len(parts) >= 4 else ""
            sm = StoreManager()
            spm = StoreProfileManager(store_manager=sm)
            try:
                prof = spm.get_profile(store_id)
                self._send_json({"ok": True, "store_id": store_id, "profile": prof})
            except Exception as exc:
                self._send_json({"ok": False, "store_id": store_id, "error": str(exc)}, status=404)
            return

        if path == "/api/proxy":
            sm = StoreManager()
            self._send_json(
                {
                    "ok": True,
                    "proxy": sm.proxy_manager.get_config().to_dict(),
                }
            )
            return

        if path == "/api/zbigtee/auth":
            self._send_json({"ok": True, "auth": ZbigteeUiOperator.get_auth_state()})
            return

        if path.startswith("/api/screenshots/"):
            parts = [unquote(p) for p in path.split("/") if p]
            if len(parts) >= 4:
                store_id = slugify_store_id(parts[2])
                filename = parts[3]
                file_path = OUTPUT_DIR / store_id / filename
                if file_path.exists():
                    data = file_path.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
            self._send_json({"ok": False, "error": "Screenshot not found"}, status=404)
            return

        self._send_json({"ok": False, "error": f"Not found: {path}"}, status=404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_json_body()
        sm = StoreManager()
        spm = StoreProfileManager(store_manager=sm)

        if path == "/api/proxy":
            try:
                cfg = sm.proxy_manager.save_config(body)
                active_shop = sm.get_store().normalized_shop or "wrydeco.myshopify.com"
                check_report = sm.proxy_manager.check_stability(target_shop_domain=active_shop, probes=2)
                updated_cfg = sm.proxy_manager.get_config()
                self._send_json(
                    {
                        "ok": bool(check_report.get("stable")),
                        "proxy": updated_cfg.to_dict(),
                        "check": check_report,
                        "error": check_report.get("error") or "",
                    },
                    status=200 if check_report.get("stable") else 400,
                )
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)
            return

        if path == "/api/proxy/check":
            try:
                proxy_payload = body.get("proxy") if isinstance(body.get("proxy"), dict) else body
                if body.get("save", True) and proxy_payload and (proxy_payload.get("host") is not None or proxy_payload.get("ip") is not None):
                    sm.proxy_manager.save_config(proxy_payload)
                    override = None
                else:
                    override = proxy_payload if (proxy_payload and proxy_payload.get("host")) else None
                active_shop = sm.get_store().normalized_shop or "wrydeco.myshopify.com"
                check_report = sm.proxy_manager.check_stability(
                    target_shop_domain=active_shop,
                    probes=int(body.get("probes") or 2),
                    override_config=override,
                )
                updated_cfg = sm.proxy_manager.get_config()
                self._send_json(
                    {
                        "ok": bool(check_report.get("stable")),
                        "proxy": updated_cfg.to_dict(),
                        "check": check_report,
                        "error": check_report.get("error") or "",
                    },
                    status=200 if check_report.get("stable") else 400,
                )
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)
            return

        if path == "/api/proxy/reset-default":
            try:
                sm.proxy_manager.reset_to_default_docs()
                active_shop = sm.get_store().normalized_shop or "wrydeco.myshopify.com"
                check_report = sm.proxy_manager.check_stability(target_shop_domain=active_shop, probes=2)
                updated_cfg = sm.proxy_manager.get_config()
                self._send_json(
                    {
                        "ok": bool(check_report.get("stable")),
                        "proxy": updated_cfg.to_dict(),
                        "check": check_report,
                    }
                )
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)
            return

        if path == "/api/stores/select":
            try:
                store = sm.set_active_store(body.get("store_id") or "")
                self._send_json({"ok": True, "active_store_id": store.id, "store": store.to_dict()})
            except KeyError as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=404)
            return

        if path == "/api/stores":
            if not body.get("id"):
                body["id"] = slugify_store_id(body.get("name") or body.get("zbigtee_domain") or "store")
            store = sm.save_store(body, set_active=bool(body.get("set_active")))
            self._send_json({"ok": True, "store": store.to_dict()})
            return

        if path.startswith("/api/stores/") and path.endswith("/test-connection"):
            parts = [unquote(p) for p in path.split("/") if p]
            store_id = parts[2] if len(parts) >= 4 else ""
            try:
                res = sm.test_connection_and_fetch_blogs(store_id)
                self._send_json(res)
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)
            return

        if path.startswith("/api/stores/") and path.endswith("/profile"):
            parts = [unquote(p) for p in path.split("/") if p]
            store_id = parts[2] if len(parts) >= 4 else ""
            try:
                saved = spm.save_profile(store_id, body)
                self._send_json({"ok": True, "store_id": store_id, "profile": saved})
            except Exception as exc:
                self._send_json({"ok": False, "store_id": store_id, "error": str(exc)}, status=400)
            return

        if path.startswith("/api/stores/") and path.endswith("/profile/seed-from-research"):
            parts = [unquote(p) for p in path.split("/") if p]
            store_id = parts[2] if len(parts) >= 5 else ""
            try:
                seeded = spm.seed_from_research(store_id, overwrite=bool(body.get("overwrite", True)))
                self._send_json({"ok": True, "store_id": store_id, "profile": seeded})
            except Exception as exc:
                self._send_json({"ok": False, "store_id": store_id, "error": str(exc)}, status=400)
            return

        if path.startswith("/api/stores/") and path.endswith("/profile/recheck-sources"):
            parts = [unquote(p) for p in path.split("/") if p]
            store_id = parts[2] if len(parts) >= 5 else ""
            try:
                rechecked = spm.recheck_profile_sources_via_proxy(
                    store_id,
                    check_collections=bool(body.get("check_collections", False)),
                )
                self._send_json(rechecked, status=200 if rechecked.get("ok") else 400)
            except Exception as exc:
                self._send_json({"ok": False, "store_id": store_id, "error": str(exc)}, status=400)
            return

        if path == "/api/zbigtee/auth":
            try:
                auth_state = ZbigteeUiOperator.save_auth_session(
                    session_token=body.get("session_token") or "",
                    workspace_id=body.get("workspace_id") or "",
                )
                self._send_json({"ok": True, "auth": auth_state})
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)
            return

        if path == "/api/zbigtee/verify-auth":
            try:
                res = ZbigteeUiOperator.verify_auth_session()
                self._send_json(res)
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)
            return

        if path == "/api/zbigtee/fetch-live":
            try:
                zb = ZbigteeUiOperator(sm, body.get("store_id"))
                res = zb.fetch_all_live_from_zbigtee(use_playwright=bool(body.get("use_playwright", True)))
                self._send_json(res)
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)
            return

        if path == "/api/stores/sync-zbigtee":
            existing_ids = {s.id for s in sm.list_stores()}
            added = []
            for proj in ZbigteeUiOperator.fetch_live_projects():
                if proj["id"] not in existing_ids:
                    sm.save_store(
                        {
                            "id": proj["id"],
                            "name": proj["name"],
                            "zbigtee_project_id": proj["zbigtee_project_id"],
                            "zbigtee_domain": proj["zbigtee_domain"],
                            "public_domain": f"https://{proj['zbigtee_domain']}",
                            "notes": "Live-scraped from Zbigtee workspace",
                        }
                    )
                    added.append(proj["id"])
            self._send_json(
                {
                    "ok": True,
                    "added": added,
                    "stores": [s.to_dict() for s in sm.list_stores()],
                }
            )
            return

        if path == "/api/pipeline/postprocess":
            try:
                pipe = BlogSyncPipeline(sm, body.get("store_id"))
                res = pipe.postprocess_only(body.get("content_id") or "01a0fb95-71df-79a0-83d4-83f747201ef5")
                self._send_json(res)
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)
            return

        if path == "/api/pipeline/sync":
            try:
                pipe = BlogSyncPipeline(sm, body.get("store_id"))
                res = pipe.sync_and_publish(
                    body.get("content_id") or "01a0fb95-71df-79a0-83d4-83f747201ef5",
                    blog_id_or_handle=body.get("blog_handle"),
                    verify=bool(body.get("verify", True)),
                )
                self._send_json(res)
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)
            return

        if path == "/api/pipeline/article-editor":
            try:
                pipe = BlogSyncPipeline(sm, body.get("store_id"))
                res = pipe.get_article_editor_data(
                    body.get("content_id") or "01a0fb95-71df-79a0-83d4-83f747201ef5",
                    fetch_live_shopify=bool(body.get("fetch_live", False)),
                )
                self._send_json(res)
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)
            return

        if path == "/api/pipeline/update-article":
            try:
                pipe = BlogSyncPipeline(sm, body.get("store_id"))
                res = pipe.update_article_comprehensive(body)
                self._send_json(res)
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)
            return

        self._send_json({"ok": False, "error": f"Unknown POST endpoint: {path}"}, status=404)

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/stores/"):
            store_id = unquote(path.split("/api/stores/", 1)[1].strip("/"))
            sm = StoreManager()
            deleted = sm.delete_store(store_id)
            if not deleted:
                self._send_json({"ok": False, "detail": f"Store '{store_id}' not found"}, status=404)
                return
            self._send_json(
                {
                    "ok": True,
                    "deleted_store_id": store_id,
                    "active_store_id": sm.get_active_store_id(),
                }
            )
            return
        self._send_json({"ok": False, "error": f"Unknown DELETE endpoint: {path}"}, status=404)


def create_http_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Module5RequestHandler)


def serve_web_app(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = create_http_server(host, port)
    print(f"Multi-Store Blog Automation Web UI running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

