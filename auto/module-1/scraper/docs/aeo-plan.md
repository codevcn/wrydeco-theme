# AEO: requirements and implementation plan

## Decisions confirmed with the user

- New scraped products in new batches only. Existing-ASIN preflight remains unchanged; no backfill.
- One Product metafield: `custom.aeo_html`, type `multi_line_text_field`.
- English Overview (80–140 words), a summary of supported attributes, and 3–8 FAQs (30–80 words per answer).
- Same isolated Antigravity conversation writes SEO and AEO; no search API, browser, extra Agent or new claim.
- Preserve nonempty existing AEO. An empty metafield may be populated; a retry may verify its own identical HTML.
- Invalid AEO blocks that product's content finalization; existing attempt limits and needs_attention apply. Other products continue.
- Dashboard supports viewing/editing the structured AEO draft and a safe HTML preview. Theme rendering is a separate future task.

## Module boundaries

`scraper/aeo/` owns the contract, input compiler, validation, deterministic HTML rendering and writing policy.
Its core accepts plain dictionaries and has no filesystem, Shopify, AGY or browser side effects.

- Input: version, product identity, source facts with IDs, price-verified option values, approved design/shape keywords.
- Draft: overview `{text, evidence_ids}`, summary `[{label, value, evidence_ids}]`, FAQs `[{question, answer, evidence_ids}]`.
- Output: normalized draft, HTML, input digest and validation counts. Evidence IDs are never rendered for customers.
- Adapter: receives a Shopify client and the validated HTML, checks field type, uses compare-and-set for empty-only writes and independently reads back the result.

The Agent cannot nominate external evidence or use competitor specifications. Citations must refer to compiler-issued IDs.
Lexical/numeric grounding is a conservative guard, not proof of every semantic assertion; the prompt and optional manual review remain necessary.

## Integration sequence

1. Snapshot AEO contract/prompt when a new AEO-enabled run is created. Runs without the version field keep their old six-field contract.
2. Expose AEO input/schema/prompt through MCP content context. Require another context read after writing visual analysis.
3. Save structured AEO beside the six SEO fields in `content.temp.json` / `content.json`. Preserve it through manual editing, recovery and retry.
4. Validate evidence IDs, lengths, unique questions, restricted claims, units/numbers and summary fields. Render HTML only in Python.
5. Extend content fingerprints using overview/answers, excluding shared question headings and evidence IDs.
6. Validate before Shopify writes. Save `aeo_input.json`, `aeo_validation.json` and `aeo.html` as run evidence.
7. Write/verify AEO before marking apply complete; persist `aeo_verified` and the preserved/written status. No productSet replay on retry.
8. Add AEO draft editing/preview and a dedicated prompt editor to Dashboard. Keep both existing Chạy batch buttons on the same handler.

## Prompt adaptation

Use the user's evidence → entity → buying intent → overview → FAQ process. Factual accuracy takes precedence.
Only gallery pixels and approved design/shape keywords may support visual observations. Color, finish, material and dimensions require supplied text/verified options.
Remove optional web search, hard five-FAQ minimum, markdown-only output and instructions that replace the MCP task lifecycle.
Keep answer-first prose, distinct useful questions, independent readability, supported-only summary attributes and avoidance of advertising filler.
Shipping/warranty/care claims require trusted store evidence; this version does not supply store policies, so omit those topics.

## Verification loop and acceptance criteria

- Core tests: valid draft; empty/unknown citations; factual/numeric mismatch; dimensions not in cited options; unsupported materials/performance; duplicate questions; length/count failures; HTML injection.
- Integration tests: AEO survives write/validate/finalize/manual edit; disabled/old runs retain prior behavior; retry does not regenerate or replay productSet; preserved AEO and compare-and-set races do not overwrite user data.
- Shopify adapter tests: empty creation, same-value retry, nonempty preservation, type mismatch, failed mutation and independent read-back failure.
- Dashboard verification through Chrome: structured fields, draft round-trip, escaped preview and prompt editing. Use local fixtures for AEO-enabled data; do not backfill the four existing store test products.
- Regression suite: existing SEO, queue, SKU, pricing, server and Shopify checks.
- Completion requires supported HTML in the intended metafield or a recorded preserve-existing decision, with no silent omission of required AEO.

## Verification completed — 2026-10-12

- All 165 scraper tests passed, including legacy SEO/queue/SKU regressions and the new AEO core, queue and Shopify adapter checks.
- Chrome verified draft editing/saving, escaped HTML preview, finalization/read-only locking and the third prompt editor in an isolated Dashboard with workers disabled.
- A real Antigravity conversation used cached source/pricing/gallery evidence from B0HB4TTLJY in a separate dry-run workspace. SEO + AEO finalized with six FAQs.
- Human review of the first generated draft found unsupported weighted-base and tier-count claims. The prompt and restricted-claim validation were strengthened; AGY corrected and re-finalized the draft successfully.
- No live Shopify mutations or definition creation were performed during AEO verification. Empty-only writes, preservation, concurrent edits and read-back were tested through mocked GraphQL/client adapters. Existing store products remain outside the new-batch scope.
- Local verification evidence is under `.runtime/verification/aeo-check/` and `.runtime/verification/aeo-dashboard.png` (ignored runtime artifacts).
