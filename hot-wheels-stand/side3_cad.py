"""Side-mechanism fold-down rack v3: ONE wall frame + ONE swing design (printed twice, mirrored). Hinges are M4 bolts.

Printed parts (per rack):
  1. frame      wall U-frame with both hinge cheeks, magnet fingers, spring tabs, open stop. Prints back-face down, nothing floats.
  2. swing_R    both bars (B1 + B2) and one cross arm per card; arm pins print in place on the bars (arms bridge a 0.5 mm gap).
  3. swing_L    mirror image of swing_R.
Hardware: 4 M4x20 button bolts + nylock nuts + 8 washers (the hinges), 2 M4x25 bolts + nuts (spring studs), 1 dowel 6 mm x 134 mm (ties the two
swings), 2 extension springs, 4 magnets 6x2, wall screws.

Coordinates (closed pose): x left/right, y up, z toward the viewer, hinge H at y=0,z=0. mm. Parallelogram H, B1 joints, B2 joints, F = H + (h0, -D):
the cross arms stay parallel to F-H, so cards translate (stay upright) while B1 swings 0..90 degrees.

x layers (right side, left is the mirror), card side -> wall:
  card +-52.5 | cradle 47.5..54 | arm 54.5..60.5 | bars B1,B2 61..67 | washer 67..67.8 | cheek 67.8..73.8 | washer 73.8..74.6 | bolt head 74.6..77.4
Swing prints with the bar's outer face (x=67) on the bed: bars (bed) -> arm pins -> arms -> cradle blocks on top.
"""
import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix
from foldout_cad import box, cylx, cylz, union, diff, hull_of, side_x, rot_about

CARD_W, CARD_H, CARD_T = 105.0, 165.0, 1.2
BLISTER_W, BLISTER_H, BLISTER_D = 85.0, 36.0, 16.0
PITCH, STEP, C0, H0_OFF, BAR_W, S0 = 45.0, 6.5, 8.5, 18.0, 14.0, 30.0
HOLE_D, PIN_D = 4.8, 4.0                 # arm joints (pin on the bar, hole in the arm), 0.4 mm radial clearance
M4_HOLE = 4.4
X_CR0, X_CR1, X_A0, X_A1 = 47.5, 54.0, 54.5, 60.5
X_B0, X_B1 = 61.0, 67.0
WASHER_T = 0.8
X_P0, X_P1 = X_B1 + WASHER_T, X_B1 + WASHER_T + 6.0       # cheek 67.8..73.8
X_HEAD0 = X_P1 + WASHER_T                                 # 74.6
X_CARD = 52.5
SLOT_CLR, CR_WALL, GAP = 0.3, 2.4, 0.4
CH_Y0, CH_Y1, CH_ZMAX = -28.0, 26.0, 30.0
TIE_Y, DOWEL_D = -9.0, 6.0
FLANGE_X1 = 92.0
HEAD_D, HEAD_H, WASH_D, NUT_AF, NUT_H = 8.0, 2.8, 9.0, 7.0, 4.0


class R3:
    def __init__(self, N):
        assert 1 <= N <= 8
        self.N = N
        self.D = max(C0 + (N - 1) * STEP + 11.0, 32.0)
        self.h0 = H0_OFF
        self.La = float(np.hypot(self.D, self.h0))
        self.Ps = PITCH + STEP * self.h0 / self.D
        self.S0 = max(S0, 0.65 * self.D)                  # first joint high enough that arm 0 clears the hinge nut at 90 degrees
        self.s = [self.S0 + j * self.Ps for j in range(N)]
        self.e = [C0 + (N - 1 - j) * STEP for j in range(N)]
        self.zr = [-e for e in self.e]
        self.yb = [self.s[j] + self.e[j] * self.h0 / self.D for j in range(N)]
        self.y_top = self.yb[-1] + CARD_H
        self.Lb = self.s[-1] + 36.0                       # open reach
        self.y_m = self.s[-1] + 29.0                      # magnet height
        self.a_sp = min(self.s[0] + 0.5 * self.Ps, self.y_m - 14.0)
        self.d_sp = max(round(0.5 * (self.y_top + 22.0) / 5.0) * 5.0, 150.0) if False else max(round(0.5 * (self.y_top + 22.0) / 5.0) * 5.0, 150.0)
        self.Lp = max(self.y_m, self.d_sp) + 14.0         # frame post height (frame is only as tall as it must be)
        self.F = np.array([self.h0, -self.D])


