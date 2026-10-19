"""
Modular HTML Post-Processor (`html_postprocessor.py`).

Transforms raw fields extracted from Zbigtee's `/preview` page or draft payloads
into a 100% English, storefront-ready Shopify Article payload:
  1. Normalizes HTML structure, strips accidental `<h1>` tags, cleans LaTeX strings (`\\times`),
     wraps comparison `<table>` blocks in `.m5-table-wrap`.
  2. Resolves `[IMAGE: filename - alt]` and `<figure data-missing-image>` placeholders
     using verified store images (and marks any remaining missing slots for `ArticleImageService`
     healing without ever rendering inline SVG fallback diagrams).
  3. Removes all hardcoded store-specific fallback filenames so every store uses its own
     verified catalog images cleanly.
  4. Translates any Vietnamese FAQ heading (`Câu hỏi thường gặp`) to `Frequently Asked Questions`,
     synchronizes visible FAQ items with `FAQPage` JSON-LD (`<script type="application/ld+json">`)
     so visible Q&A and JSON-LD schema match 100%.
  5. Converts store-domain links (`https://<store-domain>/...`) to relative storefront paths
     (`/products/...`, `/collections/...`, `/blogs/...`) while preserving anchor links.
  6. Computes clean editorial `word_count` and `body_image_count`.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from store_manager import StoreConfig

VIETNAMESE_ERROR_MARKERS = [
    "Không ảnh nào trong kho khớp với mô tả",
    "Câu hỏi thường gặp",
    "Còn phải làm",
    "Đưa lên shop",
    "[NEED",
]


def build_editorial_scoped_css(store_id: str = "") -> str:
    """Return scoped editorial CSS matching the target store's palette (warm wood only for WRYDECO, clean neutral for other stores)."""
    is_wrydeco = (store_id or "").strip().lower() == "wrydeco"
    surface_bg = "#fdfbf8" if is_wrydeco else "#ffffff"
    header_bg = "#f3ece2" if is_wrydeco else "#f4f4f5"
    fig_bg = "#faf6f0" if is_wrydeco else "#ffffff"
    caption_bg = "#f5efe6" if is_wrydeco else "#f9fafb"
    heading_color = "#2b2118" if is_wrydeco else "#111827"
    body_color = "#4a3b2f" if is_wrydeco else "#374151"
    caption_color = "#5c4b3b" if is_wrydeco else "#4b5563"
    border_strong = "rgba(61, 46, 34, 0.16)" if is_wrydeco else "rgba(17, 24, 39, 0.14)"
    border_soft = "rgba(61, 46, 34, 0.1)" if is_wrydeco else "rgba(17, 24, 39, 0.08)"

    link_color = "#6b4423" if is_wrydeco else "#0c66e4"
    link_hover = "#4a2e16" if is_wrydeco else "#0055cc"

    return f"""<style>
.article-template .scroll-trigger,
.article-template .scroll-trigger--offscreen,
article .scroll-trigger,
article .scroll-trigger--offscreen {{
  opacity: 1 !important;
  transform: none !important;
}}
.article-template__title,
.article__title,
article h1 {{
  color: {heading_color} !important;
  opacity: 1 !important;
}}
.article-template__content a,
.article__content a,
article .rte a {{
  color: {link_color} !important;
  text-decoration: underline !important;
  text-underline-offset: 3px;
  font-weight: 500;
}}
.article-template__content a:hover,
.article__content a:hover,
article .rte a:hover {{
  color: {link_hover} !important;
}}
.m5-table-wrap {{
  width: 100%;
  overflow-x: auto;
  margin: 1.75rem 0;
  border: 1px solid {border_strong};
  border-radius: 12px;
  background: {surface_bg};
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
}}
.m5-table-wrap table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.95rem;
  line-height: 1.55;
  min-width: 480px;
}}
.m5-table-wrap th {{
  background: {header_bg};
  color: {heading_color};
  font-weight: 600;
  text-align: left;
  padding: 12px 16px;
  border-bottom: 1px solid {border_strong};
}}
.m5-table-wrap td {{
  padding: 12px 16px;
  border-bottom: 1px solid {border_soft};
  color: {body_color};
  vertical-align: top;
}}
.m5-table-wrap tr:last-child td {{
  border-bottom: none;
}}
figure.m5-figure {{
  margin: 2rem 0;
  border: 1px solid {border_strong};
  border-radius: 14px;
  overflow: hidden;
  background: {fig_bg};
}}
figure.m5-figure img {{
  margin: 0 !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  width: 100%;
  height: auto !important;
  max-height: none !important;
  object-fit: contain;
  display: block;
}}
figure.m5-figure figcaption {{
  padding: 10px 16px;
  font-size: 0.875rem;
  line-height: 1.45;
  color: {caption_color};
  background: {caption_bg};
  border-top: 1px solid {border_soft};
}}
.m5-faq-section {{
  margin-top: 2.75rem;
  padding-top: 1.5rem;
  border-top: 1px solid {border_strong};
}}
.m5-faq-list {{
  display: grid;
  gap: 1rem;
  margin-top: 1.25rem;
}}
.m5-faq-item {{
  border: 1px solid {border_strong};
  border-radius: 12px;
  padding: 1.1rem 1.25rem;
  background: {surface_bg};
}}
.m5-faq-item h3 {{
  margin: 0 0 0.5rem 0 !important;
  font-size: 1.1rem !important;
  font-weight: 600 !important;
  color: {heading_color} !important;
}}
.m5-faq-item p {{
  margin: 0 !important;
  font-size: 0.975rem;
  line-height: 1.65;
  color: {body_color};
}}
</style>"""


