"""The ten grip surface designs.

Each design function receives a Ctx and returns a dict:
    t     (Mp, N) float in [0,1]  - relief: 0 = base wall (1.5 mm), 1 = crest (3.5 mm)
    rgb   (Mp, N, 3) uint8        - preview colour map (render only, never in the STL)
    holes list[shapely Polygon]   - optional (S, z) windows punched through the wall

All designs share the same cavity, foot, top taper and 1.5/3.5 mm wall/crest limits, so
they are drop-in replacements for the reference sleeve.
"""
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt, map_coordinates
from shapely import affinity
from shapely.geometry import Point, Polygon, MultiPoint, box
from shapely.ops import unary_union, voronoi_diagram

Z_LO, Z_HI = 23.0, 108.0          # textured zone (smooth collars outside)


def sm(e0, e1, x):
    x = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return x * x * (3 - 2 * x)


def lerp(a, b, w):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return a + (b - a) * np.asarray(w)[..., None]


def gauss(x, s):
    return np.exp(-0.5 * (x / s) ** 2)


def pdiff(a, b, L):
    return (a - b + L / 2) % L - L / 2


class Ctx:
    def __init__(self, F, res=0.25, seed=7):
        self.F, self.L, self.N, self.S, self.res = F, F.L, F.N, F.S, res
        _, self.Z, _ = F.rows(res)
        self.S2, self.Z2 = np.meshgrid(F.S, self.Z)
        self.z0, self.z1 = Z_LO, Z_HI
        self.hz = self.z1 - self.z0
        self.seed = seed


class Canvas:
    """High-resolution periodic raster of the unrolled surface (S wraps, z does not)."""

    def __init__(self, c, res=0.1):
        self.c, self.L, self.res = c, c.L, res
        self.zlo, self.zhi = c.Z[0], c.Z[-1]
        self.W = int(round(self.L / res))
        self.H = int(round((self.zhi - self.zlo) / res)) + 1

    def image(self):
        return Image.new("L", (self.W, self.H), 0)

    def _pts(self, S, z, shift):
        return [((s + shift) / self.res, (zz - self.zlo) / self.res) for s, zz in zip(S, z)]

    def line(self, draw, S, z, width=1, fill=255):
        for sh in (-self.L, 0.0, self.L):
            draw.line(self._pts(S, z, sh), fill=fill, width=width)

    def polygon(self, draw, S, z, fill=255):
        for sh in (-self.L, 0.0, self.L):
            draw.polygon(self._pts(S, z, sh), fill=fill)

    def edt(self, img):
        """Distance (mm) from every pixel to the nearest drawn pixel."""
        return distance_transform_edt(np.asarray(img) == 0) * self.res

    def sample(self, arr, order=1):
        co = [(self.c.Z2 - self.zlo) / self.res, self.c.S2 / self.res]
        return map_coordinates(np.asarray(arr, float), co, order=order, mode="grid-wrap")


# ---------------------------------------------------------------------------------
# 01  VORTEX GRIP - braided over/under helical straps
# ---------------------------------------------------------------------------------
def vortex(c):
    S, Z = c.S2, c.Z2
    n, m = 8, np.tan(np.radians(36))
    Ls = c.L / n
    a, b = (S - m * Z) / Ls, (S + m * Z) / Ls
    par = (np.floor(a) + np.floor(b)) % 2
    wf = 0.40
    ua, ub = (a % 1 - .5) / (wf / 2), (b % 1 - .5) / (wf / 2)
    mA, mB = 1 - sm(0.80, 1.0, np.abs(ua)), 1 - sm(0.80, 1.0, np.abs(ub))
    lvA, lvB = 0.70 + 0.30 * (1 - np.abs(ua) ** 2), 0.70 + 0.30 * (1 - np.abs(ub) ** 2)
    valley, drop = 0.10, 0.24
    aover = (par == 0)
    tA = valley + (lvA - valley - drop * mB * (~aover)) * mA
    tB = valley + (lvB - valley - drop * mA * aover) * mB
    t = np.maximum(tA, tB)
    w = sm(0.30, 0.65, t)
    rgb = lerp((52, 30, 82), (156, 108, 222), w)
    rgb = rgb * (0.86 + 0.14 * t)[..., None]
    cls = (w > 0.5).astype(np.uint8)
    return dict(t=t, rgb=rgb, cls=cls, collar=1, palette=[(58, 34, 92), (156, 108, 222)])


