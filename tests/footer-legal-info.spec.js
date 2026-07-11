// @ts-check
import { test, expect } from '@playwright/test';

// Verifies the homepage footer contact block is now driven by the first
// `store_legal_info` metaobject entry (slogan / phone_number / support_email /
// business_address) instead of hardcoded values.
const BASE_URL = process.env.THEME_PREVIEW_URL || 'http://127.0.0.1:9292/';

async function gotoHome(page) {
  await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000); // let live-reload / lazy content settle
  await page.evaluate(() => {
    document.querySelectorAll('#PBarNextFrameWrapper, [popover]').forEach((el) => el.remove());
  });
}

test.describe('Footer — store_legal_info metaobject', () => {
  test('slogan, phone, email and address all render from the metaobject', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await gotoHome(page);

    const footer = page.locator('.footer-custom');
    await footer.scrollIntoViewIfNeeded();

    // Slogan (tagline) must be present and non-empty.
    const slogan = page.locator('.footer-custom__tagline');
    await expect(slogan).toBeVisible();
    await expect(slogan).not.toBeEmpty();

    // Contact list must show all three items: phone, email, address.
    const items = page.locator('.footer-custom__contact li');
    await expect(items).toHaveCount(3);

    // Phone: rendered as a tel: link whose href has no spaces/formatting chars.
    const phoneLink = page.locator('.footer-custom__contact a[href^="tel:"]');
    await expect(phoneLink).toBeVisible();
    await expect(phoneLink).not.toBeEmpty();
    const telHref = await phoneLink.getAttribute('href');
    expect(telHref).toMatch(/^tel:[+\d]+$/); // digits/plus only, no spaces or parens

    // Email: rendered as a mailto: link.
    const emailLink = page.locator('.footer-custom__contact a[href^="mailto:"]');
    await expect(emailLink).toBeVisible();
    const mailHref = await emailLink.getAttribute('href');
    expect(mailHref).toMatch(/^mailto:\S+@\S+/);

    // Address: third item is plain text and non-empty.
    const addressText = await items.nth(2).innerText();
    expect(addressText.trim().length).toBeGreaterThan(0);
  });
});
