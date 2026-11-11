# Shopify collection and file procedures

## Resolve credentials and store identity

1. Find the WRYDECO Git root and read `admin/access-token.md`. Use the existing tool's `snapshot` command rather than writing a new Admin client. It loads `admin/.env`, falls back to `.env.shopify`, and honors environment overrides. Expected keys are `SHOPIFY_SHOP`, `SHOPIFY_API_VERSION`, `SHOPIFY_ADMIN_TOKEN` and, for renewal, `SHOPIFY_CLIENT_ID` and `SHOPIFY_CLIENT_SECRET`.
2. Normalize the store and require `wrydeco.myshopify.com` before transmitting any credential. Use the configured GraphQL API version. Read `shop { myshopifyDomain currencyCode }` and confirm the response identifies the target shop. Collection reads require product read access. The gallery flow requires access to create Files and read them back.
3. Credentials stay inside the tool's request process without being printed. The repo token CLI prints the token on success, so do not use it to prepare chat evidence. The tool renews once in memory on HTTP 401. Never include credential values, auth headers or signing parameters in ledgers, CSVs or chat. The public image verifier and upload target receive no Admin token.
4. Stop on a persistent auth or scope error and report the affected phase. Snapshot data expires after 24 hours; refresh it before resuming an older batch. This skill produces a native Admin CSV; a separately authorized proxy import needs an explicit format conversion and its own proxy workflow.

## Read and resolve smart collections

Paginate Admin GraphQL `collections(first: 100, after: $after)` until `hasNextPage` is false. Fetch `id`, `handle`, `title` and `ruleSet { appliedDisjunctively rules { column relation condition } }` plus `pageInfo { hasNextPage endCursor }`. Treat GraphQL errors or a missing or repeated pagination cursor as an incomplete catalog. Reuse the successfully read catalog within the current batch and match the exact target handle. Read the collection again when resuming a batch whose rule snapshot may have changed. [Shopify collection query and rule sets](https://shopify.dev/docs/api/admin-graphql/latest/queries/collections)

| Live rule | CSV handling |
| --- | --- |
| `TYPE EQUALS` | Set `Type` to the exact rule condition if it fits the identified product. The collection handle, display title, and Product Type can differ. |
| `TAG EQUALS` | Add the exact condition to `Tags` when the requested collection and product evidence support that assignment. Retain other confirmed required tags. |
| Variant price rule | Evaluate the comparator against the approved variant prices using Decimal and Shopify's documented rule semantics. Stop if the result is unclear. |
| Multiple rules | Apply the real all/any logic. When `appliedDisjunctively` is false, every rule must pass. When true, at least one must pass. Pick a supported assignment and record which rule it satisfies. Resolve competing Type values before writing. |
| Manual collection, unknown rule semantics, or unsupported condition | Reject the collection gate and explain the exact blocker. Collection creation, rule edits, and manual membership are separate operations. |

Observed examples include `coffee-tables` with `TYPE EQUALS coffee-tables`, `tree-bookshelves` with `TAG EQUALS tree-bookshelves`, and `all` with `VARIANT_PRICE GREATER_THAN -1`. These are illustrative. Use the live rules for every batch.

Keep collection handles and rule assignments in the handoff. The tool writes standard `Type` and `Tags` columns and rejects an unsupported smart-rule comparator rather than guessing. Preserve the exact 71-column template without adding a `Collection` column. Shopify calculates smart membership after import; verify actual membership then. [Shopify's CSV collection behavior](https://help.shopify.com/en/manual/products/import-export/using-csv#collection-column-exception)

## Resolve product authors

- Read the live `product_author` metaobjects from the verified store using the same Admin client. Paginate to completion and reuse the list within the batch. Use the author name, handle and GID to resolve assignments. Deduplicate the list by GID before choosing.
- If the user specifies an author for the product, use the unique matching Shopify entry by GID, handle, or name. Honor an explicitly specified author for the whole batch unless the product has its own assignment. If the requested author is missing or matches more than one entry, report the mismatch and stop before staging. A random choice requires the author to be unspecified.
- When no author is specified, choose one uniformly at random for that product from the live list, for example with Python `secrets.choice`. Make the choice once and record its name and GID in the working product record so retries preserve it. If the lookup fails or the list is empty, stop before staging.
- Set `author_handle` in the manifest to the selected existing handle; the tool writes it to the first CSV row, matching the native store export. Keep name/GID in the snapshot and handoff, and indicate whether the choice came from the user or the random default. Do not substitute the proxy importer's GID convention in the native CSV.

## Stage local gallery images

Start file writes only after every product passes intake, rule mapping, identity/classification, draft content validation, SKU and variant-price reconciliation. Upload only the approved files from the supplied galleries to Shopify Files. This phase prepares URL references for the CSV.

1. Run the existing tool's `stage --upload-files` with manifest, snapshot and checkpoint as described in [tool usage](tool.md). It validates the whole batch before starting writes, hashes and decodes the approved images, creates deterministic filenames and stores no signing parameters.
2. The tool uses `stagedUploadsCreate`, uploads bytes, then `fileCreate` with `duplicateResolutionMode=RAISE_ERROR`. It checkpoints intent before creation and the returned file ID before waiting for `READY`. Never construct a CDN URL from a filename.
3. Re-run the same stage command after interruption. A known file ID is polled again. An uncertain create outcome is reconciled against the deterministic filename; zero or multiple matches stop the operation. Do not delete checkpoint entries to force blind retries. No Files overwrite/delete or product mutation is implemented.
4. The tool verifies public HTTP 200, image Content-Type and actual image decoding without Admin credentials. `build` and the final `verify` repeat that verification; a URL in a checkpoint is not sufficient proof that it still exists.
5. On a permanent error preserve checkpoint/report and identify pending images. Keep Shopify Files available until the user completes manual import. Shopify may create a product copy while retaining the original Files image. [Staged uploads](https://shopify.dev/docs/api/admin-graphql/latest/mutations/stagedUploadsCreate) · [Shopify Files](https://shopify.dev/docs/api/admin-graphql/latest/mutations/fileCreate) · [CSV image behavior](https://help.shopify.com/en/manual/products/import-export/using-csv#prepare-your-images)

