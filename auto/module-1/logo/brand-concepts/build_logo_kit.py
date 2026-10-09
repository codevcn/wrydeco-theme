#!/usr/bin/env python3
"""Build the complete, production-grade Logo Kit for WRYDECO Concept B (Arbor Architecture).

Generates:
1. Master SVGs:
   - wrydeco-symbol-master.svg (256x256)
   - wrydeco-lockup-horizontal.svg (860x256)
   - wrydeco-lockup-stacked.svg (512x512)
   - wrydeco-wordmark.svg (560x100)
2. Color variants (Black, White, Clay #8A5D37, Ebony #1A1815).
3. Web & App Icons (favicon.ico, apple-touch-icon, PWA icons, manifest, head snippet).
4. High-resolution PNG renders (512px, 1024px, 2048px).
5. Presentation Board with retail/ecommerce mockups (signage, shopping bag, box, website, etc.).
6. Brand Guidelines document (BRAND-GUIDELINES.md).
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
KIT_DIR = BASE_DIR / "logo-kit"
MASTERS_DIR = KIT_DIR / "masters"
VARIANTS_DIR = KIT_DIR / "variants"
WEB_DIR = KIT_DIR / "web-icons"
PNG_DIR = KIT_DIR / "png-exports"
PRES_DIR = KIT_DIR / "presentation"

SKILL_SCRIPTS = Path(r"C:\Users\dell\.gemini\config\skills\logo-design\scripts")

# Brand Colors
COLOR_EBONY = "#1A1815"
COLOR_CLAY = "#8A5D37"
COLOR_CREAM = "#F5F1ED"
COLOR_WHITE = "#FFFFFF"

def make_wordmark_paths(start_x=0, base_y=70, cap_h=44, stroke=6.4):
    """Refined vector paths for W R Y D E C O wordmark."""
    s = stroke
    h = cap_h
    top = round(base_y - h, 1)
    bot = round(base_y, 1)
    mid = round(top + h / 2, 1)
    
    paths = []
    
    # 1. W (width: 54)
    wx = start_x
    w_d = (
        f"M {wx} {top} "
        f"H {wx + 7.5} "
        f"L {wx + 19} {bot - 5.5} "
        f"L {wx + 24} {top + 13} "
        f"H {wx + 30} "
        f"L {wx + 35} {bot - 5.5} "
        f"L {wx + 46.5} {top} "
        f"H {wx + 54} "
        f"L {wx + 38} {bot} "
        f"H {wx + 32} "
        f"L {wx + 27} {top + 21} "
        f"L {wx + 22} {bot} "
        f"H {wx + 16} Z"
    )
    paths.append(f'<path d="{w_d}"/>')
    
    cur_x = wx + 54 + 26
    
    # 2. R (width: 38)
    rx = cur_x
    r_bowl_h = 24
    r_rad = 12
    r_d = (
        f"M {rx} {top} H {rx + 20} "
        f"A {r_rad} {r_rad} 0 0 1 {rx + 20} {top + r_bowl_h} "
        f"H {rx + s} V {bot} H {rx} Z "
        f"M {rx + s} {top + s} H {rx + 20} "
        f"A {r_rad - s} {r_rad - s} 0 0 1 {rx + 20} {top + r_bowl_h - s} "
        f"H {rx + s} Z "
        f"M {rx + 16} {top + r_bowl_h - 2} "
        f"L {rx + 36} {bot} "
        f"H {rx + 28} "
        f"L {rx + 12} {top + r_bowl_h} Z"
    )
    paths.append(f'<path fill-rule="evenodd" d="{r_d}"/>')
    
    cur_x += 38 + 26
    
    # 3. Y (width: 40)
    yx = cur_x
    ymid_x = yx + 20
    y_d = (
        f"M {yx} {top} H {yx + 7.5} L {ymid_x} {top + 23} "
        f"L {yx + 40 - 7.5} {top} H {yx + 40} "
        f"L {ymid_x + 3.2} {top + 26} V {bot} H {ymid_x - 3.2} "
        f"V {top + 26} Z"
    )
    paths.append(f'<path d="{y_d}"/>')
    
    cur_x += 40 + 30
    
    # 4. D (width: 42)
    dx = cur_x
    d_rad = 22
    d_d = (
        f"M {dx} {top} H {dx + 18} "
        f"A {d_rad} {d_rad} 0 0 1 {dx + 18} {bot} "
        f"H {dx} Z "
        f"M {dx + s} {top + s} H {dx + 18} "
        f"A {d_rad - s} {d_rad - s} 0 0 1 {dx + 18} {bot - s} "
        f"H {dx + s} Z"
    )
    paths.append(f'<path fill-rule="evenodd" d="{d_d}"/>')
    
    cur_x += 42 + 26
    
    # 5. E (width: 34)
    ex = cur_x
    e_d = (
        f"M {ex} {top} H {ex + 32} V {top + s} H {ex + s} "
        f"V {mid - 3.2} H {ex + 26} V {mid + 3.2} H {ex + s} "
        f"V {bot - s} H {ex + 32} V {bot} H {ex} Z"
    )
    paths.append(f'<path d="{e_d}"/>')
    
    cur_x += 34 + 26
    
    # 6. C (width: 44)
    cx = cur_x + 22
    cy = mid
    c_rad = 22
    c_rad_in = c_rad - s
    cos45 = 0.7071
    c_d = (
        f"M {round(cx + c_rad * cos45, 1)} {round(cy - c_rad * cos45, 1)} "
        f"A {c_rad} {c_rad} 0 1 0 {round(cx + c_rad * cos45, 1)} {round(cy + c_rad * cos45, 1)} "
        f"L {round(cx + c_rad_in * cos45, 1)} {round(cy + c_rad_in * cos45, 1)} "
        f"A {c_rad_in} {c_rad_in} 0 1 1 {round(cx + c_rad_in * cos45, 1)} {round(cy - c_rad_in * cos45, 1)} Z"
    )
    paths.append(f'<path d="{c_d}"/>')
    
    cur_x += 44 + 26
    
    # 7. O (width: 46)
    ox = cur_x + 23
    o_rad = 22
    o_d = (
        f"M {ox} {top} "
        f"A {o_rad} {o_rad} 0 1 1 {ox - 0.01} {top} Z "
        f"M {ox} {top + s} "
        f"A {o_rad - s} {o_rad - s} 0 1 0 {ox + 0.01} {top + s} Z"
    )
    paths.append(f'<path fill-rule="evenodd" d="{o_d}"/>')
    
    total_w = (cur_x + 46) - start_x
    return "".join(paths), total_w


def get_symbol_body():
    """Arbor Architecture symbol vector markup."""
    return '''<g id="arbor-symbol">
    <!-- Base Letter W (Grounded Roots & Lower Canopy) -->
    <path d="
      M 36 84
      H 66
      L 96 172
      L 118 106
      H 138
      L 160 172
      L 190 84
      H 220
      L 180 204
      H 150
      L 128 138
      L 106 204
      H 76
      Z
    "/>
    <!-- Central Rising Trunk & Cantilevered Tree Shelf Branches -->
    <rect x="119" y="32" width="18" height="80"/>
    <!-- Top Canopy / Upper Shelf (cantilevered at 45°) -->
    <path d="M 128 32 L 84 76 L 96 88 L 128 56 L 160 88 L 172 76 Z"/>
    <!-- Mid Tier Branches / Shelves -->
    <path d="M 128 68 L 102 94 L 112 104 L 128 88 L 144 104 L 154 94 Z"/>
  </g>'''


def build_masters():
    MASTERS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Symbol Master (256x256)
    sym_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="wrydeco-symbol-title">
  <title id="wrydeco-symbol-title">WRYDECO Arbor Architecture Symbol</title>
  <g fill="{COLOR_EBONY}">
    {get_symbol_body()}
  </g>
</svg>'''
    (MASTERS_DIR / "wrydeco-symbol-master.svg").write_text(sym_svg, encoding="utf-8")
    
    # 2. Horizontal Lockup Master (860x256)
    wm_markup, wm_w = make_wordmark_paths(start_x=300, base_y=146, cap_h=44, stroke=6.4)
    horiz_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 860 256" width="860" height="256" role="img" aria-labelledby="wrydeco-lockup-title">
  <title id="wrydeco-lockup-title">WRYDECO Brand Lockup (Horizontal)</title>
  <g id="symbol" transform="translate(36, 28) scale(0.78)" fill="{COLOR_EBONY}">
    {get_symbol_body()}
  </g>
  <g id="wordmark" fill="{COLOR_EBONY}">
    {wm_markup}
  </g>
</svg>'''
    (MASTERS_DIR / "wrydeco-lockup-horizontal-master.svg").write_text(horiz_svg, encoding="utf-8")
    
    # 3. Stacked Lockup Master (512x512)
    wm_stacked, _ = make_wordmark_paths(start_x=56, base_y=386, cap_h=42, stroke=6.0)
    stacked_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512" role="img" aria-labelledby="wrydeco-stacked-title">
  <title id="wrydeco-stacked-title">WRYDECO Brand Lockup (Stacked)</title>
  <g id="symbol" transform="translate(148, 64) scale(0.84)" fill="{COLOR_EBONY}">
    {get_symbol_body()}
  </g>
  <g id="wordmark" fill="{COLOR_EBONY}">
    {wm_stacked}
  </g>
</svg>'''
    (MASTERS_DIR / "wrydeco-lockup-stacked-master.svg").write_text(stacked_svg, encoding="utf-8")
    
    # 4. Wordmark Only Master (560x100)
    wm_only, _ = make_wordmark_paths(start_x=40, base_y=70, cap_h=44, stroke=6.4)
    wm_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 100" width="560" height="100" role="img" aria-labelledby="wrydeco-wordmark-title">
  <title id="wrydeco-wordmark-title">WRYDECO Wordmark</title>
  <g id="wordmark" fill="{COLOR_EBONY}">
    {wm_only}
  </g>
</svg>'''
    (MASTERS_DIR / "wrydeco-wordmark-master.svg").write_text(wm_svg, encoding="utf-8")
    
    print("Master SVGs created.")


def run_export_variants():
    VARIANTS_DIR.mkdir(parents=True, exist_ok=True)
    WEB_DIR.mkdir(parents=True, exist_ok=True)
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Export symbol variants + web icons
    cmd_sym = [
        sys.executable,
        str(SKILL_SCRIPTS / "export_variants.py"),
        str(MASTERS_DIR / "wrydeco-symbol-master.svg"),
        "--title", "WRYDECO",
        "--mono", COLOR_CLAY,
        "--icon-bg", COLOR_EBONY,
        "--icon-fg", COLOR_CREAM,
        "--out-dir", str(VARIANTS_DIR),
        "--web-icons",
        "--png", "256", "512", "1024",
    ]
    subprocess.run(cmd_sym, check=True)
    
    # Copy web icon files to web-icons/ folder
    for f in VARIANTS_DIR.glob("*favicon*"):
        shutil.copy(f, WEB_DIR)
    for f in VARIANTS_DIR.glob("*icon*"):
        shutil.copy(f, WEB_DIR)
    for f in VARIANTS_DIR.glob("*.webmanifest"):
        shutil.copy(f, WEB_DIR)
    for f in VARIANTS_DIR.glob("*.html"):
        shutil.copy(f, WEB_DIR)
        
    # 2. Export horizontal lockup variants
    cmd_horiz = [
        sys.executable,
        str(SKILL_SCRIPTS / "export_variants.py"),
        str(MASTERS_DIR / "wrydeco-lockup-horizontal-master.svg"),
        "--title", "WRYDECO",
        "--only", "black", "white", "mono",
        "--mono", COLOR_CLAY,
        "--out-dir", str(VARIANTS_DIR),
        "--png", "860", "1720",
    ]
    subprocess.run(cmd_horiz, check=True)
    
    # 3. Export stacked lockup variants
    cmd_stacked = [
        sys.executable,
        str(SKILL_SCRIPTS / "export_variants.py"),
        str(MASTERS_DIR / "wrydeco-lockup-stacked-master.svg"),
        "--title", "WRYDECO",
        "--only", "black", "white", "mono",
        "--mono", COLOR_CLAY,
        "--out-dir", str(VARIANTS_DIR),
        "--png", "512", "1024",
    ]
    subprocess.run(cmd_stacked, check=True)
    
    # Move all high-res PNGs to png-exports/
    for png in VARIANTS_DIR.glob("*.png"):
        shutil.copy(png, PNG_DIR)
        
    print("Variants and web icons exported successfully.")


def build_presentation():
    PRES_DIR.mkdir(parents=True, exist_ok=True)
    
    spec = {
        "brand": "WRYDECO",
        "tagline": "Handcrafted Solid Wood & Architectural Decor",
        "brief": "WRYDECO crafts heirloom solid timber furniture, sculptural live-edge pieces, and signature tree bookshelves. The identity bridges organic nature and architectural refinement.",
        "adjectives": ["sculptural", "architectural", "organic", "heirloom", "refined"],
        "criteria": "Instant recognition at 16px, distinctive tree-and-W architecture, timeless in solid black, white, and warm timber clay.",
        "industry": "retail",
        "brand_color": COLOR_EBONY,
        "tile_color": COLOR_EBONY,
        "greyscale": False,
        "designer": "Senior Identity Designer",
        "round": "Final",
        "concepts": [
            {
                "name": "Arbor Architecture",
                "symbol": str(MASTERS_DIR / "wrydeco-symbol-master.svg"),
                "lockup": str(MASTERS_DIR / "wrydeco-lockup-horizontal-master.svg"),
                "idea": "Signature Tree Bookshelf reimagined: Grounded roots form the W, supporting a living trunk and cantilevered architectural tiers.",
                "rationale": [
                    "Directly celebrates Wrydeco's signature tree decor & live-edge woodworking",
                    "Flawless 16px to 2048px scalability without losing fine detail",
                    "Perfect for branding iron hot-stamping on solid oak and walnut"
                ]
            }
        ],
        "recommendation": "Concept B (Arbor Architecture) is the approved identity direction, combining brand heritage with modern gallery-grade presence.",
        "next_steps": [
            "Integrate web icons and favicon into Shopify theme",
            "Update Shopify store header and footer brand assets",
            "Deploy branded packaging and product burn stamps"
        ]
    }
    
    spec_path = PRES_DIR / "presentation-spec.json"
    spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
    
    cmd_pres = [
        sys.executable,
        str(SKILL_SCRIPTS / "presentation_board.py"),
        str(spec_path),
        "-o", str(PRES_DIR / "presentation.html"),
        "--png-dir", str(PRES_DIR / "slides"),
    ]
    subprocess.run(cmd_pres, check=True)
    print("Presentation board and slides generated.")


def build_guidelines():
    guidelines_md = f"""# WRYDECO — Brand Identity Guidelines

