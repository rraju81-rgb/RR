"""Step 4: cut the solid v6 spoiler into 3 pieces, cut bow-tie key pockets across both seams (hidden underside),
make the bow-tie key, place every part for a 420 x 420 x 500 mm bed (Kobra 3 Max) standing on end."""
import sys, json, os; sys.path.insert(0, 'v6/src')
import numpy as np, trimesh, manifold3d as mf
from shapely.geometry import Polygon
from trimesh.ray.ray_pyembree import RayMeshIntersector
OUT = 'v6/out'
E = trimesh.load(f'{OUT}/E2.stl')
from bowtie import *
R = RayMeshIntersector(E)
def under_frame(xs, zc):
    xx, zz = np.meshgrid(np.linspace(xs - 30, xs + 30, 13), np.linspace(zc - 13, zc + 13, 9), indexing='ij')
    O = np.column_stack([xx.ravel(), np.full(xx.size, -300.0), zz.ravel()])
    loc, ir, it = R.intersects_location(O, np.tile([0, 1.0, 0], (len(O), 1)), multiple_hits=False)
    P = loc; c = P.mean(0); u, s, vt = np.linalg.svd(P - c); n = vt[2]
    if n[1] > 0: n = -n                                                   # outward (down) normal of the underside
    A = -n
    resid = (P - c) @ n
    # origin on the plane at (xs, ?, zc)
    y0 = c[1] - (n[0] * (xs - c[0]) + n[2] * (zc - c[2])) / n[1]
    O0 = np.array([xs, y0, zc])
    E1 = np.array([1.0, 0, 0]); E1 = E1 - (E1 @ A) * A; E1 /= np.linalg.norm(E1)
    E2 = np.cross(A, E1)
    T = np.column_stack([E1, E2, A, O0])                                  # 3x4 local->world
    return T, float(np.abs(resid).max()), len(P)
pockets = []; frames = []
for side in (-1, 1):
    for zc in KEY_Z:
        T, res, npts = under_frame(side * XS, zc)
        frames.append(dict(seam=side * XS, z=zc, T=T.tolist(), plane_fit_max_dev=res))
        pockets.append((side, pocket_local().transform(T), T))
        print(f'key seam x={side*XS:+.1f} z={zc}: underside plane fit max dev {res:.3f} mm ({npts} pts), axis {np.round(T[:,2],3)}')
ME = tomf(E)
Lp = ME.trim_by_plane([-1, 0, 0], XS)
Cp = ME.trim_by_plane([1, 0, 0], -XS).trim_by_plane([-1, 0, 0], -XS)
Rp = ME.trim_by_plane([1, 0, 0], XS)
for side, P, T in pockets:
    if side < 0: Lp = Lp - P; Cp = Cp - P
    else: Rp = Rp - P; Cp = Cp - P
KEY = key_local()
parts = {'L': totm(Lp), 'C': totm(Cp), 'R': totm(Rp)}
key_world = [totm(key_local().transform(T)) for _, _, T in pockets]
key_local_tm = totm(KEY)
os.makedirs('v6/assembled', exist_ok=True)
for k, m in parts.items(): m.export(f'v6/assembled/{k}.stl')
for i, k in enumerate(key_world): k.export(f'v6/assembled/KEY_{i+1}.stl')
key_local_tm.export(f'{OUT}/_key_local.stl')
json.dump(dict(XS=XS, L=L, W=W, N=N, DP=DP, CL=CL, CF=CF, KEY_Z=KEY_Z, frames=frames), open(f'{OUT}/_parts_meta.json', 'w'), indent=1)
for k, m in parts.items():
    print(k, 'faces', len(m.faces), 'watertight', m.is_watertight, 'vol cm3 %.1f' % (m.volume / 1000), 'bounds', m.bounds.round(1).tolist())
print('key vol cm3 %.2f bounds' % (key_local_tm.volume / 1000), key_local_tm.bounds.round(2).tolist())
