"""v9 step 2: the joints. At each of the five seams:
  - the seam profile (the cored skin's cross-section) and its midline, with the skin thickness along it;
  - two dowel-pin holes (4.3 mm for 4 mm pins, 12 mm deep each side, 30-degree lead-in at the mouth, pointed end so it
    prints without a bridge), one at each end of the stretch where the skin is at least MIN_SKIN_PIN thick;
  - between them a TONGUE on the male face and a matching GROOVE in the female face, along the skin's midline, sides
    leaning CHAMFER_DEG (30 deg) off the joining direction and 30-degree tapered ends, so the pieces slide together and
    centre themselves;
  - the centre seam is groove-to-groove and takes a loose double-sided spline of the tongue's shape.
Writes the finished pieces (car coordinates) to v9/assembled/, the loose parts to v9/out/, and v9/out/joints.json.
Run from spoiler/:  python3 v9/src/p2_joints.py"""
import sys, os, json; sys.path.insert(0, 'v9/src'); sys.path.insert(0, 'v6/src')
import numpy as np, trimesh, manifold3d as mf
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
from shapely.geometry import Polygon
from matplotlib.path import Path as MPath
from bowtie import tomf, totm
from p1_core import weld
from layout import (OUT, ASM, PIECES, IDS, STEM, SEAMS, sides, seam_key, SPLINE_SEAM, CHAMFER_DEG, TONGUE_BASE, TONGUE_H,
                    CLEAR, GROOVE_EXTRA, MIN_SKIN_TONGUE, PIN_D, HOLE_D, HOLE_DEPTH, PIN_L, HOLE_CHAMFER, MIN_SKIN_PIN, PIN_GAP)
TAN = np.tan(np.radians(CHAMFER_DEG))

def seam_profile(m, c, side):
    """largest polygon of m's section just inside the face x = c (side = -1: piece left of the seam)"""
    s = m.section(plane_origin=[c + side * 0.05, 0, 0], plane_normal=[1, 0, 0])
    polys = sorted([Polygon(d[:, [2, 1]]).buffer(0) for d in s.discrete], key=lambda p: -p.area)
    return polys[0]

def midline(P, h=0.05):
    """the skin's midline as a (z, y) polyline from front to rear, the skin thickness along it, and arc length"""
    z0, y0, z1, y1 = P.bounds
    nz, ny = int((z1 - z0) / h) + 8, int((y1 - y0) / h) + 8
    zz, yy = np.meshgrid(z0 - 4 * h + np.arange(nz) * h, y0 - 4 * h + np.arange(ny) * h, indexing='ij')
    mask = MPath(np.asarray(P.exterior.coords)).contains_points(np.column_stack([zz.ravel(), yy.ravel()])).reshape(zz.shape)
    D = ndi.distance_transform_edt(mask) * h
    sk = skeletonize(mask)
    # one point per 0.5 mm of z: the topmost skeleton point (the seal-rim tab branches off below the main midline)
    iz, iy = np.nonzero(sk); zs = zz[iz, 0]; bins = np.floor((zs - z0) / 0.5).astype(int)
    pts, th = [], []
    for b in np.unique(bins):
        k = np.flatnonzero(bins == b); j = k[np.argmax(iy[k])]
        pts.append((zz[iz[j], 0], yy[0, iy[j]])); th.append(2 * D[iz[j], iy[j]])
    pts = np.array(pts); th = np.array(th)
    sm = np.column_stack([ndi.uniform_filter1d(pts[:, 0], 9, mode='nearest'), ndi.uniform_filter1d(pts[:, 1], 9, mode='nearest')])
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(sm, axis=0), axis=1))]
    return sm, ndi.minimum_filter1d(th, 5), s

def resample(pts, s, s0, s1, n):
    t = np.linspace(s0, s1, n)
    return np.column_stack([np.interp(t, s, pts[:, 0]), np.interp(t, s, pts[:, 1])])

def frames(q):
    """in-plane unit normals (z, y) along a polyline"""
    t = np.gradient(q, axis=0); t /= np.linalg.norm(t, axis=1, keepdims=True)
    return np.column_stack([-t[:, 1], t[:, 0]])

