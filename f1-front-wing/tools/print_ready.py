"""Turn the reassembled pieces into a print-ready set at one scale (default 52 %).

    python3 print_ready.py [--scale 0.52] [--bed 420 420 450] [--cut 182] [--out stl]

Run in the pipeline's working folder, after build_left_right.py (blades_posed.pkl) and
export_all.py (1_body_posed.pkl, 4a/4b_end_plate_*_posed.pkl). Needs wing_frame.pkl.

All joint features are made at PRINT scale, in the assembled position, so every pin, socket and
key lines up with its partner exactly:

* Body: placed with its underside on the wing's centre section, tip flush with the main plane's
  leading edge, then rebuilt as one seamless lofted shell (seamless_nose). The hollow inside the
  tip gets a 45-degree pointed roof, so nothing needs support when it prints tip up. It is cut
  in two (--cut mm above the rear face); two 5 mm pins in bosses inside the side walls join the
  halves.
* Wing: 8 separate blades (main plane, 2nd and 3rd element, top flap; left and right).
  - centre block (separate piece): its top is the exact shape of the body's underside, 2 pins
    hold the body; the inner ends of the six full-width blade halves slide into sockets in it;
  - end plates: the joint is one flat cut a few mm inboard of the original stubs; a straight key
    (tongue) on each stub slides into a slot inside the blade tip.
* Pins are 5 mm x 20 mm in 5.2 mm holes about 10 mm deep in each part. Sockets and keys have
  0.15 mm clearance.
* Print orientations: body halves tip up, blades standing on one end, centre block on a socket
  face, end plates on their rear edge (tilted a few degrees, gap under the edge filled).
* Checks: the assembled pieces must not overlap, every pin must clear all material and reach
  ~10 mm into both of its pieces; every file is re-loaded as a slicer would and must be
  watertight with no non-manifold edges and fit the build volume.
"""
import argparse, os, sys, pickle
import numpy as np, trimesh, manifold3d as mf
from shapely.geometry import Polygon, MultiPoint, Point
from shapely.geometry.polygon import orient
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from merge import to_manifold, from_manifold
from package_build_volume import manifold_to_stl

HOLE_R = 2.6          # 5.2 mm hole for a 5 mm pin
HOLE_DEPTH = 10.3     # per side; pin length 20 mm
PIN_D, PIN_L = 5.0, 20.0
BOSS_R = 5.0          # wall around the hole = 2.4 mm
SEG = 48              # facets on round features


def load(path):
    return pickle.load(open(path, 'rb')).copy()


def M(m):
    return to_manifold(m) if isinstance(m, trimesh.Trimesh) else m


def hull_pts(P):
    return mf.Manifold.hull_points(np.asarray(P, np.float64))


