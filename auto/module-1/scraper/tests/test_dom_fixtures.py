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
        await browser.close()
