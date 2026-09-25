# BUSINESS_CONTEXT.md — WRYDECO Business & Website Context

**Purpose:** Comprehensive business, functional, and architectural reference for AI Coding Agents and developers building and maintaining the WRYDECO Shopify store.

**Scope:** Brand positioning, product strategy, audience, Shopify architecture, live store routes, content data models (Products, Metaobjects, Collections), consultation service flow, external API integration, discount promotion architecture, SEO, and technical constraints.

**Out of scope:** Visual design styling rules (colors, fonts, spacing). Refer to `assets/base.css` and `CODING_RULES.md` for styling tokens and implementation standards.

---

## 1. Brand Snapshot

WRYDECO is a premium handcrafted natural wood furniture brand positioned between organic art, sculptural furniture, and luxury bespoke interiors.

**Core Tagline:**
> *Nature wrote the prologue. You write the legacy.*

WRYDECO is deliberately designed to feel less like a conventional mass-market e-commerce store and more like a curated, serene **gallery of functional wooden artworks**.

The brand sells statement pieces to high-income homeowners, collectors, interior architects, and design studios seeking material authenticity, craft narrative, distinct grain individuality, and long-term heirloom value.

---

## 2. Brand Positioning

WRYDECO rejects cheap, mass-market, flat-pack, or discount-first furniture archetypes.

### Strategic Positioning:
- **Luxury artisan furniture**: Solid wood exclusively; no cheap veneers, composites, or flimsy hardware.
- **Handcrafted natural solid wood**: Embracing natural grain lines, live edges, organic curves, and burls.
- **Bespoke and made-to-order capability**: Flexible sizing, customized finishes, and tailored space adaptations.
- **Organic & sculptural product DNA**: Furniture inspired by natural tree branches, flowing water, and biophilic shapes.
- **Gallery-style product storytelling**: Highlighting each item as an art piece attributed to its creator.
- **Dual-conversion engine**: Direct e-commerce purchase (DTC) paired with high-touch consultation lead capture.

### Key Differentiators:
- High price tier ($1,000 to $10,000+).
- Authentic workshop and maker storytelling.
- Two-tier product naming (Artwork Title vs Commercial/SEO Title).
- Private design consultation and custom sizing support.

---

## 3. Business Goals

The website and theme must support these core business goals:
1. **Instill deep trust** for a high-ticket DTC furniture brand through transparent workshop evidence and verified craftsmanship.
2. **Drive high conversion** via two balanced paths: direct checkout for ready designs and consultation inquiries for custom/high-ticket commissions.
3. **Present products as collectible functional art**, elevating perception above commodity retail.
4. **Clarify craftsmanship, materials, dimensions, and bespoke options** with rich interactive media and detailed specifications.
5. **Enable intuitive discovery** across collections, rooms, wood species, finishes, and individual artisans.
6. **Support trade and designer scaling** (interior designers, boutique hospitality, custom residential projects).
7. **Maintain a lean, robust Shopify Liquid architecture** supported by a centralized backend API for custom requests.

---

## 4. Target Audiences

### 4.1 Primary: High-Income DTC Homeowners
- **Profile:** Age ~28–55; upper-middle to high-income; owners of custom homes, penthouses, or luxury apartments.
- **Mindset:** Value craftsmanship, organic materials, tactile warmth, and uniqueness over mass production.
- **Conversion triggers:**
  - Gallery lifestyle photography and close-up video of handcrafting.
  - Transparent dimensions, wood types, and freight packaging proof.
  - Responsive consultation support (Email, Phone, WhatsApp) before committing to a purchase.

### 4.2 Secondary: Interior Designers & Studios
- **Profile:** Residential and boutique commercial interior designers seeking statement pieces for client projects.
- **Needs:** Custom sizing feasibility, finish swatches, technical dimensions, reliable lead times, and trade-friendly communication.

### 4.3 Tertiary: Art Furniture Collectors
- **Profile:** Connoisseurs seeking functional sculptures.
- **Needs:** Artist attribution, piece inspiration narrative, limited craft volume, and distinct material character.

---

## 5. Product Strategy & Categories

### 5.1 Product DNA
- Organic form, sculptural contours, solid timber (Walnut, Oak, Ash, Cherry, Maple).
- Finishes: Natural Oil, Smoked, Dark Brown, Matte Black.
- Craft features: Live Edge, Curved Edge, Hand-Carved Joinery, Brass Inlay.

