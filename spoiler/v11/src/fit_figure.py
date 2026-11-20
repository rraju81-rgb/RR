"""v11: how the spoiler sits on the owner's Polo GTI model. Gap map under the spoiler (plan view) and sections.
Writes v11/docs/fit_on_polo_gti.png.   Run from spoiler/ after fit_spoiler.py."""
import json, numpy as np, trimesh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from scipy.spatial import cKDTree
U = trimesh.load('v11/out/user_exterior_carframe0.ply', process=False)
f = json.load(open('v11/out/fit.json')); R = np.array(f['R']); t = np.array(f['t'])
E = trimesh.load('v6/out/E2.stl'); E.vertices = E.vertices @ R.T + t
contact = np.load('v10/out/E2_contact.npy')
c = U.triangles_center; keep = (np.abs(c[:, 0]) < 900) & (c[:, 2] > -900) & (c[:, 2] < 700) & (c[:, 1] > -650) & (c[:, 1] < 160)
T = trimesh.Trimesh(U.vertices, U.faces[keep], process=False); Pt, fi = trimesh.sample.sample_surface(T, 600000, seed=1)
kd = cKDTree(Pt)
S = E.triangles_center[contact]; N = E.face_normals[contact]
d, j = kd.query(S); sgn = -np.sign(((S - Pt[j]) * N).sum(1)); gap = d * sgn - 0.0       # underside to car, + = off the car
fig = plt.figure(figsize=(17, 12))
ax = fig.add_subplot(2, 1, 1)
sc = ax.scatter(S[:, 0], S[:, 2], c=np.clip(gap, -30, 30), s=0.4, cmap='RdBu_r', vmin=-30, vmax=30)
cb = plt.colorbar(sc, ax=ax, fraction=0.025); cb.set_label('gap to your model, mm  (blue: would be inside the car, red: off the car)')
ax.set_aspect('equal'); ax.invert_yaxis(); ax.set_xlabel('x across the car (mm)'); ax.set_ylabel('z, front at the top (mm)')
main = np.abs(S[:, 0]) < 540
ax.set_title('Underside of the spoiler on your Polo GTI model: centre %d%% within 3 mm and %d%% within 10 mm (tape gap 1.5 mm); end fins %d%% within 10 mm' % (
    round(f['roof_and_tailgate']['within_3mm_pct']), round(f['roof_and_tailgate']['within_10mm_pct']), round(f['fins']['within_10mm_pct'])), fontsize=11)
for k, x in enumerate([0.0, -450.0, -590.0]):
    a = fig.add_subplot(2, 3, 4 + k)
    for mesh, col, lw in [(U, '#c0392b', 0.9), (E, 'k', 1.3)]:
        seg = trimesh.intersections.mesh_plane(mesh, [1, 0, 0], [x, 0, 0])
        if len(seg): a.add_collection(LineCollection(seg[:, :, [2, 1]], colors=col, linewidths=lw))
    zc = E.vertices[np.abs(E.vertices[:, 0] - x) < 5][:, 2]; yc = E.vertices[np.abs(E.vertices[:, 0] - x) < 5][:, 1]
    a.set_xlim(zc.min() - 60, zc.max() + 60); a.set_ylim(yc.min() - 90, yc.max() + 40); a.set_aspect('equal'); a.grid(alpha=0.3)
    a.set_title('section at x = %d mm: your model (red), spoiler (black)' % x, fontsize=10); a.set_xlabel('z to the rear (mm)')
plt.tight_layout(); plt.savefig('v11/docs/fit_on_polo_gti.png', dpi=100)
print('centre gap median %.1f, fins median %.1f' % (np.median(gap[main]), np.median(gap[~main])))
