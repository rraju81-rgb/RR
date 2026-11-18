"""Aero test, step 5: figures and the results table (both variants must have run a4_forces.py).
Run from spoiler/:  python3 aero/src/a5_figures.py   -> aero/results/*.png, aero/results/aero_results.json"""
import sys, json, numpy as np, trimesh, matplotlib
sys.path.insert(0, 'aero/src'); sys.path.insert(0, 'v6/src')
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager, cm, colors
from matplotlib.collections import PolyCollection
from zr import render, label, grid
for f in ('michroma.ttf', 'jetbrainsmono-medium.ttf', 'spacegrotesk-medium.ttf'): font_manager.fontManager.addfont(f'v6/brochure/assets/fonts/{f}')
plt.rcParams['font.family'] = 'Space Grotesk'
VARS = ['no_spoiler', 'with_spoiler']; LAB = {'no_spoiler': 'Without spoiler', 'with_spoiler': 'With spoiler'}
R = {v: json.load(open(f'aero/out/{v}_forces.json')) for v in VARS}
def final(v): h = R[v]['history']; return h[sorted(h, key=float)[-1]]
U = R['no_spoiler']['U']; rho = R['no_spoiler']['rho']; A = R['no_spoiler']['Aref_full']
# ---------------- results table (full car), and scaled to other speeds (forces ~ V^2 at these Reynolds numbers) ----------------
out = dict(speed_kmh=100, U_ms=U, rho=rho, frontal_area_m2=A, wheelbase_m=R['no_spoiler']['wheelbase'], cells={v: R[v]['cells'] for v in VARS})
# A steady solver keeps a small oscillation from the unsteady wake, so every number is the MEAN of the last three
# written iterations (900, 1200, 1500); the min-max over them is kept as the uncertainty band.
KEYS = ('Cd', 'Cl', 'Clf', 'Clr', 'CdA_m2', 'drag_N', 'lift_N', 'lift_front_N', 'lift_rear_N', 'drag_pressure_N', 'drag_friction_N')
def last3(v, part='car'):
    h = R[v]['history']; ts = sorted(h, key=float)[-3:]
    return {k: [float(h[t][part][k]) for t in ts] for k in KEYS}, ts
for v in VARS:
    L3, ts = last3(v); out[v] = {k: float(np.mean(L3[k])) for k in KEYS}
    out[v]['band'] = {k: [float(min(L3[k])), float(max(L3[k]))] for k in ('Cd', 'Cl', 'Clf', 'Clr')}
    out[v]['averaged_over_iterations'] = [int(float(t)) for t in ts]
    out[v]['convergence'] = {t: {k: float(R[v]['history'][t]['car'][k]) for k in ('Cd', 'Cl', 'Clf', 'Clr')} for t in sorted(R[v]['history'], key=float)}
if 'spoiler' in final('with_spoiler'):
    S3, _ = last3('with_spoiler', 'spoiler'); out['spoiler_alone'] = dict(drag_N=float(np.mean(S3['drag_N'])), lift_N=float(np.mean(S3['lift_N'])))
d = {k: out['with_spoiler'][k] - out['no_spoiler'][k] for k in ('Cd', 'Cl', 'Clf', 'Clr', 'drag_N', 'lift_N', 'lift_front_N', 'lift_rear_N')}
out['delta'] = d
for kmh in (100, 130, 160):
    f = (kmh / 100.0) ** 2
    out[f'at_{kmh}'] = {v: dict(drag_N=out[v]['drag_N'] * f, lift_front_N=out[v]['lift_front_N'] * f, lift_rear_N=out[v]['lift_rear_N'] * f) for v in VARS}
json.dump(out, open('aero/results/aero_results.json', 'w'), indent=1)
print(json.dumps({k: out[k] for k in ('no_spoiler', 'with_spoiler', 'delta')}, indent=1, default=lambda x: round(x, 4)))
# ---------------- surface pressure (Cp) on the car, both variants ----------------
def wall_mesh(v):
    M = np.load(f'aero/out/{v}_mesh.npz'); F = np.load(f'aero/out/{v}_fields.npz')
    P, flat, st, sz = M['P'], M['flat'], M['starts'], M['sizes']
    walls = [k[6:] for k in F.files if k.startswith('faces_') and k != 'faces_midplane']
    tris, cp = [], []
    for w in walls:
        fi = F[f'faces_{w}']; own = F['owner'][fi]; pf = F['p'][own] / (0.5 * U ** 2)
        for k in np.unique(sz[fi]):
            sel = fi[sz[fi] == k]; c = pf[sz[fi] == k]
            idx = flat[st[sel][:, None] + np.arange(k)[None, :]]
            for j in range(1, k - 1):
                tris.append(np.stack([idx[:, 0], idx[:, j], idx[:, j + 1]], 1)); cp.append(c)
    T = np.vstack(tris); cp = np.concatenate(cp)
    m = trimesh.Trimesh(P, T, process=False)
    # mirror the half car about the symmetry plane (Y = 0) for a full-car picture
    Pm = P.copy(); Pm[:, 1] *= -1
    mm = trimesh.Trimesh(Pm, T[:, ::-1], process=False)
    full = trimesh.util.concatenate([m, mm]); cp2 = np.concatenate([cp, cp])
    full.vertices = full.vertices[:, [1, 2, 0]] * np.array([1, 1, 1.0])   # CFD (X fwd, Y lat, Z up) -> render frame (x lat, y up, z rear)
    return full, cp2