### 5.2 Hero Category: Handcrafted Tree-Branch Furniture
- Visually striking, emotionally resonant statement pieces for living rooms, libraries, and entryways.
- Includes freestanding tree bookcases, corner tree shelves, and wall-mounted branch displays.
- Price tier: ~$1,000 – $6,000.

### 5.3 Supporting Category: Sculptural Tables, Beds & Accents
- Organic wave solid wood coffee tables, live-edge root tables, platform beds with branch canopy headboards, and floor sculptures.
- Price tier: ~$1,500 – $8,000+.

### 5.4 Bespoke Commissions
- Custom dimensions, adapted shelf angles, special wood finishes, and architectural integration.
- Custom pricing quoted individually via consultation.

---

## 6. Live Store Structure & URL Routes

The WRYDECO storefront operates on Shopify's native JSON template architecture with specialized custom sections:

### 6.1 Core Storefront Routes
| Route | Template File | Business Purpose |
| :--- | :--- | :--- |
| `/` | `templates/index.json` | Brand story, curated pieces, workshop proof, consultation CTA, reviews |
| `/collections/all` | `templates/collection.json` | Complete catalog of available pieces with sorting and filtering |
| `/collections/[handle]` | `templates/collection.json` | Dedicated category collections (e.g. `tree-bookshelves`, `coffee-tables`) |
| `/products/[handle]` | `templates/product.json` | Comprehensive product gallery, artist attribution, customizer, buy box |
| `/pages/customization` | `templates/page.customization.json` | Bespoke consultation flow, 5-step process, custom inquiry form |
| `/pages/about-us` | `templates/page.about-us.json` | Brand heritage, artisan team, sustainable sourcing, Vietnamese craft |
| `/pages/showroom` | `templates/page.showroom.json` | Visual space gallery showcasing pieces in real interior settings |
| `/pages/care-guide` | `templates/page.care-guide.json` | Comprehensive maintenance guide for natural wood furniture |
| `/pages/faq` | `templates/page.faq.json` | In-depth customer care, shipping, transit protection, warranty, returns |
| `/pages/contact` | `templates/page.contact.json` | Contact form, hotline, email, support hours, and US business address |
| `/pages/product-author/[handle]` | `templates/metaobject/product_author.json` | Dedicated biography, philosophy, and works of an individual artisan |
| `/blogs/[blog-handle]` | `templates/blog.json` | Editorial blogs (`news`, `buying-guides`, `design-comparisons`) |
| `/blogs/[blog-handle]/[slug]` | `templates/article.json` | In-depth editorial guide, styling tips, craftsmanship breakdowns |
| `/apps/page/wishlist` | `snippets/wishlist-page-custom.liquid` | Customer wishlist page for saving favorite gallery pieces |

### 6.2 Rooms Navigation
In addition to traditional categories, the header navigation features a dedicated **Rooms Navigation** to guide homeowners by space:
1. **Living Room** (Coffee tables, end tables, floor sculptures, floating shelves, mirrors)
2. **Bedroom** (Platform beds with headboards, nightstands, wall mirrors)
3. **Kitchen & Dining** (Wall-mounted wine racks, rustic wine displays, fruit bowls)
4. **Home Office & Library** (Freestanding tree bookshelves, curved modern bookcases, corner shelves)
5. **Nursery & Kids' Room** (Whimsical tree bookshelves, mushroom shelves)

### 6.3 Policy Routes
- `/policies/shipping-policy` — Freight delivery, wood crating details, transit timelines.
- `/policies/refund-policy` — Transit damage claims, inspection window, returns.
- `/policies/terms-of-service` — Made-to-order commitments, natural wood grain variance.
- `/policies/privacy-policy` — Customer data protection and encryption.
- `/policies/legal-notice` & `/pages/warranty-policy` — Business disclosures and warranty terms.

---

## 7. Homepage Architecture & Experience Flow

The homepage (`templates/index.json`) is structured as an editorial gallery experience:

1. **Announcement Bar:** Free US freight shipping notification and policy link.
2. **Hero Banner (`hero-banner`):**
   - Brand statement: *"Handcrafted Sculptural Solid Wood Furniture"*.
   - Subtext highlighting natural grain and made-to-order adaptability.
   - Primary CTA: *Explore Now* (`/collections/all`) & *Book Consultation* (`/pages/customization`).
   - Trust highlights: Solid Wood Only, Made to Measure, 4.9/5 Rating.
