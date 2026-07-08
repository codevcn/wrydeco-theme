// @ts-check
import { test, expect } from '@playwright/test';
import { pathToFileURL } from 'node:url';
import path from 'node:path';

const fixtureUrl = pathToFileURL(
  path.resolve(process.cwd(), 'tests/fixtures/announcement-bar.html')
).href;

test.describe('Top Bar Announcement (marquee)', () => {
  test('server-rendered content is present for SEO/SSR', async ({ page }) => {
    await page.goto(fixtureUrl);
    const bar = page.locator('wd-announcement-bar.wd-topbar');
    await expect(bar).toBeVisible();
    await expect(bar).toContainText('Free US Shipping');
    await expect(bar).toContainText('Handcrafted to Order');
    await expect(bar).toContainText('White-Glove Delivery');
  });

  test('uses the espresso design token background and cream text', async ({ page }) => {
    await page.goto(fixtureUrl);
    const bar = page.locator('.wd-topbar');
    // --color-earth-brown #4a2c18 => rgb(74, 44, 24)
    await expect(bar).toHaveCSS('background-color', 'rgb(74, 44, 24)');
    // --color-milk #f7f2ec => rgb(247, 242, 236)
    await expect(bar).toHaveCSS('color', 'rgb(247, 242, 236)');
  });

  test('marquee is initialised: duplicated track, distance set, and animates', async ({ page }) => {
    await page.goto(fixtureUrl);
    const bar = page.locator('.wd-topbar');
    await expect(bar).toHaveAttribute('data-ready', '');

    // Track should contain more than the single original group (filled + duplicated).
    const groupCount = await page.locator('.wd-topbar__group').count();
    expect(groupCount).toBeGreaterThan(1);

    // Marquee distance variable is set to a positive pixel value.
    const distance = await bar.evaluate((el) =>
      parseFloat(getComputedStyle(el).getPropertyValue('--wd-marquee-distance'))
    );
    expect(distance).toBeGreaterThan(0);

    // The track actually moves: transform changes over time.
    const track = page.locator('.wd-topbar__track');
    const t0 = await track.evaluate((el) => getComputedStyle(el).transform);
    await page.waitForTimeout(700);
    const t1 = await track.evaluate((el) => getComputedStyle(el).transform);
    expect(t0).not.toBe(t1);
  });

  test('track is wider than the viewport so it can scroll infinitely', async ({ page }) => {
    await page.goto(fixtureUrl);
    const metrics = await page.locator('.wd-topbar__track').evaluate((el) => ({
      trackWidth: el.scrollWidth,
      viewportWidth: el.parentElement.offsetWidth,
    }));
    expect(metrics.trackWidth).toBeGreaterThan(metrics.viewportWidth);
  });

  test('is responsive on mobile (375px) with no horizontal page overflow', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 700 });
    await page.goto(fixtureUrl);

    const bar = page.locator('.wd-topbar');
    await expect(bar).toBeVisible();
    await expect(bar).toHaveAttribute('data-ready', '');

    // The bar spans the full viewport width.
    const barWidth = await bar.evaluate((el) => el.getBoundingClientRect().width);
    expect(Math.round(barWidth)).toBe(375);

    // No horizontal scrollbar on the document — content is clipped inside the viewport.
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth
    );
    expect(overflow).toBe(true);

    // Bar stays slim.
    const barHeight = await bar.evaluate((el) => el.getBoundingClientRect().height);
    expect(barHeight).toBeLessThan(60);
  });
});
