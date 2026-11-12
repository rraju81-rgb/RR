"""v7 step 1: cut the solid spoiler into 4 equal pieces, cut bow-tie key pockets across the three seams (hidden
underside) and make the six keys. Run from spoiler/:  python3 v7/src/p1_parts.py"""
import sys, json, os; sys.path.insert(0, 'v7/src'); sys.path.insert(0, 'v6/src')
import numpy as np, trimesh
from trimesh.ray.ray_pyembree import RayMeshIntersector
from bowtie import L, W, N, DP, CL, CF, tomf, totm, pocket_local, key_local
from layout import E_PATH, OUT, ASM, HALF, SEAMS, KEY_Z, PIECES

E = trimesh.load(E_PATH)
R = RayMeshIntersector(E)

def under_frame(xs, zc):
    """local frame of the underside at (xs, zc): plane fit over the key footprint; columns = E1 (across the seam),
    E2 (chordwise), A (pocket axis, into the part), origin on the plane"""
    xx, zz = np.meshgrid(np.linspace(xs - 30, xs + 30, 13), np.linspace(zc - 13, zc + 13, 9), indexing='ij')
    O = np.column_stack([xx.ravel(), np.full(xx.size, -300.0), zz.ravel()])
    P, ir, it = R.intersects_location(O, np.tile([0, 1.0, 0], (len(O), 1)), multiple_hits=False)
    c = P.mean(0); u, s, vt = np.linalg.svd(P - c); n = vt[2]
    if n[1] > 0: n = -n                                                   # outward (down) normal of the underside
    A = -n
    resid = (P - c) @ n
    y0 = c[1] - (n[0] * (xs - c[0]) + n[2] * (zc - c[2])) / n[1]
    O0 = np.array([xs, y0, zc])
    E1 = np.array([1.0, 0, 0]); E1 = E1 - (E1 @ A) * A; E1 /= np.linalg.norm(E1)
    E2 = np.cross(A, E1)
    return np.column_stack([E1, E2, A, O0]), float(np.abs(resid).max()), len(P)

def weld(m, tol=2e-3):
    """Collapse mesh edges shorter than tol (2 microns) and drop the faces that vanish. The boolean cuts leave a few
    sub-micron sliver triangles where a pocket's end bevel meets the underside; once the print files are rotated and
    stored as float32 they can register as self-intersections. Only vertex pairs joined by an edge are merged, and
    only where the collapse keeps the surface manifold (the edge's two end points share exactly two neighbours)."""
    V = np.asarray(m.vertices); F = np.asarray(m.faces).copy(); removed = 0
    for _ in range(20):                                                   # a collapse can expose another short edge
        e = np.unique(np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), 1), axis=0)
        short = e[np.linalg.norm(V[e[:, 0]] - V[e[:, 1]], axis=1) < tol]
        if len(short) == 0: break
        nb = {}
        for a_, b_ in e[np.isin(e, np.unique(short)).any(1)]:
            nb.setdefault(int(a_), set()).add(int(b_)); nb.setdefault(int(b_), set()).add(int(a_))
        remap = np.arange(len(V)); busy = set(); n = 0
        for a_, b_ in short.tolist():
            if a_ in busy or b_ in busy or len(nb[a_] & nb[b_]) != 2: continue
            remap[b_] = a_; busy |= nb[a_] | nb[b_] | {a_, b_}; n += 1    # keep collapses in one pass well apart
        if n == 0: break
        F = remap[F]
        keep = (F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 2] != F[:, 0])
        removed += int((~keep).sum()); F = F[keep]
    out = trimesh.Trimesh(V, F, process=True)
    assert out.is_watertight and out.is_winding_consistent and abs(out.volume - m.volume) < 0.05, 'weld broke the mesh'   # mm3
    return out, removed

frames = []
for xs in SEAMS:
    for zc in KEY_Z[xs]:
        T, res, npts = under_frame(xs, zc)
        frames.append(dict(seam=xs, z=zc, T=T.tolist(), plane_fit_max_dev=res))
        print(f'key seam x={xs:+7.1f} z={zc:5.1f}: underside plane fit max dev {res:.3f} mm ({npts} pts), axis {np.round(T[:, 2], 3)}')

ME = tomf(E)
parts = {}
for pid, x0, x1, stem, label in PIECES:
    M = ME
    if x0 > -HALF: M = M.trim_by_plane([1.0, 0, 0], x0)                   # keep x >= x0
    if x1 < HALF: M = M.trim_by_plane([-1.0, 0, 0], -x1)                  # keep x <= x1
    for f in frames:                                                      # pockets of the seams this piece touches
        if f['seam'] in (x0, x1): M = M - pocket_local().transform(np.array(f['T']))
    parts[pid], nrem = weld(totm(M))
    print(f'{pid}: welded sub-micron slivers, {nrem} faces removed')

os.makedirs(ASM, exist_ok=True); os.makedirs(OUT, exist_ok=True)
for pid, m in parts.items(): m.export(f'{ASM}/{pid}.stl')
for i, f in enumerate(frames): totm(key_local().transform(np.array(f['T']))).export(f'{ASM}/KEY_{i + 1}.stl')
key_local_tm = totm(key_local()); key_local_tm.export(f'{OUT}/_key_local.stl')
json.dump(dict(SEAMS=SEAMS, KEY_Z={str(k): v for k, v in KEY_Z.items()}, L=L, W=W, N=N, DP=DP, CL=CL, CF=CF, frames=frames),
          open(f'{OUT}/_parts_meta.json', 'w'), indent=1)
for pid, m in parts.items():
    print(pid, 'faces', len(m.faces), 'watertight', m.is_watertight, 'vol cm3 %.1f' % (m.volume / 1000), 'bounds', m.bounds.round(1).tolist())
print('key vol cm3 %.2f bounds' % (key_local_tm.volume / 1000), key_local_tm.bounds.round(2).tolist())
