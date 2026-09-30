#!/usr/bin/env python3
"""Ten two-page pitch brochures, one per grip design (single-colour PLA, colour options, all ten designs shown).

    python3 render_brochure_assets.py      # tinted hero / surface renders          -> brochure/assets/
    python3 render_design_assets.py        # rich per-design artwork                -> brochure/assets/
    python3 build_design_brochures.py      # -> brochure/designs/<id>_brochure.pdf   [--only 01 07 ...]

Page 1 (dark poster): big hero, the design story, a close-up, the handle note, and the whole grip in ten PLA colours.
Page 2 (light catalogue): two views, cutaway, paddle illustration, four surface images, the inspiration, and all ten designs.
Artwork is composited with PIL (brochure/art/designs/); text and shapes stay vector.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pdfkit import *  # noqa: E402,F401,F403
from pdfkit import MM  # noqa: E402
from designs import DESIGNS  # noqa: E402
from render_brochure_assets import PALETTE, COLOUR, ASSIGN  # noqa: E402
from design_content import CONTENT, ACCENT, HANDLE_NOTE  # noqa: E402
from build_brochure import (spaced, heading, smooth, soft_shadow, reflection, fit_height, BG1, PAPER,  # noqa: E402
                            PANEL_TOP, PANEL_BOT, SHORT)

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "brochure" / "assets"
ART = ROOT / "brochure" / "art" / "designs"
OUTDIR = ROOT / "brochure" / "designs"
PRT = {r["name"]: r for r in json.loads((ROOT / "print_report.json").read_text())}
NAMES = [n for n, _, _ in DESIGNS]
LABEL = {n: l for n, l, _ in DESIGNS}
FONT_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
HEX = dict(PALETTE)                                   # colour name -> hex
TILE_BG = "#E9E6E1"
CIRCLE = {"09_ergo_contour": "swatch.png"}             # smooth design: the lit relief reads better than a soft close-up
CIRCLE_CAP = {"09_ergo_contour": "UNROLLED SURFACE  ·  RELIEF ×4"}


# ---------------------------------------------------------------------------------------------- PIL helpers
def rgba(path):
    return Image.open(path).convert("RGBA")


def tight(im):
    return im.crop(im.getchannel("A").getbbox())


def hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)


def gradient_bg(W, H, top, bot):
    t = np.linspace(0, 1, H)[:, None, None]
    return Image.fromarray((np.array(top, float) * (1 - t) + np.array(bot, float) * t).repeat(W, axis=1).astype(np.uint8)).convert("RGBA")


def put_grip(canvas, gp, cx, base_y, px, shadow=0.5, shadow_rgb=(0, 0, 0), refl=0.0):
    """Shadow, optional reflection and the grip itself, bottom-centred at (cx, base_y) pixels."""
    if shadow:
        sh = soft_shadow(canvas.size, cx, base_y - 0.25 * px, gp.width * 0.56, 1.3 * px, 1.3 * px, shadow)
        canvas.paste(Image.new("RGBA", canvas.size, shadow_rgb + (255,)), (0, 0), sh)
    if refl:
        canvas.alpha_composite(reflection(gp, frac=0.14, strength=refl), (int(cx - gp.width / 2), int(base_y + 0.5 * px)))
    canvas.alpha_composite(gp, (int(cx - gp.width / 2), int(base_y - gp.height)))


# ---------------------------------------------------------------------------------------------- artwork
def art_dir(name):
    d = ART / name[:2]
    d.mkdir(parents=True, exist_ok=True)
    return d


def make_hero(name, idx, acc, px=11, W_mm=112.0, H_mm=150.0):
    """Page-1 hero: one big grip on a dark stage with a glow in the design's colour and a giant faded number."""
    W, H = int(W_mm * px), int(H_mm * px)
    base = hex_rgb(BG1)
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W * 0.52) / (W * 0.66)) ** 2 + ((yy - H * 0.50) / (H * 0.60)) ** 2)
    win = smooth(np.minimum(xx, W - 1 - xx) / (0.16 * W)) * smooth(yy / (0.22 * H)) * smooth((H - 1 - yy) / (0.18 * H))
    g = smooth(1 - r) * win
    glow = 0.26 * hex_rgb(acc) + 0.74 * base
    img = base + g[..., None] * (glow - base)
    base_y = int(137 * px)
    fl = np.clip(1 - np.sqrt(((xx - W * 0.52) / (W * 0.46)) ** 2 + ((yy - base_y) / (H * 0.06)) ** 2), 0, 1)
    img += (fl * fl * win)[..., None] * (0.30 * hex_rgb(acc) * 0.5 + np.array([14, 18, 26]))
    canvas = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")
    # giant faded design number behind the grip
    font = ImageFont.truetype(FONT_B, int(80 * px))
    ov = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    txt = f"{idx:02d}"
    bb = d.textbbox((0, 0), txt, font=font)
    d.text(((W - (bb[2] - bb[0])) / 2 - bb[0], 8 * px - bb[1]), txt, font=font, fill=tuple(hex_rgb(acc).astype(int)) + (26,))
    canvas.alpha_composite(ov)
    gp = fit_height(tight(rgba(ASSETS / name / "hero_a.png")), 127 * px)
    put_grip(canvas, gp, W * 0.52, base_y, px, shadow=0.85, refl=0.30)
    out = art_dir(name) / "hero1.png"
    canvas.convert("RGB").save(out)
    return out


