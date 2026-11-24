"""v13 step 5: figures in v13/docs/.
  v13_parts.png         the six parts, numbered as marked, from above-behind and from below
  v13_rim.png           the back edge without a brim: sections at the centre and the thick outer zone, and close-ups
  v13_back_v12_v13.png  the back edge in v12 (brim) and v13 (flush), same cameras
  v13_corner_v12_v13.png the ducktail corners in v12 (notch under the lip end) and v13 (blended)
  v13_fin_v12_v13.png   the fins' pillar side in v12 (hanging pieces) and v13
  v13_joints.png        the joint faces: tongue and groove at a span seam, pin holes at a front/rear cut
  v13_joint_detail.png  dimensioned tongue/groove and both pin holes
  v13_sections.png      v8 solid against v13 cored
  v13_bed_layouts.png   the print set on the 420 x 420 mm bed: the six parts and the pin
Run from spoiler/:  python3 v13/src/p5_figures.py"""
import sys, os, json; sys.path.insert(0, 'v13/src'); sys.path.insert(0, 'v6/src')
import numpy as np, trimesh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
from PIL import ImageDraw, ImageFont
from trimesh.ray.ray_pyembree import RayMeshIntersector
from zr import render, grid, label, look_at
from layout import (E_PATH, CAR_PATH, OUT, ASM, PRN, DOC, IDS, STEM, LABEL, SEC, HALF_OF, XS, T_SKIN, SKIRT, SKIN_V, WALL, TIP_T, TIP_R, TIP_SHIFT, END_SHIFT, END_FADE, E2_PATH,
                    TONGUE_BASE, TONGUE_H, CLEAR, GROOVE_EXTRA, CHAMFER_DEG, END_DEG, HOLE_D, HOLE_DEPTH, PIN_D, PIN_L, HOLE_CHAMFER, chord_plane)
os.makedirs(DOC, exist_ok=True)
parts = {pid: trimesh.load(f'{ASM}/{STEM[pid]}.stl') for pid in IDS}
J = json.load(open(f'{OUT}/joints.json')); V = json.load(open(f'{OUT}/validation.json'))
pins = [trimesh.load(f'{ASM}/v13_PIN_{i + 1:02d}.stl') for i in range(J['n_pins'])]
splines = [trimesh.load(f'{ASM}/v13_SPLINE_{i + 1:02d}.stl') for i in range(J['n_splines'])]
COL = {'P1': (232, 150, 70), 'P2': (205, 210, 220), 'P3': (120, 170, 230), 'P4': (240, 200, 110), 'P5': (232, 150, 70), 'P6': (205, 210, 220)}
FONT = lambda sz: ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', sz)

def proj(eye, tgt, fov, W, H, P):
    e, r, u, f = look_at(eye, tgt); fp = 0.5 * H / np.tan(np.radians(fov) / 2); q = np.asarray(P, float) - e; z = q @ f
    return np.column_stack([W / 2 + fp * (q @ r) / z, H / 2 - fp * (q @ u) / z])

