# WRYDECO Design System — Complete

## ✅ What's Ready

### Foundation & Tokens
- ✅ **130+ CSS custom properties** organized by concern:
  - Colors (primary, semantic, text, background, border, surface, brand-specific)
  - Typography (font families incl. Roboto, weights, sizes, line heights, section title)
  - Spacing scale (4px to 64px) + legacy `--space-*` aliases
  - Shadows & elevation system (4 levels)
  - Motion & easing (timing, transitions)

> **Last sync**: June 2026 — Tokens verified against `assets/base.css` (source of truth)

### Visual Foundation Specimens (17 cards)
- ✅ Primary palette, accent colors, semantic colors
- ✅ Display & body typography scales
- ✅ Spacing scale visualization
- ✅ Elevation shadows, border radius
- ✅ Motion durations, button states, focus states
- ✅ Brand identity card

### Reusable Components (9 JSX components)
- ✅ **Forms**: Button (primary, secondary, ghost, sizes), Input, Badge
- ✅ **Surfaces**: Card (default, elevated, elevation levels)
- ✅ **Layout**: Divider (horizontal, vertical)
- ✅ **UI Kit Components**: Hero, ProductGallery, ProductDetail, Footer

### UI Kit — WRYDECO Website
- ✅ **index.html** — Interactive gallery-style e-commerce homepage
- ✅ Hero section with CTA
- ✅ Product gallery grid (hover effects, card elevation)
- ✅ Product detail view (quantity, specs, consultation request form)
- ✅ Footer with navigation links

### Documentation
- ✅ **readme.md** — Complete visual foundations, design philosophy, token definitions
- ✅ **SKILL.md** — Cross-project compatibility guide with usage examples
- ✅ **Component prompts** — Usage notes for each component

---

## ⚠️ Caveats & Next Steps

### Font Files
The design system self-hosts both brand fonts (wired via `@font-face` in `tokens/fonts.css`):
- **Fraunces** (serif, display headings) — `fonts/Fraunces.woff2`
- **Plus Jakarta Sans** (sans-serif, body text) — `fonts/Plus-Jakarta-Sans.woff2`

**Action**: Fonts are wired and rendering. No further action needed.

### What You Can Do Right Now

1. **Explore the Design System tab** — See all 17 foundation cards, component library, and UI kit
2. **Copy components** — Use Button, Card, Input, Badge in your own projects
3. **Use the website UI kit** — Launch `ui_kits/website/index.html` to see a live gallery-style interface
4. **Reference tokens** — All 110 tokens available via CSS custom properties
5. **Adopt the brand** — The aesthetic is locked in: refined, organic, gallery-like, no gradients, generous whitespace

### Future Enhancements (Optional)

- Add more components (Select, Checkbox, Radio, Modal, Tabs, etc.)
- Create additional UI kits (product admin, consultation dashboard, account pages)
- Build email templates using the design system
- Create slide deck templates for presentations
- Add accessibility audit documentation
- Create Figma file that mirrors this system

---

## File Structure

```
WRYDECO Design System/
├── readme.md                          # Full design guide (read this first!)
├── SKILL.md                           # For use in Claude Code projects
├── styles.css                         # Global CSS entry point
├── tokens/
│   ├── colors.css                     # 42 color tokens
│   ├── typography.css                 # Font, weight, size, line-height tokens
│   ├── spacing.css                    # Spacing scale + component sizes
│   ├── shadows.css                    # Elevation shadows, radius, focus
│   └── motion.css                     # Easing, timing, transitions
├── components/
│   ├── forms/
│   │   ├── Button.jsx / .d.ts / .prompt.md
│   │   ├── Input.jsx / .d.ts / .prompt.md
│   │   └── forms.card.html
│   ├── surfaces/
│   │   ├── Card.jsx / .d.ts / .prompt.md
│   │   └── surfaces.card.html
│   ├── feedback/
│   │   ├── Badge.jsx / .d.ts / .prompt.md
│   │   └── feedback.card.html
│   └── layout/
│       ├── Divider.jsx / .d.ts / .prompt.md
│       └── layout.card.html
├── foundation-cards/                  # Design System tab specimens
│   ├── colors-primary.html
│   ├── colors-accent.html
│   ├── colors-semantic.html
│   ├── typography-display.html
│   ├── typography-body.html
│   ├── spacing-scale.html
│   ├── shadows-elevation.html
│   ├── shadows-radius.html
│   ├── motion-durations.html
│   ├── interaction-buttons.html
│   ├── interaction-focus.html
│   └── brand-identity.html
├── ui_kits/
│   └── website/
│       ├── index.html                 # Main gallery interface
│       ├── Hero.jsx
│       ├── ProductGallery.jsx
│       ├── ProductDetail.jsx
│       └── Footer.jsx
└── _ds_manifest.json                  # Auto-generated by compiler
```

---

## How to Use This

### For Designers/Prototypers
1. Open the **Design System** tab to see all tokens and components
2. Click into any foundation card to inspect colors, type scales, etc.
3. Launch `ui_kits/website/index.html` to interact with the complete gallery interface
4. Copy components into your designs and customize via style props

### For Developers
1. Link `styles.css` in your HTML — all 110 tokens become available
2. Reference tokens in your CSS: `background-color: var(--color-cream)`
3. Copy React components (`Button.jsx`, `Card.jsx`, etc.) into your codebase
4. Use the UI kit as a reference for layout patterns and interaction styles

### For Brand Consistency
- Always use tokens for colors, spacing, typography — never hard-code values
- Refer to `readme.md` for visual foundations (shadows, motion, hover states, density)
- Match the gallery aesthetic: quiet, refined, organic, generous whitespace
- No gradients, no emoji (unless in product imagery), minimal borders

---

## Next: What Would Make This Perfect?

Please help iterate by providing:

1. **Font files** — ✅ Fraunces & Plus Jakarta Sans wired and rendering
2. **Logo & brand assets** — high-res logo, icon set, any brand illustrations
3. **Product photography** — sample images to replace emoji placeholders in UI kit
4. **Feedback on aesthetic** — does the gallery-style direction match your vision?
5. **Additional screens needed?** — collections landing, about page, consultation form, account dashboard, etc.

---

**Status**: ✅ Design system complete and ready to use  
**Version**: 1.0.0  
**Last Updated**: June 2026  
**Brand**: WRYDECO — Premium Artisan Furniture
