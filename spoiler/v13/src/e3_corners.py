"""v13 step 0: the spoiler body E3 = the v6 body E2 with its two outer rear corners blended (the "ducktail fin").
At each outer rear corner the ducktail lip is a thin blade that sits on the rounded end of the body: there is a sharp
notch under it, it stops with a squared end, and beyond its end the top surface meets the rounded end with a small
step. Here the solid is rebuilt locally from its signed distance field:
  - a rolling-ball fillet (a morphological closing of radius R_FILLET) fills the notch and the step,
  - a light Gaussian smoothing (CORNER_SIG) right along the corner rounds the lip's squared end and its crease,
  - a smooth weight brings the change in along the corner and fades it out to nothing well inside the corner's box.
The new surface is built by marching cubes from a distance field that is exact on the faceted surface (distance to the
nearest face's plane), so wherever the blend changed nothing it lies on the original surface (to about 0.002 mm) and the
splice on the box faces leaves no seam. Writes v13/out/E3.stl and v13/out/e3_report.json.   Run from spoiler/:  python3 v13/src/e3_corners.py"""
import sys, os, json, time, hashlib; sys.path.insert(0, 'v13/src'); sys.path.insert(0, 'v6/src')
import numpy as np, trimesh, manifold3d as mf
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes
from trimesh.ray.ray_pyembree import RayMeshIntersector
from bowtie import tomf, totm
from check import report, selfx
from layout import OUT, E2_PATH, E_PATH, CORNER_CURVE, CORNER_BOX, R_FILLET, CORNER_W, CORNER_WS, CORNER_SIG
from p1_core import weld, keep_main

H = 0.25                                                                 # voxel size (mm)
T0 = time.time()
log = lambda *a: print('  %5.0fs' % (time.time() - T0), *a, flush=True)

def samples(m, spacing):
    """points on every face of m about `spacing` apart, with the index of the face each one lies on"""
    T = m.triangles; e = np.linalg.norm(T - np.roll(T, 1, axis=1), axis=2).max(1)
    nsub = np.maximum(1, np.ceil(e / spacing).astype(int)); P, F = [], []
    for n in np.unique(nsub):
        idx = np.flatnonzero(nsub == n)
        ij = np.array([(i, j) for i in range(n + 1) for j in range(n + 1 - i)], float) / n
        w = np.column_stack([1 - ij.sum(1), ij])
        P.append(np.einsum('kw,twd->tkd', w, T[idx]).reshape(-1, 3)); F.append(np.repeat(idx, len(w)))
    return np.vstack(P), np.concatenate(F)

def inside_box(R, lo, shape):
    """inside test on the grid: ray parity along +y from far below the solid (so the box may cut the solid anywhere)"""
    xs = lo[0] + (np.arange(shape[0]) + 0.5) * H; zs = lo[2] + (np.arange(shape[2]) + 0.5) * H
    X, Z = np.meshgrid(xs, zs, indexing='ij')
    O = np.column_stack([X.ravel(), np.full(X.size, -400.0), Z.ravel()])
    loc, ir, _ = R.intersects_location(O, np.tile([0, 1.0, 0], (len(O), 1)), multiple_hits=True)
    inside = np.zeros(shape, bool)
    order = np.lexsort((loc[:, 1], ir)); ir, ys = ir[order], loc[order, 1]
    st = np.flatnonzero(np.r_[True, ir[1:] != ir[:-1]]); en = np.r_[st[1:], len(ir)]
    jy = lambda y: int(np.clip(np.ceil((y - lo[1]) / H - 0.5), 0, shape[1]))   # first voxel whose centre is at or above y
    for s, e in zip(st, en):
        if (e - s) % 2: continue
        i, k = np.unravel_index(ir[s], X.shape)
        for a, b in zip(ys[s:e:2], ys[s + 1:e:2]): inside[i, jy(a):jy(b), k] = True   # exactly the centres between a and b
    return inside

