import os, sys, json, numpy as np, trimesh
from PIL import Image, ImageDraw, ImageFont
from rlib import render
src_imgs = open('pitch_imgs.py').read().split('# ---------------- wall mount')[0]; g = {}; exec(src_imgs, g)
card, CARS = g['card'], g['CARS'] + g['CARS']
RACKC, LEGC = (0.36, 0.38, 0.45), (0.78, 0.32, 0.25)
GR = (0, (1.5, 1.5, 1.52), (-900, 1100, -900, 1100)); BG = (0.955, 0.955, 0.965)
OUT = '/home/user/RR/3d-models/'
mv = lambda m, M: (lambda c: (c.apply_transform(M), c)[1])(m.copy())
CFG = {3: (121, 27.5), 5: (176, 25.0), 6: (176, 24.5)}
f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
tiles = []
for N, (YH, A) in CFG.items():
    os.environ.update(KS_N=str(N), KS_YH=str(YH), KS_ALPHA=str(A)); sys.modules.pop('build_right_fixed_rack_kickstand', None); import build_right_fixed_rack_kickstand as E
    P, L = trimesh.load(f'_ks12_{N}_rack.stl'), trimesh.load(f'_ks12_{N}_leg.stl')
    T = E.tilt(A, P); items = [(mv(P, T), RACKC, 1), (mv(L, T @ E.rot(E.PSI)), LEGC, 1)]
    for k in range(N):
        for m, c, al in card(28.5, 55*k, 3.7 + 4.6*k + 0.3, carc=CARS[k]): items.append((mv(m, T), c, al))
    ht = 40 + 55*N; zt = ht*0.42
    render(items, eye=(-380 - 20*N, -420 - 40*N, 260 + 30*N), target=(68, 40, zt), fov=34, W=640, H=820, ground=GR, bg=BG, out=f'_fam_{N}_front.png')
    render(items[:2], eye=(380 + 20*N, 420 + 40*N, 200 + 30*N), target=(68, 40, zt*0.8), fov=34, W=640, H=820, ground=GR, bg=BG, out=f'_fam_{N}_back.png')
    tiles.append((N, [f'_fam_{N}_front.png', f'_fam_{N}_back.png']))
    json.dump(dict(N=N), open(f'_fam_{N}.json', 'w'))
hh = 620; cols = []
for N, fs in tiles:
    ims = [Image.open(x).convert('RGB') for x in fs]; ims = [im.resize((int(im.width*hh/im.height), hh)) for im in ims]
    col = Image.new('RGB', (sum(i.width for i in ims) + 10, hh + 44), 'white'); x = 0; d = ImageDraw.Draw(col)
    for im, cap in zip(ims, [f'{N}-card, loaded', 'stand, from behind']):
        col.paste(im, (x, 44)); d.text((x + 10, 10), cap, fill=(29, 36, 51), font=f); x += im.width + 10
    cols.append(col)
W = max(c.width for c in cols); sheet = Image.new('RGB', (W, sum(c.height for c in cols) + 40), 'white'); y = 0
for c in cols: sheet.paste(c, (0, y)); y += c.height + 20
sheet.save(OUT + 'fixed_rack_kickstand_family_preview.png'); print('ok', sheet.size)
