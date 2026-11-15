#!/usr/bin/env node
// Render several STL files together per panel (assemblies, exploded views) with three.js in headless Chromium.
// Usage: node render_scene.js spec.json out.png
// spec = { "w": 640, "h": 560, "panels": [ { "label": "...", "eye": [x,y,z],
//          "items": [ { "file": "a.stl", "color": "#8fa6c4", "offset": [x,y,z], "opacity": 1, "edges": true } ] } ] }
const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const [specPath, outPng] = process.argv.slice(2);
  const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
  const W = spec.w || 640, H = spec.h || 560;
  for (const p of spec.panels) for (const it of p.items) it.b64 = fs.readFileSync(it.file).toString('base64');
  const html = `<!doctype html><html><head><meta charset="utf-8"><style>
  body{margin:0;background:#fff;font-family:"DejaVu Sans",Arial,sans-serif}
  .lab{position:absolute;top:14px;font-size:14px;font-weight:600;letter-spacing:.06em;color:#14181f}
  </style></head><body>
  ${spec.panels.map((p, i) => `<div class="lab" style="left:${i * W + 20}px">${p.label}</div>`).join('')}
  <canvas id="c" width="${W * spec.panels.length}" height="${H}"></canvas>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/STLLoader.js"></script>
  <script>
  const S = ${JSON.stringify(spec)};
  const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('c'), antialias: true });
  renderer.setClearColor(0xffffff, 1); renderer.setScissorTest(true); renderer.sortObjects = true;
  S.panels.forEach((p, i) => {
    const scene = new THREE.Scene();
    scene.add(new THREE.HemisphereLight(0xf4f7fb, 0x3a3f47, 0.9));
    const k = new THREE.DirectionalLight(0xffffff, 0.75); k.position.set(160, -220, 300); scene.add(k);
    const f = new THREE.DirectionalLight(0xdfe7ff, 0.4); f.position.set(-240, 180, -80); scene.add(f);
    const box = new THREE.Box3();
    p.items.forEach(it => {
      const bin = atob(it.b64), u8 = new Uint8Array(bin.length);
      for (let j = 0; j < bin.length; j++) u8[j] = bin.charCodeAt(j);
      const geom = new THREE.STLLoader().parse(u8.buffer);
      const off = it.offset || [0, 0, 0];
      geom.translate(off[0], off[1], off[2]);
      geom.computeBoundingBox(); box.union(geom.boundingBox);
      const op = it.opacity === undefined ? 1 : it.opacity;
      const mat = new THREE.MeshStandardMaterial({ color: it.color, metalness: 0.1, roughness: 0.6, side: THREE.DoubleSide,
        transparent: op < 1, opacity: op, depthWrite: op >= 1 });
      const mesh = new THREE.Mesh(geom, mat); mesh.renderOrder = op < 1 ? 2 : 1; scene.add(mesh);
      if (it.edges !== false) {
        const e = new THREE.LineSegments(new THREE.EdgesGeometry(geom, 25),
          new THREE.LineBasicMaterial({ color: 0x14181f, transparent: true, opacity: op < 1 ? 0.35 : 0.7 }));
        e.renderOrder = 3; scene.add(e);
      }
    });
    const c = box.getCenter(new THREE.Vector3()), r = box.getSize(new THREE.Vector3()).length() / 2;
    const cam = new THREE.PerspectiveCamera(24, ${W} / ${H}, 1, 10000);
    cam.up.set(0, 0, 1);
    const d = new THREE.Vector3(...p.eye).normalize();
    cam.position.copy(c).addScaledVector(d, r / Math.sin(THREE.MathUtils.degToRad(12)) * (p.zoom || 0.9));
    cam.lookAt(c);
    renderer.setViewport(i * ${W}, 0, ${W}, ${H}); renderer.setScissor(i * ${W}, 0, ${W}, ${H});
    renderer.render(scene, cam);
  });
  window.done = true;
  </script></body></html>`;
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: W * spec.panels.length, height: H } });
  const errs = [];
  page.on('pageerror', e => errs.push(String(e)));
  await page.setContent(html, { waitUntil: 'networkidle' });
  await page.waitForFunction('window.done === true', null, { timeout: 60000 });
  await page.screenshot({ path: outPng });
  await browser.close();
  console.log(errs.length ? errs.join('\n') : 'wrote ' + outPng);
})();
