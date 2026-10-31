"""Small numeric helpers: design-curve interpolation, smooth blends, polylines."""

from __future__ import annotations

import numpy as np
from scipy.interpolate import PchipInterpolator


def pchip(xs, ys):
    """Shape-preserving profile through control points, held constant outside."""
    xs = np.asarray(xs, float)
    ys = np.asarray(ys, float)
    order = np.argsort(xs)
    xs, ys = xs[order], ys[order]
    f = PchipInterpolator(xs, ys, extrapolate=False)
    lo, hi = xs[0], xs[-1]

    def g(x):
        return f(np.clip(np.asarray(x, float), lo, hi))

    return g


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def catmull_rom(points, samples_per_segment=24, alpha=0.5, closed=False,
                start_tangent_mirror_y=False, end_tangent_mirror_y=False):
    """Centripetal Catmull-Rom spline through ``points`` (N x 2).

    For open curves whose ends sit on the y = 0 symmetry plane, the
    ``*_tangent_mirror_y`` flags add a phantom point mirrored in y so the curve
    meets the plane at right angles (smooth after mirroring).

    Returns (samples, index_of_each_control_point_in_samples).
    """
    P = np.asarray(points, float)
    if closed:
        ext = np.vstack([P[-1], P, P[0], P[1]])
    else:
        if start_tangent_mirror_y:
            p_before = np.array([P[1, 0], -P[1, 1]])
        else:
            p_before = 2 * P[0] - P[1]
        if end_tangent_mirror_y:
            p_after = np.array([P[-2, 0], -P[-2, 1]])
        else:
            p_after = 2 * P[-1] - P[-2]
        ext = np.vstack([p_before, P, p_after])

    out = []
    ctrl_idx = []
    nseg = len(ext) - 3
    for i in range(nseg):
        p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]

        def tj(ti, pi, pj):
            return ti + max(np.linalg.norm(pj - pi), 1e-9) ** alpha

        t0 = 0.0
        t1 = tj(t0, p0, p1)
        t2 = tj(t1, p1, p2)
        t3 = tj(t2, p2, p3)
        t = np.linspace(t1, t2, samples_per_segment, endpoint=False)[:, None]
        a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
        a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
        a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
        b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
        b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
        c = (t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2
        ctrl_idx.append(i * samples_per_segment)
        out.append(c)
    samples = np.vstack(out)
    if not closed:
        ctrl_idx.append(len(samples))
        samples = np.vstack([samples, P[-1]])
    return samples, np.array(ctrl_idx)


def arclength(poly, closed=False):
    P = np.asarray(poly, float)
    if closed:
        P = np.vstack([P, P[:1]])
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    return np.concatenate([[0.0], np.cumsum(seg)])


def resample(poly, spacing, closed=False):
    """Resample a polyline at (approximately) uniform arc-length spacing.

    Returns (points, s_values) where s are arc-length positions on the input.
    """
    P = np.asarray(poly, float)
    if closed:
        P = np.vstack([P, P[:1]])
    s = arclength(P)
    total = s[-1]
    n = max(int(np.ceil(total / spacing)), 3)
    if closed:
        su = np.linspace(0.0, total, n, endpoint=False)
    else:
        su = np.linspace(0.0, total, n + 1)
    out = np.column_stack([np.interp(su, s, P[:, k]) for k in range(P.shape[1])])
    return out, su


def gaussian_smooth_1d(values, sigma_samples, closed=False):
    v = np.asarray(values, float)
    if sigma_samples <= 0:
        return v.copy()
    r = int(np.ceil(3 * sigma_samples))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma_samples) ** 2)
    k /= k.sum()
    if closed:
        ext = np.concatenate([v[-r:], v, v[:r]])
    else:
        ext = np.concatenate([np.full(r, v[0]), v, np.full(r, v[-1])])
    return np.convolve(ext, k, mode="valid")


def polygon_area(poly):
    x, y = np.asarray(poly, float).T
    return 0.5 * (np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def points_in_polygon(pts, poly):
    """Even-odd point-in-polygon test (vectorised over pts)."""
    pts = np.asarray(pts, float)
    poly = np.asarray(poly, float)
    x, y = pts[:, 0], pts[:, 1]
    inside = np.zeros(len(pts), bool)
    xj, yj = poly[-1]
    for xi, yi in poly:
        cond = ((yi > y) != (yj > y))
        with np.errstate(divide="ignore", invalid="ignore"):
            xint = (xj - xi) * (y - yi) / (yj - yi) + xi
        inside ^= cond & (x < xint)
        xj, yj = xi, yi
    return inside


def distance_to_polyline(pts, poly, closed=True):
    """Unsigned distance from each point to a polyline (vectorised, chunked)."""
    pts = np.asarray(pts, float)
    P = np.asarray(poly, float)
    if closed:
        P = np.vstack([P, P[:1]])
    a = P[:-1]
    b = P[1:]
    ab = b - a
    ab2 = np.maximum((ab ** 2).sum(1), 1e-12)
    out = np.empty(len(pts))
    chunk = 4096
    for i in range(0, len(pts), chunk):
        p = pts[i:i + chunk, None, :]
        t = np.clip(((p - a) * ab).sum(-1) / ab2, 0.0, 1.0)
        proj = a + t[..., None] * ab
        d = np.sqrt(((p - proj) ** 2).sum(-1))
        out[i:i + chunk] = d.min(1)
    return out
