"""v11 step 1: export the owner's Polo GTI model's exterior (no interior, no factory roof spoiler) in the spoiler's car
frame (mm; X across, Y up, Z to the rear), placed by its bumpers and the ground as the old car model:
v11/out/user_exterior_carframe0.ply (and the factory spoiler alone, user_factory_wing_carframe0.ply).
Run from spoiler/:  python3 v11/src/export_model.py [path/to/FINAL_MODEL_11.fbx]"""
import sys; sys.path.insert(0, 'v6/car/src')
import bpy, numpy as np, trimesh, os
from car_body import Y_G
FBX = sys.argv[1] if len(sys.argv) > 1 else 'v11/input/FINAL_MODEL_11.fbx'
CY, CZ = -14.4 + Y_G, -1409.0                       # as blend_usercar.py: tyres on the ground, bumpers as the old model
WING = ('winga', 'trunk_tail_light', 'trunk_body_2')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=os.path.abspath(FBX))
ext, wing = [], []
for o in bpy.data.objects:
    if o.type != 'MESH' or 'cockpit' in o.name.lower(): continue
    M = np.array(o.matrix_world); V = (np.array([v.co for v in o.data.vertices]) @ M[:3, :3].T + M[:3, 3]) * 100.0 * 1000.0
    F = [[p.vertices[0], p.vertices[k], p.vertices[k + 1]] for p in o.data.polygons for k in range(1, len(p.vertices) - 1)]
    if not F: continue
    C = np.column_stack([-V[:, 0], V[:, 2] + CY, V[:, 1] + CZ])                 # model (X, Y rear, Z up) -> car frame
    m = trimesh.Trimesh(C, np.array(F)[:, ::-1], process=False)                 # the axis swap mirrors: keep faces outward
    (wing if any(k in o.name.lower() for k in WING) else ext).append(m)
os.makedirs('v11/out', exist_ok=True)
trimesh.util.concatenate(ext).export('v11/out/user_exterior_carframe0.ply')
trimesh.util.concatenate(wing).export('v11/out/user_factory_wing_carframe0.ply')
print('exterior', sum(len(m.faces) for m in ext), 'faces; factory spoiler', sum(len(m.faces) for m in wing), 'faces')
