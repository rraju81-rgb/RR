"""Minimal signed-distance-field (SDF) sculpting kernel.

The hammerhead shark (body, cephalofoil, fins, engraved gills, mouth, ...)
is described as SDF primitives combined with smooth booleans, sampled on a
regular grid and meshed with marching cubes.

Conventions
-----------
* Units are millimetres, +X points forward, +Y to the car's left, +Z up.
* The model is mirror-symmetric about Y=0.  Only the Y >= 0 half of the grid is
  evaluated and then mirrored, so primitives that represent left/right pairs
  are defined once, on the +Y side.  Central parts must be symmetric (they use
  |y| internally or are symmetric by construction).
* Every primitive carries an integer ``label`` (a paint/material id).  The
  label of the primitive that "wins" a boolean is tracked so the final mesh
  can be colourised for previews.
"""
from __future__ import annotations

import math
import multiprocessing as mp
from dataclasses import dataclass

import numpy as np
from scipy.interpolate import PchipInterpolator

FAR = 1.0e3  # "very far outside" distance used for culled regions


# --------------------------------------------------------------------------
# smooth boolean helpers
# --------------------------------------------------------------------------
def smin(a, b, k):
    """Polynomial smooth minimum (fillet radius ~k)."""
    if k <= 0.0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1.0 - h) + a * h - k * h * (1.0 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


# --------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------
class Node:
    """Base class.  Subclasses implement ``bounds`` and ``__call__``."""

    label = 0

    def bounds(self):  # -> (lo[3], hi[3])
        raise NotImplementedError

    def __call__(self, p):  # p: (N, 3) float64 -> (N,) float64
        raise NotImplementedError


class Loft(Node):
    """Superellipse cross-sections swept along +X (fuselage-type bodies).

    ``keys`` is a list of dicts with keys
        x   station
        a   half width                     (required)
        zc  section centre height          (required)
        bt  half height above zc           (required)
        bb  half height below zc           (required)
        ys  lateral offset of the section centre (default 0, mirrored)
        nt, nb  superellipse exponent above / below zc (default 2.5)
    Parameters are interpolated with monotone cubic (PCHIP) splines.  The ends
    are closed with elliptical caps of length ``cap0`` / ``cap1``.
    """

    PARAMS = ("a", "zc", "bt", "bb", "ys", "nt", "nb")
    DEFAULTS = {"ys": 0.0, "nt": 2.5, "nb": 2.5}

    def __init__(self, keys, label=0, cap0=3.0, cap1=3.0, step=0.05):
        keys = sorted(keys, key=lambda k: k["x"])
        xs = np.array([k["x"] for k in keys], float)
        self.x0, self.x1 = float(xs[0]), float(xs[-1])
        self.step = step
        self.tx = np.arange(self.x0, self.x1 + step * 0.5, step)
        tab = {}
        for name in self.PARAMS:
            vals = np.array([k.get(name, self.DEFAULTS.get(name)) for k in keys], float)
            tab[name] = PchipInterpolator(xs, vals)(self.tx)
        # elliptical end caps
        g = np.ones_like(self.tx)
        if cap0 > 0:
            s = np.clip((self.tx - self.x0) / cap0, 0.0, 1.0)
            g *= np.sqrt(np.clip(1.0 - (1.0 - s) ** 2, 0.0, 1.0))
        if cap1 > 0:
            s = np.clip((self.x1 - self.tx) / cap1, 0.0, 1.0)
            g *= np.sqrt(np.clip(1.0 - (1.0 - s) ** 2, 0.0, 1.0))
        for name in ("a", "bt", "bb"):
            tab[name] = np.maximum(tab[name] * g, 1e-3)
        self.tab = np.stack([tab[n] for n in self.PARAMS], axis=1)  # (M, 7)
        self.label = label
        lo_y = tab["ys"] - tab["a"]
        hi_y = tab["ys"] + tab["a"]
        self._lo = np.array([self.x0, min(0.0, lo_y.min()), (tab["zc"] - tab["bb"]).min()])
        self._hi = np.array([self.x1, max(np.abs(lo_y).max(), hi_y.max()), (tab["zc"] + tab["bt"]).max()])

    def bounds(self):
        return self._lo, self._hi

    def params(self, x):
        """Section parameters (a, zc, bt, bb, ys, nt, nb) at positions x."""
        f = np.clip((x - self.x0) / self.step, 0.0, len(self.tx) - 1.000001)
        i = f.astype(np.int64)
        t = (f - i)[:, None]
        return self.tab[i] * (1 - t) + self.tab[i + 1] * t

    def __call__(self, p):
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        # Distance is estimated in the cross-section plane (first-order
        # f/|grad f| of the superellipse).  Ignoring the axial taper keeps the
        # estimate close to Euclidean for gently tapering bodies; including it
        # badly under-estimates distances near the end caps, which makes smooth
        # unions bulge.  Beyond the ends an axial term is added.
        a, zc, bt, bb, ys, nt, nb = self.params(x).T
        u = np.abs(np.abs(y) - ys) / a
        dz = z - zc
        top = dz >= 0
        b = np.where(top, bt, bb)
        n = np.where(top, nt, nb)
        w = np.abs(dz) / b
        r = np.maximum((u ** n + w ** n) ** (1.0 / n), 1e-9)
        gy = (u / r) ** (n - 1.0) / a
        gz = (w / r) ** (n - 1.0) / b
        d = (r - 1.0) / np.maximum(np.sqrt(gy * gy + gz * gz), 1e-9)
        dx = np.maximum(np.maximum(self.x0 - x, x - self.x1), 0.0)
        return np.where(dx > 0, np.sqrt(np.maximum(d, 0.0) ** 2 + dx * dx), d)


def polygon_sdf(px, py, poly):
    """Signed distance to a simple closed polygon (negative inside)."""
    d2 = np.full(px.shape, np.inf)
    inside = np.zeros(px.shape, bool)
    m = len(poly)
    for i in range(m):
        ax, ay = poly[i]
        bx, by = poly[i - 1]
        ex, ey = bx - ax, by - ay
        wx, wy = px - ax, py - ay
        t = np.clip((wx * ex + wy * ey) / (ex * ex + ey * ey + 1e-30), 0.0, 1.0)
        dx, dy = wx - ex * t, wy - ey * t
        np.minimum(d2, dx * dx + dy * dy, out=d2)
        c1 = py >= ay
        c2 = py < by
        c3 = ex * wy > ey * wx
        inside ^= (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
    d = np.sqrt(d2)
    return np.where(inside, -d, d)


class Fin(Node):
    """A thin, edge-rounded plate built from a planar outline.

    The outline lives in the plane (C, U, V); thickness is along W.  The
    half-thickness grows from ``h_edge`` at the outline to ``core(u, v)``
    (default ``h_core``) over a distance ``ramp`` inside the outline, which
    gives blade-like fins and wings.  ``offset(u, v)`` bends the mid-surface
    along W (camber / anhedral / sweep curvature).
    """

    def __init__(self, outline_uv, frame, h_edge=0.5, h_core=1.2, ramp=3.0,
                 core=None, offset=None, label=0, round_edge=0.9, offset_max=0.0):
        self.poly = np.asarray(outline_uv, float)
        C, U, V = (np.asarray(f, float) for f in frame)
        U = U / np.linalg.norm(U)
        V = V - U * np.dot(U, V)
        V = V / np.linalg.norm(V)
        self.C, self.U, self.V, self.W = C, U, V, np.cross(U, V)
        self.h_edge, self.h_core, self.ramp = h_edge, h_core, ramp
        self.core, self.offset = core, offset
        self.round = round_edge
        self.label = label
        # conservative bounds: outline +/- (max thickness + offset) along W
        tmax = (h_core if core is None else max(h_core, 3.0)) + offset_max
        pts = C + self.poly[:, :1] * U + self.poly[:, 1:2] * V
        ext = np.abs(self.W) * tmax + 0.5
        self._lo = pts.min(0) - ext
        self._hi = pts.max(0) + ext

    def bounds(self):
        return self._lo, self._hi

    def __call__(self, p):
        q = p - self.C
        u = q @ self.U
        v = q @ self.V
        w = q @ self.W
        d2 = polygon_sdf(u, v, self.poly)
        hc = self.h_core if self.core is None else self.core(u, v)
        h = self.h_edge + (hc - self.h_edge) * smoothstep(0.0, self.ramp, -d2)
        if self.offset is not None:
            w = w - self.offset(u, v)
        re = self.round * self.h_edge
        qx = d2 + re
        qy = np.abs(w) - h + re
        out = np.sqrt(np.maximum(qx, 0.0) ** 2 + np.maximum(qy, 0.0) ** 2)
        return out + np.minimum(np.maximum(qx, qy), 0.0) - re


class Ellipsoid(Node):
    def __init__(self, c, r, label=0, rot=None):
        self.c = np.asarray(c, float)
        self.r = np.asarray(r, float)
        self.R = None if rot is None else np.asarray(rot, float)  # world->local
        self.label = label
        m = self.r.max()
        self._lo, self._hi = self.c - m, self.c + m

    def bounds(self):
        return self._lo, self._hi

    def __call__(self, p):
        q = p - self.c
        if self.R is not None:
            q = q @ self.R.T
        k0 = np.linalg.norm(q / self.r, axis=1)
        k1 = np.linalg.norm(q / (self.r * self.r), axis=1)
        return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


class RoundBox(Node):
    def __init__(self, c, half, r=0.0, label=0, rot=None):
        self.c = np.asarray(c, float)
        self.h = np.asarray(half, float)
        self.r = r
        self.R = None if rot is None else np.asarray(rot, float)
        self.label = label
        m = np.linalg.norm(self.h) + r
        self._lo, self._hi = self.c - m, self.c + m

    def bounds(self):
        return self._lo, self._hi

    def __call__(self, p):
        q = p - self.c
        if self.R is not None:
            q = q @ self.R.T
        q = np.abs(q) - self.h + self.r
        out = np.linalg.norm(np.maximum(q, 0.0), axis=1)
        return out + np.minimum(q.max(axis=1), 0.0) - self.r


class Tube(Node):
    """Union of round cones along a polyline (variable radius)."""

    def __init__(self, pts, radii, label=0):
        self.p = np.asarray(pts, float)
        r = np.asarray(radii, float)
        self.r = np.full(len(self.p), float(r)) if r.ndim == 0 else r
        self.label = label
        m = self.r.max()
        self._lo = self.p.min(0) - m
        self._hi = self.p.max(0) + m

    def bounds(self):
        return self._lo, self._hi

    @staticmethod
    def round_cone(p, a, b, r1, r2):
        ba = b - a
        l2 = float(ba @ ba)
        rr = r1 - r2
        a2 = l2 - rr * rr
        il2 = 1.0 / l2
        pa = p - a
        y = pa @ ba
        z = y - l2
        x2v = pa * l2 - np.outer(y, ba)
        x2 = np.einsum("ij,ij->i", x2v, x2v)
        y2 = y * y * l2
        z2 = z * z * l2
        k = math.copysign(1.0, rr) * rr * rr * x2
        d_end = np.sqrt(x2 + z2) * il2 - r2
        d_start = np.sqrt(x2 + y2) * il2 - r1
        d_mid = (np.sqrt(x2 * a2 * il2) + y * rr) * il2 - r1
        return np.where(np.sign(z) * a2 * z2 > k, d_end,
                        np.where(np.sign(y) * a2 * y2 < k, d_start, d_mid))

    def __call__(self, p):
        d = np.full(len(p), np.inf)
        for i in range(len(self.p) - 1):
            a, b = self.p[i], self.p[i + 1]
            lo = np.minimum(a, b) - max(self.r[i], self.r[i + 1]) - 2.0
            hi = np.maximum(a, b) + max(self.r[i], self.r[i + 1]) + 2.0
            m = np.all((p >= lo) & (p <= hi), axis=1)
            if not m.any():
                continue
            d[m] = np.minimum(d[m], self.round_cone(p[m], a, b, self.r[i], self.r[i + 1]))
        return np.where(np.isfinite(d), d, FAR)


class Groove(Node):
    """Material within ``depth`` of ``base``'s surface, clipped to ``slab``.

    Used as a cutter to engrave constant-depth grooves (gill slits, ...).
    """

    def __init__(self, base, slab, depth, label=0):
        self.base, self.slab, self.depth, self.label = base, slab, depth, label

    def bounds(self):
        return self.slab.bounds()

    def __call__(self, p):
        return np.maximum(self.slab(p), -(self.base(p) + self.depth))


# --------------------------------------------------------------------------
# programme: a sequence of boolean steps with per-step smoothing
# --------------------------------------------------------------------------
@dataclass
class Step:
    op: str      # 'add' (smooth union) | 'sub' (smooth subtraction)
    node: Node
    k: float = 0.0


class Program:
    def __init__(self):
        self.steps: list[Step] = []

    def add(self, node, k=0.0):
        self.steps.append(Step("add", node, k))
        return node

    def sub(self, node, k=0.0):
        self.steps.append(Step("sub", node, k))
        return node

    def evaluate(self, p, blo, bhi, band=4.0):
        d = np.full(len(p), FAR)
        lab = np.zeros(len(p), np.uint8)
        for s in self.steps:
            lo, hi = s.node.bounds()
            m = s.k + band
            if np.any(bhi < lo - m) or np.any(blo > hi + m):
                continue
            v = s.node(p)
            if s.op == "add":
                lab = np.where(v < d, np.uint8(s.node.label), lab)
                d = smin(d, v, s.k)
            else:
                lab = np.where(-v > d, np.uint8(s.node.label), lab)
                d = smax(d, -v, s.k)
        return d, lab


# --------------------------------------------------------------------------
# grid sampling + meshing
# --------------------------------------------------------------------------
_G = {}


def _work(job):
    prog, origin, h, (i0, i1, j0, j1, k0, k1) = _G["prog"], _G["origin"], _G["h"], job
    xs = origin[0] + h * np.arange(i0, i1)
    ys = origin[1] + h * np.arange(j0, j1)
    zs = origin[2] + h * np.arange(k0, k1)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    p = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)
    blo = np.array([xs[0], ys[0], zs[0]])
    bhi = np.array([xs[-1], ys[-1], zs[-1]])
    d, lab = prog.evaluate(p, blo, bhi)
    shape = (i1 - i0, j1 - j0, k1 - k0)
    return job, d.astype(np.float32).reshape(shape), lab.reshape(shape)


def sample_half(prog, lo, hi, h, block=40, procs=None):
    """Sample the programme on the Y>=0 half grid and mirror to full grid.

    Returns (field, labels, origin) with field shape (nx, ny_full, nz).
    """
    lo = np.asarray(lo, float)
    hi = np.asarray(hi, float)
    nx = int(math.ceil((hi[0] - lo[0]) / h)) + 1
    nyh = int(math.ceil(hi[1] / h)) + 1          # y = 0 .. hi
    nz = int(math.ceil((hi[2] - lo[2]) / h)) + 1
    origin = np.array([lo[0], 0.0, lo[2]])
    jobs = [(i, min(i + block, nx), j, min(j + block, nyh), k, min(k + block, nz))
            for i in range(0, nx, block) for j in range(0, nyh, block) for k in range(0, nz, block)]
    field = np.empty((nx, nyh, nz), np.float32)
    labels = np.empty((nx, nyh, nz), np.uint8)
    _G.update(prog=prog, origin=origin, h=h)
    ctx = mp.get_context("fork")
    with ctx.Pool(procs or mp.cpu_count()) as pool:
        for (i0, i1, j0, j1, k0, k1), d, lab in pool.imap_unordered(_work, jobs, chunksize=4):
            field[i0:i1, j0:j1, k0:k1] = d
            labels[i0:i1, j0:j1, k0:k1] = lab
    full = np.concatenate([field[:, :0:-1, :], field], axis=1)
    full_lab = np.concatenate([labels[:, :0:-1, :], labels], axis=1)
    origin_full = np.array([lo[0], -(nyh - 1) * h, lo[2]])
    return full, full_lab, origin_full


def mesh_field(field, labels, origin, h):
    """Marching cubes -> (verts, faces, vert_labels) with outward winding."""
    from skimage.measure import marching_cubes

    # samples exactly on the iso-level create ambiguous (non-manifold) cubes
    field = np.where(field == 0.0, np.float32(1e-5), field)
    padded = np.pad(field, 1, mode="constant", constant_values=FAR)
    verts, faces, _n, _v = marching_cubes(padded, 0.0, spacing=(h, h, h),
                                          allow_degenerate=False, method="lewiner")
    verts = verts - h  # undo padding
    idx = np.clip(np.rint(verts / h).astype(np.int64), 0, np.array(labels.shape) - 1)
    vlab = labels[idx[:, 0], idx[:, 1], idx[:, 2]]
    verts = verts + origin
    faces = faces.astype(np.int64)
    # orient outward (positive signed volume)
    tri = verts[faces]
    vol = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6.0
    if vol < 0:
        faces = faces[:, ::-1]
    return verts, faces, vlab
