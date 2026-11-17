"""Build the 8 separate wing BLADES (assembled pose) from the reassembled parts.

* obj_37 (missing from the upload) is rebuilt as the mirror image of its twin obj_25, fitted
  onto obj_38's joint face (cross-section match + skin continuity).
* Each element is merged on its own (no webs between elements). Joints are fused
  (merge.merge_fused): faces that touch across a joint are pushed slightly into each other before
  the union, so no hairline double walls are left inside the solid.
* The three full-width elements are split on the mirror plane into a left (-n side, end plate A)
  and a right half; the top flap already comes in a left and a right piece.

Writes blades_posed.pkl ({name: trimesh}, names main_L, e2_L, e3_L, flap_L and the same with _R)
in the working directory, and plain full-size blades to <F1_OUT_DIR>/full_size/.
Needs final_poses.pkl, symmetry.pkl, assembly.pkl from the earlier steps.
"""
import os, sys, pickle
import numpy as np, trimesh, manifold3d as mf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from joints import load_parts
from faces import frame_for, register2d_multi, mirror_poly, transform_from_match
from stubs import poly_of
from endmatch import skin_continuity
from merge import merge_fused, fuse_microgaps, to_manifold, from_manifold, keep_main
from orient import stable_orient
from package_build_volume import manifold_to_stl

# element parts, from end plate A (left) to end plate B (right)
ELEM = {'main': [10, 36, 35, 20, 27, 28, 13], 'e2': [9, 32, 31, 4, 29, 30, 14],
        'e3': [7, 23, 24, 5, 33, 34, 43], 'flap_L': [6, 26, 25], 'flap_R': [38, 42]}

P = load_parts(); pose = pickle.load(open('final_poses.pkl', 'rb')); S = pickle.load(open('symmetry.pkl', 'rb'))
A = pickle.load(open('assembly.pkl', 'rb'))
n, d = S['n'], S['d']
W = {p: P[p].copy().apply_transform(pose[p]) for p in pose}

# ---- rebuild obj_37 = mirror(obj_25), fitted onto obj_38's flat joint face
def flat_face(p, mesh):
    fs = np.where((P[p].face_normals[:, 2] < -0.999) & (P[p].triangles_center[:, 2] < 0.5))[0]
    nrm = (mesh.face_normals[fs] * mesh.area_faces[fs, None]).sum(0); nrm /= np.linalg.norm(nrm)
    u, v = frame_for(nrm); oo = nrm * np.dot(nrm, mesh.triangles_center[fs].mean(0))
    return dict(n=nrm, u=u, v=v, o=oo, faces=fs, poly=poly_of(mesh.triangles[fs], oo, u, v))

if 37 in W:
    print('obj_37 present - using the real part')
else:
    m37 = W[25].copy()
    m37.vertices = m37.vertices - 2 * ((m37.vertices @ n) - d)[:, None] * n[None]
    m37.invert()
    f38, f37 = flat_face(38, W[38]), flat_face(25, m37)
    iou, th, t = max(register2d_multi(f38['poly'], mirror_poly(f37['poly'])), key=lambda r: r[0])
    T = transform_from_match(f38, f37, th, t)
    T[:3, 3] -= f38['n'] * 0.05                      # 0.05 mm overlap into obj_38 so the joint fuses
    m37.apply_transform(T)
    sk, _ = skin_continuity(W[38], f38['faces'], m37, f37['faces'], np.eye(4))   # m37 is already placed
    print(f'obj_37 rebuilt from mirrored obj_25: joint overlap {iou:.3f}, skin kink {sk:.2f} deg')
    W[37] = m37
    ELEM['flap_R'] = [37, 38, 42]

pairs = [(r['A'], r['B']) for r in A['joints']] + [(37, 38)]
blades = {}
for name, ids in ELEM.items():
    m = merge_fused({p: W[p] for p in ids}, pairs, name.upper())
    m = fuse_microgaps(m)
    m, _ = keep_main(m)
    if name.startswith('flap'):
        blades[name] = m
        continue
    pos, neg = to_manifold(m).split_by_plane(tuple(float(x) for x in n), float(d))
    for side, half in (('L', neg), ('R', pos)):         # left = -n side (end plate A side)
        h, _ = keep_main(from_manifold(half))
        blades[f'{name}_{side}'] = h

pickle.dump(blades, open('blades_posed.pkl', 'wb'))
out = os.path.join(os.environ.get('F1_OUT_DIR', 'stl'), 'full_size'); os.makedirs(out, exist_ok=True)
NAMES = {'main': '1_main_plane', 'e2': '2_second_element', 'e3': '3_third_element', 'flap': '4_top_flap'}
for k, h in sorted(blades.items()):
    base, side = k.rsplit('_', 1)
    T, _ = stable_orient(h, top=1)[0]
    fname = f"blade_{'left' if side == 'L' else 'right'}_{NAMES[base]}.stl"
    chk, bad = manifold_to_stl(to_manifold(h).transform(T[:3, :4]), os.path.join(out, fname))
    print(f'{k}: {h.volume / 1000:.1f} cm3, genus {to_manifold(h).genus()} -> full-size {fname}: watertight {chk.is_watertight}, '
          f'non-manifold edges {bad}')
