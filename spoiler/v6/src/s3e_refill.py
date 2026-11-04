"""Step 3e: cut the smoothed band out of the top surface of E1 and refill it with a quality triangulation
(Shewchuk Triangle, min angle 28 deg, ~1.1 mm edges) lifted onto the bridge surface; neighbours of split boundary
edges are fan-split so the mesh stays conforming. Output E2."""
import sys; sys.path.insert(0, 'v6/src')
import numpy as np, trimesh, triangle
from collections import defaultdict
from trimesh.ray.ray_pyembree import RayMeshIntersector
from s3c_move import targets, top_mask
E0 = trimesh.load('v6/out/E0.stl'); E1 = trimesh.load('v6/out/E1.stl')
V = E1.vertices.copy(); F = E1.faces.copy()
tgt, zin, wt = targets(V)
bv = np.zeros(len(V), bool); c = np.nonzero(zin & (wt > 0))[0]
bv[c] = top_mask(E1, V[c]) & (E1.vertex_normals[c, 1] > 0.2)
fin = bv[F].all(1)
from collections import Counter
import trimesh.graph as tg
def clean_band(fin):
    for it in range(20):
        adj = E1.face_adjacency; m = fin[adj[:, 0]] & fin[adj[:, 1]]
        comps = tg.connected_components(adj[m], nodes=np.nonzero(fin)[0], min_len=1)
        big = max(comps, key=len); fin = np.zeros(len(F), bool); fin[big] = True
        Fi = F[fin]; he = np.vstack([Fi[:, [0, 1]], Fi[:, [1, 2]], Fi[:, [2, 0]]]); key = np.sort(he, 1)
        _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True); be = he[cnt[inv] == 1]
        oc = Counter(be[:, 0].tolist()); pinch = [v for v, k in oc.items() if k > 1]
        if not pinch: return fin
        bad = np.isin(F, pinch).any(1) & fin; fin[bad] = False
    raise RuntimeError('pinch removal failed')
fin = clean_band(fin)
print('band faces', fin.sum())
# boundary edges of the band region (oriented as in band faces)
Fi = F[fin]
he = np.vstack([Fi[:, [0, 1]], Fi[:, [1, 2]], Fi[:, [2, 0]]])
key = np.sort(he, 1)
_, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
bedges = he[cnt[inv] == 1]
print('boundary edges', len(bedges))
# PSLG in (x, z)
bverts = np.unique(bedges)
loc = {v: i for i, v in enumerate(bverts)}
P2 = V[bverts][:, [0, 2]]
segs = np.array([[loc[a], loc[b]] for a, b in bedges])
# hole points for any islands: find loops; triangle needs holes only for inner loops that bound non-band islands
nxt = defaultdict(list)
for a, b in bedges: nxt[a].append(b)
loops = []; seen = set()
for a0 in nxt:
    if a0 in seen: continue
    L = [a0]; seen.add(a0); a = nxt[a0][0]
    while a != a0:
        assert len(nxt[a]) == 1 and a not in seen, 'boundary not a simple loop'
        L.append(a); seen.add(a); a = nxt[a][0]
    loops.append(L)
def sarea(L):
    p = V[L][:, [0, 2]]; return 0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])
areas = [sarea(L) for L in loops]
print('loops', len(loops), 'signed areas', np.round(sorted(areas), 1)[:6], '...')
outer_sign = np.sign(areas[int(np.argmax(np.abs(areas)))])
holes = []
for L, A in zip(loops, areas):
    if np.sign(A) != outer_sign:   # island (non-band faces enclosed by the band)
        isl = V[L][:, [0, 2]]
        from shapely.geometry import Polygon
        pt = Polygon(isl).representative_point(); holes.append([pt.x, pt.y])
