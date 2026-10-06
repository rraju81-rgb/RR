import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

const W = 1200, H = 900;
const D2R = Math.PI / 180;

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(W, H);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.82;
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.getElementById('wrap').prepend(renderer.domElement);
const pmrem = new THREE.PMREMGenerator(renderer);
const envTex = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

// ---------- materials ----------
const M = {
  orange: new THREE.MeshStandardMaterial({ color: 0xF26B1D, roughness: 0.52 }),
  char: new THREE.MeshStandardMaterial({ color: 0x30343C, roughness: 0.55 }),
  charDark: new THREE.MeshStandardMaterial({ color: 0x1B1E23, roughness: 0.6 }),
  metal: new THREE.MeshStandardMaterial({ color: 0xC9CDD2, roughness: 0.25, metalness: 0.9 }),
  tyre: new THREE.MeshStandardMaterial({ color: 0x15161A, roughness: 0.8 }),
  glass: new THREE.MeshStandardMaterial({ color: 0x1E2733, roughness: 0.15, metalness: 0.3 }),
  blister: new THREE.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.08, transparent: true, opacity: 0.22, clearcoat: 1, depthWrite: false }),
  cardBack: new THREE.MeshStandardMaterial({ color: 0xE9E6E0, roughness: 0.7 }),
  cardEdge: new THREE.MeshStandardMaterial({ color: 0xF4F2EE, roughness: 0.7 }),
  wall: new THREE.MeshStandardMaterial({ color: 0xE9E5DE, roughness: 0.95 }),
  floor: new THREE.MeshStandardMaterial({ color: 0xE9E5DE, roughness: 0.9 }),
  wood: new THREE.MeshStandardMaterial({ color: 0xC9A27A, roughness: 0.75 }),
  kraft: new THREE.MeshStandardMaterial({ color: 0xC49A6C, roughness: 0.9 }),
  kraftIn: new THREE.MeshStandardMaterial({ color: 0xD8B48A, roughness: 0.9 }),
  bed: new THREE.MeshStandardMaterial({ color: 0x23262B, roughness: 0.45, metalness: 0.2 }),
  ghost: new THREE.MeshStandardMaterial({ color: 0xF26B1D, roughness: 0.5, transparent: true, opacity: 0.28, depthWrite: false }),
};

function shade(m) { m.castShadow = true; m.receiveShadow = true; return m; }
function box(x0, x1, y0, y1, z0, z1, mat) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(x1 - x0, y1 - y0, z1 - z0), mat);
  m.position.set((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
  return shade(m);
}
function cyl(r, h, mat, axis = 'y', seg = 32) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, h, seg), mat);
  if (axis === 'x') m.rotation.z = Math.PI / 2;
  if (axis === 'z') m.rotation.x = Math.PI / 2;
  return shade(m);
}

// ---------- card art ----------
const CARDS = [
  { bg: '#C62828', bg2: '#8E1B1B', car: 0xE53935, name: 'NIGHT RACER', series: 'STREET SERIES', num: '1/10' },
  { bg: '#1565C0', bg2: '#0D3C7A', car: 0x29B6F6, name: 'BLUE COMET', series: 'TRACK STARS', num: '4/10' },
  { bg: '#2E7D32', bg2: '#1B4D1F', car: 0x9CCC65, name: 'GREEN MAMBA', series: 'MUSCLE MANIA', num: '7/10' },
  { bg: '#F9A825', bg2: '#B26A00', car: 0xFFD54F, name: 'SUN CHASER', series: 'DESERT RUN', num: '2/10' },
  { bg: '#6A1B9A', bg2: '#3E0F5C', car: 0xBA68C8, name: 'VIOLET VIPER', series: 'NEON NIGHTS', num: '9/10' },
  { bg: '#00838F', bg2: '#004D55', car: 0x26C6DA, name: 'TIDE RUNNER', series: 'COASTAL CRUISE', num: '5/10' },
  { bg: '#37474F', bg2: '#1C262B', car: 0xECEFF1, name: 'GHOST GT', series: 'STEALTH', num: '3/10' },
  { bg: '#EF6C00', bg2: '#A84300', car: 0xFFFFFF, name: 'APEX ONE', series: 'TRACK STARS', num: '8/10' },
  { bg: '#AD1457', bg2: '#6B0B35', car: 0xF8BBD0, name: 'ROSE RALLY', series: 'RALLY CUP', num: '6/10' },
  { bg: '#283593', bg2: '#151B57', car: 0xFFEB3B, name: 'VOLT', series: 'E-POWER', num: '10/10' },
  { bg: '#558B2F', bg2: '#2F5117', car: 0xFF7043, name: 'TRAIL KING', series: 'OFF ROAD', num: '2/5' },
  { bg: '#4E342E', bg2: '#2B1C18', car: 0xD7CCC8, name: 'CLASSIC 67', series: 'VINTAGE', num: '1/5' },
];
const texCache = {};
function cardTexture(i) {
  if (texCache[i]) return texCache[i];
  const o = CARDS[i % CARDS.length];
  const s = 5, cw = 108 * s, ch = 165 * s;
  const c = document.createElement('canvas'); c.width = cw; c.height = ch;
  const g = c.getContext('2d');
  const Y = (mm) => (165 - mm) * s; // card y (from bottom) -> canvas y
  const gr = g.createLinearGradient(0, 0, cw, ch); gr.addColorStop(0, o.bg); gr.addColorStop(1, o.bg2);
  g.fillStyle = gr; g.fillRect(0, 0, cw, ch);
  // speed stripes
  g.save(); g.globalAlpha = 0.16; g.fillStyle = '#fff';
  for (let k = -4; k < 12; k++) { g.beginPath(); const x = k * 70; g.moveTo(x, 0); g.lineTo(x + 26, 0); g.lineTo(x + 26 - 300, ch); g.lineTo(x - 300, ch); g.fill(); }
  g.restore();
  // hang tab hole area
  g.fillStyle = 'rgba(0,0,0,0.25)'; g.beginPath(); g.ellipse(cw / 2, Y(158), 40, 10, 0, 0, Math.PI * 2); g.fill();
  // badge
  g.fillStyle = '#fff'; g.beginPath(); g.roundRect(40, Y(148), cw - 80, 70, 14); g.fill();
  g.fillStyle = o.bg2; g.font = '900 46px Archivo'; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.fillText('DIE-CAST 1:64', cw / 2, Y(148) + 37);
  g.fillStyle = '#fff'; g.font = '700 30px Archivo'; g.fillText(o.series, cw / 2, Y(122));
  g.font = '800 26px Archivo'; g.fillText(o.num, cw / 2, Y(112));
  // big name near the top too
  g.font = '900 52px Archivo'; g.fillText(o.name, cw / 2, Y(96));
  // blister window panel
  g.fillStyle = 'rgba(255,255,255,0.88)'; g.beginPath(); g.roundRect(9 * s, Y(54), 90 * s, 42 * s, 18); g.fill();
  g.fillStyle = 'rgba(0,0,0,0.08)'; g.fillRect(9 * s, Y(22), 90 * s, 4 * s);
  // bottom name strip (stays visible on the racks)
  g.fillStyle = '#111'; g.fillRect(0, Y(13), cw, 11 * s);
  g.fillStyle = '#fff'; g.font = '900 36px Archivo'; g.textAlign = 'left';
  g.fillText(o.name, 14 * s, Y(7.5));
  g.textAlign = 'right'; g.fillStyle = o.bg; g.font = '800 26px Archivo'; g.fillText(o.num, cw - 6 * s, Y(7.5));
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  texCache[i] = t; return t;
}

