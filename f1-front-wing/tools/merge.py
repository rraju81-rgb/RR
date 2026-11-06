"""Merge posed parts into single solids: close tab clearances, boolean-union, drop internal voids."""
import os, sys, pickle, numpy as np, trimesh, manifold3d as mf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from faces import plane_groups

def close_clearances(B, A, gmin=0.03, gmax=0.8, min_area=4.0):
    """Move planar wall groups of mesh B that face mesh A across a small uniform gap onto A. Returns moved count."""
    V = B.vertices.copy()
    moved = 0
    disp = np.zeros_like(V); cnt = np.zeros(len(V))
    for n, d, fs in plane_groups(B, flat_deg=0.5, merge_deg=1.0, dist_tol=0.05):
        area = B.area_faces[fs].sum()
        if area < min_area:
            continue
        # sample points on this wall group
        pts = B.triangles_center[fs]
        cp, dist, tri = trimesh.proximity.closest_point(A, pts)
        facing = (A.face_normals[tri] @ n) < -0.95
        w = B.area_faces[fs]
        ok = facing & (dist > gmin) & (dist < gmax)
        if w[ok].sum() < 0.8 * area:
            continue
        g = np.average(dist[ok], weights=w[ok])
        if np.std(dist[ok]) > 0.06:
            continue
        vid = np.unique(B.faces[fs].ravel())
        disp[vid] += n * g; cnt[vid] += 1
        moved += 1
    B.vertices = V + disp
    return moved

def to_manifold(m):
    if hasattr(mf, 'Mesh64'):
        mesh = mf.Mesh64(vert_properties=np.asarray(m.vertices, np.float64), tri_verts=np.asarray(m.faces, np.uint64))
    else:
        mesh = mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32))
    M = mf.Manifold(mesh)
    if M.status() != mf.Error.NoError:
        raise RuntimeError(f'manifold status {M.status()}')
    return M

def from_manifold(M):
    o = M.to_mesh64() if hasattr(M, 'to_mesh64') else M.to_mesh()
    return trimesh.Trimesh(np.asarray(o.vert_properties)[:, :3].astype(np.float64), np.asarray(o.tri_verts), process=False)

def drop_cavities(m):
    parts = m.split(only_watertight=False)
    if len(parts) == 1:
        return m, 1, 0, 0.0
    keep = [p for p in parts if p.volume > 0]
    voids = [p for p in parts if p.volume <= 0]
    return (trimesh.util.concatenate(keep) if len(keep) > 1 else keep[0]), len(keep), len(voids), sum(-p.volume for p in voids)

def merge_group(P, pose, ids, joints, label=''):
    W = {p: P[p].copy().apply_transform(pose[p]) for p in ids}
    vol_parts = sum(W[p].volume for p in ids)
    nmoves = 0
    for a, b in joints:
        if a in W and b in W:
            nmoves += close_clearances(W[b], W[a])
    Ms = [to_manifold(W[p]) for p in ids]
    U = mf.Manifold.batch_boolean(Ms, mf.OpType.Add)
    print(f"   manifold: status {U.status()}, genus {U.genus()}, solids {len(U.decompose())}, volume {U.volume()/1000:.1f} cm3")
    out = from_manifold(U)
    out, nbodies, nvoids, voidvol = drop_cavities(out)
    print(f"{label}: {len(ids)} parts -> {nbodies} body(ies); walls moved {nmoves}; internal voids removed {nvoids} ({voidvol:.0f} mm3); "
          f"watertight {out.is_watertight}; volume {out.volume/1000:.1f} cm3 (parts sum {vol_parts/1000:.1f})")
    return out

def snap_facing_vertices(B, A, dmin=0.005, dmax=0.8, opp=-0.9, overshoot=0.05):
    """Snap vertices of B that face A across a small gap onto A's surface. Returns number snapped."""
    V = B.vertices
    # candidate vertices: near A's bounding box
    lo, hi = A.bounds[0] - dmax, A.bounds[1] + dmax
    cand = np.where(np.all((V >= lo) & (V <= hi), axis=1))[0]
    if len(cand) == 0:
        return 0
    cp, dist, tri = trimesh.proximity.closest_point(A, V[cand])
    sel = (dist > dmin) & (dist < dmax)
    cand, cp, tri = cand[sel], cp[sel], tri[sel]
    if len(cand) == 0:
        return 0
    # opposition test: any adjacent face of the vertex whose normal opposes A's face normal
    vf = B.vertex_faces[cand]                     # padded with -1
    nA = A.face_normals[tri]
    ok = np.zeros(len(cand), bool)
    for k in range(vf.shape[1]):
        f = vf[:, k]
        valid = f >= 0
        dots = np.einsum('ij,ij->i', B.face_normals[np.where(valid, f, 0)], nA)
        ok |= valid & (dots < opp)
    newV = V.copy()
    dirv = cp[ok] - V[cand[ok]]
    dirv /= np.linalg.norm(dirv, axis=1)[:, None]
    newV[cand[ok]] = cp[ok] + dirv * overshoot      # push slightly past A's surface so the parts overlap
    
    B.vertices = newV
    return int(ok.sum())

