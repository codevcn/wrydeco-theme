---
name: ssr-responsive-desktop-first
description: Use when building or reviewing responsive server-rendered websites with desktop-first CSS. For HTML templates, Liquid, Blade, Twig, Jinja, ERB, EJS, Handlebars, PHP templates, and other SSR template systems. Not for React, Next.js, Vue, Nuxt, or SPA-first UI.
---

# SSR Responsive Desktop-First Skill

## Core Directive

Build responsive websites where the **initial HTML is rendered on the server**, the **desktop layout is the base design**, and smaller screens are handled by clear CSS overrides.

Use JavaScript only for progressive enhancement. The page must remain readable, crawlable, and usable before client-side JavaScript runs.

## When to Use

Use this skill for:

- SSR websites and template-based pages
- Shopify Liquid themes
- Laravel Blade, Rails ERB, Django/Jinja, Twig, EJS, Handlebars, PHP templates
- marketing pages, product pages, collection pages, blogs, landing pages
- desktop-first responsive refactors
- CSS-only layout and breakpoint cleanup

Do not use this as the main skill for SPA-only apps, dashboards, canvas editors, or framework-specific React/Vue/Next/Nuxt work.

## Priority Order

1. Server-render meaningful HTML first.
2. Make the desktop layout excellent by default.
3. Add responsive CSS for laptop, tablet, and mobile.
4. Keep content accessible without JavaScript.
5. Use semantic HTML and crawlable links.
6. Use lightweight JavaScript only when needed.

## Desktop-First Rules

Desktop is the base CSS. Smaller screens override downward.

```css
.section {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 4rem;
}

@media (max-width: 1024px) {
  .section {
    gap: 2.5rem;
  }
}

@media (max-width: 768px) {
  .section {
    grid-template-columns: 1fr;
  }
}
```

Prefer `max-width` media queries:

- `1200px`: smaller desktop / laptop
- `1024px`: tablet landscape
- `768px`: tablet / large mobile
- `640px`: mobile
- `480px`: small mobile

## SSR HTML Rules

Server-render:

- headings
- body copy
- product or article content
- navigation links
- breadcrumbs
- images with `alt`
- forms and labels
- footer links

Do not hide important content behind JavaScript, sliders, tabs, modals, or client-side fetches.

Bad:

```html
<div id="app">Loading...</div>
```

Good:

```html
<main>
  <article>
    <h1>Solid Wood Dining Table</h1>
    <p>Handcrafted from selected timber with a natural oil finish.</p>
  </article>
</main>
```

## Layout Rules

Use CSS Grid for page composition. Use Flexbox for one-dimensional alignment.

Prefer:

```css
.grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 2rem;
}
```

Avoid fragile width math:

```css
.card {
  width: calc(33.333% - 20px);
}
```

Every multi-column section must define its mobile collapse explicitly.

## Container and Spacing

Use a consistent page container:

```css
.container {
  width: min(100% - 48px, 1400px);
  margin-inline: auto;
}

@media (max-width: 640px) {
  .container {
    width: min(100% - 32px, 1400px);
  }
}
```

Use fluid spacing where useful:

```css
.section-padding {
  padding-block: clamp(3rem, 6vw, 7rem);
}
```

## Typography

Use fluid type for large headings:

```css
.hero-title {
  font-size: clamp(3rem, 5vw, 6.5rem);
  line-height: 0.98;
  letter-spacing: -0.04em;
}
```

Rules:

- desktop hero heading should not become 4-5 lines
- body text should stay readable on mobile
- avoid tiny text below `14px`
- keep line length around `55-75ch`

## Images and Media

Always provide dimensions or aspect ratio.

```html
<img
  src="/images/table.webp"
  width="1200"
  height="900"
  alt="Solid wood dining table in a warm interior"
  loading="lazy"
/>
```

Rules:

- do not stretch images
- use `object-fit: cover` only when cropping is acceptable
- use `loading="eager"` only for critical above-the-fold images
- use `loading="lazy"` for below-the-fold images

## Navigation

Desktop navigation must fit on one line.

Mobile navigation may use a disclosure menu, but links must still exist as real anchors in the HTML.

Use JavaScript only to toggle visibility, not to generate the navigation.

## Forms

Use real labels.

```html
<label for="email">Email</label> <input id="email" name="email" type="email" autocomplete="email" />
```

Rules:

- no placeholder-as-label
- visible focus states
- readable error messages
- tap targets at least `44px` high on mobile

## Tables and Dense Content

Tables may remain tables for real tabular data.

On mobile, choose one:

- horizontal scroll wrapper
- card-style rows
- reduced columns
- grouped sections

Never let tables break the viewport.

## JavaScript Rules

JavaScript may enhance:

- menu toggles
- accordions
- tabs
- carousels
- form validation
- small interactions

JavaScript must not be required for:

- reading main content
- seeing product details
- crawling links
- loading primary images
- understanding page structure

## Accessibility Rules

- one clear `h1`
- logical heading order
- semantic landmarks: `header`, `nav`, `main`, `section`, `article`, `footer`
- visible keyboard focus
- sufficient contrast
- no hover-only content on mobile
- respect `prefers-reduced-motion`

## Common Failures

Avoid:

- mobile-first CSS when the brief requires desktop-first
- desktop layout treated as an afterthought
- fixed widths causing horizontal overflow
- `100vh` mobile viewport bugs
- content only rendered after JavaScript
- non-crawlable navigation
- images without dimensions or alt text
- oversized hero that hides the CTA
- tables breaking mobile width
- duplicate breakpoint logic scattered everywhere

## Pre-Flight Checklist

Before shipping, verify:

- Desktop layout works first.
- Laptop, tablet, mobile layouts are explicitly handled.
- No horizontal overflow at `1440`, `1200`, `1024`, `768`, `640`, `480`, `375`.
- Main content exists in server-rendered HTML.
- Navigation links are real anchors.
- Images have `alt`, dimensions, and correct loading behavior.
- Forms have labels and focus states.
- JavaScript is enhancement only.
- Page remains usable with JavaScript disabled.