def numbered(eye, tgt, fov, W, H, side):
    im = render([(parts[p], COL[p]) for p in IDS], eye=eye, target=tgt, up=(0, 1, 0), fov=fov, W=W, H=H, edges=True)
    d = ImageDraw.Draw(im)
    for p in IDS:
        m = parts[p]; c = m.vertices[np.argsort(m.vertices[:, 1])]                 # a point on the visible side
        pt = c[-len(c) // 6:].mean(0) if side == 'top' else c[:len(c) // 6].mean(0)
        x, y = proj(eye, tgt, fov, W, H, [pt])[0]
        d.text((x, y), p[1], fill=(25, 25, 30), font=FONT(46), anchor='mm', stroke_width=3, stroke_fill=(255, 255, 255))
    return im

# 1. parts
a = numbered((0, 900, 1250), (0, -10, 110), 40, 1400, 800, 'top')
b = numbered((0, -1150, 650), (0, -10, 110), 40, 1400, 800, 'bottom')
grid([label(a, 'v13: six parts as marked - 3 across (cut at x = +-216.7 mm), each cut into a front and a rear part'),
      label(b, 'from below: 1, 3, 5 rear parts (with the smooth tip at the back) - 2, 4, 6 front parts (2 and 6 carry the fins)')], cols=1).save(f'{DOC}/v13_parts.png')

# 2. rim (close-ups from the full-resolution cored sections: the part files are decimated to within 0.02 mm, which is
# invisible in print but shows as facets in a macro render)
sys.path.insert(0, 'v6/src'); from bowtie import tomf, totm
def full_rear(sec):
    n, d = chord_plane(sec); return totm(tomf(trimesh.load(f'{OUT}/cored_{sec}.stl')).trim_by_plane(list(n), d))
FULL = {'P3': full_rear('C'), 'P1': full_rear('L')}
FULL['P3'].export(f'{OUT}/full_P3.stl')
E = trimesh.load(E_PATH); car = trimesh.load(CAR_PATH, process=False)
st = np.load(f'{OUT}/rim_curve.npz')
fig, axs = plt.subplots(1, 2, figsize=(15, 6.2))
for ax, (x, pid) in zip(axs, [(-100.0, 'P3'), (-440.0, 'P1')]):
    for mesh, kw in [(E, dict(fc='#eef0f3', ec='#b9bec7', lw=0.8, label='original solid (v8)')), (parts[pid], dict(fc='#e8964699', ec='#a5521a', lw=1.2, label='v13 part %s' % pid[1]))]:
        s = mesh.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
        polys = sorted(s.discrete, key=lambda d: -abs(trimesh.path.polygons.area(d[:, [2, 1]]) if hasattr(trimesh.path.polygons, 'area') else 0))
        for i, d in enumerate(s.discrete):
            kw_ = kw if i == 0 else {k: v for k, v in kw.items() if k != 'label'}
            ax.add_patch(MPoly(d[:, [2, 1]], closed=True, **kw_))
    if pid == 'P1':                                                      # the hidden channel: draw its outline on top, white
        s = parts[pid].section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
        ds = sorted(s.discrete, key=lambda d: -np.ptp(d[:, 2]) * np.ptp(d[:, 1]))
        for d in ds[1:]: ax.add_patch(MPoly(d[:, [2, 1]], closed=True, fc='white', ec='#a5521a', lw=1.0))
    s = car.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
    for i, d in enumerate(s.discrete): ax.plot(d[:, 2], d[:, 1], color='#2b6cd6', lw=1.0, label='car' if i == 0 else None)
    i = np.argmin(abs(st['x'] - x)); Nz = st['N'][i, 1]; zt = st['z'][i] + TIP_T * Nz; yt = st['y_tip'][i]
    fe = np.clip((abs(x) - END_FADE[0]) / (END_FADE[1] - END_FADE[0]), 0, 1)
    ze = zt + (TIP_SHIFT + (END_SHIFT - TIP_SHIFT) * fe * fe * (3 - 2 * fe)) * Nz   # where the pocket's back face starts
    RP = RayMeshIntersector(parts[pid])
    def hit(z, y0, dy):                                                  # first surface of the part along a vertical ray
        loc, _, _ = RP.intersects_location([[x, y0, z]], [[0, dy, 0]], multiple_hits=False)
        return float(loc[0, 1]) if len(loc) else np.nan
    za = ze + 16 * Nz; top_a, ceil_a = hit(za, yt + 60, -1.0), hit(za, yt - 30, 1.0)
    zf = ze + 3.0 * Nz; zu = zt + 1.0 * Nz
    ax.set_xlim(min(ze, zt) - 26, max(ze, zt) + 30); ax.set_ylim(yt - 7, yt + 23); ax.set_aspect('equal'); ax.grid(alpha=0.25)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.09), ncol=3, fontsize=8, frameon=False)
    ax.annotate("the spoiler's own underside,\nflush to the back edge (no brim)", (zu, hit(zu, yt - 30, 1.0)), (zt + 14, yt - 5.0),
                fontsize=9, ha='center', arrowprops=dict(arrowstyle='->', lw=0.8))
    ax.annotate('pocket edge: %.0f mm round\ninto a 45° face' % TIP_R, (zf, hit(zf, yt - 30, 1.0)), (ze - 12, yt - 4.6), fontsize=9,
                ha='center', arrowprops=dict(arrowstyle='->', lw=0.8))
    if pid == 'P1':
        s_ = parts[pid].section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
        ds_ = sorted(s_.discrete, key=lambda d: -np.ptp(d[:, 2]) * np.ptp(d[:, 1]))
        if len(ds_) > 1:
            cz, cy = ds_[1][:, 2].mean(), ds_[1][:, 1].mean()
            ax.annotate('hidden channel\n(closed, prints\nwithout support)', (cz, cy), (zt + 16, yt + 15.5), fontsize=8, ha='center',
                        arrowprops=dict(arrowstyle='->', lw=0.8))
    ax.text(za, 0.5 * (top_a + ceil_a), 'skin %.1f mm' % T_SKIN, fontsize=9, ha='center', va='center')
    ax.text(ze + 30 * Nz, ceil_a - 2.2, 'pocket', fontsize=9, color='#555', ha='center', va='center')
    ax.set_title('section at x = %.0f mm (%s), z to the rear' % (x, 'centre' if x > -216 else 'outer zone, the deepest part of the back edge'), fontsize=10)
