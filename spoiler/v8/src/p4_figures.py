"""v8 step 4: figures for the v8 package. Run from spoiler/:  python3 v8/src/p4_figures.py"""
import sys, json, os; sys.path.insert(0, 'v8/src'); sys.path.insert(0, 'v6/src')
import numpy as np, trimesh
from zr import render, grid, label, fit_view
from layout import OUT, ASM, PRN, DOC, IDS, STEM, N_KEYS, N_THIN, COL, KEY_COL, CUT_Z, E_PATH, DP_THIN
from zr import look_at
THIN_COL = (40, 190, 120)            # thin keys

os.makedirs(DOC, exist_ok=True)
meta = json.load(open(f'{OUT}/_parts_meta.json')); rep = json.load(open(f'{OUT}/_print_report.json'))
P = {k: trimesh.load(f'{ASM}/{k}.stl') for k in IDS}
K = [trimesh.load(f'{ASM}/KEY_{i}.stl') for i in range(1, N_KEYS + 1)]
FR = meta['frames']
BG = (246, 246, 244)
def lab(im, t, s=26, fill=(20, 20, 20)): return label(im, t, size=s, fill=fill)
def dots(pts, r, col, step=1):
    out = []
    for q in pts[::step]:
        s = trimesh.creation.icosphere(subdivisions=1, radius=r); s.apply_translation(q); out.append((s, col))
    return out
VIEWS = [('rear three-quarter', (-0.55, 0.42, 0.72)), ('front three-quarter', (0.62, 0.40, -0.67))]

# 1 assembled, the two views the user marked on (same cameras as the v7 figure)
ims = []
for t, dr in VIEWS:
    eye, tgt, fov = fit_view(list(P.values()), dr, W=1300, H=800, dist=2600)
    im = render([(P[k], COL[k]) for k in IDS], eye=eye, target=tgt, fov=fov, W=1300, H=800, bg=BG, spec=0.35, ambient=0.28)
    ims.append(lab(im, f'v8 assembled, {t}: 6 pieces. Each end piece is split into a front half (light grey)\nand a rear half (dark grey) along its length', s=22))
grid(ims, 1, bg=BG).save(f'{DOC}/v8_assembled.png')

# 2 the cut against the lines the user drew (blue), same cameras
cut = trimesh.load(E_PATH).section(plane_origin=[0, 0, CUT_Z], plane_normal=[0, 0, 1]).vertices
cut = cut[np.abs(cut[:, 0]) > 325.5]
marks = dict(np.load('v8/data/user_marks_3d.npz')) if os.path.exists('v8/data/user_marks_3d.npz') else {}
ims = []
for (t, dr), side in zip(VIEWS, ('P1', 'P4')):
    eye, tgt, fov = fit_view(list(P.values()), dr, W=1300, H=800, dist=2600)
    items = [(P[k], COL[k]) for k in IDS]
    items += dots(cut[np.sign(cut[:, 0]) == (-1 if side == 'P1' else 1)], 1.6, (220, 30, 30), step=2)
    for k, pts in marks.items():
        if k.endswith(side): items += dots(pts, 2.4, (25, 113, 194), step=2)
    im = render(items, eye=eye, target=tgt, fov=fov, W=1300, H=800, bg=BG, spec=0.3, ambient=0.3)
    ims.append(lab(im, f'{t}: your lines (blue) and the cut (red), the plane z = {CUT_Z:.0f} mm. It runs from the middle of the\n'
                       'seam face along the piece and leaves through the fin\'s rear edge, as in your drawing', s=21))
grid(ims, 1, bg=BG).save(f'{DOC}/v8_cut_vs_marks.png')

# 3 exploded from below: end halves pulled apart along the chord too, keys lifted out of their pockets
dx = {'P1F': -135.0, 'P1R': -135.0, 'P2': -45.0, 'P3': 45.0, 'P4R': 135.0, 'P4F': 135.0}
dz = {'P1F': -45.0, 'P1R': 45.0, 'P2': 0.0, 'P3': 0.0, 'P4R': 45.0, 'P4F': -45.0}
items = []
for k in IDS:
    m = P[k].copy(); m.apply_translation([dx[k], 0, dz[k]]); items.append((m, COL[k]))
