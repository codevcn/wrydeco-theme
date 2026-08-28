# BEFORE PDP Audit Snapshot

PDP URL audited: http://127.0.0.1:9292/products/natural-wood-multi-layer-tree-branch-floating-shelf
Handle: natural-wood-multi-layer-tree-branch-floating-shelf
Snapshot date: 2026-08-25
Audit scope: local rendered PDP plus initial HTML/source
Initial HTML status: 200
Initial HTML length: 596425 bytes
Source/render finding: SEO-critical PDP content was present in initial HTML, including head tags, JSON-LD, H1, price, variant controls, gallery markup, Add to Cart markup, and product description sections.

## SEO Head

- title: Natural Wood Multi-Layer Tree Branch Floating Shelf - Wrydeco
- meta description: Transform your space with a natural wood multi-layer tree branch floating shelf. This handcrafted sculptural art piece brings unique character to any room.
- canonical URL: https://wrydeco.myshopify.com/products/natural-wood-multi-layer-tree-branch-floating-shelf
- robots meta: index, follow
- og:title: Natural Wood Multi-Layer Tree Branch Floating Shelf
- og:description: Transform your space with a natural wood multi-layer tree branch floating shelf. This handcrafted sculptural art piece brings unique character to any room.
- og:url: https://wrydeco.myshopify.com/products/natural-wood-multi-layer-tree-branch-floating-shelf
- og:image: /cdn/shop/files/8383297585209-gallery-001-logo-d735d6ca1ba7_79e483c9-df5f-41c8-9696-1a04ccf8b990.jpg?v=1787644157
- og:type: product
- og:price:amount: 44.026.000
- og:price:currency: VND
- twitter:title: Natural Wood Multi-Layer Tree Branch Floating Shelf
- twitter:description: same as meta description

Notes:
- Canonical and og:url point to `https://wrydeco.myshopify.com/...`, not local `127.0.0.1`. This matches local Shopify preview behavior observed on prior PDPs.
- og:image is root-relative instead of absolute. Social parsers generally prefer absolute image URLs.

## Above-The-Fold Product Info

- Eyebrow/collection link: Explore All Pieces -> /collections/all
- H1/product title: Natural Wood Multi-Layer Tree Branch Floating Shelf
- H1 count: 1 visible H1
- Price/default visible price: 44.026.000₫
- Review display near title: 4.8 (107 reviews)
- Reviews section state lower on page: "VERIFIED REVIEWS", "What our customers are saying", and "Reviews are taking a little longer to appear"
- Default selected variant:
  - options[Size]: 45"W x 45"H x 8"D
  - options[Wood Finish]: Natural
  - variant id: 46343016546361
- Size options visible:
  - 45"W x 45"H x 8"D
  - 55"W x 55"H x 8"D
  - 65"W x 65"H x 10"D
  - 80"W x 80"H x 10-12"D
- Wood finish options visible:
  - Natural
  - Light Oak
  - Walnut
  - Dark Walnut
  - Custom color in UI; underlying variant value is Custom / input text observed as Custom Wood Finish
- Visible option matrix: 4 sizes x 5 finishes = 20 product variants in schema/source
- Quantity control: visible decrease/increase quantity controls; default quantity field was custom/outside the product form extraction and not found as a standard `name="quantity"` input in the cart form snapshot
- Add to Cart button state: visible, enabled, text "ADD TO CART", `type="submit"`, `name="add"`
- Buy It Now button state: visible, enabled, text "BUY IT NOW"
- Product form action: /cart/add
- Product form method: post
- Hidden form id/default variant: 46343016546361
- Hidden product-id: 8383297585209
- Trust/policy text near CTA:
  - Free Worldwide Shipping
  - 1-Year Warranty
  - PRIVATE DESIGN GUIDANCE: "Book a complimentary consultation before ordering to review dimensions, finish, layout, and fit for your space. We respond within 24-48 business hours."
  - Why this piece works well
  - Worldwide delivery available: "Complimentary standard shipping for eligible destinations."
  - Natural grain variation in every piece: "Uniquely yours."
  - Handcrafted in Vietnam: "Shaped by skilled artisans and coordinated by our online support team."

## Product Description / Body

