# AEO for existing Shopify products

The Dashboard's **Bổ sung AEO cho sản phẩm trong store** accepts an integer from 1 to 1000.
The target counts verified successful writes, not scanned products or attempts.
Products are scanned by creation time descending, with cursor pagination and a fixed creation-time cutoff.
Absent, empty and whitespace-only `custom.aeo_html` values qualify. Existing nonempty content is preserved.

This flow uses the existing AEO compiler, prompt, schema, validation, renderer and empty-only Shopify adapter.
Shopify descriptions and live variant selections supply textual facts; sanitized product gallery images supply
only design/shape evidence. An ASIN or Amazon URL is not required. Source checklists and requests to confirm
unknown specifications are not evidence that those specifications are true.

An isolated `wrydeco-aeo` Antigravity conversation writes only AEO and then performs a separate complete
review turn. Both turns must validate and finalize. The worker rechecks product evidence before writing,
ensures the metafield definition, writes using compare-and-set, and independently reads the value back.
The only product mutation is `custom.aeo_html`; the ordinary batch's productSet/media/SKU/publication flow is not invoked.

Jobs and tasks persist in `aeo_backfill_runs` / `aeo_backfill_tasks` in the existing SQLite database.
Evidence, drafts, validation, HTML, initial Shopify snapshots and write intents live under
`scraper/.runtime/aeo-backfill/<job-id>/<task-id>/`.
Pause stops further writes after the current network operation; Resume continues from saved state.
Server interruption requires explicit Resume. A write with an unknown outcome stops the job until reconciliation,
preventing an uncounted successful mutation from exceeding the requested number.
Connection failures also stop at the current product. For an earlier content failure, pause the job and use
**Thử lại AEO sản phẩm này** to retry that product before continuing the catalog cursor.

Existing AEO and invalid/insufficient content do not count toward the target; older products are considered next.
If the catalog is exhausted, the Dashboard reports the exact shortfall. Shopify API failures stop the job.
One unfinished backfill job is allowed per workspace. Product ownership is checked against ordinary batches,
and isolated authoring shares a process-local runtime lock with the ordinary batch content worker.

The task details view shows the complete escaped AEO preview, structured draft and cited evidence for review.
Mechanical validation does not prove every semantic claim; the full author review and final product-level review
remain important. The feature does not promise placement or ranking in an AI search service.
