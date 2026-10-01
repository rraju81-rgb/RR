"""Builds STL files for the Side-Slide Shingle Rack (same parameters as side_slide_rack.scad).
Usage: python3 build_stl.py            -> rack_8slot.stl, rack_2slot_test.stl
Needs: pip install trimesh manifold3d numpy
Orientation: plate face on the print bed (z up = out of the wall), units mm."""
import numpy as np
import trimesh

card_w, card_h, card_t, blister_h = 105, 165, 1.2, 42
pitch, step = 55, 4.6
back_t, spine_w, ledge_h, gutter_d, slop = 3, 14, 10, 6, 0.3
rear_wall, front_wall, thumb_out = 2.4, 2.4, 8
gw = card_t + 2 * slop
ledge_w = spine_w + card_w - thumb_out
zc = lambda j: 1 + j * step

assert step >= rear_wall + slop + card_t + 0.4
assert ledge_h - gutter_d + blister_h <= pitch

def box(x0, x1, y0, y1, z0, z1):
    return trimesh.creation.box(bounds=[[x0, y0, z0], [x1, y1, z1]])

def cyl(x, y, z0, z1, d, sections=48):
    m = trimesh.creation.cylinder(radius=d / 2, height=z1 - z0, sections=sections)
    m.apply_translation([x, y, (z0 + z1) / 2])
    return m

def union(meshes):
    return trimesh.boolean.union(meshes, engine="manifold")

def build(N):
    H = (N - 1) * pitch + ledge_h - gutter_d + card_h + 5
    parts = [box(0, spine_w, 0, H, -back_t, 0)]
    for j in range(N):
        y0 = j * pitch
        z0 = zc(j) - slop - rear_wall
        z1 = zc(j) + card_t + slop + front_wall
        zg0, zg1 = zc(j) - slop, zc(j) + card_t + slop
        parts += [
            box(0, spine_w, y0, y0 + ledge_h, 0, z1),                       # spine block
            box(spine_w, ledge_w, y0, y0 + ledge_h - gutter_d, z0, z1),     # ledge floor
            box(spine_w, ledge_w, y0, y0 + ledge_h, z0, zg0),               # rear wall
            box(spine_w, ledge_w, y0, y0 + ledge_h, zg1, z1),               # front wall
        ]
        bump = trimesh.creation.icosphere(subdivisions=2, radius=0.7)       # detent bump
        bump.apply_translation([spine_w + card_w - thumb_out - 12,
                                y0 + ledge_h - gutter_d + 2, zg0 - 0.4 + 0.0])
        parts.append(bump)
    rack = union(parts)
    # keyholes through the wall plate (round head + slot running up)
    ys = sorted({ledge_h + 18, (N // 2 - 1) * pitch + ledge_h + 18,
                 (N - 1) * pitch + ledge_h + 18})   # each sits in the gap above a ledge
    cuts = []
    for y in ys:
        x = spine_w / 2
        cuts.append(cyl(x, y, -back_t - 1, 1, 9))
        for t in np.linspace(0, 12, 7):
            cuts.append(cyl(x, y + t, -back_t - 1, 1, 4.5, 24))
    rack = trimesh.boolean.difference([rack, union(cuts)], engine="manifold")
    rack.apply_translation([0, 0, back_t])   # plate underside on z = 0
    return rack

for N, name in [(8, "rack_8slot.stl"), (2, "rack_2slot_test.stl")]:
    m = build(N)
    m.export(name)
    print(name, "watertight:", m.is_watertight, "bbox:", np.round(m.extents, 1),
          "volume cm3:", round(m.volume / 1000, 1))