def signed_distance(inside, lo, tree, pts, nrm, band):
    """signed distance (mm, negative inside). Within 0.6 mm of the surface: the distance to the plane of the nearest
    sample's face (exact on the faceted surface, so the zero level is the original surface itself, with no ripple),
    blending to the distance to the nearest sample by 1.2 mm; beyond `band` the distance transform. The sign is the
    inside test's (exact at the voxel centres)."""
    d = (ndi.distance_transform_edt(~inside) - ndi.distance_transform_edt(inside)).astype(np.float32) * H
    ii = np.argwhere(np.abs(d) < band); P = lo + (ii + 0.5) * H
    dist, j = tree.query(P, workers=-1)
    sgn = np.where(inside[tuple(ii.T)], -1.0, 1.0)
    pp = ((P - pts[j]) * nrm[j]).sum(1)
    near = np.where(np.sign(pp) == sgn, pp, sgn * dist)
    a = np.clip((dist - 0.6) / 0.6, 0.0, 1.0); a = a * a * (3 - 2 * a)      # plane distance alone within 0.6 mm
    d[tuple(ii.T)] = ((1 - a) * near + a * sgn * dist).astype(np.float32)
    return d

def corner_weight(lo, shape, curve, wr):
    """1 within wr[0] of the corner curve, falling smoothly to 0 at wr[1]; also brought in and out along the curve's
    first and last 12 mm. Computed slab by slab to keep memory low."""
    seg = np.linspace(0, 1, 40)[:, None]
    C = np.vstack([a + seg * (b - a) for a, b in zip(curve[:-1], curve[1:])])           # dense points on the polyline
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))]
    tree = cKDTree(C); w0, w1 = wr
    gy = lo[1] + (np.arange(shape[1]) + 0.5) * H; gz = lo[2] + (np.arange(shape[2]) + 0.5) * H
    Y, Z = np.meshgrid(gy, gz, indexing='ij')
    out = np.zeros(shape, np.float32)
    for i in range(shape[0]):
        x = lo[0] + (i + 0.5) * H
        P = np.column_stack([np.full(Y.size, x), Y.ravel(), Z.ravel()])
        dist, j = tree.query(P, distance_upper_bound=w1 + 1.0, workers=-1)
        ok = np.isfinite(dist)
        if not ok.any(): continue
        w = np.zeros(len(P)); dd = dist[ok]; jj = j[ok]
        a = np.clip((w1 - dd) / (w1 - w0), 0, 1); a = a * a * (3 - 2 * a)
        r = np.clip(s[jj] / 12.0, 0, 1) * np.clip((s[-1] - s[jj]) / 12.0, 0, 1); r = r * r * (3 - 2 * r)
        w[ok] = a * r; out[i] = w.reshape(Y.shape)
    return out

def blend_corner(E, side):
    lo = np.array([min(side * CORNER_BOX[0][0], side * CORNER_BOX[1][0]), CORNER_BOX[0][1], CORNER_BOX[0][2]], float)
    hi = np.array([max(side * CORNER_BOX[0][0], side * CORNER_BOX[1][0]), CORNER_BOX[1][1], CORNER_BOX[1][2]], float)
    shape = np.round((hi - lo) / H).astype(int)
    key = hashlib.md5(repr((CORNER_CURVE, CORNER_BOX, R_FILLET, CORNER_W, CORNER_WS, CORNER_SIG, H, side, os.path.getsize(E2_PATH))).encode()).hexdigest()[:10]
    cache = f'{OUT}/_e3_field_{key}.npz'                                 # the blended field is slow to build: keep it
    if os.path.exists(cache):
        z = np.load(cache); dn, reg = z['dn'], z['reg']; added, removed, wmax = z['stats']; log('field from', cache)
    else:
        dn, reg, added, removed, wmax = blend_field(E, side, lo, hi, shape)
        np.savez(cache, dn=dn, reg=reg, stats=np.array([added, removed, wmax]))
    return build_surface(dn, reg, lo, hi, shape, added, removed, wmax)