def merge_group2(P, pose, ids, joints, label='', passes=2):
    W = {p: P[p].copy().apply_transform(pose[p]) for p in ids}
    vol_parts = sum(W[p].volume for p in ids)
    nsnap = 0
    for _ in range(passes):
        for a, b in joints:
            if a in W and b in W:
                nsnap += snap_facing_vertices(W[b], W[a])
                nsnap += snap_facing_vertices(W[a], W[b])
    Ms = [to_manifold(W[p]) for p in ids]
    U = mf.Manifold.batch_boolean(Ms, mf.OpType.Add)
    out = from_manifold(U)
    out, nbodies, nvoids, voidvol = drop_cavities(out)
    g = to_manifold(out).genus()
    print(f"{label}: {len(ids)} parts -> {nbodies} solid(s); vertices snapped {nsnap}; voids removed {nvoids}; genus {g}; "
          f"watertight {out.is_watertight}; volume {out.volume/1000:.1f} cm3 (parts {vol_parts/1000:.1f})")
    return out

def slit_fillers(A, B, gmin=0.02, gmax=0.9, min_area=1.0, overlap=0.05):
    """Thin convex 'filler' solids between facing parallel planar walls of A and B (tab clearance slits)."""
    GA = [(n, d, fs) for n, d, fs in plane_groups(A, flat_deg=0.5, merge_deg=1.0, dist_tol=0.05) if A.area_faces[fs].sum() >= min_area]
    GB = [(n, d, fs) for n, d, fs in plane_groups(B, flat_deg=0.5, merge_deg=1.0, dist_tol=0.05) if B.area_faces[fs].sum() >= min_area]
    fillers = []
    for nb, db, fb in GB:
        cb = B.triangles_center[fb]; wb = B.area_faces[fb]
        for na, da, fa in GA:
            if np.dot(na, nb) > -0.995:
                continue
            gap = -(da + db)        # na.x = da on A's plane, nb.x = db on B's; with na = -nb, gap = distance from B plane to A plane along nb
            if not (gmin < gap < gmax):
                continue
            # B face centres must project inside A's wall region
            proj = cb + nb[None] * gap
            cp, dist, tri = trimesh.proximity.closest_point(A, proj)
            inA = np.isin(tri, fa) & (dist < 0.05)
            if wb[inA].sum() < 0.5 * wb.sum():
                continue
            VB = B.vertices[np.unique(B.faces[fb[inA]])]
            VA = VB + nb[None] * gap
            pts = np.vstack([VB - nb[None] * overlap, VA + nb[None] * overlap])
            try:
                h = trimesh.convex.convex_hull(pts)
                if h.volume > 1e-6:
                    fillers.append(h)
            except Exception:
                pass
    return fillers

def merge_group3(P, pose, ids, joints, label=''):
    W = {p: P[p].copy().apply_transform(pose[p]) for p in ids}
    vol_parts = sum(W[p].volume for p in ids)
    fill = []
    for a, b in joints:
        if a in W and b in W:
            fill += slit_fillers(W[a], W[b])
            fill += slit_fillers(W[b], W[a])
    Ms = [to_manifold(W[p]) for p in ids] + [to_manifold(f) for f in fill]
    U = mf.Manifold.batch_boolean(Ms, mf.OpType.Add)
    out = from_manifold(U)
    out, nbodies, nvoids, voidvol = drop_cavities(out)
    g = to_manifold(out).genus()
    print(f"{label}: {len(ids)} parts + {len(fill)} slit fillers -> {nbodies} solid(s); voids removed {nvoids}; genus {g}; "
          f"watertight {out.is_watertight}; volume {out.volume/1000:.2f} cm3 (parts {vol_parts/1000:.2f})")
    return out

def _ray_gap(m, origins, dirs, gmax):
    locs, ridx, tidx = m.ray.intersects_location(origins, dirs, multiple_hits=False)
    dist = np.full(len(origins), np.inf); hn = np.zeros((len(origins), 3))
    dist[ridx] = np.linalg.norm(locs - origins[ridx], axis=1); hn[ridx] = m.face_normals[tidx]
    opp = np.einsum('ij,ij->i', dirs, hn) < -0.9
    return np.where(opp & (dist < gmax), dist, np.inf)

