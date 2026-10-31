"""Great hammerhead shark (Sphyrna mokarran) -- sculpture definition.

Proportions follow the species' morphometrics (as fractions of total length
TL = 240 mm): head width ~0.25 TL, tall falcate first dorsal ~0.18 TL,
five gill slits ending over the pectoral origin, heterocercal caudal fin with
a subterminal notch, deeply notched anal fin, long free rear tip on the
second dorsal, and a precaudal pit.

Two styles share the same anatomy:
    "pure"  the animal itself
    "f1"    the same shark carrying Formula 1 cues taken from the reference
            models: cockpit, halo, driver helmet, airbox + T-cam on the back,
            carbon front-wing endplates and a slotted flap under the
            cephalofoil.

Units: millimetres.  +X forward (snout at X=240), +Y left, +Z up, body axis
at Z=0.  The model is built straight and symmetric; the swimming curve is
applied afterwards (see build.py).
"""
from __future__ import annotations

import math

import numpy as np

from sdf import Ellipsoid, Fin, Groove, Loft, Program, RoundBox, Tube

# ---------------------------------------------------------------- paint ids
SKIN, FIN, HEAD, EYE, PUPIL, GILL, MOUTH, TEETH, CARBON, HALO, HELMET, VISOR, INTAKE, ACCENT, NOSTRIL, VFIN = range(1, 17)
SKIN_LABELS = (SKIN, FIN, HEAD, VFIN)   # countershaded skin (VFIN = ventral fins)

TL = 240.0                     # total length
GRID_LO = (-1.5, 0.0, -27.0)   # SDF sampling box (Y >= 0 half, mirrored)
GRID_HI = (241.5, 39.0, 62.0)

XZ = ((0, 0, 0), (1, 0, 0), (0, 0, 1))  # plate in XZ, thickness along Y


# ------------------------------------------------------------------ curves
def bezier(p0, p1, p2, p3, n=16, endpoint=False):
    t = np.linspace(0.0, 1.0, n, endpoint=endpoint)[:, None]
    p0, p1, p2, p3 = (np.asarray(p, float) for p in (p0, p1, p2, p3))
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t * t * p2 + t**3 * p3


def catmull_rom(pts, n=6, closed=False):
    P = np.asarray(pts, float)
    P = np.vstack([P[-1], P, P[0], P[1]]) if closed else np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0.0, 1.0, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed:
        out.append(P[-2])
    return np.array(out)


def mirror_closed(half):
    """Close a half outline drawn on +Y (from y=0 to y=0) with its mirror."""
    half = np.asarray(half, float)
    other = half[-2:0:-1].copy()
    other[:, 1] *= -1
    return np.vstack([half, other])


def fin_frame(A, B, T):
    """Frame for a fin from root leading edge A, root trailing edge B, tip T.

    Returns (frame, uT, vT, root_len) with U along the root chord and V
    towards the tip.
    """
    A, B, T = (np.asarray(p, float) for p in (A, B, T))
    U = (B - A) / np.linalg.norm(B - A)
    V = (T - A) - np.dot(T - A, U) * U
    V /= np.linalg.norm(V)
    return (A, U, V), float(np.dot(T - A, U)), float(np.dot(T - A, V)), float(np.linalg.norm(B - A))


# ================================================================== body
def body():
    """Head bulb -> trunk -> caudal peduncle, rising into the upper lobe."""
    K = [
        #  x      a     zc    bt    bb    nt   nb
        (38.0, 1.8, 10.6, 2.4, 2.0, 2.1, 2.1),
        (48.0, 2.4, 6.4, 3.0, 2.5, 2.1, 2.1),
        (60.0, 3.1, 3.0, 3.8, 3.2, 2.1, 2.1),
        (70.0, 3.8, 1.4, 4.6, 4.0, 2.1, 2.1),
        (76.0, 4.4, 1.0, 5.3, 4.6, 2.1, 2.2),
        (86.0, 5.7, 0.9, 6.9, 6.0, 2.1, 2.2),
        (98.0, 7.4, 0.9, 9.1, 7.8, 2.1, 2.2),
        (112.0, 9.2, 1.0, 11.8, 10.0, 2.1, 2.2),
        (126.0, 10.9, 1.2, 14.6, 12.0, 2.1, 2.3),
        (140.0, 12.4, 1.4, 16.6, 13.2, 2.1, 2.3),
        (152.0, 13.3, 1.5, 17.6, 13.6, 2.1, 2.3),
        (164.0, 13.8, 1.6, 17.6, 13.6, 2.1, 2.4),
        (176.0, 13.8, 1.6, 16.4, 12.8, 2.1, 2.5),
        (186.0, 13.5, 1.4, 14.8, 11.6, 2.1, 2.5),
        (196.0, 12.9, 1.2, 12.4, 9.8, 2.1, 2.6),
        (206.0, 11.9, 1.0, 10.0, 8.0, 2.1, 2.6),
        (214.0, 10.6, 0.8, 7.8, 6.2, 2.1, 2.6),
        (222.0, 8.8, 0.6, 5.6, 4.6, 2.1, 2.5),
        (230.0, 6.6, 0.4, 3.8, 3.3, 2.2, 2.4),
        (237.0, 4.4, 0.2, 2.5, 2.3, 2.2, 2.2),
    ]
    keys = [dict(x=k[0], a=k[1], zc=k[2], bt=k[3], bb=k[4], nt=k[5], nb=k[6]) for k in K]
    return Loft(keys, label=SKIN, cap0=6.0, cap1=3.0)


