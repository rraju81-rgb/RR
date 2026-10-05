import trimesh, numpy as np
from trimesh.creation import box
TOTAL = 134.0          # hinged v2: knuckle uses ~3.5 mm of the groove start, so 4 mm longer for the same 108+ mm card space
STOP_H = 10.0          # front corner support height (was 7 mm; lip in between stays 4 mm)
l = trimesh.load('6907ae8d-ledge.stl')                 # original ledge, 128.6 mm
d = TOTAL - l.bounds[1, 0]
v = l.vertices.copy(); v[v[:, 0] > 35, 0] += d          # shorten the plain middle section only
l = trimesh.Trimesh(v, l.faces, process=True)
for x0, x1 in [(21.7, 30.5), (TOTAL - 9.0, TOTAL)]:    # left / right corner supports (lip side of the groove)
    l = trimesh.boolean.union([l, box(bounds=[[x0, 2.2, 0], [x1, 6.15, STOP_H]])], engine='manifold')
print(l.is_watertight, np.round(l.bounds, 2).tolist())
l.export('ledge_134.stl')
