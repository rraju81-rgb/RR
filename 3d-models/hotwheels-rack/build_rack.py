"""Rebuild the 6-slot Hot Wheels wall rack.

Changes vs. source/rack_6slot_original.stl:
  * Frame (backbone) is thicker and wider: 3 mm -> 6 mm thick, 14 mm -> 20 mm wide.
  * Keyhole slots removed; replaced by plain 3 mm through-holes with a
    countersink on the front face. Round holes stop the rack from rotating
    on its screws (the old keyholes let it tilt to the right).
  * Display arms replaced by the profile from source/ledge.stl (longer,
    with car end-stops). Every ledge sits flush on the wall plane (z = 0)
    instead of the old staircase offsets, and each one has a solid boss and
    a gusset where it joins the frame.

Coordinates (print orientation, back face on the bed):
  x = horizontal along the wall, y = up the wall, z = out from the wall.

Usage: pip install trimesh manifold3d numpy && python build_rack.py
"""
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import Polygon

HERE = Path(__file__).parent

# --- parameters (mm) ---------------------------------------------------------
FRAME_W = 20.0          # backbone width (x)
FRAME_T = 6.0           # backbone thickness (z)
FRAME_L = 449.0         # backbone length (y), same as original
SLOTS = 6
SLOT_PITCH = 55.0       # same spacing as original
FIRST_SLOT_Y = 15.0     # room below the bottom ledge for its gusset
HOLE_D = 3.0            # screw hole
CSINK_D = 6.5           # countersink diameter at the front face
GUSSET = 12.0           # gusset leg length under each ledge
HOLE_Y = [41.0, 151.0, 430.0]  # between ledges / near the top, spread wide

# ledge.stl geometry (its own coordinates): ring centre at x = 6.6, bar
# section spans y 2.2..11.5, floor at y 7.5..11.5, height 22 in z.
LEDGE_RING_X = 6.6
LEDGE_CUT_X = 13.4      # drop the mounting ring; the frame replaces it
LEDGE_Y_MIN, LEDGE_Y_MAX = 2.2, 11.5
LEDGE_H = 22.0


def box(x0, x1, y0, y1, z0, z1):
    b = trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0])
    b.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return b


def ledge_body():
    """ledge.stl without its ring, flipped so the floor is at the bottom
    and the end-stops sit on top, with the floor underside at y = 0."""
    m = trimesh.load(HERE / "source" / "ledge.stl")
    keep = box(LEDGE_CUT_X, 200, -1, 20, -1, 30)
    m = trimesh.boolean.intersection([m, keep], engine="manifold")
    # y -> LEDGE_Y_MAX - y; a mirror inverts the winding, so fix it after
    m.apply_transform(np.array([[1, 0, 0, 0],
                                [0, -1, 0, LEDGE_Y_MAX],
                                [0, 0, 1, 0],
                                [0, 0, 0, 1]], dtype=float))
    if m.volume < 0:
        m.invert()
    # ring centre lines up with the frame centre line
    m.apply_translation([FRAME_W / 2 - LEDGE_RING_X, 0, 0])
    return m


def gusset(y):
    tri = Polygon([(FRAME_W - 1, y + 0.5), (FRAME_W - 1, y - GUSSET),
                   (FRAME_W + GUSSET, y + 0.5)])
    return trimesh.creation.extrude_polygon(tri, height=LEDGE_H)


def countersunk_hole(y):
    through = trimesh.creation.cylinder(radius=HOLE_D / 2, height=FRAME_T * 4,
                                        sections=64)
    through.apply_translation([FRAME_W / 2, y, 0])
    depth = (CSINK_D - HOLE_D) / 2          # 90 degree countersink
    cone = trimesh.creation.cone(radius=CSINK_D / 2 + 0.5, height=depth + 0.5,
                                 sections=64)
    # cone apex points +z; flip so the wide end is on the front face
    cone.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
    cone.apply_translation([FRAME_W / 2, y, FRAME_T + 0.5])
    return [through, cone]


def build():
    parts = [box(0, FRAME_W, 0, FRAME_L, 0, FRAME_T)]
    base = ledge_body()
    ledge_h = LEDGE_Y_MAX - LEDGE_Y_MIN
    for i in range(SLOTS):
        y = FIRST_SLOT_Y + i * SLOT_PITCH
        lg = base.copy()
        lg.apply_translation([0, y, 0])
        parts.append(lg)
        # solid boss in the frame at the ledge root, full ledge height
        parts.append(box(0, FRAME_W, y - GUSSET, y + ledge_h, 0, LEDGE_H))
        parts.append(gusset(y))
    rack = trimesh.boolean.union(parts, engine="manifold")
    cutters = [c for hy in HOLE_Y for c in countersunk_hole(hy)]
    rack = trimesh.boolean.difference([rack] + cutters, engine="manifold")
    return rack


if __name__ == "__main__":
    rack = build()
    out = HERE / "rack_6slot_v2.stl"
    rack.export(out)
    print(out, "extents", rack.extents.round(2), "watertight", rack.is_watertight,
          "volume", round(rack.volume, 1))