for i, km in enumerate(K):
    f = FR[i]; A = np.array(f['T'])[:, 2]; a, b = f['pieces']
    sh = np.array([(dx[a] + dx[b]) / 2, 0, (dz[a] + dz[b]) / 2])
    m = km.copy(); m.apply_translation(-A * 45 + sh); items.append((m, THIN_COL if f['thin'] else KEY_COL))
eye, tgt, fov = fit_view([m for m, _ in items], (-0.45, -0.62, 0.64), W=1600, H=1000, dist=2600)
im = render(items, eye=eye, target=tgt, fov=fov, W=1600, H=1000, bg=BG, spec=0.3, ambient=0.3)
lab(im, f'Exploded, seen from underneath: {N_KEYS} bow-tie keys, {N_KEYS - N_THIN} standard (blue) and {N_THIN} thin (green). Two across each cross\n'
        'seam (at the outer seams one into each half of the end piece) and two across each end piece\'s lengthwise cut', s=22).save(f'{DOC}/v8_exploded_underside.png')

# 4 the new lengthwise joint from below: left end halves slightly apart, its two keys lifted out
items = [(P['P1R'], COL['P1R'])]
m = P['P1F'].copy(); m.apply_translation([0, 0, -22]); items.append((m, COL['P1F']))
for i, f in enumerate(FR):
    if f['kind'] == 'lengthwise' and f['x'] < 0:
        A = np.array(f['T'])[:, 2]; m = K[i].copy(); m.apply_translation(-A * 26 + np.array([0, 0, -11])); items.append((m, KEY_COL))
c = np.array([-415.0, 5.0, 92.0]); eye = c + np.array([-150, -260, -170])
im = render(items, eye=eye, target=c, fov=38, W=1400, H=900, bg=BG, spec=0.3, ambient=0.3)
lab(im, f'New lengthwise joint of the left end piece, from below: front half (light) and rear half (dark) pulled apart.\n'
        f'Two keys (blue) lie across the cut at |x| = {meta["LKEY_X"][0]:.0f} and {meta["LKEY_X"][1]:.0f} mm, flush with the hidden underside', s=21).save(f'{DOC}/v8_lengthwise_joint.png')

# 5 bed layouts
imgs = []
bed = trimesh.creation.box(extents=[420, 420, 2]); bed.apply_translation([210, 210, -1.2])
for k in IDS:
    p = trimesh.load(f'{PRN}/{STEM[k]}.stl'); e = p.extents
    im = render([(bed, (205, 205, 210)), (p, COL[k])], eye=(210 + 650, 210 - 750, 520), target=(210, 210, 140), up=(0, 0, 1), fov=42, W=620, H=820, bg=BG, spec=0.3, ambient=0.3)
    imgs.append(lab(im, f'{STEM[k]}\n{e[0]:.0f} x {e[1]:.0f} x {e[2]:.0f} mm\non its {rep[k]["on_bed"].split(" (")[0]}', s=18))
kp = trimesh.load(f'{PRN}/{rep["KEY"]["plate"]}')
kp2 = kp.copy(); kp2.apply_translation([210 - kp.bounds.mean(0)[0], 210 - kp.bounds.mean(0)[1], 0])
keys_on_plate = [(c, THIN_COL if c.extents[2] < 5.0 else KEY_COL) for c in kp2.split(only_watertight=False)]
im = render([(bed, (205, 205, 210))] + keys_on_plate, eye=(210 + 260, 210 - 300, 260), target=(210, 210, 0), up=(0, 0, 1), fov=42, W=620, H=820, bg=BG, spec=0.3, ambient=0.3)
imgs.append(lab(im, f'bow-tie keys: {N_KEYS - N_THIN} standard (blue)\n+ {N_THIN} thin (green), with spares,\nflat on the car-side face, no supports', s=18))
grid(imgs, 7, bg=BG).save(f'{DOC}/v8_bed_layouts.png')

