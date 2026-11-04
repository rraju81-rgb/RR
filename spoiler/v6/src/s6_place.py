"""Step 6: print placement on a 420 x 420 x 500 mm bed (Anycubic Kobra 3 Max): every piece stands on a seam
face (span direction vertical); keys lie flat on their outer face. Overhang report."""
import sys, json, os; sys.path.insert(0, 'v6/src')
import numpy as np, trimesh
from scipy.spatial import ConvexHull
OUT = 'v6/out'; BED = (420.0, 420.0, 500.0); MARGIN = 12.0
meta = json.load(open(f'{OUT}/_parts_meta.json')); XS = meta['XS']
def bed_rot(P):
    h = P[ConvexHull(P).vertices]; best = None
    for a in np.radians(np.arange(0, 180, 0.25)):
        Rm = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]]); q = h @ Rm.T; ext = q.max(0) - q.min(0)
        sc = ext.max() + 1e-3 * ext.min()
        if best is None or sc < best[0]: best = (sc, a, ext)
    return best
def place(m, R3):
    V = m.vertices @ R3.T
    # bed-slinger (bed moves in Y): align the long axis of the footprint (the chord) with Y
    base = V[V[:, 2] < V[:, 2].min() + 1.0][:, :2]
    c0 = base.mean(0); w_, v_ = np.linalg.eigh(np.cov((base - c0).T)); d = v_[:, np.argmax(w_)]
    a = np.arctan2(d[0], d[1])          # rotate so that d -> +Y
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    V = V @ Rz.T
    V[:, 0] += BED[0] / 2 - (V[:, 0].min() + V[:, 0].max()) / 2
    V[:, 1] += BED[1] / 2 - (V[:, 1].min() + V[:, 1].max()) / 2
    V[:, 2] -= V[:, 2].min()
    out = trimesh.Trimesh(V, m.faces.copy(), process=False)
    if out.volume < 0: out.invert()
    return out, Rz @ R3
# world (x, y, z) -> print: span axis vertical
R_L = np.array([[0, 0, 1.0], [0, 1, 0], [-1, 0, 0]])   # Z_print = -x  (seam face x=-XS on the bed)
R_R = np.array([[0, 0, -1.0], [0, 1, 0], [1, 0, 0]])   # Z_print = +x  (seam face x=+XS on the bed)
R_C = R_R                                              # centre: left seam face on the bed
rep = {}
os.makedirs('v6/print', exist_ok=True)
names = {'L': 'v6_LEFT_end_piece', 'C': 'v6_CENTRE_piece', 'R': 'v6_RIGHT_end_piece'}
for k, R3 in [('L', R_L), ('C', R_C), ('R', R_R)]:
    m = trimesh.load(f'v6/assembled/{k}.stl')
    p, Rt = place(m, R3)
    e = p.extents; fits = bool(e[0] <= BED[0] - 2 * MARGIN and e[1] <= BED[1] - 2 * MARGIN and e[2] <= BED[2] - 2)
    # overhangs: faces pointing down more than 45 deg from vertical, above the first 0.6 mm
    n = p.face_normals; zc = p.triangles_center[:, 2]; A = p.area_faces
    ov = (n[:, 2] < -np.cos(np.radians(45))) & (zc > 0.6)
    ov60 = (n[:, 2] < -np.cos(np.radians(30))) & (zc > 0.6)
    bed_area = A[(n[:, 2] < -0.999) & (zc < 0.05)].sum()
    rep[k] = dict(file=f'{names[k]}.stl', print_extent_mm=[round(float(v), 1) for v in e], fits_420x420x500=fits,
                  bed_contact_cm2=round(float(bed_area) / 100, 1), overhang_gt45_cm2=round(float(A[ov].sum()) / 100, 1),
                  overhang_gt60_cm2=round(float(A[ov60].sum()) / 100, 1), volume_cm3=round(float(p.volume) / 1000, 1),
                  overhang_z_range=[round(float(zc[ov].min()), 1), round(float(zc[ov].max()), 1)] if ov.any() else None)
    p.export(f'v6/print/{names[k]}.stl')
    np.save(f'{OUT}/_place_{k}.npy', Rt)
    print(k, rep[k])
# key: lie on its outer face (w=0, the larger flat face) -> no overhangs
km = trimesh.load(f'{OUT}/_key_local.stl')
V = km.vertices.copy(); V[:, 2] = V[:, 2]          # w=0 face already at z=0, floor face up
kp = trimesh.Trimesh(V, km.faces, process=False)
kp.apply_translation([-kp.bounds[0][0] + 5, -kp.bounds[0][1] + 5, -kp.bounds[0][2]])
kp.export(f'v6/print/v6_BOWTIE_KEY_x4.stl')
n = kp.face_normals; zc = kp.triangles_center[:, 2]
print('key extent', kp.extents.round(2), 'overhang>45 area', float(kp.area_faces[(n[:, 2] < -0.71) & (zc > 0.3)].sum()))
# a plate of 6 keys (4 + 2 spares)
plate = []
for i in range(6):
    c = kp.copy(); c.apply_translation([(i % 3) * 62.0, (i // 3) * 30.0, 0]); plate.append(c)
pl = trimesh.util.concatenate(plate); pl.export(f'v6/print/v6_BOWTIE_KEYS_plate_of_6.stl')
rep['KEY'] = dict(file='v6_BOWTIE_KEY_x4.stl', print_extent_mm=[round(float(v), 2) for v in kp.extents], volume_cm3=round(float(kp.volume) / 1000, 2),
                  orientation='flat, outer (car-side) face on the bed; no supports')
json.dump(rep, open(f'{OUT}/_print_report.json', 'w'), indent=1)
