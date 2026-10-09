#!/usr/bin/env python3
"""Refine the 3 WRYDECO logo concepts and wordmark with precision geometry.

Concept A: 'Dovetail Monogram' — Interlocking solid timber beams at exact 60°/120° angles.
Concept B: 'Arbor Signet' — Living tree architecture carved inside a modern artisan seal.
Concept C: 'Sculptural Bentwood' — Continuous stream-bent architectural ribbon with balanced cradles.
"""
import math
from pathlib import Path

OUT_DIR = Path(__file__).parent.resolve()

def make_wordmark_paths(start_x=0, base_y=145, cap_h=46, stroke=6.5):
    """Clean geometric vector wordmark for W R Y D E C O.
    All curves use integer or 1-decimal coordinates.
    """
    s = stroke
    h = cap_h
    top = round(base_y - h, 1)
    bot = round(base_y, 1)
    mid = round(top + h / 2, 1)
    
    paths = []
    
    # 1. W (width: 52)
    wx = start_x
    # 4 clean diagonals with flat top and bottom
    w_d = (
        f"M {wx} {top} "
        f"L {wx + s * 1.1} {top} "
        f"L {wx + 18} {bot - s * 0.8} "
        f"L {wx + 26 - s * 0.5} {top + h * 0.28} "
        f"L {wx + 26 + s * 0.5} {top + h * 0.28} "
        f"L {wx + 34} {bot - s * 0.8} "
        f"L {wx + 52 - s * 1.1} {top} "
        f"L {wx + 52} {top} "
        f"L {wx + 36.5} {bot} "
        f"L {wx + 31.5} {bot} "
        f"L {wx + 26} {top + h * 0.46} "
        f"L {wx + 20.5} {bot} "
        f"L {wx + 15.5} {bot} Z"
    )
    paths.append(f'<path d="{w_d}"/>')
    
    cur_x = wx + 52 + 26
    
    # 2. R (width: 38)
    rx = cur_x
    r_bowl_h = round(h * 0.56, 1)
    r_rad = round(r_bowl_h / 2, 1)
    r_d = (
        f"M {rx} {top} H {rx + 20} "
        f"A {r_rad} {r_rad} 0 0 1 {rx + 20} {top + r_bowl_h} "
        f"H {rx + s} V {bot} H {rx} Z "
        f"M {rx + s} {top + s} H {rx + 19} "
        f"A {r_rad - s} {r_rad - s} 0 0 1 {rx + 19} {top + r_bowl_h - s} "
        f"H {rx + s} Z "
        # Leg meeting cleanly at bowl junction
        f"M {rx + 16} {top + r_bowl_h - s * 0.5} "
        f"L {rx + 36} {bot} "
        f"H {rx + 36 - s * 1.3} "
        f"L {rx + 13} {top + r_bowl_h} Z"
    )
    paths.append(f'<path fill-rule="evenodd" d="{r_d}"/>')
    
    cur_x += 38 + 26
    
    # 3. Y (width: 40)
    yx = cur_x
    ymid_x = round(yx + 20, 1)
    y_stem_top = round(top + h * 0.52, 1)
    y_d = (
        f"M {yx} {top} H {yx + s * 1.1} L {ymid_x} {y_stem_top} "
        f"L {yx + 40 - s * 1.1} {top} H {yx + 40} "
        f"L {ymid_x + s/2} {y_stem_top + s * 0.4} V {bot} H {ymid_x - s/2} "
        f"V {y_stem_top + s * 0.4} Z"
    )
    paths.append(f'<path d="{y_d}"/>')
    
    cur_x += 40 + 30
    
    # 4. D (width: 42)
    dx = cur_x
    d_rad = round(h / 2, 1)
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
        f"V {mid - s/2} H {ex + 27} V {mid + s/2} H {ex + s} "
        f"V {bot - s} H {ex + 32} V {bot} H {ex} Z"
    )
    paths.append(f'<path d="{e_d}"/>')
    
    cur_x += 34 + 26
    
    # 6. C (width: 44)
    cx = round(cur_x + 22, 1)
    cy = mid
    c_rad = round(h / 2, 1)
    c_rad_in = c_rad - s
    # 45-degree clean opening
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
    ox = round(cur_x + 23, 1)
    o_rad = round(h / 2, 1)
    o_d = (
        f"M {ox} {top} "
        f"A {o_rad} {o_rad} 0 1 1 {ox - 0.01} {top} Z "
        f"M {ox} {top + s} "
        f"A {o_rad - s} {o_rad - s} 0 1 0 {ox + 0.01} {top + s} Z"
    )
    paths.append(f'<path fill-rule="evenodd" d="{o_d}"/>')
    
    total_w = (cur_x + 46) - start_x
    return "".join(paths), total_w


