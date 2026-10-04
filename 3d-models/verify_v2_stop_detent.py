import trimesh, numpy as np
from trimesh.transformations import rotation_matrix, translation_matrix
fixed = trimesh.load('_fixed.stl'); axes = np.load('_axes.npy')
moving = sorted(trimesh.load('_moving.stl').split(), key=lambda m: m.bounds[0, 1])
I = lambda a, b: trimesh.boolean.intersection([a, b], engine='manifold').volume
def pose(m, k, th, dy):
    mm = m.copy(); mm.apply_transform(rotation_matrix(np.radians(-th), [0, 1, 0], point=[axes[k][0], 0, axes[k][2]]))
    mm.apply_translation([0, dy, 0]); return mm
for k, m in enumerate(moving):
    printed = max(I(m.copy().apply_translation(d) or m.copy(), fixed) for d in [[0,0,0]])
    shifts = max(I(pose(m, k, 0, 0).apply_transform(translation_matrix(d)) or 0, fixed) if False else
                 I(trimesh.Trimesh(m.vertices + d, m.faces), fixed) for d in [[.3,0,0],[-.3,0,0],[0,.3,0],[0,-.3,0],[0,0,.3],[0,0,-.3]])
    # in use: settled 0.4 mm down at rest; riding 0.2 mm above printed height (on top of the 0.6 mm bump) while swinging
    rest = I(pose(m, k, 0, -0.39), fixed)
    ride = max(I(pose(m, k, th, +0.25), fixed) for th in [6, 15, 30, 45, 60, 90, 110])
    back = {th: round(I(pose(m, k, th, -0.39), fixed), 2) for th in [-1, -2, -3, -5]}
    held = round(I(pose(m, k, 8, -0.39), fixed), 2)   # swung 8 deg but not lifted -> must hit the bump
    print(f'tier {k}: printed {printed:.3f} | 0.3mm shifts {shifts:.3f} | settled at 0deg {rest:.3f} | '
          f'swinging on bump {ride:.3f} | unlifted at 8deg (detent) {held} | backwards {back}')
