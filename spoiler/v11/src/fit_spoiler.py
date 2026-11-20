"""v11: place the spoiler on the owner's Polo GTI model (FINAL_MODEL_11.fbx, via user_exterior_carframe0.ply).
The spoiler's underside (the faces that sit on the car, v10/out/E2_contact.npy) less the 1.5 mm tape gap must land on the
model's roof and tailgate. Coarse search over fore-aft position, height and pitch, then point-to-plane ICP (6 degrees of
freedom). The model's factory roof spoiler and roof antenna are left out of the target. Writes v11/out/fit.json."""
import sys, json; sys.path.insert(0, 'v6/car/src')
import numpy as np, trimesh
from scipy.spatial import cKDTree

E = trimesh.load('v6/out/E2.stl'); contact = np.load('v10/out/E2_contact.npy')
U = trimesh.load('v11/out/user_exterior_carframe0.ply', process=False)
# target: the model's exterior near the roof's rear end, without the antenna (tall thin part above the roof)
c = U.triangles_center; keep = (np.abs(c[:, 0]) < 900) & (c[:, 2] > -900) & (c[:, 2] < 700) & (c[:, 1] > -650) & (c[:, 1] < 160)
T = trimesh.Trimesh(U.vertices, U.faces[keep], process=False)
Pt = T.sample(400000, return_index=False)
# target normals from the faces (sign-free for point-to-plane)
Pt, fi = trimesh.sample.sample_surface(T, 400000); Nt = T.face_normals[fi]
kd = cKDTree(Pt)
# source: contact face centres moved 1.5 mm into the car along the face normal (where the car surface should be)
S_all = E.triangles_center[contact] + E.face_normals[contact] * 1.5; A_all = E.area_faces[contact]; N_all = E.face_normals[contact]
cen = (S_all * (A_all / A_all.sum())[:, None]).sum(0)
rng = np.random.default_rng(0)
def subset(n):
    k = rng.choice(len(S_all), n, replace=False, p=A_all / A_all.sum()); return S_all[k], np.full(n, 1.0 / n)
S, w = subset(3000)

def pose(dz, dy, pitch_deg, dx=0.0, R=None):
    if R is None:
        a = np.radians(pitch_deg); R = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
    return R, cen + np.array([dx, dy, dz]) - R @ cen

def score(R, t, cap=60.0):
    Q = S @ R.T + t; d, j = kd.query(Q, distance_upper_bound=cap); d = np.where(np.isfinite(d), d, cap)
    return float((w * np.minimum(d, cap)).sum()), d

# Fore-aft position: on this model the fit is almost the same anywhere along the smooth roof (mean 4.8-6 mm), so the
# position is set where the spoiler belongs: its rear contact edge (the rim line, z = 205.5 mm at the centre in the design
# position) on the model's crest, where its tailgate top panel ends and the rear glass drops away (z = 140.5 mm). That is
# where the factory roof spoiler sits. Height and pitch are then fitted.
DZ = -65.0
best = None
for dz in [DZ]:
    for dy in np.arange(-100, 81, 2.0):
        for p in np.arange(-8, 8.1, 1.0):
            R, t = pose(dz, dy, p); s, _ = score(R, t)
            if best is None or s < best[0]: best = (s, dz, dy, p)
print('coarse best: mean distance %.1f mm at dz %.0f, dy %.0f, pitch %d' % best)
s0, dz, dy, p = best
for dz2 in [DZ]:
    for dy2 in np.arange(dy - 8, dy + 8.1, 2.0):
        for p2 in np.arange(p - 6, p + 6.1, 1.0):
            R, t = pose(dz2, dy2, p2); s, _ = score(R, t)
            if s < best[0]: best = (s, dz2, dy2, p2)
print('fine grid: mean distance %.2f mm at dz %.1f, dy %.1f, pitch %.1f' % best)
R, t = pose(best[1], best[2], best[3])
S, w = subset(20000)
# point-to-plane ICP, symmetric: pitch about x through the centroid, height and fore-aft only (car and spoiler are both
# mirror-symmetric, so no sideways shift, yaw or roll)
pitch, ty, tz = np.radians(best[3]), best[2], best[1]
for it in range(60):
    R, t = pose(tz, ty, np.degrees(pitch))
    Q = S @ R.T + t; d, j = kd.query(Q); n = Nt[j]; r = ((Q - Pt[j]) * n).sum(1)
    wr = w * np.where(np.abs(r) < 5.0, 1.0, 5.0 / np.maximum(np.abs(r), 1e-9)) * (d < 40.0)
    qc = cen + np.array([0, ty, tz])
    dQ = np.column_stack([np.zeros(len(Q)), -(Q[:, 2] - qc[2]), Q[:, 1] - qc[1]])          # d/dpitch
    J = np.column_stack([(dQ * n).sum(1), n[:, 1], n[:, 2]])
    H = (J * wr[:, None]).T @ J + 1e-6 * np.eye(3); g = (J * (wr * r)[:, None]).sum(0)
    J = J[:, :2]; H = H[:2, :2]; g = g[:2]                                    # fore-aft fixed
    x = -np.linalg.solve(H, g); pitch += x[0]; ty += x[1]
    if np.abs(x).max() < 1e-4: break
R, t = pose(tz, ty, np.degrees(pitch))
S, A, Nc = S_all, A_all, N_all
Q = S @ R.T + t; d, j = kd.query(Q); n = Nt[j]; r = ((Q - Pt[j]) * n).sum(1)
# signed gap: + where the spoiler's underside is off the car, - where it would be inside (sign from the contact normal)
sgn = np.sign(((Q - Pt[j]) * (Nc @ R.T)).sum(1)) * -1.0
gap = d * sgn
x = Q[:, 0]; main = np.abs(x) < 540; fins = ~main
def stats(m):
    g = gap[m]; ww = A[m] / A[m].sum()
    return dict(median_mm=round(float(np.median(g)), 1), p10_mm=round(float(np.percentile(g, 10)), 1), p90_mm=round(float(np.percentile(g, 90)), 1),
                within_3mm_pct=round(100 * float(ww[np.abs(g) < 3].sum()), 1), within_10mm_pct=round(100 * float(ww[np.abs(g) < 10].sum()), 1))
ang = np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1)))
res = dict(R=R.tolist(), t=t.tolist(), pitch_deg=round(float(np.degrees(pitch)), 2), rotation_deg=round(float(ang), 2), translation_mm=[round(float(v), 1) for v in (R @ cen + t - cen)],
           roof_and_tailgate=stats(main), fins=stats(fins), iterations=it + 1)
json.dump(res, open('v11/out/fit.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in res.items() if k not in ('R', 't')}, indent=1))
