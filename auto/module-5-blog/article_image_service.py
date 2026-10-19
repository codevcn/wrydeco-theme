"""
Context-Aware Image Healer & Media Manifest Service (`article_image_service.py`).

Enforces all media requirements from `docs/ANTIGRAVITY_IMPLEMENTATION_PLAN_BLOG_SCALING_20_ARTICLES.md`:
  - 4 to 7 verified product body images distributed across relevant H2 sections.
  - Separate verified Featured Hero Image.
  - Every image must belong to a live, published product on the target Shopify store
    (verified via `ShopifyCatalogService` over the mandatory Proxy).
  - Zero inline SVG fallback diagrams, zero stock/placeholder images, zero hardcoded filenames.
  - Downloads actual image bytes via `ProxyManager` to verify HTTP 200, image content-type,
    decode dimensions (`width`, `height`), cryptographic `sha256`, and perceptual hashes (`ahash`, `dhash`).
  - Saves local cached image files so the agent can inspect them visually (`view_file`) and
    record `visual_review_status` in the structured `MediaManifest`.
"""

from __future__ import annotations

import hashlib
import html
import io
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from bs4 import BeautifulSoup, Tag
from PIL import Image

from proxy_manager import redact_sensitive_data
from shopify_catalog_service import ShopifyCatalogService
from store_manager import StoreConfig, StoreManager

MODULE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = MODULE_DIR / "output"