def surface_y(loft, x, z):
    """Outer (+Y) surface of a loft at station x, height z."""
    a, zc, bt, bb, ys, nt, nb = loft.params(np.atleast_1d(float(x)))[0]
    b, n = (bt, nt) if z >= zc else (bb, nb)
    w = min(abs(z - zc) / b, 1.0)
    return ys + a * (1.0 - w**n) ** (1.0 / n)


def surface_z(loft, x, y, top=False):
    a, zc, bt, bb, ys, nt, nb = loft.params(np.atleast_1d(float(x)))[0]
    u = min(abs(abs(y) - ys) / a, 1.0)
    b, n = (bt, nt) if top else (bb, nb)
    s = (1.0 - u**n) ** (1.0 / n)
    return zc + b * s if top else zc - b * s


# ----------------------------------------------------------- cephalofoil
HEAD_LE = np.array([(0.0, 239.0), (1.6, 239.9), (4.0, 240.3), (10.0, 240.2), (16.0, 239.6),
                    (21.0, 238.7), (25.0, 237.5), (27.8, 236.2)])
HEAD_TIP = np.array([(29.6, 234.6), (30.6, 232.6), (30.7, 230.6), (30.0, 229.2), (28.6, 228.8)])
HEAD_TE = np.array([(26.0, 229.0), (22.0, 228.0), (18.2, 226.6), (14.6, 224.2), (12.0, 221.0),
                    (10.4, 217.4), (9.4, 213.8), (0.0, 210.0)])
HEAD_DROOP = 1.6   # tips sit lower than the centre (front view arch)


def head_mid_z(y):
    return -HEAD_DROOP * (np.clip(np.abs(y), 0, 30.6) / 30.6) ** 2


def cephalofoil(style):
    half = np.vstack([HEAD_LE, HEAD_TIP, HEAD_TE])[:, ::-1]  # -> (x, y)
    outline = catmull_rom(mirror_closed(half), n=5, closed=True)
    le_y, le_x = HEAD_LE[:, 0], HEAD_LE[:, 1]
    te_y, te_x = HEAD_TE[::-1, 0], HEAD_TE[::-1, 1]
    camber = -0.45 if style == "f1" else 0.35   # f1: inverted wing section

    def core(u, v):
        return 2.25 - 0.95 * np.clip(np.abs(v) / 30.6, 0, 1) ** 1.2

    def offset(u, v):
        av = np.abs(v)
        xle = np.interp(av, le_y, le_x)
        xte = np.interp(av, te_y, te_x)
        s = np.clip((xle - u) / np.maximum(xle - xte, 1e-3), 0.0, 1.0)
        fade = np.clip((av - 9.0) / 6.0, 0.0, 1.0)      # no camber where the head meets the body
        return head_mid_z(v) + camber * fade * np.sin(math.pi * s)

    return Fin(outline, ((0, 0, 0), (1, 0, 0), (0, 1, 0)), h_edge=0.7, h_core=2.25, ramp=4.0,
               core=core, offset=offset, label=HEAD, offset_max=2.2)


# ------------------------------------------------------------------ fins
def first_dorsal():
    le = bezier((179.5, 17.0), (174.5, 35.0), (164.0, 51.5), (148.6, 60.2), n=22)
    apex = [(147.2, 60.1), (146.9, 59.2)]
    te = bezier((147.6, 58.0), (153.8, 46.5), (155.8, 31.5), (146.4, 21.6), n=22)
    rest = [(145.2, 20.8), (146.0, 18.4), (152.0, 13.0), (168.0, 10.0), (182.0, 9.0)]
    outline = np.vstack([le, apex, te, rest])

    def core(u, v):
        return 2.4 - 1.4 * np.clip((v - 16.0) / 42.0, 0, 1)

    return Fin(outline, XZ, h_edge=0.55, h_core=2.4, ramp=4.0, core=core, label=FIN)


