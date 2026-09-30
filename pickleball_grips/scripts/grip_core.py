"""Core geometry for the pickleball grip family.

Every grip is a *displacement-mapped tube* wrapped around the reference cavity:

    P(S, z, h) = cavity_point(S) + h * outward_normal(S) + z * e_z

  S : arclength along the crest-offset curve (offset 3.5 mm) - periodic, length L
  z : height above the butt (0 .. z_top)
  h : distance of the outer skin from the cavity wall

The cavity itself (octagonal bore, floor at z=5, open top) is copied verbatim
from the reference profile, so fitment is identical for every design.  Only the
outer skin h(S, z) changes between designs.
"""
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, gaussian_filter1d
from scipy.spatial import cKDTree

DATA = Path(__file__).resolve().parent.parent / "data"

# print-orientation limiter: outer skin may grow outward by at most SLOPE mm per mm of
# height (45 deg overhang) so every design prints upright without supports.
OVERHANG_SLOPE = 1.0

# textured zone (smooth collars outside).  Extended up the neck like the reference's honeycomb.
ZONE_LO, ZONE_HI = 21.5, 116.0
# print rules for a solid 100 % infill part on a 0.4 mm nozzle
BASE_WALL = 1.2     # 3 x 0.4 mm perimeters
MIN_RIM = 0.8       # thinnest skin anywhere (2 x 0.4 mm); the reference tapers to 0.36 mm
POST_SIGMA = 0.20   # mm - rounding applied after the overhang limiter