**Version:** 1.0 (Final Release)  
**Brand Positioning:** Handcrafted Solid Wood Furniture & Architectural Sculptural Decor  
**Core Identity Mark:** Arbor Architecture (Concept B)

---

## 1. Brand Concept & Story

WRYDECO stands for the convergence of **"Wry"** (expressive sculptural curvature, defying rigid mass-market furniture) and **"Deco"** (architectural craftsmanship, timeless aesthetic elegance).

The **Arbor Architecture** identity mark pays direct homage to Wrydeco's signature creations—the **Tree Bookshelf** and **Sculptural Living Timber**:
- **The Base:** The roots and lower canopy form an architectural, grounded letter **W** representing structural integrity, craftsmanship, and strength.
- **The Trunk & Tiers:** Rising from the central apex, the column extends upward with balanced, cantilevered diagonal branches at 45°, echoing the iconic shelving tiers of natural tree furniture.
- **Craftsmanship:** Designed with absolute geometric precision, maintaining perfect optical balance from a 16px browser favicon up to physical laser-burned timber branding irons.

---

## 2. Official Color Palette

| Color Name | HEX | RGB | CMYK | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **Timber Ebony** | `#1A1815` | `26, 24, 21` | `70, 65, 65, 80` | **Primary Brand Color** — Logos, text, high-contrast marks |
| **Warm Clay / Walnut** | `#8A5D37` | `138, 93, 55` | `25, 55, 80, 15` | **Secondary Brand Color** — Accents, luxury packaging, warm timber tone |
| **Natural Cream** | `#F5F1ED` | `245, 241, 237` | `2, 3, 5, 0` | **Surface Background** — Storefront background, paper stock |
| **Stone Neutral** | `#E8E4DF` | `232, 228, 223` | `7, 6, 8, 0` | **Border / Muted Surface** — Borders, dividers, subtle tags |
| **Pure White** | `#FFFFFF` | `255, 255, 255` | `0, 0, 0, 0` | **Negative Space / Reverse** — Knockouts on dark backgrounds |

