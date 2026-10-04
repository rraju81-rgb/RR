"""Rebuild the 6-slot Hot Wheels wall rack.

Changes vs. source/rack_6slot_original.stl:
  * Frame (backbone) is thicker and wider: 3 mm -> 6 mm thick, 14 mm -> 20 mm wide.
  * Keyhole slots removed; replaced by plain 3 mm through-holes with a
    countersink on the front face, so the rack can't rotate on its screws.
  * Keeps the original step-by-step display: each ledge sits STEP mm further
    from the wall than the one below it (4.6 mm, same as the original).
  * Each ledge is a car channel based on source/ledge.stl (same length, back
    wall + end stop), widened into a groove the car slides into from the open
    end: floor, back wall, chamfered front lip, end stop at the frame and a
    small retaining bump at the open end.

Coordinates (print orientation, back face on the bed):
  x = horizontal along the wall, y = up the wall, z = out from the wall.

Usage: pip install trimesh manifold3d shapely numpy && python build_rack.py
"""
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import Polygon

HERE = Path(__file__).parent

# --- frame (mm) --------------------------------------------------------------
FRAME_W = 20.0          # backbone width (x)
FRAME_T = 6.0           # backbone thickness (z)
FRAME_L = 449.0         # backbone length (y), same as original
HOLE_D = 3.0            # screw hole
CSINK_D = 6.5           # countersink diameter at the front face
HOLE_Y = [40.0, 150.0, 430.0]  # between ledges / near the top, spread wide

# --- ledges (mm) -------------------------------------------------------------
SLOTS = 6
SLOT_PITCH = 55.0       # same spacing as original
FIRST_SLOT_Y = 10.0
STEP = 4.6              # extra distance from the wall per slot (original step)
LEDGE_LEN = 122.0       # bar length of ledge.stl (128.6 minus its ring)
BACK_T = 3.0            # back wall thickness at the bottom slot (ledge.stl flange)
BACK_H = 9.3            # back wall height above floor underside (ledge.stl flange)
FLOOR_T = 3.0           # channel floor thickness
GROOVE_W = 36.0         # inside width of the groove (Hot Wheels cars are ~30-34)
LIP_T = 3.0             # front lip thickness
LIP_H = 4.0             # front lip height above the floor
END_T = 3.0             # end stop wall at the frame end
BUMP_H = 1.5            # retaining bump at the open end
BUMP_W = 6.0
BUMP_FROM_END = 6.0


def box(x0, x1, y0, y1, z0, z1):
    b = trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0])
    b.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return b


def prism_yz(points, x0, x1):
    """Extrude a polygon given in (y, z) along x from x0 to x1."""
    m = trimesh.creation.extrude_polygon(Polygon(points), height=x1 - x0)
    # extrude_polygon builds in (x, y) and extrudes along z; remap to (y, z, x)
    m.apply_transform(np.array([[0, 0, 1, x0],
                                [1, 0, 0, 0],
                                [0, 1, 0, 0],
                                [0, 0, 0, 1]], dtype=float))
    return m


def prism_xy(points, z0, z1):
    m = trimesh.creation.extrude_polygon(Polygon(points), height=z1 - z0)
    m.apply_translation([0, 0, z0])
    return m


def ledge(y, k):
    """Car channel for slot k with its floor underside at height y."""
    back = BACK_T + k * STEP               # stepped back wall thickness
    depth = back + GROOVE_W + LIP_T        # total projection from the wall
    x0 = FRAME_W - 1.0                     # overlap into the frame
    x1 = FRAME_W + LEDGE_LEN
    floor_top = y + FLOOR_T
    parts = [
        box(x0, x1, y, y + BACK_H, 0, back),          # back wall
        box(x0, x1, y, floor_top, 0, depth),          # floor
        # front lip, 45 deg underside so it prints without support and
        # guides the wheels into the groove
        prism_yz([(floor_top - 0.01, depth - LIP_T - LIP_H),
                  (floor_top - 0.01, depth),
                  (floor_top + LIP_H, depth),
                  (floor_top + LIP_H, depth - LIP_T)], x0, x1),
        # end stop at the frame end
        box(x0, FRAME_W + END_T, y, floor_top + LIP_H, 0, depth),
    ]
    # low ramped bump near the open end keeps the car from rolling out
    bx = x1 - BUMP_FROM_END
    parts.append(prism_xy([(bx - BUMP_W / 2, floor_top - 0.01),
                           (bx + BUMP_W / 2, floor_top - 0.01),
                           (bx, floor_top + BUMP_H)], back - 0.01, depth - LIP_T + 0.01))
    return parts


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
    for k in range(SLOTS):
        parts += ledge(FIRST_SLOT_Y + k * SLOT_PITCH, k)
    rack = trimesh.boolean.union(parts, engine="manifold")
    cutters = [c for hy in HOLE_Y for c in countersunk_hole(hy)]
    return trimesh.boolean.difference([rack] + cutters, engine="manifold")


if __name__ == "__main__":
    rack = build()
    out = HERE / "rack_6slot_v2.stl"
    rack.export(out)
    print(out, "extents", rack.extents.round(2), "watertight", rack.is_watertight,
          "volume", round(rack.volume, 1))
