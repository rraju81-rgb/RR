"""v7 step 3: print placement on a 420 x 420 x 500 mm bed (Anycubic Kobra 3 Max). Every piece stands on a seam
face with the span direction vertical, so each print is 325 mm tall. The middle pieces stand on the centre-seam
face (x = 0), where the walls rise vertically from the bed. Keys lie flat on their outer face.
Run from spoiler/:  python3 v7/src/p3_place.py"""
import sys, json, os; sys.path.insert(0, 'v7/src'); sys.path.insert(0, 'v6/src')
import numpy as np, trimesh
from scipy.spatial import ConvexHull
from layout import OUT, ASM, PRN, PIECES, N_KEYS
from check import report

BED = (420.0, 420.0, 500.0); MARGIN = 12.0

def place(m, R3):
    V = m.vertices @ R3.T
    # bed-slinger (bed moves in Y): align the long axis of the footprint (the chord) with Y
    # (tip-to-tip direction of the footprint: it does not depend on how the mesh is triangulated)
    base = V[V[:, 2] < V[:, 2].min() + 1.0][:, :2]
    h = base[ConvexHull(base).vertices]
    D = np.linalg.norm(h[:, None] - h[None], axis=2); i, j = np.unravel_index(D.argmax(), D.shape)
    d = h[j] - h[i]
    if d[1] < 0: d = -d
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
R_NEG = np.array([[0, 0, 1.0], [0, 1, 0], [-1, 0, 0]])   # Z_print = -x : the piece's +x face is on the bed
R_POS = np.array([[0, 0, -1.0], [0, 1, 0], [1, 0, 0]])   # Z_print = +x : the piece's -x face is on the bed
ROT = {'P1': R_NEG, 'P2': R_NEG, 'P3': R_POS, 'P4': R_POS}   # P1: x=-325 face down; P2, P3: x=0 face down; P4: x=+325 face down
DOWN = {'P1': 'cut face (x = -325)', 'P2': 'centre-seam face (x = 0)', 'P3': 'centre-seam face (x = 0)', 'P4': 'cut face (x = +325)'}

rep = {}
os.makedirs(PRN, exist_ok=True)
for pid, x0, x1, stem, label in PIECES:
    m = trimesh.load(f'{ASM}/{pid}.stl')
    p, Rt = place(m, ROT[pid])
    e = p.extents; fits = bool(e[0] <= BED[0] - 2 * MARGIN and e[1] <= BED[1] - 2 * MARGIN and e[2] <= BED[2] - 2)
    n = p.face_normals; zc = p.triangles_center[:, 2]; A = p.area_faces
    def ov(deg):                        # faces pointing down more than `deg` from vertical, above the first 0.6 mm
        k = (n[:, 2] < -np.sin(np.radians(deg))) & (zc > 0.6)
        return round(float(A[k].sum()) / 100, 1), ([round(float(zc[k].min()), 1), round(float(zc[k].max()), 1)] if k.any() else None)
    bed_area = A[(n[:, 2] < -0.999) & (zc < 0.05)].sum()
    base = p.vertices[p.vertices[:, 2] < 0.05]
    rep[pid] = dict(file=f'{stem}.stl', on_bed=DOWN[pid], print_extent_mm=[round(float(v), 1) for v in e], fits_420x420x500=fits,
                    bed_contact_cm2=round(float(bed_area) / 100, 1),
                    footprint_mm=[round(float(v), 1) for v in (base.max(0) - base.min(0))[:2]],
                    overhang_gt45_cm2=ov(45)[0], overhang_gt45_z=ov(45)[1], overhang_gt55_cm2=ov(55)[0], overhang_gt55_z=ov(55)[1],
                    overhang_gt60_cm2=ov(60)[0], volume_cm3=round(float(p.volume) / 1000, 1))
    p.export(f'{PRN}/{stem}.stl')
    np.save(f'{OUT}/_place_{pid}.npy', Rt)
    # check the file as written (float32 STL), since this is what gets sliced
    r, sx = report(trimesh.load(f'{PRN}/{stem}.stl'), stem)
    rep[pid]['print_file_ok'] = bool(r['watertight'] and r['winding'] and r['bodies'] == 1 and r['selfx_faces'] == 0 and r['zero_area'] == 0)
    rep[pid]['print_file_selfx_faces'] = r['selfx_faces']
    print(pid, rep[pid])

# key: lies on its outer face (w = 0, the larger flat face) -> no overhangs
km = trimesh.load(f'{OUT}/_key_local.stl')
kp = trimesh.Trimesh(km.vertices.copy(), km.faces, process=False)
kp.apply_translation([-kp.bounds[0][0] + 5, -kp.bounds[0][1] + 5, -kp.bounds[0][2]])
kp.export(f'{PRN}/v7_BOWTIE_KEY_x{N_KEYS}.stl')
n = kp.face_normals; zc = kp.triangles_center[:, 2]
print('key extent', kp.extents.round(2), 'overhang>45 area', float(kp.area_faces[(n[:, 2] < -0.71) & (zc > 0.3)].sum()))
NPL = N_KEYS + 2                         # a plate of 8 keys: 6 + 2 spares
plate = []
for i in range(NPL):
    c = kp.copy(); c.apply_translation([(i % 4) * 62.0, (i // 4) * 30.0, 0]); plate.append(c)
pl = trimesh.util.concatenate(plate); pl.export(f'{PRN}/v7_BOWTIE_KEYS_plate_of_{NPL}.stl')
rep['KEY'] = dict(file=f'v7_BOWTIE_KEY_x{N_KEYS}.stl', plate=f'v7_BOWTIE_KEYS_plate_of_{NPL}.stl', plate_extent_mm=[round(float(v), 1) for v in pl.extents],
                  print_extent_mm=[round(float(v), 2) for v in kp.extents], volume_cm3=round(float(kp.volume) / 1000, 2),
                  orientation='flat, outer (car-side) face on the bed; no supports')
json.dump(rep, open(f'{OUT}/_print_report.json', 'w'), indent=1)
print('KEY', rep['KEY'])
bad = [k for k, v in rep.items() if k != 'KEY' and not (v['print_file_ok'] and v['fits_420x420x500'])]
print('ALL PRINT FILES OK' if not bad else f'PRINT FILE CHECK FAILED: {bad}')
sys.exit(1 if bad else 0)
