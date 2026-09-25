# WRYDECO Project Coding Guidelines

This document outlines the mandatory rules and standards that must be followed when writing code for the WRYDECO Shopify Theme.

## 1. Responsive Design (Desktop-First)

All new components and layouts must follow modern responsive design practices.

- **Skill Reference:** `.agents/skills/responsive-design`
- **Approach:** Always design and code desktop-first. Start with desktop styles and override for smaller screens using max-width breakpoints.
- **Techniques:** Utilize fluid typography, CSS Grid, Flexbox, and container queries for adaptive interfaces. Ensure touch targets are at least 44x44px.

## 2. SEO & SSR-First Coding

All code must be optimized for search engines following an Server-Side Rendering (SSR) first architecture.

- **Skill Reference:** `.agents/skills/optimize-seo-ssr-coding`
- **Approach:** SEO-critical content (product names, descriptions, main images) MUST be available in the initial server-rendered HTML. Client-side rendering is strictly for non-critical interactivity or UI enhancements.
- **Key Elements:** Maintain semantic HTML (`main`, `article`, `section`), logical heading structures (H1, H2, H3), stable canonical URLs, and optimized image SEO (proper `alt` text, formats, and lazy loading for below-the-fold content).

## 3. Styling Reference (Design System)

Maintain design consistency by strictly adhering to the defined design system tokens and components.

- **Reference File:** `assets/base.css` — this is the single source of truth for all CSS variables (colors, typography, spacing, shadows, motion).
- **Approach:** Prefer the global CSS variables defined in `assets/base.css` when they help maintain design consistency. CSS values may also be hardcoded when appropriate; using a CSS variable is not mandatory.
- **Scope:** This allowance applies across CSS files, Liquid `{% stylesheet %}` tags, and inline styles.

## 4. Business Context & Tone

The technical implementation must align with the brand's luxury positioning.

- **Reference File:** `doc/BUSINESS_CONTEXT.md`
- **Approach:** WRYDECO is a premium handcrafted natural wood furniture brand. Treat the website as a gallery of functional art.
- **Constraints:** Prioritize trust signals and consultation leads. Never use language or UI patterns that make the brand feel "budget", "mass-produced", or "discount-first". Ensure data models for products and artists match the required business specifications.

## 5. Shopify Sections Layout

- Try to maintain `display: block` for the shopify-section wrapper.
- If it is strictly necessary to change the `display` property of the shopify-section, you must ask for permission first.

## 6. Global Notifications (Toast)

- All user-facing temporary notifications, alerts, and feedback messages MUST use the global Toast component.
- **Implementation:** Do not write custom alert logic or duplicate notification UI. Always call the global JavaScript function `window.showToast({ message: '...', type: 'success|error|info', position: 'top-right|bottom-right|...', duration: 4000 })`.

## 7. Language and Localization

- All text displayed to the end user (on the website interface) must be written entirely in English.
- Strictly do not use Vietnamese or any other language for UI components (buttons, labels, placeholders, messages, etc.).

## 8. File References (Shopify Files)

- All file assets have been fully uploaded to Shopify Content > Files.
- When writing code that references a file (images, fonts, scripts, styles, etc.), always use the `file_url` filter instead of `asset_url`.
- **Exception:** `asset_url` is still correct for files that genuinely live in the theme's `assets/` folder (e.g. compiled/critical assets not managed via Shopify Files).

## 9. Icon & SVG Rendering, Creation, and Usage

- **Rendering Constraint:** When rendering icons or graphical symbols on the web interface, you MUST strictly use inline SVG code. NEVER use HTML Entities (e.g., `&#x25B6;`, `&rarr;`, etc.) for this purpose.
- **Tool Requirement:** Whenever an AI Agent needs to create an icon in the codebase, write SVG code, or source an SVG image, it MUST use the `iconify` API tool located in the `my-tools` folder.
- **Error Handling:** If an error occurs while using the Iconify API, the Agent is free to handle it, but it MUST explicitly notify the user that an error occurred during the API execution.

## 10. External API Calls & Service Architecture

- **Mandatory Rule:** When writing code that needs to call external APIs (outside standard Shopify core storefront/cart routes), developers and AI agents MUST use a centralized API Service rather than hardcoding API endpoints, domains, headers, or request configurations in individual sections, snippets, or blocks.
- **Reference Service:** `assets/api-service.js` (exposing `window.WrydecoApi`).
- **Core Endpoints & Methods Provided:**
  - `uploadCustomColorImage(file)`: Uploads custom color/finish reference images to `https://admin.wrydeco.com/api/upload-image`.
  - `submitCustomSizeRequest(payload)`: Submits quick custom size inquiries to `https://admin.wrydeco.com/api/custom-size-requests`.
  - `submitConsultation(formData, [customEndpoint])`: Submits bespoke design consultation inquiries to `https://admin.wrydeco.com/api/consultations`.
- **Rationale:** Centralizing API logic ensures maintainability, seamless scalability, unified CORS/error handling, and eliminates bug risks from fragmented hardcoded URLs across the codebase.

## 11. Cart Interaction & Drawer Architecture

- **Primary Interface:** WRYDECO strictly uses a slide-out Cart Drawer (`sections/cart-drawer.liquid`) instead of a traditional standalone cart page.
- **Global Redirect:** Direct access or navigation to `/cart` is automatically intercepted and redirected to `/collections/all` while programmatically opening the Cart Drawer (configured in `layout/theme.liquid`).
- **Implementation Standard:** Any new components, buy buttons, quick-add triggers, or cart count links MUST trigger or update the Cart Drawer directly. Do NOT create links or redirects sending users to `/cart`.

## 12. Tiered Spending Discount & Promotion System

- **Architecture:** The store implements a structured 10-tier spending discount system (`WRY100` to `WRY1000` corresponding to order subtotals from $900 to $9,900).
- **Centralized Engine:** Discount eligibility evaluation, session caching, and automated checkout application are strictly handled by `assets/wry-discount-auto-apply-v2.js` and the global customer eligibility flag `window.WrydecoCustomerDiscountEligible`.
- **Implementation Standard:** AI agents and developers must NOT create duplicate discount application scripts, hardcode conflicting promotion codes, or bypass the centralized auto-apply mechanism.

## 13. Theme Build & Release Cleanup

- **Clean Release Rule:** Before packing or archiving the theme for production upload via `compress-store-src.cmd`, all local development and test hooks (such as lead-capture popup debug toggles) MUST be thoroughly purged.
- **Execution Script:** Always ensure the test code removal script (`scripts/lead-capture-test/remove-test-src.cmd`) is invoked prior to generating uploadable zip archives to ensure debug elements never leak into production.

