// @ts-check
import { test, expect } from '@playwright/test';
import { pathToFileURL } from 'node:url';
import path from 'node:path';

const fixtureUrl = pathToFileURL(
  path.resolve(process.cwd(), 'tests/fixtures/announcement-bar.html')
).href;

test.describe('Top Bar Announcement (static)', () => {
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

  test('message is static: a single group, no marquee animation or movement', async ({ page }) => {
    await page.goto(fixtureUrl);
    const bar = page.locator('.wd-topbar');

    // No marquee: the bar is never marked ready and the message is not duplicated.
    await expect(bar).not.toHaveAttribute('data-ready', '');
    await expect(page.locator('.wd-topbar__group')).toHaveCount(1);

    // The track has no running animation.
    const animationName = await page
      .locator('.wd-topbar__track')
      .evaluate((el) => getComputedStyle(el).animationName);
    expect(animationName).toBe('none');

    // The track does not move over time (transform stays constant).
    const track = page.locator('.wd-topbar__track');
    const t0 = await track.evaluate((el) => getComputedStyle(el).transform);
    await page.waitForTimeout(700);
    const t1 = await track.evaluate((el) => getComputedStyle(el).transform);
    expect(t0).toBe(t1);
  });

  test('the message sits centered within the bar', async ({ page }) => {
    await page.goto(fixtureUrl);
    const centering = await page.locator('.wd-topbar__track').evaluate((el) => {
      const track = el.getBoundingClientRect();
      const group = el.querySelector('.wd-topbar__group').getBoundingClientRect();
      const leftGap = group.left - track.left;
      const rightGap = track.right - group.right;
      return { leftGap, rightGap };
    });
    // Left and right gaps around the message should be roughly equal (centered).
    expect(Math.abs(centering.leftGap - centering.rightGap)).toBeLessThan(2);
  });

  test('is responsive on mobile (375px) with no horizontal page overflow', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 700 });
    await page.goto(fixtureUrl);

    const bar = page.locator('.wd-topbar');
    await expect(bar).toBeVisible();

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
