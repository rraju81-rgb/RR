"""Turn the four assembled pieces into a pinned, print-ready set at one scale (default 52 %).

    python3 print_ready.py [--scale 0.52] [--bed 420 420 450] [--out stl]

Run in the pipeline's working folder, after build_left_right.py (wing_left/right_posed.pkl) and
export_all.py (1_body_posed.pkl, 4a/4b_end_plate_*_posed.pkl). Needs wing_frame.pkl.

All joint features are made at PRINT scale, in the assembled position, so every pin hole lines
up with its partner exactly:

* Nose seat: the nose (mirror plane on the wing's centre line) is placed with its underside on
  the wing's centre section, tip flush with the main plane's leading edge. A saddle under the
  nose (split down the centre line with the wing) fills the slots there; its top is the exact
  shape of the nose underside.
* Pins are 5 mm x 20 mm. Holes are 5.2 mm, about 10 mm deep in each part:
  - left wing <-> right wing: 2 pins across the centre line, through the saddle;
  - nose <-> wing: 1 pin in each saddle half (far apart, so the nose can't twist), up into a
    boss inside the nose;
  - wing <-> end plate: 2 pins per side, in teardrop bosses that bridge the element slots next
    to the end plate (the elements are only ~4 mm thick there). The joint is first moved to one
    flat cut a few mm inboard, because the end plate's element stubs ended at different spans.
* Print orientations: nose standing on its rear opening (rim trimmed flat), wings standing on
  the centre face (span vertical: the aerofoils print as plain layers), end plates standing on
  their rear edge (tilted a few degrees, with the gap under the edge filled, so they stand flat).
  Every boss has a 45-degree underside in its print orientation. The top flap starts in mid-air
  when the wing stands up, so break-away support towers are included in each wing file.
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


def teardrop(c, r, down, axis, y0, y1, seg=SEG):
    """Prism along `axis` (unit) from y0 to y1 with a teardrop section: circle radius r at c,
    pointed towards `down` (unit, perpendicular to axis) so the underside is 45 degrees."""
    c, down, axis = np.asarray(c, float), np.asarray(down, float), np.asarray(axis, float)
    side = np.cross(axis, down)
    a = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    ring = [c + r * (np.cos(t) * side + np.sin(t) * down) for t in a] + [c + down * r * np.sqrt(2)]
    ring = np.array(ring)
    ring = ring - axis * (ring @ axis)[:, None]
    return hull_pts(np.vstack([ring + axis * y0, ring + axis * y1]))


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


def trim_rim(nose, trim):
    """Trim the nose's uneven rear rim flat; return manifold and the print 'up' direction."""
    V = nose.vertices
    rim = V[V[:, 0] < V[:, 0].min() + 8]
    c = rim.mean(0); _, _, vt = np.linalg.svd(rim - c); pn = vt[2] if vt[2][0] > 0 else -vt[2]
    h0 = (V @ pn).min()
    return M(nose).trim_by_plane(tuple(pn), float(h0 + trim)), pn


# ----------------------------------------------------------------------------- saddle
def section_xz(mesh, y, xlo, xhi):
    sec = mesh.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
    if sec is None:
        return np.zeros((0, 2))
    P = np.vstack([np.asarray(d)[:, [0, 2]] for d in sec.discrete])
    return P[(P[:, 0] > xlo) & (P[:, 0] < xhi)]


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


