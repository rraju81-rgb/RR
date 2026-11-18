// node spec/src/export.js  (from spoiler/) -> spec/Polo_Roof_Spoiler_Spec_Sheet.pdf + .png
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const dir = path.join(__dirname, '..');
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 794, height: 1123 }, deviceScaleFactor: 2.6 });
  const page = await ctx.newPage();
  await page.goto('file://' + path.join(dir, 'spec_sheet.html'));
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(500);
  await page.pdf({ path: path.join(dir, 'Polo_Roof_Spoiler_Spec_Sheet.pdf'), format: 'A4', printBackground: true, preferCSSPageSize: true });
  await page.locator('section.page').screenshot({ path: path.join(dir, 'Polo_Roof_Spoiler_Spec_Sheet.png') });
  const fonts = await page.evaluate(() => Array.from(document.fonts).map(f => f.family + ':' + f.status));
  console.log('spec sheet exported; fonts', fonts.join(', '));
  await browser.close();
})();