# ---------------- swing parts ----------------
def pin_down(sign, y, z, x_start, x_cone0):
    """pin on a bar growing toward smaller |x| (print up): shank, 45 degree cone head (d3 -> d7), flat top. built along -x for sign=+1."""
    d0, d1 = PIN_D, 6.6                      # head top must stay at |x| >= 53 so it never touches a card (cards reach x = 52.5)
    h = (d1 - d0) / 2.0
    sh = cylx(*side_x(sign, x_cone0, x_start), y, z, d0, 28)
    c0 = cylx(*side_x(sign, x_cone0 - 0.01, x_cone0), y, z, d0, 28)
    c1 = cylx(*side_x(sign, x_cone0 - h - 0.01, x_cone0 - h), y, z, d1, 28)
    top = cylx(*side_x(sign, x_cone0 - h - 0.2, x_cone0 - h), y, z, d1, 28)
    return union([sh, hull_of([c0, c1]), top])


def b1(R, sign):
    xa, xb = side_x(sign, X_B0, X_B1)
    body = union([box(xa, xb, TIE_Y, R.Lb, -BAR_W / 2, BAR_W / 2), cylx(xa, xb, TIE_Y, 0.0, BAR_W, 40)])
    cuts = [cylx(xa - 1, xb + 1, 0.0, 0.0, M4_HOLE, 28),               # hinge bolt H
            cylx(xa - 1, xb + 1, TIE_Y, 0.0, DOWEL_D + 0.3, 28),       # dowel
            cylx(xa - 1, xb + 1, R.a_sp, 0.0, M4_HOLE, 28)]            # spring stud
    px0, px1 = side_x(sign, X_B1 - 2.2, X_B1 + 0.1)
    cuts.append(cylx(px0, px1, R.y_m, 0.0, 6.2, 32))                   # magnet pocket, outer face (bed side)
    hx0, hx1 = side_x(sign, X_B0 - 1.0, X_B0 + 3.2)
    cuts.append(cylx(hx0, hx1, R.a_sp, 0.0, (7.0 + 0.5) / np.cos(np.pi / 6), 6))   # hex pocket for the spring stud's head (inner face = top of the print)
    m = diff(body, cuts)
    pins = [pin_down(sign, y, 0.0, X_B0 + 0.5, X_A0 - 0.2) for y in R.s]
    return union([m] + pins)


def b2(R, sign):
    xa, xb = side_x(sign, X_B0, X_B1)
    y_end = R.h0 + R.s[-1] + 14.0
    body = union([box(xa, xb, R.h0, y_end, -R.D - BAR_W / 2, -R.D + BAR_W / 2), cylx(xa, xb, R.h0, -R.D, BAR_W, 40)])
    m = diff(body, [cylx(xa - 1, xb + 1, R.h0, -R.D, M4_HOLE, 28)])
    pins = [pin_down(sign, s + R.h0, -R.D, X_B0 + 0.5, X_A0 - 0.2) for s in R.s]
    return union([m] + pins)


def arm(R, sign, j):
    xa, xb = side_x(sign, X_A0, X_A1)
    J1, J2 = (R.s[j], 0.0), (R.s[j] + R.h0, -R.D)
    r = 6.0
    body = hull_of([cylx(xa, xb, J1[0], J1[1], 2 * r, 32), cylx(xa, xb, J2[0], J2[1], 2 * r, 32)])
    zr, yb = R.zr[j], R.yb[j]
    gz0, gz1 = zr - SLOT_CLR, zr + CARD_T + SLOT_CLR
    box_yz = (yb - 3.0, yb + 22.0, gz0 - CR_WALL, gz1 + CR_WALL)
    cx0, cx1 = side_x(sign, X_CR0, X_CR1)
    block = box(cx0, cx1, *box_yz)
    nk0, nk1 = side_x(sign, X_CR1 - 0.2, X_A0 + 0.2)
    foot = hull_of([cylx(nk0, nk1, J1[0], J1[1], 2 * r, 32), cylx(nk0, nk1, J2[0], J2[1], 2 * r, 32)])
    neck = trimesh.boolean.intersection([foot, box(nk0 - 1, nk1 + 1, *box_yz)], engine="manifold")
    m = union([body, neck, block])
    sx0, sx1 = side_x(sign, X_CR0 - 1.0, X_CARD + 1.0)
    m = diff(m, [box(sx0, sx1, yb, yb + 23.0, gz0, gz1)])
    holes = [cylx(xa - 1, xb + 1, J1[0], J1[1], HOLE_D, 24), cylx(xa - 1, xb + 1, J2[0], J2[1], HOLE_D, 24)]
    return diff(m, holes)


def swing(R, sign):
    """whole printable swing side as one mesh (bars + arms, pins through the arm holes)."""
    return union([b1(R, sign), b2(R, sign)] + [arm(R, sign, j) for j in range(R.N)])


