import trimesh, numpy as np
B = lambda op, *m: getattr(trimesh.boolean, op)(list(m), engine='manifold')
PLATE = 6.0            # back plate 3 mm -> 6 mm (thickened toward the front; wall face stays at z=0)
HOLE_D = 3.0           # plain round screw hole replacing each keyhole
HOLE_Y = [28.0, 138.0, 303.0]   # centre of each keyhole's round part
m = trimesh.load('rack_6ledge_120.stl')

# thicken the spine plate over its full length
m = B('union', m, trimesh.creation.box(bounds=[[0, 0, 0], [14, 449, PLATE]]))
# fill the keyholes, then drill the 3 mm holes straight through the plate
for y in HOLE_Y:
    m = B('union', m, trimesh.creation.box(bounds=[[2, y-5, 0], [12, y+15, PLATE]]))
    h = trimesh.creation.cylinder(radius=HOLE_D/2, height=PLATE+4, sections=64)
    h.apply_translation([7, y, PLATE/2])
    m = B('difference', m, h)
print(m.is_watertight, np.round(m.bounds, 2).tolist(), round(m.volume, 1), len(m.split()))
m.export('rack_6ledge_120_3mmholes.stl')
