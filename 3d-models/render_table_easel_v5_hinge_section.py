import os, numpy as np, trimesh, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
os.environ.update(EASEL_N='3', EASEL_YH='125', EASEL_BASE_END='117', EASEL_ANGLES='15,17.5,20,22.5')
ns = {}; exec(open('easel_v5.py').read().split("if __name__ == '__main__':")[0], ns)
P, L = trimesh.load('_easel5_3card_panel.stl'), trimesh.load('_easel5_3card_leg.stl')
P4, L4 = trimesh.load('_easel_3card_panel.stl'), trimesh.load('_easel_3card_leg.stl')
H = ns['H2']
fig, axs = plt.subplots(1, 2, figsize=(11, 4.6), dpi=150)
for ax, (p, l, t) in zip(axs, [(P4, L4, 'v4 (failed): flat 0.4 mm gaps, 4 mm pin'), (P, L, 'v5: 45° cone joints, 0.5 mm gaps, 5 mm pin')]):
    for m, c in [(p, '#3a3f4b'), (l, '#c0392b')]:
        s = m.section(plane_origin=[0, H['y'], 0], plane_normal=[0, 1, 0])     # cut through the hinge axis
        if s is None: continue
        for poly in s.polygons_full if hasattr(s, 'polygons_full') else []:
            pass
        sp, T = s.to_2D(to_3D=np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)) if False else (None, None)
        for e in s.discrete: ax.fill(e[:, 0], e[:, 2], color=c, alpha=0.85, lw=0)
    ax.set_xlim(-10, 34); ax.set_ylim(-17, -1); ax.set_aspect('equal'); ax.set_title(t, fontsize=10)
    ax.set_xlabel('x (mm): this axis points UP when printed', fontsize=8); ax.set_ylabel('z (mm)', fontsize=8); ax.tick_params(labelsize=7)
axs[1].text(-9, -2.2, 'grey = fixed (panel + pin), red = moving (leg)', fontsize=8)
plt.tight_layout(); plt.savefig('/home/user/RR/3d-models/table_easel_v5_hinge_section.png'); print('ok')
