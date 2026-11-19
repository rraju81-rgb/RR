"""v9 step 5: figures in v9/docs/.
  v9_assembled.png      the six pieces in place, from above and from below (pockets)
  v9_section.png        cross-sections: the v8 solid against the v9 cored skin, thickness coloured
  v9_joints.png         tongue face, groove face, an exploded seam with its pins, the centre spline
  v9_joint_detail.png   dimensioned section through the tongue and groove (30-degree flanks) and a pin hole
  v9_bed_layouts.png    every print file on the 420 x 420 mm bed
Run from spoiler/:  python3 v9/src/p5_figures.py"""
import sys, os, json; sys.path.insert(0, 'v9/src'); sys.path.insert(0, 'v6/src')
import numpy as np, trimesh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
from zr import render, grid, label
from layout import (E_PATH, OUT, ASM, PRN, DOC, IDS, STEM, LABEL, SEAMS, T_SKIN, TONGUE_BASE, TONGUE_H, CLEAR, GROOVE_EXTRA,
                    CHAMFER_DEG, HOLE_D, HOLE_DEPTH, PIN_D, PIN_L, HOLE_CHAMFER)
os.makedirs(DOC, exist_ok=True)
parts = {pid: trimesh.load(f'{ASM}/{STEM[pid]}.stl') for pid in IDS}
COL = [(205, 210, 220), (232, 150, 70), (205, 210, 220), (232, 150, 70), (205, 210, 220), (232, 150, 70)]
items = [(parts[pid], COL[i]) for i, pid in enumerate(IDS)]
spline = trimesh.load(f'{ASM}/v9_CENTRE_SPLINE.stl')
J = json.load(open(f'{OUT}/joints.json')); V = json.load(open(f'{OUT}/validation.json'))
pins = [trimesh.load(f'{ASM}/v9_PIN_{i + 1:02d}.stl') for i in range(J['n_pins'])]

# 1. assembled
a = render(items, eye=(0, 900, 1250), target=(0, -10, 110), up=(0, 1, 0), fov=40, W=1400, H=800, edges=True)
b = render(items, eye=(0, -1150, 650), target=(0, -10, 110), up=(0, 1, 0), fov=40, W=1400, H=800, edges=True)
grid([label(a, 'v9: six equal pieces (216.7 mm each), from above and behind'),
      label(b, 'from below: the underside is cored (pockets), every visible surface is unchanged')], cols=1).save(f'{DOC}/v9_assembled.png')

# 2. sections v8 solid vs v9 cored
E = trimesh.load(E_PATH)
fig, axs = plt.subplots(3, 1, figsize=(12, 10))
for ax, (x, pid) in zip(axs, [(-300.0, 'P2'), (-100.0, 'P3'), (-560.0, 'P1')]):
    for mesh, kw in [(E, dict(fc='#d9dde4', ec='#9aa3b0', lw=1.0, label='v8: solid')), (parts[pid], dict(fc='#e8964688', ec='#b85c1a', lw=1.2, label='v9: cored'))]:
        s = mesh.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
        if s is None: continue
        for i, d in enumerate(s.discrete):
            ax.add_patch(MPoly(d[:, [2, 1]], closed=True, **(kw if i == 0 else {k: v for k, v in kw.items() if k != 'label'})))
    ax.autoscale(); ax.set_aspect('equal'); ax.grid(alpha=0.3); ax.legend(loc='upper left', fontsize=8)
    ax.set_title('section at x = %.0f mm (%s): greatest thickness of the piece %.1f mm' % (x, LABEL[pid], V['thickness'][pid]['max_mm']), fontsize=10)
    ax.set_xlabel('z (mm, to the rear)'); ax.set_ylabel('y (mm)')
plt.tight_layout(); plt.savefig(f'{DOC}/v9_section.png', dpi=110); plt.close()

