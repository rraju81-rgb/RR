"""v8 step 2: validation of the six assembled pieces and ten keys. Run from spoiler/:  python3 v8/src/p2_validate.py"""
import sys, json; sys.path.insert(0, 'v8/src'); sys.path.insert(0, 'v6/src')
import numpy as np, trimesh
from check import report
from bowtie import tomf
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
    # skin above the pocket, over the whole key footprint (the 45 deg end bevels make the pocket shallower at the ends)
    uu, vv = np.meshgrid(np.linspace(-meta['L'] / 2, meta['L'] / 2, 29), np.linspace(-meta['W'] / 2, meta['W'] / 2, 13), indexing='ij')
    u = uu.ravel(); v = vv.ravel(); depth = np.clip(meta['L'] / 2 - np.abs(u), 0, meta['DP'])
    pts = T[:, 3] + u[:, None] * T[:, 0] + v[:, None] * T[:, 1] + depth[:, None] * A
    loc2, ir2, it2 = R2.intersects_location(pts, np.tile(A, (len(pts), 1)), multiple_hits=False)
    sk = np.linalg.norm(loc2 - pts[ir2], axis=1)
    good = (inter < 1e-3 and set(near) == set(f['pieces']) and min(near.values()) > 0.10 and abs(d).max() < 0.20
            and sk.min() > 4.5)
    ok &= good
    key_checks.append(dict(key=i + 1, kind=f['kind'], x=f['x'], z=f['z'], pieces=f['pieces'], overlap_mm3=round(float(inter), 5),
                           min_gap=near, protrudes_max=round(float(d.max()), 3), recessed_max=round(float(d.min()), 3),
                           skin_min=round(float(sk.min()), 2), skin_mean=round(float(sk.mean()), 2)))
    print(f"KEY_{i + 1} {f['kind']:10s} x={f['x']:+6.1f} z={f['z']:5.1f}: overlap {inter:.4f} mm3 | min gap {near} | "
          f"face vs underside {d.min():+.3f}..{d.max():+.3f} mm | skin over pocket min {sk.min():.2f} mean {sk.mean():.2f} mm", 'OK' if good else 'FAIL')

print('--- reassembly')
U = MP[IDS[0]]
for p in IDS[1:]: U = U + MP[p]
dv = (E2.volume - U.volume()) / 1000
print('pieces together %.1f cm3 ; solid body %.1f cm3 ; difference (= the %d pockets) %.2f cm3' % (U.volume() / 1000, E2.volume / 1000, N_KEYS, dv))
ok &= bool(5.0 * N_KEYS < dv < 6.0 * N_KEYS)            # each pocket is about 5.5 cm3
pair_overlap = max((MP[a] ^ MP[b]).volume() for i, a in enumerate(IDS) for b in IDS[i + 1:])
print('largest overlap between any two pieces: %.5f mm3' % pair_overlap); ok &= pair_overlap < 1e-3
res['_keys'] = key_checks; res['_reassembly'] = dict(pocket_volume_cm3=round(float(dv), 2), pair_overlap_mm3=float(pair_overlap))
res['_all_ok'] = bool(ok)
json.dump(res, open(f'{OUT}/_validation.json', 'w'), indent=1)
print('ALL CHECKS PASSED' if ok else 'SOME CHECKS FAILED')
sys.exit(0 if ok else 1)
