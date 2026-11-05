"""Extract planar joint-candidate faces from part meshes and match them pairwise."""
import numpy as np, trimesh
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity

def plane_groups(m, flat_deg=0.5, merge_deg=1.0, dist_tol=0.12):
    """Region-grow coplanar faces over edges, then merge regions lying on the same plane."""
    import trimesh.graph as tg
    adj = m.face_adjacency
    flat = m.face_adjacency_angles < np.radians(flat_deg)
    comps = tg.connected_components(adj[flat], nodes=np.arange(len(m.faces)), min_len=1)
    a = m.area_faces; c = m.triangles_center; fn = m.face_normals
    regs = []
    for fs in comps:
        fs = np.asarray(fs)
        w = a[fs]
        n = (fn[fs] * w[:, None]).sum(0); n /= np.linalg.norm(n)
        p = (c[fs] * w[:, None]).sum(0) / w.sum()
        regs.append([n, p, list(fs), float(w.sum())])
    regs.sort(key=lambda r: -r[3])
    groups = []
    for n, p, fs, ar in regs:
        for g in groups:
            if np.dot(g[0], n) > np.cos(np.radians(merge_deg)) and abs(np.dot(g[0], p - g[1])) < dist_tol:
                g[2].extend(fs); break
        else:
            groups.append([n, p, list(fs)])
    return [(g[0], float(np.dot(g[0], g[1])), np.array(g[2])) for g in groups]

def frame_for(n):
    ref = np.array([0, 0, 1.0]) if abs(n[2]) < 0.9 else np.array([1.0, 0, 0])
    u = np.cross(ref, n); u /= np.linalg.norm(u)
    v = np.cross(n, u)
    return u, v

def sharp_fraction(m, faces, sharp_deg=40):
    S = np.zeros(len(m.faces), bool); S[faces] = True
    adj = m.face_adjacency; ang = m.face_adjacency_angles
    e = m.face_adjacency_edges
    L = np.linalg.norm(m.vertices[e[:, 0]] - m.vertices[e[:, 1]], axis=1)
    inS = S[adj]
    bd = inS[:, 0] ^ inS[:, 1]
    if bd.sum() == 0:
        return 0.0, 0.0
    sharp = ang[bd] > np.radians(sharp_deg)
    return float((L[bd] * sharp).sum() / L[bd].sum()), float(L[bd].sum())

def joint_faces(m, min_area=15.0, min_extent=35.0, min_sharp=0.75):
    out = []
    V = m.vertices
    for n, d, fs in plane_groups(m):
        area = m.area_faces[fs].sum()
        if area < min_area:
            continue
        proj = V @ n
        extent = proj.max() - proj.min()
        if extent < min_extent:
            continue
        # face must be on the boundary: material lies on -n side
        if d < proj.max() - 1e-3 - 1e9:  # (kept generic; flats may be interior steps)
            pass
        sf, blen = sharp_fraction(m, fs)
        if sf < min_sharp:
            continue
        u, v = frame_for(n)
        o = n * d
        tris = m.triangles[fs] - o
        polys = [Polygon(np.c_[t @ u, t @ v]) for t in tris]
        poly = unary_union([p.buffer(1e-4) for p in polys if p.area > 1e-9]).buffer(-1e-4)
        if poly.is_empty:
            continue
        out.append(dict(n=n, d=d, faces=fs, area=float(area), u=u, v=v, o=o, poly=poly,
                        sharp=sf, extent=float(extent),
                        depth=float(proj.max() - d)))  # >0 means part extends beyond this plane along +n
    return out

def moments(poly):
    """centroid, principal angle, eigenvalues of 2nd moment (approx via triangulation of exterior)."""
    c = np.array(poly.centroid.coords[0])
    pts = []
    geoms = poly.geoms if isinstance(poly, MultiPolygon) else [poly]
    # sample interior on a grid for robust moments
    minx, miny, maxx, maxy = poly.bounds
    step = max(min(maxx - minx, maxy - miny) / 60.0, 0.3)
    from shapely import vectorized  # noqa
    return c

def raster(poly, res, bounds):
    from shapely import contains_xy
    minx, miny, maxx, maxy = bounds
    xs = np.arange(minx, maxx, res) + res / 2
    ys = np.arange(miny, maxy, res) + res / 2
    X, Y = np.meshgrid(xs, ys)
    return contains_xy(poly, X, Y)

def shape_stats(poly, res=0.5):
    from shapely import contains_xy
    minx, miny, maxx, maxy = poly.bounds
    xs = np.arange(minx, maxx, res) + res / 2
    ys = np.arange(miny, maxy, res) + res / 2
    X, Y = np.meshgrid(xs, ys)
    M = contains_xy(poly, X, Y)
    P = np.c_[X[M], Y[M]]
    if len(P) < 3:
        P = np.array(poly.exterior.coords) if hasattr(poly, 'exterior') else np.array(poly.geoms[0].exterior.coords)
    c = P.mean(0)
    C = np.cov((P - c).T)
    w, V = np.linalg.eigh(C)
    ang = np.arctan2(V[1, 1], V[0, 1])  # major axis angle
    return c, ang, w[::-1]