3. **Credibility Record:** 400+ Homes Styled, 372 Verified Reviews, 4.7 Average Rating, 27+ Years Craft.
4. **Welcome Video (`welcome-video`):** Highlighting the journey *"From Nature to Artful Living"*.
5. **Curated Collections (`shop-collections`):** Visual navigation across 5 core categories.
6. **Signature Pieces (`signature-pieces`):**
   - 12 flagship artworks displayed with Artwork Name, Artisan Attribution (`by [Artist]`), starting price, Wishlist toggle, and quick "Customize" trigger.
7. **Custom Order Process (`made-to-order-steps`):**
   - Clear **5-step transparent workflow**:
     - *01. Book Consultation* — Submit space photos & requirements.
     - *02. Review Scope & Quote* — Agree on dimensions, species, and quote.
     - *03. Approve & Pay* — Formalize order and production queue.
     - *04. Proof, Craft & Confirm* — Workshop shaping with pre-shipment photo approval.
     - *05. Pack & Ship* — Heavy-duty timber crating and insured freight delivery.
8. **Workshop Evidence (`workshop-evidence`):** Real-world video/photo proof of handcrafting, assembly, and crating protection.
9. **Materials & Personalization (`materials-craftsmanship`):** Species selection, wood finishes, and edge profiles.
10. **Design Consultation Showcase (`styling-consultation`):** Introduction of Lead Consultant Mr. Dan, response SLA (24–48h).
11. **Meet the Makers (`meet-the-makers`):** Carousel featuring the 6 official studio artisans.
12. **Client Reviews (`client-reviews`):** Verified customer reviews with home installation photos.
13. **Journal & Wood Care (`home-blog`):** Editorial articles linking design questions to product solutions.
14. **FAQ Snapshot (`faq-editorial-page` & `faq-editorial-trust`):** Quick answers to high-consideration shipping and care questions.

---

## 8. Artisans & Makers Data Architecture

WRYDECO features **6 official master artisans** modeled as Shopify Metaobjects (`type: product_author`):

| Artisan Name | Handle / Slug | Title / Specialty | Metaobject GID |
| :--- | :--- | :--- | :--- |
| **Khoi Hoang** | `khoi-hoang` | Principal Artisan / Curved Forms | `gid://shopify/Metaobject/194643198009` |
| **Lam Nguyen** | `lam-nguyen` | Master Wood Sculptor / Intricate Carving | `gid://shopify/Metaobject/194643165241` |
| **Nhan Pham** | `nhan-pham` | Bespoke Commission Director / Floor Sculptures | `gid://shopify/Metaobject/195646947385` |
| **Nhien Le** | `nhien-le` | Organic Form Specialist / Whimsical Tree Shelves | `gid://shopify/Metaobject/195647275065` |
| **Son Tran** | `son-tran` | Natural Grain Curator / Raw Timber Selection | `gid://shopify/Metaobject/195647701049` |
| **Tin Dang** | `tin-dang` (or `alex-nguyen`) | Master Surface Finisher / Tree Bookshelves | `gid://shopify/Metaobject/194643296313` |

### Two-Tier Product Naming Rule:
1. **Artwork Name (Tên tác phẩm nghệ thuật):**
   - Evocative, gallery-style title displayed prominently on cards and product headers (e.g., *Canyon Spirit Arbor*, *Golden Bough Bookshelf*, *The Infinity Wave Table*).
   - Displayed together with artisan attribution: `by [Artist Name]`.
2. **Commercial / SEO Title (Tên thương mại/SEO):**
   - Keyword-optimized title used for page meta titles, search engine results, Google Merchant Center, and catalog indexing (e.g., *Handcrafted Natural Wood Corner Tree Branch Bookshelf*).

---

## 9. Product Page Conversion Architecture

The product detail template (`templates/product.json`) provides a high-converting, trust-rich layout:
- **Media Gallery:** Multi-angle lifestyle photography, close-up grain shots, zoom capability, and process video embeds.
- **Dual Title & Maker Attribution:** Prominent artwork name, linked author badge leading to the maker's profile.
- **Variant Picker:** Swatches for wood finishes (Natural, Walnut Tone, Warm Oak, Dark Rustic) and dimensional variants.
- **Dual Conversion Actions:**
  - Primary button: *Add to Cart* / *Buy It Now* for standard specifications.
  - Secondary button: *Quick Custom Size* / *Request Customization* (`snippets/quick-customize.liquid`) for modified dimensions.
