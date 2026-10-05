"""
5-tier folding card easel, print-in-place, single hinge.

Redesign of table_easel_3card_folding.stl:
  * the top (kickstand) hinge and the kickstand panel are removed; only the
    bottom hinge between the card panel and the base is kept
  * the ribbed base ("back support") is narrowed from 119 mm to a 40 mm leg
  * 5 card ledges instead of 3
  * everything prints flat on the bed in one plane (no stacked panels with
    0.5 mm air gaps, no long bridges, no support material)

Hinge: alternating knuckles with 45-degree cone pins (no bridged pin, every
overhang <= 45 deg). The angle is held by a V-shaped stop under the hinge: the
two chamfered plate ends close flush when the panel is folded to STAND_ANGLE,
so the panel can't lean back further.

Coordinates (print frame): bed is z = 0, hinge axis runs along X at
y = 0, z = HINGE_R. Card panel is +Y, base leg is -Y.

Run:  python3 card_easel.py   -> writes STL files next to this script.
Requires: manifold3d, numpy, trimesh
"""

import math
import os

import numpy as np
import trimesh
from manifold3d import Manifold, CrossSection

# ---------------------------------------------------------------- parameters
WIDTH = 119.0            # panel width (X), same as original

# hinge
HINGE_R = 4.5            # knuckle radius (axis height above bed)
KNUCKLES = 11            # odd: panel knuckles at both ends
KNUCKLE_GAP = 0.5        # axial gap between knuckles
RADIAL_CLEAR = 0.5       # plate clearance around the other part's knuckle
CONE_R = 3.0             # cone pin base radius (45 deg cone, height = radius)
CONE_CLEAR = 0.4         # normal clearance between cone and socket
STAND_ANGLE = 75.0       # panel angle to the table when opened (deg)

# card panel
PLATE_T = 3.0            # panel plate thickness
TIERS = 5
TIER_PITCH = 36.0        # distance between card ledges along the panel
FIRST_TIER_Y = 7.0       # first lip position from hinge axis
STEP = 4.5               # height step between tiers (= max card thickness)
TOP_TREAD = PLATE_T + 1.5  # rail height of the top tier
LIP_T = 3.0              # lip thickness (Y)
LIP_H = 3.0              # lip height above tread
RAIL_T = 3.0             # rail thickness (X)
RAIL_X = [0.0, 37.0, WIDTH - 37.0 - RAIL_T, WIDTH - RAIL_T]  # rail left edges
TOP_EXTRA = 40.0         # panel length above the top lip

# base leg
BASE_T = 4.0             # base plate thickness
BASE_BAR = 12.0          # full-width hinge bar depth (from axis)
LEG_W = 40.0             # leg width (was 119)
LEG_L = 55.0             # leg length from hinge axis
PAD_L = 8.0              # foot pad length at leg end

SEG = 96                 # circle resolution

HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- helpers
def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def x_cyl(x0, x1, r0, r1=None):
    """Cylinder/cone along +X from x0 to x1, centred on the hinge axis."""
    r1 = r0 if r1 is None else r1
    c = Manifold.cylinder(x1 - x0, r0, r1, SEG).rotate([0, 90, 0])
    return c.translate([x0, 0, HINGE_R])


def x_cone_neg(x_base, h, r):
    """Cone with base at x_base pointing toward -X."""
    c = Manifold.cylinder(h, r, 0.0, SEG).rotate([0, -90, 0])
    return c.translate([x_base, 0, HINGE_R])


def ccw(pts):
    a = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return pts if a > 0 else pts[::-1]


def union(parts):
    return Manifold.batch_boolean(parts, m3_add) if len(parts) > 1 else parts[0]


from manifold3d import OpType  # noqa: E402

m3_add = OpType.Add


def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3],
                           np.asarray(mesh.tri_verts), process=True)


