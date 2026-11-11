# WRYDECO CSV contract

## Headers and row layout

Use `temp/template_products_shopify_export.csv`: exactly **71 headers**, names and order unchanged. The CLI pins the approved header sequence in `scripts/prepare-product-csv-tool/native_contract.json` and rejects template drift. If the template is missing or changes, resolve it before building; do not fall back to an older 70-column export or a generic Shopify sample. Template product rows supply formatting examples only, never new-product facts.

- Keep each product's rows contiguous under one distinct ASCII kebab-case `Handle`. Write product metadata and option names on the first row. Use one variant row per approved tuple with the exact option values, final `Variant Price` and `Variant SKU`. Preserve axis order and measurements as provided. Put the first image on the first product row when available.
- Assign ordered gallery images to existing rows, then add image-only rows containing `Handle`, `Image Src`, `Image Position` and `Image Alt Text`. Keep variant cells empty on image-only rows. Use one row per unique image and number positions from 1. Write specific English alt text based on the sold item and the view. Fill `Variant Image` only for a verified variant-to-photo assignment and use the exact URL present in the gallery.
- Use the approved ledger from [intake.md](intake.md) for option names, option values and prices. Use the project `scraper.sku.build_sku_plan` and `sku_rules.json` for missing SKUs. Pass option pairs, the final handle, approved tags and any verified ASIN. Use the WRY route for products without Amazon provenance. Pass SKUs already reserved in the batch as occupied and compare case-insensitively. Apply the repo's 18–40 character rule. The current proxy parser requires a two-digit terminal index. Flag a plan incompatible with that parser before upload.
- Let the CLI write UTF-8 CSV with LF endings and CSV quoting. Embedded LF characters inside list cells are intentional and do not represent extra CSV records. Never pre-escape them as literal `\\n`, write a JSON list into the CSV cell, or edit the resulting CSV by hand.

## Product classification and defaults

Identify the product shown consistently across the gallery before generating content. Use the target collection and variant evidence to disambiguate it from props. Review the clearest image and another relevant angle when available. Record the image(s) and the observed part used for the decision. Assess branches that are part of the sold product, including branches incorporated into its structure.

| Visual finding | `Interior Style` output |
| --- | --- |
| At least one visibly pointed branch **or** multiple visible branches | `["Rustic"]` |
| Sufficient views show neither a pointed branch nor multiple branches | `["Japandi","Mid-Century","Organic Modern"]` |
| Subject or relevant structure remains obscured or ambiguous | Reject gallery intake and request a clearer view or identification |

A single rounded branch can follow the second rule when the rest of the item is visible. Decorative stems, props, and branches of other objects never count. This is WRYDECO's assignment policy for this workflow. The three-label assignment supplies catalog metadata. Claims in the SEO or AEO copy still need separate supporting evidence.

Propose `Room Type (product.metafields.custom.room_type)` from the product's supported function and the target collection, using the Module 3 whitelist: Living Room, Bedroom, Kitchen & Dining, Home Office & Library, Nursery & Kids' Room, Entryway & Hallway, Bathroom. Use only defensible choices and the exact current store choices in the tool snapshot. If suitability remains unknown, flag it for review. Supply JSON arrays **in the JSON manifest only**. For native CSV the tool joins `Interior Style` and `Room Type` values with actual LF characters, matching the supplied store export. GraphQL/proxy imports use a different representation; do not run that serializer on this output.

