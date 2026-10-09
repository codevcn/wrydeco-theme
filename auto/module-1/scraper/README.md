# Amazon–Shopify queue scraper

The system has four independent parts:

1. One Playwright crawler verifies Amazon data and prices sequentially.
2. SQLite stores durable content/apply queues and the Event Log.
3. Flask owns one long-lived Antigravity control conversation plus one isolated content conversation per product.
4. One Shopify worker applies ready products sequentially from idempotent checkpoints.

Flask starts Antigravity and verifies its workspace MCP connection in the background. Manifest editing and crawler runs are available immediately; queued content waits for a successful Agent bootstrap, while Shopify consumes only already-validated `content.json` tasks.

## Install

```powershell
python -m pip install -r scraper/requirements.txt
python -m playwright install chromium
Copy-Item scraper/.env.example scraper/.env
```

Add Shopify credentials to `scraper/.env`. Antigravity uses the existing local `agy` login; no Agent API token is stored here. The optional `ANTIGRAVITY_*` settings shown in `.env.example` override the executable and timeouts.

## Dashboard and workers

```powershell
python -m scraper serve --host 127.0.0.1 --port 5000
```

After the port is bound successfully, the server automatically opens `http://127.0.0.1:5000` in the default browser. The process runs the Dashboard, a single crawler, one long-lived Antigravity control conversation, isolated product content workers, and a single Shopify dispatcher. The crawler and Shopify dispatcher are driven by their durable queues rather than the Agent readiness gate, so Antigravity cold-start latency never blocks manifest work or new crawl runs.

To stop every Dashboard server registered by this workspace, run `stop-server.cmd` from the project root. The command validates registered process IDs before terminating their process trees.

For a headless Shopify dispatcher without the Dashboard:

```powershell
python -m scraper worker
```

## Antigravity runtime

The repository contains a workspace-local MCP definition and a restricted `wrydeco-content` Agent. `python -m scraper serve` launches a control `agy` process in stream-json mode, sends a minimal bootstrap prompt that calls `queue_status`, and keeps that process/conversation until the server stops. The control conversation only handles bootstrap, readiness, and health checks; it never receives product data. The API exposes `process_ready` after the CLI has supplied a valid conversation ID and MCP tool bridge, while `ready` becomes true only after the bootstrap result and marker are verified.

For every queued product, the server launches a separate Antigravity process/conversation restricted by `WRYDECO_EXPECTED_TASK_ID`. Retries for that product stay inside the same isolated conversation, and the process exits immediately after finalization or terminal failure. This prevents facts and copy from an earlier product leaking into later content. Finished content conversations are recorded as `pending_cleanup` in **Quản lý conversations**.

Before content is queued, the crawler downloads the verified Amazon gallery, decodes and re-encodes each image without embedded EXIF/IPTC/XMP metadata, and creates `evidence/gallery/contact-sheet.jpg`. The Agent must read the contact sheet, the first gallery image, and another image when available. MCP exposes only images under `evidence/gallery/`; A+ Content images and every other non-gallery image are hidden and rejected, while `aplus_text` remains available as factual text evidence. The Agent uses the source title and product type to identify the target object, then writes `visual_analysis.json` containing design/shape keywords only. Visual analysis cannot infer material, color, finish, dimensions, performance, or certification from pixels.

Content validation is fail-closed. Storefront copy must use the approved visual keywords, remain grounded in `source.json`, and pass persistent exact/near-duplicate comparison against prior finalized scraper content. A collision is returned without exposing the other product's full copy; after three unsuccessful revisions, the product moves to `needs_attention` and Shopify is not mutated.

If startup reports an authentication error, run `agy` once from this project directory, complete login, exit it, then use **Khởi động lại Agent**. A later process failure is fail-closed and is never restarted automatically.

Each successful server lifecycle creates a fresh Antigravity conversation. When a newer conversation becomes active, older scraper-owned conversations are marked `pending_cleanup`. Open **Quản lý conversations** in the Antigravity Runtime card, choose **Mở TUI để xóa**, then use `/resume` and `Ctrl+Delete` in Antigravity to confirm deletion of the displayed ID. After Antigravity has deleted it, click **Đã xóa trong Antigravity** to remove that session, its turns, and associated Agent events from the scraper database. The Dashboard never simulates deletion keystrokes and never edits Antigravity's `.gemini` storage.

## CLI

Create one crawl execution and return as soon as crawling is complete:

```powershell
python -m scraper run --manifest scraper/input/products.json --headless
```

This command only crawls/enqueues; it does not start Antigravity or run Shopify. Other commands:

```powershell
python -m scraper mcp
python -m scraper worker
python -m scraper status
```

## Runtime and recovery

`scraper/.runtime/orchestrator.sqlite3` is the orchestration source of truth. WAL mode, foreign keys, transactional claims, claim-token hashes, and leases prevent duplicate content work. Product artifacts remain inspectable under `scraper/runs/<run-id>/<ASIN>/`.

On restart, the system expires stale content leases, marks interrupted crawls for an explicit **Resume crawl**, restores interrupted apply work from `apply_progress.json`, reconciles gallery/visual artifacts, rebuilds missing content fingerprints, and enqueues valid orphaned `content.json` files. A Shopify failure is never retried automatically; use **Retry Shopify** after reviewing it.

The Event Log contains crawler, sanitized Antigravity/MCP lifecycle, and Shopify events from SQLite. Claim tokens, evidence payloads, prompts, credentials, and private reasoning are never exposed to the browser.

Pricing behavior remains fail-closed: `Decimal`, signed additional prices, complete combination/footer verification within `$0.01`, Wood Finish consistency checks, and the default 100-combination cap.
