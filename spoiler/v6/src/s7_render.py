"""Step 7: figures for the v6 package."""
import sys, json; sys.path.insert(0, 'v6/src')
import numpy as np, trimesh
from zr import render, grid, label, look_at, fit_view
from PIL import Image, ImageDraw, ImageFont
OUT = 'v6/out'; DOC = 'v6/docs'
meta = json.load(open(f'{OUT}/_parts_meta.json'))
P = {k: trimesh.load(f'v6/assembled/{k}.stl') for k in 'LCR'}
K = [trimesh.load(f'v6/assembled/KEY_{i}.stl') for i in range(1, 5)]
COL = {'L': (70, 74, 82), 'C': (232, 118, 34), 'R': (70, 74, 82)}
KC = (60, 170, 230)
BG = (246, 246, 244)
def lab(im, t, s=26, fill=(20, 20, 20)): return label(im, t, size=s, fill=fill)
# 2 exploded from below
ex = {'L': [-90, 0, 0], 'C': [0, 0, 0], 'R': [90, 0, 0]}
items = []
for k in 'LCR':
    m = P[k].copy(); m.apply_translation(ex[k]); items.append((m, COL[k]))
for i, km in enumerate(K):
    T = np.array(meta['frames'][i]['T']); A = T[:, 2]; side = np.sign(meta['frames'][i]['seam'])
    m = km.copy(); m.apply_translation(-A * 45 + np.array([side * 45, 0, 0])); items.append((m, KC))
eye, tgt, fov = fit_view([m for m, _ in items], (-0.45, -0.62, 0.64), W=1600, H=1000, dist=2600)
im = render(items, eye=eye, target=tgt, fov=fov, W=1600, H=1000, bg=BG, spec=0.3, ambient=0.3)
lab(im, 'Exploded, seen from underneath: 4 bow-tie keys (blue) drop into pockets that straddle each seam').save(f'{DOC}/v6_exploded_underside.png')
# 3 close-up of right seam underside, pieces slightly apart, keys lifted out
items = []
for k in 'CR':
    m = P[k].copy(); m.apply_translation([0 if k == 'C' else 25, 0, 0]); items.append((m, COL[k]))
for i in (2, 3):
    T = np.array(meta['frames'][i]['T']); A = T[:, 2]
    m = K[i].copy(); m.apply_translation(-A * 28 + np.array([12.5, 0, 0])); items.append((m, KC))
c = np.array([meta['XS'] + 12, 0, 145])
eye = c + np.array([-120, -260, 210])
im = render(items, eye=eye, target=c, fov=40, W=1400, H=1000, bg=BG, spec=0.3, ambient=0.3)
lab(im, 'Right seam from below: dovetail half-pockets in both pieces + keys (glue in, flush with the underside)').save(f'{DOC}/v6_seam_closeup.png')
# 4 bed layouts
imgs = []
names = {'L': 'v6_LEFT_end_piece', 'C': 'v6_CENTRE_piece', 'R': 'v6_RIGHT_end_piece'}
bed = trimesh.creation.box(extents=[420, 420, 2]); bed.apply_translation([210, 210, -1.2])
for k in 'LCR':
    p = trimesh.load(f'v6/print/{names[k]}.stl')
    eye = (210 + 650, 210 - 750, 520); tgt = (210, 210, 200)
    im = render([(bed, (205, 205, 210)), (p, COL[k])], eye=eye, target=tgt, up=(0, 0, 1), fov=42, W=700, H=900, bg=BG, spec=0.3, ambient=0.3)
    e = p.extents
    imgs.append(lab(im, f'{names[k]}\n{e[0]:.0f} x {e[1]:.0f} x {e[2]:.0f} mm on 420x420 bed', s=22))
kp = trimesh.load(f'v6/print/v6_BOWTIE_KEYS_plate_of_6.stl')
kp2 = kp.copy(); kp2.apply_translation([210 - kp.bounds.mean(0)[0], 210 - kp.bounds.mean(0)[1], 0])
im = render([(bed, (205, 205, 210)), (kp2, KC)], eye=(210 + 260, 210 - 300, 260), target=(210, 210, 0), up=(0, 0, 1), fov=42, W=700, H=900, bg=BG, spec=0.3, ambient=0.3)
imgs.append(lab(im, 'bow-tie keys: 4 needed (+2 spares)\nflat on the car-side face, no supports', s=22))
grid(imgs, 4, bg=BG).save(f'{DOC}/v6_bed_layouts.png')
print('renders done')