# ---------------------------------------------------------------------------------
# 02  CELLULAR MOD - staggered stacked cells, some recessed as insert pockets
# ---------------------------------------------------------------------------------
def cellular(c):
    rng = np.random.default_rng(21)
    nr, nc = 9, 8
    pitch, cw = c.hz / nr, c.L / nc
    zz = np.clip(c.Z2 - c.z0, 0, c.hz - 1e-6)
    r = np.floor(zz / pitch).astype(int)
    v = zz - r * pitch
    dze = np.minimum(v, pitch - v) - 0.7
    stag = (r % 2) * cw / 2
    u = np.mod(c.S2 - stag, cw)
    dse = np.minimum(u, cw - u) - 0.7
    ci = np.floor((c.S2 - stag) / cw).astype(int) % nc
    d = np.minimum(dze, dse)
    lv = rng.choice([0.80, 0.90, 1.0], size=(nr, nc), p=[.3, .4, .3])[r, ci]
    ins = (rng.random((nr, nc)) < 0.22)[r, ci]
    t = np.where(d < 0, 0.0, 0.12 + (lv - 0.12) * sm(0.0, 1.0, d))
    pocket = sm(1.6, 2.2, d) * ins
    t = t - (t - 0.42) * pocket
    rgb = lerp((136, 136, 132), (168, 168, 162), lv - .8)
    rgb = np.where((d < 0)[..., None], np.array([70, 70, 72.]), rgb)
    rgb = lerp(rgb, (200, 30, 34), pocket > 0.5)
    cls = np.where(pocket > 0.5, 2, np.where(d < 0, 0, 1)).astype(np.uint8)
    return dict(t=t, rgb=rgb, cls=cls, collar=1, palette=[(70, 70, 72), (150, 150, 146), (200, 30, 34)])


# ---------------------------------------------------------------------------------
# 03  TESSEL-BLOCK - faceted triangular pyramids in staggered rows
# ---------------------------------------------------------------------------------
def tessel(c):
    nx, nr = 12, 10
    ell, hr = c.L / nx, c.hz / nr
    zz = np.clip(c.Z2 - c.z0, 0, c.hz - 1e-6)
    q = zz / hr
    r = np.floor(q).astype(int)
    fq = q - r
    p = c.S2 / ell - 0.5 * r
    i = np.floor(p)
    fx = p - i
    up = fq + np.abs(2 * fx - 1) <= 1
    bC, bA, bB = fq, 1 - fx - fq / 2, fx - fq / 2
    ic = np.where(fx < 0.5, 0, 1)
    dx = np.where(fx < 0.5, fx, fx - 1)
    dC, dB, dA = 1 - fq, fq / 2 + dx, fq / 2 - dx
    bmin = np.where(up, np.minimum(np.minimum(bA, bB), bC), np.minimum(np.minimum(dA, dB), dC))
    g = np.clip(3 * bmin, 0, 1)
    lvl = np.where(up, 1.0, 0.80)
    t = 0.05 + (lvl - 0.05) * np.clip(g / 0.88, 0, 1)
    ident = (r + i.astype(int) + ic * (~up) + (~up)) % 2
    rim = (r == 0) | (r == nr - 1)
    base = np.where(ident[..., None] == 0, np.array([232, 116, 42.]), np.array([56, 122, 196.]))
    base = np.where(rim[..., None], np.array([132, 132, 130.]), base)
    rgb = base * (0.45 + 0.55 * np.clip(g / 0.9, 0, 1))[..., None]
    cls = np.where(rim, 0, np.where(ident == 0, 1, 2)).astype(np.uint8)
    return dict(t=t, rgb=rgb, cls=cls, collar=0, palette=[(132, 132, 130), (232, 116, 42), (56, 122, 196)])