function makeCar(color) {
  const g = new THREE.Group();
  const paint = new THREE.MeshPhysicalMaterial({ color, roughness: 0.28, metalness: 0.55, clearcoat: 1, clearcoatRoughness: 0.1 });
  const body = shade(new THREE.Mesh(new RoundedBoxGeometry(64, 9, 20, 3, 2.5), paint)); body.position.set(0, 9, 0); g.add(body);
  const nose = shade(new THREE.Mesh(new RoundedBoxGeometry(18, 5, 19, 3, 2), paint)); nose.position.set(25, 12.5, 0); g.add(nose);
  const cab = shade(new THREE.Mesh(new RoundedBoxGeometry(30, 8, 17, 3, 3), M.glass)); cab.position.set(-4, 16.5, 0); g.add(cab);
  const roof = shade(new THREE.Mesh(new RoundedBoxGeometry(20, 2, 16, 2, 1), paint)); roof.position.set(-6, 20.5, 0); g.add(roof);
  for (const x of [-20, 21]) for (const z of [-8.5, 8.5]) {
    const w = cyl(5.2, 4, M.tyre, 'z'); w.position.set(x, 5.2, z); g.add(w);
    const h = cyl(2.8, 4.4, M.metal, 'z'); h.position.set(x, 5.2, z); g.add(h);
  }
  return g;
}

// a carded car; local origin = bottom-left-back corner, card face toward +z, width w
function makeCard(i, w = 108) {
  const g = new THREE.Group();
  const front = new THREE.MeshStandardMaterial({ map: cardTexture(i), roughness: 0.55 });
  const mats = [M.cardEdge, M.cardEdge, M.cardEdge, M.cardEdge, front, M.cardBack];
  const plate = shade(new THREE.Mesh(new THREE.BoxGeometry(w, 165, 1.2), mats));
  plate.position.set(w / 2, 82.5, 0.6); g.add(plate);
  const car = makeCar(CARDS[i % CARDS.length].car); car.scale.setScalar(0.95); car.position.set(w / 2, 14.5, 12.5); g.add(car);
  const bl = new THREE.Mesh(new RoundedBoxGeometry(w - 22, 38, 24, 3, 3), M.blister);
  bl.position.set(w / 2, 34, 1.2 + 12); bl.renderOrder = 5; g.add(bl);
  return g;
}

