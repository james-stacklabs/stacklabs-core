import { chromium } from 'playwright';
import fs from 'fs';

(async () => {
  console.log('🚀 Launching Sovereign OS ATF Navigation Sweep...');
  const browser = await chromium.launch({
    args: ['--disable-features=VaapiVideoDecoder,VaapiVideoDecodeLinuxGL', '--no-sandbox']
  });
  
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();

  // Mapped Targets from the Sovereign System Codex Port Manifest
  const routes = [
    { name: 'Root Portal', url: 'https://clio.taila01894.ts.net:3000/' },
    { name: 'Sovereign Cinema', url: 'https://clio.taila01894.ts.net:3000/?room=prospectus' },
    { name: 'FanStack Dashboard', url: 'https://clio.taila01894.ts.net:3000/?room=kanban' },
    { name: 'AetherVet Telepresence', url: 'https://clio.taila01894.ts.net:3000/?room=aether_vet' },
    { name: 'WeedStack Matrix', url: 'https://clio.taila01894.ts.net:3000/?room=wildseed' }
  ];

  let auditLog = `### 📋 ATF NAVIGATION AUDIT LOG - MAY 28, 2026\n\n`;

  page.on('console', msg => {
    if (msg.type() === 'error') {
      auditLog += `❌ Console Error: ${msg.text()}\n`;
    }
  });

  // 1. Visit Root Portal and Authenticate
  console.log('🔑 Performing pilot authentication flow...');
  try {
    await page.goto('https://clio.taila01894.ts.net:3000/', { waitUntil: 'networkidle', timeout: 15000 });
    await page.fill('#auth-username', 'james');
    await page.fill('#auth-password', '!!Stella1977');
    await page.click('#auth-submit');
    await page.waitForSelector('text=PROD ENVIRONMENT', { timeout: 15000 });
    console.log('✅ Authentication successful! Session established.');
  } catch (authErr) {
    console.error('❌ Authentication failed:', authErr.message);
    auditLog += `💥 Authentication Failure: ${authErr.message}\n\n`;
  }

  for (const route of routes) {
    console.log(`Checking route: ${route.name} -> ${route.url}`);
    auditLog += `#### Subsystem: ${route.name}\n`;

    try {
      const response = await page.goto(route.url, { waitUntil: 'networkidle', timeout: 15000 });
      const status = response.status();
      auditLog += `* HTTP Status: **${status}**\n`;

      // Invariant Check: Verify Global Environment Banner Mandate (KI-031)
      const bannerVisible = await page.locator('text=PROD ENVIRONMENT').isVisible();
      auditLog += `* KI-031 Banner Present: **${bannerVisible ? 'YES ✅' : 'NO ❌'}**\n\n`;
    } catch (err) {
      auditLog += `💥 Route Crash: ${err.message}\n\n`;
    }
  }

  fs.writeFileSync('/home/james/sovereign_inbox/reports/atf_nav_results.md', auditLog);
  await browser.close();
  console.log('🏁 Sweep complete. Results staged in inbox reports.');
})();
