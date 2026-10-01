"""Fold-down stand-up rack: parametric CAD (parallelogram linkage, no gears).

Coordinates (closed pose): x = left/right, y = up, z = toward the viewer, hinge H at y=0,z=0.
Units mm.

Mechanism
  * Panel (B1): two vertical side bars + top bar, hinged on the wall frame at H.
  * B2: two shorter bars behind it, hinged on the wall frame at F = H + (-D, +h0).
    B2 is a translated copy of B1, so H-B1j-B2j-F is a parallelogram for every joint j.
  * Cross arms j (one per card per side) join B1 at s_j and B2 at s_j + (-D,h0).
    The arms therefore always stay parallel to F-H, i.e. they TRANSLATE while the panel
    rotates 0..90 degrees. Each card sits in a cradle on its two arms, so it keeps its
    orientation: it stays upright. Closed: cards overlap in a column. Open: they stand in a row.
  * x layers (one side): card +-52.5 | cradle 47.5..54 | arm 54.5..60.5 | bars 61..67
    | spacer 67..71 | wall cheek 71..77.  Counterbalance spring: panel post at height A_SP -> wall anchor at D_SP.
"""
import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix

# ---------------- parameters ----------------
CARD_W, CARD_H, CARD_T = 105.0, 165.0, 1.2
BLISTER_W, BLISTER_H, BLISTER_D = 85.0, 36.0, 16.0
PITCH = 45.0          # visible strip per card
STEP = 6.5            # depth step between cards
C0 = 8.5              # gap between the panel hinge plane and the front card
H0_OFF = 18.0         # h0: offset of the B2 pivot above the B1 pivot (keeps the bars apart)
BAR_W = 14.0
S0 = 40.0             # height of the first joint above the hinge
HOLE_D, PIN_D = 3.8, 3.0
X_CARD, X_CR0, X_CR1, X_ARM0, X_ARM1 = 52.5, 47.5, 54.0, 54.5, 60.5
X_B0, X_B1, X_SP1, X_CH1 = 61.0, 67.0, 71.0, 77.0
A_SP = 64.0           # spring post height on the panel bar
CHEEK_ZMAX = 48.0
CHEEK_YMAX = 28.0
SLOT_CLR = 0.3
CR_WALL = 2.4


class Rack:
    def __init__(self, N):
        assert 1 <= N <= 8
        self.N = N
        self.D = max(C0 + (N - 1) * STEP + 11.0, 32.0)
        self.h0 = H0_OFF
        self.La = float(np.hypot(self.D, self.h0))
        self.Ps = PITCH + STEP * self.h0 / self.D          # joint pitch
        self.s = [S0 + j * self.Ps for j in range(N)]
        self.e = [C0 + (N - 1 - j) * STEP for j in range(N)]   # card depth behind the panel
        self.zr = [-e for e in self.e]                     # card rear face z (closed)
        self.yb = [self.s[j] + self.e[j] * self.h0 / self.D for j in range(N)]   # card bottom y
        self.y_top = self.yb[-1] + CARD_H
        self.L = self.y_top + 22.0
        self.d_sp = max(round(0.5 * self.L / 5.0) * 5.0, 150.0)   # wall anchor height of the counterbalance spring
        self.H = np.array([0.0, 0.0])      # (y, z)
        self.F = np.array([self.h0, -self.D])


# ---------------- geometry helpers ----------------
def box(x0, x1, y0, y1, z0, z1):
    return trimesh.creation.box(bounds=[[min(x0, x1), min(y0, y1), min(z0, z1)],
                                        [max(x0, x1), max(y0, y1), max(z0, z1)]])


def cylx(x0, x1, y, z, d, sections=40):
    m = trimesh.creation.cylinder(radius=d / 2, height=abs(x1 - x0), sections=sections)
    m.apply_transform(rotation_matrix(np.pi / 2, [0, 1, 0]))
    m.apply_translation([(x0 + x1) / 2, y, z])
    return m