def build_saddle(wing, nose, W, xlo, xhi, dy=0.5):
    """Solid under the nose, |y| <= W: convex hull of the element sections (slots filled) up to
    the nose, minus the nose itself, clipped to the nose's outline seen from above."""
    gx, gy = np.meshgrid(np.arange(xlo, xhi, 1.0), np.arange(-W, W + 1e-9, 1.0))
    cr = crossings(nose, gx.ravel(), gy.ravel())
    inner = np.array([c[1] for c in cr if len(c) >= 3])          # inside face of the bottom wall
    zcap = inner.min() - 0.3                         # cap stays below the inside of the nose wall
    parts = []
    prev = None
    for y in np.arange(-W, W + 1e-9, dy):
        P = section_xz(wing, y, xlo, xhi)
        if len(P) < 3:
            prev = None; continue
        P = np.vstack([P, [[P[:, 0].min(), zcap], [P[:, 0].max(), zcap]]])
        H = MultiPoint([tuple(p) for p in P]).convex_hull
        ring = np.array(H.exterior.coords)[:-1]
        cur = np.c_[ring[:, 0], np.full(len(ring), y), ring[:, 1]]
        if prev is not None:
            parts.append(hull_pts(np.vstack([prev, cur])))
        prev = cur
    sad = mf.Manifold.batch_boolean(parts, mf.OpType.Add)
    # outline of the nose from above, 0.5 mm inside
    q = nose.vertices[nose.vertices[:, 0] > xlo - 30]
    out = orient(MultiPoint([tuple(p) for p in q[:, :2]]).convex_hull.buffer(-0.5), 1.0)
    cs = mf.CrossSection([np.array(out.exterior.coords)[:-1]])
    prism = mf.Manifold.extrude(cs, 400).translate((0, 0, -200))
    sad = (sad ^ prism) - M(nose)                      # top takes the exact shape of the underside
    pieces = sorted(sad.decompose(), key=lambda p: -p.volume())
    return pieces[0], zcap


def column(mesh, x, y):
    """(bottom, top) z of the first solid run through (x, y)."""
    c = crossings(mesh, np.array([x]), np.array([y]))[0]
    return (c[0], c[1]) if len(c) >= 2 else (np.nan, np.nan)


# ----------------------------------------------------------------------------- pins
def centre_pins(sad, nose, W):
    """Pin axes for left<->right (along y) and nose<->wing (along z), inside the saddle."""
    sm = from_manifold(sad)
    x0, x1 = sm.bounds[0, 0], sm.bounds[1, 0]; Ls = x1 - x0
    yn = W / 2
    lr, nz = [], []
    for f in (0.10, 0.52):                               # left <-> right, across the centre line
        x = x0 + f * Ls
        zb, zt = column(sm, x, 0.0)
        th = zt - zb
        lr.append(dict(p0=(x, -HOLE_DEPTH, (zb + zt) / 2), p1=(x, HOLE_DEPTH, (zb + zt) / 2), wall=(th - 2 * HOLE_R) / 2))
    for f, y in ((0.30, yn), (0.75, -yn)):              # nose <-> wing: one per half, far apart
        x = x0 + f * Ls
        zb, zt = column(sm, x, y)
        ds = min(HOLE_DEPTH, (zt - zb) - 1.0)            # leave a 1 mm floor under the wing
        dn = PIN_L + 0.5 - ds
        cz = crossings(nose, np.array([x]), np.array([y]))[0]
        nz.append(dict(x=x, y=y, z=zt, ds=ds, dn=dn, z_in=cz[1], floor=(zt - zb) - ds))
    return lr, nz


def nose_boss(p, up):
    """Boss inside the nose for a vertical pin, with a 45-degree underside towards -up
    (the nose prints standing on its rear opening, tip up)."""
    top = p['z'] + p['dn'] + 1.2
    a = np.linspace(0, 2 * np.pi, SEG, endpoint=False)
    ring = np.c_[p['x'] + BOSS_R * np.cos(a), p['y'] + BOSS_R * np.sin(a), np.zeros(SEG)]
    h = top - p['z_in']
    dn_xy = -np.array([up[0], up[1], 0.0]); dn_xy /= np.linalg.norm(dn_xy)
    pts = np.vstack([ring + [0, 0, p['z_in'] - 0.6], ring + [0, 0, top], ring + [0, 0, p['z_in'] - 0.6] + dn_xy * h])
    return hull_pts(pts)


