const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const OUT_DIR_DROPS = '/home/james/sovereign_inbox/pilot_drops/screenshots';
const OUT_DIR_ARTIFACT = '/home/james/.gemini/antigravity-cli/brain/3a489e4d-e10d-420e-a5aa-c0923d36a9d2';

async function capture() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });
  const page = await context.newPage();

  console.log('Navigating to http://127.0.0.1:8088/sync...');
  await page.goto('http://127.0.0.1:8088/sync', { waitUntil: 'networkidle' });

  // 1. Sovereign Void (Default)
  console.log('Capturing Sovereign Void...');
  const voidPath1 = path.join(OUT_DIR_DROPS, 'Screenshot_Sync_Cockpit_Sovereign_Void.png');
  const voidPath2 = path.join(OUT_DIR_ARTIFACT, 'Screenshot_Sync_Cockpit_Sovereign_Void.png');
  await page.screenshot({ path: voidPath1, fullPage: true });
  fs.copyFileSync(voidPath1, voidPath2);

  // 2. Stark S / Iron Man HUD
  console.log('Switching to Stark S theme...');
  await page.click('.theme-btn[data-theme="stark"]');
  await page.waitForTimeout(500);
  const starkPath1 = path.join(OUT_DIR_DROPS, 'Screenshot_Sync_Cockpit_Stark_S.png');
  const starkPath2 = path.join(OUT_DIR_ARTIFACT, 'Screenshot_Sync_Cockpit_Stark_S.png');
  await page.screenshot({ path: starkPath1, fullPage: true });
  fs.copyFileSync(starkPath1, starkPath2);

  // 3. Amazin Mets
  console.log('Switching to Amazin Mets theme...');
  await page.click('.theme-btn[data-theme="mets"]');
  await page.waitForTimeout(500);
  const metsPath1 = path.join(OUT_DIR_DROPS, 'Screenshot_Sync_Cockpit_Amazin_Mets.png');
  const metsPath2 = path.join(OUT_DIR_ARTIFACT, 'Screenshot_Sync_Cockpit_Amazin_Mets.png');
  await page.screenshot({ path: metsPath1, fullPage: true });
  fs.copyFileSync(metsPath1, metsPath2);

  // 4. Test Persistence on main /drops page
  console.log('Navigating to http://127.0.0.1:8088/ to verify theme persistence...');
  await page.goto('http://127.0.0.1:8088/', { waitUntil: 'networkidle' });
  const mainMetsPath1 = path.join(OUT_DIR_DROPS, 'Screenshot_Pilot_Drop_Mets_Persistent.png');
  const mainMetsPath2 = path.join(OUT_DIR_ARTIFACT, 'Screenshot_Pilot_Drop_Mets_Persistent.png');
  await page.screenshot({ path: mainMetsPath1, fullPage: true });
  fs.copyFileSync(mainMetsPath1, mainMetsPath2);

  await browser.close();
  console.log('✔ All visual twin captures completed successfully!');
}

capture().catch(err => {
  console.error('Visual twin capture error:', err);
  process.exit(1);
});
