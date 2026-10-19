"""
Pre-Publish Fact, Policy & Catalog Claim Auditor (`article_fact_auditor.py`).

Audits an article's HTML body, title, summary, and SEO metadata against:
  1. The store's verified `StoreEditorialProfile` (`data/store_profiles/<store_id>.json`),
     including `policies.*.forbidden_claims`, `conflict_blocked` guardrails, and `do_not_claim`.
  2. Live Shopify Admin GraphQL product/variant evidence (`ShopifyCatalogService`),
     ensuring every linked `/products/<handle>` is ACTIVE, published online, and returns HTTP 200.
  3. Live internal link checks (`/collections/...`, `/pages/...`, `/policies/...`, `/blogs/...`)
     through the mandatory Proxy (`ProxyManager`).
  4. English-only editorial hygiene (zero Vietnamese prompt prefixes or raw LaTeX tokens).
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from shopify_catalog_service import ShopifyCatalogService
from store_manager import DATA_DIR, StoreManager, slugify_store_id
from store_profile_manager import StoreProfileManager

_VIETNAMESE_LEAK_PATTERNS = [
    re.compile(r"\bTrả lời\b", re.IGNORECASE),
    re.compile(r"\bViết nội dung cho\b", re.IGNORECASE),
    re.compile(r"\bNội dung cho vùng\b", re.IGNORECASE),
    re.compile(r"\bTrang cho\b", re.IGNORECASE),
    re.compile(r"\bCâu hỏi thường gặp\b", re.IGNORECASE),
]

_RAW_LATEX_PATTERNS = [
    re.compile(r"\\times\b"),
    re.compile(r"\\frac\b"),
    re.compile(r"\\approx\b"),
    re.compile(r"\\text\{"),
]

_CORRUPT_PRICE_PATTERNS: List[tuple[str, re.Pattern[str], str]] = [
    (
        "CORRUPT_PRICE_BROKEN_RANGE",
        re.compile(r"(?:(?<=[(\s])\.\d{2}\s+to\s+,\d+|\bto\s+,\d+|\(\s*to\s*,)"),
        "Article contains corrupted price range expression with missing dollar signs or swallowed digits",
    ),
    (
        "CORRUPT_PRICE_LEADING_COMMA",
        re.compile(r"(?:(?<=[(\s>]),\d{3}(?:\.\d{2})?)"),
        "Article contains corrupted price string with leading comma and missing leading digit/dollar sign",
    ),
    (
        "CORRUPT_PRICE_MISSING_DOLLAR_OR_DIGIT",
        re.compile(r"(?:range\s+from\s+\.\d{2}|\(\s*\.\d{2}\s+to|<td>\s*\.\d{2}\s+to)"),
        "Article contains corrupted price with missing dollar sign or swallowed leading digit",
    ),
]

# Store-specific semantic claim patterns that must be blocked even if phrased slightly differently
_STORE_FORBIDDEN_REGEX: Dict[str, List[tuple[str, re.Pattern[str], str]]] = {
    "wrydeco": [
        (
            "WRYDECO_FALSE_CHANGE_OF_MIND_RETURN",
            re.compile(
                r"\b(no[-\s]*questions[-\s]*asked\s+returns?|free\s+returns?\s+for\s+any\s+reason|(?:accept(?:s|ed)?|allow(?:s|ed)?|eligible\s+for)\s+returns?\s+for\s+change\s+of\s+mind|returns?\s+for\s+change\s+of\s+mind\s+(?:are\s+)?(?:accepted|allowed|offered))\b",
                re.IGNORECASE,
            ),
            "WRYDECO accepts returns within 30 calendar days only for damaged, defective, or incorrect items; change-of-mind returns are not accepted.",
        ),
        (
            "WRYDECO_CONTRADICTORY_RETURN_POLICY",
            re.compile(
                r"\breturns\s+within\s+30\s+calendar\s+days.*(not\s+accepted|are\s+not\s+accepted)\b",
                re.IGNORECASE,
            ),
            "WRYDECO accepts returns within 30 calendar days for damaged, defective, or incorrect items; do not claim damaged/defective returns are not accepted.",
        ),
        (
            "WRYDECO_FALSE_WARRANTY_DURATION",
            re.compile(r"\b(lifetime|[2-9][-\s]*year|10[-\s]*year)\s+(structural\s+|limited\s+)?warranty\b", re.IGNORECASE),
            "WRYDECO offers a 1-year limited warranty from delivery covering defects in materials and workmanship; do not claim multi-year or lifetime warranty.",
        ),
        (
            "WRYDECO_FALSE_INSTALLATION_INCLUDED",
            re.compile(
                r"\b(includes?\s+(free\s+)?(wall\s+mounting|professional\s+installation)|white[-\s]*glove\s+wall\s+installation\s+included)\b",
                re.IGNORECASE,
            ),
            "WRYDECO standard shipping does not include wall mounting or installation services unless confirmed in writing.",
        ),
    ],
    "dizzycustom": [
        (
            "DIZZY_SHIPPING_POLICY_CONFLICT",
            re.compile(
                r"\b(free\s+(standard\s+)?shipping\s+on\s+all\s+orders|\$6\.95\s+flat[-\s]*rate\s+shipping)\b",
                re.IGNORECASE,
            ),
            "DizzyCustom has conflicting shipping timelines/rates across pages ($6.95/DTG text vs product page); do not cite unverified flat-rate or free shipping on all orders.",
        ),
        (
            "DIZZY_FALSE_CANCELLATION_48H",
            re.compile(r"\b(48[-\s]*hour|72[-\s]*hour)\s+cancellation\b", re.IGNORECASE),
            "DizzyCustom allows order cancellation or modification only within 24 hours of purchase.",
        ),
    ],
    "jeminise": [
        (
            "JEMINISE_FALSE_HAND_EMBROIDERY",
            re.compile(
                r"\b(hand[-\s]*(stitched|pieced|embroidered|quilted)\s+patchwork|raised\s+thread\s+embroidery)\b",
                re.IGNORECASE,
            ),
            "Jeminise bedding uses printed artwork designs; do not claim hand-pieced patchwork or raised thread embroidery.",
        ),
        (
            "JEMINISE_FALSE_FREE_WORLDWIDE_SHIPPING",
            re.compile(r"\bfree\s+(worldwide|global|international)\s+shipping\b", re.IGNORECASE),
            "Jeminise offers free shipping to the US and Canada; supported international destinations have a $5.99 flat fee.",
        ),
    ],
    "chillgen": [
        (
            "CHILLGEN_FALSE_WOOL_CLAIM",
            re.compile(r"\b(100%\s+(natural\s+)?wool|hand[-\s]*knotted\s+wool)\b", re.IGNORECASE),
            "Do not claim catalog-wide 100% natural or hand-knotted wool for ChillGen printed rugs.",
        ),
        (
            "CHILLGEN_FALSE_INTERNATIONAL_SHIPPING",
            re.compile(r"\b(free\s+(worldwide|international)\s+shipping|ships\s+to\s+alaska\s+and\s+hawaii)\b", re.IGNORECASE),
            "ChillGen ships only to supported street addresses in the contiguous United States.",
        ),
    ],
    "preaureum": [
        (
            "PREAUREUM_FALSE_GENUINE_COWHIDE",
            re.compile(
                r"\b(100%\s+genuine\s+(full[-\s]*grain\s+)?(cowhide|calfskin)\s+leather|genuine\s+full[-\s]*grain\s+leather)\b",
                re.IGNORECASE,
            ),
            "PreAureum FAQ describes its bags as durable leather-style material; do not claim 100% genuine full-grain cowhide leather unless verified on the specific product.",
        ),
        (
            "PREAUREUM_FALSE_RAISED_EMBOSSING",
            re.compile(
                r"\b(hand[-\s]*tooled\s+raised\s+leather|raised\s+3d\s+(carving|embossing|stitching))\b",
                re.IGNORECASE,
            ),
            "PreAureum 3D-effect designs are custom printed artwork on leather-style material, not raised carving or embossing.",
        ),
        (
            "PREAUREUM_FALSE_FREE_INTL_SHIPPING",
            re.compile(r"\bfree\s+(worldwide|global|international)\s+shipping\b", re.IGNORECASE),
            "PreAureum offers free standard shipping in the US; international shipping rates are calculated at checkout.",
        ),
    ],
}


@dataclass
class FactAuditReport:
    passed: bool
    store_id: str
    content_id: str
    handle: str
    title: str
    checked_at: str
    blocking_errors_count: int = 0
    warnings_count: int = 0
    blocking_errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    verified_products: List[Dict[str, Any]] = field(default_factory=list)
    verified_internal_links: List[Dict[str, Any]] = field(default_factory=list)
    policy_checks: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ArticleFactAuditor:
    """Audits article claims, policy compliance, product evidence, and internal links."""

    def __init__(
        self,
        store_manager: Optional[StoreManager] = None,
        profile_manager: Optional[StoreProfileManager] = None,
        catalog_service: Optional[ShopifyCatalogService] = None,
    ) -> None:
        self.store_manager = store_manager or StoreManager(data_dir=DATA_DIR)
        self.profile_manager = profile_manager or StoreProfileManager(store_manager=self.store_manager)
        self.catalog_service = catalog_service or ShopifyCatalogService(store_manager=self.store_manager)

    def audit_article(
        self,
        store_id: str,
        title: str,
        handle: str,
        body_html: str,
        summary: str = "",
        seo_title: str = "",
        seo_description: str = "",
        content_id: str = "",
        verify_live_urls: bool = True,
    ) -> FactAuditReport:
        sid = slugify_store_id(store_id)
        store = self.store_manager.get_store(sid)
        now_iso = datetime.now(timezone.utc).isoformat()

        blocking_errors: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []
        verified_products: List[Dict[str, Any]] = []
        verified_links: List[Dict[str, Any]] = []
        policy_checks: List[Dict[str, Any]] = []

        # 1. Load & validate active Store Editorial Profile
        try:
            profile = self.profile_manager.get_profile(sid)
        except Exception as exc:
            blocking_errors.append(
                {
                    "code": "MISSING_OR_INVALID_STORE_PROFILE",
                    "message": f"Store '{sid}' does not have a valid Store Editorial Profile: {exc}",
                }
            )
            return FactAuditReport(
                passed=False,
                store_id=sid,
                content_id=content_id,
                handle=handle,
                title=title,
                checked_at=now_iso,
                blocking_errors_count=len(blocking_errors),
                blocking_errors=blocking_errors,
            )

        if not profile.get("ready_for_publishing") or profile.get("profile_status") != "active_verified":
            blocking_errors.append(
                {
                    "code": "STORE_PROFILE_NOT_READY",
                    "message": f"Store Editorial Profile for '{sid}' has status='{profile.get('profile_status')}' and ready_for_publishing={profile.get('ready_for_publishing')}.",
                }
            )

        soup = BeautifulSoup(body_html or "", "html.parser")
        visible_text = " ".join(
            [
                title or "",
                summary or "",
                seo_title or "",
                seo_description or "",
                soup.get_text(" ", strip=True),
            ]
        )
        visible_lower = visible_text.lower()

        # 2. Check Vietnamese leak or raw LaTeX
        for pat in _VIETNAMESE_LEAK_PATTERNS:
            m = pat.search(visible_text)
            if m:
                blocking_errors.append(
                    {
                        "code": "VIETNAMESE_TEXT_LEAK",
                        "message": f"Found non-English prompt/UI text in article: '{m.group(0)}'",
                    }
                )
        for pat in _RAW_LATEX_PATTERNS:
            m = pat.search(visible_text)
            if m:
                blocking_errors.append(
                    {
                        "code": "RAW_LATEX_LEAK",
                        "message": f"Found unformatted raw LaTeX token in article: '{m.group(0)}'",
                    }
                )

        # 3. Check policy forbidden_claims & conflict_blocked guardrails
        policies = profile.get("policies") or {}
        for pol_key, pol_obj in policies.items():
            if not isinstance(pol_obj, dict):
                continue
            c_status = pol_obj.get("conflict_status", "none")
            forbidden_list = pol_obj.get("forbidden_claims") or []
            pol_violations: List[str] = []
            for phrase in forbidden_list:
                clean_phrase = str(phrase or "").strip()
                if not clean_phrase:
                    continue
                if clean_phrase.lower() not in visible_lower:
                    continue
                if clean_phrase.lower() == "returns for change of mind":
                    # Do not flag if stating the truthful negative policy ("returns for change of mind are not accepted")
                    if re.search(r"\b(?:returns?\s+for\s+change\s+of\s+mind\s+(?:are\s+)?not\s+accepted|not\s+accepted\s+for\s+change\s+of\s+mind|returns?\s+are\s+not\s+accepted\s+for\s+change\s+of\s+mind|no\s+returns?\s+for\s+change\s+of\s+mind)\b", visible_lower):
                        continue
                    if not re.search(r"\b(?:accepts?\s+returns?\s+for\s+change\s+of\s+mind|returns?\s+for\s+change\s+of\s+mind\s+(?:are\s+)?accepted)\b", visible_lower):
                        continue
                elif clean_phrase.lower() in ("guaranteed delivery date", "guaranteed delivery dates"):
                    # Do not flag truthful negative statements ("estimates rather than guaranteed delivery dates", "not a guaranteed delivery date", etc.)
                    if re.search(r"\b(?:rather\s+than\s+guaranteed\s+delivery\s+dates?|not\s+(?:a\s+)?guaranteed\s+delivery\s+dates?|estimates?,?\s+not\s+guaranteed\s+delivery\s+dates?|estimates?\s+rather\s+than\s+guaranteed\s+delivery\s+dates?)\b", visible_lower):
                        continue
                elif clean_phrase.lower() in ("includes free wall mounting installation", "white-glove wall installation included"):
                    # Do not flag truthful negative statements ("does not include wall mounting", "installation not included") or in FAQ questions
                    if re.search(r"\b(?:does\s+not\s+include\s+(?:free\s+)?(?:wall\s+mounting|professional\s+installation)|installation\s+not\s+included|installation\s+services?\s+not\s+included|professional\s+installation\s+not\s+included)\b", visible_lower):
                        continue
                pol_violations.append(clean_phrase)
                blocking_errors.append(
                    {
                        "code": f"POLICY_FORBIDDEN_CLAIM_{pol_key.upper()}",
                        "message": f"Article contains forbidden {pol_key} claim '{clean_phrase}' (conflict_status={c_status}).",
                        "policy_summary": pol_obj.get("summary"),
                    }
                )
            policy_checks.append(
                {
                    "policy_key": pol_key,
                    "conflict_status": c_status,
                    "passed": len(pol_violations) == 0,
                    "violations": pol_violations,
                }
            )

        # Check store-specific regex guardrails
        for code, regex_pat, msg in _STORE_FORBIDDEN_REGEX.get(sid, []):
            for m in regex_pat.finditer(visible_text):
                matched_span = m.group(0)
                start_idx = max(0, m.start() - 30)
                preceding_text = visible_text[start_idx:m.start()].lower()
                # If preceded by negation or in a question context, ignore false installation claims
                if code == "WRYDECO_FALSE_INSTALLATION_INCLUDED":
                    if any(neg in preceding_text for neg in ("not ", "does not ", "doesn't ", "never ", "without ")):
                        continue
                    # Check if inside a question
                    window = visible_text[max(0, m.start() - 60):min(len(visible_text), m.end() + 60)].lower()
                    if "?" in window and any(q in window for q in ("does ", "can ", "is ", "do ")):
                        continue
                blocking_errors.append(
                    {
                        "code": code,
                        "message": f"{msg} (Matched: '{matched_span}')",
                    }
                )

        # Check corrupted price expressions
        for p_code, p_pat, p_msg in _CORRUPT_PRICE_PATTERNS:
            m = p_pat.search(visible_text) or p_pat.search(body_html)
            if m:
                blocking_errors.append(
                    {
                        "code": p_code,
                        "message": f"{p_msg} (Matched: '{m.group(0)}')",
                    }
                )

        # 4. Extract internal links and product handles from body_html
        base_dom = store.resolved_public_domain.rstrip("/")
        store_hosts = {
            urlparse(base_dom).netloc.lower(),
            store.normalized_shop.lower(),
            (store.zbigtee_domain or "").lower(),
        }
        store_hosts.discard("")

        internal_urls: List[str] = []
        product_handles: List[str] = []
        seen_urls = set()
        seen_handles = set()

        for a_tag in soup.find_all("a", href=True):
            href = (a_tag.get("href") or "").strip()
            if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
                continue

            resolved = href
            if href.startswith("/"):
                resolved = f"{base_dom}{href}"
            parsed_u = urlparse(resolved)
            host_lower = (parsed_u.netloc or "").lower().replace("www.", "")

            is_internal = href.startswith("/") or any(
                host_lower == h.replace("www.", "") for h in store_hosts
            )
            if not is_internal:
                continue

            if resolved not in seen_urls:
                seen_urls.add(resolved)
                internal_urls.append(resolved)

            if "/products/" in parsed_u.path:
                ph = parsed_u.path.split("/products/")[-1].strip("/").split("?")[0]
                if ph and ph not in seen_handles:
                    seen_handles.add(ph)
                    product_handles.append(ph)

        # 5. Verify referenced products against Shopify Admin GraphQL API
        for ph in product_handles:
            try:
                ev = self.catalog_service.get_product_evidence(
                    sid,
                    ph,
                    verify_live_url=verify_live_urls,
                )
                if not ev.get("ok"):
                    blocking_errors.append(
                        {
                            "code": "PRODUCT_NOT_FOUND_IN_SHOPIFY_API",
                            "message": f"Referenced product handle '{ph}' does not exist in Shopify catalog for '{sid}'.",
                        }
                    )
                    continue
                prod = ev["product"]
                if prod.get("status") != "ACTIVE" or not prod.get("is_published_online"):
                    blocking_errors.append(
                        {
                            "code": "PRODUCT_NOT_PUBLISHED_ONLINE",
                            "message": f"Product '{ph}' has status={prod.get('status')} and is_published_online={prod.get('is_published_online')}.",
                        }
                    )
                if verify_live_urls and not prod.get("storefront_live_ok", True):
                    blocking_errors.append(
                        {
                            "code": "PRODUCT_STOREFRONT_URL_NOT_200",
                            "message": f"Product URL '{prod.get('storefront_url')}' returned HTTP {prod.get('storefront_http_status')}.",
                        }
                    )
                verified_products.append(
                    {
                        "handle": ph,
                        "product_id": prod.get("product_id"),
                        "title": prod.get("title"),
                        "status": prod.get("status"),
                        "is_published_online": prod.get("is_published_online"),
                        "price_range": prod.get("price_range"),
                        "variants_count": prod.get("variants_count"),
                        "media_count": prod.get("media_count"),
                        "storefront_url": prod.get("storefront_url"),
                        "storefront_http_status": prod.get("storefront_http_status", 200),
                    }
                )
            except Exception as exc:
                blocking_errors.append(
                    {
                        "code": "PRODUCT_API_VERIFICATION_ERROR",
                        "message": f"Failed to verify product '{ph}' via Shopify API: {exc}",
                    }
                )

        # 6. Verify all internal links return HTTP 200 via Proxy
        if verify_live_urls and internal_urls:
            url_check = self.catalog_service.verify_storefront_urls(sid, internal_urls)
            for item in url_check.get("results") or []:
                verified_links.append(item)
                if not item.get("ok"):
                    blocking_errors.append(
                        {
                            "code": "BROKEN_INTERNAL_LINK",
                            "message": f"Internal link '{item.get('requested_url')}' -> '{item.get('resolved_url')}' failed with HTTP {item.get('http_status')} ({item.get('error', '')}).",
                        }
                    )

        if len(internal_urls) == 0:
            warnings.append(
                {
                    "code": "NO_INTERNAL_STORE_LINKS",
                    "message": "Article body does not contain any internal links to store products or collections.",
                }
            )

        return FactAuditReport(
            passed=len(blocking_errors) == 0,
            store_id=sid,
            content_id=content_id,
            handle=handle,
            title=title,
            checked_at=now_iso,
            blocking_errors_count=len(blocking_errors),
            warnings_count=len(warnings),
            blocking_errors=blocking_errors,
            warnings=warnings,
            verified_products=verified_products,
            verified_internal_links=verified_links,
            policy_checks=policy_checks,
        )

    def sanitize_article_claims(
        self,
        store_id: str,
        title: str,
        handle: str,
        body_html: str,
        summary: str = "",
        seo_title: str = "",
        seo_description: str = "",
        content_id: str = "",
        verify_live_urls: bool = True,
    ) -> Dict[str, Any]:
        """
        Inspect and sanitize unsupported or forbidden policy/material claims across `body_html`,
        `summary`, `seo_title`, and `seo_description` based on the store's `StoreEditorialProfile`,
        then re-run `audit_article` to verify whether all blocking claim issues are resolved.
        """
        sid = slugify_store_id(store_id)
        profile = self.profile_manager.get_profile(sid)
        policies = profile.get("policies") or {}

        applied_edits: List[Dict[str, str]] = []
        updated_html = body_html or ""
        updated_summary = summary or ""
        updated_seo_desc = seo_description or ""

        # 1. Clean raw LaTeX tokens
        if "\\times" in updated_html:
            updated_html = re.sub(r"\\times\b", "×", updated_html)
            applied_edits.append({"type": "latex_cleanup", "detail": "Replaced \\times with ×"})

        # 2. Replace store-specific forbidden regex patterns with truthful, policy-safe phrasing
        safe_replacements: Dict[str, List[tuple[re.Pattern[str], str, str]]] = {
            "wrydeco": [
                (
                    re.compile(
                        r"\breturns\s+within\s+30\s+calendar\s+days\s+for\s+damaged,\s+defective,\s+or\s+incorrect\s+items\s+are\s+not\s+accepted\.?\b",
                        re.IGNORECASE,
                    ),
                    "returns are accepted within 30 calendar days for damaged, defective, or incorrect items (returns for change of mind are not accepted).",
                    "Fixed contradictory return statement: damaged/defective items are accepted within 30 days while change of mind is not accepted",
                ),
                (
                    re.compile(
                        r"\b(no[-\s]*questions[-\s]*asked\s+returns?|free\s+returns?\s+for\s+any\s+reason|(?:accept(?:s|ed)?|allow(?:s|ed)?|eligible\s+for)\s+returns?\s+for\s+change\s+of\s+mind|returns?\s+for\s+change\s+of\s+mind\s+(?:are\s+)?(?:accepted|allowed|offered))\b",
                        re.IGNORECASE,
                    ),
                    "returns are accepted within 30 calendar days only for damaged, defective, or incorrect items (returns for change of mind are not accepted)",
                    "Clarified WRYDECO 30-day return eligibility for damaged, defective, or incorrect items only",
                ),
                (
                    re.compile(r"\b(lifetime|[2-9][-\s]*year|10[-\s]*year)\s+(structural\s+|limited\s+)?warranty\b", re.IGNORECASE),
                    "1-year limited warranty",
                    "Corrected warranty duration to verified 1-year limited warranty",
                ),
                (
                    re.compile(
                        r"\b(includes?\s+(free\s+)?(wall\s+mounting|professional\s+installation)|white[-\s]*glove\s+wall\s+installation\s+included)\b",
                        re.IGNORECASE,
                    ),
                    "ships as a wall-mounted shelf unit (professional installation not included in standard shipping)",
                    "Clarified that standard shipping does not include wall mounting or installation services",
                ),
            ],
            "dizzycustom": [
                (
                    re.compile(
                        r"\b(free\s+(standard\s+)?shipping\s+on\s+all\s+orders|\$6\.95\s+flat[-\s]*rate\s+shipping)\b",
                        re.IGNORECASE,
                    ),
                    "current checkout shipping options",
                    "Replaced conflicted shipping claim with neutral checkout reference",
                ),
                (
                    re.compile(r"\b(48[-\s]*hour|72[-\s]*hour)\s+cancellation\b", re.IGNORECASE),
                    "24-hour cancellation",
                    "Corrected cancellation window to verified 24-hour window",
                ),
            ],
            "jeminise": [
                (
                    re.compile(
                        r"\b(hand[-\s]*(stitched|pieced|embroidered|quilted)\s+patchwork|raised\s+thread\s+embroidery)\b",
                        re.IGNORECASE,
                    ),
                    "printed patchwork-inspired artwork",
                    "Clarified printed artwork construction instead of hand-stitched/raised embroidery",
                ),
                (
                    re.compile(r"\bfree\s+(worldwide|global|international)\s+shipping\b", re.IGNORECASE),
                    "free standard shipping to the US and Canada",
                    "Corrected shipping scope to US and Canada",
                ),
            ],
            "chillgen": [
                (
                    re.compile(r"\b(100%\s+(natural\s+)?wool|hand[-\s]*knotted\s+wool)\b", re.IGNORECASE),
                    "soft printed low-pile surface",
                    "Replaced unsupported wool claim with verified printed rug surface description",
                ),
                (
                    re.compile(
                        r"\b(free\s+(worldwide|global|international)\s+shipping|ships\s+to\s+alaska\s+and\s+hawaii)\b",
                        re.IGNORECASE,
                    ),
                    "free standard shipping across the contiguous United States",
                    "Corrected shipping region to contiguous US",
                ),
            ],
            "preaureum": [
                (
                    re.compile(
                        r"\b(100%\s+genuine\s+(full[-\s]*grain\s+)?(cowhide|calfskin)\s+leather|genuine\s+full[-\s]*grain\s+leather)\b",
                        re.IGNORECASE,
                    ),
                    "durable leather-style material",
                    "Aligned material description with PreAureum FAQ ('leather-style material')",
                ),
                (
                    re.compile(
                        r"\b(hand[-\s]*tooled\s+raised\s+leather|raised\s+3d\s+(carving|embossing|stitching))\b",
                        re.IGNORECASE,
                    ),
                    "3D-effect printed artwork",
                    "Clarified 3D-effect printed artwork instead of raised carving/embossing",
                ),
                (
                    re.compile(r"\bfree\s+(worldwide|global|international)\s+shipping\b", re.IGNORECASE),
                    "free standard US shipping",
                    "Corrected shipping scope to free standard US shipping",
                ),
            ],
        }

        for pat, repl, desc in safe_replacements.get(sid, []):
            def _sub_smart(m: re.Match, target_text: str) -> str:
                preceding = target_text[max(0, m.start() - 30):m.start()].lower()
                if "wrydeco" in sid and any(neg in preceding for neg in ("not ", "does not ", "doesn't ", "never ", "without ")):
                    return m.group(0)
                # Check if inside a question
                q_window = target_text[max(0, m.start() - 80):min(len(target_text), m.end() + 80)].lower()
                if "wrydeco" in sid and "?" in q_window and any(q in q_window for q in ("does ", "is ", "do ", "can ")):
                    return m.group(0)
                return repl if isinstance(repl, str) else repl(m)

            if pat.search(updated_html):
                new_h = pat.sub(lambda m: _sub_smart(m, updated_html), updated_html)
                if new_h != updated_html:
                    updated_html = new_h
                    applied_edits.append({"type": "store_regex_sanitization", "detail": desc})
            if pat.search(updated_summary):
                updated_summary = pat.sub(lambda m: _sub_smart(m, updated_summary), updated_summary)
            if pat.search(updated_seo_desc):
                updated_seo_desc = pat.sub(lambda m: _sub_smart(m, updated_seo_desc), updated_seo_desc)

        # 3. Check literal policy forbidden_claims
        for pol_key, pol_obj in policies.items():
            if not isinstance(pol_obj, dict):
                continue
            for phrase in pol_obj.get("forbidden_claims") or []:
                clean_phrase = str(phrase or "").strip()
                if not clean_phrase:
                    continue
                if clean_phrase.lower() == "returns for change of mind":
                    pat = re.compile(
                        r"\b(accepts?\s+returns?\s+for\s+change\s+of\s+mind|returns?\s+for\s+change\s+of\s+mind\s+(?:are\s+)?accepted)\b",
                        re.IGNORECASE,
                    )
                elif clean_phrase.lower() in ("guaranteed delivery date", "guaranteed delivery dates"):
                    # Only match affirmative claims of guaranteed delivery, not "rather than guaranteed delivery dates" or "not a guaranteed delivery date"
                    def _replace_guaranteed(m: re.Match, target_str: str) -> str:
                        preceding = target_str[max(0, m.start() - 30):m.start()].lower()
                        if any(neg in preceding for neg in ("rather than", "not a", "not ", "no ", "estimates, not")):
                            return m.group(0)
                        return "current estimated delivery timeline"
                    pat = re.compile(r"\bguaranteed\s+delivery\s+dates?\b", re.IGNORECASE)
                    if pat.search(updated_html):
                        new_h = pat.sub(lambda m: _replace_guaranteed(m, updated_html), updated_html)
                        if new_h != updated_html:
                            updated_html = new_h
                            applied_edits.append({"type": f"forbidden_policy_claim_{pol_key}", "detail": f"Sanitized affirmative '{clean_phrase}' claim"})
                    if pat.search(updated_summary):
                        updated_summary = pat.sub(lambda m: _replace_guaranteed(m, updated_summary), updated_summary)
                    if pat.search(updated_seo_desc):
                        updated_seo_desc = pat.sub(lambda m: _replace_guaranteed(m, updated_seo_desc), updated_seo_desc)
                    continue
                elif clean_phrase.lower() in ("includes free wall mounting installation", "white-glove wall installation included"):
                    continue
                else:
                    pat = re.compile(re.escape(clean_phrase), re.IGNORECASE)
                if pat.search(updated_html):
                    updated_html = pat.sub("refer to our store policy page for current details", updated_html)
                    applied_edits.append(
                        {
                            "type": f"forbidden_policy_claim_{pol_key}",
                            "detail": f"Sanitized forbidden phrase '{clean_phrase}'",
                        }
                    )
                if pat.search(updated_summary):
                    updated_summary = pat.sub("current store policy details", updated_summary)
                if pat.search(updated_seo_desc):
                    updated_seo_desc = pat.sub("current store policy details", updated_seo_desc)

        # 4. Remove broken internal links pointing to non-existent products/collections if any
        soup = BeautifulSoup(updated_html, "html.parser")
        base_dom = self.store_manager.get_store(sid).resolved_public_domain.rstrip("/")
        for a_tag in list(soup.find_all("a", href=True)):
            href = (a_tag.get("href") or "").strip()
            if "/products/" in href:
                ph = href.split("/products/")[-1].strip("/").split("?")[0]
                if ph:
                    ev = self.catalog_service.get_product_evidence(sid, ph, verify_live_url=False)
                    if not ev.get("ok") or not (ev.get("product") or {}).get("is_published_online"):
                        # Unwrap broken product link so anchor text remains readable without a 404 link
                        a_tag.unwrap()
                        applied_edits.append(
                            {
                                "type": "unwrapped_non_live_product_link",
                                "detail": f"Removed link to non-live product handle '{ph}'",
                            }
                        )
            elif href.startswith(("/collections/", "/pages/", "/blogs/")) and verify_live_urls:
                v_res = self.catalog_service.verify_storefront_urls(sid, [f"{base_dom}{href}"])
                items = v_res.get("results") or []
                if items and not items[0].get("ok"):
                    a_tag.unwrap()
                    applied_edits.append(
                        {
                            "type": "unwrapped_broken_internal_link",
                            "detail": f"Removed broken internal link '{href}'",
                        }
                    )

        # If no valid internal links remain after unwrapping, add a contextual link to the store's main catalog/collection
        remaining_internal = [
            a
            for a in soup.find_all("a", href=True)
            if (a.get("href") or "").startswith("/")
            or (base_dom and (a.get("href") or "").startswith(base_dom))
        ]
        if not remaining_internal:
            q_fallback = " ".join([w for w in (title or "").lower().split() if w not in {"the", "a", "an", "and", "guide", "buying", "for", "with"}][:3])
            prods = self.catalog_service.search_products(sid, query=q_fallback, limit=3, active_only=True).get("products") or []
            if prods:
                top_p = prods[0]
                note_p = soup.new_tag("p")
                note_p.append("Explore more designs in our collection, including the ")
                link_tag = soup.new_tag("a", href=f"{base_dom}/products/{top_p['handle']}")
                link_tag.string = top_p["title"]
                note_p.append(link_tag)
                note_p.append(".")
                faq_sec = soup.find("section", class_="m5-faq-section")
                if faq_sec:
                    faq_sec.insert_before(note_p)
                else:
                    soup.append(note_p)
                applied_edits.append(
                    {
                        "type": "added_verified_product_link",
                        "detail": f"Added verified internal link to '/products/{top_p['handle']}'",
                    }
                )

        updated_html = str(soup)

        # 5. Heal corrupted price expressions
        from html_postprocessor import heal_corrupted_prices
        healed_html = heal_corrupted_prices(updated_html)
        if healed_html != updated_html:
            applied_edits.append({"type": "heal_prices", "detail": "Repaired corrupted price strings in body_html"})
            updated_html = healed_html

        healed_summary = heal_corrupted_prices(updated_summary)
        if healed_summary != updated_summary:
            applied_edits.append({"type": "heal_prices_summary", "detail": "Repaired corrupted price strings in summary"})
            updated_summary = healed_summary

        healed_seo_desc = heal_corrupted_prices(updated_seo_desc)
        if healed_seo_desc != updated_seo_desc:
            applied_edits.append({"type": "heal_prices_seo_desc", "detail": "Repaired corrupted price strings in seo_description"})
            updated_seo_desc = healed_seo_desc

        report = self.audit_article(
            store_id=sid,
            title=title,
            handle=handle,
            body_html=updated_html,
            summary=updated_summary,
            seo_title=seo_title,
            seo_description=updated_seo_desc,
            content_id=content_id,
            verify_live_urls=verify_live_urls,
        )
        return {
            "ok": report.passed,
            "store_id": sid,
            "content_id": content_id,
            "handle": handle,
            "applied_edits": applied_edits,
            "body_html": updated_html,
            "summary": updated_summary,
            "seo_description": updated_seo_desc,
            "report": report.to_dict(),
        }

    def save_fact_audit_report(self, report: FactAuditReport, output_root: Optional[ Any] = None) -> str:
        import json
        from pathlib import Path

        if output_root is None:
            output_root = Path(__file__).resolve().parent / "output" / report.store_id
        else:
            output_root = Path(output_root)
        output_root.mkdir(parents=True, exist_ok=True)
        path = output_root / f"{report.handle}_fact_audit.json"
        path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return str(path)

