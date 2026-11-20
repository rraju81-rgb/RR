"""v10 step 1: core the solid spoiler (v6/out/E2.stl) section by section (left, centre, right) so that no part of it is
thicker than 10 mm, with the new grooved rim at the back.
  1. As v9: faces on the car and faces that face the car may be cut; all other faces stay exactly as they are.
  2. Per section, on a 0.5 mm voxel grid aligned to one global lattice (so neighbouring sections agree exactly at the
     seams): everything deeper than the skin below the faces that stay is the region to remove (pocket under the ridge,
     trim under the lip root, fin tips from the pillar side). Marching cubes gives its smooth surface.
  3. The rim's two legs (rim.py: clean sweeps along one smooth curve) are taken back out of that region, so they stay:
     cored section = section - (pocket - legs). Between the legs is the glue groove.
The right section is the mirror of the left one. Writes v10/out/cored_L|C|R.stl, rim_curve.npz, rim_legs.stl, core_report.json.   Run from spoiler/:
python3 v10/src/p1_core.py [L C R]"""
import sys, os, json, time; sys.path.insert(0, 'v10/src'); sys.path.insert(0, 'v6/src')
import numpy as np, trimesh, manifold3d as mf
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes
from trimesh.ray.ray_pyembree import RayMeshIntersector
from bowtie import tomf, totm
from check import report
from layout import E_PATH, CAR_PATH, OUT, HALF, SECTIONS, T_SKIN, S_FIN, FIN_X, VOX, MARGIN, UNDER_GAP, CUT_GAP, LIP_EXTRA, LIP_RAMP, RIM_X, SKIRT
import rim

def car_distance(E, car, direction=None):
    Rc = RayMeshIntersector(car)
    c, n = E.triangles_center, E.face_normals
    dirs = n if direction is None else np.tile(np.asarray(direction, float), (len(c), 1))
    loc, ir, it = Rc.intersects_location(c + n * 0.01, dirs, multiple_hits=False)
    d = np.full(len(c), np.inf); d[ir] = np.linalg.norm(loc - c[ir], axis=1)
    return d

def skin_at(x):
    t = np.clip((np.abs(x) - FIN_X[0]) / (FIN_X[1] - FIN_X[0]), 0, 1)
    return T_SKIN + (S_FIN - T_SKIN) * t

def surface_points(m, spacing):
    T = m.triangles; e = np.linalg.norm(T - np.roll(T, 1, axis=1), axis=2).max(1)
    nsub = np.maximum(1, np.ceil(e / spacing).astype(int)); out = [T.reshape(-1, 3)]
    for n in np.unique(nsub):
        tri = T[nsub == n]
        ij = np.array([(i, j) for i in range(n + 1) for j in range(n + 1 - i)], float) / n
        w = np.column_stack([1 - ij.sum(1), ij])
        out.append(np.einsum('kw,twd->tkd', w, tri).reshape(-1, 3))
    return np.vstack(out)

def weld(m, tol=2e-3):
    """collapse sub-2-micron edges left by the booleans, keeping the surface manifold"""
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

def clean_written(make, name, tols):
    """the mesh as it will be written (float32 STL) must have no folded faces: try make(tol) for each tol"""
    import tempfile
    best = None
    for tol in tols:
        try: m = make(tol)
        except AssertionError as e: print('   %s: tol %.3f skipped (%s)' % (name, tol, e)); continue
        with tempfile.NamedTemporaryFile(suffix='.stl') as f:
            m.export(f.name); r, sx = report(trimesh.load(f.name), name)
        if r['selfx_faces'] == 0 and r['watertight'] and r['bodies'] == 1: return m, tol, 0
        if r['watertight'] and r['bodies'] == 1 and (best is None or r['selfx_faces'] < best[2]): best = (m, tol, r['selfx_faces'])
    assert best is not None, f'{name}: no clean mesh at any tolerance'
    return best

def written_folds(m, name=''):
    """folded (self-intersecting) faces in the mesh as written to a float32 STL"""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.stl') as f:
        m.export(f.name); r, sx = report(trimesh.load(f.name), name)
    return r['selfx_faces'] if (r['watertight'] and r['bodies'] == 1) else 10 ** 9