class Frame:
    def __init__(self, ds=0.25, dense=0.05, wall=BASE_WALL, rim=MIN_RIM):
        P = json.loads((DATA / "reference_profile.json").read_text())
        self.P = P
        self.z_top = P["z_top"]
        self.z_floor = P["z_floor"]
        self.z_foot = P["z_foot_top"]
        self.crest = P["crest_offset"]
        self.wall = wall                       # base wall of the textured zone (reference: 1.5)
        self.min_rim = rim                     # minimum skin thickness (reference tapers to 0.36)
        self.foot_z, self.foot_e = np.array(P["foot_table"]).T
        self.taper_z, self.taper_e = np.array(P["taper_table"]).T

        ring = np.array(P["cavity_ring"])[:-1]
        if 0.5 * np.sum(ring[:, 0] * np.roll(ring[:, 1], -1) - np.roll(ring[:, 0], -1) * ring[:, 1]) < 0:
            ring = ring[::-1]
        start = np.argmin(np.hypot(ring[:, 0], ring[:, 1] - ring[:, 1].max()))   # top-face centre
        ring = np.roll(ring, -start, axis=0)
        self.ring = ring

        # dense resample that keeps every original polygon vertex (cavity stays exact)
        pts = []
        for k in range(len(ring)):
            a, b = ring[k], ring[(k + 1) % len(ring)]
            n = max(1, int(np.ceil(np.hypot(*(b - a)) / dense)))
            pts.append(a + (b - a) * (np.arange(n) / n)[:, None])
        self.dp = np.vstack(pts)
        nd = len(self.dp)
        d1 = np.roll(self.dp, -1, 0) - np.roll(self.dp, 1, 0)
        sig = 0.25 / dense
        tx = gaussian_filter1d(d1[:, 0], sig, mode="wrap")
        ty = gaussian_filter1d(d1[:, 1], sig, mode="wrap")
        tn = np.hypot(tx, ty)
        self.dn = np.c_[ty / tn, -tx / tn]                         # outward normals (CCW ring)
        crest_pts = self.dp + self.crest * self.dn
        seg = np.hypot(*(np.roll(crest_pts, -1, 0) - crest_pts).T)
        self.dS = np.r_[0, np.cumsum(seg)]                          # nd+1 values, last = L
        self.L = float(self.dS[-1])

        self.N = int(round(self.L / ds))
        self.S = np.arange(self.N) * self.L / self.N
        self.c, self.n = self._interp(self.S)
        self.center = self.c.mean(0)
        self._tree = cKDTree(self.dp)

    # --- parameter <-> geometry -------------------------------------------------
    def _interp(self, S):
        S = np.mod(np.asarray(S, float), self.L)
        idx = np.interp(S, self.dS, np.arange(len(self.dS)))
        i0 = np.floor(idx).astype(int) % len(self.dp)
        i1 = (i0 + 1) % len(self.dp)
        f = (idx - np.floor(idx))[..., None]
        c = self.dp[i0] * (1 - f) + self.dp[i1] * f
        n = self.dn[i0] * (1 - f) + self.dn[i1] * f
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        return c, n

    def point_at(self, S, z, h):
        c, n = self._interp(S)
        return np.c_[c + n * np.asarray(h)[..., None], np.asarray(z)]

    def locate(self, pts):
        """3D points -> (S, z, offset-from-cavity) using the nearest cavity sample."""
        d, i = self._tree.query(pts[:, :2])
        off = np.einsum("ij,ij->i", pts[:, :2] - self.dp[i], self.dn[i])
        return self.dS[i], pts[:, 2], off

    # --- envelope ---------------------------------------------------------------
    def E_foot(self, z):
        return np.interp(z, self.foot_z, self.foot_e)

    def E_ref_upper(self, z):
        """The reference's own outer offset above the foot (crest zone + taper)."""
        z = np.asarray(z, float)
        return np.where(z < self.taper_z[0], self.crest, np.interp(z, self.taper_z, self.taper_e))

    def E_upper(self, z):
        """Outer offset used by the grips: the reference curve, but never thinner than min_rim."""
        return np.maximum(self.E_ref_upper(z), self.min_rim)

    def rows(self, res=0.25):
        """Ring heights.  Foot rows | pattern rows (from z=20) | taper rows."""
        foot = np.array([0, .05, .1, .2, .3, .45, .6, .8, 1.0, 1.25, 1.5, 1.8, 2.2, 3, 4.5, 7, 10, 13, 16, 18.5, 19.5])
        pat = np.arange(20.0, 118.0 + 1e-9, res)
        tap = np.r_[np.arange(118.5, 124.0, 0.5), np.arange(124.0, 132.0, 1.0), self.z_top]
        return foot, pat, tap

    def zone_window(self, z, lo=ZONE_LO, hi=ZONE_HI, ramp=1.5):
        """1 inside the textured zone, 0 in the smooth collars (t=1 there)."""
        s = lambda x: np.clip(x, 0, 1) ** 2 * (3 - 2 * np.clip(x, 0, 1))
        return s((z - lo) / ramp) * (1 - s((z - hi + ramp) / ramp))

    # --- assembling the outer skin ---------------------------------------------
    def skin(self, t, res=0.25):
        """t: (Mp, N) texture in [0,1] on the pattern rows -> (z rows, H offsets, n_foot)."""
        foot, pat, tap = self.rows(res)
        assert t.shape == (len(pat), self.N), (t.shape, len(pat), self.N)
        w = self.zone_window(pat)[:, None]
        t = np.clip(t * w + (1 - w), 0, 1)
        Eu = self.E_upper(pat)[:, None]
        B = np.minimum(self.wall, Eu)
        Hp = B + (Eu - B) * t
        # 45-degree overhang limiter (first row is the flush start of the textured zone)
        dz = np.diff(pat)[:, None]
        for j in range(1, len(pat)):
            Hp[j] = np.minimum(Hp[j], Hp[j - 1] + OVERHANG_SLOPE * dz[j - 1])
        # The limiter runs per column on the row grid, so on diagonal edges each column's chamfer starts
        # on a different row (0.25 mm teeth).  Averaging removes the teeth and cannot steepen a slope
        # bound, so the 45 degree limit still holds; then re-clip to the wall/envelope limits.
        ds = self.L / self.N
        Hp = gaussian_filter(Hp, (POST_SIGMA / res, POST_SIGMA / ds), mode=("nearest", "wrap"))
        Hp = np.clip(Hp, B, Eu)
        Hf = np.repeat(self.E_foot(foot)[:, None], self.N, 1)
        Ht = np.repeat(self.E_upper(tap)[:, None], self.N, 1)
        z = np.r_[foot, pat, tap]
        H = np.vstack([Hf, Hp, Ht])
        return z, H, len(foot)


