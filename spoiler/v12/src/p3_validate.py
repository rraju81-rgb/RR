"""v12 step 3: checks on the six parts, the splines and the pins. Stops with an error if one fails.
  - meshes: watertight, consistent winding, one body, no self-intersections, no zero-area faces;
  - each part inside its section (a tongue may stand 2.6 mm proud) and on its side of its front/rear cut;
  - THICKNESS: the largest sphere that fits inside each part (its greatest thickness) is at most 10 mm;
  - joints: no part overlaps a neighbour, a spline or a pin; tongue and spline clearances; pin-hole walls;
  - the outer surfaces of neighbouring parts meet at every seam.
Writes v12/out/validation.json.   Run from spoiler/:  python3 v12/src/p3_validate.py"""
import sys, json; sys.path.insert(0, 'v12/src'); sys.path.insert(0, 'v6/src')
import numpy as np, trimesh
from check import report
from bowtie import tomf
from thickness import max_thickness
from p2_parts import Frame, seam_profile
from layout import OUT, ASM, IDS, STEM, SEC, HALF_OF, SECTIONS, XS, chord_plane, part_id

MAX_T = 10.0
parts = {pid: trimesh.load(f'{ASM}/{STEM[pid]}.stl') for pid in IDS}
J = json.load(open(f'{OUT}/joints.json'))
splines = [trimesh.load(f'{ASM}/v12_SPLINE_{i + 1:02d}.stl') for i in range(J['n_splines'])]
pins = [trimesh.load(f'{ASM}/v12_PIN_{i + 1:02d}.stl') for i in range(J['n_pins'])]
res = dict(meshes={}, extents={}, thickness={}, overlaps={}, clearance={}, seams={}); ok = True
def fail(msg):
    global ok; ok = False; print('   FAIL:', msg)

print('--- meshes')
for k, m in list(parts.items()) + [('SPLINE_%d' % (i + 1), s) for i, s in enumerate(splines)] + [('PIN', pins[0])]:
    r, sx = report(m, k); res['meshes'][k] = r
    good = r['watertight'] and r['winding'] and r['bodies'] == 1 and r['selfx_faces'] == 0 and r['zero_area'] == 0
    print(k, {a: r[a] for a in ['faces', 'watertight', 'winding', 'volume_cm3', 'bodies', 'selfx_faces', 'zero_area']}, 'OK' if good else 'FAIL')
    if not good: fail(f'{k} mesh')

print('--- extents')
secx = {s: (a, b) for s, a, b in SECTIONS}
for pid in IDS:
    m = parts[pid]; x0, x1 = secx[SEC[pid]]; n, d = chord_plane(SEC[pid]); h = m.vertices @ n - d
    side_ok = h.min() >= -0.05 if HALF_OF[pid] == 'rear' else h.max() <= 0.05
    good = m.bounds[0][0] >= x0 - 2.6 and m.bounds[1][0] <= x1 + 2.6 and side_ok
    res['extents'][pid] = dict(x=[round(float(m.bounds[0][0]), 2), round(float(m.bounds[1][0]), 2)], section=[round(x0, 2), round(x1, 2)],
                               cut_side_mm=[round(float(h.min()), 2), round(float(h.max()), 2)])
    print(pid, res['extents'][pid], 'OK' if good else 'FAIL')
    if not good: fail(f'{pid} outside its place')

print('--- thickness (largest sphere inside each part)')
for pid in IDS:
    th, c = max_thickness(parts[pid])
    res['thickness'][pid] = dict(max_mm=round(th, 2), at=[round(float(v), 1) for v in c])
    print('%s: %.2f mm at (%.0f, %.0f, %.0f)' % (pid, th, *c), 'OK' if th <= MAX_T else 'FAIL')
    if th > MAX_T: fail(f'{pid} is {th:.2f} mm thick')

print('--- overlaps')
M = {pid: tomf(m) for pid, m in parts.items()}
pairs = [('P1', 'P2'), ('P3', 'P4'), ('P5', 'P6'), ('P1', 'P3'), ('P2', 'P4'), ('P3', 'P5'), ('P4', 'P6'),
         ('P1', 'P4'), ('P2', 'P3'), ('P3', 'P6'), ('P4', 'P5')]