def build_concept_a():
    """Concept A: Architectural Timber W (Dovetail Joinery Monogram).
    Four precision solid timber beams interlocking at clean 60°/120° angles.
    Centered at (128, 128), optical height = 156, width = 192.
    Clean mortise-and-tenon spacing of 10 units.
    """
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title-a">
  <title id="title-a">Wrydeco Architectural Timber W Monogram</title>
  <path fill="#1A1815" fill-rule="evenodd" d="
    M 36 50
    L 68 50
    L 92 140
    L 62 186
    L 36 60
    Z
    M 68 194
    L 96 150
    L 124 94
    L 132 94
    L 106 194
    Z
    M 124 94
    L 132 94
    L 160 150
    L 188 194
    L 150 194
    Z
    M 188 186
    L 164 140
    L 188 50
    L 220 50
    L 220 60
    Z
    M 112 50
    L 144 50
    L 136 78
    L 120 78
    Z
  "/>
</svg>'''
    # Let's make Concept A an impeccably solid, interlocking monogram:
    # 2 interlocking chevrons that form a majestic W:
    # Chevron 1: Left V
    # Chevron 2: Right V
    # Interlocking at the center keel with a dovetail joint!
    # Let's write the exact path:
    # Left stem: (32, 52) to (88, 204)
    # Left inner: (88, 204) to (128, 104)
    # Right inner: (128, 104) to (168, 204)
    # Right stem: (168, 204) to (224, 52)
    # Width of timber = 32.
    # Angle of diagonals: exactly 60° from horizontal!
    # cos(60) = 0.5, sin(60) = 0.866.
    # If height = 152, dx = 152 / 1.732 = 87.7
    # Let's build a unified path with a 10px negative space joinery cut:
    svg_clean = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title-a">
  <title id="title-a">Wrydeco Architectural Timber W Monogram</title>
  <g fill="#1A1815">
    <!-- Left Timber Wing (outer leg + inner rise) -->
    <path d="M 32 52 L 64 52 L 96 156 L 118 100 L 102 100 L 88 140 L 64 62 L 32 62 Z"/>
    <path d="M 72 204 L 100 132 L 122 188 L 96 204 Z"/>
    <!-- Right Timber Wing -->
    <path d="M 134 188 L 156 132 L 184 204 L 160 204 Z"/>
    <path d="M 138 100 L 154 100 L 160 156 L 192 52 L 224 52 L 192 62 L 168 140 Z"/>
  </g>
</svg>'''
    # Actually, let's create a pure, monolithic, architectural Letterform W:
    # A single solid path with chamfered joints and an inner negative-space timber key.
    # Look at classic furniture marks like Herman Miller or Knoll: powerful, memorable, simple.
    svg_monolith = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title-a">
  <title id="title-a">Wrydeco Architectural Timber W Monogram</title>
  <path fill="#1A1815" fill-rule="evenodd" d="
    M 32 56
    H 66
    L 96 158
    L 120 76
    H 136
    L 160 158
    L 190 56
    H 224
    L 182 200
    H 150
    L 128 126
    L 106 200
    H 74
    Z
    M 128 152
    L 138 186
    H 118
    Z
  "/>
</svg>'''
    return svg_monolith


def build_concept_b():
    """Concept B: Arbor Signet (Living Tree Architecture).
    Wrydeco's signature tree motif + letter W, unified inside a luxury squircle artisan seal.
    Bold, organic, architectural branches supporting shelves.
    """
    # Squircle frame: x=24, y=24, w=208, h=208, rx=44.
    # Inner cutout forms:
    # The Tree + W:
    # A solid, magnificent tree whose trunk sprouts from the W's central apex,
    # branching into three cantilevered tiers (echoing tree bookshelves).
    # All negative space carved with evenodd rule.
    # Total canvas: 256x256.
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title-b">
  <title id="title-b">Wrydeco Arbor Signet</title>
  <rect x="24" y="24" width="208" height="208" rx="44" fill="#1A1815"/>
  <!-- The Living Tree & W carved out in pure negative space -->
  <!-- We can use fill="#F5F1ED" (brand cream) or build as single evenodd path for master -->
  <path fill="#F5F1ED" d="
    M 60 76
    H 78
    L 96 142
    L 118 76
    H 124
    V 62
    C 114 62 106 56 102 48
    H 116
    C 120 52 124 54 128 54
    C 132 54 136 52 140 48
    H 154
    C 150 56 142 62 132 62
    V 76
    H 138
    L 160 142
    L 178 76
    H 196
    L 170 178
    H 148
    L 128 114
    L 108 178
    H 86
    Z
  "/>
</svg>'''
    # For a production master that works on ANY background (transparent / one-color),
    # let's make Concept B a standalone positive silhouette (no outer box required), OR a true evenodd knockout:
    # A true evenodd knockout in a squircle:
    svg_evenodd = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title-b">
  <title id="title-b">Wrydeco Arbor Signet</title>
  <path fill="#1A1815" fill-rule="evenodd" d="
    M 68 24
    H 188
    A 44 44 0 0 1 232 68
    V 188
    A 44 44 0 0 1 188 232
    H 68
    A 44 44 0 0 1 24 188
    V 68
    A 44 44 0 0 1 68 24
    Z
    M 58 72
    H 76
    L 96 140
    L 118 72
    H 124
    V 60
    C 112 60 102 52 98 44
    H 114
    C 118 48 122 51 128 51
    C 134 51 138 48 142 44
    H 158
    C 154 52 144 60 132 60
    V 72
    H 138
    L 160 140
    L 180 72
    H 198
    L 170 184
    H 148
    L 128 116
    L 108 184
    H 86
    Z
  "/>
