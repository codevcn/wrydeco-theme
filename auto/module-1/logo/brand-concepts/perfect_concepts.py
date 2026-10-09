#!/usr/bin/env python3
"""Perfect the 3 WRYDECO logo concepts to museum-grade craft.

Concept A: 'Timber Joinery' (Letterform / Monogram)
  - Three solid architectural timber beams interlocking to form a bold, grounded W with precision woodworking negative-space seams.

Concept B: 'Arbor Architecture' (Pictorial / Letterform)
  - Signature Tree Bookshelf reimagined: A sculpted tree whose roots form the grounded base of a W, and whose cantilevered branches form architectural tiers.

Concept C: 'Sculptural Bentwood' (Abstract / Sculptural Contour)
  - Continuous steam-bent hardwood ribbon with sweeping organic cradles and planed timber terminals.
"""
from pathlib import Path

OUT_DIR = Path(__file__).parent.resolve()

def make_wordmark_paths(start_x=300, base_y=146, cap_h=44, stroke=6.4):
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
    
    return "".join(paths)


def build_concept_a():
    """Concept A: Timber Joinery (Letterform / Monogram).
    Inspired by master wood joinery: three bold timber planks angled at 60°/120° that interlock.
    Left outer slab, center V-keel, right outer slab.
    Crisp, powerful, architectural.
    """
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title-a">
  <title id="title-a">Wrydeco Timber Joinery Monogram</title>
  <g fill="#1A1815">
    <!-- Left outer timber plank -->
    <path d="
      M 32 56
      H 66
      L 106 186
      L 74 196
      Z
    "/>
    <!-- Center interlocking V-keel -->
    <path d="
      M 84 204
      L 128 72
      L 172 204
      H 140
      L 128 166
      L 116 204
      Z
    "/>
    <!-- Right outer timber plank -->
    <path d="
      M 224 56
      H 190
      L 150 186
      L 182 196
      Z
    "/>
  </g>
</svg>'''
    # Let's make Concept A a unified single path with incredible geometric harmony:
    # A sculpted W where two interlocking chevrons fit together like mortise & tenon:
    svg_monogram = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title-a">
  <title id="title-a">Wrydeco Timber Joinery Monogram</title>
  <g fill="#1A1815">
    <!-- Left Timber Wing -->
    <polygon points="32,56 68,56 112,192 76,204"/>
    <!-- Center Chevron Keel (interlocking with negative space) -->
    <polygon points="90,204 128,88 166,204 138,204 128,172 118,204"/>
    <!-- Right Timber Wing -->
    <polygon points="224,56 188,56 144,192 180,204"/>
  </g>
</svg>'''
    return svg_monogram


def build_concept_b():
    """Concept B: Arbor Architecture (The Living Tree Bookshelf).
    Direct tribute to Wrydeco's signature product: A magnificent tree whose roots form the grounded base of a W,
    and whose cantilevered diagonal branches form architectural tiers/shelves.
    Clean, modern, organic yet structural.
    """
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title-b">
  <title id="title-b">Wrydeco Arbor Architecture Symbol</title>
  <path fill="#1A1815" fill-rule="evenodd" d="
    M 36 68
    H 66
    L 94 154
    L 116 88
    V 42
    H 86
    V 28
    H 170
    V 42
    H 140
    V 88
    L 162 154
    L 190 68
    H 220
    L 180 200
    H 150
    L 128 132
    L 106 200
    H 76
    Z
    M 128 60
    C 120 60 114 66 114 74
    H 142
    C 142 66 136 60 128 60
    Z
  "/>
</svg>'''
    # Let's create an organic tree structure in pure vector:
    # Trunk in center with 45° diagonal tree branches:
    svg_tree_clean = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title-b">
  <title id="title-b">Wrydeco Arbor Architecture Symbol</title>
  <g fill="#1A1815">
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
    <!-- Center trunk -->
    <rect x="119" y="32" width="18" height="80"/>
    <!-- Top Canopy / Upper Shelf (cantilevered at 45°) -->
    <path d="M 128 32 L 84 76 L 96 88 L 128 56 L 160 88 L 172 76 Z"/>
    <!-- Mid Tier Branches / Shelves -->
    <path d="M 128 68 L 102 94 L 112 104 L 128 88 L 144 104 L 154 94 Z"/>
  </g>
</svg>'''
    return svg_tree_clean


def build_concept_c():
    """Concept C: Sculptural Bentwood Arc (Continuous Wry Ribbon).
    Continuous steam-bent solid wood ribbon with sweeping organic cradles and planed timber terminals.
    Refined with harmonious thickness and optical lift.
    """
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title-c">
  <title id="title-c">Wrydeco Sculptural Bentwood Arc</title>
  <path fill="#1A1815" fill-rule="evenodd" d="
    M 36 64
    H 62
    C 62 128 78 174 96 174
    C 112 174 120 134 128 88
    C 136 134 144 174 160 174
    C 178 174 194 128 194 64
    H 220
    C 220 152 196 204 160 204
    C 134 204 124 160 128 120
    C 132 160 122 204 96 204
    C 60 204 36 152 36 64
    Z
  "/>
</svg>'''
    return svg


def build_lockup(symbol_markup, title_id, title_text):
    wordmark_markup = make_wordmark_paths(start_x=300, base_y=146, cap_h=44, stroke=6.4)
    lockup_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 860 256" width="860" height="256" role="img" aria-labelledby="{title_id}">
  <title id="{title_id}">{title_text}</title>
  <g id="symbol" transform="translate(36, 28) scale(0.78)">
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
    sym_a = build_concept_a()
    (OUT_DIR / "concept-a-symbol.svg").write_text(sym_a, encoding="utf-8")
    lock_a = build_lockup(extract_inner(sym_a), "title-lockup-a", "Wrydeco Timber Joinery Monogram Lockup")
    (OUT_DIR / "concept-a-lockup.svg").write_text(lock_a, encoding="utf-8")
    
    sym_b = build_concept_b()
    (OUT_DIR / "concept-b-symbol.svg").write_text(sym_b, encoding="utf-8")
    lock_b = build_lockup(extract_inner(sym_b), "title-lockup-b", "Wrydeco Arbor Architecture Lockup")
    (OUT_DIR / "concept-b-lockup.svg").write_text(lock_b, encoding="utf-8")
    
    sym_c = build_concept_c()
    (OUT_DIR / "concept-c-symbol.svg").write_text(sym_c, encoding="utf-8")
    lock_c = build_lockup(extract_inner(sym_c), "title-lockup-c", "Wrydeco Sculptural Bentwood Lockup")
    (OUT_DIR / "concept-c-lockup.svg").write_text(lock_c, encoding="utf-8")
    
    print("Perfected 6 SVG files written.")


if __name__ == "__main__":
    main()
