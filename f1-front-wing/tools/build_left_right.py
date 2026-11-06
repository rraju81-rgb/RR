"""Build the LEFT and RIGHT wing halves (assembled pose) from the reassembled parts.

* obj_37 (missing from the upload) is rebuilt as the mirror image of its twin obj_25, fitted
  onto obj_38's joint face (cross-section match + skin continuity).
* Small webs tie the four elements of each half together (stations +/-150 and +/-440 mm).
* The merged wing is split on its mirror plane into left (-n side) and right (+n side).

Writes wing_left_posed.pkl / wing_right_posed.pkl (trimesh meshes) in the working directory.
Needs final_poses.pkl, symmetry.pkl, assembly.pkl from the earlier steps.
"""
import os, sys, pickle
import numpy as np, trimesh, manifold3d as mf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from joints import load_parts
from faces import frame_for, register2d_multi, mirror_poly, transform_from_match
from stubs import poly_of
from endmatch import skin_continuity
from merge import slit_fillers_patch, to_manifold, from_manifold, drop_cavities, heal_slits, keep_main
from bridges import bridge
from orient import stable_orient
from package_build_volume import manifold_to_stl

ELEM = {'main': [10, 36, 35, 20, 27, 28, 13], 'f2': [9, 32, 31, 4, 29, 30, 14],
        'f3': [7, 23, 24, 5, 33, 34, 43], 'top': [6, 26, 25, 38, 42]}          # front -> rear
PAIRS = [('main', 'f2'), ('f2', 'f3'), ('f3', 'top')]
STATIONS = [-440, -150, 150, 440]

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
    ELEM['top'] = [6, 26, 25, 37, 38, 42]

ids = sorted({p for v in ELEM.values() for p in v})
grp = {k: trimesh.util.concatenate([W[p] for p in v]) for k, v in ELEM.items()}

# ---- webs between neighbouring elements
webs = []
for s in STATIONS:
    for a, b in PAIRS:
        h, gap = bridge(grp[a], grp[b], n, n * (d + s))
        if h is not None:
            webs.append(h)
            print(f'web at {s:+d} mm {a}-{b}: slot gap {gap:.1f} mm')

# ---- union (with tab-clearance fillers), heal, split on the mirror plane
pairs = [(r['A'], r['B']) for r in A['joints']] + [(25, 37), (37, 38)]
fill = []
for a, b in pairs:
    if a in ids and b in ids:
        fill += slit_fillers_patch(W[a], W[b]); fill += slit_fillers_patch(W[b], W[a])
Ms = [to_manifold(W[p]) for p in ids] + [to_manifold(f) for f in fill] + [to_manifold(w) for w in webs]
wing = from_manifold(mf.Manifold.batch_boolean(Ms, mf.OpType.Add))
wing, _, _, _ = drop_cavities(wing)
wing = heal_slits(wing, verbose=False)
wing, _ = keep_main(wing)
print(f'full wing: {len(wing.split(only_watertight=False))} solid(s), {wing.volume / 1000:.1f} cm3')

M = to_manifold(wing)
pos, neg = M.split_by_plane(tuple(float(x) for x in n), float(d))
for name, half in [('left', neg), ('right', pos)]:          # left = -n side (end plate A side)
    h = from_manifold(half)
    h, _, _, _ = drop_cavities(h)
    h, dropped = keep_main(h)
    print(f'{name} wing: {len(h.split(only_watertight=False))} solid(s), {h.volume / 1000:.1f} cm3, watertight {h.is_watertight}')
    pickle.dump(h, open(f'wing_{name}_posed.pkl', 'wb'))
    # full-size master, lying on its most stable face
    out = os.path.join(os.environ.get('F1_OUT_DIR', 'stl'), 'full_size'); os.makedirs(out, exist_ok=True)
    T, _ = stable_orient(h, top=1)[0]
    fname = '2_left_wing.stl' if name == 'left' else '3_right_wing.stl'
    chk, bad = manifold_to_stl(to_manifold(h).transform(T[:3, :4]), os.path.join(out, fname))
    print(f'   full-size {fname}: watertight {chk.is_watertight}, non-manifold edges {bad}')
