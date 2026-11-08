// node export.js  -> Polo_Roof_Spoiler_Brochure.pdf + brochure_page1.png / brochure_page2.png
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const dir = __dirname;
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 794, height: 1123 }, deviceScaleFactor: 2.6 });
  const page = await ctx.newPage();
  await page.goto('file://' + path.join(dir, 'brochure.html'));
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(600);
  await page.pdf({ path: path.join(dir, 'Polo_Roof_Spoiler_Brochure.pdf'), format: 'A4', printBackground: true, preferCSSPageSize: true });
  const sections = await page.locator('section.page').all();
  for (let i = 0; i < sections.length; i++) {
    await sections[i].screenshot({ path: path.join(dir, 'brochure_page' + (i + 1) + '.png') });
  }
  const fonts = await page.evaluate(() => Array.from(document.fonts).map(f => f.family + ':' + f.status));
  console.log('pages', sections.length, 'fonts', fonts.join(', '));
  await browser.close();
})();
