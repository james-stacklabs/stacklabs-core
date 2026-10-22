const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ 
    ignoreHTTPSErrors: true, 
    args: ['--no-sandbox', '--ignore-certificate-errors'] 
  });
  const page = await browser.newPage();
  
  page.on('console', msg => console.log(`[BROWSER CONSOLE] ${msg.type()}: ${msg.text()}`));
  page.on('pageerror', error => console.log(`[BROWSER ERROR] ${error.message}`));
  
  console.log("Navigating to http://127.0.0.1:3008/");
  await page.goto('http://127.0.0.1:3008/', { waitUntil: 'networkidle0' });
  
  console.log("Page loaded. Waiting 3 seconds for React to mount...");
  await new Promise(r => setTimeout(r, 3000));
  
  await browser.close();
})();
