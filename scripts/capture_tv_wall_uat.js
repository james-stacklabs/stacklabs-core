const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const outputDir = '/home/james/sovereign_inbox/today/uat_screenshots';
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--ignore-certificate-errors']
  });

  const page = await browser.newPage({
    viewport: { width: 1920, height: 1080 }
  });

  try {
    console.log('Navigating to Sovereign Sports Watch Party (Port 3010)...');
    await page.goto('https://clio.taila01894.ts.net:3010/fan-portal', {
      waitUntil: 'networkidle',
      timeout: 15000
    });

    await page.waitForTimeout(3000);

    const liveScreenshotPath = path.join(outputDir, 'sports_bar_tv_wall_live_twin.png');
    await page.screenshot({ path: liveScreenshotPath, fullPage: true });
    console.log(`Live Twin UAT Screenshot saved to ${liveScreenshotPath}`);

    // Also save copy to brain session artifacts directory
    const brainPath = '/home/james/.gemini/antigravity/brain/93f12832-0fd5-4c81-a609-e0c21780f24b/sports_bar_tv_wall_live_twin.png';
    fs.copyFileSync(liveScreenshotPath, brainPath);
    console.log(`Brain copy saved to ${brainPath}`);

  } catch (err) {
    console.error('Playwright capture warning:', err.message);
    const fallbackPath = path.join(outputDir, 'sports_bar_tv_wall_live_twin.png');
    await page.screenshot({ path: fallbackPath, fullPage: true }).catch(() => {});
  } finally {
    await browser.close();
  }
})();
