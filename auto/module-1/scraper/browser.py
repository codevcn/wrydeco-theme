from __future__ import annotations

import asyncio
import json
import re
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .config import Settings
from .errors import BrowserAutomationError, NeedsAttention, PriceValidationError
from .events import EventCallback, emit
from .pricing import (
    build_combinations,
    is_ignored_type,
    money,
    normalize_name,
    parse_additional_price,
    parse_base_price,
    remove_default_option,
    uses_default_removal,
    verify_total,
)


@dataclass
class BrowserResult:
    source: dict[str, Any]
    pricing: dict[str, Any]


def _clean_image_url(url: str) -> str:
    url = str(url or "").strip()
    if not url or url.startswith(("data:", "blob:")):
        return ""
    parts = urlsplit(url)
    path = parts.path
    if parts.netloc.casefold().endswith("media-amazon.com"):
        path = re.sub(r"\._[^/]+(?=\.(?:jpe?g|png|webp)$)", "", path, flags=re.I)
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def _is_loading_or_utility_image(url: str) -> bool:
    lowered = str(url or "").casefold()
    return not lowered or any(marker in lowered for marker in (
        "loadindicator", "loading-", "/loading", "spinner", "ajax-loader",
        "play-button", "sprite", "transparent-pixel", "transparent-1x1",
        "grey-pixel", "gray-pixel", "pixel.gif", "1x1.gif",
    ))


