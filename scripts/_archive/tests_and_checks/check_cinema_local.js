import { chromium } from 'playwright';
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ ignoreHTTPSErrors: true });
  page.on('pageerror', err => console.log('Unhandled Exception:', err));
  page.on('console', msg => console.log('Console:', msg.text()));
  await page.goto('https://127.0.0.1:3008/');
  await page.waitForTimeout(2000);
  const content = await page.content();
  console.log("HTML:", content.substring(0, 500));
  await browser.close();
})();
