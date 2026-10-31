"""The MANTA top shell: one design language, packaged for LMDh and LMH.

Design coordinates (millimetres)
--------------------------------
* x: longitudinal, positive rearward, 0 at the front axle centre line
* y: lateral, positive to the right, 0 on the car centre plane
* z: vertical, positive up, 0 on the reference plane (flat underside of the car)

The shell is described as

1. a *crown* height field ``H(x, y)`` sculpted from smooth primitives that
   map to manta-ray anatomy (see DESIGN.md):

   - ``deck``      : the broad, slightly drooping pectoral "wing" surface
   - ``fuselage``  : the dorsal body hump (nose -> canopy -> engine cover)
   - ``front fender`` ridges, whose forward ends narrow into the two
     cephalic-fin "horns" that frame the mouth intake
   - ``rear fender`` ridges, which sweep up into the wing-tip endplates

2. a plan-view *outline* (where the crown stops) with, at every point, the
   shoulder radius, wall undercut and lower edge height of the *skirt* that
   rolls the crown down to the parting line,

3. plan-view cut-outs (the five gill-slit louvres over each front wheel) and
   material regions (windscreen, side glass),

4. appendages: dorsal fin + tail, crescent rear wing, endplates, mirrors.

Everything is authored once in a *reference frame* sized for LMDh
(5100 x 2000 x 1060 mm, wheelbase 3148 mm) and mapped into each class
envelope by :meth:`Variant.mx` (longitudinal stations) and :meth:`Variant.mz`
(heights above 800 mm).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .curves import catmull_rom, pchip, smoothstep
from .regs import CLASSES, ClassRules

REF_X_ANCHORS = np.array([-1000.0, 0.0, 3148.0, 4100.0])
REF_Z_LIMIT = 1060.0
Z_STRETCH_START = 800.0


@dataclass(frozen=True)
class Variant:
    rules: ClassRules
    wheelbase: float
    x_front: float  # front-most point of the shell
    x_rear: float  # rear-most point of the shell
    front_track: float = 1650.0  # tyre centre to tyre centre
    rear_track: float = 1610.0
    wheel_z_front: float = 300.0  # wheel centre above reference plane
    wheel_z_rear: float = 290.0

    @property
    def key(self) -> str:
        return self.rules.key

    @property
    def x_rear_axle(self) -> float:
        return self.wheelbase

    @property
    def length(self) -> float:
        return self.x_rear - self.x_front

    def mx(self, x):
        """Map reference-frame stations to this variant (piecewise linear)."""
        x = np.asarray(x, float)
        xb = np.array([self.x_front, 0.0, self.wheelbase, self.x_rear])
        xa = REF_X_ANCHORS
        out = np.interp(x, xa, xb)
        lo = x < xa[0]
        hi = x > xa[-1]
        out = np.where(lo, xb[0] + (x - xa[0]) * (xb[1] - xb[0]) / (xa[1] - xa[0]), out)
        out = np.where(hi, xb[-1] + (x - xa[-1]) * (xb[-1] - xb[-2]) / (xa[-1] - xa[-2]), out)
        return out

    def mz(self, z):
        """Map reference heights: unchanged up to 800 mm, then stretched so the
        reference 1060 mm limit lands on this class's height limit."""
        z = np.asarray(z, float)
        s = (self.rules.max_height - Z_STRETCH_START) / (REF_Z_LIMIT - Z_STRETCH_START)
        return np.where(z <= Z_STRETCH_START, z, Z_STRETCH_START + (z - Z_STRETCH_START) * s)

    @property
    def z_scale_upper(self) -> float:
        return (self.rules.max_height - Z_STRETCH_START) / (REF_Z_LIMIT - Z_STRETCH_START)


VARIANTS = {
    "lmdh": Variant(CLASSES["lmdh"], wheelbase=3148.0, x_front=-1000.0, x_rear=4100.0),
    "lmh": Variant(CLASSES["lmh"], wheelbase=3100.0, x_front=-980.0, x_rear=4020.0),
}


# --------------------------------------------------------------------------
# Reference design data (LMDh-sized frame). Each list is (x, value).
# --------------------------------------------------------------------------