def cylz(z0, z1, x, y, d, sections=40):
    m = trimesh.creation.cylinder(radius=d / 2, height=abs(z1 - z0), sections=sections)
    m.apply_translation([x, y, (z0 + z1) / 2])
    return m


def union(ms):
    ms = [m for m in ms if m is not None]
    return trimesh.boolean.union(ms, engine="manifold") if len(ms) > 1 else ms[0]


def diff(a, cuts):
    return trimesh.boolean.difference([a] + list(cuts), engine="manifold")


def hull_of(meshes):
    return trimesh.convex.convex_hull(np.vstack([m.vertices for m in meshes]))


def side_x(sign, x0, x1):
    return (x0, x1) if sign > 0 else (-x1, -x0)


# ---------------- parts ----------------
def bar(R, sign, y_start, y_end, zc, hole_ys):
    """vertical bar (in the y-z plane) in the bar layer, with holes at hole_ys."""
    xa, xb = side_x(sign, X_B0, X_B1)
    body = union([box(xa, xb, y_start, y_end, zc - BAR_W / 2, zc + BAR_W / 2),
                  cylx(xa, xb, y_start, zc, BAR_W)])
    cuts = [cylx(xa - 1, xb + 1, y, zc, HOLE_D, 24) for y in hole_ys]
    return diff(body, cuts)


def panel(R):
    parts = []
    for sg in (1, -1):
        parts.append(bar(R, sg, 0.0, R.L, 0.0, [0.0, A_SP] + R.s))
    top = box(-X_B1, X_B1, R.L - 14, R.L, -BAR_W / 2, BAR_W / 2)
    pockets = [cylz(-BAR_W / 2 - 1, -BAR_W / 2 + 2.2, x, R.L - 7, 6.2, 32) for x in (-30, 30)]
    return diff(union(parts + [top]), pockets)


def b2(R):
    """two bars behind the panel, hinged at F, joined by a tie bar low down near F
    (a bar at the far end would swing through the cards)."""
    y_end = R.h0 + R.s[-1] + 14.0
    parts = []
    for sg in (1, -1):
        parts.append(bar(R, sg, R.h0, y_end, -R.D, [R.h0] + [s + R.h0 for s in R.s]))
    ty = R.h0 + 14.0
    parts.append(box(-X_B1, X_B1, ty, ty + 12, -R.D - BAR_W / 2, -R.D + BAR_W / 2))
    return union(parts)


def arm(R, sign, j):
    xa, xb = side_x(sign, X_ARM0, X_ARM1)
    J1 = (R.s[j], 0.0)
    J2 = (R.s[j] + R.h0, -R.D)
    r = 6.0
    body = hull_of([cylx(xa, xb, J1[0], J1[1], 2 * r, 32), cylx(xa, xb, J2[0], J2[1], 2 * r, 32)])
    # cradle block for the card (inward of the arm), axis-aligned in world (card stays upright).
    # It stops 0.5 mm short of the arm layer; a neck inside this arm's own footprint joins it,
    # so no other arm can ever touch it.
    zr, yb = R.zr[j], R.yb[j]
    gz0, gz1 = zr - SLOT_CLR, zr + CARD_T + SLOT_CLR
    cx0, cx1 = side_x(sign, X_CR0, X_CR1)
    yz_box = dict(y0=yb - 3.0, y1=yb + 22.0, z0=gz0 - CR_WALL, z1=gz1 + CR_WALL)
    block = box(cx0, cx1, yz_box["y0"], yz_box["y1"], yz_box["z0"], yz_box["z1"])
    nk0, nk1 = side_x(sign, X_CR1 - 0.2, X_ARM0 + 0.2)
    foot = hull_of([cylx(nk0, nk1, J1[0], J1[1], 2 * r, 32), cylx(nk0, nk1, J2[0], J2[1], 2 * r, 32)])
    neck = trimesh.boolean.intersection(
        [foot, box(nk0 - 1, nk1 + 1, yz_box["y0"], yz_box["y1"], yz_box["z0"], yz_box["z1"])], engine="manifold")
    arm_m = union([body, neck, block])
    # slot for the card edge: from the inner face outward to 1.0 mm short of the arm, open at the top
    sx0, sx1 = side_x(sign, X_CR0 - 1.0, X_CARD + 1.0)
    slot = box(sx0, sx1, yb, yb + 23.0, gz0, gz1)
    # holes and nut pockets (inner face)
    nx0, nx1 = side_x(sign, X_ARM0 - 0.01, X_ARM0 + 2.6)
    cuts = [slot]
    for (y, z) in (J1, J2):
        cuts.append(cylx(xa - 1, xb + 1, y, z, HOLE_D, 24))
        cuts.append(cylx(nx0, nx1, y, z, 6.6, 6))
    return diff(arm_m, cuts)


