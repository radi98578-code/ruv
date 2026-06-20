const { chromium } = require('./node_modules/@playwright/test');

(async () => {
  const browser = await chromium.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(2000);

  // Dismiss onboarding tour
  const buttons = await page.$$('button');
  for (const btn of buttons) {
    const txt = await btn.innerText().catch(() => '');
    if (txt.includes('Skip')) { await btn.click(); break; }
  }
  await page.keyboard.press('Escape');
  await page.waitForTimeout(4000);

  await page.screenshot({ path: 'C:\\Users\\Rubik\\AppData\\Local\\Temp\\dashboard2.png' });
  await browser.close();
  console.log('done');
})().catch(e => { console.error(e.message); process.exit(1); });
