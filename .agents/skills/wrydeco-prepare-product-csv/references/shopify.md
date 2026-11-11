# Shopify collection and file procedures

## Resolve credentials and store identity

1. Find the WRYDECO Git root and read `admin/access-token.md`. Load the actual configuration from `admin/.env`, using the precedence documented in `admin/get_access_token.py` if a key is missing. Expected keys are `SHOPIFY_SHOP`, `SHOPIFY_API_VERSION`, `SHOPIFY_ADMIN_TOKEN` and, for renewal, `SHOPIFY_CLIENT_ID` and `SHOPIFY_CLIENT_SECRET`.
2. Normalize the store and require `wrydeco.myshopify.com` before transmitting any credential. Use the configured GraphQL API version. Read `shop { myshopifyDomain currencyCode }` and confirm the response identifies the target shop. Collection reads require product read access. The gallery flow requires access to create Files and read them back.
3. Load credentials into the request process without printing them. The repo token CLI prints the token on success, so use the documented token exchange programmatically when the configured token returns HTTP 401. Keep the renewed token in memory and retry the original operation once. Never include credential values, auth headers, or upload signing parameters in logs, ledgers, CSVs, or chat. Send the Admin token only to the verified Shopify shop. The staged upload destination receives its returned signing parameters and file bytes.
4. Stop on a persistent auth error or a scope error and report the affected phase. When using the separately authorized proxy importer, follow the repo's [proxy import skill](../../shopify-import-proxy/SKILL.md) for its network and import operations.

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

Keep the collection handle and rule assignments in the handoff. The proxy importer reads the standard `Type` and `Tags` columns. Its current parser does not implement membership from a `Collection` column. With a verified smart rule, the product fields are sufficient for Shopify to calculate membership. The Shopify Admin native CSV exception accepts a collection title if explicitly needed for that route. The SOP's normal smart-collection path uses the standard export headers. Verify actual membership only after authorized import. [Shopify's CSV collection behavior](https://help.shopify.com/en/manual/products/import-export/using-csv#collection-column-exception)

## Resolve product authors

- Read the live `product_author` metaobjects from the verified store using the same Admin client. Paginate to completion and reuse the list within the batch. Use the author name, handle and GID to resolve assignments. Deduplicate the list by GID before choosing.
- If the user specifies an author for the product, use the unique matching Shopify entry by GID, handle, or name. Honor an explicitly specified author for the whole batch unless the product has its own assignment. If the requested author is missing or matches more than one entry, report the mismatch and stop before staging. A random choice requires the author to be unspecified.
- When no author is specified, choose one uniformly at random for that product from the live list, for example with Python `secrets.choice`. Make the choice once and record its name and GID in the working product record so retries preserve it. If the lookup fails or the list is empty, stop before staging.
- Put the full `gid://shopify/Metaobject/…` in the product's first CSV row. Include the selected author in the handoff and indicate whether the choice came from the user or the random default.

## Stage local gallery images

Start file writes only after every product passes intake, rule mapping, identity/classification, draft content validation, SKU and variant-price reconciliation. Upload only the approved files from the supplied galleries to Shopify Files. This phase prepares URL references for the CSV.

1. Record a batch image map before uploading. For each image record shop, product handle, source path, SHA-256, gallery position, alt text and deterministic filename, such as `<handle>-01-<hash>.<extension>`. Keep the verified source fingerprint and derived upload fingerprint separately if a user-authorized image transformation is applied.
2. Reuse `ShopifyClient.stage_image` in `auto/module-1/scraper/shopify.py` or the same documented GraphQL sequence. Configure it for the verified shop and current in-memory token. The default client renewal can write into its configured env path, so route credential handling through the procedure above or an isolated ephemeral config with no persistent credential file. Send the local image with its verified MIME type and intended alt text. Use `stagedUploadsCreate`, upload bytes to the returned target, then call `fileCreate` with its `resourceUrl` and `contentType: IMAGE`.
3. Capture the Shopify file ID as soon as it is available, then poll that ID for `fileStatus` and `MediaImage.image.url`. Accept only `READY` with a direct HTTPS image URL. Check the URL is fetchable as an image without sending Admin credentials. The staging URL and resource URL are temporary upload artifacts. Record only the final CDN URL in `Image Src`.
4. Update the image map after each successful upload. On retry, reuse a matching checkpoint entry and verify its ID and URL. If a previous call may have created a file before its ID was recorded, reconcile by the deterministic filename and existing file state before reissuing the create. Where the wrapper returns only after polling, use the same GraphQL steps directly when an intermediate ID is needed. Treat multiple matches or mismatched provenance as unresolved. Never overwrite or delete a Shopify file by default.
5. Stop on a permanent error or an unresolved create outcome. Preserve the checkpoint and identify any pending images. Produce the final CSV after every required image is verified and can be mapped to its gallery position. Shopify Admin's native CSV import can create a product copy of an image hosted in Files while retaining the original. [Staged uploads](https://shopify.dev/docs/api/admin-graphql/latest/mutations/stagedUploadsCreate) · [Shopify Files](https://shopify.dev/docs/api/admin-graphql/latest/mutations/fileCreate) · [CSV image behavior](https://help.shopify.com/en/manual/products/import-export/using-csv#prepare-your-images)

