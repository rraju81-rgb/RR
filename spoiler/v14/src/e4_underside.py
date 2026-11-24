"""v14 step 0b: the body E4 = E3 with the step along the back of the underside faired out.
The v6 body's underside was conformed to the car (with a 1.5 mm tape gap) over its contact band; behind the band it
meets the original underside with a step 2-5 mm tall, which runs along the whole back edge and shows as a line from
below. Here it is smoothed into one gentle ramp: the body's signed distance field is smoothed (Gaussian, STEP_SIG) around
the step line only (full within STEP_W[0] of it, nothing beyond STEP_W[1]), and the rebuilt surface is spliced in where
it meets the original. The left half is built and mirrored for the right (the body is symmetric to 0.02 mm), so both
sides match exactly and meet without a seam at x = 0.
Writes v14/out/E4.stl and v14/out/e4_report.json.   Run from spoiler/:  python3 v14/src/e4_underside.py"""
import sys, os, json, time; sys.path.insert(0, 'v14/src'); sys.path.insert(0, 'v6/src')
import numpy as np, trimesh, manifold3d as mf
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes
from trimesh.ray.ray_pyembree import RayMeshIntersector
from bowtie import tomf, totm
from check import report, selfx
from layout import OUT, E3_PATH, E_PATH, STEP_SIG, STEP_W, STEP_X
from p1_core import weld, keep_main
import e3_corners as e3

H = 0.4                                                                   # voxel size (mm)
SEG = 30.0                                                                # splice boxes along x (mm)
T0 = time.time()
log = lambda *a: print('  %5.0fs' % (time.time() - T0), *a, flush=True)

def step_line(E, st):
    """the step along the back of the underside, left half: for each x, where the underside (seen from below) is steepest
    within 35 mm in front of and 20 mm behind the contact line; smoothed along x"""
    R = RayMeshIntersector(E); xs = np.arange(-STEP_X[1], 0.01, 2.0); out = []
    for x in xs:
        i = np.argmin(np.abs(st['x'] - x)); zc = st['z'][i]
        zz = np.arange(zc - 35, zc + 20.01, 0.5)
        loc, ir, _ = R.intersects_location(np.column_stack([np.full(len(zz), x), np.full(len(zz), -400.0), zz]),
                                           np.tile([0, 1.0, 0], (len(zz), 1)), multiple_hits=False)
        y = np.full(len(zz), np.nan); y[ir] = loc[:, 1]
        g = np.gradient(y, zz); g[~np.isfinite(g)] = 0
        k = int(np.argmax(g)); out.append((x, y[k], zz[k], np.degrees(np.arctan(g[k]))))
    P = np.array(out)
    for c in (1, 2): P[:, c] = ndi.gaussian_filter1d(P[:, c], 3.0, mode='nearest')
    return P