def build_mesh(F, z, H):
    """Watertight sleeve: foot/skin rings + rim + cavity wall + floor + butt cap."""
    M, N = H.shape
    out = np.empty((M, N, 3))
    out[..., :2] = F.c[None] + F.n[None] * H[..., None]
    out[..., 2] = z[:, None]
    cav_top = np.c_[F.c, np.full(N, F.z_top)]
    cav_flr = np.c_[F.c, np.full(N, F.z_floor)]
    ctr = F.c.mean(0)
    bc = np.r_[ctr, 0.0]
    fc = np.r_[ctr, F.z_floor]
    V = np.vstack([out.reshape(-1, 3), cav_top, cav_flr, bc, fc])
    o = M * N
    iT, iF, iBc, iFc = o, o + N, o + 2 * N, o + 2 * N + 1
    i = np.arange(N)
    i1 = (i + 1) % N
    faces = []
    for j in range(M - 1):                                     # outer skin
        a, b, c, d = j * N + i, j * N + i1, (j + 1) * N + i1, (j + 1) * N + i
        # split every quad along its shorter 3D diagonal: follows the contour on steep
        # ramps and avoids the zig-zag a fixed diagonal produces
        ac = np.linalg.norm(V[a] - V[c], axis=1) <= np.linalg.norm(V[b] - V[d], axis=1)
        t1 = np.where(ac[:, None], np.c_[a, b, c], np.c_[a, b, d])
        t2 = np.where(ac[:, None], np.c_[a, c, d], np.c_[b, c, d])
        faces += [t1, t2]
    ot = (M - 1) * N + i
    ot1 = (M - 1) * N + i1
    faces += [np.c_[ot, ot1, iT + i1], np.c_[ot, iT + i1, iT + i]]            # top rim
    a, b, c, d = iF + i, iF + i1, iT + i1, iT + i
    faces += [np.c_[a, c, b], np.c_[a, d, c]]                                  # cavity wall (faces inward)
    faces += [np.c_[np.full(N, iFc), iF + i, iF + i1]]                         # cavity floor
    faces += [np.c_[np.full(N, iBc), i1, i]]                                   # butt cap (ring 0 = z 0)
    return V, np.vstack(faces).astype(np.int32)


# --- hole cutting (through-windows) ---------------------------------------------
def _earcut(pts2d):
    import mapbox_earcut as ec
    return ec.triangulate_float64(np.ascontiguousarray(pts2d, np.float64), np.array([len(pts2d)], np.uint32)).reshape(-1, 3)


def cutter_mesh(F, poly, h_lo=-1.0, h_hi=8.0, seg=0.25):
    """Loft a (S,z) polygon along the wall normals -> closed prism used to punch a window."""
    ring = np.asarray(poly.exterior.coords)[:-1]
    if poly.exterior.is_ccw is False:
        ring = ring[::-1]
    dense = []
    for k in range(len(ring)):
        a, b = ring[k], ring[(k + 1) % len(ring)]
        n = max(1, int(np.ceil(np.hypot(*(b - a)) / seg)))
        dense.append(a + (b - a) * (np.arange(n) / n)[:, None])
    r = np.vstack(dense)
    K = len(r)
    lo = F.point_at(r[:, 0], r[:, 1], np.full(K, h_lo))
    hi = F.point_at(r[:, 0], r[:, 1], np.full(K, h_hi))
    tri = _earcut(r)
    V = np.vstack([lo, hi])
    k = np.arange(K)
    k1 = (k + 1) % K
    faces = [tri[:, ::-1], tri + K]                                         # bottom (down), top (up)
    faces += [np.c_[k, k1, K + k1], np.c_[k, K + k1, K + k]]                # sides
    f = np.vstack(faces).astype(np.int32)
    vol = np.einsum("ij,ij->", V[f[:, 0]], np.cross(V[f[:, 1]], V[f[:, 2]])) / 6
    if vol < 0:
        f = f[:, ::-1]
    return V, f


