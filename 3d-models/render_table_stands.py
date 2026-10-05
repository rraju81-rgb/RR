import trimesh, numpy as np, json, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import importlib.util
spec = importlib.util.spec_from_file_location('ts', 'table_stands.py')
src = open('table_stands.py').read().split('CONFIG = {')[0]      # reuse helpers without rebuilding
ns = {}; exec(src, ns)
CFG = {'A': (4, 3*55.0+22.0), 'B': (3, 232.0)}
rep = json.load(open('table_stands_report.json'))
fig = plt.figure(figsize=(22, 16))
for row, v in enumerate('AB'):
    body = trimesh.load(f'table_stand_{v}.stl'); lift, yc = np.load(f'_tbl_{v}.npy')
    ns['N'], ns['LP'] = CFG[v]
    sides = [+1] if v == 'A' else [+1, -1]
    cards = [c for sd in sides for c in ns['card_slabs'](lift, yc, sd)]
    for cdx in cards: cdx.apply_translation([-ns['X0'], 0, 0]) if False else None
    # 3D views
    for col, (elev, azim) in enumerate([(18, -125), (18, -55)]):
        a = fig.add_subplot(2, 3, row*3 + col + 1, projection='3d')
        pc = Poly3DCollection(body.triangles, edgecolor='none'); n = body.face_normals
        sh = 0.4 + 0.6*np.clip(n @ np.array([0.4, -0.6, 0.7]), 0, 1)
        pc.set_facecolor(np.c_[sh*0.25, sh*0.27, sh*0.3, np.ones_like(sh)]); a.add_collection3d(pc)
        for i, cdx in enumerate(cards):
            sliding = (i == 1)                      # second card shown half-way through sliding in from the open end
            cm = trimesh.Trimesh(cdx.vertices + ([75, 0, 0] if sliding else [0, 0, 0]), cdx.faces)
            cc = Poly3DCollection(cm.triangles, edgecolor='none')
            cc.set_facecolor((0.95, 0.55, 0.1, 0.55) if sliding else (0.15, 0.45, 0.9, 0.35)); a.add_collection3d(cc)
        a.set_xlim(-10, 200); a.set_ylim(-60, 180); a.set_zlim(0, 340); a.set_box_aspect((210, 240, 340))
        a.view_init(elev, azim); a.set_axis_off()
        a.set_title(f"Variant {v}: {'Easel (4 cards)' if v=='A' else 'A-frame, double-sided (6 cards)'}" + (' - front' if col == 0 else ' - rear') + '\nsolid stop wall left, open right: orange card sliding in')
    # side profile with CoM
    a = fig.add_subplot(2, 3, row*3 + 3)
    s = body.section(plane_origin=[60, 0, 0], plane_normal=[1, 0, 0])
    for e in s.discrete: a.plot(e[:, 1], e[:, 2], color='#222', lw=1.2)
    s2 = body.section(plane_origin=[2, 0, 0], plane_normal=[1, 0, 0])
    for e in s2.discrete: a.plot(e[:, 1], e[:, 2], color='#999', lw=0.8)
    for cdx in cards:
        ss = cdx.section(plane_origin=[60, 0, 0], plane_normal=[1, 0, 0])
        for e in ss.discrete: a.plot(e[:, 1], e[:, 2], color='#2a6fd8', lw=1.5)
    st = rep[v]['stability']
    for name, mk in [('empty', 'o'), ('full', 's'), ('one side full', '^')]:
        if name in st:
            a.plot(st[name]['com_Y'], st[name]['com_Z'], mk, color='r', ms=9, label=f"CoM {name}: tip {st[name]['tip_angle_front_deg']} / {st[name]['tip_angle_rear_deg']} deg")
    a.plot([body.bounds[0, 1], body.bounds[1, 1]], [-3, -3], 'g-', lw=4, label='footprint on table')
    a.set_aspect('equal'); a.grid(True, alpha=0.3); a.legend(loc='upper right', fontsize=8)
    a.set_xlabel('depth Y (mm), viewer on the left'); a.set_ylabel('height Z (mm)'); a.set_title(f'Variant {v} side section (cards blue)')
    a.set_xlim(-70, 190); a.set_ylim(-10, 345)
plt.tight_layout(); plt.savefig('/home/user/RR/3d-models/table_stands_preview.png', dpi=60)
