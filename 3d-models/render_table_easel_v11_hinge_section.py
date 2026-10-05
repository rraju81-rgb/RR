import os, sys, trimesh, numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
os.environ.update(KS_N='3'); import build_table_easel_kickstand_v11 as E
P, L = [trimesh.load(f'_ks11_3card_{n}.stl') for n in ('panel', 'leg')]
fig, ax = plt.subplots(figsize=(7, 4.6), dpi=150)
for m, col, lab in [(P, '#3b4a6b', 'panel + pin'), (L, '#c0392b', 'leg')]:
    s = m.section(plane_origin=[0, 0, E.H['z']], plane_normal=[0, 0, 1])
    for poly in s.to_planar(to_2D=np.array([[0, 1, 0, 0], [1, 0, 0, 0], [0, 0, 1, -E.H['z']], [0, 0, 0, 1]], float))[0].polygons_full:
        x, y = poly.exterior.xy; ax.fill(x, y, color=col, alpha=0.85, lw=0)
        for h in poly.interiors: x, y = h.xy; ax.fill(x, y, color='white', lw=0)
    ax.plot([], [], color=col, lw=6, label=lab)
ax.set_xlim(E.YH - 20, E.YH + 14); ax.set_ylim(E.X0 - 2, E.XP[1] + 6); ax.set_aspect('equal')
ax.axhline(E.X0, color='k', lw=1); ax.text(E.YH - 19.5, E.X0 - 1.6, 'print bed (stop-wall end)', fontsize=7)
ax.set_xlabel('y, up the panel (mm)', fontsize=8); ax.set_ylabel('x, print height (mm)', fontsize=8); ax.tick_params(labelsize=7)
ax.set_title('Hinge cut along its axis, as printed: pin + cone foot (panel), 24 mm leg barrel, 8 mm panel barrel\n'
             '0.7 mm round the pin, 0.8 mm on every 45° cone; nothing prints flat over a gap', fontsize=8)
ax.legend(fontsize=7, loc='upper left'); plt.tight_layout(); plt.savefig('/home/user/RR/3d-models/table_build_table_easel_kickstand_v11_hinge_section.png')
print('ok')
