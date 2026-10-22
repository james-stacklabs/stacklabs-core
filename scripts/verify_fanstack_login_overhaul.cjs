/**
 * Automated Playwright Verification: FanStack Creator Login Interface & Brand Crest Overhaul
 * Ticket: WO-2026-0910-FANSTACK-LOGIN-VISUAL-OVERHAUL
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const UAT_DIR = '/home/james/sovereign_inbox/tickets/WO-2026-0910-FANSTACK-LOGIN-VISUAL-OVERHAUL/uat';
const BRAIN_DIR = '/home/james/.gemini/antigravity-ide/brain/41a78641-70ef-4ecb-bb93-1dcec22bf6f9';
const LOOKBOOK_DIR = '/home/james/sovereign_inbox/reports/portal_3009_lookbook_assets';

[UAT_DIR, BRAIN_DIR, LOOKBOOK_DIR].forEach(dir => {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
});

async function runVerification() {
  console.log('🚀 [UAT] Launching Headless Chromium for Login Overhaul Verification...');
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--ignore-certificate-errors']
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    ignoreHTTPSErrors: true,
  });

  const page = await context.newPage();

  // Listen for console messages and errors
  page.on('console', msg => {
    if (msg.type() === 'error') console.log(`   [Browser Console Error]: ${msg.text()}`);
  });

  console.log('🌐 [UAT] Navigating to https://localhost:3009/?login=true ...');
  await page.goto('https://localhost:3009/?login=true', {
    waitUntil: 'domcontentloaded',
    timeout: 15000
  });

  // Wait for login elements
  await page.waitForSelector('[data-testid="login-card-container"]', { timeout: 8000 });
  await page.waitForSelector('[data-testid="fanstack-crest"]', { timeout: 5000 });
  await page.waitForSelector('[data-testid="live-telemetry-pill"]', { timeout: 5000 });
  await page.waitForTimeout(1000); // Allow ambient glows to settle

  console.log('📸 [UAT] Capturing Desktop Full-Page Screenshot...');
  const desktopScreenshot = path.join(UAT_DIR, 'login_overhaul_live_desktop.png');
  await page.screenshot({ path: desktopScreenshot, fullPage: true });
  fs.copyFileSync(desktopScreenshot, path.join(BRAIN_DIR, 'login_overhaul_live_desktop.png'));
  fs.copyFileSync(desktopScreenshot, path.join(LOOKBOOK_DIR, 'login_overhaul_mockup.png'));

  // 1. Assert Brand Crest & Title
  const crestVisible = await page.isVisible('[data-testid="fanstack-crest"]');
  console.log(`   ✓ FanStackCrest SVG rendered: ${crestVisible}`);
  if (!crestVisible) throw new Error('FanStackCrest SVG not visible!');

  const brandTitle = await page.textContent('h1');
  console.log(`   ✓ Brand Title: "${brandTitle.trim()}"`);
  if (!brandTitle.includes('FANSTACK')) throw new Error('Brand title FANSTACK missing!');

  // 2. Assert Telemetry Ingress Pill
  const pillText = await page.textContent('[data-testid="live-telemetry-pill"]');
  console.log(`   ✓ Telemetry Pill Text: "${pillText.replace(/\s+/g, ' ').trim()}"`);
  if (!pillText.includes('LIVE TELEMETRY: MLB ACTIVE') || !pillText.includes('SUBWAY SERIES')) {
    throw new Error('Telemetry pill text mismatch!');
  }

  // 3. Test Password Reveal Toggle
  console.log('🔑 [UAT] Testing Password Reveal Toggle...');
  const passwordInput = page.locator('#auth-password');
  const toggleBtn = page.locator('[data-testid="password-toggle-btn"]');

  await passwordInput.fill('TestSecretKey2026!');
  let inputType = await passwordInput.getAttribute('type');
  console.log(`   Initial password input type: ${inputType}`);
  if (inputType !== 'password') throw new Error('Expected initial type to be password');

  await toggleBtn.click();
  await page.waitForTimeout(300);
  inputType = await passwordInput.getAttribute('type');
  console.log(`   After toggle click, password input type: ${inputType}`);
  if (inputType !== 'text') throw new Error('Expected toggled type to be text');

  await toggleBtn.click();
  await page.waitForTimeout(300);
  inputType = await passwordInput.getAttribute('type');
  console.log(`   After second click, password input type: ${inputType}`);
  if (inputType !== 'password') throw new Error('Expected reset type to be password');

  // 4. Test Mobile Responsive Viewport (Pixel 10a / 392x844)
  console.log('📱 [UAT] Testing Mobile Viewport (392x844)...');
  await page.setViewportSize({ width: 392, height: 844 });
  await page.waitForTimeout(500);
  const mobileScreenshot = path.join(UAT_DIR, 'login_overhaul_live_mobile.png');
  await page.screenshot({ path: mobileScreenshot, fullPage: true });
  fs.copyFileSync(mobileScreenshot, path.join(BRAIN_DIR, 'login_overhaul_live_mobile.png'));
  console.log('   ✓ Mobile screenshot saved');

  // Reset viewport back to desktop for authentication test
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.waitForTimeout(500);

  // 5. Test Authentication Flow (wardynym / LGM2026!)
  console.log('⚡ [UAT] Submitting Authentication with Tyler Ward Credentials (wardynym)...');
  const usernameInput = page.locator('#auth-username');
  await usernameInput.fill('wardynym');
  await passwordInput.fill('LGM2026!');

  const submitBtn = page.locator('#auth-submit');
  await submitBtn.click();

  console.log('⏳ [UAT] Waiting for login response and Creator Studio transition...');
  // Wait for login card to disappear or main portal element to appear
  try {
    await page.waitForFunction(() => {
      return !document.querySelector('[data-testid="login-card-container"]') || document.querySelector('[data-testid="navigation-rail"]') || document.body.innerText.includes('Creator Studio') || document.body.innerText.includes('LOGOUT') || document.body.innerText.includes('WARM');
    }, { timeout: 10000 });
    console.log('   ✓ Successfully authenticated! Login card dissolved into authenticated workspace.');
  } catch (err) {
    // Take screenshot of failure
    await page.screenshot({ path: path.join(UAT_DIR, 'auth_failure_debug.png') });
    throw new Error(`Authentication transition timed out: ${err.message}`);
  }

  await page.waitForTimeout(2000);
  const authStudioScreenshot = path.join(UAT_DIR, 'creator_studio_authenticated.png');
  await page.screenshot({ path: authStudioScreenshot, fullPage: true });
  fs.copyFileSync(authStudioScreenshot, path.join(BRAIN_DIR, 'creator_studio_authenticated.png'));
  console.log('📸 [UAT] Captured Authenticated Creator Studio Screenshot.');

  await browser.close();
  console.log('🎉 [UAT] ALL PLAYWRIGHT ASSERTIONS PASSED SUCCESSFULLY!');
}

runVerification().catch(err => {
  console.error('❌ [UAT] Verification failed:', err);
  process.exit(1);
});