def resplit_tip(wing_half, ep, side, inset=4.5):
    """Move the wing / end plate joint to ONE flat cut, `inset` mm inboard of where the end plate's
    element stubs used to start (they ended at different spans, too short for 10 mm holes).
    Returns (wing half, end plate, |y| of the new joint plane)."""
    from merge import slit_fillers_patch
    y_s = float((ep.vertices[:, 1] * side).min()) - inset
    fill = slit_fillers_patch(wing_half, ep) + slit_fillers_patch(ep, wing_half)
    U = mf.Manifold.batch_boolean([M(wing_half), M(ep)] + [M(f) for f in fill], mf.OpType.Add)
    E = U.trim_by_plane((0, float(side), 0), y_s)
    Wn = U.trim_by_plane((0, -float(side), 0), -y_s)
    return Wn, E, y_s


def element_sections(mesh, y):
    """Outlines (x, z) of the wing elements cut by the plane |y| = y, front (main plane) first."""
    sec = mesh.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
    polys = [Polygon(np.asarray(d)[:, [0, 2]]).buffer(0) for d in sec.discrete if len(d) > 3]
    polys = [p for p in polys if p.area > 1.0]
    els = [dict(xmin=p.bounds[0], xmax=p.bounds[2], pts=np.asarray(p.exterior.coords)) for p in polys]
    return sorted(els, key=lambda e: -e['xmax'])


def mid_z(el, x):
    P = el['pts']
    d = np.abs(P[:, 0] - x)
    q = P[d < max(1.0, np.sort(d)[min(5, len(d) - 1)])]
    return (q[:, 1].min() + q[:, 1].max()) / 2


def end_plate_pins(joint_mesh, side, y_s):
    """Two pins per end plate, each in a teardrop boss bridging the slot between two elements:
    main plane / 2nd element and 3rd element / top flap."""
    els = element_sections(joint_mesh, side * (y_s - 0.3))
    if len(els) != 4:
        raise RuntimeError(f'expected 4 element sections at the end plate joint, found {len(els)}')
    out = []
    for a, b in ((0, 1), (2, 3)):
        A, B = els[a], els[b]
        xc = (A['xmin'] + B['xmax']) / 2
        zc = (mid_z(A, A['xmin'] + 2.5) + mid_z(B, B['xmax'] - 2.5)) / 2
        out.append(dict(xc=xc, zc=zc, ycut=y_s, de=HOLE_DEPTH, dw=HOLE_DEPTH, slot=(a, b), gap=A['xmin'] - B['xmax']))
    return out


