import numpy as np, trimesh

def stable_orient(m, top=3):
    """Return list of (transform, probability) for the most stable resting poses, centred on the bed."""
    T, prob = trimesh.poses.compute_stable_poses(m, n_samples=1, threshold=0.0)
    out = []
    for t, p in list(zip(T, prob))[:top]:
        mm = m.copy(); mm.apply_transform(t)
        b = mm.bounds; c = np.array([(b[0][0] + b[1][0]) / 2, (b[0][1] + b[1][1]) / 2, b[0][2]])
        tt = np.eye(4); tt[:3, 3] = -c
        out.append((tt @ t, float(p)))
    return out

def max_scale_on_bed(m, bed, angles=np.arange(0, 180, 2)):
    """Largest uniform scale so that mesh m (in its current pose) fits bed (x,y,z), rotating only about Z."""
    hull = m.convex_hull.vertices
    best, best_a = 0, 0
    h = np.ptp(hull[:, 2])
    for a in np.radians(angles):
        R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
        xy = hull[:, :2] @ R.T
        w, d = np.ptp(xy, axis=0)
        s = min(bed[0] / w, bed[1] / d, bed[2] / h)
        if s > best:
            best, best_a = s, a
    return best, np.degrees(best_a)