def heal_slits(m, gmax=0.9, overlap=0.05, iters=4, verbose=True):
    """Fill thin slits (opposing walls < gmax apart) of a merged solid with small overlapping prisms."""
    for it in range(iters):
        n = m.face_normals; T = m.triangles; c = T.mean(1)
        g_c = _ray_gap(m, c + n * 0.002, n, gmax)
        cand = np.where(np.isfinite(g_c) & (g_c > 0.003))[0]
        if len(cand) == 0:
            break
        # require the three (slightly inset) corners to see the opposing wall too
        gv = []
        for k in range(3):
            p = T[cand, k] * 0.85 + c[cand] * 0.15
            gv.append(_ray_gap(m, p + n[cand] * 0.002, n[cand], gmax))
        gv = np.stack(gv, 1)
        ok = np.all(np.isfinite(gv), axis=1)
        cand, gv = cand[ok], gv[ok]
        if len(cand) == 0:
            break
        prisms = []
        for f, g3 in zip(cand, gv):
            v = T[f]; nf = n[f]
            pts = np.vstack([v - nf * overlap, v + nf[None] * (g3[:, None] + overlap)])
            try:
                h = trimesh.convex.convex_hull(pts)
                if h.volume > 1e-7:
                    prisms.append(h)
            except Exception:
                pass
        Ms = [to_manifold(m)] + [to_manifold(h) for h in prisms]
        m = from_manifold(mf.Manifold.batch_boolean(Ms, mf.OpType.Add))
        m, _, _, _ = drop_cavities(m)
        if verbose:
            print(f"   heal pass {it+1}: bridged {len(prisms)} slit faces -> genus {to_manifold(m).genus()}")
    return m

def coplanar_patches(m, flat_deg=0.5, min_area=1.0):
    """Connected coplanar face patches (region growing over flat edges, no merging of separate regions)."""
    import trimesh.graph as tg
    adj = m.face_adjacency
    flat = m.face_adjacency_angles < np.radians(flat_deg)
    comps = tg.connected_components(adj[flat], nodes=np.arange(len(m.faces)), min_len=1)
    out = []
    for fs in comps:
        fs = np.asarray(fs)
        a = m.area_faces[fs]
        if a.sum() < min_area:
            continue
        n = (m.face_normals[fs] * a[:, None]).sum(0); n /= np.linalg.norm(n)
        d = float(np.dot(n, (m.triangles_center[fs] * a[:, None]).sum(0) / a.sum()))
        out.append((n, d, fs))
    return out

def slit_fillers_patch(A, B, gmin=0.02, gmax=0.9, overlap=0.05):
    PA = coplanar_patches(A); PB = coplanar_patches(B)
    fillers = []
    for nb, db, fb in PB:
        cb = B.triangles_center[fb]; wb = B.area_faces[fb]
        for na, da, fa in PA:
            if np.dot(na, nb) > -0.995:
                continue
            gap = -(da + db)
            if not (gmin < gap < gmax):
                continue
            proj = cb + nb[None] * gap
            cp, dist, tri = trimesh.proximity.closest_point(A, proj)
            inA = np.isin(tri, fa) & (dist < 0.05)
            if wb[inA].sum() < 0.5 * wb.sum():
                continue
            VB = B.vertices[np.unique(B.faces[fb[inA]])]
            # the patch must be compact (convex-ish): hull area vs patch area sanity check
            pts = np.vstack([VB - nb[None] * overlap, VB + nb[None] * (gap + overlap)])
            try:
                h = trimesh.convex.convex_hull(pts)
            except Exception:
                continue
            # reject if hull footprint is much larger than the patch (non-convex patch)
            if h.volume > 1.3 * wb[inA].sum() * (gap + 2 * overlap) + 1e-3:
                continue
            fillers.append(h)
    return fillers

def keep_main(m, frac=0.002):
    parts = m.split(only_watertight=False)
    if len(parts) == 1:
        return m, 0
    vols = np.array([p.volume for p in parts])
    keep = [p for p, v in zip(parts, vols) if v > frac * vols.max()]
    print("   fragment volumes dropped (mm3):", np.round(sorted(v for v in vols if v <= frac * vols.max()), 4))
    return (trimesh.util.concatenate(keep) if len(keep) > 1 else keep[0]), len(parts) - len(keep)

def merge_group4(P, pose, ids, joints, label=''):
    W = {p: P[p].copy().apply_transform(pose[p]) for p in ids}
    vol_parts = sum(W[p].volume for p in ids)
    fill = []
    for a, b in joints:
        if a in W and b in W:
            fill += slit_fillers_patch(W[a], W[b])
            fill += slit_fillers_patch(W[b], W[a])
    Ms = [to_manifold(W[p]) for p in ids] + [to_manifold(f) for f in fill]
    out = from_manifold(mf.Manifold.batch_boolean(Ms, mf.OpType.Add))
    out, nb, nv, vv = drop_cavities(out)
    print(f"{label}: {len(ids)} parts + {len(fill)} slit fillers -> {len(out.split(only_watertight=False))} solid(s); "
          f"genus {to_manifold(out).genus()}; volume {out.volume/1000:.2f} cm3 (parts {vol_parts/1000:.2f})")
    return out
