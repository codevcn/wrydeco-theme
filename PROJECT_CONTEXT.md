# PROJECT_CONTEXT.md — WRYDECO Master Project Reference

> **Quick Summary for AI Agents & Developers:**  
> This file is the single comprehensive source of truth for the **WRYDECO** Shopify store project. Read this file first to understand the entire business context, brand positioning, product architecture, design system, coding guidelines, external APIs, and operational workflows without needing to scan hundreds of codebase files or crawl the live website.

---

## 1. Brand Snapshot & Business Core

### 1.1 Brand Identity & Tagline
- **Brand Name:** WRYDECO (`wrydeco.myshopify.com` / `wrydeco.com`)
- **Brand Tagline:**
  > *Nature wrote the prologue. You write the legacy.*
- **Core Concept:** WRYDECO is positioned between organic art, sculptural woodwork, and bespoke luxury interior architecture. The website is deliberately designed as a **serene, curated gallery of functional wooden artworks** rather than a conventional commercial furniture shop.
- **Tone of Voice:** Premium, poetic yet grounded, calm, confident, craft-centered, and deeply trustworthy. Words to avoid: *cheap, budget, discount-first, mass-produced, factory, fast furniture*.

### 1.2 Target Audiences
1. **High-Income DTC Homeowners (Primary):** Discerning homeowners looking for heirloom statement pieces with material authenticity, unique wood grain, and custom sizing options.
2. **Interior Designers & Studios (Secondary):** Trade professionals requiring bespoke sizing, custom finish tailoring, transparent lead times, and white-glove packaging.
3. **Art Furniture Collectors (Tertiary):** Buyers valuing individual artisan attribution, sculptural rarity, and organic live-edge individuality.

### 1.3 Strategic Business Model (Dual-Conversion Engine)
WRYDECO converts traffic through two parallel, equally critical paths:
1. **Direct E-commerce (DTC):** For standard-specification pieces (Add to Cart / Buy Now).
2. **High-Touch Bespoke Consultation:** For custom dimensions, adapted spatial layouts, or commissioned work (Book Consultation / Quick Custom Size).

### 1.4 Product Catalog Strategy & Hero Categories
- **Hero Category: Handcrafted Tree-Branch Furniture:** Freestanding tree bookshelves, wall-mounted branch shelves, corner tree shelves, and branching displays ($1,000 – $6,000).
- **Supporting Sculptural Furniture:** Organic wave oak coffee tables, live-edge root centerpieces, platform beds with branch canopy headboards, tall carved floor sculptures, and architectural wine racks ($1,500 – $8,000+).
- **Bespoke Commissions:** Fully tailored measurements, finish matching, and room integrations ($2,000 – $10,000+).
- **Live Catalog Size:** 93 live products organized into 35 public automated collections.

### 1.5 Two-Tier Product Naming Architecture
To preserve the gallery aesthetic while maximizing commercial search visibility:
- **Tier 1: Artwork Title (Tên tác phẩm nghệ thuật):** Displayed prominently on cards, banners, and product hero blocks together with the maker's attribution (e.g. *Canyon Spirit Arbor*, *The Golden Bough Bookshelf*, *The Infinity Wave Table* by *Khoi Hoang*).
- **Tier 2: Commercial / SEO Title (Tên thương mại/SEO):** Descriptive, keyword-rich title used for HTML `<title>`, Open Graph, Google Merchant Center, product feeds, and search indexing (e.g. *Handcrafted Natural Wood Corner Tree Branch Bookshelf*).

### 1.6 Official Master Artisans (Shopify Metaobjects)
The studio features **6 official master artisans** modeled as Shopify Metaobjects (`type: product_author`):
1. **Khoi Hoang** (`khoi-hoang`) — *Principal Artisan* (Curved lines & live-edge harmony)
2. **Lam Nguyen** (`lam-nguyen`) — *Master Wood Sculptor* (Intricate structural shaping)
3. **Nhan Pham** (`nhan-pham`) — *Bespoke Commission Director* (Large-scale installations & sculptures)
4. **Nhien Le** (`nhien-le`) — *Organic Form Specialist* (Whimsical tree shelves & mushroom shapes)
5. **Son Tran** (`son-tran`) — *Natural Grain Curator* (Raw timber selection & grain reading)
6. **Tin Dang** (`tin-dang` / `alex-nguyen`) — *Master Surface Finisher* (Multi-tier tree bookshelves)

*(Detailed reference: [doc/BUSINESS_CONTEXT.md](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/doc/BUSINESS_CONTEXT.md))*

---

## 2. Project Architecture & Directory Layout

