"""Build the final car: body (marching cubes) -> clean -> conform under the spoiler -> details."""
import sys, time; sys.path.insert(0, 'v6/car/src')
import numpy as np, trimesh
from car_body import build_mesh
from car_conform import conform
from car_detail import build
step = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
t = time.time()
car = build_mesh(step=step)
car.update_faces(car.nondegenerate_faces()); car.update_faces(car.unique_faces()); car.remove_unreferenced_vertices()
print('body', len(car.faces), 'faces  %.0fs' % (time.time() - t))
car.export('v6/car/out/car_body_base.ply')
E = trimesh.load('v6/out/E2.stl')
carc, d = conform(car, E)
assert len(carc.vertices) == len(car.vertices)
carc.export('v6/car/out/car_body_conf.ply')
np.save('v6/car/out/covered.npy', carc.metadata['covered'].astype(np.float32))
# de-noised shading normals for blend_scene (cached here so they always match the meshes)
from car_zones import smooth_normals
for nm, m in [('base', car), ('conf', carc)]:
    np.save(f'v6/car/out/normals_{nm}.npy', smooth_normals(np.asarray(m.vertices), np.asarray(m.faces)).astype(np.float32))
D = build(carc)
for k, m in D.items():
    if m is not None: m.export(f'v6/car/out/{k}.stl')
print('done %.0fs' % (time.time() - t))
