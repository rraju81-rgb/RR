"""Package the four print files (body, left wing, right wing, end plates) at one common scale
so that every file fits a given build volume, oriented ready to print.

    python3 package_build_volume.py --bed 420 420 450 [--scale 0.52] [--out stl]

* body: stood upright on its rear opening (no supports inside the hollow nose); the slightly
  uneven rear rim is trimmed flat (3.2 mm at full size) so the whole rim sits on the bed.
* wings: lying on their most stable face.
* end plates: both plates lying flat, side by side in one file (left plate at -X).
Inputs (working directory): wing_left_posed.pkl, wing_right_posed.pkl (build_left_right.py)
and the full-size body / end plate STLs from export_all.py (--full).
"""
import argparse, os, sys
import numpy as np, trimesh, manifold3d as mf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pickle
from merge import to_manifold
from finalize import separate_coincident, slit_scan
from orient import stable_orient, max_scale_on_bed

def _write(M, path, tol):
    if tol:
        M = M.simplify(tol)
    o = M.to_mesh64()
    V = np.asarray(o.vert_properties)[:, :3].astype(np.float64); F = np.asarray(o.tri_verts).astype(np.int64)
    V, _ = separate_coincident(V, F)                     # touching sheets must not weld together in STL
    tm = trimesh.Trimesh(V, F, process=False)
    keep = lambda m: [c for c in m.split(only_watertight=False) if abs(c.volume) > 1.0]
    parts = keep(tm); tm = trimesh.util.concatenate(parts) if len(parts) > 1 else parts[0]
    lo, hi = tm.bounds; tm.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
    tm.export(path)
    chk = trimesh.load(path, force='mesh')               # slivers that only separate after welding
    parts = keep(chk)
    if len(parts) != len(chk.split(only_watertight=False)):
        (trimesh.util.concatenate(parts) if len(parts) > 1 else parts[0]).export(path)
        chk = trimesh.load(path, force='mesh')
    e = chk.edges_sorted; _, cnt = np.unique(e, axis=0, return_counts=True)
    return chk, int((cnt != 2).sum())

def manifold_to_stl(M, path, expect_solids=1, scale=1.0):
    """Export so the STL survives slicer-style re-welding: try no simplification first, then light
    simplification; keep the first watertight result with no bad edges and the fewest slit samples."""
    best = None
    for tol in (None, 1e-5, 1e-4, 1e-3, 5e-3):
        chk, bad = _write(M, path, tol)
        ok = chk.is_watertight and bad == 0 and len(chk.split(only_watertight=False)) == expect_solids
        slits = slit_scan(chk, lo=0.05 * scale, hi=0.9 * scale) if ok else 10 ** 9
        if best is None or (ok, -slits) > (best[0], -best[1]):
            best = (ok, slits, tol)
        if ok and slits <= 2:
            break
    if best[2] != tol:
        chk, bad = _write(M, path, best[2])
    return chk, bad