def decimate_clean(m0, name, percs=(0.12, 0.2, 0.35, 0.55), max_dev=0.02):
    """fewer faces without folds: quadric edge collapse (triangle quality kept), accepted only if the written file has
    no folded faces, the volume is unchanged (< 0.05%) and no surface point moved more than max_dev mm"""
    import pymeshlab
    for perc in percs:
        ms = pymeshlab.MeshSet(); ms.add_mesh(pymeshlab.Mesh(vertex_matrix=np.asarray(m0.vertices, float), face_matrix=np.asarray(m0.faces, np.int32)))
        ms.apply_filter('meshing_decimation_quadric_edge_collapse', targetperc=perc, qualitythr=0.5, preservetopology=True,
                        preservenormal=True, planarquadric=True, optimalplacement=True, autoclean=True)
        g = ms.current_mesh(); md = trimesh.Trimesh(g.vertex_matrix(), g.face_matrix(), process=True)
        if not (md.is_watertight and md.is_winding_consistent) or abs(md.volume - m0.volume) > 5e-4 * abs(m0.volume): continue
        P = md.sample(20000); _, d, _ = trimesh.proximity.closest_point(m0, P)
        if d.max() > max_dev: continue
        if written_folds(md, name) == 0: return md, perc
    return m0, 1.0

def keep_main(m):
    """drop zero-volume slivers the booleans can leave (a few faces, < 1 mm3); anything bigger is an error"""
    b = m.split(only_watertight=False)
    if len(b) == 1: return m
    b = sorted(b, key=lambda q: -abs(q.volume))
    assert all(abs(q.volume) < 1.0 and len(q.faces) < 200 for q in b[1:]), 'a real piece came off'
    return b[0]

