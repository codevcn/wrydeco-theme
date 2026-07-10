const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  console.log('Navigating to http://127.0.0.1:9292/pages/customization...');
  await page.goto('http://127.0.0.1:9292/pages/customization');
  
  // Wait for the form section to be visible
  await page.waitForSelector('.custom-inquiry');
  
  console.log('Taking a screenshot of the form...');
  const formElement = await page.$('.custom-inquiry');
  const screenshotPath = path.join(__dirname, 'form-screenshot.png');
  
  if (formElement) {
    await formElement.screenshot({ path: screenshotPath });
    console.log(`Screenshot saved to ${screenshotPath}`);
  } else {
    console.log('Could not find the form element.');
  }

  await browser.close();
})();
