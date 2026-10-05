import trimesh, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from trimesh.creation import box
def add(a, m, col, alpha=1.0):
    pc = Poly3DCollection(m.triangles, edgecolor='none'); n = m.face_normals
    sh = 0.4 + 0.6*np.clip(n @ np.array([0.5, 0.7, 0.6]), 0, 1)
    pc.set_facecolor(np.c_[sh*col[0], sh*col[1], sh*col[2], np.full_like(sh, alpha)]); a.add_collection3d(pc)
r = trimesh.load('rack_v2_hinged_134.stl'); ybot = r.bounds[0, 1]
fl = trimesh.load('foot_left_hinged.stl'); fl.apply_translation([0, ybot - 4, 0])
fr = trimesh.load('foot_right_hinged.stl'); fr.apply_translation([0, ybot - 4, 0])
cards = [box(bounds=[[25.5, 55*k + 3.2, 3.8 + 4.6*k], [133.5, 55*k + 168, 4.3 + 4.6*k]]) for k in range(6)]
sliding = box(bounds=[[150, 3.2, 3.8], [258, 168, 4.3]])          # bottom card, half-way through sliding in
fig = plt.figure(figsize=(22, 12))
# world view: table = XZ plane, rack y is up -> plot (x, z, y)
P = np.array([[1,0,0,0],[0,0,1,0],[0,1,0,0],[0,0,0,1]], float)
def W(m): m = m.copy(); m.apply_transform(P); return m if m.volume > 0 else (m.invert() or m)
a = fig.add_subplot(1, 3, 1, projection='3d')
add(a, W(r), (0.3, 0.32, 0.36)); add(a, W(fl), (0.2, 0.7, 0.3)); add(a, W(fr), (0.2, 0.7, 0.3))
for c in cards: add(a, W(c), (0.2, 0.5, 0.95), 0.35)
add(a, W(sliding), (0.95, 0.55, 0.1), 0.5)
a.quiver(260, 4, 30, -40, 0, 0, color='#e07000', lw=2)
a.set_xlim(-20, 280); a.set_ylim(-100, 140); a.set_zlim(-10, 450); a.set_box_aspect((300, 240, 460)); a.view_init(14, -62); a.set_axis_off()
a.set_title('Hinged rack on its clip-on feet (green)\norange: bottom card sliding in from the side')
for i, (m, t, xr) in enumerate([(fl, 'Left foot: spine socket', (-15, 30)), (fr, 'Right foot: ledge cradle + tip stop', (105, 145))]):
    a = fig.add_subplot(2, 3, 2 + i*3 - (0 if i == 0 else 0) + (0 if i == 0 else 0), projection='3d') if False else fig.add_subplot(2, 3, 2 + 3*i, projection='3d')
    add(a, W(m), (0.2, 0.7, 0.3))
    rr = trimesh.boolean.intersection([r, box(bounds=[[xr[0], ybot - 5, -50], [xr[1], 30, 60]])], engine='manifold')
    add(a, W(rr), (0.3, 0.32, 0.36), 0.25)
    a.set_xlim(*xr); a.set_ylim(-90, 125); a.set_zlim(ybot - 6, 30); a.set_box_aspect((xr[1]-xr[0], 215, 40)); a.view_init(28, -50); a.set_axis_off(); a.set_title(t + ' (rack ghosted)')
for i, (m, t) in enumerate([(fl, 'left foot'), (fr, 'right foot')]):
    a = fig.add_subplot(2, 3, 3 + 3*i)
    xm = (m.bounds[0, 0] + m.bounds[1, 0]) / 2 + (0 if i == 0 else -8)
    for mesh, c, lw in [(m, '#1a8a3a', 1.4), (r, '#555', 0.8)]:
        s = mesh.section(plane_origin=[xm, 0, 0], plane_normal=[1, 0, 0])
        if s is not None:
            for e in s.discrete: a.plot(e[:, 2], e[:, 1], color=c, lw=lw)
    a.axhline(ybot - 4, color='k', lw=0.6); a.set_xlim(-90, 125); a.set_ylim(ybot - 6, 40); a.set_aspect('equal'); a.grid(True, alpha=0.3)
    a.set_title(f'{t}: side section at x={xm:.0f} (green foot, grey rack)'); a.set_xlabel('front/back (mm)')
plt.tight_layout(); plt.savefig('/home/user/RR/3d-models/rack_table_feet_preview.png', dpi=60)