def second_dorsal():
    le = bezier((103.0, 8.6), (101.6, 12.5), (99.6, 16.0), (97.2, 18.6), n=10)
    te = bezier((96.8, 16.4), (97.8, 12.8), (94.4, 10.6), (88.0, 9.4), n=12)
    outline = np.vstack([[(106.0, 5.0)], le, [(96.4, 18.5), (96.2, 17.6)], te,
                         [(87.4, 8.7), (90.0, 6.0), (100.0, 4.5)]])

    def core(u, v):
        return 1.4 - 0.6 * np.clip((v - 9.0) / 9.0, 0, 1)

    return Fin(outline, XZ, h_edge=0.45, h_core=1.4, ramp=2.5, core=core, label=FIN)


def anal_fin():
    le = bezier((103.2, -5.0), (101.5, -9.0), (99.5, -12.5), (97.0, -15.2), n=10)
    te = bezier((96.4, -13.4), (97.6, -10.6), (95.0, -8.6), (89.5, -7.6), n=12)
    outline = np.vstack([[(107.0, -2.5)], le, [(96.2, -15.2), (95.9, -14.3)], te,
                         [(88.8, -7.0), (91.0, -4.0), (100.0, -2.0)]])

    def core(u, v):
        return 1.3 - 0.5 * np.clip((-6.0 - v) / 9.0, 0, 1)

    return Fin(outline, XZ, h_edge=0.45, h_core=1.3, ramp=2.5, core=core, label=VFIN)


def caudal_fin():
    upper = bezier((70.0, 5.2), (50.0, 11.0), (27.0, 22.5), (6.5, 36.0), n=24)
    tip = [(4.0, 37.6), (2.8, 37.5), (2.7, 36.3), (4.0, 34.4)]
    term = [(8.0, 30.6), (10.6, 29.4), (11.0, 27.0)]          # terminal lobe + subterminal notch
    post = bezier((11.8, 25.8), (20.0, 16.0), (26.5, 7.0), (31.0, 1.4), n=18)
    lo_post = bezier((31.0, 1.4), (30.0, -7.0), (30.4, -15.5), (33.6, -24.6), n=12)
    lo_tip = [(34.6, -25.8), (35.9, -25.7)]
    lo_ant = bezier((36.8, -24.8), (44.0, -15.0), (54.0, -7.0), (66.0, -3.6), n=14)
    outline = np.vstack([upper, tip, term, post, lo_post, lo_tip, lo_ant, [(74.0, -2.0), (74.0, 4.0)]])

    def core(u, v):
        return 2.0 - 1.2 * np.clip((70.0 - u) / 50.0, 0, 1)

    return Fin(outline, XZ, h_edge=0.45, h_core=2.0, ramp=3.5, core=core, label=FIN)


def pectoral_fin():
    frame, uT, vT, Lr = fin_frame((190.5, 8.4, -6.8), (172.0, 7.6, -8.8), (164.5, 37.5, -17.0))
    le = bezier((0, 0), (0.15 * uT, 0.42 * vT), (0.5 * uT, 0.82 * vT), (uT, vT), n=20)
    tip = [(uT + 0.7, vT - 0.2), (uT + 0.6, vT - 1.0)]
    te = bezier((uT + 0.3, vT - 1.6), (0.8 * uT, 0.62 * vT), (0.72 * uT + 0.2 * Lr, 0.26 * vT),
                (Lr + 1.5, 2.2), n=20)
    outline = np.vstack([[(0, -2.5)], le, tip, te, [(Lr + 1.2, 1.2), (Lr - 1.0, -2.5)]])

    def core(u, v):
        return 2.4 - 1.5 * np.clip(v / vT, 0, 1)

    def offset(u, v):
        return 0.003 * np.clip(v, 0, None) ** 2

    return Fin(outline, frame, h_edge=0.5, h_core=2.4, ramp=3.5, core=core, offset=offset,
               label=FIN, offset_max=2.8)