def blend_field(E, side, lo, hi, shape):
    inside = inside_box(RayMeshIntersector(E), lo, shape); log('inside')
    c = E.triangles_center
    sub = trimesh.Trimesh(E.vertices, E.faces[np.all((c > lo - 12) & (c < hi + 12), axis=1)], process=False)
    pts, fi = samples(sub, 0.25); nrm = sub.face_normals[fi]; tree = cKDTree(pts); log('samples', len(pts))
    band = R_FILLET + 3.0
    d = signed_distance(inside, lo, tree, pts, nrm, band); del inside; log('distance')
    # closing: dilate by R_FILLET, then measure the distance back from the dilated surface
    vv, ff, _, _ = marching_cubes(d, level=R_FILLET, spacing=(H, H, H))
    dc = d.copy()
    ii = np.argwhere(d < R_FILLET + 0.01); ii = ii[d[tuple(ii.T)] > -band]
    e1 = cKDTree(vv + lo + 0.5 * H).query(lo + (ii + 0.5) * H, workers=-1)[0].astype(np.float32)
    dc[tuple(ii.T)] = np.minimum(d[tuple(ii.T)], R_FILLET - e1); del ii, e1, vv, ff; log('closing')
    curve = np.array([[side * p[0], p[1], p[2]] for p in CORNER_CURVE], float)
    ws = corner_weight(lo, shape, curve, CORNER_WS)
    dc = ws * ndi.gaussian_filter(dc, CORNER_SIG / H) + (1 - ws) * dc; del ws        # round the lip's end and crease
    w = corner_weight(lo, shape, curve, CORNER_W)
    dn = (w * dc + (1 - w) * d).astype(np.float32); del dc
    dn = (w * ndi.gaussian_filter(dn, 0.6) + (1 - w) * dn).astype(np.float32)   # no voxel-scale ripple where it is rebuilt
    added = float(((dn <= 0) & (d > 0)).sum() * H ** 3); removed = float(((dn > 0) & (d <= 0)).sum() * H ** 3)
    chg = np.abs(d - dn); del d; log('blend')
    # the region to rebuild: a smooth blob 2 mm round everything the blend changed by more than 0.01 mm. On its surface the
    # new and the original shapes agree to 0.01 mm, so the splice leaves no seam; everywhere else the original triangles stay
    reg = ndi.binary_dilation(chg > 0.01, iterations=8); del chg
    return dn, reg, added, removed, float(w.max())

def build_surface(dn, reg, lo, hi, shape, added, removed, wmax):
    """the new corner: marching cubes of the blended field (closed by padding the box with 'outside'), cut to a box 1 mm
    inside the grid. The field is exact on the faceted surface, so where the blend changed nothing (all of the box but the
    corner itself, and so on the box faces where it is spliced in) the new surface lies on the original to about 0.002 mm"""
    vv, ff, _, _ = marching_cubes(np.pad(dn, 1, constant_values=5.0), level=0.0, spacing=(H, H, H))
    m = trimesh.Trimesh(vv + lo - 0.5 * H, ff, process=True)
    if m.volume < 0: m.invert()
    BOX = mf.Manifold.cube(list(hi - lo - 2.0)).translate(list(lo + 1.0))
    corner = tomf(m) ^ BOX
    nsx = len(selfx(totm(corner))); assert nsx == 0, 'corner patch self-intersects (%d faces)' % nsx
    log('surface: %d faces, changed region %.1f cm3' % (len(m.faces), reg.sum() * H ** 3 / 1000))
    return corner, BOX, dict(box=[lo.round(1).tolist(), hi.round(1).tolist()], voxels=int(np.prod(shape)),
                             added_mm3=round(float(added), 1), removed_mm3=round(float(removed), 1), max_weight=round(float(wmax), 2))

if __name__ == '__main__':
    E = trimesh.load(E2_PATH)
    if '--test' in sys.argv:                                             # left corner only, for a look
        corner, BOX, info = blend_corner(E, -1); log(info)
        totm((tomf(E) - BOX) + corner).export(sys.argv[-1]); sys.exit()
    M = tomf(E); rep = {}
    for side, name in ((-1, 'left'), (1, 'right')):
        corner, BOX, info = blend_corner(E, side)
        M = (M - BOX) + corner
        rep[name] = info; log(name, info)
    raw = totm(M)
    for tol in (0.0, 1e-6, 1e-5, 1e-4, 1e-3):                           # merge only near-duplicate points: the smallest
        try: E3 = keep_main(weld(raw, tol=tol) if tol else raw)          # merge that gives one clean closed body
        except AssertionError: continue
        r, sx = report(E3, 'E3')
        if r['watertight'] and r['bodies'] == 1 and r['selfx_faces'] == 0: break
        log('merge %g: %s' % (tol, {k: r[k] for k in ('watertight', 'bodies', 'selfx_faces')}))
    rep['E3'] = {k: r[k] for k in ('faces', 'watertight', 'winding', 'volume_cm3', 'bodies', 'selfx_faces', 'zero_area')}
    rep['E2_volume_cm3'] = round(float(E.volume) / 1000, 2)
    log(rep['E3'], 'E2 volume %.2f cm3' % rep['E2_volume_cm3'])
    assert r['watertight'] and r['bodies'] == 1 and r['selfx_faces'] == 0, 'E3 is not one clean closed body'
    E3.export(E_PATH); json.dump(rep, open(f'{OUT}/e3_report.json', 'w'), indent=1)
    log('wrote', E_PATH)
