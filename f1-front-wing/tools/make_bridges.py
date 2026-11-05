"""Fit the wing's mirror plane and build the small webs that tie neighbouring elements together.

Writes symmetry.pkl (plane normal n, offset d) and bridges.pkl (list of trimesh webs, in the
assembled frame of final_poses.pkl).
"""
import sys, pickle
import numpy as np, trimesh
from scipy.spatial import cKDTree
from scipy.optimize import least_squares
sys.path.insert(0, '.')
from joints import load_parts
from bridges import bridge

ELEMENTS = {'e1': [10, 36, 35, 20, 27, 28, 13], 'e2': [9, 32, 31, 4, 29, 30, 14],
            'e3': [7, 23, 24, 5, 33, 34, 43], 'e4': [6, 26, 25, 37, 38, 42]}
NEIGHBOURS = [('e1', 'e2'), ('e2', 'e3'), ('e3', 'e4')]   # slot-gap order across the cascade
STATIONS = [-440, 0, 440]                                    # mm from the mirror plane

P = load_parts(); pose = pickle.load(open('final_poses.pkl', 'rb'))
grp = lambda ids: trimesh.util.concatenate([P[p].copy().apply_transform(pose[p]) for p in ids if p in pose])
M = {k: grp(v) for k, v in ELEMENTS.items()}

# mirror plane from the three complete elements + both end plates
full = trimesh.util.concatenate([M['e1'], M['e2'], M['e3'], grp([11, 12]), grp([16, 41])])
pts = full.sample(40000); tree = cKDTree(pts)
cA, cB = grp([11, 12]).vertices.mean(0), grp([16, 41]).vertices.mean(0)
n0 = (cB - cA) / np.linalg.norm(cB - cA)
refl = lambda X, n, d: X - 2 * ((X @ n) - d)[:, None] * n[None]
sub = pts[::8]
def res(x):
    n = x[:3] / np.linalg.norm(x[:3])
    return np.minimum(tree.query(refl(sub, n, x[3]))[0], 5.0)
sol = least_squares(res, np.r_[n0, np.dot(n0, (cA + cB) / 2)], loss='soft_l1')
n, d = sol.x[:3] / np.linalg.norm(sol.x[:3]), sol.x[3]
pickle.dump(dict(n=n, d=d), open('symmetry.pkl', 'wb'))

webs = []
for s in STATIONS:
    for a, b in NEIGHBOURS:
        h, gap = bridge(M[a], M[b], n, n * (d + s))
        if h is None:
            print(f"station {s:+d} {a}-{b}: element missing here, no web")
            continue
        print(f"station {s:+d} {a}-{b}: slot gap {gap:.1f} mm, web {np.sort(h.extents).round(1)} mm")
        webs.append(h)
pickle.dump(webs, open('bridges.pkl', 'wb'))
