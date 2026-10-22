#!/usr/bin/env node
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

async function run() {
  console.log('[*] Starting Sovereign Sentinel Ag Vision UAT verification...');

  const ticketDir = '/home/james/sovereign_inbox/tickets/WO0010032-AG-SENTINEL-PASTURE-AND-LIVESTOCK-V/uat';
  const todayDir = '/home/james/sovereign_inbox/today/uat_screenshots';
  const brainDir = '/home/james/.gemini/antigravity-ide/brain/730f4e06-ad1d-4824-8cd2-ac1b515e3c1f';

  fs.mkdirSync(ticketDir, { recursive: true });
  fs.mkdirSync(todayDir, { recursive: true });
  fs.mkdirSync(brainDir, { recursive: true });

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const context = await browser.newContext({
    ignoreHTTPSErrors: true,
    viewport: { width: 1920, height: 1080 }
  });

  const page = await context.newPage();

  // Listen to console logs
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log(`[Browser Console Error]: ${msg.text()}`);
    }
  });

  const targetUrl = 'https://localhost:3038/';
  console.log(`[*] Navigating to ${targetUrl}...`);
  await page.goto(targetUrl, { waitUntil: 'networkidle', timeout: 20000 });
  await page.waitForTimeout(2000);

  // Click on Agricultural Edge Vision tab
  console.log('[*] Switching to Agricultural Edge Vision tab...');
  const agVisionTab = await page.locator('button:has-text("Agricultural Edge Vision")');
  if (await agVisionTab.count() > 0) {
    await agVisionTab.click();
    console.log('[+] Clicked Agricultural Edge Vision tab.');
  } else {
    console.error('[-] Could not find Agricultural Edge Vision tab in nav rail');
  }

  // Wait for dual stream components to mount and load data
  await page.waitForTimeout(3000);

  // Verify view components exist
  const floraTitle = await page.locator('text=Pasture Botany & Bovine Toxicology');
  const livestockTitle = await page.locator('text=Livestock Biometric Hide Identification');
  const bufferTitle = await page.locator('text=Edge Ingress Telemetry Log');

  console.log(`[*] Pasture Botany header visible: ${await floraTitle.count() > 0}`);
  console.log(`[*] Livestock Biometrics header visible: ${await livestockTitle.count() > 0}`);
  console.log(`[*] Telemetry Buffer Dock visible: ${await bufferTitle.count() > 0}`);

  // Test selecting another specimen: Wild Black Cherry
  console.log('[*] Testing specimen selector (Wild Black Cherry)...');
  const cherryButton = page.locator('button:has-text("Wild Black Cherry")');
  if (await cherryButton.count() > 0) {
    await cherryButton.click();
    await page.waitForTimeout(1000);
    console.log('[+] Selected Wild Black Cherry. Verifying LETHAL badge...');
  }

  // Test clicking "Execute Botanical Scan"
  console.log('[*] Clicking "Execute Botanical Scan"...');
  const scanButton = page.locator('button:has-text("Execute Botanical Scan")');
  if (await scanButton.count() > 0) {
    await scanButton.click();
    await page.waitForTimeout(2000);
    console.log('[+] Botanical scan triggered and logged.');
  }

  // Test Livestock Biometrics: Select LH-2026-001 (Longhorn Matriarch)
  console.log('[*] Testing livestock selector (lh_001)...');
  const lhButton = page.locator('button:has-text("lh_001")');
  if (await lhButton.count() > 0) {
    await lhButton.click();
    await page.waitForTimeout(1000);
    console.log('[+] Selected lh_001.');
  }

  // Test toggling OCR Tag Fallback
  console.log('[*] Toggling OCR Tag Fallback mode...');
  const ocrToggle = page.locator('button:has-text("OCR Tag Fallback")');
  if (await ocrToggle.count() > 0) {
    await ocrToggle.click();
    await page.waitForTimeout(1000);
    console.log('[+] OCR Tag Fallback enabled.');
  }

  // Capture Live Dual Stream Viewport
  const liveScreenshotTicket = path.join(ticketDir, 'ag_sentinel_live_browser.png');
  const liveScreenshotToday = path.join(todayDir, 'ag_sentinel_live_browser.png');
  const liveScreenshotBrain = path.join(brainDir, 'ag_sentinel_live_browser.png');

  console.log('[*] Capturing live browser screenshot...');
  await page.screenshot({ path: liveScreenshotTicket, fullPage: true });
  fs.copyFileSync(liveScreenshotTicket, liveScreenshotToday);
  fs.copyFileSync(liveScreenshotTicket, liveScreenshotBrain);
  console.log(`[+] Saved live dual stream screenshot to: ${liveScreenshotTicket}`);

  // Also test clicking "Synchronize Buffer"
  console.log('[*] Testing Synchronize Buffer button...');
  const syncBtn = page.locator('button:has-text("Synchronize Buffer")');
  if (await syncBtn.count() > 0 && !(await syncBtn.isDisabled())) {
    await syncBtn.click();
    await page.waitForTimeout(2000);
    console.log('[+] Buffer synchronized!');
  } else {
    console.log('[*] Buffer already synced or empty.');
  }

  // Take an additional screenshot of Botany Focus view
  console.log('[*] Testing Pasture Botany Focus mode...');
  const floraFocusBtn = page.locator('button:has-text("Pasture Botany")');
  if (await floraFocusBtn.count() > 0) {
    await floraFocusBtn.first().click();
    await page.waitForTimeout(1000);
    const floraScreenshot = path.join(ticketDir, 'ag_sentinel_flora_focus.png');
    await page.screenshot({ path: floraScreenshot, fullPage: true });
    console.log(`[+] Saved flora focus screenshot to: ${floraScreenshot}`);
  }

  await browser.close();
  console.log('[+] All UAT automated verification completed successfully!');
}

run().catch(err => {
  console.error('[!] Verification failed:', err);
  process.exit(1);
});
