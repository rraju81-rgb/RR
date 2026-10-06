import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
const [,, outDir, only, plain] = process.argv;
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1200, height: 900 }, deviceScaleFactor: 2 });
page.on('console', m => console.log('console:', m.text()));
page.on('pageerror', e => console.log('ERR', e.message));
await page.goto('http://127.0.0.1:8123/index.html');
await page.waitForFunction(() => window.ready === true, null, { timeout: 60000 });
const shots = only && only !== 'all' ? only.split(',') : await page.evaluate(() => window.SHOTS);
for (const s of shots) {
  const t = Date.now();
  for (const ann of (plain === 'both' ? [true, false] : [true])) {
    await page.evaluate(([n, a]) => window.renderShot(n, a), [s, ann]);
    await page.screenshot({ path: `${outDir}/${s}${ann ? '' : '_clean'}.png`, clip: { x: 0, y: 0, width: 1200, height: 900 } });
  }
  console.log(s, Date.now() - t, 'ms');
}
await browser.close();
