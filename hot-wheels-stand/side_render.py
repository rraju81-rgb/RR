"""Previews from the real meshes. python3 side_render.py [N] [--gif]"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw
import side_cad as C
import raster

N = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 4
os.makedirs("side", exist_ok=True)
R, P = C.build(N)
COLS = [(0.85, 0.2, 0.15), (0.15, 0.45, 0.85), (0.95, 0.6, 0.1), (0.2, 0.65, 0.35), (0.6, 0.25, 0.7), (0.9, 0.85, 0.2)]

def color(n):
    if n.startswith("card"): return COLS[int(n[4:]) % 6]
    if n.startswith("arm"): return (0.25, 0.55, 0.75)
    if n.startswith("b1"): return (0.80, 0.82, 0.86)
    if n.startswith("b2"): return (0.55, 0.60, 0.68)
    if n == "tie": return (0.9, 0.7, 0.2)
    if n == "washer": return (0.1, 0.1, 0.1)
    if n.startswith("cheek"): return (0.35, 0.36, 0.40)
    return (0.22, 0.23, 0.26)

def items(phi, frame=True):
    pm = C.posed(R, P, phi)
    it = [(m, color(n)) for n, m in pm.items() if frame or n != "frame"]
    for sg in (1, -1):
        it.append((C.spring_mesh(R, phi, sg), (0.95, 0.5, 0.1)))
    return it

tw = lambda p: np.column_stack([p[:, 0], -p[:, 2], p[:, 1]])      # viewer on +z

def view(phi, elev, azim, size, scale, **kw):
    im, _ = raster.render(items(phi, **kw), tw, elev, azim, size, scale)
    return raster.crop(im)

if __name__ == "__main__" and "--gif" not in sys.argv:
    s = 1.35 if N <= 3 else (1.1 if N == 4 else 0.95)
    view(0, 6, -28, (700, 1100), s).save(f"side/preview_N{N}_closed.png")
    view(90, 24, -38, (1100, 900), s).save(f"side/preview_N{N}_open.png")
    ims = [view(p, 0, 90, (520, 800), s) for p in (0, 30, 60, 90)]
    h = max(i.height for i in ims)
    out = Image.new("RGB", (sum(i.width for i in ims) + 30, h + 40), "white")
    x, d = 0, ImageDraw.Draw(out)
    for i, p in zip(ims, (0, 30, 60, 90)):
        out.paste(i, (x, 40 + h - i.height)); d.text((x + 8, 12), f"panel {p} deg (side view, wall on the left)", fill=(20, 20, 20)); x += i.width + 10
    out.save(f"side/preview_N{N}_poses.png")
    print("saved")

def make_gif(step=6):
    s = 1.0 if N >= 4 else 1.25
    cs = [raster.render(items(p), tw, 20, -38, (1000, 900), s)[1] for p in (0, 90)]
    center = ((cs[0][0] + cs[1][0]) / 2, (cs[0][1] + cs[1][1]) / 2)
    seq = list(range(0, 91, step)) + [90] * 4 + list(range(90, -1, -step)) + [0] * 3
    frames = []
    for p in seq:
        im, _ = raster.render(items(p), tw, 20, -38, (1000, 900), s, center=center)
        ImageDraw.Draw(im).text((12, 10), f"{N} stalls, panel {p} deg", fill=(20, 20, 20))
        frames.append(im.convert("P", palette=Image.ADAPTIVE))
    frames[0].save(f"side/side_N{N}_open.gif", save_all=True, append_images=frames[1:], duration=110, loop=0)
    print("gif", len(frames))

if "--gif" in sys.argv:
    make_gif()