def cut_windows(F, V, Fc, polys):
    import manifold3d as m3d
    base = m3d.Manifold(m3d.Mesh(np.asarray(V, np.float32), np.asarray(Fc, np.uint32)))
    cutters = []
    for p in polys:
        cv, cf = cutter_mesh(F, p)
        cutters.append(m3d.Manifold(m3d.Mesh(np.asarray(cv, np.float32), np.asarray(cf, np.uint32))))
    res = m3d.Manifold.batch_boolean([base] + cutters, m3d.OpType.Subtract)
    if hasattr(res, 'simplify'):
        res = res.simplify(0.002)          # collapse sliver/degenerate triangles left by the cuts (2 um)
    m = res.to_mesh()
    return np.asarray(m.vert_properties[:, :3], np.float64), np.asarray(m.tri_verts, np.int32)


# --- grid reduction: drop rows/cols that are linear within eps ------------------
def _pos(F, z, H, cols):
    p = np.empty(H.shape + (3,))
    p[..., :2] = F.c[cols][None] + F.n[cols][None] * H[..., None]
    p[..., 2] = z[:, None]
    return p


def reduce_grid(F, z, H, eps=0.004, protect=()):
    """Remove whole rings / columns whose skin is linear within eps (mm).  The grid stays
    structured (no T-junctions); cavity nodes are tested too, so the bore never changes."""
    rows = np.arange(len(z))
    cols = np.arange(H.shape[1])
    protect = set(protect)
    for _ in range(40):
        changed = False
        for par in (0, 1):                                      # ---- rows
            P = _pos(F, z[rows], H[np.ix_(rows, cols)], cols)
            k = np.arange(1, len(rows) - 1)
            k = k[(k % 2 == par) & ~np.isin(rows[k], list(protect))]
            if not len(k):
                continue
            za, zb, zc = z[rows[k - 1]], z[rows[k]], z[rows[k + 1]]
            f = ((zb - za) / np.maximum(zc - za, 1e-12))[:, None, None]
            err = np.linalg.norm(P[k] - (P[k - 1] * (1 - f) + P[k + 1] * f), axis=2).max(1)
            ok = err < eps
            if ok.any():
                rows = np.delete(rows, k[ok]); changed = True
        for par in (0, 1):                                      # ---- columns
            P = _pos(F, z[rows], H[np.ix_(rows, cols)], cols)
            k = np.arange(par, len(cols), 2)
            p, q = (k - 1) % len(cols), (k + 1) % len(cols)
            Sg = F.S[cols]
            f = (((Sg[k] - Sg[p]) % F.L) / ((Sg[q] - Sg[p]) % F.L))
            err = np.linalg.norm(P[:, k] - (P[:, p] * (1 - f)[None, :, None] + P[:, q] * f[None, :, None]), axis=2).max(0)
            cav = F.c[cols]
            cerr = np.linalg.norm(cav[k] - (cav[p] * (1 - f)[:, None] + cav[q] * f[:, None]), axis=1)
            ok = (err < eps) & (cerr < eps)
            if ok.any():
                cols = np.delete(cols, k[ok]); changed = True
        if not changed:
            break
    return rows, cols


class _SubFrame:
    """A Frame restricted to a subset of columns (for reduced meshes)."""
    def __init__(self, F, cols):
        self.c, self.n = F.c[cols], F.n[cols]
        self.z_top, self.z_floor = F.z_top, F.z_floor


def build_mesh_reduced(F, z, H, eps=0.004):
    rows, cols = reduce_grid(F, z, H, eps=eps, protect=(0, len(z) - 1))
    return build_mesh(_SubFrame(F, cols), z[rows], H[np.ix_(rows, cols)])


def write_stl(path, V, Fc):
    tri = V[Fc].astype(np.float32)
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(nrm, axis=1, keepdims=True)
    nrm = np.where(ln > 0, nrm / np.where(ln > 0, ln, 1), 0).astype(np.float32)
    rec = np.zeros(len(Fc), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"], rec["v"] = nrm, tri
    with open(path, "wb") as f:
        f.write(b"Pickleball grip - fitment matched to PickleballGrip_1.3mf".ljust(80, b" "))
        f.write(np.uint32(len(Fc)).tobytes())
        f.write(rec.tobytes())