// ---------- PITLANE wall racks (SWING / SLIDE) ----------
// local frame: wall at z=0, x along the wall (ledges extend +x), y up. side=-1 mirrors for the left-hand rack.
function wallRack(opt) {
  const { type = 'slide', side = 1, open = {}, lift = {}, cards = [0, 1, 2, 3, 4, 5], cardOff = {}, cardLift = {}, ghost = {} } = opt;
  const outer = new THREE.Group();
  const inner = new THREE.Group(); inner.scale.x = side; outer.add(inner);
  const yi = (i) => 20 + 55 * i, ci = (i) => 16 + 4.6 * i;
  const anchors = {};
  // spine / wall mount, 20 wide, 350 tall, stepped depth
  for (let i = 0; i < 6; i++) {
    const y0 = i === 0 ? 0 : yi(i), y1 = i === 5 ? 350 : yi(i + 1);
    inner.add(box(0, 20, y0, y1, 0, ci(i) + (type === 'slide' ? 4.8 : 2), M.char));
  }
  for (const [y, i] of [[10, 0], [185, 3], [340, 5]]) {
    const s = cyl(3.2, 1, M.metal, 'z'); s.position.set(10, y, ci(i) + (type === 'slide' ? 4.8 : 2) + 0.4); inner.add(s);
    const s2 = cyl(1.2, 1.2, M.charDark, 'z'); s2.position.set(10, y, ci(i) + (type === 'slide' ? 4.8 : 2) + 0.7); inner.add(s2);
  }
  for (let i = 0; i < 6; i++) {
    const y = yi(i), c = ci(i);
    if (type === 'slide') {
      inner.add(box(20, 156, y, y + 3, c - 3, c + 4.8, M.orange));
      inner.add(box(20, 156, y + 3, y + 22, c - 3, c, M.orange));
      inner.add(box(20, 48, y + 3, y + 22, c, c + 4.8, M.orange)); // end stop
      inner.add(box(48, 156, y + 3, y + 6, c + 1.8, c + 4.8, M.orange));
      inner.add(box(150, 156, y + 3, y + 11, c + 1.3, c + 4.8, M.orange));
      if (cards[i] != null) {
        const w = 105, x0 = 49 + (cardOff[i] || 0);
        const k = makeCard(cards[i], w); k.position.set(side === 1 ? x0 : x0 + w, y + 3, c); if (side === -1) k.scale.x = -1;
        inner.add(k);
      }
      anchors['row' + i] = new THREE.Vector3(156, y + 6, c + 4.8);
      anchors['stop' + i] = new THREE.Vector3(34, y + 22, c + 4.8);
    } else {
      // knuckle + pin on the wall mount
      const px = 27, pz = c + 9;
      inner.add(box(20, 33, y - 6, y, c - 1, c + 15, M.char));
      const pin = cyl(2.5, 21, M.char); pin.position.set(px, y + 4.5, pz); inner.add(pin);
      const L = new THREE.Group(); L.position.set(px, y + (lift[i] || 0), pz); L.rotation.y = -(open[i] || 0) * D2R; inner.add(L);
      const P = (x0, x1, y0, y1, z0, z1, mat = M.orange) => box(x0 - px, x1 - px, y0 - y, y1 - y, z0 - pz, z1 - pz, mat);
      L.add(P(23, 156, y, y + 3, c - 3, c + 4.8));
      L.add(P(23, 156, y + 3, y + 22, c - 3, c));
      L.add(P(34, 156, y + 3, y + 6, c + 1.8, c + 4.8));
      L.add(P(150, 156, y + 3, y + 11, c + 1.3, c + 4.8));
      L.add(P(23, 34, y + 3, y + 22, c, c + 4.8));
      L.add(P(23, 34, y, y + 3, c + 4.8, c + 10));
      const ring = cyl(5.1, 15, M.orange); ring.position.set(0, 7.5, 0); L.add(ring);
      const hole = cyl(2.75, 15.2, M.charDark); hole.position.set(0, 7.5, 0); L.add(hole);
      if (cards[i] != null) {
        const w = 105, x0 = 38 + (cardOff[i] || 0);
        const k = makeCard(cards[i], w);
        k.position.set((side === 1 ? x0 : x0 + w) - px, 3 + (cardLift[i] || 0), c - pz); if (side === -1) k.scale.x = -1;
        L.add(k);
      }
      if (ghost[i] != null) {
        const G = new THREE.Group(); G.position.set(px, y, pz); G.rotation.y = -ghost[i] * D2R; inner.add(G);
        G.add(box(23 - px, 156 - px, 0, 3, c - 3 - pz, c + 4.8 - pz, M.ghost));
        G.add(box(23 - px, 156 - px, 3, 22, c - 3 - pz, c - pz, M.ghost));
      }
      anchors['ring' + i] = new THREE.Vector3(px, y + 15 + (lift[i] || 0), pz);
      anchors['pin' + i] = new THREE.Vector3(px, y + 15, pz);
      anchors['tip' + i] = new THREE.Vector3(156, y + 11, c + 4.8);
      anchors['L' + i] = L;
    }
  }
  outer.userData.anchor = (name) => {
    const a = anchors[name].clone(); a.x *= side; return a;
  };
  outer.userData.side = side; outer.userData.anchors = anchors; outer.userData.inner = inner;
  return outer;
}

// ---------- SlideRack Fold (tabletop, kickstand) ----------
const FOLD = { 3: { h: 121, lean: 27.5 }, 5: { h: 176, lean: 25.0 }, 6: { h: 176, lean: 24.5 } };
function foldRack(opt) {
  const { n = 5, leg = 35, cards = null, cardOff = {}, upright = false } = opt;
  const { h, lean } = FOLD[n];
  const root = new THREE.Group();
  const R = new THREE.Group(); root.add(R);
  const yi = (i) => 55 * i, ci = (i) => 4 + 4.6 * i;
  const Ht = yi(n - 1) + 22;
  const A = {};
  for (let i = 0; i < n; i++) {
    const y = yi(i), c = ci(i), y1 = i === n - 1 ? Ht : yi(i + 1);
    R.add(box(0, 10, y, y1, 0, c + 4.8, M.char));                 // end wall
    R.add(box(10, 28, y, y + 22, c - 3, c + 4.8, M.char));        // stop block
    R.add(box(10, 136, y, y + 3, c - 3, c + 4.8, M.char));        // ledge
    R.add(box(28, 136, y + 3, y + 22, c - 3, c, M.char));         // back wall
    R.add(box(28, 136, y + 3, y + 6, c + 1.8, c + 4.8, M.char));  // front lip
    R.add(box(131, 136, y + 3, y + 10, c + 1.3, c + 4.8, M.char)); // corner post
    if (cards && cards[i] != null) {
      const k = makeCard(cards[i], 108); k.position.set(28 + (cardOff[i] || 0), y + 3, c); R.add(k);
    }
    A['open' + i] = new THREE.Vector3(136, y + 6, c + 4.8);
    A['stop' + i] = new THREE.Vector3(19, y + 22, c + 4.8);
    A['groove' + i] = new THREE.Vector3(100, y + 3, c + 1.5);
  }
  // hinge: rack barrel on the end wall + bracket
  R.add(box(0, 10, h - 7, h + 7, -6, 0, M.char));
  const rb = cyl(5, 10, M.char, 'x'); rb.position.set(5, h, -6); R.add(rb);
  const pin = cyl(2.5, 30, M.char, 'x'); pin.position.set(20, h, -6); R.add(pin);
  // leg
  const th = upright ? 0 : lean * D2R, thL = lean * D2R;
  const L = (h * Math.cos(thL) - 6 * Math.sin(thL)) / Math.cos((35 * D2R) - thL);
  const Lg = new THREE.Group(); Lg.position.set(0, h, -6); Lg.rotation.x = leg * D2R; R.add(Lg);
  const lb = cyl(6, 19, M.orange, 'x'); lb.position.set(20.6, 0, 0); Lg.add(lb);
  Lg.add(box(10.6, 90.6, -L, -3, -3, 3, M.orange));
  Lg.add(box(10.6, 30, -10, 0, -3, 4, M.orange));
  A.hinge = new THREE.Vector3(20, h, -6);
  A.legFoot = new THREE.Vector3(50, -L, -3); A.Lg = Lg; A.L = L; A.h = h; A.Ht = Ht;
  if (!upright) R.rotation.x = -th;
  root.userData = { A, R, lean, Ht, h };
  root.userData.world = (v, local = R) => { root.updateMatrixWorld(true); return local.localToWorld(v.clone()); };
  return root;
}

