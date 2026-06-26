---
name: wrydeco-design
description: Use this skill to generate well-branded interfaces and assets for WRYDECO, the premium artisan furniture brand. Contains essential design guidelines, colors, typography, spacing, components, and UI kit templates for prototyping and production.
user-invocable: true
---

# WRYDECO Design System Skill

This skill gives you access to the complete WRYDECO design system — a refined, gallery-style aesthetic for a luxury artisan bespoke furniture brand.

## What's Included

- **Foundation tokens** — Color palette, typography, spacing, shadows, motion systems
- **UI components** — Button, Input, Card, Badge, Divider, and more (React/JSX)
- **UI kits** — Complete WRYDECO website/gallery interface with interactive screens
- **Design guidelines** — Voice, tone, visual foundations, interaction patterns, accessibility

## Quick Start

1. Read `readme.md` at the root of this skill — it contains the complete visual and brand foundations
2. Explore the **Design System** tab to see color swatches, typography, spacing, shadows, and brand identity
3. Copy components from `components/` into your project, or link the global `styles.css` to access tokens
4. Use `ui_kits/website/` as a starting point for gallery-style e-commerce or content-focused interfaces

## Core Philosophy

WRYDECO is **quiet, refined, editorial, and organic**:
- Premium, gallery-like aesthetic (not typical e-commerce)
- Natural materials and warm tones (cream, stone, ebony, sage, clay)
- Generous whitespace, restrained interactions
- Handcrafted storytelling and sustainable sourcing emphasized
- No gradients, no emoji, no rounded corners on large containers

## Common Tasks

### Creating a page with WRYDECO styling

```html
<link rel="stylesheet" href="path/to/styles.css">

<button style="
  padding: 12px 20px;
  background-color: var(--color-ebony);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
">
  Explore Collection
</button>
```

### Using color tokens

```css
/* Background */
background-color: var(--color-cream);    /* Default page bg */
background-color: var(--color-stone);    /* Alternate section */
background-color: white;                  /* Elevated surfaces only */

/* Text */
color: var(--text-primary);               /* Black text */
color: var(--text-secondary);             /* Gray text */
color: var(--text-tertiary);              /* Lightest text */

/* Accents */
color: var(--color-clay);                 /* Gold/bronze accent */
color: var(--color-sage);                 /* Green accent */
```

### Using typography

```css
/* Display headings */
font-family: var(--font-display);
font-size: var(--font-size-display-lg);   /* 48px */
font-weight: var(--font-weight-bold);
line-height: var(--line-height-tight);    /* 1.2 */

/* Body text */
font-family: var(--font-body);
font-size: var(--font-size-body-md);      /* 16px */
line-height: var(--line-height-generous); /* 1.6 */
```

### Spacing and layout

```css
/* Use the spacing scale */
padding: var(--sp-4);       /* 16px */
margin-bottom: var(--sp-5); /* 24px */
gap: var(--sp-6);           /* 32px between flex items */

/* Max width for centered layouts */
max-width: var(--layout-max-width);  /* 1200px */
padding: var(--layout-padding-desktop); /* 32px */
```

### Shadows and elevation

```css
/* Cards and default elements */
box-shadow: var(--shadow-elevation-1);

/* Hover state */
box-shadow: var(--shadow-elevation-2);

/* Dropdowns, modals */
box-shadow: var(--shadow-elevation-3);
box-shadow: var(--shadow-elevation-4);
```

### Buttons

```jsx
// Primary action (dark, elevated)
<button style={{
  backgroundColor: 'var(--color-ebony)',
  color: 'white',
  padding: '12px 20px',
  border: 'none',
  borderRadius: 'var(--radius-sm)',
  fontWeight: '600',
  cursor: 'pointer',
}}>
  Primary Action
</button>

// Secondary (lighter background)
<button style={{
  backgroundColor: 'var(--color-stone)',
  color: 'var(--color-ebony)',
  padding: '12px 20px',
  border: 'none',
  borderRadius: 'var(--radius-sm)',
  fontWeight: '600',
  cursor: 'pointer',
}}>
  Secondary Action
</button>

// Ghost (outlined, transparent)
<button style={{
  backgroundColor: 'transparent',
  color: 'var(--color-ebony)',
  border: '1px solid var(--color-linen)',
  padding: '12px 20px',
  borderRadius: 'var(--radius-sm)',
  fontWeight: '600',
  cursor: 'pointer',
}}>
  Ghost Action
</button>
```

### Hover states

```css
/* On hover: darken background OR adjust shadow */
:hover {
  background-color: var(--color-bark);        /* darker brown */
  box-shadow: var(--shadow-elevation-2);      /* increase elevation */
}

/* On focus (keyboard) */
:focus {
  outline: 2px solid var(--color-sage);
  outline-offset: 2px;
}
```

## File Structure

```
WRYDECO Design System/
├── readme.md                             # Full design guide
├── styles.css                            # Global CSS entry (imports all tokens)
├── tokens/
│   ├── colors.css
│   ├── typography.css
│   ├── spacing.css
│   ├── shadows.css
│   └── motion.css
├── components/
│   ├── forms/                            # Button, Input, etc.
│   ├── surfaces/                         # Card, etc.
│   ├── feedback/                         # Badge, etc.
│   └── layout/                           # Divider, etc.
├── foundation-cards/                     # Design System tab specimens
│   ├── colors-primary.html
│   ├── typography-display.html
│   └── ...
├── ui_kits/
│   └── website/                          # WRYDECO website example
│       ├── index.html
│       ├── Hero.jsx
│       ├── ProductGallery.jsx
│       └── ...
└── assets/                               # (placeholder for logos, icons)
```

## Key Design Decisions

1. **No CSS-in-JS or npm packages** — components use inline styles and CSS custom properties only, keeping them lightweight and portable
2. **Generous whitespace** — the brand aesthetic demands breathing room; never cramp content
3. **Warm, muted palette** — all colors pull from natural materials (wood, stone, clay); no bright neons
4. **Restrained interactions** — hover/focus effects are subtle (color shift, shadow increase, never scale or bounce)
5. **Premium typography** — serif display + warm sans-serif body, with generous line spacing
6. **Gallery curation** — every element earns its place; no filler or placeholder content

## Support & Questions

Refer to `readme.md` for complete visual foundations. Explore the **Design System** tab to see all tokens, components, and UI kits in action.

---

**Version**: 1.0.0  
**Brand**: WRYDECO — Handcrafted, Bespoke, Premium  
**Last Updated**: June 2026
