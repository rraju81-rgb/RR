"""Side-mechanism fold-down rack (v2): 4 printed parts, all moving parts live in two side modules.

Printed parts (per rack):
  1. module_R   cheek + panel bar B1 + bar B2 + one cross arm per card, print-in-place (pins integral)
  2. module_L   mirror of module_R
  3. wall_frame thin U frame (posts + crossbars), magnet fingers, spring anchors
  4. tie_bar    square bar through both B1 bars so the two sides move together
Hardware: 2 extension springs, 4 magnets 6x2, wall screws, 1 M3 screw + washer for the tie bar.

Coordinates (closed pose): x = left/right, y = up, z = toward the viewer, hinge H at y=0, z=0. mm.
Parallelogram: H, B1 joints, B2 joints, F = H + (-D, +h0). The cross arms stay parallel to F-H, so they
translate while B1 rotates 0..90 deg; each card sits in cradles on its two arms and stays upright.

x layers (right module; the left one is the mirror), inner -> outer:
  card +-52.5 | cradle 47.5..54 | arm 54.5..60.5 | B1,B2 bars 61..67 | arm-pin heads 67.5..70.5
  | cheek 71.5..77.5 | H/F pin heads 77.8..80.6 | spring plane ~81 | flange screws x=85 (flange to x=92)
Every joint pin is printed on the LOWER layer (arm or bar) and rises through the hole of the upper layer, so
heads are 45 degree cones (no supports) and every gap is 0.4-0.5 mm. Print with the card side (x=47.5) down.
"""
import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix
from foldout_cad import box, cylx, cylz, union, diff, hull_of, side_x, rot_about

# ---------------- parameters ----------------
CARD_W, CARD_H, CARD_T = 105.0, 165.0, 1.2
BLISTER_W, BLISTER_H, BLISTER_D = 85.0, 36.0, 16.0
PITCH, STEP, C0, H0_OFF, BAR_W, S0 = 45.0, 6.5, 8.5, 18.0, 14.0, 30.0
HOLE_D, PIN_D = 3.8, 3.0                # arm joints
BIG_HOLE, BIG_PIN = 5.2, 4.4            # hinge pins H, F and the spring post
X_CR0, X_CR1, X_A0, X_A1 = 47.5, 54.0, 54.5, 60.5
X_B0, X_B1, X_P0, X_P1 = 61.0, 67.0, 71.5, 77.5
X_CARD = 52.5
SLOT_CLR, CR_WALL = 0.3, 2.4
GAP = 0.4
CH_Y0, CH_Y1, CH_ZMAX = -28.0, 26.0, 30.0        # cheek extent
TIE_Y, TIE_S = -9.0, 6.0                          # tie bar height on B1, square size
FLANGE_X1 = 92.0


class R2:
    def __init__(self, N):
        assert 1 <= N <= 8
        self.N = N
        self.D = max(C0 + (N - 1) * STEP + 11.0, 32.0)
        self.h0 = H0_OFF
        self.La = float(np.hypot(self.D, self.h0))
        self.Ps = PITCH + STEP * self.h0 / self.D
        self.s = [S0 + j * self.Ps for j in range(N)]
        self.e = [C0 + (N - 1 - j) * STEP for j in range(N)]
        self.zr = [-e for e in self.e]
        self.yb = [self.s[j] + self.e[j] * self.h0 / self.D for j in range(N)]
        self.y_top = self.yb[-1] + CARD_H
        self.Lf = self.y_top + 22.0                      # frame height
        self.Lb = self.s[-1] + 36.0                      # B1 length (this is how far the panel sticks out when open)
        self.y_m = self.s[-1] + 29.0                     # magnet height
        self.a_sp = min(self.s[0] + 0.5 * self.Ps, self.y_m - 14.0)   # spring post height on B1
        self.d_sp = max(round(0.5 * self.Lf / 5.0) * 5.0, 150.0)   # wall anchor height
        self.F = np.array([self.h0, -self.D])


def X(sign, x):
    return sign * x


