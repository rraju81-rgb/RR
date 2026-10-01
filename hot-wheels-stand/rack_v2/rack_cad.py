"""Accordion hook rack v4: rail-guided scissor frame. 3 printed designs + M4 hardware.

Printed:   link_A (plain bar, 3 holes) | link_B (same bar + hook tab) | rail segment (slot, rear nut groove, finger joints)
Hardware:  M4 button-head bolts, nylon-lock nuts, washers (every pivot); countersunk wall screws.  No printed pins, no snaps, no springs.

Front view, x right, y up, z out of the wall.  The rail is a horizontal strip behind the frame at y = 0.  The bottom row H_k = (k*w, 0)
rides in the rail: H_0 is a fixed pivot (round hole), H_1..H_K are bolts sliding in the rail slot (nuts slide in the rear groove).
Upper row U_k = (k*w, h), w = L cos(t), h = L sin(t).  K cars = K cells (K links A + K links B).  The hook of B_i sits on a tab TAB mm beyond
H_i, so the hooks are at (i*w + TAB cos t, -TAB sin t): one pitch apart and exactly level (the rail fixes the row), at every angle.
Pull the last hook right to open (slot end = open stop), push left to fold (slot start = folded stop).

Layers (z, mm): rail -9.6..-0.4 | link A 0..5 | link B 5..10 | washer 10..10.8 | bolt head 10.8..13.6 | hook collar 10..14 | peg 14..27
"""
import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix

# ---------------- parameters ----------------
L_LINK = 150.0
LINK_W, LINK_T = 12.0, 5.0
BOLT_D, HOLE_D = 4.0, 4.4              # M4 bolt, 0.2 mm radial clearance
ZA0, ZA1 = 0.0, 5.0
ZB0, ZB1 = ZA1, ZA1 + LINK_T           # 5..10
WASHER_D, WASHER_T = 9.0, 0.8
HEAD_D, HEAD_H = 8.0, 2.8              # ISO 7380 button head M4
NUT_AF, NUT_H = 7.0, 4.0               # DIN 985 nylon-lock nut M4
TAB = 16.0
COLLAR_D, COLLAR_Z1 = 12.0, ZB1 + 4.0  # 14.0
PEG_D, PEG_Z1, PEG_TILT_DEG = 4.8, 27.0, 6.0
OPEN_PITCH = 112.0
TH_MIN = float(np.arccos(OPEN_PITCH / L_LINK))
TH_MAX = np.radians(70.0)
# rail
RAIL_W = 28.0
RAIL_Z0, RAIL_Z1, RAIL_FRONT_Z0 = -9.6, -0.4, -2.8
SLOT_W, GROOVE_W = 5.0, 7.6
POCKET_DEPTH = 5.0
FINGER_Y0, FINGER_Y1, FINGER_LEN, FINGER_CLR = 5.5, 13.0, 14.0, 0.25
MAX_SEG = 230.0
CSK_D, CSK_H = 8.4, 2.0                # countersink for M4 flat-head wall screws
CARD_W, CARD_H, CARD_T = 105.0, 165.0, 1.2
CARD_TOP, BLISTER_W, BLISTER_H, BLISTER_D = 12.0, 85.0, 36.0, 16.0
CARD_HOLE_D = 7.0
CARD_Z = COLLAR_Z1 + 0.4


class Rack:
    def __init__(self, N):
        assert 1 <= N <= 8
        self.N = self.K = N
        self.L = L_LINK
        self.h_min, self.h_max = self.L * np.sin(TH_MIN), self.L * np.sin(TH_MAX)
        self.w_open, self.w_folded = self.L * np.cos(TH_MIN), self.L * np.cos(TH_MAX)
        self.x_end = self.K * self.w_open + 14.0
        self.x_start = -14.0

    def wh(self, th):
        return self.L * np.cos(th), self.L * np.sin(th)

    def hook_xy(self, k, th):
        w, _ = self.wh(th)
        return k * w + TAB * np.cos(th), -TAB * np.sin(th)


# ---------------- helpers ----------------
def box(x0, x1, y0, y1, z0, z1):
    return trimesh.creation.box(bounds=[[min(x0, x1), min(y0, y1), min(z0, z1)], [max(x0, x1), max(y0, y1), max(z0, z1)]])


def cylz(z0, z1, x, y, d, sections=36):
    m = trimesh.creation.cylinder(radius=d / 2, height=abs(z1 - z0), sections=sections)
    m.apply_translation([x, y, (z0 + z1) / 2])
    return m


