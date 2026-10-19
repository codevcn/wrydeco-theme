import asyncio
from decimal import Decimal
from pathlib import Path

import pytest

from scraper.browser import AmazonBrowser, _clean_image_url, _dedupe_urls
from scraper.config import Settings


FIXTURES = Path(__file__).parent / "fixtures"


def test_amazon_image_variants_are_canonicalized():
    assert _clean_image_url("https://m.media-amazon.com/images/I/abc._AC_SX679_.jpg") == "https://m.media-amazon.com/images/I/abc.jpg"


def test_loading_indicators_and_utility_images_are_rejected():
    urls = _dedupe_urls([
        "https://m.media-amazon.com/images/G/01/ui/loadIndicators/loading-large_labeled._CB485921664_.gif",
        "https://m.media-amazon.com/images/G/01/x/transparent-1x1.png",
        "https://m.media-amazon.com/images/I/real._AC_SL1254_.jpg",
    ])
    assert urls == ["https://m.media-amazon.com/images/I/real.jpg"]


def test_gallery_aplus_and_top_document_customization(tmp_path):
    asyncio.run(_test_gallery_aplus_and_top_document_customization(tmp_path))


async def _test_gallery_aplus_and_top_document_customization(tmp_path):
    playwright = pytest.importorskip("playwright.async_api")
    async with playwright.async_playwright() as runtime:
        try:
            browser = await runtime.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"Playwright Chromium is not installed: {exc}")
        page = await browser.new_page()
        scraper = AmazonBrowser(Settings(profile_dir=tmp_path / "profile"))
        await page.set_content((FIXTURES / "pdp_lazy.html").read_text(encoding="utf-8"))
        await page.add_script_tag(path=str(Path(__file__).parents[1] / "extension" / "shared.js"))
        gallery = await scraper._extract_gallery(page)
        assert "https://images.example/one.jpg" in gallery
        assert "https://images.example/other-variant.jpg" not in gallery
        aplus, _, _ = await scraper._extract_aplus(page)
        assert "https://images.example/aplus.jpg" in aplus
        await page.set_content((FIXTURES / "customization.html").read_text(encoding="utf-8"))
        dynamic = await scraper._extract_dynamic(page, scraper.settings.price_tolerance * 10000)
        assert dynamic["verified_all"] is True
        assert str(dynamic["variants"][0]["verified_total"]) == "120.00"
        await browser.close()


def test_customization_iframe_is_detected(tmp_path):
    asyncio.run(_test_customization_iframe_is_detected(tmp_path))


async def _test_customization_iframe_is_detected(tmp_path):
    playwright = pytest.importorskip("playwright.async_api")
    async with playwright.async_playwright() as runtime:
        try:
            browser = await runtime.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"Playwright Chromium is not installed: {exc}")
        page = await browser.new_page()
        await page.set_content('<iframe id="gc-iframe" name="gc-iframe" srcdoc="<div class=gc-customization-page></div>"></iframe>')
        scraper = AmazonBrowser(Settings(profile_dir=tmp_path / "profile"))
        frame = await scraper._customization_frame(page)
        assert frame.name == "gc-iframe"
        await browser.close()


def test_gestalt_customization_prices_and_ignored_groups(tmp_path):
    asyncio.run(_test_gestalt_customization_prices_and_ignored_groups(tmp_path))


async def _test_gestalt_customization_prices_and_ignored_groups(tmp_path):
    playwright = pytest.importorskip("playwright.async_api")
    async with playwright.async_playwright() as runtime:
        try:
            browser = await runtime.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"Playwright Chromium is not installed: {exc}")
        page = await browser.new_page()
        await page.set_content((FIXTURES / "customization_gestalt.html").read_text(encoding="utf-8"))
        scraper = AmazonBrowser(Settings(profile_dir=tmp_path / "profile"))
        pricing = await scraper._extract_dynamic(page, Decimal("3415.00"))
        assert [group["name"] for group in pricing["option_types"]] == [
            "Choose Size", "Add On-Site Installation"
        ]
        # The existing Size/default rule intentionally removes the sole
        # zero-price first value, so only the two paid sizes remain.
        assert [variant["verified_total"] for variant in pricing["variants"]] == [
            Decimal("4215.00"), Decimal("4565.00"),
            Decimal("5015.00"), Decimal("5365.00"),
        ]
        assert pricing["variants"][0]["options"][0]["value"] == '26"W x 64"H x 14"D'
        assert pricing["variants"][0]["selection"][0]["dom_index"] == 1
        assert pricing["option_types"][0]["options"][0]["source_value"].endswith("Best Choice")
        await browser.close()


