#!/usr/bin/env python3
"""Craft pass for WRYDECO logo concepts.

Implements 3 distinctive, production-grade geometric marks:
- Concept A: 'Timber Chevron' — Architectural joinery monogram (solid timber slabs with 12px joinery seam).
- Concept B: 'Tree Shelf Signet' — Living tree architecture & signature tree bookshelf carved inside artisan seal.
- Concept C: 'Sculptural Bentwood' — Interlocking bentwood arches with architectural planed terminals.
"""
import math
from pathlib import Path

OUT_DIR = Path(__file__).parent.resolve()

def make_wordmark_paths(start_x=310, base_y=146, cap_h=44, stroke=6.4):
    """Refined vector paths for W R Y D E C O wordmark."""
    s = stroke
    h = cap_h
    top = round(base_y - h, 1)
    bot = round(base_y, 1)
    mid = round(top + h / 2, 1)
    
    paths = []
    
    # 1. W (width: 54)
    # Using clean 75°/105° angles: dx = dy / tan(75°) ≈ dy / 3.732
    # For h=44, total dx for outer stem ≈ 11.8
    wx = start_x
    w_d = (
        f"M {wx} {top} "
        f"H {wx + 7.5} "
        f"L {wx + 19} {bot - 5.5} "
        f"L {wx + 27 - 3} {top + 13} "
        f"H {wx + 27 + 3} "
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
        # Diagonal leg meeting cleanly
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
    """Concept A: Timber Chevron (Architectural Joinery Monogram).
    Two interlocking solid timber V-chevrons locking together at the keel with an architectural seam.
    Clean 75°/105° timber cuts.
    Solid, monumental, heirloom woodworking.
    """
    # 256x256 canvas.
    # Left V-slab:
    # Outer stem from (32, 56) down to (84, 204), inner rise from (84, 204) to (122, 92)
    # Right V-slab:
    # Inner rise from (134, 92) to (172, 204), outer stem from (172, 204) to (224, 56)
    # The 12px vertical seam between x=122 and x=134 represents the precision joinery joint.
    # Timber beam thickness: 30 units.
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title-a">
  <title id="title-a">Wrydeco Timber Chevron Monogram</title>
  <g fill="#1A1815">
    <!-- Left Timber Chevron Beam -->
    <path d="
      M 32 56
      H 66
      L 96 154
      L 122 80
      H 122
      V 112
      L 104 162
      L 82 204
      H 64
      L 32 56
      Z
    "/>
    <!-- Right Timber Chevron Beam -->
    <path d="
      M 224 56
      H 190
      L 160 154
      L 134 80
      H 134
      V 112
      L 152 162
      L 174 204
      H 192
      L 224 56
      Z
    "/>
    <!-- Interlocking Center Keel Joint (Solid Keystone Block) -->
    <polygon points="128,124 146,176 110,176"/>
  </g>
</svg>'''
    # Let's make Concept A completely seamless and solid:
    # An iconic, bold W where the two halves lock together cleanly:
    svg_clean = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title-a">
  <title id="title-a">Wrydeco Timber Chevron Monogram</title>
  <path fill="#1A1815" fill-rule="evenodd" d="
    M 32 56
    H 66
    L 96 156
    L 122 76
    H 134
    L 160 156
    L 190 56
    H 224
    L 182 204
    H 150
    L 128 132
    L 106 204
    H 74
    Z
    M 128 156
    L 142 196
    H 114
    Z
  "/>
</svg>'''
    return svg_clean


def build_concept_b():
    """Concept B: Tree Shelf Signet (Arbor Architecture).
    Brand Heritage Reimagined: The living tree bookshelf carved inside a modern artisan seal.
    A solid grounded W at the base; a central trunk rises up and branches into 2 pairs of
    cantilevered architectural shelves (signature Wrydeco Tree Bookshelves).
    """
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title-b">
  <title id="title-b">Wrydeco Tree Shelf Signet</title>
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
    M 56 68
    H 76
    L 96 142
    L 120 74
    H 120
    V 42
    H 136
    V 74
    H 136
    L 160 142
    L 180 68
    H 200
    L 172 188
    H 148
    L 128 116
    L 108 188
    H 84
    Z
    M 136 50
    H 166
    V 60
    H 136
    Z
    M 90 74
    H 120
    V 84
    H 90
    Z
    M 136 94
    H 170
    V 104
    H 136
    Z
    M 86 116
    H 120
    V 126
    H 86
    Z
  "/>
</svg>'''
    # Even simpler and more iconic:
    # Instead of lots of small shelves, let's create a majestic tree canopy where the branches
    # branch upward at 45° like sculptural tree arms:
    svg_tree = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title-b">
  <title id="title-b">Wrydeco Tree Shelf Signet</title>
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
    M 56 72
    H 78
    L 98 142
    L 118 72
    H 118
    V 46
    L 94 46
    L 94 56
    L 114 56
    V 72
    H 118
    L 98 142
    L 128 112
    L 138 72
    V 56
    L 158 56
    L 158 46
    L 138 46
    V 72
    H 138
    L 158 142
    L 178 72
    H 200
    L 170 184
    H 148
    L 128 120
    L 108 184
    H 86
    Z
  "/>
</svg>'''
    # Let's craft Concept B as a standalone organic tree silhouette (without the square tile restriction)
    # OR a clean emblem where the tree trunk grows out of the W:
    # Standalone mark:
    # Base: Solid architectural W.
    # Center trunk rises up to Y=40 and branches out with two balanced sculptural cantilevered limbs (45° angles).
    svg_standalone_tree = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title-b">
  <title id="title-b">Wrydeco Arbor Living Timber Symbol</title>
  <path fill="#1A1815" fill-rule="evenodd" d="
    M 36 68
    H 68
    L 94 156
    L 118 78
    V 48
    H 96
    V 34
    H 160
    V 48
    H 138
    V 78
    L 162 156
    L 188 68
    H 220
    L 182 204
    H 150
    L 128 128
    L 106 204
    H 74
    Z
    M 128 94
    L 142 144
    H 114
    Z
  "/>
</svg>'''
    # Look at that: The top has a horizontal capital / architectural branch beam (like a wooden lintel or shelf),
    # creating a fusion of an ancient tree pillar and modern architectural console!
    return svg_standalone_tree


def build_concept_c():
    """Concept C: Sculptural Bentwood Arc (Continuous Wry Ribbon).
    Two interlocking curved wooden arches with planed architectural terminals.
    Smooth tangential curvature representing bentwood furniture craft.
    """
    # A single continuous flowing ribbon of solid timber:
    # Outer terminals are planed at 45° angles:
    # Left terminal at (40, 64) cut horizontally.
    # Center apex at (128, 96).
    # Right terminal at (216, 64).
    # Bottom cradles at (84, 196) and (172, 196).
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
    wordmark_markup = make_wordmark_paths(start_x=310, base_y=146, cap_h=44, stroke=6.4)
    lockup_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 860 256" width="860" height="256" role="img" aria-labelledby="{title_id}">
  <title id="{title_id}">{title_text}</title>
  <g id="symbol" transform="translate(40, 28) scale(0.78)">
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
    lock_a = build_lockup(extract_inner(sym_a), "title-lockup-a", "Wrydeco Timber Chevron Monogram Lockup")
    (OUT_DIR / "concept-a-lockup.svg").write_text(lock_a, encoding="utf-8")
    
    sym_b = build_concept_b()
    (OUT_DIR / "concept-b-symbol.svg").write_text(sym_b, encoding="utf-8")
    lock_b = build_lockup(extract_inner(sym_b), "title-lockup-b", "Wrydeco Arbor Living Timber Lockup")
    (OUT_DIR / "concept-b-lockup.svg").write_text(lock_b, encoding="utf-8")
    
    sym_c = build_concept_c()
    (OUT_DIR / "concept-c-symbol.svg").write_text(sym_c, encoding="utf-8")
    lock_c = build_lockup(extract_inner(sym_c), "title-lockup-c", "Wrydeco Sculptural Bentwood Lockup")
    (OUT_DIR / "concept-c-lockup.svg").write_text(lock_c, encoding="utf-8")
    
    print("Craft pass SVGs generated.")


if __name__ == "__main__":
    main()
