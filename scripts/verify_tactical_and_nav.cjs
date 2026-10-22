const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--ignore-certificate-errors']
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    ignoreHTTPSErrors: true
  });

  const page = await context.newPage();
  console.log('Navigating to Command Center on Port 3009...');
  await page.goto('https://localhost:3009/?domain=MLB&room=starter', { waitUntil: 'networkidle' });

  await page.waitForTimeout(1500);

  // Take screenshot of the Command Center
  const screenshotPath = '/home/james/.gemini/antigravity-ide/brain/41a78641-70ef-4ecb-bb93-1dcec22bf6f9/command_center_collapsed_and_renamed.png';
  await page.screenshot({ path: screenshotPath });
  console.log(`Screenshot saved to ${screenshotPath}`);

  // Check text of watch party
  const navText = await page.content();
  const hasFanStackWatchParty = navText.includes('FanStack Watch Party');
  const hasSovereignWatchParty = navText.includes('Sovereign Watch Party');

  console.log(`Has 'FanStack Watch Party': ${hasFanStackWatchParty}`);
  console.log(`Has 'Sovereign Watch Party': ${hasSovereignWatchParty}`);

  await browser.close();
})();
