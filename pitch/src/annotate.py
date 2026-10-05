import numpy as np, trimesh, json
from PIL import Image, ImageDraw, ImageFont
from rlib import project
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
OUT = '/home/user/RR/pitch/'
F = lambda s: ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', s)
FB = lambda s: ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', s)
INK, ACC = (29, 36, 51), (232, 132, 30)

def callouts(img_name, cam, notes, out):
    im = Image.open(OUT + img_name).convert('RGB'); W, H = im.size; d = ImageDraw.Draw(im)
    for p3, (lx, ly), text in notes:
        px, py = project(np.array(p3, float), cam[0], cam[1], W, H, cam[2])[0]
        f = F(int(H*0.026)); tw, th = d.textbbox((0, 0), text, font=f)[2:]
        bx0, by0 = min(lx*W, W - tw - 26), ly*H
        d.line([(px, py), (bx0 + (0 if bx0 > px else tw + 16), by0 + th/2 + 6)], fill=INK, width=3)
        r = 7; d.ellipse([px - r, py - r, px + r, py + r], fill=ACC, outline=INK, width=2)
        d.rounded_rectangle([bx0 - 2, by0, bx0 + tw + 16, by0 + th + 12], radius=8, fill=(255, 255, 255), outline=INK, width=2)
        d.text((bx0 + 7, by0 + 5), text, fill=INK, font=f)
    im.save(OUT + out)

wl = lambda x, y, z: (x, -z, y)          # rack frame -> wall scene
# wall rack, bare
callouts('w_bare.png', ((-200, -900, 330), (65, 0, 225), 30), [
    (wl(7, 303, 6), (0.03, 0.12), '3 mm screw holes (x3)'),
    (wl(7, 400, 3), (0.42, 0.08), '6 mm thick wall strip'),
    (wl(130, 277, 8), (0.42, 0.30), '130 mm ledges, 55 mm apart'),
    (wl(130, 2, 8), (0.55, 0.90), '6 identical ledges'),
    (wl(7, 28, 6), (0.03, 0.80), 'screw hole')], 'w_bare_ann.png')
callouts('w_detail.png', ((260, -150, 140), (118, -6, 10), 34), [
    (wl(126, 9, 7), (0.55, 0.06), '10 mm corner support'),
    (wl(130, 18, 2.5), (0.58, 0.40), 'open end: card slides in'),
    (wl(80, 20, 1.5), (0.04, 0.88), '22 mm back wall + 1.8 mm groove')], 'w_detail_ann.png')
# tabletop
B = trimesh.load('_ub_base.stl'); v = B.vertices
rest_top = v[v[:, 2] > B.bounds[1, 2] - 1].mean(axis=0)
X0b, X1b = B.bounds[0, 0], B.bounds[1, 0]
rest_left = v[(v[:, 0] < X0b + 10.5) & (v[:, 2] > 25)].mean(axis=0)
rest_right = v[(v[:, 0] > X1b - 10.5) & (v[:, 2] > 25)].mean(axis=0)
callouts('t_explode.png', ((-300, -420, 260), (60, 30, 110), 34), [
    (rest_left, (0.02, 0.74), 'back rest (x2), 15° lean'),
    ((55, B.bounds[0, 1] + 6, 9), (0.05, 0.92), 'slot + low front lip'),
    ((55, 20, 200), (0.04, 0.05), 'card rack lifts straight out')], 't_explode_ann.png')
R5 = trimesh.load('_ub_rack_5.stl')
callouts('t_back.png', ((320, 420, 260), (60, 40, 110), 34), [
    ((55, R5.bounds[1, 1] - 30, 160), (0.55, 0.06), 'rib grid stiffens the back'),
    (rest_right, (0.45, 0.45), 'edge rib rests on back rest'),
    ((105, B.bounds[1, 1] - 15, 4), (0.55, 0.90), 'feet + solid gussets')], 't_back_ann.png')
print('annotated')

# ---------------- price charts ----------------
pr = json.load(open('pricing.json'))
def chart(rows, title, out, note):
    rows = sorted(rows, key=lambda r: r[1])
    fig, ax = plt.subplots(figsize=(7.4, 0.42*len(rows) + 1.2), dpi=200)
    for i, (name, p, ours) in enumerate(rows):
        ax.barh(i, p, height=0.62, color='#e8841e' if ours else '#b7bcc6', edgecolor='white', linewidth=2)
        ax.text(p + max(r[1] for r in rows)*0.012, i, f'₹{p:,}', va='center', fontsize=8.5, color='#1d2433', fontweight='bold' if ours else 'normal')
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows], fontsize=8.5, color='#1d2433')
    for t, r in zip(ax.get_yticklabels(), rows):
        if r[2]: t.set_fontweight('bold')
    ax.set_xlim(0, max(r[1] for r in rows)*1.16); ax.xaxis.grid(True, color='#e3e6eb', lw=0.8); ax.set_axisbelow(True)
    for s in ('top', 'right', 'left'): ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color('#c9ced8'); ax.tick_params(axis='x', labelsize=7.5, colors='#5a6070'); ax.tick_params(axis='y', length=0)
    ax.set_title(title, fontsize=10, color='#1d2433', loc='left', fontweight='bold'); import textwrap; ax.set_xlabel('\n'.join(textwrap.wrap(note, 105)), fontsize=7.2, color='#5a6070')
    plt.tight_layout(); plt.savefig(OUT + out, facecolor='white'); plt.close()
W = {r['name']: r['price'] for r in pr['lines']['wall']}; T = {r['name']: r['price'] for r in pr['lines']['table']}
chart([('Carded wall stand mount, 2 bases (Amazon.in)', 299, False), ('Garage64 carded wall display (Amazon.in)', 349, False),
       ('Modular wall hanger, base + 2 ext. (Amazon.in)', 499, False), ('18-car display rack (Amazon.in)', 519, False),
       ('SlideRack Wall 6', W['SlideRack Wall 6'], True), ('SlideRack Wall 6 + Table Feet', W['Wall 6 + Table Feet bundle'], True),
       ('SlideRack Wall Pro (hinged)', W['SlideRack Wall Pro (hinged)'], True)],
      'Wall displays in India: listed price vs SlideRack', 'chart_wall.png', 'Price in ₹ (GST incl.). Competitor prices as listed (discounted) on Amazon.in, Oct 2026. A 40-car acrylic wall case lists at ₹3,998.')
chart([('6-car tabletop rack (Amazon.in)', 349, False), ('Hexagon tabletop rack (Amazon.in)', 359, False), ('12-slot premium rack (Amazon.in)', 564, False),
       ('3D-printed 5-rack card stand (Flipkart)', 1500, False), ('SlideRack Tabletop Set 3', T['Tabletop Set 3 (base + 3-card rack)'], True),
       ('SlideRack Tabletop Set 5', T['Tabletop Set 5 (base + 5-card rack)'], True), ('SlideRack Collector Combo (3 + 5)', T['Collector Combo (base + 3 + 5 racks)'], True)],
      'Tabletop displays in India: listed price vs SlideRack', 'chart_table.png', 'Price in ₹ (GST incl.). Competitor prices as listed on Amazon.in / Flipkart, Oct 2026; most low-cost racks hold loose cars, not carded cars.')
print('charts')