- Default `Vendor=Wrydeco`, `Status=active`, `Published=false`, `Gift Card=false`, `Wood Type=wood` and `Product Material=wood` as approved batch conventions. Write these product-level values only on the first product row. Product status and the Published flag are separate: the active-status default does not change the publication flag. They do not establish a wood species, material grade or construction method for copy.
- Set nonempty `Type` and `Tags` from the resolved collection rules and confirmed catalog conventions. `Product Category` is required in this workflow: choose a defensible exact breadcrumb, verified by the tool's live taxonomy lookup. Do not use `Uncategorized`, fabricate a category or classify a component as a complete lamp without evidence.
- Fill `Author Info (product.metafields.custom.author_info)` with the selected existing `product_author` **handle**, matching the native template. Keep its GID in the store snapshot as provenance. Follow [author selection](shopify.md#resolve-product-authors). Treat assignment as catalog metadata; maker claims in copy need confirmed evidence.
- Leave `Bought Amount` blank without real data. Leave `Amazon Link` and A+ `Rich Description` blank unless the input includes those sources. A local gallery belongs in the image columns.
- For **every variant row**, the tool supplies `Variant Fulfillment Service=manual`, `Variant Inventory Policy=deny`, `Variant Weight Unit=kg`, `Variant Grams=0.0`, `Variant Requires Shipping=true`, `Variant Taxable=true`, `Variant Inventory Tracker=""`, `Variant Inventory Qty=0`. These are WRYDECO import conventions, not claims that Shopify universally rejects other valid spellings or that the real product weighs zero. Do not invent tracked inventory or a stock quantity such as 50. Use the tool's supported `variants[].fields` overrides only for confirmed values; unsupported overrides fail validation.
- Leave compare-at price, cost, barcodes, packing dimensions, unsupported media, app fields and merchandising fields blank without support. The exact barcode header is `Variant Barcodes` in this template. Image-only rows contain only Handle and image fields, with all variant defaults blank. Report any source data the current manifest cannot represent rather than silently discarding it.

## SEO and AEO

Read the actual repo prompts at `auto/module-1/scraper/AGENT_PROMPT.md`, `auto/module-1/scraper/CONTENT_TASK_PROMPT.md` and `auto/module-1/scraper/aeo/PROMPT.md`. Use their editorial and evidence rules. Replace the scraper's Amazon/MCP task lifecycle with the approved local ledger and photo evidence. Write natural English in WRYDECO's gallery tone.

| Header | Contract for generated content |
| --- | --- |
| `Title` | Approved work title when supplied. Otherwise factual product title, 50–70 characters. |
| `Handle` | Stable, unique ASCII kebab-case URL identifier, 50–60 characters for generated handles. |
| `Body (HTML)` | Safe semantic HTML in the `wrydeco-product-description` wrapper with supported product differentiators. |
| `SEO product title (product.metafields.custom.seo_product_title)` | Commercial title of 50–70 characters, without brand or pipe. |
| `SEO Title` | 50–60 characters including the exact suffix ` \| Wrydeco`. |
| `SEO Description` | 150–160 characters, starting with `Explore` or `Shop the`, ending with a period. |
| `Product AEO HTML (product.metafields.custom.aeo_html)` | Validated, escaped HTML rendered from the structured draft. |

### Evidence and SEO validation

Reuse the pure functions in `auto/module-1/scraper/content.py`; do not launch a scraper task or change its validators. Put `auto/module-1` on the Python import path when calling them locally.

1. Keep a per-product evidence record with source locations: supplied factual title/text, confirmed facts, exact variant tuples and units, and inspected gallery paths. If no source title exists, use the neutral product identity established during intake. Never put generated marketing copy into the evidence used to validate itself. Metadata defaults, random author assignment and collection rules do not establish material, maker attribution, construction or performance claims.
2. Build `text_source` with `title`, `bullets` and optional `aplus_text` from that record. Include approved option facts and each complete dimension tuple as separate bullets, preserving the source axes, units and variant association. Do not claim unavailable combinations. Keep visual observations separate from factual text.
3. Build the local visual record using `target_identity`, gallery `evidence_ids`, and 2–6 distinct phrases each in `design_keywords` and `shape_keywords`. Use `validate_visual_analysis` with a stable local product key as `expected_task_id`, the actual `source_digest(text_source)`, and the set of inspected gallery paths as `allowed_evidence_ids`. Preserve the Module 1 restrictions on visual inference; the local identifiers replace MCP identifiers only.
4. Call `validate_content` and `validate_content_grounding` on the content draft. For grounding, use a copy of `text_source` whose bullets also include the validated design/shape phrases, so supported visual words are not rejected solely because there is no Amazon title. Track those added bullets as visual-origin facts. Never add material, finish or performance guesses. Review every claim against the ledger as well: the lexical validator is not a complete semantic fact checker.
5. Call `validate_visual_keyword_usage` with the validated visual record. Keep at least two distinctive supported facts in each generated product-title field, one approved visual phrase in a title field, two in the description and one in an SEO field, following the original prompts. Correct errors before image staging.

### Preserve artwork titles and approved handles

The actual CSV `Title` preserves a supplied, approved artwork name, including a short name such as `The Golden Bough`. Keep the commercial identity in `seo_product_title`; do not pad or replace the artwork name to satisfy Module 1's factual-title length rule. An artwork name may also intentionally omit factual or visual keywords. Check the actual name separately for nonempty plain English text, faithful preservation and unsupported factual claims; do not require marketing keywords in it.

For that case, validate a **separate copy** of the draft with `title` set to the final `seo_product_title`, and run the SEO/grounding/visual checks above on that copy. The commercial title must satisfy the normal length, identity and evidence rules. If an explicitly approved handle falls outside the generated 50–60 character target, verify the actual handle against `[a-z0-9]+(?:-[a-z0-9]+)*`, preserve it, and use a compliant generated handle only in the validation copy. An invalid handle remains a blocker. Never serialize the validation copy or claim the original artwork title/handle passed the unmodified length validator. Record the actual values, the checked commercial title and each exception in the validation report. Compare duplicates using the **actual final CSV values**.

### AEO compilation and validation

Build the AEO evidence context with `scraper.aeo.build_input`, passing the identified product type, supported source text, exact option tuples and visible design/shape facts. When citing combined measurements, record the entire verified tuple as one fact with its axes and units. Draft an 80–140 word Overview, optional supported summary and 3–8 distinct FAQs, with each answer 30–80 words and directly answering its question first. Cite actual evidence IDs. Use `validate_and_render(context, draft)["html"]` for the cell and review the text against the evidence. An option label may support an offered dimension or finish. Photos support shape and visible structure. Exclude unsupported dimensions, species, materials, accessories, capacity, care, safety, warranty and shipping promises. If fewer than three useful FAQ intents are supportable, report the missing facts before staging any images.

Pass the original `text_source`, **not** the visual-augmented SEO grounding copy, to `build_input`. Pass the validated visual record through its `visual` argument so those facts retain `approved_visual` provenance. Pricing must use `{"variants": [{"options": [{"name": "...", "value": "..."}]}]}` for the approved rows. `build_input` deduplicates individual option values and does not preserve tuple associations by itself. For a combined measurement claim, cite the `source:bullet:<index>` issued for the corresponding complete verified tuple in `text_source.bullets`; do not invent IDs or merge measurements from different rows. The `summary` key is required by the draft schema even when its value is `[]`. Save the structured draft, evidence context and validator result alongside the rendered HTML.

### Current-batch and historical similarity

Use `content_fingerprints` and `content_similarity` on final output values, including the preserved artwork title and handle. Read the current thresholds from `OrchestratorStore._content_collisions` in `auto/module-1/scraper/store.py`; currently they are `title=0.88`, `seo_product_title=0.88`, `seo_title=0.88`, `seo_description=0.85`, `description_html=0.82`, `handle=1.0` and `aeo_html=0.97`. Compare normalized text and exact hashes as Module 1 does. For AEO, compare the normalized Overview plus FAQ answers from `content_fingerprints`, not the HTML wrapper or repeated FAQ questions alone.

- The tool compares every product pair in the batch and active fingerprints in `auto/module-1/scraper/.runtime/orchestrator.sqlite3`, opened in SQLite `mode=ro`. Supply accessible earlier validated batch reports with repeatable `--prior-report` arguments. Collision reports retain source product IDs. The tool never instantiates `OrchestratorStore`, runs migrations or writes CSV products into its queue/fingerprint tables.
- Treat collisions as unresolved content issues before staging. Revise generated copy using the actual evidence and recheck; preserve approved artwork titles and handles, and report conflicts requiring the user's decision. Do not fabricate differences to force distinct copy.
- Report which historical sources were checked and how many records they cover. An absent, empty, unreadable or incomplete index provides no evidence of catalog-wide uniqueness. If historical coverage is unavailable, still run current-batch checks and explicitly mark historical comparison as incomplete; a claim of full-catalog uniqueness is not permitted. If the user requires complete historical coverage, resolve that requirement before staging.
- Save the source/visual records, actual content draft, any validation copy and exceptions, normalized fingerprints and comparison report with the batch handoff so subsequent batches can reuse them. Keep factual grounding, visual checks, AEO validation, current-batch similarity and historical coverage as separate results.

## Final verification and handoff

- Round-trip with a CSV reader. Verify exact header order and row widths, one product header row per distinct handle, all source tuple-to-price mappings, case-insensitively unique SKUs, contiguous gallery positions, valid image URLs, and correct variant image references. Compare HTML after decoding the CSV. Review the destination collection assignments and ensure they still correspond to the serialized Type, Tags and prices.
- Run the CLI's separate `verify` command with the manifest, store snapshot and checkpoint against the final saved CSV. Require `valid=true`, `manifest_compared=true`, successful public-image downloads and `ready_for_import=true`. `verify --offline` or verification without a manifest can audit an old file but cannot establish readiness. The `check` command intentionally never claims readiness.
- For handoff include CSV, manifest, image checkpoint, validation reports, counts, category/collection/author assignments, historical coverage and any exceptions or deferred source data. Keep original Shopify Files available until manual import has completed. Manual Shopify Admin import and its subsequent verification belong to the user unless separately requested. A future proxy import needs its own explicit conversion and validation; this skill no longer treats the proxy parser as the native CSV correctness oracle.

