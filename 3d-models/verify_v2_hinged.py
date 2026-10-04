import trimesh, numpy as np
from trimesh.transformations import rotation_matrix, translation_matrix
fixed = trimesh.load('_fixed.stl'); moving = trimesh.load('_moving.stl').split()
axes = np.load('_axes.npy')
moving = sorted(moving, key=lambda m: m.bounds[0,1])
I = lambda a,b: trimesh.boolean.intersection([a,b], engine='manifold').volume
print('parts:', len(moving))
for k, m in enumerate(moving):
    ax = axes[k]; row = []
    for th in [-3, 0, 15, 30, 45, 60, 90, 110]:
        # positive = ledge tip swings out away from the wall (+x -> +z); rotation about +Y by -th
        R = rotation_matrix(np.radians(-th), [0,1,0], point=[ax[0], 0, ax[2]])
        mm = m.copy(); mm.apply_transform(R)
        v = I(mm, fixed); row.append(f'{th}:{v:.2f}')
    # clearance at rest: shift moving 0.3 mm in each direction, must still not touch fixed
    sh = max(I(m.copy().apply_transform(translation_matrix(d)), fixed)
             for d in [[.3,0,0],[-.3,0,0],[0,.3,0],[0,-.3,0],[0,0,.3],[0,0,-.3]])
    print(f'ledge {k}: overlap by angle', ' '.join(row), f'| 0.3mm shift overlap {sh:.3f}')
