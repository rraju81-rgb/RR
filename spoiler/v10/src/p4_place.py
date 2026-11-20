"""v10 step 4: print placement on a 420 x 420 x 500 mm bed (Anycubic Kobra 3 Max).
Every part stands on its FRONT/REAR CUT (a flat face with the spline groove in it): the rear parts on their front face,
the front parts on their rear face. The skin then rises as a long, low curved wall (130-160 mm tall instead of v9's
217 mm), set across the bed's diagonal; the visible top surface is printed as a side wall, with no support on it.
Splines lie flat; pins stand on end, all on one plate.   Run from spoiler/:  python3 v10/src/p4_place.py"""
import sys, json, os, tempfile; sys.path.insert(0, 'v10/src'); sys.path.insert(0, 'v6/src')
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
    # splines: flat, side by side on one plate
    J = json.load(open(f'{OUT}/joints.json')); plate = []; x0, y0, row_h = 20.0, 20.0, 0.0; sp_rep = []
    for i in range(J['n_splines']):
        s = trimesh.load(f'{ASM}/v10_SPLINE_{i + 1:02d}.stl')
        # its seam normal: the axis of least extent of the strip's vertices; lies flat, lengthwise along x
        C = np.cov((s.vertices - s.vertices.mean(0)).T); w, v = np.linalg.eigh(C); nrm = v[:, 0]
        q, R, tr = place(s, nrm, center=False, lengthwise=True)
        if x0 + q.extents[0] > BED[0] - 20.0: x0, y0, row_h = 20.0, y0 + row_h + 10.0, 0.0     # next row
        q.apply_translation([x0 - q.bounds[0][0], y0 - q.bounds[0][1], -q.bounds[0][2]])
        x0 += q.extents[0] + 10.0; row_h = max(row_h, q.extents[1])
        q.export(f'{PRN}/v10_SPLINE_{i + 1:02d}.stl'); plate.append(q)
        sp_rep.append(dict(file=f'v10_SPLINE_{i + 1:02d}.stl', extent_mm=[round(float(v_), 1) for v_ in q.extents], overhang_gt45_cm2=overhangs(q)(45)))
    pl = trimesh.util.concatenate(plate)
    if pl.extents[1] > BED[1] - 2 * MARGIN: print('spline plate too long:', pl.extents)
    pl.export(f'{PRN}/v10_SPLINES_plate.stl'); rep['SPLINES'] = dict(plate='v10_SPLINES_plate.stl', items=sp_rep, plate_extent_mm=[round(float(v_), 1) for v_ in pl.extents])
    # pins: standing on end; needed + 4 spares on one plate
    pin = trimesh.load(f'{OUT}/pin_local.stl'); pin.apply_translation(-pin.bounds[0]); pin.export(f'{PRN}/v10_PIN_3x18.stl')
    npl = J['n_pins'] + 4; cols = 8; pp = []
    for i in range(npl):
        q = pin.copy(); q.apply_translation([(i % cols) * 10.0 + 10, (i // cols) * 10.0 + 10, 0]); pp.append(q)
    trimesh.util.concatenate(pp).export(f'{PRN}/v10_PINS_3x18_plate_x{npl}.stl')
    rep['PIN'] = dict(file='v10_PIN_3x18.stl', plate=f'v10_PINS_3x18_plate_x{npl}.stl', size_mm=[3.0, PIN_L], n_needed=J['n_pins'], plate_count=npl)
    json.dump(rep, open(f'{OUT}/print_report.json', 'w'), indent=1)
    for k in ('SPLINES', 'PIN'): print(k, rep[k])
    bad = [k for k in IDS if not (rep[k]['print_file_ok'] and rep[k]['fits_420x420x500'])]
    print('ALL PRINT FILES OK' if not bad else f'PRINT FILE CHECK FAILED: {bad}')
    sys.exit(1 if bad else 0)