def slice_row(name, n=10, gap_px=350, half=175):
    im = rgba(ASSETS / name / "row.png")
    cx0 = im.width / 2
    return [tight(im.crop((int(cx0 + (i - (n - 1) / 2) * gap_px - half), 0, int(cx0 + (i - (n - 1) / 2) * gap_px + half), im.height))) for i in range(n)]


def make_colour_panel(name, px=11, W_mm=186.0, H_mm=62.0):
    """The same grip in all ten PLA colours on a dark stage (the labels are vector text on the page)."""
    W, H = int(W_mm * px), int(H_mm * px)
    canvas = gradient_bg(W, H, (34, 42, 56), (20, 26, 35))
    pitch = W_mm / 10
    for i, gp in enumerate(slice_row(name)):
        gp = fit_height(gp, 40.5 * px)
        put_grip(canvas, gp, (i + 0.5) * pitch * px, 47.0 * px, px, shadow=0.7, refl=0.22)
    out = art_dir(name) / "colours.png"
    canvas.convert("RGB").save(out)
    return out


def make_view_panel(name, kind, px=16, W_mm=43.5, H_mm=76.0):
    """Row-B panel on a soft studio gradient: a turn of the grip, the half section, or the paddle illustration."""
    W, H = int(W_mm * px), int(H_mm * px)
    canvas = gradient_bg(W, H, PANEL_TOP, PANEL_BOT)
    if kind in ("a", "b"):
        gp = fit_height(tight(rgba(ASSETS / name / f"hero_{kind}.png")), 62 * px)
        put_grip(canvas, gp, W / 2, 69 * px, px, shadow=0.42, shadow_rgb=(40, 34, 28))
    elif kind == "cutaway":
        gp = fit_height(tight(rgba(ASSETS / name / "cutaway.png")), 62 * px)
        put_grip(canvas, gp, W / 2, 69 * px, px, shadow=0.35, shadow_rgb=(40, 34, 28))
    else:                                                          # paddle: rendered at the panel aspect already
        pd = rgba(ASSETS / name / "paddle.png").resize((W, H), Image.LANCZOS)
        canvas.alpha_composite(pd)
    out = art_dir(name) / f"view_{kind}.png"
    canvas.convert("RGB").save(out)
    return out


def make_collection(cur, px=12, W_mm=186.0, H_mm=52.0):
    """All ten designs side by side (each in its own colour) on a soft panel."""
    W, H = int(W_mm * px), int(H_mm * px)
    canvas = gradient_bg(W, H, (236, 232, 225), (224, 219, 210))
    pitch = W_mm / 10
    for i, n in enumerate(NAMES):
        gp = fit_height(tight(rgba(ASSETS / n / "hero_a.png")), 38 * px)
        put_grip(canvas, gp, (i + 0.5) * pitch * px, 41 * px, px, shadow=0.40, shadow_rgb=(40, 34, 28))
    out = ART / "collection.png"
    if not out.exists():
        canvas.convert("RGB").save(out)
    return out


# ---------------------------------------------------------------------------------------------- vector motifs (inspiration)
def _ellipse(cx, cy, rx, ry, rot_deg, n=28):
    a = math.radians(rot_deg)
    pts = []
    for k in range(n):
        t = 2 * math.pi * k / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        pts.append((cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)))
    return pts