# ---------------------------------------------------------------------------------
# 04  LOGIC-GRIP - interlocking jigsaw pieces separated by fine grooves
# ---------------------------------------------------------------------------------
def _knob(ell):
    neck = box(0.40 * ell, -0.02 * ell, 0.60 * ell, 0.22 * ell)
    head = Point(0.5 * ell, 0.285 * ell).buffer(0.165 * ell, 40)
    k = unary_union([neck, head])
    return k.buffer(0.05 * ell, 24).buffer(-0.05 * ell, 24)


def _place(k, origin, u, v):
    xs, ys = k.exterior.xy
    xs, ys = np.array(xs), np.array(ys)
    X = origin[0] + xs * u[0] + ys * v[0]
    Y = origin[1] + xs * u[1] + ys * v[1]
    return Polygon(np.c_[X, Y])


def logic(c):
    rng = np.random.default_rng(11)
    nx, ny = 8, 6
    cw, ch = c.L / nx, c.hz / ny
    Vs = rng.choice([-1, 1], size=(ny, nx))          # vertical edge k (at S=k*cw), row r
    Hs = rng.choice([-1, 1], size=(ny + 1, nx))      # horizontal edge r (z=z0+r*ch), col k
    kV, kH = _knob(ch), _knob(cw)
    pieces = {}
    for r in range(ny):
        for k in range(nx):
            s0, s1 = k * cw, (k + 1) * cw
            z0, z1 = c.z0 + r * ch, c.z0 + (r + 1) * ch
            P = box(s0, z0, s1, z1)
            # left edge (index k), right edge (k+1)
            for (edge_k, sgn_side, s_e) in ((k, "L", s0), ((k + 1) % nx, "R", s1)):
                sg = Vs[r, edge_k]
                if sgn_side == "L":
                    if sg == +1:     # knob emerges from left neighbour into this piece
                        P = P.difference(_place(kV, (s_e, z0), (0, 1), (1, 0)))
                    else:            # knob emerges from this piece toward -S
                        P = P.union(_place(kV, (s_e, z0), (0, 1), (-1, 0)))
                else:
                    if sg == +1:     # knob emerges from this piece toward +S
                        P = P.union(_place(kV, (s_e, z0), (0, 1), (1, 0)))
                    else:            # knob emerges from right neighbour into this piece
                        P = P.difference(_place(kV, (s_e, z0), (0, 1), (-1, 0)))
            for (edge_r, side, z_e) in ((r, "B", z0), (r + 1, "T", z1)):
                if edge_r in (0, ny):
                    continue
                sg = Hs[edge_r, k]
                if side == "B":
                    if sg == +1:
                        P = P.difference(_place(kH, (s0, z_e), (1, 0), (0, 1)))
                    else:
                        P = P.union(_place(kH, (s0, z_e), (1, 0), (0, -1)))
                else:
                    if sg == +1:
                        P = P.union(_place(kH, (s0, z_e), (1, 0), (0, 1)))
                    else:
                        P = P.difference(_place(kH, (s0, z_e), (1, 0), (0, -1)))
            pieces[(r, k)] = P
    cv = Canvas(c, 0.1)
    lines, ids = cv.image(), Image.new("L", (cv.W, cv.H), 0)
    dl, di = ImageDraw.Draw(lines), ImageDraw.Draw(ids)
    for (r, k), P in pieces.items():
        for g in (P.geoms if hasattr(P, "geoms") else [P]):
            x, y = g.exterior.xy
            cv.line(dl, x, y, width=1)
            cv.polygon(di, x, y, fill=1 + ((r + k) % 2))
    d = cv.sample(cv.edt(lines))
    ident = cv.sample(np.asarray(ids), order=0)
    gw = 0.55
    t = np.where(d < gw, 0.0, 0.85 * sm(gw, gw + 0.75, d))
    t = t + 0.15 * sm(0.9, 3.6, d)
    t = np.where(ident == 0, 0.0, t)
    rgb = np.where((ident == 1)[..., None], np.array([42, 60, 138.]), np.array([158, 164, 170.]))
    rgb = lerp(np.array([50, 50, 54.]), rgb, sm(0.0, 0.5, t) * 0 + np.clip(t * 4, 0, 1))
    rgb = rgb * (0.75 + 0.25 * t)[..., None]
    cls = np.where(t < 0.25, 0, np.where(ident == 1, 1, 2)).astype(np.uint8)
    return dict(t=t, rgb=rgb, cls=cls, collar=2, palette=[(50, 50, 54), (42, 60, 138), (158, 164, 170)])