Main description area:
- Section heading: Details, Materials & Care
- Tabs:
  - Description (active by default)
  - Dimensions
  - Delivery & Refunds
  - Care Guide
  - Customization

Active Description tab text:
- "FLOATING ART SHELF"
- Intro paragraph: "Turn an empty kitchen wall into functional art with a handcrafted tree branch floating shelf that gives cookbooks, jars, mugs, plants, and collected décor a more intentional home while adding warmth, texture, and natural character to the space."
- Detail 01: "Unique Handcrafted Wood Character"
  - "Each piece is individually handcrafted by skilled artisans, so every shelf carries its own wood grain flow, knots, branch-inspired curves, and tonal variation. That natural individuality gives it a one-of-a-kind presence that feels more like art than standard storage."
- Detail 02: "Many Layered Display Levels"
  - "The multi-layer branch-style layout creates vertical rhythm and plenty of styling possibilities for spice jars, ceramics, candles, framed prints, bowls, small plants, cookbooks, and decorative accents, helping everyday kitchen storage look curated and elevated."
- Detail 03: "Designed For Refined Interiors"
  - "A strong fit for kitchens, breakfast nooks, coffee corners, dining spaces, living rooms, studies, home libraries, and entryways. Works beautifully with organic modern, rustic, Japandi, farmhouse, woodland, wabi-sabi, and collected-vintage styling."
- Detail 04: "Statement Piece & Gift-Worthy Design"
  - "Crafted with care and prepared for secure delivery, each floating shelf features slight variation in wood tone and branch form that highlights its handmade nature. A memorable gift for design lovers, home cooks, book lovers, artists, and homeowners who appreciate artisan décor."

Hidden Dimensions tab text:
- "Dimensions & sizing"
- "Every WRYDECO piece is crafted to order in the sizes shown here. Choose the option that best suits your space, and because each piece is handmade, dimensions can be tailored to fit exactly where it will live."
- Available sizes:
  - 45"W x 45"H x 8"D
  - 55"W x 55"H x 8"D
  - 65"W x 65"H x 10"D
  - 80"W x 80"H x 10-12"D
- "Measurements are approximate and handcrafted to order, so slight variation is a natural part of solid wood."
- "Use, placement, mounting, hardware, and recommended load guidance are provided with the delivered piece where applicable and are based on the final design."
- Rendering/text extraction issue: "Available sizesPick your size..." lacks spacing, and size values run together in extracted text.

Hidden Delivery & Refunds tab text:
- "Every piece is handcrafted and made to order, so all sales are final. Non-returnable does not mean unsupported. If your order arrives damaged, defective, or incorrect, we will make it right."
- All sales final: custom, made-to-order, used, and sale items are not eligible for return.
- Natural variation of solid wood is described as character, not defect.
- Damaged/defective arrival: refund or replacement may be requested.
- Report window: within 30 calendar days of delivery with order number, clear photos, packaging, shipping label, visible damage, and video where useful.
- Installation guidance: some pieces are freestanding; others may require wall mounting, anchoring, or professional installation depending on final design and destination conditions. Standard shipping does not include installation unless confirmed in writing.
- Refund timing: approved refunds issued to original payment method, typically within 10 business days of approval.
- Link text: Read the full Return & Refund Policy

Hidden Care Guide tab text:
- "Solid wood responds to seasonal changes and develops character over time. Your delivered piece includes product-specific use, placement, and care guidance where applicable."
- Essentials: wipe with soft dry/slightly damp cloth; use coasters/mats/trivets; keep away from direct sunlight and heat.
- Daily/seasonal/long-term care guidance.
- Materials & finishes:
  - Oil finish: re-oil every 6-12 months.
  - Matte finish: clean gently and avoid waxes.
  - Natural grain: embrace unique markings.
- Avoid abrasive pads, silicone sprays, harsh chemicals, and hot items directly on surface.
- Link text: See the full Care Guide

Hidden Customization tab text:
- "Every WRYDECO piece can be tailored to you -- choose your slab and finish, adjust the dimensions, or work one-on-one with our design concierge to create a piece made entirely for your space."
- "Share your space, style, and timeline, and we'll guide you from first sketch to finished piece."
- Link text: Request a private consultation