```
.
├── admin/               # Admin token tools and Shopify GraphQL data cleanup scripts
├── assets/              # Core CSS, global JS services (api-service.js, base.css, toast.js, etc.)
├── auto/                # Automation modules (FastAPI backend, review generator, Amazon sync)
│   ├── module-1/        # Amazon product data extraction and rich-media pipeline
│   ├── module-3/        # Dedicated FastAPI backend server (admin.wrydeco.com)
│   └── module-4/        # AI-driven human-like product review generation engine
├── blocks/              # Reusable Shopify theme blocks (group.liquid, text.liquid)
├── config/              # Global theme settings schema & presets (settings_schema.json)
├── doc/                 # Business requirements, API documentation, room mappings, guidelines
│   ├── BUSINESS_CONTEXT.md # Master business reference document
│   ├── WEB-REQUIREMENTS.md # Original UI/UX specifications
│   ├── consultation-service-flow.md # Deep dive into bespoke consultation process
│   └── temp-server-api-doc/ # Endpoints documentation for consultations & custom size
├── extensions/          # Shopify Apps / Checkout UI extensions (product-note-checkout)
├── layout/              # Top-level page wrappers (theme.liquid, password.liquid)
├── locales/             # Internationalization dictionaries (en.default.json)
├── my-tools/            # Internal developer tooling (iconify MCP Python server)
├── scripts/             # Local developer lifecycle scripts (lead-capture test hooks)
├── sections/            # 60 modular, customizable Shopify Liquid sections
├── snippets/            # 43 reusable Liquid components, popups, and SEO helpers
└── templates/           # 20 JSON templates mapping sections to pages
```

---

## 3. Storefront Routes & User Navigation

### 3.1 Live URL Routing Map
| Page Type | Storefront URL | Template / Section Implementation |
| :--- | :--- | :--- |
| **Homepage** | `/` | [templates/index.json](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/templates/index.json) (14 curated editorial sections) |
| **Catalog / All** | `/collections/all` | [templates/collection.json](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/templates/collection.json) (Filtered product grid) |
| **Collection Detail** | `/collections/[handle]` | [templates/collection.json](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/templates/collection.json) (`tree-bookshelves`, `coffee-tables`, etc.) |
| **Product Detail** | `/products/[handle]` | [templates/product.json](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/templates/product.json) (Gallery, maker badge, specs, buy box) |
| **Bespoke Service** | `/pages/customization` | [templates/page.customization.json](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/templates/page.customization.json) (Consultation brief form) |
| **Brand Story** | `/pages/about-us` | [templates/page.about-us.json](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/templates/page.about-us.json) (Heritage, artisans, sustainability) |
| **Visual Showroom** | `/pages/showroom` | [templates/page.showroom.json](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/templates/page.showroom.json) (Interactive space showcase) |
| **Care Guide** | `/pages/care-guide` | [templates/page.care-guide.json](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/templates/page.care-guide.json) (Solid wood preservation & cleaning) |
| **Customer FAQ** | `/pages/faq` | [templates/page.faq.json](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/templates/page.faq.json) (Shipping, crating, warranty, returns) |
| **Contact Us** | `/pages/contact` | [templates/page.contact.json](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/templates/page.contact.json) (Inquiry form, US office address, hotline) |
| **Artisan Profile** | `/pages/product-author/[handle]` | [templates/metaobject/product_author.json](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/templates/metaobject/product_author.json) (Bio & works) |
| **Blog & Guides** | `/blogs/[blog-handle]/[slug]` | [templates/article.json](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/templates/article.json) (`news`, `buying-guides`, `design-comparisons`) |
| **Customer Wishlist**| `/apps/page/wishlist` | Rendered via [snippets/wishlist-page-custom.liquid](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/snippets/wishlist-page-custom.liquid) |

### 3.2 Header Rooms Navigation
A dedicated category navigation bar guides visitors by residential space:
- **Living Room** (Coffee tables, end tables, floor sculptures, floating shelves)
- **Bedroom** (Platform beds with branch headboards, bedside nightstands, wall mirrors)
- **Kitchen & Dining** (Wall-mounted wine racks, rustic wine shelves, fruit bowls)
- **Home Office & Library** (Standing tree bookshelves, modern curved bookcases, corner units)
- **Nursery & Kids' Room** (Mushroom shelves, nature tree displays)

### 3.3 Transparent 5-Step Custom Order Process
Featured prominently across the homepage and customization page:
1. `01. Book Consultation` — Share room photos, wall dimensions, and design desires.
2. `02. Review Scope & Quote` — Discuss with design consultants via Email, Phone, or WhatsApp.
3. `03. Approve & Pay` — Finalize custom technical drawings and production schedule.
4. `04. Proof, Craft & Confirm` — Workshop handcrafting with pre-shipment photo approval.
5. `05. Pack & Ship` — Heavy-duty wooden crating and insured freight delivery to destination.

---

## 4. Design System & Visual Styling

