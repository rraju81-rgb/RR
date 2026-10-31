// Headless renders of viewer/index.html with Playwright + Chromium (SwiftShader WebGL).
// usage: node render_views.cjs <port> <outdir> <w> <h> "name|query" ["name|query" ...]
const { chromium } = require('playwright');

(async () => {
  const [port, outdir, w, h, ...jobs] = process.argv.slice(2);
  const browser = await chromium.launch({
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
  });
  for (const job of jobs) {
    const [name, q] = job.split('|');
    const page = await browser.newPage({ viewport: { width: +w, height: +h } });
    page.on('pageerror', (e) => console.error('pageerror:', e.message));
    await page.goto(`http://127.0.0.1:${port}/viewer/index.html?shot=1&w=${w}&h=${h}&${q}`);
    await page.waitForFunction(() => window.__ready || window.__error, null, { timeout: 240000 });
    const err = await page.evaluate(() => window.__error);
    if (err) throw new Error(`${name}: ${err}`);
    await page.waitForTimeout(250);
    await page.screenshot({ path: `${outdir}/${name}.png` });
    await page.close();
    console.log('rendered', name);
  }
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
