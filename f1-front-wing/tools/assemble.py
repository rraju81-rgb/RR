import os, sys, pickle, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from joints import load_parts

def select_joints(results, max_skin=0.5, min_iou=0.95):
    """Greedy one-to-one selection of end-joints (each part end used once)."""
    good = [r for r in results if r['skin'] <= max_skin and min(r['iou'], r['iou2']) >= min_iou]
    good.sort(key=lambda r: r['skin'] - min(r['iou'], r['iou2']))
    used_ends, sel = set(), []
    for r in good:
        if r['i'] in used_ends or r['j'] in used_ends:
            continue
        used_ends |= {r['i'], r['j']}
        sel.append(r)
    return sel

def components(parts, joints):
    adj = {p: [] for p in parts}
    for r in joints:
        adj[r['A']].append((r['B'], r.get('T_refined', r['T'])))               # T maps B -> A
        adj[r['B']].append((r['A'], np.linalg.inv(r.get('T_refined', r['T']))))  # inv maps A -> B
    seen, comps = set(), []
    for root in parts:
        if root in seen:
            continue
        pose = {root: np.eye(4)}
        stack = [root]; seen.add(root)
        while stack:
            a = stack.pop()
            for b, T in adj[a]:
                if b not in pose:
                    pose[b] = pose[a] @ T
                    seen.add(b); stack.append(b)
        comps.append(pose)
    return comps

if __name__ == '__main__':
    P = load_parts()
    R = pickle.load(open('endmatch.pkl', 'rb'))['results']
    J = select_joints(R)
    print('selected joints:', len(J))
    for r in J:
        print(f"  {r['kind']:4} obj_{r['A']} - obj_{r['B']}  skin {r['skin']:.2f}")
    comps = components(list(P), J)
    comps.sort(key=lambda c: -len(c))
    for c in comps:
        print('component:', sorted(c))
    pickle.dump(dict(joints=J, comps=comps), open('assembly.pkl', 'wb'))
