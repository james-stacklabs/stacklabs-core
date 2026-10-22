const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  console.log('🚀 Starting Playwright verification for WO0010150 (Sovereign Listen)...');
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const screenshotsDir = '/home/james/SovereignOS/screenshots';
  if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir, { recursive: true });
  }

  // --- Desktop Test ---
  console.log('\n🖥️  Testing Desktop Viewport (1920x1080)...');
  const desktopContext = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await desktopContext.newPage();

  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  await page.goto('http://localhost:3040/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);

  // 1. Verify Header Pilot Drop link
  console.log('1. Checking Pilot Drop Header Link...');
  const pilotDropLink = await page.$('a[href="https://drop.stacklabsllc.com"]');
  if (!pilotDropLink) {
    throw new Error('Pilot Drop link not found in Header!');
  }
  const pilotDropTarget = await pilotDropLink.getAttribute('target');
  const pilotDropText = await pilotDropLink.innerText();
  console.log(`   Pilot Drop link found: target="${pilotDropTarget}", text="${pilotDropText.trim()}"`);
  if (pilotDropTarget !== '_blank') throw new Error('Pilot Drop link missing target="_blank"');
  if (!pilotDropText.includes('Pilot Drop')) throw new Error('Pilot Drop text missing from link');
  const emeraldIndicator = await pilotDropLink.$('.bg-emerald-400.animate-pulse');
  if (!emeraldIndicator) throw new Error('Emerald pulse indicator missing inside Pilot Drop link');
  console.log('   ✅ Pilot Drop Header link verified.');

  // 2. Verify In-Player Episode Switcher Pills
  console.log('2. Checking In-Player Episode Switcher Pills...');
  const ep1Button = await page.$('button:has-text("Ep 1: The Pendulum")');
  const ep2Button = await page.$('button:has-text("Ep 2: The Sovereign Response")');
  if (!ep1Button || !ep2Button) {
    throw new Error('Episode switcher buttons not found in AudioPlayer!');
  }

  // Check Ep 1 is initially active
  const ep1Class = await ep1Button.getAttribute('class');
  console.log(`   Ep 1 active styling check: ${ep1Class.includes('bg-cyan-500/20')}`);
  if (!ep1Class.includes('bg-cyan-500/20')) {
    throw new Error('Ep 1 button should be active initially');
  }

  // 3. Verify Prev / Next Initial States on Track 1
  console.log('3. Checking Prev/Next controls initial state (Ep 1)...');
  const prevBtn = await page.$('button[title="Previous Episode"]');
  const nextBtn = await page.$('button[title="Next Episode"]');
  if (!prevBtn || !nextBtn) {
    throw new Error('Previous/Next buttons not found in AudioPlayer controls row!');
  }

  const prevDisabledInitial = await prevBtn.getAttribute('disabled');
  const nextDisabledInitial = await nextBtn.getAttribute('disabled');
  console.log(`   Ep 1: Prev disabled = ${prevDisabledInitial !== null}, Next disabled = ${nextDisabledInitial !== null}`);
  if (prevDisabledInitial === null) throw new Error('Prev button must be disabled on first track!');
  if (nextDisabledInitial !== null) throw new Error('Next button must NOT be disabled on first track!');

  // 4. Test clicking Ep 2 pill
  console.log('4. Clicking Ep 2 Switcher Pill...');
  await ep2Button.click();
  await page.waitForTimeout(500);

  const titleAfterEp2Click = await page.$eval('h1', el => el.innerText);
  console.log(`   Active track title after clicking Ep 2: "${titleAfterEp2Click}"`);
  if (!titleAfterEp2Click.includes('The Sovereign Response')) {
    throw new Error(`Expected title to contain 'The Sovereign Response', got: ${titleAfterEp2Click}`);
  }

  const ep2ClassAfterClick = await ep2Button.getAttribute('class');
  if (!ep2ClassAfterClick.includes('bg-cyan-500/20')) {
    throw new Error('Ep 2 button should be active after click');
  }

  // Prev should now be enabled, Next should be disabled
  const prevDisabledOnEp2 = await prevBtn.getAttribute('disabled');
  const nextDisabledOnEp2 = await nextBtn.getAttribute('disabled');
  console.log(`   Ep 2: Prev disabled = ${prevDisabledOnEp2 !== null}, Next disabled = ${nextDisabledOnEp2 !== null}`);
  if (prevDisabledOnEp2 !== null) throw new Error('Prev button must be enabled on track 2!');
  if (nextDisabledOnEp2 === null) throw new Error('Next button must be disabled on track 2!');

  // 5. Test clicking Prev button
  console.log('5. Clicking Prev Track button...');
  await prevBtn.click();
  await page.waitForTimeout(500);

  const titleAfterPrevClick = await page.$eval('h1', el => el.innerText);
  console.log(`   Active track title after clicking Prev: "${titleAfterPrevClick}"`);
  if (!titleAfterPrevClick.includes('The Pendulum & The Algorithm')) {
    throw new Error(`Expected title to contain 'The Pendulum & The Algorithm', got: ${titleAfterPrevClick}`);
  }

  // 6. Test clicking Next button
  console.log('6. Clicking Next Track button...');
  await nextBtn.click();
  await page.waitForTimeout(500);

  const titleAfterNextClick = await page.$eval('h1', el => el.innerText);
  console.log(`   Active track title after clicking Next: "${titleAfterNextClick}"`);
  if (!titleAfterNextClick.includes('The Sovereign Response')) {
    throw new Error(`Expected title to contain 'The Sovereign Response', got: ${titleAfterNextClick}`);
  }

  // Capture desktop screenshot
  const desktopScreenshot = path.join(screenshotsDir, 'listen_desktop_verification.png');
  await page.screenshot({ path: desktopScreenshot });
  console.log(`   Desktop screenshot saved: ${desktopScreenshot}`);

  await desktopContext.close();

  // --- Mobile Test ---
  console.log('\n📱 Testing Mobile Viewport (390x844)...');
  const mobileContext = await browser.newContext({
    viewport: { width: 390, height: 844 }
  });
  const mobilePage = await mobileContext.newPage();
  await mobilePage.goto('http://localhost:3040/', { waitUntil: 'networkidle' });
  await mobilePage.waitForTimeout(1000);

  // Check switcher pills in mobile viewport
  const mobileEp1 = await mobilePage.$('.lg\\:hidden button:has-text("Ep 1: The Pendulum")');
  const mobileEp2 = await mobilePage.$('.lg\\:hidden button:has-text("Ep 2: The Sovereign Response")');
  if (!mobileEp1 || !mobileEp2) {
    throw new Error('Episode switcher buttons not found on mobile view!');
  }

  const mobilePrev = await mobilePage.$('.lg\\:hidden button[title="Previous Episode"]');
  const mobileNext = await mobilePage.$('.lg\\:hidden button[title="Next Episode"]');
  if (!mobilePrev || !mobileNext) {
    throw new Error('Previous/Next buttons not found on mobile view!');
  }

  // Test mobile episode switcher click
  await mobileEp2.click();
  await mobilePage.waitForTimeout(500);
  const mobileTitle = await mobilePage.$eval('h1', el => el.innerText);
  console.log(`   Mobile track title after switch: "${mobileTitle}"`);
  if (!mobileTitle.includes('The Sovereign Response')) {
    throw new Error('Failed to switch episode on mobile!');
  }

  // Capture mobile screenshot
  const mobileScreenshot = path.join(screenshotsDir, 'listen_mobile_verification.png');
  await mobilePage.screenshot({ path: mobileScreenshot });
  console.log(`   Mobile screenshot saved: ${mobileScreenshot}`);

  await mobileContext.close();
  await browser.close();

  if (consoleErrors.length > 0) {
    console.warn('⚠️ Console errors detected:', consoleErrors);
  } else {
    console.log('✅ Zero console errors detected.');
  }

  console.log('\n🎉 ALL ACCEPTANCE CRITERIA VERIFIED SUCCESSFULLY!');
})();