// ---------- scene / overlay helpers ----------
let scene, camera;
const ov = document.getElementById('ov');
const NS = 'http://www.w3.org/2000/svg';
function el(tag, attrs, parent = ov) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); parent.appendChild(e); return e; }
function proj(v) { const p = v.clone().project(camera); return [(p.x + 1) / 2 * W, (1 - p.y) / 2 * H]; }

function newScene(bg = 0xEEEBE6, fog = true) {
  scene = new THREE.Scene();
  scene.background = new THREE.Color(bg);
  scene.environment = envTex;
  if (fog) scene.fog = new THREE.Fog(bg, 1400, 3200);
  ov.innerHTML = '';
  const defs = el('defs', {});
  const mk = el('marker', { id: 'ah', viewBox: '0 0 10 10', refX: 7, refY: 5, markerWidth: 5, markerHeight: 5, orient: 'auto-start-reverse' }, defs);
  el('path', { d: 'M0,0 L10,5 L0,10 z', fill: '#F26B1D' }, mk);
  const mk2 = el('marker', { id: 'ahd', viewBox: '0 0 10 10', refX: 7, refY: 5, markerWidth: 6, markerHeight: 6, orient: 'auto-start-reverse' }, defs);
  el('path', { d: 'M0,0 L10,5 L0,10 z', fill: '#1F2329' }, mk2);
  const f = el('filter', { id: 'sh', x: '-20%', y: '-20%', width: '140%', height: '140%' }, defs);
  el('feDropShadow', { dx: 0, dy: 2, stdDeviation: 3, 'flood-opacity': 0.18 }, f);
}
function lights({ target = new THREE.Vector3(0, 0, 0), dir = [-0.5, 1, 0.8], size = 500, intensity = 2.4 } = {}) {
  scene.add(new THREE.HemisphereLight(0xffffff, 0xd9d2c8, 0.5));
  const d = new THREE.DirectionalLight(0xffffff, intensity);
  const v = new THREE.Vector3(...dir).normalize().multiplyScalar(1500);
  d.position.copy(target).add(v); d.target.position.copy(target);
  d.castShadow = true; d.shadow.mapSize.set(4096, 4096);
  const sc = d.shadow.camera; sc.left = -size; sc.right = size; sc.top = size; sc.bottom = -size; sc.near = 100; sc.far = 4000;
  d.shadow.bias = -0.0004; d.shadow.normalBias = 0.6; d.shadow.radius = 6;
  scene.add(d); scene.add(d.target);
  const fill = new THREE.DirectionalLight(0xfff4e8, 0.6); fill.position.set(target.x + 900, target.y + 300, target.z + 600); scene.add(fill);
}
function cam(pos, target, fov = 26) {
  camera = new THREE.PerspectiveCamera(fov, W / H, 10, 6000);
  camera.position.set(...pos); camera.lookAt(new THREE.Vector3(...target));
  camera.updateMatrixWorld(); camera.updateProjectionMatrix();
}
function floor(y = 0, mat = M.floor) { const p = new THREE.Mesh(new THREE.PlaneGeometry(8000, 8000), mat); p.rotation.x = -Math.PI / 2; p.position.y = y; p.receiveShadow = true; scene.add(p); return p; }
function wall(z = 0, mat = M.wall) { const p = new THREE.Mesh(new THREE.PlaneGeometry(8000, 8000), mat); p.position.z = z - 0.05; p.receiveShadow = true; scene.add(p); return p; }

