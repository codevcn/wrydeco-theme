# AFTER PDP Audit Snapshot And BEFORE Comparison

PDP URL audited: http://127.0.0.1:9292/products/handcrafted-tree-branch-book-shelf-natural-wood
Handle: handcrafted-tree-branch-book-shelf-natural-wood
Snapshot date: 2026-08-25
Baseline BEFORE snapshot: todo/SEO/before_pdp_handcrafted-tree-branch-book-shelf-natural-wood_20260825.md
BEFORE snapshot found: yes
AFTER source status: 200
AFTER source length: 587114 bytes
Source/render finding: AFTER SEO-critical PDP content is present in initial HTML, including head tags, JSON-LD, H1, price, variant controls, gallery markup, Add to Cart markup, and updated product description.

## SEO Head Comparison

| Field | BEFORE | AFTER | Result |
| --- | --- | --- | --- |
| title | Handcrafted Tree Branch Book Shelf Corner Bookcase - Wrydeco | Open Branch Corner Tree Bookcase \| Wrydeco | Changed as intended; cleaner but phrase still needs editorial review |
| meta description | Transform your living room with a handcrafted tree branch bookshelf. This natural wood multi-layer wall bookcase displays art, plants, and books elegantly. | Explore the Open Branch Corner Tree Bookcase by Wrydeco, designed for unused room corner. Compare available sizes, finishes and product imagery. | Changed as intended; less generic, but grammar issue: "for unused room corner" should be "for an unused room corner" |
| canonical URL | https://wrydeco.myshopify.com/products/handcrafted-tree-branch-book-shelf-natural-wood | https://wrydeco.myshopify.com/products/handcrafted-tree-branch-book-shelf-natural-wood | Unchanged |
| robots meta | index, follow | index, follow | Unchanged |
| og:title | Handcrafted Tree Branch Book Shelf Corner Bookcase | Open Branch Corner Tree Bookcase \| Wrydeco | Changed with SEO title |
| og:description | Same as BEFORE meta description | Same as AFTER meta description | Changed with SEO description |
| og:url | https://wrydeco.myshopify.com/products/handcrafted-tree-branch-book-shelf-natural-wood | https://wrydeco.myshopify.com/products/handcrafted-tree-branch-book-shelf-natural-wood | Unchanged |
| og:image | /cdn/shop/files/8386190180409-gallery-001-logo-9a1f87292ba9.jpg?v=1787644179 | /cdn/shop/files/8386190180409-gallery-001-logo-9a1f87292ba9_ab6c8485-3643-423b-9355-c11dcf987e46.jpg?v=1787653797 | Changed CDN asset URL/version; still product gallery image, but review if image asset identity should have been preserved |
| og:type | product | product | Unchanged |
| og:price:amount | 79.448.000 | 79.448.000 | Unchanged |
| og:price:currency | VND | VND | Unchanged |

Notes:
- Product URL/handle stayed unchanged.
- Canonical/og:url still use `wrydeco.myshopify.com` in local preview, same as BEFORE.
- og:image remains root-relative rather than absolute, same SEO concern as BEFORE.

SEO head comparison result: PASS, with minor copy review for meta grammar and existing og:image absolute URL concern.

## Above-The-Fold Product Info Comparison

| Field | BEFORE | AFTER | Result |
| --- | --- | --- | --- |
| H1 / product title | Handcrafted Tree Branch Book Shelf Corner Bookcase | Open Branch Corner Tree Bookcase | Changed as intended |
| Price | 79.448.000 VND visible as 79.448.000₫ | 79.448.000 VND visible as 79.448.000₫ | Unchanged |
| Review display | 4.8 (107 reviews) | 4.8 (107 reviews) | Unchanged |
| Default selected variant | 49"W x 55"H x 8"D / Natural, variant 46359030300729 | 49"W x 55"H x 8"D / Natural, variant 46359030300729 | Unchanged |
| Size options | 4 sizes: 49, 60, 75, 90 inch width options | Same 4 sizes | Unchanged |
| Finish options | Natural, Light Oak, Walnut, Dark Walnut, Custom | Same values; UI text still shows Custom color while input text is Custom Wood Finish / value Custom | Functionally unchanged |
| Add to Cart state | Visible, enabled, ADD TO CART, /cart/add form present | Visible, enabled, ADD TO CART, /cart/add form present | Unchanged |
| Buy It Now | Visible, enabled | Visible, enabled | Unchanged |
| CTA trust text | Free Worldwide Shipping, 1-Year Warranty, design consultation, worldwide delivery, grain variation, handcrafted in Vietnam | Same | Unchanged |

