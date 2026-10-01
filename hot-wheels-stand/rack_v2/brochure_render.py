"""Demo renders for the brochure: python3 brochure_render.py -> brochure/img_*.png"""
import os, numpy as np
from PIL import Image, ImageFilter
import trimesh
from trimesh.transformations import rotation_matrix
import rack_cad as C, raster
from rack_cad import box, cylz, union, diff, hull_of

os.makedirs("brochure", exist_ok=True)
tw = lambda p: np.column_stack([p[:, 0], -p[:, 2], p[:, 1]])
CAR_COLS = [((0.90, 0.12, 0.10), (0.1, 0.15, 0.25)), ((0.1, 0.45, 0.95), (0.1, 0.12, 0.2)), ((1.0, 0.75, 0.05), (0.1, 0.12, 0.2)),
            ((0.1, 0.7, 0.3), (0.1, 0.12, 0.2)), ((0.7, 0.2, 0.85), (0.1, 0.12, 0.2))]
CARD_COLS = [(1.0, 1.0, 1.0)] * 5
BAND = [(0.95, 0.35, 0.1), (0.1, 0.35, 0.8), (0.95, 0.6, 0.0), (0.1, 0.55, 0.3), (0.6, 0.15, 0.7)]


def _ext(pts, z0, z1):
    import shapely.geometry as sg
    m = trimesh.creation.extrude_polygon(sg.Polygon(pts), z1 - z0)
    m.apply_translation([0, 0, z0])
    return m


def car(cx, cy, z0, style):
    """generic 1:64 coupe (side profile extruded), nose to +x. returns [(mesh,color)]"""
    k, D = 1.15, 12.0
    P = [(-38, 3), (-38, 9), (-31, 11), (-19, 12), (-11, 19.5), (7, 19.5), (19, 12.5), (34, 10.5), (38, 7), (38, 3)]
    if style % 2:
        P = [(-38, 3), (-38, 14), (-33, 14), (-31, 11)] + P[3:]       # spoiler
    W = [(-9, 12.8), (-4.5, 18.4), (6, 18.4), (14.5, 12.8)]
    body = _ext(P, 0, D)
    win = _ext(W, -0.2, D + 1.2)
    wh = union([cylz(-1.0, D + 1.0, dx, 6.5, 13.5, 28) for dx in (-23, 24)])
    rim = union([cylz(-1.0, D + 2.4, dx, 6.5, 7, 20) for dx in (-23, 24)])
    out = []
    for m, col in ((body, CAR_COLS[style % 5][0]), (win, (0.12, 0.17, 0.28)), (wh, (0.07, 0.07, 0.07)), (rim, (0.85, 0.85, 0.88))):
        m = m.copy(); m.apply_scale(k); m.apply_translation([cx, cy - 10, z0]); out.append((m, col))
    return out


def card_items(i, x, y, z_off=0.0, lift=0.0, car_style=None):
    """card + blister frame + car. returns list (mesh,color). z_off pushes the card out of the hook."""
    cz = C.CARD_Z + z_off
    top, bot = y + C.CARD_TOP, y + C.CARD_TOP - C.CARD_H
    base = diff(box(x - C.CARD_W / 2, x + C.CARD_W / 2, bot, top, cz, cz + C.CARD_T), [cylz(cz - 1, cz + C.CARD_T + 1, x, y, C.CARD_HOLE_D, 28)])
    band_t = box(x - C.CARD_W / 2, x + C.CARD_W / 2, y - 22, y - 8, cz + C.CARD_T, cz + C.CARD_T + .4)
    band_b = box(x - C.CARD_W / 2, x + C.CARD_W / 2, bot, bot + 6, cz + C.CARD_T, cz + C.CARD_T + .4)
    by0 = bot + 4 + 6
    shell = diff(box(x - C.BLISTER_W / 2, x + C.BLISTER_W / 2, by0, by0 + C.BLISTER_H + 8, cz + C.CARD_T, cz + C.CARD_T + C.BLISTER_D),
                 [box(x - C.BLISTER_W / 2 + 1.5, x + C.BLISTER_W / 2 - 1.5, by0 + 1.5, by0 + C.BLISTER_H + 8 - 1.5, cz + C.CARD_T - 1, cz + C.CARD_T + C.BLISTER_D + 1)])
    # a thin clear-look rear plate in the blister: nothing (car sits on the card)
    cy = by0 + (C.BLISTER_H + 8) / 2
    out = [(base, CARD_COLS[i % 5]), (band_t, BAND[i % 5]), (band_b, BAND[i % 5]), (shell, (0.80, 0.86, 0.9))]
    out += car(x, cy, cz + C.CARD_T + 1.0, i if car_style is None else car_style)
    return out


