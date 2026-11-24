"""v13 step 1: core the solid spoiler (v6/out/E2.stl) section by section (left, centre, right) so that no part of it is
thicker than 10 mm, with the new smooth tip at the back (no groove, no leg).
  1. As v9: faces on the car and faces that face the car may be cut; all other faces stay exactly as they are.
  2. Per section, on a 0.5 mm voxel grid aligned to one global lattice (so neighbouring sections agree exactly at the
     seams), as smooth fields:
     POCKET  everything deeper than the skin below the faces that stay (pocket under the ridge, fin tips from the pillar
             side), but only in front of the rounded tip: the pocket ceiling runs down a 45-degree slope, filleted, to a
             rounded tip (radius TIP_R) on the car; behind the tip nothing comes off from below, so the spoiler's own
             underside carries on unchanged;
     CHANNEL where the back edge is deeper than C_MIN (|x| > ~180 mm) a solid tip would be thicker than 10 mm, so it is
             hollow inside: a channel kept SKIN_V under the top, SKIRT over the underside and WALL behind the slope.
             It runs through the span seams, so in each part it opens only on the seam face.
     Marching cubes gives the smooth surface of the region to remove; cored section = section - region.
The right section is the mirror of the left one. Writes v13/out/cored_L|C|R.stl, rim_curve.npz, core_report.json.
Run from spoiler/:  python3 v13/src/p1_core.py [L C R]"""
import sys, os, json, time; sys.path.insert(0, 'v13/src'); sys.path.insert(0, 'v6/src')
import numpy as np, trimesh, manifold3d as mf
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes
from trimesh.ray.ray_pyembree import RayMeshIntersector
from bowtie import tomf, totm
from check import report
from layout import (E_PATH, CAR_PATH, OUT, HALF, SECTIONS, T_SKIN, S_FIN, FIN_X, VOX, MARGIN, UNDER_GAP, CUT_GAP, RIM_X,
                    RIM_FADE, RIM_END, END_FADE, END_SHIFT, TIP_SHIFT, EDGE_DROP, TIP_T, M_FRONT, K_BLEND, SKIN_V, SKIRT, WALL, C_MIN)
import rim
from rim import tip_profile, wall_line

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

def smin(a, b, k):
    """smooth minimum (polynomial, blend width k): rounds the corner where two removal fields meet into a fillet.
    Written to keep few full-size temporaries (the grids are up to 160 million voxels)"""
    h = b - a; h *= 0.5 / k; h += 0.5; np.clip(h, 0.0, 1.0, out=h)
    r = a - b; r *= h; r += b                                            # b (1 - h) + a h
    q = 1.0 - h; q *= h; q *= k; r -= q                                  # - k h (1 - h)
    return r

def distance_field(pts, lo, hi, shape, band, exact_where):
    """distance (mm) from each voxel centre to the nearest of pts: a distance transform, then exact distances for the
    voxels where exact_where(D) holds (near the levels that matter)"""
    P = pts[np.all((pts >= lo - 1) & (pts <= hi + 1), axis=1)]
    if len(P) == 0: return np.full(shape, 1e3, np.float32)
    idx = np.floor((P - lo) / VOX).astype(int); ok = np.all((idx >= 0) & (idx < shape), axis=1)
    seed = np.zeros(shape, bool); seed[tuple(idx[ok].T)] = True
    D = ndi.distance_transform_edt(~seed).astype(np.float32) * VOX; del seed
    ii = np.argwhere(exact_where(D) & band)
    if len(ii):
        sub = pts[np.all((pts >= lo - 20) & (pts <= hi + 20), axis=1)]
        D[tuple(ii.T)] = cKDTree(sub).query(lo + (ii + 0.5) * VOX, workers=-1)[0].astype(np.float32)
    return D

def clean_cuttable(E, cuttable, max_area=500.0):
    """visible faces form one connected outer surface: small islands of visible faces inside cuttable areas are cuttable"""
    vis = ~cuttable; adj = E.face_adjacency; kk = vis[adj[:, 0]] & vis[adj[:, 1]]
    comps = trimesh.graph.connected_components(adj[kk], nodes=np.flatnonzero(vis), min_len=1)
    big = max(len(c) for c in comps); out = cuttable.copy(); n = 0
    for c in comps:
        if len(c) < big and E.area_faces[c].sum() < max_area: out[c] = True; n += 1
    print('cuttable: %d small islands of visible faces made cuttable' % n, flush=True)
    return out

