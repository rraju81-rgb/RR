#!/usr/bin/env node
// Turn the drawing SVGs into true-size PDFs (and PNG previews) with headless Chromium.
// Usage: node svg2pdf.js ../out/drawing_formed.svg ../out/drawing_blank.svg ../out/template_1to1.svg
const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const files = process.argv.slice(2);
  const browser = await chromium.launch();
  for (const f of files) {
    const svg = fs.readFileSync(f, 'utf8');
    const m = svg.match(/width="([\d.]+)mm" height="([\d.]+)mm"/);
    if (!m) { console.error('no mm size in', f); process.exitCode = 1; continue; }
    const w = parseFloat(m[1]), h = parseFloat(m[2]);
    const page = await browser.newPage();
    await page.setContent(`<html><head><style>@page{size:${w}mm ${h}mm;margin:0}html,body{margin:0;padding:0;background:#fff}svg{display:block}</style></head><body>${svg}</body></html>`);
    await page.pdf({ path: f.replace(/\.svg$/, '.pdf'), width: `${w}mm`, height: `${h}mm`, printBackground: true, pageRanges: '1' });
    const k = 4; // px per mm for the preview
    await page.setViewportSize({ width: Math.round(w * k), height: Math.round(h * k) });
    await page.addStyleTag({ content: `svg{width:${w * k}px;height:${h * k}px}` });
    await page.screenshot({ path: f.replace(/\.svg$/, '.png'), clip: { x: 0, y: 0, width: Math.round(w * k), height: Math.round(h * k) } });
    await page.close();
    console.log('wrote', f.replace(/\.svg$/, '.pdf'), `${w} x ${h} mm`);
  }
  await browser.close();
})();