# Dorsal body: centre-line height of nose / canopy / engine cover.
FUS_Z = [(-822, 352), (-700, 378), (-400, 430), (0, 486), (250, 528), (420, 578),
         (600, 664), (900, 812), (1200, 934), (1400, 994), (1600, 1034), (1760, 1050),
         (1950, 1046), (2200, 1014), (2500, 958), (2800, 908), (3148, 860),
         (3500, 814), (3784, 780), (4100, 770)]
# Dorsal body half-width where it meets the deck.
FUS_W = [(-822, 330), (-500, 345), (0, 372), (420, 462), (800, 532), (1200, 566),
         (1700, 556), (2100, 496), (2500, 440), (3148, 386), (3784, 322), (4100, 300)]
# Cross-section exponent: low = rounded, high = flat roof + steep glass.
FUS_N = [(-822, 2.0), (0, 2.1), (420, 2.4), (900, 3.4), (1450, 3.9), (1900, 3.9),
         (2500, 2.8), (3784, 2.3)]

# Pectoral deck (valleys, sidepod tops, rear channels) and its outboard droop.
DECK_Z = [(-1000, 330), (-878, 334), (-600, 375), (-300, 415), (0, 445), (400, 515),
          (700, 578), (1000, 605), (1500, 612), (2000, 612), (2400, 628), (2800, 668),
          (3148, 698), (3500, 718), (3800, 728), (4100, 736)]
DECK_DROOP = [(-1000, 0), (700, 0), (1000, 34), (2300, 34), (2800, 0), (4100, 0)]

# Front fender ridge; its nose end narrows into the cephalic "horn".
FF_Y = [(-1000, 476), (-940, 484), (-860, 504), (-750, 566), (-550, 690), (-300, 790),
        (0, 828), (300, 832), (500, 818), (700, 800), (900, 790)]
FF_Z = [(-1000, 432), (-940, 478), (-860, 522), (-760, 566), (-600, 628), (-450, 686),
        (-200, 752), (0, 772), (200, 768), (400, 735), (550, 662), (650, 604), (760, 560),
        (900, 520)]
FF_WI = [(-1000, 34), (-900, 44), (-750, 96), (-450, 220), (0, 320), (400, 320),
         (700, 280)]
FF_WO = [(-1000, 34), (-900, 46), (-750, 104), (-450, 300), (0, 420), (400, 420),
         (700, 360)]
FF_N = [(-1000, 2.0), (-750, 2.2), (-300, 2.9), (700, 2.9)]

# Rear fender ridge; it rises toward the wing-tip endplates.
RF_Y = [(2300, 720), (2700, 785), (3148, 805), (3600, 830), (3900, 880), (4088, 925)]
RF_Z = [(2200, 590), (2500, 668), (2800, 748), (3148, 795), (3500, 822), (3800, 862),
        (4000, 895), (4088, 915)]
RF_WI = [(2300, 200), (3148, 260), (3800, 230), (4088, 140)]
RF_WO = [(2300, 300), (3148, 400), (3800, 300), (4088, 160)]
RF_N = [(2300, 2.6), (4088, 2.4)]

# Foot easing exponents (bigger = softer, wider fillet into the deck).
FUS_M = 1.6
FF_M = 2.0
RF_M = 2.0