def pocket_mesh(RE, vis_pts, box, st, skirt_pts):
    """the region deeper than the skin below the faces that stay, inside box, as a closed mesh (grid on the global lattice)"""
    lo = np.floor(np.array(box[0], float) / VOX) * VOX; hi = np.ceil(np.array(box[1], float) / VOX) * VOX
    shape = np.round((hi - lo) / VOX).astype(int)
    xs = lo[0] + (np.arange(shape[0]) + 0.5) * VOX; zs = lo[2] + (np.arange(shape[2]) + 0.5) * VOX
    X, Z = np.meshgrid(xs, zs, indexing='ij')
    O = np.column_stack([X.ravel(), np.full(X.size, lo[1] - 5.0), Z.ravel()])
    loc, ir, it = RE.intersects_location(O, np.tile([0, 1.0, 0], (len(O), 1)), multiple_hits=True)
    inside = np.zeros(shape, bool)
    order = np.lexsort((loc[:, 1], ir)); ir, ys = ir[order], loc[order, 1]
    starts = np.flatnonzero(np.r_[True, ir[1:] != ir[:-1]]); ends = np.r_[starts[1:], len(ir)]
    jy = lambda y: np.clip(np.round((y - lo[1]) / VOX - 0.5).astype(int), 0, shape[1])
    for s, e in zip(starts, ends):
        if (e - s) % 2: continue
        i, k = np.unravel_index(ir[s], X.shape)
        for a, b in zip(ys[s:e:2], ys[s + 1:e:2]): inside[i, jy(a):jy(b), k] = True
    P = vis_pts[np.all((vis_pts >= lo - 1) & (vis_pts <= hi + 1), axis=1)]
    idx = np.floor((P - lo) / VOX).astype(int); ok = np.all((idx >= 0) & (idx < shape), axis=1)
    seed = np.zeros(shape, bool); seed[tuple(idx[ok].T)] = True
    D = ndi.distance_transform_edt(~seed).astype(np.float32) * VOX; del seed
    sk = skin_at(xs)[:, None, None].astype(np.float32)
    near = (np.abs(D - sk) < 1.5) & ndi.binary_dilation(inside, iterations=3)
    ii = np.argwhere(near); del near
    sub = P[np.all((P >= lo - 15) & (P <= hi + 15), axis=1)]
    D[tuple(ii.T)] = cKDTree(sub).query(lo + (ii + 0.5) * VOX, workers=-1)[0].astype(np.float32); del ii
    G = D - sk; del D
    # skirt: stay at least SKIRT deep below the spoiler's own underside behind the rim line
    Q = skirt_pts[np.all((skirt_pts >= lo - 1) & (skirt_pts <= hi + 1), axis=1)]
    if len(Q):
        idx = np.floor((Q - lo) / VOX).astype(int); okq = np.all((idx >= 0) & (idx < shape), axis=1)
        seed = np.zeros(shape, bool); seed[tuple(idx[okq].T)] = True
        D2 = ndi.distance_transform_edt(~seed).astype(np.float32) * VOX; del seed
        near = (np.abs(D2 - SKIRT) < 1.5) & ndi.binary_dilation(inside, iterations=3)
        ii = np.argwhere(near); del near
        subq = Q[np.all((Q >= lo - 10) & (Q <= hi + 10), axis=1)]
        D2[tuple(ii.T)] = cKDTree(subq).query(lo + (ii + 0.5) * VOX, workers=-1)[0].astype(np.float32); del ii
        np.minimum(G, D2 - SKIRT, out=G); del D2
    # behind the rim line the lip is trimmed only where it is thicker than T_SKIN + LIP_EXTRA (ramping in over LIP_RAMP)
    S2 = np.column_stack([st['x'], st['z']]); _, j = cKDTree(S2).query(np.column_stack([X.ravel(), Z.ravel()]))
    t = ((np.column_stack([X.ravel(), Z.ravel()]) - S2[j]) * st['N'][j]).sum(1).reshape(X.shape)
    shift = LIP_EXTRA * np.clip(-t / LIP_RAMP, 0, 1) * (np.abs(X) <= RIM_X)
    G -= shift[:, None, :].astype(np.float32)
    zone = ndi.binary_dilation(inside, iterations=2)
    deep = (G > 0) & zone
    lab, n = ndi.label(deep)
    opens = np.unique(lab[deep & ~inside])
    keep = np.isin(lab, opens[opens > 0]); del lab
    sealed = int(deep.sum() - keep.sum())
    bridged = 0
    for _ in range(12):                                                  # never cut a bit of the part off
        lab2, n2 = ndi.label(inside & ~keep)
        if n2 <= 1: break
        sizes = np.bincount(lab2.ravel()); sizes[0] = 0; small = (lab2 > 0) & (lab2 != np.argmax(sizes))
        give = keep & ndi.binary_dilation(small, iterations=4)
        keep &= ~give; bridged += int(give.sum())
    del lab2
    Gm = np.where(zone, G, -1.0).astype(np.float32); del G
    Gm[deep & ~keep] = -1.0
    for lev in (0.0123, 0.0317, 0.0571):
        vv, ff, _, _ = marching_cubes(np.pad(Gm, 1, constant_values=-1.0), level=lev, spacing=(VOX, VOX, VOX))
        vv = vv - VOX * 0.5 + lo
        m = trimesh.Trimesh(vv, ff, process=False)
        if m.is_watertight: break
    if m.volume < 0: m.invert()
    trimesh.smoothing.filter_taubin(m, iterations=6)
    return m, dict(voxels=int(np.prod(shape)), inside_cm3=float(inside.sum() * VOX ** 3 / 1000),
                   pocket_cm3=float(keep.sum() * VOX ** 3 / 1000), sealed_voxels=sealed, bridged_voxels=bridged)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    E = trimesh.load(E_PATH); car = trimesh.load(CAR_PATH, process=False)
    dcar = car_distance(E, car); contact = dcar < UNDER_GAP
    ddown = car_distance(E, car, (0, -1.0, 0)); dup = car_distance(E, E, (0, 1.0, 0))
    cuttable = ((dcar < CUT_GAP) | ((E.face_normals[:, 1] < -0.25) & (ddown < 80.0)) |
                ((E.face_normals[:, 1] < 0.3) & (np.abs(E.triangles_center[:, 0]) < 560) & (dup < 40.0)))
    np.save(f'{OUT}/E2_contact.npy', contact); np.save(f'{OUT}/E2_cuttable.npy', cuttable)
    vis_pts = surface_points(trimesh.Trimesh(E.vertices, E.faces[~cuttable], process=False), 0.35)
    st = rim.rim_curve(E, car); np.savez(f'{OUT}/rim_curve.npz', **st)
    rl, fl = rim.legs(st)
    LEGS = tomf(fl); totm(LEGS).export(f'{OUT}/rim_legs.stl')            # the front leg (the rear one is now the skirt)
    # skirt points: dense points on the underside faces behind the rim line (per point, so its edge follows the line)
    und = cuttable & (E.face_normals[:, 1] < -0.2)
    up_ = surface_points(trimesh.Trimesh(E.vertices, E.faces[und], process=False), 0.35)
    from scipy.spatial import cKDTree as _K
    S2 = np.column_stack([st['x'], st['z']]); _, j = _K(S2).query(up_[:, [0, 2]])
    tq = ((up_[:, [0, 2]] - S2[j]) * st['N'][j]).sum(1)
    skirt_pts = up_[(tq < 0.0) & (np.abs(up_[:, 0]) <= 560.0)]
    np.save(f'{OUT}/skirt_pts_count.npy', np.array([len(skirt_pts)]))
    print('rim: %d stations, x %.0f..%.0f; worst gap under the rear leg %.2f mm (|x|<540); %.1fs' % (
        len(st['x']), st['x'].min(), st['x'].max(), st['gap_rear_leg'][np.abs(st['x']) < 540].max(), time.time() - t0))
    RE = RayMeshIntersector(E); ME = tomf(E)
    only = sys.argv[1:]
    rep = json.load(open(f'{OUT}/core_report.json')) if only and os.path.exists(f'{OUT}/core_report.json') else {}
    for sec, x0, x1 in SECTIONS:
        if only and sec not in only: continue
        t = time.time()
        if sec == 'R':
            # the spoiler is mirror-symmetric (to 0.02 mm); the car model under it is not quite (up to ~1 mm), which would
            # make the two sides core slightly differently. The right section is the exact mirror of the left one.
            Lm = trimesh.load(f'{OUT}/cored_L.stl'); cored = Lm.copy(); cored.vertices[:, 0] *= -1; cored.invert()
            cored.export(f'{OUT}/cored_R.stl')
            rep['R'] = dict(rep.get('L', {}), x=[x0, x1], mirrored_from='L', seconds=round(time.time() - t, 1))
            print('R mirrored from L', flush=True); json.dump(rep, open(f'{OUT}/core_report.json', 'w'), indent=1)
            continue
        M = ME
        if x0 > -HALF + 1e-6: M = M.trim_by_plane([1.0, 0, 0], x0)
        if x1 < HALF - 1e-6: M = M.trim_by_plane([-1.0, 0, 0], -x1)
        slab = totm(M); b = slab.bounds
        box = ((max(x0 - MARGIN, -HALF - 2), b[0, 1] - 3, b[0, 2] - 3), (min(x1 + MARGIN, HALF + 2), b[1, 1] + 3, b[1, 2] + 3))
        pm, info = pocket_mesh(RE, vis_pts, box, st, skirt_pts)
        assert pm.is_watertight, f'{sec}: pocket mesh not watertight'
        cut = tomf(pm) - LEGS
        res_ = M - cut
        cored, tol, nsx = clean_written(lambda t_: keep_main(weld(totm(res_.simplify(t_) if t_ else res_))), sec, (0.0, 0.001, 0.002, 0.004))
        info['cleanup_microns'] = round(tol * 1000); info['folded_faces'] = nsx
        bodies = len(cored.split(only_watertight=False))
        cored.export(f'{OUT}/cored_{sec}.stl')
        rep[sec] = dict(x=[x0, x1], solid_cm3=round(slab.volume / 1000, 1), cored_cm3=round(cored.volume / 1000, 1),
                        removed_pct=round(100 * (1 - cored.volume / slab.volume), 1), bodies=bodies,
                        **{k: (round(v, 1) if isinstance(v, float) else v) for k, v in info.items()},
                        watertight=bool(cored.is_watertight), faces=len(cored.faces), seconds=round(time.time() - t, 1))
        print(sec, json.dumps(rep[sec]), flush=True)
        assert bodies == 1, f'{sec} is in {bodies} bodies'
        json.dump(rep, open(f'{OUT}/core_report.json', 'w'), indent=1)
    print('done in %.0fs' % (time.time() - t0))