def pelvic_fin():
    frame, uT, vT, Lr = fin_frame((122.0, 4.0, -8.2), (114.0, 3.6, -7.6), (107.5, 11.2, -16.0))
    le = bezier((0, 0), (0.2 * uT, 0.45 * vT), (0.55 * uT, 0.85 * vT), (uT, vT), n=12)
    tip = [(uT + 0.5, vT - 0.2), (uT + 0.4, vT - 0.8)]
    te = bezier((uT + 0.2, vT - 1.2), (0.8 * uT, 0.55 * vT), (0.75 * uT, 0.25 * vT), (Lr + 1.0, 1.4), n=12)
    outline = np.vstack([[(0, -2.0)], le, tip, te, [(Lr + 0.8, 0.6), (Lr - 1.0, -2.0)]])

    def core(u, v):
        return 1.5 - 0.8 * np.clip(v / vT, 0, 1)

    return Fin(outline, frame, h_edge=0.45, h_core=1.5, ramp=2.5, core=core, label=VFIN)


# ---------------------------------------------------------- head details
def eyes():
    socket = Ellipsoid((231.8, 29.0, -1.4), (3.6, 2.6, 2.4), label=HEAD)
    ball = Ellipsoid((232.0, 30.3, -1.4), (2.2, 1.5, 2.0), label=EYE)
    pupil = Ellipsoid((232.25, 31.55, -1.35), (1.2, 0.5, 1.3), label=PUPIL)
    return socket, ball, pupil


def nostril():
    """Nostril + prenarial groove along the front margin near the eye."""
    pts = []
    for t in np.linspace(0.0, 1.0, 8):
        y = 22.6 + 3.8 * t
        x = float(np.interp(y, HEAD_LE[:, 0], HEAD_LE[:, 1])) + 0.05   # on the front margin
        pts.append((x, y, float(head_mid_z(y))))
    return Tube(pts, np.linspace(0.3, 0.45, 8), label=NOSTRIL)


def mouth(bodyloft):
    """Crescent mouth under the head with a row of upper teeth."""
    arc = []
    for t in np.linspace(0.0, 1.0, 14):
        y = 9.0 * t
        x = 225.2 - 7.8 * t**1.8
        arc.append((x, y, surface_z(bodyloft, x, y) + 0.15))
    cut = Tube(arc, np.linspace(1.1, 0.55, 14), label=MOUTH)
    teeth = []
    for t in np.linspace(0.03, 0.9, 10):
        y = 9.0 * t
        x = 225.2 - 7.8 * t**1.8 + 0.75
        zs = surface_z(bodyloft, x, y)
        teeth.append(Tube([(x + 0.2, y, zs + 0.5), (x - 0.25, y, zs - 1.0)], [0.5, 0.07], label=TEETH))
    return cut, teeth


def gill_slits(bodyloft):
    """Five slightly curved gill slits on the left flank (mirrored)."""
    cutters = []
    for gx, gh in [(203.0, 10.6), (199.0, 11.6), (195.0, 12.4), (191.0, 12.0), (187.0, 11.0)]:
        zc = -0.8
        zs = np.linspace(zc - gh / 2, zc + gh / 2, 10)
        bow = 0.7 * (1.0 - ((zs - zc) / (gh / 2)) ** 2)        # bowed forwards in the middle
        inner, outer = [], []
        for z, b in zip(zs, bow):
            ys = surface_y(bodyloft, gx + b, z)
            inner.append((ys - 2.6, z))
            outer.append((ys + 1.2, z))
        outline = np.vstack([inner, outer[::-1]])

        def offset(u, v, zs=zs, bow=bow):
            return np.interp(v, zs, bow)

        slab = Fin(outline, ((gx, 0.0, 0.0), (0, 1, 0), (0, 0, 1)), h_edge=0.48, h_core=0.48,
                   ramp=1.0, offset=offset, label=GILL, offset_max=1.0, round_edge=0.95)
        cutters.append(Groove(bodyloft, slab, depth=1.6, label=GILL))
    return cutters


def precaudal_pit(bodyloft):
    x = 73.5
    zt = surface_z(bodyloft, x, 0.0, top=True)
    return Tube([(x, 0.0, zt + 0.25), (x - 0.2, 2.6, zt - 0.6)], 0.55, label=SKIN)


