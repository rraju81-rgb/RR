"""Aero test, step 1: CFD geometry in metres for OpenFOAM (snappyHexMesh).
CFD frame: X = streamwise (air flows +X, the car's front bumper at X = 0), Y = lateral (car's x), Z = up (ground at Z = 0).
From the car/spoiler frame (x lateral, y up, z rearward, mm): X = (z - z_front)/1000, Y = x/1000, Z = (y - y_ground)/1000.
Surfaces (closed):
  body.stl       the car body with the roof shaped under the spoiler (v6/car/out/car_body_conf.ply): used WITH the spoiler
  body_base.stl  the original car body (v6/car/out/car_body_base.ply): the car WITHOUT the spoiler
  mirrors.stl  door mirrors
  wheelF.stl / wheelR.stl  front / rear wheel pairs: simple tyres (rounded cylinders), sunk 8 mm into the ground
  spoiler.stl  the finished spoiler (v6/out/E2.stl), lowered 3 mm so it seals onto the roof as the tape does
Run from spoiler/:  python3 aero/src/a1_geometry.py"""
import sys; sys.path.insert(0, 'v6/car/src')
import numpy as np, trimesh, pymeshlab, os, json
from car_body import Z_F, Y_G, S_FA, S_RA, WHEEL_R, WHEEL_W, TRACK
OUT = 'aero/out/geometry'; os.makedirs(OUT, exist_ok=True)

def to_cfd(V): return np.column_stack([(V[:, 2] - Z_F) / 1000.0, V[:, 0] / 1000.0, (V[:, 1] - Y_G) / 1000.0])
def decimate(m, n):
    ms = pymeshlab.MeshSet(); ms.add_mesh(pymeshlab.Mesh(m.vertices, m.faces))
    ms.meshing_decimation_quadric_edge_collapse(targetfacenum=n, preservenormal=True, preservetopology=True, qualitythr=0.5, planarquadric=True)
    ms.meshing_remove_duplicate_vertices(); ms.meshing_remove_unreferenced_vertices()
    c = ms.current_mesh(); return trimesh.Trimesh(c.vertex_matrix(), c.face_matrix(), process=True)
def report(name, m):
    print(f'{name:12s} faces {len(m.faces):7d} watertight {m.is_watertight} winding {m.is_winding_consistent} vol {m.volume:.4f} m3 bounds {np.round(m.bounds, 3).tolist()}')

car = trimesh.load('v6/car/out/car_body_conf.ply', process=True)
print('body (raw)', len(car.faces), 'watertight', car.is_watertight)
body = decimate(car, 320000)
if not body.is_watertight:
    trimesh.repair.fill_holes(body); trimesh.repair.fix_normals(body)
body = trimesh.Trimesh(to_cfd(body.vertices), body.faces, process=True)
if body.volume < 0: body.invert()
# the car WITHOUT the spoiler is the original body: the roof of car_body_conf was reshaped to sit 1.5 mm under the
# spoiler (for the renders), and without the spoiler on top that reshaped edge left a step on the roof
base = decimate(trimesh.load('v6/car/out/car_body_base.ply', process=True), 320000)
if not base.is_watertight: trimesh.repair.fill_holes(base); trimesh.repair.fix_normals(base)
base = trimesh.Trimesh(to_cfd(base.vertices), base.faces, process=True)
if base.volume < 0: base.invert()
mir = trimesh.load('v6/car/out/mirrors.stl'); mir = trimesh.Trimesh(to_cfd(mir.vertices), mir.faces, process=True)
if mir.volume < 0: mir.invert()
# The spoiler sits on the roof with the 1.5 mm tape gap; it is lowered 3 mm so its underside seals onto the roof as the
# tape does. (Moving only the hidden, car-facing vertices into the body to close every gap under 8 mm was tried: it
# folded the surface. The few wedge-shaped slivers left at the edges are handled by the solver's speed cap.)
spo = trimesh.load('v6/out/E2.stl'); V = spo.vertices.copy(); V[:, 1] -= 3.0
spo = trimesh.Trimesh(to_cfd(V), spo.faces, process=True)
if spo.volume < 0: spo.invert()

