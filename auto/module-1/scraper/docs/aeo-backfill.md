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

The Dashboard shows the five newest runs as expandable cards. **Xem toàn bộ lịch sử** opens a dialog
with ten summaries per page; **Xem thêm lịch sử** loads older runs without the previous twenty-run limit.
Opening a history card fetches its product details on demand. Selecting a product opens the padded AEO
review panel. Closing the dialog is supported through its close button, Escape, or the backdrop.
**Tải lại tiến trình AEO** shows a spinner while loading, disables duplicate clicks, and reports the
completion time or connection error. Refreshing and browsing history do not create jobs or retry products.

## Image reading and bounded recovery

`read_evidence` supplies native MCP image content. The AEO Agent must inspect those pixels directly;
`view_file` remains restricted to Antigravity's explicitly spooled `output.txt` results.
A denied file read records an `agent_file_read_denied` event with the sanitized `denied_path`,
tool state, session and assigned task. Other tool parameters and file contents are not logged.

For this specific violation, the worker revokes the old MCP claim, closes the failed conversation,
then starts a fresh one for the same product and phase. The replacement must claim and read all
required gallery evidence again. A review retry preserves the draft and still requires a complete
review. Retries share the phase's existing `ANTIGRAVITY_MAX_CONTENT_ATTEMPTS` budget (default 3).
After that limit, the product is marked as an error and older candidates are considered.
Other protocol violations are not automatically retried by this recovery path.

When starting with `run-server.cmd`, Python code changes require a server restart: after the current
job finishes, press Q or Ctrl+C in the server window and run `run-server.cmd` again. The command file and
launch procedure stay the same. Restarting does not rerun a historical completed job.
