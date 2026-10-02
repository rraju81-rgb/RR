"""Previews for v2: python3 render_v2.py  -> v2/preview_*.png"""
import numpy as np, trimesh, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from build_v2 import *

def draw(ax, meshes, colors, elev, azim):
    light = np.array([0.4, -0.8, 0.6]); light /= np.linalg.norm(light)
    for m, c in zip(meshes, colors):
        v = m.vertices[m.faces]
        P = v[:, :, [0, 2, 1]].copy(); P[:, :, 1] *= -1     # X=x, Y=-z, Z=y(up)
        n = m.face_normals[:, [0, 2, 1]].copy(); n[:, 1] *= -1
        s = 0.55 + 0.45 * np.clip(n @ light, 0, 1)
        ax.add_collection3d(Poly3DCollection(P, facecolors=[tuple(np.array(c) * k) + (1,) for k in s],
                                             edgecolors="none"))
    allv = np.vstack([m.vertices for m in meshes]); lo, hi = allv.min(0), allv.max(0)
    ax.set_xlim(lo[0], hi[0]); ax.set_ylim(-hi[2], -lo[2]); ax.set_zlim(lo[1], hi[1])
    ax.set_box_aspect((hi[0]-lo[0], hi[2]-lo[2], hi[1]-lo[1])); ax.view_init(elev, azim); ax.set_axis_off()

def zoom(ax, y0, y1):   # crop to a vertical band
    ax.set_zlim(y0, y1); b = ax.get_box_aspect(); ax.set_box_aspect((b[0], b[1], (y1-y0)))

N = 3
fixed, ledges = build_hinged(N, parts_out=True)
def posed(ang):
    out = []
    for l, hz, y0 in ledges:
        m = l.copy(); m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-ang), [0, 1, 0], [hx, 0, hz])); out.append(m)
    return out
dark, light_ = (0.25, 0.25, 0.3), (0.95, 0.6, 0.1)
fig = plt.figure(figsize=(15, 6), dpi=100)
for i, (ang, title) in enumerate([(0, "closed"), (45, "ledges open 45°"), (90, "ledges open 90°")]):
    ax = fig.add_subplot(1, 3, i + 1, projection="3d")
    draw(ax, [fixed] + posed(ang), [dark] + [light_] * N, 28, -62)
    ax.set_title(f"hinged {N}-slot rack, {title}", fontsize=10)
fig.savefig("v2/preview_hinged_3slot.png", bbox_inches="tight"); plt.close(fig)

# 2D views: rear view of the frame (holes), and top view of ledge 0 swinging
from matplotlib.patches import Polygon
fig, (a, b, c) = plt.subplots(1, 3, figsize=(15, 7), dpi=100)
t = build_thick(N)
# rear view: slice at z=-back_t/2 of the thick plate -> outline polygons
sec = t.section(plane_origin=[0, 0, -back_t / 2], plane_normal=[0, 0, 1])
for e in sec.entities: a.plot(sec.vertices[e.points][:, 0], sec.vertices[e.points][:, 1], "k", lw=0.8)
a.set_aspect("equal"); a.set_title(f"{N}-slot thick frame, plate section: holes {hole_ys(N,0)[0][0]:.1f} mm from bottom / top", fontsize=9)
# top view of ledge 0 at several angles (project onto x,z)
l, hz, y0 = ledges[0]
for ang, col in ((0, "C0"), (30, "C1"), (60, "C2"), (90, "C3")):
    m = l.copy(); m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-ang), [0, 1, 0], [hx, 0, hz]))
    s2 = m.section(plane_origin=[0, y0 + ledge_h * 0.8, 0], plane_normal=[0, 1, 0])
    if s2 is None: continue
    for e in s2.entities: b.plot(s2.vertices[e.points][:, 0], s2.vertices[e.points][:, 2], col, lw=1)
fs = fixed.section(plane_origin=[0, y0 + ledge_h * 0.8, 0], plane_normal=[0, 1, 0])
b.plot([-5, 30], [0, 0], "k", lw=3); b.plot([hx], [hz], "k+", ms=12)
b.set_aspect("equal"); b.set_xlim(-5, 125); b.set_ylim(-5, 125); b.set_xlabel("x (mm)"); b.set_ylabel("z (mm, out of wall)")
b.set_title("top view, ledge swinging 0/30/60/90° about the pin (+)", fontsize=9)
# hinge cross-section along the pin axis (x-y plane at z=hz)
for mm, col in ((fixed, "k"), (l, "C1")):
    sc = mm.section(plane_origin=[0, 0, hz], plane_normal=[0, 0, 1])
    for e in sc.entities: c.plot(sc.vertices[e.points][:, 0], sc.vertices[e.points][:, 1], col, lw=1)
c.set_aspect("equal"); c.set_xlim(-5, 50); c.set_ylim(-2, 40); c.set_title("hinge section on the pin axis: black = fixed lugs/pin, orange = ledge", fontsize=9)
fig.savefig("v2/preview_detail.png", bbox_inches="tight"); plt.close(fig)

# latch preview: closed/latched vs bars up
fx, lg, bars = build_hinged(3, parts_out='latch', latch=True)
fig = plt.figure(figsize=(12, 6), dpi=100)
for i, (ang, title) in enumerate([(0, "latched (bar down)"), (180, "unlatched (bar up)")]):
    bm = []
    for b, (px, yp) in bars:
        m = b.copy(); m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(ang), [0, 0, 1], [px, yp, 0])); bm.append(m)
    ax = fig.add_subplot(1, 2, i + 1, projection="3d")
    draw(ax, [fx] + [l[0] for l in lg] + bm, [dark] + [light_] * 3 + [(0.2, 0.7, 0.9)] * 3, 20, -50)
    ax.set_xlim(-5, 60); ax.set_title(title, fontsize=10)
    ax.set_zlim(0, 150); ax.set_box_aspect((65, 40, 150))
fig.savefig("v2/preview_latch.png", bbox_inches="tight"); plt.close(fig)
