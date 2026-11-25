"""v15 step 1: core the solid spoiler (v14/out/E4.stl: the v6 body with the ducktail lip ends blended and the step under
the back faired) section by section (left, centre, right) into a thin shell, open underneath.
  1. Faces that sit on the car in front of the rim line (the line where the underside leaves the car at the back), and
     the fins' pillar side, are hidden: the shell opens through them. All other faces are visible and stay exactly as
     they are, with a skin T_SKIN (4 mm) under them; that includes the spoiler's own underside behind the rim line, under
     the ducktail lip.
  2. Per section, on a 0.5 mm voxel grid aligned to one global lattice (so neighbouring sections agree exactly at the
     seams), one smooth removal field: everything more than the skin below the visible faces, except a closed layer
     over the underside at the front (tape band) and the back (adhesive band) that thins smoothly to nothing, so the
     opening starts with no step; joint lands (LAND_T) along the cuts for the pins and tongues, tapering smoothly back to
     the skin. The field is Gaussian-smoothed (SHELL_SIG), so every inside corner is rounded and nothing shows a voxel.
     Marching cubes gives the region to remove; cored section = section - region.
The right section is the mirror of the left one. Writes v15/out/cored_L|C|R.stl, rim_curve.npz, core_report.json.
Run from spoiler/:  python3 v15/src/p1_core.py [L C R]"""
import sys, os, json, time; sys.path.insert(0, 'v15/src'); sys.path.insert(0, 'v6/src')
import numpy as np, trimesh, manifold3d as mf
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes
from trimesh.ray.ray_pyembree import RayMeshIntersector
from parity import fill_inside
from bowtie import tomf, totm
from check import report
from layout import (E_PATH, CAR_PATH, OUT, HALF, SECTIONS, T_SKIN, S_FIN, FIN_X, VOX, MARGIN, UNDER_GAP, CUT_GAP, RIM_X,
                    TIP_T, OPEN_H, BACK_W, K_WALL, T_CH, WALL_FADE_X, LAND_T, LAND, SHELL_SIG, chord_plane)
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

def unfold(m, name='', rounds=6):
    """the booleans can leave a few folded (self-intersecting) faces, sub-millimetre (where a rounded edge meets the
    underside at a slant, or on a splice seam of the body): take out each fold with the ring of faces round it and fill
    the small hole again, until the mesh as written to a float32 STL has none. Returns (mesh, rounds used); the surface
    moves by well under a micron."""
    import tempfile, pymeshlab
    from check import selfx
    def written(q):
        with tempfile.NamedTemporaryFile(suffix='.stl') as f:
            q.export(f.name); return trimesh.load(f.name)
    w = written(m); v0 = w.volume
    for r in range(rounds + 1):
        sx = selfx(w)
        if len(sx) == 0:
            assert w.is_watertight and w.is_winding_consistent and abs(w.volume - v0) < 1.0, f'{name}: unfolding broke the mesh'
            return w, r
        if r == rounds: break
        print('   %s: %d folded faces, taken out and filled' % (name, len(sx)), flush=True)
        ms = pymeshlab.MeshSet(); ms.add_mesh(pymeshlab.Mesh(vertex_matrix=np.asarray(w.vertices, float), face_matrix=np.asarray(w.faces, np.int32)))
        ms.apply_filter('compute_selection_by_self_intersections_per_face')
        ms.apply_filter('apply_selection_dilatation')                   # the folds and one ring round them
        ms.apply_filter('meshing_remove_selected_vertices_and_faces')
        ms.apply_filter('meshing_remove_unreferenced_vertices')
        ms.apply_filter('meshing_close_holes', maxholesize=200, newfaceselected=False, selfintersection=False)
        g = ms.current_mesh(); w = written(trimesh.Trimesh(g.vertex_matrix(), g.face_matrix(), process=True))
    raise AssertionError(f'{name}: folded faces remain after unfolding')

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

def smoothstep(t):
    t = np.clip(t, 0.0, 1.0); return t * t * (3.0 - 2.0 * t)