def m_rope(pg, x, y, s, c, t):
    for i in range(7):
        cy = y + s * (0.17 + 0.62 * i / 6)
        pg.polygon(_ellipse(x + s * 0.5, cy, s * 0.30, s * 0.075, 28), fill=c, stroke=shade(c, 0.35), sw_=0.25)
        pg.polygon(_ellipse(x + s * 0.5, cy + s * 0.055, s * 0.30, s * 0.062, -28), fill=t, stroke=shade(c, 0.25), sw_=0.25)


def m_brick(pg, x, y, s, c, t):
    rows, bw, bh, gap = 6, s * 0.30, s * 0.11, s * 0.028
    for r in range(rows):
        off = (bw / 2 + gap) if r % 2 else 0
        for k in range(-1, 4):
            bx, by = x + s * 0.06 + k * (bw + gap) + off, y + s * 0.10 + r * (bh + gap * 1.4)
            if bx < x or bx + bw > x + s - 0.0:
                continue
            filled = (r * 3 + k) % 5 == 1
            pg.rect(bx, by, bw, bh, fill=(c if filled else None), stroke=c, sw_=0.3, r=0.7)


def m_gem(pg, x, y, s, c, t):
    cx, cy = x + s / 2, y + s / 2
    n, R, r = 8, s * 0.44, s * 0.22
    ang = [math.radians(22.5 + 45 * k) for k in range(n)]
    O = [(cx + R * math.cos(a), cy + R * math.sin(a)) for a in ang]
    Ii = [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in ang]
    for k in range(n):
        k2 = (k + 1) % n
        pg.polygon([O[k], O[k2], Ii[k2]], fill=(t if k % 2 else tint(c, 0.35)), stroke=c, sw_=0.25)
        pg.polygon([O[k], Ii[k2], Ii[k]], fill=(c if k % 2 else shade(c, 0.12)), stroke=c, sw_=0.25)
    pg.polygon(Ii, fill=tint(c, 0.6), stroke=c, sw_=0.25)


def m_puzzle(pg, x, y, s, c, t):
    a, g = s * 0.40, s * 0.05
    for i in range(2):
        for j in range(2):
            px_, py_ = x + s * 0.05 + i * (a + g), y + s * 0.05 + j * (a + g)
            pg.rect(px_, py_, a, a, fill=(c if (i + j) % 2 == 0 else t), stroke=c, sw_=0.3, r=1.0)
    for (kx, ky, f) in ((x + s * 0.05 + a + g / 2, y + s * 0.05 + a * 0.5, True), (x + s * 0.05 + a * 0.5, y + s * 0.05 + a + g / 2, False),
                        (x + s * 0.05 + a + g / 2, y + s * 0.05 + a + g + a * 0.5, False), (x + s * 0.05 + a + g + a * 0.5, y + s * 0.05 + a + g / 2, True)):
        pg.circle(kx, ky, s * 0.055, fill=(c if f else t), stroke=c, sw_=0.3)


def m_neuro(pg, x, y, s, c, t):
    pts = [(0.15, 0.25), (0.42, 0.12), (0.72, 0.22), (0.88, 0.5), (0.62, 0.52), (0.30, 0.48), (0.14, 0.75), (0.45, 0.85), (0.78, 0.82)]
    links = [(0, 1), (1, 2), (2, 3), (2, 4), (1, 5), (0, 5), (5, 4), (5, 6), (5, 7), (4, 7), (7, 8), (4, 8), (3, 8)]
    for a, b in links:
        (x1, y1), (x2, y2) = pts[a], pts[b]
        mx_, my_ = (x1 + x2) / 2 + (y2 - y1) * 0.18, (y1 + y2) / 2 - (x2 - x1) * 0.18
        curve = [((1 - u) ** 2 * x1 + 2 * (1 - u) * u * mx_ + u * u * x2, (1 - u) ** 2 * y1 + 2 * (1 - u) * u * my_ + u * u * y2) for u in np.linspace(0, 1, 14)]
        pg.polyline([(x + s * px_, y + s * py_) for px_, py_ in curve], c, 0.55)
    for i, (px_, py_) in enumerate(pts):
        pg.circle(x + s * px_, y + s * py_, s * (0.07 if i in (5, 4) else 0.05), fill=c, stroke=shade(c, 0.3), sw_=0.2)