---

## 3. Brand Assets & Deliverables

### A. Masters (`logo-kit/masters/`)
- `wrydeco-symbol-master.svg` — 256×256 pure vector symbol.
- `wrydeco-lockup-horizontal-master.svg` — 860×256 primary horizontal lockup.
- `wrydeco-lockup-stacked-master.svg` — 512×512 centered stacked lockup for social/packaging.
- `wrydeco-wordmark-master.svg` — 560×100 standalone custom geometric wordmark.

### B. Production Variants (`logo-kit/variants/`)
- **One-Color Black (`*-black.svg`)**: For laser engraving, hot-foil stamping, single-color thermal shipping labels.
- **Reversed White (`*-white.svg`)**: For dark backgrounds, dark mode UI, and dark timber finishes (Espresso/Ebony).
- **Brand Monochrome (`*-mono-8a5d37.svg`)**: Rendered in warm walnut clay.
- **Social Avatar / Square (`*-square.svg`)**: Centered on a 256×256 canvas with generous optical padding.
- **Mobile App Icon (`*-app-icon.svg`)**: Symbol knocked out in cream on an ebony squircle tile.

### C. Web & Favicon Suite (`logo-kit/web-icons/`)
- `favicon.ico` (Multi-size: 16×16, 32×32, 48×48).
- `apple-touch-icon.png` (180×180).
- `icon-192.png` & `icon-512.png` (PWA application icons).
- `site.webmanifest` & `head-snippet.html` for direct Shopify theme integration.

