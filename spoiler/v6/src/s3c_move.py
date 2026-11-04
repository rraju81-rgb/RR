"""Step 3c: move top-surface vertices of E0 in the step band onto the cubic bridge (vertex moves only).
y = y0 + wt(x) * (H(x,z) - y0). Top-surface test uses rays offset by a few microns (avoids rays through vertices)."""
import sys; sys.path.insert(0, 'v6/src')
import numpy as np, trimesh
from trimesh.ray.ray_pyembree import RayMeshIntersector
C = dict(np.load('v6/out/_smooth_top.npz')); cx = C['x']; xend = float(C['xend'])
src = sys.argv[1] if len(sys.argv) > 1 else 'v6/out/E0.stl'
dst = sys.argv[2] if len(sys.argv) > 2 else 'v6/out/E1.stl'
def hermite(z, za, zb, ya, yb, sa, sb):
    L = zb - za; t = np.clip((z - za) / L, 0, 1)
    return (2*t**3 - 3*t**2 + 1) * ya + (t**3 - 2*t**2 + t) * L * sa + (-2*t**3 + 3*t**2) * yb + (t**3 - t**2) * L * sb
def targets(V):
    xv, zv = V[:, 0], V[:, 2]
    idx = np.clip(np.searchsorted(cx, xv) - 1, 0, len(cx) - 2)
    ok = (xv >= cx[0]) & (xv <= cx[-1])
    w = np.clip(xv - cx[idx], 0, 1)
    acc = 0; zin = ok.copy()
    for j, ww in [(idx, 1 - w), (idx + 1, w)]:
        za, zb = C['za'][j], C['zb'][j]
        acc = acc + ww * hermite(zv, za, zb, C['ya'][j], C['yb'][j], C['sa'][j], C['sb'][j])
        zin &= (zv >= za) & (zv <= zb)
    t = np.clip((xend - np.abs(xv)) / 12.0, 0, 1); wt = t * t * (3 - 2 * t)
    return acc, zin, wt
def top_mask(mesh, V, tol=0.05):
    R = RayMeshIntersector(mesh)
    best = np.zeros(len(V), bool)
    for dx, dz in [(0.0031, 0.0017), (-0.0023, 0.0029), (0.0013, -0.0037)]:
        o = V.copy(); o[:, 0] += dx; o[:, 2] += dz; o[:, 1] = 300.0
        lc, ri, ti = R.intersects_location(o, np.tile([0, -1.0, 0], (len(o), 1)), multiple_hits=False)
        first = np.full(len(o), np.nan); first[ri] = lc[:, 1]
        best |= np.abs(first - V[:, 1]) < tol
    return best
if __name__ == '__main__':
    E = trimesh.load(src)
    V = E.vertices.copy()
    tgt, zin, wt = targets(V)
    cand = zin & (wt > 0) & (np.abs(tgt - V[:, 1]) < 1.5)
    ci = np.nonzero(cand)[0]
    top = top_mask(E, V[ci])
    ci = ci[top]
    dy = wt[ci] * (tgt[ci] - V[ci, 1]); V[ci, 1] += dy
    print('moved', len(ci), 'max |dy| %.3f' % np.abs(dy).max(), ' (candidates', cand.sum(), ')')
    trimesh.Trimesh(V, E.faces, process=False).export(dst)