def tyre(cx, cz_axle):
    """rounded cylinder about the lateral axis: radius WHEEL_R, width WHEEL_W, 25 mm shoulder radius (car frame mm)"""
    R, hw, rs = WHEEL_R, WHEEL_W / 2, 25.0
    prof = [(0.0, -hw)]
    for a in np.linspace(-np.pi / 2, 0, 7): prof.append((R - rs + rs * np.cos(a), -hw + rs + rs * np.sin(a)))
    for a in np.linspace(0, np.pi / 2, 7): prof.append((R - rs + rs * np.cos(a), hw - rs + rs * np.sin(a)))
    prof.append((0.0, hw))
    n = 160; ang = np.linspace(0, 2 * np.pi, n, endpoint=False); Vs = []; F = []
    P = np.array(prof)
    for r, x in P: Vs.append(np.column_stack([np.full(n, x), r * np.cos(ang), r * np.sin(ang)]))
    Vs = np.vstack(Vs); m = len(P)
    for i in range(m - 1):
        for j in range(n):
            a0 = i * n + j; a1 = i * n + (j + 1) % n; b0 = (i + 1) * n + j; b1 = (i + 1) * n + (j + 1) % n
            F += [[a0, b0, b1], [a0, b1, a1]]
    t = trimesh.Trimesh(Vs, np.array(F), process=True)          # axis = x (lateral)
    t.merge_vertices(); t.update_faces(t.nondegenerate_faces()); t.remove_unreferenced_vertices()
    t.apply_translation([cx, Y_G + WHEEL_R - 8.0, cz_axle])     # sunk 8 mm into the ground (contact patch)
    if t.volume < 0: t.invert()
    return t
wheels = {}
for nm, s_ax in (('wheelF', S_FA), ('wheelR', S_RA)):
    zc = Z_F + s_ax
    pair = trimesh.util.concatenate([tyre(+TRACK / 2, zc), tyre(-TRACK / 2, zc)])
    wheels[nm] = trimesh.Trimesh(to_cfd(pair.vertices), pair.faces, process=True)

parts = dict(body=body, body_base=base, mirrors=mir, spoiler=spo, **wheels)
for k, m in parts.items():
    report(k, m); m.export(f'{OUT}/{k}.stl')
# frontal area (full car, projected on the YZ plane) with and without the spoiler
def frontal(meshes, h=0.004):
    import matplotlib.path as mpath
    Y = np.arange(-1.0, 1.0, h); Z = np.arange(0.0, 1.6, h); YY, ZZ = np.meshgrid(Y, Z); hit = np.zeros(YY.shape, bool)
    from trimesh.ray.ray_pyembree import RayMeshIntersector
    for m in meshes:
        R = RayMeshIntersector(m); O = np.column_stack([np.full(YY.size, -5.0), YY.ravel(), ZZ.ravel()])
        hit |= R.intersects_any(O, np.tile([1.0, 0, 0], (len(O), 1))).reshape(YY.shape)
    return float(hit.sum() * h * h)
A0 = frontal([base, mir, wheels['wheelF'], wheels['wheelR']]); A1 = frontal([body, mir, spo, wheels['wheelF'], wheels['wheelR']])
info = dict(z_front_mm=Z_F, y_ground_mm=Y_G, wheelbase_m=(S_RA - S_FA) / 1000, x_front_axle_m=S_FA / 1000, x_rear_axle_m=S_RA / 1000,
            wheel_radius_m=WHEEL_R / 1000, track_m=TRACK / 1000, frontal_area_m2_no_spoiler=A0, frontal_area_m2_with_spoiler=A1,
            car_length_m=float(body.bounds[1][0] - body.bounds[0][0]), car_height_m=float(max(body.bounds[1][2], spo.bounds[1][2])),
            spoiler_lowered_mm=3.0)
json.dump(info, open(f'{OUT}/geometry_info.json', 'w'), indent=1)
print(json.dumps(info, indent=1))
