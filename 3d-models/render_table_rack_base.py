import trimesh, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
src = open('table_stands.py').read().split('CONFIG = {')[0]; ns = {}; exec(src, ns)
def add(a, m, col, alpha=1.0, edge=0.06):
    pc = Poly3DCollection(m.triangles, edgecolor=(0, 0, 0, edge), linewidths=0.15); n = m.face_normals
    sh = 0.4 + 0.6*np.clip(n @ np.array([0.45, -0.55, 0.7]), 0, 1)
    pc.set_facecolor(np.c_[sh*col[0], sh*col[1], sh*col[2], np.full_like(sh, alpha)]); a.add_collection3d(pc)
def setup(a, zt, yr=(-40, 160), elev=16, azim=-128):
    a.set_xlim(-10, 200); a.set_ylim(*yr); a.set_zlim(0, zt); a.set_box_aspect((210, yr[1]-yr[0], zt)); a.view_init(elev, azim); a.set_axis_off()
RACK, BASE, BLUE, ORANGE = (0.33, 0.35, 0.4), (0.25, 0.62, 0.38), (0.15, 0.45, 0.9), (0.95, 0.55, 0.1)
fig = plt.figure(figsize=(24, 13))
for row, N in enumerate((3, 5)):
    R = trimesh.load(f'_rb_rack_{N}.stl'); B = trimesh.load(f'_rb_base_{N}.stl'); lift, LP = np.load(f'_rb_{N}.npy')
    ns['N'], ns['LP'] = N, LP; zt = 420 if N == 5 else 330
    for col, (elev, azim, ttl) in enumerate([(14, -128, 'front'), (20, 45, 'back')]):
        a = fig.add_subplot(2, 4, row*4 + col + 1, projection='3d')
        add(a, R, RACK); add(a, B, BASE)
        if col == 0:
            for k, c in enumerate(ns['card_slabs'](lift, None, +1)):
                if k == 1: c.apply_translation([90, 0, 0])
                add(a, c, ORANGE if k == 1 else BLUE, 0.45 if k == 1 else 0.3, 0)
        setup(a, zt, elev=elev, azim=azim)
        a.set_title(f'{N}-card display, {ttl}' + ('\norange card sliding in from the open end' if col == 0 else '\nrib-stiffened rack back on the green base'))
    a = fig.add_subplot(2, 4, row*4 + 3, projection='3d'); add(a, B, BASE)
    setup(a, 200 if N == 5 else 150, elev=22, azim=-130); a.set_title(f'Base for {N} cards (frame-holder style)\nprints upright, no supports')
    a = fig.add_subplot(2, 4, row*4 + 4)
    for m, c in [(R, '#444'), (B, '#2a8a4a')]:
        s = m.section(plane_origin=[3, 0, 0], plane_normal=[1, 0, 0])
        for e in s.discrete: a.plot(e[:, 1], e[:, 2], color=c, lw=1.2)
    for c in ns['card_slabs'](lift, None, +1):
        s = c.section(plane_origin=[55, 0, 0], plane_normal=[1, 0, 0])
        for e in s.discrete: a.plot(e[:, 1], e[:, 2], color='#2a6fd8', lw=1.0)
    a.set_aspect('equal'); a.grid(True, alpha=0.3); a.set_xlabel('depth (mm), viewer on the left')
    a.set_title(f'{N}-card side section through the end rib (grey rack, green base, blue cards)')
plt.tight_layout(); plt.savefig('/home/user/RR/3d-models/table_rack_base_preview.png', dpi=58)
