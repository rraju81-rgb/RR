"""Final pose solve: BFS initialisation over all part-to-part joints + global least squares."""
import os, sys, pickle, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from joints import load_parts
from refine import boundary_vertices
from ends import part_ends
from posegraph import pairs_from, optimize

P = load_parts()
A = pickle.load(open('assembly.pkl', 'rb')); D = pickle.load(open('matches.pkl', 'rb'))
by = {}
for f in D['faces']:
    by.setdefault(f['part'], []).append(f)
J = []
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
    J.append((a, b, T, best[0], best[1]))
for s in pickle.load(open('stub_joints.pkl', 'rb')):
    pA, pB = pairs_from(s['bA'], s['bB'], s['T_refined'])
    J.append((s['A'], s['B'], s['T_refined'], pA, pB))
print('joints:', len(J), ' min pairs per joint:', min(len(j[3]) for j in J))

# BFS init
adj = {}
for a, b, T, _, _ in J:
    adj.setdefault(a, []).append((b, T)); adj.setdefault(b, []).append((a, np.linalg.inv(T)))
poses = {}
for root in (11, 3):
    pose = {root: np.eye(4)}; stack = [root]
    while stack:
        x = stack.pop()
        for y, T in adj.get(x, []):
            if y not in pose:
                pose[y] = pose[x] @ T; stack.append(y)
    cons = [(a, b, pA, pB) for a, b, T, pA, pB in J if a in pose and b in pose]
    opt, r0, r1 = optimize(pose, cons, root)
    rms = lambda r: np.sqrt(np.mean(r.reshape(-1, 3) ** 2, axis=0).sum())
    print(f"component rooted at obj_{root}: {len(pose)} parts, {len(cons)} joints; residual RMS {rms(r0):.4f} -> {rms(r1):.4f} mm, max {np.abs(r0).max():.3f} -> {np.abs(r1).max():.3f} mm")
    poses.update(opt)
pickle.dump(poses, open('final_poses.pkl', 'wb'))
print('placed:', sorted(poses))
