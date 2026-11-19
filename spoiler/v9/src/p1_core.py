"""v9 step 1: cut the solid spoiler (v6/out/E2.stl) into six equal pieces and core each one from underneath, so that no
part of it is thicker than 10 mm (see the notes on coring in layout.py).
  1. Faces that sit on the car (the car body within UNDER_GAP along the face normal; the tape gap is 1.5 mm) and faces
     that face the car (within CUT_GAP: the underside of the lip as well) may be cut. All other faces stay as they are.
  2. Per piece, on a 0.5 mm voxel grid: inside test (ray parity), distance to the faces that stay (exact Euclidean
     distance transform from dense points on them).
  3. Removed: everything deeper than the skin (T_SKIN, blending to S_FIN at the fin tips) below those faces, except the
     seal rim along the line where the underside leaves the car at the back. Pockets that would be sealed inside the part
     are dropped. Marching cubes on the distance field gives a smooth pocket surface, subtracted from the slice.
Writes v9/out/cored_P1..P6.stl and v9/out/core_report.json.   Run from spoiler/:  python3 v9/src/p1_core.py"""
import sys, os, json, time; sys.path.insert(0, 'v9/src'); sys.path.insert(0, 'v6/src')
import numpy as np, trimesh, manifold3d as mf
from scipy import ndimage as ndi
from skimage.measure import marching_cubes
from trimesh.ray.ray_pyembree import RayMeshIntersector
from bowtie import tomf, totm
from layout import E_PATH, CAR_PATH, OUT, HALF, PIECES, T_SKIN, S_FIN, FIN_X, RIM_W, VOX, UNDER_GAP, CUT_GAP

def car_distance(E, car, direction=None):
    """per face of E: distance to the car body along the face's outward normal, or along a fixed direction (inf if the
    ray misses it)"""
    Rc = RayMeshIntersector(car)
    c, n = E.triangles_center, E.face_normals
    dirs = n if direction is None else np.tile(np.asarray(direction, float), (len(c), 1))
    loc, ir, it = Rc.intersects_location(c + n * 0.01, dirs, multiple_hits=False)
    d = np.full(len(c), np.inf); d[ir] = np.linalg.norm(loc - c[ir], axis=1)
    return d

def exit_line(E, contact, step=0.5):
    """where the underside leaves the car at the back: for each x, the largest z of the faces on the car (main body:
    z > 100, y > -45). Returns (x, z) samples, |x| <= 582 (beyond that the fin takes over)"""
    c = E.triangles_center; sel = contact & (c[:, 2] > 100) & (c[:, 1] > -45)
    xs = np.arange(-582.0, 582.0 + step, step); zc = np.full(len(xs), np.nan)
    cx, cz = c[sel, 0], c[sel, 2]; order = np.argsort(cx); cx, cz = cx[order], cz[order]
    for i, x in enumerate(xs):
        a, b = np.searchsorted(cx, [x - 6.0, x + 6.0])                   # +-6 mm: bridges strips a hair over the gap
        if b > a: zc[i] = cz[a:b].max()
    ok = np.isfinite(zc); zc = np.interp(xs, xs[ok], zc[ok])
    zc = ndi.uniform_filter1d(zc, size=41, mode='nearest')               # 20 mm average: smooth over the faceted steps
    jump = np.abs(np.diff(zc))[np.abs(xs[:-1]) < 530]
    assert jump.max() < 0.6, f'exit line still jumps {jump.max():.1f} mm'
    return np.column_stack([xs, zc])

def skin_at(x):
    """skin depth (mm) as a function of x: T_SKIN on the main body, blending to S_FIN at the fin tips"""
    t = np.clip((np.abs(x) - FIN_X[0]) / (FIN_X[1] - FIN_X[0]), 0, 1)
    return T_SKIN + (S_FIN - T_SKIN) * t

