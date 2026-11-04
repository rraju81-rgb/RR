"""Step 2: envelope E0 = TOP exterior skin + BOTTOM underside + 0.2 mm stitch strip across the old glue gap."""
import sys; sys.path.insert(0, 'v6/src')
import numpy as np, trimesh
from meshutil import submesh, boundary_loops
T = trimesh.load('input/v5_TOP.stl'); B = trimesh.load('input/v5_BOTTOM.stl')
intT = np.load('v6/out/_intT_clean.npy'); intB = np.load('v6/out/_classify.npz')['intB']
S1 = submesh(T, ~intT); S2 = submesh(B, ~intB)
L1 = np.array(boundary_loops(S1)[0][0]); L2 = np.array(boundary_loops(S2)[0][0])
nv1 = len(S1.vertices)
V = np.vstack([S1.vertices, S2.vertices]); F = [S1.faces, S2.faces + nv1]
A = L1.copy()                 # S1 half-edge direction A[i]->A[i+1]
Br = (L2[::-1] + nv1).copy()  # reversed S2 loop, so Br[j]->Br[j+1] is opposite of S2's half-edges
PA = V[A]; PB = V[Br]
# start at closest pair
from scipy.spatial import cKDTree
d, j = cKDTree(PB).query(PA)
i0 = int(np.argmin(d)); j0 = int(j[i0])
A = np.roll(A, -i0); PA = V[A]; Br = np.roll(Br, -j0); PB = V[Br]
# check they run the same way
ta = PA[5] - PA[0]; tb = PB[5] - PB[0]
print('direction dot', np.dot(ta, tb) / np.linalg.norm(ta) / np.linalg.norm(tb))
n, m = len(A), len(Br)
i = j = 0; tris = []
while i < n or j < m:
    a0, a1 = A[i % n], A[(i + 1) % n]
    b0, b1 = Br[j % m], Br[(j + 1) % m]
    if i >= n:
        adv = 'B'
    elif j >= m:
        adv = 'A'
    else:
        # shortest diagonal rule
        dA = np.linalg.norm(V[a1] - V[b0]); dB = np.linalg.norm(V[b1] - V[a0])
        adv = 'A' if dA <= dB else 'B'
    if adv == 'A':
        tris.append([a1, a0, b0]); i += 1
    else:
        tris.append([b0, b1, a0]); j += 1
F.append(np.array(tris))
E0 = trimesh.Trimesh(V, np.vstack(F), process=False)
E0.merge_vertices(merge_tex=True, merge_norm=True)
E0.remove_unreferenced_vertices()
print('faces', len(E0.faces), 'watertight', E0.is_watertight, 'winding consistent', E0.is_winding_consistent, 'volume cm3', round(E0.volume / 1000, 1))
if E0.volume < 0: E0.invert()
E0.export('v6/out/E0.stl')