Above-fold result: PASS.

## Product Description / Body Comparison

BEFORE active intro:
- "SCULPTURAL TREE-INSPIRED STORAGE"
- "Transform an empty living room corner into a functional piece of art with a handcrafted tree branch bookshelf that gives books, plants, pottery, framed photos, and collected décor a more intentional, visually warm place to live."

AFTER active intro:
- "The Open Branch Corner Tree Bookcase is a wood corner tree bookshelf defined by its open asymmetrical branch layout with generous shelf spacing. Its form is intended to create functional display or storage space in an unused room corner."

BEFORE product-specific detail pattern:
- Four marketing blocks: Unique Handcrafted Wood Character, Multi-Layer Display For Curated Styling, Artwork-Inspired Statement Piece, Designed For Living Room Corners & Design-Led Spaces.
- Broad styling/lifestyle language: gallery-like presence, grounded/artful mood, Japandi/wabi-sabi/farmhouse/woodland styling.

AFTER product-specific detail pattern:
- Product Details:
  - Design focus: open asymmetrical branch layout with generous shelf spacing
  - Available sizes: 49"W x 55"H x 8"D; 60"W x 60"H x 10"D; 75"W x 69"H x 12"D; 90"W x 82"H x 12"D
  - Available finishes: Natural; Light Oak; Walnut; Dark Walnut; Custom
  - Product type: corner-bookshelf
- Planning Your Space:
  - Measure both walls of the corner, nearby trim, outlets, and walking clearance before choosing a size.
  - Confirm the final installation requirements for the exact product.
- Before You Order:
  - Confirm wood species, load/weight capacity, production and delivery lead time, and care instructions through latest Wrydeco information or support.
  - Do not assume these details from imagery alone.

Main section/tabs:
- BEFORE: Details, Materials & Care with Description, Dimensions, Delivery & Refunds, Care Guide, Customization.
- AFTER: Same tabs and section structure.

Material claims:
- BEFORE: natural wood, solid wood, organic grain, knots, tonal variation, oiled/matte finish care, handmade.
- AFTER active copy says "wood corner tree bookshelf" and avoids wood species. Hidden global tabs still contain the broader solid wood/care language from BEFORE.

Size/dimension claims:
- BEFORE: same four size options plus "dimensions can be tailored to fit exactly where it will live" in hidden tab.
- AFTER active copy lists exact available sizes and adds measuring guidance. Hidden Dimensions tab remains unchanged, including the stronger customization wording.

Finish claims:
- BEFORE: Natural, Light Oak, Walnut, Dark Walnut, Custom color.
- AFTER active copy lists Natural, Light Oak, Walnut, Dark Walnut, Custom. Finish controls unchanged.

Mounting/installation claims:
- BEFORE hidden Delivery tab said some pieces may require wall mounting, anchoring, or professional installation depending on final design and conditions.
- AFTER active copy adds "Confirm the final installation requirements for the exact product." This is safer and does not invent hardware/load details.

Delivery/lead-time claims:
- BEFORE global process section included First 24 Hours, Day 2-7 sketch/sample, next 5 days finishing, next 7-10 days shipping coordination.
- AFTER active copy avoids claiming lead time and explicitly asks buyers to confirm lead time. Global process section still remains unchanged elsewhere on page.

Care/warranty/return claims:
- BEFORE hidden Care/Delivery tabs and CTA trust text contained care, warranty, return, final-sale, and refund timing language.
- AFTER active copy does not introduce new care/warranty/return claims. Hidden tabs and CTA trust language remain unchanged.

