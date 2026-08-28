# BEFORE PDP Audit Snapshot

PDP URL audited: http://127.0.0.1:9292/products/handcrafted-tree-branch-book-shelf-natural-wood
Handle: handcrafted-tree-branch-book-shelf-natural-wood
Snapshot date: 2026-08-25
Audit scope: local rendered PDP plus initial HTML/source
Initial HTML status: 200
Initial HTML length: 589182 bytes
Source/render finding: SEO-critical PDP content was present in initial HTML, including head tags, JSON-LD, H1, price, variant controls, gallery markup, Add to Cart markup, and product description sections.

## SEO Head

- title: Handcrafted Tree Branch Book Shelf Corner Bookcase - Wrydeco
- meta description: Transform your living room with a handcrafted tree branch bookshelf. This natural wood multi-layer wall bookcase displays art, plants, and books elegantly.
- canonical URL: https://wrydeco.myshopify.com/products/handcrafted-tree-branch-book-shelf-natural-wood
- robots meta: index, follow
- og:title: Handcrafted Tree Branch Book Shelf Corner Bookcase
- og:description: Transform your living room with a handcrafted tree branch bookshelf. This natural wood multi-layer wall bookcase displays art, plants, and books elegantly.
- og:url: https://wrydeco.myshopify.com/products/handcrafted-tree-branch-book-shelf-natural-wood
- og:image: /cdn/shop/files/8386190180409-gallery-001-logo-9a1f87292ba9.jpg?v=1787644179
- og:type: product
- og:price:amount: 79.448.000
- og:price:currency: VND
- twitter:card: summary_large_image
- twitter:title: Handcrafted Tree Branch Book Shelf Corner Bookcase
- twitter:description: same as meta description

Notes:
- Canonical and og:url point to `https://wrydeco.myshopify.com/...`, not the local `127.0.0.1` URL. This is expected in local Shopify preview but should be verified against the intended production domain.
- og:image is root-relative instead of absolute in the rendered head/source. Social parsers usually prefer absolute image URLs.

## Above-The-Fold Product Info

- Eyebrow/collection link: Corner Bookshelf
- H1/product title: Handcrafted Tree Branch Book Shelf Corner Bookcase
- H1 count: 1 visible H1
- Price/default visible price: 79.448.000₫
- Review display near title: 4.8 (107 reviews)
- Reviews section state lower on page: "VERIFIED REVIEWS", "What our customers are saying", and "Reviews are taking a little longer to appear"
- Default selected variant:
  - options[Size]: 49"W x 55"H x 8"D
  - options[Wood Finish]: Natural
  - variant id: 46359030300729
- Size options visible:
  - 49"W x 55"H x 8"D
  - 60"W x 60"H x 10"D
  - 75"W x 69"H x 12"D
  - 90"W x 82"H x 12"D
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
- Hidden form id/default variant: 46359030300729
- Hidden product-id: 8386190180409
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
- "SCULPTURAL TREE-INSPIRED STORAGE"
- Intro paragraph: "Transform an empty living room corner into a functional piece of art with a handcrafted tree branch bookshelf that gives books, plants, pottery, framed photos, and collected décor a more intentional, visually warm place to live."
- Detail 01: "Unique Handcrafted Wood Character"
  - "Each piece is individually handcrafted by skilled artisans, so every bookshelf carries its own organic grain flow, knots, tonal variation, and branch-inspired curves. That one-of-a-kind natural character makes it feel far more special than ordinary wall storage."
- Detail 02: "Multi-Layer Display For Curated Styling"
  - "Designed with many layered display areas, this branch-style bookshelf creates vertical rhythm and visual depth for books, candles, ceramics, vases, keepsakes, and art objects--helping everyday décor feel more expressive, elevated, and beautifully arranged."
- Detail 03: "Artwork-Inspired Statement Piece"
  - "The sculptural tree silhouette brings movement, texture, and a gallery-like presence to the wall, making it ideal for customers who want storage that also functions as décor. It adds a grounded, artful mood to refined living room interiors."
