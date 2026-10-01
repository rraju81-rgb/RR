"""Previews of the accordion hook rack. python3 accordion_render.py [N] [--gif]"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw
import accordion_cad as C
import raster

N = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 4
os.makedirs("accordion", exist_ok=True)
A = C.Acc(N)
T = C.build_templates()
PLATE = C.wall_plate(A)
COLS = [(0.85, 0.2, 0.15), (0.15, 0.45, 0.85), (0.95, 0.6, 0.1), (0.2, 0.65, 0.35), (0.6, 0.25, 0.7), (0.9, 0.85, 0.2)]

def color(n):
    if n.startswith("card"): return COLS[int(n[4:]) % 6]
    if n.startswith("link"): return (0.82, 0.84, 0.88) if n[4] == "A" else (0.60, 0.64, 0.72)
    if n.startswith("hook"): return (0.95, 0.55, 0.12)
    if n.startswith("piv"): return (0.2, 0.2, 0.24)
    return (0.30, 0.31, 0.34)

tw = lambda p: np.column_stack([p[:, 0], -p[:, 2], p[:, 1]])

def items(th, cards):
    parts = C.assembly(A, th, dict(T, plate=PLATE), with_cards=cards)
    return [(m, color(n)) for n, (m, g) in parts.items()]

def view(th, cards, elev, azim, size, scale, center=None):
    im, c = raster.render(items(th, cards), tw, elev, azim, size, scale, center)
    return raster.crop(im), c

if __name__ == "__main__" and "--gif" not in sys.argv:
    s = 1.5 if N <= 3 else (1.25 if N == 4 else 1.05)
    view(C.TH_MIN, True, 8, -22, (1400, 900), s)[0].save(f"accordion/preview_N{N}_open.png")
    view(C.TH_MAX, False, 8, -22, (800, 900), 1.4)[0].save(f"accordion/preview_N{N}_folded.png")
    view(C.TH_MIN, True, 0, 0, (1400, 900), s)[0].save(f"accordion/preview_N{N}_front.png")
    print("saved")

if "--gif" in sys.argv:
    s = 1.0 if N >= 4 else 1.3
    cs = [raster.render(items(t, False), tw, 10, -20, (1200, 800), s)[1] for t in (C.TH_MIN, C.TH_MAX)]
    center = ((cs[0][0] + cs[1][0]) / 2, (cs[0][1] + cs[1][1]) / 2)
    degs = list(range(14, 71, 4)) + [70] * 3 + list(range(70, 13, -4)) + [14] * 3
    frames = []
    for d in degs:
        th = np.radians(d)
        im, _ = raster.render(items(th, d <= 22), tw, 10, -20, (1200, 800), s, center=center)
        ImageDraw.Draw(im).text((12, 10), f"{N} stalls, link angle {d} deg" + ("" if d <= 22 else "  (cards off while folded)"), fill=(20, 20, 20))
        frames.append(im.convert("P", palette=Image.ADAPTIVE))
    frames[0].save(f"accordion/accordion_N{N}.gif", save_all=True, append_images=frames[1:], duration=120, loop=0)
    print("gif", len(frames))