def pin_on(sign, y, z, x_start, x_cone0, d_shank, d_head, flat=1.0):
    """pin along +x (mirrored by sign): shank x_start..x_cone0, 45 degree cone to d_head, short flat top."""
    h = (d_head - d_shank) / 2.0
    sh = cylx(X(sign, x_start), X(sign, x_cone0), y, z, d_shank, 28)
    c0 = cylx(X(sign, x_cone0), X(sign, x_cone0 + 0.01), y, z, d_shank, 28)
    c1 = cylx(X(sign, x_cone0 + h), X(sign, x_cone0 + h + 0.01), y, z, d_head, 28)
    cone = hull_of([c0, c1])
    top = cylx(X(sign, x_cone0 + h), X(sign, x_cone0 + h + flat), y, z, d_head, 28)
    return union([sh, cone, top])


# ---------------- module parts ----------------
def cheek(R, sign):
    xa, xb = side_x(sign, X_P0, X_P1)
    plate = box(xa, xb, CH_Y0, CH_Y1, -R.D - 9.0, CH_ZMAX)
    fx0, fx1 = side_x(sign, X_P0, FLANGE_X1)
    flange = box(fx0, fx1, CH_Y0, CH_Y1, -R.D - 9.0, -R.D - 6.0)
    lx0, lx1 = side_x(sign, X_B0 + 0.5, X_P0 + 0.5)
    lug_open = box(lx0, lx1, -14.0, -7.0 - GAP, 18.0, CH_ZMAX)       # B1 rests here at 90 deg
    body = union([plate, flange, lug_open])      # closed position is set by the magnets (they self-centre)
    cuts = [cylx(xa - 1, xb + 1, 0.0, 0.0, BIG_HOLE, 32),
            cylx(xa - 1, xb + 1, R.h0, -R.D, BIG_HOLE, 32)]
    for y in (-20.0, 0.0, 20.0):
        cuts.append(cylz(-R.D - 10.0, -R.D - 5.0, X(sign, 85.0), y, 4.5, 24))
    return diff(body, cuts)


def b1(R, sign):
    xa, xb = side_x(sign, X_B0, X_B1)
    body = union([box(xa, xb, TIE_Y, R.Lb, -BAR_W / 2, BAR_W / 2), cylx(xa, xb, TIE_Y, 0.0, BAR_W, 40)])   # tail below H carries the tie bar
    cuts = [cylx(xa - 1, xb + 1, y, 0.0, HOLE_D, 24) for y in R.s]
    cuts.append(box(xa - 1, xb + 1, TIE_Y - (TIE_S + 0.4) / 2, TIE_Y + (TIE_S + 0.4) / 2, -(TIE_S + 0.4) / 2, (TIE_S + 0.4) / 2))
    px0, px1 = side_x(sign, X_B1 - 2.2, X_B1 + 0.1)
    cuts.append(cylx(px0, px1, R.y_m, 0.0, 6.2, 32))                # magnet pocket, outer face
    m = diff(body, cuts)
    hinge = pin_on(sign, 0.0, 0.0, X_B1 - 0.5, X_P1 + 0.3, BIG_PIN, BIG_PIN + 4.0)
    post = pin_on(sign, R.a_sp, 0.0, X_B1 - 0.5, 82.0, BIG_PIN, BIG_PIN + 4.0)
    return union([m, hinge, post])


def b2(R, sign):
    xa, xb = side_x(sign, X_B0, X_B1)
    y_end = R.h0 + R.s[-1] + 14.0
    body = union([box(xa, xb, R.h0, y_end, -R.D - BAR_W / 2, -R.D + BAR_W / 2), cylx(xa, xb, R.h0, -R.D, BAR_W, 40)])
    cuts = [cylx(xa - 1, xb + 1, s + R.h0, -R.D, HOLE_D, 24) for s in R.s]
    m = diff(body, cuts)
    hinge = pin_on(sign, R.h0, -R.D, X_B1 - 0.5, X_P1 + 0.3, BIG_PIN, BIG_PIN + 4.0)
    return union([m, hinge])


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
    pins = [pin_on(sign, J1[0], J1[1], X_A1 - 0.5, X_B1 + GAP + 0.1, PIN_D, 7.0),
            pin_on(sign, J2[0], J2[1], X_A1 - 0.5, X_B1 + GAP + 0.1, PIN_D, 7.0)]
    return union([m] + pins)


