// Render PNG images of the lever guard from the viewer page with headless Chromium.
//
//   node render.mjs <viewer.html> <out_dir> [three_dir]
//
// SHOTS_FILE=shots.json replaces the built-in shot list (e.g. tools/bike_shots.json for the bike
// page); SHOTS=a.png,b.png renders only those files.
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

const DEFAULT_SHOTS = [
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
    file: "exploded.png", colour: "red", reference: false, explode: 1, size: [1800, 1000], fov: 31,
    camera: { pos: [250, 250, 200], target: [-34, 38, -4] },
  },
  {
    file: "bend_gusset_detail.png", colour: "red", diffuser: false, size: [1400, 1000], fov: 34,
    camera: { pos: [-10, 95, 84], target: [10, 43, -25] },
  },
  {
    file: "wind_guard_front.png", colour: "red", size: [1600, 1000], fov: 28,
    camera: { pos: [60, 420, 120], target: [-80, 40, 0] },
  },
  {
    file: "wind_guard_mount_detail.png", colour: "red", reference: false, size: [1400, 1000], fov: 30,
    camera: { pos: [95, 70, -205], target: [-25, 58, -34] },
  },
  ...["red", "blue", "gold", "black", "silver"].map((c) => ({
    file: `colour_${c}.png`, colour: c, reference: false, size: [800, 640], fov: 34,
    camera: { pos: [210, 250, 170], target: [-62, 42, -2] },
  })),
];

const SHOTS = process.env.SHOTS_FILE ? JSON.parse(fs.readFileSync(process.env.SHOTS_FILE, "utf8")) : DEFAULT_SHOTS;

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

const only = process.env.SHOTS ? process.env.SHOTS.split(",") : null;
for (const shot of SHOTS.filter((s) => !only || only.includes(s.file))) {
  await page.evaluate((o) => window.viewer.shot(o), shot);
  await page.waitForTimeout(500);
  const box = await page.locator("#stage").boundingBox();
  await page.screenshot({ path: path.join(outDir, shot.file), clip: box, timeout: 120000 });
  console.log("rendered", shot.file);
}
await browser.close();
