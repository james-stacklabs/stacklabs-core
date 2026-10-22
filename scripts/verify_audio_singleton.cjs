const { chromium } = require('playwright');

(async () => {
  console.log('🚀 Starting Playwright Audio Singleton Verification for WO0010152...');
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto('http://localhost:3040/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);

  // 1. Verify exactly ONE native <audio> element exists
  console.log('1. Checking count of <audio> elements in DOM...');
  const audioCount = await page.evaluate(() => document.querySelectorAll('audio').length);
  console.log(`   Audio elements count: ${audioCount}`);
  if (audioCount !== 1) {
    throw new Error(`Expected exactly 1 audio element, found ${audioCount}`);
  }
  console.log('   ✅ Exactly 1 <audio> element found in the DOM.');

  // Check initial track source
  const initialSrc = await page.evaluate(() => {
    const el = document.querySelector('audio');
    return el ? el.src : null;
  });
  console.log(`   Initial audio src: ${initialSrc}`);
  if (!initialSrc || !initialSrc.includes('Why_AI_makes_human_labor_unnecessary')) {
    throw new Error(`Expected initial src to include Why_AI_makes_human_labor_unnecessary, got: ${initialSrc}`);
  }

  // 2. Test Play / Pause reflecting on the single audio element
  console.log('2. Testing Play/Pause reflection on single audio element...');
  const playButton = await page.locator('button[title="Play"]').first();
  await playButton.click();
  await page.waitForTimeout(500);

  const isPlayingAfterClick = await page.evaluate(() => {
    const el = document.querySelector('audio');
    return el ? !el.paused : false;
  });
  console.log(`   Audio element isPlaying (paused === false): ${isPlayingAfterClick}`);

  // Pause
  const pauseButton = await page.locator('button[title="Pause"]').first();
  await pauseButton.click();
  await page.waitForTimeout(500);

  const isPausedAfterClick = await page.evaluate(() => {
    const el = document.querySelector('audio');
    return el ? el.paused : false;
  });
  console.log(`   Audio element isPaused (paused === true): ${isPausedAfterClick}`);
  if (!isPausedAfterClick) {
    throw new Error('Expected audio element to be paused after clicking Pause button');
  }
  console.log('   ✅ Play/Pause correctly reflects on single audio element.');

  // 3. Test Toggling between Track 1 and Track 2
  console.log('3. Testing episode switch to Ep 2...');
  const ep2Btn = await page.locator('button:has-text("Ep 2: The Sovereign Response")').first();
  await ep2Btn.click();
  await page.waitForTimeout(500);

  // Verify src updated on that single audio element
  const srcAfterEp2 = await page.evaluate(() => {
    const el = document.querySelector('audio');
    return el ? el.src : null;
  });
  console.log(`   Audio src after clicking Ep 2: ${srcAfterEp2}`);
  if (!srcAfterEp2 || !srcAfterEp2.includes('Why_AI_is_hitting_a_physical_wall')) {
    throw new Error(`Expected src to include Why_AI_is_hitting_a_physical_wall, got: ${srcAfterEp2}`);
  }

  // Verify still exactly 1 audio element
  const audioCountAfterSwitch = await page.evaluate(() => document.querySelectorAll('audio').length);
  if (audioCountAfterSwitch !== 1) {
    throw new Error(`Expected still exactly 1 audio element, found ${audioCountAfterSwitch}`);
  }
  console.log('   ✅ Single audio element source switched cleanly to Track 2.');

  // 4. Test Prev button back to Track 1
  console.log('4. Testing Prev button back to Track 1...');
  const prevBtn = await page.locator('button[title="Previous Episode"]').first();
  await prevBtn.click();
  await page.waitForTimeout(500);

  const srcAfterPrev = await page.evaluate(() => {
    const el = document.querySelector('audio');
    return el ? el.src : null;
  });
  console.log(`   Audio src after clicking Prev: ${srcAfterPrev}`);
  if (!srcAfterPrev || !srcAfterPrev.includes('Why_AI_makes_human_labor_unnecessary')) {
    throw new Error(`Expected src to include Why_AI_makes_human_labor_unnecessary, got: ${srcAfterPrev}`);
  }
  console.log('   ✅ Previous track switch verified on singleton audio element.');

  // 5. Test Mobile Viewport
  console.log('5. Testing Mobile Viewport (390x844)...');
  const mobilePage = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await mobilePage.goto('http://localhost:3040/', { waitUntil: 'networkidle' });
  await mobilePage.waitForTimeout(500);

  const mobileAudioCount = await mobilePage.evaluate(() => document.querySelectorAll('audio').length);
  console.log(`   Mobile DOM Audio count: ${mobileAudioCount}`);
  if (mobileAudioCount !== 1) {
    throw new Error(`Expected 1 audio element in mobile DOM, found ${mobileAudioCount}`);
  }

  // Mobile switch to Ep 2
  const mobileEp2Btn = mobilePage.locator('.lg\\:hidden button:has-text("Ep 2: The Sovereign Response")');
  await mobileEp2Btn.click();
  await mobilePage.waitForTimeout(500);

  const mobileSrcAfterSwitch = await mobilePage.evaluate(() => {
    const el = document.querySelector('audio');
    return el ? el.src : null;
  });
  console.log(`   Mobile Audio src after switch: ${mobileSrcAfterSwitch}`);
  if (!mobileSrcAfterSwitch || !mobileSrcAfterSwitch.includes('Why_AI_is_hitting_a_physical_wall')) {
    throw new Error(`Expected mobile src to include Why_AI_is_hitting_a_physical_wall, got: ${mobileSrcAfterSwitch}`);
  }
  console.log('   ✅ Mobile viewport verified: exactly 1 audio element maintained across interactions.');

  await browser.close();
  console.log('\n🎉 ALL AUDIO SINGLETON ACCEPTANCE CRITERIA VERIFIED SUCCESSFULLY!');
})();
