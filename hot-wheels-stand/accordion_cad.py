"""Accordion hook rack (lazy-tongs frame). The frame IS the mechanism; cards hang from printed hooks.

4 printed designs, all printable flat or on their side with no supports:
  link        flat bar, 3 holes (qty 2K)               K = stalls - 1 cells
  pivot_pin   snap pin (head + split barb)             qty 2K (K centre pivots, K-1 upper nodes, 1 slot pin)
  hook_pin    snap pin + collar + blade hook           qty N (one per card)
  wall_plate  plate with 1 hole, 1 vertical slot       qty 1

Geometry (viewed from the front, x right, y up, z out of the wall). Hooks sit on the BOTTOM row H_k = (k*w, 0);
upper row U_k = (k*w, h). w = L cos(t), h = L sin(t). H_0 is pinned in the wall plate, U_0 slides in a vertical slot,
so gravity pulls the upper row down = the rack opens by itself and rests at the open stop. Cards hang from the
hook blades, which are neutral: the hook row never changes height.
Layers (z): plate -6.4..-0.4 | link layer A (/ links) 0..5 | link layer B (\\ links) 5.4..10.4 | heads 10.9..12.5 |
hook collar 10.9..12.9 | peg 12.9..22 (5 mm round) | card 13.3..14.5, blister to 30.5.
"""
import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix
from foldout_cad import box, cylx, cylz, union, diff, hull_of

# ---------------- parameters ----------------
L_LINK = 118.0                # hole-to-hole length of a link
LINK_W, LINK_T = 12.0, 5.0
HOLE_D, PIN_D = 4.4, 4.0      # 0.2 mm radial clearance
ZA0, ZA1, ZB0, ZB1 = 0.0, 5.0, 5.4, 10.4
HEAD_Z0, HEAD_Z1, HEAD_D = 10.9, 12.5, 8.0
BARB_TIP_Z, BARB_Z0, BARB_Z1, BARB_D = -6.0, -4.4, -3.4, 5.8     # barb sits in the plate's rear groove (shoulder behind the front part)
PLATE_Z0, PLATE_Z1 = -6.4, -0.4
PLATE_FRONT_Z0 = -3.2         # front part of the plate (holds the barb shoulder) is -3.2..-0.4
SLOT_W, GROOVE_W = 4.6, 8.0
PLATE_HALF_W = 16.0
COLLAR_Z0, COLLAR_Z1, COLLAR_D = 10.9, 12.9, 14.0
PEG_Z1, PEG_D, CARD_HOLE_D = 22.0, 5.0, 7.0
TH_MIN, TH_MAX = np.radians(14.0), np.radians(70.0)
CARD_W, CARD_H, CARD_T = 105.0, 165.0, 1.2
CARD_TOP, BLISTER_W, BLISTER_H, BLISTER_D = 12.0, 85.0, 36.0, 16.0   # hole sits 12 mm below the card top
CARD_Z = COLLAR_Z1 + 0.4
BED = 300.0


class Acc:
    def __init__(self, N):
        assert 1 <= N <= 8
        self.N, self.K = N, N - 1
        self.L = L_LINK
        self.h_min, self.h_max = self.L * np.sin(TH_MIN), self.L * np.sin(TH_MAX)
        self.w_open, self.w_closed = self.L * np.cos(TH_MIN), self.L * np.cos(TH_MAX)

    def wh(self, th):
        return self.L * np.cos(th), self.L * np.sin(th)


# ---------------- parts ----------------
def link_mesh():
    r = LINK_W / 2
    L = L_LINK
    body = hull_of([cylz(ZA0, ZA1, -L / 2, 0.0, 2 * r, 40), cylz(ZA0, ZA1, L / 2, 0.0, 2 * r, 40)])
    cuts = [cylz(ZA0 - 1, ZA1 + 1, x, 0.0, HOLE_D, 28) for x in (-L / 2, 0.0, L / 2)]
    return diff(body, cuts)


def _pin_core(z_head1):
    shank = cylz(BARB_Z1, z_head1, 0, 0, PIN_D, 28)
    tip = cylz(BARB_TIP_Z, BARB_TIP_Z + 0.01, 0, 0, 3.0, 24)
    r1 = cylz(BARB_Z0, BARB_Z0 + 0.01, 0, 0, BARB_D, 24)
    barb = hull_of([tip, r1])
    flat = cylz(BARB_Z0, BARB_Z1, 0, 0, BARB_D, 24)
    return union([shank, barb, flat])


def _kerf():
    return box(-4.0, 4.0, -0.5, 0.5, BARB_TIP_Z - 1, -0.4)          # splits the barb in two (flexes in y)


def pivot_pin():
    head = cylz(HEAD_Z0, HEAD_Z1, 0, 0, HEAD_D, 32)
    return diff(union([_pin_core(HEAD_Z0 + 0.2), head]), [_kerf()])


def hook_pin():
    collar = cylz(COLLAR_Z0, COLLAR_Z1, 0, 0, COLLAR_D, 40)
    peg = cylz(COLLAR_Z1 - 0.2, PEG_Z1 - 1.0, 0, 0, PEG_D, 28)
    tip = hull_of([cylz(PEG_Z1 - 1.0, PEG_Z1 - 0.99, 0, 0, PEG_D, 28), cylz(PEG_Z1 - 0.01, PEG_Z1, 0, 0, PEG_D - 1.6, 28)])
    return diff(union([_pin_core(COLLAR_Z0 + 0.2), collar, peg, tip]), [_kerf()])