### 4.1 Single Source of Truth: `assets/base.css`
All styling variables, tokens, and utility classes must align with `assets/base.css`.

### 4.2 Color Palette
- **Gallery White (`--color-background`):** `#FFFFFF` (Primary backdrop, clean museum feel)
- **Off-Grey Gallery Wall:** `#F9F9F9` / `#F7F2EC` (Alternating section backgrounds)
- **Earth Brown (`--color-earth-brown`):** `#2B1D0E` (Primary text, dark accents)
- **Warm Wood Tones (`--color-clay`, `--color-sand`):** Natural timber accent shades
- **Shipping Green:** `#185C3D` (Free shipping badge & trust elements)
- **Pure Red:** `#FF000D` (Subtle sale/discount highlights)

### 4.3 Typography
- **Primary Body & Headings:** `Plus Jakarta Sans`, with fallbacks to `Fraunces`, `Arial`, `sans-serif`.
- Loaded via `@font-face` in `snippets/css-variables.liquid` referencing the optimized WOFF2 asset hosted on Shopify CDN:
  ```liquid
  src: url('{{ "Plus-Jakarta-Sans.woff2" | file_url }}') format('woff2');
  ```

### 4.4 UI Principles
- **Generous Whitespace:** Spacious margins and padding to create a luxurious gallery ambiance.
- **Micro-Interactions & Hover:** Subtle scale on images, smooth tab transitions, and elegant accordions.
- **No Clutter:** Strictly no flashing countdown clocks, aggressive spin-to-win popups, or fake scarcity banners.

---

## 5. Mandatory Coding Rules (13 Core Rules)

Every developer and AI agent must strictly follow the rules in [CODING_RULES.md](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/CODING_RULES.md):

1. **Responsive Design (Desktop-First):** Always write desktop styles first, override for smaller viewports via `@media (max-width: ...)`. Touch targets must be at least $44 \times 44\text{px}$.
2. **SEO & SSR-First Architecture:** SEO-critical content (titles, descriptions, H1-H3 headings, main images, schema) MUST be rendered server-side via Liquid. Client JS is strictly for non-critical interactivity.
3. **Styling Tokens:** Prefer global CSS variables defined in `assets/base.css` to maintain brand visual consistency.
4. **Business Context & Tone:** Never implement patterns that make the brand look cheap. Strictly adhere to [doc/BUSINESS_CONTEXT.md](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/doc/BUSINESS_CONTEXT.md).
5. **Sections Layout Wrapper:** Always preserve `display: block` on the `.shopify-section` wrapper. Do NOT change it without explicit permission.
6. **Global Notifications (Toast):** All user alerts, success messages, and feedback MUST call `window.showToast({ message: '...', type: 'success|error|info', position: 'top-right', duration: 4000 })`. Never write custom alert popups.
7. **100% English Language:** All text displayed to end users must be in English. Strictly do not expose Vietnamese or placeholder text on the UI.
8. **Shopify File References (`file_url` vs `asset_url`):** Use `file_url` for assets uploaded to Shopify Files (fonts, static media). Use `asset_url` only for files residing directly inside the theme's `assets/` directory.
9. **Inline SVG via Iconify MCP Tool:** All icons must be rendered as inline SVG. NEVER use HTML Entities (e.g. `&#x25B6;`, `&rarr;`). Create/extract icons using the local Python tool in [my-tools/iconify/](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/my-tools/iconify).
10. **Centralized External API Service:** Never hardcode external API URLs across components. All external API requests must go through `assets/api-service.js` (`window.WrydecoApi`).
11. **Cart Interaction & Drawer Architecture:** WRYDECO strictly uses the slide-out Cart Drawer (`sections/cart-drawer.liquid`). Any attempt to access `/cart` is globally redirected to `/collections/all` while automatically opening the drawer. Never link directly to `/cart`.
12. **Tiered Spending Discount System:** The store features 10 tiered codes (`WRY100` to `WRY1000`). Evaluation and checkout injection are strictly managed by `assets/wry-discount-auto-apply-v2.js` and `window.WrydecoCustomerDiscountEligible`. Do not write competing discount scripts.
13. **Theme Build & Release Cleanup:** Before running `compress-store-src.cmd` to create a production theme zip, always execute `scripts/lead-capture-test/remove-test-src.cmd` to purge local test/debug elements.

---

## 6. External API Architecture & Integration

External backend capabilities are powered by a dedicated FastAPI application residing in [auto/module-3/](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/auto/module-3) deployed on the production VPS at `https://admin.wrydeco.com`.

### 6.1 Frontend Gateway: `window.WrydecoApi` ([assets/api-service.js](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/assets/api-service.js))
Exposes three standardized methods:

