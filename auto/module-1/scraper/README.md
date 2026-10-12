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

## Product AEO

New Dashboard and CLI batches generate AEO in the same isolated product conversation as SEO.
Existing-ASIN preflight still skips products already on Shopify; earlier unversioned runs keep their original contract.
The module in `aeo/` compiles source text, price-verified options and approved visual shape/design facts into
an evidence-ID input. Antigravity writes an English Overview (80–140 words), supported summary attributes and
3–8 FAQs (30–80 words per answer). No search API is required or available in the content conversation.

Validation checks the draft contract, evidence IDs, restricted claims, numbers, dimension axes/units and duplicates.
Python renders escaped HTML and the Shopify adapter writes only `custom.aeo_html` (`multi_line_text_field`, Product).
Empty-only compare-and-set writes and independent read-back preserve existing content, including concurrent edits.
Failed content validation blocks only that product; existing Agent retry limits and needs_attention handling apply.
These mechanical checks do not prove every semantic claim: the authoring prompt requires factual grounding.

The Dashboard's **Product Overview & FAQ · AEO** editor accepts structured JSON, shows the available evidence,
and previews escaped HTML in a sandbox. Claim/finalization locks apply to AEO as they do to SEO.
The AEO prompt is editable in **Chỉnh Prompt** and is snapshotted with its schema in `aeo-contract.json` for each new run.
Inspect `aeo_input.json`, `aeo_validation.json`, `aeo.html` and `aeo_shopify.json` in the product workspace.
Storefront/theme rendering is separate. See `docs/aeo-plan.md` for requirements and module input/output.

## Variant SKUs

Every batch now plans SKUs after building the final variant combinations. Tags containing
`amazon` select `amz`; other tags select `wry`, even when the source URL is Amazon.
Colors/finishes are always abbreviated, marketing phrases are removed from SKU components,
and collisions are regenerated using the next available suffix. Rules and source aliases
are editable in `sku_rules.json`; see `docs/product-sku-rules.md` for the full contract.

The apply worker writes SKUs with `productSet`, reads every live variant back, and marks
`sku_verified` only after matching the saved plan and checking other SKU owners. Resume
can repair SKU-less old checkpoints by variant ID without replaying `productSet`.
Dry runs read Shopify to produce an inspectable `sku_plan.json` without mutations.

SKU assignment runs automatically in the batch. The separate Preview SKU/Set SKU
buttons, their API endpoints, and their results panel have been removed. Batch SKU
plans, verification events, and retry checkpoints remain available in run artifacts.
Floating **VIEW LINKS** instantly scrolls to the product list; **VIEW PROGRESS**
instantly scrolls to the progress section. Both leave space below the sticky header.
An additional **Chạy batch** button stays fixed at the upper right below the header.
It uses the same batch action as the original button; both disable while submitting
the request to prevent duplicate submissions.

Crawled option values now share the SKU marketing filter. Original selections are
all price-verified before cleanup; their source labels and DOM/ASIN identities stay
in evidence. Cleaned values are used for Shopify options, including cached pricing.
Equivalent combinations merge only at equal verified prices; conflicting prices or
empty labels stop the product. Resuming an already-applied product preserves its
saved option labels when verifying or repairing SKUs.
