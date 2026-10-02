"""python3 render_clip.py -> clip/preview_*.png"""
import numpy as np, trimesh, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from build_clip import *

def raster(meshes, colors, elev, azim, size=(520, 640), lim=None):
    """small z-buffer rasteriser (matplotlib's painter sort breaks on big meshes)"""
    W, H = size
    ca, sa, ce, se = np.cos(np.radians(azim)), np.sin(np.radians(azim)), np.cos(np.radians(elev)), np.sin(np.radians(elev))
    Rz = np.array([[ca, -sa, 0], [sa, ca, 0], [0, 0, 1]]); Rx = np.array([[1, 0, 0], [0, ce, -se], [0, se, ce]])
    # model x right, y up, z toward viewer (+z out of wall); rotate about up axis then tilt
    Ry = np.array([[ca, 0, sa], [0, 1, 0], [-sa, 0, ca]]); Rt = np.array([[1, 0, 0], [0, ce, -se], [0, se, ce]])
    M = Rt @ Ry
    allv = np.vstack([m.vertices for m in meshes]) @ M.T
    if lim is not None: allv = np.array(lim) @ M.T
    lo, hi = allv.min(0), allv.max(0); sc = min((W - 20) / (hi[0] - lo[0]), (H - 20) / (hi[1] - lo[1]))
    img = np.ones((H, W, 3)); zb = np.full((H, W), -1e9)
    L = np.array([0.3, 0.5, 0.8]); L /= np.linalg.norm(L)
    for m, c in zip(meshes, colors):
        v = m.vertices @ M.T; n = m.face_normals @ M.T
        px = (v[:, 0] - lo[0]) * sc + 10; py = H - ((v[:, 1] - lo[1]) * sc + 10)
        for f, nn in zip(m.faces, n):
            if nn[2] <= 0: continue
            sh = 0.45 + 0.55 * max(0, nn @ L)
            xs, ys, zs = px[f], py[f], v[f, 2]
            x0, x1 = int(max(0, np.floor(xs.min()))), int(min(W - 1, np.ceil(xs.max())))
            y0, y1 = int(max(0, np.floor(ys.min()))), int(min(H - 1, np.ceil(ys.max())))
            if x1 < x0 or y1 < y0: continue
            X, Y = np.meshgrid(np.arange(x0, x1 + 1) + .5, np.arange(y0, y1 + 1) + .5)
            d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
            if abs(d) < 1e-9: continue
            a = ((ys[1] - ys[2]) * (X - xs[2]) + (xs[2] - xs[1]) * (Y - ys[2])) / d
            b = ((ys[2] - ys[0]) * (X - xs[2]) + (xs[0] - xs[2]) * (Y - ys[2])) / d
            cc = 1 - a - b; inside = (a >= -1e-6) & (b >= -1e-6) & (cc >= -1e-6)
            z = a * zs[0] + b * zs[1] + cc * zs[2]
            sub = zb[y0:y1 + 1, x0:x1 + 1]; upd = inside & (z > sub)
            sub[upd] = z[upd]; img[y0:y1 + 1, x0:x1 + 1][upd] = np.array(c) * sh
    return img


def panel(ax, ms, cs, el, az, lim=None, title="", size=(520, 640)):
    ax.imshow(raster(ms, cs, el, az, size, lim)); ax.set_axis_off(); ax.set_title(title, fontsize=10)

def box8(lo, hi): return [[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
grey, orange, dk, blue = (0.75, 0.75, 0.78), (0.95, 0.6, 0.1), (0.3, 0.3, 0.35), (0.2, 0.7, 0.9)
strip, clip = build_strip(), build_clip()
def rack(i, ang=0, y=None):
    y = (30.0 + 60 * i - foot_h) if y is None else y
    return [place(clip, 0, y), place(ledge_at(i, ang), 0, y)], [dk, orange]

fig, axs = plt.subplots(1, 3, figsize=(16, 7), dpi=100)
ms, cs = [strip], [grey]
for i in range(4): a, c = rack(i); ms += a; cs += c
panel(axs[0], ms, cs, 12, 25, ([-60, 0, -5], [130, 240, 60]), "25 mm strip + 4 racks (closed, snap-locked)")
ms, cs = [strip], [grey]
for i, ang in enumerate((0, 35, 70, 0)): a, c = rack(i, ang); ms += a; cs += c
panel(axs[1], ms, cs, 50, 30, ([-60, 0, -5], [130, 240, 120]), "ledges: closed / 35 / 70 degrees / closed")
a, c = rack(0); panel(axs[2], [strip] + a, [grey] + c, 20, 35, ([-20, 15, -5], [40, 60, 40]), "clip on the dovetail rail, ledge on the pin", (520, 640))
fig.savefig("clip/preview_assembly.png", bbox_inches="tight"); plt.close(fig)

fig, axs = plt.subplots(1, 3, figsize=(16, 5), dpi=100)
for ax, (m, k, t) in zip(axs, [(strip, "strip", "wall strip (print front face down)"), (clip, "clip", "hinge clip (print standing)"), (build_ledge(0), "ledge", "ledge (print standing)")]):
    p = to_print(m, k); panel(ax, [p], [dk], 25, 35, title=t, size=(480, 380))
fig.savefig("clip/preview_parts.png", bbox_inches="tight"); plt.close(fig)
