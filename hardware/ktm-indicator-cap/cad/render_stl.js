#!/usr/bin/env node
// Render STL files side by side with three.js in headless Chromium (needs Playwright and internet for three.js).
// Usage: node render_stl.js out.png "file.stl|ex,ey,ez|Label" ["file2.stl|ex,ey,ez|Label"] ...
//   ex,ey,ez = direction from the part towards the camera (z is up)
const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const [outPng, ...specs] = process.argv.slice(2);
  const panels = specs.map(s => {
    const [file, eye, label] = s.split('|');
    return { b64: fs.readFileSync(file).toString('base64'), eye: eye.split(',').map(Number), label: label || file };
  });
  const W = 640, H = 560;
  const html = `<!doctype html><html><head><meta charset="utf-8"><style>
  body{margin:0;background:#fff;font-family:"DejaVu Sans",Arial,sans-serif}
  .lab{position:absolute;top:14px;font-size:14px;font-weight:600;letter-spacing:.06em;color:#14181f}
  </style></head><body>
  ${panels.map((p, i) => `<div class="lab" style="left:${i * W + 20}px">${p.label}</div>`).join('')}
  <canvas id="c" width="${W * panels.length}" height="${H}"></canvas>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/STLLoader.js"></script>
  <script>
  const P = ${JSON.stringify(panels)};
  const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('c'), antialias: true });
  renderer.setClearColor(0xffffff, 1); renderer.setScissorTest(true);
  P.forEach((p, i) => {
    const bin = atob(p.b64), u8 = new Uint8Array(bin.length);
    for (let j = 0; j < bin.length; j++) u8[j] = bin.charCodeAt(j);
    const geom = new THREE.STLLoader().parse(u8.buffer);
    geom.computeBoundingBox();
    const c = geom.boundingBox.getCenter(new THREE.Vector3()), r = geom.boundingBox.getSize(new THREE.Vector3()).length() / 2;
    const scene = new THREE.Scene();
    scene.add(new THREE.HemisphereLight(0xf4f7fb, 0x3a3f47, 0.95));
    const k = new THREE.DirectionalLight(0xffffff, 0.75); k.position.set(120, -160, 220); scene.add(k);
    const f = new THREE.DirectionalLight(0xdfe7ff, 0.45); f.position.set(-180, 140, -60); scene.add(f);
    scene.add(new THREE.Mesh(geom, new THREE.MeshStandardMaterial({ color: 0x9aa3ae, metalness: 0.1, roughness: 0.6, side: THREE.DoubleSide })));
    scene.add(new THREE.LineSegments(new THREE.EdgesGeometry(geom, 25), new THREE.LineBasicMaterial({ color: 0x14181f, transparent: true, opacity: 0.75 })));
    const cam = new THREE.PerspectiveCamera(26, ${W} / ${H}, 1, 5000);
    cam.up.set(0, 0, 1);
    const d = new THREE.Vector3(...p.eye).normalize();
    if (Math.abs(d.z) > 0.999) cam.up.set(0, 1, 0);
    cam.position.copy(c).addScaledVector(d, r / Math.sin(THREE.MathUtils.degToRad(13)) * 0.92);
    cam.lookAt(c);
    renderer.setViewport(i * ${W}, 0, ${W}, ${H}); renderer.setScissor(i * ${W}, 0, ${W}, ${H});
    renderer.render(scene, cam);
  });
  window.done = true;
  </script></body></html>`;
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: W * panels.length, height: H } });
  const errs = [];
  page.on('pageerror', e => errs.push(String(e)));
  await page.setContent(html, { waitUntil: 'networkidle' });
  await page.waitForFunction('window.done === true', null, { timeout: 30000 });
  await page.screenshot({ path: outPng });
  await browser.close();
  console.log(errs.length ? errs.join('\n') : 'wrote ' + outPng);
})();
