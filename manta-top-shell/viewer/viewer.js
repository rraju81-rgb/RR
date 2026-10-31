// MANTA top shell viewer (three.js). Loads ../exports/<variant>/manta_<variant>.glb
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

// exports/ sits next to viewer/ in the repo, or next to the page when hosted flat
const EXPORT_BASES = ['../exports', './exports'];
let exportBase = null;
async function findExportBase() {
  for (const b of EXPORT_BASES) {
    try { const r = await fetch(`${b}/lmdh/report.json`); if (r.ok) return b; } catch { /* try next */ }
  }
  return EXPORT_BASES[0];
}

const params = new URLSearchParams(location.search);
const state = {
  variant: params.get('variant') || 'lmdh',
  look: params.get('look') || 'livery',
  view: params.get('view') || 'hero',
  appendages: params.get('appendages') !== '0',
  context: params.get('context') !== '0',
  stand: params.get('stand') === '1',
  bg: params.get('bg') || 'studio',
  shot: params.get('shot') === '1',
};
if (state.stand) { state.context = false; state.appendages = false; }
if (state.shot && params.get('ui') !== '1') document.body.classList.add('shot');

const VARIANTS = { lmdh: 'LMDh', lmh: 'LMH' };
const LOOKS = { livery: 'Manta livery', clay: 'Clay study', carbon: 'Raw carbon' };
const VIEWS = { hero: '3/4 front', rear: '3/4 rear', front: 'Front', side: 'Side', top: 'Top', back: 'Rear', low: 'Low front' };
const GROUND_Y = -0.052; // ground plane in glTF metres (ride height under the reference plane)

const W = +params.get('w') || window.innerWidth;
const H = +params.get('h') || window.innerHeight;
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(state.shot ? 1 : Math.min(window.devicePixelRatio, 2));
renderer.setSize(W, H);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
document.getElementById('app').appendChild(renderer.domElement);

const scene = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.03).texture;

const camera = new THREE.PerspectiveCamera(28, W / H, 0.05, 200);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

// lights
const hemi = new THREE.HemisphereLight(0xdfe9f3, 0x1b1f24, 0.55);
scene.add(hemi);
const key = new THREE.DirectionalLight(0xffffff, 2.2);
key.position.set(4.5, 8.0, 5.5);
key.castShadow = true;
key.shadow.mapSize.set(state.shot ? 4096 : 2048, state.shot ? 4096 : 2048);
key.shadow.camera.left = -6; key.shadow.camera.right = 6;
key.shadow.camera.top = 6; key.shadow.camera.bottom = -6;
key.shadow.camera.near = 0.5; key.shadow.camera.far = 30;
key.shadow.bias = -0.0002;
key.shadow.normalBias = 0.02;
key.shadow.radius = 4;
scene.add(key);
scene.add(key.target);
const rim = new THREE.DirectionalLight(0xbcd7ff, 0.9);
rim.position.set(-6, 3, -7);
scene.add(rim);

// ground + backdrop
const groundMat = new THREE.MeshStandardMaterial({ color: 0xd9dde2, roughness: 0.92, metalness: 0 });
const ground = new THREE.Mesh(new THREE.CircleGeometry(40, 96), groundMat);
ground.rotation.x = -Math.PI / 2;
ground.position.y = GROUND_Y;
ground.receiveShadow = true;
scene.add(ground);

function setBackground() {
  if (state.bg === 'white') { scene.background = new THREE.Color(0xffffff); return; }
  const dark = state.bg === 'dark' || state.stand;
  const c = document.createElement('canvas');
  c.width = 4; c.height = 256;
  const g = c.getContext('2d');
  const grad = g.createLinearGradient(0, 0, 0, 256);
  if (dark) { grad.addColorStop(0, '#2a3037'); grad.addColorStop(1, '#0b0d10'); }
  else { grad.addColorStop(0, '#f4f6f8'); grad.addColorStop(1, '#c9ced4'); }
  g.fillStyle = grad; g.fillRect(0, 0, 4, 256);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  scene.background = tex;
  groundMat.color.set(dark ? 0x15181c : 0xd3d8de);
  hemi.intensity = dark ? 0.35 : 0.55;
}

