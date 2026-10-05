import trimesh, numpy as np, json, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from trimesh.creation import box
exec(open('easel_v3.py').read().split("if __name__ == '__main__':")[0])
def add(a, m, col, alpha=1.0):
    pc = Poly3DCollection(m.triangles, edgecolor='none'); n = m.face_normals
    sh = 0.45 + 0.55*np.clip(n @ np.array([0.4, -0.5, 0.75]), 0, 1)
    pc.set_facecolor(np.c_[sh*col[0], sh*col[1], sh*col[2], np.full_like(sh, alpha)]); a.add_collection3d(pc)
def setup(a, ext, elev=16, azim=-128):
    a.set_xlim(-10, 200); a.set_ylim(*ext[0]); a.set_zlim(*ext[1]); a.set_box_aspect((210, ext[0][1]-ext[0][0], ext[1][1]-ext[1][0])); a.view_init(elev, azim); a.set_axis_off()
mv = lambda m, M: (lambda c: (c.apply_transform(M), c)[1])(m.copy())
GREY, BLUE, ORANGE, GREEN, RED = (0.32, 0.34, 0.38), (0.15, 0.45, 0.9), (0.95, 0.55, 0.1), (0.25, 0.65, 0.35), (0.8, 0.3, 0.25)
P, B, L = [trimesh.load(f'_easel_{n}.stl') for n in ('panel', 'base', 'leg')]
grooves = json.load(open('_easel_grooves.json'))
fig = plt.figure(figsize=(24, 14))
# folded (as printed), shown standing
a = fig.add_subplot(2, 4, 1, projection='3d')
for m, c in [(P, GREY), (B, GREEN), (L, RED)]:
    mm = mv(m, tilt(0)); mm.apply_translation([8, 0, 0]); add(a, mm, c)
setup(a, ((-40, 60), (0, 180)), 20, -60); a.set_title('Folded flat (as printed)\ngrey panel, green base, red leg')
for i, alpha in enumerate([10, 15, 25]):
    a = fig.add_subplot(2, 4, 2 + i, projection='3d')
    T = tilt(alpha); phi = base_angle(alpha); psi, _ = leg_angle(alpha)
    for m, M, c in [(P, T, GREY), (B, T @ rot(H1, -phi), GREEN), (L, T @ rot(H2, psi), RED)]:
        mm = mv(m, M); mm.apply_translation([8, 0, 0]); add(a, mm, c)
    for k in range(3):
        zg = 3.7 + 4.6*k + 0.3; sl = (k == 1)
        cb = box(bounds=[[1.5 + (90 if sl else 0), 55*k + 3.2, zg], [109.5 + (90 if sl else 0), 55*k + 168, zg + 0.5]])
        cb.apply_transform(T); cb.apply_translation([8, 0, 0]); add(a, cb, ORANGE if sl else BLUE, 0.45 if sl else 0.3)
    setup(a, ((-50, 170), (0, 260)))
    a.set_title(f'Display at {alpha} deg (groove {i+1 if alpha < 20 else i + 2} of 4)\norange card sliding in from the open end')
# side section with all four leg positions
a = fig.add_subplot(2, 4, 8)
for alpha, col in zip([10, 15, 20, 25], ['#1f77b4', '#2ca02c', '#ff7f0e', '#d62728']):
    T = tilt(alpha); phi = base_angle(alpha); psi, _ = leg_angle(alpha)
    for m, M, lw in [(P, T, 1.0), (L, T @ rot(H2, psi), 1.0)]:
        s = mv(m, M).section(plane_origin=[60, 0, 0], plane_normal=[1, 0, 0])
        for e in s.discrete: a.plot(e[:, 1], e[:, 2], color=col, lw=lw)
    a.plot([], [], color=col, label=f'{alpha} deg')
s = mv(B, tilt(15) @ rot(H1, -base_angle(15))).section(plane_origin=[60, 0, 0], plane_normal=[1, 0, 0])
for e in s.discrete: a.fill(e[:, 1], e[:, 2], color='#3a3')
a.set_aspect('equal'); a.grid(True, alpha=0.3); a.legend(); a.set_title('Side section: 4 angle settings\n(green base with 4 grooves)'); a.set_xlabel('depth (mm)')
# one-sided stands
for j, Nc in enumerate([3, 5]):
    body = trimesh.load(f'table_onesided_{Nc}card.stl'); lift, LPc = np.load(f'_os_{Nc}.npy')
    ns['N'], ns['LP'] = Nc, LPc
    for v, (elev, azim) in enumerate([(16, -128), (18, -40)]):
        a = fig.add_subplot(2, 4, 5 + j*1 + (0 if v == 0 else 0), projection='3d') if v == 0 else None
        if a is None: continue
        add(a, body, GREY)
        for k, c in enumerate(ns['card_slabs'](lift, None, +1)):
            if k == 1: c.apply_translation([90, 0, 0])
            add(a, c, ORANGE if k == 1 else BLUE, 0.45 if k == 1 else 0.3)
        setup(a, ((-40, 160), (0, 420 if Nc == 5 else 300)), 14, -125)
        a.set_title(f'One-sided stand, {Nc} cards\nlattice back leg + base')
a = fig.add_subplot(2, 4, 7, projection='3d')
body = trimesh.load('table_onesided_5card.stl'); add(a, body, GREY)
setup(a, ((-40, 160), (0, 260)), 18, -40); a.set_title('One-sided 5-card stand from behind:\ndiamond lattice support')
plt.tight_layout(); plt.savefig('/home/user/RR/3d-models/table_stands_v3_preview.png', dpi=58)
