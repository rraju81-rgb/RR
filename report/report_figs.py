import trimesh, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from trimesh.creation import box
from trimesh.transformations import rotation_matrix
src = open('table_stands.py').read().split('CONFIG = {')[0]; ns = {}; exec(src, ns)
OUT = '/home/user/RR/report/'
INK, RACK, BASE, CARD, ACC = '#1d2433', (0.30, 0.33, 0.38), (0.20, 0.55, 0.42), (0.16, 0.42, 0.85), (0.93, 0.52, 0.12)
def add(a, m, col, alpha=1.0, edge=0.04):
    pc = Poly3DCollection(m.triangles, edgecolor=(0, 0, 0, edge), linewidths=0.12); n = m.face_normals
    sh = 0.42 + 0.58*np.clip(n @ np.array([0.45, -0.55, 0.7]), 0, 1)
    pc.set_facecolor(np.c_[sh*col[0], sh*col[1], sh*col[2], np.full_like(sh, alpha)]); a.add_collection3d(pc)
def frame(a, xl, yl, zl, elev, azim):
    a.set_xlim(*xl); a.set_ylim(*yl); a.set_zlim(*zl); a.set_box_aspect((xl[1]-xl[0], yl[1]-yl[0], zl[1]-zl[0])); a.view_init(elev, azim); a.set_axis_off()
P = np.array([[1,0,0,0],[0,0,1,0],[0,1,0,0],[0,0,0,1]], float)     # rack frame (x,y,z) -> view (x, z, y): rack standing up
def up(m): m = m.copy(); m.apply_transform(P); return m if m.volume > 0 else (m.invert() or m)

# --- Fig 1: hero - product family ------------------------------------------------------------
fig = plt.figure(figsize=(14, 6.2))
a = fig.add_subplot(1, 3, 1, projection='3d')                          # wall rack with cards
W = trimesh.load('rack_6ledge_130_3mmholes.stl'); add(a, up(W), RACK)
for k in range(6):
    c = box(bounds=[[23, 55*k + 3.2, 3.8 + 4.6*k], [131, 55*k + 168, 4.3 + 4.6*k]]); add(a, up(c), CARD, 0.28, 0)
frame(a, (-10, 140), (-60, 90), (0, 460), 12, -118); a.set_title('Wall rack, 6 cards', color=INK, fontsize=12)
for j, N in enumerate((3, 5)):
    a = fig.add_subplot(1, 3, 2 + j, projection='3d')
    R = trimesh.load(f'_ub_rack_{N}.stl'); B = trimesh.load('_ub_base.stl'); lift, LP = np.load(f'_ub_{N}.npy'); ns['N'], ns['LP'] = N, LP
    add(a, R, RACK); add(a, B, BASE)
    for k, c in enumerate(ns['card_slabs'](lift, None, +1)):
        if k == 1: c.apply_translation([85, 0, 0])
        add(a, c, ACC if k == 1 else CARD, 0.5 if k == 1 else 0.28, 0)
    frame(a, (-10, 200), (-40, 160), (0, 420 if N == 5 else 330), 13, -125)
    a.set_title(f'Tabletop, {N}-card rack on the universal base', color=INK, fontsize=12)
plt.tight_layout(); plt.savefig(OUT + 'fig_hero.png', dpi=130, facecolor='white'); plt.close()

# --- Fig 2: how the card geometry works (dimensioned side section of the wall rack) --------------
fig, axs = plt.subplots(1, 2, figsize=(13, 6.2), gridspec_kw={'width_ratios': [1, 1.25]})
a = axs[0]
s = W.section(plane_origin=[70, 0, 0], plane_normal=[1, 0, 0])
for e in s.discrete: a.fill(e[:, 2], e[:, 1], color='#5a6070')
for k in range(3):
    a.add_patch(plt.Rectangle((3.85 + 4.6*k, 55*k + 3.2), 0.5, 140, color='#2a6fd8', alpha=0.9))
a.annotate('', xy=(-6, 55), xytext=(-6, 0), arrowprops=dict(arrowstyle='<->', color=INK)); a.text(-13, 25, '55 mm\npitch', ha='center', color=INK, fontsize=9)
a.annotate('', xy=(13.0, 63), xytext=(8.4, 63), arrowprops=dict(arrowstyle='<->', color='#c0392b')); a.text(24, 60, '4.6 mm step\nper tier', color='#c0392b', fontsize=9)
a.text(22, 2, 'groove 1.8 mm\n(1.3 behind the\ncorner supports)', fontsize=8.5, color=INK)
a.text(22, 95, 'each card passes\n0.4 mm behind\nthe ledge above', fontsize=8.5, color='#2a6fd8')
a.set_xlim(-18, 52); a.set_ylim(-5, 170); a.set_aspect('equal'); a.set_title('Shingle geometry (side section)', color=INK)
a.set_xlabel('mm from wall'); a.set_ylabel('mm up the wall')
a = axs[1]                                                               # top view: side loading
lg = trimesh.load('ledge_130.stl')
for t in lg.triangles: a.fill(t[:, 0], t[:, 1], color='#5a6070', edgecolor='none')
a.add_patch(plt.Rectangle((21.7, 6.2), 108, 0.6, color='#2a6fd8')); a.add_patch(plt.Rectangle((150, 6.2), 108, 0.6, color='#e8841e'))
a.annotate('', xy=(132, 6.5), xytext=(170, 6.5), arrowprops=dict(arrowstyle='->', lw=2, color='#e8841e'))
a.text(175, 9, 'card slides in from the open end', color='#e8841e', fontsize=9)
a.text(2, 16, 'solid end / hinge', color=INK, fontsize=9); a.text(105, 16, '10 mm corner support', color=INK, fontsize=9)
a.annotate('', xy=(130, -4), xytext=(0, -4), arrowprops=dict(arrowstyle='<->', color=INK)); a.text(55, -9, '130 mm ledge, 108.3 mm clear groove', color=INK, fontsize=9)
a.set_xlim(-5, 265); a.set_ylim(-14, 22); a.set_aspect('equal'); a.axis('off'); a.set_title('Top view of one ledge: side loading', color=INK)
plt.tight_layout(); plt.savefig(OUT + 'fig_geometry.png', dpi=130, facecolor='white'); plt.close()