# ---------------------------------------------------------------- hinge layout
FOLD = 180.0 - STAND_ANGLE            # rotation from flat to standing
HALF = math.radians(FOLD / 2.0)       # V-stop half angle from vertical
K_LEN = (WIDTH - (KNUCKLES - 1) * KNUCKLE_GAP) / KNUCKLES
knuckles = [(i * (K_LEN + KNUCKLE_GAP), i * (K_LEN + KNUCKLE_GAP) + K_LEN)
            for i in range(KNUCKLES)]
panel_k = [k for i, k in enumerate(knuckles) if i % 2 == 0]
base_k = [k for i, k in enumerate(knuckles) if i % 2 == 1]
CLEAR_R = HINGE_R + RADIAL_CLEAR
SOCKET_SHIFT = CONE_CLEAR / math.sin(math.radians(45))


def v_trim(m, side):
    """Keep the part of m on the panel (+1) / base (-1) side of the V stop."""
    n = np.array([0.0, side * math.cos(HALF), math.sin(HALF)])
    # plane through the axis line (0, 0, HINGE_R)
    return m.trim_by_plane(n.tolist(), float(n[2] * HINGE_R))


def clearance(zones, length):
    """Clearance cylinders around the other part's knuckles (incl. gaps)."""
    return union([x_cyl(max(a - KNUCKLE_GAP, -1), min(b + KNUCKLE_GAP, WIDTH + 1),
                        CLEAR_R) for a, b in zones])


# ---------------------------------------------------------------- card panel
def tier_y(k):
    return FIRST_TIER_Y + k * TIER_PITCH


def tread_h(k):  # k = 0 is the bottom (front-most) tier
    return TOP_TREAD + (TIERS - 1 - k) * STEP


PANEL_END = tier_y(TIERS - 1) + LIP_T + TOP_EXTRA


def build_panel():
    parts = [box(0, WIDTH, 0, PANEL_END, 0, PLATE_T)]

    # rails: vertical fins whose top is a descending staircase
    pts = [(FIRST_TIER_Y, 0.0)]
    for k in range(TIERS):
        y0 = tier_y(k)
        y1 = tier_y(k + 1) if k < TIERS - 1 else PANEL_END
        pts += [(y0, tread_h(k)), (y1, tread_h(k))]
    pts += [(PANEL_END, 0.0)]
    # CrossSection is in (u, v); extrude along +w. Map u->Y, v->Z, w->X.
    prof = CrossSection([ccw(pts)])
    rail = prof.extrude(RAIL_T)                    # (Y, Z, X)
    rail = rail.transform([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0]])
    for x in RAIL_X:
        parts.append(rail.translate([x, 0, 0]))

    # lips: full-width walls that catch the bottom edge of each card
    for k in range(TIERS):
        y = tier_y(k)
        parts.append(box(0, WIDTH, y, y + LIP_T, 0, tread_h(k) + LIP_H))

    panel = union(parts)

    # diamond windows in the plate between rails (saves ~25% plastic/time)
    gaps = [(RAIL_X[i] + RAIL_T, RAIL_X[i + 1]) for i in range(len(RAIL_X) - 1)]
    holes = []
    for k in range(TIERS):
        y0 = tier_y(k) + LIP_T
        y1 = tier_y(k + 1) if k < TIERS - 1 else PANEL_END - 4
        cy = (y0 + y1) / 2
        for a, b in gaps:
            d = min(b - a, y1 - y0) - 8.0          # diamond diagonal
            if d < 8:
                continue
            sq = Manifold.cube([d / math.sqrt(2)] * 2 + [PLATE_T + 2], center=True)
            holes.append(sq.rotate([0, 0, 45]).translate([(a + b) / 2, cy, PLATE_T / 2]))
    panel = panel - union(holes)

    # hinge end: V stop + clearance around base knuckles
    panel = v_trim(panel, +1) - clearance(base_k, WIDTH)

    # knuckles with cone pins
    kn = []
    for a, b in panel_k:
        kn.append(x_cyl(a, b, HINGE_R))
        if b < WIDTH - 1:   # cone into the next (base) knuckle
            kn.append(x_cyl(b - 0.5, b + CONE_R, CONE_R + 0.5, 0.0))
        if a > 1:
            kn.append(x_cone_neg(a + 0.5, CONE_R + 0.5, CONE_R + 0.5))
        # web joining the knuckle to the plate
        kn.append(v_trim(box(a, b, 0, HINGE_R + 3, 0, PLATE_T), +1))
    return union([panel] + kn)