def union(ms):
    ms = [m for m in ms if m is not None]
    return trimesh.boolean.union(ms, engine="manifold") if len(ms) > 1 else ms[0]


def diff(a, cuts):
    return trimesh.boolean.difference([a] + list(cuts), engine="manifold")


def hull_of(ms):
    return trimesh.convex.convex_hull(np.vstack([m.vertices for m in ms]))


def hexprism(z0, z1, x, y, af):
    d = af / np.cos(np.pi / 6)
    m = trimesh.creation.cylinder(radius=d / 2, height=abs(z1 - z0), sections=6)
    m.apply_translation([x, y, (z0 + z1) / 2])
    return m


# ---------------- hook and links ----------------
def hook(x, y, z_base):
    collar = cylz(z_base - 0.5, COLLAR_Z1, x, y, COLLAR_D, 40)
    dy = (PEG_Z1 - COLLAR_Z1) * np.tan(np.radians(PEG_TILT_DEG))
    peg = hull_of([cylz(COLLAR_Z1 - 0.01, COLLAR_Z1, x, y, PEG_D, 32), cylz(PEG_Z1 - 0.8, PEG_Z1 - 0.79, x, y + dy, PEG_D, 32)])
    tip = hull_of([cylz(PEG_Z1 - 0.8, PEG_Z1 - 0.79, x, y + dy, PEG_D, 28), cylz(PEG_Z1 - 0.01, PEG_Z1, x, y + dy, PEG_D - 1.6, 28)])
    return union([collar, peg, tip])


_cache = {}


def link_A():
    if "A" in _cache:
        return _cache["A"].copy()
    L, r = L_LINK, LINK_W / 2
    body = hull_of([cylz(ZA0, ZA1, -L / 2, 0.0, 2 * r, 40), cylz(ZA0, ZA1, L / 2, 0.0, 2 * r, 40)])
    m = diff(body, [cylz(ZA0 - 1, ZA1 + 1, x, 0.0, HOLE_D, 28) for x in (-L / 2, 0.0, L / 2)])
    _cache["A"] = m
    return m.copy()


def link_B():
    if "B" in _cache:
        return _cache["B"].copy()
    L, r = L_LINK, LINK_W / 2
    xh = L / 2 + TAB
    body = hull_of([cylz(ZB0, ZB1, -L / 2, 0.0, 2 * r, 40), cylz(ZB0, ZB1, xh, 0.0, COLLAR_D + 2.0, 40)])
    m = diff(body, [cylz(ZB0 - 1, ZB1 + 1, x, 0.0, HOLE_D, 28) for x in (-L / 2, 0.0, L / 2)])
    m = union([m, hook(xh, 0.0, ZB1)])
    _cache["B"] = m
    return m.copy()


# ---------------- hardware ----------------
def _bolt(x, y, z_top, z_tip, nut_z, nut_hex=True):
    head_z0 = z_top + WASHER_T
    return {"bolt": union([cylz(z_tip, head_z0 + 0.01, x, y, BOLT_D, 24), cylz(head_z0, head_z0 + HEAD_H, x, y, HEAD_D, 28)]),
            "nut": hexprism(nut_z[0], nut_z[1], x, y, NUT_AF),
            "washer": diff(cylz(z_top, z_top + WASHER_T, x, y, WASHER_D, 28), [cylz(z_top - 1, z_top + 2, x, y, BOLT_D + 0.2, 20)])}


def bolt_free(x, y):
    """pivot in the lattice (centre or upper node): bolt M4x16 through A and B, nylock nut behind link A (with a rear washer)."""
    d = _bolt(x, y, ZB1, -5.2, (-NUT_H - 0.8, -0.8))
    d["washer_rear"] = diff(cylz(-0.8, 0.0, x, y, WASHER_D, 28), [cylz(-1, 1, x, y, BOLT_D + 0.2, 20)])
    return d


def bolt_slide(x, top="B"):
    """H_k on the rail: bolt M4x20 through the links and the rail slot, nut in the rear groove (it cannot turn, it slides)."""
    return _bolt(x, 0.0, ZB1 if top == "B" else ZA1, -9.2, (-9.2, -5.2))


def bolt_pivot():
    """H_0: bolt M4x20 through A_1 and the rail's round hole, nut in the hex pocket."""
    return _bolt(0.0, 0.0, ZA1, -9.2, (-9.2, -5.2))


