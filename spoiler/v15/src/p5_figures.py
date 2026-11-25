"""v15 step 5: figures in v15/docs/.
  v15_parts.png         the six parts, numbered as marked, from above-behind and from below
  v15_shell.png         the thin shell: sections at the centre and the outer zone (4 mm skin, solid front band, the
                        opening's 30-degree front ramp, the shell wrapping round the back edge), close-ups from below
  v15_cut_v14_v15.png   the cut faces you marked: v14 (skin, cavity and closed underside) against v15 (the 4 mm shell),
                        at the span seam and at the front/rear cut
  v15_back_v14_v15.png  the underside at the back in v14 (closed) and v15 (open, smooth), same cameras
  v15_joints.png        the joint faces: tongue and groove at a span seam, pin holes at a front/rear cut
  v15_joint_detail.png  dimensioned tongue/groove and both pin holes
  v15_sections.png      v8 solid against v15 cored
  v15_bed_layouts.png   the print set on the 420 x 420 mm bed: the six parts and the pin
Run from spoiler/:  python3 v15/src/p5_figures.py"""
import sys, os, json; sys.path.insert(0, 'v15/src'); sys.path.insert(0, 'v6/src')
import numpy as np, trimesh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
from PIL import Image, ImageDraw, ImageFont
from trimesh.ray.ray_pyembree import RayMeshIntersector
from functools import partial
from zr import render as zrender, grid, label, look_at
# per-corner normals: the opening's 30-degree edges are creases lined with thin boolean slivers, and normals smoothed
# across them draw a false saw-tooth along each edge; shading each corner from the faces near its own face keeps it clean
render = partial(zrender, corner=20.0)
from bowtie import tomf, totm
from layout import (E_PATH, CAR_PATH, OUT, ASM, PRN, DOC, IDS, STEM, LABEL, SEC, HALF_OF, XS, T_SKIN, LAND_T, OPEN_H,
                    TONGUE_BASE, TONGUE_H, CLEAR, GROOVE_EXTRA, CHAMFER_DEG, HOLE_D, HOLE_DEPTH, PIN_D, PIN_L, chord_plane)
os.makedirs(DOC, exist_ok=True)
parts = {pid: trimesh.load(f'{ASM}/{STEM[pid]}.stl') for pid in IDS}
J = json.load(open(f'{OUT}/joints.json')); V = json.load(open(f'{OUT}/validation.json'))
pins = [trimesh.load(f'{ASM}/v15_PIN_{i + 1:02d}.stl') for i in range(J['n_pins'])]
COL = {'P1': (232, 150, 70), 'P2': (205, 210, 220), 'P3': (120, 170, 230), 'P4': (240, 200, 110), 'P5': (232, 150, 70), 'P6': (205, 210, 220)}
FONT = lambda sz: ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', sz)
c = (205, 208, 215)

def proj(eye, tgt, fov, W, H, P):
    e, r, u, f = look_at(eye, tgt); fp = 0.5 * H / np.tan(np.radians(fov) / 2); q = np.asarray(P, float) - e; z = q @ f
    return np.column_stack([W / 2 + fp * (q @ r) / z, H / 2 - fp * (q @ u) / z])

