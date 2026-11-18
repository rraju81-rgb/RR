"""Dimensioned drawing of the finished spoiler (plan view, side view, centre-line section) for the spec sheet.
Run from spoiler/:  python3 spec/src/drawing.py  -> spec/img/drawing.png (transparent, light lines for the dark sheet)"""
import numpy as np, trimesh, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from shapely.geometry import Polygon
from shapely.ops import unary_union
for f in ('michroma.ttf', 'jetbrainsmono-medium.ttf'): font_manager.fontManager.addfont(f'v6/brochure/assets/fonts/{f}')
MONO = 'JetBrains Mono'
E = trimesh.load('v6/out/E2.stl')
def silhouette(keep):
    polys = [Polygon(t) for t in E.triangles[:, :, keep]]
    return unary_union([p for p in polys if p.area > 1e-6]).buffer(0.01)
plan = silhouette([0, 2]); side = silhouette([2, 1])
sec = E.section(plane_origin=[0, 0, 0], plane_normal=[1, 0, 0])
sec2, _ = sec.to_2D(to_2D=np.array([[0, 0, 1, 0], [0, 1, 0, 0], [1, 0, 0, 0], [0, 0, 0, 1.0]]))   # (z, y)
LINE, DIM, TXT, OR = '#e8eaee', '#9aa3b2', '#c9ced7', '#ff5c1e'
fig = plt.figure(figsize=(8.0, 4.6), dpi=300); fig.patch.set_alpha(0)
def ax_at(rect):
    a = fig.add_axes(rect); a.set_aspect('equal'); a.axis('off'); a.patch.set_alpha(0); return a
def draw_poly(a, g, lw=0.9, fill=None):
    gs = getattr(g, 'geoms', [g])
    for p in gs:
        x, y = p.exterior.xy; a.fill(x, y, color=fill, lw=0) if fill else None; a.plot(x, y, color=LINE, lw=lw)
        for r in p.interiors: xi, yi = r.xy; a.plot(xi, yi, color=LINE, lw=lw * 0.8)
def dim(a, p0, p1, off, text, horiz=True, fs=8.4):
    (x0, y0), (x1, y1) = p0, p1
    if horiz:
        y = off; a.plot([x0, x0], [y0, y], color=DIM, lw=0.4); a.plot([x1, x1], [y1, y], color=DIM, lw=0.4)
        a.annotate('', (x0, y), (x1, y), arrowprops=dict(arrowstyle='<|-|>', color=DIM, lw=0.5, shrinkA=0, shrinkB=0, mutation_scale=5))
        a.text((x0 + x1) / 2, y + (18 if off > y0 else -18), text, ha='center', va='bottom' if off > y0 else 'top', color=TXT, fontsize=fs, family=MONO)
    else:
        x = off; a.plot([x0, x], [y0, y0], color=DIM, lw=0.4); a.plot([x1, x], [y1, y1], color=DIM, lw=0.4)
        a.annotate('', (x, y0), (x, y1), arrowprops=dict(arrowstyle='<|-|>', color=DIM, lw=0.5, shrinkA=0, shrinkB=0, mutation_scale=5))
        a.text(x + (12 if off > x0 else -12), (y0 + y1) / 2, text, ha='left' if off > x0 else 'right', va='center', color=TXT, fontsize=fs, family=MONO, rotation=90)
# plan view (x across, z rearward -> drawn with the rear at the bottom)
a1 = ax_at([0.02, 0.36, 0.96, 0.62])
from shapely.affinity import scale
pl = scale(plan, 1, -1, origin=(0, 0))
draw_poly(a1, pl, fill='#1b1f28')
xmn, ymn, xmx, ymx = pl.bounds
dim(a1, (xmn, ymx), (xmx, ymx), ymx + 60, '1300 mm  overall width')
dim(a1, (xmx, ymx), (xmx, ymn), xmx + 55, '292 mm', horiz=False)
a1.text(xmn, ymn - 40, 'PLAN VIEW  ·  FRONT EDGE AT TOP', color=DIM, fontsize=7.4, family=MONO, va='top')
a1.set_xlim(xmn - 40, xmx + 160); a1.set_ylim(ymn - 110, ymx + 140)
# side view (z rearward -> to the right, y up)
a2 = ax_at([0.03, 0.02, 0.44, 0.34])
draw_poly(a2, side, fill='#1b1f28')
zmn, ymn2, zmx, ymx2 = side.bounds
dim(a2, (zmn, ymx2), (zmx, ymx2), ymx2 + 30, '292 mm')
dim(a2, (zmn, ymx2), (zmn, ymn2), zmn - 30, '147 mm', horiz=False)
a2.text(zmn, ymn2 - 22, 'SIDE VIEW  ·  END FIN', color=DIM, fontsize=7.4, family=MONO, va='top')
a2.set_xlim(zmn - 90, zmx + 40); a2.set_ylim(ymn2 - 60, ymx2 + 75)
# centre-line section
a3 = ax_at([0.52, 0.02, 0.46, 0.34])
for e in sec2.entities:
    pts = sec2.vertices[e.points]; a3.fill(pts[:, 0], pts[:, 1], color='#1b1f28', lw=0); a3.plot(pts[:, 0], pts[:, 1], color=LINE, lw=0.9)
V = np.asarray(sec2.vertices); z0, z1 = V[:, 0].min(), V[:, 0].max(); y0, y1 = V[:, 1].min(), V[:, 1].max()
dim(a3, (z0, y1), (z1, y1), y1 + 26, '267 mm chord')
k = np.argmax([np.ptp(np.asarray(V[np.abs(V[:, 0] - z) < 3, 1])) if (np.abs(V[:, 0] - z) < 3).sum() > 1 else 0 for z in np.linspace(z0, z1, 80)])
zk = np.linspace(z0, z1, 80)[k]; m = np.abs(V[:, 0] - zk) < 3; yt, yb = V[m, 1].max(), V[m, 1].min()
a3.annotate('', (zk, yb), (zk, yt), arrowprops=dict(arrowstyle='<|-|>', color=OR, lw=0.5, shrinkA=0, shrinkB=0, mutation_scale=4))
a3.text(zk + 6, yb - 6, '18.5 mm max', color=OR, fontsize=7.8, family=MONO, va='top')
lip = V[V[:, 0] > z1 - 70]; a3.text(z1 - 4, lip[:, 1].max() + 8, 'LIP KICK-UP 12°', color=OR, fontsize=7.8, family=MONO, ha='right', va='bottom')
a3.text(z0, y0 - 22, 'CENTRE-LINE SECTION', color=DIM, fontsize=7.4, family=MONO, va='top')
a3.set_xlim(z0 - 20, z1 + 20); a3.set_ylim(y0 - 60, y1 + 75)
fig.savefig('spec/img/drawing.png', transparent=True)
print('spec/img/drawing.png')
