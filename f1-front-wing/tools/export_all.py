import sys, pickle, numpy as np, trimesh
sys.path.insert(0, 'tools')
import finalize
from orient import stable_orient

import os
OUT = os.environ.get('F1_OUT_DIR', 'stl') + '/'
WING_IDS = [10, 36, 35, 20, 27, 28, 13, 9, 32, 31, 4, 29, 30, 14, 7, 23, 24, 5, 33, 34, 43, 6, 26, 25, 38, 42]

def run(which):
    jobs = []
    if 'body' in which:
        jobs.append(('1_body_RED.stl', lambda: finalize.build([3, 2, 39, 40, 1], 'BODY')))
    if 'endplates' in which:
        jobs.append(('3_endplate_A_BLUE.stl', lambda: finalize.build([11, 12], 'ENDPLATE_A')))
        jobs.append(('3_endplate_B_BLUE.stl', lambda: finalize.build([16, 41], 'ENDPLATE_B')))
    if 'wing' in which:
        ids = list(WING_IDS) + ([37] if 37 in __import__('joints').load_parts() else [])
        name = '2_wing_GREEN.stl' if 37 in ids else '2_wing_GREEN_INCOMPLETE_missing_obj37.stl'
        jobs.append((name, lambda: finalize.build_wing(ids, pickle.load(open('bridges.pkl', 'rb')), 'WING')))
    for fname, fn in jobs:
        m = fn()
        T, p = stable_orient(m, top=1)[0]
        for tol in (0.005, 0.01, 0.02):
            r = finalize.export_clean2(m, T, OUT + fname, tol)
            if r['watertight'] and r['bad_edges'] == 0 and r['solids'] == 1:
                break
        chk = trimesh.load(OUT + fname, force='mesh')
        print(f"==> {fname}: tol {tol} | {r['tris']} tris | watertight {r['watertight']} | non-manifold edges {r['bad_edges']} | solids {r['solids']} | "
              f"volume {r['volume']/1000:.1f} cm3 | size {np.round(r['extents'], 1)} mm | visible slits {finalize.slit_scan(chk)}")

if __name__ == '__main__':
    run(sys.argv[1:] or ['body', 'endplates', 'wing'])