plt.tight_layout(); plt.savefig(f'{DOC}/_rim_sec.png', dpi=110); plt.close()
from PIL import Image
sec = Image.open(f'{DOC}/_rim_sec.png'); os.remove(f'{DOC}/_rim_sec.png')
c = (205, 208, 215)
r1 = render([(FULL['P3'], c)], eye=(-140, -35, 300), target=(-120, 20, 205), up=(0, 1, 0), fov=30, W=900, H=560, edges=True)
r2 = render([(FULL['P3'], c)], eye=(60, -140, 200), target=(0, 15, 170), up=(0, 1, 0), fov=50, W=900, H=560, edges=True)
r3 = render([(FULL['P1'], c)], eye=(-430, -90, 300), target=(-440, 0, 180), up=(0, 1, 0), fov=40, W=900, H=560, edges=True)
row = grid([label(r1, 'from behind, under the lip (part 3)', size=18), label(r2, 'from below: flush back edge, pocket (part 3)', size=18),
            label(r3, 'outer zone (part 1)', size=18)], cols=3)
W = max(sec.width, row.width); canvas = Image.new('RGB', (W, sec.height + row.height), (255, 255, 255))
canvas.paste(sec, ((W - sec.width) // 2, 0)); canvas.paste(row.resize((W, int(row.height * W / row.width))) if row.width != W else row, (0, sec.height))
canvas.save(f'{DOC}/v13_rim.png')
# v12 against v13, same cameras: the back edge (no brim), the ducktail corners, the fins' pillar side
cams = [dict(eye=(-290, -95, 150), target=(-205, 14, 205), up=(0, 1, 0), fov=30),
        dict(eye=(-300, -75, 120), target=(-330, 8, 196), up=(0, 1, 0), fov=34),
        dict(eye=(-480, -420, 120), target=(-500, 0, 130), up=(0, 0, 1), fov=40),
        dict(eye=(-500, -300, 360), target=(-520, -10, 150), up=(0, 1, 0), fov=34)]
V12 = 'v12/out/assembled'
if os.path.exists(f'{V12}/v12_3_CENTRE_REAR.stl'):
    old = {k: trimesh.load(f'{V12}/v12_{k}.stl') for k in ('1_LEFT_REAR', '2_LEFT_FRONT', '3_CENTRE_REAR')}
    new = {k: parts[p] for k, p in (('1_LEFT_REAR', 'P1'), ('2_LEFT_FRONT', 'P2'), ('3_CENTRE_REAR', 'P3'))}
    oc, gc = (230, 150, 80), (200, 205, 215)
    sets = [('3_CENTRE_REAR',), ('1_LEFT_REAR',), ('1_LEFT_REAR', '2_LEFT_FRONT'), ('1_LEFT_REAR', '2_LEFT_FRONT')]
    names = ['the cut end of part 3', 'part 1, outer zone', 'left end from below', 'left end from below-behind']
    ims = []
    for cam, keys, nm in zip(cams, sets, names):
        for tag, src in (('v12: brim along the back', old), ('v13: no brim, flush', new)):
            ims.append(label(render([(src[k], oc if 'REAR' in k else gc) for k in keys], W=760, H=520, edges=False, spec=0.2, **cam),
                             '%s (%s)' % (tag, nm), size=17, fill=(255, 220, 120)))
    grid(ims, cols=2).save(f'{DOC}/v13_back_v12_v13.png')
    def crop(m): return totm(tomf(m).trim_by_plane([1, 0, 0], -600.0).trim_by_plane([-1, 0, 0], 380.0).trim_by_plane([0, 0, 1], 95.0))
    A, B = crop(trimesh.load(E2_PATH)), crop(E)
    ims = []
    for cam, nm in [(dict(eye=(-430, 130, 330), target=(-505, 2, 178), fov=30), 'from above-behind'),
                    (dict(eye=(-640, 40, 260), target=(-505, 0, 178), fov=28), 'from outside-behind'),
                    (dict(eye=(-660, -5, 175), target=(-505, 0, 178), fov=26), 'from outside, level')]:
        for tag, m in (('v12: notch under the lip end', A), ('v13: lip blended into the end', B)):
            ims.append(label(render([(m, (172, 178, 188))], up=(0, 1, 0), W=760, H=520, edges=False, spec=0.35, **cam), '%s (%s)' % (tag, nm),
                             size=17, fill=(255, 220, 120)))
    grid(ims, cols=2).save(f'{DOC}/v13_corner_v12_v13.png')
    camF = dict(eye=(-470, -40, 60), target=(-610, -75, 20), up=(0, 1, 0), fov=40)
    grid([label(render([(old['2_LEFT_FRONT'], gc)], W=760, H=520, edges=False, spec=0.2, **camF), 'v12: part 2, pillar side of the fin', size=17, fill=(255, 220, 120)),
          label(render([(new['2_LEFT_FRONT'], gc)], W=760, H=520, edges=False, spec=0.2, **camF), 'v13: hanging pieces removed', size=17, fill=(255, 220, 120))],
         cols=2).save(f'{DOC}/v13_fin_v12_v13.png')

# 3. joints
o = (240, 120, 40)
def near(group, x, tol=25): return [g for g in group if abs(g.centroid[0] - x) < tol]
P1x = parts['P1'].copy(); P1x.apply_translation([-60, 0, 0])
im1 = render([(parts['P1'], c)], eye=(-XS + 140, 75, 215), target=(-XS, 18, 175), up=(0, 1, 0), fov=30, W=1000, H=600, edges=True)
im2 = render([(parts['P3'], c)], eye=(-XS - 130, 70, 210), target=(-XS, 20, 170), up=(0, 1, 0), fov=30, W=1000, H=600, edges=True)
P4x = parts['P4'].copy(); n, d = chord_plane('C'); P4x.apply_translation(-n * 70)
im3 = render([(P4x, c), (parts['P3'], c)] + [(s_, o) for s_ in splines if abs(s_.centroid[0]) < 216] + [(p, o) for p in pins if abs(p.centroid[2] - 122) < 15],
             eye=(0, 330, 40), target=(0, 5, 95), up=(0, 1, 0), fov=50, W=1000, H=600, edges=True)
im4 = render([(parts['P3'], c)], eye=(0, -40, -60), target=(0, 20, 125), up=(0, 1, 0), fov=55, W=1000, H=600, edges=True)
grid([label(im1, 'span seam face of part 1: 30-degree tongue between two pin holes'), label(im2, 'groove face of part 3 with its two pin holes'),
      label(im3, 'front/rear cut opened: the pins (orange) between parts 3 and 4'), label(im4, 'cut face of part 3: pin holes only')], cols=2).save(f'{DOC}/v13_joints.png')

# 4. joint detail
tan = np.tan(np.radians(CHAMFER_DEG)); wt = TONGUE_BASE - 2 * TONGUE_H * tan; gm = TONGUE_BASE + 2 * CLEAR; gd = TONGUE_H + GROOVE_EXTRA
fig, axs = plt.subplots(1, 2, figsize=(12, 5)); sk = T_SKIN; L_ = 10.0
ax = axs[0]
ax.add_patch(MPoly([(-L_, -sk / 2), (0, -sk / 2), (0, -TONGUE_BASE / 2), (TONGUE_H, -wt / 2), (TONGUE_H, wt / 2), (0, TONGUE_BASE / 2), (0, sk / 2), (-L_, sk / 2)], fc='#d9dde4', ec='k', lw=1.2))
ax.add_patch(MPoly([(L_, -sk / 2), (0.05, -sk / 2), (0.05, -gm / 2), (0.05 + gd, -(gm - 2 * gd * tan) / 2), (0.05 + gd, (gm - 2 * gd * tan) / 2), (0.05, gm / 2), (0.05, sk / 2), (L_, sk / 2)], fc='#e8964688', ec='#b85c1a', lw=1.2))
ax.text(-L_ + 0.4, sk / 2 + 0.6, 'side part (tongue)', fontsize=9); ax.text(1.2, sk / 2 + 0.6, 'centre part (groove)', fontsize=9)
ax.text(-9.6, -5.6, 'tongue %.1f wide, %.1f tall,\nsides %d° off the joining direction' % (TONGUE_BASE, TONGUE_H, CHAMFER_DEG), fontsize=8)
ax.text(2.2, -5.6, 'groove %.1f wide, %.1f deep\n(%.1f mm a side)' % (gm, gd, CLEAR), fontsize=8)
ax.set_xlim(-L_ - 0.5, L_ + 0.5); ax.set_ylim(-7.2, 6.2); ax.set_aspect('equal'); ax.axis('off'); ax.set_title('span seams: tongue and groove (mm)', fontsize=10)
ax = axs[1]; r = HOLE_D / 2
a_ = np.linspace(0.25 * np.pi, 1.75 * np.pi, 60); td = np.vstack([[0, r * np.sqrt(2)], np.column_stack([r * np.sin(a_), r * np.cos(a_)])])
ax.add_patch(MPoly(td + [-4.5, 0], fc='white', ec='k', lw=1.0)); ax.add_patch(plt.Circle((-4.5, 0), PIN_D / 2, fc='#f07828', ec='k', lw=0.8))
ax.add_patch(plt.Circle((4.5, 0), r, fc='white', ec='k', lw=1.0)); ax.add_patch(plt.Circle((4.5, 0), PIN_D / 2, fc='#f07828', ec='k', lw=0.8))
ax.annotate('', (-4.5, 3.6), (-4.5, 5.2), arrowprops=dict(arrowstyle='<-')); ax.text(-4.5, 5.4, 'up as printed', fontsize=8, ha='center')
ax.text(-4.5, -3.6, 'span seams:\nteardrop hole, %.1f mm' % HOLE_D, fontsize=8, ha='center', va='top')
ax.text(4.5, -3.6, 'front/rear cuts (pins only):\nround hole, %.1f mm,\npointed end' % HOLE_D, fontsize=8, ha='center', va='top')
ax.text(0, 6.6, 'pins %.0f x %.0f mm in holes %.1f deep each side, 30° lead-in' % (PIN_D, PIN_L, HOLE_DEPTH), fontsize=8, ha='center')
ax.set_xlim(-9, 9); ax.set_ylim(-7.5, 7.5); ax.set_aspect('equal'); ax.axis('off'); ax.set_title('pin holes, across the pin (mm)', fontsize=10)
plt.tight_layout(); plt.savefig(f'{DOC}/v13_joint_detail.png', dpi=120); plt.close()

# 5. sections
fig, axs = plt.subplots(3, 1, figsize=(12, 10))
for ax, (x, pp) in zip(axs, [(-100.0, ('P3', 'P4')), (-330.0, ('P1', 'P2')), (-470.0, ('P1', 'P2'))]):
    for mesh, kw in [(E, dict(fc='#d9dde4', ec='#9aa3b0', lw=1.0, label='v8: solid'))] + [(parts[p], dict(fc='#e8964688', ec='#b85c1a', lw=1.2, label='v13: part %s' % p[1])) for p in pp]:
        s = mesh.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
        if s is None: continue
        for i, d in enumerate(s.discrete): ax.add_patch(MPoly(d[:, [2, 1]], closed=True, **(kw if i == 0 else {k: v for k, v in kw.items() if k != 'label'})))
    ax.autoscale(); ax.set_aspect('equal'); ax.grid(alpha=0.3); ax.legend(loc='upper right', fontsize=8)
    ax.set_title('section at x = %.0f mm: greatest thickness of these parts %.1f / %.1f mm' % (x, V['thickness'][pp[0]]['max_mm'], V['thickness'][pp[1]]['max_mm']), fontsize=10)
plt.tight_layout(); plt.savefig(f'{DOC}/v13_sections.png', dpi=110); plt.close()

# 6. bed layouts
P = json.load(open(f'{OUT}/print_report.json')); ims = []
for pid in IDS:
    m = trimesh.load(f'{PRN}/{STEM[pid]}.stl')
    bed = trimesh.creation.box(extents=[420, 420, 2]); bed.apply_translation([210, 210, -1.2])
    im = render([(bed, (60, 64, 72)), (m, COL[pid])], eye=(210 + 520, 210 - 620, 470), target=(210, 210, 70), up=(0, 0, 1), fov=40, W=700, H=520, edges=True)
    r_ = P[pid]
    ims.append(label(im, '%s %s: %.0f x %.0f x %.0f mm, %s' % (pid[1], STEM[pid].replace('v13_', '').split('_', 1)[1], *r_['print_extent_mm'],
               'no support' if r_['overhang_gt55_cm2'] < 3 else 'no support (%.0f cm2 of short bridges)' % r_['overhang_gt55_cm2']), size=16))
m = trimesh.load(f'{PRN}/v13_PIN_3x18.stl'); c0 = m.bounds.mean(0)
im = render([(m, (232, 150, 70))], eye=(c0[0] + 14, c0[1] - 22, c0[2] + 10), target=c0, up=(0, 0, 1), fov=45, W=700, H=520, edges=True)
ims.append(label(im, 'the pin, 3 x 18 mm: one model, print %d (%d + 4 spare)' % (P['PIN']['print_count'], J['n_pins']), size=16))
grid(ims, cols=4).save(f'{DOC}/v13_bed_layouts.png')
print('figures written to', DOC)