def wall_plate(A):
    K = A.K
    ytop = (A.h_max if K >= 1 else 0.0) + 22.0
    ybot = -22.0
    body = box(-PLATE_HALF_W, PLATE_HALF_W, ybot, ytop, PLATE_Z0, PLATE_Z1)
    cuts = [cylz(PLATE_Z0 - 1, PLATE_Z1 + 1, 0.0, 0.0, HOLE_D, 28),
            cylz(PLATE_Z0 - 1, PLATE_FRONT_Z0 + 0.0, 0.0, 0.0, GROOVE_W, 32)]          # pocket for the H_0 barb
    if K >= 1:
        r = SLOT_W / 2
        cuts.append(hull_of([cylz(PLATE_Z0 - 1, PLATE_Z1 + 1, 0.0, A.h_min, SLOT_W, 28),
                             cylz(PLATE_Z0 - 1, PLATE_Z1 + 1, 0.0, A.h_max, SLOT_W, 28)]))
        cuts.append(box(-GROOVE_W / 2, GROOVE_W / 2, A.h_min - 4.5, A.h_max + 4.5, PLATE_Z0 - 1, PLATE_FRONT_Z0))
    for (x, y) in screw_points(A):
        cuts.append(cylz(PLATE_Z0 - 1, PLATE_Z1 + 1, x, y, 4.5, 24))
    return diff(body, cuts)


def screw_points(A):
    ytop = (A.h_max if A.K >= 1 else 0.0) + 22.0
    pts = [(-12.0, -10.0), (-12.0, ytop - 8.0)]
    if A.K >= 1:
        pts.append((12.0, ytop - 8.0))
        pts.append((12.0, -10.0))
    return pts


def screw_head(x, y):
    return cylz(PLATE_Z1, PLATE_Z1 + 3.0, x, y, 8.0, 24)


def card_mesh(x):
    body = diff(box(x - CARD_W / 2, x + CARD_W / 2, -CARD_H + CARD_TOP, CARD_TOP, CARD_Z, CARD_Z + CARD_T),
                [cylz(CARD_Z - 1, CARD_Z + CARD_T + 1, x, 0.0, CARD_HOLE_D, 28)])      # the hang hole
    bl = box(x - BLISTER_W / 2, x + BLISTER_W / 2, -CARD_H + CARD_TOP + 4, -CARD_H + CARD_TOP + 4 + BLISTER_H,
             CARD_Z + CARD_T, CARD_Z + CARD_T + BLISTER_D)
    return union([body, bl])


# ---------------- assembly at an opening angle ----------------
def build_templates():
    return dict(link=link_mesh(), pivot=pivot_pin(), hook=hook_pin())


def assembly(A, th, T, with_cards=True):
    """returns dict name -> (mesh, group). group names used by the tests."""
    out = {}
    w, h = A.wh(th)
    plate = wall_plate(A) if "plate" not in T else T["plate"]
    out["plate"] = (plate, "fixed")
    for k in range(A.N):
        m = T["hook"].copy()
        m.apply_translation([k * w, 0.0, 0.0])
        out[f"hook{k}"] = (m, f"hook{k}")
        if with_cards:
            out[f"card{k}"] = (card_mesh(k * w), f"hook{k}")
    for i in range(1, A.K + 1):
        cx, cy = (i - 0.5) * w, h / 2
        for tag, ang, z0 in (("A", th, ZA0), ("B", -th, ZB0)):
            m = T["link"].copy()
            m.apply_translation([0, 0, z0])
            m.apply_transform(rotation_matrix(ang, [0, 0, 1]))
            m.apply_translation([cx, cy, 0])
            out[f"link{tag}{i}"] = (m, f"link{tag}{i}")
        p = T["pivot"].copy()
        p.apply_translation([cx, cy, 0])
        out[f"pivC{i}"] = (p, f"pivC{i}")
    for k in range(0, A.K):          # upper row nodes U_0..U_{K-1}
        p = T["pivot"].copy()
        p.apply_translation([k * w, h, 0])
        out[f"pivU{k}"] = (p, f"pivU{k}")
    return out


def hardware(A):
    return {f"screw{i}": screw_head(x, y) for i, (x, y) in enumerate(screw_points(A))}


def joints(A, th):
    """world positions of every pin and which links it joins (for closure / statics)."""
    w, h = A.wh(th)
    J = []
    for i in range(1, A.K + 1):
        J.append(dict(name=f"C{i}", pos=((i - 0.5) * w, h / 2), links=(f"A{i}", f"B{i}")))
    for k in range(1, A.K):
        J.append(dict(name=f"H{k}", pos=(k * w, 0.0), links=(f"B{k}", f"A{k + 1}")))
        J.append(dict(name=f"U{k}", pos=(k * w, h), links=(f"A{k}", f"B{k + 1}")))
    return J


if __name__ == "__main__":
    import sys
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    A = Acc(N)
    T = build_templates()
    for n, m in T.items():
        print(n, "watertight", m.is_watertight, [round(x, 1) for x in m.extents])
    P = wall_plate(A)
    print("plate", P.is_watertight, [round(x, 1) for x in P.extents])
    print("open spacing", round(A.w_open, 1), "closed", round(A.w_closed, 1), "h", round(A.h_min, 1), round(A.h_max, 1))