# 3. joints
c = (205, 208, 215); o = (240, 120, 40)
P1, P2, P3, P4 = parts['P1'], parts['P2'], parts['P3'], parts['P4']
s0 = SEAMS[0]
im1 = render([(P2, c)], eye=(s0 - 130, 60, 140), target=(s0, 12, 120), up=(0, 1, 0), fov=28, W=1000, H=560, edges=True)
im2 = render([(P1, c)], eye=(s0 + 130, 60, 140), target=(s0, 12, 120), up=(0, 1, 0), fov=28, W=1000, H=560, edges=True)
P1x = P1.copy(); P1x.apply_translation([-45, 0, 0]); near = [p for p in pins if abs(p.centroid[0] - s0) < 1]
im3 = render([(P1x, c), (P2, c)] + [(p, o) for p in near], eye=(s0 - 40, 160, -150), target=(s0 - 15, 10, 120), up=(0, 1, 0), fov=40, W=1000, H=560, edges=True)
P3x = P3.copy(); P3x.apply_translation([-30, 0, 0]); P4x = P4.copy(); P4x.apply_translation([30, 0, 0])
pc = [p for p in pins if abs(p.centroid[0]) < 1]
im4 = render([(P3x, c), (P4x, c), (spline, o)] + [(p, o) for p in pc], eye=(-60, 170, -140), target=(0, 30, 140), up=(0, 1, 0), fov=40, W=1000, H=560, edges=True)
grid([label(im1, 'tongue face (male): 30-degree chamfered tongue between two pin holes'), label(im2, 'groove face (female): matching groove and pin holes'),
      label(im3, 'a seam opened up: 3 mm pins (orange) in both faces'), label(im4, 'centre seam: groove to groove, with the loose spline and pins')], cols=2).save(f'{DOC}/v9_joints.png')

# 4. dimensioned joint detail (section across the tongue, in the plane of the joining direction)
tan = np.tan(np.radians(CHAMFER_DEG)); wt = TONGUE_BASE - 2 * TONGUE_H * tan; gm = TONGUE_BASE + 2 * CLEAR; gd = TONGUE_H + GROOVE_EXTRA
fig, axs = plt.subplots(1, 2, figsize=(13, 5.2))
ax = axs[0]; sk = T_SKIN; L = 10.0
ax.add_patch(MPoly([(-L, -sk / 2), (0, -sk / 2), (0, -TONGUE_BASE / 2), (TONGUE_H, -wt / 2), (TONGUE_H, wt / 2), (0, TONGUE_BASE / 2), (0, sk / 2), (-L, sk / 2)], fc='#d9dde4', ec='k', lw=1.2))
ax.add_patch(MPoly([(L, -sk / 2), (0.05, -sk / 2), (0.05, -gm / 2), (0.05 + gd, -(gm - 2 * gd * tan) / 2), (0.05 + gd, (gm - 2 * gd * tan) / 2), (0.05, gm / 2), (0.05, sk / 2), (L, sk / 2)], fc='#e8964688', ec='#b85c1a', lw=1.2))
ax.text(-L + 0.5, sk / 2 - 1.0, 'tongue piece', fontsize=9); ax.text(3.2, sk / 2 - 1.0, 'groove piece', fontsize=9)
ax.text(-7.6, -2.7, 'tongue: %.1f wide at the face,\n%.1f tall, sides %d deg off the\njoining direction, top %.1f wide' % (TONGUE_BASE, TONGUE_H, CHAMFER_DEG, wt), fontsize=8, va='center')
ax.text(3.6, -sk / 2 + 0.6, 'groove %.1f wide, %.1f deep\n(%.1f mm clearance a side)' % (gm, gd, CLEAR), fontsize=8)
ax.annotate('', (-L + 1, -sk / 2), (-L + 1, sk / 2), arrowprops=dict(arrowstyle='<->')); ax.text(-L + 1.3, 0, 'skin\n%.1f' % sk, fontsize=8, va='center')
ax.arrow(-6, -6.2, 4.5, 0, head_width=0.4, color='tab:blue'); ax.text(-6, -7.1, 'pieces slide together this way', fontsize=8, color='tab:blue')
ax.set_xlim(-L - 0.5, L + 0.5); ax.set_ylim(-7.8, 6); ax.set_aspect('equal'); ax.set_title('tongue and groove, across the joint (mm)', fontsize=10); ax.axis('off')
ax = axs[1]; r = HOLE_D / 2; lead = HOLE_CHAMFER / tan
for side, col in ((-1, '#d9dde4'), (1, '#e8964688')):
    ax.add_patch(MPoly([(0.05 * side, -sk / 2), (side * 13, -sk / 2), (side * 13, sk / 2), (0.05 * side, sk / 2)], fc=col, ec='k', lw=1.0))
    ax.add_patch(MPoly([(0.05 * side, -r - HOLE_CHAMFER), (side * lead, -r), (side * HOLE_DEPTH, -r), (side * (HOLE_DEPTH + r), 0), (side * HOLE_DEPTH, r), (side * lead, r), (0.05 * side, r + HOLE_CHAMFER)], fc='white', ec='k', lw=0.8))