Generic/duplicated/awkward wording reduced:
- Reduced: old broad lifestyle and decor language in active Description tab was largely removed.
- Improved: active copy is more concrete about layout, sizes, finishes, planning, and uncertainty boundaries.
- Remaining issues:
  - Meta description grammar: "designed for unused room corner" should be "designed for an unused room corner".
  - H1/title phrase "Open Branch Corner Tree Bookcase" is cleaner than BEFORE but still slightly unnatural; "Open-Branch Corner Tree Bookcase" or "Open Branch Corner Bookshelf" may read better.
  - Hidden tabs still retain several old broad claims and the "Available sizesPick your size" spacing issue.

Unsupported claims:
- No major new unsupported claim introduced in the active product description.
- AFTER active description deliberately avoids inventing wood species, load capacity, hardware, lead time, wall compatibility, child safety, warranty, shipping, or customer stories.
- Existing global/trust claims remain from BEFORE and still need policy/ops substantiation.

Description quality comparison result: PASS, with minor grammar/editorial cleanup recommended.
Unsupported claims check: PASS for product-data update; NEEDS REVIEW for existing global/trust claims that remain.

## Product Data And UX Integrity Comparison

| Field | BEFORE | AFTER | Result |
| --- | --- | --- | --- |
| Handle | handcrafted-tree-branch-book-shelf-natural-wood | handcrafted-tree-branch-book-shelf-natural-wood | Unchanged |
| Product ID | 8386190180409 | 8386190180409 | Unchanged |
| Variant/options count | 4 size x 5 finish = 20 variants | 4 size x 5 finish = 20 variants | Unchanged |
| Default variant ID | 46359030300729 | 46359030300729 | Unchanged |
| Default price | 79.448.000₫ | 79.448.000₫ | Unchanged |
| Size 60 / Natural behavior | Price changed to 100.755.000₫, variant 46359030333497 | Price changed to 100.755.000₫, URL variant 46359030333497, hidden form ID 46359030333497 after wait | Intact |
| Size 60 / Walnut behavior | Price 100.755.000₫, variant 46359047667769 | Price 100.755.000₫, variant 46359047667769 | Intact |
| Gallery count | 8 thumbnails | 8 thumbnails | Unchanged |
| Gallery click | Thumbnail 2 changed active image | Thumbnail 2 changed active image to gallery-006 image | Intact |
| Add to Cart | Visible/enabled, not submitted | Visible/enabled, not submitted | Intact |
| Mobile layout | No page-level horizontal overflow; gallery/tabs horizontal scrolling | No page-level horizontal overflow; same pattern | Unchanged |

AFTER interaction details:
- Default state: 49"W x 55"H x 8"D / Natural, variant 46359030300729, price 79.448.000₫, Add to Cart enabled.
- After size-only retest: 60"W x 60"H x 10"D / Natural, variant 46359030333497, price 100.755.000₫, URL included `?variant=46359030333497`.
- After finish Walnut: variant 46359047667769, price 100.755.000₫.
- Gallery thumbnail 2: active thumbnail changed to 2, visible image changed to gallery-006 file.

Notes:
- CDN image filenames/versions changed after update. Gallery count and behavior are intact; if "preserve gallery" meant exact media asset identity, review this image URL change before scaling.
- Gallery alt text changed from old title to new title, but all product gallery alts remain identical rather than angle-specific.

Variant/price/gallery/Add-to-Cart integrity result: PASS, with media URL change noted for review.

## Structured Data / JSON-LD Comparison

| Field | BEFORE | AFTER | Result |
| --- | --- | --- | --- |
| Schema type | ProductGroup | ProductGroup | Unchanged |
| Schema name | Handcrafted Tree Branch Book Shelf Corner Bookcase | Open Branch Corner Tree Bookcase | Changed with product title |
| Schema description | Old active Description tab copy beginning "Sculptural Tree-Inspired Storage..." | New active product copy beginning "The Open Branch Corner Tree Bookcase is a wood corner tree bookshelf..." | Changed with product description |
| Schema URL | https://wrydeco.myshopify.com/products/handcrafted-tree-branch-book-shelf-natural-wood | Same | Unchanged |
| Schema image | First gallery image old CDN path | First gallery image new CDN path/version | Changed; still matches visible first image |
| Variant count | 20 | 20 | Unchanged |
| ProductGroupID | 8386190180409 | 8386190180409 | Unchanged |
| Offers | Offer entries, VND, InStock, prices 79448000 / 100755000 / 122062000 / 146032000 | Same | Unchanged |
| aggregateRating/review | Not present despite visible 4.8 (107 reviews) | Not present despite visible 4.8 (107 reviews) | Existing issue remains |