def iou_after(polyA, polyB, theta, t):
    pb = affinity.rotate(polyB, theta, origin=(0, 0), use_radians=True)
    pb = affinity.translate(pb, t[0], t[1])
    inter = polyA.intersection(pb).area
    uni = polyA.area + pb.area - inter
    return inter / uni if uni > 0 else 0.0

def register2d(polyA, polyB):
    """Find rotation theta + translation t so that rot(polyB)+t ~ polyA. polyB already mirrored."""
    cA, aA, wA = shape_stats(polyA)
    cB, aB, wB = shape_stats(polyB)
    best = (-1, None, None)
    # if nearly isotropic, scan all angles
    iso = (wA[1] / max(wA[0], 1e-9) > 0.6)
    cands = list(np.radians(np.arange(0, 360, 6))) if iso else [aA - aB, aA - aB + np.pi]
    for th0 in cands:
        for dth in np.radians(np.arange(-6, 6.1, 1.5)):
            th = th0 + dth
            R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
            t = cA - R @ cB
            s = iou_after(polyA, polyB, th, t)
            if s > best[0]:
                best = (s, th, t)
    # local refine (coordinate descent)
    s, th, t = best
    step_a, step_t = np.radians(0.75), 0.5
    for _ in range(40):
        improved = False
        for dth, dx, dy in [(step_a, 0, 0), (-step_a, 0, 0), (0, step_t, 0), (0, -step_t, 0), (0, 0, step_t), (0, 0, -step_t)]:
            th2 = th + dth
            R = np.array([[np.cos(th2), -np.sin(th2)], [np.sin(th2), np.cos(th2)]])
            # keep centroid aligned when rotating, then apply offset
            t2 = (cA - R @ cB) + (t - (cA - np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]]) @ cB)) + np.array([dx, dy])
            s2 = iou_after(polyA, polyB, th2, t2)
            if s2 > s + 1e-5:
                s, th, t = s2, th2, t2; improved = True
        if not improved:
            step_a /= 2; step_t /= 2
            if step_t < 0.02:
                break
    return s, th, t

def mirror_poly(poly):
    return affinity.scale(poly, xfact=1, yfact=-1, origin=(0, 0))

def transform_from_match(fA, fB, theta, t):
    """4x4 transform mapping part-B coords into part-A coords for face fB mating fA."""
    # B mirrored frame: (uB, -vB, -nB) with origin oB ; A frame: (uA, vA, nA) origin oA
    FB = np.stack([fB['u'], -fB['v'], -fB['n']])          # rows: world->local for B
    FA = np.stack([fA['u'], fA['v'], fA['n']])
    R2 = np.eye(3); R2[:2, :2] = [[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]]
    # local_B = FB @ (x - oB)  (note: poly for B was built with (u,v) coords then mirrored y->-y: consistent with rows u,-v)
    # local_A = R2 @ local_B + [t,0]
    # x_A = oA + FA.T @ local_A
    Rw = FA.T @ R2 @ FB
    tw = fA['o'] + FA.T @ np.r_[t, 0] - Rw @ fB['o']
    T = np.eye(4); T[:3, :3] = Rw; T[:3, 3] = tw
    return T

def register2d_multi(polyA, polyB, n_scan=None):
    """Like register2d but returns refined optima for every initial orientation (both principal flips,
    or a coarse angular scan for near-isotropic shapes)."""
    cA, aA, wA = shape_stats(polyA)
    cB, aB, wB = shape_stats(polyB)
    iso = (wA[1] / max(wA[0], 1e-9) > 0.6)
    inits = list(np.radians(np.arange(0, 360, 15))) if iso else [aA - aB, aA - aB + np.pi]
    outs = []
    for th0 in inits:
        best = (-1, None, None)
        for dth in np.radians(np.arange(-8, 8.1, 1.0)):
            th = th0 + dth
            R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
            t = cA - R @ cB
            s = iou_after(polyA, polyB, th, t)
            if s > best[0]:
                best = (s, th, t)
        s, th, t = best
        step_a, step_t = np.radians(0.75), 0.5
        for _ in range(60):
            improved = False
            for dth, dx, dy in [(step_a, 0, 0), (-step_a, 0, 0), (0, step_t, 0), (0, -step_t, 0), (0, 0, step_t), (0, 0, -step_t)]:
                th2 = th + dth
                R2 = np.array([[np.cos(th2), -np.sin(th2)], [np.sin(th2), np.cos(th2)]])
                R1 = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
                t2 = (cA - R2 @ cB) + (t - (cA - R1 @ cB)) + np.array([dx, dy])
                s2 = iou_after(polyA, polyB, th2, t2)
                if s2 > s + 1e-5:
                    s, th, t = s2, th2, t2; improved = True
            if not improved:
                step_a /= 2; step_t /= 2
                if step_t < 0.02:
                    break
        outs.append((s, th % (2 * np.pi), t))
    # dedupe by angle
    outs.sort(key=lambda o: -o[0])
    ded = []
    for o in outs:
        if all(abs(((o[1] - d[1] + np.pi) % (2 * np.pi)) - np.pi) > np.radians(3) for d in ded):
            ded.append(o)
    return ded
