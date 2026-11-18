"""v8 step 2: validation of the six assembled pieces and ten keys (8 standard, 2 thin).
Run from spoiler/:  python3 v8/src/p2_validate.py"""
import sys, json; sys.path.insert(0, 'v8/src'); sys.path.insert(0, 'v6/src')
import numpy as np, trimesh
from check import report
from bowtie import tomf, pocket_local, bowtie_outline
from shapely.geometry import Point
from trimesh.ray.ray_pyembree import RayMeshIntersector
from layout import E_PATH, OUT, ASM, IDS, PIECES, N_KEYS, CUT_Z

meta = json.load(open(f'{OUT}/_parts_meta.json'))
parts = {k: trimesh.load(f'{ASM}/{k}.stl') for k in IDS}
keys = [trimesh.load(f'{ASM}/KEY_{i}.stl') for i in range(1, N_KEYS + 1)]
E2 = trimesh.load(E_PATH); R2 = RayMeshIntersector(E2)
res = {}; ok = True

print('--- meshes')
for k, m in list(parts.items()) + [(f'KEY_{i + 1}', km) for i, km in enumerate(keys)]:
    r, sx = report(m, k); res[k] = r
    good = r['watertight'] and r['winding'] and r['bodies'] == 1 and r['selfx_faces'] == 0 and r['zero_area'] == 0
    ok &= good
    print(k, {a: r[a] for a in ['faces', 'watertight', 'winding', 'volume_cm3', 'bodies', 'selfx_faces', 'zero_area']}, 'OK' if good else 'FAIL')

print('--- piece extents')
for pid, x0, x1, zs, stem, label in PIECES:
    b = parts[pid].bounds
    good = b[0][0] >= x0 - 0.1 and b[1][0] <= x1 + 0.1                       # within its span slot
    if zs is None: good &= abs((b[1][0] - b[0][0]) - 325.0) < 0.1             # full-chord pieces are 325 mm long
    if zs == 'F': good &= b[1][2] <= CUT_Z + 1e-3
    if zs == 'R': good &= b[0][2] >= CUT_Z - 1e-3
    ok &= bool(good)
    print(f'{pid} {stem}: x {b[0][0]:+.2f} .. {b[1][0]:+.2f}, z {b[0][2]:+.2f} .. {b[1][2]:+.2f}', 'OK' if good else 'FAIL')

print('--- keys in their pockets')
MP = {k: tomf(m) for k, m in parts.items()}
key_checks = []
SKIN_MIN = {False: 4.5, True: 4.0}                  # material over the pocket floor: standard keys / thin keys
# skin sample points: a grid over the key footprint, kept only inside the bow-tie outline (the pocket's real footprint)
uu, vv = np.meshgrid(np.linspace(-meta['L'] / 2, meta['L'] / 2, 57), np.linspace(-meta['W'] / 2, meta['W'] / 2, 25), indexing='ij')
OUTL = bowtie_outline()
ins = np.array([OUTL.contains(Point(a, b)) or OUTL.exterior.distance(Point(a, b)) < 1e-6 for a, b in zip(uu.ravel(), vv.ravel())])
U_S, V_S = uu.ravel()[ins], vv.ravel()[ins]
def exit_skin(pts, A):
    """distance along A from each point to where the ray leaves the solid (the top surface)"""
    loc, ir, it = R2.intersects_location(pts, np.tile(A, (len(pts), 1)), multiple_hits=True)
    ex = (E2.face_normals[it] @ A) > 0
    d = np.full(len(pts), np.inf); dist = np.linalg.norm(loc - pts[ir], axis=1); np.minimum.at(d, ir[ex], dist[ex])
    return d
for i, km in enumerate(keys):
    f = meta['frames'][i]; T = np.array(f['T']); A = T[:, 2]
    K = tomf(km)
    inter = sum((K ^ MP[p]).volume() for p in IDS)
    gaps = {p: K.min_gap(MP[p], 2.0) for p in IDS}
    near = {p: round(g, 3) for p, g in gaps.items() if g < 2.0}
    # outer face flushness: key outer face vs the underside of the solid body
    fc = km.triangles_center; fn = km.face_normals
    outer = (fn @ -A) > 0.99
    o = fc[outer] - A * 5.0
    loc, ir, it = R2.intersects_location(o, np.tile(A, (len(o), 1)), multiple_hits=False)
    d = ((loc - o[ir]) @ A) - 5.0                    # +: underside is above (inside) the key face -> key protrudes
    # skin above the pocket floor, over the whole pocket footprint (the 45 deg end bevels make the pocket shallower at
    # the ends); measured to where the ray leaves the solid, so a point on a lobe tip below the underside is not misread
    depth = np.clip(meta['L'] / 2 - np.abs(U_S), 0, f['dp'])
    pts = T[:, 3] + U_S[:, None] * T[:, 0] + V_S[:, None] * T[:, 1] + depth[:, None] * A
    sk = exit_skin(pts, A)
    good = (inter < 1e-3 and set(near) == set(f['pieces']) and min(near.values()) > 0.10 and abs(d).max() < 0.20
            and sk.min() > SKIN_MIN[f['thin']] and np.isfinite(sk).all())
    ok &= good
    key_checks.append(dict(key=i + 1, kind=f['kind'], x=f['x'], z=f['z'], pieces=f['pieces'], thin=f['thin'], dp=f['dp'],
                           thickness_mm=round(float(((km.vertices - T[:, 3]) @ A).max()), 3),
                           overlap_mm3=round(float(inter), 5),
                           min_gap=near, protrudes_max=round(float(d.max()), 3), recessed_max=round(float(d.min()), 3),
                           skin_min=round(float(sk.min()), 2), skin_mean=round(float(sk.mean()), 2)))
    print(f"KEY_{i + 1} {f['kind']:10s}{' THIN' if f['thin'] else '     '} x={f['x']:+6.1f} z={f['z']:5.1f}: overlap {inter:.4f} mm3 | min gap {near} | "
          f"face vs underside {d.min():+.3f}..{d.max():+.3f} mm | skin over pocket min {sk.min():.2f} mean {sk.mean():.2f} mm", 'OK' if good else 'FAIL')

print('--- reassembly')
U = MP[IDS[0]]
for p in IDS[1:]: U = U + MP[p]
dv = (E2.volume - U.volume()) / 1000
ME2 = tomf(E2)
expect = sum((ME2 ^ pocket_local(f['dp']).transform(np.array(f['T']))).volume() for f in meta['frames']) / 1000
print('pieces together %.1f cm3 ; solid body %.1f cm3 ; difference %.2f cm3 ; the %d pockets cut from the body %.2f cm3'
      % (U.volume() / 1000, E2.volume / 1000, dv, N_KEYS, expect))
ok &= bool(abs(dv - expect) < 0.02)                     # nothing but the pockets is missing
pair_overlap = max((MP[a] ^ MP[b]).volume() for i, a in enumerate(IDS) for b in IDS[i + 1:])
print('largest overlap between any two pieces: %.5f mm3' % pair_overlap); ok &= pair_overlap < 1e-3
res['_keys'] = key_checks; res['_reassembly'] = dict(pocket_volume_cm3=round(float(dv), 2), expected_pocket_volume_cm3=round(float(expect), 2),
                                                   pair_overlap_mm3=float(pair_overlap))
res['_all_ok'] = bool(ok)
json.dump(res, open(f'{OUT}/_validation.json', 'w'), indent=1)
print('ALL CHECKS PASSED' if ok else 'SOME CHECKS FAILED')
sys.exit(0 if ok else 1)