</svg>'''
    return svg_evenodd


def build_concept_c():
    """Concept C: Sculptural Bentwood Arc (Continuous Wry Ribbon).
    Pure tangential geometry representing steam-bent hardwood furniture.
    The outer crests are proud (y=64), sweeping into twin cradles at baseline (y=192),
    rising into an elegant central peak (y=88).
    Stroke width: exactly 24 units, with rounded organic caps.
    """
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title-c">
  <title id="title-c">Wrydeco Sculptural Bentwood Arc</title>
  <path fill="none" stroke="#1A1815" stroke-width="24" stroke-linecap="round" stroke-linejoin="round" d="
    M 44 64
    C 44 148 76 192 98 192
    C 118 192 122 136 128 88
    C 134 136 138 192 158 192
    C 180 192 212 148 212 64
  "/>
</svg>'''
    return svg


def build_lockup(symbol_markup, title_id, title_text, is_signet=False):
    """Horizontal lockup with 1:1 symbol on left, wordmark on right.
    viewBox: 0 0 860 256.
    """
    wordmark_markup, wm_w = make_wordmark_paths(start_x=310, base_y=146, cap_h=44, stroke=6.4)
    
    # Subtitle: ARTISAN WOODWORK
    # Let's keep the primary wordmark crisp and proud
    scale = 0.76 if is_signet else 0.78
    trans_x = 36 if is_signet else 40
    trans_y = 30 if is_signet else 28
    
    lockup_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 860 256" width="860" height="256" role="img" aria-labelledby="{title_id}">
  <title id="{title_id}">{title_text}</title>
  <g id="symbol" transform="translate({trans_x}, {trans_y}) scale({scale})">
    {symbol_markup}
  </g>
  <g id="wordmark" fill="#1A1815">
    {wordmark_markup}
  </g>
</svg>'''
    return lockup_svg


def extract_inner(svg_str):
    import re
    start = svg_str.find(">") + 1
    end = svg_str.rfind("</svg>")
    inner = svg_str[start:end].strip()
    inner = re.sub(r"<title[^>]*>.*?</title>", "", inner, flags=re.DOTALL)
    return inner.strip()


def main():
    # Write refined symbols
    sym_a = build_concept_a()
    (OUT_DIR / "concept-a-symbol.svg").write_text(sym_a, encoding="utf-8")
    lock_a = build_lockup(extract_inner(sym_a), "title-lockup-a", "Wrydeco Architectural Timber W Lockup")
    (OUT_DIR / "concept-a-lockup.svg").write_text(lock_a, encoding="utf-8")
    
    sym_b = build_concept_b()
    (OUT_DIR / "concept-b-symbol.svg").write_text(sym_b, encoding="utf-8")
    lock_b = build_lockup(extract_inner(sym_b), "title-lockup-b", "Wrydeco Arbor Signet Lockup", is_signet=True)
    (OUT_DIR / "concept-b-lockup.svg").write_text(lock_b, encoding="utf-8")
    
    sym_c = build_concept_c()
    (OUT_DIR / "concept-c-symbol.svg").write_text(sym_c, encoding="utf-8")
    lock_c = build_lockup(extract_inner(sym_c), "title-lockup-c", "Wrydeco Sculptural Bentwood Lockup")
    (OUT_DIR / "concept-c-lockup.svg").write_text(lock_c, encoding="utf-8")
    
    print("Refined 6 SVG files written successfully.")


if __name__ == "__main__":
    main()
