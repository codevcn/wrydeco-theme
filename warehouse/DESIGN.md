# Ashdeco

## Overview

**Product:** Ashdeco
**URL:** https://ashdeco.com/
**Surface type:** e-commerce
**Audience:** Consumers and shoppers
**Brand character:** Product-focused shopping experience with a rich, diverse color palette and 5 typefaces.

### Design Principles

- Trust signals first — credibility reduces friction more than clever copy.
- Clear path to action — one primary CTA per view, never stacked.
- Speed over polish — perceived performance is part of the design system.

## Colors

| Token           | Value     | Role           |
| --------------- | --------- | -------------- |
| --bg-card-hover | `#E3E3E3` | Background     |
| --bg-card       | `#EDEDED` | Background     |
| --bg            | `#F7F7F7` | Background     |
| color-6         | `#F4ECDD` | Surface        |
| color-3         | `#767676` | Text Secondary |
| color-2         | `#E60023` | Accent         |
| color-4         | `#249ED6` | Accent         |
| color-1         | `#36210A` | Border         |
| color-8         | `#EFEFEF` | Border         |
| color-10        | `#FFFFFF` | Text Light     |

## Typography

**Primary Font:** Plus Jakarta Sans
**Font stack:** "Plus Jakarta Sans", Fraunces, Arial, Roboto, "Times New Roman", serif

| Level     | Size | Usage                  |
| --------- | ---- | ---------------------- |
| text-xs   | 12px | Captions, metadata     |
| text-sm   | 14px | Labels, secondary text |
| text-base | 15px | Body text (default)    |
| text-lg   | 35px | Subheadings, emphasis  |
| text-xl   | 46px | Section headings       |
| text-2xl  | 64px | Section headings       |

**Weight scale:** 400 · 500 · 600 · 700 · 800
**Line heights:** 64px · 46.016px · 25.6px · 24px · 22.4px · 22.0877px · 21px · 36.2376px · 20.8px · 19.2px · 16.8px · 13px · 15.6px

## Spacing

**Base unit:** 4px

`space-1: 4px` · `space-2: 6px` · `space-3: 8px` · `space-4: 10px` · `space-5: 11px` · `space-6: 12px` · `space-7: 14px` · `space-8: 16px` · `space-9: 18px` · `space-10: 20px` · `space-11: 24px` · `space-12: 25px` · `space-13: 32px` · `space-14: 48px` · `space-15: 64px` · `space-16: 80px` · `space-17: 104px` · `space-18: 295px`

## Shapes

**Border radius:** `radius-sm: 0px 0px 4px` · `radius-md: 4px` · `radius-lg: 16px` · `radius-xl: 46px` · `radius-full: 50%` · `radius-6: 999px`

## Elevation

_None detected._

## Motion

- **duration-fast:** `all`
- **duration-fast:** `none`
- **duration-fast:** `transform 0.1s`
- **duration-fast:** `background 0.15s`
- **duration-fast:** `0.15s`
- **duration-fast:** `transform 0.15s`
- **duration-fast:** `color 0.15s`
- **duration-base:** `color 0.2s`
- **duration-base:** `transform 0.2s`
- **duration-base:** `background 0.2s, border-color 0.2s`
- **duration-base:** `0.2s`
- **duration-base:** `opacity 0.25s, transform 0.25s`
- **duration-base:** `background 0.25s`
- **duration-base:** `transform 0.3s cubic-bezier(0.2, 0.8, 0.2, 1), background 0.2s`
- **duration-base:** `transform 0.3s cubic-bezier(0.2, 0.8, 0.2, 1)`
- **duration-slow:** `transform 0.6s`

## Components

- **Buttons:** 175 detected
- **Links:** 231 detected
- **Inputs:** 5 detected
- **Navigation:** 3 elements
- **Lists:** 39 detected
- **Forms:** 6 detected
- **Images:** 363 detected

## Do's and Don'ts

### Do

- Reference tokens by name, not raw values — agents and developers should use `color.text.primary`, not `#171717`.
- Define all interactive states: default, hover, focus-visible, active, disabled.
- Use the spacing scale for all padding, margin, and gap values.
- Write content in sentence case. Reserve ALL CAPS for acronyms only.
- Test every component at the smallest and largest breakpoint before shipping.

### Don't

- Do not introduce colors outside the extracted palette.
- Do not use arbitrary spacing values — stick to the scale.
- Do not mix border-radius values. Pin to the detected set (0px 0px 4px, 4px, 16px, 46px, 50%, 999px).
- Do not stack more than one primary CTA per viewport.
- Do not use red for non-error UI — reserve it for destructive actions and warnings.
- Do not ship components without defining hover, focus-visible, and disabled states.

## Writing Tone

Persuasive, benefit-driven, trustworthy. Active voice, urgency without pressure.

## Authoring Workflow

When creating or updating a component guideline for this system, follow this sequence:

1. **State the intent** — one sentence on what the component does and why it exists.
2. **Map tokens** — list every color, spacing, typography, and radius token the component uses. No raw values.
3. **Define anatomy** — break the component into named parts (container, label, icon, etc.) with their token assignments.
4. **Specify states** — document every state: default, hover, focus-visible, active, disabled, loading, error, empty.
5. **Describe interactions** — keyboard, pointer, and touch behavior, including edge cases (long content, overflow, truncation).
6. **Add accessibility criteria** — write testable pass/fail checks (e.g. "focus ring must be visible at 3:1 contrast").
7. **List anti-patterns** — concrete examples of misuse with a brief explanation of why each is wrong.
8. **Close with a QA checklist** — a mechanical list of verifiable items (see Definition of Done below).

## Required Output Structure

Every component guideline produced from this system must contain these sections, in order:

1. Overview — purpose, when to use, when not to use.
2. Tokens and foundations — all referenced tokens from the tables above.
3. Anatomy and variants — named parts, variant matrix, responsive behavior.
4. States and interactions — full state table, keyboard/pointer/touch behavior.
5. Accessibility — ARIA attributes, contrast requirements, focus management, screen reader behavior.
6. Content guidelines — copy length, tone, capitalisation, placeholder text rules.
7. Anti-patterns — explicit examples of what not to build, with reasoning.

## Component Requirements

Every component built against this system must:

- Reference only tokens defined in the tables above — no hardcoded hex, px, or font values.
- Define all interactive states: default, hover, focus-visible, active, disabled, loading, error.
- Specify responsive behavior at the smallest and largest supported breakpoint.
- Handle edge cases: empty state, overflow / truncation, maximum content length.
- Include keyboard navigation (Tab, Enter, Escape, Arrow keys where applicable).
- Document ARIA roles, labels, and live-region behavior where relevant.
- Include known page component density: - **Buttons:** 175 detected
- **Links:** 231 detected
- **Inputs:** 5 detected
- **Navigation:** 3 elements
- **Lists:** 39 detected
- **Forms:** 6 detected
- **Images:** 363 detected

## Definition of Done

A component is not complete until every item below is checked:

- Renders correctly in its default state (smoke test).
- All states documented and visually verified (hover, focus, disabled, loading, error, empty).
- All visual values use design tokens — zero hardcoded values.
- Keyboard navigation works without a pointer.
- No critical accessibility violations (contrast, ARIA, focus order).
- Tested at smallest and largest breakpoint.
- Anti-patterns section lists at least one concrete misuse example.
- Documentation covers purpose, usage, props/API, and limitations.
