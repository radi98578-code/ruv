const { chromium } = require('./node_modules/@playwright/test');

(async () => {
  const browser = await chromium.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(2000);

  // Dismiss onboarding
  const buttons = await page.$$('button');
  for (const btn of buttons) {
    const txt = await btn.innerText().catch(() => '');
    if (txt.includes('Skip')) { await btn.click(); break; }
  }
  await page.keyboard.press('Escape');
  await page.waitForTimeout(1500);

  // Click "Run the simulation" or the run/play button in topbar
  const allBtns = await page.$$('button');
  for (const btn of allBtns) {
    const txt = await btn.innerText().catch(() => '');
    if (txt.toLowerCase().includes('run') || txt.toLowerCase().includes('start')) {
      console.log('Clicking: ' + txt.trim());
      await btn.click();
      break;
    }
  }
  await page.waitForTimeout(4000);
  await page.screenshot({ path: 'C:\\Users\\Rubik\\AppData\\Local\\Temp\\dashboard3.png' });

  // Also try navigating to the inspector/scene panel via sidebar
  // Look for sidebar nav items
  const navItems = await page.$$('[role="navigation"] a, nav a, .rail a, aside a');
  console.log('Nav items: ' + navItems.length);

  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
