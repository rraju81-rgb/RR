"""Step 1: split v5 TOP / BOTTOM faces into exterior skin vs internal (pocket, ledges, cavity, glue gap)."""
import numpy as np, trimesh, sys
from trimesh.ray.ray_pyembree import RayMeshIntersector
T = trimesh.load('input/v5_TOP.stl'); B = trimesh.load('input/v5_BOTTOM.stl')
asm = trimesh.util.concatenate([T, B])
nT = len(T.faces)
R_asm = RayMeshIntersector(asm)

def first_hit(origins, dirs, maxd):
    """returns (hit_mask, hit_is_bottom, distance) for first hit within maxd"""
    loc, ir, it = R_asm.intersects_location(origins, dirs, multiple_hits=False)
    hit = np.zeros(len(origins), bool); isB = np.zeros(len(origins), bool); dist = np.full(len(origins), np.inf)
    d = np.linalg.norm(loc - origins[ir], axis=1)
    ok = d <= maxd
    hit[ir[ok]] = True; isB[ir[ok]] = it[ok] >= nT; dist[ir[ok]] = d[ok]
    return hit, isB, dist

def classify(m, other_is_bottom):
    c = m.triangles_center; n = m.face_normals
    p = c + n * 0.03
    hit, isB, dist = first_hit(p, n, 20.0)
    toward_other = hit & (isB == other_is_bottom)
    # enclosed test: from a point just outside the face, rays up and down both hit the assembly
    p2 = c + n * 0.08
    up = np.tile([0, 1.0, 0], (len(c), 1)); dn = -up
    hu, _, _ = first_hit(p2, up, 120.0); hd, _, _ = first_hit(p2, dn, 120.0)
    enclosed = hu & hd
    # also check +-z and +-x for enclosed-ness (cavity end walls)
    return toward_other, enclosed

tT, eT = classify(T, True)
tB, eB = classify(B, False)
intT = tT | eT
intB = tB | eB
print('TOP faces', nT, 'internal', intT.sum(), '(toward BOTTOM', tT.sum(), ', enclosed', eT.sum(), ')')
print('BOTTOM faces', len(B.faces), 'internal', intB.sum(), '(toward TOP', tB.sum(), ', enclosed', eB.sum(), ')')
np.savez('v6/out/_classify.npz', intT=intT, intB=intB, tT=tT, eT=eT, tB=tB, eB=eB)
# clean-up by connectivity: tiny internal islands -> exterior, tiny exterior fragments -> internal
adj = T.face_adjacency
def comps_of(mask):
    a = adj[mask[adj[:, 0]] & mask[adj[:, 1]]]
    return trimesh.graph.connected_components(a, nodes=np.nonzero(mask)[0], min_len=1)
ic = intT.copy()
for it in range(3):
    for c in comps_of(ic):
        if len(c) < 2000: ic[c] = False
    ce = comps_of(~ic); big = max(ce, key=len)
    for c in ce:
        if len(c) < len(big): ic[c] = True
print('TOP internal after clean-up', ic.sum())
np.save('v6/out/_intT_clean.npy', ic)