// display stand (sculpture mode): gallery plinth, black base, post into the shell
const STAND_LIFT = 0.42; // shell raised above the ground [m]
const stand = new THREE.Group();
{
  const black = new THREE.MeshPhysicalMaterial({ color: 0x0b0c0e, roughness: 0.28, metalness: 0.3, clearcoat: 0.8 });
  const plinthMat = new THREE.MeshStandardMaterial({ color: 0x26292e, roughness: 0.85 });
  const plinth = new THREE.Mesh(new THREE.BoxGeometry(2.7, 0.16, 6.4), plinthMat);
  plinth.position.set(0, GROUND_Y + 0.08, -1.55);
  const base = new THREE.Mesh(new THREE.BoxGeometry(1.25, 0.07, 1.9), black);
  base.position.set(0, GROUND_Y + 0.16 + 0.035, -1.55);
  const postH = STAND_LIFT + 0.86 - 0.23;
  const post = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.06, postH, 40), black);
  post.position.set(0, GROUND_Y + 0.23 + postH / 2, -1.55);
  for (const o of [plinth, base, post]) { o.castShadow = true; o.receiveShadow = true; stand.add(o); }
}
scene.add(stand);

// materials for the finishes
function makeLooks() {
  const paint = {
    livery: new THREE.MeshPhysicalMaterial({ color: 0x0f2436, metalness: 0.45, roughness: 0.3, clearcoat: 1, clearcoatRoughness: 0.05 }),
    clay: new THREE.MeshPhysicalMaterial({ color: 0x8f969e, metalness: 0.0, roughness: 0.5, clearcoat: 0.3 }),
    carbon: new THREE.MeshPhysicalMaterial({ color: 0x1a1c1f, metalness: 0.25, roughness: 0.38, clearcoat: 1, clearcoatRoughness: 0.08 }),
  };
  const marking = {
    livery: new THREE.MeshPhysicalMaterial({ color: 0xe6ebf0, metalness: 0.1, roughness: 0.3, clearcoat: 1, clearcoatRoughness: 0.05 }),
    clay: paint.clay, carbon: paint.carbon,
  };
  const glass = new THREE.MeshPhysicalMaterial({ color: 0x050608, metalness: 0.6, roughness: 0.06, clearcoat: 1, clearcoatRoughness: 0.02, side: THREE.DoubleSide });
  const dark = new THREE.MeshPhysicalMaterial({ color: 0x141518, metalness: 0.25, roughness: 0.4, clearcoat: 0.7, side: THREE.DoubleSide });
  const edge = new THREE.MeshStandardMaterial({ color: 0x0b0c0e, roughness: 0.7, side: THREE.DoubleSide });
  const head = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xe9f4ff, emissiveIntensity: 2.6 });
  const tail = new THREE.MeshStandardMaterial({ color: 0x400000, emissive: 0xff1a10, emissiveIntensity: 2.6 });
  const interior = new THREE.MeshStandardMaterial({ color: 0x15171b, roughness: 0.7, metalness: 0.2, side: THREE.BackSide });
  return { paint, marking, glass, dark, edge, head, tail, interior };
}
const L = makeLooks();

function materialFor(name, look) {
  switch (name) {
    case 'paint': return look === 'carbon' ? L.paint.carbon : L.paint[look];
    case 'marking': return L.marking[look];
    case 'glass': return L.glass;
    case 'carbon': return look === 'clay' ? L.paint.clay : L.dark;
    case 'edge': return look === 'clay' ? L.paint.clay : L.edge;
    case 'headlight': return look === 'clay' ? L.paint.clay : L.head;
    case 'taillight': return look === 'clay' ? L.paint.clay : L.tail;
    default: return null; // keep GLB material (context)
  }
}

const loader = new GLTFLoader();
const cache = {};
let current = null;
let report = null;

