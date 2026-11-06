import os, sys, pickle, numpy as np, trimesh
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from joints import load_parts
from merge import merge_group4, heal_slits, to_manifold, keep_main

def slit_scan(m, n=200000, seed=0, lo=0.05, hi=0.9):
    np.random.seed(seed)
    pts, fi = trimesh.sample.sample_surface(m, n)
    nn = m.face_normals[fi]; o = pts + nn * 0.002
    locs, ridx, tidx = m.ray.intersects_location(o, nn, multiple_hits=False)
    d = np.full(n, np.inf); hn = np.zeros((n, 3))
    d[ridx] = np.linalg.norm(locs - o[ridx], axis=1); hn[ridx] = m.face_normals[tidx]
    sl = (np.einsum('ij,ij->i', nn, hn) < -0.9) & (d > lo) & (d < hi)
    return int(sl.sum())

def build(ids, label):
    P = load_parts(); pose = pickle.load(open('final_poses.pkl', 'rb'))
    A = pickle.load(open('assembly.pkl', 'rb')); S = pickle.load(open('stub_joints.pkl', 'rb'))
    pairs = [(r['A'], r['B']) for r in A['joints']] + [(s['A'], s['B']) for s in S]
    m = merge_group4(P, pose, ids, pairs, label)
    m = heal_slits(m)
    m, dropped = keep_main(m)
    if dropped: print(f'   dropped {dropped} tiny loose fragments')
    print(f"   {label}: visible slits (>0.05mm) remaining: {slit_scan(m)} samples; watertight {m.is_watertight}; solids {len(m.split(only_watertight=False))}; volume {m.volume/1000:.2f} cm3")
    return m

if __name__ == '__main__':
    out = {}
    for name, ids in [('body', [3, 2, 39, 40, 1]), ('endplate_A', [11, 12]), ('endplate_B', [16, 41])]:
        out[name] = build(ids, name.upper())
        out[name].export(f'final_{name}_assembled_pose.stl')

def build_wing(ids, extra, label='WING'):
    import manifold3d as mf
    from merge import slit_fillers_patch, drop_cavities, from_manifold
    P = load_parts(); pose = pickle.load(open('final_poses.pkl', 'rb'))
    A = pickle.load(open('assembly.pkl', 'rb')); S = pickle.load(open('stub_joints.pkl', 'rb'))
    pairs = [(r['A'], r['B']) for r in A['joints']] + [(s['A'], s['B']) for s in S]
    W = {p: P[p].copy().apply_transform(pose[p]) for p in ids}
    fill = []
    for a, b in pairs:
        if a in W and b in W:
            fill += slit_fillers_patch(W[a], W[b]); fill += slit_fillers_patch(W[b], W[a])
    Ms = [to_manifold(W[p]) for p in ids] + [to_manifold(f) for f in fill] + [to_manifold(e) for e in extra]
    m = from_manifold(mf.Manifold.batch_boolean(Ms, mf.OpType.Add))
    m, _, _, _ = drop_cavities(m)
    print(f"{label}: {len(ids)} parts + {len(fill)} slit fillers + {len(extra)} bridges -> {len(m.split(only_watertight=False))} solid(s); volume {m.volume/1000:.1f} cm3 (parts {sum(W[p].volume for p in ids)/1000:.1f})")
    m = heal_slits(m)
    m, dropped = keep_main(m)
    print(f"   {label}: visible slits (>0.05mm): {slit_scan(m)} samples; watertight {m.is_watertight}; solids {len(m.split(only_watertight=False))}; volume {m.volume/1000:.1f} cm3")
    return m

def export_clean(m, T, path, tol=0.005):
    """Orient (4x4 T), simplify away sub-micron slivers inside manifold3d, export STL, verify after slicer-style welding."""
    import manifold3d as mf
    M = to_manifold(m)
    M = M.transform(np.asarray(T[:3, :4], dtype=np.float64))
    M = M.simplify(tol)
    o = M.to_mesh64()
    tm = trimesh.Trimesh(np.asarray(o.vert_properties)[:, :3], np.asarray(o.tri_verts), process=False)
    tm.export(path)
    chk = trimesh.load(path, force='mesh')
    e = chk.edges_sorted; _, cnt = np.unique(e, axis=0, return_counts=True)
    return dict(tris=len(chk.faces), watertight=chk.is_watertight, bad_edges=int((cnt != 2).sum()),
                degenerate=int((chk.area_faces < 1e-10).sum()), volume=chk.volume, extents=chk.extents,
                solids=len(chk.split(only_watertight=False)), status=str(M.status()), genus=M.genus())

def separate_coincident(V, F, eps=0.004):
    """Push apart distinct vertices that would weld together in an STL (same float32 position)."""
    V = V.copy()
    key = np.round(V.astype(np.float32).astype(np.float64), 5)
    _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    dup = np.where(cnt[inv] > 1)[0]
    if len(dup) == 0:
        return V, 0
    # move each copy towards the centre of its own incident faces: copies that belong to
    # different sheets then always end up apart (moving along normals can leave them together)
    cen = V[F].mean(1)
    acc = np.zeros_like(V); cnt = np.zeros(len(V))
    for k in range(3):
        np.add.at(acc, F[:, k], cen); np.add.at(cnt, F[:, k], 1)
    dirv = acc[dup] / np.maximum(cnt[dup], 1)[:, None] - V[dup]
    nrm = np.linalg.norm(dirv, axis=1); nrm[nrm == 0] = 1
    V[dup] += dirv / nrm[:, None] * eps
    return V, len(dup)

def export_clean2(m, T, path, tol=0.01):
    import manifold3d as mf
    M = to_manifold(m).transform(np.asarray(T[:3, :4], dtype=np.float64)).simplify(tol)
    o = M.to_mesh64()
    V = np.asarray(o.vert_properties)[:, :3].astype(np.float64); F = np.asarray(o.tri_verts).astype(np.int64)
    V2, ndup = separate_coincident(V, F)
    tm = trimesh.Trimesh(V2, F, process=False)
    comps = tm.split(only_watertight=False)
    if len(comps) > 1:                                   # drop zero-volume sliver shells
        comps = [c for c in comps if abs(c.volume) > 1.0]
        tm = trimesh.util.concatenate(comps) if len(comps) > 1 else comps[0]
    tm.export(path)
    chk0 = trimesh.load(path, force='mesh')
    comps = chk0.split(only_watertight=False)
    if len(comps) > 1:                                   # slivers that only separate after welding
        comps = [c for c in comps if abs(c.volume) > 1.0]
        (trimesh.util.concatenate(comps) if len(comps) > 1 else comps[0]).export(path)
    chk = trimesh.load(path, force='mesh')
    e = chk.edges_sorted; _, cnt = np.unique(e, axis=0, return_counts=True)
    return dict(tris=len(chk.faces), watertight=chk.is_watertight, bad_edges=int((cnt != 2).sum()), separated=ndup,
                degenerate=int((chk.area_faces < 1e-10).sum()), volume=chk.volume, extents=chk.extents,
                solids=len(chk.split(only_watertight=False)))
