# WRYDECO Project Coding Guidelines

This document outlines the mandatory rules and standards that must be followed when writing code for the WRYDECO Shopify Theme.

## 1. Responsive Design (Mobile-First)

All new components and layouts must follow modern responsive design practices.

- **Skill Reference:** `.agents/skills/responsive-design`
- **Approach:** Always design and code mobile-first. Start with mobile styles and enhance for larger screens using content-based breakpoints.
- **Techniques:** Utilize fluid typography, CSS Grid, Flexbox, and container queries for adaptive interfaces. Ensure touch targets are at least 44x44px.

## 2. SEO & SSR-First Coding

All code must be optimized for search engines following an Server-Side Rendering (SSR) first architecture.

- **Skill Reference:** `.agents/skills/optimize-seo-ssr-coding`
- **Approach:** SEO-critical content (product names, descriptions, main images) MUST be available in the initial server-rendered HTML. Client-side rendering is strictly for non-critical interactivity or UI enhancements.
- **Key Elements:** Maintain semantic HTML (`main`, `article`, `section`), logical heading structures (H1, H2, H3), stable canonical URLs, and optimized image SEO (proper `alt` text, formats, and lazy loading for below-the-fold content).

## 3. Styling Reference (Design System)

Maintain design consistency by strictly adhering to the defined design system tokens and components.

- **Main Design System:** `doc/design-system/` folder. Từ bây giờ trở đi, folder này sẽ là design system chính của project.
- **Reference File:** `assets/base.css` (để tham khảo các biến cơ bản, tuy nhiên cần ưu tiên đối chiếu với `doc/design-system/`).
- **Approach:** All styling must reference the global CSS variables and components defined in the design system. Do not use hardcoded hex codes, pixel values for spacing/radius, or arbitrary font sizes.
- **Scope:** This rule applies across all CSS files, Liquid `{% stylesheet %}` tags, and inline styles.

## 4. Business Context & Tone

The technical implementation must align with the brand's luxury positioning.

- **Reference File:** `doc/BUSINESS_CONTEXT.md`
- **Approach:** WRYDECO is a premium handcrafted natural wood furniture brand. Treat the website as a gallery of functional art.
- **Constraints:** Prioritize trust signals and consultation leads. Never use language or UI patterns that make the brand feel "budget", "mass-produced", or "discount-first". Ensure data models for products and artists match the required business specifications.

## 5. Shopify Sections Layout

- Cố gắng giữ shopify-section có `display: block`
- Khi bắt buộc thay đổi `display` của shopify-section thì phải hỏi trước.