pslg = dict(vertices=P2, segments=segs)
if holes: pslg['holes'] = np.array(holes)
T = triangle.triangulate(pslg, 'pq28a0.55')
TV = T['vertices']; TT = T['triangles']
nb = len(P2)
print('triangle: verts', len(TV), 'tris', len(TT), 'holes', len(holes))
# map triangle vertices -> 3D
newpos = np.zeros((len(TV), 3))
newpos[:nb] = V[bverts]
# Steiner points: on boundary segments (marker!=0) or interior
vm = T['vertex_markers'].ravel()
# locate boundary Steiner points on their original segment
segP = P2[segs]  # (S,2,2)
for k in range(nb, len(TV)):
    p = TV[k]
    if vm[k] != 0:
        a = segP[:, 0]; b = segP[:, 1]; ab = b - a; t = np.clip(((p - a) * ab).sum(1) / (ab * ab).sum(1), 0, 1)
        d = np.linalg.norm(a + ab * t[:, None] - p, axis=1); s = int(np.argmin(d))
        A3, B3 = V[bverts[segs[s, 0]]], V[bverts[segs[s, 1]]]
        newpos[k] = A3 + (B3 - A3) * t[s]
    else:
        newpos[k] = [p[0], np.nan, p[1]]
inter = np.isnan(newpos[:, 1])
# heights for interior points: y0 from E0 top surface, blend with bridge
R0 = RayMeshIntersector(E0)
q = newpos[inter].copy(); q[:, 1] = 300.0
lc, ri, ti = R0.intersects_location(q, np.tile([0, -1.0, 0], (len(q), 1)), multiple_hits=False)
y0 = np.full(len(q), np.nan); y0[ri] = lc[:, 1]
H, zq, wq = targets(np.column_stack([q[:, 0], y0, q[:, 2]]))
yi = y0 + wq * (H - y0)
assert np.isfinite(yi).all(), 'ray miss'
newpos[inter, 1] = yi
# assemble: vertex ids for triangle verts
vid = np.empty(len(TV), np.int64); vid[:nb] = bverts
vid[nb:] = len(V) + np.arange(len(TV) - nb)
Vn = np.vstack([V, newpos[nb:]])
band_tris = vid[TT][:, ::-1]          # CCW in (x,z) gives -y normal -> flip
# split outer neighbours of boundary edges that received Steiner points
split = defaultdict(list)   # (a,b) original oriented band edge -> list of (t, vid)
for k in range(nb, len(TV)):
    if vm[k] != 0:
        p = TV[k]; a = segP[:, 0]; b = segP[:, 1]; ab = b - a; t = np.clip(((p - a) * ab).sum(1) / (ab * ab).sum(1), 0, 1)
        d = np.linalg.norm(a + ab * t[:, None] - p, axis=1); s = int(np.argmin(d))
        split[(bverts[segs[s, 0]], bverts[segs[s, 1]])].append((t[s], vid[k]))
Fo = F[~fin].tolist(); out = []
emap = {}
for (a, b), lst in split.items():
    emap[(b, a)] = [v for _, v in sorted(lst, key=lambda z: -z[0])]   # outer face uses edge b->a; points ordered from b to a
nsplit = 0
for f in Fo:
    done = False
    for e in range(3):
        u, w = f[e], f[(e + 1) % 3]; o = f[(e + 2) % 3]
        if (u, w) in emap:
            chain = [u] + emap[(u, w)] + [w]
            for p0, p1 in zip(chain[:-1], chain[1:]): out.append([p0, p1, o])
            done = True; nsplit += 1; break
    if not done: out.append(f)
# a face may have more than one split edge; iterate until none left
def resolve(faces):
    changed = True
    while changed:
        changed = False; res = []
        for f in faces:
            hit = False
            for e in range(3):
                u, w = f[e], f[(e + 1) % 3]; o = f[(e + 2) % 3]
                if (u, w) in emap:
                    chain = [u] + emap[(u, w)] + [w]
                    for p0, p1 in zip(chain[:-1], chain[1:]): res.append([p0, p1, o])
                    hit = True; changed = True; break
            if not hit: res.append(f)
        faces = res
    return faces
# remove emap entries already consumed? (each outer face edge (u,w) appears once) -> resolve on all outer faces
out = resolve(Fo)
Fn = np.vstack([np.array(out), band_tris])
E2 = trimesh.Trimesh(Vn, Fn, process=False)
E2.remove_unreferenced_vertices()
E2 = trimesh.Trimesh(E2.vertices, E2.faces, process=True)
print('E2 faces', len(E2.faces), 'watertight', E2.is_watertight, 'winding', E2.is_winding_consistent, 'vol', round(E2.volume / 1000, 2))
E2.export('v6/out/E2.stl')
