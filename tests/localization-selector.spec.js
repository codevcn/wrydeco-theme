// @ts-check
import { test, expect } from '@playwright/test';

// Runs against the local `shopify theme dev` proxy, which reflects local file
// changes instantly. The proxy returns 401 for the actual POST /localization,
// so the country-switch test verifies the submitted request (method + payload)
// rather than the resulting page — the wiring is what matters here.
const BASE_URL = process.env.THEME_PREVIEW_URL || 'http://127.0.0.1:9292/';

async function gotoTheme(page) {
  await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000); // let live-reload / lazy content settle
  await page.evaluate(() => {
    document.querySelectorAll('#PBarNextFrameWrapper, [popover]').forEach((el) => el.remove());
  });
}

test.describe('Country / currency picker', () => {
  test('header picker opens, lists countries with flag/currency, and submits the switch', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await gotoTheme(page);

    const trigger = page.locator('.loc-picker--header .loc-picker__trigger');
    await expect(trigger).toBeVisible();
    await expect(page.locator('.loc-picker--header .loc-picker__trigger img')).toHaveAttribute('src', /flagcdn\.com\/[a-z]{2}\.svg/);

    await trigger.click();
    await expect(page.locator('.loc-picker--header .loc-picker__panel')).toBeVisible();

    const options = page.locator('.loc-picker--header .loc-picker__option');
    expect(await options.count()).toBeGreaterThan(1);
    const first = options.first();
    await expect(first.locator('.loc-picker__flag img')).toBeVisible();
    await expect(first.locator('.loc-picker__code')).not.toBeEmpty();
    await expect(first.locator('.loc-picker__name')).not.toBeEmpty();
    await expect(page.locator('.loc-picker--header .loc-picker__option.is-selected')).toHaveCount(1);

    // Choosing a different country POSTs to /localization with that country_code.
    const currentValue = await page.locator('.loc-picker--header .loc-picker__option.is-selected').getAttribute('value');
    const target = await options.evaluateAll(
      (els, current) => els.map((e) => e.getAttribute('value')).find((v) => v !== current),
      currentValue
    );
    expect(target).toBeTruthy();

    const [request] = await Promise.all([
      page.waitForRequest((r) => r.url().includes('/localization') && r.method() === 'POST'),
      page.locator(`.loc-picker--header .loc-picker__option[value="${target}"]`).click(),
    ]);
    // Shopify's localization form posts multipart/form-data, so match the field + value.
    const body = request.postData() || '';
    expect(body).toMatch(new RegExp('name="country_code"[\\s\\S]*?' + target));
  });

  test('header search filters the country list', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await gotoTheme(page);

    await page.locator('.loc-picker--header .loc-picker__trigger').click();
    await page.fill('.loc-picker--header [data-loc-search]', 'viet');

    const visible = page.locator('.loc-picker--header .loc-picker__item:not([hidden])');
    await expect(visible).toHaveCount(1);
    await expect(visible.locator('.loc-picker__name')).toHaveText(/vietnam/i);
  });

  test('footer picker sits inside the newsletter section and opens', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await gotoTheme(page);

    // Position: the footer picker now lives inside the "Stay Inspired" newsletter block.
    const inNewsletter = await page.evaluate(
      () => !!document.querySelector('.footer-custom__localization')?.closest('.footer-custom__newsletter')
    );
    expect(inNewsletter).toBe(true);

    const trigger = page.locator('.footer-custom__localization .loc-picker__trigger');
    await trigger.scrollIntoViewIfNeeded();
    await expect(trigger).toBeVisible();

    await trigger.click({ force: true });
    await expect(page.locator('.footer-custom__localization .loc-picker__panel')).toBeVisible();
    expect(await page.locator('.footer-custom__localization .loc-picker__option').count()).toBeGreaterThan(1);
  });

  test('mobile drawer exposes the inline picker', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await gotoTheme(page);

    await page.click('[data-mobile-menu-open]');
    const trigger = page.locator('.loc-picker--drawer .loc-picker__trigger');
    await trigger.scrollIntoViewIfNeeded();
    await expect(trigger).toBeVisible();

    await trigger.click({ force: true });
    await expect(page.locator('.loc-picker--drawer .loc-picker__panel')).toBeVisible();
  });
});