- Detail 04: "Designed For Living Room Corners & Design-Led Spaces"
  - "A strong fit for living room corners, reading nooks, studies, home libraries, bedrooms, entryways, cabins, and boutique offices. Works beautifully with organic modern, Japandi, wabi-sabi, farmhouse, woodland, rustic, and collected-vintage styling."

Hidden Dimensions tab text:
- "Dimensions & sizing"
- "Every WRYDECO piece is crafted to order in the sizes shown here. Choose the option that best suits your space, and because each piece is handmade, dimensions can be tailored to fit exactly where it will live."
- Available sizes:
  - 49"W x 55"H x 8"D
  - 60"W x 60"H x 10"D
  - 75"W x 69"H x 12"D
  - 90"W x 82"H x 12"D
- "Measurements are approximate and handcrafted to order, so slight variation is a natural part of solid wood."
- "Use, placement, mounting, hardware, and recommended load guidance are provided with the delivered piece where applicable and are based on the final design."
- Rendering issue in extracted text: "Available sizesPick your size..." lacked a space in text extraction.

Hidden Delivery & Refunds tab text:
- "Every piece is handcrafted and made to order, so all sales are final. Non-returnable does not mean unsupported. If your order arrives damaged, defective, or incorrect, we will make it right."
- All sales final: "Custom, made-to-order, used, and sale items are not eligible for return. The natural variation of solid wood -- grain, tone, knots, and texture -- is part of its character, not a defect."
- Damaged/defective arrival: refund or replacement may be requested.
- Report window: within 30 calendar days of delivery with order number, photos, packaging, shipping label, visible damage, and video where useful.
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
- Crafted by Khoi Hoang / PRINCIPAL ARTISAN
- Artisan quote about raw wood and handmade wooden pieces
- Trust/process claims: CARVED WITH PRECISION, ONE OF A KIND, MADE ENTIRELY BY HAND, DIRECT FROM THE WORKSHOP, 27+ YEARS OF CRAFTSMANSHIP
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

- Product handle inferred from URL: handcrafted-tree-branch-book-shelf-natural-wood
- Product id observed: 8386190180409
- Visible variant/options count:
  - 4 size options
  - 5 finish options
  - 20 variants in ProductGroup JSON-LD
- Default variant id: 46359030300729
- Variant interaction test:
  - Before: 49"W x 55"H x 8"D / Natural, variant id 46359030300729, price 79.448.000₫
  - After clicking size 60"W x 60"H x 10"D: variant id changed to 46359030333497, price changed to 100.755.000₫
  - After clicking finish Walnut while size 60 was selected: variant id changed to 46359047667769, price remained 100.755.000₫
  - State was restored to 49"W x 55"H x 8"D / Natural, variant id 46359030300729, price 79.448.000₫
- Add to Cart appeared functional:
  - Form `/cart/add` present
  - Add button visible and enabled
  - Submit was not clicked to avoid changing cart state
- Gallery state:
  - 8 visible gallery thumbnails
  - Default active thumbnail: 1 of 8
  - Main image default: /cdn/shop/files/8386190180409-gallery-001-logo-9a1f87292ba9.jpg?v=1787644179&width=1200
  - Main image alt: Handcrafted Tree Branch Book Shelf Corner Bookcase
  - Thumbnail 2 click test: active thumbnail changed to 2; visible main image changed to /cdn/shop/files/8386190180409-gallery-006-logo-4ba6c056a09a.jpg?v=1787644179&width=1200
  - Main gallery images use width="1200" height="1200"; first image loading="eager" and fetchpriority="high"; some later gallery images loading="lazy"
  - All product gallery image alts observed were identical: "Handcrafted Tree Branch Book Shelf Corner Bookcase"
- Mobile/layout quick check:
  - Temporary mobile viewport: 390x844
  - document scrollWidth matched clientWidth, no page-level horizontal overflow detected
  - Gallery thumbnail row and details tabs are horizontally scrollable regions
  - No obvious clipping found in H1, price, variants, Add to Cart, or trust blocks during quick DOM viewport check