def pocket_mesh(RE, vis_pts, box, st, back_pts, seams):
    """the region to remove inside box, as a closed mesh (grid on the global lattice):
    the POCKET (open to the car): deeper than the skin below the faces that stay, and in front of the rounded tip;
    the CHANNEL (hidden, v13): where the back edge is deeper than C_MIN, the inside of it, kept SKIN_V below the top,
    SKIRT above the spoiler's own underside behind the tip (back_pts) and WALL behind the tip's 45-degree face.
    seams: the x of this section's seam planes; a channel piece is kept only if it runs through one (so it opens there)"""
    lo = np.floor(np.array(box[0], float) / VOX) * VOX; hi = np.ceil(np.array(box[1], float) / VOX) * VOX
    shape = np.round((hi - lo) / VOX).astype(int)
    xs = lo[0] + (np.arange(shape[0]) + 0.5) * VOX; ys = (lo[1] + (np.arange(shape[1]) + 0.5) * VOX).astype(np.float32)
    zs = lo[2] + (np.arange(shape[2]) + 0.5) * VOX
    X, Z = np.meshgrid(xs, zs, indexing='ij')
    O = np.column_stack([X.ravel(), np.full(X.size, lo[1] - 5.0), Z.ravel()])
    loc, ir, it = RE.intersects_location(O, np.tile([0, 1.0, 0], (len(O), 1)), multiple_hits=True)
    inside = np.zeros(shape, bool)
    order = np.lexsort((loc[:, 1], ir)); ir, yh = ir[order], loc[order, 1]
    starts = np.flatnonzero(np.r_[True, ir[1:] != ir[:-1]]); ends = np.r_[starts[1:], len(ir)]
    jy = lambda y: np.clip(np.round((y - lo[1]) / VOX - 0.5).astype(int), 0, shape[1])
    for s, e in zip(starts, ends):
        if (e - s) % 2: continue
        i, k = np.unravel_index(ir[s], X.shape)
        for a, b in zip(yh[s:e:2], yh[s + 1:e:2]): inside[i, jy(a):jy(b), k] = True
    # v13: the spoiler's own underside height in every column (first hit from below), lightly smoothed: the pocket's back
    # face rises from it, so the face always starts on the underside itself, at a definite angle
    ylow = np.full(X.size, np.nan, np.float32); ylow[ir[starts]] = yh[starts]; ylow = ylow.reshape(X.shape)
    hit = np.isfinite(ylow); num = ndi.gaussian_filter(np.where(hit, ylow, 0.0), 2.0)
    base = np.where(hit, num / np.maximum(ndi.gaussian_filter(hit.astype(float), 2.0), 1e-6) - EDGE_DROP, 1e3).astype(np.float32)
    del ylow, num
    near_in = ndi.binary_dilation(inside, iterations=3)
    sk = skin_at(xs)[:, None, None].astype(np.float32)
    # distance below the faces that stay (exact near the pocket skin and the channel's top skin)
    D = distance_field(vis_pts, lo, hi, shape, near_in,
                       lambda D: ((np.abs(D - sk) < 1.5) | ((D > SKIN_V - 1.5) & (D < C_MIN + 1.0))))
    G = D - sk
    # rim coordinates of every column: t forward of the rim line, u forward of the tip; fade weight at the rim's ends
    S2 = np.column_stack([st['x'], st['z']]); XZ = np.column_stack([X.ravel(), Z.ravel()]); _, j = cKDTree(S2).query(XZ)
    t = ((XZ - S2[j]) * st['N'][j]).sum(1).reshape(X.shape)
    u = (t - TIP_T).astype(np.float32); del XZ
    w = np.clip((RIM_END - np.abs(X)) / RIM_FADE, 0.0, 1.0).astype(np.float32)   # v13: 1 to beyond the spoiler's ends
    # POCKET: deeper than the skin, and in front of / below the rounded tip's surface (behind the tip nothing comes off
    # from below: the envelope drops away there, so the spoiler's own underside stays)
    # v13: no brim. The pocket's back face starts TIP_SHIFT forward of the contact line (END_SHIFT towards the spoiler's
    # ends), so behind it the spoiler's own underside carries on unchanged and flush, right round the back edge; the hidden
    # channel takes over inside the band this leaves solid. The face rises from the underside with a TIP_R round into the
    # 45-degree slope, so its edge meets the underside cleanly (no grazing cut)
    fe = np.clip((np.abs(X) - END_FADE[0]) / (END_FADE[1] - END_FADE[0]), 0.0, 1.0)
    sh = (TIP_SHIFT + (END_SHIFT - TIP_SHIFT) * fe * fe * (3 - 2 * fe)).astype(np.float32)
    ue = (u - sh).astype(np.float32)
    env = base + np.where(ue >= 0, tip_profile(ue), 3.0 * ue).astype(np.float32)
    B = env[:, None, :] - ys[None, :, None]
    P = smin(G, B, K_BLEND); del B
    for i in np.flatnonzero(w.min(axis=1) < 1.0):                        # the rim's ends: fade back to the plain skin
        P[i] = w[i][None, :] * P[i] + (1 - w[i][None, :]) * G[i]
    del G
    # a light smoothing (0.5 mm): the skin is an offset of the faceted top surface, whose facet edges would otherwise show
    # as faint creases in the pocket ceiling and along the edge of the slope
    P = ndi.gaussian_filter(P, 1.0, mode='nearest')
    # CHANNEL: inside the deep back edge only (C_MIN), kept off the top, the underside behind the tip and the tip's face
    D2 = distance_field(back_pts, lo, hi, shape, near_in, lambda D: D < C_MIN - SKIN_V + 1.5)
    V = D - SKIN_V
    tmp = D2 - SKIRT; np.minimum(V, tmp, out=V)
    np.add(D, D2, out=tmp); tmp -= C_MIN; np.minimum(V, tmp, out=V)
    del D, D2
    np.subtract(ys[None, :, None], (base + wall_line(ue))[:, None, :], out=tmp)
    tmp *= np.float32(np.cos(np.arctan(M_FRONT))); tmp -= WALL; np.minimum(V, tmp, out=V)
    np.negative(P, out=tmp); tmp -= SKIRT; np.minimum(V, tmp, out=V); del tmp     # and SKIRT clear of the pocket
    rimzone = (np.abs(X) <= RIM_X) & (t > -45.0) & (t < 35.0 + sh)
    V[~np.broadcast_to(rimzone[:, None, :], shape)] = -1.0
    V[~inside] = -1.0
    F = np.maximum(P, V, out=P); del P
    zone = ndi.binary_dilation(inside, iterations=2)
    deep = (F > 0) & zone
    lab, n = ndi.label(deep)
    opens = np.unique(lab[deep & ~inside]); opens = opens[opens > 0]
    keep = np.isin(lab, opens)
    # channel pieces: sealed in the section, kept if they run through one of its seams (they open on the seam face)
    ii = np.argwhere(deep & ~keep & (V > 0)); del V
    ch_kept, ch_drop = [], 0
    if len(ii):
        ll = lab[tuple(ii.T)]; xv = lo[0] + (ii[:, 0] + 0.5) * VOX
        for L_ in np.unique(ll):
            k = ll == L_; x_a, x_b = xv[k].min(), xv[k].max()
            if k.sum() > 50 and any(x_a < sx - VOX and x_b > sx + VOX for sx in seams):
                keep |= lab == L_; ch_kept.append([int(k.sum()), round(float(x_a), 1), round(float(x_b), 1)])
            else: ch_drop += int(k.sum())
    del ii
    sealed = int(deep.sum() - keep.sum())
    bridged = 0
    for _ in range(12):                                                  # never cut a bit of the part off
        lab2, n2 = ndi.label(inside & ~keep)
        if n2 <= 1: break
        sizes = np.bincount(lab2.ravel()); sizes[0] = 0; small = (lab2 > 0) & (lab2 != np.argmax(sizes))
        give = keep & ndi.binary_dilation(small, iterations=4)
        keep &= ~give; bridged += int(give.sum())
    del lab, lab2
    Gm = np.where(zone, F, -1.0).astype(np.float32); del F
    Gm[deep & ~keep] = -1.0
    for lev in (0.0123, 0.0317, 0.0571):
        vv, ff, _, _ = marching_cubes(np.pad(Gm, 1, constant_values=-1.0), level=lev, spacing=(VOX, VOX, VOX))
        vv = vv - VOX * 0.5 + lo
        m = trimesh.Trimesh(vv, ff, process=False)
        if m.is_watertight: break
    if m.volume < 0: m.invert()
    trimesh.smoothing.filter_taubin(m, iterations=6)
    return m, dict(voxels=int(np.prod(shape)), inside_cm3=float(inside.sum() * VOX ** 3 / 1000),
                   pocket_cm3=float(keep.sum() * VOX ** 3 / 1000), channel_pieces=ch_kept, channel_dropped_voxels=ch_drop,
                   sealed_voxels=sealed, bridged_voxels=bridged)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    E = trimesh.load(E_PATH); car = trimesh.load(CAR_PATH, process=False)
    dcar = car_distance(E, car); contact = dcar < UNDER_GAP
    ddown = car_distance(E, car, (0, -1.0, 0)); dup = car_distance(E, E, (0, 1.0, 0))
    cuttable = ((dcar < CUT_GAP) | ((E.face_normals[:, 1] < -0.25) & (ddown < 80.0)) |
                ((E.face_normals[:, 1] < 0.3) & (np.abs(E.triangles_center[:, 0]) < 560) & (dup < 40.0)))
    # v13: from a few faces on the fins' pillar side the test ray slips past the car model, so they would count as visible
    # and keep a full skin under them: lumps hanging into the pocket. The visible faces form one connected outer surface;
    # any small island of 'visible' faces inside the cuttable area is cuttable too.
    cuttable = clean_cuttable(E, cuttable)
    np.save(f'{OUT}/E2_contact.npy', contact); np.save(f'{OUT}/E2_cuttable.npy', cuttable)
    vis_pts = surface_points(trimesh.Trimesh(E.vertices, E.faces[~cuttable], process=False), 0.35)
    st = rim.rim_curve(E, car); np.savez(f'{OUT}/rim_curve.npz', **st)
    # the spoiler's own underside behind the tip (all cuttable faces there, per point so the edge follows the tip line):
    # the channel keeps SKIRT clear of it, so it stays exactly as it is
    cp = surface_points(trimesh.Trimesh(E.vertices, E.faces[cuttable], process=False), 0.35)
    S2 = np.column_stack([st['x'], st['z']]); _, j = cKDTree(S2).query(cp[:, [0, 2]])
    uq = ((cp[:, [0, 2]] - S2[j]) * st['N'][j]).sum(1) - TIP_T
    # (towards the ends, where the pocket closes, the underside in front of the tip is kept too, so it counts as well)
    back_pts = cp[(uq < END_SHIFT + 12.0) & (np.abs(cp[:, 0]) <= RIM_X + 5.0)]; del cp   # v13: the underside behind the pocket's edge
    inner = np.abs(st['x']) < 540
    print('rim: %d stations, x %.0f..%.0f; tip %.1f mm forward of the rim line, gap to the car %.1f-%.1f mm, back edge %.1f-%.1f mm deep; %.1fs' % (
        len(st['x']), st['x'].min(), st['x'].max(), TIP_T, st['gap_tip'][inner].min(), st['gap_tip'][inner].max(),
        np.nanmin(st['depth_tip'][inner]), np.nanmax(st['depth_tip'][inner]), time.time() - t0), flush=True)
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
        seams = [v for v in (x0, x1) if abs(v) < HALF - 1e-6]
        pm, info = pocket_mesh(RE, vis_pts, box, st, back_pts, seams)
        assert pm.is_watertight, f'{sec}: pocket mesh not watertight'
        cut = tomf(pm)
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