def numbered(eye, tgt, fov, W, H, side):
    im = render([(parts[p], COL[p]) for p in IDS], eye=eye, target=tgt, up=(0, 1, 0), fov=fov, W=W, H=H, edges=True)
    d = ImageDraw.Draw(im)
    for p in IDS:
        m = parts[p]; cc = m.vertices[np.argsort(m.vertices[:, 1])]                 # a point on the visible side
        pt = cc[-len(cc) // 6:].mean(0) if side == 'top' else cc[:len(cc) // 6].mean(0)
        x, y = proj(eye, tgt, fov, W, H, [pt])[0]
        d.text((x, y), p[1], fill=(25, 25, 30), font=FONT(46), anchor='mm', stroke_width=3, stroke_fill=(255, 255, 255))
    return im

def outline(ax, mesh, origin, normal, axes, **kw):
    """the section of mesh by the plane, drawn in the plane's coordinates axes = (i, j) of the 3D point"""
    s_ = mesh.section(plane_origin=origin, plane_normal=normal)
    if s_ is None: return None
    for i, d in enumerate(s_.discrete):
        ax.add_patch(MPoly(d[:, list(axes)], closed=True, **(kw if i == 0 else {k: v for k, v in kw.items() if k != 'label'})))
    return s_

# 1. parts
a = numbered((0, 900, 1250), (0, -10, 110), 40, 1400, 800, 'top')
b = numbered((0, -1150, 650), (0, -10, 110), 40, 1400, 800, 'bottom')
grid([label(a, 'v15: six parts as marked - 3 across (cut at x = +-216.7 mm), each cut into a front and a rear part'),
      label(b, 'from below: a 4 mm shell, open underneath - 1, 3, 5 rear parts, 2, 4, 6 front parts (2 and 6 carry the fins)')], cols=1).save(f'{DOC}/v15_parts.png')

# 2. the shell: sections (original solid, v15 part, car) and close-ups from below (from the full-resolution cored sections:
# the part files are decimated to within 0.02 mm, which is invisible in print but shows as facets in a macro render)
def full_rear(sec):
    n, d = chord_plane(sec); return totm(tomf(trimesh.load(f'{OUT}/cored_{sec}.stl')).trim_by_plane(list(n), d))
FULL = {'P3': full_rear('C'), 'P1': full_rear('L')}
FULL['P3'].export(f'{OUT}/full_P3.stl')                              # for the studio close-up (blend_scene.py rim)
E = trimesh.load(E_PATH); car = trimesh.load(CAR_PATH, process=False)
_st = np.load(f'{OUT}/rim_curve.npz'); _o = np.argsort(_st['x']); RIM = np.column_stack([_st['x'][_o], _st['z'][_o]])
fig, axs = plt.subplots(2, 1, figsize=(15, 9.6))
for ax, (x, pp) in zip(axs, [(-100.0, ('P3', 'P4')), (-440.0, ('P1', 'P2'))]):
    outline(ax, E, [x, 0, 0], [1, 0, 0], (2, 1), fc='#eef0f3', ec='#b9bec7', lw=0.8, label='solid spoiler (v8-v14 outside)')
    for k, p in enumerate(pp):
        outline(ax, parts[p], [x, 0, 0], [1, 0, 0], (2, 1), fc='#e8964699', ec='#a5521a', lw=1.1, label='v15 parts %s and %s' % (pp[0][1], pp[1][1]) if k == 0 else None)
    s_ = car.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
    for i, d in enumerate(s_.discrete): ax.plot(d[:, 2], d[:, 1], color='#2b6cd6', lw=0.9, label='car' if i == 0 else None)
    b_ = E.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0]).bounds
    z0, z1, y0, y1 = b_[0, 2], b_[1, 2], b_[0, 1], b_[1, 1]
    R = RayMeshIntersector(parts[pp[0]]); R2 = RayMeshIntersector(parts[pp[1]])
    def hits(z, RR):
        loc, _, _ = RR.intersects_location([[x, y0 - 30, z]], [[0, 1.0, 0]], multiple_hits=True)
        return np.sort(loc[:, 1]) if len(loc) else np.array([])
    zm = z0 + 0.62 * (z1 - z0) if x > -216 else z0 + 0.45 * (z1 - z0)
    h = hits(zm, R)
    if len(h) >= 2:
        ax.annotate('skin %.1f mm' % (h[-1] - h[-2]), (zm, 0.5 * (h[-1] + h[-2])), (zm - 25, y1 + 9), fontsize=9, ha='center', arrowprops=dict(arrowstyle='->', lw=0.8))
        ax.annotate('open underneath: nothing\nbut the 4 mm skin here', (zm + 4, h[-2] - 2.5), (zm - 12, y0 - 9), fontsize=9, ha='center', arrowprops=dict(arrowstyle='->', lw=0.8))
    zf = z0 + 0.12 * (z1 - z0)
    ax.annotate('solid where thinner than %.0f mm\n(the tape band at the front)' % OPEN_H, (zf, y1 - 0.25 * (y1 - y0)), (zf + 8, y1 + 12), fontsize=9, ha='center', arrowprops=dict(arrowstyle='->', lw=0.8))
    zb = float(np.interp(x, RIM[:, 0], RIM[:, 1])) - 2.0                  # the shell's edge along the rim line
    loc, _, _ = RayMeshIntersector(E).intersects_location([[x, y0 - 30, zb]], [[0, 1.0, 0]], multiple_hits=False)
    yb = float(loc[0, 1]) if len(loc) else y0
    ax.annotate('back edge: no band, no brim - the %.0f mm shell wraps round it;\nits edge on the car takes the adhesive' % T_SKIN, (zb, yb), (zb + 0.02 * (z1 - z0), y0 - 22), fontsize=9, ha='center', arrowprops=dict(arrowstyle='->', lw=0.8))
    ax.set_xlim(z0 - 4, z1 + 6); ax.set_ylim(y0 - 27, y1 + 18); ax.set_aspect('equal'); ax.grid(alpha=0.25)
    ax.legend(loc='upper right', fontsize=8, framealpha=0.9)
    ax.set_title('section at x = %.0f mm (%s), z to the rear: one opening: a %d-degree ramp at the front, open right to the back edge; '
                 'joint land %.1f mm at the front/rear cut' % (x, 'centre' if x > -216 else 'outer zone', 30, LAND_T), fontsize=10)