def prism(pts, s, levels, c, direction, n=160):
    """closed solid swept along the midline (z, y). levels: [(h, width, (s_start, s_end)), ...] from one face to the other;
    at x = c + direction*h the section is `width` wide and spans that arc-length range (so the ends taper too)"""
    rails = []
    for h, w, (sa, sb) in levels:
        q = resample(pts, s, sa, sb, n); nn = frames(q); x = np.full(n, c + direction * h)
        Lr = q + nn * (w / 2); Rr = q - nn * (w / 2)
        rails.append((np.column_stack([x, Lr[:, 1], Lr[:, 0]]), np.column_stack([x, Rr[:, 1], Rr[:, 0]])))
    ring = [r[0] for r in rails] + [r[1] for r in rails[::-1]]           # around the section: left side up, right side down
    K = len(ring); V = np.vstack(ring); F = []
    for i in range(n - 1):
        for k in range(K):
            k2 = (k + 1) % K; a0, a1, b0, b1 = k * n + i, k2 * n + i, k * n + i + 1, k2 * n + i + 1
            F += [[a0, b0, b1], [a0, b1, a1]]
    for i in (0, n - 1):                                                  # end caps: fan over the (convex) section
        for k in range(1, K - 1): F.append([i, k * n + i, (k + 1) * n + i] if i == 0 else [i, (k + 1) * n + i, k * n + i])
    m = trimesh.Trimesh(V, np.array(F), process=True)
    if m.volume < 0: m.invert()
    assert m.is_watertight and m.is_winding_consistent and m.is_volume, 'prism is not a closed solid'
    return m

def hole(c, zy):
    """pin hole through the seam (one revolved solid): 4.3 mm, 12 mm into each piece, pointed ends (90-degree cone, so
    it prints without a bridge) and a 30-degree lead-in at the face"""
    r = HOLE_D / 2; lead = HOLE_CHAMFER / TAN                            # lead-in: 30 degrees off the axis
    prof = np.array([[0, -HOLE_DEPTH - r], [r, -HOLE_DEPTH], [r, -lead], [r + HOLE_CHAMFER, 0], [r, lead], [r, HOLE_DEPTH],
                     [0, HOLE_DEPTH + r]], float)
    M = mf.Manifold.revolve(mf.CrossSection([prof], mf.FillRule.EvenOdd), 48)   # axis = local z
    T = np.array([[0, 0, 1.0, c], [0, 1.0, 0, zy[1]], [-1.0, 0, 0, zy[0]]])  # proper rotation: local z -> x, local y -> y
    return M.transform(T)

def pin_part():
    """4 mm dowel, PIN_L long, 0.4 mm x 45-degree chamfer at both ends (revolved), axis = z"""
    r = PIN_D / 2; ch = 0.4
    prof = np.array([[0, 0], [r - ch, 0], [r, ch], [r, PIN_L - ch], [r - ch, PIN_L], [0, PIN_L]], float)
    return totm(mf.Manifold.revolve(mf.CrossSection([prof], mf.FillRule.EvenOdd), 64))

