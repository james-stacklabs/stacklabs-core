const { chromium } = require('/home/james/SovereignOS/16_StackLabsLLC/node_modules/playwright');
const path = require('path');
const fs = require('fs');

const OUT_DIR = '/home/james/sovereign_inbox/today/uat_screenshots';
if (!fs.existsSync(OUT_DIR)) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

const TICKET_DIR = '/home/james/sovereign_inbox/tickets/WO0010190/mockups';
if (!fs.existsSync(TICKET_DIR)) {
  fs.mkdirSync(TICKET_DIR, { recursive: true });
}

(async () => {
  console.log('===============================================================');
  console.log('🦅 STACKLABS GATEWAY BRIEFING: PLAYWRIGHT UAT & TWIN VERIFICATION');
  console.log('===============================================================');

  const browser = await chromium.launch({
    headless: true,
    args: ['--ignore-certificate-errors', '--no-sandbox', '--disable-setuid-sandbox']
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    ignoreHTTPSErrors: true
  });
  const page = await context.newPage();

  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });
  page.on('pageerror', err => {
    consoleErrors.push(err.message);
  });

  const url = 'https://127.0.0.1:3000/gateway_preview.html';
  console.log(`[+] Navigating to ${url}...`);
  await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(1000);

  // 1. Verify Briefing Section Presence
  const briefingSec = await page.$('#briefing');
  if (!briefingSec) {
    throw new Error('FAILED: #briefing section not found in DOM!');
  }
  console.log('[✓] Found #briefing section in DOM.');

  // 2. Verify Video Element and Attributes
  const videoEl = await page.$('#briefing video');
  if (!videoEl) {
    throw new Error('FAILED: video element not found inside #briefing!');
  }
  const poster = await videoEl.getAttribute('poster');
  console.log(`[✓] Video poster attribute: ${poster}`);

  const sources = await page.$$eval('#briefing video source', els => els.map(e => ({ src: e.getAttribute('src'), type: e.getAttribute('type') })));
  console.log(`[✓] Video sources: ${JSON.stringify(sources)}`);

  // 3. Check for Horizontal Scrollbar / Overflow Regression
  const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
  console.log(`[+] Document scrollWidth: ${scrollWidth}, clientWidth: ${clientWidth}`);
  if (scrollWidth > clientWidth) {
    console.warn(`[!] Warning: Horizontal overflow detected: scrollWidth ${scrollWidth} > clientWidth ${clientWidth}`);
  } else {
    console.log('[✓] Zero horizontal overflow / scrollbar regressions detected.');
  }

  // 4. Scroll to Briefing Section
  await briefingSec.scrollIntoViewIfNeeded();
  await page.waitForTimeout(500);

  // 5. Capture Focused Briefing Section Screenshot (Desktop 1920x1080)
  const briefingBox = await briefingSec.boundingBox();
  const focusedCapture = path.join(TICKET_DIR, 'pegasus_visual_twin_briefing_section_desktop.png');
  await briefingSec.screenshot({ path: focusedCapture });
  fs.copyFileSync(focusedCapture, path.join(OUT_DIR, 'stacklabs_briefing_section_desktop.png'));
  console.log(`[✓] Captured Briefing Section Twin: ${focusedCapture} (${fs.statSync(focusedCapture).size} bytes)`);

  // 6. Capture Full Page Desktop Screenshot
  const fullDesktop = path.join(TICKET_DIR, 'pegasus_visual_twin_gateway_preview_desktop.png');
  await page.screenshot({ path: fullDesktop, fullPage: false });
  fs.copyFileSync(fullDesktop, path.join(OUT_DIR, 'stacklabs_gateway_preview_desktop.png'));
  console.log(`[✓] Captured Viewport Desktop Twin: ${fullDesktop} (${fs.statSync(fullDesktop).size} bytes)`);

  // 7. Test Mobile Viewport (375x667)
  console.log('[+] Testing Mobile Viewport (375x667)...');
  await page.setViewportSize({ width: 375, height: 667 });
  await page.waitForTimeout(500);
  await briefingSec.scrollIntoViewIfNeeded();
  await page.waitForTimeout(500);

  const mobileScrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  const mobileClientWidth = await page.evaluate(() => document.documentElement.clientWidth);
  console.log(`[+] Mobile scrollWidth: ${mobileScrollWidth}, clientWidth: ${mobileClientWidth}`);

  const mobileCapture = path.join(TICKET_DIR, 'pegasus_visual_twin_briefing_section_mobile.png');
  await briefingSec.screenshot({ path: mobileCapture });
  fs.copyFileSync(mobileCapture, path.join(OUT_DIR, 'stacklabs_briefing_section_mobile.png'));
  console.log(`[✓] Captured Mobile Briefing Twin: ${mobileCapture} (${fs.statSync(mobileCapture).size} bytes)`);

  await browser.close();

  // Summary
  console.log('\n===============================================================');
  console.log('📊 PLAYWRIGHT VERIFICATION SUMMARY');
  console.log('===============================================================');
  console.log(`Console Errors: ${consoleErrors.length}`);
  if (consoleErrors.length > 0) {
    console.log('Errors:', consoleErrors);
  }
  console.log('Visual Twins Generated:');
  console.log(`  - ${focusedCapture}`);
  console.log(`  - ${fullDesktop}`);
  console.log(`  - ${mobileCapture}`);
  console.log('===============================================================\n');

  if (consoleErrors.length > 0) {
    process.exit(1);
  }
})();