plt.tight_layout(); plt.savefig(f'{DOC}/_shell_sec.png', dpi=105); plt.close()
sec = Image.open(f'{DOC}/_shell_sec.png'); os.remove(f'{DOC}/_shell_sec.png')
r1 = render([(FULL['P3'], c)], eye=(-120, -150, 330), target=(-100, 15, 190), up=(0, 1, 0), fov=40, W=900, H=560, spec=0.3)
r2 = render([(FULL['P3'], c)], eye=(-60, -260, 60), target=(-60, 15, 165), up=(0, 1, 0), fov=52, W=900, H=560, spec=0.3)
r3 = render([(FULL['P1'], c)], eye=(-430, -160, 300), target=(-440, 0, 170), up=(0, 1, 0), fov=44, W=900, H=560, spec=0.3)
row = grid([label(r1, 'from below-behind: the back edge and the lip (part 3)', size=18), label(r2, 'from below-front: into the shell (part 3)', size=18),
            label(r3, 'outer zone from below-behind (part 1)', size=18)], cols=3)
W = max(sec.width, row.width); canvas = Image.new('RGB', (W, sec.height + row.height), (255, 255, 255))
canvas.paste(sec, ((W - sec.width) // 2, 0)); canvas.paste(row.resize((W, int(row.height * W / row.width))) if row.width != W else row, (0, sec.height))
canvas.save(f'{DOC}/v15_shell.png')

# 3. v14 against v15: the cut faces you marked (section outlines in the cut planes), and the underside at the back
V14 = 'v14/out/assembled'
if os.path.exists(f'{V14}/v14_3_CENTRE_REAR.stl'):
    old = {k: trimesh.load(f'{V14}/v14_{k}.stl') for k in ('1_LEFT_REAR', '2_LEFT_FRONT', '3_CENTRE_REAR', '4_CENTRE_FRONT')}
    new = {k: parts[p] for k, p in (('1_LEFT_REAR', 'P1'), ('2_LEFT_FRONT', 'P2'), ('3_CENTRE_REAR', 'P3'), ('4_CENTRE_FRONT', 'P4'))}
    n_c, d_c = chord_plane('C')
    cuts = [('span seam x = -216.7 mm, part 1 (left rear)', '1_LEFT_REAR', [-XS - 0.05, 0, 0], [1, 0, 0], (2, 1)),
            ('span seam x = -216.7 mm, part 2 (left front)', '2_LEFT_FRONT', [-XS - 0.05, 0, 0], [1, 0, 0], (2, 1)),
            ('front/rear cut z = %.0f mm, part 3 (centre rear)' % d_c, '3_CENTRE_REAR', [0, 0, d_c + 0.05], [0, 0, 1], (0, 1))]
    fig, axs = plt.subplots(3, 2, figsize=(16, 10.5), gridspec_kw=dict(width_ratios=[1, 1]))
    for row, (title, k, o, nrm, axes) in zip(axs, cuts):
        lims = []
        for ax, (tag, src, kw) in zip(row, (('v14: skin, cavity and closed underside', old, dict(fc='#c9ced6', ec='#5d6674', lw=1.0)),
                                            ('v15: the %.0f mm shell (joint land %.1f mm at the cut)' % (T_SKIN, LAND_T), new, dict(fc='#e8964699', ec='#a5521a', lw=1.2)))):
            s_ = src[k].section(plane_origin=o, plane_normal=nrm)
            polys = [d[:, list(axes)] for d in s_.discrete] if s_ is not None else []
            for d in polys: ax.add_patch(MPoly(d, closed=True, **kw))
            area = s_.to_planar()[0].area / 100 if s_ is not None else 0.0
            ax.set_title('%s\n%s: cut face %.0f cm2' % (title, tag, area), fontsize=9)
            if polys: P_ = np.vstack(polys); lims.append((P_.min(0), P_.max(0)))
            ax.set_aspect('equal'); ax.grid(alpha=0.25)
        lo_ = np.min([l[0] for l in lims], axis=0) - 3; hi_ = np.max([l[1] for l in lims], axis=0) + 3
        for ax in row: ax.set_xlim(lo_[0], hi_[0]); ax.set_ylim(lo_[1], hi_[1]); ax.set_xlabel('x (mm, across)' if k.startswith('3') else 'z (mm, to the rear)', fontsize=8)
    plt.tight_layout(); plt.savefig(f'{DOC}/v15_cut_v14_v15.png', dpi=100); plt.close()
    cams = [dict(eye=(-290, -95, 150), target=(-205, 14, 205), up=(0, 1, 0), fov=30),
            dict(eye=(-300, -75, 120), target=(-330, 8, 196), up=(0, 1, 0), fov=34),
            dict(eye=(-480, -420, 120), target=(-500, 0, 130), up=(0, 0, 1), fov=40),
            dict(eye=(-160, -330, 40), target=(-150, 10, 150), up=(0, 1, 0), fov=50)]
    oc, gc = (230, 150, 80), (200, 205, 215)
    sets = [('3_CENTRE_REAR',), ('1_LEFT_REAR',), ('1_LEFT_REAR', '2_LEFT_FRONT'), ('3_CENTRE_REAR', '4_CENTRE_FRONT')]
    names = ['the cut end of part 3', 'part 1, outer zone', 'left end from below', 'centre from below-front']
    ims = []
    for cam, keys, nm in zip(cams, sets, names):
        for tag, src in (('v14: closed underside (thick)', old), ('v15: thin shell, open, smooth', new)):
            ims.append(label(render([(src[k], oc if 'REAR' in k else gc) for k in keys], W=760, H=520, edges=False, spec=0.2, **cam),
                             '%s (%s)' % (tag, nm), size=17, fill=(255, 220, 120)))
    grid(ims, cols=2).save(f'{DOC}/v15_back_v14_v15.png')

# 4. joints
o = (240, 120, 40)
im1 = render([(parts['P1'], c)], eye=(-XS + 140, 75, 215), target=(-XS, 18, 175), up=(0, 1, 0), fov=30, W=1000, H=600, edges=True)
im2 = render([(parts['P3'], c)], eye=(-XS - 130, 70, 210), target=(-XS, 20, 170), up=(0, 1, 0), fov=30, W=1000, H=600, edges=True)
P4x = parts['P4'].copy(); n, d = chord_plane('C'); P4x.apply_translation(-n * 70)
im3 = render([(P4x, c), (parts['P3'], c)] + [(p, o) for p in pins if abs(p.centroid[2] - 122) < 15],
             eye=(0, 330, 40), target=(0, 5, 95), up=(0, 1, 0), fov=50, W=1000, H=600, edges=True)
im4 = render([(parts['P3'], c)], eye=(0, -40, -60), target=(0, 20, 125), up=(0, 1, 0), fov=55, W=1000, H=600, edges=True)
grid([label(im1, 'span seam face of part 1: 30-degree tongue and the pin holes, on the joint land'), label(im2, 'groove face of part 3 with its pin holes'),
      label(im3, 'front/rear cut opened: the pins (orange) between parts 3 and 4'), label(im4, 'cut face of part 3: pin holes in the joint land')], cols=2).save(f'{DOC}/v15_joints.png')

# 5. joint detail
tan = np.tan(np.radians(CHAMFER_DEG)); wt = TONGUE_BASE - 2 * TONGUE_H * tan; gm = TONGUE_BASE + 2 * CLEAR; gd = TONGUE_H + GROOVE_EXTRA
fig, axs = plt.subplots(1, 2, figsize=(12, 5)); sk = LAND_T; L_ = 10.0
ax = axs[0]
ax.add_patch(MPoly([(-L_, -sk / 2), (0, -sk / 2), (0, -TONGUE_BASE / 2), (TONGUE_H, -wt / 2), (TONGUE_H, wt / 2), (0, TONGUE_BASE / 2), (0, sk / 2), (-L_, sk / 2)], fc='#d9dde4', ec='k', lw=1.2))
ax.add_patch(MPoly([(L_, -sk / 2), (0.05, -sk / 2), (0.05, -gm / 2), (0.05 + gd, -(gm - 2 * gd * tan) / 2), (0.05 + gd, (gm - 2 * gd * tan) / 2), (0.05, gm / 2), (0.05, sk / 2), (L_, sk / 2)], fc='#e8964688', ec='#b85c1a', lw=1.2))
ax.text(-L_ + 0.4, sk / 2 + 0.6, 'side part (tongue)', fontsize=9); ax.text(1.2, sk / 2 + 0.6, 'centre part (groove)', fontsize=9)
ax.text(-9.6, -6.2, 'tongue %.1f wide, %.1f tall,\nsides %d° off the joining direction' % (TONGUE_BASE, TONGUE_H, CHAMFER_DEG), fontsize=8)
ax.text(2.2, -6.2, 'groove %.1f wide, %.1f deep\n(%.1f mm a side)' % (gm, gd, CLEAR), fontsize=8)
ax.text(0, -8.0, 'in the %.1f mm joint land along the cut' % LAND_T, fontsize=8, ha='center')
ax.set_xlim(-L_ - 0.5, L_ + 0.5); ax.set_ylim(-8.8, 6.6); ax.set_aspect('equal'); ax.axis('off'); ax.set_title('span seams: tongue and groove (mm)', fontsize=10)
ax = axs[1]; r = HOLE_D / 2
a_ = np.linspace(0.25 * np.pi, 1.75 * np.pi, 60); td = np.vstack([[0, r * np.sqrt(2)], np.column_stack([r * np.sin(a_), r * np.cos(a_)])])
ax.add_patch(MPoly(td + [-4.5, 0], fc='white', ec='k', lw=1.0)); ax.add_patch(plt.Circle((-4.5, 0), PIN_D / 2, fc='#f07828', ec='k', lw=0.8))
ax.add_patch(plt.Circle((4.5, 0), r, fc='white', ec='k', lw=1.0)); ax.add_patch(plt.Circle((4.5, 0), PIN_D / 2, fc='#f07828', ec='k', lw=0.8))
ax.annotate('', (-4.5, 3.6), (-4.5, 5.2), arrowprops=dict(arrowstyle='<-')); ax.text(-4.5, 5.4, 'up as printed', fontsize=8, ha='center')
ax.text(-4.5, -3.6, 'span seams:\nteardrop hole, %.1f mm' % HOLE_D, fontsize=8, ha='center', va='top')
ax.text(4.5, -3.6, 'front/rear cuts (pins only):\nround hole, %.1f mm,\npointed end' % HOLE_D, fontsize=8, ha='center', va='top')
ax.text(0, 6.6, 'pins %.0f x %.0f mm in holes %.1f deep each side, 30° lead-in' % (PIN_D, PIN_L, HOLE_DEPTH), fontsize=8, ha='center')
ax.set_xlim(-9, 9); ax.set_ylim(-7.5, 7.5); ax.set_aspect('equal'); ax.axis('off'); ax.set_title('pin holes, across the pin (mm)', fontsize=10)
plt.tight_layout(); plt.savefig(f'{DOC}/v15_joint_detail.png', dpi=120); plt.close()

# 6. sections
fig, axs = plt.subplots(3, 1, figsize=(12, 10))
for ax, (x, pp) in zip(axs, [(-100.0, ('P3', 'P4')), (-330.0, ('P1', 'P2')), (-470.0, ('P1', 'P2'))]):
    for mesh, kw in [(E, dict(fc='#d9dde4', ec='#9aa3b0', lw=1.0, label='v8: solid'))] + [(parts[p], dict(fc='#e8964688', ec='#b85c1a', lw=1.2, label='v15: part %s' % p[1])) for p in pp]:
        s = mesh.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
        if s is None: continue
        for i, d in enumerate(s.discrete): ax.add_patch(MPoly(d[:, [2, 1]], closed=True, **(kw if i == 0 else {k: v for k, v in kw.items() if k != 'label'})))
    ax.autoscale(); ax.set_aspect('equal'); ax.grid(alpha=0.3); ax.legend(loc='upper right', fontsize=8)
    ax.set_title('section at x = %.0f mm: greatest thickness of these parts %.1f / %.1f mm' % (x, V['thickness'][pp[0]]['max_mm'], V['thickness'][pp[1]]['max_mm']), fontsize=10)
plt.tight_layout(); plt.savefig(f'{DOC}/v15_sections.png', dpi=110); plt.close()

# 7. bed layouts
P = json.load(open(f'{OUT}/print_report.json')); ims = []
for pid in IDS:
    m = trimesh.load(f'{PRN}/{STEM[pid]}.stl')
    bed = trimesh.creation.box(extents=[420, 420, 2]); bed.apply_translation([210, 210, -1.2])
    im = render([(bed, (60, 64, 72)), (m, COL[pid])], eye=(210 + 520, 210 - 620, 470), target=(210, 210, 70), up=(0, 0, 1), fov=40, W=700, H=520, edges=True)
    r_ = P[pid]
    ims.append(label(im, '%s %s: %.0f x %.0f x %.0f mm, %s' % (pid[1], STEM[pid].replace('v15_', '').split('_', 1)[1], *r_['print_extent_mm'],
               'no support' if r_['overhang_gt55_cm2'] < 3 else 'no support (%.0f cm2 of short bridges)' % r_['overhang_gt55_cm2']), size=16))
m = trimesh.load(f'{PRN}/v15_PIN_3x18.stl'); c0 = m.bounds.mean(0)
im = render([(m, (232, 150, 70))], eye=(c0[0] + 14, c0[1] - 22, c0[2] + 10), target=c0, up=(0, 0, 1), fov=45, W=700, H=520, edges=True)
ims.append(label(im, 'the pin, 3 x 18 mm: one model, print %d (%d + 4 spare)' % (P['PIN']['print_count'], J['n_pins']), size=16))
grid(ims, cols=4).save(f'{DOC}/v15_bed_layouts.png')
print('figures written to', DOC)