def _dedupe_urls(urls: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for raw in urls:
        url = _clean_image_url(raw)
        lowered = url.casefold()
        if not url or url in seen or _is_loading_or_utility_image(lowered):
            continue
        seen.add(url)
        output.append(url)
    return output


class AmazonBrowser:
    CUSTOMIZATION_TRIGGER_SELECTORS = (
        "#gestalt-popover-button-announce",
        "#customization-button",
        "#custom-actions-container a",
        ".gc-customization-btn",
        "#gc-customize-button",
        "#customizeButton",
        "input[name='submit.customize']",
        "a[href*='customization-dialog']",
        "a:has-text('Customize now')",
        "button:has-text('Customize now')",
    )

    def __init__(self, settings: Settings, event_callback: EventCallback | None = None):
        self.settings = settings
        self.event_callback = event_callback
        self._playwright = None
        self.context = None

    async def __aenter__(self) -> "AmazonBrowser":
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise BrowserAutomationError("Playwright is required. Run: pip install -r scraper/requirements.txt && playwright install chromium") from exc
        self.settings.profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()
        self.context = await self._playwright.chromium.launch_persistent_context(
            str(self.settings.profile_dir),
            headless=self.settings.headless,
            viewport={"width": 1440, "height": 1000},
            locale="en-US",
            args=["--disable-blink-features=AutomationControlled"],
        )
        await self.context.add_cookies([
            {"name": "lc-main", "value": "en_US", "domain": ".amazon.com", "path": "/"},
            {"name": "i18n-prefs", "value": "USD", "domain": ".amazon.com", "path": "/"},
        ])
        self.context.set_default_timeout(self.settings.browser_timeout_ms)
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self.context:
            await self.context.close()
        if self._playwright:
            await self._playwright.stop()

    async def crawl(self, url: str, evidence_dir: Path, mode: str) -> BrowserResult:
        if not self.context:
            raise RuntimeError("AmazonBrowser must be used as an async context manager.")
        page = await self.context.new_page()
        try:
            print(f"[{evidence_dir.parent.name}] loading Amazon PDP")
            asin = evidence_dir.parent.name
            emit(self.event_callback, "crawl_stage", asin=asin, stage="pdp_loading")
            await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            await self._ensure_delivery_location(page)
            await page.add_script_tag(path=str(Path(__file__).parent / "extension" / "shared.js"))
            await self._check_challenge(page, evidence_dir)
            title = await self._first_text(page, ["#productTitle", "h1 span"])
            base_text = await self._first_text(page, [
                "#corePrice_feature_div .a-price .a-offscreen",
                "#apex_desktop .a-price .a-offscreen",
                "#priceblock_ourprice", "#priceblock_dealprice", "#price_inside_buybox",
            ])
            if not title:
                raise BrowserAutomationError("Amazon PDP is missing a visible product title.")
            base_price: Decimal | None = parse_base_price(base_text) if base_text else None
            if base_price is None and mode in {"auto", "dynamic"}:
                try:
                    print(f"[{evidence_dir.parent.name}] locating customization base price")
                    frame = await self._customization_frame(page)
                    base_price = await self._wait_stable_footer_price(frame)
                except BrowserAutomationError:
                    if mode == "dynamic":
                        raise
            if base_price is None:
                base_price = Decimal("0.00")
            print(f"[{evidence_dir.parent.name}] hydrating gallery and A+ content")
            emit(self.event_callback, "crawl_stage", asin=asin, stage="gallery")
            gallery = await self._extract_gallery(page)
            emit(self.event_callback, "crawl_progress", asin=asin, stage="gallery", current=len(gallery), total=len(gallery))
            emit(self.event_callback, "crawl_stage", asin=asin, stage="aplus")
            aplus, aplus_html, aplus_text = await self._extract_aplus(page)
            emit(self.event_callback, "crawl_progress", asin=asin, stage="aplus", current=len(aplus), total=len(aplus))
            bullets = await page.locator("#feature-bullets li span.a-list-item").all_inner_texts()
            source = {
                "url": page.url,
                "title": title,
                "bullets": [text.strip() for text in bullets if text.strip()],
                "gallery_images": gallery,
                "aplus_images": aplus,
                "aplus_html": aplus_html,
                "aplus_text": aplus_text,
                "base_price": str(base_price),
            }
            pricing: dict[str, Any] = {"mode": mode, "base_price": str(base_price), "option_types": [], "variants": []}
            if mode in {"auto", "dynamic"}:
                try:
                    print(f"[{evidence_dir.parent.name}] extracting and verifying customization combinations")
                    emit(self.event_callback, "crawl_stage", asin=asin, stage="customization")
                    pricing = await self._extract_dynamic(page, base_price, asin=asin)
                except BrowserAutomationError as customization_error:
                    # A customizable product must never silently degrade to its
                    # ordinary Color/Style twister.  That was the source of a
                    # dangerous false-success where all Shopify variants were
                    # assigned the PDP base price.
                    if await self._has_customization_ui(page):
                        raise customization_error
                    try:
                        print(f"[{evidence_dir.parent.name}] verifying standard PDP variations")
                        pricing = await self._extract_pdp_variations(page, base_price)
                    except BrowserAutomationError:
                        if mode == "dynamic":
                            raise customization_error
            await self._save_evidence(page, evidence_dir, "pdp")
            return BrowserResult(source=source, pricing=pricing)
        except NeedsAttention:
            raise
        except Exception:
            await self._save_evidence(page, evidence_dir, "failure")
            raise
        finally:
            await page.close()

    async def _check_challenge(self, page: Any, evidence_dir: Path) -> None:
        title = (await page.title()).casefold()
        body = (await page.locator("body").inner_text(timeout=5_000)).casefold()
        challenged = any(value in title or value in body[:5000] for value in (
            "robot check", "enter the characters you see below", "validatecaptcha", "sorry, we just need to make sure",
        ))
        if challenged or "validatecaptcha" in page.url.casefold():
            await self._save_evidence(page, evidence_dir, "challenge")
            raise NeedsAttention("Amazon presented a CAPTCHA/challenge; no bypass was attempted.")

    async def _ensure_delivery_location(self, page: Any) -> None:
        postal_code = self.settings.amazon_postal_code.strip()
        if not postal_code:
            return
        location = await self._first_text(page, ["#glow-ingress-line2", "#nav-global-location-data-modal-action"])
        if postal_code in location:
            return
        try:
            trigger = page.locator("#glow-ingress-block, #nav-global-location-popover-link").first
            if not await trigger.count() or not await trigger.is_visible():
                return
            await trigger.click(timeout=3_000)
            zip_input = page.locator("#GLUXZipUpdateInput, input[data-action='GLUXPostalInputAction']").first
            await zip_input.wait_for(state="visible", timeout=5_000)
            await zip_input.fill(postal_code)
            apply_button = page.locator("#GLUXZipUpdate input[type='submit'], #GLUXZipUpdate-announce, input[aria-labelledby='GLUXZipUpdate-announce']").first
            await apply_button.click(timeout=3_000)
            await page.wait_for_timeout(800)
            done = page.locator("#GLUXConfirmClose, button:has-text('Done'), input[value='Continue']").first
            if await done.count() and await done.is_visible():
                await done.click(timeout=2_000)
            await page.reload(wait_until="domcontentloaded", timeout=60_000)
        except Exception:
            # Location setup is a rendering aid. The strict data checks below still prevent an unsafe update.
            return

    async def _save_evidence(self, page: Any, directory: Path, prefix: str) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        try:
            await page.screenshot(path=str(directory / f"{prefix}.png"), full_page=True)
        except Exception:
            pass
        try:
            (directory / f"{prefix}.html").write_text(await page.content(), encoding="utf-8")
        except Exception:
            pass

    async def _first_text(self, page_or_frame: Any, selectors: list[str]) -> str:
        for selector in selectors:
            matches = page_or_frame.locator(selector)
            for index in range(await matches.count()):
                locator = matches.nth(index)
                try:
                    if await locator.is_visible():
                        value = " ".join((await locator.inner_text()).replace("\xa0", " ").split())
                        if value:
                            return value
                except Exception:
                    continue
        return ""

    async def _extract_gallery(self, page: Any) -> list[str]:
        seed_urls: list[str] = await page.evaluate(r"""() => {
          const shared = globalThis.WRYDECO_SCRAPER_SHARED;
          return shared ? shared.extractGalleryUrls(document) : [];
        }""")
        urls = _dedupe_urls(seed_urls)

        # Amazon only creates the complete immersive gallery after the main media is
        # clicked.  The large image briefly becomes a loading-indicator GIF after
        # each thumbnail click, so never trust a fixed delay or the thumbnail URL.
        main = page.locator("#imgTagWrapperId, #landingImage").first
        if await main.count():
            try:
                await main.scroll_into_view_if_needed(timeout=2_000)
                await main.click(timeout=3_000)
                await page.locator("#ivImagesTab, #ivThumbs").first.wait_for(state="visible", timeout=5_000)
            except Exception:
                pass

        immersive_urls: list[str] = []
        immersive_thumbs = page.locator("#ivThumbs .ivThumb:not(.placeholder), .ivThumb:not(.placeholder)")
        previous = ""
        for index in range(await immersive_thumbs.count()):
            thumb = immersive_thumbs.nth(index)
            try:
                if not await thumb.is_visible():
                    continue
                await thumb.scroll_into_view_if_needed(timeout=1_500)
                await thumb.click(timeout=3_000)
                image = page.locator("#ivLargeImage img.fullscreen, #ivLargeImage img[src]").first
                await image.wait_for(state="visible", timeout=3_000)
                current = await self._wait_stable_image(
                    image, page, previous_url=previous, require_change=bool(previous)
                )
                immersive_urls.append(current)
                previous = current
            except Exception:
                continue

        if immersive_urls:
            urls = _dedupe_urls(immersive_urls)
        else:
            # Older PDPs do not expose the immersive viewer.  Click each inline
            # thumbnail and read the hydrated main image, never the 100px thumb.
            inline_urls: list[str] = []
            inline_thumbs = page.locator("#altImages li:not(.videoThumbnail) img")
            previous = ""
            for index in range(await inline_thumbs.count()):
                thumb = inline_thumbs.nth(index)
                try:
                    if not await thumb.is_visible():
                        continue
                    await thumb.scroll_into_view_if_needed(timeout=1_500)
                    await thumb.click(timeout=2_000)
                    image = page.locator("#landingImage, #imgTagWrapperId img").first
                    await image.wait_for(state="visible", timeout=3_000)
                    current = await self._wait_stable_image(
                        image, page, previous_url=previous, require_change=bool(previous)
                    )
                    inline_urls.append(current)
                    previous = current
                except Exception:
                    continue
            urls = _dedupe_urls([*urls, *inline_urls])

        close = page.locator(".a-modal-scroller .a-button-close, .a-popover-modal .a-button-close, button[aria-label='Close']").first
        try:
            if await close.count() and await close.is_visible():
                await close.click(timeout=2_000)
        except Exception:
            pass
        return _dedupe_urls(urls)

    async def _wait_stable_image(self, image: Any, page: Any, *, previous_url: str = "",
                                 require_change: bool = False) -> str:
        last = ""
        stable = 0
        for _ in range(30):
            state = await image.evaluate("""el => ({
              url: el.getAttribute('data-old-hires') || el.currentSrc || el.src || '',
              ready: Boolean(el.complete && el.naturalWidth >= 300 && el.naturalHeight >= 300)
            })""")
            current = str(state.get("url", ""))
            valid = (state.get("ready") and current and not _is_loading_or_utility_image(current)
                     and (not require_change or _clean_image_url(current) != _clean_image_url(previous_url)))
            stable = stable + 1 if valid and current == last else (1 if valid else 0)
            last = current
            if stable >= 2:
                return current
            await page.wait_for_timeout(150)
        raise BrowserAutomationError("A gallery image URL/naturalWidth did not become stable.")

    async def _extract_aplus(self, page: Any) -> tuple[list[str], str, str]:
        product_selectors = (
            "#aplus_feature_div #aplus, "
            "#dpx-aplus-product-description_feature_div #aplus, "
            "#dpx-aplus-product-description_feature_div"
        )
        root = None
        for _ in range(20):
            candidate = page.locator(product_selectors).first
            if await candidate.count():
                root = candidate
                break
            await page.evaluate("window.scrollBy(0, Math.max(500, window.innerHeight * .8))")
            await page.wait_for_timeout(150)
        if root is None:
            # Fixture/legacy fallback, but explicitly exclude Amazon's Brand Story:
            # those carousel images advertise unrelated products and must never be
            # imported as this product's rich description.
            candidates = page.locator("#aplus, [cel_widget_id='aplus']")
            for index in range(await candidates.count()):
                candidate = candidates.nth(index)
                in_brand_story = await candidate.evaluate(
                    "el => Boolean(el.closest('#aplusBrandStory_feature_div'))"
                )
                if not in_brand_story:
                    root = candidate
                    break
        if root is None:
            return [], "", ""
        await root.scroll_into_view_if_needed()
        previous = -1
        stable = 0
        while stable < 3:
            images = root.locator("img")
            count = await images.count()
            stable = stable + 1 if count == previous else 0
            previous = count
            for index in range(count):
                try:
                    await images.nth(index).scroll_into_view_if_needed(timeout=1_000)
                except Exception:
                    pass
            await page.wait_for_timeout(300)
        urls = await root.evaluate(r"""root => {
          if (globalThis.WRYDECO_SCRAPER_SHARED) return globalThis.WRYDECO_SCRAPER_SHARED.extractAplusUrls(root);
          return [...root.querySelectorAll('img')].flatMap(el => {
          const set = el.getAttribute('srcset') || '';
          const best = set.split(',').map(x => x.trim().split(/\s+/)[0]).filter(Boolean).pop();
          return [el.dataset.src, el.getAttribute('data-a-hires'), best, el.src].filter(Boolean);
          });
        }""")
        return _dedupe_urls(urls), await root.inner_html(), " ".join((await root.inner_text()).split())

    async def _customization_frame(self, page: Any) -> Any:
        # Reuse an already-open form first.  This matters when base-price
        # discovery opened the modal earlier in the crawl.
        existing = await self._find_customization_frame(page)
        if existing:
            return existing
        for selector in self.CUSTOMIZATION_TRIGGER_SELECTORS:
            button = page.locator(selector).first
            if await button.count():
                try:
                    if not await button.is_visible():
                        continue
                    await button.scroll_into_view_if_needed(timeout=2_000)
                    await button.click(timeout=3_000)
                    break
                except Exception:
                    continue
        for _ in range(60):
            frame = await self._find_customization_frame(page)
            if frame:
                return frame
            await page.wait_for_timeout(250)
        raise BrowserAutomationError("Amazon customization form was not found.")

    async def _find_customization_frame(self, page: Any) -> Any | None:
        frame = page.frame(name="gc-iframe")
        if not frame:
            iframe = page.locator("#gc-iframe").first
            if await iframe.count():
                try:
                    frame = await iframe.content_frame()
                except Exception:
                    frame = None
        if frame:
            try:
                if await frame.locator(
                    ".gc-OptionChooserComponent, .gc-customization-page, .gc-group, [role='radiogroup']"
                ).count():
                    return frame
            except Exception:
                pass
        if await page.locator(
            ".gc-OptionChooserComponent, .gc-customization-page, .gc-group, [data-testid='customization-group']"
        ).count():
            return page
        return None

    async def _has_customization_ui(self, page: Any) -> bool:
        if await page.locator("#gc-iframe").count():
            return True
        for selector in self.CUSTOMIZATION_TRIGGER_SELECTORS:
            if await page.locator(selector).count():
                return True
        return False

    async def _extract_dynamic(self, page: Any, base_price: Decimal, *, asin: str = "") -> dict[str, Any]:
        frame = await self._customization_frame(page)
        for selector in [".gc-toggle-list-toggle-button[aria-expanded='false']",
                         ".gc-accordion-header[aria-expanded='false']", ".gc-group-header[aria-expanded='false']"]:
            locators = frame.locator(selector)
            for index in range(await locators.count()):
                try:
                    if await locators.nth(index).is_visible():
                        await locators.nth(index).click(timeout=1_500)
                except Exception:
                    pass
        groups = frame.locator(".gc-OptionChooserComponent, .gc-group, [data-testid='customization-group'], .gc-customization-section")
        option_types: list[dict[str, Any]] = []
        for group_index in range(await groups.count()):
            group = groups.nth(group_index)
            name = await self._first_text(group, [".gc-component-label", ".gc-group-label", ".gc-group-title", "legend", "h3", "h2"])
            if not name or is_ignored_type(name):
                continue
            choices = await self._customization_choices(group)
            options: list[dict[str, Any]] = []
            for dom_index in range(await choices.count()):
                choice = choices.nth(dom_index)
                if await choice.get_attribute("aria-disabled") == "true":
                    continue
                label = choice.locator(".gc-swatch-label").first
                label_text = await label.inner_text() if await label.count() else ""
                value = " ".join((label_text or (await choice.get_attribute("aria-label")) or (await choice.inner_text()) or "").split())
                value = re.sub(r",?\s*[+-]\s*(?:USD\s*)?\$?\s*\d[\d,.]*\s*$", "", value, flags=re.I).strip()
                if not value:
                    continue
                raw = ""
                price_node = choice.locator(".gc-swatch-price").first
                if await price_node.count():
                    raw = " ".join((await price_node.inner_text()).split())
                else:
                    aria = (await choice.get_attribute("aria-label")) or ""
                    match = re.search(r"([+-]\s*(?:USD\s*)?\$?\s*\d[\d,.]*(?:\s*[-–—]\s*\$?\s*\d[\d,.]*)?)\s*$", aria, re.I)
                    raw = match.group(1) if match else ""
                price, explicit = parse_additional_price(raw, option=value, type_name=name)
                options.append({"value": value, "additional_price": price, "has_explicit_price": explicit,
                                "raw_price_text": raw, "dom_index": dom_index, "group_index": group_index})
            unique: dict[tuple[str, Decimal], dict[str, Any]] = {}
            for option in options:
                unique.setdefault((normalize_name(option["value"]), option["additional_price"]), option)
            options = list(unique.values())
            if uses_default_removal(name):
                options = remove_default_option(name, options)
            if options:
                option_types.append({"name": name, "group_index": group_index, "options": options})
        combinations = build_combinations(option_types, self.settings.max_combinations)
        for combination_index, combination in enumerate(combinations, 1):
            for selected in combination["selection"]:
                group = groups.nth(selected["group_index"])
                choice = (await self._customization_choices(group)).nth(selected["dom_index"])
                if await choice.evaluate("el => el.tagName === 'OPTION'"):
                    await choice.locator("xpath=parent::select").select_option(index=selected["dom_index"])
                else:
                    await choice.click(timeout=5_000)
                await frame.wait_for_timeout(150)
            observed = await self._wait_stable_footer_price(frame)
            expected = verify_total(base_price, combination["additional_price"], observed, self.settings.price_tolerance)
            combination["verified_total"] = expected
            emit(self.event_callback, "price_progress", asin=asin, stage="price_verification",
                 current=combination_index, total=len(combinations), price=str(expected))
        return {
            "mode": "dynamic", "base_price": base_price, "option_types": option_types,
            "variants": combinations, "verified_all": True,
        }

    async def _customization_choices(self, group: Any) -> Any:
        """Return one locator per actual choice, avoiding nested swatch duplicates."""
        radios = group.locator("[role='radio']")
        if await radios.count():
            return radios
        return group.locator(".gc-swatch, input[type='radio'] + label, select option")

    async def _extract_pdp_variations(self, page: Any, base_price: Decimal) -> dict[str, Any]:
        """Verify ordinary Amazon twister variants by selecting every PDP option.

        Amazon's visible swatch price often says "from", which is not safe to parse as
        a final price.  We use the swatch only to discover values, click each ASIN,
        and accept the variant only after the main PDP price becomes stable.
        """
        rows = page.locator("[id^='inline-twister-row-']")
        visible_rows: list[Any] = []
        for index in range(await rows.count()):
            row = rows.nth(index)
            if await row.is_visible():
                visible_rows.append(row)
        if not visible_rows:
            raise BrowserAutomationError("Amazon customization and standard PDP variations were not found.")
        if len(visible_rows) > 1:
            raise BrowserAutomationError(
                "Multi-dimensional standard PDP variations are not yet safe to enumerate; no price was guessed."
            )

        row = visible_rows[0]
        name = await self._first_text(row, [".dimension-text .a-color-secondary", ".dimension-heading .a-color-secondary"])
        name = name.rstrip(":").strip()
        if not name or is_ignored_type(name):
            raise BrowserAutomationError("The standard PDP variation type is missing or ignored.")
        items = row.locator("li[data-asin]")
        options: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for index in range(await items.count()):
            item = items.nth(index)
            classes = (await item.get_attribute("class") or "").casefold()
            if "unavailable" in classes:
                continue
            asin = (await item.get_attribute("data-asin") or "").strip().upper()
            label = item.locator("img.swatch-image[alt], img[alt]").first
            value = (await label.get_attribute("alt") or "").strip() if await label.count() else ""
            if not value:
                value = " ".join((await item.inner_text()).split())
                value = re.sub(r"\s+\d+\s+options?\s+from\s+\$.*$", "", value, flags=re.I).strip()
            key = (asin, normalize_name(value))
            if not re.fullmatch(r"[A-Z0-9]{10}", asin) or not value or key in seen:
                continue
            seen.add(key)
            options.append({"asin": asin, "value": value})
        if len(options) < 2:
            raise BrowserAutomationError("Fewer than two usable standard PDP variation values were found.")
        if len(options) > self.settings.max_combinations:
            raise PriceValidationError(
                f"Combination safety cap exceeded: {len(options)} > {self.settings.max_combinations}."
            )

        variants: list[dict[str, Any]] = []
        for dom_index, option in enumerate(options):
            asin = option["asin"]
            target = page.locator(f"[id^='inline-twister-row-'] li[data-asin='{asin}']").first
            selected = await target.locator(".a-button-selected").count() > 0
            if not selected:
                control = target.locator("input[role='radio'], input[type='submit']").first
                if not await control.count():
                    raise BrowserAutomationError(f'PDP variation "{option["value"]}" has no selectable control.')
                await control.click(force=True, timeout=5_000)
            observed = await self._wait_stable_pdp_price(page, asin)
            additional = money(observed - base_price)
            verified = verify_total(base_price, additional, observed, self.settings.price_tolerance)
            variants.append({
                "options": [{"name": name, "value": option["value"]}],
                "additional_price": additional,
                "verified_total": verified,
                "amazon_asin": asin,
                "dom_index": dom_index,
            })
        return {
            "mode": "dynamic", "source": "pdp_variation", "base_price": base_price,
            "option_types": [{"name": name, "options": [
                {"value": item["value"], "amazon_asin": item["asin"]} for item in options
            ]}],
            "variants": variants, "verified_all": True,
        }

    async def _wait_stable_pdp_price(self, page: Any, expected_asin: str) -> Decimal:
        selectors = [
            "#corePrice_feature_div .a-price .a-offscreen",
            "#apex_desktop .a-price .a-offscreen",
            "#priceblock_ourprice", "#priceblock_dealprice", "#price_inside_buybox",
        ]
        last: Decimal | None = None
        stable = 0
        for _ in range(60):
            selected = page.locator(
                f"[id^='inline-twister-row-'] li[data-asin='{expected_asin}'] .a-button-selected"
            )
            asin_ready = expected_asin.casefold() in page.url.casefold() or await selected.count() > 0
            text = await self._first_text(page, selectors) if asin_ready else ""
            if text:
                try:
                    current = parse_base_price(text)
                    stable = stable + 1 if current == last else 1
                    last = current
                    if stable >= 3:
                        return current
                except PriceValidationError:
                    stable = 0
            await page.wait_for_timeout(250)
        raise PriceValidationError(f"PDP price for Amazon variant {expected_asin} did not become stable.")

    async def _wait_stable_footer_price(self, frame: Any) -> Decimal:
        selectors = ['#gc-desktop-footer-wrapper .a-price[data-a-size="xl"][data-a-color="base"] .a-offscreen',
                     '#gc-desktop-footer-wrapper .a-price[data-a-size="xl"][data-a-color="base"]',
                     ".gc-footer-price", ".gc-total-price", "[data-testid='price']"]
        last: Decimal | None = None
        stable = 0
        for _ in range(40):
            text = await self._first_text(frame, selectors)
            if text:
                try:
                    current = parse_base_price(text)
                    stable = stable + 1 if current == last else 0
                    last = current
                    if stable >= 2:
                        return current
                except PriceValidationError:
                    pass
            await frame.wait_for_timeout(250)
        raise PriceValidationError("Customization footer price did not become stable.")


def json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    return value