# --- Fig 3: hinge detail (v2 hinged rack, one ledge swung out) ------------------------------------
fx = trimesh.load('_fixed.stl'); mv = sorted(trimesh.load('_moving.stl').split(), key=lambda m: m.bounds[0, 1]); ax3 = np.load('_axes.npy')
fig = plt.figure(figsize=(13, 5.6))
a = fig.add_subplot(1, 2, 1, projection='3d')
cut = lambda m: trimesh.boolean.intersection([m, box(bounds=[[-5, -10, -5], [70, 140, 80]])], engine='manifold')
add(a, up(cut(fx)), RACK)
for k, m in enumerate(mv[:3]):
    mm = m.copy()
    if k == 1: mm.apply_transform(rotation_matrix(np.radians(-55), [0, 1, 0], point=[ax3[k][0], 0, ax3[k][2]]))
    add(a, up(cut(mm)), (0.24, 0.48, 0.80))
frame(a, (-5, 70), (-5, 80), (-5, 140), 22, -60); a.set_title('Print-in-place hinge: ledge 2 swung out 55°', color=INK)
a = fig.add_subplot(1, 2, 2)
k = 2; y0 = ax3[k][1]
for mesh, c, ls in [(fx, '#555', '-'), (mv[k], '#2a6fd8', '-')]:
    for yy, l2 in [(y0 - 1.2, '-'), (y0 - 0.2, '--')]:
        s = mesh.section(plane_origin=[0, yy, 0], plane_normal=[0, 1, 0])
        if s is not None:
            for e in s.discrete: a.plot(e[:, 0], e[:, 2], l2, color=c, lw=1.1)
s = mv[k].section(plane_origin=[0, y0 + 11, 0], plane_normal=[0, 1, 0])
for e in s.discrete: a.plot(e[:, 0], e[:, 2], color='#2a6fd8', lw=1.6)
s = fx.section(plane_origin=[0, y0 + 11, 0], plane_normal=[0, 1, 0])
for e in s.discrete: a.plot(e[:, 0], e[:, 2], color='#555', lw=1.6)
a.text(20, 30, 'knuckles + 45° cone pins\n0.4 mm clearance', fontsize=9, color=INK)
a.text(30, 3, 'tooth in slot = backward stop\nbump in pocket = snap detent', fontsize=9, color=INK)
a.set_xlim(0, 45); a.set_ylim(0, 40); a.set_aspect('equal'); a.grid(alpha=0.3); a.set_title('Hinge, stop and detent (top sections)', color=INK)
plt.tight_layout(); plt.savefig(OUT + 'fig_hinge.png', dpi=130, facecolor='white'); plt.close()

# --- Fig 4: design evolution strip --------------------------------------------------------------
steps = [('44ab539c-rack_6slot.stl', '1  Original 6-slot rack'), ('rack_6ledge_130_3mmholes.stl', '2  Six ledges, 130 mm,\n6 mm plate, 3 mm holes'),
         (None, '3  Hinged ledges, stop\n+ snap detent'), ('_ub_rack_5.stl', '4  Tabletop rack +\nuniversal base')]
fig = plt.figure(figsize=(14, 4.6))
for i, (f, t) in enumerate(steps):
    a = fig.add_subplot(1, 4, i + 1, projection='3d')
    if f is None:
        add(a, up(fx), RACK)
        for k, m in enumerate(mv):
            mm = m.copy()
            if k in (1, 3): mm.apply_transform(rotation_matrix(np.radians(-50), [0, 1, 0], point=[ax3[k][0], 0, ax3[k][2]]))
            add(a, up(mm), (0.24, 0.48, 0.80))
        frame(a, (-10, 140), (-20, 130), (0, 460), 18, -60)
    elif f.startswith('_ub'):
        add(a, trimesh.load(f), RACK); add(a, trimesh.load('_ub_base.stl'), BASE); frame(a, (-10, 130), (-30, 130), (0, 260), 16, -125)
    else:
        add(a, up(trimesh.load(f)), RACK); frame(a, (-10, 140), (-40, 90), (0, 460), 14, -120)
    a.set_title(t, color=INK, fontsize=11)
plt.tight_layout(); plt.savefig(OUT + 'fig_evolution.png', dpi=120, facecolor='white'); plt.close()
print('ok')