# ---------------------------------------------------------------------------------
# 05  NEURO-TREAD - raised neural network over a dimpled base
# ---------------------------------------------------------------------------------
def _lattice_dist(S, Z, sp):
    rh = sp * 0.8660254
    q = Z / rh
    j0 = np.floor(q)
    best = np.full(S.shape, 1e9)
    for j in (j0, j0 + 1):
        x0 = (j % 2) * sp / 2
        m = np.round((S - x0) / sp)
        best = np.minimum(best, np.hypot(S - (x0 + m * sp), Z - j * rh))
    return best


def neuro(c):
    rng = np.random.default_rng(3)
    nS, nZ = 8, 6
    sS = c.L / nS
    zs = np.linspace(c.z0 + 5, c.z1 - 5, nZ)
    sZ = zs[1] - zs[0]
    P = []
    for j, z in enumerate(zs):
        for i in range(nS):
            P.append(((i + 0.5 * (j % 2)) * sS + rng.uniform(-.28, .28) * sS, z + rng.uniform(-.3, .3) * sZ))
    P = np.array(P)
    tiled = np.vstack([P + [sh, 0] for sh in (-c.L, 0, c.L)])
    from scipy.spatial import Delaunay
    tri = Delaunay(tiled)
    edges = set()
    for s in tri.simplices:
        for a, b in ((s[0], s[1]), (s[1], s[2]), (s[0], s[2])):
            edges.add((min(a, b), max(a, b)))
    cv = Canvas(c, 0.1)
    ax, soma = cv.image(), cv.image()
    dax, dso = ImageDraw.Draw(ax), ImageDraw.Draw(soma)
    for a, b in edges:
        p, q = tiled[a], tiled[b]
        mid = (p + q) / 2
        if not (-0.05 * c.L <= mid[0] < 1.05 * c.L):
            continue
        ln = np.hypot(*(q - p))
        if ln > 1.75 * sS:
            continue
        key = np.sin(np.round(mid[0] % c.L, 1) * 12.9898 + np.round(mid[1], 1) * 78.233) * 43758.5453
        u = key - np.floor(key)
        if u < 0.38:
            continue
        nrm = np.array([-(q - p)[1], (q - p)[0]]) / ln
        ctrl = mid + nrm * ln * (0.20 if u > 0.6 else -0.20)
        tt = np.linspace(0, 1, 24)[:, None]
        pts = (1 - tt) ** 2 * p + 2 * (1 - tt) * tt * ctrl + tt ** 2 * q
        cv.line(dax, pts[:, 0], pts[:, 1], width=1)
    for p in tiled:
        if -3 <= p[0] <= c.L + 3:
            for sh in (-c.L, 0, c.L):
                x, y = (p[0] + sh) / cv.res, (p[1] - cv.zlo) / cv.res
                dso.ellipse([x - 1, y - 1, x + 1, y + 1], fill=255)
    d_ax = cv.sample(cv.edt(ax))
    d_so = cv.sample(cv.edt(soma))
    ridge = np.maximum(1 - sm(0.55, 0.95, d_ax), 1 - sm(1.9, 2.4, d_so))
    dnet = np.minimum(d_ax - 0.75, d_so - 2.1)
    dots = _lattice_dist(c.S2, c.Z2, c.L / 46)
    bump = 1 - sm(0.45, 0.95, dots)
    moat = sm(0.9, 1.9, dnet)
    bg = (0.26 + 0.26 * bump) * (0.25 + 0.75 * moat)
    t = np.maximum(bg, ridge)
    red = np.clip(ridge * 1.5, 0, 1)
    rgb = lerp((22, 22, 24), (44, 44, 48), bump * (1 - red))
    rgb = lerp(rgb, (206, 24, 32), red)
    cls = (red > 0.5).astype(np.uint8)
    return dict(t=t, rgb=rgb, cls=cls, collar=0, palette=[(24, 24, 26), (206, 24, 32)])