def card(R, j):
    zr, yb = R.zr[j], R.yb[j]
    body = box(-CARD_W / 2, CARD_W / 2, yb, yb + CARD_H, zr, zr + CARD_T)
    bl = box(-BLISTER_W / 2, BLISTER_W / 2, yb + 4, yb + 4 + BLISTER_H, zr + CARD_T, zr + CARD_T + BLISTER_D)
    return union([body, bl])


def pin(sign, y, z, x_tail, x_head0, head_d=6.0, head_h=2.0):
    """M3-style bolt: shank from x_tail to x_head0 (outwards), head on top."""
    a, b = (x_tail, x_head0) if sign > 0 else (-x_head0, -x_tail)
    sh = cylx(a, b, y, z, PIN_D, 24)
    h0_, h1_ = (x_head0, x_head0 + head_h) if sign > 0 else (-x_head0 - head_h, -x_head0)
    return union([sh, cylx(h0_, h1_, y, z, head_d, 24)])


def spacer(sign, y, z):
    xa, xb = side_x(sign, X_B1, X_SP1)
    return diff(cylx(xa, xb, y, z, 8.0, 32), [cylx(xa - 1, xb + 1, y, z, HOLE_D, 24)])


def wall_parts(R):
    """returns dict name->mesh of the fixed wall frame (several meshes, tight bounding boxes)."""
    out = {}
    zb0, zb1 = -R.D - 11.0, -R.D - 8.0
    for sg in (1, -1):
        px0, px1 = side_x(sg, X_B0, X_CH1)
        cx0, cx1 = side_x(sg, X_SP1, X_CH1)
        post = box(px0, px1, -30, R.L + 8, zb0, zb1)
        cheek = box(cx0, cx1, -30, CHEEK_YMAX, zb0, CHEEK_ZMAX)
        sx0, sx1 = side_x(sg, X_B0, X_SP1 + 0.5)
        stop = box(sx0, sx1, -14, -7.0, 24, 44)
        ax0, ax1 = side_x(sg, X_SP1 + 0.5, X_CH1 - 1.0)
        tab = box(ax0, ax1, R.d_sp - 6, R.d_sp + 6, zb0, 5.0)
        m = union([post, cheek, stop, tab])
        cuts = [cylx(cx0 - 1, cx1 + 1, 0.0, 0.0, HOLE_D, 24), cylx(cx0 - 1, cx1 + 1, R.h0, -R.D, HOLE_D, 24)]
        mx = (px0 + px1) / 2
        cuts.append(cylx(ax0 - 1, ax1 + 1, R.d_sp, 0.0, HOLE_D, 24))
        for y in (R.d_sp + 20.0, R.L - 30.0):
            cuts.append(cylz(zb0 - 1, zb1 + 1, mx + (3.0 if sg > 0 else -3.0), y, 4.5, 24))
        out["post_R" if sg > 0 else "post_L"] = diff(m, cuts)
    top = box(-X_CH1, X_CH1, R.L - 14, R.L, zb0, -7.4)
    pockets = [cylz(-7.4 - 2.2, -7.4 + 1, x, R.L - 7, 6.2, 32) for x in (-30, 30)]
    out["top_crossbar"] = diff(top, pockets)
    out["bottom_crossbar"] = box(-X_CH1, X_CH1, -30, -22, zb0, zb1)
    return out