Other body sections observed:
- Crafted by Son Tran / MASTER WOODWORKER
- Trust/process claims: CARVED WITH PRECISION, ONE OF A KIND, EVERY TIME, MADE ENTIRELY BY HAND, DIRECT FROM THE WORKSHOP
- OUR PROCESS / Handcrafted with Purpose.
- SOUL OF SOLID WOOD / No Two Pieces Are Ever Truly Alike
- Order Process & Delivery with steps:
  1. Receive Order
  2. First 24 Hours
  3. Day 2-7: Create Sketch & Sample
  4. Send Sample Photos or Video
  5. Finish Surface & Details
  6. Send Final Photos or Video
  7. Disassemble & Box the Parts
  8. Shipping
- Lead Time text:
  - First 24 Hours: contact customer to collect detailed custom information.
  - Day 2-7: create sketch design and raw sample; photos/video sent for approval.
  - Next 5 days: final finishing completed; final photos/video sent before packing.
  - Next 7-10 days: after confirmation and packing, standard shipping coordinated to eligible destination.
- Related section: "CURATED FOR HARMONY" / "Pairs Beautifully With"

## Product Data And UX Integrity

- Product handle inferred from URL: natural-wood-multi-layer-tree-branch-floating-shelf
- Product id observed: 8383297585209
- Visible variant/options count:
  - 4 size options
  - 5 finish options
  - 20 variants in ProductGroup JSON-LD
- Default variant id: 46343016546361
- Variant interaction test:
  - Default: 45"W x 45"H x 8"D / Natural, variant 46343016546361, price 44.026.000₫
  - Size-only focused retest: 55"W x 55"H x 8"D / Natural updated after a longer wait to variant 46343016579129, price 52.016.000₫, URL `?variant=46343016579129`
  - Size 55 / Walnut: variant 46343026573369, price 52.016.000₫
  - State restored to 45"W x 45"H x 8"D / Natural, variant 46343016546361, price 44.026.000₫
- Add to Cart appeared functional:
  - Form `/cart/add` present
  - Add button visible and enabled
  - Submit was not clicked to avoid changing cart state
- Gallery state:
  - 8 visible gallery thumbnails
  - Default active thumbnail: 1 of 8
  - Main image default: /cdn/shop/files/8383297585209-gallery-001-logo-d735d6ca1ba7_79e483c9-df5f-41c8-9696-1a04ccf8b990.jpg?v=1787644157&width=1200
  - Main image alt: Natural Wood Multi-Layer Tree Branch Floating Shelf
  - Thumbnail 2 click test: active thumbnail changed to 2; visible main image changed to /cdn/shop/files/8383297585209-gallery-002-logo-331c1c394e9a_837df712-1fe1-4ddb-b68b-9aaeb6f5bd02.jpg?v=1787644157&width=1200
  - Product gallery image alts observed were identical: "Natural Wood Multi-Layer Tree Branch Floating Shelf"
- Mobile/layout quick check:
  - Temporary mobile viewport: 390x844
  - document scrollWidth matched clientWidth, no page-level horizontal overflow detected
  - Gallery thumbnail row and details tabs are horizontally scrollable regions
  - No obvious clipping found in H1, price, variants, Add to Cart, or trust blocks during quick DOM viewport check
- UX note:
  - Size-only variant update may take longer than the first short wait; it updated correctly after a focused longer wait.

## Structured Data / JSON-LD

- JSON-LD type: ProductGroup
- @context: http://schema.org/
- @id: /products/natural-wood-multi-layer-tree-branch-floating-shelf#product
- brand: Wrydeco
- category: Floating Bookcases & Shelves
- schema name: Natural Wood Multi-Layer Tree Branch Floating Shelf
- schema url: https://wrydeco.myshopify.com/products/natural-wood-multi-layer-tree-branch-floating-shelf
- schema description: active Description tab text beginning with "Floating Art Shelf..." and the four description points.
- schema image: first variant uses https://wrydeco.myshopify.com/cdn/shop/files/8383297585209-gallery-001-logo-d735d6ca1ba7_79e483c9-df5f-41c8-9696-1a04ccf8b990.jpg?v=1787644157&width=1920
- productGroupID: 8383297585209
- Variant/offer count: 20 `hasVariant` Product entries
- Offers:
  - All observed offers use @type Offer
  - availability: http://schema.org/InStock
  - priceCurrency: VND
  - Price by size:
    - 45"W x 45"H x 8"D: 44026000
    - 55"W x 55"H x 8"D: 52016000
    - 65"W x 65"H x 10"D: 59793000
    - 80"W x 80"H x 10-12"D: 71245000
  - Finish variants retain the same price by selected size
