"""Global pose-graph refinement: every joint contributes exact vertex correspondences."""
import os, sys, pickle, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scipy.optimize import least_squares
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot
from joints import load_parts
from refine import boundary_vertices
from ends import part_ends

def pairs_from(bA, bB, T, tol=0.03):
    """Exact correspondences (pA in A coords, pB in B coords) at transform T (B->A)."""
    Xb = bB @ T[:3, :3].T + T[:3, 3]
    d, idx = cKDTree(bA).query(Xb)
    ok = d < tol
    return bA[idx[ok]], bB[ok]

def collect_constraints():
    P = load_parts()
    A = pickle.load(open('assembly.pkl', 'rb')); D = pickle.load(open('matches.pkl', 'rb'))
    links = pickle.load(open('stub_links.pkl', 'rb'))
    by = {}
    for f in D['faces']:
        by.setdefault(f['part'], []).append(f)
    cons = []
    for r in A['joints']:
        a, b, T = r['A'], r['B'], r['T_refined']
        eA = [e for e in part_ends(by[a]) if e['total'] >= 250]; eB = [e for e in part_ends(by[b]) if e['total'] >= 250]
        best = None
        for ea in eA:
            for eb in eB:
                if np.dot(ea['n'], T[:3, :3] @ eb['n']) > -0.99:
                    continue
                fa = np.concatenate([f['faces'] for f in ea['faces']]); fb = np.concatenate([f['faces'] for f in eb['faces']])
                pA, pB = pairs_from(boundary_vertices(P[a], fa), boundary_vertices(P[b], fb), T)
                if best is None or len(pA) > len(best[0]):
                    best = (pA, pB)
        cons.append((a, b, best[0], best[1]))
    # stub links: tip vertices are in endplate *component* coords; convert to tip-part coords
    exec_ns = {}
    exec(open('tools/wing_assembly.py').read().split("ENDS = {p: end_face(p)")[0], exec_ns)
    comps = A['comps']
    for ids in ([11, 12], [16, 41]):
        tips, ms = exec_ns['stub_tips_relaxed'](ids)
        comp = [c for c in comps if ids[0] in c][0]
        for L in [l for l in links if l['ep'] == ids]:
            e = exec_ns['end_face'](L['elem'])
            bB = boundary_vertices(P[L['elem']], e['faces'])
            best = None
            for t in tips:
                bA = boundary_vertices(t['faces_mesh'], t['faces'])
                pA, pB = pairs_from(bA, bB, L['T'])
                if best is None or len(pA) > len(best[1]):
                    best = (t, pA, pB)
            t, pA, pB = best
            Cinv = np.linalg.inv(comp[t['part']])
            pA_part = pA @ Cinv[:3, :3].T + Cinv[:3, 3]
            cons.append((t['part'], L['elem'], pA_part, pB))
    return P, cons

def to_T(x):
    T = np.eye(4); T[:3, :3] = Rot.from_rotvec(x[:3]).as_matrix(); T[:3, 3] = x[3:]
    return T

def optimize(init_pose, cons, fixed):
    parts = sorted(init_pose)
    idx = {p: i for i, p in enumerate(parts)}
    # parametrize as small corrections around the initial pose: T = init @ delta
    def residuals(x):
        res = []
        for a, b, pA, pB in cons:
            if a not in idx or b not in idx:
                continue
            Ta = init_pose[a] @ (np.eye(4) if a == fixed else to_T(x[6 * idx[a]: 6 * idx[a] + 6]))
            Tb = init_pose[b] @ (np.eye(4) if b == fixed else to_T(x[6 * idx[b]: 6 * idx[b] + 6]))
            wa = pA @ Ta[:3, :3].T + Ta[:3, 3]
            wb = pB @ Tb[:3, :3].T + Tb[:3, 3]
            res.append((wa - wb).ravel())
        return np.concatenate(res)
    x0 = np.zeros(6 * len(parts))
    r0 = residuals(x0)
    sol = least_squares(residuals, x0, method='trf', x_scale=np.tile([1e-3, 1e-3, 1e-3, 1.0, 1.0, 1.0], len(parts)))
    r1 = residuals(sol.x)
    out = {p: init_pose[p] @ (np.eye(4) if p == fixed else to_T(sol.x[6 * idx[p]: 6 * idx[p] + 6])) for p in parts}
    return out, r0, r1

if __name__ == '__main__':
    P, cons = collect_constraints()
    print('constraints:', len(cons), ' total point pairs:', sum(len(c[2]) for c in cons))
    wing = pickle.load(open('wing_pose.pkl', 'rb'))
    A = pickle.load(open('assembly.pkl', 'rb'))
    nose = [c for c in A['comps'] if 3 in c][0]
    poses = {}
    for name, init, fixed in [('wing', wing, 11), ('nose', nose, 3)]:
        opt, r0, r1 = optimize(init, [c for c in cons if c[0] in init and c[1] in init], fixed)
        rms0 = np.sqrt(np.mean(r0.reshape(-1, 3) ** 2, axis=0).sum()); rms1 = np.sqrt(np.mean(r1.reshape(-1, 3) ** 2, axis=0).sum())
        print(f"{name}: residual RMS {rms0:.4f} -> {rms1:.4f} mm ; max {np.abs(r0).max():.3f} -> {np.abs(r1).max():.3f} mm")
        poses[name] = opt
    # per-joint residual after optimisation
    allp = {**poses['wing'], **poses['nose']}
    worst = []
    for a, b, pA, pB in cons:
        Ta, Tb = allp[a], allp[b]
        d = np.linalg.norm((pA @ Ta[:3, :3].T + Ta[:3, 3]) - (pB @ Tb[:3, :3].T + Tb[:3, 3]), axis=1)
        if len(d) == 0:
            print(f'  (no exact pairs for joint obj_{a}-obj_{b})'); continue
        worst.append((d.max(), a, b, np.sqrt((d ** 2).mean())))
    worst.sort(reverse=True)
    for w in worst[:6]:
        print(f"  joint obj_{w[1]}-obj_{w[2]}: rms {w[3]:.3f} max {w[0]:.3f} mm")
    pickle.dump(poses, open('global_poses.pkl', 'wb'))