# Plan-view crown outline, right half, from the mouth lip on the centre plane
# round to the tail on the centre plane. Columns:
#   x, y, shoulder radius, wall undercut [deg], lower-edge z, max skirt drop
# (lower-edge z is further raised by the wheel arches, see *_arch_z).
OUTLINE = [
    (-822, 0, 22, 0, 300, 999),      # mouth: upper lip on the centre plane
    (-825, 200, 22, 0, 296, 999),
    (-832, 340, 20, 0, 280, 999),
    (-852, 412, 14, 0, 150, 999),    # lip rolls into the horn's inner face
    (-892, 438, 12, 0, 76, 999),
    (-930, 446, 12, 0, 76, 999),
    (-972, 461, 11, 0, 76, 999),
    (-998, 477, 10, 0, 76, 999),     # cephalic-fin horn tip
    (-990, 497, 10, 0, 76, 999),
    (-958, 511, 11, 0, 76, 999),
    (-905, 534, 12, 0, 76, 999),     # horn root: blade reaches the splitter
    (-850, 568, 14, 0, 70, 92),      # thin pectoral leading edge (light blade)
    (-760, 652, 16, 0, 70, 88),
    (-660, 754, 18, 0, 70, 86),
    (-575, 862, 20, 0, 70, 92),
    (-525, 934, 26, 0, 70, 105),
    (-480, 961, 34, 0, 70, 110),     # front fender front corner (arch starts here)
    (-380, 962, 42, 0, 90, 999),     # front fender side (front arch cut)
    (0, 962, 42, 0, 90, 999),
    (380, 962, 42, 0, 90, 999),
    (432, 961, 41, 0, 70, 150),      # arch flank blends into the overhang lip
    (470, 959, 40, 0, 70, 82),       # thin overhang: wheel-well exit + radiator
    (640, 942, 38, 2, 70, 76),       #   inlet open underneath (manta gill zone)
    (820, 916, 36, 6, 70, 76),
    (900, 906, 35, 9, 70, 130),      # sidepod wall sweeps down from the overhang
    (980, 898, 34, 13, 70, 230),
    (1060, 893, 34, 17, 70, 360),
    (1150, 888, 34, 22, 90, 999),    # sidepod: thin undercut "wing" edge
    (1650, 890, 34, 22, 90, 999),
    (2150, 882, 36, 20, 90, 999),
    (2420, 888, 38, 14, 90, 999),
    (2640, 922, 40, 6, 90, 999),     # coke-bottle flare into the rear fender
    (2800, 954, 42, 0, 90, 999),
    (2950, 962, 42, 0, 90, 999),     # rear fender side (rear arch cut)
    (3400, 962, 42, 0, 90, 999),
    (3720, 962, 40, 0, 330, 999),
    (3880, 960, 34, 0, 560, 999),    # side panel tapers up behind the rear wheel
    (3990, 955, 28, 0, 70, 120),
    (4060, 948, 18, 0, 70, 60),
    (4088, 932, 10, 0, 70, 40),      # pectoral fin tip
    (4082, 912, 8, 0, 0, 30),        # crescent trailing edge (short lip)
    (4040, 850, 6, 0, 0, 26),
    (3962, 740, 6, 0, 0, 24),
    (3882, 600, 6, 0, 0, 24),
    (3822, 450, 6, 0, 0, 24),
    (3782, 300, 6, 0, 0, 24),
    (3758, 150, 6, 0, 0, 24),
    (3750, 0, 6, 0, 0, 24),          # tail on the centre plane
]

# Gill-slit louvres over each front wheel (mandatory wheel-arch openings):
# five slightly curved slots, like the five gill slits of a manta.
GILL_X = [-30.0, 42.0, 114.0, 186.0, 258.0]
GILL_Y = (712.0, 925.0)
GILL_SWEEP = 0.12  # x shift per mm of y (outer end further forward)
GILL_BULGE = 10.0  # mm of arc bow
GILL_HALF_WIDTH = 14.0

# Glazing, expressed in (x, t) with t = y / fuselage half-width.
WINDSCREEN_T = [(470, 0.0), (472, 0.30), (478, 0.62), (492, 0.80), (800, 0.76),
                (1100, 0.64), (1300, 0.55), (1405, 0.47), (1440, 0.30), (1452, 0.0)]
SIDE_WINDOW_T = [(1150, 0.71), (1300, 0.655), (1750, 0.615), (1895, 0.645),
                 (1870, 0.76), (1800, 0.86), (1400, 0.885), (1210, 0.845)]

# Livery: pale "shoulder chevrons" like the markings on a manta's back
# (plan polygon, right side, reference frame) and the cut line that makes the
# cephalic horns contrast-coloured.
CHEVRON = [(560, 650), (700, 846), (1300, 872), (2050, 836), (2330, 780), (1700, 700),
           (1000, 650)]
HORN_CUT_X = -838.0

# Dorsal fin side profile (reference frame).
FIN_TOP = [(1880, 1049), (2300, 1041), (2900, 1024), (3500, 1006), (3800, 998),
           (4000, 991), (4070, 982), (4100, 964)]
FIN_TAIL_LOWER = [(4100, 964), (4040, 944), (3930, 906), (3770, 826)]
FIN_X_ROOT = (1880.0, 3740.0)

# Crescent rear wing (reference frame).
WING_SPAN_HALF = 990.0
WING_LE_X0, WING_LE_SWEEP = 3590.0, 150.0
WING_CHORD0, WING_CHORD_TIP_LOSS = 335.0, 35.0
WING_LE_Z0, WING_LE_RISE = 930.0, 25.0
WING_AOA_DEG = 9.5
WING_CAMBER, WING_CAMBER_POS, WING_THICK = 0.075, 0.42, 0.115
GURNEY_H = 14.0

