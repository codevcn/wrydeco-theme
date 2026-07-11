// @ts-check
import { test, expect } from '@playwright/test';

// Verifies the "Meet the People Behind WRYDECO" team section on /pages/about-us
// now renders its 3 cards from the first 3 `product_author` metaobject entries
// (author_name / author_bio / author_image_url) instead of broken theme assets.
const BASE_URL = process.env.THEME_PREVIEW_URL || 'http://127.0.0.1:9292';

test.describe('About page team — metaobject-driven cards', () => {
  test('renders 3 cards with metaobject names, Shopify CDN images and bios', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`${BASE_URL}/pages/about-us`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    await page.evaluate(() => {
      document.querySelectorAll('#PBarNextFrameWrapper, [popover]').forEach((el) => el.remove());
    });

    const section = page.locator('.about-new-team');
    await section.scrollIntoViewIfNeeded();
    await expect(section).toBeVisible();

    const cards = page.locator('.about-new-team__grid .about-new-member');
    await expect(cards).toHaveCount(3);

    // Each card: non-empty name, non-empty bio, and an image sourced from
    // Shopify Files (metaobject author_image_url) — not a broken theme asset.
    for (let i = 0; i < 3; i++) {
      const card = cards.nth(i);
      await expect(card.locator('h3')).not.toBeEmpty();
      await expect(card.locator('.about-new-member__bio')).not.toBeEmpty();
      const img = card.locator('.about-new-member__media img');
      await expect(img).toHaveAttribute('src', /cdn\.shopify\.com/);
      // Image must actually load (natural width > 0), i.e. not a broken image.
      await expect
        .poll(async () => img.evaluate((/** @type {HTMLImageElement} */ el) => el.naturalWidth))
        .toBeGreaterThan(0);
    }

    // Spot-check the real author names from the first 3 metaobject entries.
    const names = await page.locator('.about-new-team__grid .about-new-member h3').allInnerTexts();
    expect(names.join(' | ')).toMatch(/Lam Nguyen/);
    expect(names.join(' | ')).toMatch(/Khoi Hoang/);
    expect(names.join(' | ')).toMatch(/Tin Dang/);
  });
});
