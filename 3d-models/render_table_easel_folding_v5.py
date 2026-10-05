import os, json, numpy as np, trimesh
from PIL import Image, ImageDraw, ImageFont
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from rlib import render
src_imgs = open('pitch_imgs.py').read().split('# ---------------- wall mount')[0]; g = {}; exec(src_imgs, g)
card, CARS, PANEL, BASEC, LEGC = g['card'], g['CARS'], (0.36, 0.38, 0.45), (0.20, 0.56, 0.44), (0.78, 0.32, 0.25)
GR = (0, (1.5, 1.5, 1.52), (-800, 1000, -800, 1000)); BG = (0.955, 0.955, 0.965)
OUT = '/home/user/RR/3d-models/'; tiles = []
for N, YH, BE, ANG in [(3, 125, 117, '15,17.5,20,22.5'), (5, 160, 152, '17.5,20,22.5')]:
    os.environ.update(EASEL_N=str(N), EASEL_YH=str(YH), EASEL_BASE_END=str(BE), EASEL_ANGLES=ANG)
    ns = {}; exec(open('easel_v5.py').read().split("if __name__ == '__main__':")[0], ns)
    P, B, L = [trimesh.load(f'_easel5_{N}card_{n}.stl') for n in ('panel', 'base', 'leg')]
    mv = lambda m, M: (lambda c: (c.apply_transform(M), c)[1])(m.copy())
    angs = [float(a) for a in ANG.split(',')]
    H = 1050 if N == 5 else 900
    # folded, standing on its edge for the picture
    Tf = ns['tilt'](0.0)
    render([(mv(P, Tf), PANEL, 1), (mv(B, Tf), BASEC, 1), (mv(L, Tf), LEGC, 1)], eye=(-260, -330, 230 if N == 3 else 300), target=(55, 10, 90 if N == 3 else 125),
           fov=34, W=700, H=H, ground=GR, bg=BG, out=f'_ez5_{N}_folded.png')
    for a in (angs[0], angs[-1]):
        T = ns['tilt'](a); phi = ns['base_angle'](a); psi, _ = ns['leg_angle'](a)
        items = [(mv(P, T), PANEL, 1), (mv(B, T @ ns['rot'](ns['H1'], -phi)), BASEC, 1), (mv(L, T @ ns['rot'](ns['H2'], psi)), LEGC, 1)]
        for k in range(N):
            for m, c, al in card(1.5 + (95 if k == 1 else 0), 55*k, 3.7 + 4.6*k + 0.3, carc=CARS[k]):
                items.append((mv(m, T), c, al))
        render(items, eye=(350, 380, 260 if N == 3 else 330), target=(55, 40, 100 if N == 3 else 130), fov=34, W=700, H=H, ground=GR, bg=BG, out=f'_ez5_{N}_{a}_back.png')
        render(items, eye=(-330, -430, 260 if N == 3 else 330), target=(55, 20, 100 if N == 3 else 135), fov=34, W=700, H=H, ground=GR, bg=BG, out=f'_ez5_{N}_{a}.png')
    # side sections of every setting
    fig, ax = plt.subplots(figsize=(4.6, 4.6*(1.2 if N == 5 else 1.0)), dpi=150)
    for a, col in zip(angs, ['#1f77b4', '#2ca02c', '#ff7f0e', '#d62728']):
        T = ns['tilt'](a); psi, _ = ns['leg_angle'](a)
        for m, M in [(P, T), (L, T @ ns['rot'](ns['H2'], psi))]:
            s = mv(m, M).section(plane_origin=[12, 0, 0], plane_normal=[1, 0, 0])
            for e in s.discrete: ax.plot(e[:, 1], e[:, 2], color=col, lw=0.9)
        ax.plot([], [], color=col, label=f'{a:g}°')
    s = mv(B, ns['tilt'](angs[1]) @ ns['rot'](ns['H1'], -ns['base_angle'](angs[1]))).section(plane_origin=[12, 0, 0], plane_normal=[1, 0, 0])
    for e in s.discrete: ax.fill(e[:, 1], e[:, 2], color='#2a8a5a')
    ax.set_aspect('equal'); ax.grid(alpha=0.3); ax.legend(fontsize=8, title='card face tilt', title_fontsize=8)
    ax.set_title(f'{N}-card: leg positions on the {BE - 3.5:.0f} mm base', fontsize=9); ax.set_xlabel('depth (mm)', fontsize=8); ax.tick_params(labelsize=7)
    plt.tight_layout(); plt.savefig(f'_ez5_{N}_sections.png'); plt.close()
    tiles.append([f'_ez5_{N}_folded.png', f'_ez5_{N}_{angs[0]}.png', f'_ez5_{N}_{angs[-1]}.png', f'_ez5_{N}_{angs[-1]}_back.png', f'_ez5_{N}_sections.png'])
    tiles[-1] = (N, angs, tiles[-1])
f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
rows = []
for N, angs, fs in tiles:
    ims = [Image.open(x).convert('RGB') for x in fs]
    hh = 560; ims = [im.resize((int(im.width*hh/im.height), hh)) for im in ims]
    row = Image.new('RGB', (sum(i.width for i in ims) + 10*len(ims), hh + 44), 'white'); x = 0; d = ImageDraw.Draw(row)
    caps = ['folded flat (as printed)', f'open at {angs[0]:g}°', f'open at {angs[-1]:g}°', f'{angs[-1]:g}°, from behind', f'all {len(angs)} leg settings']
    for im, c in zip(ims, caps):
        row.paste(im, (x, 44)); d.text((x + 10, 10), f'{N}-card: {c}', fill=(29, 36, 51), font=f); x += im.width + 10
    rows.append(row)
Wd = max(r.width for r in rows); sheet = Image.new('RGB', (Wd, sum(r.height for r in rows) + 20), 'white'); y = 0
for r in rows: sheet.paste(r, (0, y)); y += r.height + 20
sheet.save(OUT + 'table_easel_folding_v5_preview.png'); print('ok', sheet.size)
