#!/usr/bin/env python3
"""Build and refine 3 original SVG logo concepts for WRYDECO.
Outputs:
  - concept-a-symbol.svg: Architectural Timber W (Interlocking Joinery)
  - concept-a-lockup.svg: Symbol + Wordmark horizontal
  - concept-b-symbol.svg: Arbor & Signet (Living Tree Architecture)
  - concept-b-lockup.svg: Symbol + Wordmark horizontal
  - concept-c-symbol.svg: Sculptural Bentwood Arc (Continuous Wry Ribbon)
  - concept-c-lockup.svg: Symbol + Wordmark horizontal
"""
import math
import os
from pathlib import Path

OUT_DIR = Path(__file__).parent.resolve()

def make_wordmark_paths(start_x=0, base_y=160, cap_h=64, stroke=8.5):
    """Generate path data for W R Y D E C O with architectural elegance and optical craft."""
    s = stroke
    h = cap_h
    top = base_y - h
    bot = base_y
    mid = top + h / 2
    
    # We will generate precise vector paths for each letter
    # Tracking / spacing between letters
    paths = []
    
    # --- W ---
    # Width = 64
    wx = start_x
    # 4 diagonal strokes with clean miters
    # Outer left, inner left, inner right, outer right
    # Let's draw W as a single filled polygon with mitered joins
    # Points along top and bottom
    w_pts = [
        # Outer left top
        (wx, top),
        (wx + s * 1.2, top),
        (wx + 22, bot - s * 0.8),
        (wx + 32 - s * 0.6, top + h * 0.28),
        (wx + 32 + s * 0.6, top + h * 0.28),
        (wx + 42, bot - s * 0.8),
        (wx + 64 - s * 1.2, top),
        (wx + 64, top),
        (wx + 45, bot),
        (wx + 39, bot),
        (wx + 32, top + h * 0.48),
        (wx + 25, bot),
        (wx + 19, bot),
    ]
    w_d = "M " + " L ".join(f"{round(x, 1)} {round(y, 1)}" for x, y in w_pts) + " Z"
    paths.append(f'<path d="{w_d}"/>')
    
    # Spacing
    cur_x = wx + 64 + 28
    
    # --- R ---
    # Width = 46
    rx = cur_x
    # Vertical stem + upper bowl + diagonal leg
    r_d = (
        f"M {rx} {top} H {rx + 24} "
        f"A {h * 0.28} {h * 0.28} 0 0 1 {rx + 24} {top + h * 0.56} "
        f"H {rx + s} V {bot} H {rx} Z "
        # Inner counter
        f"M {rx + s} {top + s} H {rx + 22} "
        f"A {h * 0.28 - s} {h * 0.28 - s} 0 0 1 {rx + 22} {top + h * 0.56 - s} "
        f"H {rx + s} Z "
        # Diagonal leg
        f"M {rx + 18} {top + h * 0.50} L {rx + 42} {bot} H {rx + 42 - s * 1.3} "
        f"L {rx + 14} {top + h * 0.50 + s} Z"
    )
    paths.append(f'<path fill-rule="evenodd" d="{r_d}"/>')
    
    cur_x += 46 + 28
    
    # --- Y ---
    # Width = 48
    yx = cur_x
    ymid_x = yx + 24
    y_stem_top = top + h * 0.52
    y_d = (
        f"M {yx} {top} H {yx + s * 1.2} L {ymid_x} {y_stem_top} "
        f"L {yx + 48 - s * 1.2} {top} H {yx + 48} "
        f"L {ymid_x + s/2} {y_stem_top + s * 0.4} V {bot} H {ymid_x - s/2} "
        f"V {y_stem_top + s * 0.4} Z"
    )
    paths.append(f'<path d="{y_d}"/>')
    
    cur_x += 48 + 32
    
    # --- D ---
    # Width = 50
    dx = cur_x
    r_d_outer = h / 2
    r_d_inner = r_d_outer - s
    d_d = (
        f"M {dx} {top} H {dx + 22} "
        f"A {r_d_outer} {r_d_outer} 0 0 1 {dx + 22} {bot} "
        f"H {dx} Z "
        f"M {dx + s} {top + s} H {dx + 22} "
        f"A {r_d_inner} {r_d_inner} 0 0 1 {dx + 22} {bot - s} "
        f"H {dx + s} Z"
    )
    paths.append(f'<path fill-rule="evenodd" d="{d_d}"/>')
    
    cur_x += 50 + 28
    
    # --- E ---
    # Width = 42
    ex = cur_x
    e_d = (
        f"M {ex} {top} H {ex + 40} V {top + s} H {ex + s} "
        f"V {mid - s/2} H {ex + 34} V {mid + s/2} H {ex + s} "
        f"V {bot - s} H {ex + 40} V {bot} H {ex} Z"
    )
    paths.append(f'<path d="{e_d}"/>')
    
    cur_x += 42 + 28
    
    # --- C ---
    # Width = 52
    cx = cur_x + 26
    cy = mid
    cr_out = h / 2
    cr_in = cr_out - s
    # 45 degree opening on the right
    # Arc from angle 45 deg to 315 deg
    c_d = (
        f"M {round(cx + cr_out * 0.7071, 1)} {round(cy - cr_out * 0.7071, 1)} "
        f"A {cr_out} {cr_out} 0 1 0 {round(cx + cr_out * 0.7071, 1)} {round(cy + cr_out * 0.7071, 1)} "
        f"L {round(cx + cr_in * 0.7071, 1)} {round(cy + cr_in * 0.7071, 1)} "
        f"A {cr_in} {cr_in} 0 1 1 {round(cx + cr_in * 0.7071, 1)} {round(cy - cr_in * 0.7071, 1)} Z"
    )
    paths.append(f'<path d="{c_d}"/>')
    
    cur_x += 52 + 28
    
    # --- O ---
    # Width = 54
    ox = cur_x + 27
    oy = mid
    o_d = (
        f"M {ox} {top} "
        f"A {h/2} {h/2} 0 1 1 {ox - 0.01} {top} Z "
        f"M {ox} {top + s} "
        f"A {h/2 - s} {h/2 - s} 0 1 0 {ox + 0.01} {top + s} Z"
    )
    paths.append(f'<path fill-rule="evenodd" d="{o_d}"/>')
    
    total_w = (cur_x + 54) - start_x
    return "".join(paths), total_w