def ep_boss_parts(p, side):
    """(wing part, end plate part, hole) for one end plate pin, in the assembled frame.
    Teardrop section pointing to -x: 45-degree underside when the end plate stands on its rear edge."""
    Y = np.array([0, 1.0, 0]); c = (p['xc'], 0, p['zc']); down = (-1.0, 0, 0)
    span = lambda a, b: (min(side * a, side * b), max(side * a, side * b))
    y_in, y_cut, y_out = p['ycut'] - p['dw'] - 1.2, p['ycut'], p['ycut'] + p['de'] + 1.2
    wing_part = teardrop(c, BOSS_R, down, Y, *span(y_in, y_cut))
    # 45-degree lead-in at the inboard end, so it also prints with the wing standing up
    small = 1.4; rr = BOSS_R * np.sqrt(2)
    a = np.linspace(0, 2 * np.pi, SEG, endpoint=False)
    ring = lambda r, y: np.c_[p['xc'] + r * np.cos(a), np.full(SEG, side * y), p['zc'] + r * np.sin(a)]
    lead = np.vstack([ring(BOSS_R, y_in), [[p['xc'] - rr, side * y_in, p['zc']]], ring(small, y_in - (rr - small))])
    wing_part = wing_part + hull_pts(lead)
    ep_part = teardrop(c, BOSS_R, down, Y, *span(y_cut, y_out))
    hole = cyl((p['xc'], side * (p['ycut'] - p['dw']), p['zc']), (p['xc'], side * (p['ycut'] + p['de']), p['zc']), HOLE_R)
    return wing_part, ep_part, hole


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
def pin_axes(lr, nz, ep_pins):
    """(label, start, end) of every 20 mm pin, fully pushed home, in the assembled frame."""
    out = []
    for p in lr:
        x, _, z = p['p0']
        out.append(('left wing <-> right wing', (x, -PIN_L / 2, z), (x, PIN_L / 2, z)))
    for p in nz:
        z0 = p['z'] - p['ds']
        out.append((f"body <-> {'left' if p['y'] > 0 else 'right'} wing", (p['x'], p['y'], z0), (p['x'], p['y'], z0 + PIN_L)))
    for p in ep_pins:
        sd = p['side']; nm = 'left' if sd > 0 else 'right'
        out.append((f'{nm} wing <-> {nm} end plate', (p['xc'], sd * (p['ycut'] - PIN_L / 2), p['zc']), (p['xc'], sd * (p['ycut'] + PIN_L / 2), p['zc'])))
    return out


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scale', type=float, default=0.52)
    ap.add_argument('--bed', nargs=3, type=float, default=[420, 420, 450])
    ap.add_argument('--out', default='stl')
    ap.add_argument('--trim', type=float, default=3.2, help='mm (full size) trimmed off the nose rear rim')
    ap.add_argument('--saddle', type=float, default=26.0, help='saddle half-width, mm at full size')
    args = ap.parse_args()
    s = args.scale; BED = np.array(args.bed)
    os.makedirs(args.out, exist_ok=True)

    WF = pickle.load(open('wing_frame.pkl', 'rb')); Rw, org = WF['Rw'], WF['org']
    S = np.eye(4); S[:3, :3] = s * Rw; S[:3, 3] = -s * Rw @ org        # world -> wing frame, print scale
    def get(f):
        m = load(f); m.apply_transform(S); return m
    wl, wr = get('wing_left_posed.pkl'), get('wing_right_posed.pkl')
    body = get('1_body_posed.pkl')
    epl, epr = get('4a_end_plate_left_posed.pkl'), get('4b_end_plate_right_posed.pkl')
    wing = trimesh.util.concatenate([wl, wr])

    # --- nose on the wing, saddle under it
    cen = wing.vertices[np.abs(wing.vertices[:, 1]) < 1.0]
    x_tip = cen[:, 0].max()
    nose, _ = place_nose(body, wing, x_tip, s)
    W = args.saddle * s
    sad, _ = build_saddle(wing, nose, W, xlo=-40, xhi=x_tip + 1)
    print(f'saddle: {sad.volume() / 1000:.1f} cm3, {2 * W:.1f} mm wide')
    lr, nz = centre_pins(sad, nose, W)
    WL = M(wl) + sad.trim_by_plane((0, 1.0, 0), 0.0)
    WR = M(wr) + sad.trim_by_plane((0, -1.0, 0), 0.0)
    for p in lr:
        h = cyl(p['p0'], p['p1'], HOLE_R)
        WL, WR = WL - h, WR - h
        print(f"pin left<->right at x={p['p0'][0]:.1f} z={p['p0'][2]:.1f}: hole {HOLE_DEPTH:.1f} mm each side, wall {p['wall']:.1f} mm")
    NOSE, up_nose = trim_rim(nose, args.trim * s)
    for p in nz:
        NOSE = NOSE + nose_boss(p, up_nose)
    for p in nz:
        h = cyl((p['x'], p['y'], p['z'] - p['ds']), (p['x'], p['y'], p['z'] + p['dn']), HOLE_R)
        NOSE = NOSE - h
        if p['y'] > 0: WL = WL - h
        else: WR = WR - h
        print(f"pin nose<->{'left' if p['y'] > 0 else 'right'} wing at x={p['x']:.1f} y={p['y']:+.1f}: hole {p['ds']:.1f} mm in the wing "
              f"(floor {p['floor']:.1f} mm), {p['dn']:.1f} mm in the nose")

    # --- end plates: one flat joint plane, two pins each
    EP = {}; ep_pins = []
    for side, name in ((+1, 'left'), (-1, 'right')):
        Wm = WL if side > 0 else WR
        joint = from_manifold(Wm + M(epl if side > 0 else epr))
        Wn, En, y_s = resplit_tip(from_manifold(Wm), epl if side > 0 else epr, side)
        print(f'{name} end plate joint moved to |y| = {y_s:.1f} mm (one flat cut through the 4 elements)')
        for p in end_plate_pins(joint, side, y_s):
            wp, epp, hole = ep_boss_parts(p, side)
            Wn = (Wn + (wp - En)) - hole
            En = (En + (epp - Wn)) - hole
            print(f"pin {name} wing<->end plate across the slot between elements {p['slot']} (slot {p['gap']:.1f} mm): "
                  f"hole {p['dw']:.1f} mm in the wing, {p['de']:.1f} mm in the end plate")
            ep_pins.append(dict(p, side=side))
        if side > 0: WL = Wn
        else: WR = Wn
        EP[side] = En
    EPL, EPR = EP[1], EP[-1]
    pickle.dump(dict(WL=from_manifold(WL), WR=from_manifold(WR), NOSE=from_manifold(NOSE), EPL=from_manifold(EPL),
                     EPR=from_manifold(EPR), nose_up=up_nose, lr=lr, nz=nz, ep=ep_pins), open('print_ready_assembled.pkl', 'wb'))
    verify_assembly(dict(body=NOSE, left_wing=WL, right_wing=WR, left_end_plate=EPL, right_end_plate=EPR), pin_axes(lr, nz, ep_pins))

    # --- print orientations
    files = []
    Tn = rot_to_z(up_nose)
    files.append(('1_body.stl', place_on_bed(NOSE, Tn), 1, f'standing on its rear opening'))
    for name, Wm, up in (('2_left_wing.stl', WL, (0, 1.0, 0)), ('3_right_wing.stl', WR, (0, -1.0, 0))):
        Wo = place_on_bed(Wm, rot_to_z(up))
        tw = support_towers(Wo, up_axis=2)
        for h_top, t in tw:
            print(f'   {name}: break-away support tower up to {h_top:.1f} mm')
        allm = mf.Manifold.batch_boolean([Wo] + [t for _, t in tw], mf.OpType.Add)
        files.append((name, allm, len(allm.decompose()), 'standing on the centre-line face'))
    gap = 15.0
    eps = []
    for Em, name in ((EPL, 'left'), (EPR, 'right')):
        Eo, ang, ch = flat_base(place_on_bed(Em, rot_to_z((1.0, 0, 0))))
        print(f'{name} end plate stands on its rear edge: tilted {ang:+.1f} deg, gap under the edge filled (up to {ch:.1f} mm)')
        eps.append(Eo)
    b0, b1 = eps[0].bounding_box(), eps[1].bounding_box()
    w0, w1 = b0[3] - b0[0], b1[3] - b1[0]
    E = eps[0].translate((-(w0 + gap) / 2, 0, 0)) + eps[1].translate(((w1 + gap) / 2, 0, 0))
    files.append(('4_end_plates.stl', E, 2, 'standing on their rear edges'))
    files.append(('5_pins.stl', pin_set(10), 10, f'{PIN_D:.0f} x {PIN_L:.0f} mm, standing'))

    print(f'\nscale {s * 100:.0f}%  build volume {BED[0]:.0f} x {BED[1]:.0f} x {BED[2]:.0f} mm')
    for fname, Mn, ns, how in files:
        chk, bad = manifold_to_stl(Mn, os.path.join(args.out, fname), expect_solids=ns, scale=s)
        ext = chk.extents
        print(f'{fname:18s} {ext[0]:6.1f} x {ext[1]:6.1f} x {ext[2]:6.1f} mm  fits={bool(np.all(ext <= BED))}  '
              f'solids={len(chk.split(only_watertight=False))}  watertight={chk.is_watertight}  non-manifold={bad}  '
              f'overhang>45deg={overhang_area(chk):.0f} mm2  ({how})')


if __name__ == '__main__':
    main()