def surface_points(m, spacing):
    """deterministic points covering every triangle of m at <= spacing (barycentric grid per triangle)"""
    T = m.triangles; e = np.linalg.norm(T - np.roll(T, 1, axis=1), axis=2).max(1)
    nsub = np.maximum(1, np.ceil(e / spacing).astype(int)); out = [T.reshape(-1, 3)]
    for n in np.unique(nsub):
        tri = T[nsub == n]
        ij = np.array([(i, j) for i in range(n + 1) for j in range(n + 1 - i)], float) / n
        w = np.column_stack([1 - ij.sum(1), ij])                          # barycentric weights
        out.append(np.einsum('kw,twd->tkd', w, tri).reshape(-1, 3))
    return np.vstack(out)

def weld(m, tol=2e-3):
    """collapse sub-2-micron edges left by the booleans (as v7/v8), keeping the surface manifold"""
    V = np.asarray(m.vertices); F = np.asarray(m.faces).copy()
    for _ in range(20):
        e = np.unique(np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), 1), axis=0)
        short = e[np.linalg.norm(V[e[:, 0]] - V[e[:, 1]], axis=1) < tol]
        if len(short) == 0: break
        nb = {}
        for a_, b_ in e[np.isin(e, np.unique(short)).any(1)]:
            nb.setdefault(int(a_), set()).add(int(b_)); nb.setdefault(int(b_), set()).add(int(a_))
        remap = np.arange(len(V)); busy = set(); n = 0
        for a_, b_ in short.tolist():
            if a_ in busy or b_ in busy or len(nb[a_] & nb[b_]) != 2: continue
            remap[b_] = a_; busy |= nb[a_] | nb[b_] | {a_, b_}; n += 1
        if n == 0: break
        F = remap[F]; F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 2] != F[:, 0])]
    out = trimesh.Trimesh(V, F, process=True)
    assert out.is_watertight and out.is_winding_consistent and abs(out.volume - m.volume) < 0.05, 'weld broke the mesh'
    return out

