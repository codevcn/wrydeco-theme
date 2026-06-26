# WRYDECO Design System

A refined, gallery-style design system for WRYDECO—a luxury artisan bespoke furniture brand specializing in handcrafted natural solid-wood pieces, organic sculptural forms, sustainable sourcing, and private design consultation.

---

## Brand Overview

**WRYDECO** transforms furniture shopping into an art-collecting experience. The brand embodies:

- **Handcrafted authenticity** — natural solid-wood pieces, rustic tree-branch shelves, artisan storytelling
- **Gallery-like presentation** — editorial, refined, quiet aesthetic with careful curation
- **Sustainability** — transparent sourcing, respect for natural materials
- **Bespoke consultation** — private design guidance and personalized service

### Visual Direction

The design system reflects a **refined gallery aesthetic**: organic, premium, editorial, and distinct. Think minimalist art galleries, high-end furniture showrooms, and carefully curated editorial design—not typical e-commerce.

**Sources:**

- `uploads/WRYDECO_ALL_ABOUT_PROJECT.docx` — Brand definition and strategic overview
- `uploads/WRYDECO_Website_Requirements_VI.docx` — Website and product interface requirements

---

## Content Fundamentals

### Voice & Tone

- **I vs. You**: Primarily "you" (inviting the customer in), occasional "we" (artisan storytelling: "we source," "we handcraft")
- **Casing**: Title Case for product names and collection names; sentence case for body copy
- **Formality**: Premium, conversational, never salesy. Speak like a gallery curator, not a marketer
- **Examples**:
  - ✅ "Discover your next heirloom piece"
  - ✅ "Handcrafted from sustainably sourced walnut"
  - ✅ "Each piece tells a story"
  - ❌ "Buy now!" / "Limited time offer!"
- **Emoji**: None. This is a premium brand—emoji undermines the gallery aesthetic
- **Vibe**: Editorial, thoughtful, organic, quiet. Minimal fluff; every word earns its place

### Product Copy Patterns

- **Headlines**: Poetic but clear ("A Shelf with Character" not "Wooden Shelf v3")
- **Descriptions**: Lead with the story/material, then dimensions and care
- **CTAs**: "Explore," "View Details," "Schedule a Consultation"—never "Add to Cart" in prominence

---

## Visual Foundations

### Color System

#### Base Palette

The WRYDECO palette evokes natural materials, gallery walls, and premium restraint:

- **Primary Neutral** (`--color-cream`): `#f5f1ed` — warm cream, echoing natural wood tones
- **Secondary Neutral** (`--color-stone`): `#e8e4df` — warm taupe, gallery wall
- **Warm Dark** (`--color-ebony`): `#1a1815` — deep brown-black, wood grain
- **Warm Mid** (`--color-bark`): `#6b5d52` — warm mid-brown, weathered wood
- **Accent Natural** (`--color-clay`): `#a8845c` — warm clay/bronze, natural accent
- **Accent Living** (`--color-sage`): `#7a8968` — soft sage-green, organic/living element
- **Warm Gray** (`--color-linen`): `#b8b4af` — neutral gray-brown
- **Off-Black** (`--color-charcoal`): `#2a2622` — softer than pure black

#### Semantic Colors

- `--color-success`: `#7a8968` (sage)
- `--color-warning`: `#c9913d` (warm gold)
- `--color-error`: `#b85c5c` (warm rust-red)
- `--color-info`: `#7a8968` (sage, same as success—very limited alerts needed)

#### Color Usage Rules

- **Backgrounds**: Cream or stone, primarily. White only in nested modals/cards
- **Text**: Ebony on cream/stone; cream text very sparingly (high-contrast only)
- **Accents**: Clay and sage, used to draw attention—sparingly. Never gradients or neon
- **Hover states**: Darken text slightly (ebony → bark), OR lighten background by 2–3% (cream → stone)
- **Press states**: Darken background 5–8% or shift text to bark
- **Disabled**: Linen text on cream background; 50% opacity
- **Borders**: Use linen; never bright colors. Very minimal borders overall
- **Imagery**: Warm tones, film grain, naturalistic (never oversaturated, never B&W unless archival context)

### Typography

#### Font Selection

WRYDECO uses **premium, editorial typefaces** reflecting a gallery aesthetic:

- **Display/Headings**: `Fraunces` — a soft, organic high-contrast serif with old-style character, self-hosted from `fonts/Fraunces.woff2` (variable, weights 100–900). Fallback: Georgia, serif.

  - Weights: Regular (400), Bold (700)
  - All-caps: Reserved for labels and accent text only, very sparingly

- **Body/UI**: `Plus Jakarta Sans` — a warm, humanist geometric sans-serif, self-hosted from `fonts/Plus-Jakarta-Sans.woff2` (variable, weights 200–800). Fallback: system sans-serif stack.

  - Weights: Regular (400), Medium (500), Semibold (600)