// overlay primitives
function header(kicker, title) {
  const g = el('g', { class: 't' });
  el('rect', { x: 40, y: 36, width: 8, height: 64, fill: '#F26B1D' }, g);
  el('text', { x: 62, y: 58, 'font-size': 17, 'font-weight': 700, fill: '#F26B1D', 'letter-spacing': 2.5 }, g).textContent = kicker.toUpperCase();
  el('text', { x: 62, y: 94, 'font-size': 34, 'font-weight': 900, fill: '#1F2329' }, g).textContent = title;
}
function callout(p3, n, title, sub, dx, dy) {
  const [x, y] = proj(p3);
  const lx = x + dx, ly = y + dy;
  const g = el('g', { class: 't' });
  el('line', { x1: x, y1: y, x2: lx, y2: ly, stroke: '#1F2329', 'stroke-width': 1.6 }, g);
  el('circle', { cx: x, cy: y, r: 6, fill: '#F26B1D', stroke: '#fff', 'stroke-width': 2.5 }, g);
  const lines = sub ? sub.split('\n') : [];
  const tw = Math.max(title.length * 10.6, ...lines.map((l) => l.length * 8.1)) + 62;
  const th = 40 + lines.length * 21;
  let bx = dx >= 0 ? lx : lx - tw, by = ly - 22;
  bx = Math.max(24, Math.min(W - 24 - tw, bx)); by = Math.max(120, Math.min(H - 24 - th, by));
  el('rect', { x: bx, y: by, width: tw, height: th, rx: 10, fill: '#fff', filter: 'url(#sh)' }, g);
  if (n != null) {
    el('circle', { cx: bx + 22, cy: by + 21, r: 13, fill: '#F26B1D' }, g);
    el('text', { x: bx + 22, y: by + 27, 'font-size': 16, 'font-weight': 800, fill: '#fff', 'text-anchor': 'middle' }, g).textContent = n;
  }
  const tx = bx + (n != null ? 44 : 16);
  el('text', { x: tx, y: by + 27, 'font-size': 18, 'font-weight': 800, fill: '#1F2329' }, g).textContent = title;
  lines.forEach((l, k) => { el('text', { x: tx, y: by + 50 + k * 21, 'font-size': 14.5, 'font-weight': 500, fill: '#4A505A' }, g).textContent = l; });
}
function arrow3(a, b, color = '#F26B1D', w = 5) {
  const [x1, y1] = proj(a), [x2, y2] = proj(b);
  el('line', { x1, y1, x2, y2, stroke: color, 'stroke-width': w, 'stroke-linecap': 'round', 'marker-end': color === '#F26B1D' ? 'url(#ah)' : 'url(#ahd)' });
}
function arcPts(center, u, v, r, a0, a1, n = 40) {
  const pts = [];
  for (let k = 0; k <= n; k++) { const a = (a0 + (a1 - a0) * k / n) * D2R; pts.push(center.clone().addScaledVector(u, r * Math.cos(a)).addScaledVector(v, r * Math.sin(a))); }
  return pts;
}
function poly3(pts, color = '#F26B1D', w = 5, arrowEnd = true, dash = null) {
  const d = pts.map((p, k) => { const [x, y] = proj(p); return (k ? 'L' : 'M') + x.toFixed(1) + ',' + y.toFixed(1); }).join(' ');
  const a = { d, fill: 'none', stroke: color, 'stroke-width': w, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' };
  if (arrowEnd) a['marker-end'] = 'url(#ah)';
  if (dash) a['stroke-dasharray'] = dash;
  el('path', a);
}
function tag(p3, text, dx = 0, dy = 0, opts = {}) {
  const [x, y] = proj(p3);
  const g = el('g', { class: 't' });
  const w = text.length * (opts.size ? opts.size * 0.62 : 10.4) + 24;
  el('rect', { x: x + dx - w / 2, y: y + dy - 17, width: w, height: 32, rx: 16, fill: opts.fill || '#1F2329' }, g);
  el('text', { x: x + dx, y: y + dy + 5, 'font-size': opts.size || 16, 'font-weight': 800, fill: opts.color || '#fff', 'text-anchor': 'middle' }, g).textContent = text;
}
function dim(a, b, text, off = [0, 0], color = '#1F2329') {
  const [x1, y1] = proj(a), [x2, y2] = proj(b);
  const g = el('g', { class: 't' });
  el('line', { x1, y1, x2, y2, stroke: color, 'stroke-width': 2, 'marker-start': 'url(#ahd)', 'marker-end': 'url(#ahd)' }, g);
  const mx = (x1 + x2) / 2 + off[0], my = (y1 + y2) / 2 + off[1];
  const w = text.length * 9.6 + 20;
  el('rect', { x: mx - w / 2, y: my - 14, width: w, height: 26, rx: 6, fill: '#fff', stroke: color, 'stroke-width': 1.2 }, g);
  el('text', { x: mx, y: my + 5, 'font-size': 15, 'font-weight': 800, fill: color, 'text-anchor': 'middle' }, g).textContent = text;
}
function stepBadges(items) { // bottom strip with numbered steps
  const g = el('g', { class: 't' });
  const n = items.length, bw = (W - 80 - (n - 1) * 14) / n;
  items.forEach((t, k) => {
    const x = 40 + k * (bw + 14), y = H - 74;
    el('rect', { x, y, width: bw, height: 44, rx: 22, fill: '#1F2329' }, g);
    el('circle', { cx: x + 22, cy: y + 22, r: 14, fill: '#F26B1D' }, g);
    el('text', { x: x + 22, y: y + 28, 'font-size': 16, 'font-weight': 900, fill: '#fff', 'text-anchor': 'middle' }, g).textContent = k + 1;
    el('text', { x: x + 46, y: y + 28, 'font-size': 16, 'font-weight': 700, fill: '#fff' }, g).textContent = t;
  });
}

// ---------- shots ----------
const V = (x, y, z) => new THREE.Vector3(x, y, z);
const SHOTS = {};

// ===== GARAGE (SWING) =====
SHOTS.swing_hero = () => {
  newScene(); wall();
  const r = wallRack({ type: 'swing' }); scene.add(r);
  lights({ target: V(80, 200, 0), dir: [-0.6, 0.9, 1], size: 400 });
  cam([700, 360, 1250], [110, 235, 30], 27);
  return () => {
    header('PITLANE GARAGE · swing-out wall rack', '6 cars, 6 doors, one 35 cm rail');
    callout(V(180, 397, 36), 1, 'Every card on show', 'rows step 4.6 mm forward,\nso each name stays readable', 120, -40);
    callout(r.userData.anchor('ring3'), 2, 'Own door per card', 'each ledge swings on its own pin', -250, -110);
    callout(V(10, 20, 26), 3, 'One-piece wall mount', 'pins built in · 3 screws', -260, 60);
  };
};
SHOTS.swing_open = () => {
  newScene(); wall();
  const r = wallRack({ type: 'swing', open: { 2: 80 }, cardLift: { 2: 70 }, ghost: { 2: 0 } }); scene.add(r);
  lights({ target: V(80, 200, 0), dir: [-0.5, 0.9, 1], size: 450 });
  cam([-560, 470, 980], [60, 250, 80], 28);
  return () => {
    header('How it works · GARAGE', 'Swing out, swap the card, swing shut');
    const c = r.userData.anchor('pin2');
    const y = 20 + 55 * 2 + 14;
    poly3(arcPts(V(27, y, 34.2), V(1, 0, 0), V(0, 0, 1), 112, 8, 76), '#F26B1D', 5);
    const L = r.userData.anchors.L2; L.updateMatrixWorld(true);
    const top = L.localToWorld(V(60, 260, -2)), lo = L.localToWorld(V(60, 205, -2));
    arrow3(lo, top);
    callout(V(27, y - 2, 34), 1, 'Swing out', 'opens to 135°, closed has a stop', -260, 140);
    callout(L.localToWorld(V(50, 245, 0)), 2, 'Lift the card out', 'drop the next one in', -300, -60);
    callout(V(130, 20 + 55 * 4 + 10, 40), 3, 'Others stay put', 'no unhooking the cards in front', 140, -60);
    stepBadges(['Swing the door out', 'Swap the card', 'Swing it shut']);
  };
};
SHOTS.swing_lift = () => {
  newScene(); wall();
  const r = wallRack({ type: 'swing', open: { 3: 60 }, lift: { 3: 45 }, cards: [0, 1, 2, null, 4, 5] }); scene.add(r);
  lights({ target: V(80, 200, 0), dir: [-0.5, 0.9, 1], size: 450 });
  cam([600, 440, 780], [70, 245, 40], 30);
  return () => {
    header('Easy care · GARAGE', 'Every ledge lifts off its pin');
    const p = r.userData.anchor('pin3');
    const ring = r.userData.anchor('ring3');
    arrow3(V(p.x, p.y + 32, p.z), V(p.x, p.y + 64, p.z));
    callout(V(p.x, p.y - 1, p.z), 1, 'Ø5 pin, built into the mount', 'chamfered root for strength', -300, 90);
    callout(V(ring.x, ring.y - 8, ring.z + 5), 2, 'Lift 15.5 mm to remove', 'clean, recolour or replace a ledge', 60, -150);
    callout(V(150, 20 + 55 * 1 + 10, 33), 3, 'Spare ledges available', '₹99 each or 3 for ₹249', 80, 70);
  };
};
SHOTS.swing_twin = () => {
  newScene(); wall();
  const R1 = wallRack({ type: 'swing', side: 1, cards: [0, 1, 2, 3, 4, 5], open: { 4: 70 } }); scene.add(R1);
  const R2 = wallRack({ type: 'swing', side: -1, cards: [6, 7, 8, 9, 10, 11], open: { 1: 70 } }); R2.position.y = -27.5; scene.add(R2);
  lights({ target: V(0, 200, 0), dir: [-0.4, 0.9, 1], size: 500 });
  cam([280, 260, 1350], [0, 210, 40], 27);
  return () => {
    header('GARAGE TWIN · right + left', 'A 12-car centrepiece for your wall');
    callout(V(0, 350, 30), 1, 'Mirrored pair, spines together', 'left rack hangs 27.5 mm lower', 140, -50);
    callout(V(-120, 20 + 55 * 1 - 27.5 + 15, 140), 2, 'Shelves alternate', 'opening one side never\ntouches the other', -230, 170);
    callout(V(150, 20 + 55 * 4 + 15, 130), 3, '12 cards, every name visible', '', 120, 130);
  };
};

// ===== GRID (SLIDE) =====
SHOTS.slide_hero = () => {
  newScene(); wall();
  const r = wallRack({ type: 'slide', cards: [6, 7, 0, 1, 2, 3] }); scene.add(r);
  lights({ target: V(80, 200, 0), dir: [-0.6, 0.9, 1], size: 400 });
  cam([700, 360, 1250], [110, 235, 30], 27);
  return () => {
    header('PITLANE GRID · slide-in wall rack', 'One piece. No moving parts.');
    callout(V(156, 20 + 55 * 3 + 8, 35), 1, 'Its own lane for every card', 'open end on the right (or left)', 120, -60);
    callout(V(20, 20 + 55 * 5 + 22, 41), 2, 'Solid end stop', 'every card lines up exactly', -270, -10);
    callout(V(156, 26, 22), 3, 'Lowest cost per car', '6 cards from ₹799 · ₹133 per car', 90, 60);
  };
};
SHOTS.slide_load = () => {
  newScene(); wall();
  const r = wallRack({ type: 'slide', cards: [6, 7, 0, 1, 2, 3], cardOff: { 3: 75 } }); scene.add(r);
  lights({ target: V(120, 200, 0), dir: [-0.6, 0.9, 1], size: 450 });
  cam([480, 420, 1150], [150, 255, 40], 30);
  return () => {
    header('How it works · GRID', 'Slide in from the side until it stops');
    const y = 20 + 55 * 3 + 30, c = 16 + 4.6 * 3 + 30;
    arrow3(V(330, y, c), V(240, y, c));
    callout(V(156, 20 + 55 * 3 + 4, 32), 1, '1.8 mm slot holds the card', 'a low lip keeps it from tipping', 120, 120);
    callout(V(34, 20 + 55 * 3 + 22, 33), 2, 'Stops at the end block', 'no fiddling to line it up', -300, -60);
    callout(V(300, 20 + 55 * 5 + 40, 30), 3, 'Leave ~11 cm free wall', 'on the open side for loading', 40, -120);
    stepBadges(['Hang it with 3 screws', 'Slide the card in', 'Slide it out the same way']);
  };
};
SHOTS.slide_profile = () => {
  newScene(); wall();
  const r = wallRack({ type: 'slide', cards: [6, 7, 0, 1, 2, 3] }); scene.add(r);
  lights({ target: V(80, 200, 0), dir: [0.9, 0.7, 0.6], size: 450 });
  cam([860, 300, 600], [90, 230, 40], 30);
  return () => {
    header('Why it shows better · GRID', 'Stepped rows, every name readable');
    dim(V(156, 20 + 55 * 1 + 12, 16 + 4.6 * 1 + 4.8), V(156, 20 + 55 * 2 + 12, 16 + 4.6 * 2 + 4.8), '55 mm', [64, 0]);
    callout(V(156, 20 + 55 * 4 + 6, 16 + 4.6 * 4 + 4.8), 1, 'Each row steps 4.6 mm out', 'like roof tiles: car + name in view', 80, -90);
    callout(V(130, 20 + 55 * 0 + 8, 30), 2, 'Name strip stays clear', 'low front lip, chamfered posts', 80, 60);
  };
};
SHOTS.slide_twin = () => {
  newScene(); wall();
  const R1 = wallRack({ type: 'slide', side: 1, cards: [0, 1, 2, 3, 4, 5] }); scene.add(R1);
  const R2 = wallRack({ type: 'slide', side: -1, cards: [6, 7, 8, 9, 10, 11], cardOff: { 2: 60 } }); R2.position.y = -27.5; scene.add(R2);
  lights({ target: V(0, 200, 0), dir: [-0.4, 0.9, 1], size: 500 });
  cam([-260, 260, 1350], [0, 205, 40], 27);
  return () => {
    header('GRID TWIN · right + left', '12 cards, loads from both sides');
    callout(V(-215, 20 + 55 * 2 - 27.5 + 40, 30), 1, 'Left rack loads from the left', '', -90, -230);
    callout(V(200, 20 + 55 * 3 + 40, 30), 2, 'Right rack loads from the right', '', 40, -270);
    callout(V(0, 160, 30), 3, 'Twin for ₹1,449', 'vs ₹1,598 bought singly', 160, 290);
  };
};

// ===== PODIUM (Fold) =====
function placeFold(n, x, z, cards, opts = {}) { const f = foldRack({ n, cards, ...opts }); f.position.set(x, 0, z); scene.add(f); return f; }
SHOTS.fold_family = () => {
  newScene(0xEEEBE6); floor();
  const a = placeFold(3, -230, 0, [0, 1, 2]);
  const b = placeFold(5, -40, 0, [3, 4, 5, 6, 7]);
  const c = placeFold(6, 150, 0, [8, 9, 10, 11, 0, 1]);
  lights({ target: V(0, 100, 0), dir: [-0.5, 1, 0.9], size: 500 });
  cam([520, 420, 1250], [10, 150, 0], 28);
  return () => {
    header('PITLANE PODIUM · tabletop', 'Three sizes: 3, 5 and 6 cards');
    tag(V(-162, 0, 60), 'PODIUM 3 · ₹499', 0, 34);
    tag(V(28, 0, 60), 'PODIUM 5 · ₹649', 0, 34);
    tag(V(218, 0, 60), 'PODIUM 6 · ₹749', 0, 34);
  };
};
SHOTS.fold_stand = () => {
  newScene(); floor();
  const f = placeFold(5, 0, 0, [3, 4, 5, 6, 7]);
  lights({ target: V(60, 100, 0), dir: [0.6, 1, -0.2], size: 400 });
  cam([-860, 360, -1020], [40, 175, -40], 26);
  return () => {
    header('How it works · PODIUM', 'Flip the leg. It stops at 35°.');
    const { A, R } = f.userData; f.updateMatrixWorld(true);
    const hw = R.localToWorld(A.hinge.clone());
    // arc in the rack's y-z plane around the hinge
    const pts = [];
    for (let k = 0; k <= 40; k++) { const a = (35 * k / 40) * D2R; pts.push(R.localToWorld(V(95, A.h - 120 * Math.cos(a), -6 - 120 * Math.sin(a)))); }
    poly3(pts, '#F26B1D', 5);
    callout(hw, 1, 'Print-in-place hinge', 'no screws, glue or loose pins', -60, -150);
    callout(R.localToWorld(V(50, A.h - A.L + 30, -6)), 2, 'Hard stop at 35°', 'rack leans back 25° · stable', -320, 60);
    callout(R.localToWorld(V(100, 55 * 4 + 20, 18)), 3, 'Open frame, no back panel', 'the whole card stays on show', 120, -60);
  };
};
SHOTS.fold_load = () => {
  newScene(); floor();
  const f = placeFold(5, 0, 0, [3, 4, null, 6, 7]);
  const g = placeFold(5, 0, 0, null); scene.remove(g);
  // card being slid in at row 2
  const { R } = f.userData;
  const k = makeCard(5, 108); k.position.set(28 + 95, 55 * 2 + 3, 4 + 4.6 * 2); R.add(k);
  lights({ target: V(60, 100, 0), dir: [-0.5, 1, 0.9], size: 450 });
  cam([540, 330, 820], [110, 150, 0], 28);
  return () => {
    header('How it works · PODIUM', 'Swap a car in three seconds');
    f.updateMatrixWorld(true);
    const a = R.localToWorld(V(330, 55 * 2 + 70, 40)), b = R.localToWorld(V(250, 55 * 2 + 70, 40));
    arrow3(a, b);
    callout(R.localToWorld(V(19, 55 * 2 + 22, 18)), 1, 'Slides to a fixed stop', 'fits 108 × 165 mm 1:64 cards', -300, -70);
    callout(R.localToWorld(V(136, 55 * 1 + 6, 13)), 2, 'Never pick the stand up', 'cards go in and out from the side', 60, 140);
    stepBadges(['Open the stand', 'Slide the cards in', 'Fold it away']);
  };
};
SHOTS.fold_flat = () => {
  newScene(); floor();
  // 5-card rack folded, lying on its back, half inside a slim sleeve box
  const f = foldRack({ n: 5, leg: 0, upright: true });
  f.rotation.x = -Math.PI / 2; // back (z<0) faces down
  f.position.set(0, 9.5, 0); scene.add(f);
  // after rotation: rack y -> -z (length runs toward -z), z -> +y (thickness up)
  // sleeve box: inner 146 wide, 46 high, 260 long, from z=-90 to z=-350
  const z0 = -110, z1 = -370, bw = 152, bh = 48;
  scene.add(box(-8, bw - 8, 0, 2, z1, z0, M.kraft));
  scene.add(box(-8, bw - 8, bh, bh + 2, z1, z0, M.kraft));
  scene.add(box(-10, -8, 0, bh + 2, z1, z0, M.kraft));
  scene.add(box(bw - 8, bw - 6, 0, bh + 2, z1, z0, M.kraft));
  scene.add(box(-10, bw - 6, 0, bh + 2, z1 - 2, z1, M.kraft));
  // box label stripe
  scene.add(box(20, bw - 36, bh + 2, bh + 2.4, z1 + 40, z1 + 90, M.orange));
  // a loose standing PODIUM 3 for scale
  const s = foldRack({ n: 3, leg: 35, cards: [0, 1, 2] }); s.position.set(330, 0, -480); s.rotation.y = -0.3; scene.add(s);
  lights({ target: V(80, 0, -150), dir: [-0.4, 1, 0.6], size: 500 });
  cam([560, 620, 560], [20, 40, -120], 30);
  return () => {
    header('Store it · ship it · gift it', 'Folds flat to 31–45 mm');
    arrow3(V(70, 70, 150), V(70, 70, 20));
    dim(V(-30, 0, 30), V(-30, 40, 30), '40 mm', [-52, 0]);
    callout(V(70, 49, -250), 1, 'Fits a slim gift box', 'cheapest courier slab, no instructions', -80, -130);
    callout(V(60, 1, 40), 2, 'Leg folds flat against the back', 'for a drawer, shelf or the post', 80, 70);
  };
};
SHOTS.fold_print = () => {
  newScene(0xE6E8EB); floor(0, new THREE.MeshStandardMaterial({ color: 0xE6E8EB, roughness: 0.9 }));
  // printer bed
  scene.add(box(-130, 130, 0, 8, -130, 130, M.bed));
  scene.add(box(-130, 130, 8, 8.4, -130, -126, M.orange));
  const f = foldRack({ n: 5, leg: 0, upright: true });
  f.rotation.z = Math.PI / 2; // x -> y : end wall on the bed
  f.position.set(121, 8, -10); scene.add(f);
  // nozzle / hot-end hint
  lights({ target: V(0, 80, 0), dir: [-0.5, 1, 0.8], size: 400 });
  cam([620, 420, 700], [0, 100, 0], 30);
  return () => {
    header('Made to be made · PODIUM', 'One print. Nothing to assemble.');
    callout(V(0, 8, 70), 1, 'Prints as it lies', 'end wall on the bed · no supports', -330, 60);
    callout(V(-20, 130, 0), 2, 'Hinge prints already working', '0.6–0.8 mm gaps, 45° cones', -330, -150);
    callout(V(-90, 136, 30), 3, 'Same design, more ledges', '3, 5 or 6 cards · one job per size', 340, -260);
  };
};

// cover / range shot: everything together
SHOTS.range = () => {
  newScene(); wall(); floor(0, M.floor);
  const R1 = wallRack({ type: 'swing', side: 1, cards: [0, 1, 2, 3, 4, 5], open: { 4: 55 } }); R1.position.set(40, 420, 0); scene.add(R1);
  const R2 = wallRack({ type: 'swing', side: -1, cards: [6, 7, 8, 9, 10, 11] }); R2.position.set(40, 392.5, 0); scene.add(R2);
  const S1 = wallRack({ type: 'slide', side: 1, cards: [7, 6, 9, 1, 3, 0] }); S1.position.set(330, 420, 0); scene.add(S1);
  // shelf/desk
  scene.add(box(-260, 600, 0, 360, 0, 260, M.wood));
  const f1 = foldRack({ n: 5, cards: [1, 2, 3, 4, 5] }); f1.position.set(-220, 360, 120); f1.rotation.y = 0.25; scene.add(f1);
  const f2 = foldRack({ n: 3, cards: [8, 9, 10] }); f2.position.set(330, 360, 120); f2.rotation.y = -0.2; scene.add(f2);
  lights({ target: V(100, 500, 60), dir: [-0.5, 1, 0.9], size: 700 });
  cam([300, 700, 2100], [120, 560, 40], 27);
  return () => {};
};

window.SHOTS = Object.keys(SHOTS);
window.renderShot = async (name, annotate = true) => {
  await document.fonts.load('900 20px Archivo'); await document.fonts.load('500 20px Archivo'); await document.fonts.ready;
  for (const k in texCache) delete texCache[k];
  const post = SHOTS[name]();
  scene.traverse((o) => { if (o.material) for (const m of [].concat(o.material)) m.envMapIntensity = 0.45; });
  renderer.render(scene, camera);
  if (annotate) post();
  return true;
};
window.ready = true;