def main():
    E = trimesh.load(E3_PATH); st = np.load(f'{OUT}/rim_curve.npz') if os.path.exists(f'{OUT}/rim_curve.npz') else None
    if st is None:
        import rim; car = trimesh.load('v6/car/out/car_body_conf.ply', process=False); st = rim.rim_curve(E, car)
    P = step_line(E, st); log('step line: %d points, steepest %.0f-%.0f deg' % (len(P), P[:, 3].min(), P[:, 3].max()))
    m = STEP_W[1] + 4 * STEP_SIG
    lo = np.array([-STEP_X[1] - m, P[:, 1].min() - m, P[:, 2].min() - m]); hi = np.array([m, P[:, 1].max() + m, P[:, 2].max() + m])
    lo = np.floor(lo / H) * H; hi = np.ceil(hi / H) * H; shape = np.round((hi - lo) / H).astype(int)
    log('box', lo.round(1).tolist(), hi.round(1).tolist(), 'voxels %.1fM' % (np.prod(shape) / 1e6))
    e3.H = H                                                              # the corner tools, on this grid
    cache = f'{OUT}/_e4_d_{os.path.getsize(E3_PATH)}_{H}_{lo[0]:.1f}_{lo[1]:.1f}_{lo[2]:.1f}.npy'
    if os.path.exists(cache): d = np.load(cache); log('distance from', cache)
    else:
        inside = e3.inside_box(RayMeshIntersector(E), lo, shape); log('inside')
        c = E.triangles_center
        sub = trimesh.Trimesh(E.vertices, E.faces[np.all((c > lo - 8) & (c < hi + 8), axis=1)], process=False)
        pts, fi = e3.samples(sub, 0.3); nrm = sub.face_normals[fi]; tree = cKDTree(pts); log('samples', len(pts))
        d = e3.signed_distance(inside, lo, tree, pts, nrm, 7.0); del inside; log('distance')   # exact within 7 mm
        np.save(cache, d)
    # weight: around the step line, and faded out towards the spoiler's ends (the corners are blended there already)
    curve = P[:, :3][:, [0, 1, 2]]
    w = e3.corner_weight(lo, shape, curve, STEP_W, ramps=(0.0, 0.0))
    xs = lo[0] + (np.arange(shape[0]) + 0.5) * H
    fx = np.clip((STEP_X[1] - np.abs(xs)) / (STEP_X[1] - STEP_X[0]), 0, 1); fx = fx * fx * (3 - 2 * fx)
    w *= fx[:, None, None].astype(np.float32); log('weight')
    dn = (w * ndi.gaussian_filter(d, STEP_SIG / H) + (1 - w) * d).astype(np.float32)
    added = float(((dn <= 0) & (d > 0)).sum() * H ** 3); removed = float(((dn > 0) & (d <= 0)).sum() * H ** 3); del d
    vv, ff, _, _ = marching_cubes(np.pad(dn, 1, constant_values=5.0), level=0.0, spacing=(H, H, H)); del dn
    mL = trimesh.Trimesh(vv + lo - 0.5 * H, ff, process=True)
    if mL.volume < 0: mL.invert()
    mR = mL.copy(); mR.vertices[:, 0] *= -1; mR.invert()                  # the right half: the mirror image
    # the splice region: a staircase of short boxes that follow the step line, each reaching just past where the fairing
    # ends (so the new surface there is the original one) and clear of the thin trailing lip; they all cut the same patch,
    # so where they meet the cuts match exactly
    BL = None; edges = np.r_[np.arange(-STEP_X[1] - 10.0, -1.0, SEG), 0.0]
    for xa, xb in zip(edges[:-1], edges[1:]):
        k = (P[:, 0] > xa - 6) & (P[:, 0] < xb + 6); q = P[k] if k.any() else P[np.argsort(np.abs(P[:, 0] - xa))[:3]]
        b0 = np.maximum([xa, q[:, 1].min() - 22.0, q[:, 2].min() - 22.0], lo + 1.0)
        b1 = np.minimum([xb, q[:, 1].max() + 16.0, q[:, 2].max() + 16.0], hi - 1.0)
        bx = mf.Manifold.cube(list(b1 - b0)).translate(list(b0)); BL = bx if BL is None else BL + bx
    BR = BL.mirror([1.0, 0, 0])
    pL, pR = tomf(mL) ^ BL, tomf(mR) ^ BR
    for pp, nm in ((pL, 'left'), (pR, 'right')):
        nsx = len(selfx(totm(pp))); assert nsx == 0, f'{nm} patch self-intersects ({nsx} faces)'
    log('patches')
    M = ((tomf(E) - BL) - BR) + pL + pR
    raw = totm(M)
    for tol in (0.0, 1e-6, 1e-5, 1e-4, 1e-3):                           # the smallest merge that gives one clean closed body
        try: E4 = keep_main(weld(raw, tol=tol) if tol else raw)
        except AssertionError: continue
        r, _ = report(E4, 'E4')
        if r['watertight'] and r['bodies'] == 1 and r['selfx_faces'] == 0: break
    rep = dict(step_line=dict(points=len(P), steepest_deg=[round(float(P[:, 3].min()), 1), round(float(P[:, 3].max()), 1)]),
               box=[lo.round(1).tolist(), hi.round(1).tolist()], added_mm3_per_side=round(added, 1), removed_mm3_per_side=round(removed, 1),
               E4={k: r[k] for k in ('faces', 'watertight', 'winding', 'volume_cm3', 'bodies', 'selfx_faces', 'zero_area')},
               E3_volume_cm3=round(float(E.volume) / 1000, 2))
    log(rep['E4'], 'E3 volume %.2f cm3' % rep['E3_volume_cm3'])
    if not (r['watertight'] and r['bodies'] == 1 and r['selfx_faces'] == 0): raw.export(f'{OUT}/_e4_raw.stl')
    assert r['watertight'] and r['bodies'] == 1 and r['selfx_faces'] == 0, 'E4 is not one clean closed body'
    E4.export(E_PATH); json.dump(rep, open(f'{OUT}/e4_report.json', 'w'), indent=1)
    log('wrote', E_PATH)

if __name__ == '__main__':
    main()
