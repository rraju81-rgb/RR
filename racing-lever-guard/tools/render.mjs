// Render PNG images of the lever guard from the viewer page with headless Chromium.
//
//   node render.mjs <viewer.html> <out_dir> [three_dir]
//
// three_dir: a local copy of the three@0.160.0 npm package; when given, CDN requests for three
// are served from it (for machines without internet access).
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");

const [viewer, outDir, threeDir] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });

const SHOTS = [
  {
    file: "hero.png", colour: "red", size: [1600, 1100], fov: 26,
    camera: { pos: [215, 285, 185], target: [-58, 34, -10] },
  },
  { file: "plan_view.png", view: "plan", colour: "red", size: [1600, 1000] },
  { file: "front_view.png", view: "front", colour: "red", size: [1600, 900] },
  {
    file: "bar_end_view.png", colour: "red", size: [1400, 1000], fov: 24,
    camera: { pos: [330, 60, 70], target: [0, 28, -14] },
  },
  {
    file: "exploded.png", colour: "red", reference: false, explode: 1, size: [1800, 1000], fov: 24,
    camera: { pos: [250, 250, 200], target: [14, 30, -14] },
  },
  ...["red", "blue", "gold", "black", "silver"].map((c) => ({
    file: `colour_${c}.png`, colour: c, reference: false, size: [800, 640], fov: 26,
    camera: { pos: [170, 220, 150], target: [-30, 38, -12] },
  })),
];

const browser = await chromium.launch({
  executablePath: process.env.CHROME || undefined,
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
});
const page = await browser.newPage({ viewport: { width: 1900, height: 1300 }, deviceScaleFactor: 1 });
page.on("console", (m) => { if (m.type() === "error") console.log("console:", m.text()); });
page.on("pageerror", (e) => console.log("pageerror:", e.message));
if (threeDir) {
  await page.route("https://cdn.jsdelivr.net/npm/three@0.160.0/**", (route) => {
    const rel = new URL(route.request().url()).pathname.replace("/npm/three@0.160.0/", "");
    route.fulfill({ path: path.join(threeDir, rel), contentType: "text/javascript" });
  });
}
await page.route("https://fonts.googleapis.com/**", (r) => r.fulfill({ body: "", contentType: "text/css" }));
await page.goto("file://" + path.resolve(viewer));
await page.waitForFunction(() => window.viewerReady === true, null, { timeout: 120000 });

for (const shot of SHOTS) {
  await page.evaluate((o) => window.viewer.shot(o), shot);
  await page.waitForTimeout(500);
  await page.locator("#stage").screenshot({ path: path.join(outDir, shot.file) });
  console.log("rendered", shot.file);
}
await browser.close();