def card(R, j):
    zr, yb = R.zr[j], R.yb[j]
    body = box(-CARD_W / 2, CARD_W / 2, yb, yb + CARD_H, zr, zr + CARD_T)
    bl = box(-BLISTER_W / 2, BLISTER_W / 2, yb + 4, yb + 4 + BLISTER_H, zr + CARD_T, zr + CARD_T + BLISTER_D)
    return union([body, bl])


def tie_bar(R):
    bar = box(-X_B1, X_B1 + 0.5, TIE_Y - TIE_S / 2, TIE_Y + TIE_S / 2, -TIE_S / 2, TIE_S / 2)
    head = cylx(X_B1 + 0.5, X_B1 + 3.2, TIE_Y, 0.0, 9.0, 32)
    return union([bar, head])


def washer(R):
    return cylx(-X_B1 - 2.8, -X_B1 - 0.1, TIE_Y, 0.0, 9.0, 32)       # hardware: M3 washer + screw head


def frame(R):
    zb0, zb1 = -R.D - 12.0, -R.D - 9.0
    parts, cuts = [], []
    for sg in (1, -1):
        px0, px1 = side_x(sg, X_B0, FLANGE_X1)
        parts.append(box(px0, px1, CH_Y0, R.Lf + 8.0, zb0, zb1))
        # magnet finger beside the top of B1
        fx0, fx1 = side_x(sg, X_B1 + 0.6, X_B1 + 0.6 + 3.3)
        parts.append(box(fx0, fx1, R.y_m - 5.0, R.y_m + 5.0, zb0, 7.0))
        cuts.append(cylx(*side_x(sg, X_B1 + 0.5, X_B1 + 0.6 + 2.2), R.y_m, 0.0, 6.2, 32))
        # spring anchor tab
        tx0, tx1 = side_x(sg, 78.5, 84.0)
        parts.append(box(tx0, tx1, R.d_sp - 6, R.d_sp + 6, zb0, 5.0))
        cuts.append(cylx(tx0 - 1, tx1 + 1, R.d_sp, 0.0, HOLE_D, 24))
        for y in (-20.0, 0.0, 20.0):
            cuts.append(cylz(zb0 - 1, zb1 + 1, X(sg, 85.0), y, 4.5, 24))
        for y in (R.d_sp + 25.0, R.Lf - 30.0):
            cuts.append(cylz(zb0 - 1, zb1 + 1, X(sg, 76.0), y, 4.5, 24))
    parts.append(box(-FLANGE_X1, FLANGE_X1, R.Lf - 14.0, R.Lf, zb0, zb1))
    parts.append(box(-FLANGE_X1, FLANGE_X1, CH_Y0, CH_Y0 + 8.0, zb0, zb1))
    return diff(union(parts), cuts)


# ---------------- assembly ----------------
def build(N):
    R = R2(N)
    P = {"frame": dict(mesh=frame(R), group="fixed"),
         "tie": dict(mesh=tie_bar(R), group="panel"),
         "washer": dict(mesh=washer(R), group="panel", hardware=True)}
    for sg, tag in ((1, "R"), (-1, "L")):
        P[f"cheek_{tag}"] = dict(mesh=cheek(R, sg), group="fixed", module=tag)
        P[f"b1_{tag}"] = dict(mesh=b1(R, sg), group="panel", module=tag)
        P[f"b2_{tag}"] = dict(mesh=b2(R, sg), group="b2", module=tag)
        for j in range(N):
            P[f"arm{j}_{tag}"] = dict(mesh=arm(R, sg, j), group=f"j{j}", module=tag)
    for j in range(N):
        P[f"card{j}"] = dict(mesh=card(R, j), group=f"j{j}")
    return R, P


def pose_transforms(R, P, phi_deg):
    out = {}
    TH = rot_about(phi_deg, 0.0, 0.0)
    TF = rot_about(phi_deg, R.h0, -R.D)
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
    """thin rod standing in for the extension spring (post on B1 -> anchor tab on the frame)."""
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


if __name__ == "__main__":
    import sys
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    R, P = build(N)
    print("N", N, "D", round(R.D, 1), "Lb (open reach)", round(R.Lb, 1), "Lf", round(R.Lf, 1), "Ps", round(R.Ps, 2))
    bad = [k for k, d in P.items() if not d["mesh"].is_watertight]
    print("parts", len(P), "non-watertight:", bad)