for a, b in pairs:
    v = float((M[a] ^ M[b]).volume()); res['overlaps'][f'{a}-{b}'] = round(v, 3)
    if v > 1.0: fail(f'{a} overlaps {b} by {v:.1f} mm3')
for name, group in (('spline', splines), ('pin', pins)):
    worst = 0.0
    for i, s in enumerate(group):
        S = tomf(s); worst = max(worst, max(float((S ^ M[pid]).volume()) for pid in IDS))
    res['overlaps'][name + '_max'] = round(worst, 3)
    if worst > 1.0: fail(f'a {name} overlaps a part by {worst:.1f} mm3')
print(res['overlaps'])

print('--- clearances')
for xs_, side in ((-XS, 'L'), (XS, 'R')):
    for half in ('front', 'rear'):
        male = part_id(side, half); female = part_id('C', half); d = -1 if xs_ < 0 else 1   # tongue points towards the centre part
        cen = parts[male].triangles_center
        proud = (-d * (cen[:, 0] - xs_) < -0.05) if False else ((cen[:, 0] - xs_) * (1 if xs_ < 0 else -1) > 0.05)
        _, dist, _ = trimesh.proximity.closest_point(parts[female], cen[proud])
        res['clearance'][f'tongue {xs_:+.1f} {half}'] = round(float(dist.min()), 3)
        if dist.min() < 0.12: fail(f'tongue {xs_:+.1f} {half}: clearance {dist.min():.3f} mm')
for i, s in enumerate(splines):
    P = s.sample(4000, return_index=False) if len(s.vertices) < 4000 else s.vertices
    near = min(float(trimesh.proximity.closest_point(parts[pid], P)[1].min()) for pid in IDS if parts[pid].bounds[0][0] - 5 < s.bounds[1][0] and parts[pid].bounds[1][0] + 5 > s.bounds[0][0])
    res['clearance'][f'spline {i + 1}'] = round(near, 3)
    if near < 0.12: fail(f'spline {i + 1}: clearance {near:.3f} mm')
print(res['clearance'])
walls = [w for seg in J['span'].values() for w in seg['pin_walls_mm']] + [w for seg in J['chord'].values() for w in seg['pin_walls_mm']]
res['pin_walls_min_mm'] = min(walls); print('pin-hole walls >= %.1f mm' % min(walls))
if min(walls) < 1.45: fail('a pin-hole wall is thinner than 1.5 mm')

print('--- seams: outer surfaces meet')
for xs_ in (-XS, XS):
    fr = Frame([xs_, 0, 0], [1.0, 0, 0])
    for half in ('front', 'rear'):
        a, b = (part_id('L', half), part_id('C', half)) if xs_ < 0 else (part_id('C', half), part_id('R', half))
        PA, PB = seam_profile(parts[a], fr, -1, holes=False), seam_profile(parts[b], fr, +1, holes=False)
        r = dict(mismatch_mm2=round(float(PA.symmetric_difference(PB).area), 2), area_mm2=round(float(PA.area), 1))
        res['seams'][f'{xs_:+.1f} {half}'] = r; print(f'span {xs_:+.1f} {half} {a}|{b}', r)
for sec, x0, x1 in SECTIONS:
    n, d = chord_plane(sec); xm = 0.5 * (x0 + x1); fr = Frame([xm, 0, (d - n[0] * xm) / n[2]], n)
    a, b = part_id(sec, 'front'), part_id(sec, 'rear')
    PA, PB = seam_profile(parts[a], fr, -1, holes=False), seam_profile(parts[b], fr, +1, holes=False)
    r = dict(mismatch_mm2=round(float(PA.symmetric_difference(PB).area), 2), area_mm2=round(float(PA.area), 1))
    res['seams'][f'cut {sec}'] = r; print(f'cut {sec} {a}|{b}', r)
res['ok'] = ok
json.dump(res, open(f'{OUT}/validation.json', 'w'), indent=1)
print('ALL CHECKS PASSED' if ok else 'SOME CHECKS FAILED')
if not ok: sys.exit(1)