def build_concept_a_symbol():
    """Concept A: Architectural Timber W (Mortise & Tenon Joinery Monogram).
    Geometric precision: Interlocking solid timber chevrons with architectural dovetail/miter cuts.
    """
    # 256x256 canvas, centered.
    # Solid, sculptural, timeless woodworking joinery.
    # Four faceted solid timber beams forming a majestic W.
    # Left wing, left-center diagonal, right-center diagonal, right wing.
    # Clean 60°/30° architectural geometry with genuine negative space joinery seams.
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title-a">
  <title id="title-a">Wrydeco Architectural Timber W Monogram</title>
  <g fill="#1A1815">
    <!-- Left outer timber pillar / beam -->
    <path d="M 32 60 L 68 60 L 98 160 L 68 196 L 32 74 Z"/>
    <!-- Left interior chevron beam interlocking at bottom keel -->
    <path d="M 72 200 L 102 164 L 124 100 L 132 100 L 112 200 Z"/>
    <!-- Right interior chevron beam -->
    <path d="M 144 200 L 124 100 L 132 100 L 154 164 L 184 200 Z"/>
    <!-- Right outer timber pillar / beam -->
    <path d="M 224 60 L 188 60 L 158 160 L 188 196 L 224 74 Z"/>
    <!-- Architectural central keystone block (representing solid timber joinery key) -->
    <polygon points="128,48 144,88 112,88"/>
  </g>
</svg>'''
    return svg


def build_concept_b_symbol():
    """Concept B: Arbor & Signet (Living Tree Architecture).
    Brand Equity Reimagined: The rooted letter W ascends into sculpted, cantilevered branches.
    Enclosed in a refined squircle signet (modern artisan seal).
    """
    # Let's create an iconic, unified negative-space carving on a rounded square signet.
    # Or a standalone clean organic tree silhouette where the trunk and roots form a perfect W!
    # Standalone mark (no fake background tile):
    # Base: Solid sculpted W.
    # Center: The trunk rises and splits symmetrically into 3 cantilevered shelves / branches.
    # Consistent stroke / silhouette weight: 18-24px, completely solid and scalable.
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title-b">
  <title id="title-b">Wrydeco Arbor Living Timber Symbol</title>
  <path fill="#1A1815" fill-rule="evenodd" d="
    M 36 64
    L 62 64
    L 86 166
    L 116 88
    L 116 54
    C 102 54 90 44 90 32
    L 112 32
    C 114 38 120 42 128 42
    C 136 42 142 38 144 32
    L 166 32
    C 166 44 154 54 140 54
    L 140 88
    L 170 166
    L 194 64
    L 220 64
    L 182 208
    L 156 208
    L 128 132
    L 100 208
    L 74 208
    Z
    M 128 72
    C 123 72 118 76 116 82
    L 128 114
    L 140 82
    C 138 76 133 72 128 72
    Z
  "/>
</svg>'''
    return svg


