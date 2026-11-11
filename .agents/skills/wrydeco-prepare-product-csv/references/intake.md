# Intake gates

Approve each of the three inputs for each product before authoring, uploading, or writing a CSV. Use a temporary product key such as the image folder basename to reconcile all three inputs. Check presence and product mapping across the entire batch before making Shopify requests. Resolve the live currency and collection rules only after that local check passes. Assign a batch verdict after checking all products. A rejection anywhere blocks the entire batch, including partial CSV drafts. A readable but ambiguous value is a rejection until corrected. When reporting a rejection, state the product key, input, observed issue, and smallest correction that would unblock it.

## 1. Screenshot of the priced variant table

**Approve** when every axis name and unit is readable, every offered row is visible, and each row maps to exactly one complete purchasable tuple and its final selling price. Multiple screenshots can form one table when their order and any overlap are provable. Record a proven repeated screenshot row once. Treat repeated tuples elsewhere in the source table as duplicates. Preserve the ordered axis names and source values. The export supports up to three axes. If the screenshot lists dimensions in separate columns, keep those axes separate. An explicit user instruction can supply context for an ambiguous header or price convention.

**Reject** a missing, cropped or illegible table, uncertain column or product association, missing values or prices, an axis that changes meaning across rows, duplicate tuples, conflicting overlap across screenshots, or more than three axes. Reject option-level prices or surcharges unless the source also provides the base price, exact adjustment rules and allowed combinations so every final price can be reconstructed. Do not expand a sparse table into a Cartesian product or invent prices for missing combinations.

### Price approval procedure

1. Transcribe a source ledger for every visible row with screenshot and row reference, original option cells, original price text, and normalized price. Capture headers and any currency/units printed in the source. Distinguish sale price from list price, compare-at price, price ranges, and surcharges.
2. Read every option cell and price twice from the image. Use OCR as a transcription aid and visually reconcile its output with the source. Zoom or re-read a tight crop of any unclear digit or separator. If still ambiguous, reject that row and name the exact cell that needs a clearer image or correction.
3. Verify the target store currency via the Shopify procedure. WRYDECO was observed using USD. A table marked in another currency, or a currency symbol with competing interpretations, requires an explicit user-approved conversion rule before proceeding. An unlabeled table can use verified store currency when the source is a WRYDECO selling-price table and contains no conflicting currency cues. Record the decision in the ledger.
4. Resolve the number format from the table as a whole. For example, an unambiguous comma-grouped integer `2,083` becomes `2083`. A value such as `2,083` by itself can also be a decimal in another locale, so require clarification when the table or user context cannot distinguish the formats. Compare ambiguous or mixed separators with the rest of the source. Never auto-strip every comma or period. Use `Decimal`, preserve the exact monetary amount, and serialize plain decimal text with no currency symbol, grouping or exponent. Reject a missing, negative, non-finite, out-of-precision or ambiguous price. Treat zero as rejected until explicitly confirmed. Do not round an amount to force it into currency precision.
5. Count source tuples and compare the ordered tuple-to-price mapping against the planned variants and the CSV after serialization. Reject every discrepancy, including swapped price rows, unit changes and duplicate tuples introduced by normalization. Report surprising amounts for review when the visual source is unclear. Retain a clearly verified amount even if it looks unusual.

Example of a source row once the table establishes inch units and comma grouping: `Width=10 in | Height=30 in | 2,083` yields one variant priced `2083` USD. Seven distinct rows in the screenshot yield seven variants, even when other width/height pairings are possible.

## 2. Local product photo folder

**Approve** an explicit, accessible folder mapped to exactly one product, with at least one valid, decodable image and enough views to identify the item for sale and classify visible branches. Inventory approved images with relative paths, format and a content fingerprint. Use supplied gallery order if available. Otherwise choose the clearest view of the product first and order remaining images deterministically. Deduplicate identical bytes within a gallery and record what was skipped.

**Reject** a missing, unreadable or empty folder, corrupt intended gallery files, a folder containing several products without an explicit mapping, or a set of images that leaves the product or its branch classification ambiguous. Exclude clearly unrelated screenshots, documents and hidden files from gallery candidates. If a file intended for the gallery is unsupported or unreadable, identify it in the rejection. For a scene with multiple objects, use the collection and the object shown consistently across views to locate the sold subject. If two candidates still fit, request the intended item or a clearer view before proceeding.

## 3. Target collection handle

**Approve** an unambiguous handle supplied for the product or explicitly shared by the batch that matches exactly one existing collection on verified WRYDECO and whose smart rules can be satisfied from approved product data. Resolve the live collection rules, any required product type or tags, and rule compatibility with the image subject using [shopify.md](shopify.md). A pasted collection URL can supply its final handle when the destination is unambiguous and confirmed by Admin API.

**Reject** a missing handle, a title with no unambiguous handle, a collection on another shop, an unknown handle, an unreadable rule set, a manual collection requiring a separate assignment, or a rule the product cannot satisfy. Reject competing mappings when the evidence does not select one. A collection rule can supply a Type or Tag. It cannot supply an unsupported specification or justify misclassifying the item. Record the exact handle, resolved rule and proposed assignments in the ledger.

If collection or credential verification is unavailable, label that gate unresolved and stop before authoring or uploading. A temporary API outage does not make the collection invalid.

