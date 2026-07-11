// @ts-check
import { test, expect } from '@playwright/test';

// Verifies the "Meet the Makers" homepage section now renders one card per
// `product_author` metaobject entry (author_name / author_bio /
// author_image_url) instead of theme blocks.
const BASE_URL = process.env.THEME_PREVIEW_URL || 'http://127.0.0.1:9292/';

async function gotoHome(page) {
  await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000); // let live-reload / lazy content settle
  await page.evaluate(() => {
    document.querySelectorAll('#PBarNextFrameWrapper, [popover]').forEach((el) => el.remove());
  });
}

test.describe('Meet the Makers — metaobject-driven cards', () => {
  test('renders one card per Product Author entry with name, image and profile link', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await gotoHome(page);

    const section = page.locator('.meet-makers');
    await section.scrollIntoViewIfNeeded();
    await expect(section).toBeVisible();

    const cards = page.locator('.meet-makers__slider .maker-card');
    const count = await cards.count();
    // Metaobject has 6 published entries (see admin screenshot).
    expect(count).toBe(6);

    // Every card maps to a metaobject entry: it must have a non-empty name,
    // an image sourced from Shopify Files, and a profile link to the
    // metaobject's own storefront URL.
    for (let i = 0; i < count; i++) {
      const card = cards.nth(i);
      await expect(card.locator('.maker-card__name')).not.toBeEmpty();
      await expect(card.locator('.maker-card__img')).toHaveAttribute('src', /cdn\.shopify\.com/);
      await expect(card.locator('.maker-card__img-link')).toHaveAttribute('href', /product_author|product-author/i);
    }

    // Spot-check that real author names from the metaobject are present.
    const names = await page.locator('.meet-makers__slider .maker-card__name').allInnerTexts();
    expect(names.join(' | ')).toMatch(/Tin Dang|Son Tran|Lam Nguyen/);

    // Bios must be server-rendered (SSR), not empty placeholders.
    const firstBio = page.locator('.meet-makers__slider .maker-card__bio').first();
    await expect(firstBio).not.toBeEmpty();
  });
});