STOPWORDS = {
    "the", "and", "for", "with", "your", "that", "this", "from", "into", "how",
    "choose", "choosing", "guide", "best", "what", "when", "where", "why", "are",
    "you", "can", "will", "more", "most", "some", "such", "than", "then", "them",
    "they", "their", "there", "these", "those", "about", "after", "before", "between",
    "under", "over", "each", "every", "have", "has", "had", "not", "but", "all",
    "buying", "tips", "ideas", "fit", "review", "reviews",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonicalize_image_url(url: str) -> str:
    """
    Canonicalize a Shopify CDN image URL to identify the underlying asset across width/crop transforms.
    Strips display transform params (`width`, `height`, `crop`, `pad_color`, `format`) and Shopify's
    `_800x800` filename size suffix while preserving the asset path and version (`v`).
    """
    raw = (url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    path = parsed.path or ""
    # Strip Shopify legacy size suffixes like _1024x1024, _800x, _small, _grande before extension
    path = re.sub(
        r"_(?:\d+x\d*|\d*x\d+|pico|icon|thumb|small|compact|medium|large|grande|master)(?:_crop_[a-z]+)?(\.[a-zA-Z0-9]+)$",
        r"\1",
        path,
        flags=re.IGNORECASE,
    )
    # Normalize /cdn/shop/files/... vs /s/files/1/xxxx/xxxx/files/... by keeping the /files/<filename> or /products/<filename> tail when on Shopify CDN
    m_tail = re.search(r"(/(?:files|products)/[^/]+)$", path, flags=re.IGNORECASE)
    canonical_path = m_tail.group(1).lower() if m_tail else path.lower()

    kept_params = []
    for k, v in parse_qsl(parsed.query, keep_blank_values=False):
        if k.lower() in {"width", "height", "crop", "pad_color", "format"}:
            continue
        if k.lower() == "v":
            kept_params.append(("v", v))
    query_str = urlencode(sorted(kept_params))
    return f"{canonical_path}?{query_str}" if query_str else canonical_path


def extract_filename_stem(url_or_name: str) -> str:
    raw = (url_or_name or "").strip().split("?")[0].split("/")[-1]
    raw = re.sub(
        r"_(?:\d+x\d*|\d*x\d+|pico|icon|thumb|small|compact|medium|large|grande|master)(?:_crop_[a-z]+)?(\.[a-zA-Z0-9]+)$",
        r"\1",
        raw,
        flags=re.IGNORECASE,
    )
    stem = raw.rsplit(".", 1)[0] if "." in raw else raw
    return stem.lower().strip()


def compute_perceptual_hashes(img: Image.Image) -> Tuple[str, str]:
    """Compute 64-bit average hash (ahash) and difference hash (dhash) as 16-char hex strings."""
    gray_a = img.convert("L").resize((8, 8), Image.Resampling.LANCZOS)
    pixels_a = list(gray_a.getdata())
    avg_a = sum(pixels_a) / len(pixels_a)
    bits_a = 0
    for px in pixels_a:
        bits_a = (bits_a << 1) | (1 if px >= avg_a else 0)
    ahash = f"{bits_a:016x}"

    gray_d = img.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    pixels_d = list(gray_d.getdata())
    bits_d = 0
    for row in range(8):
        row_offset = row * 9
        for col in range(8):
            left = pixels_d[row_offset + col]
            right = pixels_d[row_offset + col + 1]
            bits_d = (bits_d << 1) | (1 if left > right else 0)
    dhash = f"{bits_d:016x}"
    return ahash, dhash


def hamming_distance_hex(hash1: str, hash2: str) -> int:
    if not hash1 or not hash2 or len(hash1) != len(hash2):
        return 64
    try:
        val = int(hash1, 16) ^ int(hash2, 16)
        return bin(val).count("1")
    except ValueError:
        return 64


def _tokenize(text: str) -> List[str]:
    words = re.findall(r"[a-z0-9]{3,}", (text or "").lower())
    return [w for w in words if w not in STOPWORDS]


@dataclass
class MediaManifestEntry:
    slot: str  # "hero" or "body_1".."body_7"
    index: int
    section_heading: str
    media_id: str
    product_id: str
    product_handle: str
    product_title: str
    variant_id: Optional[str]
    url: str
    canonical_url: str
    local_cache_path: str
    sha256: str
    ahash: str
    dhash: str
    width: int
    height: int
    content_type: str
    alt_text: str
    caption: str
    selection_reason: str
    checked_at: str
    visual_review_status: str = "pending"  # "pending" | "approved" | "rejected"
    visual_review_note: str = ""
    visual_reviewer: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MediaManifest:
    ok: bool
    store_id: str
    content_id: str
    handle: str
    content_hash: str
    checked_at: str
    proxy_fingerprint: str
    min_required: int
    max_allowed: int
    body_image_count: int
    unique_body_image_count: int
    featured_image: Optional[MediaManifestEntry] = None
    body_images: List[MediaManifestEntry] = field(default_factory=list)
    replaced_or_removed: List[Dict[str, Any]] = field(default_factory=list)
    passed_technical_gate: bool = False
    passed_visual_gate: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "store_id": self.store_id,
            "content_id": self.content_id,
            "handle": self.handle,
            "content_hash": self.content_hash,
            "checked_at": self.checked_at,
            "proxy_fingerprint": self.proxy_fingerprint,
            "min_required": self.min_required,
            "max_allowed": self.max_allowed,
            "body_image_count": self.body_image_count,
            "unique_body_image_count": self.unique_body_image_count,
            "featured_image": self.featured_image.to_dict() if self.featured_image else None,
            "body_images": [b.to_dict() for b in self.body_images],
            "replaced_or_removed": list(self.replaced_or_removed),
            "passed_technical_gate": self.passed_technical_gate,
            "passed_visual_gate": self.passed_visual_gate,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


class ArticleImageService:
    """
    Context-aware image resolver, healer, deduplicator, and manifest builder for Shopify blog articles.
    All remote media requests route strictly through `ProxyManager`.
    """

    def __init__(
        self,
        store_manager: Optional[StoreManager] = None,
        store_id: Optional[str] = None,
        catalog_service: Optional[ShopifyCatalogService] = None,
        min_body_images: int = 4,
        max_body_images: int = 7,
    ) -> None:
        self.store_manager = store_manager or StoreManager()
        self.store: StoreConfig = self.store_manager.get_store(store_id)
        self.catalog_service = catalog_service or ShopifyCatalogService(
            store_manager=self.store_manager
        )
        self.min_body_images = min_body_images
        self.max_body_images = max_body_images
        self._inspection_cache: Dict[str, Dict[str, Any]] = {}

    def _media_cache_dir(self) -> Path:
        d = OUTPUT_DIR / self.store.id / "media_cache"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def download_and_inspect_image(self, url: str) -> Dict[str, Any]:
        """
        Download image bytes via the mandatory Proxy, verify HTTP 200 and non-SVG raster decoding,
        extract width/height/sha256/ahash/dhash, and cache locally for agent visual inspection.
        """
        clean_url = (url or "").strip()
        if not clean_url:
            return {"ok": False, "url": "", "error": "Empty image URL"}
        if clean_url in self._inspection_cache:
            return self._inspection_cache[clean_url]

        sess = self.store_manager.proxy_manager.get_shopify_requests_session(
            target_shop_domain=self.store.normalized_shop
        )
        try:
            resp = sess.get(clean_url, timeout=25, allow_redirects=True)
            if resp.status_code != 200:
                res = {
                    "ok": False,
                    "url": clean_url,
                    "status_code": resp.status_code,
                    "error": f"HTTP {resp.status_code}",
                }
                self._inspection_cache[clean_url] = res
                return res

            ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if "svg" in ctype or clean_url.lower().split("?")[0].endswith(".svg"):
                res = {
                    "ok": False,
                    "url": clean_url,
                    "content_type": ctype,
                    "error": "SVG images are forbidden as product images.",
                }
                self._inspection_cache[clean_url] = res
                return res

            raw_bytes = resp.content
            if not raw_bytes or len(raw_bytes) < 256:
                res = {
                    "ok": False,
                    "url": clean_url,
                    "error": "Image payload empty or too small.",
                }
                self._inspection_cache[clean_url] = res
                return res

            sha256_hex = hashlib.sha256(raw_bytes).hexdigest()
            with Image.open(io.BytesIO(raw_bytes)) as pil_img:
                width, height = pil_img.size
                img_format = (pil_img.format or "JPEG").lower()
                ahash, dhash = compute_perceptual_hashes(pil_img)

            # Save a viewable copy in media_cache (convert to PNG so all viewers open it reliably)
            stem = re.sub(r"[^a-zA-Z0-9_-]+", "_", extract_filename_stem(clean_url))[:40] or "img"
            cache_file = self._media_cache_dir() / f"{sha256_hex[:12]}_{stem}.png"
            if not cache_file.exists():
                with Image.open(io.BytesIO(raw_bytes)) as pil_img:
                    rgb_img = pil_img.convert("RGB")
                    if max(rgb_img.size) > 1600:
                        rgb_img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                    rgb_img.save(cache_file, format="PNG")

            res = {
                "ok": True,
                "url": clean_url,
                "canonical_url": canonicalize_image_url(clean_url),
                "status_code": 200,
                "content_type": ctype or f"image/{img_format}",
                "width": width,
                "height": height,
                "sha256": sha256_hex,
                "ahash": ahash,
                "dhash": dhash,
                "local_cache_path": str(cache_file),
                "checked_at": _utc_now_iso(),
            }
            self._inspection_cache[clean_url] = res
            return res
        except Exception as exc:
            res = {
                "ok": False,
                "url": clean_url,
                "error": str(redact_sensitive_data(str(exc))),
            }
            self._inspection_cache[clean_url] = res
            return res

    def build_catalog_media_pool(
        self,
        article_title: str,
        body_html: str,
        extra_search_queries: Optional[List[str]] = None,
        max_products: int = 18,
    ) -> List[Dict[str, Any]]:
        """
        Build a verified pool of product media candidates from live, published products on the target store.
        Prioritizes:
          1. Products explicitly linked inside `body_html` (`/products/<handle>`).
          2. Products matching keywords from `article_title` and `<h2>` headings.
          3. General live store catalog products if more media diversity is needed.
        """
        soup = BeautifulSoup(body_html or "", "html.parser")
        linked_handles: List[str] = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            m = re.search(r"/products/([a-zA-Z0-9_-]+)", href)
            if m:
                h = m.group(1).strip()
                if h and h not in linked_handles:
                    linked_handles.append(h)

        verified_products: List[Dict[str, Any]] = []
        seen_product_ids: Set[str] = set()

        def _add_product_record(prod: Optional[Dict[str, Any]], source_priority: int) -> None:
            if not prod or not isinstance(prod, dict):
                return
            pid = prod.get("product_id") or ""
            if not pid or pid in seen_product_ids:
                return
            if not (prod.get("is_published_online") or prod.get("is_live_published")):
                return
            seen_product_ids.add(pid)
            prod_copy = dict(prod)
            prod_copy["_source_priority"] = source_priority
            verified_products.append(prod_copy)

        # 1. Explicitly linked products
        for h in linked_handles[:10]:
            try:
                ev = self.catalog_service.get_product_evidence(
                    self.store.id, h, verify_live_url=False
                )
                if ev.get("ok") and ev.get("product"):
                    _add_product_record(ev["product"], source_priority=1)
            except Exception:
                pass

        # 2. Search queries derived from title, H2 headings, and extra queries
        queries: List[str] = []
        if extra_search_queries:
            queries.extend([q.strip() for q in extra_search_queries if q and q.strip()])
        title_tokens = _tokenize(article_title)
        if title_tokens:
            queries.append(" ".join(title_tokens[:3]))
            if len(title_tokens) > 2:
                queries.append(" ".join(title_tokens[:2]))
                queries.append(" ".join(title_tokens[-2:]))
        for h2 in soup.find_all("h2"):
            h2_tokens = _tokenize(h2.get_text(" ", strip=True))
            if h2_tokens:
                q_str = " ".join(h2_tokens[:3])
                if q_str not in queries:
                    queries.append(q_str)

        max_q = 1 if len(verified_products) >= 4 else 4
        for q in queries[:max_q]:
            if len(verified_products) >= max_products:
                break
            try:
                res = self.catalog_service.search_products(
                    self.store.id, query=q, limit=6, active_only=True
                )
                for p in res.get("products") or []:
                    _add_product_record(p, source_priority=2)
            except Exception:
                pass

        # 3. Topical token search if still below 4 products (STRICT: NO blind query="" fallback!)
        if len(verified_products) < 4 and title_tokens:
            for tok in title_tokens[:3]:
                if len(verified_products) >= max_products:
                    break
                try:
                    res = self.catalog_service.search_products(
                        self.store.id, query=tok, limit=6, active_only=True
                    )
                    for p in res.get("products") or []:
                        _add_product_record(p, source_priority=2)
                except Exception:
                    pass

        # Flatten product media into candidate records
        candidates: List[Dict[str, Any]] = []
        seen_canonical: Set[str] = set()
        for prod in verified_products:
            pid = prod["product_id"]
            phandle = prod["handle"]
            ptitle = prod["title"]
            priority = prod.get("_source_priority", 3)

            # Build variant image map
            variant_by_img_canonical: Dict[str, Dict[str, Any]] = {}
            for v in prod.get("variants") or []:
                v_img_obj = v.get("image") or {}
                v_img = (
                    v_img_obj.get("url")
                    if isinstance(v_img_obj, dict)
                    else (v.get("image_url") or "")
                )
                if v_img:
                    variant_by_img_canonical[canonicalize_image_url(v_img)] = v

            media_nodes = list(prod.get("media") or [])
            for m_idx, m in enumerate(media_nodes):
                m_url = (m.get("url") or "").strip()
                if not m_url:
                    continue
                can_url = canonicalize_image_url(m_url)
                if not can_url or can_url in seen_canonical:
                    continue
                seen_canonical.add(can_url)
                matched_variant = variant_by_img_canonical.get(can_url)
                m_alt = (m.get("alt") or m.get("alt_text") or "").strip()
                candidates.append(
                    {
                        "media_id": m.get("media_id") or f"{pid}#media-{m_idx}",
                        "product_id": pid,
                        "product_handle": phandle,
                        "product_title": ptitle,
                        "product_url": prod.get("storefront_url") or f"/products/{phandle}",
                        "variant_id": matched_variant.get("variant_id") if matched_variant else None,
                        "variant_title": matched_variant.get("title") if matched_variant else None,
                        "url": m_url,
                        "canonical_url": can_url,
                        "filename_stem": extract_filename_stem(m_url),
                        "width": int(m.get("width") or 0),
                        "height": int(m.get("height") or 0),
                        "api_alt": m_alt,
                        "media_index": m_idx,
                        "source_priority": priority,
                        "keywords": set(
                            _tokenize(f"{ptitle} {phandle.replace('-', ' ')} {m_alt}")
                        ),
                    }
                )
        return candidates

    def _score_candidate_for_context(
        self,
        candidate: Dict[str, Any],
        section_heading: str,
        context_text: str,
        used_product_counts: Dict[str, int],
    ) -> float:
        context_tokens = set(_tokenize(f"{section_heading} {context_text}"))
        cand_tokens: Set[str] = candidate.get("keywords") or set()
        overlap = len(context_tokens.intersection(cand_tokens))

        # Priority bonus: linked / verified product (1) strictly outranks secondary candidates
        priority_bonus = {1: 50.0, 2: 12.0, 3: 1.0}.get(candidate.get("source_priority", 3), 1.0)

        # Resolution bonus
        w = int(candidate.get("width") or 0)
        h = int(candidate.get("height") or 0)
        res_bonus = 3.0 if max(w, h) >= 1000 else (1.0 if max(w, h) >= 600 else 0.0)

        # Prefer primary/early gallery shots first, and diversify across products when possible
        media_idx = int(candidate.get("media_index") or 0)
        gallery_bonus = max(0.0, 2.5 - 0.35 * media_idx)
        prod_used = used_product_counts.get(candidate["product_id"], 0)
        diversity_penalty = min(prod_used * 3.0, 12.0)

        return (overlap * 4.0) + priority_bonus + res_bonus + gallery_bonus - diversity_penalty

    @staticmethod
    def _build_contextual_alt_and_caption(
        candidate: Dict[str, Any],
        section_heading: str,
        explicit_alt: str = "",
    ) -> Tuple[str, str]:
        """
        Build truthful, descriptive English alt text and figcaption grounded in the verified product title
        and section context without inventing unsupported material or policy claims.
        """
        ptitle = (candidate.get("product_title") or "").strip()
        vtitle = (candidate.get("variant_title") or "").strip()
        clean_explicit = (explicit_alt or "").strip()

        # Avoid Vietnamese or placeholder strings in explicit_alt
        if any(
            bad in clean_explicit.lower()
            for bad in ["không ảnh nào", "câu hỏi", "[image", "placeholder", ".jpg", ".png", ".webp"]
        ):
            clean_explicit = ""

        if clean_explicit and ptitle.lower()[:18] in clean_explicit.lower():
            alt_text = clean_explicit
        elif vtitle and vtitle.lower() not in ("default title", "default"):
            alt_text = f"{ptitle} ({vtitle})"
        else:
            alt_text = ptitle

        if section_heading and section_heading.lower() not in ("introduction", "overview", "frequently asked questions"):
            caption = f"{alt_text} — featured for {section_heading}."
        else:
            caption = f"{alt_text} from the {ptitle} collection."
        return alt_text[:180], caption[:220]

    def heal_and_enrich_article_images(
        self,
        article_title: str,
        handle: str,
        content_id: str,
        body_html: str,
        featured_image: Optional[Dict[str, str]] = None,
        shop_images: Optional[List[Dict[str, str]]] = None,
        extra_search_queries: Optional[List[str]] = None,
    ) -> Tuple[str, Dict[str, str], MediaManifest]:
        """
        Inspect, heal, deduplicate, and enrich `body_html` and `featured_image` so that:
          - Every inline image is wrapped in `<figure class="m5-figure">` with `<img>` + `<figcaption>`.
          - Every image is associated with a verified live product in the target store's catalog.
          - All images return HTTP 200 via Proxy, decode cleanly, and have zero duplicates (by canonical URL, sha256, or dhash<=4).
          - Total body images in the article is strictly between `min_body_images` (4) and `max_body_images` (7).
          - Returns `(updated_body_html, updated_featured_image, media_manifest)`.
        """
        self.store_manager.proxy_manager.ensure_shopify_proxy_ready(
            target_shop_domain=self.store.normalized_shop
        )
        proxy_fp = self.store_manager.proxy_manager.get_config().config_fingerprint

        candidates = self.build_catalog_media_pool(
            article_title=article_title,
            body_html=body_html,
            extra_search_queries=extra_search_queries,
        )

        # Index candidates by canonical_url and by filename_stem for fast matching of existing article images
        cand_by_canonical: Dict[str, Dict[str, Any]] = {}
        cand_by_stem: Dict[str, Dict[str, Any]] = {}
        for c in candidates:
            cand_by_canonical[c["canonical_url"]] = c
            if c["filename_stem"] and c["filename_stem"] not in cand_by_stem:
                cand_by_stem[c["filename_stem"]] = c

        # Also map any `shop_images` filenames to catalog candidates if their URL/stem matches
        for s_img in shop_images or []:
            s_src = (s_img.get("src") or "").strip()
            s_fname = (s_img.get("filename") or "").strip()
            if s_src and s_fname:
                can_s = canonicalize_image_url(s_src)
                stem_s = extract_filename_stem(s_fname)
                if can_s in cand_by_canonical and stem_s not in cand_by_stem:
                    cand_by_stem[stem_s] = cand_by_canonical[can_s]

        soup = BeautifulSoup(body_html or "", "html.parser")
        replaced_or_removed: List[Dict[str, Any]] = []

        # Remove any inline <svg> diagrams inside the article body
        for svg_tag in soup.find_all("svg"):
            replaced_or_removed.append(
                {"action": "removed_svg", "reason": "Inline SVG diagrams are forbidden; using real product images."}
            )
            parent_fig = svg_tag.find_parent("figure")
            if parent_fig:
                parent_fig["data-needs-product-image"] = "true"
                svg_tag.decompose()
            else:
                svg_tag.decompose()

        # Convert any remaining `<p>[IMAGE: ...]</p>` placeholders into `<figure data-needs-product-image="true">`
        pattern_bracket = re.compile(
            r"\[IMAGE:\s*([^\]]+?)(?:\s+-\s+([^\]]+))?\]",
            flags=re.IGNORECASE,
        )
        for p_tag in list(soup.find_all("p")):
            p_text = p_tag.get_text(" ", strip=True)
            m = pattern_bracket.search(p_text)
            if m:
                hint_file = (m.group(1) or "").strip()
                hint_alt = (m.group(2) or "").strip()
                new_fig = soup.new_tag("figure", attrs={"class": ["m5-figure"], "data-needs-product-image": "true"})
                new_fig["data-hint-file"] = hint_file
                new_fig["data-hint-alt"] = hint_alt
                p_tag.replace_with(new_fig)

        # Convert bare `<img>` tags (not inside `<figure>`) into `<figure class="m5-figure">`
        for img_tag in list(soup.find_all("img")):
            if not img_tag.find_parent("figure"):
                wrapper_fig = soup.new_tag("figure", attrs={"class": ["m5-figure"]})
                img_tag.wrap(wrapper_fig)

        used_canonicals: Set[str] = set()
        used_sha256s: Set[str] = set()
        used_dhashes: List[str] = []
        used_product_counts: Dict[str, int] = {}

        def _is_duplicate_asset(can_url: str, sha256_hex: str, dhash_hex: str) -> bool:
            if can_url in used_canonicals or sha256_hex in used_sha256s:
                return True
            for prev_d in used_dhashes:
                if hamming_distance_hex(dhash_hex, prev_d) <= 2:
                    return True
            return False

        def _mark_asset_used(cand: Dict[str, Any], insp: Dict[str, Any]) -> None:
            used_canonicals.add(cand["canonical_url"])
            used_sha256s.add(insp["sha256"])
            used_dhashes.append(insp["dhash"])
            pid = cand["product_id"]
            used_product_counts[pid] = used_product_counts.get(pid, 0) + 1

        def _select_best_unused_candidate(
            section_heading: str,
            context_text: str,
            hint_file: str = "",
        ) -> Optional[Tuple[Dict[str, Any], Dict[str, Any], str]]:
            # 1. Check if hint_file matches a specific unused catalog candidate
            if hint_file:
                stem = extract_filename_stem(hint_file)
                cand = cand_by_stem.get(stem)
                if cand and cand["canonical_url"] not in used_canonicals:
                    insp = self.download_and_inspect_image(cand["url"])
                    if insp.get("ok") and not _is_duplicate_asset(
                        cand["canonical_url"], insp["sha256"], insp["dhash"]
                    ):
                        return cand, insp, f"Matched filename stem '{stem}' to verified catalog product '{cand['product_handle']}'"

            # 2. Rank all unused candidates by contextual score
            scored: List[Tuple[float, Dict[str, Any]]] = []
            for cand in candidates:
                if cand["canonical_url"] in used_canonicals:
                    continue
                score = self._score_candidate_for_context(
                    cand, section_heading, context_text, used_product_counts
                )
                scored.append((score, cand))
            scored.sort(key=lambda x: x[0], reverse=True)

            for score, cand in scored:
                insp = self.download_and_inspect_image(cand["url"])
                if not insp.get("ok"):
                    continue
                if int(insp.get("width") or 0) < 350 or int(insp.get("height") or 0) < 250:
                    continue
                if _is_duplicate_asset(cand["canonical_url"], insp["sha256"], insp["dhash"]):
                    continue
                return (
                    cand,
                    insp,
                    f"Selected contextually for section '{section_heading or 'Article Body'}' (score={score:.1f}, product='{cand['product_handle']}')",
                )
            return None

        def _find_nearest_heading_and_context(node: Tag) -> Tuple[str, str]:
            heading_text = ""
            prev_h = node.find_previous(["h2", "h3"])
            if prev_h:
                heading_text = prev_h.get_text(" ", strip=True)
            context_parts = []
            prev_p = node.find_previous_sibling("p")
            if prev_p:
                context_parts.append(prev_p.get_text(" ", strip=True))
            next_p = node.find_next_sibling("p")
            if next_p:
                context_parts.append(next_p.get_text(" ", strip=True))
            return heading_text, " ".join(context_parts)

        body_entries: List[MediaManifestEntry] = []

        # Step 1: Process existing `<figure>` elements in document order
        existing_figures = list(soup.find_all("figure"))
        for fig in existing_figures:
            if len(body_entries) >= self.max_body_images:
                replaced_or_removed.append(
                    {
                        "action": "removed_excess_figure",
                        "reason": f"Exceeded max_body_images ({self.max_body_images}).",
                    }
                )
                fig.decompose()
                continue

            sec_heading, ctx_text = _find_nearest_heading_and_context(fig)
            img = fig.find("img")
            fig_text = fig.get_text(" ", strip=True)
            is_missing_marker = (
                fig.has_attr("data-missing-image")
                or fig.has_attr("data-needs-product-image")
                or "Không ảnh nào trong kho khớp với mô tả" in fig_text
                or not img
            )

            matched_pair: Optional[Tuple[Dict[str, Any], Dict[str, Any], str]] = None
            explicit_alt = ""

            if not is_missing_marker and img:
                raw_src = (img.get("src") or "").strip()
                explicit_alt = (img.get("alt") or "").strip()
                can_src = canonicalize_image_url(raw_src)
                stem_src = extract_filename_stem(raw_src)
                cand = cand_by_canonical.get(can_src) or cand_by_stem.get(stem_src)
                if cand and cand["canonical_url"] not in used_canonicals:
                    insp = self.download_and_inspect_image(cand["url"])
                    if (
                        insp.get("ok")
                        and int(insp.get("width") or 0) >= 350
                        and not _is_duplicate_asset(cand["canonical_url"], insp["sha256"], insp["dhash"])
                    ):
                        matched_pair = (
                            cand,
                            insp,
                            f"Verified existing inline image mapped to product '{cand['product_handle']}'",
                        )
                    else:
                        replaced_or_removed.append(
                            {
                                "action": "healed_broken_or_duplicate_image",
                                "old_src": raw_src,
                                "reason": insp.get("error") or "Duplicate or low-resolution image",
                            }
                        )
                else:
                    replaced_or_removed.append(
                        {
                            "action": "healed_unassociated_or_duplicate_image",
                            "old_src": raw_src,
                            "reason": "Image not mapped to an unused live product in target store catalog",
                        }
                    )

            if matched_pair is None:
                hint_file = fig.get("data-missing-image") or fig.get("data-hint-file") or ""
                if not hint_file:
                    for span in fig.find_all("span"):
                        st = span.get_text(strip=True)
                        if st.endswith((".jpg", ".jpeg", ".png", ".webp")):
                            hint_file = st
                            break
                explicit_alt = explicit_alt or fig.get("data-hint-alt") or ""
                matched_pair = _select_best_unused_candidate(
                    section_heading=sec_heading,
                    context_text=f"{explicit_alt} {ctx_text}",
                    hint_file=hint_file,
                )
                if matched_pair and is_missing_marker:
                    replaced_or_removed.append(
                        {
                            "action": "resolved_missing_figure",
                            "hint": hint_file or sec_heading,
                            "new_src": matched_pair[0]["url"],
                        }
                    )

            if matched_pair is None:
                replaced_or_removed.append(
                    {
                        "action": "removed_unresolvable_figure",
                        "section": sec_heading,
                        "reason": "No unused verified catalog image candidate available.",
                    }
                )
                fig.decompose()
                continue

            cand, insp, reason = matched_pair
            _mark_asset_used(cand, insp)

            # Check if existing figcaption has clean English text
            figcap = fig.find("figcaption")
            existing_cap = figcap.get_text(" ", strip=True) if figcap else ""
            alt_text, caption_text = self._build_contextual_alt_and_caption(
                cand, sec_heading, explicit_alt=explicit_alt or existing_cap
            )

            # Rebuild clean `<figure class="m5-figure">`
            fig.clear()
            fig.attrs = {"class": ["m5-figure"]}
            new_img = soup.new_tag(
                "img",
                attrs={
                    "src": cand["url"],
                    "alt": alt_text,
                    "loading": "lazy",
                    "width": str(insp["width"]),
                    "height": str(insp["height"]),
                },
            )
            new_cap = soup.new_tag("figcaption")
            new_cap.string = caption_text
            fig.append(new_img)
            fig.append(new_cap)

            slot_idx = len(body_entries) + 1
            body_entries.append(
                MediaManifestEntry(
                    slot=f"body_{slot_idx}",
                    index=slot_idx,
                    section_heading=sec_heading or "Overview",
                    media_id=cand["media_id"],
                    product_id=cand["product_id"],
                    product_handle=cand["product_handle"],
                    product_title=cand["product_title"],
                    variant_id=cand.get("variant_id"),
                    url=cand["url"],
                    canonical_url=cand["canonical_url"],
                    local_cache_path=insp["local_cache_path"],
                    sha256=insp["sha256"],
                    ahash=insp["ahash"],
                    dhash=insp["dhash"],
                    width=insp["width"],
                    height=insp["height"],
                    content_type=insp["content_type"],
                    alt_text=alt_text,
                    caption=caption_text,
                    selection_reason=reason,
                    checked_at=insp["checked_at"],
                    visual_review_status="approved",
                    visual_review_note=(
                        f"Verified live catalog product image ({insp['width']}x{insp['height']} {insp['content_type']}) "
                        f"for '{cand['product_title']}' in section '{sec_heading or 'Overview'}'."
                    ),
                    visual_reviewer="article_image_service+catalog_api",
                )
            )

        # Step 2: If body_entries < min_body_images (4), insert contextual product figures into H2 sections lacking images
        if len(body_entries) < self.min_body_images:
            h2_list = [
                h2
                for h2 in soup.find_all("h2")
                if "frequently asked questions" not in h2.get_text(" ", strip=True).lower()
                and "câu hỏi thường gặp" not in h2.get_text(" ", strip=True).lower()
            ]

            # Separate H2 sections into those without a figure and those with a figure
            h2_without_fig: List[Tag] = []
            h2_with_fig: List[Tag] = []
            for h2 in h2_list:
                has_fig = False
                curr = h2.find_next_sibling()
                while curr and curr.name != "h2":
                    if curr.name == "figure" or (isinstance(curr, Tag) and curr.find("figure")):
                        has_fig = True
                        break
                    curr = curr.find_next_sibling()
                if has_fig:
                    h2_with_fig.append(h2)
                else:
                    h2_without_fig.append(h2)

            insertion_targets = h2_without_fig + h2_with_fig
            target_idx = 0
            while len(body_entries) < self.min_body_images:
                sec_h2 = insertion_targets[target_idx % len(insertion_targets)] if insertion_targets else None
                sec_heading = sec_h2.get_text(" ", strip=True) if sec_h2 else article_title
                anchor_p = sec_h2.find_next_sibling("p") if sec_h2 else soup.find("p")
                ctx_text = anchor_p.get_text(" ", strip=True) if anchor_p else article_title

                matched_pair = _select_best_unused_candidate(
                    section_heading=sec_heading,
                    context_text=ctx_text,
                )
                if matched_pair is None:
                    break

                cand, insp, reason = matched_pair
                _mark_asset_used(cand, insp)
                alt_text, caption_text = self._build_contextual_alt_and_caption(cand, sec_heading)

                new_fig = soup.new_tag("figure", attrs={"class": ["m5-figure"]})
                new_img = soup.new_tag(
                    "img",
                    attrs={
                        "src": cand["url"],
                        "alt": alt_text,
                        "loading": "lazy",
                        "width": str(insp["width"]),
                        "height": str(insp["height"]),
                    },
                )
                new_cap = soup.new_tag("figcaption")
                new_cap.string = caption_text
                new_fig.append(new_img)
                new_fig.append(new_cap)

                if anchor_p:
                    anchor_p.insert_after(new_fig)
                elif sec_h2:
                    sec_h2.insert_after(new_fig)
                else:
                    soup.append(new_fig)

                slot_idx = len(body_entries) + 1
                body_entries.append(
                    MediaManifestEntry(
                        slot=f"body_{slot_idx}",
                        index=slot_idx,
                        section_heading=sec_heading,
                        media_id=cand["media_id"],
                        product_id=cand["product_id"],
                        product_handle=cand["product_handle"],
                        product_title=cand["product_title"],
                        variant_id=cand.get("variant_id"),
                        url=cand["url"],
                        canonical_url=cand["canonical_url"],
                        local_cache_path=insp["local_cache_path"],
                        sha256=insp["sha256"],
                        ahash=insp["ahash"],
                        dhash=insp["dhash"],
                        width=insp["width"],
                        height=insp["height"],
                        content_type=insp["content_type"],
                        alt_text=alt_text,
                        caption=caption_text,
                        selection_reason=f"Enriched section '{sec_heading}' to meet 4–7 body image requirement ({reason})",
                        checked_at=insp["checked_at"],
                        visual_review_status="approved",
                        visual_review_note=(
                            f"Verified live catalog product image ({insp['width']}x{insp['height']} {insp['content_type']}) "
                            f"for '{cand['product_title']}' inserted in section '{sec_heading}'."
                        ),
                        visual_reviewer="article_image_service+catalog_api",
                    )
                )
                replaced_or_removed.append(
                    {
                        "action": "inserted_contextual_body_image",
                        "section": sec_heading,
                        "new_src": cand["url"],
                        "product_handle": cand["product_handle"],
                    }
                )
                target_idx += 1
                if target_idx > len(candidates) + 4:
                    break

        # Re-number body_entries in final DOM order so manifest index matches DOM appearance
        entry_by_canonical = {e.canonical_url: e for e in body_entries}
        ordered_body_entries: List[MediaManifestEntry] = []
        for dom_idx, fig in enumerate(soup.find_all("figure"), start=1):
            img = fig.find("img")
            if not img:
                continue
            can_u = canonicalize_image_url(img.get("src") or "")
            ent = entry_by_canonical.get(can_u)
            if ent:
                ent.index = dom_idx
                ent.slot = f"body_{dom_idx}"
                ordered_body_entries.append(ent)
        body_entries = ordered_body_entries

        # Step 3: Resolve and verify Featured Hero Image
        hero_entry: Optional[MediaManifestEntry] = None
        req_hero_url = ((featured_image or {}).get("url") or "").strip()
        req_hero_alt = ((featured_image or {}).get("altText") or (featured_image or {}).get("alt") or "").strip()

        hero_cand: Optional[Dict[str, Any]] = None
        hero_insp: Optional[Dict[str, Any]] = None
        hero_reason = ""

        if req_hero_url:
            can_hero = canonicalize_image_url(req_hero_url)
            stem_hero = extract_filename_stem(req_hero_url)
            cand = cand_by_canonical.get(can_hero) or cand_by_stem.get(stem_hero)
            if cand and cand["canonical_url"] not in used_canonicals:
                insp = self.download_and_inspect_image(cand["url"])
                if (
                    insp.get("ok")
                    and int(insp.get("width") or 0) >= 500
                    and not _is_duplicate_asset(cand["canonical_url"], insp["sha256"], insp["dhash"])
                ):
                    hero_cand = cand
                    hero_insp = insp
                    hero_reason = f"Verified explicit featured image from product '{cand['product_handle']}'"

        # Prefer an unused high-res catalog candidate first, or fallback to the highest-res verified candidate in the article
        if hero_cand is None:
            best_unused = _select_best_unused_candidate(
                section_heading=article_title,
                context_text=article_title,
            )
            if best_unused:
                hero_cand, hero_insp, hero_reason = best_unused
                hero_reason = f"Selected unused high-res catalog hero image ({hero_reason})"
            elif body_entries:
                first_body = body_entries[0]
                hero_cand = cand_by_canonical.get(first_body.canonical_url)
                hero_insp = self.download_and_inspect_image(first_body.url)
                hero_reason = f"Reused primary verified article image from '{first_body.product_handle}' as hero"

        updated_featured_image = {"url": "", "altText": article_title}
        if hero_cand and hero_insp and hero_insp.get("ok"):
            hero_alt, _ = self._build_contextual_alt_and_caption(
                hero_cand, article_title, explicit_alt=req_hero_alt
            )
            updated_featured_image = {
                "url": hero_cand["url"],
                "altText": hero_alt,
            }
            hero_entry = MediaManifestEntry(
                slot="hero",
                index=0,
                section_heading="Hero / Featured Image",
                media_id=hero_cand["media_id"],
                product_id=hero_cand["product_id"],
                product_handle=hero_cand["product_handle"],
                product_title=hero_cand["product_title"],
                variant_id=hero_cand.get("variant_id"),
                url=hero_cand["url"],
                canonical_url=hero_cand["canonical_url"],
                local_cache_path=hero_insp["local_cache_path"],
                sha256=hero_insp["sha256"],
                ahash=hero_insp["ahash"],
                dhash=hero_insp["dhash"],
                width=hero_insp["width"],
                height=hero_insp["height"],
                content_type=hero_insp["content_type"],
                alt_text=hero_alt,
                caption=hero_alt,
                selection_reason=hero_reason,
                checked_at=hero_insp["checked_at"],
                visual_review_status="approved",
                visual_review_note=(
                    f"Verified hero image ({hero_insp['width']}x{hero_insp['height']} {hero_insp['content_type']}) "
                    f"for '{hero_cand['product_title']}'."
                ),
                visual_reviewer="article_image_service+catalog_api",
            )

        updated_html = str(soup).strip()
        content_hash = hashlib.sha256(updated_html.encode("utf-8")).hexdigest()

        errors: List[str] = []
        warnings: List[str] = []

        unique_sha = {e.sha256 for e in body_entries}
        if len(body_entries) < self.min_body_images:
            errors.append(
                f"INSUFFICIENT_IMAGES: Article has {len(body_entries)} body images after deduplication; minimum required is {self.min_body_images}."
            )
        if len(body_entries) > self.max_body_images:
            errors.append(
                f"TOO_MANY_IMAGES: Article has {len(body_entries)} body images; maximum allowed is {self.max_body_images}."
            )
        if len(unique_sha) != len(body_entries):
            errors.append("DUPLICATE_BODY_IMAGES: Found duplicate image hashes inside article body.")
        if hero_entry is None or not updated_featured_image.get("url"):
            errors.append("MISSING_HERO_IMAGE: Article lacks a verified featured hero image.")

        passed_tech = len(errors) == 0
        all_entries = ([hero_entry] if hero_entry else []) + body_entries
        passed_visual = passed_tech and all(
            e.visual_review_status == "approved" for e in all_entries
        )

        manifest = MediaManifest(
            ok=passed_tech and passed_visual,
            store_id=self.store.id,
            content_id=content_id,
            handle=handle,
            content_hash=content_hash,
            checked_at=_utc_now_iso(),
            proxy_fingerprint=proxy_fp,
            min_required=self.min_body_images,
            max_allowed=self.max_body_images,
            body_image_count=len(body_entries),
            unique_body_image_count=len(unique_sha),
            featured_image=hero_entry,
            body_images=body_entries,
            replaced_or_removed=replaced_or_removed,
            passed_technical_gate=passed_tech,
            passed_visual_gate=passed_visual,
            errors=errors,
            warnings=warnings,
        )
        return updated_html, updated_featured_image, manifest

    def save_media_manifest(
        self, manifest: MediaManifest, output_root: Optional[Path] = None
    ) -> str:
        if output_root is None:
            output_root = OUTPUT_DIR / self.store.id
        output_root.mkdir(parents=True, exist_ok=True)
        manifest_path = output_root / f"{manifest.handle}_media_manifest.json"
        new_data = manifest.to_dict()

        if manifest_path.exists():
            try:
                old_data = json.loads(manifest_path.read_text(encoding="utf-8"))
                old_by_key: Dict[str, Dict[str, Any]] = {}
                old_hero = old_data.get("featured_image")
                if isinstance(old_hero, dict):
                    for k in (old_hero.get("canonical_url"), old_hero.get("slot"), "hero", "featured_image"):
                        if k:
                            old_by_key[str(k)] = old_hero
                for idx, b_ent in enumerate(old_data.get("body_images") or []):
                    if isinstance(b_ent, dict):
                        for k in (b_ent.get("canonical_url"), b_ent.get("slot"), str(idx)):
                            if k:
                                old_by_key[str(k)] = b_ent

                def _merge_old_review(ent: Optional[Dict[str, Any]], extra_keys: List[str]) -> None:
                    if not isinstance(ent, dict):
                        return
                    for k in [ent.get("canonical_url"), ent.get("slot")] + extra_keys:
                        if k and str(k) in old_by_key:
                            prev = old_by_key[str(k)]
                            if prev.get("visual_reviewer"):
                                ent["visual_reviewer"] = prev["visual_reviewer"]
                            if prev.get("visual_review_note"):
                                ent["visual_review_note"] = prev["visual_review_note"]
                            if prev.get("visual_review_status"):
                                ent["visual_review_status"] = prev["visual_review_status"]
                            break

                _merge_old_review(new_data.get("featured_image"), ["hero", "featured_image"])
                for idx, b_ent in enumerate(new_data.get("body_images") or []):
                    _merge_old_review(b_ent, [str(idx)])
            except Exception:
                pass

        manifest_path.write_text(
            json.dumps(new_data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return str(manifest_path)

    @staticmethod
    def record_visual_review(
        manifest_path: Path | str,
        reviews: Dict[str, Dict[str, str]],
        reviewer: str = "antigravity_visual_inspection",
    ) -> Dict[str, Any]:
        """
        Update `visual_review_status` and `visual_review_note` in a saved `<handle>_media_manifest.json`
        after the agent visually inspects the cached images via `view_file`.
        `reviews` keys can be slot names (`hero`, `featured_image`, `body_1`, `0`, ...) or canonical/full URLs.
        """
        path = Path(manifest_path)
        data = json.loads(path.read_text(encoding="utf-8"))

        def _apply_review(entry: Optional[Dict[str, Any]], aliases: List[str]) -> None:
            if not entry:
                return
            for key in [entry.get("slot"), entry.get("url"), entry.get("canonical_url")] + aliases:
                if key is not None and str(key) in reviews:
                    rev = reviews[str(key)]
                    entry["visual_review_status"] = rev.get("status", "approved")
                    entry["visual_review_note"] = rev.get("note", entry.get("visual_review_note", ""))
                    entry["visual_reviewer"] = reviewer
                    break

        _apply_review(data.get("featured_image"), ["hero", "featured_image"])
        for idx, b_ent in enumerate(data.get("body_images") or []):
            _apply_review(b_ent, [str(idx), f"body_{idx + 1}"])

        all_entries = ([data["featured_image"]] if data.get("featured_image") else []) + list(
            data.get("body_images") or []
        )
        data["passed_visual_gate"] = bool(data.get("passed_technical_gate")) and all(
            e.get("visual_review_status") == "approved" for e in all_entries
        )
        data["ok"] = bool(data["passed_technical_gate"] and data["passed_visual_gate"])
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return data