def upright_body(body, trim):
    """Stand the nose on its rear opening; trim the rim flat. Returns (manifold, height at 100 %)."""
    c = body.vertices.mean(0); _, V = np.linalg.eigh(np.cov((body.vertices - c).T)); ax = V[:, 2]
    t = (body.vertices - c) @ ax
    wid = lambda sel: np.ptp(((body.vertices - c) @ V[:, 1])[sel])
    if wid(t > t.max() - 60) > wid(t < t.min() + 60):
        ax, t = -ax, -t                                   # +ax points to the tip
    rim = body.vertices[t < t.min() + 15]
    _, _, vt = np.linalg.svd(rim - rim.mean(0)); pn = vt[2] if np.dot(vt[2], ax) > 0 else -vt[2]
    h0 = (body.vertices @ pn).min()
    M = to_manifold(body).trim_by_plane(tuple(pn), float(h0 + trim))
    x = np.cross(pn, [1, 0, 0] if abs(pn[0]) < 0.9 else [0, 1, 0]); x /= np.linalg.norm(x); y = np.cross(pn, x)
    R = np.eye(4); R[:3, :3] = np.stack([x, y, pn])
    M = M.transform(R[:3, :4])
    return M, M.bounding_box()[5] - M.bounding_box()[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bed', nargs=3, type=float, default=[420, 420, 450])
    ap.add_argument('--scale', type=float, default=None, help='common scale; default = largest that fits (2%% margin)')
    ap.add_argument('--full', default='full_size', help='folder with full-size 1_body / 3_endplate_A / 3_endplate_B STLs')
    ap.add_argument('--out', default='stl')
    ap.add_argument('--trim', type=float, default=3.2, help='mm trimmed off the body rear rim (full size)')
    args = ap.parse_args()
    BED = np.array(args.bed)

    full = args.full
    body = trimesh.load(os.path.join(full, '1_body.stl'), force='mesh')
    epA = trimesh.load(os.path.join(full, '4a_end_plate_left.stl'), force='mesh')
    epB = trimesh.load(os.path.join(full, '4b_end_plate_right.stl'), force='mesh')
    wings = {k: pickle.load(open(f'wing_{k}_posed.pkl', 'rb')) for k in ('left', 'right')}

    Mbody, hbody = upright_body(body, args.trim)
    wingT = {k: stable_orient(m, top=1)[0][0] for k, m in wings.items()}
    limits = {'body (upright)': 0.98 * BED[2] / hbody}
    bb = Mbody.bounding_box(); limits['body (upright)'] = min(limits['body (upright)'], 0.98 * BED[0] / (bb[3] - bb[0]), 0.98 * BED[1] / (bb[4] - bb[1]))
    for k, m in wings.items():
        mm = m.copy(); mm.apply_transform(wingT[k])
        limits[f'{k} wing'] = max_scale_on_bed(mm, BED * 0.98)[0]
    gap = 15.0
    pair_w = epA.extents[0] + gap + epB.extents[0]; pair_d = max(epA.extents[1], epB.extents[1]); pair_h = max(epA.extents[2], epB.extents[2])
    limits['end plates'] = min(0.98 * BED[0] / pair_w, 0.98 * BED[1] / pair_d, 0.98 * BED[2] / pair_h)
    for k, v in limits.items():
        print(f'max scale for {k}: {v * 100:.1f}%')
    s = args.scale or np.floor(min(limits.values()) * 100) / 100
    print(f'==> common scale {s * 100:.0f}%')

    os.makedirs(args.out, exist_ok=True)
    S = np.eye(4); S[:3, :3] *= s
    results = []
    chk, bad = manifold_to_stl(Mbody.transform(S[:3, :4]), os.path.join(args.out, '1_body.stl'), scale=s)
    results.append(('1_body.stl', chk, bad))
    for k, fname in (('left', '2_left_wing.stl'), ('right', '3_right_wing.stl')):
        T = S @ wingT[k]
        M = to_manifold(wings[k]).transform(T[:3, :4])
        # turn about Z so the footprint fits the bed
        hull = np.asarray(M.to_mesh64().vert_properties)[:, :3]
        best = None
        for a in np.radians(np.arange(0, 180, 1)):
            Rz = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
            ext = np.ptp(hull[:, :2] @ Rz.T, axis=0)
            slack = min(BED[0] - ext[0], BED[1] - ext[1])
            if best is None or slack > best[0]:
                best = (slack, a)
        a = best[1]; Rz = np.eye(4); Rz[:2, :2] = [[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]]
        chk, bad = manifold_to_stl(M.transform(Rz[:3, :4]), os.path.join(args.out, fname), scale=s)
        results.append((fname, chk, bad))
    # end plates: scaled, side by side (left plate at -X), one file with two solids
    pl = []
    for m, side in ((epA, -1), (epB, +1)):
        c = to_manifold(m).transform(S[:3, :4])
        b = c.bounding_box(); w = b[3] - b[0]
        c = c.translate((side * (gap * s / 2 + w / 2) - (b[0] + b[3]) / 2, -(b[1] + b[4]) / 2, -b[2]))
        pl.append(c)
    both = pl[0] + pl[1]
    chk, bad = manifold_to_stl(both, os.path.join(args.out, '4_end_plates.stl'), expect_solids=2, scale=s)
    results.append(('4_end_plates.stl', chk, bad))

    print(f'\nbuild volume {BED[0]:.0f} x {BED[1]:.0f} x {BED[2]:.0f} mm, scale {s * 100:.0f}%')
    for fname, chk, bad in results:
        ext = chk.extents
        fits = bool(np.all(ext <= BED))
        print(f'{fname:18s} {ext[0]:6.1f} x {ext[1]:6.1f} x {ext[2]:6.1f} mm  fits={fits}  solids={len(chk.split(only_watertight=False))}  '
              f'watertight={chk.is_watertight}  non-manifold edges={bad}  volume={chk.volume / 1000:.1f} cm3  slit samples={slit_scan(chk, lo=0.05 * s, hi=0.9 * s)}')


if __name__ == '__main__':
    main()