- aggregateRating/review structured data: not found in ProductGroup JSON-LD, despite visible 4.8 (107 reviews) review summary near title.

Schema mismatches / notes:
- Visible review summary exists, but ProductGroup JSON-LD does not include aggregateRating or review data.
- Visible gallery has 8 images, but variant schema image appears to use the first gallery image.
- `@id` values are relative while offer URLs and schema URL are absolute.
- Local page URL is `127.0.0.1`, while canonical/schema/offer URLs use `wrydeco.myshopify.com`; verify intended production domain before launch/import validation.
- Schema description contains HTML-derived whitespace and an escaped `&amp;` in "Statement Piece &amp; Gift-Worthy Design".

## Breadcrumbs And Internal Links

- Breadcrumb trail: no explicit breadcrumb nav detected.
- Product eyebrow/collection link: Explore All Pieces -> /collections/all
- Consultation/customization links:
  - /pages/customization
  - /pages/customization#custom-inquiry__story-telling
- Artisan/profile link:
  - /pages/product-author/son-tran
- Related product links visible:
  - Rustic Solid Wood Tree Branch Wall Mounted Bookshelf -> /products/rustic-solid-wood-tree-branch-wall-mounted-bookshelf?pr_prod_strat=collection_fallback&pr_rec_id=466c64ed2&pr_rec_pid=8383297650745&pr_ref_pid=8383297585209&pr_seq=uniform
  - Handcrafted Wooden Tree Branch Floating Wall Shelf -> /products/handcrafted-wooden-tree-branch-floating-wall-shelf?pr_prod_strat=collection_fallback&pr_rec_id=466c64ed2&pr_rec_pid=8383297683513&pr_ref_pid=8383297585209&pr_seq=uniform
  - Multi-Layer Sculptural Wood Tree Branch Wall Shelf -> /products/multi-layer-sculptural-wood-tree-branch-wall-shelf?pr_prod_strat=collection_fallback&pr_rec_id=466c64ed2&pr_rec_pid=8383297716281&pr_ref_pid=8383297585209&pr_seq=uniform
  - Unique Natural Wood Tree Branch Floating Wall Shelf -> /products/unique-natural-wood-tree-branch-floating-wall-shelf?pr_prod_strat=collection_fallback&pr_rec_id=466c64ed2&pr_rec_pid=8383297749049&pr_ref_pid=8383297585209&pr_seq=uniform
  - Handcrafted Natural Wood Tree Branch Floating Shelf -> /products/handcrafted-natural-wood-tree-branch-floating-shelf-1?pr_prod_strat=collection_fallback&pr_rec_id=466c64ed2&pr_rec_pid=8383297781817&pr_ref_pid=8383297585209&pr_seq=uniform
  - Handcrafted Tree Branch Bookshelf -> /products/tree-branch-bookshelf-the-whispering-sequoia?pr_prod_strat=collection_fallback&pr_rec_id=466c64ed2&pr_rec_pid=8376399495225&pr_ref_pid=8383297585209&pr_seq=uniform
- Footer/internal collection links observed:
  - /collections/signature-pieces
  - /collections/bookshelf-modern
  - /collections/bookshelf-rustic
  - /collections/standing-bookshelf
  - /collections/corner-bookshelf
  - /collections/floating-bookshelf
  - /collections/new-arrivals
- Policy/trust links observed:
  - /pages/about-us
  - /pages/customization
  - /pages/care-guide
  - /pages/faq
  - /pages/contact
  - /pages/warranty-policy
  - /policies/shipping-policy
  - /policies/refund-policy
  - /policies/terms-of-service
  - /policies/privacy-policy
- Link status spot check:
  - The first 20 visible important internal URLs checked returned 200 and did not redirect.
