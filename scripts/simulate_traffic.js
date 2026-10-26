const { chromium } = require('@playwright/test');

const STORE_URL = 'https://wrydeco.myshopify.com';
const STORE_PASSWORD = '123456';

async function bypassStorePassword(page) {
  try {
    await page.goto(`${STORE_URL}/password`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const passwordInput = await page.$('input[type="password"]');
    if (passwordInput) {
      console.log('  [Auth] Entering store password...');
      await passwordInput.fill(STORE_PASSWORD);
      await Promise.all([
        page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 20000 }).catch(() => {}),
        passwordInput.press('Enter'),
      ]);
      console.log('  [Auth] Store password accepted.');
    }
  } catch (err) {
    console.log('  [Auth] Note:', err.message);
  }
}

async function simulateInteractions(page, label) {
  console.log(`  [Action] Simulating user behavior on ${label}...`);
  
  // Wait for clarity to load
  await page.waitForTimeout(2000);
  
  // Natural scrolling behavior
  const scrollDepths = [300, 750, 1400, 2200, 1100, 400, 0];
  for (const depth of scrollDepths) {
    await page.evaluate((y) => window.scrollTo({ top: y, behavior: 'smooth' }), depth);
    await page.waitForTimeout(1000 + Math.random() * 500);
    
    // Simulate mouse movements across screen
    await page.mouse.move(200 + Math.random() * 400, 200 + Math.random() * 300);
  }

  // Click on a few interactive elements (like buttons, links, or cards)
  const clickableSelectors = [
    'a.wooden-btn',
    'button',
    '.plp-product-card',
    '.accordion__summary',
    '.hero-new__action',
    'nav a'
  ];
  
  for (const sel of clickableSelectors) {
    const el = await page.$(sel);
    if (el && await el.isVisible()) {
      try {
        const box = await el.boundingBox();
        if (box) {
          await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
          await page.waitForTimeout(300);
          // dispatch click or hover
          console.log(`  [Action] Clicked element matching: ${sel}`);
          await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
          await page.waitForTimeout(1500);
          break;
        }
      } catch (e) {
        // ignore and continue
      }
    }
  }

  // Wait to allow Clarity collect beacon to send
  await page.waitForTimeout(3000);
  
  const clarityStatus = await page.evaluate(() => {
    return {
      hasClarity: typeof window.clarity === 'function',
      cookies: document.cookie.includes('_clck'),
      url: window.location.href
    };
  });
  console.log(`  [Clarity] Status: hasClarity=${clarityStatus.hasClarity}, cookieActive=${clarityStatus.cookies}`);
}

async function runSession(browser, sessionIndex, userAgent, viewport) {
  console.log(`\n========================================`);
  console.log(`Starting Simulated Session #${sessionIndex} (${viewport.width}x${viewport.height})`);
  console.log(`========================================`);
  
  const context = await browser.newContext({
    userAgent,
    viewport,
  });
  
  const page = await context.newPage();
  
  // 1. Password check
  await bypassStorePassword(page);
  
  // Pages to visit in this session
  const routes = [
    '/',
    '/collections/tree-bookshelves',
    '/collections/all',
    '/pages/about-us',
    '/pages/care-guide',
    '/pages/customization'
  ];

  // Pick 2-3 pages per session
  const shuffled = routes.sort(() => 0.5 - Math.random()).slice(0, 3);
  
  for (const route of shuffled) {
    const targetUrl = `${STORE_URL}${route}`;
    console.log(`\nNavigating to: ${targetUrl}`);
    try {
      await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 25000 });
      await simulateInteractions(page, route);
    } catch (e) {
      console.log(`  Error on ${route}:`, e.message);
    }
  }

  // Ensure final Clarity beacon flushes before closing
  await page.waitForTimeout(4000);
  await context.close();
}

async function main() {
  console.log('Launching browser to simulate multi-user traffic on https://wrydeco.myshopify.com ...');
  const browser = await chromium.launch({ headless: true });

  const devices = [
    {
      name: 'Desktop Chrome',
      viewport: { width: 1440, height: 900 },
      ua: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
    },
    {
      name: 'Macbook Safari',
      viewport: { width: 1280, height: 800 },
      ua: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15'
    },
    {
      name: 'Mobile iPhone 14',
      viewport: { width: 390, height: 844 },
      ua: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'
    },
    {
      name: 'Tablet iPad Pro',
      viewport: { width: 820, height: 1180 },
      ua: 'Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'
    }
  ];

  for (let i = 0; i < devices.length; i++) {
    const dev = devices[i];
    await runSession(browser, i + 1, dev.ua, dev.viewport);
  }

  await browser.close();
  console.log('\nTraffic simulation complete! Data dispatched to Microsoft Clarity.');
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
