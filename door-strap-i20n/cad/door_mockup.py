"""Illustrative door-trim patch used only for the 'installed' render.

NOT a scan of the i20 N door card - it simply shows how the module face sits
in the recessed, ribbed handle pocket behind the trim aperture.
"""
import cadquery as cq

import door_strap as ds

POCKET_X = (-80.0, 170.0)
POCKET_H = 96.0
POCKET_RR, POCKET_RF = 34.0, 42.0
TRIM_Y = -12.0          # trim front surface (occupant side)
APERTURE_GAP = 0.5


POCKET_H_FRONT = 88.0


def _pocket_pts():
    x0, x1 = POCKET_X
    return [(x0, -POCKET_H / 2), (x1, -POCKET_H_FRONT / 2),
            (x1, POCKET_H_FRONT / 2), (x0, POCKET_H / 2)]


RADII = (POCKET_RR, POCKET_RF, POCKET_RF, POCKET_RR)


def _outline():
    return ds.poly_wire(_pocket_pts(), RADII)


def build_trim():
    slab = ds.box(-260, 380, TRIM_Y, 16.0, -190, 190)
    # room behind the trim for the module's flange and screw ears
    slab = slab.cut(ds.box(-95, 95, ds.FLANGE_Y0 - 0.5, 20, -50, 50))
    pocket = _outline().extrude(-60).translate((0, -40, 0))
    pocket = pocket.cut(ds.torus())
    slab = slab.cut(pocket)
    try:
        slab = slab.faces("<Y").edges("not %LINE").fillet(5.0)
    except Exception:
        pass
    # aperture for the module
    slab = slab.cut(ds.outline_prism(APERTURE_GAP, -40, 40))
    # grooves continue across the fixed part of the pocket
    P = ds.outline_points(-9.0, _pocket_pts(), RADII)
    for zg in ds.GROOVE_Z:
        ext = ds._crossings(P, zg, 1)
        if ext:
            slab = slab.cut(ds.groove_tool(zg, ds.FACE_L / 2 + 9.0,
                                           ext[1] - ds.GROOVE_R))
    return slab
