import trimesh, numpy as np, manifold3d as mf
EXT = 15.0  # +1.5 cm widget width
rack = trimesh.load('rack_6slot.stl')
ledge = trimesh.load('ledge.stl')

# 1) stretch the 6 slot arms: move arm tips (x>85) outwards; arm faces are x-parallel so this is a clean stretch
v = rack.vertices.copy(); v[v[:,0] > 85, 0] += EXT
rack = trimesh.Trimesh(v, rack.faces, process=True)
rack_ext = rack.copy()

# 2) stretch the ledge card groove the same amount (keep hinge boss + end stops unchanged)
w = ledge.vertices.copy(); w[w[:,0] > 35, 0] += EXT
ledge = trimesh.Trimesh(w, ledge.faces, process=True)
ledge_ext = ledge.copy()

# 3) fill the ledge's hinge bore (it gets fused to the spine, a pin hole is not needed)
bore = trimesh.creation.cylinder(radius=4.6, height=18.0, sections=96)
bore.apply_translation([6.6, 6.6, 9.0])
ledge = trimesh.boolean.union([ledge, bore], engine='manifold')

# 4) stand the ledge up: ledge Z -> rack Y (up), ledge Y -> rack Z (out of wall), rotation about X by -90deg
#    offset so the ledge card groove (ledge y 5.7..7.5) lines up with the arm slot (rack z 3.7..5.5)
T = np.array([[1,0,0,0],[0,0,1,0],[0,-1,0,11.2],[0,0,0,1]], float)
ledge.apply_transform(T)
clip = trimesh.creation.box(bounds=[[-5,-5,0],[200,60,40]])
ledge = trimesh.boolean.intersection([ledge, clip], engine='manifold')

# 5) remove the bottom arm (y 0..10) but keep the 3 mm spine back plate there
cut = trimesh.creation.box(bounds=[[-1,-1,-1],[200,10.0001,12]])
keep = trimesh.creation.box(bounds=[[0,0,0],[14,10.0001,3]])
body = trimesh.boolean.difference([rack, cut], engine='manifold')
body = trimesh.boolean.union([body, keep, ledge], engine='manifold')

for name, mesh in [('rack_6slot_wide.stl', rack_ext), ('ledge_wide.stl', ledge_ext), ('rack_5slot_ledge_wide.stl', body)]:
    print(name, mesh.is_watertight, np.round(mesh.bounds,2).tolist(), round(mesh.volume,1), len(mesh.split()))
    mesh.export(name)