# ---------------- rail ----------------
def segment_cuts(R):
    """x positions of the joints between rail segments (each segment <= MAX_SEG long)."""
    total = R.x_end - R.x_start
    n = int(np.ceil(total / MAX_SEG))
    return [R.x_start + total * i / n for i in range(n + 1)]


def csk_screw_points(R):
    pts = []
    cuts = segment_cuts(R)
    for a, b in zip(cuts[:-1], cuts[1:]):
        for f in (0.28, 0.72):
            x = a + (b - a) * f
            pts += [(x, -9.0), (x, 9.0)] if f == 0.28 else [(x, 9.0), (x, -9.0)]
    return pts


def rail_segments(R):
    """list of printable segments (finger joints). segment i has fingers on its right end; segment i+1 has the matching pockets."""
    cuts = segment_cuts(R)
    segs = []
    for i, (a, b) in enumerate(zip(cuts[:-1], cuts[1:])):
        right = i < len(cuts) - 2
        left = i > 0
        x1 = b + (FINGER_LEN if right else 0.0)
        body = box(a, x1, -RAIL_W / 2, RAIL_W / 2, RAIL_Z0, RAIL_Z1)
        cuts_m = []
        if left:                                            # pockets for the previous segment's fingers
            for ys in (1, -1):
                cuts_m.append(box(a - 1, a + FINGER_LEN + FINGER_CLR, min(ys * FINGER_Y0 - ys * FINGER_CLR, ys * FINGER_Y1 + ys * FINGER_CLR),
                                  max(ys * FINGER_Y0 - ys * FINGER_CLR, ys * FINGER_Y1 + ys * FINGER_CLR), RAIL_Z0 - 1, RAIL_Z1 + 1))
        # the fingers on the right end are the part of the body beyond b limited to the finger y bands
        if right:
            keep = [box(b - 0.01, x1, ys * FINGER_Y0, ys * FINGER_Y1, RAIL_Z0, RAIL_Z1) for ys in (1, -1)] if False else None
            cut_ends = [box(b, x1 + 1, -RAIL_W / 2 - 1, -FINGER_Y1 - 0.0, RAIL_Z0 - 1, RAIL_Z1 + 1),
                        box(b, x1 + 1, -FINGER_Y0, FINGER_Y0, RAIL_Z0 - 1, RAIL_Z1 + 1),
                        box(b, x1 + 1, FINGER_Y1, RAIL_W / 2 + 1, RAIL_Z0 - 1, RAIL_Z1 + 1)]
            cuts_m += cut_ends
        # slot + groove (in this segment's x range), pivot hole + pocket in the first segment
        sx0, sx1 = max(a, R.w_folded - BOLT_D / 2 - 0.4), min(b + (FINGER_LEN if right else 0), R.K * R.w_open + BOLT_D / 2 + 0.4)
        if sx1 > sx0 + 1.0:
            cuts_m.append(hull_of([cylz(RAIL_Z0 - 1, RAIL_Z1 + 1, sx0 + SLOT_W / 2 if a <= R.w_folded - 3 else sx0 - 1, 0.0, SLOT_W, 24) if False else
                                   box(sx0 if a > R.w_folded else sx0, sx0 + 0.01, -SLOT_W / 2, SLOT_W / 2, RAIL_Z0 - 1, RAIL_Z1 + 1),
                                   box(sx1 - 0.01, sx1, -SLOT_W / 2, SLOT_W / 2, RAIL_Z0 - 1, RAIL_Z1 + 1)]))
            cuts_m.append(box(sx0 - (5.0 if a <= R.w_folded else 1.0), sx1 + (5.0 if b + (FINGER_LEN if right else 0) >= R.K * R.w_open else 1.0),
                              -GROOVE_W / 2, GROOVE_W / 2, RAIL_Z0 - 1, RAIL_FRONT_Z0))
        if i == 0:
            cuts_m.append(cylz(RAIL_Z0 - 1, RAIL_Z1 + 1, 0.0, 0.0, HOLE_D, 28))
            cuts_m.append(hexprism(RAIL_Z0 - 1, RAIL_Z0 + POCKET_DEPTH, 0.0, 0.0, NUT_AF + 0.4))
        for (x, y) in csk_screw_points(R):
            if a + 6 < x < b - 6:
                cuts_m.append(cylz(RAIL_Z0 - 1, RAIL_Z1 + 1, x, y, 4.5, 24))
                cuts_m.append(hull_of([cylz(RAIL_Z1 - CSK_H, RAIL_Z1 - CSK_H + 0.01, x, y, 4.5, 24), cylz(RAIL_Z1, RAIL_Z1 + 0.01, x, y, CSK_D, 24)]))
        segs.append(diff(body, cuts_m))
    return segs


