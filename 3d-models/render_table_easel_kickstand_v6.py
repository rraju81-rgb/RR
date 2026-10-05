import os, sys, json, numpy as np, trimesh
from PIL import Image, ImageDraw, ImageFont
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from rlib import render
src_imgs = open('pitch_imgs.py').read().split('# ---------------- wall mount')[0]; g = {}; exec(src_imgs, g)
card, CARS, PANEL, LEGC = g['card'], g['CARS'], (0.36, 0.38, 0.45), (0.78, 0.32, 0.25)
GR = (0, (1.5, 1.5, 1.52), (-800, 1000, -800, 1000)); BG = (0.955, 0.955, 0.965)
OUT = '/home/user/RR/3d-models/'; rows_spec = []
mv = lambda m, M: (lambda c: (c.apply_transform(M), c)[1])(m.copy())
for N, YH, A in [(3, 90, 26.5), (5, 140, 25)]:
    os.environ.update(KS_N=str(N), KS_YH=str(YH), KS_ALPHA=str(A)); sys.modules.pop('build_table_easel_kickstand_v6', None); import build_table_easel_kickstand_v6 as E
    P, L = [trimesh.load(f'_ks_{N}card_{n}.stl') for n in ('panel', 'leg')]
    H = 1000 if N == 5 else 860; zt = 85 if N == 3 else 120
    Tf = E.tilt(0.0, P)
    render([(mv(P, Tf), PANEL, 1), (mv(L, Tf), LEGC, 1)], eye=(330, 380, 240 if N == 3 else 300), target=(55, 10, zt), fov=34, W=700, H=H, ground=GR, bg=BG, out=f'_ks6_{N}_folded.png')
    T = E.tilt(A, P); items = [(mv(P, T), PANEL, 1), (mv(L, T @ E.rot(E.PSI)), LEGC, 1)]
    for k in range(N):
        for m, c, al in card(1.5 + (95 if k == 1 else 0), 55*k, 3.7 + 4.6*k + 0.3, carc=CARS[k]):
            items.append((mv(m, T), c, al))
    render(items, eye=(-330, -430, 260 if N == 3 else 330), target=(55, 20, zt), fov=34, W=700, H=H, ground=GR, bg=BG, out=f'_ks6_{N}_open.png')
    render(items, eye=(330, 400, 230 if N == 3 else 300), target=(55, 30, zt - 15), fov=34, W=700, H=H, ground=GR, bg=BG, out=f'_ks6_{N}_back.png')
    # side section through the middle knuckle: folded (0 deg) and open (35 deg)
    fig, ax = plt.subplots(figsize=(4.4, 4.4*(1.25 if N == 5 else 1.0)), dpi=150)
    for psi, col, lab in [(0, '#888888', 'folded 0°'), (E.PSI, '#c0392b', f'open {E.PSI:g}° (stop)')]:
        for m, M, c in [(P, T, '#3b4a6b'), (L, T @ E.rot(psi), col)]:
            s = mv(m, M).section(plane_origin=[E.XC, 0, 0], plane_normal=[1, 0, 0])
            if s is None: continue
            for e in s.discrete: ax.plot(e[:, 1], e[:, 2], color=c, lw=0.9)
        ax.plot([], [], color=col, label=lab)
    ax.axhline(0, color='k', lw=0.6); ax.set_aspect('equal'); ax.grid(alpha=0.3); ax.legend(fontsize=7, loc='upper left')
    ax.set_title(f'{N}-card: section at the hinge, card face {A:g}° back', fontsize=8); ax.set_xlabel('depth (mm)', fontsize=7); ax.tick_params(labelsize=6)
    plt.tight_layout(); plt.savefig(f'_ks6_{N}_section.png'); plt.close()
    rows_spec.append((N, A, [f'_ks6_{N}_folded.png', f'_ks6_{N}_open.png', f'_ks6_{N}_back.png', f'_ks6_{N}_section.png']))
    if N == 3:   # hinge close-up, from behind, open
        hy = (T @ np.array([E.XC, E.YH, E.H['z'], 1]))[:3]
        render(items[:2], eye=(hy[0] + 70, hy[1] + 120, hy[2] + 40), target=tuple(hy), fov=30, W=800, H=640, ground=GR, bg=BG, out='_ks6_hinge_open.png')
        Tf2 = E.tilt(0.0, P); hy2 = (Tf2 @ np.array([E.XC, E.YH, E.H['z'], 1]))[:3]
        render([(mv(P, Tf2), PANEL, 1), (mv(L, Tf2), LEGC, 1)], eye=(hy2[0] + 70, hy2[1] + 120, hy2[2] + 40), target=tuple(hy2), fov=30, W=800, H=640, ground=GR, bg=BG, out='_ks6_hinge_folded.png')
f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
rows = []
for N, A, fs in rows_spec:
    ims = [Image.open(x).convert('RGB') for x in fs]; hh = 560; ims = [im.resize((int(im.width*hh/im.height), hh)) for im in ims]
    row = Image.new('RGB', (sum(i.width for i in ims) + 10*len(ims), hh + 44), 'white'); x = 0; d = ImageDraw.Draw(row)
    for im, c in zip(ims, ['folded flat (as printed)', f'open, {A:g}° display', 'from behind', 'hinge section']):
        row.paste(im, (x, 44)); d.text((x + 10, 10), f'{N}-card: {c}', fill=(29, 36, 51), font=f); x += im.width + 10
    rows.append(row)
hz = [Image.open(x).convert('RGB') for x in ('_ks6_hinge_folded.png', '_ks6_hinge_open.png')]; hh = 560
hz = [im.resize((int(im.width*hh/im.height), hh)) for im in hz]
row = Image.new('RGB', (sum(i.width for i in hz) + 20, hh + 44), 'white'); d = ImageDraw.Draw(row); x = 0
for im, c in zip(hz, ['hinge close-up: folded (0°)', 'hinge close-up: open, tab on the panel (35°)']):
    row.paste(im, (x, 44)); d.text((x + 10, 10), c, fill=(29, 36, 51), font=f); x += im.width + 10
rows.append(row)
Wd = max(r.width for r in rows); sheet = Image.new('RGB', (Wd, sum(r.height for r in rows) + 40), 'white'); y = 0
for r in rows: sheet.paste(r, (0, y)); y += r.height + 20
sheet.save(OUT + 'table_easel_kickstand_v6_preview.png'); print('ok', sheet.size)