## Structured Data / JSON-LD

- JSON-LD type: ProductGroup
- @context: http://schema.org/
- @id: /products/handcrafted-tree-branch-book-shelf-natural-wood#product
- brand: Wrydeco
- category: Bookcases & Standing Shelves
- schema name: Handcrafted Tree Branch Book Shelf Corner Bookcase
- schema url: https://wrydeco.myshopify.com/products/handcrafted-tree-branch-book-shelf-natural-wood
- schema description: the active product description HTML/text beginning with "Sculptural Tree-Inspired Storage..." and the four description points.
- schema image: each variant uses https://wrydeco.myshopify.com/cdn/shop/files/8386190180409-gallery-001-logo-9a1f87292ba9.jpg?v=1787644179&width=1920
- productGroupID: 8386190180409
- Variant/offer count: 20 `hasVariant` Product entries
- Offers:
  - All observed offers use @type Offer
  - availability: http://schema.org/InStock
  - priceCurrency: VND
  - Price by size:
    - 49"W x 55"H x 8"D: 79448000
    - 60"W x 60"H x 10"D: 100755000
    - 75"W x 69"H x 12"D: 122062000
    - 90"W x 82"H x 12"D: 146032000
  - Finish variants retain the same price by selected size
- aggregateRating/review structured data: not found in ProductGroup JSON-LD, despite visible 4.8 (107 reviews) review summary near title.

Schema mismatches / notes:
- Visible review summary exists, but ProductGroup JSON-LD does not include aggregateRating or review data.
- Visible gallery has 8 images, but each variant schema image points to the same first gallery image.
- `@id` values are relative while offer URLs and schema URL are absolute.
- Local page URL is `127.0.0.1`, while canonical/schema/offer URLs use `wrydeco.myshopify.com`; verify intended production domain before launch/import validation.
- Schema description contains HTML-derived whitespace and entity remnants in raw JSON-LD.

## Breadcrumbs And Internal Links

- Breadcrumb trail: no explicit breadcrumb nav detected.
- Product eyebrow/collection link: Corner Bookshelf -> /collections/corner-bookshelf
- Consultation/customization links:
  - /pages/customization
  - /pages/customization#custom-inquiry__story-telling
- Artisan/profile link:
  - /pages/product-author/khoi-hoang
- Related product links visible:
  - Handcrafted Natural Wood Corner Tree Bookshelf Whispering -> /products/handcrafted-natural-wood-corner-tree-bookshelf-whisper?pr_prod_strat=collection_fallback&pr_rec_id=1f1e2a4e4&pr_rec_pid=8386253783097&pr_ref_pid=8386190180409&pr_seq=uniform
  - Handcrafted Natural Wood Corner Tree Bookshelf Crimson -> /products/handcrafted-natural-wood-corner-tree-bookshelf-crimson?pr_prod_strat=collection_fallback&pr_rec_id=1f1e2a4e4&pr_rec_pid=8386253979705&pr_ref_pid=8386190180409&pr_seq=uniform
  - Handcrafted Natural Wood Corner Tree Bookshelf -> /products/handcrafted-natural-wood-corner-tree-branch-bookshelf?pr_prod_strat=collection_fallback&pr_rec_id=1f1e2a4e4&pr_rec_pid=8386254045241&pr_ref_pid=8386190180409&pr_seq=uniform
  - Large Handcrafted Tree Branch Corner Bookshelf for Nursery -> /products/large-wood-tree-branch-corner-bookshelf-for-nursery?pr_prod_strat=collection_fallback&pr_rec_id=1f1e2a4e4&pr_rec_pid=8386254176313&pr_ref_pid=8386190180409&pr_seq=uniform
  - Large Handcrafted Tree Branch Corner Bookshelf for Nursery -> /products/sculptural-tree-branch-corner-bookshelf-for-nursery?pr_prod_strat=collection_fallback&pr_rec_id=1f1e2a4e4&pr_rec_pid=8386254307385&pr_ref_pid=8386190180409&pr_seq=uniform
  - Large Handcrafted Tree Branch Corner Bookshelf for Nursery -> /products/handcrafted-tree-branch-corner-bookshelf-nursery?pr_prod_strat=collection_fallback&pr_rec_id=1f1e2a4e4&pr_rec_pid=8386355462201&pr_ref_pid=8386190180409&pr_seq=uniform
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
- "27+ YEARS OF CRAFTSMANSHIP" should be substantiated for the named artisan/brand.
- "Made entirely by hand" and "Every WRYDECO piece can be tailored to you" are broad claims and should match actual production and customization constraints.
- "Dimensions can be tailored to fit exactly where it will live" is a potentially over-precise customization promise.
- Delivery timeline claims should be checked against operational reality:
  - First 24 hours contact
  - Day 2-7 sketch/sample
  - Next 5 days finishing
  - Next 7-10 days shipping coordination
