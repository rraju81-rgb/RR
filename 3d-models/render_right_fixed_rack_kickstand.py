import numpy as np, trimesh
from PIL import Image, ImageDraw, ImageFont
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from rlib import render
src_imgs = open('pitch_imgs.py').read().split('# ---------------- wall mount')[0]; g = {}; exec(src_imgs, g)
card, CARS = g['card'], g['CARS'] + g['CARS']
import build_right_fixed_rack_kickstand as E
RACKC, LEGC = (0.36, 0.38, 0.45), (0.78, 0.32, 0.25)
GR = (0, (1.5, 1.5, 1.52), (-900, 1100, -900, 1100)); BG = (0.955, 0.955, 0.965)
OUT = '/home/user/RR/3d-models/'
mv = lambda m, M: (lambda c: (c.apply_transform(M), c)[1])(m.copy())
P, L = trimesh.load('_ks12_rack.stl'), trimesh.load('_ks12_leg.stl')
T = E.tilt(E.ALPHA, P); Tl = T @ E.rot(E.PSI)
items = [(mv(P, T), RACKC, 1), (mv(L, Tl), LEGC, 1)]
for k in range(6):
    for m, c, al in card(28.5 + (100 if k == 2 else 0), 55*k, 3.7 + 4.6*k + 0.3, carc=CARS[k]):
        items.append((mv(m, T), c, al))
render(items, eye=(-420, -560, 420), target=(68, 60, 190), fov=34, W=760, H=1000, ground=GR, bg=BG, out='_ks12_front.png')
render(items, eye=(470, 560, 360), target=(68, 60, 170), fov=34, W=760, H=1000, ground=GR, bg=BG, out='_ks12_back.png')
# as printed: lying on the end wall, leg folded
Pp = trimesh.load('right_fixed_rack_kickstand_PRINT.stl')
render([(Pp, RACKC, 1)], eye=(260, -300, 420), target=(16, 225, 68), fov=40, W=760, H=1000, ground=(0, (1.5, 1.5, 1.52), (-900, 1100, -900, 1100)), bg=BG, out='_ks12_print.png')
# hinge close-up from behind, open
hy = (T @ np.array([14, E.YH, E.H['z'], 1]))[:3]
render(items[:2], eye=(hy[0] - 60, hy[1] + 120, hy[2] + 50), target=tuple(hy), fov=32, W=800, H=640, ground=GR, bg=BG, out='_ks12_hinge.png')
# side section through the leg barrel: folded and open
fig, ax = plt.subplots(figsize=(4.6, 6.0), dpi=150)
for psi, col, lab in [(0, '#888888', 'folded 0°'), (E.PSI, '#c0392b', f'open {E.PSI:g}° (stop)')]:
    for m, M, cc in [(P, T, '#3b4a6b'), (L, T @ E.rot(psi), col)]:
        s = mv(m, M).section(plane_origin=[10, 0, 0], plane_normal=[1, 0, 0])
        if s is None: continue
        for e in s.discrete: ax.plot(e[:, 1], e[:, 2], color=cc, lw=0.8)
    ax.plot([], [], color=col, label=lab)
ax.axhline(0, color='k', lw=0.6); ax.set_aspect('equal'); ax.grid(alpha=0.3); ax.legend(fontsize=7, loc='upper left')
ax.set_title(f'section at the hinge, rack leaning {E.ALPHA:g}°', fontsize=8); ax.set_xlabel('depth (mm)', fontsize=7); ax.tick_params(labelsize=6)
plt.tight_layout(); plt.savefig('_ks12_section.png'); plt.close()
f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
fs = ['_ks12_print.png', '_ks12_front.png', '_ks12_back.png', '_ks12_section.png']
caps = ['one print (end wall cut to 297 mm)', f'open, {E.ALPHA:g}° lean, 6 cards', 'from behind', 'hinge section']
ims = [Image.open(x).convert('RGB') for x in fs]; hh = 760; ims = [im.resize((int(im.width*hh/im.height), hh)) for im in ims]
row = Image.new('RGB', (sum(i.width for i in ims) + 10*len(ims), hh + 44), 'white'); x = 0; d = ImageDraw.Draw(row)
for im, c in zip(ims, caps): row.paste(im, (x, 44)); d.text((x + 10, 10), c, fill=(29, 36, 51), font=f); x += im.width + 10
hz = Image.open('_ks12_hinge.png').convert('RGB'); hz = hz.resize((int(hz.width*560/hz.height), 560))
row2 = Image.new('RGB', (row.width, 560 + 44), 'white'); row2.paste(hz, (0, 44)); ImageDraw.Draw(row2).text((10, 10), 'hinge, open: stop tab on the end wall (35°)', fill=(29, 36, 51), font=f)
sheet = Image.new('RGB', (row.width, row.height + row2.height + 20), 'white'); sheet.paste(row, (0, 0)); sheet.paste(row2, (0, row.height + 20))
sheet.save(OUT + 'right_fixed_rack_kickstand_preview.png'); print('ok', sheet.size)