AFTER schema first variant:
- name: Open Branch Corner Tree Bookcase - 49"W x 55"H x 8"D / Natural
- offer price: 79448000
- priceCurrency: VND
- availability: http://schema.org/InStock
- offer URL: https://wrydeco.myshopify.com/products/handcrafted-tree-branch-book-shelf-natural-wood?variant=46359030300729

Structured data result: PASS for update integrity; NEEDS REVIEW for existing missing aggregateRating if the review summary is intended to be represented in schema.

## Breadcrumbs And Internal Links Comparison

| Field | BEFORE | AFTER | Result |
| --- | --- | --- | --- |
| Breadcrumb trail | No explicit breadcrumb nav detected | No explicit breadcrumb nav detected | Unchanged |
| Eyebrow collection link | Corner Bookshelf -> /collections/corner-bookshelf | Same | Unchanged |
| Consultation links | /pages/customization and /pages/customization#custom-inquiry__story-telling | Same | Unchanged |
| Artisan profile | /pages/product-author/khoi-hoang | Same | Unchanged |
| Related product links | Same related handles with `pr_*` params | Same related handles with `pr_*` params, different `pr_rec_id` value | Functionally unchanged |
| Policy/care links | About, Customization, Care Guide, FAQ, Contact, Warranty, Shipping, Refund, Terms, Privacy | Same | Unchanged |
| Link status spot check | First 20 important internal URLs returned 200 | First 20 important internal URLs returned 200 | Unchanged |

Internal link issues:
- No new broken/redirected links found in spot check.
- Existing issue remains: related product URLs include `pr_*` recommendation parameters and some image anchors have empty text.

Internal links comparison result: PASS, with existing related-link SEO cleanup still recommended outside product-data update scope.

## Verdicts

- Summary of intended SEO changes detected:
  - Product title/H1 changed to "Open Branch Corner Tree Bookcase".
  - SEO title, meta description, OG title/description, Twitter title/description changed.
  - Active product description changed from generic lifestyle copy to more concrete product/planning copy.
  - JSON-LD ProductGroup name/description and variant names updated to match the new product title/copy.
  - Gallery image alt text updated to new product title.

- Summary of unintended changes detected:
  - Product/gallery CDN image URLs changed to new file/version paths. Gallery works and still has 8 images, but review this if exact media preservation was required.
  - Minor meta grammar issue introduced: "designed for unused room corner".
  - Existing issues remain: missing aggregateRating despite visible review summary, no explicit breadcrumbs, related product links use tracking/recommendation params, root-relative og:image, hidden tabs retain some old broad claims.

Result ratings:
- SEO head comparison result: PASS
- H1/title/meta comparison result: NEEDS REVIEW
- Description quality comparison result: PASS
- Unsupported claims check: PASS for the updated active copy; NEEDS REVIEW for unchanged global/trust claims
- Variant/price/gallery/Add-to-Cart integrity: PASS
- Structured data comparison result: PASS
- Internal links comparison result: PASS
- Overall verdict: NEEDS REVIEW

Specific fixes required before importing or scaling:
1. Fix meta description grammar: change "designed for unused room corner" to "designed for an unused room corner" or a stronger natural sentence.
2. Editorially confirm the new product name. "Open Branch Corner Tree Bookcase" is better than the old title, but still slightly awkward; consider "Open-Branch Corner Tree Bookcase" or "Open Branch Corner Bookshelf" if aligned with keyword strategy.
3. Confirm whether changed Shopify CDN image filenames/versions are acceptable. If the update should not touch media assets, review import settings before scaling.
4. Keep the new active description's uncertainty language; it avoids inventing wood species, load capacity, hardware, lead time, or care specifics.
5. Existing non-blocking SEO cleanup for later theme/schema work: absolute og:image, aggregateRating only if valid, explicit breadcrumbs, clean related product URLs, and more specific gallery alt text.
