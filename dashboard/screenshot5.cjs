const { chromium } = require('./node_modules/@playwright/test');

(async () => {
  const browser = await chromium.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(1500);

  for (const btn of await page.$$('button')) {
    const txt = await btn.innerText().catch(() => '');
    if (txt.includes('Skip')) { await btn.click(); break; }
  }
  await page.keyboard.press('Escape');
  await page.waitForTimeout(800);

  // Click Run
  for (const btn of await page.$$('button')) {
    const txt = await btn.innerText().catch(() => '');
    if (txt.includes('▶') || txt.toLowerCase() === 'run') { await btn.click(); break; }
  }
  await page.waitForTimeout(1000);

  // Navigate to Inspector
  const sideIcons = await page.$$('nav button, aside button, [class*="rail"] button, [class*="sidebar"] button');
  for (const btn of sideIcons) {
    const label = await btn.getAttribute('aria-label').catch(() => '');
    if (label === 'Inspector') { await btn.click(); break; }
  }
  await page.waitForTimeout(3000);
  await page.screenshot({ path: 'C:\\Users\\Rubik\\AppData\\Local\\Temp\\dashboard5.png' });
  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
