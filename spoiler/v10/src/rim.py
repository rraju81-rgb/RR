"""v10 grooved rim: the smooth curve the rim follows, and its two legs as clean swept solids.
The curve: for each x, where the gap between the spoiler's underside and the car first grows past RIM_G (the rear edge
of the contact band at the back), then a lower envelope over RIM_WIN and Gaussian smoothing over RIM_SIG, so it is one
smooth line (no steps from the car model's faceted crest). The legs: a profile swept along that line (see layout.py)."""
import numpy as np, trimesh
from scipy import ndimage as ndi
from scipy.interpolate import RegularGridInterpolator as RGI
from skimage.measure import find_contours
from trimesh.ray.ray_pyembree import RayMeshIntersector
from layout import RIM_G, RIM_WIN, RIM_SIG, RIM_LEG, RIM_GAP, RIM_SLOPE, RIM_X, RIM_S

def gap_map(E, car, x0=-600.0, x1=600.0, dx=1.0, z0=90.0, z1=235.0, dz=0.5):
    xs = np.arange(x0, x1 + 1e-9, dx); zs = np.arange(z0, z1 + 1e-9, dz)
    X, Z = np.meshgrid(xs, zs, indexing='ij')
    def first(R, y0, dy):
        O = np.column_stack([X.ravel(), np.full(X.size, y0), Z.ravel()])
        loc, ir, it = R.intersects_location(O, np.tile([0, dy, 0], (len(O), 1)), multiple_hits=False)
        out = np.full(X.size, np.nan); out[ir] = loc[:, 1]; return out.reshape(X.shape)
    return xs, zs, first(RayMeshIntersector(E), -400.0, 1.0), first(RayMeshIntersector(car), 400.0, -1.0)

def rim_curve(E, car, step=1.0):
    """stations along the rim: (x, z) in plan, forward unit normal (x, z), and y0 (just under the underside)"""
    xs, zs, ybot, ycar = gap_map(E, car)
    g = np.where(np.isfinite(ybot - ycar), ybot - ycar, 50.0)
    xb = np.arange(-RIM_X, RIM_X + 1e-9, 0.5)
    zz = []
    for G0 in RIM_G:
        c = max(find_contours(g, G0), key=len)
        P = np.column_stack([np.interp(c[:, 0], np.arange(len(xs)), xs), np.interp(c[:, 1], np.arange(len(zs)), zs)])
        zb = np.full(len(xb), np.nan)
        for i, x in enumerate(xb):
            k = np.abs(P[:, 0] - x) < 0.75
            if k.any(): zb[i] = P[k, 1].max()
        ok = np.isfinite(zb); zz.append(np.interp(xb, xb[ok], zb[ok]))
    base = np.mean(zz, axis=0)
    zr = ndi.gaussian_filter1d(ndi.minimum_filter1d(base, int(RIM_WIN / 0.5), mode='nearest'), RIM_SIG / 0.5, mode='nearest')
    # resample by arc length in plan
    s = np.r_[0, np.cumsum(np.hypot(np.diff(xb), np.diff(zr)))]
    t = np.arange(0, s[-1] + 1e-9, step)
    x = np.interp(t, s, xb); z = np.interp(t, s, zr)
    T = np.column_stack([np.gradient(x), np.gradient(z)]); T /= np.linalg.norm(T, axis=1, keepdims=True)
    N = np.column_stack([T[:, 1], -T[:, 0]])                                  # forward (into the contact band)
    Yb = RGI((xs, zs), np.where(np.isfinite(ybot), ybot, 1e3), bounds_error=False, fill_value=1e3)
    def base(t0, t1):                                                     # just under the underside, across one leg
        y = np.min([Yb(np.column_stack([x + b * N[:, 0], z + b * N[:, 1]])) for b in np.arange(t0, t1 + 0.01, 0.5)], axis=0)
        return ndi.gaussian_filter1d(y, 4.0, mode='nearest') - 0.3
    y0r = base(0.0, RIM_LEG); y0f = base(RIM_LEG + RIM_GAP, 2 * RIM_LEG + RIM_GAP)
    Gi = RGI((xs, zs), g, bounds_error=False, fill_value=50.0)
    gap_rear = np.max([Gi(np.column_stack([x + b * N[:, 0], z + b * N[:, 1]])) for b in np.arange(0, RIM_LEG + 0.01, 0.5)], axis=0)
    return dict(x=x, z=z, N=N, y0r=y0r, y0f=y0f, gap_rear_leg=gap_rear)

def _sweep(st, prof, y0, centre, seg=1.0):
    """closed solid: 2D profile (t forward, s up above y0) swept along the stations. The outline is cut into ~seg mm
    pieces (no long thin faces) and each end is capped with a fan from `centre`, a point that sees the whole outline"""
    pts = []
    for a, b in zip(prof, prof[1:] + prof[:1]):
        k = max(1, int(np.ceil(np.hypot(b[0] - a[0], b[1] - a[1]) / seg)))
        pts += [(a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k) for j in range(k)]
    x, z, N = st['x'], st['z'], st['N']; n, K = len(x), len(pts)
    V = np.empty((K * n + 2, 3))
    for k, (tt, ss) in enumerate(pts):
        V[k * n:(k + 1) * n] = np.column_stack([x + tt * N[:, 0], y0 + ss, z + tt * N[:, 1]])
    for e, i in enumerate((0, n - 1)):
        V[K * n + e] = [x[i] + centre[0] * N[i, 0], y0[i] + centre[1], z[i] + centre[0] * N[i, 1]]
    F = []
    for i in range(n - 1):
        for k in range(K):
            k2 = (k + 1) % K; a0, a1, b0, b1 = k * n + i, k2 * n + i, k * n + i + 1, k2 * n + i + 1
            F += [[a0, b0, b1], [a0, b1, a1]]
    for e, i in enumerate((0, n - 1)):
        c = K * n + e
        for k in range(K):
            k2 = (k + 1) % K
            F.append([c, k * n + i, k2 * n + i] if i == 0 else [c, k2 * n + i, k * n + i])
    m = trimesh.Trimesh(V, np.array(F), process=True)
    if m.volume < 0: m.invert()
    assert m.is_watertight and m.is_winding_consistent and m.is_volume, 'rim sweep is not a closed solid'
    return m

def legs(st):
    """the two legs, each a closed solid: (rear leg, front leg)"""
    k = np.tan(np.radians(RIM_SLOPE)); A, G, B, S, D = RIM_LEG, RIM_GAP, RIM_LEG, RIM_S, 8.0
    rear = [(0, -D), (A, -D), (A, 0), (A - k * S, S), (-k * S, S), (0, 0)]
    f0 = A + G
    front = [(f0, -D), (f0 + B, -D), (f0 + B, 0), (f0 + B + k * S, S), (f0 + k * S, S), (f0, 0)]
    # counter-clockwise in (t, s) seen along the sweep direction is not guaranteed: _sweep fixes the orientation
    return (_sweep(st, rear, st['y0r'], (A / 2 - 0.5, 0.5)), _sweep(st, front, st['y0f'], (f0 + B - 0.5, 0.5)))
