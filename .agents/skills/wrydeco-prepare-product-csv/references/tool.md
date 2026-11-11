# Stable native CSV tool

Run commands from the WRYDECO Git root. The CLI is `python scripts/prepare-product-csv-tool/run.py`. See `--help` or `<command> --help`. Dependencies are in `scripts/prepare-product-csv-tool/requirements.txt`; install only if the local Python environment lacks them. Use a separate batch folder such as `temp/product-batch-20261111/`. The CLI is a repository tool, not an MCP server; Antigravity can invoke it through its terminal tool.

## Input manifest

Start with:

```powershell
python scripts/prepare-product-csv-tool/run.py init --out temp/product-batch-20261111/manifest.json
```

Edit the JSON with the file-edit tool. This is the AI-authored source record, not a CSV. Replace example values; create one `products[]` object per supplied product. Never write a new script that serializes CSV rows.

- `version=1`, `shop=wrydeco.myshopify.com`, `currency=USD`. A different currency requires a deliberate tool extension and an approved conversion rule, not rounding.
- Product: unique `id`, ASCII `handle`, exact taxonomy breadcrumb `category`, collection handle `collection`, `type`, array `tags`, existing `author_handle`, `interior_style`/`room_type` arrays, `evidence`, `content`, `variants`, `images`. `material` defaults to `wood`. Unsupported extra product keys are rejected; defer and disclose data the current manifest cannot represent.
- Preserve a user-approved artwork title with `approved_artwork_title` equal to `content.title`. An explicitly approved handle outside the generated length target needs `approved_handle` equal to `handle`. These are recorded exceptions; keep commercial `seo_product_title` fully validated.
- `variants[]`: ordered `options=[{"name":"Width","value":"10 in"},{"name":"Height","value":"30 in"}]`, `price="2083"`, `source_ref="SP01-price.png, row 1"`. Use exact final prices as strings and exact original option values; never expand missing combinations. At most three axes and 99 variants per product are supported by the two-digit SKU policy. Stop for a larger matrix rather than truncating it. A zero price requires `zero_price_confirmed=true`.
- Leave `sku` absent to let the Module 1 SKU planner generate it. If supplied, provide every variant SKU; the tool verifies the plan and collisions with the batch/store snapshot. Amazon provenance needs a verified `asin` and confirmed Amazon routing tags. Do not add a false source tag to obtain a prefix.
- Optional `image_index` is a **1-based** gallery index supported by variant evidence. Do not assign it based only on row order. Optional `fields` accepts supported exact variant header names and string values, for example `{"Variant Compare At Price":"2200.00"}`. The default empty inventory tracker is intentional; the current WRYDECO profile rejects tracked inventory. Keep unverified weights and packing dimensions out of overrides.
- `images[]`: ordered objects with accessible local `path` and English `alt`. Relative paths resolve from the manifest's directory. A pre-existing real public `url` may be supplied; otherwise stage fills the checkpoint, not the manifest. Deduplicate identical local image bytes before checking. Every image must decode as PNG/JPEG/WEBP/GIF, at most 20 MiB and 25 megapixels.
- `evidence.source`: factual source `title`, array `bullets`, optional `aplus_text`, all grounded in supplied records. Put complete approved measurement tuples in individual bullets if AEO will cite combined axes. No generated copy or visual assumptions may be laundered into these text facts.
- `evidence.visual`: `target_identity`, inspected gallery `evidence_ids` using exactly the manifest's image `path` strings, and 2–6 observed phrases each in `design_keywords` and `shape_keywords`. Images support shape/visible structure only. The tool supplies digest/product identifiers.
- `content`: `title`, `description_html`, `seo_product_title`, `seo_title`, `seo_description`, `handle` and structured `aeo`. Never author `aeo_html` directly; the tool derives it. Read all three original Module 1 prompts as required in [csv-contract.md](csv-contract.md#seo-and-aeo).

## Live read snapshot and AEO context

After all local input gates pass and proposed categories are identified:

```powershell
python scripts/prepare-product-csv-tool/run.py snapshot --manifest temp/product-batch-20261111/manifest.json --out temp/product-batch-20261111/store.json
python scripts/prepare-product-csv-tool/run.py context --manifest temp/product-batch-20261111/manifest.json --out temp/product-batch-20261111/aeo-context.json
```

`snapshot` is read-only on Shopify. It reads current choices, metaobject author handles/GIDs, smart rules, taxonomy categories, handles and SKUs. Resolve any mismatch rather than editing the snapshot to bypass it. Snapshots expire after 24 hours. If the category is absent, identify the actual sold item and correct its taxonomy; do not force a superficially similar category.

`context` issues actual AEO fact IDs. Use only those IDs in `content.aeo`. Finish its plain-text Overview, `summary` array (possibly empty) and 3–8 FAQs. The tool validates/escapes the final HTML. Neither command establishes that the AI correctly read the screenshots: inspect the pixels and source mapping yourself.

## Check, stage, build, verify

```powershell
python scripts/prepare-product-csv-tool/run.py check --manifest temp/product-batch-20261111/manifest.json --snapshot temp/product-batch-20261111/store.json --checkpoint temp/product-batch-20261111/images.json --report temp/product-batch-20261111/check.json
python scripts/prepare-product-csv-tool/run.py stage --manifest temp/product-batch-20261111/manifest.json --snapshot temp/product-batch-20261111/store.json --checkpoint temp/product-batch-20261111/images.json --upload-files --report temp/product-batch-20261111/stage.json
python scripts/prepare-product-csv-tool/run.py build --manifest temp/product-batch-20261111/manifest.json --snapshot temp/product-batch-20261111/store.json --checkpoint temp/product-batch-20261111/images.json --out temp/product-batch-20261111/products.csv --report temp/product-batch-20261111/build.json
python scripts/prepare-product-csv-tool/run.py verify --manifest temp/product-batch-20261111/manifest.json --snapshot temp/product-batch-20261111/store.json --checkpoint temp/product-batch-20261111/images.json --csv temp/product-batch-20261111/products.csv --report temp/product-batch-20261111/verify.json
```

Run these sequentially and inspect each report. Exit code 1 is a failure. A batch fails as a whole; correct every product issue before staging. Content collisions are reported separately from field errors. No `build --offline` option exists. `build` refuses to overwrite an existing final file; choose a new filename for revisions. It accepts the final path only after checking the actual serialized candidate. Keep the manifest, snapshot and checkpoint alongside the CSV for exact reconstruction.

When previous validated handoff reports are available, add `--prior-report path/to/earlier-verify.json` to `check`, `stage`, `build` and `verify`; repeat for multiple reports. The tool compares their saved fingerprints as well as the Module 1 read-only index and current batch. Missing history is disclosed as incomplete coverage rather than a uniqueness guarantee.

`check` validates content, SKU planning and native field structure before uploads; it never declares readiness. `stage` is the only command with Shopify Files writes and requires `--upload-files`. It never creates or publishes a product. For an external public gallery URL already supplied in the manifest, staging can be skipped; build still downloads and decodes that URL. A new Files upload resumes from its saved ID or uncertain-create reconciliation, never from a guessed URL.

`build`/`verify` read the saved CSV with a strict CSV reader, require all 71 headers and their order, check product-only vs variant vs image-only cells, required defaults, lowercase booleans, exact LF-separated choices, categories/authors, unique valid SKUs, complete option tuples, prices, gallery positions and variant image membership. They compare every serialized cell against the manifest-derived plan. Every unique gallery URL must return public HTTP 200 with image MIME and decodable image bytes. A failed download blocks readiness and prevents final CSV acceptance.

The native profile supplies all required defaults described in [csv-contract.md](csv-contract.md#product-classification-and-defaults), including `Status=active` only on each product's first row. `Published=false` is a separate default. Optional unsupported columns remain present and empty. A `0.0` default weight means no verified shipping weight was supplied; do not describe it as a measured value.

For a read-only audit of an old CSV:

```powershell
python scripts/prepare-product-csv-tool/run.py verify --csv D:/D-Downloads/shopify-download/wrydeco_wood_floor_lamp_bases_20261111.csv --offline --report temp/product-batch-20261111/old-file-audit.json
```

This is useful for diagnostics but cannot claim readiness: without a manifest it cannot prove the source prices/options, and `--offline` omits network verification. Do not repair the old CSV by filling in plausible URLs or inferred source data.

## Validation scope and handoff

Require the final independent report to contain `valid=true`, `manifest_compared=true`, `ready_for_import=true`, and no errors/collisions. Report product/variant/gallery counts, chosen category/collection/author, defaults, exceptions, deferred facts and historical coverage. The tool reads the existing Module 1 fingerprint index in read-only mode and compares the current batch; it never claims this index covers the entire Shopify catalog. Preserve reports for the subsequent manual import review.

An import-ready result means the tool's documented checks passed at that time. It does not mean a Shopify import was performed, that its server-side validation has been exercised, or that images cannot be removed later. Keep Files available through import. The user performs the final manual Shopify Admin import in this workflow.

For changes to the reusable tool, run its local regression suite:

```powershell
python -m pytest scripts/prepare-product-csv-tool/tests/test_tool.py -q -p no:cacheprovider
```

The suite uses generated local images and mocked network responses, including successful multi-product exports, broken schema/defaults/lists, missing images, HTTP 404/HTML/corrupt responses, checkpoint recovery and mutation prevention. It does not upload test photos or import test products into the store.
