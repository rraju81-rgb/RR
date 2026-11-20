"""Illustrative door-trim patch used only for the 'installed' render.

NOT a scan of the i20 N door card - it simply shows how the module face sits
in the recessed, ribbed handle pocket behind the trim aperture.
"""
import cadquery as cq

import door_strap as ds

POCKET_X = (-182.0, 94.0)     # native RH frame: front of car = -X
POCKET_H = 92.0               # height at the rear end (+X)
TRIM_Y = -12.0          # trim front surface (occupant side)
APERTURE_GAP = 0.5


POCKET_H_FRONT = 82.0         # height at the front end (-X)
POCKET_RR, POCKET_RF = 32.0, 40.0


def _pocket_pts():
    x0, x1 = POCKET_X
    return [(x0, -POCKET_H_FRONT / 2), (x1, -POCKET_H / 2),
            (x1, POCKET_H / 2), (x0, POCKET_H_FRONT / 2)]


RADII = (POCKET_RF, POCKET_RR, POCKET_RR, POCKET_RF)


def _outline():
    return ds.poly_wire(_pocket_pts(), RADII)


def build_trim():
    slab = ds.box(-380, 260, TRIM_Y, 16.0, -190, 190)
    # room behind the trim for the module's deck, clip pads and clips
    slab = slab.cut(ds.box(-102, 90, ds.FLANGE_Y0 - 0.5, 20, -56, 56))
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
        face = ds._crossings(ds.loop_points("face", 0.0), zg, 1)
        if ext and face:
            x1 = face[0] - 9.0          # stop short of the module (front side)
            if x1 - ext[0] > 2 * ds.GROOVE_R + 6:
                slab = slab.cut(ds.groove_tool(zg, ext[0] + ds.GROOVE_R,
                                               x1 - ds.GROOVE_R))
    return slab