ax.add_patch(MPoly([(-PIN_L / 2, -PIN_D / 2), (PIN_L / 2, -PIN_D / 2), (PIN_L / 2, PIN_D / 2), (-PIN_L / 2, PIN_D / 2)], fc='#f07828', ec='k', lw=0.8, alpha=0.9))
ax.text(-12.5, sk / 2 + 0.4, '%.1f mm hole, %.1f deep each side, pointed end (prints without a bridge), 30-degree lead-in' % (HOLE_D, HOLE_DEPTH), fontsize=8)
ax.text(-5, -sk / 2 - 1.2, 'pin: %.0f mm x %.0f mm (steel or brass rod, or printed)' % (PIN_D, PIN_L), fontsize=8, color='#b85c1a')
ax.set_xlim(-14, 14); ax.set_ylim(-7, 6.5); ax.set_aspect('equal'); ax.axis('off'); ax.set_title('pin and hole, along the pin (mm)', fontsize=10)
plt.tight_layout(); plt.savefig(f'{DOC}/v9_joint_detail.png', dpi=120); plt.close()

# 5. bed layouts
P = json.load(open(f'{OUT}/print_report.json'))
ims = []
for pid in IDS:
    m = trimesh.load(f'{PRN}/{STEM[pid]}.stl')
    bed = trimesh.creation.box(extents=[420, 420, 2]); bed.apply_translation([210, 210, -1.2])
    im = render([(bed, (60, 64, 72)), (m, (232, 150, 70))], eye=(210 + 520, 210 - 620, 420), target=(210, 210, 110), up=(0, 0, 1), fov=40, W=700, H=520, edges=True)
    r = P[pid]
    ims.append(label(im, '%s  %s: %.0f x %.0f x %.0f mm, %s' % (pid, STEM[pid].replace('v9_', ''), *r['print_extent_mm'], 'no support' if r['overhang_gt55_cm2'] < 3 else 'fin: %.0f cm2 over 55 deg, hidden side' % r['overhang_gt55_cm2']), size=17))
for f, t in (('v9_PINS_3x18_plate_x14.stl', '14 pins 3 x 18 mm (10 + 4 spare), standing'), ('v9_CENTRE_SPLINE.stl', 'centre spline, on a narrow edge')):
    m = trimesh.load(f'{PRN}/{f}'); c0 = m.bounds.mean(0)
    im = render([(m, (232, 150, 70))], eye=(c0[0] + 60, c0[1] - 90, c0[2] + 70), target=c0, up=(0, 0, 1), fov=45, W=700, H=520, edges=True)
    ims.append(label(im, t, size=17))
grid(ims, cols=4).save(f'{DOC}/v9_bed_layouts.png')
print('figures written to', DOC)
