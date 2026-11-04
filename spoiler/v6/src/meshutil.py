import numpy as np, trimesh
from collections import defaultdict

def submesh(m, mask):
    f = m.faces[mask]
    u, inv = np.unique(f, return_inverse=True)
    return trimesh.Trimesh(m.vertices[u], inv.reshape(-1, 3), process=False)

def boundary_loops(m):
    """ordered boundary loops (vertex index lists) of an open mesh, oriented consistent with faces"""
    e = np.vstack([m.faces[:, [0, 1]], m.faces[:, [1, 2]], m.faces[:, [2, 0]]])
    key = np.sort(e, 1)
    _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    be = e[cnt[inv] == 1]
    nxt = defaultdict(list)
    for a, b in be:
        nxt[a].append(b)
    bad = [k for k, v in nxt.items() if len(v) != 1]
    loops = []; used = set()
    for a0 in list(nxt.keys()):
        if a0 in used: continue
        loop = [a0]; used.add(a0); a = a0
        while True:
            if not nxt[a]: break
            b = nxt[a][0]
            if b == a0: break
            if b in used: loop.append(-1); break
            loop.append(b); used.add(b); a = b
        loops.append(loop)
    return loops, bad

def components(m):
    return trimesh.graph.connected_components(m.face_adjacency, nodes=np.arange(len(m.faces)), min_len=1)