# ---------------------------------------------------------------------------------
# 06  CARBON MATRIX - 2/2 twill weave with smooth reinforcement patches
# ---------------------------------------------------------------------------------
def carbon(c):
    p = c.L / 60
    zz = c.Z2 - c.z0
    i, j = np.floor(c.S2 / p).astype(int), np.floor(zz / p).astype(int)
    fx, fy = c.S2 / p - i, zz / p - j
    warp_over = ((i + j) % 4) < 2
    crown = np.where(warp_over, 4 * fx * (1 - fx), 4 * fy * (1 - fy))
    crown = np.sqrt(np.clip(crown, 0, 1))
    tw = np.where(warp_over, 0.60, 0.53) + 0.13 * crown - 0.10 * (1 - np.where(warp_over, np.minimum(4 * fy * (1 - fy) * 3, 1), np.minimum(4 * fx * (1 - fx) * 3, 1)))
    # reinforcement patches: thresholded smooth periodic noise
    terms = [(2, 61, 0.0, 1.0), (3, -37, 1.7, 0.9), (5, 46, 3.1, 0.7), (4, -29, 5.0, 0.6), (1, -80, 2.2, 0.8)]
    q = sum(a * np.sin(2 * np.pi * (k * c.S2 / c.L + zz / lam) + ph) for k, lam, ph, a in terms)
    q = q / sum(a for *_, a in terms)
    mp = sm(0.18, 0.30, q)
    patch_t = 0.94 + 0.05 * np.clip(q, 0, 1)
    t = tw * (1 - mp) + patch_t * mp
    wv = np.where(warp_over, 34, 22) + 10 * crown
    rgb = lerp(np.stack([wv, wv, wv + 4], -1), (128, 132, 138), mp)
    cls = (mp > 0.5).astype(np.uint8)
    return dict(t=t, rgb=rgb, cls=cls, collar=0, palette=[(28, 28, 32), (128, 132, 138)])


# ---------------------------------------------------------------------------------
# 07  VORONOI-CORE - Voronoi lattice of ribs, cells punched through for airflow
# ---------------------------------------------------------------------------------
def _cells(sites, L, zlo, zhi):
    pts = []
    for sh in (-L, 0.0, L):
        for s, z in sites:
            pts += [(s + sh, z), (s + sh, 2 * zlo - z), (s + sh, 2 * zhi - z)]
    vd = voronoi_diagram(MultiPoint(pts), envelope=box(-2 * L, zlo - 90, 3 * L, zhi + 90))
    polys = list(vd.geoms)
    out = []
    for s, z in sites:
        pt = Point(s, z)
        out.append(next(pg for pg in polys if pg.contains(pt)))
    return out


