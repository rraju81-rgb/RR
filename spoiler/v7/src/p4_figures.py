"""v7 step 4: figures for the v7 package. Run from spoiler/:  python3 v7/src/p4_figures.py"""
import sys, json, os; sys.path.insert(0, 'v7/src'); sys.path.insert(0, 'v6/src')
import numpy as np, trimesh, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from zr import render, grid, label, fit_view
from bowtie import bowtie_outline
from layout import OUT, ASM, PRN, DOC, IDS, STEM, N_KEYS, COL, KEY_COL, SEAMS

os.makedirs(DOC, exist_ok=True)
meta = json.load(open(f'{OUT}/_parts_meta.json')); rep = json.load(open(f'{OUT}/_print_report.json'))
P = {k: trimesh.load(f'{ASM}/{k}.stl') for k in IDS}
K = [trimesh.load(f'{ASM}/KEY_{i}.stl') for i in range(1, N_KEYS + 1)]
FR = meta['frames']
BG = (246, 246, 244)
def lab(im, t, s=26, fill=(20, 20, 20)): return label(im, t, size=s, fill=fill)

# 1 assembled, two views
ims = []
for t, dr in [('rear three-quarter', (-0.55, 0.42, 0.72)), ('front three-quarter', (0.62, 0.40, -0.67))]:
    eye, tgt, fov = fit_view(list(P.values()), dr, W=1300, H=800, dist=2600)
    im = render([(P[k], COL[k]) for k in IDS], eye=eye, target=tgt, fov=fov, W=1300, H=800, bg=BG, spec=0.35, ambient=0.28)
    ims.append(lab(im, f'v7 assembled, {t}: four equal pieces of 325 mm (colours mark the pieces)', s=24))
grid(ims, 1, bg=BG).save(f'{DOC}/v7_assembled.png')

# 2 exploded from below
ex = {'P1': -135.0, 'P2': -45.0, 'P3': 45.0, 'P4': 135.0}
seam_dx = {SEAMS[0]: -90.0, SEAMS[1]: 0.0, SEAMS[2]: 90.0}
items = []
for k in IDS:
    m = P[k].copy(); m.apply_translation([ex[k], 0, 0]); items.append((m, COL[k]))
for i, km in enumerate(K):
    A = np.array(FR[i]['T'])[:, 2]
    m = km.copy(); m.apply_translation(-A * 45 + np.array([seam_dx[FR[i]['seam']], 0, 0])); items.append((m, KEY_COL))
eye, tgt, fov = fit_view([m for m, _ in items], (-0.45, -0.62, 0.64), W=1600, H=1000, dist=2600)
im = render(items, eye=eye, target=tgt, fov=fov, W=1600, H=1000, bg=BG, spec=0.3, ambient=0.3)
lab(im, 'Exploded, seen from underneath: 6 bow-tie keys (blue), two across each of the three seams').save(f'{DOC}/v7_exploded_underside.png')

# 3 seam close-ups from below: pieces slightly apart, keys lifted out
ims = []
for title, a, b, ki, xs in [('Centre seam from below', 'P2', 'P3', (2, 3), 0.0), ('Right outer seam from below', 'P3', 'P4', (4, 5), 325.0)]:
    items = [(P[a], COL[a])]
    m = P[b].copy(); m.apply_translation([25, 0, 0]); items.append((m, COL[b]))
    for i in ki:
        A = np.array(FR[i]['T'])[:, 2]
        m = K[i].copy(); m.apply_translation(-A * 28 + np.array([12.5, 0, 0])); items.append((m, KEY_COL))
    c = np.array([xs + 12, 0, 145]); eye = c + np.array([-120, -260, 210])
    im = render(items, eye=eye, target=c, fov=40, W=1200, H=860, bg=BG, spec=0.3, ambient=0.3)
    ims.append(lab(im, f'{title}: dovetail half-pockets in both pieces + keys\n(glued in, flush with the underside)', s=22))
grid(ims, 2, bg=BG).save(f'{DOC}/v7_seam_closeup.png')

# 4 bed layouts
imgs = []
bed = trimesh.creation.box(extents=[420, 420, 2]); bed.apply_translation([210, 210, -1.2])
for k in IDS:
    p = trimesh.load(f'{PRN}/{STEM[k]}.stl')
    im = render([(bed, (205, 205, 210)), (p, COL[k])], eye=(210 + 650, 210 - 750, 520), target=(210, 210, 160), up=(0, 0, 1), fov=42, W=620, H=820, bg=BG, spec=0.3, ambient=0.3)
    e = p.extents
    imgs.append(lab(im, f'{STEM[k]}\n{e[0]:.0f} x {e[1]:.0f} x {e[2]:.0f} mm, on its {rep[k]["on_bed"].split(" (")[0]}', s=19))
kp = trimesh.load(f'{PRN}/{rep["KEY"]["plate"]}')
kp2 = kp.copy(); kp2.apply_translation([210 - kp.bounds.mean(0)[0], 210 - kp.bounds.mean(0)[1], 0])
im = render([(bed, (205, 205, 210)), (kp2, KEY_COL)], eye=(210 + 260, 210 - 300, 260), target=(210, 210, 0), up=(0, 0, 1), fov=42, W=620, H=820, bg=BG, spec=0.3, ambient=0.3)
imgs.append(lab(im, f'bow-tie keys: {N_KEYS} needed (+2 spares)\nflat on the car-side face, no supports', s=19))
grid(imgs, 5, bg=BG).save(f'{DOC}/v7_bed_layouts.png')