def rail_full(R):
    return union(rail_segments(R))


def card_mesh(x, y=0.0):
    body = diff(box(x - CARD_W / 2, x + CARD_W / 2, y - CARD_H + CARD_TOP, y + CARD_TOP, CARD_Z, CARD_Z + CARD_T),
                [cylz(CARD_Z - 1, CARD_Z + CARD_T + 1, x, y, CARD_HOLE_D, 28)])
    bl = box(x - BLISTER_W / 2, x + BLISTER_W / 2, y - CARD_H + CARD_TOP + 4, y - CARD_H + CARD_TOP + 4 + BLISTER_H,
             CARD_Z + CARD_T, CARD_Z + CARD_T + BLISTER_D)
    return union([body, bl])


def screw_flat_head(x, y):
    """DIN 7991 M4 countersunk head sitting in the countersink (flush with the rail face)."""
    return hull_of([cylz(RAIL_Z1 - CSK_H + 0.2, RAIL_Z1 - CSK_H + 0.21, x, y, 4.0, 20), cylz(RAIL_Z1 - 0.15, RAIL_Z1 - 0.14, x, y, CSK_D - 0.5, 20)])


# ---------------- the frame at an opening angle ----------------
def assembly(R, th, with_cards=True, rail=None, hardware=True):
    """name -> (mesh, group).  H_k nodes slide along the rail; everything else is rigid per link."""
    w, h = R.wh(th)
    parts = {}
    for i in range(1, R.K + 1):
        cx, cy = (i - 0.5) * w, h / 2
        a = link_A()
        a.apply_transform(rotation_matrix(th, [0, 0, 1]))
        a.apply_translation([cx, cy, 0])
        parts[f"A{i}"] = (a, f"A{i}")
        b = link_B()
        b.apply_transform(rotation_matrix(-th, [0, 0, 1]))
        b.apply_translation([cx, cy, 0])
        parts[f"B{i}"] = (b, f"B{i}")
        if hardware:
            u = np.array([np.cos(th), np.sin(th)])
            for key, (px, py) in (("c", (cx, cy)), ("e", tuple(np.array([cx, cy]) + u * R.L / 2))):
                if key == "e" and i == R.K:
                    continue
                for nm, m in bolt_free(px, py).items():
                    parts[f"{nm}_{i}{key}"] = (m, f"A{i}")
        if with_cards:
            x, y = R.hook_xy(i, th)
            parts[f"card{i}"] = (card_mesh(x, y), f"B{i}")
    if hardware:
        for k in range(1, R.K + 1):                                       # sliding bolts at H_k (top link is B_k)
            for nm, m in bolt_slide(k * w).items():
                parts[f"{nm}_H{k}"] = (m, f"slide{k}")
        for nm, m in bolt_pivot().items():
            parts[f"{nm}_pivot"] = (m, "fixed")
    parts["rail"] = (rail if rail is not None else rail_full(R), "fixed")
    return parts


def hardware_fixed(R):
    return {f"wall_screw{i}": screw_flat_head(x, y) for i, (x, y) in enumerate(csk_screw_points(R))}


def bolt_count(R):
    K = R.K
    return {"M4x16 button-head bolt": K + (K - 1), "M4x20 button-head bolt (rail)": K + 1, "M4 nylon-lock nut": 2 * K + (K - 1) + 1 - (K - 1) + (K - 1),
            "M4 washer (front)": 2 * K, "M4 washer (rear)": K + (K - 1),
            "M4 countersunk wall screw": len(csk_screw_points(R))}


if __name__ == "__main__":
    import sys
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    R = Rack(N)
    print(f"N={N} theta {np.degrees(TH_MIN):.1f}..{np.degrees(TH_MAX):.0f} deg  pitch {R.w_open:.1f}/{R.w_folded:.1f}  rail x {R.x_start:.0f}..{R.x_end:.0f}  cuts {[round(c) for c in segment_cuts(R)]}")
    for n, m in (("link_A", link_A()), ("link_B", link_B())):
        print(f"{n:8s} watertight={m.is_watertight} extents={[round(float(x), 1) for x in m.extents]}")
    for i, s in enumerate(rail_segments(R)):
        print(f"rail seg {i}: watertight={s.is_watertight} extents={[round(float(x), 1) for x in s.extents]}")