def voronoi(c):
    rng = np.random.default_rng(5)
    zlo, zhi = 27.5, 103.5
    nS, nZ = 9, 6
    sites = []
    for j in range(nZ):
        for i in range(nS):
            s = (i + 0.5 * (j % 2) + rng.uniform(-.35, .35)) * c.L / nS
            z = zlo + (j + .5 + rng.uniform(-.3, .3)) * (zhi - zlo) / nZ
            sites.append((s % c.L, z))
    for _ in range(3):                                   # Lloyd relaxation (keeps some irregularity)
        cells = _cells(sites, c.L, zlo, zhi)
        sites = [((cl.centroid.x) % c.L, cl.centroid.y) for cl in cells]
    cells = _cells(sites, c.L, zlo, zhi)
    hw, r = 1.3, 1.0
    wins = []
    for cl in cells:
        w = cl.buffer(-(hw + r)).buffer(r, 16)
        if not w.is_empty and w.area > 8:
            wins.append(w.simplify(0.02))
    cv = Canvas(c, 0.1)
    img = cv.image()
    dr = ImageDraw.Draw(img)
    for w in wins:
        x, y = w.exterior.xy
        cv.polygon(dr, x, y)
    d = cv.sample(cv.edt(img))
    t = 0.55 + 0.45 * sm(0.0, 1.35, d)
    rgb = lerp((104, 52, 190), (150, 96, 236), sm(0.55, 1.0, t))
    cls = np.zeros(t.shape, np.uint8)
    return dict(t=t, rgb=rgb, holes=wins, cls=cls, collar=0, palette=[(138, 84, 228)])


# ---------------------------------------------------------------------------------
# 08  TOPO-FLOW - wood-grain / topographic contour ridges around knots
# ---------------------------------------------------------------------------------
def topo(c):
    S, Z, L = c.S2, c.Z2, c.L
    hills = [(0.14, 46, 13, 15, 0.85), (0.52, 78, 17, 19, 1.0), (0.84, 42, 11, 13, 0.75), (0.33, 98, 10, 11, 0.55)]
    H = 0.030 * Z
    for fs, zc, a, b, amp in hills:
        H = H + amp * 0.9 * np.exp(-((pdiff(S, fs * L, L) / a) ** 2 + ((Z - zc) / b) ** 2))
    H = H + 0.05 * np.sin(2 * np.pi * (3 * S / L) + 0.04 * Z + 0.6)
    dH = 0.20
    ph = 2 * np.pi * H / dH
    cr = 0.5 + 0.5 * np.cos(ph)
    t = 0.40 + 0.60 * cr ** 2.3
    grain = 0.5 + 0.5 * np.sin(2 * np.pi * (S / L * 47) + 3.0 * np.sin(2 * np.pi * Z / 37))
    rgb = lerp((214, 172, 128), (120, 72, 40), sm(0.35, 0.95, t))
    rgb = rgb * (0.94 + 0.06 * grain)[..., None]
    cls = np.digitize(t, [0.55, 0.80]).astype(np.uint8)
    return dict(t=t, rgb=rgb, cls=cls, collar=1, palette=[(214, 172, 128), (168, 116, 78), (120, 72, 40)])


# ---------------------------------------------------------------------------------
# 09  ERGO-CONTOUR - smooth anatomical swell, finger flutes and thumb rest
# ---------------------------------------------------------------------------------
def ergo(c):
    S, Z, L = c.S2, c.Z2, c.L
    Sp = 0.0                                             # palm face (back)
    Sf = 0.50 * L                                        # finger face (toward the default camera)
    base = 0.82 + 0.18 * np.cos(2 * np.pi * (Z - c.z0) / c.hz)          # hour-glass swell
    t = base + 0.16 * gauss(pdiff(S, Sp, L), 0.16 * L) * gauss(Z - 60, 24)   # palm pad
    flutes = sum(gauss(Z - zk, 3.9) for zk in (44, 58, 72, 86))               # four finger flutes
    t = t - 0.55 * gauss(pdiff(S, Sf, L), 0.15 * L) * flutes
    t = t - 0.45 * gauss(pdiff(S, (Sf + 0.20 * L) % L, L), 6.0) * gauss(Z - 97, 8.0)   # thumb dish
    t = np.clip(t, 0.12, 1.0)
    rgb = np.broadcast_to(np.array([66., 66., 72.]), t.shape + (3,)).copy()
    cls = np.zeros(t.shape, np.uint8)
    return dict(t=t, rgb=rgb, cls=cls, collar=0, palette=[(66, 66, 72)])