async function loadVariant(v) {
  if (cache[v]) return cache[v];
  exportBase ??= await findExportBase();
  return new Promise((resolve, reject) => {
    loader.load(`${exportBase}/${v}/manta_${v}.glb`, (gltf) => {
      const root = gltf.scene;
      const inside = [];
      root.traverse((o) => {
        if (o.isMesh) {
          o.castShadow = true;
          o.receiveShadow = ['floor', 'tyre', 'rim'].includes(o.material.name);
          o.userData.matName = o.material.name;
          let p = o; while (p && p.name !== 'top_shell_skin') p = p.parent;
          if (p) inside.push(o);
          if (o.material.name === 'tyre' || o.material.name === 'rim' || o.material.name === 'floor') o.material.side = THREE.DoubleSide;
        }
      });
      // raw-carbon interior of the shell (visible from below / behind)
      for (const o of inside) {
        const back = new THREE.Mesh(o.geometry, L.interior);
        back.userData.matName = '__interior';
        o.add(back);
      }
      cache[v] = root;
      resolve(root);
    }, undefined, reject);
  });
}

async function loadReport(v) {
  try { const r = await fetch(`${exportBase}/${v}/report.json`); return r.ok ? await r.json() : null; } catch { return null; }
}

function applyState() {
  if (!current) return;
  current.traverse((o) => {
    if (o.isMesh) {
      const m = materialFor(o.userData.matName, state.look);
      if (m) o.material = m;
    }
  });
  const show = { top_shell_skin: true, dorsal_fin: true, rear_wing: state.appendages, endplates: state.appendages,
                 mirrors: state.appendages, context: state.context };
  for (const child of current.children) child.visible = show[child.name] ?? true;
  stand.visible = state.stand;
  ground.visible = params.get('ground') !== '0';
  current.position.y = state.stand ? STAND_LIFT : 0;
  setBackground();
  updateUI();
}

function bbox() {
  const box = new THREE.Box3();
  current.updateMatrixWorld(true);
  for (const c of current.children) if (c.visible) box.expandByObject(c);
  if (state.stand) box.expandByObject(stand);
  return box;
}

const DIRS = {
  hero: [-0.78, 0.36, 0.86], rear: [0.72, 0.42, -0.86], front: [0, 0.06, 1], side: [-1, 0.03, 0],
  top: [0.0001, 1, 0.0002], back: [0, 0.10, -1], low: [-0.55, 0.12, 1],
};

// Orthographic technical views: ?ortho=side|top|front|back&ow=<width m>&oc=<cx,cy,cz glTF>
const ORTHO = { side: [[1, 0, 0], [0, 1, 0]], top: [[0, 1, 0], [-1, 0, 0]], front: [[0, 0, 1], [0, 1, 0]], back: [[0, 0, -1], [0, 1, 0]] };
let orthoCam = null;
function setupOrtho() {
  const o = params.get('ortho');
  if (!o || !ORTHO[o]) return false;
  const ow = +params.get('ow'), oh = ow * H / W;
  const c = new THREE.Vector3(...params.get('oc').split(',').map(Number));
  orthoCam = new THREE.OrthographicCamera(-ow / 2, ow / 2, oh / 2, -oh / 2, 0.01, 100);
  const [dir, up] = ORTHO[o];
  orthoCam.position.copy(c).addScaledVector(new THREE.Vector3(...dir), 30);
  orthoCam.up.set(...up);
  orthoCam.lookAt(c);
  key.target.position.copy(c);
  return true;
}

