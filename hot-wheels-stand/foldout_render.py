"""Previews rendered from the real CAD meshes. python3 foldout_render.py [N]
-> foldout/preview_N<n>_closed.png, _open.png, _poses.png, foldout_N<n>_open.gif"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw
import foldout_cad as C
import raster

N = int(sys.argv[1]) if len(sys.argv) > 1 else 4
os.makedirs("foldout", exist_ok=True)
R, P = C.build(N)
CARD_COLS = [(0.85, 0.2, 0.15), (0.15, 0.45, 0.85), (0.95, 0.6, 0.1), (0.2, 0.65, 0.35), (0.6, 0.25, 0.7), (0.9, 0.85, 0.2)]

def color(n):
    if n.startswith("card"):
        return CARD_COLS[int(n[4:]) % 6]
    if n.startswith("arm"):
        return (0.25, 0.55, 0.75)
    if n == "panel":
        return (0.78, 0.8, 0.84)
    if n == "b2":
        return (0.55, 0.58, 0.64)
    if n.startswith(("pin", "spacer", "springpost")):
        return (0.12, 0.12, 0.14)
    return (0.30, 0.31, 0.34)

def items(phi, skip_wall=False, with_springs=True):
    pm = C.posed(R, P, phi)
    it = [(m, color(n)) for n, m in pm.items() if not (skip_wall and P[n]["group"] == "fixed" and n.startswith(("post", "top_", "bottom_")))]
    if with_springs:
        for sg in (1, -1):
            it.append((C.spring_mesh(R, phi, sg), (0.9, 0.55, 0.1)))
    return it

# world mapping: viewer on +z. model (x, y, z) -> world (x, -z, y)
tw = lambda p: np.column_stack([p[:, 0], -p[:, 2], p[:, 1]])

def view(phi, elev, azim, size, scale, **kw):
    im, _ = raster.render(items(phi, **kw), tw, elev, azim, size, scale)
    return raster.crop(im)

if __name__ == "__main__":
    s = 1.5 if N >= 4 else 1.9
    closed = view(0, 6, -28, (700, 1000), s)
    so = s if N <= 4 else 1.15
    opened = view(90, 24, -38, (1100, 800 if N <= 4 else 1000), so)
    closed.save(f"foldout/preview_N{N}_closed.png")
    opened.save(f"foldout/preview_N{N}_open.png")
    # four side-view poses
    ims = [view(p, 0, 90, (520, 700), 1.0, skip_wall=False) for p in (0, 30, 60, 90)]
    h = max(i.height for i in ims)
    out = Image.new("RGB", (sum(i.width for i in ims) + 30, h + 40), "white")
    x = 0
    d = ImageDraw.Draw(out)
    for i, p in zip(ims, (0, 30, 60, 90)):
        out.paste(i, (x, 40 + h - i.height)); d.text((x + 8, 12), f"panel {p} deg (side view, wall on the left)", fill=(20, 20, 20)); x += i.width + 10
    out.save(f"foldout/preview_N{N}_poses.png")
    print("saved", closed.size, opened.size, out.size)


def make_gif(n_frames_step=6):
    """animated opening, iso view with a fixed camera"""
    import io
    pts = [(raster.render(items(p, with_springs=True), tw, 20, -38, (1000, 900), 1.05)) for p in (0, 90)]
    cs = [p[1] for p in pts]
    center = ((cs[0][0] + cs[1][0]) / 2, (cs[0][1] + cs[1][1]) / 2)
    seq = list(range(0, 91, n_frames_step)) + [90] * 4 + list(range(90, -1, -n_frames_step)) + [0] * 3
    frames = []
    for p in seq:
        im, _ = raster.render(items(p), tw, 20, -38, (1000, 900), 1.05, center=center)
        ImageDraw.Draw(im).text((12, 10), f"{N} stalls, panel {p} deg", fill=(20, 20, 20))
        frames.append(im.convert("P", palette=Image.ADAPTIVE))
    frames[0].save(f"foldout/foldout_N{N}_open.gif", save_all=True, append_images=frames[1:], duration=110, loop=0)
    print("gif", len(frames), "frames")

if "--gif" in sys.argv:
    make_gif()