if __name__ == '__main__':
    os.makedirs(ASM, exist_ok=True)
    cored = {pid: trimesh.load(f'{OUT}/cored_{pid}.stl') for pid in IDS}
    ops = {pid: {'add': [], 'cut': []} for pid in IDS}
    loose = {'pins': [], 'spline': None}; rep = {}
    for k, c in enumerate(SEAMS):
        L, R = IDS[k], IDS[k + 1]; sL, sR = sides(c)
        P = seam_profile(cored[L], c, -1)
        pts, th, s = midline(P)
        ok = th >= MIN_SKIN_PIN
        # longest run of the midline where the skin takes a pin
        runs = np.split(np.arange(len(ok)), np.flatnonzero(np.diff(ok.astype(int))) + 1)
        run = max([r_ for r_ in runs if ok[r_[0]]], key=lambda r_: s[r_[-1]] - s[r_[0]])
        sa, sb = s[run[0]], s[run[-1]]
        foot = HOLE_D / 2 + HOLE_CHAMFER + 1.0
        p1s, p2s = sa + foot + 2.0, sb - foot - 2.0                       # pins just inside both ends of that run
        pins = [resample(pts, s, v, v, 1)[0] for v in (p1s, p2s)]
        t0 = p1s + HOLE_D / 2 + HOLE_CHAMFER + PIN_GAP; t1 = p2s - HOLE_D / 2 - HOLE_CHAMFER - PIN_GAP
        tong = np.interp([t0, t1], s, th)
        assert th[(s >= t0) & (s <= t1)].min() >= MIN_SKIN_TONGUE, f'seam {c}: skin too thin under the tongue'
        dch = TONGUE_H * TAN; wt = TONGUE_BASE - 2 * TONGUE_H * TAN
        # tongue: from 0.5 mm inside the male piece (flanks carried on) to TONGUE_H out of the face
        def tongue(direction):
            return prism(pts, s, [(-0.5, TONGUE_BASE + 2 * 0.5 * TAN, (t0 - 0.5 * TAN, t1 + 0.5 * TAN)),
                                  (TONGUE_H, wt, (t0 + dch, t1 - dch))], c, direction)
        gd = TONGUE_H + GROOVE_EXTRA; gm = TONGUE_BASE + 2 * CLEAR
        def groove(direction):                                            # direction: into the female piece
            return prism(pts, s, [(-0.5, gm + 2 * 0.5 * TAN, (t0 - CLEAR - 0.5 * TAN, t1 + CLEAR + 0.5 * TAN)),
                                  (gd, gm - 2 * gd * TAN, (t0 - CLEAR + gd * TAN, t1 + CLEAR - gd * TAN))], c, direction)
        if sL == 'M': ops[L]['add'].append(tongue(+1.0)); ops[R]['cut'].append(groove(+1.0))
        elif sR == 'M': ops[R]['add'].append(tongue(-1.0)); ops[L]['cut'].append(groove(-1.0))
        else:                                                             # groove-to-groove: loose spline
            ops[L]['cut'].append(groove(-1.0)); ops[R]['cut'].append(groove(+1.0))
            loose['spline'] = prism(pts, s, [(-TONGUE_H, wt, (t0 + dch, t1 - dch)), (0.0, TONGUE_BASE, (t0, t1)),
                                             (TONGUE_H, wt, (t0 + dch, t1 - dch))], c, +1.0)
        for p in pins:
            H = hole(c, p)
            ops[L]['cut'].append(H); ops[R]['cut'].append(H)
            loose['pins'].append((c, p))
        rep[seam_key(c)] = dict(pieces=[L, R], faces=[sL, sR], pins_zy=[[round(float(v), 1) for v in p] for p in pins],
                                tongue_length=round(float(t1 - t0), 1), skin_under_tongue_min=round(float(th[(s >= t0) & (s <= t1)].min()), 2),
                                skin_at_pins=[round(float(np.interp(v, s, th)), 2) for v in (p1s, p2s)],
                                tongue_z=[round(float(np.interp(v, s, pts[:, 0])), 1) for v in (t0, t1)])
        print('seam %+7.1f %s|%s %s/%s: pins at z=%.0f, %.0f (skin %.2f, %.2f mm); tongue %.0f mm long, skin under it >= %.2f mm' % (
            c, L, R, sL, sR, pins[0][0], pins[1][0], *rep[seam_key(c)]['skin_at_pins'], t1 - t0, rep[seam_key(c)]['skin_under_tongue_min']))
    out = {}
    for pid in IDS:
        M = tomf(cored[pid])
        for a in ops[pid]['add']: M = M + tomf(a)
        for cu in ops[pid]['cut']: M = M - (cu if isinstance(cu, mf.Manifold) else tomf(cu))
        out[pid] = weld(totm(M.simplify(0.005)))                         # drop detail finer than 5 microns: ~8x smaller files
        out[pid].export(f'{ASM}/{STEM[pid]}.stl')
        print(pid, STEM[pid], 'watertight', out[pid].is_watertight, 'volume %.1f cm3' % (out[pid].volume / 1000), 'bodies', len(out[pid].split(only_watertight=False)))
    pin = pin_part(); pin.export(f'{OUT}/pin_local.stl')
    loose['spline'].export(f'{ASM}/v9_CENTRE_SPLINE.stl')
    for i, (c, p) in enumerate(loose['pins']):                            # pins in place (assembled view)
        q = pin.copy(); q.apply_transform(np.array([[0, 0, 1.0, c - PIN_L / 2], [0, 1.0, 0, p[1]], [-1.0, 0, 0, p[0]], [0, 0, 0, 1]]))
        q.export(f'{ASM}/v9_PIN_{i + 1:02d}.stl')
    json.dump(dict(seams=rep, n_pins=len(loose['pins']), spline_volume_cm3=round(loose['spline'].volume / 1000, 2)), open(f'{OUT}/joints.json', 'w'), indent=1)
    print('pins: %d, spline %.1f cm3' % (len(loose['pins']), loose['spline'].volume / 1000))