# ---------------- frame ----------------
def frame(R):
    zb0, zb1 = -R.D - 12.0, -R.D - 9.0
    parts, cuts = [], []
    for sg in (1, -1):
        px0, px1 = side_x(sg, X_B0, FLANGE_X1)
        parts.append(box(px0, px1, CH_Y0, R.Lp, zb0, zb1))
        ca, cb = side_x(sg, X_P0, X_P1)
        parts.append(box(ca, cb, CH_Y0, CH_Y1, zb1 - 0.5, CH_ZMAX))                                        # hinge cheek (a wall on the plate)
        lx0, lx1 = side_x(sg, X_B0 + 0.5, X_P0 + 0.5)
        lug_edge = side_x(sg, X_P0, X_P0 + 1.0)
        parts.append(hull_of([box(lx0, lx0 + sg * 0.01, -14.0, -7.0 - GAP, 18.0, CH_ZMAX),               # 90 degree stop, 45 degree underside
                              box(*lug_edge, -14.0, -7.0 - GAP, 18.0 - (X_P0 - X_B0 - 0.5), CH_ZMAX)]))
        cuts += [cylx(ca - 1, cb + 1, 0.0, 0.0, M4_HOLE, 28), cylx(ca - 1, cb + 1, R.h0, -R.D, M4_HOLE, 28)]
        fx0, fx1 = side_x(sg, X_B1 + 0.6, X_B1 + 0.6 + 3.3)
        parts.append(box(fx0, fx1, R.y_m - 5.0, R.y_m + 5.0, zb0, 7.0))
        cuts.append(cylx(*side_x(sg, X_B1 + 0.5, X_B1 + 0.6 + 2.2), R.y_m, 0.0, 6.2, 32))
        tx0, tx1 = side_x(sg, 78.5, 84.0)
        parts.append(box(tx0, tx1, R.d_sp - 6, R.d_sp + 6, zb0, 5.0))
        cuts.append(cylx(tx0 - 1, tx1 + 1, R.d_sp, 0.0, HOLE_D, 24))
        for y in (-20.0, 0.0, 20.0):
            cuts.append(cylz(zb0 - 1, zb1 + 1, sg * 85.0, y, 4.5, 24))
        for y in (R.Lp - 30.0, 0.5 * (R.Lp + 20.0)):
            cuts.append(cylz(zb0 - 1, zb1 + 1, sg * 76.0, y, 4.5, 24))
    parts.append(box(-FLANGE_X1, FLANGE_X1, R.Lp - 14.0, R.Lp, zb0, zb1))
    parts.append(box(-FLANGE_X1, FLANGE_X1, CH_Y0, CH_Y0 + 8.0, zb0, zb1))
    return diff(union(parts), cuts)


# ---------------- hardware (for fit checks only) ----------------
def hinge_hw(sign, y, z):
    """M4x20 button bolt from the outside, nylock nut on the swing's inner face, washers on both sides of the cheek."""
    bolt = union([cylx(*side_x(sign, 54.6, X_HEAD0 + 0.01), y, z, 4.0, 24), cylx(*side_x(sign, X_HEAD0, X_HEAD0 + HEAD_H), y, z, HEAD_D, 28)])
    nut = cylx(*side_x(sign, X_B0 - NUT_H, X_B0), y, z, NUT_AF / np.cos(np.pi / 6), 6)
    w1 = diff(cylx(*side_x(sign, X_B1, X_P0), y, z, WASH_D, 28), [cylx(*side_x(sign, X_B1 - 1, X_P0 + 1), y, z, 4.2, 20)])
    w2 = diff(cylx(*side_x(sign, X_P1, X_HEAD0), y, z, WASH_D, 28), [cylx(*side_x(sign, X_P1 - 1, X_HEAD0 + 1), y, z, 4.2, 20)])
    return union([bolt, nut, w1, w2])


def stud_hw(sign, y):
    """M4x25 hex bolt: head sunk in a hex pocket on the inner face of B1, nut on the outer face, spring hooks on the free shank."""
    bolt = union([cylx(*side_x(sign, X_B0 + 0.4, X_B0 + 0.4 + 2.8), y, 0.0, 7.0 / np.cos(np.pi / 6), 6), cylx(*side_x(sign, X_B0 + 3.0, 82.0), y, 0.0, 4.0, 24)])
    nut = cylx(*side_x(sign, X_B1, X_B1 + NUT_H), y, 0.0, NUT_AF / np.cos(np.pi / 6), 6)
    return union([bolt, nut])