```javascript
// 1. Upload reference finish/color photo
const res = await window.WrydecoApi.uploadCustomColorImage(file);

// 2. Submit quick custom size inquiry from product page
const res = await window.WrydecoApi.submitCustomSizeRequest({
  product_id: "8355804577849",
  product_handle: "custom-handcrafted-natural-wood-corner-tree-bookshelf",
  product_name: "Custom Handcrafted Natural Wood Corner Tree Bookshelf",
  custom_size_description: "Height 84 inches, depth 14 inches",
  customer_contact: "client@example.com"
});

// 3. Submit bespoke consultation request with space attachments
const formData = new FormData();
formData.append("name", "Michael Scott");
formData.append("phone_or_email", "michael@dundermifflin.com");
formData.append("message", "Looking for a custom branch bookshelf for my living room wall.");
formData.append("file1", fileInput.files[0]);
const res = await window.WrydecoApi.submitConsultation(formData);
```

### 6.2 Endpoint Specifications
- **`POST /api/consultations`:** Accepts `multipart/form-data`. Supports multiple files (JPEG, PNG, PDF up to 10MB each, total max 30MB). Returns `{ "success": true }`.
- **`POST /api/custom-size-requests`:** Accepts `multipart/form-data`. Returns `{ "success": true, "id": ..., "message": "Custom size request received." }`.
- **`POST /api/upload-image`:** Accepts image file, stores media, and returns public URL.

---

## 7. Tiered Spending Discounts & Lead Capture

WRYDECO incentivizes high average order value (AOV) through tiered fixed discounts without cheapening brand perception:

| Discount Code | Discount Value | Minimum Subtotal |
| :---: | :---: | :---: |
| `WRY100` | $100 | $900 |
| `WRY200` | $200 | $1,900 |
| `WRY300` | $300 | $2,900 |
| `WRY400` | $400 | $3,900 |
| `WRY500` | $500 | $4,900 |
| `WRY600` | $600 | $5,900 |
| `WRY700` | $700 | $6,900 |
| `WRY800` | $800 | $7,900 |
| `WRY900` | $900 | $8,900 |
| `WRY1000` | $1,000 | $9,900 |

- **Lead Capture Modal (`snippets/lead-capture-popup.liquid`):** Collects customer email upon initial browsing and activates discount eligibility.
- **Auto-Apply Engine (`assets/wry-discount-auto-apply-v2.js`):** Listens to Cart Drawer changes, automatically calculates the optimal tier, and applies the code directly to checkout.

---

## 8. Development & Build Lifecycle

### 8.1 Local Theme Development
Run the development command from root:
```cmd
dev.cmd
```
- Automatically triggers `scripts/lead-capture-test/init-test-src.cmd` to inject test debug buttons.
- Launches Shopify CLI dev server via `dev_wrapper.py` (`shopify theme dev --store wrydeco.myshopify.com`).
- Generates an ASCII **QR code in the terminal** for immediate real-device mobile previewing.

### 8.2 Building & Packaging for Production
When ready to release an updated theme package:
```cmd
compress-store-src.cmd
```
1. Executes `scripts/lead-capture-test/remove-test-src.cmd` to strip dev test code.
2. Automatically reads and bumps the semantic version in `src-version.json` (e.g. `3.7.8` $\rightarrow$ `3.7.9`).
3. Deletes older zip archives and archives the production directories (`assets`, `blocks`, `config`, `layout`, `locales`, `sections`, `snippets`, `templates`) into `Skeleton-[VERSION]-upload.zip`.

### 8.3 Pushing Changes to Shopify Store
```cmd
push-theme.cmd
```
Directly pushes local theme code to `wrydeco.myshopify.com` via Shopify CLI.

---

## 9. Critical Caveats & AI Anti-Patterns

When interacting with or generating code for WRYDECO:

| ❌ NEVER DO THIS | ✅ ALWAYS DO THIS INSTEAD |
| :--- | :--- |
| Never create navigation links to `/cart` | Always trigger the slide-out Cart Drawer (`[data-cart-drawer-open]`) |
| Never hardcode API URLs like `https://admin.wrydeco.com/...` in components | Always use `window.WrydecoApi` methods from `assets/api-service.js` |
| Never use HTML entities (`&#x25B6;`, `&rarr;`) for UI arrows/icons | Always render inline SVGs obtained via `my-tools/iconify` |
| Never display raw Vietnamese text to end users | Ensure 100% of user-facing UI labels, placeholders, and buttons are in natural English |
| Never overwrite an artist's Artwork Name with a generic SEO product title | Display the evocative Artwork Name prominently with `by [Artist Name]` attribution |
| Never alter `.shopify-section { display: block; }` | Keep standard section block formatting to avoid breaking Shopify grid layouts |
| Never use custom `alert()` or bespoke popup code for user feedback | Always call `window.showToast({ message, type })` |
| Never package theme zip files manually | Always run `compress-store-src.cmd` so test code is purged and versions bump cleanly |