# ---------------------------------------------------------------- base leg
def build_base():
    cx = WIDTH / 2
    bar = box(0, WIDTH, -BASE_BAR, 0, 0, BASE_T)
    leg = box(cx - LEG_W / 2, cx + LEG_W / 2, -LEG_L, -BASE_BAR + 1, 0, BASE_T)
    # foot pad: same height as the knuckles so the leg sits level
    pad = box(cx - LEG_W / 2, cx + LEG_W / 2, -LEG_L, -LEG_L + PAD_L, 0, 2 * HINGE_R)
    # fillets between bar and leg (45 deg gussets, printed flat)
    g = []
    for s in (-1, 1):
        x0 = cx + s * LEG_W / 2
        tri = CrossSection([ccw([(0, 0), (s * 10.0, 0), (0, -10.0)])])
        tri = tri.extrude(BASE_T).translate([x0, -BASE_BAR + 0.5, 0])
        g.append(tri)
    base = union([bar, leg, pad] + g)
    base = v_trim(base, -1) - clearance(panel_k, WIDTH)

    kn, sockets = [], []
    for a, b in base_k:
        kn.append(x_cyl(a, b, HINGE_R))
        # conical sockets for the panel's cone pins on both faces
        apex_r = (a - KNUCKLE_GAP) + CONE_R + SOCKET_SHIFT        # from left
        sockets.append(x_cyl(a - 0.2, apex_r, apex_r - (a - 0.2), 0.0))
        apex_l = (b + KNUCKLE_GAP) - CONE_R - SOCKET_SHIFT        # from right
        sockets.append(x_cone_neg(b + 0.2, (b + 0.2) - apex_l, (b + 0.2) - apex_l))
    return union([base] + kn) - union(sockets)


# ---------------------------------------------------------------- folded pose
def fold_panel(m, deg=FOLD):
    """Rotate the panel about the hinge axis (mountain fold)."""
    return (m.translate([0, 0, -HINGE_R]).rotate([-deg, 0, 0])
             .translate([0, 0, HINGE_R]))


def standing(panel, base):
    """Whole easel as it stands on a table (base leg underneath, z up)."""
    m = union([fold_panel(panel), base])
    # base pad top (z = 2R) goes on the table: flip 180 deg about X
    return m.rotate([180, 0, 0]).translate([0, 0, 2 * HINGE_R])


if __name__ == "__main__":
    panel = build_panel()
    base = build_base()
    flat = union([panel, base])

    print(f"knuckle length {K_LEN:.2f} mm, fold {FOLD:.0f} deg, "
          f"panel length {PANEL_END:.1f} mm")
    bb = flat.bounding_box()
    print("print bounding box (mm):",
          f"{bb[3]-bb[0]:.1f} x {bb[4]-bb[1]:.1f} x {bb[5]-bb[2]:.1f}")
    print(f"volume {flat.volume()/1000:.1f} cm3 (~{flat.volume()/1000*1.24:.0f} g PLA solid)")
    print("min gap panel<->base (flat):", round(panel.min_gap(base, 2.0), 3))
    for d in (30, 60, 90, FOLD - 1):
        fp = fold_panel(panel, d)
        print(f"  fold {d:5.1f}: overlap {(fp ^ base).volume():.3f} mm3, "
              f"gap {fp.min_gap(base, 2.0):.3f}")
    fp = fold_panel(panel, FOLD + 3)
    print(f"  fold {FOLD+3:5.1f}: overlap {(fp ^ base).volume():.1f} mm3 (stop engaged)")

    to_trimesh(flat).export(os.path.join(HERE, "card_easel_5tier_print_in_place.stl"))
    to_trimesh(standing(panel, base)).export(
        os.path.join(HERE, "card_easel_5tier_preview_standing.stl"))
    print("written.")