- **Mono**: System mono or `Courier New` for code/specs; used rarely

#### Type Scale (px)

- **Display Large**: 48px / 1.2 line-height (headings, hero text)
- **Display Medium**: 36px / 1.3 line-height (section headings, product titles)
- **Display Small**: 28px / 1.4 line-height (sub-headings)
- **Body Large**: 18px / 1.6 line-height (intro text, calls-to-action)
- **Body Regular**: 16px / 1.6 line-height (standard body copy)
- **Body Small**: 14px / 1.5 line-height (secondary info, captions)
- **Caption**: 12px / 1.4 line-height (minimal use; small labels only)

#### Type Rules

- **Minimum size on web**: 16px body, never smaller than 14px for UI labels
- **Line spacing**: Generous (1.5–1.6 for body text); creates editorial elegance
- **Letter spacing**: Slightly increased on headings (+0.02em), normal elsewhere
- **Weight hierarchy**: Bold (600+) for emphasis; avoid all-caps for body copy
- **Font pairing**: Serif display + warm sans-serif body; consistent across all surfaces

### Spacing & Layout

#### Spacing Scale (CSS variables: `--sp-*`)

- `--sp-0`: 0px
- `--sp-1`: 4px (micro-spacing, internal component padding)
- `--sp-2`: 8px (component padding, gutter)
- `--sp-3`: 12px (small gaps)
- `--sp-4`: 16px (standard padding, margins)
- `--sp-5`: 24px (generous whitespace)
- `--sp-6`: 32px (section spacing)
- `--sp-7`: 48px (major section breaks)
- `--sp-8`: 64px (full-page breathing room)

#### Layout Rules

- **Margins, not padding collapsing**: Use flex/grid with `gap` for all sibling spacing
- **Columns**: 12-column grid on desktop; 4-column on tablet; 1-column on mobile
- **Max content width**: 1200px; full-bleed permitted for hero images and section backgrounds
- **Gutters**: 24px (desktop), 16px (tablet), 12px (mobile)
- **Card padding**: 24px (desktop) / 16px (mobile)
- **Safe inset**: Minimum 16px padding on mobile edges

### Cards & Surfaces

#### Card Design

- **Background**: Cream (`--color-cream`) or white for elevated content
- **Border**: None; rely on shadow
- **Shadow**: Subtle, warm: `0 2px 8px rgba(26, 24, 21, 0.08)`
  - On hover: `0 4px 16px rgba(26, 24, 21, 0.12)` (minimal depth change)
- **Corners**: 2px border-radius (subtle, restrained—not 12px)
- **Padding**: 24px default; 16px on mobile

#### Container Backgrounds

- **Primary**: Cream (`--color-cream`)
- **Alternate section**: Stone (`--color-stone`) for visual rhythm
- **Premium/Elevated**: White, sparingly
- **No gradients**: Use solid colors only—flat, editorial

### Imagery & Visual Texture

#### Imagery Style

- **Film grain**: Subtle grain/noise overlay on photography (authenticity, not digital-smooth)
- **Color tone**: Warm-toned photography (golden hour, warm light). No cool blues unless contextual
- **Saturation**: Natural, never oversaturated. Approachable, not hyperreal
- **B&W photography**: Reserved for artisan/heritage storytelling only
- **Full-bleed images**: Used for hero sections and product galleries; otherwise contained in cards

#### Illustrations & Icons

- No hand-drawn SVG illustrations (too casual for gallery aesthetic)
- Geometric icons only, minimal weight (1–2px stroke)
- Icon color: Ebony, bark, or sage; never accent clay unless special emphasis
- No emoji

### Borders & Dividers

#### Borders

- **Minimal**: Borders are rare; prefer shadows and whitespace
- **Color**: `--color-linen` (warm gray) only
- **Weight**: 1px
- **Radius**: Never on full containers; 2px only on specific elements (inputs, small cards)
- **Dividers**: 1px solid linen; used sparingly between sections only

### Shadow System

#### Shadows (all warm-toned, `rgba(26, 24, 21, ...)`—ebony with transparency)

- **Elevation 1** (cards, floating): `0 2px 8px rgba(26, 24, 21, 0.08)`
- **Elevation 2** (elevated cards, modals): `0 4px 16px rgba(26, 24, 21, 0.12)`
- **Elevation 3** (dropdowns, popovers): `0 8px 24px rgba(26, 24, 21, 0.15)`
- **Elevation 4** (full modals): `0 16px 40px rgba(26, 24, 21, 0.2)`

#### Shadow Usage

- **Never drop shadows on text** (use color contrast instead)
- **Hover shadows**: Increase by one level (Elevation 1 → Elevation 2)
- **No inner shadows** (too complex for gallery aesthetic)

### Animations & Motion

#### Animation Rules

