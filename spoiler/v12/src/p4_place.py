"""v12 step 4: the print set, on a 420 x 420 x 500 mm bed (Anycubic Kobra 3 Max): the six parts and one pin model, nothing
else. Every part stands on its FRONT/REAR CUT (a flat face with only pin holes in it): the rear parts on their front
face, the front parts on their rear face. The skin then rises as a long, low curved wall (134-141 mm tall), set across
the bed's diagonal; the visible top surface is printed as a side wall, with no support on it. The pin is one model,
standing on end: print it as many times as joints.json says (plus spares).   Run from spoiler/:  python3 v12/src/p4_place.py"""
import sys, json, os, tempfile; sys.path.insert(0, 'v12/src'); sys.path.insert(0, 'v6/src')
import numpy as np, trimesh
from check import report
from bowtie import tomf, totm
from layout import OUT, ASM, PRN, IDS, STEM, SEC, HALF_OF, LABEL, chord_plane, PIN_L
from p1_core import written_folds, decimate_clean

BED = (420.0, 420.0, 500.0); MARGIN = 12.0
Yc = np.array([0.0, 1.0, 0.0])

def frame_up(up):
    up = up / np.linalg.norm(up); X0 = np.cross(up, Yc); X0 /= np.linalg.norm(X0); Y0 = np.cross(up, X0)
    return np.vstack([X0, Y0, up])                                      # rows: print X, Y, Z in car coordinates

def best_spin(V, lengthwise=False):
    """turn about the vertical: smallest square footprint (parts, across the bed's diagonal), or lengthwise along x"""
    best = None
    for a in np.radians(np.arange(0, 180, 0.5)):
        c, s = np.cos(a), np.sin(a); x = V[:, 0] * c - V[:, 1] * s; y = V[:, 0] * s + V[:, 1] * c
        e = np.ptp(y) if lengthwise else max(np.ptp(x), np.ptp(y))
        if best is None or e < best[0]: best = (e, a)
    a = best[1]; return np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1.0]])

def place(m, up, center=True, lengthwise=False):
    R = frame_up(up); V = m.vertices @ R.T
    Rz = best_spin(V, lengthwise); R = Rz @ R; V = m.vertices @ R.T
    tr = np.array([BED[0] / 2 - (V[:, 0].min() + V[:, 0].max()) / 2, BED[1] / 2 - (V[:, 1].min() + V[:, 1].max()) / 2, -V[:, 2].min()])
    if not center: tr[:2] = 0
    out = m.copy(); T = np.eye(4); T[:3, :3] = R; T[:3, 3] = tr; out.apply_transform(T)    # float64, proper rotation
    place.last_tol = 0
    if written_folds(out) != 0:                                          # the file as written (float32) must be clean:
        for k in range(1, 12):                                           # a few microns' shift changes the float rounding
            q = out.copy(); q.apply_translation([0.0017 * k, 0.0011 * k, 0.0])
            if written_folds(q) == 0: out = q; tr = tr + [0.0017 * k, 0.0011 * k, 0.0]; break
        else:
            out, perc = decimate_clean(out, 'placed', percs=(0.9, 0.75, 0.6, 0.45, 0.3), max_dev=0.03); place.last_tol = round(1 - perc, 2)
    return out, R, tr

def overhangs(p):
    n = p.face_normals; zc = p.triangles_center[:, 2]; A = p.area_faces
    def ov(deg):
        k = (n[:, 2] < -np.sin(np.radians(deg))) & (zc > 0.6)
        return round(float(A[k].sum()) / 100, 1)
    return ov

if __name__ == '__main__':
    os.makedirs(PRN, exist_ok=True)
    for f in os.listdir(PRN): os.remove(f'{PRN}/{f}')
    rep = {}
    for pid in IDS:
        m = trimesh.load(f'{ASM}/{STEM[pid]}.stl'); n, d = chord_plane(SEC[pid])
        up = n if HALF_OF[pid] == 'rear' else -n                        # stands on its cut face
        p, R, tr = place(m, up)
        e = p.extents; fits = bool(e[0] <= BED[0] - 2 * MARGIN and e[1] <= BED[1] - 2 * MARGIN and e[2] <= BED[2] - 2)
        ov = overhangs(p); nz = p.face_normals[:, 2]; zc = p.triangles_center[:, 2]
        rep[pid] = dict(file=f'{STEM[pid]}.stl', label=LABEL[pid], stands_on='its %s cut face' % ('front' if HALF_OF[pid] == 'rear' else 'rear'),
                        print_extent_mm=[round(float(v), 1) for v in e], fits_420x420x500=fits,
                        bed_contact_cm2=round(float(p.area_faces[(nz < -0.999) & (zc < 0.05)].sum()) / 100, 1),
                        overhang_gt45_cm2=ov(45), overhang_gt55_cm2=ov(55), overhang_gt60_cm2=ov(60),
                        volume_cm3=round(float(p.volume) / 1000, 1), redecimated=place.last_tol)
        p.export(f'{PRN}/{STEM[pid]}.stl'); np.save(f'{OUT}/_place_{pid}.npy', np.column_stack([R, tr]))
        r, sx = report(trimesh.load(f'{PRN}/{STEM[pid]}.stl'), STEM[pid])
        rep[pid]['print_file_ok'] = bool(r['watertight'] and r['winding'] and r['bodies'] == 1 and r['selfx_faces'] == 0 and r['zero_area'] == 0)
        print(pid, rep[pid], flush=True)
    # the pin: one model, standing on end (print it n_pins times, plus a few spare)
    J = json.load(open(f'{OUT}/joints.json'))
    pin = trimesh.load(f'{OUT}/pin_local.stl'); pin.apply_translation(-pin.bounds[0]); pin.export(f'{PRN}/v12_PIN_3x18.stl')
    r, sx = report(trimesh.load(f'{PRN}/v12_PIN_3x18.stl'), 'pin')
    rep['PIN'] = dict(file='v12_PIN_3x18.stl', size_mm=[3.0, PIN_L], n_needed=J['n_pins'], print_count=J['n_pins'] + 4,
                      print_file_ok=bool(r['watertight'] and r['winding'] and r['bodies'] == 1 and r['selfx_faces'] == 0))
    files = sorted(os.listdir(PRN)); rep['print_set'] = files
    assert files == sorted([f'{STEM[k]}.stl' for k in IDS] + ['v12_PIN_3x18.stl']), f'print/ holds {files}'
    json.dump(rep, open(f'{OUT}/print_report.json', 'w'), indent=1)
    print('PIN', rep['PIN']); print('print set:', len(rep['print_set']), 'files:', ', '.join(rep['print_set']))
    bad = [k for k in IDS if not (rep[k]['print_file_ok'] and rep[k]['fits_420x420x500'])] + ([] if rep['PIN']['print_file_ok'] else ['PIN'])
    print('ALL PRINT FILES OK' if not bad else f'PRINT FILE CHECK FAILED: {bad}')
    sys.exit(1 if bad else 0)