# Endplate side profile at the wing tips (reference frame), y = +/-994.
ENDPLATE_Y = 994.0
ENDPLATE_HALF_T = 5.0
ENDPLATE_X = (3520.0, 4092.0)
ENDPLATE_TOP = [(3520, 892), (3600, 935), (3690, 994), (3780, 1036), (3880, 1052),
                (4000, 1056), (4072, 1050), (4092, 1022)]

# Mirrors (reference frame): pod centre, half-sizes.
MIRROR_C = (420.0, 712.0, 790.0)
MIRROR_HALF = (96.0, 30.0, 36.0)


class MantaDesign:
    """Evaluates the MANTA shell surfaces for one class variant."""

    def __init__(self, variant: Variant):
        self.v = v = variant
        mx, mz = v.mx, v.mz

        def prof(data, map_z=True):
            xs = mx([d[0] for d in data])
            ys = np.array([d[1] for d in data], float)
            return pchip(xs, mz(ys) if map_z else ys)

        self.zc = prof(FUS_Z)
        self.wf = prof(FUS_W, False)
        self.nf = prof(FUS_N, False)
        self.zd = prof(DECK_Z)
        self.droop = prof(DECK_DROOP, False)
        self.ff_y = prof(FF_Y, False)
        self.ff_z = prof(FF_Z)
        self.ff_wi = prof(FF_WI, False)
        self.ff_wo = prof(FF_WO, False)
        self.ff_n = prof(FF_N, False)
        self.rf_y = prof(RF_Y, False)
        self.rf_z = prof(RF_Z)
        self.rf_wi = prof(RF_WI, False)
        self.rf_wo = prof(RF_WO, False)
        self.rf_n = prof(RF_N, False)
        self.ff_range = (mx(-1020.0), mx(900.0))
        self.rf_range = (mx(2200.0), mx(4120.0))

    # ------------------------------------------------------------------
    # crown height field
    # ------------------------------------------------------------------
    def deck(self, x, y):
        y = np.abs(y)
        return self.zd(x) - self.droop(x) * (y / 1000.0) ** 2

    @staticmethod
    def _eased(t, n, m):
        """Bump profile: 1 at t = 0, 0 with zero slope at t = 1, 0 beyond."""
        return np.clip(1.0 - np.minimum(t, 1.0) ** n, 0.0, 1.0) ** m

    def fuselage(self, x, y, deck=None):
        """Dorsal body (nose / canopy / engine cover) height above the deck."""
        y = np.abs(y)
        d = self.deck(x, y) if deck is None else deck
        t = y / self.wf(x)
        return (self.zc(x) - d) * self._eased(t, self.nf(x), FUS_M)

    def _ridge(self, x, y, deck, yc, wi, wo, n, zt, rng, m):
        """Fender ridge height above the deck (eased into it at both feet)."""
        dy = np.abs(y) - yc(x)
        w = np.where(dy < 0, wi(x), wo(x))
        t = np.abs(dy) / w
        win = smoothstep(rng[0] - 1.0, rng[0] + 40.0, x) * (1 - smoothstep(rng[1] - 150.0, rng[1], x))
        amp = np.maximum(zt(x) - deck, 0.0) * win
        return amp * self._eased(t, n(x), m)

    def H(self, x, y):
        """Crown height: deck plus additively composed, tangent-eased bumps.

        Every bump meets the deck with zero slope, so the composed surface is
        C1 everywhere and the fillets are as soft as the bump exponents make
        them (no tight smooth-max creases).
        """
        x = np.asarray(x, float)
        y = np.abs(np.asarray(y, float))
        d = self.deck(x, y)
        h = d + self.fuselage(x, y, d)
        h = h + self._ridge(x, y, d, self.ff_y, self.ff_wi, self.ff_wo, self.ff_n, self.ff_z,
                            self.ff_range, FF_M)
        h = h + self._ridge(x, y, d, self.rf_y, self.rf_wi, self.rf_wo, self.rf_n, self.rf_z,
                            self.rf_range, RF_M)
        return h

    def grad_H(self, x, y, eps=1.5):
        gx = (self.H(x + eps, y) - self.H(x - eps, y)) / (2 * eps)
        gy = (self.H(x, y + eps) - self.H(x, y - eps)) / (2 * eps)
        return gx, gy

    # ------------------------------------------------------------------
    # plan outline and skirt parameters
    # ------------------------------------------------------------------
    def outline_controls(self):
        o = np.array(OUTLINE, float)
        o[:, 0] = self.v.mx(o[:, 0])
        return o

    def outline_half(self, samples_per_segment=40):
        """Dense crown outline (right half) plus per-sample skirt parameters.

        Each control point fixes the skirt's lower edge either absolutely
        (``max_drop >= 900``: edge at ``zb``) or relative to the crown edge
        (``max_drop < 900``: a lip ``max_drop`` deep). Between control points
        the two modes are blended, so the edge line stays smooth.

        Returns (pts[N,2], params[N,5]) with params = r_s, undercut,
        w (0 = absolute, 1 = relative), A (absolute edge), D (lip depth).
        """
        o = self.outline_controls()
        pts, idx = catmull_rom(o[:, :2], samples_per_segment, closed=False,
                               start_tangent_mirror_y=True, end_tangent_mirror_y=True)
        z0c = self.H(o[:, 0], o[:, 1])
        rel = o[:, 5] < 900.0
        # absolute edges on the outer side walls already include the wheel arches
        side = o[:, 1] > 880.0
        a_abs = np.where(side, np.maximum.reduce([o[:, 4], self.front_arch_z(o[:, 0]),
                                                  self.rear_arch_z(o[:, 0])]), o[:, 4])
        ctrl = np.column_stack([o[:, 2], o[:, 3], rel.astype(float),
                                np.where(rel, z0c - o[:, 5], a_abs),
                                np.where(rel, o[:, 5], z0c - a_abs)])
        params = np.column_stack([np.interp(np.arange(len(pts)), idx, ctrl[:, k])
                                  for k in range(ctrl.shape[1])])
        pts[0, 1] = 0.0
        pts[-1, 1] = 0.0
        return pts, params

    def front_arch_z(self, x):
        """Lower edge of the side wall around the front wheel (arch opening)."""
        return _arch(x, 0.0, half_width=505.0, top=668.0, base=90.0, p=3.2)

    def rear_arch_z(self, x):
        return _arch(x, self.v.x_rear_axle, half_width=470.0, top=540.0, base=90.0, p=3.0)

    # ------------------------------------------------------------------
    # cut-outs and material regions (right half, plan view)
    # ------------------------------------------------------------------
    def gill_slots(self, n_side=24, n_cap=10):
        """Closed plan polygons of the five gill-slit louvres (right side)."""
        mx = self.v.mx
        slots = []
        y0, y1 = GILL_Y
        for xc in GILL_X:
            s = np.linspace(0.0, 1.0, n_side)
            yy = y0 + (y1 - y0) * s
            xx = xc + GILL_SWEEP * ((y1 + y0) / 2 - yy) + GILL_BULGE * (4 * s * (1 - s) - 2.0 / 3.0)
            xx = mx(xx)
            c = np.column_stack([xx, yy])
            tan = np.gradient(c, axis=0)
            tan /= np.linalg.norm(tan, axis=1, keepdims=True)
            nrm = np.column_stack([-tan[:, 1], tan[:, 0]])
            r = GILL_HALF_WIDTH
            left = c + r * nrm
            right = c - r * nrm
            a_end = np.arctan2(nrm[-1, 1], nrm[-1, 0])
            a_start = np.arctan2(-nrm[0, 1], -nrm[0, 0])
            cap_end = [c[-1] + r * np.array([np.cos(a), np.sin(a)])
                       for a in np.linspace(a_end, a_end - np.pi, n_cap + 2)[1:-1]]
            cap_start = [c[0] + r * np.array([np.cos(a), np.sin(a)])
                         for a in np.linspace(a_start, a_start - np.pi, n_cap + 2)[1:-1]]
            poly = np.vstack([left, cap_end, right[::-1], cap_start])
            slots.append(poly)
        return slots

    def _t_poly(self, data, closed, samples=16):
        xs = self.v.mx(np.array([d[0] for d in data], float))
        pts = np.column_stack([xs, [d[1] for d in data]])
        if closed:
            dense, _ = catmull_rom(pts, samples, closed=True)
        else:
            dense, _ = catmull_rom(pts, samples, closed=False)
        y = dense[:, 1] * self.wf(dense[:, 0])
        return np.column_stack([dense[:, 0], y])

    def windscreen_half(self):
        """Open polyline from the centre plane round to the centre plane."""
        p = self._t_poly(WINDSCREEN_T, closed=False)
        p[0, 1] = 0.0
        p[-1, 1] = 0.0
        return p

    def side_window(self):
        return self._t_poly(SIDE_WINDOW_T, closed=True)

    def chevron(self):
        pts = np.array(CHEVRON, float)
        pts[:, 0] = self.v.mx(pts[:, 0])
        dense, _ = catmull_rom(pts, 16, closed=True)
        return dense

    # ------------------------------------------------------------------
    # appendage geometry helpers
    # ------------------------------------------------------------------
    def fin_profile(self, n_root=160):
        """Closed side-view (x, z) outline of the dorsal fin + tail."""
        v = self.v
        x0, x1 = v.mx(FIN_X_ROOT[0]), v.mx(FIN_X_ROOT[1])
        xr = np.linspace(x0, x1, n_root)
        zr = self.H(xr, np.zeros_like(xr)) - 12.0
        top = np.array(FIN_TOP, float)
        tail = np.array(FIN_TAIL_LOWER, float)
        top_x, top_z = v.mx(top[:, 0]), v.mz(top[:, 1])
        tail_x, tail_z = v.mx(tail[:, 0]), v.mz(tail[:, 1])
        # top edge from front to rear (dense), then tail lower edge to root end
        top_pts, _ = catmull_rom(np.column_stack([top_x, top_z]), 24)
        tail_pts, _ = catmull_rom(np.column_stack([tail_x, tail_z]), 16)
        # The fin starts where its top line meets the roof.
        z_roof = self.H(top_pts[:, 0], 0 * top_pts[:, 0])
        keep = top_pts[:, 1] > z_roof - 12.0
        top_pts = top_pts[keep]
        root = np.column_stack([xr, zr])
        root = root[root[:, 0] >= top_pts[0, 0]]
        poly = np.vstack([root[::-1][:-1], top_pts, tail_pts[1:], ])
        # close back to the root start via the tail lower edge end
        return poly

    def wing_section(self, yabs, n=60):
        """Crescent rear-wing section at |y| (reference airfoil rigidly placed)."""
        v = self.v
        s = (yabs / WING_SPAN_HALF) ** 2
        chord = WING_CHORD0 - WING_CHORD_TIP_LOSS * s
        x_le = v.mx(WING_LE_X0 + WING_LE_SWEEP * s)
        z_le = v.mz(WING_LE_Z0 + WING_LE_RISE * s)
        xu, zu, xl, zl = naca4_inverted(WING_CAMBER, WING_CAMBER_POS, WING_THICK, n)
        # closed loop: TE -> upper -> LE -> lower -> TE
        xs = np.concatenate([xu[::-1], xl[1:]])
        zs = np.concatenate([zu[::-1], zl[1:]])
        a = np.radians(WING_AOA_DEG)
        X = x_le + chord * (xs * np.cos(a) + zs * np.sin(a))
        Z = z_le + chord * (xs * np.sin(a) - zs * np.cos(a))
        return X, Z, chord, x_le, z_le


def _arch(x, xc, half_width, top, base, p):
    t = np.clip(np.abs(np.asarray(x, float) - xc) / half_width, 0.0, 1.0)
    return base + (top - base) * (1.0 - t ** p) ** (1.0 / p)


def naca4_inverted(m, p, t, n=60):
    """NACA 4-digit style section (unit chord) with cosine spacing.

    Returns upper/lower surfaces of the *normal* (lift-up) section; the caller
    flips z to make it a downforce section.
    """
    beta = np.linspace(0.0, np.pi, n)
    x = 0.5 * (1 - np.cos(beta))
    yt = 5 * t * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x ** 2 + 0.2843 * x ** 3 - 0.1036 * x ** 4)
    yc = np.where(x < p, m / p ** 2 * (2 * p * x - x ** 2), m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * x - x ** 2))
    dyc = np.where(x < p, 2 * m / p ** 2 * (p - x), 2 * m / (1 - p) ** 2 * (p - x))
    th = np.arctan(dyc)
    xu = x - yt * np.sin(th)
    yu = yc + yt * np.cos(th)
    xl = x + yt * np.sin(th)
    yl = yc - yt * np.cos(th)
    return xu, yu, xl, yl