# 6 v7 end piece vs the two v8 halves, as printed
try:
    old = trimesh.load('v7/print/v7_1_LEFT_END.stl')
    f_ = trimesh.load(f'{PRN}/{STEM["P1F"]}.stl'); r_ = trimesh.load(f'{PRN}/{STEM["P1R"]}.stl')
    o = old.copy(); o.apply_translation([-150, 0, 0]); a = f_.copy(); a.apply_translation([20, 0, 0]); b = r_.copy(); b.apply_translation([135, 0, 0])
    im = render([(bed, (205, 205, 210)), (o, (150, 152, 158)), (a, COL['P1F']), (b, COL['P1R'])], eye=(210 + 560, 210 - 900, 430),
                target=(210, 210, 150), up=(0, 0, 1), fov=40, W=1100, H=900, bg=BG, spec=0.3, ambient=0.3)
    lab(im, f'Left end piece as printed. v7 (grey): {old.extents[2]:.0f} mm tall, standing, with supports under the fin.\n'
            f'v8: front half {f_.extents[2]:.0f} mm and rear half {r_.extents[2]:.0f} mm, lying on the flat cut face, no fin supports', s=20).save(f'{DOC}/v8_vs_v7_end_piece.png')
except Exception as e:
    print('comparison skipped:', e)

# 7 the left end piece's inner face (where it meets the middle piece), seen as in the user's slicer screenshot: lying
# as on the car, from the middle piece's side. One key into each half: the rear half's at z = 161 (as before) and the
# new thin key in the front half at z = 80 (the first v8 had both, z = 123 and 161, in the rear half).
from PIL import ImageDraw, ImageFont
FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 19)
FONTB = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 19)
def project(pts, eye, tgt, up, fov, W, H):
    e, r, u, f = look_at(eye, tgt, up); d = np.atleast_2d(pts) - e
    F = 0.5 * H / np.tan(np.radians(fov) / 2); z = d @ f
    return np.column_stack([W / 2 + F * (d @ r) / z, H / 2 - F * (d @ u) / z])
def callout(im, xy, text, to, bold=False, col=(20, 20, 20)):
    dr = ImageDraw.Draw(im); dr.line([tuple(to), tuple(xy)], fill=col, width=2)
    dr.ellipse([to[0] - 4, to[1] - 4, to[0] + 4, to[1] + 4], fill=col)
    dr.multiline_text((xy[0] + 6, xy[1] - 12), text, fill=col, font=FONTB if bold else FONT, spacing=4)
import trimesh.ray.ray_pyembree as _rp
RE = _rp.RayMeshIntersector(trimesh.load(E_PATH))
def under(x, z):
    loc, ir, it = RE.intersects_location(np.array([[x, -300.0, z]]), [[0, 1.0, 0]], multiple_hits=False); return loc[0]
fs = {f['z']: (i, f) for i, f in enumerate(FR) if f['kind'] == 'cross' and f['x'] < -300}
W7, H7 = 1500, 640
c7 = np.array([-480.0, -5.0, 112.0]); up7 = (0, 1, 0)
eye7 = c7 + 450 * np.array([np.cos(np.radians(24)), np.sin(np.radians(24)), 0.0]); fov7 = 36
ims = []
for with_keys in (False, True):
    items = [(P['P1F'], COL['P1F']), (P['P1R'], COL['P1R'])]
    if with_keys:
        for zk, (i, f) in fs.items(): items.append((K[i], THIN_COL if f['thin'] else KEY_COL))
    im = render(items, eye=eye7, target=c7, up=up7, fov=fov7, W=W7, H=H7, bg=BG, spec=0.3, ambient=0.32)
    q = {zk: project(under(-325.0, zk) + [0, -1, 0], eye7, c7, up7, fov7, W7, H7)[0] for zk in (161.0, 80.0, CUT_Z)}
    (i_t, f_t) = fs[80.0]
    callout(im, q[161.0] + [-330, 95], 'rear half: standard key, unchanged\n(z = 161 mm)', q[161.0])
    callout(im, q[80.0] + [70, 85], f'front half: NEW thin key (z = 80 mm)\n{DP_THIN - 0.25:.2f} mm thick, same bow-tie outline', q[80.0], bold=True)
    callout(im, q[CUT_Z] + [-60, 150], 'joint between the front and rear halves (z = 100 mm)', q[CUT_Z])
    ims.append(lab(im, ('Left end piece, both halves, lying as on the car, seen from the end that joins the middle piece (your screenshot view).\n'
                        + ('With the keys in: standard key (blue) in the rear half, thin key (green) in the front half.\nThe half of each key that sticks out goes into the middle piece.' if with_keys else
                           'The two pockets at this end: one in each half. Before, both were in the rear half (z = 123 and 161 mm).')), s=20))
grid(ims, 1, bg=BG).save(f'{DOC}/v8_end_piece_keys.png')
print('figures done')