cmap = plt.get_cmap('RdYlBu_r'); norm = colors.Normalize(-1.2, 0.6)
ims = []
for v in VARS:
    m, cp = wall_mesh(v)
    fc = cmap(norm(np.clip(cp, -1.2, 0.6)))[:, :3] * 255.0
    for nm, eye, tgt, fov in [('rear', (-2.7, 2.7, 7.6), (0.0, 0.95, 3.45), 27), ('top', (-1.9, 5.4, 6.6), (0.0, 1.1, 3.05), 30)]:
        im = render([(m, fc)], eye=eye, target=tgt, fov=fov, W=900, H=600, bg=(246, 246, 244), spec=0.15, ambient=0.55)
        ims.append(label(im, f'{LAB[v]}: surface pressure', size=20, fill=(20, 20, 20)))
g = grid(ims, 2, bg=(246, 246, 244))
# colour bar strip underneath
fig = plt.figure(figsize=(g.width / 200, 1.2), dpi=200); ax = fig.add_axes([0.25, 0.55, 0.5, 0.16])
cbar = matplotlib.colorbar.ColorbarBase(ax, cmap=cmap, norm=norm, orientation='horizontal')
cbar.set_label('pressure coefficient Cp   (blue = suction, red = pressure)', fontsize=9); ax.tick_params(labelsize=8)
fig.patch.set_facecolor((246 / 255, 246 / 255, 244 / 255)); fig.savefig('aero/out/_cbar.png', dpi=200); plt.close(fig)
from PIL import Image
cb = Image.open('aero/out/_cbar.png').convert('RGB'); cb = cb.resize((g.width, int(cb.height * g.width / cb.width)))
G = Image.new('RGB', (g.width, g.height + cb.height), (246, 246, 244)); G.paste(g, (0, 0)); G.paste(cb, (0, g.height))
G.save('aero/results/cp_surface.png')
# ---------------- mid-plane (car centre line) velocity, both variants, rear half of the car ----------------
def midplane(v):
    M = np.load(f'aero/out/{v}_mesh.npz'); F = np.load(f'aero/out/{v}_fields.npz')
    P, flat, st, sz = M['P'], M['flat'], M['starts'], M['sizes']
    fi = F['faces_midplane']; own = F['owner'][fi]
    polys = [P[flat[st[i]: st[i] + sz[i]]][:, [0, 2]] for i in fi]
    return polys, np.linalg.norm(F['U'][own], axis=1), F['p'][own] / (0.5 * U ** 2)
fig, axs = plt.subplots(2, 1, figsize=(11, 7.2), dpi=150)
for ax, v in zip(axs, VARS):
    polys, mag, cp = midplane(v)
    pc = PolyCollection(polys, array=mag / U, cmap='turbo', clim=(0, 1.35), edgecolors='face', linewidths=0.1); ax.add_collection(pc)
    ax.set_xlim(1.6, 7.2); ax.set_ylim(0, 2.3); ax.set_aspect('equal')
    ax.set_title(f'{LAB[v]}: air speed on the car centre line (U / U∞), 100 km/h', fontsize=11, loc='left')
    ax.set_xlabel('m from the front bumper'); ax.set_ylabel('height, m')
cb = fig.colorbar(pc, ax=axs, shrink=0.7, label='U / U∞'); plt.savefig('aero/results/midplane_speed.png', bbox_inches='tight'); plt.close()
# ---------------- convergence of the coefficients (written every 300 iterations) ----------------
fig, axs = plt.subplots(1, 2, figsize=(11, 3.6), dpi=150)
for v, c in zip(VARS, ('#6b7280', '#ff5c1e')):
    it = [int(float(t)) for t in out[v]['convergence']]
    axs[0].plot(it, [out[v]['convergence'][t]['Cd'] for t in out[v]['convergence']], 'o-', color=c, label=LAB[v])
    axs[1].plot(it, [out[v]['convergence'][t]['Clr'] for t in out[v]['convergence']], 'o-', color=c, label=LAB[v])
axs[0].set_title('Drag coefficient Cd vs iteration'); axs[1].set_title('Rear-axle lift coefficient vs iteration')
for a in axs: a.grid(alpha=0.3); a.set_xlabel('iteration'); a.legend()
plt.tight_layout(); plt.savefig('aero/results/convergence.png'); plt.close()
# ---------------- summary bars at 100 and 130 km/h ----------------
fig, axs = plt.subplots(1, 2, figsize=(11, 3.8), dpi=150)
for ax, kmh in zip(axs, (100, 130)):
    r = out[f'at_{kmh}']; keys = [('drag_N', 'Drag'), ('lift_front_N', 'Lift, front axle'), ('lift_rear_N', 'Lift, rear axle')]
    x = np.arange(len(keys)); wdt = 0.36
    for j, (v, c) in enumerate(zip(VARS, ('#6b7280', '#ff5c1e'))):
        vals = [r[v][k] for k, _ in keys]; b = ax.bar(x + (j - 0.5) * wdt, vals, wdt, color=c, label=LAB[v])
        for xi, val in zip(x + (j - 0.5) * wdt, vals): ax.text(xi, val + (6 if val >= 0 else -6), f'{val:.0f}', ha='center', va='bottom' if val >= 0 else 'top', fontsize=8)
    ax.axhline(0, color='k', lw=0.6); ax.set_xticks(x, [n for _, n in keys]); ax.set_ylabel('N (positive lift = up)'); ax.set_title(f'{kmh} km/h'); ax.legend(fontsize=8); ax.grid(axis='y', alpha=0.3)
plt.tight_layout(); plt.savefig('aero/results/forces_summary.png'); plt.close()
print('figures written to aero/results/')
