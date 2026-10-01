"""Flat-fold hook tile: ONE printed part per card, hook arm prints in place, thin (8 mm), no hardware except wall screws.

A tile is a flat slab 112 x 24 x 8 mm screwed to the wall. In the slab sits a flat hook arm on a VERTICAL print-in-place pin.
Folded, the arm lies flush in a pocket in the front face. Swung out 90 degrees (a short stop makes it stop there) it points out of the wall and
a card hangs on it through its hang hole. Because the hinge axis is vertical, the card's weight never tries to fold the arm.
Tiles snap side by side (tongue and groove) at 112 mm pitch; stack rows 185 mm apart for a grid.

Wall coordinates: x right, y up, z out of the wall. Tile occupies x 0..112, y 0..24, z 0..8 (front face z = 8).
Print orientation: front face down (flip about x), so the arm lies on the bed and the pocket opens downward: no supports.
"""
import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix
from rack_helpers import box, cylz, cylx, cyly, union, diff, hull_of

W, HT, T = 112.0, 24.0, 8.0
FLAP_T, FLAP_H = 4.0, 4.5          # arm cross-section (z when folded x y); diagonal 6.0 mm so it passes a >= 6.5 mm hang hole
TAB = 28.0                          # hinge axis to tip
HEEL = 4.0                          # stop heel behind the axis
CL = 0.40                           # clearance all round (radial)
PIN_D, HOLE_D, PIN_LEN = 3.0, 3.8, 3.0
XH, YH = W / 2.0, HT / 2.0
ZH = T - FLAP_T / 2.0
ALPHA_MAX = 84.0                    # pocket cut-out is swept to this angle; clearance makes the real stop about 90
SCREW_X = (14.0, W - 14.0)
SCREW_D, CSK_D, CSK_H = 4.5, 8.6, 2.0
KEY_H, KEY_L, KEY_CL = 8.0, 3.0, 0.25
CARD_W, CARD_H, CARD_T = 105.0, 165.0, 1.2
BLISTER_W, BLISTER_H, BLISTER_D = 85.0, 36.0, 16.0
CARD_TOP, CARD_HOLE = 12.0, 7.0     # hang hole centre 12 mm below the card top (assumed)


def flap_body():
    # chamfered tip so it enters the hang hole easily
    cham = hull_of([box(XH + TAB - 2.0, XH + TAB - 1.99, YH - FLAP_H / 2, YH + FLAP_H / 2, T - FLAP_T, T),
                    box(XH + TAB - 0.01, XH + TAB, YH - FLAP_H / 2 + 0.8, YH + FLAP_H / 2 - 0.8, T - FLAP_T + 0.8, T - 0.8)])
    body = union([box(XH - HEEL, XH + TAB - 2.0, YH - FLAP_H / 2, YH + FLAP_H / 2, T - FLAP_T, T), cham])
    pin = cyly(YH - FLAP_H / 2 - PIN_LEN, YH + FLAP_H / 2 + PIN_LEN, XH, ZH, PIN_D, 28)
    return union([body, pin])


def flap(alpha_deg=0.0):
    m = flap_body()
    if alpha_deg:
        m.apply_transform(rotation_matrix(-np.radians(alpha_deg), [0, 1, 0], point=[XH, YH, ZH]))
    return m


def _cut_shape():
    return box(XH - HEEL - CL, XH + TAB + CL, YH - FLAP_H / 2 - CL, YH + FLAP_H / 2 + CL, T - FLAP_T - CL, T + 2.0)


def _hole():
    """pin hole along y, teardrop with the apex toward the rear (up when printed front-down)."""
    y0, y1 = YH - FLAP_H / 2 - CL - PIN_LEN - 0.3, YH + FLAP_H / 2 + CL + PIN_LEN + 0.3
    c = cyly(y0, y1, XH, ZH, HOLE_D, 32)
    apex = box(XH - 0.05, XH + 0.05, y0, y1, ZH - HOLE_D / 2 * 1.414, ZH - HOLE_D / 2 * 0.7)
    return hull_of([c, apex])


def tile():
    body = box(0, W, 0, HT, 0, T)
    cuts = []
    sweep = []
    for a in np.arange(0.0, ALPHA_MAX + 0.01, 2.0):
        c = _cut_shape()
        c.apply_transform(rotation_matrix(-np.radians(a), [0, 1, 0], point=[XH, YH, ZH]))
        sweep.append(c)
    cuts.append(union(sweep))
    cuts.append(_hole())
    for x in SCREW_X:
        cuts.append(cylz(-1, T + 1, x, YH, SCREW_D, 24))
        cuts.append(hull_of([cylz(T - CSK_H, T - CSK_H + 0.01, x, YH, SCREW_D, 24), cylz(T, T + 0.01, x, YH, CSK_D, 24)]))
    # groove on the left side, tongue on the right
    cuts.append(box(-1, KEY_L + KEY_CL, YH - KEY_H / 2 - KEY_CL, YH + KEY_H / 2 + KEY_CL, -1, T + 1))
    m = diff(body, cuts)
    tongue = box(W - 0.5, W + KEY_L, YH - KEY_H / 2, YH + KEY_H / 2, 0, T)
    return union([m, tongue])


def to_print(m):
    """flip front face down: rotate 180 about x, then shift to the bed."""
    m = m.copy()
    m.apply_transform(rotation_matrix(np.pi, [1, 0, 0]))
    m.apply_translation([0, -m.bounds[0][1], -m.bounds[0][2]])
    return m


def print_assembly():
    """tile + arm folded, in the print orientation (this is the STL to print)."""
    t, f = tile(), flap(0.0)
    both = union([t, f]) if False else trimesh.util.concatenate([t, f])
    return to_print(both)


def card(x_center, y_hole, z_back):
    top = y_hole + CARD_TOP
    body = diff(box(x_center - CARD_W / 2, x_center + CARD_W / 2, top - CARD_H, top, z_back, z_back + CARD_T),
                [cylz(z_back - 1, z_back + CARD_T + 1, x_center, y_hole, CARD_HOLE, 28)])
    bl = box(x_center - BLISTER_W / 2, x_center + BLISTER_W / 2, top - CARD_H + 4, top - CARD_H + 4 + BLISTER_H, z_back + CARD_T, z_back + CARD_T + BLISTER_D)
    return union([body, bl])


if __name__ == "__main__":
    t, f = tile(), flap(0.0)
    print("tile", t.is_watertight, [round(float(v), 1) for v in t.extents], "flap", f.is_watertight, [round(float(v), 1) for v in f.extents])
    print("print size", [round(float(v), 1) for v in print_assembly().extents])
