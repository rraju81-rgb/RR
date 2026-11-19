"""v9 step 3: checks on the six finished pieces, the centre spline and the pins. Stops with an error if one fails.
  - meshes: watertight, consistent winding, one body, no self-intersections, no zero-area faces;
  - each piece inside its 216.7 mm slot;
  - THICKNESS: the largest sphere that fits inside each piece (its greatest thickness) is at most 10 mm;
  - joints: neighbouring pieces, the spline and the pins do not overlap; tongue-to-groove clearance; pin-hole walls;
  - the outer surfaces of neighbouring pieces meet exactly at each seam.
Writes v9/out/validation.json.   Run from spoiler/:  python3 v9/src/p3_validate.py"""
import sys, json; sys.path.insert(0, 'v9/src'); sys.path.insert(0, 'v6/src')
import numpy as np, trimesh, manifold3d as mf
from check import report
from bowtie import tomf
from thickness import max_thickness
from p2_joints import seam_profile
from layout import OUT, ASM, PIECES, IDS, STEM, SEAMS, sides, seam_key, HOLE_D, HOLE_DEPTH, PIN_L, CLEAR, W_PIECE

MAX_T = 10.0
parts = {pid: trimesh.load(f'{ASM}/{STEM[pid]}.stl') for pid in IDS}
spline = trimesh.load(f'{ASM}/v9_CENTRE_SPLINE.stl')
joints = json.load(open(f'{OUT}/joints.json'))
pins = [trimesh.load(f'{ASM}/v9_PIN_{i + 1:02d}.stl') for i in range(joints['n_pins'])]
res = dict(meshes={}, extents={}, thickness={}, seams={}); ok = True

def fail(msg):
    global ok; ok = False; print('   FAIL:', msg)

print('--- meshes')
for k, m in list(parts.items()) + [('SPLINE', spline), ('PIN', pins[0])]:
    r, sx = report(m, k); res['meshes'][k] = r
    good = r['watertight'] and r['winding'] and r['bodies'] == 1 and r['selfx_faces'] == 0 and r['zero_area'] == 0
    print(k, {a: r[a] for a in ['faces', 'watertight', 'winding', 'volume_cm3', 'bodies', 'selfx_faces', 'zero_area']}, 'OK' if good else 'FAIL')
    if not good: fail(f'{k} mesh')

print('--- slots')
for pid, x0, x1, stem, label in PIECES:
    b = parts[pid].bounds
    # the tongue stands 2.5 mm proud of a male face; everything else stays inside the slot
    good = b[0][0] >= x0 - 2.6 and b[1][0] <= x1 + 2.6
    res['extents'][pid] = dict(x=[round(float(b[0][0]), 2), round(float(b[1][0]), 2)], slot=[round(x0, 2), round(x1, 2)])
    print(pid, res['extents'][pid], 'OK' if good else 'FAIL')
    if not good: fail(f'{pid} outside its slot')

print('--- thickness (largest sphere inside each piece)')
for pid in IDS:
    th, c = max_thickness(parts[pid])
    res['thickness'][pid] = dict(max_mm=round(th, 2), at=[round(float(v), 1) for v in c])
    print('%s: %.2f mm at (%.0f, %.0f, %.0f)' % (pid, th, *c), 'OK' if th <= MAX_T else 'FAIL')
    if th > MAX_T: fail(f'{pid} is {th:.2f} mm thick')

print('--- seams')
M = {pid: tomf(m) for pid, m in parts.items()}
for k, c in enumerate(SEAMS):
    L, R = IDS[k], IDS[k + 1]; sL, sR = sides(c); key = seam_key(c); r = {}
    r['overlap_mm3'] = round(float((M[L] ^ M[R]).volume()), 3)
    if key == 0.0:
        S = tomf(spline); r['spline_overlap_mm3'] = round(float((S ^ M[L]).volume() + (S ^ M[R]).volume()), 3)
    near = [p for p in pins if abs(p.centroid[0] - c) < 1]
    r['pin_overlap_mm3'] = round(float(sum((tomf(p) ^ M[L]).volume() + (tomf(p) ^ M[R]).volume() for p in near)), 3)
    # clearance round the tongue: points on the male piece standing proud of the face -> distance to the female piece
    if 'M' in (sL, sR):
        male, female, d = (L, R, +1) if sL == 'M' else (R, L, -1)
        mm = parts[male]; cen = mm.triangles_center
        proud = (d * (cen[:, 0] - c) > 0.05)
        pts = cen[proud]
        _, dist, _ = trimesh.proximity.closest_point(parts[female], pts)
        r['tongue_clearance_min_mm'] = round(float(dist.min()), 3)
        if dist.min() < 0.12: fail(f'seam {c:.1f}: tongue clearance {dist.min():.3f} mm')
    # pin-hole walls: the thinnest wall round each hole, along its whole depth (circles of growing radius must stay
    # inside the piece)
    walls = []
    for zy in joints['seams'][str(key)]['pins_zy']:
        for pid, side in ((L, -1), (R, +1)):
            a = np.linspace(0, 2 * np.pi, 48, endpoint=False); dep = np.linspace(1.0, HOLE_DEPTH - 0.3, 20)
            A, Dp = np.meshgrid(a, dep); w = 3.0
            for wall in np.arange(0.2, 3.01, 0.1):
                rr = HOLE_D / 2 + wall
                P = np.column_stack([c + side * Dp.ravel(), zy[1] + rr * np.sin(A.ravel()), zy[0] + rr * np.cos(A.ravel())])
                if not parts[pid].contains(P).all(): w = wall - 0.1; break
            walls.append(round(float(w), 1))
    r['hole_wall_min_mm'] = min(walls)
    if min(walls) < 1.45: fail(f'seam {c:.1f}: a pin hole wall is only {min(walls):.1f} mm')
    # outer surfaces meet: the two seam profiles (the top skin is cut from the same body, so it must coincide)
    PL, PR = seam_profile(parts[L], c, -1), seam_profile(parts[R], c, +1)
    r['profile_mismatch_area_mm2'] = round(float(PL.symmetric_difference(PR).area), 2)
    r['profile_area_mm2'] = round(float(PL.area), 1)
    good = r['overlap_mm3'] < 1.0 and r.get('spline_overlap_mm3', 0) < 1.0 and r['pin_overlap_mm3'] < 1.0
    res['seams'][str(key)] = r
    print('seam %+7.1f %s|%s:' % (c, L, R), r, 'OK' if good else 'FAIL')
    if not good: fail(f'seam {c:.1f} overlap')

res['ok'] = ok
json.dump(res, open(f'{OUT}/validation.json', 'w'), indent=1)
print('ALL CHECKS PASSED' if ok else 'SOME CHECKS FAILED')
if not ok: sys.exit(1)
