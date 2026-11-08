"""Procedural VW Polo 6R/6C-class 5-door hatchback body (implicit surface + marching cubes), built in the
spoiler's coordinates (x lateral, y up, z rearward, mm). Dimensions: L 3970, W 1682, H 1469, WB 2470."""
import numpy as np
from scipy.interpolate import CubicSpline
from skimage import measure
import trimesh

# ---------------- placement relative to the spoiler ----------------
S_ROOF_REAR = 3540.0                 # s (from front bumper) of the roof/tailgate joint (spoiler underside V at z=148)
Z_F = 148.0 - S_ROOF_REAR            # front bumper z
L, WB, W2 = 3970.0, 2470.0, 841.0
S_FA, S_RA = 805.0, 805.0 + WB       # axles
H_TOT = 1469.0
Z_PK = -972.0                        # roof peak z
KR = 1.104e-4                        # roof longitudinal curvature (parabola)
Y_PK = 152.4                         # roof peak y (car surface)
Y_G = Y_PK - H_TOT                   # ground y
KAPPA = 1.12e-4                      # roof crown curvature across x
WHEEL_R, WHEEL_W = 310.0, 195.0
TRACK = 1460.0

def s_of(z): return z - Z_F
def h_of(y): return y - Y_G

def catmull(pts, n=12, closed=True):
    P = np.asarray(pts, float)
    if closed: P = np.vstack([P[-1], P, P[0], P[1]])
    else: P = np.vstack([P[0], P, P[-1]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        t = np.linspace(0, 1, n, endpoint=False)[:, None]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return np.vstack(out)

def poly_sdf(poly, A, B):
    """signed distance (negative inside) to closed polygon poly (N,2) at points (A,B) arrays"""
    P = np.column_stack([A.ravel(), B.ravel()]).astype(np.float64)
    d = np.full(len(P), np.inf); sgn = np.ones(len(P))
    V = np.asarray(poly, float); Vn = np.roll(V, -1, 0)
    for a, b in zip(V, Vn):
        e = b - a; w = P - a
        t = np.clip((w @ e) / (e @ e), 0, 1)
        q = w - t[:, None] * e
        d = np.minimum(d, np.einsum('ij,ij->i', q, q))
        c1 = P[:, 1] >= a[1]; c2 = P[:, 1] < b[1]; c3 = (e[0] * w[:, 1] - e[1] * w[:, 0]) > 0
        flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
        sgn[flip] *= -1
    return (sgn * np.sqrt(d)).reshape(A.shape) * -1.0 * -1.0  # inside negative (see sign convention below)

def smin(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h ** 3 * k / 6.0
def smax(a, b, k): return -smin(-a, -b, k)

# ---------------- 2D profiles ----------------
# lower body side profile (s, h), clockwise/anticlockwise does not matter for poly_sdf
SIDE_LOW = catmull([
    (185, 214), (110, 232), (52, 268), (18, 330), (2, 420), (0, 470), (8, 545), (34, 615), (78, 680), (150, 735), (240, 768),
    (450, 812), (760, 872), (1000, 922), (1170, 958),
    (1400, 972), (1900, 988), (2500, 1004), (3100, 1020), (3500, 1030), (3742, 1030),
    (3796, 1013), (3842, 958), (3880, 872), (3910, 774), (3930, 700), (3946, 652), (3962, 590), (3969, 520), (3966, 452),
    (3950, 380), (3912, 306), (3840, 258), (3720, 232), (3300, 200), (2500, 186), (1000, 186), (400, 202)], n=10)
SIDE_CAB = catmull([
    (1110, 880), (1150, 940), (1176, 962), (1420, 1124), (1660, 1286), (1880, 1438), (1890, 1640), (3560, 1640),
    (3585, 1420), (3612, 1354), (3672, 1250), (3735, 1132), (3798, 1012), (3814, 880)], n=10)
PLAN_LOW = catmull([
    (0, 0), (240, 7), (430, 26), (560, 60), (650, 110), (715, 178), (762, 262), (796, 370), (818, 520), (832, 760),
    (839, 1150), (841, 1800), (841, 2700), (838, 3100), (832, 3400), (820, 3640), (798, 3800), (758, 3900), (680, 3948),
    (520, 3963), (300, 3969), (0, 3971),
    (-300, 3969), (-520, 3963), (-680, 3948), (-758, 3900), (-798, 3800), (-820, 3640), (-832, 3400), (-838, 3100),
    (-841, 2700), (-841, 1800), (-839, 1150), (-832, 760), (-818, 520), (-796, 370), (-762, 262), (-715, 178), (-650, 110),
    (-560, 60), (-430, 26), (-240, 7)], n=10)
PLAN_CAB = catmull([
    (0, 1065), (400, 1090), (650, 1160), (762, 1320), (806, 1540), (815, 2000), (815, 2900), (810, 3200), (800, 3420),
    (776, 3600), (716, 3790), (540, 3836), (0, 3850),
    (-540, 3836), (-716, 3790), (-776, 3600), (-800, 3420), (-810, 3200), (-815, 2900), (-815, 2000), (-806, 1540),
    (-762, 1320), (-650, 1160), (-400, 1090)], n=10)

def grid2d_sdf(poly, a0, a1, da, b0, b1, db):
    A = np.arange(a0, a1 + 1e-9, da); B = np.arange(b0, b1 + 1e-9, db)
    AA, BB = np.meshgrid(A, B, indexing='ij')
    return A, B, poly_sdf(poly, AA, BB)

def bilinear(A, B, G, a, b):
    ia = np.clip((a - A[0]) / (A[1] - A[0]), 0, len(A) - 1.000001); ib = np.clip((b - B[0]) / (B[1] - B[0]), 0, len(B) - 1.000001)
    i0 = np.floor(ia).astype(np.int64); j0 = np.floor(ib).astype(np.int64); fa = ia - i0; fb = ib - j0
    return (G[i0, j0] * (1 - fa) * (1 - fb) + G[i0 + 1, j0] * fa * (1 - fb) + G[i0, j0 + 1] * (1 - fa) * fb + G[i0 + 1, j0 + 1] * fa * fb)

_HP = np.load('v6/car/data/hump_profile.npz')   # v6 spoiler underside centre-line (|x|<120) minus the 1.5 mm tape gap
def roof_center_y(z):
    """roof centre-line height: parabola in front of the spoiler, measured spoiler underside (-1.5 mm) under it"""
    y = Y_PK - KR * (z - Z_PK) ** 2
    zp, yp = _HP['z'], _HP['y']
    ym = np.interp(z, zp, yp)
    w = np.clip((z - 60.0) / 40.0, 0, 1); w = w * w * (3 - 2 * w)           # blend parabola -> measured over z 60..100
    out = (1 - w) * y + w * ym
    return np.where(z > zp[-1], yp[-1] + (z - zp[-1]) * 0.3, out)

SEC_H = np.array([186, 205, 235, 270, 330, 450, 600, 760, 880, 930, 940, 955, 985, 1010, 1045])   # heights relative to crease 935
SEC_X = np.array([786, 806, 818, 826, 832, 838, 841, 841, 840, 839, 838.2, 831.5, 815, 801, 788])
def crease_h(s): return np.interp(s, [0, 700, 1500, 3300, 3970], [800, 905, 935, 955, 960])
def tumble_low(h, s=None):
    hc = 935.0 if s is None else crease_h(s)
    hr = np.where(h > 760, h - (hc - 935.0), h)          # shift the upper section with the crease line
    return np.interp(hr, SEC_H, SEC_X) / 841.0
def tumble_cab(h, s):
    t = np.interp(s, [0, 3100, 3400, 3650, 4000], [0.36, 0.36, 0.72, 0.74, 0.74])
    return 1.0 - t * np.maximum(h - 985.0, 0) / 815.0
def body_field(X, Yv, Zv, prof):
    """implicit (negative inside) on broadcast arrays X (nx,1,1), Y (1,ny,1), Z (1,1,nz)"""
    s = s_of(Zv); h = h_of(Yv)
    (Al, Bl, Gl), (Ac, Bc, Gc), (Apl, Bpl, Gpl), (Apc, Bpc, Gpc) = prof
    shape = np.broadcast_shapes(X.shape, Yv.shape, Zv.shape)
    Xa = np.broadcast_to(np.abs(X), shape); Ha = np.broadcast_to(h, shape); Sa = np.broadcast_to(s, shape)
    # lower body
    side_l = bilinear(Al, Bl, Gl, Sa, Ha)
    plan_l = bilinear(Apl, Bpl, Gpl, Xa / tumble_low(Ha, Sa), Sa)
    low = smax(side_l, plan_l, 30.0)
    # cabin
    s_wrap = Sa + 0.00022 * Xa ** 2 * np.where(Sa < 2500, -1.0, 1.0)   # wrap windshield (sides further back) / rear glass
    side_c = bilinear(Ac, Bc, Gc, s_wrap, Ha)
    plan_c = bilinear(Apc, Bpc, Gpc, Xa / tumble_cab(Ha, Sa), Sa)
    yr = roof_center_y(np.broadcast_to(Zv, shape)) - KAPPA * Xa ** 2
    roof = (np.broadcast_to(Yv, shape) - yr) / np.sqrt(1 + (2 * KAPPA * Xa) ** 2)
    cab = smax(smax(plan_c, roof, 105.0), side_c, 45.0)
    body = smin(low, cab, 14.0)
    # wheel arches (outer part only)
    for sa in (S_FA, S_RA):
        dc = np.sqrt((Sa - sa) ** 2 + (Ha - WHEEL_R) ** 2) - 368.0
        cut = smax(dc, 590.0 - Xa, 10.0)
        body = smax(body, -cut, 8.0)
    return body

def build_profiles():
    return (grid2d_sdf(SIDE_LOW, -30, 4000, 4.0, 150, 1100, 4.0),
            grid2d_sdf(SIDE_CAB, 1050, 3900, 4.0, 850, 1700, 4.0),
            grid2d_sdf(PLAN_LOW, 0, 900, 4.0, -30, 4000, 4.0),
            grid2d_sdf(PLAN_CAB, 0, 900, 4.0, 1000, 3900, 4.0))

def build_mesh(step=5.0, out=None):
    prof = build_profiles()
    xs = np.arange(0.0, 880.0 + 1e-9, step)
    ys = np.arange(Y_G - 5.0, Y_PK + 30.0, step)
    zs = np.arange(Z_F - 30.0, Z_F + L + 30.0, step)
    F = np.empty((len(xs), len(ys), len(zs)), np.float32)
    ch = 40
    for k in range(0, len(zs), ch):
        zz = zs[k:k + ch]
        F[:, :, k:k + ch] = body_field(xs[:, None, None], ys[None, :, None], zz[None, None, :], prof)
    # close the domain at x=0 by mirroring one slice
    Ff = np.concatenate([F[1:][::-1], F], axis=0)
    xf = np.concatenate([-xs[1:][::-1], xs])
    v, f, n, _ = measure.marching_cubes(Ff, level=0.0, spacing=(step, step, step))
    v[:, 0] += xf[0]; v[:, 1] += ys[0]; v[:, 2] += zs[0]
    m = trimesh.Trimesh(v, f[:, ::-1], process=True)
    if m.volume < 0: m.invert()
    if out: m.export(out)
    return m

if __name__ == '__main__':
    import sys, time
    t = time.time()
    m = build_mesh(step=float(sys.argv[1]) if len(sys.argv) > 1 else 8.0, out='v6/car/out/car_body.stl')
    print('faces', len(m.faces), 'watertight', m.is_watertight, 'bounds', m.bounds.round(1).tolist(), 'time %.1fs' % (time.time() - t))
    print('size L x W x H:', (m.bounds[1] - m.bounds[0])[[2, 0, 1]].round(1), ' ground y', Y_G)