def build_concept_c_symbol():
    """Concept C: Sculptural Bentwood Arc (Continuous Wry Ribbon).
    Expressive curvature ("Wry") meets deco elegance.
    Continuous steam-bent solid wood ribbon forming a flowing, sculptural W.
    Tangential circle geometry, perfectly balanced, luxury furniture presence.
    """
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title-c">
  <title id="title-c">Wrydeco Sculptural Bentwood Arc</title>
  <path fill="#1A1815" fill-rule="evenodd" d="
    M 36 72
    C 36 150 72 204 96 204
    C 118 204 124 168 128 128
    C 132 168 138 204 160 204
    C 184 204 220 150 220 72
    C 202 72 186 118 174 156
    C 168 176 164 182 160 182
    C 156 182 150 154 146 122
    C 140 76 136 52 128 52
    C 120 52 116 76 110 122
    C 106 154 100 182 96 182
    C 92 182 88 176 82 156
    C 70 118 54 72 36 72
    Z
  "/>
</svg>'''
    return svg


def build_lockup(symbol_svg_body, title_id, title_text):
    """Build a horizontal lockup (820 x 256) combining the 256x256 symbol and WRYDECO wordmark."""
    # Symbol placed at X=32, Y=32, scaled to 192x192
    wordmark_markup, wm_w = make_wordmark_paths(start_x=280, base_y=146, cap_h=46, stroke=6.8)
    
    # Subtitle / descriptor: "HANDCRAFTED SOLID WOOD" or "ARTISAN WOODWORK & DECOR"
    # To keep strict pure vector without live text in the lockup, we can keep the primary wordmark or craft small glyphs
    total_width = 820
    lockup_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_width} 256" width="{total_width}" height="256" role="img" aria-labelledby="{title_id}">
  <title id="{title_id}">{title_text}</title>
  <g id="symbol" transform="translate(32, 28) scale(0.78)">
    {symbol_svg_body}
  </g>
  <g id="wordmark" fill="#1A1815">
    {wordmark_markup}
  </g>
</svg>'''
    return lockup_svg


def extract_inner_svg(svg_str):
    """Extract contents inside <svg>...</svg>."""
    start = svg_str.find(">") + 1
    end = svg_str.rfind("</svg>")
    inner = svg_str[start:end].strip()
    # Strip <title> if present
    import re
    inner = re.sub(r"<title[^>]*>.*?</title>", "", inner, flags=re.DOTALL)
    return inner.strip()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Concept A
    sym_a = build_concept_a_symbol()
    (OUT_DIR / "concept-a-symbol.svg").write_text(sym_a, encoding="utf-8")
    lock_a = build_lockup(extract_inner_svg(sym_a), "title-lockup-a", "Wrydeco Architectural Timber W Lockup")
    (OUT_DIR / "concept-a-lockup.svg").write_text(lock_a, encoding="utf-8")
    
    # Concept B
    sym_b = build_concept_b_symbol()
    (OUT_DIR / "concept-b-symbol.svg").write_text(sym_b, encoding="utf-8")
    lock_b = build_lockup(extract_inner_svg(sym_b), "title-lockup-b", "Wrydeco Arbor Living Timber Lockup")
    (OUT_DIR / "concept-b-lockup.svg").write_text(lock_b, encoding="utf-8")
    
    # Concept C
    sym_c = build_concept_c_symbol()
    (OUT_DIR / "concept-c-symbol.svg").write_text(sym_c, encoding="utf-8")
    lock_c = build_lockup(extract_inner_svg(sym_c), "title-lockup-c", "Wrydeco Sculptural Bentwood Arc Lockup")
    (OUT_DIR / "concept-c-lockup.svg").write_text(lock_c, encoding="utf-8")
    
    print("Generated 6 SVG files in brand-concepts/")


if __name__ == "__main__":
    main()
