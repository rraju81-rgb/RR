"""v9 step 4: print placement on a 420 x 420 x 500 mm bed (Anycubic Kobra 3 Max).
- Every piece stands on its GROOVE face (the female seam face), so the tongue face, where there is one, is on top. The
  six pieces are 216.7 mm tall (219.2 with the tongue) and their walls are vertical-ish: the cored skin is printed as
  a thin curved wall, layer on layer.
- The centre spline stands on one of its narrow edges (its sides lean 30 degrees: no support).
- The pins stand on end, 14 on a plate (10 + 4 spares).
Run from spoiler/:  python3 v9/src/p4_place.py"""
import sys, json, os; sys.path.insert(0, 'v9/src'); sys.path.insert(0, 'v6/src')
import numpy as np, trimesh
from scipy.spatial import ConvexHull
from check import report
from bowtie import tomf, totm
from layout import OUT, ASM, PRN, PIECES, STEM, SEAMS, sides, PIN_L

BED = (420.0, 420.0, 500.0); MARGIN = 12.0
R_NEG = np.array([[0, 0, 1.0], [0, 1, 0], [-1, 0, 0]])           # Z_print = -x : the piece's +x face is on the bed
R_POS = np.array([[0, 0, -1.0], [0, 1, 0], [1, 0, 0]])           # Z_print = +x : the piece's -x face is on the bed

def groove_face(pid, x0, x1):
    """which end of the piece is its groove face: 'x1' (the +x end) or 'x0'"""
    for k, c in enumerate(SEAMS):
        if abs(c - x1) < 0.1 and sides(c)[0] == 'F': return 'x1'
        if abs(c - x0) < 0.1 and sides(c)[1] == 'F': return 'x0'
    raise ValueError(pid)

def place(m, R3):
    V = m.vertices @ R3.T
    base = V[V[:, 2] < V[:, 2].min() + 1.0][:, :2]                       # long axis of the footprint along Y (bed-slinger)
    h = base[ConvexHull(base).vertices]
    D = np.linalg.norm(h[:, None] - h[None], axis=2); i, j = np.unravel_index(D.argmax(), D.shape)
    d = h[j] - h[i]
    if d[1] < 0: d = -d
    a = np.arctan2(d[0], d[1])
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    V = V @ Rz.T
    V[:, 0] += BED[0] / 2 - (V[:, 0].min() + V[:, 0].max()) / 2
    V[:, 1] += BED[1] / 2 - (V[:, 1].min() + V[:, 1].max()) / 2
    V[:, 2] -= V[:, 2].min()
    R = Rz @ R3; tr = V[0] - R @ m.vertices[0]
    # apply the same transform inside manifold3d, then make sure the file as written (float32) has no folded triangles:
    # where the pocket wall grazes the seal rim the booleans can leave a zero-thickness flap a few microns wide, which
    # rounding can fold over. If that happens, drop detail finer than 5 / 10 / 20 microns and write it again.
    import tempfile
    for tol in (0.0, 0.005, 0.01, 0.02):
        M = tomf(m).transform(np.column_stack([R, tr]))
        if tol: M = M.simplify(tol)
        out = totm(M)
        with tempfile.NamedTemporaryFile(suffix='.stl') as f:
            out.export(f.name); r, sx = report(trimesh.load(f.name), 'tmp')
        if r['selfx_faces'] == 0 and r['watertight'] and r['bodies'] == 1: break
    assert np.allclose(out.bounds, np.array([V.min(0), V.max(0)]), atol=0.05)
    place.last_tol = tol
    return out, R

def overhangs(p):
    n = p.face_normals; zc = p.triangles_center[:, 2]; A = p.area_faces
    def ov(deg):                        # faces pointing down more than `deg` from vertical, above the first 0.6 mm
        k = (n[:, 2] < -np.sin(np.radians(deg))) & (zc > 0.6)
        return round(float(A[k].sum()) / 100, 1), ([round(float(zc[k].min()), 1), round(float(zc[k].max()), 1)] if k.any() else None)
    return ov

