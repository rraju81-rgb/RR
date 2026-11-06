"""Merge, heal and export the full-size BODY and the two END PLATES into <F1_OUT_DIR>/full_size/.
(The wing halves are built by build_left_right.py.)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, trimesh
import finalize
from merge import to_manifold
from orient import stable_orient
from package_build_volume import manifold_to_stl

OUT = os.path.join(os.environ.get('F1_OUT_DIR', 'stl'), 'full_size')

def run():
    os.makedirs(OUT, exist_ok=True)
    jobs = [('1_body.stl', [3, 2, 39, 40, 1], 'BODY'),
            ('4a_end_plate_left.stl', [11, 12], 'END PLATE LEFT'),
            ('4b_end_plate_right.stl', [16, 41], 'END PLATE RIGHT')]
    for fname, ids, label in jobs:
        m = finalize.build(ids, label)
        T, _ = stable_orient(m, top=1)[0]
        chk, bad = manifold_to_stl(to_manifold(m).transform(T[:3, :4]), os.path.join(OUT, fname))
        print(f"==> {fname}: {np.round(chk.extents, 1)} mm | watertight {chk.is_watertight} | non-manifold edges {bad} | "
              f"solids {len(chk.split(only_watertight=False))} | volume {chk.volume / 1000:.1f} cm3")

if __name__ == '__main__':
    run()
