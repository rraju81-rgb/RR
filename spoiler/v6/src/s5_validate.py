"""Step 5: validation of the assembled parts and keys."""
import sys, json; sys.path.insert(0, 'v6/src')
import numpy as np, trimesh, manifold3d as mf
from check import report
from trimesh.ray.ray_pyembree import RayMeshIntersector
OUT = 'v6/out'
meta = json.load(open(f'{OUT}/_parts_meta.json'))
def tomf(m):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
parts = {k: trimesh.load(f'v6/assembled/{k}.stl') for k in 'LCR'}
keys = [trimesh.load(f'v6/assembled/KEY_{i}.stl') for i in range(1, 5)]
res = {}
for k, m in list(parts.items()) + [(f'KEY_{i+1}', km) for i, km in enumerate(keys)]:
    r, sx = report(m, k); res[k] = r
    print(k, {a: r[a] for a in ['faces', 'watertight', 'winding', 'volume_cm3', 'bodies', 'selfx_faces', 'zero_area']})
# key interference / clearance
MP = {k: tomf(m) for k, m in parts.items()}
E2 = trimesh.load(f'{OUT}/E2.stl')
for i, km in enumerate(keys):
    K = tomf(km)
    inter = sum((K ^ MP[p]).volume() for p in 'LCR')
    gaps = {p: K.min_gap(MP[p], 2.0) for p in 'LCR'}
    print(f'KEY_{i+1}: overlap with parts {inter:.4f} mm3, min gap to L/C/R', {p: round(g, 3) for p, g in gaps.items()})
# outer face flushness: key outer face vs E2 underside (ray from key face points downward/outward)
R2 = RayMeshIntersector(E2)
for i, km in enumerate(keys):
    T = np.array(meta['frames'][i]['T']); A = T[:, 2]
    fc = km.triangles_center; fn = km.face_normals
    outer = (fn @ -A) > 0.99                         # faces facing out of the pocket (towards the car)
    o = fc[outer] - A * 5.0
    loc, ir, it = R2.intersects_location(o, np.tile(A, (len(o), 1)), multiple_hits=False)
    d = ((loc - o[ir]) @ A) - 5.0                    # +: E2 underside is above (inside) the key face -> key protrudes
    print(f'KEY_{i+1}: outer face vs underside: key protrudes max {d.max():+.3f} / recessed max {d.min():+.3f} mm')
# skin above the pocket floors
for i, f in enumerate(meta['frames']):
    T = np.array(f['T']); A = T[:, 2]; O = T[:, 3]
    uu, vv = np.meshgrid(np.linspace(-20, 20, 21), np.linspace(-10, 10, 11), indexing='ij')
    pts = O + uu.ravel()[:, None] * T[:, 0] + vv.ravel()[:, None] * T[:, 1] + meta['DP'] * A
    loc, ir, it = R2.intersects_location(pts, np.tile(A, (len(pts), 1)), multiple_hits=False)
    sk = np.linalg.norm(loc - pts[ir], axis=1)
    print(f"pocket seam {f['seam']:+.1f} z={f['z']}: skin above floor min {sk.min():.2f} mm, mean {sk.mean():.2f}")
# reassembly: parts + keys + pockets == E2 ?
U = MP['L'] + MP['C'] + MP['R']
print('assembled pieces volume %.1f cm3 ; E2 %.1f ; difference (= pocket volume) %.2f cm3' % (U.volume() / 1000, E2.volume / 1000, (E2.volume - U.volume()) / 1000))
json.dump(res, open(f'{OUT}/_validation.json', 'w'), indent=1)