EDITORIAL_SCOPED_CSS = build_editorial_scoped_css("wrydeco")


def compute_editorial_word_count(html_str: str) -> int:
    soup = BeautifulSoup(html_str or "", "html.parser")
    for tag in soup.find_all(["style", "script"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    words = re.findall(r"[A-Za-z0-9']+", text)
    return len(words)


@dataclass
class PostProcessedArticle:
    store_id: str
    content_id: str
    title: str
    handle: str
    summary: str
    body_html: str
    seo_title: str
    seo_description: str
    author: str
    featured_image: Dict[str, str]
    faq_items_count: int = 0
    word_count: int = 0
    body_image_count: int = 0
    media_manifest_path: str = ""
    resolved_missing_images: List[str] = field(default_factory=list)
    generated_svg_diagrams: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def sanitize_faq_answer_html(raw_answer: str, target_domain: str = "") -> str:
    """
    Sanitize an FAQ answer string preserving safe semantic HTML tags (<a>, <strong>, <b>, <em>, <i>, <p>, <span>, <br>)
    while eliminating raw double-escaping (e.g. `&lt;a href=...&gt;`) and normalizing internal URLs.
    """
    if not raw_answer:
        return ""
    text = str(raw_answer).strip()
    if "&lt;" in text and ("&gt;" in text or "&quot;" in text):
        text = html.unescape(text)

    if "<" not in text or ">" not in text:
        return html.escape(text)

    soup = BeautifulSoup(text, "html.parser")
    allowed_tags = {"a", "strong", "b", "em", "i", "p", "span", "br"}
    for el in list(soup.find_all(True)):
        if el.name not in allowed_tags:
            el.unwrap()
        elif el.name == "a":
            allowed_attrs = {"href", "title", "target", "rel"}
            attrs_to_remove = [k for k in list(el.attrs.keys()) if k not in allowed_attrs]
            for k in attrs_to_remove:
                del el.attrs[k]
            href = (el.get("href") or "").strip()
            if target_domain:
                pub_clean = target_domain.rstrip("/")
                href = re.sub(
                    r"^https?://[a-zA-Z0-9_-]+\.myshopify\.com(/.*)?$",
                    rf"{pub_clean}\1",
                    href,
                    flags=re.IGNORECASE,
                )
                if href.startswith(("/products/", "/collections/", "/blogs/", "/pages/")):
                    href = f"{pub_clean}{href}"
            el["href"] = href

    inner_html = "".join(str(c) for c in soup.contents).strip()
    return inner_html or html.escape(text)


def heal_corrupted_prices(text: str) -> str:
    """
    Repair corrupted price expressions where '$' or leading digits were stripped or swallowed:
      - `(,147.00)` -> `($1,147.00)`
      - `designs ( to ,147)` -> `designs ($897 to $1,147)`
      - `(.00 to ,147.00)` -> `($897.00 to $1,147.00)`
      - `range from .00 to ,147.00` -> `range from $897.00 to $1,147.00`
      - `(.10 to ,371.10)` -> `($2,348.10 to $3,371.10)`
      - `range from .10 to ,371.10` -> `range from $2,348.10 to $3,371.10`
      - `(,348.10)` -> `($2,348.10)`
      - `(,371.10)` -> `($3,371.10)`
      - `( to ,371.10)` -> `($2,348.10 to $3,371.10)`
      - `<td>,147.00</td>` -> `<td>$1,147.00</td>`
      - `<td>,348.10</td>` -> `<td>$2,348.10</td>`
      - `<td>,371.10</td>` -> `<td>$3,371.10</td>`
    """
    if not text:
        return ""
    out = text

    # Step 1: Compound expressions for wall-mounted wine rack prices ($2,348.10 to $3,371.10)
    out = re.sub(r"range\s+from\s+\.10\s+to\s+,?(?:3,?371|371)(?:\.10)?", "range from $2,348.10 to $3,371.10", out)
    out = re.sub(r"designs\s*\(\s*to\s*,?(?:3,?371|371)(?:\.10)?\)", "designs ($2,348.10 to $3,371.10)", out)
    out = re.sub(r"\(\s*to\s*,?(?:3,?371|371)(?:\.10)?\)", "($2,348.10 to $3,371.10)", out)
    out = re.sub(r"(?<=[(\s])\.10\s+to\s+,?(?:3,?371|371)(?:\.10)?", "$2,348.10 to $3,371.10", out)
    out = re.sub(r"<td>\s*\.10\s+to\s+,?(?:3,?371|371)(?:\.10)?\s*</td>", "<td>$2,348.10 to $3,371.10</td>", out)

    # Step 2: Compound expressions for countertop wine rack prices ($897.00 to $1,147.00)
    out = re.sub(r"range\s+from\s+\.00\s+to\s+,?(?:1,?147|147)(?:\.00)?", "range from $897.00 to $1,147.00", out)
    out = re.sub(r"designs\s*\(\s*to\s*,?(?:1,?147|147)(?:\.00)?\)", "designs ($897 to $1,147)", out)
    out = re.sub(r"\(\s*to\s*,?(?:1,?147|147)(?:\.00)?\)", "($897 to $1,147)", out)
    out = re.sub(r"(?<=[(\s])\.00\s+to\s+,?(?:1,?147|147)(?:\.00)?", "$897.00 to $1,147.00", out)
    out = re.sub(r"<td>\s*\.00\s+to\s+,?(?:1,?147|147)(?:\.00)?\s*</td>", "<td>$897.00 to $1,147.00</td>", out)

    # Step 3: Specific individual product prices
    out = re.sub(r"\(\s*,?(?:348|2,?348)(?:\.10)?\)", "($2,348.10)", out)
    out = re.sub(r"\(\s*,?(?:371|3,?371)(?:\.10)?\)", "($3,371.10)", out)
    out = re.sub(r"\(\s*,?(?:147|1,?147)(?:\.00)?\)", "($1,147.00)", out)
    out = re.sub(r"<td>\s*,?(?:348|2,?348)(?:\.10)?\s*</td>", "<td>$2,348.10</td>", out)
    out = re.sub(r"<td>\s*,?(?:371|3,?371)(?:\.10)?\s*</td>", "<td>$3,371.10</td>", out)
    out = re.sub(r"<td>\s*,?(?:147|1,?147)(?:\.00)?\s*</td>", "<td>$1,147.00</td>", out)
    out = re.sub(r"(?<=[(\s]),348(?:\.10)?", "$2,348.10", out)
    out = re.sub(r"(?<=[(\s]),371(?:\.10)?", "$3,371.10", out)
    out = re.sub(r"(?<=[(\s]),147(?:\.00)?", "$1,147.00", out)

    # Step 4: General broken prefix `.NN to ,<number>` pattern: e.g. `.00 to ,500`
    out = re.sub(r"(?<=[(\s])\.\d{2}\s+to\s+,?(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)", r"starting prices to $\1", out)

    # Step 5: General broken `( to ,<number>)`
    out = re.sub(r"\(\s*to\s*,?(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)\)", r"(up to $\1)", out)

    # Step 6: General leading comma without dollar sign in parens or text: `(,450.00)` -> `($450.00)`
    out = re.sub(r"\(\s*,(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)\)", r"($\1)", out)
    out = re.sub(r"<td>\s*,(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)\s*</td>", r"<td>$\1</td>", out)

    # Step 7: Missing '$' before numbers ending with .00 or currency format in table cells:
    def _fix_table_price(m):
        raw_val = m.group(1).replace(",", "")
        try:
            val_float = float(raw_val)
            return f"<td>${val_float:,.2f}</td>"
        except ValueError:
            return m.group(0)

    out = re.sub(r"<td>\s*(\d{2,6}\.\d{2})\s*</td>", _fix_table_price, out)

    def _fix_table_range(m):
        try:
            v1 = float(m.group(1).replace(",", ""))
            v2 = float(m.group(2).replace(",", ""))
            return f"<td>${v1:,.2f} to ${v2:,.2f}</td>"
        except ValueError:
            return m.group(0)

    out = re.sub(r"<td>\s*(\d{2,6}(?:\.\d{2})?)\s+to\s+(\d{2,6}(?:\.\d{2})?)\s*</td>", _fix_table_range, out)

    return out


class HtmlPostProcessor:
    """Post-processes raw Zbigtee `/preview` data into a clean Shopify Article payload."""

    def __init__(self, store: StoreConfig) -> None:
        self.store = store

    def process_preview_payload(self, raw_payload: Dict[str, Any]) -> PostProcessedArticle:
        title = (raw_payload.get("title") or "").strip()
        slug = (raw_payload.get("slug") or "").strip()
        meta_desc = heal_corrupted_prices((raw_payload.get("meta_description") or "").strip())
        raw_html = heal_corrupted_prices((raw_payload.get("body_html") or "").strip())
        raw_faq = raw_payload.get("faq_json_ld")
        faq_json_str = heal_corrupted_prices(
            json.dumps(raw_faq, ensure_ascii=False)
            if isinstance(raw_faq, dict)
            else str(raw_faq or "").strip()
        )
        shop_images: List[Dict[str, str]] = list(raw_payload.get("shop_images") or [])

        # Build lookup map by filename
        image_by_filename: Dict[str, Dict[str, str]] = {}
        for img in shop_images:
            src = (img.get("src") or "").strip()
            fname = (img.get("filename") or "").strip()
            if not fname and src:
                fname = src.split("/")[-1].split("?")[0]
            if fname and src:
                img_alt = (img.get("alt") or img.get("shows") or title).strip()
                image_by_filename[fname.lower()] = {"src": src, "alt": img_alt}

        resolved_missing: List[str] = []
        generated_svgs: List[str] = []
        unresolved_images: List[str] = []

        # 1. Strip any accidental <h1> tags so section/article.liquid remains the single H1
        raw_html = re.sub(r"<h1[^>]*>.*?</h1>", "", raw_html, flags=re.IGNORECASE | re.DOTALL)

        # 1b. Clean up raw LaTeX dimension strings (e.g. $14.2 \times 9.8$ -> 14.2 × 9.8; requires \times so prices are never stripped)
        raw_html = re.sub(
            r"\$(\d+(?:\.\d+)?(?:\s*\\times\s*\d+(?:\.\d+)?)+)\$",
            lambda m: re.sub(r"\s*\\times\s*", " × ", m.group(1)),
            raw_html,
        )
        raw_html = re.sub(r"\\times\b", "×", raw_html)
        raw_html = re.sub(r"\\approx\b", "≈", raw_html)

        # 2. Replace `<p>[IMAGE: filename - alt]</p>` or `<p>[IMAGE: placeholder]</p>` when mapped in shop_images;
        #    otherwise convert to `<figure data-missing-image="...">` so `ArticleImageService` can heal it contextually.
        pattern_bracket = re.compile(
            r"(?:<p>\s*)?\[IMAGE:\s*([^\]]+?)(?:\s+-\s+([^\]]+))?\]\s*(?:</p>)?",
            flags=re.IGNORECASE,
        )

        def _replace_bracket_image(match: re.Match) -> str:
            filename = (match.group(1) or "").strip()
            explicit_alt = (match.group(2) or "").strip()
            lower_name = filename.lower()
            if lower_name in image_by_filename:
                real_src = image_by_filename[lower_name]["src"]
                alt_text = explicit_alt or image_by_filename[lower_name].get("alt") or title
                safe_alt = html.escape(alt_text)
                resolved_missing.append(f"{filename} -> {real_src}")
                return (
                    f'<figure class="m5-figure">'
                    f'<img src="{real_src}" alt="{safe_alt}" loading="lazy">'
                    f"<figcaption>{safe_alt}</figcaption>"
                    f"</figure>"
                )
            unresolved_images.append(filename)
            return (
                f'<figure class="m5-figure" data-missing-image="{html.escape(filename)}" '
                f'data-hint-alt="{html.escape(explicit_alt)}"></figure>'
            )

        processed_html = pattern_bracket.sub(_replace_bracket_image, raw_html)

        # 3. Handle rendered `<figure>` blocks containing `Không ảnh nào trong kho khớp với mô tả.`
        soup = BeautifulSoup(processed_html, "html.parser")
        for fig in soup.find_all("figure"):
            fig_text = fig.get_text(" ", strip=True)
            if "Không ảnh nào trong kho khớp với mô tả" in fig_text or fig.has_attr("data-missing-image"):
                fname_candidate = fig.get("data-missing-image", "")
                if not fname_candidate:
                    for span in fig.find_all("span"):
                        st = span.get_text(strip=True)
                        if st.endswith((".jpg", ".jpeg", ".png", ".webp")):
                            fname_candidate = st
                            break
                alt_candidate = (
                    fig.get("data-hint-alt")
                    or fig_text.replace("Không ảnh nào trong kho khớp với mô tả.", "").replace(fname_candidate, "").strip()
                )
                lower_name = fname_candidate.lower()
                if lower_name and lower_name in image_by_filename:
                    real_src = image_by_filename[lower_name]["src"]
                    final_alt = alt_candidate or image_by_filename[lower_name].get("alt") or title
                    new_fig = BeautifulSoup(
                        f'<figure class="m5-figure">'
                        f'<img src="{real_src}" alt="{html.escape(final_alt)}" loading="lazy">'
                        f"<figcaption>{html.escape(final_alt)}</figcaption>"
                        f"</figure>",
                        "html.parser",
                    )
                    fig.replace_with(new_fig)
                    resolved_missing.append(f"{fname_candidate} -> {real_src}")
                else:
                    if (fname_candidate or alt_candidate) not in unresolved_images:
                        unresolved_images.append(fname_candidate or alt_candidate or "missing-figure-image")

        # 4. Deduplicate repeated product images in `<figure>` tags using unused `shop_images` (no hardcoded store filenames)
        used_srcs = set()
        for fig in soup.find_all("figure"):
            img = fig.find("img")
            if not img:
                continue
            if "m5-figure" not in (fig.get("class") or []):
                fig["class"] = list(fig.get("class") or []) + ["m5-figure"]
            src = (img.get("src") or "").strip()
            if src in used_srcs:
                replacement_src = None
                for item in shop_images:
                    cand_src = (item.get("src") or "").strip()
                    if cand_src and cand_src not in used_srcs:
                        replacement_src = cand_src
                        break
                if replacement_src:
                    img["src"] = replacement_src
                    src = replacement_src
            if src:
                used_srcs.add(src)

        # 5. Wrap all `<table>` elements in `.m5-table-wrap` for responsive editorial styling
        for tbl in soup.find_all("table"):
            parent = tbl.parent
            if not (parent and parent.name == "div" and "m5-table-wrap" in (parent.get("class") or [])):
                wrapper = soup.new_tag("div", attrs={"class": "m5-table-wrap"})
                tbl.wrap(wrapper)

        # 6. Normalize internal links matching `zbigtee_domain` or `normalized_shop` to canonical public domain
        target_domain = (self.store.resolved_public_domain or "https://wrydeco.com").rstrip("/")
        for a_tag in soup.find_all("a", href=True):
            href_val = a_tag["href"].strip()
            href_val = re.sub(
                r"^https?://[a-zA-Z0-9_-]+\.myshopify\.com(/.*)?$",
                rf"{target_domain}\1",
                href_val,
                flags=re.IGNORECASE,
            )
            if self.store.zbigtee_domain:
                href_val = re.sub(
                    rf"^https?://(?:www\.)?{re.escape(self.store.zbigtee_domain)}(/.*)?$",
                    rf"{target_domain}\1",
                    href_val,
                    flags=re.IGNORECASE,
                )
            if href_val.startswith(("/products/", "/collections/", "/blogs/", "/pages/")):
                href_val = f"{target_domain}{href_val}"
            a_tag["href"] = href_val

        # 7. Normalize FAQ headings, wrap raw FAQ questions/answers into .m5-faq-section/.m5-faq-item,
        #    and synchronize visible FAQ items with `FAQPage` JSON-LD schema
        for existing_style in soup.find_all("style"):
            existing_style.decompose()
        for existing_ld in soup.find_all("script", attrs={"type": "application/ld+json"}):
            if not faq_json_str:
                faq_json_str = existing_ld.get_text(strip=True)
            existing_ld.decompose()

        # Step 7a: Find any existing FAQ heading
        faq_heading = None
        for heading in soup.find_all(["h2", "h3"]):
            h_txt = heading.get_text(strip=True).lower()
            if "câu hỏi thường gặp" in h_txt or "frequently asked questions" in h_txt or h_txt == "faq":
                heading.string = "Frequently Asked Questions"
                heading["id"] = "faq"
                faq_heading = heading
                break

        # Step 7b: If an FAQ heading exists but items are not wrapped in .m5-faq-item, wrap raw siblings
        if faq_heading and not soup.select(".m5-faq-item"):
            raw_faq_sibs = []
            cur = faq_heading.next_sibling
            while cur:
                if hasattr(cur, "name") and cur.name:
                    if cur.name in ("h1", "h2"):
                        break
                    raw_faq_sibs.append(cur)
                cur = cur.next_sibling

            extracted_raw_faqs: List[Dict[str, str]] = []
            cur_q: Optional[str] = None
            cur_ans: List[str] = []

            for el in raw_faq_sibs:
                is_q = (
                    el.name in ("h3", "h4")
                    or (el.name == "p" and el.find("strong") and re.match(r"^\*?\s*(?:Q:|Question:)", el.get_text().strip(), re.IGNORECASE))
                )
                if is_q:
                    if cur_q and cur_ans:
                        extracted_raw_faqs.append({"question": cur_q, "answer": " ".join(cur_ans)})
                        cur_ans = []
                    cur_q = re.sub(r"^\*?\s*(?:Q:|Question:)\s*", "", el.get_text(" ", strip=True), flags=re.IGNORECASE)
                elif el.name == "p":
                    p_text = "".join(str(c) for c in el.contents).strip() or el.get_text(" ", strip=True)
                    if p_text:
                        cur_ans.append(p_text)

            if cur_q and cur_ans:
                extracted_raw_faqs.append({"question": cur_q, "answer": " ".join(cur_ans)})

            if extracted_raw_faqs:
                faq_html_parts = [
                    '<section class="m5-faq-section" aria-labelledby="faq">',
                    '  <h2 id="faq">Frequently Asked Questions</h2>',
                    '  <div class="m5-faq-list">',
                ]
                for item in extracted_raw_faqs:
                    safe_a = sanitize_faq_answer_html(item["answer"], target_domain=target_domain)
                    faq_html_parts.append(
                        f'    <div class="m5-faq-item">\n'
                        f"      <h3>{html.escape(item['question'])}</h3>\n"
                        f"      <p>{safe_a}</p>\n"
                        f"    </div>"
                    )
                faq_html_parts.append("  </div>\n</section>")
                new_faq_sec = BeautifulSoup("\n".join(faq_html_parts), "html.parser")

                for sib in raw_faq_sibs:
                    sib.decompose()
                faq_heading.replace_with(new_faq_sec)

        # Step 7c: Update any table of contents anchor pointing to previous FAQ anchor names
        for a_tag in soup.find_all("a", href=True):
            h_val = a_tag["href"].strip().lower()
            if h_val in ("#frequently-asked-questions", "#cau-hoi-thuong-gap"):
                a_tag["href"] = "#faq"

        # Step 8: Parse entities and ensure JSON-LD / visible items parity
        faq_entities: List[Dict[str, str]] = []
        if faq_json_str:
            try:
                faq_obj = json.loads(faq_json_str)
                for ent in faq_obj.get("mainEntity", []):
                    q_name = re.sub(r"^\*?\s*Q:\s*", "", (ent.get("name") or "").strip(), flags=re.IGNORECASE)
                    a_text = ((ent.get("acceptedAnswer") or {}).get("text") or "").strip()
                    if q_name and a_text:
                        faq_entities.append({"question": q_name, "answer": a_text})
            except Exception:
                pass

        # Extract visible `.m5-faq-item` if present in HTML
        visible_faq_items: List[Dict[str, str]] = []
        for item_div in soup.select(".m5-faq-item"):
            q_el = item_div.find(["h3", "h4", "strong"])
            p_el = item_div.find("p")
            if q_el and p_el:
                q_txt = re.sub(r"^\*?\s*Q:\s*", "", q_el.get_text(" ", strip=True), flags=re.IGNORECASE)
                a_txt = "".join(str(c) for c in p_el.contents).strip() or p_el.get_text(" ", strip=True)
                if q_txt and a_txt:
                    visible_faq_items.append({"question": q_txt, "answer": a_txt})

        # If visible FAQ exists, visible FAQ is the source of truth for JSON-LD parity
        if visible_faq_items:
            faq_entities = visible_faq_items

        has_faq_heading = any(
            "frequently asked questions" in h.get_text(strip=True).lower() or h.get("id") == "faq"
            for h in soup.find_all(["h2", "h3"])
        )
        if faq_entities and not has_faq_heading:
            for p_tag in soup.find_all("p"):
                p_txt = p_tag.get_text(strip=True).lower()
                if p_txt in ("contents", "on this page"):
                    nxt_list = p_tag.find_next_sibling(["ol", "ul"])
                    if nxt_list and nxt_list.find("a", href=re.compile(r"^#")) and not nxt_list.find("a", href="#faq"):
                        li_tag = soup.new_tag("li")
                        a_tag = soup.new_tag("a", href="#faq")
                        a_tag.string = "Frequently asked questions"
                        li_tag.append(a_tag)
                        nxt_list.append(li_tag)
                    break

            faq_html_parts = [
                '<section class="m5-faq-section" aria-labelledby="faq">',
                '  <h2 id="faq">Frequently Asked Questions</h2>',
                '  <div class="m5-faq-list">',
            ]
            for item in faq_entities:
                safe_a = sanitize_faq_answer_html(item['answer'], target_domain=target_domain)
                faq_html_parts.append(
                    f'    <div class="m5-faq-item">'
                    f"      <h3>{html.escape(item['question'])}</h3>"
                    f"      <p>{safe_a}</p>"
                    f"    </div>"
                )
            faq_html_parts.append("  </div>")
            faq_html_parts.append("</section>")
            soup.append(BeautifulSoup("\n".join(faq_html_parts), "html.parser"))

        # 8b. Normalize all internal links across the entire article (including newly appended FAQ) to target_domain
        for a_tag in soup.find_all("a", href=True):
            href_val = a_tag["href"].strip()
            href_val = re.sub(
                r"^https?://[a-zA-Z0-9_-]+\.myshopify\.com(/.*)?$",
                rf"{target_domain}\1",
                href_val,
                flags=re.IGNORECASE,
            )
            if self.store.zbigtee_domain:
                href_val = re.sub(
                    rf"^https?://(?:www\.)?{re.escape(self.store.zbigtee_domain)}(/.*)?$",
                    rf"{target_domain}\1",
                    href_val,
                    flags=re.IGNORECASE,
                )
            if href_val.startswith(("/products/", "/collections/", "/blogs/", "/pages/")):
                href_val = f"{target_domain}{href_val}"
            a_tag["href"] = href_val

        clean_faq_json = ""
        faq_count = len(faq_entities)
        if faq_entities:
            synced_faq_schema = {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": ent["question"],
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": sanitize_faq_answer_html(ent["answer"], target_domain=target_domain),
                        },
                    }
                    for ent in faq_entities
                ],
            }
            clean_faq_json = json.dumps(synced_faq_schema, ensure_ascii=False, indent=2)

        final_body_parts = [build_editorial_scoped_css(self.store.id), str(soup).strip()]
        if clean_faq_json:
            final_body_parts.append(
                f'<script type="application/ld+json">\n{clean_faq_json}\n</script>'
            )

        final_body_html = "\n\n".join(final_body_parts)

        # 9. Determine Featured Image (prefer explicit featured_image, then first shop_image, then first inline img)
        featured_image: Dict[str, str] = {"url": "", "altText": title}
        explicit_feat = raw_payload.get("featured_image")
        if isinstance(explicit_feat, dict) and (explicit_feat.get("url") or "").strip():
            featured_image = {
                "url": explicit_feat["url"].strip(),
                "altText": (explicit_feat.get("altText") or explicit_feat.get("alt") or title).strip(),
            }
        elif shop_images and (shop_images[0].get("src") or "").strip():
            featured_image = {
                "url": shop_images[0]["src"].strip(),
                "altText": (shop_images[0].get("alt") or shop_images[0].get("shows") or title).strip(),
            }
        else:
            first_img = soup.find("img")
            if first_img and first_img.get("src"):
                featured_image = {
                    "url": first_img["src"].strip(),
                    "altText": (first_img.get("alt") or title).strip(),
                }

        # 10. Determine Summary / Excerpt
        summary = meta_desc
        if not summary:
            first_p = soup.find("p")
            if first_p:
                summary = first_p.get_text(" ", strip=True)

        body_imgs = soup.find_all("img")
        word_count = compute_editorial_word_count(final_body_html)

        # 11. Sanity check for missing images and leftover Vietnamese UI markers
        warnings: List[str] = []
        for missing_name in unresolved_images:
            warnings.append(
                f"Thiếu ảnh trong nội dung bài viết: không tìm thấy ảnh '{missing_name}' trong shop_images (cần chữa bằng ArticleImageService)."
            )
        if not body_imgs:
            warnings.append("Bài viết không có bất kỳ thẻ ảnh <img> nào trong nội dung.")
        if soup.find("svg"):
            warnings.append(
                "Phát hiện thẻ <svg> trong nội dung bài viết (không được phép render SVG sơ đồ; vui lòng thay bằng ảnh sản phẩm thật từ store)."
            )
        if not featured_image.get("url"):
            warnings.append("Bài viết thiếu ảnh đại diện (Featured Hero Image).")
        for marker in VIETNAMESE_ERROR_MARKERS:
            if marker.lower() in final_body_html.lower():
                warnings.append(f"Detected leftover Vietnamese string: '{marker}'")
        if "[IMAGE:" in final_body_html and not unresolved_images:
            warnings.append("Detected unresolved [IMAGE: ...] placeholder in final HTML.")

        return PostProcessedArticle(
            store_id=self.store.id,
            content_id=raw_payload.get("content_id") or slug,
            title=title,
            handle=slug,
            summary=summary,
            body_html=final_body_html,
            seo_title=title,
            seo_description=meta_desc or summary[:155],
            author=self.store.default_author or f"{self.store.name} Studio",
            featured_image=featured_image,
            faq_items_count=faq_count,
            word_count=word_count,
            body_image_count=len(body_imgs),
            media_manifest_path="",
            resolved_missing_images=resolved_missing,
            generated_svg_diagrams=generated_svgs,
            warnings=warnings,
        )

    def normalize_faq_section_and_schema(self, soup: BeautifulSoup) -> Tuple[BeautifulSoup, int]:
        """
        Normalize FAQ headings and wrap raw FAQ questions/answers into .m5-faq-section/.m5-faq-item,
        and ensure matching FAQPage JSON-LD schema is present.
        """
        target_domain = (self.store.resolved_public_domain or "https://wrydeco.com").rstrip("/")
        faq_heading = None
        for heading in soup.find_all(["h2", "h3"]):
            h_txt = heading.get_text(strip=True).lower()
            if "câu hỏi thường gặp" in h_txt or "frequently asked questions" in h_txt or h_txt == "faq":
                heading.string = "Frequently Asked Questions"
                heading["id"] = "faq"
                faq_heading = heading
                break

        if faq_heading and not soup.select(".m5-faq-item"):
            raw_faq_sibs = []
            cur = faq_heading.next_sibling
            while cur:
                if hasattr(cur, "name") and cur.name:
                    if cur.name in ("h1", "h2"):
                        break
                    raw_faq_sibs.append(cur)
                cur = cur.next_sibling

            extracted_raw_faqs: List[Dict[str, str]] = []
            cur_q: Optional[str] = None
            cur_ans: List[str] = []

            for el in raw_faq_sibs:
                is_q = (
                    el.name in ("h3", "h4")
                    or (el.name == "p" and el.find("strong") and re.match(r"^\*?\s*(?:Q:|Question:)", el.get_text().strip(), re.IGNORECASE))
                )
                if is_q:
                    if cur_q and cur_ans:
                        extracted_raw_faqs.append({"question": cur_q, "answer": " ".join(cur_ans)})
                        cur_ans = []
                    cur_q = re.sub(r"^\*?\s*(?:Q:|Question:)\s*", "", el.get_text(" ", strip=True), flags=re.IGNORECASE)
                elif el.name == "p":
                    p_text = "".join(str(c) for c in el.contents).strip() or el.get_text(" ", strip=True)
                    if p_text:
                        cur_ans.append(p_text)

            if cur_q and cur_ans:
                extracted_raw_faqs.append({"question": cur_q, "answer": " ".join(cur_ans)})

            if extracted_raw_faqs:
                faq_html_parts = [
                    '<section class="m5-faq-section" aria-labelledby="faq">',
                    '  <h2 id="faq">Frequently Asked Questions</h2>',
                    '  <div class="m5-faq-list">',
                ]
                for item in extracted_raw_faqs:
                    safe_a = sanitize_faq_answer_html(item["answer"], target_domain=target_domain)
                    faq_html_parts.append(
                        f'    <div class="m5-faq-item">\n'
                        f"      <h3>{html.escape(item['question'])}</h3>\n"
                        f"      <p>{safe_a}</p>\n"
                        f"    </div>"
                    )
                faq_html_parts.append("  </div>\n</section>")
                new_faq_sec = BeautifulSoup("\n".join(faq_html_parts), "html.parser")

                for sib in raw_faq_sibs:
                    sib.decompose()
                faq_heading.replace_with(new_faq_sec)

        for a_tag in soup.find_all("a", href=True):
            h_val = a_tag["href"].strip().lower()
            if h_val in ("#frequently-asked-questions", "#cau-hoi-thuong-gap"):
                a_tag["href"] = "#faq"

        visible_faq_items: List[Dict[str, str]] = []
        for item_div in soup.select(".m5-faq-item"):
            q_el = item_div.find(["h3", "h4", "strong"])
            p_el = item_div.find("p")
            if q_el and p_el:
                q_txt = re.sub(r"^\*?\s*(?:Q:|Question:)\s*", "", q_el.get_text(" ", strip=True), flags=re.IGNORECASE)
                a_txt = "".join(str(c) for c in p_el.contents).strip() or p_el.get_text(" ", strip=True)
                if q_txt and a_txt:
                    visible_faq_items.append({"question": q_txt, "answer": a_txt})

        if visible_faq_items:
            for existing_ld in soup.find_all("script", attrs={"type": "application/ld+json"}):
                existing_ld.decompose()
            synced_faq_schema = {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": ent["question"],
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": sanitize_faq_answer_html(ent["answer"], target_domain=target_domain),
                        },
                    }
                    for ent in visible_faq_items
                ],
            }
            clean_faq_json = json.dumps(synced_faq_schema, ensure_ascii=False, indent=2)
            ld_tag = soup.new_tag("script", attrs={"type": "application/ld+json"})
            ld_tag.string = f"\n{clean_faq_json}\n"
            soup.append(ld_tag)

        return soup, len(visible_faq_items)

    def refresh_warnings_and_counts(self, article: PostProcessedArticle) -> PostProcessedArticle:
        """Re-evaluate warnings, word_count, and body_image_count after image healing or claim sanitization."""
        soup = BeautifulSoup(article.body_html or "", "html.parser")
        soup, faq_count = self.normalize_faq_section_and_schema(soup)
        article.body_html = str(soup)
        if faq_count > 0:
            article.faq_items_count = faq_count
        body_imgs = [
            img for img in soup.find_all("img") if (img.get("src") or "").strip()
        ]
        article.body_image_count = len(body_imgs)
        article.word_count = compute_editorial_word_count(article.body_html)

        warnings: List[str] = []
        if soup.find("figure", attrs={"data-missing-image": True}) or "[IMAGE:" in article.body_html:
            warnings.append("Phát hiện placeholder ảnh chưa được thay bằng ảnh sản phẩm thật.")
        if len(body_imgs) < 4:
            warnings.append(
                f"Số lượng ảnh trong thân bài ({len(body_imgs)}) chưa đạt ngưỡng 4–7 ảnh sản phẩm."
            )
        elif len(body_imgs) > 7:
            warnings.append(
                f"Số lượng ảnh trong thân bài ({len(body_imgs)}) vượt quá ngưỡng tối đa 7 ảnh."
            )
        if soup.find("svg"):
            warnings.append("Phát hiện thẻ <svg> trong nội dung bài viết.")
        if not (article.featured_image or {}).get("url"):
            warnings.append("Bài viết thiếu ảnh đại diện (Featured Hero Image).")
        for marker in VIETNAMESE_ERROR_MARKERS:
            if marker.lower() in article.body_html.lower():
                warnings.append(f"Detected leftover Vietnamese string: '{marker}'")
        article.warnings = warnings
        return article

    def save_processed_article(
        self, article: PostProcessedArticle, output_root: Optional[Path] = None
    ) -> Dict[str, str]:
        if output_root is None:
            output_root = Path(__file__).resolve().parent / "output" / self.store.id
        output_root.mkdir(parents=True, exist_ok=True)

        json_path = output_root / f"{article.handle}_processed.json"
        html_path = output_root / f"{article.handle}_processed.html"

        json_path.write_text(
            json.dumps(article.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        html_path.write_text(article.body_html, encoding="utf-8")
        return {
            "json_path": str(json_path),
            "html_path": str(html_path),
        }
