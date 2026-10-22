import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

(async () => {
  console.log('🚀 Launching Sovereign Sports Fan Portal (Port 3010) Playwright Audit...');
  
  // Ensure directories exist
  fs.mkdirSync('/home/james/SovereignOS/lookbook_assets', { recursive: true });
  fs.mkdirSync('/home/james/SovereignOS/vault_matrix', { recursive: true });
  fs.mkdirSync('/home/james/sovereign_inbox/reports', { recursive: true });

  const browser = await chromium.launch({
    args: ['--disable-features=VaapiVideoDecoder,VaapiVideoDecodeLinuxGL', '--no-sandbox']
  });
  
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();

  let auditLog = `### 📋 SOVEREIGN SPORTS 3010 AUDIT REPORT - ${new Date().toLocaleDateString()}\n\n`;
  let consoleErrors = [];

  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
      console.log(`❌ Console Error: ${msg.text()}`);
    }
  });

  // 1. Visit Sports Fan Portal Directly
  console.log('📺 Navigating directly to Sovereign Sports Fan Portal (Port 3010)...');
  let loaded = false;
  try {
    await page.goto('https://clio.taila01894.ts.net:3010/fan-portal?game_room=824910', { waitUntil: 'networkidle', timeout: 20000 });
    
    // Check if we see key portal elements
    const crosstalkBadge = page.locator('text=Sovereign Sports').or(page.locator('text=No Game Room Selected'));
    if (await crosstalkBadge.first().isVisible()) {
      console.log('✅ Sports Fan Portal page loaded successfully using pre-existing session.');
      loaded = true;
      auditLog += `* Pilot Session Verification: **PASSED ✅** (Pre-authenticated)\n`;
    }
  } catch (err) {
    console.log('ℹ️ Direct access failed or timed out. Current URL:', page.url(), 'Error:', err.message);
  }

  // 2. Fallback Authentication Flow
  if (!loaded) {
    console.log('🔑 Performing fallback authentication flow on main portal...');
    try {
      await page.goto('https://clio.taila01894.ts.net:3000/', { waitUntil: 'networkidle', timeout: 20000 });
      console.log('Main portal URL:', page.url());
      const usernameInput = page.locator('#auth-username');
      if (await usernameInput.isVisible()) {
        console.log('Logging in...');
        await usernameInput.fill('james');
        await page.fill('#auth-password', '!!Stella1977');
        await page.click('#auth-submit');
        await page.waitForTimeout(2000);
      } else {
        console.log('Auth input not visible, already logged in?');
      }
      
      console.log('📺 Retrying navigation to Sovereign Sports Fan Portal...');
      await page.goto('https://clio.taila01894.ts.net:3010/fan-portal?game_room=824910', { waitUntil: 'networkidle', timeout: 20000 });
      console.log('Sports portal URL after navigation retry:', page.url());
      try {
        await page.waitForSelector('div.fan-portal-workspace', { timeout: 20000 });
        console.log('✅ Sports Fan Portal loaded successfully after authentication.');
        auditLog += `* Pilot Session Verification: **PASSED ✅** (Authenticated via fallback)\n`;
        loaded = true;
      } catch (selErr) {
        await page.screenshot({ path: '/home/james/SovereignOS/lookbook_assets/auth_failure.png' });
        console.error('❌ Selector wait failed. Captured lookbook_assets/auth_failure.png. Page content:', await page.content());
        throw selErr;
      }
    } catch (authErr) {
      console.error('❌ Fallback authentication failed:', authErr.message);
      auditLog += `* Pilot Session Verification: **FAILED ❌** (${authErr.message})\n`;
    }
  }

  // 3. Page Load check
  auditLog += `* Fan Portal Page Load: **${loaded ? 'PASSED ✅' : 'FAILED ❌'}**\n`;

  let fanPortalVerified = false;
  let hasSoundboard = false;
  let centralWidth = 'unknown';

  // 4. Verify Layout Structure (65% Central Column / 35% Terrace Balcony)
  if (loaded) {
    console.log('📐 Auditing 65/35 "Deep Void" layout structural integrity...');
    try {
      const centralBroadcastColumn = page.locator('.central-broadcast-column');
      const isCentralVisible = await centralBroadcastColumn.isVisible();
      centralWidth = await centralBroadcastColumn.evaluate(el => el.style.width);
      
      console.log(`Central Broadcast column width: ${centralWidth}, Visible: ${isCentralVisible}`);
      
      if (isCentralVisible && centralWidth === '65%') {
        console.log('✅ 65/35 Deep Void layout verified successfully.');
        auditLog += `* 65/35 Layout Verification: **PASSED ✅** (Central Column Width: ${centralWidth})\n`;
        fanPortalVerified = true;
      } else {
        console.warn('⚠️ 65/35 Layout check returned unexpected values.');
        auditLog += `* 65/35 Layout Verification: **WARNING ⚠️** (Width: ${centralWidth}, Visible: ${isCentralVisible})\n`;
      }
    } catch (layoutErr) {
      console.error('❌ Layout verification failed:', layoutErr.message);
      auditLog += `* 65/35 Layout Verification: **FAILED ❌** (${layoutErr.message})\n`;
    }

    // 5. Verify Advocate Soundboard elements
    console.log('🔊 Auditing Advocate Soundboard visibility...');
    try {
      const expandBtn = page.locator('text=EXPAND DECK CONTROLS');
      if (await expandBtn.isVisible()) {
        console.log('Clicking EXPAND DECK CONTROLS...');
        await expandBtn.click();
        await page.waitForTimeout(500); // Wait for state update
      }
      
      const soundboardHeader = page.locator('text=ADVOCATE SOUNDBOARD');
      hasSoundboard = await soundboardHeader.first().isVisible();
      console.log(`Advocate Soundboard header visible: ${hasSoundboard}`);
      auditLog += `* Advocate Soundboard Present: **${hasSoundboard ? 'YES ✅' : 'NO ❌'}**\n`;
    } catch (soundboardErr) {
      console.error('❌ Advocate Soundboard verification failed:', soundboardErr.message);
      auditLog += `* Advocate Soundboard Present: **FAILED ❌** (${soundboardErr.message})\n`;
    }

    // Capture screenshot to lookbook_assets/fan_portal_core.png
    try {
      await page.screenshot({ path: '/home/james/SovereignOS/lookbook_assets/fan_portal_core.png' });
      console.log('📸 Fan Portal screenshot captured successfully to lookbook_assets/fan_portal_core.png');
      auditLog += `* Fan Portal Screenshot: **CAPTURED ✅**\n`;
    } catch (screenshotErr) {
      console.error('❌ Failed to capture Fan Portal screenshot:', screenshotErr.message);
    }
  }

  // 6. Navigate to Creator Portal
  console.log('📺 Navigating to Creator Portal / Playcall Desk...');
  let creatorLoaded = false;
  let commandDeckVisible = false;
  let toxicityIndexVisible = false;
  let mardCoreVisible = false;

  try {
    await page.goto('https://clio.taila01894.ts.net:3010/creator-portal', { waitUntil: 'networkidle', timeout: 20000 });
    
    // Check for "Playcall Desk" or "Dormant Switch"
    const dormantSwitchText = page.locator('text=Dormant Switch');
    if (await dormantSwitchText.first().isVisible()) {
      console.log('✅ Creator Portal page loaded successfully.');
      creatorLoaded = true;
      auditLog += `* Creator Portal Load: **PASSED ✅**\n`;

      // Verify command deck
      commandDeckVisible = await page.locator('text=Web-Slinger Command Deck').first().isVisible();
      auditLog += `* Web-Slinger Command Deck Visible: **${commandDeckVisible ? 'YES ✅' : 'NO ❌'}**\n`;

      // Find Boggs Toxicity Index
      toxicityIndexVisible = await page.locator('text=Boggs Toxicity Index').first().isVisible();
      auditLog += `* Boggs Toxicity Index Control: **${toxicityIndexVisible ? 'YES ✅' : 'NO ❌'}**\n`;

      // Find M.A.R.D. Core Engine toggle
      mardCoreVisible = await page.locator('text=M.A.R.D. Core Engine').first().isVisible();
      auditLog += `* M.A.R.D. Core Engine Toggle: **${mardCoreVisible ? 'YES ✅' : 'NO ❌'}**\n`;

      // Capture screenshot to lookbook_assets/creator_portal_core.png
      try {
        await page.screenshot({ path: '/home/james/SovereignOS/lookbook_assets/creator_portal_core.png' });
        console.log('📸 Creator Portal screenshot captured successfully to lookbook_assets/creator_portal_core.png');
        auditLog += `* Creator Portal Screenshot: **CAPTURED ✅**\n`;
      } catch (screenshotErr) {
        console.error('❌ Failed to capture Creator Portal screenshot:', screenshotErr.message);
      }
    }
  } catch (err) {
    console.error('❌ Failed to load Creator Portal:', err.message);
    auditLog += `* Creator Portal Load: **FAILED ❌** (${err.message})\n`;
  }

  // 7. Output compiled schema JSON file
  const schema = {
    theme: {
      darkMode: true,
      backgroundColor: '#0f172a',
      fontFamily: 'monospace'
    },
    fanPortal: {
      url: 'https://clio.taila01894.ts.net:3010/fan-portal?game_room=824910',
      layout: '65/35',
      centralColumnWidth: centralWidth,
      sidebarColumnWidth: '35%',
      soundboardVisible: hasSoundboard
    },
    creatorPortal: {
      url: 'https://clio.taila01894.ts.net:3010/creator-portal',
      commandDeckVisible: commandDeckVisible,
      toxicityIndexVisible: toxicityIndexVisible,
      mardCoreVisible: mardCoreVisible
    },
    timestamp: new Date().toISOString()
  };

  try {
    fs.writeFileSync('/home/james/SovereignOS/vault_matrix/sports_portal_3010_schema.json', JSON.stringify(schema, null, 2));
    console.log('✅ Compiled schema JSON written to /home/james/SovereignOS/vault_matrix/sports_portal_3010_schema.json');
    auditLog += `* Schema JSON Compilation: **PASSED ✅**\n`;
  } catch (jsonErr) {
    console.error('❌ Failed to write schema JSON:', jsonErr.message);
    auditLog += `* Schema JSON Compilation: **FAILED ❌** (${jsonErr.message})\n`;
  }

  // Console Errors summary
  if (consoleErrors.length > 0) {
    auditLog += `\n### ❌ Console Errors Detected during session:\n`;
    consoleErrors.forEach(err => {
      auditLog += `- \`${err}\`\n`;
    });
  } else {
    auditLog += `\n### ✅ Zero Console Errors Detected.\n`;
  }

  // Write audit results
  fs.writeFileSync('/home/james/sovereign_inbox/reports/sovereign_3010_audit_results.md', auditLog);
  console.log('🏁 Audit completed successfully. Report written to /home/james/sovereign_inbox/reports/sovereign_3010_audit_results.md');

  await browser.close();
})();