- **Sticky Buy Bar:** Mobile and desktop sticky bar ensuring friction-free checkout or inquiry.
- **Trust Elements:**
  - Wood authenticity badge (100% Solid Natural Wood).
  - Free insured freight shipping badge.
  - White-glove crating guarantee.
- **Accordions & Rich Specs:** Detailed dimensions, assembly guidelines, wood care, warranty, and freight lead time.
- **Social Proof:** Verified customer reviews and related pieces from the same collection or maker.

---

## 10. External API & Service Architecture

To maintain high performance and avoid hardcoded endpoints, all custom requests route through a centralized client service ([`assets/api-service.js`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/assets/api-service.js) via `window.WrydecoApi`) communicating with the dedicated backend server ([`auto/module-3`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/auto/module-3) at `admin.wrydeco.com`):

### 10.1 Key Endpoints
1. **`POST /api/consultations`**
   - **Content-Type:** `multipart/form-data`
   - **Payload:** `name`, `phone_or_email`, `message`, `consultation_time` (optional), and multiple room/space attachments (`JPEG`, `PNG`, `PDF` up to 10MB each, total max 30MB).
   - **Response:** `{ "success": true }`.
2. **`POST /api/custom-size-requests`**
   - **Content-Type:** `multipart/form-data`
   - **Payload:** `product_id`, `product_handle`, `product_name`, `custom_size_description`, `customer_contact`.
   - **Response:** `{ "success": true, "id": ..., "message": "Custom size request received." }`.
3. **`POST /api/upload-image`**
   - **Payload:** Single image file for customer reference finishes.

### 10.2 Notification Architecture
All client-side user feedback, form submission responses, and cart alerts must strictly use the unified toast system:
```javascript
window.showToast({
  message: "Your consultation request has been submitted successfully!",
  type: "success", // 'success' | 'error' | 'info'
  position: "top-right",
  duration: 4000
});
```

---

## 11. Tiered Spending Discount Promotion Architecture

While maintaining luxury positioning, WRYDECO utilizes a structured **Tiered Spending Discount Architecture** to reward high-order volume without appearing "cheap":

### Fixed Tiered Codes:
| Code | Discount Amount | Minimum Order Subtotal |
| :--- | :--- | :--- |
| `WRY100` | $100 off | $900 |
| `WRY200` | $200 off | $1,900 |
| `WRY300` | $300 off | $2,900 |
| `WRY400` | $400 off | $3,900 |
| `WRY500` | $500 off | $4,900 |
| `WRY600` | $600 off | $5,900 |
| `WRY700` | $700 off | $6,900 |
| `WRY800` | $800 off | $7,900 |
| `WRY900` | $900 off | $8,900 |
| `WRY1000` | $1,000 off | $9,900 |

### Promotion Implementation:
- **Lead Capture Popup (`snippets/lead-capture-popup.liquid`):** Offers first-time visitors a welcome tiered incentive in exchange for email newsletter subscription.
- **Auto-Apply Engine (`assets/wry-discount-auto-apply-v2.js`):** Automatically evaluates cart value in real time and applies the highest eligible discount tier directly at checkout.

---

## 12. SEO & SSR-First Standards

All pages are optimized for search engines via Server-Side Rendering (Liquid SSR):
- **Canonical URLs:** Dynamically generated to prevent duplicate content across collection handles.
- **Structured Data (JSON-LD):**
  - `Organization` & `WebSite` schemas on the index page.
  - `Product` schema (with price, currency, availability, reviews, and high-res image list) on product pages.
  - `BreadcrumbList` on catalog and article pages.
  - `FAQPage` schema on FAQ sections.
  - `Article` schema on blog posts.
- **Image Optimization:** Explicit `alt` descriptions on all lifestyle and product photography; `file_url` filter utilized for CDN-hosted media assets.

---

## 13. AI Agent Operating Guidelines

When developing or modifying code in this repository:
1. **Preserve the Gallery Aesthetic:** Keep typography elegant, whitespace generous, and avoid garish badges, flashing countdown timers, or low-tier ecommerce clutters.
2. **Respect the Dual-Title Model:** Never overwrite an artwork title with a generic SEO name on user-facing cards.
3. **Adhere to `CODING_RULES.md`:**
   - Desktop-first responsive layout (touch targets $\ge 44\times 44\text{px}$).
   - Keep `.shopify-section` wrappers as `display: block`.
   - Use `window.WrydecoApi` for backend calls.
   - Use `window.showToast` for all notification dialogs.
   - User-facing text must be 100% in English.
   - Use inline SVGs via the internal Iconify tool (`my-tools/iconify`).