# ---------------------------------------------------------------------------------
# 10  HEXA-MOD - modular hex pads with level-coded heights
# ---------------------------------------------------------------------------------
def hexa(c):
    rng = np.random.default_rng(17)
    nx = 12
    W = c.L / nx
    R = W / np.sqrt(3)
    rowp = 1.5 * R
    nrows = int(np.round(c.hz / rowp))
    S, zz = c.S2, np.clip(c.Z2 - c.z0, 0, c.hz)
    # nearest pointy-top hex centre (cube rounding)
    qf = (np.sqrt(3) / 3 * S - zz / 3) / R
    rf = (2 / 3 * zz) / R
    xf, zf = qf, rf
    yf = -xf - zf
    rx, ry, rz = np.round(xf), np.round(yf), np.round(zf)
    dxs, dys, dzs = np.abs(rx - xf), np.abs(ry - yf), np.abs(rz - zf)
    fix_x = (dxs > dys) & (dxs > dzs)
    fix_y = ~fix_x & (dys > dzs)
    rx = np.where(fix_x, -ry - rz, rx)
    rz = np.where(~fix_x & ~fix_y, -rx - ry, rz)
    cx = R * np.sqrt(3) * (rx + rz / 2)
    cz = R * 1.5 * rz
    dx, dz = S - cx, zz - cz
    dx = (dx + c.L / 2) % c.L - c.L / 2
    a = W / 2
    nrm = np.maximum.reduce([np.abs(dx), np.abs(0.5 * dx + 0.8660254 * dz), np.abs(-0.5 * dx + 0.8660254 * dz)])
    dedge = a - nrm
    col = (np.round(cx / W - 0.5 * (rz % 2)).astype(int)) % nx
    row = rz.astype(int)
    h = rng.random((nrows + 6, nx))
    hv = h[np.clip(row + 1, 0, nrows + 5), col]
    zc = cz / c.hz
    env = 0.5 + 0.5 * np.sin(2 * np.pi * (1.2 * zc) + 1.4 * np.sin(2 * np.pi * col / nx * 2))
    val = 0.5 * env + 0.5 * hv
    level = np.digitize(val, [0.34, 0.58, 0.80])
    lv = np.array([0.50, 0.68, 0.84, 1.0])[level]
    gap = 0.85
    t = np.where(dedge < gap, 0.0, lv * sm(gap, gap + 0.8, dedge))
    palette = np.array([[70, 74, 78.], [116, 120, 126.], [176, 180, 186.], [214, 58, 40.]])
    rgb = palette[level] * (0.8 + 0.2 * sm(gap, gap + .9, dedge))[..., None]
    rgb = np.where((dedge < gap)[..., None], np.array([28, 28, 30.]), rgb)
    cls = np.where(dedge < gap, 0, level + 1).astype(np.uint8)
    return dict(t=t, rgb=rgb, cls=cls, collar=2, palette=[(28, 28, 30), (70, 74, 78), (116, 120, 126), (176, 180, 186), (214, 58, 40)])


DESIGNS = [
    ("01_vortex_grip", "VORTEX GRIP", vortex),
    ("02_cellular_mod", "CELLULAR MOD", cellular),
    ("03_tessel_block", "TESSEL-BLOCK", tessel),
    ("04_logic_grip", "LOGIC-GRIP", logic),
    ("05_neuro_tread", "NEURO-TREAD", neuro),
    ("06_carbon_matrix", "CARBON MATRIX", carbon),
    ("07_voronoi_core", "VORONOI-CORE", voronoi),
    ("08_topo_flow", "TOPO-FLOW", topo),
    ("09_ergo_contour", "ERGO-CONTOUR", ergo),
    ("10_hexa_mod", "HEXA-MOD", hexa),
]