def m_twill(pg, x, y, s, c, t):
    n = 10
    cs = s * 0.86 / n
    for i in range(n):
        for j in range(n):
            horiz = ((i + j) // 2) % 2 == 0
            bx, by = x + s * 0.07 + j * cs, y + s * 0.07 + i * cs
            if horiz:
                pg.rect(bx + cs * 0.06, by + cs * 0.18, cs * 0.88, cs * 0.64, fill=c, stroke=shade(c, 0.3), sw_=0.15, r=0.3)
            else:
                pg.rect(bx + cs * 0.18, by + cs * 0.06, cs * 0.64, cs * 0.88, fill=t, stroke=shade(c, 0.2), sw_=0.15, r=0.3)


def m_wing(pg, x, y, s, c, t):
    from scipy.spatial import Voronoi
    from shapely.geometry import LineString, box
    rng = np.random.default_rng(7)
    pts = []
    for r in range(-1, 8):
        for k in range(-1, 8):
            pts.append(((k + (0.5 if r % 2 else 0)) / 6 * 1.0 + rng.normal(0, 0.028), r / 6 * 0.86 + rng.normal(0, 0.028)))
    vor = Voronoi(np.array(pts))
    clip = box(0.04, 0.06, 0.96, 0.94)
    for ridge in vor.ridge_vertices:
        if -1 in ridge:
            continue
        seg = LineString(vor.vertices[ridge]).intersection(clip)
        if seg.is_empty or seg.geom_type != "LineString":
            continue
        (x1, y1), (x2, y2) = list(seg.coords)[0], list(seg.coords)[-1]
        pg.line(x + s * x1, y + s * y1, x + s * x2, y + s * y2, c, 0.6, cap=1)
    pg.rect(x + s * 0.04, y + s * 0.06, s * 0.92, s * 0.88, stroke=c, sw_=0.6, r=2.0)


def m_contour(pg, x, y, s, c, t):
    cx, cy = x + s * 0.52, y + s * 0.5
    for i, k in enumerate(np.linspace(0.06, 0.46, 9)):
        pts = []
        for th in np.linspace(0, 2 * math.pi, 90):
            r = 0.86 * k * s * (1 + 0.10 * math.sin(3 * th + 0.8 + k * 3) + 0.06 * math.sin(5 * th + 1.7) + 0.04 * (1 - k) * math.cos(2 * th))
            pts.append((cx + r * math.cos(th) * 1.05 - (0.05 - k * 0.1) * s, cy + r * math.sin(th) * 0.92))
        pg.polyline(pts + [pts[0]], c, 0.4 if i % 3 else 0.7)


def m_pebble(pg, x, y, s, c, t):
    cx, cy, a, b = x + s / 2, y + s / 2, s * 0.40, s * 0.44
    pts = []
    for th in np.linspace(0, 2 * math.pi, 120):
        ct, st = math.cos(th), math.sin(th)
        pts.append((cx + a * np.sign(ct) * abs(ct) ** (2 / 2.7), cy + b * np.sign(st) * abs(st) ** (2 / 2.7)))
    pg.polygon(pts, fill=t, stroke=c, sw_=0.5)
    for k in range(4):
        yy = cy - b * 0.52 + k * b * 0.30
        pg.polyline([(cx - a * 0.55 + u * a * 1.1, yy + 1.4 * math.sin(u * math.pi)) for u in np.linspace(0, 1, 16)], c, 0.4)
    pg.polygon(_ellipse(cx + a * 0.25, cy - b * 0.68, a * 0.22, b * 0.11, -20), stroke=c, sw_=0.4)


def m_hex(pg, x, y, s, c, t):
    R = s * 0.105
    shades = [tint(c, 0.75), tint(c, 0.5), tint(c, 0.25), c]
    rows = 6
    for r in range(rows):
        for k in range(5):
            cx = x + s * 0.12 + k * R * 1.74 + (R * 0.87 if r % 2 else 0)
            cy = y + s * 0.12 + r * R * 1.5
            if cx + R * 0.87 > x + s * 0.98:
                continue
            pts = [(cx + R * 0.93 * math.cos(math.radians(60 * i + 30)), cy + R * 0.93 * math.sin(math.radians(60 * i + 30))) for i in range(6)]
            pg.polygon(pts, fill=shades[(r * 2 + k * 3 + (r * k) % 3) % 4], stroke=c, sw_=0.25)


MOTIF = {"rope": m_rope, "brick": m_brick, "gem": m_gem, "puzzle": m_puzzle, "neuro": m_neuro, "twill": m_twill, "wing": m_wing,
         "contour": m_contour, "pebble": m_pebble, "hex": m_hex}


# ---------------------------------------------------------------------------------------------- pages
def colour_strip(pg):
    for i, (_, hx) in enumerate(PALETTE):
        pg.rect(i * 21, 0, 21.05, 3.2, fill="#" + hx)


def index_line(pg, y, cur, on_dark):
    """'01 VORTEX  02 CELLULAR ...' with the current design highlighted - the whole collection on every page."""
    acc = ACCENT[NAMES[cur]][0 if on_dark else 1]
    base, strong = ("#6E7A8A", "#D5DBE4") if on_dark else (SUBTLE, INK)
    items = [f"{i + 1:02d} {SHORT[n]}" for i, n in enumerate(NAMES)]
    total = sum(sw(t, F_R, 5.6) / MM for t in items)
    gap = (186 - total) / (len(items) - 1)
    x = 12.0
    for i, t in enumerate(items):
        w = sw(t, F_B if i == cur else F_R, 5.6) / MM
        pg.text(x, y, t, F_B if i == cur else F_R, 5.6, acc if i == cur else base)
        if i == cur:
            pg.rect(x, y + 1.2, w, 0.5, fill=acc)
        x += sw(items[i], F_R, 5.6) / MM + gap


def page_one(pg, n, cur, art):
    C, (acc, _) = CONTENT[n], ACCENT[n]
    colour = ASSIGN[n]
    pg.rect(0, 0, 210, 297, fill=BG1)
    colour_strip(pg)
    spaced(pg, 12, 15.0, f"PG-{cur + 1:02d}  ·  THE GRIP COLLECTION", F_B, 7.0, "#9AA5B4", 1.4)
    spaced(pg, 198, 15.0, "PLA  ·  ONE COLOUR  ·  100 % SOLID", F_R, 6.8, "#9AA5B4", 1.0, anchor="r")
    spaced(pg, 12, 29.0, f"DESIGN {cur + 1:02d} OF 10", F_B, 7.2, acc, 1.5)
    title = LABEL[n].upper()
    size = 38.0
    while sw(title, F_B, size) / MM > 160:
        size -= 1
    pg.text(11.4, 29.0 + 6 + size * 0.3, title, F_B, size, WHITE)
    pg.para(12, 29.0 + 6 + size * 0.3 + 4.0, C["tagline"], 130, F_R, 10.4, "#B5BFCC", leading=13.4, max_lines=2)
    pg.image(art["hero1"], 98, 58, 112, 150, quality=93)

    # ---- left column: the design, a close-up, the handle
    x0, w0 = 12.0, 84.0
    cr = 23.0
    n_story = len(wrap(C["story"], F_R, 8.5, w0))
    n_note = len(wrap(HANDLE_NOTE, F_R, 7.9, w0))
    story_end = 70.0 + 3.6 + n_story * 11.2 / MM
    block = 2 * cr + 5.0 + 2.6 + 1.0 + n_note * 10.2 / MM + 3.4 + 12.4
    spare = max(0.0, 206.0 - story_end - block - 7.0 - 9.0)
    gap_a, gap_b = 7.0 + min(spare / 2, 9.0), 9.0 + min(spare / 2, 9.0)
    y = heading(pg, x0, 70.0, "The design", acc, WHITE, w0, "#2A3442")
    yy = pg.para(x0, y + 1.0, C["story"], w0, F_R, 8.5, "#C5CDD8", leading=11.2)
    cy = yy + gap_a + cr
    cx = x0 + cr + 1.0
    circ = ASSETS / n / ("surface_dark.png" if (ASSETS / n / "surface_dark.png").exists() else CIRCLE.get(n, "surface.png"))
    pg.image(circ, cx - cr, cy - cr, 2 * cr, 2 * cr, quality=90, round_=cr)
    pg.circle(cx, cy, cr, stroke=acc, sw_=0.7)
    pg.circle(cx, cy, cr + 1.6, stroke=acc, sw_=0.15)
    spaced(pg, cx, cy + cr + 5.2, CIRCLE_CAP.get(n, "CLOSE-UP  ·  MID BODY"), F_R, 4.8, "#8F9BAB", 0.6, anchor="c")
    stats = [(f"{PRT[n]['weight_g']['PLA']:.1f} g", "PLA, SOLID")] + list(C["stats"])
    sx = x0 + 2 * cr + 7.0
    for i, (big, small) in enumerate(stats):
        ty = cy - cr + 5.0 + i * 15.8
        pg.rect(sx, ty, 1.0, 11.2, fill=acc)
        pg.text(sx + 3.0, ty + 5.4, big, F_B, 11.0, WHITE)
        spaced(pg, sx + 3.0, ty + 9.6, small, F_R, 4.6, "#8F9BAB", 0.5)
    yh = cy + cr + 5.2 + gap_b
    y = heading(pg, x0, yh, "The handle", acc, WHITE, w0, "#2A3442")
    yy = pg.para(x0, y + 1.0, HANDLE_NOTE, w0, F_R, 7.9, "#C5CDD8", leading=10.2)
    tiles = [("132.8 mm", "LENGTH"), ("32 × 26 mm", "BORE"), ("100 %", "INFILL"), ("0.20 mm", "LAYERS")]
    tw, gp = 19.5, 2.0
    ty = yy + 3.4
    for i, (big, small) in enumerate(tiles):
        tx = x0 + i * (tw + gp)
        pg.rect(tx, ty, tw, 12.4, fill="#1A212C", r=1.6)
        pg.text(tx + tw / 2, ty + 5.6, big, F_B, 7.6, WHITE, anchor="c")
        spaced(pg, tx + tw / 2, ty + 9.6, small, F_R, 4.2, "#8F9BAB", 0.4, anchor="c")

    # ---- the whole grip in ten colours
    yc = 216.0
    heading(pg, 12, yc, "Choose your colour", acc, WHITE, 120, "#2A3442")
    spaced(pg, 198, yc, f"DESIGNER'S PICK:  {colour.upper()}", F_B, 5.8, acc, 0.8, anchor="r")
    py0 = yc + 4.0
    pg.image(art["colours"], 12, py0, 186, 62.0, quality=92, round_=2.6)
    pitch = 18.6
    for i, (nm, hx) in enumerate(PALETTE):
        cx_ = 12 + (i + 0.5) * pitch
        pick = nm == colour
        if pick:
            pg.rect(12 + i * pitch + 0.5, py0 + 0.8, pitch - 1.0, 60.4, stroke=acc, sw_=0.4, r=1.8)
            spaced(pg, cx_, py0 + 4.0, "PICK", F_B, 4.6, acc, 0.6, anchor="c")
        pg.text(cx_, py0 + 54.6, nm, F_B, 5.0, WHITE, anchor="c")
        pg.text(cx_, py0 + 58.0, "#" + hx, F_R, 4.4, "#8F9BAB", anchor="c")
    index_line(pg, 290.6, cur, True)


def page_two(pg, n, cur, art):
    C, (_, acc) = CONTENT[n], ACCENT[n]
    pg.rect(0, 0, 210, 297, fill=PAPER)
    colour_strip(pg)
    spaced(pg, 12, 15.0, f"PG-{cur + 1:02d}  ·  {LABEL[n].upper()}", F_B, 7.0, MUTED, 1.3)
    spaced(pg, 198, 15.0, "VIEWS & SURFACES", F_R, 7.0, MUTED, 1.0, anchor="r")
    pg.text(11.6, 31.5, f"{LABEL[n].title()}, all round.", F_B, 23, INK)
    pg.text(12, 38.4, "Four views, four surfaces and the idea behind the design. Shown as it prints: one solid PLA colour.", F_R, 8.6, MUTED)

    xs = [12 + i * 47.5 for i in range(4)]
    cap = lambda x, y, s: spaced(pg, x, y, s, F_B, 5.3, MUTED, 0.45)
    # views
    yb = 45.0
    for x, key, label in zip(xs, ("a", "b", "cutaway", "paddle"),
                             ("3/4 VIEW  ·  TURN 0°", "SIDE VIEW  ·  TURN 90°", "CUTAWAY  ·  SOLID WALL", "ON A PADDLE  ·  ILLUSTRATION")):
        pg.image(art["view_" + key], x, yb, 43.5, 76.0, quality=92, round_=2.4)
        cap(x, yb + 79.6, label)
    # surfaces
    yc = 131.0
    for x, key, label in zip(xs, ("surface", "rim", "swatch", "surface2"),
                             ("CLOSE-UP  ·  MID BODY", "RIM & BORE  ·  FROM ABOVE", "UNROLLED  ·  RELIEF ×4" if n == "09_ergo_contour" else "UNROLLED  ·  LIT RELIEF", "RAKING LIGHT  ·  LOW BODY")):
        pg.image(ASSETS / n / f"{key}.png", x, yc, 43.5, 43.5, quality=90, round_=2.4)
        cap(x, yc + 47.2, label)
    # inspiration + why it grips
    yd = 184.0
    pg.rect(12, yd, 34.0, 34.0, fill=tint(acc, 0.86), r=2.4)
    MOTIF[C["motif"]](pg, 12, yd, 34.0, acc, tint(acc, 0.72))
    y = heading(pg, 50.0, yd + 3.2, "Design inspiration", acc, INK, 56)
    pg.para(50.0, y + 0.6, C["inspiration"], 52.0, F_R, 7.6, INK, leading=9.6)
    xr = 110.0
    y = heading(pg, xr, yd + 3.2, "Why it grips", acc, INK, 88)
    yy = y + 0.6
    for f in C["features"]:
        pg.rect(xr + 0.2, yy + 1.2, 1.6, 1.6, fill=acc)
        yy = pg.para(xr + 4.0, yy, f, 84.0, F_R, 8.0, INK, leading=10.0) + 1.3
    yy += 1.4
    pg.rect(xr, yy, 88.0, 0.2, fill=HAIR)
    spaced(pg, xr, yy + 4.4, "PRINT TIP", F_B, 5.4, acc, 0.7)
    pg.para(xr, yy + 6.2, C["tip"], 88.0, F_I, 7.4, MUTED, leading=9.4, max_lines=2)
    # the whole collection
    ye = 226.0
    heading(pg, 12, ye, "The whole collection", acc, INK, 186)
    ey = ye + 3.8
    pg.image(art["collection"], 12, ey, 186, 52.0, quality=92, round_=2.6)
    pitch = 18.6
    for i, nn in enumerate(NAMES):
        cx_ = 12 + (i + 0.5) * pitch
        cur_ = i == cur
        pg.text(cx_, ey + 45.4, f"{i + 1:02d}", F_B, 6.0, acc if cur_ else MUTED, anchor="c")
        pg.text(cx_, ey + 49.4, SHORT[nn], F_B if cur_ else F_R, 4.9, INK if cur_ else MUTED, anchor="c")
        if cur_:
            pg.rect(12 + i * pitch + 0.6, ey + 0.8, pitch - 1.2, 50.4, stroke=acc, sw_=0.5, r=2.0)
    pg.text(12, 289.6, "The paddle in the illustration is generic, not your paddle.   Every design prints in any of the ten PLA colours "
            "shown on page 1.   100 % infill  ·  0.20 mm layers  ·  upright, butt end down.", F_R, 5.4, SUBTLE)


def build(n):
    cur = NAMES.index(n)
    ART.mkdir(parents=True, exist_ok=True)
    acc_dark = ACCENT[n][0]
    art = dict(hero1=make_hero(n, cur + 1, acc_dark), colours=make_colour_panel(n), collection=make_collection(cur))
    for k in ("a", "b", "cutaway", "paddle"):
        art["view_" + k] = make_view_panel(n, k)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    out = OUTDIR / f"{n}_brochure.pdf"
    c = new_canvas(out, f"{LABEL[n]} - grip brochure (PG-{cur + 1:02d})", subject="Single-colour PLA pitch brochure",
                   keywords="pickleball, grip, 3D print, PLA")
    pg = Page(c)
    page_one(pg, n, cur, art)
    c.showPage()
    pg = Page(c)
    page_two(pg, n, cur, art)
    c.showPage()
    c.save()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    for n in NAMES:
        if a.only and not any(n.startswith(o) for o in a.only):
            continue
        out = build(n)
        print("wrote", out.name, f"{out.stat().st_size / 1e6:.1f} MB", flush=True)


if __name__ == "__main__":
    main()
