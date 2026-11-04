"""Step 8: key drawing, joint sections, hero + before/after figures."""
import sys, json; sys.path.insert(0, 'v6/src')
import numpy as np, trimesh, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from zr import render, grid, label, look_at, fit_view
OUT = 'v6/out'; DOC = 'v6/docs'
meta = json.load(open(f'{OUT}/_parts_meta.json'))
from bowtie import bowtie_outline
L_, W_, N_, DP_, CL_, CF_ = meta['L'], meta['W'], meta['N'], meta['DP'], meta['CL'], meta['CF']
P = bowtie_outline(); K = P.buffer(-CL_, join_style=1)
fig = plt.figure(figsize=(16, 10))
ax = fig.add_subplot(2, 2, 1)
for g, c, lw, lab_ in [(P, '0.5', 1.0, 'pocket outline (in the parts)'), (K, 'tab:blue', 2.0, 'key outline (0.15 mm smaller per side)')]:
    x, y = g.exterior.xy; ax.plot(x, y, color=c, lw=lw, label=lab_)
ax.axvline(0, color='r', ls='--', lw=1); ax.text(0.6, 13.5, 'seam', color='r')
ax.annotate('', xy=(-L_/2, -15.5), xytext=(L_/2, -15.5), arrowprops=dict(arrowstyle='<->')); ax.text(-4, -18.5, f'{L_:.0f} mm')
ax.annotate('', xy=(L_/2 + 3, -W_/2), xytext=(L_/2 + 3, W_/2), arrowprops=dict(arrowstyle='<->')); ax.text(L_/2 + 4, -1, f'{W_:.0f}')
ax.annotate('', xy=(2.5, -N_/2), xytext=(2.5, N_/2), arrowprops=dict(arrowstyle='<->')); ax.text(3.2, -1, f'neck {N_:.0f}')
ax.set_aspect('equal'); ax.set_xlim(-36, 40); ax.set_ylim(-21, 17); ax.grid(alpha=.3); ax.legend(loc='upper left', fontsize=8)
ax.set_title('Bow-tie key, top view (dovetail flanks 12 deg, corners R2 / neck R3)')
ax = fig.add_subplot(2, 2, 2)
top = L_/2 - CL_ * np.sqrt(2); h = DP_ - CF_
ax.plot([-top, top, top - h, -(top - h), -top], [0, 0, h, h, 0], 'tab:blue', lw=2)
ax.plot([-L_/2, L_/2, L_/2 - DP_, -(L_/2 - DP_), -L_/2], [0, 0, DP_, DP_, 0], color='0.5', lw=1)
ax.axvline(0, color='r', ls='--', lw=1)
ax.text(-27, -1.6, 'car-side face (flat, flush with the underside) - print this face on the bed', fontsize=8)
ax.text(-12, h + 0.4, f'key {h:.2f} mm thick, 45 deg end bevels; pocket {DP_:.1f} mm deep', fontsize=8)
ax.set_aspect('equal'); ax.set_xlim(-32, 32); ax.set_ylim(-3, 9); ax.grid(alpha=.3); ax.set_title('Key side view (grey = pocket)')
# joint sections through the assembled parts
parts = {k: trimesh.load(f'v6/assembled/{k}.stl') for k in 'LC'}
key = trimesh.load('v6/assembled/KEY_1.stl')
T = np.array(meta['frames'][0]['T']); E1, E2v, A, O = T[:, 0], T[:, 1], T[:, 2], T[:, 3]
ax = fig.add_subplot(2, 2, 3)
for nm, m, c in [('L', parts['L'], '0.35'), ('C', parts['C'], 'tab:orange'), ('key', key, 'tab:blue')]:
    s = m.section(plane_origin=O, plane_normal=E2v)
    if s is None: continue
    for e in s.discrete:
        q = e - O; ax.fill(q @ E1, q @ A, color=c, alpha=0.55 if nm != 'key' else 0.9, lw=0.5)
ax.axvline(0, color='r', ls='--', lw=1); ax.text(1, -4, 'seam', color='r')
ax.set_aspect('equal'); ax.set_xlim(-60, 60); ax.set_ylim(-6, 22); ax.grid(alpha=.3)
ax.set_title('Section along the span through the front key (z = 127): key locks both pieces'); ax.set_xlabel('across seam (mm)'); ax.set_ylabel('into the part (mm)')
ax = fig.add_subplot(2, 2, 4)
O2 = O + E1 * (-14.0)
for nm, m, c in [('L', parts['L'], '0.35'), ('key', key, 'tab:blue')]:
    s = m.section(plane_origin=O2, plane_normal=E1)
    for e in s.discrete:
        q = e - O2; ax.fill(q @ E2v, q @ A, color=c, alpha=0.55 if nm != 'key' else 0.9, lw=0.5)
ax.set_aspect('equal'); ax.set_xlim(-40, 40); ax.set_ylim(-6, 22); ax.grid(alpha=.3)
ax.set_title('Section across a key lobe (14 mm from the seam): 6.5+ mm of skin above'); ax.set_xlabel('chordwise (mm)')
plt.tight_layout(); plt.savefig(f'{DOC}/v6_bowtie_key_drawing.png', dpi=90)
# hero, full spoiler with fins, rear three-quarter
BG = (246, 246, 244)
P3 = {k: trimesh.load(f'v6/assembled/{k}.stl') for k in 'LCR'}
COL = {'L': (70, 74, 82), 'C': (232, 118, 34), 'R': (70, 74, 82)}
ims = []
for t, dr in [('rear three-quarter', (-0.55, 0.42, 0.72)), ('front three-quarter', (0.62, 0.40, -0.67))]:
    eye, tgt, fov = fit_view(list(P3.values()), dr, W=1300, H=800, dist=2600)
    im = render([(P3[k], COL[k]) for k in 'LCR'], eye=eye, target=tgt, fov=fov, W=1300, H=800, bg=BG, spec=0.35, ambient=0.28)
    ims.append(label(im, f'v6 assembled, {t} (orange = centre piece)', size=24, fill=(20, 20, 20)))
grid(ims, 1, bg=BG).save(f'{DOC}/v6_assembled.png')
# before / after of the rear top-surface step
E0 = trimesh.load(f'{OUT}/E0.stl'); E2 = trimesh.load(f'{OUT}/E2.stl')
def flat(m): return trimesh.Trimesh(m.vertices[m.faces].reshape(-1, 3), np.arange(len(m.faces) * 3).reshape(-1, 3), process=False)
eye = (-260, 260, 420); tgt = (-120, 25, 175); e, r, u, f = look_at(eye, tgt)
ims = []
for nm, m in [('v5 (before): step line across the rear part', E0), ('v6 (after): step removed', E2)]:
    im = render([(flat(m), (150, 230, 30))], eye=eye, target=tgt, fov=40, W=900, H=600, ssaa=2, light=-f + 0.3 * u, spec=0.5, fill_light=0.0, ambient=0.12, crease=None)
    ims.append(label(im, nm + ' - flat shading like a slicer', size=20))
for nm, m in [('v5 zebra: stripes break at the step', E0), ('v6 zebra: stripes run through', E2)]:
    im = render([(m, (235, 235, 235))], eye=eye, target=tgt, fov=40, W=900, H=600, ssaa=2, light=-f + 0.3 * u, spec=0.2, fill_light=0.2, ambient=0.25, zebra=40, zebra_axis=(0, 0, 1), crease=35)
    ims.append(label(im, nm, size=20, fill=(220, 0, 0)))
grid(ims, 2).save(f'{DOC}/v6_rear_step_before_after.png')
print('drawings done')
