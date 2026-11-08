"""Smooth per-vertex zone fields (positive inside) for paint / glass / trim / lamps / plastics.
Blender's shader thresholds the interpolated fields, so zone borders are smooth inside triangles."""
import numpy as np
from matplotlib.path import Path
from car_body import s_of, h_of, PLAN_CAB, tumble_cab
from car_mats import plan_halfwidth, DLO

def poly_signed(poly_path, P):
    """signed distance (positive inside) of 2D points P to the polygon of a matplotlib Path"""
    V = poly_path.vertices; Vn = np.roll(V, -1, 0); d = np.full(len(P), np.inf)
    for a, b in zip(V, Vn):
        e = b - a; w = P - a; t = np.clip((w @ e) / (e @ e), 0, 1); q = w - t[:, None] * e
        d = np.minimum(d, np.einsum('ij,ij->i', q, q))
    d = np.sqrt(d); inside = poly_path.contains_points(P)
    return np.where(inside, d, -d)

def smooth_fields(F, faces, nv, iters=10):
    import scipy.sparse as sp
    e = np.vstack([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    A = sp.coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(nv, nv)).tocsr(); A = ((A + A.T) > 0).astype(np.float32)
    deg = np.asarray(A.sum(1)).ravel()
    out = {}
    for k_, v in F.items():
        x = v.astype(np.float32).copy()
        for _ in range(iters): x = 0.5 * x + 0.5 * (A @ x) / np.maximum(deg, 1)
        out[k_] = x
    return out

def vertex_normals(V, F):
    """area-weighted vertex normals"""
    V = np.asarray(V, np.float64); F = np.asarray(F)
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    N = np.zeros_like(V)
    for k in range(3):
        for c in range(3): N[:, k] += np.bincount(F[:, c], weights=fn[:, k], minlength=len(V))
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)

def smooth_normals(V, F, iters=60, tau=0.02, N=None):
    """Feature-preserving (bilateral) smoothing of vertex normals over the 1-ring graph. Neighbours whose normals differ
    by a few degrees (marching-cubes / profile-polygon noise) are averaged; real creases (> ~15 deg between neighbours)
    get almost no weight and stay sharp. Geometry is not moved, so the spoiler fit is unchanged."""
    import scipy.sparse as sp
    F = np.asarray(F); nv = len(V)
    N = vertex_normals(V, F) if N is None else np.asarray(N, np.float64).copy()
    e = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]); e = np.vstack([e, e[:, ::-1]])
    W = sp.coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(nv, nv)).tocsr(); W.sum_duplicates()
    r = np.repeat(np.arange(nv), np.diff(W.indptr)); c = W.indices
    for _ in range(iters):
        W.data = np.exp(-(1.0 - np.einsum('ij,ij->i', N[r], N[c])) / tau)
        M = N + W @ N
        N = M / np.maximum(np.linalg.norm(M, axis=1, keepdims=True), 1e-12)
    return N

def fields(V, N):
    x, y, z = V[:, 0], V[:, 1], V[:, 2]; s = s_of(z); h = h_of(y); ax = np.abs(x)
    nx, ny, nz = N[:, 0], N[:, 1], N[:, 2]
    k = 200.0                                   # normal terms -> mm-ish
    mn = lambda *a: np.minimum.reduce(a)
    mx = lambda *a: np.maximum.reduce(a)
    cab_hw = plan_halfwidth(PLAN_CAB, s) * tumble_cab(h, s)
    ws = mn(s - 1150, 1895 - s, h - 975, (1402 - 0.00011 * ax ** 2) - h, (-nz - 0.40) * k, (cab_hw - 70) - ax)
    # rear window by position only (a normal test here left a ragged lower edge)
    rw = mn(s - 3585, 3810 - s, h - 1018, (1356 - 0.00010 * ax ** 2) - h, (cab_hw - 95) - ax)
    # side windows: the outline sets the edges. The normal test only keeps glass off the roof's flat top; at 0.42 it ran
    # alongside the outline's top edge and the two alternated, giving a zig-zag edge.
    dlo = mn(poly_signed(DLO, np.column_stack([s, h])), (np.abs(nx) - 0.25) * k)
    bp = mn(dlo, 38 - np.abs(s - (2228 + (h - 1000) * 0.10)))
    glass = mx(ws, rw, mn(dlo, -bp))
    # tail lamps: one patch wrapped round each rear corner, by position only (the old |nx| / nz tests left ragged edges
    # and flakes at the wrap). At these heights both the side and the rear face are steeper than ~30 deg, so
    # s > 3690 and |x| > 500 inside the height band select just the corner patch.
    a_in = np.maximum(805.0 - ax, 0.0)                                                     # > 0 on the rear face
    b_fw = np.maximum(np.interp(h, [774, 872, 958, 1013], [3910, 3880, 3842, 3796]) - s, 0.0)  # > 0 on the side
    tl_hi = 1003.0 - 0.16 * a_in
    tl_lo = 870.0 + 0.07 * a_in + 0.03 * b_fw
    tail = mn(s - 3690.0, ax - 500.0, h - tl_lo, tl_hi - h)
    rev = mn(tail, 640 - ax, 948 - h)
    head = mn(420 - s, ax - 300, 790 - ax, h - (650 + (ax - 300) * 0.07), (758 + (ax - 300) * 0.03) - h, mx((-nz - 0.15) * k, (np.abs(nx) - 0.5) * k))
    grille = mn(170 - s, 300 - ax, h - 652, 742 - h, (-nz - 0.3) * k)
    chrome = mn(grille, 6 - np.abs(h - 700))
    intake = mn(260 - s, h - 262, 470 - h, (560 - (470 - h) * 0.35) - ax, (-nz - 0.25) * k)
    diffuser = mn(s - 3800, 372 - h, (nz + 0.3) * k)
    under = mn((-ny - 0.6) * k, 230 - h)
    plastic = mx(mn(grille, -chrome), intake, diffuser, under)
    return dict(glass=glass, trim=bp, tail=mn(tail, -rev), rev=rev, head=head, chrome=chrome, plastic=plastic)
