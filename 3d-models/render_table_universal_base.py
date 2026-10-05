import trimesh, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
src = open('table_stands.py').read().split('CONFIG = {')[0]; ns = {}; exec(src, ns)
def add(a, m, col, alpha=1.0, edge=0.05):
    pc = Poly3DCollection(m.triangles, edgecolor=(0, 0, 0, edge), linewidths=0.15); n = m.face_normals
    sh = 0.4 + 0.6*np.clip(n @ np.array([0.45, -0.55, 0.7]), 0, 1)
    pc.set_facecolor(np.c_[sh*col[0], sh*col[1], sh*col[2], np.full_like(sh, alpha)]); a.add_collection3d(pc)
RACK, BASE, BLUE, ORANGE = (0.33, 0.35, 0.4), (0.25, 0.62, 0.38), (0.15, 0.45, 0.9), (0.95, 0.55, 0.1)
B = trimesh.load('_ub_base.stl'); B1 = trimesh.load('_rb_base_5.stl')
fig = plt.figure(figsize=(24, 12))
a = fig.add_subplot(2, 4, 1, projection='3d'); add(a, B1, (0.6, 0.6, 0.62))
a.set_xlim(-10, 60); a.set_ylim(-20, 80); a.set_zlim(0, 70); a.set_box_aspect((70, 100, 70)); a.view_init(12, 20); a.set_axis_off(); a.set_title('Before: wedge gap under the back rest')
a = fig.add_subplot(2, 4, 5, projection='3d'); add(a, B, BASE)
a.set_xlim(-10, 60); a.set_ylim(-20, 80); a.set_zlim(0, 70); a.set_box_aspect((70, 100, 70)); a.view_init(12, 20); a.set_axis_off(); a.set_title('After: gusset follows the back rest, gap filled')
a = fig.add_subplot(2, 4, 2)
for m, c, lab in [(B1, '#999', 'before'), (B, '#1a7a3a', 'after (universal base)')]:
    s = m.section(plane_origin=[-3, 0, 0], plane_normal=[1, 0, 0])
    for i, e in enumerate(s.discrete): a.plot(e[:, 1], e[:, 2], color=c, lw=1.6 if c != '#999' else 1.0, label=lab if i == 0 else None)
a.set_aspect('equal'); a.grid(True, alpha=0.3); a.legend(); a.set_title('Side profile through a back rest'); a.set_xlim(-25, 135); a.set_ylim(-3, 150)
for j, N in enumerate((3, 5)):
    R = trimesh.load(f'_ub_rack_{N}.stl'); lift, LP = np.load(f'_ub_{N}.npy'); ns['N'], ns['LP'] = N, LP
    for v, (elev, azim, t) in enumerate([(14, -128, 'front'), (20, 45, 'back')]):
        a = fig.add_subplot(2, 4, 3 + v + 4*j, projection='3d')
        add(a, R, RACK); add(a, B, BASE)
        if v == 0:
            for k, c in enumerate(ns['card_slabs'](lift, None, +1)):
                if k == 1: c.apply_translation([90, 0, 0])
                add(a, c, ORANGE if k == 1 else BLUE, 0.45 if k == 1 else 0.3, 0)
        zt = 420 if N == 5 else 330
        a.set_xlim(-10, 200); a.set_ylim(-40, 160); a.set_zlim(0, zt); a.set_box_aspect((210, 200, zt)); a.view_init(elev, azim); a.set_axis_off()
        a.set_title(f'{N}-card rack on the universal base ({t})')
a = fig.add_subplot(2, 4, 6)
for N, c in [(3, '#d0661a'), (5, '#2a6fd8')]:
    R = trimesh.load(f'_ub_rack_{N}.stl')
    for i, e in enumerate(R.section(plane_origin=[-3, 0, 0], plane_normal=[1, 0, 0]).discrete): a.plot(e[:, 1], e[:, 2], color=c, lw=1, label=f'{N}-card rack' if i == 0 else None)
for e in B.section(plane_origin=[-3, 0, 0], plane_normal=[1, 0, 0]).discrete: a.plot(e[:, 1], e[:, 2], color='#1a7a3a', lw=1.6)
a.set_aspect('equal'); a.grid(True, alpha=0.3); a.legend(); a.set_title('Both racks fit the same base (side section)')
plt.tight_layout(); plt.savefig('/home/user/RR/3d-models/table_universal_base_preview.png', dpi=58)
