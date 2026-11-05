"""Refine every part-to-part joint by ICP on the cut boundary vertices both sides share.

Reads assembly.pkl (from assemble.py) and matches.pkl, stores T_refined on each joint and
rebuilds the connected components with the refined transforms.
"""
import sys, pickle
import numpy as np
sys.path.insert(0, '.')
from joints import load_parts
from refine import boundary_vertices, icp_refine_exact
from ends import part_ends
from assemble import components

P = load_parts()
A = pickle.load(open('assembly.pkl', 'rb'))
D = pickle.load(open('matches.pkl', 'rb'))
by = {}
for f in D['faces']:
    by.setdefault(f['part'], []).append(f)

for r in A['joints']:
    a, b, T = r['A'], r['B'], r['T']
    eA = [e for e in part_ends(by[a]) if e['total'] >= 250]
    eB = [e for e in part_ends(by[b]) if e['total'] >= 250]
    best = None
    for ea in eA:
        for eb in eB:
            if np.dot(ea['n'], T[:3, :3] @ eb['n']) > -0.99:
                continue
            fa = np.concatenate([f['faces'] for f in ea['faces']])
            fb = np.concatenate([f['faces'] for f in eb['faces']])
            T2, rms, frac = icp_refine_exact(boundary_vertices(P[a], fa), boundary_vertices(P[b], fb), T)
            if best is None or frac > best[2]:
                best = (T2, rms, frac)
    r['T_refined'], rms, r['exact_frac'] = best
    print(f"{r['kind']:4} obj_{a}-obj_{b}: exact pairs {r['exact_frac'] * 100:3.0f}%  rms {rms:.4f} mm")

A['comps'] = sorted(components(list(P), A['joints']), key=lambda c: -len(c))
pickle.dump(A, open('assembly.pkl', 'wb'))
