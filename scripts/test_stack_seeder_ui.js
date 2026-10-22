import { chromium } from 'playwright';

(async () => {
  console.log('🚀 Initiating Stack Seeder UI User Acceptance Test...');
  const browser = await chromium.launch({
    args: ['--disable-features=VaapiVideoDecoder,VaapiVideoDecodeLinuxGL', '--no-sandbox']
  });

  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();

  // 1. Visit Portal & Perform Login
  console.log('🔑 Authenticating as James...');
  try {
    await page.goto('https://clio.taila01894.ts.net:3016/', { waitUntil: 'networkidle', timeout: 20000 });
    
    const isAuthVisible = await page.isVisible('#auth-username');
    if (isAuthVisible) {
      console.log('🔑 Found authentication gate. Logging in...');
      await page.fill('#auth-username', 'james');
      await page.fill('#auth-password', '!!Stella1977');
      await page.click('#auth-submit');
      await page.waitForSelector('text=ENVIRONMENT', { timeout: 20000 });
      console.log('✅ Authentication successful!');
    } else {
      console.log('✅ Auto-authenticated via Tailnet IP / existing session.');
    }
  } catch (err) {
    console.error('❌ Authentication failed:', err.message);
    await browser.close();
    process.exit(1);
  }

  // 2. Navigate to Stack Seeder Room
  console.log('🌱 Navigating to Stack Seeder portal room...');
  try {
    await page.goto('https://clio.taila01894.ts.net:3016/?room=stack_seeder', { waitUntil: 'networkidle', timeout: 20000 });
    await page.waitForSelector('text=STACK SEEDER', { timeout: 20000 });
    console.log('✅ Stack Seeder Console loaded successfully.');
  } catch (err) {
    console.error('❌ Failed to load Stack Seeder Console:', err.message);
    await browser.close();
    process.exit(1);
  }

  // 3. Select WeedStack Preset
  console.log('🌿 Applying "WeedStack" Preset...');
  try {
    await page.selectOption('select', 'weedstack');
    // Verify inputs populated
    await page.waitForFunction(() => {
      const input = document.querySelector('input[placeholder*="James\'s Bistro"]');
      return input && input.value !== '';
    }, { timeout: 10000 });
    console.log('✅ Preset values applied successfully to the form inputs.');
  } catch (err) {
    console.error('❌ Failed to apply preset:', err.message);
    await browser.close();
    process.exit(1);
  }

  // 4. Trigger Ingestion Sequence
  console.log('⚙️ Navigating to Ingestion Pipeline tab...');
  try {
    await page.click('button:has-text("Ingestion Pipeline")');
    console.log('⚙️ Executing brand ingestion cascade...');
    await page.click('button:has-text("Execute Ingestion Sequence")');
    console.log('⏳ Ingestion sequence triggered, monitoring terminal logs...');
    
    // Wait for complete screen (contains text: "Stack Successfully Seeded!")
    await page.waitForSelector('text=Stack Successfully Seeded!', { timeout: 90000 });
    console.log('🎉 Ingestion complete! Success screen is visible.');
    
    const details = await page.locator('.grid').first().innerText();
    console.log('\n📊 UAT INGESTION METRICS PREVIEW:\n' + details + '\n');
  } catch (err) {
    console.error('❌ Ingestion cascade timed out or failed:', err.message);
    await browser.close();
    process.exit(1);
  }

  await browser.close();
  console.log('🏁 Stack Seeder UI User Acceptance Test Passed Successfully!');
})();
