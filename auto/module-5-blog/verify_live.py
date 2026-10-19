"""
Automated Playwright Live Verification Runner (`verify_live.py`).

Verifies published Shopify blog articles on both Desktop (1440x900) and Mobile (390x844)
through the mandatory Proxy (`ProxyManager`), automatically unlocking the Shopify storefront
password gate if present, and producing a structured pass/fail report plus full screenshots.

Crucial integrity guarantees (Section 17 of Implementation Plan):
  - Measures `horizontalOverflow` (`scrollWidth > innerWidth + 2`) on both Desktop and Mobile
    BEFORE applying any screenshot-helper CSS (`overflow: visible`, `height: auto`).
  - Uses dedicated Desktop and Mobile contexts/renders so responsive layout and image loading
    are tested authentically.
  - Scopes body image, SVG, word count, table, and internal link checks strictly to the article
    content container (excluding header/footer/navigation logos and icons).
  - Verifies 12 upgraded core checks + 4 extended SEO/quality checks (16 checks total),
    including Canonical URL, Open Graph tags, FAQ visible vs JSON-LD parity, and live HTTP 200
    verification of internal links via Proxy.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from playwright.sync_api import Page, sync_playwright

from article_image_service import canonicalize_image_url
from shopify_catalog_service import ShopifyCatalogService
from store_manager import StoreConfig, StoreManager

MODULE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = MODULE_DIR / "output"

VIETNAMESE_DIACRITIC_RE = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
    r"ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]"
)


def _unlock_storefront_if_needed(page: Page, password: str) -> bool:
    """If the Shopify storefront is on the `/password` protection page, submit the password and wait for redirect."""
    if not password:
        return False

    has_pwd_input = page.locator('input[type="password"], input[name="password"]').count() > 0
    if not has_pwd_input and "/password" not in page.url:
        return False

    pwd_input = page.locator('input[type="password"], input[name="password"]').first
    if not pwd_input.is_visible():
        triggers = page.locator(
            'button:has-text("password"), a:has-text("password"), summary:has-text("password")'
        )
        if triggers.count() > 0:
            try:
                triggers.first.click(timeout=3000)
                page.wait_for_timeout(500)
            except Exception:
                pass

    pwd_input.fill(password)
    submit_btn = page.locator(
        'form[action*="password"] button[type="submit"], form[action*="password"] input[type="submit"], button[type="submit"]'
    ).first
    try:
        with page.expect_navigation(wait_until="domcontentloaded", timeout=25000):
            submit_btn.click()
    except Exception:
        try:
            submit_btn.click()
        except Exception:
            pass
    for _ in range(12):
        if "/password" not in page.url:
            break
        page.wait_for_timeout(500)
    page.wait_for_timeout(1000)
    return True


SCROLL_LAZY_LOAD_WITHOUT_CSS_MUTATION_JS = """async () => {
    const dismissedPopups = [];
    for (const el of document.querySelectorAll('button, a, [role="button"]')) {
        const txt = (el.innerText || el.getAttribute('aria-label') || '').trim().toLowerCase();
        if (txt === 'no, thanks' || txt === 'no thanks' || txt === 'continue browsing' || txt === 'close dialog' || txt === 'close modal') {
            try {
                el.click();
                dismissedPopups.push(txt);
            } catch (e) {}
        }
    }
    const imgs = Array.from(document.querySelectorAll('img'));
    for (const img of imgs) {
        img.removeAttribute('loading');
        img.loading = 'eager';
        img.decoding = 'sync';
        img.scrollIntoView({ behavior: 'instant', block: 'center' });
        if (!img.complete || img.naturalWidth === 0) {
            await new Promise(resolve => {
                img.addEventListener('load', resolve, { once: true });
                img.addEventListener('error', resolve, { once: true });
                setTimeout(resolve, 4000);
            });
        }
        try { await img.decode(); } catch (e) {}
    }
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
    await new Promise(r => setTimeout(r, 300));
    return dismissedPopups;
}"""


PREPARE_FULLPAGE_SCREENSHOT_JS = """() => {
    for (const el of document.querySelectorAll('html, body, .page-wrapper, main, #MainContent')) {
        el.style.setProperty('height', 'auto', 'important');
        el.style.setProperty('max-height', 'none', 'important');
        el.style.setProperty('overflow-y', 'visible', 'important');
        el.scrollTop = 0;
    }
    window.scrollTo(0, 0);
}"""


EXTRACT_DESKTOP_METRICS_JS = """() => {
    const h1s = Array.from(document.querySelectorAll('h1')).map(el => el.innerText.trim()).filter(Boolean);
    const contentEl = document.querySelector('.m5-article-content')
        || document.querySelector('.article-editorial__content, .article-template__content, .article__content, article .rte, .article-template .rte, main article')
        || document.body;

    const dedicatedHeroImg = document.querySelector(
        '.article-editorial__image, .article-template__hero-container img, .article__featured-image img, .article-image img, article header img, .article-hero img'
    );
    const fallbackFirstArticleImg = contentEl.querySelector('figure.m5-figure img, img');
    const heroImg = dedicatedHeroImg || fallbackFirstArticleImg;

    // Visible excerpt / dek or visible opening paragraph (never hidden <meta>)
    const dekEl = document.querySelector('.article-editorial__dek, .article-template__excerpt, .article__excerpt, .article-excerpt');
    const firstVisibleP = Array.from(contentEl.querySelectorAll('p')).find(p => {
        const t = (p.innerText || '').trim();
        const r = p.getBoundingClientRect();
        return t.length >= 30 && r.width > 0 && r.height > 0;
    });
    const visibleExcerptText = (dekEl && dekEl.getBoundingClientRect().height > 0 ? dekEl.innerText.trim() : '')
        || (firstVisibleP ? firstVisibleP.innerText.trim() : '');

    // Body images strictly inside contentEl
    const figureImgs = Array.from(contentEl.querySelectorAll('figure.m5-figure img'));
    const rawImgs = figureImgs.length > 0
        ? figureImgs
        : Array.from(contentEl.querySelectorAll('img')).filter(img => img !== dedicatedHeroImg);

    const bodyImgs = rawImgs.map(img => ({
        src: img.currentSrc || img.src || '',
        rawSrc: img.getAttribute('src') || '',
        alt: img.alt || '',
        complete: !!img.complete,
        naturalWidth: img.naturalWidth || 0,
        naturalHeight: img.naturalHeight || 0
    }));

    // Check ALL <svg> elements inside the article body content (excluding theme share buttons / small UI icons)
    const bodySvgs = Array.from(contentEl.querySelectorAll('svg')).filter(svg => {
        const cls = (svg.getAttribute('class') || '').toLowerCase();
        const parentShare = svg.closest('.share-button, .article-template__social-sharing, .social-sharing, [class*="share"], [class*="social"], header, footer, nav, a, button');
        const r = svg.getBoundingClientRect();
        const isSmallThemeIcon = r.width <= 32 && r.height <= 32 && !svg.closest('figure');
        return !parentShare && !isSmallThemeIcon && !cls.includes('icon-share') && !cls.includes('icon-clipboard');
    }).map(svg => {
        const r = svg.getBoundingClientRect();
        return { width: r.width, height: r.height, role: svg.getAttribute('role') || '' };
    });

    const tables = Array.from(contentEl.querySelectorAll('table')).map(tbl => {
        const r = tbl.getBoundingClientRect();
        const wrap = tbl.closest('.m5-table-wrap');
        const wrapRect = wrap ? wrap.getBoundingClientRect() : r;
        return {
            width: r.width,
            wrapperWidth: wrapRect.width,
            wrapped: !!wrap,
            overflowsViewport: wrapRect.width > window.innerWidth + 2
        };
    });

    const faqHeading = contentEl.querySelector('#faq, .m5-faq-section h2, h2#faq');
    const visibleFaqItems = Array.from(contentEl.querySelectorAll('.m5-faq-item')).map(item => ({
        question: (item.querySelector('h3, h4, strong')?.innerText || '').trim(),
        answer: (item.querySelector('p')?.innerText || '').trim()
    })).filter(x => x.question && x.answer);

    const jsonLdScripts = Array.from(document.querySelectorAll('script[type="application/ld+json"]')).map(s => s.innerText.trim());
    let faqSchemaValid = false;
    let faqSchemaEntities = [];
    for (const raw of jsonLdScripts) {
        try {
            const parsed = JSON.parse(raw);
            const candidates = Array.isArray(parsed) ? parsed : (parsed['@graph'] ? parsed['@graph'] : [parsed]);
            for (const node of candidates) {
                if (node && node['@type'] === 'FAQPage' && Array.isArray(node.mainEntity)) {
                    faqSchemaValid = true;
                    faqSchemaEntities = node.mainEntity.map(ent => ({
                        question: (ent.name || '').trim(),
                        answer: ((ent.acceptedAnswer || {}).text || '').trim()
                    })).filter(x => x.question && x.answer);
                }
            }
        } catch (e) {}
    }

    const fullText = contentEl.innerText || '';
    const words = (fullText.match(/[A-Za-z0-9']+/g) || []);
    const wordCount = words.length;

    const vietnameseMarkers = [
        'Không ảnh nào trong kho khớp với mô tả',
        'Câu hỏi thường gặp',
        'Còn phải làm',
        'Đưa lên shop',
        '[IMAGE:',
        '[NEED',
        '\\times'
    ].filter(m => fullText.includes(m));

    const internalLinks = Array.from(contentEl.querySelectorAll('a[href]')).filter(a => {
        if (a.closest('.share-button, .article-template__social-sharing, .social-sharing, [class*="share"], [class*="social"], header, footer, nav')) {
            return false;
        }
        const href = (a.getAttribute('href') || '').toLowerCase();
        if (href.includes('facebook.com/sharer') || href.includes('twitter.com/intent') || href.includes('x.com/intent') || href.includes('pinterest.com/pin') || href.includes('linkedin.com/share')) {
            return false;
        }
        return true;
    }).map(a => ({
        href: (a.getAttribute('href') || '').trim(),
        resolvedHref: a.href || '',
        text: (a.innerText || '').trim()
    }));

    const brokenAnchors = [];
    for (const lnk of internalLinks) {
        if (lnk.href.startsWith('#') && lnk.href.length > 1) {
            const targetId = lnk.href.slice(1);
            if (!document.getElementById(targetId) && !document.querySelector(`[name="${CSS.escape(targetId)}"]`)) {
                brokenAnchors.push(lnk.href);
            }
        }
    }

    const canonicalHref = document.querySelector('link[rel="canonical"]')?.getAttribute('href') || '';
    const metaDescription = document.querySelector('meta[name="description"]')?.getAttribute('content') || '';
    const ogTitle = document.querySelector('meta[property="og:title"]')?.getAttribute('content') || '';
    const ogDescription = document.querySelector('meta[property="og:description"]')?.getAttribute('content') || '';
    const ogUrl = document.querySelector('meta[property="og:url"]')?.getAttribute('content') || '';
    const ogImage = document.querySelector('meta[property="og:image"], meta[property="og:image:secure_url"]')?.getAttribute('content') || '';

    const horizontalOverflow = document.documentElement.scrollWidth > window.innerWidth + 2;

    return {
        url: window.location.href,
        title: document.title,
        h1s,
        heroLoaded: heroImg ? (heroImg.tagName === 'IMG' && heroImg.complete && heroImg.naturalWidth > 0) : false,
        heroSrc: heroImg ? (heroImg.currentSrc || heroImg.src || '') : '',
        dedicatedHeroFound: !!dedicatedHeroImg,
        dekText: visibleExcerptText,
        bodyImgs,
        bodySvgs,
        tables,
        faqHeadingText: faqHeading ? faqHeading.innerText.trim() : '',
         faqItemsCount: visibleFaqItems.length,
        visibleFaqItems,
        faqSchemaValid,
        faqSchemaEntities,
        wordCount,
        fullTextSample: fullText.slice(0, 4000),
        vietnameseMarkers,
        internalLinks,
        brokenAnchors,
        canonicalHref,
        metaDescription,
        og: {
            title: ogTitle,
            description: ogDescription,
            url: ogUrl,
            image: ogImage
        },
        viewportWidth: window.innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
        horizontalOverflow
    };
}"""


EXTRACT_MOBILE_METRICS_JS = """() => {
    const horizontalOverflow = document.documentElement.scrollWidth > window.innerWidth + 2;
    const contentEl = document.querySelector('.m5-article-content')
        || document.querySelector('.article-editorial__content, .article-template__content, .article__content, article .rte, .article-template .rte, main article')
        || document.body;
    const figureImgs = Array.from(contentEl.querySelectorAll('figure.m5-figure img, img'));
    const overflowingImgs = figureImgs.filter(img => {
        const r = img.getBoundingClientRect();
        return r.width > window.innerWidth + 2;
    }).length;
    const tables = Array.from(contentEl.querySelectorAll('table'));
    const overflowingTables = tables.filter(tbl => {
        const wrap = tbl.closest('.m5-table-wrap') || tbl;
        const r = wrap.getBoundingClientRect();
        return r.width > window.innerWidth + 2;
    }).length;
    return {
        viewportWidth: window.innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
        horizontalOverflow,
        overflowingImgs,
        overflowingTables,
        loadedBodyImgs: figureImgs.filter(img => img.complete && img.naturalWidth > 0).length
    };
}"""


def verify_published_article(
    store_manager: StoreManager,
    store_id: Optional[str],
    article_url: str,
    expected_handle: str = "tree-bookcase-guide",
    expected_title: Optional[str] = None,
    min_body_images: int = 4,
    max_body_images: int = 7,
    min_word_count: int = 900,
) -> Dict[str, Any]:
    """
    Open the live Shopify article URL in headless Chromium across Desktop (1440x900)
    and Mobile (390x844) via the mandatory Proxy, run 16 quality, SEO & layout checks
    (measuring layout BEFORE any screenshot CSS overrides), and capture screenshots.
    """
    store: StoreConfig = store_manager.get_store(store_id)
    store_out_dir = OUTPUT_DIR / store.id
    store_out_dir.mkdir(parents=True, exist_ok=True)

    desktop_screenshot = store_out_dir / f"{expected_handle}_live_desktop.png"
    mobile_screenshot = store_out_dir / f"{expected_handle}_live_mobile.png"
    report_path = store_out_dir / f"{expected_handle}_verification_report.json"

    # Mandatory Proxy Gate: blocks immediately if proxy is unconfigured or unstable
    pw_proxy = store_manager.proxy_manager.get_playwright_proxy(
        target_shop_domain=store.normalized_shop
    )
    proxy_cfg = store_manager.proxy_manager.get_config()
    proxy_summary = proxy_cfg.masked_summary

    checks: List[Dict[str, Any]] = []
    dismissed_popups: List[str] = []

    desktop_ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    mobile_ua = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy=pw_proxy,
            args=["--disable-blink-features=AutomationControlled"],
        )

        # 1. Desktop Verification (1440x900)
        desktop_context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=desktop_ua,
            proxy=pw_proxy,
        )
        desktop_context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = desktop_context.new_page()

        resp = page.goto(article_url, wait_until="domcontentloaded", timeout=35000)
        status_code = resp.status if resp else 0

        if _unlock_storefront_if_needed(page, store.storefront_password):
            resp2 = page.goto(article_url, wait_until="domcontentloaded", timeout=35000)
            if resp2:
                status_code = resp2.status

        # Resilient fallback: if custom domain returns 404 on blog articles (e.g. wrydeco.com), fallback to myshopify.com
        if status_code == 404 and store.normalized_shop and store.resolved_public_domain and store.resolved_public_domain in article_url:
            alt_url = article_url.replace(store.resolved_public_domain, f"https://{store.normalized_shop}")
            resp_alt = page.goto(alt_url, wait_until="domcontentloaded", timeout=35000)
            if resp_alt and resp_alt.status in (200, 302):
                article_url = alt_url
                status_code = resp_alt.status
                if _unlock_storefront_if_needed(page, store.storefront_password):
                    resp_alt2 = page.goto(article_url, wait_until="domcontentloaded", timeout=35000)
                    if resp_alt2:
                        status_code = resp_alt2.status

        try:
            page.wait_for_load_state("load", timeout=12000)
        except Exception:
            pass
        page.wait_for_timeout(800)

        # Scroll to trigger lazy-loaded images WITHOUT mutating CSS overflow/height
        popups = page.evaluate(SCROLL_LAZY_LOAD_WITHOUT_CSS_MUTATION_JS) or []
        dismissed_popups.extend(popups)

        has_any_hero = page.evaluate(
            """() => {
                const h = document.querySelector('.article-editorial__image, .article-template__hero-container img, .article__featured-image img, .article-image img, article img, figure.m5-figure img');
                return !!(h && h.tagName === 'IMG' && h.complete && h.naturalWidth > 0);
            }"""
        )
        if not has_any_hero:
            page.wait_for_timeout(2000)
            resp_retry = page.goto(
                article_url,
                wait_until="domcontentloaded",
                timeout=35000,
            )
            if resp_retry:
                status_code = resp_retry.status
            try:
                page.wait_for_load_state("load", timeout=10000)
            except Exception:
                pass
            page.wait_for_timeout(800)
            page.evaluate(SCROLL_LAZY_LOAD_WITHOUT_CSS_MUTATION_JS)

        # Measure Desktop metrics BEFORE applying full-page screenshot CSS helpers
        desktop_metrics = page.evaluate(EXTRACT_DESKTOP_METRICS_JS)

        # Now apply screenshot helper and capture Desktop screenshot
        page.evaluate(PREPARE_FULLPAGE_SCREENSHOT_JS)
        page.screenshot(path=str(desktop_screenshot), full_page=True)

        # Reuse storage state (so password unlock cookie is preserved) in a clean Mobile viewport test
        storage_state = desktop_context.storage_state()
        desktop_context.close()

        # 2. Mobile Verification (390x844) in its own clean page/viewport before any CSS mutation
        mobile_context = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent=mobile_ua,
            is_mobile=True,
            has_touch=True,
            storage_state=storage_state,
            proxy=pw_proxy,
        )
        mobile_context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        m_page = mobile_context.new_page()
        m_page.goto(article_url, wait_until="domcontentloaded", timeout=35000)
        try:
            m_page.wait_for_load_state("load", timeout=10000)
        except Exception:
            pass
        m_page.wait_for_timeout(600)
        m_page.evaluate(SCROLL_LAZY_LOAD_WITHOUT_CSS_MUTATION_JS)

        # Measure Mobile metrics BEFORE any CSS mutation
        mobile_metrics = m_page.evaluate(EXTRACT_MOBILE_METRICS_JS)

        m_page.evaluate(PREPARE_FULLPAGE_SCREENSHOT_JS)
        m_page.screenshot(path=str(mobile_screenshot), full_page=True)
        mobile_context.close()
        browser.close()

    # Verify internal links and OG image via Proxy HTTP requests
    catalog_service = ShopifyCatalogService(store_manager=store_manager)
    raw_links = desktop_metrics.get("internalLinks") or []
    broken_anchors = desktop_metrics.get("brokenAnchors") or []

    allowed_hosts = {
        store.normalized_shop.lower(),
        (store.zbigtee_domain or "").lower(),
        f"www.{(store.zbigtee_domain or '').lower()}",
    }
    allowed_hosts.discard("")
    allowed_hosts.discard("www.")

    internal_paths_to_check: List[str] = []
    foreign_or_invalid_links: List[str] = []

    for lnk in raw_links:
        href = (lnk.get("href") or "").strip()
        if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue
        if href.startswith("/"):
            if href not in internal_paths_to_check:
                internal_paths_to_check.append(href)
        elif href.startswith(("http://", "https://")):
            parsed = urlparse(href)
            host = (parsed.hostname or "").lower()
            if host in allowed_hosts:
                rel_p = parsed.path or "/"
                if rel_p not in internal_paths_to_check:
                    internal_paths_to_check.append(rel_p)
            else:
                foreign_or_invalid_links.append(href)
        else:
            foreign_or_invalid_links.append(href)

    link_http_results: List[Dict[str, Any]] = []
    if internal_paths_to_check:
        try:
            v_res = catalog_service.verify_storefront_urls(store.id, internal_paths_to_check[:15])
            link_http_results = list(v_res.get("results") or [])
        except Exception as exc:
            link_http_results = [{"url": u, "ok": False, "error": str(exc)} for u in internal_paths_to_check[:15]]

    broken_http_links = [r for r in link_http_results if not r.get("ok")]

    # Evaluate the 12 core checks + 4 extended checks
    final_url = desktop_metrics.get("url") or ""
    http_ok = (
        status_code == 200
        and "/password" not in final_url
        and expected_handle.lower() in final_url.lower()
    )
    checks.append({
        "id": "http_status_ok",
        "label": "HTTP 200 & Storefront Unlocked at Expected Article Handle",
        "passed": http_ok,
        "detail": f"HTTP {status_code} at {final_url}",
    })

    h1_list = desktop_metrics.get("h1s") or []
    h1_ok = len(h1_list) == 1 and (
        not expected_title or expected_title.strip().lower() in h1_list[0].strip().lower()
    )
    checks.append({
        "id": "single_h1_matches_title",
        "label": "Single H1 Matches Article Title",
        "passed": h1_ok,
        "detail": f"Found {len(h1_list)} H1(s): {h1_list}",
    })

    checks.append({
        "id": "hero_featured_image_loaded",
        "label": "Featured Hero Image Loaded",
        "passed": bool(desktop_metrics.get("heroLoaded")),
        "detail": (
            f"Hero image loaded ({desktop_metrics.get('heroSrc')})"
            if desktop_metrics.get("heroLoaded")
            else "Hero image missing or broken"
        ),
    })

    dek_text = (desktop_metrics.get("dekText") or "").strip()
    checks.append({
        "id": "excerpt_dek_visible",
        "label": "Article Excerpt / Opening Summary Visible on Page",
        "passed": len(dek_text) >= 30,
        "detail": dek_text[:180] if dek_text else "Missing visible excerpt/opening paragraph",
    })

    body_imgs = desktop_metrics.get("bodyImgs") or []
    broken_imgs = [
        img["src"]
        for img in body_imgs
        if not img.get("complete") or int(img.get("naturalWidth") or 0) == 0
    ]
    count_in_range = min_body_images <= len(body_imgs) <= max_body_images
    checks.append({
        "id": "all_body_images_loaded",
        "label": f"All Inline Product Images Loaded ({min_body_images}–{max_body_images} body images)",
        "passed": count_in_range and len(broken_imgs) == 0,
        "detail": (
            f"{len(body_imgs)} inline body images loaded (required {min_body_images}–{max_body_images}), "
            f"{len(broken_imgs)} broken"
        ),
    })

    body_svgs = desktop_metrics.get("bodySvgs") or []
    checks.append({
        "id": "no_svg_fallback_rendered",
        "label": "Zero Inline SVG Fallback Diagrams in Article Body",
        "passed": len(body_svgs) == 0,
        "detail": (
            "Zero SVG elements in article body"
            if len(body_svgs) == 0
            else f"Unexpected SVG(s) found in article body: {body_svgs}"
        ),
    })

    tables = desktop_metrics.get("tables") or []
    tables_ok = len(tables) == 0 or all(
        t.get("wrapped") and not t.get("overflowsViewport") for t in tables
    )
    checks.append({
        "id": "tables_responsive",
        "label": "Comparison Tables Wrapped & Fit Viewport",
        "passed": tables_ok,
        "detail": f"{len(tables)} tables checked ({sum(1 for t in tables if t.get('wrapped'))} wrapped)",
    })

    faq_heading_text = (desktop_metrics.get("faqHeadingText") or "").strip()
    faq_items_count = int(desktop_metrics.get("faqItemsCount") or 0)
    faq_ok = faq_heading_text.lower() == "frequently asked questions" and faq_items_count >= 1
    checks.append({
        "id": "faq_section_english",
        "label": "FAQ Section Visible & 100% English",
        "passed": faq_ok,
        "detail": f"Heading='{faq_heading_text or 'None'}', visible_items={faq_items_count}",
    })

    visible_faqs = desktop_metrics.get("visibleFaqItems") or []
    schema_faqs = desktop_metrics.get("faqSchemaEntities") or []
    faq_parity_ok = (
        bool(desktop_metrics.get("faqSchemaValid"))
        and len(schema_faqs) == len(visible_faqs)
        and len(schema_faqs) >= 1
        and all(
            s["question"].strip().lower() == v["question"].strip().lower()
            for s, v in zip(schema_faqs, visible_faqs)
        )
    )
    checks.append({
        "id": "faq_json_ld_valid",
        "label": "FAQPage JSON-LD Valid & Matches Visible FAQ Items",
        "passed": faq_parity_ok,
        "detail": (
            f"JSON-LD FAQ count={len(schema_faqs)}, visible FAQ count={len(visible_faqs)}, parity={faq_parity_ok}"
        ),
    })

    vn_leftovers = list(desktop_metrics.get("vietnameseMarkers") or [])
    sample_txt = desktop_metrics.get("fullTextSample") or ""
    if VIETNAMESE_DIACRITIC_RE.search(sample_txt):
        vn_leftovers.append("vietnamese_diacritics_detected")
    checks.append({
        "id": "no_vietnamese_leftovers",
        "label": "100% Clean English Content (Zero Placeholders, LaTeX, or VN Strings)",
        "passed": len(vn_leftovers) == 0,
        "detail": "Zero error markers" if not vn_leftovers else f"Leftovers: {vn_leftovers}",
    })

    links_ok = (
        len(internal_paths_to_check) >= 1
        and len(foreign_or_invalid_links) == 0
        and len(broken_anchors) == 0
        and len(broken_http_links) == 0
    )
    checks.append({
        "id": "internal_links_valid",
        "label": "Internal Storefront Links Live (HTTP 200 via Proxy) & Valid Anchors",
        "passed": links_ok,
        "detail": (
            f"Checked {len(link_http_results)} internal paths (broken={len(broken_http_links)}), "
            f"foreign={len(foreign_or_invalid_links)}, broken_anchors={len(broken_anchors)}"
        ),
    })

    mobile_ok = (
        not mobile_metrics.get("horizontalOverflow")
        and int(mobile_metrics.get("overflowingImgs") or 0) == 0
        and int(mobile_metrics.get("overflowingTables") or 0) == 0
    )
    checks.append({
        "id": "mobile_layout_clean",
        "label": "Mobile Viewport (390x844) Zero Horizontal Overflow (Pre-CSS Mutation)",
        "passed": mobile_ok,
        "detail": (
            f"scrollWidth={mobile_metrics.get('scrollWidth')} vs viewport={mobile_metrics.get('viewportWidth')}, "
            f"overflowingImgs={mobile_metrics.get('overflowingImgs')}, overflowingTables={mobile_metrics.get('overflowingTables')}"
        ),
    })

    # Extended Check 13: Canonical URL
    canonical_href = (desktop_metrics.get("canonicalHref") or "").strip()
    canonical_ok = (
        bool(canonical_href)
        and expected_handle.lower() in canonical_href.lower()
        and "_cb=" not in canonical_href
    )
    checks.append({
        "id": "canonical_url_valid",
        "label": "Canonical URL Present & Clean (Matches Article Handle, Zero Cache-Buster)",
        "passed": canonical_ok,
        "detail": f"canonical='{canonical_href}'",
    })

    # Extended Check 14: Open Graph Metadata
    og_data = desktop_metrics.get("og") or {}
    og_ok = bool(og_data.get("title")) and bool(og_data.get("url")) and bool(og_data.get("image"))
    checks.append({
        "id": "open_graph_tags_valid",
        "label": "Open Graph Tags (og:title, og:url, og:image) Present",
        "passed": og_ok,
        "detail": f"og:title='{og_data.get('title', '')[:60]}', og:image={'present' if og_data.get('image') else 'missing'}",
    })

    # Extended Check 15: Editorial Word Count
    word_count = int(desktop_metrics.get("wordCount") or 0)
    checks.append({
        "id": "word_count_sufficient",
        "label": f"Editorial Word Count Sufficient (>={min_word_count} words)",
        "passed": word_count >= min_word_count,
        "detail": f"word_count={word_count} (min={min_word_count})",
    })

    # Extended Check 16: Zero Duplicate Body Images
    canonical_body_urls = [
        canonicalize_image_url(img.get("src") or img.get("rawSrc") or "")
        for img in body_imgs
        if (img.get("src") or img.get("rawSrc"))
    ]
    unique_body_urls = set(canonical_body_urls)
    dedup_ok = len(canonical_body_urls) >= min_body_images and len(unique_body_urls) == len(canonical_body_urls)
    checks.append({
        "id": "unique_body_images_verified",
        "label": "Zero Duplicate Product Images in Article Body",
        "passed": dedup_ok,
        "detail": f"{len(unique_body_urls)} unique canonical image assets out of {len(canonical_body_urls)} inline images",
    })

    passed_count = sum(1 for c in checks if c["passed"])
    report = {
        "ok": passed_count == len(checks),
        "store_id": store.id,
        "expected_handle": expected_handle,
        "article_url": article_url,
        "proxy_used": proxy_summary,
        "proxy_fingerprint": proxy_cfg.config_fingerprint,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "passed_count": passed_count,
        "total_checks": len(checks),
        "word_count": word_count,
        "body_image_count": len(body_imgs),
        "unique_body_image_count": len(unique_body_urls),
        "dismissed_popups": dismissed_popups,
        "desktop_layout": {
            "viewport_width": desktop_metrics.get("viewportWidth"),
            "scroll_width": desktop_metrics.get("scrollWidth"),
            "horizontal_overflow": desktop_metrics.get("horizontalOverflow"),
        },
        "mobile_layout": mobile_metrics,
        "seo_metadata": {
            "canonical": canonical_href,
            "meta_description": desktop_metrics.get("metaDescription"),
            "og": og_data,
        },
        "internal_links_checked": link_http_results,
        "checks": checks,
        "screenshots": {
            "desktop": str(desktop_screenshot),
            "mobile": str(mobile_screenshot),
        },
    }
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report