- **Easing**: `cubic-bezier(0.4, 0, 0.2, 1)` (Material Design standard—smooth, natural)
- **Durations**:
  - Micro-interactions (hover, focus): 150ms
  - Page transitions, modals: 300ms
  - Larger reveal animations: 400–600ms
- **No infinite loops**: Animations complete and rest; no spinning icons or breathing effects
- **Reduced motion**: Respect `@media (prefers-reduced-motion: reduce)` — instant or fade-only
- **Fades & slides**: Preferred; no bounces or elastic effects (too playful for gallery brand)

#### Interaction Feedback

- **Hover**: Slight color shift (text darkens) + shadow increase + cursor change
- **Press/Active**: Color shift + 2px offset OR scale to 0.98 (subtle, not dramatic)
- **Focus**: Outline in `--color-sage` (2px, 2px offset) for keyboard nav
- **Disabled**: 50% opacity, cursor not-allowed, no hover effects

### Density & Whitespace

#### Information Density

- **Gallery aesthetic = generous whitespace**: Never cramp content
- **List items**: 24px vertical padding minimum; 16px on mobile
- **Form inputs**: 24px tall, 16px padding; 32px tall variant for primacy
- **Buttons**: 40px tall (touch-target), 16–24px padding horizontal
- **Never**: More than 3 items per row on desktop for product cards; 1–2 per row on mobile

#### Breathing Room

- **Between sections**: 48–64px (desktop) / 32–48px (mobile)
- **Between heading & body**: 12–16px
- **Paragraph spacing**: 1.5× line-height after each paragraph

### Focus & Accessibility

#### Focus States

- **Keyboard focus**: 2px solid `--color-sage` outline, 2px offset
- **Visible on all interactive elements**: buttons, links, inputs, checkboxes, etc.
- **Never `outline: none`** without replacing with custom focus style

#### Color Contrast

- **Text on background**: Minimum WCAG AA (4.5:1) for body text, AAA (7:1) preferred
- **Interactive elements**: Same rules
- **Test**: All combinations verified for contrast

---

## Components Overview

The design system includes reusable UI primitives organized by concern:

- **Forms**: Button, Input, Select, Checkbox, Radio, FormLabel, Textarea
- **Feedback**: Badge, Tag, Alert, Toast, Skeleton
- **Navigation**: Breadcrumb, Tabs, Pagination
- **Data Display**: Table, Image, Divider, Empty State
- **Modals & Overlays**: Modal, Tooltip, Popover, Dropdown
- **Layout**: Stack, Grid, Container

Each component follows the visual foundations (color, spacing, type, shadows) and is production-ready.

---

## UI Kits

### WRYDECO Website/Gallery

A high-fidelity, interactive recreation of the WRYDECO e-commerce gallery experience:

- **Homepage**: Hero, featured collections, social proof
- **Product Gallery**: Grid view with filtering, detail modal
- **Product Detail**: Images, specifications, customization, consultation CTA
- **Collections**: Curated collections landing
- **About/Sustainability**: Brand story, sourcing transparency
- **Consultation**: Request form, availability picker

---

## Foundation Specimen Cards

The Design System tab displays \~20 foundation cards organized into groups:

- **Colors** (primary, semantic, neutrals)
- **Typography** (display, body, scales)
- **Spacing** (scale, usage)
- **Shadows** & **Elevation**
- **Brand** (logos, imagery treatment)

---

## File Organization

```
WRYDECO Design System/
├── styles.css                    # Global CSS entry point (imports all below)
├── tokens/
│   ├── colors.css
│   ├── typography.css
│   ├── spacing.css
│   ├── shadows.css
│   └── motion.css
├── assets/
│   ├── logos/
│   ├── icons/
│   └── imagery/
├── components/
│   ├── forms/
│   │   ├── Button.jsx
│   │   ├── Button.d.ts
│   │   ├── Button.prompt.md
│   │   ├── Input.jsx
│   │   └── ...
│   ├── feedback/
│   └── ...
├── foundation-cards/             # @dsCard HTML files for Design System tab
│   ├── colors-primary.html
│   ├── colors-semantic.html
│   ├── type-display.html
│   └── ...
├── ui_kits/
│   └── website/
│       ├── index.html
│       ├── Hero.jsx
│       ├── ProductGallery.jsx
│       └── ...
└── _ds_manifest.json            # Auto-generated by compiler
```

---

## Next Steps

1. ✅ Brand foundation & visual system defined
2. 🔄 Token CSS files (colors, typography, spacing, shadows, motion)
3. 🔄 Foundation specimen cards for Design System tab
4. 🔄 Reusable component library (forms, feedback, navigation, etc.)
5. 🔄 WRYDECO website UI kit (homepage, product gallery, detail, etc.)
6. 🔄 SKILL.md for cross-project compatibility
7. 🔄 Final system validation

---

**Design System Version**: 1.0.0\
**Last Updated**: June 2026\
**Brand**: WRYDECO — Handcrafted, Bespoke, Premium