def pocket_mesh(E, RE, vis_pts, box, exitl):
    """the region to remove (deeper than the skin below the faces that stay, minus the seal rim), inside
    box = ((x0,y0,z0),(x1,y1,z1)), as a closed mesh"""
    lo, hi = np.array(box[0], float), np.array(box[1], float)
    shape = np.ceil((hi - lo) / VOX).astype(int)
    xs = lo[0] + (np.arange(shape[0]) + 0.5) * VOX; zs = lo[2] + (np.arange(shape[2]) + 0.5) * VOX
    # inside: rays up the y axis through every (x, z) column, filled between entry and exit hits
    X, Z = np.meshgrid(xs, zs, indexing='ij')
    O = np.column_stack([X.ravel(), np.full(X.size, lo[1] - 5.0), Z.ravel()])
    loc, ir, it = RE.intersects_location(O, np.tile([0, 1.0, 0], (len(O), 1)), multiple_hits=True)
    inside = np.zeros(shape, bool)
    order = np.lexsort((loc[:, 1], ir)); ir, ys = ir[order], loc[order, 1]
    starts = np.flatnonzero(np.r_[True, ir[1:] != ir[:-1]]); ends = np.r_[starts[1:], len(ir)]
    jy = lambda y: np.clip(np.round((y - lo[1]) / VOX - 0.5).astype(int), 0, shape[1])
    for s, e in zip(starts, ends):
        if (e - s) % 2: continue                                          # grazing hit: skip the column
        i, k = np.unravel_index(ir[s], X.shape)
        for a, b in zip(ys[s:e:2], ys[s + 1:e:2]):
            inside[i, jy(a):jy(b), k] = True
    # distance (mm) from every voxel centre to the nearest visible-surface voxel
    P = vis_pts[np.all((vis_pts >= lo - 1) & (vis_pts <= hi + 1), axis=1)]
    idx = np.floor((P - lo) / VOX).astype(int); ok = np.all((idx >= 0) & (idx < shape), axis=1)
    seed = np.zeros(shape, bool); seed[tuple(idx[ok].T)] = True
    D = ndi.distance_transform_edt(~seed).astype(np.float32) * VOX
    sk = skin_at(xs)[:, None, None].astype(np.float32)
    # near the pocket surface use exact distances to the surface points: the voxel transform measures to voxelised
    # surface, whose 0.5 mm height steps would show as terraces on the pocket ceiling
    near = (np.abs(D - sk) < 1.5) & ndi.binary_dilation(inside, iterations=3)
    from scipy.spatial import cKDTree
    ii = np.argwhere(near); Q = lo + (ii + 0.5) * VOX
    sub = P[np.all((P >= lo - 15) & (P <= hi + 15), axis=1)]
    D[tuple(ii.T)] = cKDTree(sub).query(Q, workers=-1)[0].astype(np.float32)
    G = D - sk                                                            # > 0: deeper than the skin
    # seal rim: within RIM_W (in plan) of the exit line, on the car side of it, main body only
    ex = exitl[(exitl[:, 0] >= lo[0] - 5) & (exitl[:, 0] <= hi[0] + 5)]
    rim = np.zeros(shape, bool)
    if len(ex) > 1:
        t = np.linspace(0, 1, 40)[:, None]
        dense = np.vstack([ex[i] + t * (ex[i + 1] - ex[i]) for i in range(len(ex) - 1)])
        pix = np.floor((dense - lo[[0, 2]]) / VOX).astype(int)
        pix = pix[(pix[:, 0] >= 0) & (pix[:, 0] < shape[0]) & (pix[:, 1] >= 0) & (pix[:, 1] < shape[2])]
        on = np.zeros((shape[0], shape[2]), bool); on[pix[:, 0], pix[:, 1]] = True
        dxz = ndi.distance_transform_edt(~on) * VOX
        zc = np.interp(xs, ex[:, 0], ex[:, 1])
        band = (dxz <= RIM_W) & (zs[None, :] <= zc[:, None] + 0.5) & (np.abs(xs)[:, None] <= 582)
        ys_ = lo[1] + (np.arange(shape[1]) + 0.5) * VOX
        rim = band[:, None, :] & (ys_ > -45)[None, :, None] & inside
    zone = ndi.binary_dilation(inside, iterations=2)
    deep = (G > 0) & zone & ~rim
    lab, n = ndi.label(deep)
    opens = np.unique(lab[deep & ~inside])                                # components that reach outside the part
    keep = np.isin(lab, opens[opens > 0])
    sealed = int(deep.sum() - keep.sum())
    # never cut a bit of the part off: if the material left over falls apart, give back the cut next to the small bits
    bridged = 0
    for _ in range(12):
        lab2, n2 = ndi.label(inside & ~keep)
        if n2 <= 1: break
        sizes = np.bincount(lab2.ravel()); sizes[0] = 0; small = (lab2 > 0) & (lab2 != np.argmax(sizes))
        give = keep & ndi.binary_dilation(small, iterations=4)
        keep &= ~give; bridged += int(give.sum())
    Gm = np.where(zone & ~rim, G, -1.0).astype(np.float32)
    Gm[deep & ~keep] = -1.0                                               # dropped or given back: not cut
    # level nudged off 0: voxel distances can land exactly on the skin depth, and exact ties leave holes in the surface
    for lev in (0.0123, 0.0317, 0.0571):
        vv, ff, _, _ = marching_cubes(np.pad(Gm, 1, constant_values=-1.0), level=lev, spacing=(VOX, VOX, VOX))
        vv = vv - VOX * 0.5 + lo                                          # padded index -> mm (voxel centres)
        m = trimesh.Trimesh(vv, ff, process=False)        # no vertex merge: it fuses pinch points into non-manifold edges
        if m.is_watertight: break
    if m.volume < 0: m.invert()                                           # marching cubes faces point up the gradient
    trimesh.smoothing.filter_taubin(m, iterations=6)
    return m, dict(voxels=int(np.prod(shape)), inside_cm3=float(inside.sum() * VOX ** 3 / 1000),
                   pocket_cm3=float(keep.sum() * VOX ** 3 / 1000), sealed_voxels=sealed, bridged_voxels=bridged, rim_cm3=float(rim.sum() * VOX ** 3 / 1000))

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    E = trimesh.load(E_PATH); car = trimesh.load(CAR_PATH, process=False)
    dcar = car_distance(E, car); contact = dcar < UNDER_GAP
    # may be cut: faces that face the car, and faces that look down with the car close below them (just behind the
    # tape band the lip's underside climbs steeply and its normal runs parallel to the rear window, missing the car)
    ddown = car_distance(E, car, (0, -1.0, 0))
    # ... and, on the main body, faces with the spoiler's own material straight above them (the small curved step in the
    # underside behind the tape band faces backwards, and its normal clears the car's crest)
    dup = car_distance(E, E, (0, 1.0, 0))
    cuttable = ((dcar < CUT_GAP) | ((E.face_normals[:, 1] < -0.25) & (ddown < 80.0)) |
                ((E.face_normals[:, 1] < 0.3) & (np.abs(E.triangles_center[:, 0]) < 560) & (dup < 40.0)))
    np.save(f'{OUT}/E2_contact.npy', contact); np.save(f'{OUT}/E2_cuttable.npy', cuttable)
    keepf = trimesh.Trimesh(E.vertices, E.faces[~cuttable], process=False)
    vis_pts = surface_points(keepf, 0.35)
    exitl = exit_line(E, contact); np.save(f'{OUT}/exit_line.npy', exitl)
    print('on the car: %.0f%% of the area; may be cut: %.0f%%; %d points on the faces that stay; %.1fs' % (
        100 * E.area_faces[contact].sum() / E.area, 100 * E.area_faces[cuttable].sum() / E.area, len(vis_pts), time.time() - t0))
    RE = RayMeshIntersector(E); ME = tomf(E)
    rep = {}
    only = sys.argv[1:]                                                   # optional: piece ids to redo
    if only and os.path.exists(f'{OUT}/core_report.json'): rep = json.load(open(f'{OUT}/core_report.json'))
    for pid, x0, x1, stem, label in PIECES:
        if only and pid not in only: continue
        t = time.time()
        M = ME
        if x0 > -HALF + 1e-6: M = M.trim_by_plane([1.0, 0, 0], x0)
        if x1 < HALF - 1e-6: M = M.trim_by_plane([-1.0, 0, 0], -x1)
        slab = totm(M)
        b = slab.bounds; margin = 12.0
        box = ((max(x0 - margin, -HALF - 2), b[0, 1] - 3, b[0, 2] - 3), (min(x1 + margin, HALF + 2), b[1, 1] + 3, b[1, 2] + 3))
        pm, info = pocket_mesh(E, RE, vis_pts, box, exitl)
        assert pm.is_watertight, f'{pid}: pocket mesh not watertight'
        cored = weld(totm(M - tomf(pm)))
        cored.export(f'{OUT}/cored_{pid}.stl')
        rep[pid] = dict(label=label, x=[x0, x1], solid_cm3=round(slab.volume / 1000, 1), cored_cm3=round(cored.volume / 1000, 1),
                        removed_pct=round(100 * (1 - cored.volume / slab.volume), 1), **{k: (round(v, 1) if isinstance(v, float) else v) for k, v in info.items()},
                        watertight=bool(cored.is_watertight), faces=len(cored.faces), seconds=round(time.time() - t, 1))
        print(pid, label, json.dumps(rep[pid]))
    json.dump(rep, open(f'{OUT}/core_report.json', 'w'), indent=1)
    tot_s = sum(r['solid_cm3'] for r in rep.values()); tot_c = sum(r['cored_cm3'] for r in rep.values())
    for pid in rep: assert len(trimesh.load(f'{OUT}/cored_{pid}.stl').split(only_watertight=False)) == 1, f'{pid} is in more than one body'
    print('total: solid %.0f cm3 -> cored %.0f cm3 (%.0f%% less); %.0fs' % (tot_s, tot_c, 100 * (1 - tot_c / tot_s), time.time() - t0))