def test_standard_pdp_variations_are_clicked_and_price_verified(tmp_path):
    asyncio.run(_test_standard_pdp_variations_are_clicked_and_price_verified(tmp_path))


async def _test_standard_pdp_variations_are_clicked_and_price_verified(tmp_path):
    playwright = pytest.importorskip("playwright.async_api")
    async with playwright.async_playwright() as runtime:
        try:
            browser = await runtime.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"Playwright Chromium is not installed: {exc}")
        page = await browser.new_page()
        await page.set_content((FIXTURES / "pdp_variations.html").read_text(encoding="utf-8"))
        scraper = AmazonBrowser(Settings(profile_dir=tmp_path / "profile"))
        pricing = await scraper._extract_pdp_variations(page, Decimal("100.00"))
        assert pricing["source"] == "pdp_variation"
        assert [item["verified_total"] for item in pricing["variants"]] == [Decimal("100.00"), Decimal("125.00")]
        assert [item["options"][0]["value"] for item in pricing["variants"]] == ["Natural", "Walnut"]
        assert pricing["variants"][0]["options"][0]["source_value"] == "Natural (Recommended)"
        await browser.close()


def test_continue_shopping_interstitial_is_dismissed_and_pdp_reloaded(tmp_path):
    asyncio.run(_test_continue_shopping_interstitial_is_dismissed_and_pdp_reloaded(tmp_path))


async def _test_continue_shopping_interstitial_is_dismissed_and_pdp_reloaded(tmp_path):
    playwright = pytest.importorskip("playwright.async_api")
    from scraper.errors import NeedsAttention

    interstitial_html = """<!DOCTYPE html><html><head><title>Amazon.com</title></head><body>
    <div class="a-box a-alert a-alert-info"><h4>Click the button below to continue shopping</h4></div>
    <form method="get" action="/errors_page/validateCaptcha">
      <input type="hidden" name="amzn" value="token">
      <input type="hidden" name="amzn-r" value="/">
      <input type="hidden" name="field-keywords" value="PLFCGX">
      <button type="submit" class="a-button-text" alt="Continue shopping">Continue shopping</button>
    </form></body></html>"""
    home_html = "<!DOCTYPE html><html><head><title>Amazon.com</title></head><body><div>Home</div></body></html>"
    pdp_html = """<!DOCTYPE html><html><head><title>Amazon.com: Product</title></head><body>
    <span id="glow-ingress-line2">New York 10001</span>
    <span id="productTitle">Handcrafted Solid Wood Floating Shelf</span>
    </body></html>"""
    captcha_html = """<!DOCTYPE html><html><head><title>Robot Check</title></head><body>
    <h4>Enter the characters you see below</h4>
    <form method="get" action="/errors_page/validateCaptcha">
      <input type="text" id="captchacharacters" name="field-keywords">
      <button type="submit">Continue shopping</button>
    </form></body></html>"""

    async with playwright.async_playwright() as runtime:
        try:
            browser = await runtime.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"Playwright Chromium is not installed: {exc}")
        page = await browser.new_page()
        state = {"cleared": False}

        async def handle_route(route):
            url = route.request.url
            if "validateCaptcha" in url:
                state["cleared"] = True
                await route.fulfill(status=200, content_type="text/html", body=home_html)
            elif url.endswith("/dp/B0H6FGCCVP"):
                body = pdp_html if state["cleared"] else interstitial_html
                await route.fulfill(status=200, content_type="text/html", body=body)
            elif url.endswith("/dp/B0CAPTCHA1"):
                await route.fulfill(status=200, content_type="text/html", body=captcha_html)
            else:
                await route.fulfill(status=200, content_type="text/html", body=home_html)

        await page.route("**/*", handle_route)
        scraper = AmazonBrowser(Settings(profile_dir=tmp_path / "profile"))
        title = await scraper._load_pdp(page, "https://www.amazon.com/dp/B0H6FGCCVP", tmp_path / "evidence")
        assert state["cleared"] is True
        assert title == "Handcrafted Solid Wood Floating Shelf"

        with pytest.raises(NeedsAttention):
            await scraper._load_pdp(page, "https://www.amazon.com/dp/B0CAPTCHA1", tmp_path / "captcha_evidence")
        await browser.close()