# ---------------- assembly ----------------
def build(N):
    """returns (rack, parts) where parts: name -> dict(mesh, group, kind)."""
    R = Rack(N)
    P = {}
    for k, m in wall_parts(R).items():
        P[k] = dict(mesh=m, group="fixed")
    P["panel"] = dict(mesh=panel(R), group="panel")
    P["b2"] = dict(mesh=b2(R), group="b2")
    for sg, tag in ((1, "R"), (-1, "L")):
        P[f"spacerH_{tag}"] = dict(mesh=spacer(sg, 0.0, 0.0), group="fixed")
        P[f"spacerF_{tag}"] = dict(mesh=spacer(sg, R.h0, -R.D), group="fixed")
        P[f"pinH_{tag}"] = dict(mesh=pin(sg, 0.0, 0.0, X_B0 - 1.0, X_CH1, 6.0, 2.0), group="fixed")
        P[f"pinF_{tag}"] = dict(mesh=pin(sg, R.h0, -R.D, X_B0 - 1.0, X_CH1, 6.0, 2.0), group="fixed")
        P[f"springpost_{tag}"] = dict(mesh=pin(sg, A_SP, 0.0, X_B0 - 0.5, X_SP1 + 4.0, 7.0, 1.5), group="panel")
    for j in range(N):
        g = f"j{j}"
        P[f"card{j}"] = dict(mesh=card(R, j), group=g)
        for sg, tag in ((1, "R"), (-1, "L")):
            P[f"arm{j}_{tag}"] = dict(mesh=arm(R, sg, j), group=g)
            P[f"pin1_{j}_{tag}"] = dict(mesh=pin(sg, R.s[j], 0.0, X_ARM0 + 0.5, X_B1), group=g)
            P[f"pin2_{j}_{tag}"] = dict(mesh=pin(sg, R.s[j] + R.h0, -R.D, X_ARM0 + 0.5, X_B1), group=g)
    return R, P


def rot_about(phi_deg, y0, z0):
    """opening rotation about the x axis through (y0, z0); positive phi moves the top toward +z."""
    T = rotation_matrix(np.radians(phi_deg), [1, 0, 0], point=[0, y0, z0])
    return T


def spring_mesh(R, phi_deg, sign):
    """thin rod standing in for the extension spring from the panel post to the wall anchor."""
    TH = rot_about(phi_deg, 0.0, 0.0)
    A = (TH @ np.array([0.0, A_SP, 0.0, 1.0]))[:3]
    W = np.array([0.0, R.d_sp, 0.0])
    x = sign * (X_SP1 + 2.5)
    d = W - A
    d[0] = 0.0
    u = d / np.linalg.norm(d)
    p0 = np.array([x, *(A[1:] + 6.0 * u[1:])])          # stop 6 mm short of each end (hooks)
    p1 = np.array([x, *(W[1:] - 12.0 * u[1:])])
    return trimesh.creation.cylinder(radius=3.0, segment=[p0, p1], sections=12)


def pose_transforms(R, P, phi_deg):
    """4x4 transform per part at panel angle phi."""
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
            Jp = TH @ J
            T = np.eye(4)
            T[:3, 3] = (Jp - J)[:3]
            out[name] = T
    return out


def posed(R, P, phi_deg):
    tr = pose_transforms(R, P, phi_deg)
    return {n: d["mesh"].copy().apply_transform(tr[n]) for n, d in P.items()}


if __name__ == "__main__":
    import sys
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    R, P = build(N)
    print("N", N, "D", round(R.D, 1), "La", round(R.La, 1), "Ps", round(R.Ps, 2), "L", round(R.L, 1))
    for k, d in P.items():
        m = d["mesh"]
        print(f"{k:16s} watertight={m.is_watertight} vol={m.volume:9.1f}")