def scene(R, th, n_cards=None, lifted=None, rail=None):
    rail = rail or C.rail_full(R)
    P = C.assembly(R, th, False, rail, True)
    its = []
    for n, (m, g) in P.items():
        col = (0.82, 0.84, 0.88) if n[0] == "A" else (0.55, 0.6, 0.7) if n[0] == "B" and n[1].isdigit() else \
              (0.25, 0.26, 0.3) if n == "rail" else (0.12, 0.12, 0.14)
        its.append((m, col))
    for i in range(1, R.K + 1):
        if n_cards is not None and i not in n_cards: continue
        x, y = R.hook_xy(i, th)
        if lifted == i:
            its += [(m.copy().apply_translation([10, 38, 85]), c) for m, c in card_items(i - 1, x, y)]
        else:
            its += card_items(i - 1, x, y)
    its += [(m, (0.1, 0.1, 0.12)) for m in C.hardware_fixed(R).values()]
    return its


WALL = np.array([226, 224, 219])


def stage(im, shadow=True):
    a = np.asarray(im.convert("RGB")).astype(int)
    mask = (np.abs(a - 255).sum(2) > 6)
    W, H = im.size
    bg = np.zeros((H, W, 3)); yy = np.linspace(0, 1, H)[:, None, None]
    bg[:] = WALL * (1.03 - 0.10 * yy)
    out = Image.fromarray(bg.astype(np.uint8))
    sh = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(9))
    sh = sh.point(lambda v: int(v * 0.35))
    shadow_layer = Image.new("RGB", (W, H), (60, 55, 50))
    out.paste(shadow_layer, (14, 18), sh)
    out.paste(im.convert("RGB"), (0, 0), Image.fromarray((mask * 255).astype(np.uint8)))
    return out


def save(name, im, pad=60):
    im = raster.crop(im, pad=10)
    W, H = im.size
    canvas = Image.new("RGB", (W + 2 * pad, H + 2 * pad), (255, 255, 255)); canvas.paste(im, (pad, pad))
    stage(canvas).save(f"brochure/{name}.png")


if __name__ == "__main__":
    R5, R3 = C.Rack(5), C.Rack(3)
    r5, r3 = C.rail_full(R5), C.rail_full(R3)
    save("img_hero", raster.render(scene(R5, C.TH_MIN, rail=r5), tw, 10, -24, (2000, 1100), 1.3)[0])
    save("img_front3", raster.render(scene(R3, C.TH_MIN, rail=r3), tw, 0, 0, (1800, 1000), 1.7)[0])
    save("img_pick", raster.render(scene(R5, C.TH_MIN, lifted=3, rail=r5), tw, 12, -16, (2000, 1300), 1.25)[0])
    save("img_closed", raster.render(scene(R3, C.TH_MAX, n_cards=[], rail=r3), tw, 10, -24, (1600, 800), 1.4)[0])
    im, c = raster.render(scene(R5, C.TH_MIN, n_cards=[2], rail=r5), tw, 18, -35, (1800, 1300), 3.4,)
    save("img_hook", im)
    print(os.listdir("brochure"))
