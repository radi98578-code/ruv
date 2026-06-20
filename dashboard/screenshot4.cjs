const { chromium } = require('./node_modules/@playwright/test');

(async () => {
  const browser = await chromium.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(1500);

  // Dismiss onboarding
  for (const btn of await page.$$('button')) {
    const txt = await btn.innerText().catch(() => '');
    if (txt.includes('Skip')) { await btn.click(); break; }
  }
  await page.keyboard.press('Escape');
  await page.waitForTimeout(800);

  // Click Run
  for (const btn of await page.$$('button')) {
    const txt = await btn.innerText().catch(() => '');
    if (txt.toLowerCase().includes('▶') || txt.toLowerCase().includes('run')) {
      await btn.click();
      break;
    }
  }
  await page.waitForTimeout(1000);

  // Click sidebar icons to navigate to scene/inspector view
  const sideIcons = await page.$$('nav button, aside button, [class*="rail"] button, [class*="sidebar"] button');
  console.log('Sidebar buttons: ' + sideIcons.length);
  for (const btn of sideIcons) {
    const label = await btn.getAttribute('aria-label').catch(() => '');
    const title = await btn.getAttribute('title').catch(() => '');
    console.log('btn:', label, title);
  }

  // Try clicking left sidebar second icon (usually scene)
  if (sideIcons.length > 1) {
    await sideIcons[1].click();
    await page.waitForTimeout(2000);
  }

  await page.screenshot({ path: 'C:\\Users\\Rubik\\AppData\\Local\\Temp\\dashboard4.png' });

  // Log visible text
  const text = await page.evaluate(() => document.body.innerText.slice(0, 300));
  console.log('TEXT:', text);

  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