# ------------------------------------------------------------- F1 cues
def f1_cockpit():
    """Cockpit cut-out, seated driver, halo and airbox on the shark's back."""
    cut = RoundBox((204.5, 0.0, 10.0), (7.6, 5.0, 3.2), r=2.6, label=CARBON)
    seat = [
        (Ellipsoid((201.0, 0.0, 6.6), (4.2, 5.4, 1.8), label=CARBON), 0.5),       # shoulders
        (RoundBox((199.3, 0.0, 8.4), (2.0, 5.0, 1.6), r=1.0, label=CARBON), 0.6),  # headrest
        (Ellipsoid((202.3, 0.0, 7.9), (2.2, 2.1, 2.2), label=CARBON), 0.3),       # neck
        (Ellipsoid((202.5, 0.0, 9.9), (3.9, 3.2, 3.5), label=HELMET), 0.0),
        (Ellipsoid((204.5, 0.0, 10.3), (2.0, 2.9, 1.15), label=VISOR), 0.25),
    ]
    path = [(213.6, 0.0, 15.2), (213.4, 1.4, 15.25), (212.3, 3.4, 15.3), (210.2, 5.3, 15.3),
            (207.3, 6.6, 15.1), (204.0, 7.3, 14.7), (200.6, 7.5, 13.9), (197.8, 7.5, 12.7),
            (196.0, 7.4, 11.0), (195.2, 7.2, 9.4)]
    p = catmull_rom(path, n=6)
    halo = Tube(p, np.full(len(p), 0.85), label=HALO)
    pillar = Tube(catmull_rom([(213.4, 0, 14.9), (214.8, 0, 12.6), (216.0, 0, 10.4), (217.0, 0, 7.2)], n=4),
                  np.linspace(0.85, 1.05, 13), label=HALO)
    air = Loft([dict(x=180.0, a=2.2, zc=14.4, bt=1.6, bb=4.0), dict(x=185.0, a=3.6, zc=15.6, bt=3.0, bb=5.0),
                dict(x=190.0, a=4.0, zc=16.4, bt=3.2, bb=5.5), dict(x=194.0, a=3.0, zc=16.6, bt=2.4, bb=5.0),
                dict(x=196.0, a=1.6, zc=16.0, bt=1.4, bb=4.0)], label=SKIN, cap0=3.0, cap1=1.8)
    inlet = Ellipsoid((196.4, 0.0, 17.0), (2.4, 2.4, 2.0), label=INTAKE)
    tcam = RoundBox((191.2, 0.0, 19.9), (1.6, 0.8, 0.5), r=0.35, label=ACCENT)
    return cut, seat, halo, pillar, air, inlet, tcam


def f1_front_flap():
    """Slotted carbon flap tucked under the head's rear margin (front-wing cue)."""
    te_y, te_x = HEAD_TE[::-1, 0], HEAD_TE[::-1, 1]
    ys = np.linspace(11.0, 28.0, 14)
    xte = np.interp(ys, te_y, te_x)
    outline = np.vstack([np.stack([xte + 1.6, ys], 1), np.stack([xte - 4.4, ys], 1)[::-1]])
    z0 = float(head_mid_z(20.0)) - 2.6
    pitch = math.tan(math.radians(24.0))

    def offset(u, v):
        xt = np.interp(v, ys, xte) + 1.6
        return (xt - u) * pitch + (head_mid_z(v) - head_mid_z(20.0))

    return Fin(outline, ((0, 0, z0), (1, 0, 0), (0, 1, 0)), h_edge=0.45, h_core=0.6, ramp=1.5,
               offset=offset, label=CARBON, offset_max=3.0)


# ============================================================== programme
def build_program(style="pure"):
    P = Program()
    b = P.add(body())
    P.add(cephalofoil(style), k=3.0)
    socket, ball, pupil = eyes()
    P.add(socket, k=1.2)

    P.add(first_dorsal(), k=4.0)
    P.add(second_dorsal(), k=2.0)
    P.add(anal_fin(), k=2.0)
    P.add(caudal_fin(), k=3.0)
    P.add(pectoral_fin(), k=3.0)
    P.add(pelvic_fin(), k=2.0)

    if style == "f1":
        cut, seat, halo, pillar, air, inlet, tcam = f1_cockpit()
        P.add(air, k=3.0)
        P.add(f1_front_flap(), k=0.5)

    # engraved details
    for g in gill_slits(b):
        P.sub(g, k=0.3)
    mcut, teeth = mouth(b)
    P.sub(mcut, k=0.3)
    P.sub(nostril(), k=0.2)
    P.sub(precaudal_pit(b), k=0.4)
    if style == "f1":
        P.sub(cut, k=1.0)
        P.sub(inlet, k=0.4)
        for node, k in seat:
            P.add(node, k=k)
        P.add(halo, k=0.6)
        P.add(pillar, k=0.6)
        P.add(tcam, k=0.3)

    for t in teeth:
        P.add(t, k=0.0)
    P.add(ball, k=0.5)
    P.add(pupil, k=0.0)
    return P
