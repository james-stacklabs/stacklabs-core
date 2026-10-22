const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    ignoreHTTPSErrors: true,
  });
  const page = await context.newPage();

  console.log('Navigating to https://www.stacklabsllc.com/wildseed ...');
  await page.goto('https://www.stacklabsllc.com/wildseed', { waitUntil: 'networkidle', timeout: 30000 });

  // Click Parchment theme
  console.log('Selecting Parchment theme...');
  await page.click('[data-testid="theme-btn-parchment"]');
  await page.waitForTimeout(1000);

  const outDir = '/home/james/SovereignOS/vault_matrix/playbook_assets';
  fs.mkdirSync(outDir, { recursive: true });

  // 1. Hero
  await page.screenshot({ path: path.join(outDir, 'wildseed_parchment_1_hero.png') });
  console.log('Saved hero screenshot');

  // 2. Extract Vault & Terpene Radar
  const vaultEl = await page.$('#vault');
  if (vaultEl) {
    await vaultEl.scrollIntoViewIfNeeded();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(outDir, 'wildseed_parchment_2_vault.png') });
    console.log('Saved vault & radar screenshot');
  }

  // 3. Field Notes
  const notesEl = await page.$('#field-notes');
  if (notesEl) {
    await notesEl.scrollIntoViewIfNeeded();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(outDir, 'wildseed_parchment_3_fieldnotes.png') });
    console.log('Saved field notes screenshot');

    // Open first essay modal
    const readBtn = await page.$('#field-notes article button');
    if (readBtn) {
      await readBtn.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: path.join(outDir, 'wildseed_parchment_3b_modal.png') });
      console.log('Saved reading modal screenshot');
      // Close modal
      const closeBtn = await page.$('button[aria-label="Close modal"]') || await page.$('div.fixed.z-50 button:has(svg.lucide-x)');
      if (closeBtn) await closeBtn.click();
      await page.waitForTimeout(500);
    }
  }

  // 4. Saloon Lounge
  const saloonEl = await page.$('#saloon');
  if (saloonEl) {
    await saloonEl.scrollIntoViewIfNeeded();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(outDir, 'wildseed_parchment_4_saloon.png') });
    console.log('Saved saloon lounge screenshot');
  }

  // 5. Delivery Radar
  const deliveryEl = await page.$('#delivery');
  if (deliveryEl) {
    await deliveryEl.scrollIntoViewIfNeeded();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(outDir, 'wildseed_parchment_5_delivery.png') });
    console.log('Saved delivery radar screenshot');
  }

  await browser.close();
  console.log('All Parchment section verification captures completed.');
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