# 5 v6 piece vs v7 piece on the same bed (print height)
try:
    old = trimesh.load('v6/print/v6_CENTRE_piece.stl'); new = trimesh.load(f'{PRN}/{STEM["P2"]}.stl')
    o = old.copy(); o.apply_translation([-105, 0, 0]); n = new.copy(); n.apply_translation([105, 0, 0])
    im = render([(bed, (205, 205, 210)), (o, (150, 152, 158)), (n, COL['P2'])], eye=(210 + 520, 210 - 900, 430), target=(210, 210, 200), up=(0, 0, 1), fov=40, W=1100, H=900, bg=BG, spec=0.3, ambient=0.3)
    lab(im, f'Print height on the 420 x 420 mm bed\nv6 centre piece (grey): {old.extents[2]:.0f} mm    v7 middle piece (orange): {new.extents[2]:.0f} mm', s=24).save(f'{DOC}/v7_vs_v6_print_height.png')
except Exception as e:
    print('height comparison skipped:', e)

# 6 key drawing + joint sections
L_, W_, N_, DP_, CL_, CF_ = meta['L'], meta['W'], meta['N'], meta['DP'], meta['CL'], meta['CF']
Po = bowtie_outline(); Ko = Po.buffer(-CL_, join_style=1)
fig = plt.figure(figsize=(16, 10))
ax = fig.add_subplot(2, 2, 1)
for g, c, lw, lab_ in [(Po, '0.5', 1.0, 'pocket outline (in the parts)'), (Ko, 'tab:blue', 2.0, f'key outline ({CL_} mm smaller per side)')]:
    x, y = g.exterior.xy; ax.plot(x, y, color=c, lw=lw, label=lab_)
ax.axvline(0, color='r', ls='--', lw=1); ax.text(0.6, 13.5, 'seam', color='r')
ax.annotate('', xy=(-L_/2, -15.5), xytext=(L_/2, -15.5), arrowprops=dict(arrowstyle='<->')); ax.text(-4, -18.5, f'{L_:.0f} mm')
ax.annotate('', xy=(L_/2 + 3, -W_/2), xytext=(L_/2 + 3, W_/2), arrowprops=dict(arrowstyle='<->')); ax.text(L_/2 + 4, -1, f'{W_:.0f}')
ax.annotate('', xy=(2.5, -N_/2), xytext=(2.5, N_/2), arrowprops=dict(arrowstyle='<->')); ax.text(3.2, -1, f'neck {N_:.0f}')
ax.set_aspect('equal'); ax.set_xlim(-36, 40); ax.set_ylim(-21, 17); ax.grid(alpha=.3); ax.legend(loc='upper left', fontsize=8)
ax.set_title('Bow-tie key, top view (same key as v6; all 6 are identical)')
ax = fig.add_subplot(2, 2, 2)
top = L_/2 - CL_ * np.sqrt(2); h = DP_ - CF_
ax.plot([-top, top, top - h, -(top - h), -top], [0, 0, h, h, 0], 'tab:blue', lw=2)
ax.plot([-L_/2, L_/2, L_/2 - DP_, -(L_/2 - DP_), -L_/2], [0, 0, DP_, DP_, 0], color='0.5', lw=1)
ax.axvline(0, color='r', ls='--', lw=1)
ax.text(-27, -1.6, 'car-side face (flat, flush with the underside) - print this face on the bed', fontsize=8)
ax.text(-12, h + 0.4, f'key {h:.2f} mm thick, 45 deg end bevels; pocket {DP_:.1f} mm deep', fontsize=8)
ax.set_aspect('equal'); ax.set_xlim(-32, 32); ax.set_ylim(-3, 9); ax.grid(alpha=.3); ax.set_title('Key side view (grey = pocket)')
ki = 2                                                # front key of the centre seam, between P2 and P3
T = np.array(FR[ki]['T']); E1, E2v, A, O = T[:, 0], T[:, 1], T[:, 2], T[:, 3]
ax = fig.add_subplot(2, 2, 3)
for nm, m, c in [('P2', P['P2'], '0.35'), ('P3', P['P3'], 'tab:orange'), ('key', K[ki], 'tab:blue')]:
    s = m.section(plane_origin=O, plane_normal=E2v)
    if s is None: continue
    for e in s.discrete:
        q = e - O; ax.fill(q @ E1, q @ A, color=c, alpha=0.55 if nm != 'key' else 0.9, lw=0.5)
ax.axvline(0, color='r', ls='--', lw=1); ax.text(1, -4, 'seam', color='r')
ax.set_aspect('equal'); ax.set_xlim(-60, 60); ax.set_ylim(-6, 22); ax.grid(alpha=.3)
ax.set_title(f'Section along the span through the centre-seam front key (z = {FR[ki]["z"]:.0f}): key locks both pieces')
ax.set_xlabel('across seam (mm)'); ax.set_ylabel('into the part (mm)')
ax = fig.add_subplot(2, 2, 4)
O2 = O + E1 * (-14.0)
for nm, m, c in [('P2', P['P2'], '0.35'), ('key', K[ki], 'tab:blue'), ('key', K[ki + 1], 'tab:blue')]:     # both keys of this seam
    s = m.section(plane_origin=O2, plane_normal=E1)
    if s is None: continue
    for e in s.discrete:
        q = e - O2; ax.fill(q @ E2v, q @ A, color=c, alpha=0.55 if nm != 'key' else 0.9, lw=0.5)
ax.set_aspect('equal'); ax.set_xlim(-62, 30); ax.set_ylim(-6, 26); ax.grid(alpha=.3)
ax.set_title('Section across both keys of the centre seam, 14 mm from the seam: 6.4+ mm of skin above'); ax.set_xlabel('chordwise (mm), rear of the car to the left')
plt.tight_layout(); plt.savefig(f'{DOC}/v7_bowtie_key_drawing.png', dpi=90)
print('figures done')