def dowel():
    return cylx(-X_B1 - 0.05, X_B1 + 0.05, TIE_Y, 0.0, DOWEL_D, 28)


def card(R, j):
    zr, yb = R.zr[j], R.yb[j]
    body = box(-CARD_W / 2, CARD_W / 2, yb, yb + CARD_H, zr, zr + CARD_T)
    bl = box(-BLISTER_W / 2, BLISTER_W / 2, yb + 4, yb + 4 + BLISTER_H, zr + CARD_T, zr + CARD_T + BLISTER_D)
    return union([body, bl])


# ---------------- assembly ----------------
def build(N, with_cards=True):
    R = R3(N)
    P = {"frame": dict(mesh=frame(R), group="fixed"), "dowel": dict(mesh=dowel(), group="panel", hardware=True)}
    for sg, tag in ((1, "R"), (-1, "L")):
        P[f"b1_{tag}"] = dict(mesh=b1(R, sg), group="panel", module=tag)
        P[f"b2_{tag}"] = dict(mesh=b2(R, sg), group="b2", module=tag)
        for j in range(N):
            P[f"arm{j}_{tag}"] = dict(mesh=arm(R, sg, j), group=f"j{j}", module=tag)
        P[f"hbolt_{tag}"] = dict(mesh=hinge_hw(sg, 0.0, 0.0), group="fixed", hardware=True)
        P[f"fbolt_{tag}"] = dict(mesh=hinge_hw(sg, R.h0, -R.D), group="fixed", hardware=True)
        P[f"stud_{tag}"] = dict(mesh=stud_hw(sg, R.a_sp), group="panel", hardware=True)
    if with_cards:
        for j in range(N):
            P[f"card{j}"] = dict(mesh=card(R, j), group=f"j{j}")
    return R, P


def pose_transforms(R, P, phi_deg):
    out = {}
    TH, TF = rot_about(phi_deg, 0.0, 0.0), rot_about(phi_deg, R.h0, -R.D)
    for name, d in P.items():
        g = d["group"]
        if g == "fixed":
            out[name] = np.eye(4)
        elif g == "panel":
            out[name] = TH
        elif g == "b2":
            out[name] = TF
        else:
            j = int(g[1:])
            J = np.array([0.0, R.s[j], 0.0, 1.0])
            T = np.eye(4)
            T[:3, 3] = ((TH @ J) - J)[:3]
            out[name] = T
    return out


def posed(R, P, phi_deg):
    tr = pose_transforms(R, P, phi_deg)
    return {n: d["mesh"].copy().apply_transform(tr[n]) for n, d in P.items()}


def spring_mesh(R, phi_deg, sign):
    TH = rot_about(phi_deg, 0.0, 0.0)
    A = (TH @ np.array([0.0, R.a_sp, 0.0, 1.0]))[:3]
    W = np.array([0.0, R.d_sp, 0.0])
    x = sign * 81.2
    d = W - A
    d[0] = 0.0
    u = d / np.linalg.norm(d)
    p0 = np.array([x, *(A[1:] + 6.0 * u[1:])])
    p1 = np.array([x, *(W[1:] - 12.0 * u[1:])])
    return trimesh.creation.cylinder(radius=3.0, segment=[p0, p1], sections=12)


# ---------------- print orientation ----------------
def print_swing(R, sign):
    """swing side with the bar's outer face (|x| = 67) on the bed, y along the bed. returns a mesh with min z = 0."""
    m = swing(R, sign)
    if sign > 0:
        M = np.array([[0, 0, 1, 0], [0, 1, 0, 0], [-1, 0, 0, X_B1], [0, 0, 0, 1.0]])
    else:
        M = np.array([[0, 0, -1, 0], [0, 1, 0, 0], [1, 0, 0, X_B1], [0, 0, 0, 1.0]])
    m.apply_transform(M)
    m.apply_translation([-m.bounds[0][0], -m.bounds[0][1], 0])
    return m


def print_frame(R):
    m = frame(R)
    m.apply_translation([0, -m.bounds[0][1], -m.bounds[0][2]])
    return m


if __name__ == "__main__":
    import sys
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    R, P = build(N)
    print("N", N, "D", round(R.D, 1), "reach Lb", round(R.Lb, 1), "post Lp", round(R.Lp, 1))
    print("non-watertight:", [k for k, d in P.items() if not d["mesh"].is_watertight])
    for nm, m in (("frame", print_frame(R)), ("swing_R", print_swing(R, 1)), ("swing_L", print_swing(R, -1))):
        print(nm, [round(float(v), 1) for v in m.extents], "watertight", m.is_watertight)
