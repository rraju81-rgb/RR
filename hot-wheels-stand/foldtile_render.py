"""Renders for the flat-fold hook tile rack: python3 foldtile_render.py"""
import os, numpy as np, trimesh
from PIL import Image, ImageFilter, ImageDraw
import shapely.geometry as sg
import foldtile_cad as C
import raster
from rack_helpers import box, cylz, union, diff, hull_of

os.makedirs("foldtile", exist_ok=True)
tw = lambda p: np.column_stack([p[:, 0], -p[:, 2], p[:, 1]])
CAR_COLS = [(0.90, 0.12, 0.10), (0.1, 0.45, 0.95), (1.0, 0.75, 0.05), (0.1, 0.7, 0.3), (0.7, 0.2, 0.85), (0.95, 0.4, 0.1)]
BAND = [(0.95, 0.35, 0.1), (0.1, 0.35, 0.8), (0.95, 0.6, 0.0), (0.1, 0.55, 0.3), (0.6, 0.15, 0.7), (0.9, 0.2, 0.2)]
WALL = np.array([226, 224, 219])


def _ext(pts, z0, z1):
    m = trimesh.creation.extrude_polygon(sg.Polygon(pts), z1 - z0); m.apply_translation([0, 0, z0]); return m


def car(cx, cy, z0, style):
    k, D = 1.1, 12.0
    P = [(-38, 3), (-38, 9), (-31, 11), (-19, 12), (-11, 19.5), (7, 19.5), (19, 12.5), (34, 10.5), (38, 7), (38, 3)]
    if style % 2: P = [(-38, 3), (-38, 14), (-33, 14), (-31, 11)] + P[3:]
    body, win = _ext(P, 0, D), _ext([(-9, 12.8), (-4.5, 18.4), (6, 18.4), (14.5, 12.8)], -0.2, D + 1.2)
    wh = union([cylz(-1.0, D + 1.0, dx, 6.5, 13.5, 28) for dx in (-23, 24)])
    rim = union([cylz(-1.0, D + 2.4, dx, 6.5, 7, 20) for dx in (-23, 24)])
    out = []
    for m, col in ((body, CAR_COLS[style % 6]), (win, (0.12, 0.17, 0.28)), (wh, (0.07, 0.07, 0.07)), (rim, (0.85, 0.85, 0.88))):
        m = m.copy(); m.apply_scale(k); m.apply_translation([cx, cy - 10, z0]); out.append((m, col))
    return out


def card_items(i, xc, yh, z_back):
    top, bot = yh + C.CARD_TOP, yh + C.CARD_TOP - C.CARD_H
    base = diff(box(xc - C.CARD_W / 2, xc + C.CARD_W / 2, bot, top, z_back, z_back + C.CARD_T), [cylz(z_back - 1, z_back + C.CARD_T + 1, xc, yh, C.CARD_HOLE, 28)])
    zt = z_back + C.CARD_T
    bands = [box(xc - C.CARD_W / 2, xc + C.CARD_W / 2, yh - 22, yh - 8, zt, zt + 0.4), box(xc - C.CARD_W / 2, xc + C.CARD_W / 2, bot, bot + 6, zt, zt + 0.4)]
    by0 = bot + 10
    shell = diff(box(xc - C.BLISTER_W / 2, xc + C.BLISTER_W / 2, by0, by0 + 44, zt, zt + C.BLISTER_D),
                 [box(xc - C.BLISTER_W / 2 + 1.5, xc + C.BLISTER_W / 2 - 1.5, by0 + 1.5, by0 + 42.5, zt - 1, zt + C.BLISTER_D + 1)])
    out = [(base, (1, 1, 1))] + [(b, BAND[i % 6]) for b in bands] + [(shell, (0.8, 0.86, 0.9))]
    return out + car(xc, by0 + 22, zt + 1.0, i)


def scene(cols=5, rows=1, alpha=90.0, cards=True, row_pitch=185.0, z_back=None):
    its = []
    for r in range(rows):
        for c in range(cols):
            dx, dy = c * C.W, -r * row_pitch
            t = C.tile(); t.apply_translation([dx, dy, 0]); its.append((t, (0.86, 0.86, 0.84)))
            f = C.flap(alpha); f.apply_translation([dx, dy, 0]); its.append((f, (0.95, 0.5, 0.12)))
            if cards:
                zb = z_back if z_back is not None else C.T + 6.0
                its += card_items(c + r * cols, dx + C.XH, dy + C.YH, zb)
    return its


def stage(im):
    a = np.asarray(im.convert("RGB")).astype(int)
    mask = (np.abs(a - 255).sum(2) > 6)
    W, H = im.size
    yy = np.linspace(0, 1, H)[:, None, None]
    out = Image.fromarray((np.zeros((H, W, 3)) + WALL * (1.03 - 0.10 * yy)).astype(np.uint8))
    sh = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * 0.3))
    out.paste(Image.new("RGB", (W, H), (60, 55, 50)), (10, 14), sh)
    out.paste(im.convert("RGB"), (0, 0), Image.fromarray((mask * 255).astype(np.uint8)))
    return out


def save(name, im, pad=50):
    im = raster.crop(im, pad=10); W, H = im.size
    can = Image.new("RGB", (W + 2 * pad, H + 2 * pad), (255, 255, 255)); can.paste(im, (pad, pad)); stage(can).save(f"foldtile/{name}.png")


if __name__ == "__main__":
    save("preview_5car_hero", raster.render(scene(5), tw, 10, -24, (2000, 1300), 1.15)[0])
    save("preview_3car_front", raster.render(scene(3), tw, 0, 0, (1600, 1100), 1.55)[0])
    save("preview_3car_side", raster.render(scene(3), tw, 0, 90, (900, 1000), 1.5)[0])
    save("preview_5car_folded_flat", raster.render(scene(5, alpha=0.0, cards=False), tw, 8, -20, (2000, 400), 1.2)[0])
    save("preview_3x2_grid", raster.render(scene(3, 2), tw, 8, -20, (1600, 1500), 0.95)[0])
    save("preview_arm_closeup", raster.render(scene(1, alpha=90.0, cards=True), tw, 22, -35, (1400, 1200), 3.4)[0])
    # hinge animation
    frames, center = [], None
    for a in list(range(0, 91, 6)) + [90] * 3 + list(range(90, -1, -6)):
        im, c = raster.render(scene(1, alpha=a, cards=(a >= 80)), tw, 24, -38, (900, 800), 2.6, center); center = center or c
        ImageDraw.Draw(im).text((10, 8), f"arm {a} deg", fill=(20, 20, 20)); frames.append(im.convert("P", palette=Image.ADAPTIVE))
    frames[0].save("foldtile/arm_fold_animation.gif", save_all=True, append_images=frames[1:], duration=90, loop=0)
    print(sorted(os.listdir("foldtile")))