if __name__ == '__main__':
    os.makedirs(PRN, exist_ok=True)
    for f in os.listdir(PRN): os.remove(f'{PRN}/{f}')
    rep = {}
    for pid, x0, x1, stem, label in PIECES:
        m = trimesh.load(f'{ASM}/{stem}.stl')
        gf = groove_face(pid, x0, x1)
        p, Rt = place(m, R_NEG if gf == 'x1' else R_POS)
        e = p.extents; fits = bool(e[0] <= BED[0] - 2 * MARGIN and e[1] <= BED[1] - 2 * MARGIN and e[2] <= BED[2] - 2)
        ov = overhangs(p); n = p.face_normals; zc = p.triangles_center[:, 2]
        bed_area = p.area_faces[(n[:, 2] < -0.999) & (zc < 0.05)].sum()
        base = p.vertices[p.vertices[:, 2] < 0.05]
        rep[pid] = dict(file=f'{stem}.stl', label=label, on_bed='groove face (x = %.1f)' % (x1 if gf == 'x1' else x0),
                        print_extent_mm=[round(float(v), 1) for v in e], fits_420x420x500=fits,
                        bed_contact_cm2=round(float(bed_area) / 100, 1), footprint_mm=[round(float(v), 1) for v in (base.max(0) - base.min(0))[:2]],
                        overhang_gt45_cm2=ov(45)[0], overhang_gt45_z=ov(45)[1], overhang_gt55_cm2=ov(55)[0], overhang_gt60_cm2=ov(60)[0],
                        volume_cm3=round(float(p.volume) / 1000, 1), simplified_microns=round(place.last_tol * 1000))
        p.export(f'{PRN}/{stem}.stl'); np.save(f'{OUT}/_place_{pid}.npy', Rt)
        r, sx = report(trimesh.load(f'{PRN}/{stem}.stl'), stem)            # the file as written (float32 STL)
        rep[pid]['print_file_ok'] = bool(r['watertight'] and r['winding'] and r['bodies'] == 1 and r['selfx_faces'] == 0 and r['zero_area'] == 0)
        print(pid, rep[pid])
    # centre spline: stands on a narrow edge (x vertical)
    sp = trimesh.load(f'{ASM}/v9_CENTRE_SPLINE.stl'); sp_p, _ = place(sp, R_POS)
    sp_p.apply_translation([-sp_p.bounds[0][0] + 10, -sp_p.bounds[0][1] + 10, 0])
    ov = overhangs(sp_p); sp_p.export(f'{PRN}/v9_CENTRE_SPLINE.stl')
    rep['SPLINE'] = dict(file='v9_CENTRE_SPLINE.stl', print_extent_mm=[round(float(v), 1) for v in sp_p.extents], overhang_gt45_cm2=ov(45)[0],
                         volume_cm3=round(float(sp.volume) / 1000, 2), orientation='on a narrow edge; sides lean 30 degrees, no support')
    # pins: standing on end; one file with a single pin, one plate with 14 (10 + 4 spares)
    pin = trimesh.load(f'{OUT}/pin_local.stl'); pin.apply_translation([-pin.bounds[0][0], -pin.bounds[0][1], -pin.bounds[0][2]])
    pin.export(f'{PRN}/v9_PIN_3x18.stl')
    plate = []
    for i in range(14):
        q = pin.copy(); q.apply_translation([(i % 7) * 10.0 + 10, (i // 7) * 10.0 + 10, 0]); plate.append(q)
    pl = trimesh.util.concatenate(plate); pl.export(f'{PRN}/v9_PINS_3x18_plate_x14.stl')
    rep['PIN'] = dict(file='v9_PIN_3x18.stl', plate='v9_PINS_3x18_plate_x14.stl', size_mm=[3.0, PIN_L], n_needed=10, plate_count=14,
                      orientation='standing on end')
    json.dump(rep, open(f'{OUT}/print_report.json', 'w'), indent=1)
    for k in ('SPLINE', 'PIN'): print(k, rep[k])
    bad = [k for k, v in rep.items() if k.startswith('P') and k[1:].isdigit() and not (v['print_file_ok'] and v['fits_420x420x500'])]
    print('ALL PRINT FILES OK' if not bad else f'PRINT FILE CHECK FAILED: {bad}')
    sys.exit(1 if bad else 0)
