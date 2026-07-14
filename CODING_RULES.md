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
- **Approach:** All styling must reference the global CSS variables defined in `assets/base.css`. Do not use hardcoded hex codes, pixel values for spacing/radius, or arbitrary font sizes.
- **Scope:** This rule applies across all CSS files, Liquid `{% stylesheet %}` tags, and inline styles.

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

## 9. SVG Creation and Usage

- Whenever an AI Agent needs to create an SVG image or write SVG code, it MUST use the `iconify` MCP server located in the `my-tools` folder.
- **Error Handling:** If an error occurs while using the MCP, the Agent is free to handle it, but it MUST explicitly notify the user that an error occurred during the MCP execution.

## 10. Icon Creation

- If an AI Agent needs to create an icon in the codebase, it MUST use inline SVG code.
- This SVG code MUST be sourced using Iconify, strictly adhering to Rule 9.