- Refund/final-sale language should align exactly with active store policy.
- Material claims include natural wood, solid wood, organic grain, knots, tonal variation, oiled/matte finish care. These should be true for this product and each finish option.
- Mounting/load guidance is deferred to delivered piece; acceptable, but product page itself does not give load capacity or mounting hardware specifics.

## Generic / Duplicated / Awkward Copy Found

- Product title/H1 wording is awkward: "Book Shelf" should likely be "Bookshelf"; "Corner Bookcase" duplicates the bookshelf concept.
- Meta description is readable but generic and formulaic: "Transform your living room..." / "displays art, plants, and books elegantly."
- Description uses broad lifestyle phrasing that may be duplicated across similar PDPs:
  - "functional piece of art"
  - "more intentional, visually warm place to live"
  - "far more special than ordinary wall storage"
  - "expressive, elevated, and beautifully arranged"
  - "gallery-like presence"
  - "grounded, artful mood"
  - "organic modern, Japandi, wabi-sabi, farmhouse, woodland, rustic, and collected-vintage styling"
- Related products show repeated/similar names, especially multiple "Large Handcrafted Tree Branch Corner Bookshelf for Nursery" cards.
- Hidden dimensions text extraction shows "Available sizesPick your size..." without spacing.
- Finish UI says "Custom color" while the variant/schema value is "Custom"; the custom input text says "Custom Wood Finish."
- All gallery image alts are identical and do not describe individual image angles/details.

## Overall Verdict

Verdict: NEEDS REVIEW

Reason:
- Product UX appears intact enough for a BEFORE snapshot and pilot-copy update: page renders, H1/price/options/gallery/CTA are present, variant changes update price and variant id, Add to Cart appears enabled, and internal links spot-checked return 200.
- Content and schema need review before scaling: title wording is awkward, copy contains broad/generic claims, visible reviews are not represented in ProductGroup structured data, related product links use tracking parameters, and some claims should be substantiated before import.

Recommended fixes before updating this PDP:
1. Rewrite product title/H1 and SEO title to use cleaner wording, likely "Handcrafted Tree Branch Corner Bookshelf" or another approved target term, while preserving the URL handle unless intentionally changed.
2. Rewrite meta description to be more product-specific and less generic.
3. Tighten product description around verifiable features: corner placement, tree-branch silhouette, dimensions, finish options, made-to-order process, and intended use.
4. Verify or soften claims for free worldwide shipping, 1-year warranty, 27+ years craftsmanship, made entirely by hand, exact customization, and delivery timelines.
5. Keep size/finish variant names, variant IDs, prices, inventory, images, and product handle unchanged during product-data update.
6. Confirm production canonical domain; local source currently uses `wrydeco.myshopify.com`.
7. Consider adding ProductGroup aggregateRating only if review data is valid and policy-compliant.
8. Improve image alt text diversity if product image metadata is part of the update scope.
9. Prefer clean related product URLs without `pr_*` parameters if theme changes are later allowed; do not handle that as part of product-data update unless specifically scoped.