function frame(view) {
  if (setupOrtho()) return;
  const cam = params.get('cam'), tgt = params.get('target');
  if (cam && tgt && state.shot) {
    camera.fov = +(params.get('fov') || 30); camera.aspect = W / H; camera.updateProjectionMatrix();
    camera.position.set(...cam.split(',').map(Number));
    const t = new THREE.Vector3(...tgt.split(',').map(Number));
    controls.target.copy(t); camera.lookAt(t); controls.update(); key.target.position.copy(t);
    return;
  }
  const box = bbox();
  const c = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const d = new THREE.Vector3(...DIRS[view] || DIRS.hero).normalize();
  const radius = size.length() * 0.5;
  const fov = view === 'top' || view === 'side' || view === 'front' || view === 'back' ? 14 : 28;
  camera.fov = fov;
  camera.aspect = W / H;
  camera.updateProjectionMatrix();
  const tight = { top: 0.72, side: 0.74, front: 0.86, back: 0.86, hero: 0.66, rear: 0.66, low: 0.62 }[view] ?? 0.8;
  const margin = state.shot ? 1 : 1.2; // interactive: leave room for the panels
  // fit to the narrower of the vertical and horizontal fields of view (phones in portrait)
  const vhalf = THREE.MathUtils.degToRad(fov) / 2;
  const hhalf = Math.atan(Math.tan(vhalf) * (W / H));
  const portrait = W / H < 1 ? 1.2 : 1;
  const fit = radius / Math.sin(Math.min(vhalf, hhalf)) * tight * margin * portrait * (state.stand ? 1.12 : 1);
  camera.position.copy(c).addScaledVector(d, fit);
  if (view === 'top') camera.up.set(1, 0, 0); else camera.up.set(0, 1, 0);
  controls.target.copy(c);
  camera.lookAt(c);
  controls.update();
  key.target.position.copy(c);
}

function updateUI() {
  const mk = (id, map, keyName, cb) => {
    const el = document.getElementById(id);
    el.innerHTML = '';
    for (const [k, label] of Object.entries(map)) {
      const b = document.createElement('button');
      b.textContent = label;
      if (state[keyName] === k) b.className = 'on';
      b.onclick = () => cb(k);
      el.appendChild(b);
    }
  };
  mk('variants', VARIANTS, 'variant', async (k) => { state.variant = k; await show(); });
  mk('looks', LOOKS, 'look', (k) => { state.look = k; applyState(); });
  mk('views', VIEWS, 'view', (k) => { state.view = k; frame(k); updateUI(); });
  document.getElementById('appendages').checked = state.appendages;
  document.getElementById('context').checked = state.context;
  document.getElementById('stand').checked = state.stand;
  const info = document.getElementById('info');
  if (report) {
    const rows = report.checks.map((c) => `<tr><td>${c.name}</td><td class="${c.pass ? 'ok' : 'bad'}">${c.value}</td></tr>`).join('');
    info.innerHTML = `<b>${report.class_name}</b><br><span style="color:var(--muted)">regulation checks (generated)</span><table>${rows}</table>`;
  } else info.textContent = '';
}

document.getElementById('title').addEventListener('click', () => {
  document.body.classList.toggle('show-controls');
});

document.getElementById('checks').addEventListener('click', () => {
  document.body.classList.toggle(window.innerWidth <= 720 ? 'show-info' : 'hide-info');
});

for (const id of ['appendages', 'context', 'stand']) {
  document.getElementById(id).addEventListener('change', (e) => {
    state[id] = e.target.checked;
    if (id === 'stand' && state.stand) { state.context = false; state.appendages = false; }
    applyState(); frame(state.view);
  });
}

async function show() {
  document.getElementById('msg').style.display = 'grid';
  const root = await loadVariant(state.variant);
  if (current) scene.remove(current);
  current = root;
  scene.add(current);
  report = await loadReport(state.variant);
  applyState();
  frame(state.view);
  document.getElementById('msg').style.display = 'none';
}

let frames = 0;
function loop() {
  // in screenshot mode render a few frames and then stop (software GL is slow)
  if (state.shot && frames >= 4) { window.__ready = true; return; }
  requestAnimationFrame(loop);
  controls.update();
  renderer.render(scene, orthoCam || camera);
  if (current) frames++;
}

window.addEventListener('resize', () => {
  if (state.shot) return;
  const w = window.innerWidth, h = window.innerHeight;
  renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix();
});

show().catch((e) => { document.getElementById('msg').textContent = 'Could not load model: ' + e + ' (serve this folder over http, see README)'; window.__error = String(e); });
loop();