- Internal link SEO issue:
  - Related product links use recommendation/tracking query parameters (`pr_prod_strat`, `pr_rec_id`, `pr_rec_pid`, `pr_ref_pid`, `pr_seq`). They work locally, but clean canonical product URLs are preferable for crawlable product-card links.
  - Some related product cards have empty linked image anchors followed by text links to the same URL; not broken, but creates repeated/empty-anchor links.

## Unsupported Or Risky Claims Found

- "Free Worldwide Shipping" is strong. Nearby copy qualifies with "eligible destinations", but the button text itself is absolute.
- "1-Year Warranty" should be verified against the warranty policy and product scope.
- "Handcrafted in Vietnam" should match actual fulfillment/workshop data.
- "Made entirely by hand" and "Every WRYDECO piece can be tailored to you" are broad claims and should match actual production and customization constraints.
- "Dimensions can be tailored to fit exactly where it will live" is a potentially over-precise customization promise.
- Delivery timeline claims should be checked against operational reality:
  - First 24 hours contact
  - Day 2-7 sketch/sample
  - Next 5 days finishing
  - Next 7-10 days shipping coordination
- Refund/final-sale language should align exactly with active store policy.
- Material claims include natural wood, solid wood, wood grain, knots, tonal variation, oiled/matte finish care. These should be true for this product and each finish option.
- Mounting/load guidance is deferred to delivered piece; product page itself does not give load capacity, exact mounting hardware, wall type compatibility, or installation requirements.
- "Gift-worthy" and "memorable gift" are subjective marketing claims; not high-risk but generic.

## Generic / Duplicated / Awkward Copy Found

- Product title/H1 is keyword-heavy and long: "Natural Wood Multi-Layer Tree Branch Floating Shelf".
- Meta description is generic/formulaic: "Transform your space..." and "brings unique character to any room."
- Description uses broad lifestyle language likely duplicated across group:
  - "functional art"
  - "more intentional home"
  - "warmth, texture, and natural character"
  - "one-of-a-kind presence"
  - "curated and elevated"
  - "refined interiors"
  - long style list: organic modern, rustic, Japandi, farmhouse, woodland, wabi-sabi, collected-vintage
  - "gift-worthy design"
- Hidden dimensions text extraction shows "Available sizesPick your size..." without spacing.
- Finish UI says "Custom color" while underlying variant value is "Custom" and input text is "Custom Wood Finish."
- All gallery image alts are identical and do not describe individual image angles/details.
- Related products are highly similar and likely part of a duplicate-description group.

## Overall Verdict

Verdict: NEEDS REVIEW

Reason:
- Product UX appears intact enough for a BEFORE snapshot and pilot-copy update: page renders, H1/price/options/gallery/CTA are present, variant changes update price and variant id after sufficient wait, Add to Cart appears enabled, and internal links spot-checked return 200.
- Content and schema need review before scaling: title/meta/body copy are generic and likely duplicated, visible reviews are not represented in ProductGroup structured data, related product links use tracking parameters, and multiple claims should be substantiated before import.

Recommended fixes before updating this PDP:
1. Rewrite product title/H1 and SEO title into a cleaner, less keyword-stuffed name while preserving the product URL handle unless intentionally changed.
2. Rewrite meta description to be more product-specific and less generic.
3. Replace broad lifestyle copy with concrete details: floating/wall shelf use, branch layout, exact sizes, finish choices, room planning, and what should be confirmed before purchase.
4. Avoid inventing wood species, load capacity, hardware, wall compatibility, child safety, lead time, warranty, shipping, or customer stories.
5. Verify or soften claims for free worldwide shipping, 1-year warranty, made entirely by hand, exact customization, delivery timelines, and solid/natural wood care.
6. Keep size/finish variant names, variant IDs, prices, inventory, images, and product handle unchanged during product-data update unless the import is explicitly scoped to change them.
7. Consider adding ProductGroup aggregateRating only if review data is valid and policy-compliant.
8. Improve image alt text diversity if product image metadata is part of the update scope.
9. Prefer clean related product URLs without `pr_*` parameters if theme changes are later allowed; do not handle that as part of product-data update unless specifically scoped.