---

## 4. Clear Space & Minimum Sizing

- **Clear Space:** Maintain a clear margin around the symbol and lockups equal to at least **half the width of the W stem** ($X$). No typography, imagery, or UI borders may encroach into this zone.
- **Minimum Digital Sizes:**
  - Symbol only: **16 px** (browser tab favicon), **24 px** (mobile status bar).
  - Horizontal lockup: **120 px width** (mobile navigation header).
  - Stacked lockup: **96 px width** (footer / card badge).
- **Minimum Print Sizes:**
  - Symbol: **6 mm** (hot burn stamp on timber / hang tag).
  - Lockup: **25 mm width** (business cards / care instruction booklets).

---

## 5. Usage & Misuse Rules

- **DO** use the solid Ebony mark on light, natural wood and cream backgrounds.
- **DO** use the reversed White mark on dark timber, walnut, and black surfaces.
- **DO** use the approved Warm Clay monochrome variant for premium gift packaging and tissue wrap.
- **DON'T** stretch, skew, or distort the mark's proportions.
- **DON'T** add drop shadows, outer glows, bevels, or photographic textures over the vector mark.
- **DON'T** place the dark mark over busy, low-contrast photographic backgrounds without a solid backing plate.
- **DON'T** alter the relative scale between the symbol and the wordmark in the master lockups.
"""
    (KIT_DIR / "BRAND-GUIDELINES.md").write_text(guidelines_md, encoding="utf-8")
    print("Brand Guidelines written.")


def main():
    print("=== Building WRYDECO Logo Kit ===")
    build_masters()
    run_export_variants()
    build_presentation()
    build_guidelines()
    print("=== WRYDECO Logo Kit Build Complete ===")


if __name__ == "__main__":
    main()