def cyl(p0, p1, r, seg=SEG):
    """Cylinder from point p0 to p1."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0; L = np.linalg.norm(d); z = d / L
    x = np.cross(z, [1, 0, 0] if abs(z[0]) < 0.9 else [0, 1, 0]); x /= np.linalg.norm(x); y = np.cross(z, x)
    T = np.eye(4)[:3]; T[:, 0], T[:, 1], T[:, 2], T[:, 3] = x, y, z, p0
    return mf.Manifold.cylinder(L, r, r, seg).transform(T)


# ----------------------------------------------------------------------------- nose
def mirror_plane(mesh, n0, d0, iters=12, n_pts=60000):
    """Refine a mirror-symmetry plane (n, d) of a mesh: reflect surface samples, pair each with the
    closest surface point, and take the perpendicular bisector of the pairs."""
    pts, _ = trimesh.sample.sample_surface(mesh, n_pts, seed=7)
    pq = trimesh.proximity.ProximityQuery(mesh)
    n, d = n0 / np.linalg.norm(n0), float(d0)
    for _ in range(iters):
        refl = pts - 2 * ((pts @ n) - d)[:, None] * n
        q, dist, _ = pq.on_surface(refl)
        ok = dist < np.percentile(dist, 80)
        p, qq = pts[ok], q[ok]                            # qq ~ mirror partner of p
        v = p - qq; v[(v @ n) < 0] *= -1
        n = v.sum(0); n /= np.linalg.norm(n)
        d = float(np.mean(((p + qq) / 2) @ n))
    return n, d, float(np.median(dist))


def nose_frame(body, s):
    """Axes of the nose: ex along the underside centre line towards the tip, ez up, ey left
    (normal of the nose's mirror plane)."""
    V = body.vertices; cb = V.mean(0)
    _, E = np.linalg.eigh(np.cov((V - cb).T))
    ax, lat, ver = E[:, 2], E[:, 1], E[:, 0]
    lat, d, err = mirror_plane(body, lat, lat @ cb)
    cb = cb - ((cb @ lat) - d) * lat                      # centroid onto the mirror plane
    ax = ax - (ax @ lat) * lat; ax /= np.linalg.norm(ax)
    ver = np.cross(lat, ax)
    print(f'nose mirror plane: median mismatch {err:.3f} mm')
    pts, _ = trimesh.sample.sample_surface(body, 600000, seed=2)
    t = (pts - cb) @ ax
    if np.ptp(((pts - cb) @ lat)[t > t.max() - 30 * s]) > np.ptp(((pts - cb) @ lat)[t < t.min() + 30 * s]):
        ax = -ax; t = -t; ver = -ver                      # +ax points to the (narrow) tip
    la = (pts - cb) @ lat; h = (pts - cb) @ ver
    Ln = np.ptp(t); st = np.linspace(t.max() - 0.82 * Ln, t.max() - 0.05 * Ln, 40)
    lo, hi = [], []
    for t0 in st:
        sel = (np.abs(t - t0) < 1.5 * s) & (np.abs(la) < 12 * s)
        lo.append(h[sel].min()); hi.append(h[sel].max())
    def fit(y):
        A = np.c_[st, np.ones_like(st)]; c, *_ = np.linalg.lstsq(A, y, rcond=None)
        return c, np.sqrt(np.mean((A @ c - y) ** 2))
    (blo, rlo), (bhi, rhi) = fit(np.array(lo)), fit(np.array(hi))
    if rhi < rlo:                                         # the straight side is the underside
        ver = -ver; b = -bhi[0]
    else:
        b = blo[0]
    ex = ax + b * ver; ex /= np.linalg.norm(ex)           # stays in the mirror plane
    ez = ver - np.dot(ver, ex) * ex; ez /= np.linalg.norm(ez)
    ey = np.cross(ez, ex)
    return cb, ex, ey, ez, min(rlo, rhi)


def place_nose(body, wing, x_tip, s):
    """Rigid transform putting the nose's flat underside on the wing centre section."""
    cb, ex, ey, ez, rms = nose_frame(body, s)
    R = np.stack([ex, ey, ez])
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = -R @ cb
    nose = body.copy(); nose.apply_transform(T)
    T2 = np.eye(4); T2[0, 3] = x_tip - nose.vertices[:, 0].max(); T2[2, 3] = 200 - nose.vertices[:, 2].min()
    nose.apply_transform(T2); T = T2 @ T
    # lower it onto the wing: shortest upward ray from the wing's upper surfaces to the nose
    pts, fi = trimesh.sample.sample_surface(wing, 1500000, seed=4)
    nb = nose.bounds
    keep = (wing.face_normals[fi][:, 2] > 0.2) & (pts[:, 0] > nb[0, 0]) & (np.abs(pts[:, 1]) < nb[1, 1])
    o = pts[keep] + [0, 0, 1e-3]
    loc, ri, _ = nose.ray.intersects_location(o, np.tile([0, 0, 1.0], (len(o), 1)), multiple_hits=False)
    gap = (loc[:, 2] - o[ri, 2]).min()
    T3 = np.eye(4); T3[2, 3] = -gap
    nose.apply_transform(T3)
    print(f'nose: underside straightness rms {rms:.2f} mm; placed tip at x={x_tip:.1f}, '
          f'underside z={nose.vertices[:, 2].min():.2f} (resting on the wing)')
    return nose, T3 @ T


def _section_rings(mesh, x, close=0.06):
    """Outer contour and largest cavity contour (as (n,2) arrays in (y, z)) of the section x = const,
    with hairline gaps closed (morphological closing)."""
    sec = mesh.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
    if sec is None:
        return None, None
    res = Polygon()
    polys = [Polygon(np.asarray(e)[:, [1, 2]]).buffer(0) for e in sec.discrete if len(e) >= 3]
    for q in sorted(polys, key=lambda q: -q.area):           # even-odd: cavity inside the outline
        res = res.symmetric_difference(q)
    res = res.buffer(close).buffer(-close)
    if res.is_empty:
        return None, None
    big = max(getattr(res, 'geoms', [res]), key=lambda g: g.area)
    outer = np.asarray(big.exterior.coords)[:-1]
    holes = sorted(big.interiors, key=lambda r: -Polygon(r).area)
    inner = np.asarray(holes[0].coords)[:-1] if holes and Polygon(holes[0]).area > 4.0 else None
    return outer, inner


def _polar(ring, c, ang):
    """Distance from centre c to the (star-shaped) closed ring along each direction in ang."""
    P = ring - c; Q = np.roll(P, -1, axis=0); E = Q - P
    d = np.c_[np.cos(ang), np.sin(ang)]
    # solve t*d = P + u*E for every (ray, edge)
    den = d[:, None, 0] * E[None, :, 1] - d[:, None, 1] * E[None, :, 0]
    with np.errstate(divide='ignore', invalid='ignore'):
        t = (P[None, :, 0] * E[None, :, 1] - P[None, :, 1] * E[None, :, 0]) / den
        u = (P[None, :, 0] * d[:, None, 1] - P[None, :, 1] * d[:, None, 0]) / den
    ok = (np.abs(den) > 1e-12) & (u >= -1e-9) & (u <= 1 + 1e-9) & (t > 0)
    return np.where(ok, t, -np.inf).max(1)


def _loft_solid(xs, cs, rs, ang, front=None, back_cap=True):
    """Closed mesh through rings at stations xs (centres cs (k,2), radii rs (k,n)); the last ring
    is closed by a fan to `front` (3-vector) or by a flat cap; the first ring by a flat cap."""
    k, n = rs.shape
    ring = np.stack([np.c_[np.full(n, xs[i]), cs[i, 0] + rs[i] * np.cos(ang), cs[i, 1] + rs[i] * np.sin(ang)] for i in range(k)])
    V = list(ring.reshape(-1, 3)); F = []
    idx = lambda i, j: i * n + (j % n)
    for i in range(k - 1):
        for j in range(n):
            a, b, c, d = idx(i, j), idx(i, j + 1), idx(i + 1, j + 1), idx(i + 1, j)
            F += [(a, b, c), (a, c, d)]
    rear = len(V); V.append([xs[0], cs[0, 0], cs[0, 1]])
    F += [(rear, idx(0, j + 1), idx(0, j)) for j in range(n)]
    tip = len(V); V.append(front if front is not None else [xs[-1], cs[-1, 0], cs[-1, 1]])
    F += [(tip, idx(k - 1, j), idx(k - 1, j + 1)) for j in range(n)]
    tm = trimesh.Trimesh(np.array(V), np.array(F), process=False)
    if tm.volume < 0:
        tm.invert()
    return tm


def rot_a_to_b(a, b):
    """3x3 rotation taking unit vector a onto unit vector b."""
    a = np.asarray(a, float) / np.linalg.norm(a); b = np.asarray(b, float) / np.linalg.norm(b)
    v = np.cross(a, b); c = np.dot(a, b)
    if np.linalg.norm(v) < 1e-12:
        return np.eye(3) if c > 0 else -np.eye(3)
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + K + K @ K * (1 - c) / np.dot(v, v)


def seamless_nose(nose, trim, n_ang=256, step=1.0, fine=0.25, fine_len=14.0, smooth=0.0):
    """Rebuild the nose as ONE continuous shell: its outer skin and its cavity are lofted through
    cross-sections taken every `step` mm (`fine` mm near the tip), square to the rear rim, so none
    of the original parts' joint faces, tabs or hairline gaps survive. The uneven rear rim ends up
    `trim` mm shorter and flat. Returns (manifold, print 'up' direction, info)."""
    V = nose.vertices
    rim = V[V[:, 0] < V[:, 0].min() + 8]
    _, _, vt = np.linalg.svd(rim - rim.mean(0)); pn = vt[2] if vt[2][0] > 0 else -vt[2]
    R = rot_a_to_b(pn, [1.0, 0, 0])                          # local frame: rim normal along +x
    loc = trimesh.Trimesh(V @ R.T, nose.faces, process=False)
    L = loc.vertices
    x0, x1 = L[:, 0].min(), L[:, 0].max()
    apex = L[np.argmax(L[:, 0])]
    xs = np.r_[np.arange(x0 + trim, x1 - fine_len, step), np.arange(x1 - fine_len, x1 - 0.1, fine)]
    ang = np.linspace(0, 2 * np.pi, n_ang, endpoint=False) + np.pi / 2
    outs, ins = [], []
    for x in xs:
        o, i = _section_rings(loc, x)
        outs.append(o); ins.append(i)
    first = next(j for j, i in enumerate(ins) if i is not None)       # first complete ring at the rear
    keep = [j for j in range(first, len(xs)) if outs[j] is not None and len(outs[j]) >= 8]
    xs = xs[keep]; outs = [outs[j] for j in keep]; ins = [ins[j] for j in keep]
    co = np.array([Polygon(o).centroid.coords[0] for o in outs])
    kc = 0
    while kc < len(ins) and ins[kc] is not None:
        kc += 1
    ci = np.array([Polygon(i).centroid.coords[0] for i in ins[:kc]])
    def sm(x, a):
        """Gaussian smoothing along the nose in millimetres (sigma `smooth`), fading out over the
        last 3 mm before the tip so the tip keeps its shape; same weights at every station, so
        the change of section spacing leaves no line."""
        if not smooth:
            return a
        sig = smooth * np.clip((x1 - x) / 10.0, 0.02, 1.0)
        dx = np.gradient(x)                                  # weight by spacing: uneven spacing adds no bias
        W = np.exp(-0.5 * ((x[:, None] - x[None, :]) / sig[:, None]) ** 2) * dx[None, :]
        W /= W.sum(1, keepdims=True)
        return W @ a
    co = sm(xs, co); ci = sm(xs[:kc], ci)
    ro = sm(xs, np.array([_polar(o, c, ang) for o, c in zip(outs, co)]))
    ri = sm(xs[:kc], np.array([_polar(i, c, ang) for i, c in zip(ins[:kc], ci)]))
    if xs[0] > x0 + trim + 0.01:                            # rim was ragged here: carry the first full
        xs = np.r_[x0 + trim, xs]                            # ring back to the trim plane
        co = np.r_[co[:1], co]; ro = np.r_[ro[:1], ro]; ci = np.r_[ci[:1], ci]; ri = np.r_[ri[:1], ri]; kc += 1
    outer = _loft_solid(xs, co, ro, ang, front=apex)
    xi = np.r_[xs[0] - 2.0, xs[:kc]]; ci = np.r_[ci[:1], ci]; ri = np.r_[ri[:1], ri]   # open the rear
    cavity = M(_loft_solid(xi, ci, ri, ang))
    # 45-degree pointed roof on the cavity inside the tip: the nose prints tip up, so a flat roof
    # there would need a support column from the bed all the way up through the nose
    Hc = 2.0 * (x1 - x0) + 50.0                                 # tall enough to cover the whole nose
    cone = mf.Manifold.cylinder(Hc, Hc, 0.0, 96)               # apex up (+z)
    Tc = np.eye(4)[:3]; Tc[:, 0] = [0, 1, 0]; Tc[:, 1] = [0, 0, 1]; Tc[:, 2] = [1, 0, 0]
    Tc[:, 3] = [xs[kc - 1] - Hc, ci[-1, 0], ci[-1, 1]]
    cavity = cavity ^ cone.transform(Tc)
    shell = M(outer) - cavity
    shell = sorted(shell.decompose(), key=lambda q: -q.volume())[0]
    nfull = shell.num_tri()
    shell = shell.simplify(0.005)                            # merge triangles where the surface is flat
    T = np.eye(4)[:3]; T[:, :3] = R.T                       # back to the wing frame
    shell = shell.transform(T)
    return shell, pn, dict(stations=len(xs), cavity_stations=kc, length=float(x1 - xs[0]),
                           triangles=f'{nfull} -> {shell.num_tri()}')


# ----------------------------------------------------------------------------- centre block
def crossings(mesh, x, y, z0=-1e3):
    """Sorted z of every surface crossing of the vertical lines through (x, y)."""
    m = trimesh.Trimesh(mesh.vertices, mesh.faces, process=False)
    o = np.c_[x, y, np.full(len(x), z0)]
    loc, ri, _ = m.ray.intersects_location(o, np.tile([0, 0, 1.0], (len(o), 1)), multiple_hits=True)
    loc = np.asarray(loc).reshape(-1, 3)
    out = [[] for _ in range(len(x))]
    for i, z in zip(ri, loc[:, 2]):
        out[i].append(z)
    return [np.unique(np.round(np.sort(v), 5)) for v in out]


def column(mesh, x, y):
    """(bottom, top) z of the first solid run through (x, y)."""
    c = crossings(mesh, np.array([x]), np.array([y]))[0]
    return (c[0], c[1]) if len(c) >= 2 else (np.nan, np.nan)


def _sections_xz(mesh, y):
    sec = mesh.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
    if sec is None:
        return []
    return [Polygon(np.asarray(d)[:, [0, 2]]).buffer(0) for d in sec.discrete if len(d) > 3]


def _extrude_y(poly, y0, y1):
    """Prism of a shapely polygon (in x, z) between y0 and y1."""
    out = []
    for g in getattr(poly, 'geoms', [poly]):
        if g.is_empty or g.area < 1e-3:
            continue
        g = orient(g, 1.0)
        cs = mf.CrossSection([np.array(g.exterior.coords)[:-1]] + [np.array(r.coords)[:-1] for r in g.interiors])
        e = mf.Manifold.extrude(cs, y1 - y0)                     # along +z in (x, z') -> map to (x, y, z)
        T = np.zeros((3, 4)); T[0, 0] = 1; T[2, 1] = 1; T[1, 2] = 1; T[1, 3] = y0
        out.append(e.transform(T))
    return mf.Manifold.batch_boolean(out, mf.OpType.Add) if out else mf.Manifold()


def build_center_block(roots, nose, W, D, wall=1.4, clr=0.15, dy=0.5):
    """Separate centre block under the nose, |y| <= W. It holds the inner ends of the six full-width
    blade halves in sockets D mm deep (blade outline + clr), its top is the exact shape of the nose
    underside, and it has >= `wall` mm of material around every socket.
    roots: {name: (manifold blade half, side)} with the blades still reaching y = 0."""
    allb = trimesh.util.concatenate([from_manifold(m) for m, _ in roots.values()])
    xlo, xhi = allb.bounds[0, 0] - 5, allb.bounds[1, 0] + 5
    gx, gy = np.meshgrid(np.arange(xlo, xhi, 1.0), np.arange(-W, W + 1e-9, 1.0))
    cr = crossings(nose, gx.ravel(), gy.ravel())
    inner = np.array([c[1] for c in cr if len(c) >= 3])
    zcap = inner.min() - 0.3                          # stays below the inside of the nose wall
    parts, prev = [], None
    for y in np.arange(-W, W + 1e-9, dy):
        polys = [q.buffer(wall) for q in _sections_xz(allb, y) if q.area > 0.5]
        if not polys:
            prev = None; continue
        P = np.vstack([np.asarray(q.exterior.coords) for q in polys])
        P = np.vstack([P, [[P[:, 0].min(), zcap], [P[:, 0].max(), zcap]]])
        ring = np.array(MultiPoint([tuple(p) for p in P]).convex_hull.exterior.coords)[:-1]
        cur = np.c_[ring[:, 0], np.full(len(ring), y), ring[:, 1]]
        if prev is not None:
            parts.append(hull_pts(np.vstack([prev, cur])))
        prev = cur
    blk = mf.Manifold.batch_boolean(parts, mf.OpType.Add)
    q = nose.vertices[nose.vertices[:, 0] > xlo - 30]
    out = orient(MultiPoint([tuple(p) for p in q[:, :2]]).convex_hull.buffer(1.5), 1.0)
    prism = mf.Manifold.extrude(mf.CrossSection([np.array(out.exterior.coords)[:-1]]), 400).translate((0, 0, -200))
    blk = (blk ^ prism) - M(nose)
    blk = sorted(blk.decompose(), key=lambda p: -p.volume())[0]
    sockets = []
    for name, (bm, side) in roots.items():
        tb = from_manifold(bm)
        prof = unary_union_safe([g for yy in np.linspace(W - D, W + 2.0, 7) for g in _sections_xz(tb, side * yy) if g.area > 0.5])
        y0, y1 = (W - D - 0.3, W + 1.0)
        sockets.append(_extrude_y(prof.buffer(clr), *(sorted([side * y0, side * y1]))))
    blk = blk - mf.Manifold.batch_boolean(sockets, mf.OpType.Add)
    return blk, zcap


def unary_union_safe(geoms):
    from shapely.ops import unary_union
    return unary_union([g for g in geoms if not g.is_empty]).buffer(0)


# ----------------------------------------------------------------------------- pins
def nose_pins(blk, nose, x_range, min_gap=45.0):
    """Two pins on the centre line, nose <-> centre block, as far apart as the block allows."""
    bm = from_manifold(blk)
    xs = np.arange(x_range[0] + 8, x_range[1] - 8, 1.0)
    th = []
    for x in xs:
        zb, zt = column(bm, x, 0.0)
        th.append(zt - zb if np.isfinite(zb) else 0)
    th = np.array(th)
    ok = th >= HOLE_DEPTH + 1.0
    cand = xs[ok] if ok.sum() >= 2 else xs[np.argsort(-th)[:20]]
    a, b = cand.min(), cand.max()
    if b - a < min_gap:
        print(f'   note: nose pins only {b - a:.0f} mm apart')
    out = []
    for x in (a, b):
        zb, zt = column(bm, x, 0.0)
        ds = min(HOLE_DEPTH, (zt - zb) - 1.0)
        dn = PIN_L + 0.5 - ds
        cz = crossings(nose, np.array([x]), np.array([0.0]))[0]
        out.append(dict(x=x, y=0.0, z=zt, ds=ds, dn=dn, z_in=cz[1], floor=(zt - zb) - ds))
    return out


def nose_boss(p, up):
    """Boss inside the nose for a vertical pin, with a 45-degree underside towards -up
    (the nose prints standing on its rear opening, tip up)."""
    top = p['z'] + p['dn'] + 1.2
    a = np.linspace(0, 2 * np.pi, SEG, endpoint=False)
    ring = np.c_[p['x'] + BOSS_R * np.cos(a), p['y'] + BOSS_R * np.sin(a), np.zeros(SEG)]
    h = top - p['z_in']
    dn_xy = -np.array([up[0], up[1], 0.0]); dn_xy /= np.linalg.norm(dn_xy)
    pts = np.vstack([ring + [0, 0, p['z_in'] - 0.6], ring + [0, 0, top], ring + [0, 0, p['z_in'] - 0.6] + dn_xy * 1.5 * h])
    return hull_pts(pts)


def resplit_tip(blades_side, ep, side, inset=4.5):
    """Move the blade / end plate joint to ONE flat cut, `inset` mm inboard of where the end plate's
    element stubs used to start. The old joint (now inside the end plate) is fused.
    Returns (end plate manifold, |y| of the joint plane)."""
    from merge import merge_fused, fuse_microgaps
    y_s = float((ep.vertices[:, 1] * side).min()) - inset
    wing_half = trimesh.util.concatenate([from_manifold(b) for b in blades_side])
    U = M(fuse_microgaps(merge_fused({'w': wing_half, 'e': ep}, [('w', 'e')]), verbose=False))
    return U.trim_by_plane((0, float(side), 0), y_s), y_s


def end_plate_keys(blades_side, side, y_s, Lg=5.0, wall=0.9, clr=0.15):
    """Keys joining the blade tips to an end plate: a thin tongue on each end plate stub slides into
    a matching slot inside the blade tip. All four keys of one end plate run in ONE direction, the
    blades' average sweep at the tip (back and slightly down), so the end plate slides on in one
    straight move. Each tongue is the part of its blade that stays inside the blade over the key
    length along that direction, shrunk by `wall` + `clr`. The tongue's lowest edge is cut back at
    45 degrees: the end plate prints standing on its rear edge (+x up).
    Returns (tongues, slots, (dx, dz)) - manifolds per blade, and the slide direction per mm."""
    from shapely import affinity
    secs, drift = [], []
    ts = np.linspace(0.2, Lg + 0.5, 9)
    for b in blades_side:
        tb = from_manifold(b)
        S_ = [unary_union_safe([q for q in _sections_xz(tb, side * (y_s - t)) if q.area > 0.5]) for t in ts]
        secs.append(S_)
        c0, c1 = np.array(S_[-1].centroid.coords[0]), np.array(S_[0].centroid.coords[0])
        drift.append((c1 - c0) / (ts[-1] - ts[0]))                 # per mm towards the tip
    D_ = np.array(drift)
    dx, dz = D_[:, 0].mean(), (D_[:, 1].max() + D_[:, 1].min()) / 2
    def skew(poly, e0, e1):
        """Prism of poly (x, z at eta = y_s) running from eta = e0 to e1 along (dx, side, dz)."""
        out = []
        for g in getattr(poly, 'geoms', [poly]):
            g = orient(g, 1.0)
            e = mf.Manifold.extrude(mf.CrossSection([np.array(g.exterior.coords)[:-1]]), e1 - e0)
            T = np.array([[1, 0, dx, (e0 - y_s) * dx], [0, 0, side, side * e0], [0, 1, dz, (e0 - y_s) * dz]], float)
            out.append(e.transform(T))
        return mf.Manifold.batch_boolean(out, mf.OpType.Add)
    tongues, slots = [], []
    for S_ in secs:
        core = None
        for t, g in zip(ts, S_):
            g = affinity.translate(g, xoff=t * dx, yoff=t * dz)    # undo the slide offset at that depth
            core = g if core is None else core.intersection(g)
        t2 = core.buffer(-(wall + clr)).buffer(-0.4).buffer(0.4)    # drop parts thinner than 0.8 mm
        t2 = max(getattr(t2, 'geoms', [t2]), key=lambda g: g.area)
        t = skew(t2, y_s - Lg, y_s + 0.4)                            # 0.4 mm into the stub
        nrm = np.array([1.0, side, 0.0]) / np.sqrt(2)                # x + side*y >= xmin + y_s
        tongues.append(t.trim_by_plane(tuple(nrm), float((t2.bounds[0] + y_s) / np.sqrt(2))))
        slots.append(skew(t2.buffer(clr), y_s - Lg - 0.4, y_s + 0.01))
    return tongues, slots, (dx, dz)


def split_nose(NOSE, up, h_cut):
    """Cut the nose square to its print axis, h_cut mm above its rear face, joined by two 5 mm pins
    in bosses on the inside of the side walls. Returns (rear, front, pins)."""
    V = from_manifold(NOSE).vertices
    u0 = (V @ up).min(); u_cut = u0 + h_cut
    lat = np.array([0, 1.0, 0]); lat = lat - (lat @ up) * up; lat /= np.linalg.norm(lat)
    ev = np.cross(up, lat)
    sec = from_manifold(NOSE).section(plane_origin=up * u_cut, plane_normal=up)
    loops = [np.asarray(d) for d in sec.discrete]
    to2 = lambda P: np.c_[P @ lat, P @ ev]
    polys = sorted([Polygon(to2(P)).buffer(0) for P in loops], key=lambda q: -q.area)
    cav = polys[1]                                          # inside of the wall
    c0 = np.array(cav.centroid.coords[0])
    ext = lambda pt: np.array(pt) if not hasattr(pt, 'geoms') else np.array(max(pt.geoms, key=lambda g: abs(g.x - c0[0])).coords[0])
    from shapely.geometry import LineString
    pins, bosses = [], []
    for sgn in (-1, 1):
        hit = LineString([tuple(c0), tuple(c0 + np.array([sgn * 400, 0]))]).intersection(cav.exterior)
        q = np.array(hit.coords[0]) if hit.geom_type == 'Point' else np.array(sorted([g.coords[0] for g in hit.geoms], key=lambda t: abs(t[0] - c0[0]))[0])
        c2 = q - np.array([sgn * (BOSS_R + 0.4), 0])
        to3 = lambda a, b, uu: a * lat + b * ev + uu * up
        a = np.linspace(0, 2 * np.pi, SEG, endpoint=False)
        circ = [(c2[0] + BOSS_R * np.cos(t), c2[1] + BOSS_R * np.sin(t)) for t in a]
        wallpts = [(q[0] + sgn * 0.9, q[1] + BOSS_R), (q[0] + sgn * 0.9, q[1] - BOSS_R)]
        prof = circ + wallpts
        top, bot = u_cut + HOLE_DEPTH + 1.2, u_cut - HOLE_DEPTH - 1.2
        P3 = [to3(x, y, uu) for (x, y) in prof for uu in (bot, top)]
        # 45-degree lead-in under the rear half's boss (that half prints rear down, cut at the top)
        w = 1.5 * (2 * BOSS_R + 0.4)                     # steeper than 45 degrees everywhere on the boss
        P3 += [to3(q[0] + sgn * 0.9, q[1] + BOSS_R, bot - w), to3(q[0] + sgn * 0.9, q[1] - BOSS_R, bot - w)]
        bosses.append(hull_pts(np.array(P3)))
        pc = to3(c2[0], c2[1], 0)
        pins.append(('body rear <-> body front', pc + up * (u_cut - PIN_L / 2), pc + up * (u_cut + PIN_L / 2)))
    N2 = NOSE + mf.Manifold.batch_boolean(bosses, mf.OpType.Add)
    rear = N2.trim_by_plane(tuple(-up), float(-u_cut))
    front = N2.trim_by_plane(tuple(up), float(u_cut))
    for _, p0, p1 in pins:
        mid = (np.asarray(p0) + np.asarray(p1)) / 2
        h = cyl(mid - up * HOLE_DEPTH, mid + up * HOLE_DEPTH, HOLE_R)
        rear, front = rear - h, front - h
    return rear, front, pins, u_cut


# ----------------------------------------------------------------------------- break-away supports
def _section_poly(tm, axis, h):
    """Filled cross-section of mesh tm by the plane coordinate[axis] = h, as a shapely geometry
    in the two other coordinates."""
    other = [i for i in range(3) if i != axis]
    o = np.zeros(3); o[axis] = h; nrm = np.zeros(3); nrm[axis] = 1
    sc = tm.section(plane_origin=o, plane_normal=nrm)
    if sc is None:
        return Polygon()
    res = Polygon()
    polys = [Polygon(np.asarray(e)[:, other]).buffer(0) for e in sc.discrete if len(e) >= 3]
    for q in sorted(polys, key=lambda q: -q.area):        # even-odd: holes inside outlines
        res = res.symmetric_difference(q)
    return res.buffer(0)


def support_towers(part, up_axis=2, gap=0.3, step=0.25, min_area=6.0, max_span=3.0):
    """Break-away towers from the bed under every spot that starts in mid-air when `part` is printed
    with +axis `up_axis` up and its lowest point on the bed. Areas held on two sides (bridges, the
    roofs of holes) or reaching less than `max_span` mm from printed material are left alone."""
    from shapely.ops import unary_union
    tm = from_manifold(part) if not isinstance(part, trimesh.Trimesh) else part
    other = [i for i in range(3) if i != up_axis]
    lo, hi = tm.bounds[0, up_axis], tm.bounds[1, up_axis]
    towers = []
    prev = _section_poly(tm, up_axis, lo + 0.05)
    h = lo + 0.05 + step
    while h < hi:
        cur = _section_poly(tm, up_axis, h)
        new = cur.difference(prev.buffer(0.45 + step))
        for g in getattr(new, 'geoms', [new]):
            if g.is_empty or g.area < min_area:
                continue
            near = prev.buffer(0.6 + step)
            touching = [q for q in getattr(near, 'geoms', [near]) if q.intersects(g.buffer(0.3))]
            if len(touching) >= 2:
                continue                                   # bridge between two printed areas
            if not prev.is_empty:
                x0, y0, x1, y1 = g.bounds
                gx, gy = np.meshgrid(np.arange(x0, x1, 0.5), np.arange(y0, y1, 0.5))
                pts = [Point(c) for c in zip(gx.ravel(), gy.ravel()) if g.contains(Point(c))]
                if not pts or max(prev.distance(pt) for pt in pts) <= max_span:
                    continue                               # short reach: prints as a small overhang
            towers.append((h - step, g))
        prev = cur
        h += step
    out = []
    for h_top, g in towers:
        below = unary_union([_section_poly(tm, up_axis, z) for z in np.arange(lo + 0.1, h_top - gap, 1.0)]).buffer(0.6)
        foot = g.buffer(-0.2).difference(below).buffer(-0.1)
        for f in getattr(foot, 'geoms', [foot]):
            if f.is_empty or f.area < min_area:
                continue
            f = orient(f, 1.0)
            t = mf.Manifold.extrude(mf.CrossSection([np.array(f.exterior.coords)[:-1]]), h_top - gap - lo)
            T = np.zeros((3, 4)); T[other[0], 0] = 1; T[other[1], 1] = 1; T[up_axis, 2] = 1; T[up_axis, 3] = lo
            out.append((h_top, t.transform(T)))                # manifold fixes the winding if mirrored
    return out


def flat_base(Mo, depth=8.0):
    """Give a part that stands on an uneven edge (already oriented, +z up) a flat foot without
    cutting anything off: tilt it so the edge rests on its two outermost low points, then fill the
    gap under the edge between them with a strip. Returns (manifold, tilt in degrees, largest fill)."""
    tm = from_manifold(Mo)
    b = tm.bounds
    gx, gy = np.meshgrid(np.arange(b[0, 0], b[1, 0], 0.5), np.arange(b[0, 1], b[1, 1], 0.5))
    def lowest(tm):
        cr = crossings(tm, gx.ravel(), gy.ravel())
        return np.array([c[0] if len(c) else np.nan for c in cr]).reshape(gx.shape)
    zf = lowest(tm)
    ok = zf < np.nanmin(zf) + depth
    P = np.c_[gx[ok], gy[ok], zf[ok]]
    c = P[:, :2].mean(0); _, _, vt = np.linalg.svd(P[:, :2] - c); d = vt[0]
    t = (P[:, :2] - c) @ d
    # lower convex hull of the edge profile (t, z): its longest segment is the line it can rest on
    tb = np.round(t / 0.5) * 0.5                            # lowest point per 0.5 mm along the edge
    pts = np.array([[u, P[tb == u, 2].min()] for u in np.unique(tb)])
    cross2 = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    hull = []
    for q in pts:
        while len(hull) >= 2 and cross2(hull[-2], hull[-1], q) <= 0:
            hull.pop()
        hull.append(q)
    hull = np.array(hull)
    k = np.argmax(np.diff(hull[:, 0])); (t0, z0), (t1, z1) = hull[k], hull[k + 1]
    slope = (z1 - z0) / (t1 - t0)
    ang = np.arctan(slope)
    axis = np.array([-d[1], d[0], 0.0])                     # horizontal, normal to the edge direction
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    R = np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * K @ K
    p0 = np.array([c[0] + d[0] * t0, c[1] + d[1] * t0, z0])
    T = np.eye(4)[:3]; T[:, :3] = R; T[:, 3] = p0 - R @ p0
    Mo = Mo.transform(T)
    zmin = Mo.bounding_box()[2]
    Mo = Mo.translate((0, 0, -zmin))
    tm = from_manifold(Mo)
    b = tm.bounds
    gx, gy = np.meshgrid(np.arange(b[0, 0], b[1, 0], 0.5), np.arange(b[0, 1], b[1, 1], 0.5))
    zf = lowest(tm).ravel()
    t2 = (np.c_[gx.ravel(), gy.ravel()] - c) @ d
    span = (t2 > min(t0, t1) + 1) & (t2 < max(t0, t1) - 1) & np.isfinite(zf)
    tb = np.round(t2[span] / 0.5) * 0.5
    prof = np.array([zf[span][tb == u].min() for u in np.unique(tb)])
    gap = float(prof.max())                                  # highest point of the edge between the contacts
    top = _section_poly(tm, 2, gap + 0.3)
    strip = [mf.Manifold.extrude(mf.CrossSection([np.array(orient(g, 1.0).exterior.coords)[:-1]]), gap + 0.3)
             for g in getattr(top, 'geoms', [top]) if g.area > 1.0]
    Mo = mf.Manifold.batch_boolean([Mo] + strip, mf.OpType.Add)
    return Mo, float(np.degrees(ang)), gap


# ----------------------------------------------------------------------------- orientation
def rot_to_z(v):
    """Rotation (4x4) taking unit vector v to +z."""
    v = np.asarray(v, float) / np.linalg.norm(v); z = np.array([0, 0, 1.0])
    c = np.dot(v, z)
    if c > 1 - 1e-12:
        return np.eye(4)
    if c < -1 + 1e-12:
        R = np.diag([1, -1, -1.0])
    else:
        k = np.cross(v, z); sn = np.linalg.norm(k); k /= sn
        K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
        R = np.eye(3) + sn * K + (1 - c) * K @ K
    T = np.eye(4); T[:3, :3] = R
    return T


def overhang_area(m, up=(0, 0, 1.0), deg=45.0, skip_bed=0.3):
    tm = from_manifold(m) if not isinstance(m, trimesh.Trimesh) else m
    up = np.asarray(up, float); h = tm.triangles_center @ up
    sel = (tm.face_normals @ -up > np.cos(np.radians(deg))) & (h > (tm.vertices @ up).min() + skip_bed)
    return float(tm.area_faces[sel].sum())


# ----------------------------------------------------------------------------- checks
def verify_assembly(parts, pins):
    """Assembled check: the pieces must not overlap, and every pin must slide in without touching
    material while reaching well into both of its pieces."""
    names = list(parts)
    print('\nassembly check (print scale):')
    worst = 0.0
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            v = (parts[names[i]] ^ parts[names[j]]).volume()
            worst = max(worst, v)
            if v > 0.5:
                print(f'   OVERLAP {names[i]} / {names[j]}: {v:.1f} mm3')
    print(f'   pieces overlap: largest {worst:.2f} mm3 (0 = they only touch)')
    for lab, a, b in pins:
        pin = cyl(a, b, PIN_D / 2)
        clash = {n: (pin ^ m).volume() for n, m in parts.items()}
        # depth inside each piece = length of the pin axis inside that piece's hole (bounding box of the hole region)
        hole = cyl(a, b, HOLE_R + 1.2) - cyl(a, b, HOLE_R)
        inside = {n: (hole ^ m).volume() / (np.pi * ((HOLE_R + 1.2) ** 2 - HOLE_R ** 2)) for n, m in parts.items()}
        engaged = {n: d for n, d in inside.items() if d > 1.0}
        print(f"   pin {lab:32s} touches material: {max(clash.values()):.2f} mm3; engages " +
              ', '.join(f'{n} {d:.1f} mm' for n, d in engaged.items()))


# ----------------------------------------------------------------------------- main
def pin_set(n=10, d=PIN_D, L=PIN_L, ch=0.5, gap=4.0):
    """n pins standing on end, with chamfered ends, in one file."""
    a = np.linspace(0, 2 * np.pi, SEG, endpoint=False)
    r = d / 2
    ring = lambda rr, z: np.c_[rr * np.cos(a), rr * np.sin(a), np.full(SEG, z)]
    one = hull_pts(np.vstack([ring(r - ch, 0), ring(r, ch), ring(r, L - ch), ring(r - ch, L)]))
    cols = int(np.ceil(np.sqrt(n)))
    return mf.Manifold.batch_boolean([one.translate(((i % cols) * (d + gap), (i // cols) * (d + gap), 0)) for i in range(n)], mf.OpType.Add)


def place_on_bed(Mn, T):
    Mn = Mn.transform(T[:3, :4])
    b = Mn.bounding_box()
    return Mn.translate((-(b[0] + b[3]) / 2, -(b[1] + b[4]) / 2, -b[2]))


BLADE_FILES = {'main': '1_main_plane', 'e2': '2_second_element', 'e3': '3_third_element', 'flap': '4_top_flap'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scale', type=float, default=0.52)
    ap.add_argument('--bed', nargs=3, type=float, default=[420, 420, 450])
    ap.add_argument('--out', default='stl')
    ap.add_argument('--trim', type=float, default=3.2, help='mm (full size) trimmed off the nose rear rim')
    ap.add_argument('--block', type=float, default=16.0, help='centre block half-width, mm (print scale)')
    ap.add_argument('--socket', type=float, default=10.0, help='depth of the blade sockets, mm')
    ap.add_argument('--cut', type=float, default=182.0, help='nose cut, mm above its rear face (print scale)')
    args = ap.parse_args()
    s = args.scale; BED = np.array(args.bed); W, D = args.block, args.socket
    os.makedirs(args.out, exist_ok=True)

    WF = pickle.load(open('wing_frame.pkl', 'rb')); Rw, org = WF['Rw'], WF['org']
    S = np.eye(4); S[:3, :3] = s * Rw; S[:3, 3] = -s * Rw @ org        # world -> wing frame, print scale
    def get(m):
        m = m.copy(); m.apply_transform(S); return m
    blades = {k: get(m) for k, m in pickle.load(open('blades_posed.pkl', 'rb')).items()}
    body = get(load('1_body_posed.pkl'))
    epl, epr = get(load('4a_end_plate_left_posed.pkl')), get(load('4b_end_plate_right_posed.pkl'))
    wing = trimesh.util.concatenate(list(blades.values()))

    # --- nose: placed on the wing, rebuilt as one seamless shell
    cen = wing.vertices[np.abs(wing.vertices[:, 1]) < 1.0]
    nose, _ = place_nose(body, wing, cen[:, 0].max(), s)
    NOSE, up_nose, info = seamless_nose(nose, args.trim * s)
    nose = from_manifold(NOSE)
    print(f"nose rebuilt as one seamless shell: {info['stations']} sections, {info['triangles']} triangles, "
          f"length {info['length']:.1f} mm, genus {NOSE.genus()}")
    full = os.path.join(args.out, 'full_size'); os.makedirs(full, exist_ok=True)        # plain 100 % reference
    manifold_to_stl(place_on_bed(NOSE, rot_to_z(up_nose)).scale((1 / s, 1 / s, 1 / s)), os.path.join(full, '1_body.stl'))

    # --- centre block: nose seat + sockets for the six inner blade ends
    B = {k: M(m) for k, m in blades.items()}
    roots = {k: (B[k], 1 if k.endswith('_L') else -1) for k in B if not k.startswith('flap')}
    blk, _ = build_center_block(roots, nose, W, D)
    for k, (bm, side) in roots.items():
        B[k] = bm.trim_by_plane((0, float(side), 0), float(W - D))      # each blade ends inside its socket
    print(f'centre block: {blk.volume() / 1000:.1f} cm3, {2 * W:.0f} mm wide, 6 blade sockets {D:.0f} mm deep')
    bb = blk.bounding_box()
    pins = []
    for p in nose_pins(blk, nose, (bb[0], bb[3])):
        NOSE = NOSE + nose_boss(p, up_nose)
        h = cyl((p['x'], 0, p['z'] - p['ds']), (p['x'], 0, p['z'] + p['dn']), HOLE_R)
        NOSE, blk = NOSE - h, blk - h
        z0 = p['z'] - p['ds']
        pins.append(('body front <-> centre block', (p['x'], 0, z0), (p['x'], 0, z0 + PIN_L)))
        print(f"pin body <-> centre block at x={p['x']:.1f}: hole {p['ds']:.1f} mm in the block (floor {p['floor']:.1f} mm), "
              f"{p['dn']:.1f} mm in the body")

    # --- end plates: a key on each end plate stub slides into a slot in its blade tip
    EP = {}
    for side, ep, tag in ((1, epl, 'L'), (-1, epr, 'R')):
        names = sorted(k for k in B if k.endswith('_' + tag))
        En, y_s = resplit_tip([B[k] for k in names], ep, side)
        for k in names:
            B[k] = B[k].trim_by_plane((0, float(-side), 0), float(-y_s))   # blade ends at the joint plane
        tongues, slots, (dx, dz) = end_plate_keys([B[k] for k in names], side, y_s)
        EP[side] = En + mf.Manifold.batch_boolean(tongues, mf.OpType.Add)
        for k, sl in zip(names, slots):
            B[k] = B[k] - sl
        ang = np.degrees(np.arctan(np.hypot(dx, dz)))
        print(f"{'left' if side > 0 else 'right'} end plate: joint at |y| = {y_s:.1f} mm, a 5 mm key into each blade tip; "
              f"slides on {ang:.0f} deg off the span (back {abs(dx):.2f}, down {abs(dz):.2f} mm per mm)")
        for k, t in zip(names, tongues):
            print(f'   key {k}: {t.volume():.0f} mm3')

    # --- nose in two pieces
    rear, front, cut_pins, u_cut = split_nose(NOSE, up_nose, args.cut)
    pins += cut_pins
    print(f'body cut {args.cut:.0f} mm above its rear face; 2 pins in bosses on the inside of the side walls')

    pieces = {'body rear': rear, 'body front': front, 'centre block': blk}
    pieces.update({f'blade {k}': B[k] for k in sorted(B)})
    pieces.update({'left end plate': EP[1], 'right end plate': EP[-1]})
    pickle.dump(dict(pieces={k: from_manifold(v) for k, v in pieces.items()}, pins=pins, up_nose=up_nose),
                open('print_ready_assembled.pkl', 'wb'))
    verify_assembly(pieces, pins)

    # --- print orientations
    files = [('1a_body_rear.stl', place_on_bed(rear, rot_to_z(up_nose)), 'standing on its rear opening'),
             ('1b_body_front.stl', place_on_bed(front, rot_to_z(up_nose)), 'standing on the cut face, tip up'),
             ('2_centre_block.stl', place_on_bed(blk, rot_to_z((0, -1.0, 0))), 'standing on one socket face')]
    for k in sorted(B):
        base, tag = k.rsplit('_', 1); side = 1 if tag == 'L' else -1
        up = (0, -side, 0) if base == 'flap' else (0, side, 0)          # flap: tip down; others: inner end down
        Bo = place_on_bed(B[k], rot_to_z(up))
        tw = support_towers(Bo, up_axis=2)
        for h_top, _ in tw:
            print(f'   blade {k}: break-away support tower up to {h_top:.1f} mm')
        Bo = mf.Manifold.batch_boolean([Bo] + [t for _, t in tw], mf.OpType.Add)
        how = 'standing on its outer end' if base == 'flap' else 'standing on its inner end'
        files.append((f"{'3_left' if side > 0 else '4_right'}_blade_{BLADE_FILES[base]}.stl", Bo, how))
    eps = []
    for Em, name in ((EP[1], 'left'), (EP[-1], 'right')):
        Eo, ang, ch = flat_base(place_on_bed(Em, rot_to_z((1.0, 0, 0))))
        print(f'{name} end plate stands on its rear edge: tilted {ang:+.1f} deg, gap under the edge filled (up to {ch:.1f} mm)')
        eps.append(Eo)
    b0, b1 = eps[0].bounding_box(), eps[1].bounding_box()
    w0, w1 = b0[3] - b0[0], b1[3] - b1[0]
    files.append(('5_end_plates.stl', eps[0].translate((-(w0 + 15) / 2, 0, 0)) + eps[1].translate(((w1 + 15) / 2, 0, 0)),
                  'standing on their rear edges'))
    files.append(('6_pins.stl', pin_set(6), f'{PIN_D:.0f} x {PIN_L:.0f} mm, standing'))

    print(f'\nscale {s * 100:.0f}%  build volume {BED[0]:.0f} x {BED[1]:.0f} x {BED[2]:.0f} mm')
    for fname, Mn, how in files:
        chk, bad = manifold_to_stl(Mn, os.path.join(args.out, fname), expect_solids=len(Mn.decompose()), scale=s)
        ext = chk.extents
        print(f'{fname:40s} {ext[0]:6.1f} x {ext[1]:6.1f} x {ext[2]:6.1f} mm  fits={bool(np.all(ext <= BED))}  '
              f'solids={len(chk.split(only_watertight=False))}  watertight={chk.is_watertight}  non-manifold={bad}  '
              f'overhang>45deg={overhang_area(chk):.0f} mm2  ({how})')


if __name__ == '__main__':
    main()