def shell_mesh(RE, vis_pts, hid_pts, box, seams, chord, rim_xz):
    """v15: the region to remove inside box, as a closed mesh (grid on the global lattice): one opening, everything more
    than the skin below the visible faces (vis_pts), open through the underside on the car (hid_pts), between a 30-degree
    ramp at the front (where the part gets OPEN_H thick) and one at the back (BACK_W in front of the rim line); joint
    lands along the cuts; and a hidden channel inside the back band. One field, Gaussian-smoothed, so the inside of the
    shell is smooth everywhere, nothing starts with a step and the opening's edges are clean lines.
    rim_xz: the rim line in plan (x, z), sorted by x.
    A removal piece is kept if it opens through the hidden faces, or runs through one of the section's seams (x in
    seams) or across its front/rear cut (chord = (n, d)); anything sealed is left solid."""
    lo = np.floor(np.array(box[0], float) / VOX) * VOX; hi = np.ceil(np.array(box[1], float) / VOX) * VOX
    shape = np.round((hi - lo) / VOX).astype(int)
    xs = lo[0] + (np.arange(shape[0]) + 0.5) * VOX; zs = lo[2] + (np.arange(shape[2]) + 0.5) * VOX
    X, Z = np.meshgrid(xs, zs, indexing='ij')
    jy = lambda y: np.clip(np.round((y - lo[1]) / VOX - 0.5).astype(int), 0, shape[1])
    inside = fill_inside(RE, xs, zs, lo[1] - 5.0, shape[1], jy)         # ray parity, robust to rays along edges (parity.py)
    near_in = ndi.binary_dilation(inside, iterations=6)
    # plan fields (x, z): the lines where the opening starts at the front and at the back, and the skin (with the lands)
    th = inside.sum(axis=1).astype(np.float32) * VOX                    # the part's thickness in each column
    th = ndi.gaussian_filter(th, 2.0 / VOX)
    gx, gz = np.gradient(th, VOX); g = np.maximum(np.hypot(gx, gz), 0.03); del gx, gz
    s_o = np.clip((th - OPEN_H) / g, -40.0, 40.0); del th, g             # plan distance past the line where it is OPEN_H thick
    zr = np.interp(xs, rim_xz[:, 0], rim_xz[:, 1])[:, None]
    s_b = np.clip(zr - Z - BACK_W, -40.0, 40.0)                          # plan distance in front of the back band
    fade = 1.0 - smoothstep((np.abs(X) - WALL_FADE_X[0]) / (WALL_FADE_X[1] - WALL_FADE_X[0]))
    f_front = fade * (1.0 - smoothstep((Z - (zr - BACK_W - 40.0)) / 15.0))   # the front ramp belongs to the front only
    s_o = (s_o * f_front + 40.0 * (1.0 - f_front)).astype(np.float32)[:, None, :]; del f_front
    s_b = (s_b * fade + 40.0 * (1.0 - fade)).astype(np.float32)[:, None, :]
    d_ch = np.abs(chord[0][0] * X + chord[0][2] * Z - chord[1])
    w = 1.0 - smoothstep((d_ch - LAND[0]) / (LAND[1] - LAND[0]))
    for sx in seams:                                                     # span seams: up to the back band
        w_s = (1.0 - smoothstep((np.abs(X - sx) - LAND[0]) / (LAND[1] - LAND[0]))) * (1.0 - smoothstep((Z - (zr - BACK_W - 12.0)) / 10.0))
        w = np.maximum(w, w_s)
    t_skin = (T_SKIN + (LAND_T - T_SKIN) * w).astype(np.float32)[:, None, :]
    del X, Z, d_ch, w, fade
    # exact distances where they matter (the lands are 8.6 mm, the ramps up to ~12 mm), the distance transform beyond
    D = distance_field(vis_pts, lo, hi, shape, near_in, lambda D: D < 12.5)                 # below the visible faces
    Dh = distance_field(hid_pts, lo, hi, shape, near_in, lambda D: D < 12.5)                # over the underside on the car
    S = np.minimum(D, Dh); np.negative(S, out=S, where=inside)           # signed distance to the body (negative inside)
    kn = 1.0 / np.sqrt(1.0 + K_WALL ** 2)
    Wb = Dh * (-K_WALL); Wb += s_b; Wb *= kn                             # > 0 in front of the back ramp
    # the hidden channel inside the back band: at least T_CH from the top, the lip, the underside and the back ramp
    C_ = D - T_CH; np.minimum(C_, Dh - T_CH, out=C_); np.minimum(C_, -Wb - T_CH, out=C_)
    np.copyto(C_, -1.0, where=~inside)
    # the opening: more than the skin below the visible faces, and past both ramps
    D -= t_skin
    W = Dh * (-K_WALL); W += s_o; W *= kn; np.minimum(D, W, out=D); del W
    np.minimum(D, Wb, out=D); del Wb, Dh
    np.maximum(D, C_, out=D); del C_                                     # opening or channel
    G = ndi.gaussian_filter(D, SHELL_SIG / VOX); del D, S                # smooth: rounded inside corners, no voxel steps; the
                                                                        # ramps meet the underside along a crisp, clean line
    zone = ndi.binary_dilation(inside, iterations=2)
    G[~zone] = -1.0
    deep = G > 0
    lab, n = ndi.label(deep)
    opens = np.unique(lab[deep & ~inside]); opens = opens[opens > 0]
    keep = np.isin(lab, opens)                                           # open through the hidden faces
    ii = np.argwhere(deep & ~keep)
    ch_kept, ch_drop = [], 0
    if len(ii):
        ll = lab[tuple(ii.T)]; P_ = lo + (ii + 0.5) * VOX; xv = P_[:, 0]; sv = P_ @ np.asarray(chord[0], float) - chord[1]
        for L_ in np.unique(ll):
            k = ll == L_; x_a, x_b = xv[k].min(), xv[k].max()
            through = any(x_a < sx - VOX and x_b > sx + VOX for sx in seams) or (sv[k].min() < -VOX and sv[k].max() > VOX)
            if k.sum() > 50 and through:
                keep |= lab == L_; ch_kept.append([int(k.sum()), round(float(x_a), 1), round(float(x_b), 1)])
            else: ch_drop += int(k.sum())
        del ll, P_, xv, sv
    del ii
    sealed = int(deep.sum() - keep.sum())
    bridged = 0
    for _ in range(12):                                                  # never cut a bit of the part off
        lab2, n2 = ndi.label(inside & ~keep)
        if n2 <= 1: break
        sizes = np.bincount(lab2.ravel()); sizes[0] = 0; small = (lab2 > 0) & (lab2 != np.argmax(sizes))
        give = keep & ndi.binary_dilation(small, iterations=4)
        keep &= ~give; bridged += int(give.sum())
    del lab
    G[deep & ~keep] = -1.0
    opened = float((keep & inside).sum() * VOX ** 3 / 1000)
    for lev in (0.0123, 0.0317, 0.0571):
        vv, ff, _, _ = marching_cubes(np.pad(G, 1, constant_values=-1.0), level=lev, spacing=(VOX, VOX, VOX))
        vv = vv - VOX * 0.5 + lo
        m = trimesh.Trimesh(vv, ff, process=False)
        if m.is_watertight: break
    if m.volume < 0: m.invert()
    trimesh.smoothing.filter_taubin(m, iterations=6)
    return m, dict(voxels=int(np.prod(shape)), inside_cm3=float(inside.sum() * VOX ** 3 / 1000), removed_cm3=opened,
                   removal_pieces=int(len(opens)) + len(ch_kept), dropped_voxels=ch_drop, sealed_voxels=sealed, bridged_voxels=bridged)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    E = trimesh.load(E_PATH); car = trimesh.load(CAR_PATH, process=False)
    dcar = car_distance(E, car); contact = dcar < UNDER_GAP
    ddown = car_distance(E, car, (0, -1.0, 0)); dup = car_distance(E, E, (0, 1.0, 0))
    cuttable = ((dcar < CUT_GAP) | ((E.face_normals[:, 1] < -0.25) & (ddown < 80.0)) |
                ((E.face_normals[:, 1] < 0.3) & (np.abs(E.triangles_center[:, 0]) < 560) & (dup < 40.0)))
    # v15: from a few faces on the fins' pillar side the test ray slips past the car model, so they would count as visible
    # and keep a full skin under them: lumps hanging into the pocket. The visible faces form one connected outer surface;
    # any small island of 'visible' faces inside the cuttable area is cuttable too.
    cuttable = clean_cuttable(E, cuttable)
    st = rim.rim_curve(E, car); np.savez(f'{OUT}/rim_curve.npz', **st)
    o = np.argsort(st['x']); rim_xz = np.column_stack([st['x'][o], st['z'][o]])
    # v15: the shell opens only through faces that sit on (or face) the car IN FRONT of the rim line, and through the fins'
    # pillar side; behind the rim line the spoiler's own underside (under the ducktail lip) is a visible face with its skin
    c = E.triangles_center
    hidden = cuttable & ((c[:, 2] < np.interp(c[:, 0], rim_xz[:, 0], rim_xz[:, 1])) | (np.abs(c[:, 0]) > RIM_X))
    np.save(f'{OUT}/E2_contact.npy', contact); np.save(f'{OUT}/E2_cuttable.npy', hidden)
    vis_pts = surface_points(trimesh.Trimesh(E.vertices, E.faces[~hidden], process=False), 0.35)
    hid_pts = surface_points(trimesh.Trimesh(E.vertices, E.faces[hidden], process=False), 0.35)
    inner = np.abs(st['x']) < 540
    print('rim: %d stations, x %.0f..%.0f; back edge %.1f-%.1f mm deep at the rim; %d visible, %d hidden faces; %.1fs' % (
        len(st['x']), st['x'].min(), st['x'].max(), np.nanmin(st['depth_tip'][inner]), np.nanmax(st['depth_tip'][inner]),
        (~hidden).sum(), hidden.sum(), time.time() - t0), flush=True)
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
        pm, info = shell_mesh(RE, vis_pts, hid_pts, box, seams, chord_plane(sec), rim_xz)
        assert pm.is_watertight, f'{sec}: removal mesh not watertight'
        cut = tomf(pm)
        res_ = M - cut
        cored, tol, nsx = clean_written(lambda t_: keep_main(weld(totm(res_.simplify(t_) if t_ else res_))), sec, (0.0, 0.001, 0.002, 0.004))
        if nsx: cored, ur = unfold(cored, sec); nsx = 0; info['unfold_rounds'] = ur   # v15: relax the few folds the booleans left
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
