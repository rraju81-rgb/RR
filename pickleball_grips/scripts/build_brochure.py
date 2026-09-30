#!/usr/bin/env python3
"""Two-page pitch brochure / poster for the ten grips, single-colour PLA.

    python3 render_brochure_assets.py      # once: tinted renders -> brochure/assets/
    python3 build_brochure.py              # -> brochure/PickleballGrips_Brochure.pdf

Page 1 (dark poster): headline, the ten grips as a fanned hero, a short note on the handle, the PLA colour options.
Page 2 (light catalogue): two views and a surface close-up of every design, with a line of inspiration each.
Artwork is composited with PIL (brochure/art/, regenerated on every run); all text and shapes stay vector.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pdfkit import *  # noqa: E402,F401,F403
from pdfkit import MM  # noqa: E402
from designs import DESIGNS  # noqa: E402
from render_brochure_assets import PALETTE, COLOUR, ASSIGN, SHOWCASE  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "brochure" / "assets"
ART = ROOT / "brochure" / "art"
OUT = ROOT / "brochure" / "PickleballGrips_Brochure.pdf"
FIT = {r["name"]: r for r in json.loads((ROOT / "fitment_report.json").read_text())}
PRT = {r["name"]: r for r in json.loads((ROOT / "print_report.json").read_text())}
NAMES = [n for n, _, _ in DESIGNS]
LABEL = {n: l for n, l, _ in DESIGNS}
SHORT = {"01_vortex_grip": "VORTEX", "02_cellular_mod": "CELLULAR", "03_tessel_block": "TESSEL", "04_logic_grip": "LOGIC",
         "05_neuro_tread": "NEURO", "06_carbon_matrix": "CARBON", "07_voronoi_core": "VORONOI", "08_topo_flow": "TOPO",
         "09_ergo_contour": "ERGO", "10_hexa_mod": "HEXA"}
INSPIRE = {
    "01_vortex_grip": "Braided rope and woven straps: crossing strands that bite into the palm from every angle.",
    "02_cellular_mod": "Brickwork and stacked stone: staggered cells, with a few recessed pockets for optional inserts.",
    "03_tessel_block": "Cut gemstones and folded paper: faceted pyramids that catch the light and the fingertips.",
    "04_logic_grip": "Jigsaw puzzles: interlocking pieces with mushroom knobs, every row locked to the next.",
    "05_neuro_tread": "Neural networks: nodes joined by curved ridges that rise above a field of fine bumps.",
    "06_carbon_matrix": "Carbon-fibre cloth: a real over-under twill, the finest texture in the set, with smooth patches.",
    "07_voronoi_core": "Dragonfly wings and cracked earth: a rib lattice with open windows. The lightest of the ten.",
    "08_topo_flow": "Contour maps and tree rings: flowing ridges that wrap the handle around four wood-grain knots.",
    "09_ergo_contour": "A river-worn pebble: a smooth swell with finger flutes and a thumb rest shaped for the hand.",
    "10_hexa_mod": "Honeycomb: individual hex pads on four height levels, a pattern you can feel as well as see.",
}
BG1 = "#0F131A"          # page 1 background
LIME = "#9BE04A"
PAPER = "#F4F1EC"       # page 2 background
GREEN_INK = "#3B8A1E"
PANEL_TOP, PANEL_BOT = (240, 236, 229), (224, 219, 210)


def spaced(pg, x, y, s, font, size, color, tracking=0.6, anchor="l"):
    total = sum(sw(ch, font, size) / MM + tracking for ch in s) - tracking
    xx = x - (total if anchor == "r" else total / 2 if anchor == "c" else 0)
    for ch in s:
        pg.text(xx, y, ch, font, size, color)
        xx += sw(ch, font, size) / MM + tracking


def heading(pg, x, y, text, color_bar, color_text, w=None, rule=HAIR):
    pg.rect(x, y - 3.2, 1.5, 3.9, fill=color_bar)
    spaced(pg, x + 3.2, y, text.upper(), F_B, 7.0, color_text, 0.7)
    if w:
        tw = sum(sw(ch, F_B, 7.0) / MM + 0.7 for ch in text.upper())
        pg.line(x + 3.2 + tw + 2.0, y - 1.1, x + w, y - 1.1, rule, 0.2)
    return y + 2.6


def grip_img(name, tag):
    im = Image.open(ASSETS / name / f"hero_{tag}.png").convert("RGBA")
    return im.crop(im.getchannel("A").getbbox())


def fit_height(im, h_px):
    k = h_px / im.height
    return im.resize((max(1, int(round(im.width * k))), int(round(h_px))), Image.LANCZOS)


def soft_shadow(size, cx, cy, rx, ry, blur, alpha):
    """Blurred elliptical contact shadow as an 'L' mask (0..255)."""
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=int(255 * alpha))
    return m.filter(ImageFilter.GaussianBlur(blur))


def reflection(gp, frac=0.26, strength=0.30):
    """Vertical mirror of the grip fading out over `frac` of its height - a glossy-floor look."""
    h = int(gp.height * frac)
    r = gp.transpose(Image.FLIP_TOP_BOTTOM).crop((0, 0, gp.width, h))
    fade = np.linspace(strength, 0.0, h)[:, None] ** 1.3
    a = np.asarray(r.getchannel("A"), float) / 255 * fade
    r.putalpha(Image.fromarray((a * 255).astype(np.uint8)))
    return r.filter(ImageFilter.GaussianBlur(1.2))


# ------------------------------------------------------------------------------------------------ artwork
HERO_H, HERO_BASE, PITCH = 134.0, 117.0, 18.0          # mm: hero height, floor line, grip pitch


def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def make_hero(px=11):
    """Page-1 hero: the ten grips fanned in an arch on a dark studio floor, each in its own PLA colour."""
    W, H = 210 * px, int(HERO_H * px)
    base = np.array(hexrgb(BG1)) * 255
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W * 0.5) / (W * 0.62)) ** 2 + ((yy - H * 0.50) / (H * 0.66)) ** 2)
    g = smooth(1 - r) * smooth(np.minimum(xx, W - 1 - xx) / (0.16 * W)) * smooth(yy / (0.30 * H)) * smooth((H - 1 - yy) / (0.18 * H))   # zero at all four image edges
    img = base + g[..., None] * (np.array([50, 68, 96]) - base) * 0.85
    base_y = int(HERO_BASE * px)                                    # floor line
    fl = np.clip(1 - np.sqrt(((xx - W * 0.5) / (W * 0.50)) ** 2 + ((yy - base_y) / (H * 0.07)) ** 2), 0, 1)
    img += (fl * fl * smooth(np.minimum(xx, W - 1 - xx) / (0.12 * W)) * smooth((H - 1 - yy) / (0.10 * H)))[..., None] * np.array([34, 46, 64]) * 0.9
    canvas = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")
    pitch = PITCH * px
    order = sorted(range(10), key=lambda k: -abs(k - 4.5))          # outer grips first, centre grips on top
    for k in order:
        name = NAMES[k]
        d = abs(k - 4.5)
        h_mm = 112.0 - 3.4 * (d - 0.5)
        gp = fit_height(grip_img(name, "a" if k % 2 == 0 else "b"), h_mm * px)
        cx = W / 2 + (k - 4.5) * pitch
        x0, y0 = int(cx - gp.width / 2), int(base_y - gp.height)
        sh = soft_shadow(canvas.size, cx, base_y - 0.3 * px, gp.width * 0.56, 1.7 * px, 1.6 * px, 0.85)
        canvas.paste(Image.new("RGBA", canvas.size, (0, 0, 0, 255)), (0, 0), sh)
        rf = reflection(gp, frac=0.14)
        canvas.alpha_composite(rf, (x0, base_y + int(0.6 * px)))
        canvas.alpha_composite(gp, (x0, y0))
    out = ART / "hero.png"
    canvas.convert("RGB").save(out)
    return out


def make_panel(name, px=16, w_mm=34.8, h_mm=66.0):
    """Page-2 card panel: two views of one grip (az 32 and -30 deg) standing on a soft studio floor."""
    W, H = int(w_mm * px), int(h_mm * px)
    t = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array(PANEL_TOP, float), np.array(PANEL_BOT, float)
    canvas = Image.fromarray((top * (1 - t) + bot * t).repeat(W, axis=1).astype(np.uint8)).convert("RGBA")
    base_y = int((h_mm - 5.0) * px)
    for tag, fx in (("a", 0.26), ("b", 0.74)):
        gp = fit_height(grip_img(name, tag), 55.0 * px)
        cx = W * fx
        sh = soft_shadow(canvas.size, cx, base_y - 0.2 * px, gp.width * 0.58, 1.2 * px, 1.1 * px, 0.45)
        canvas.paste(Image.new("RGBA", canvas.size, (40, 34, 28, 255)), (0, 0), sh)
        canvas.alpha_composite(gp, (int(cx - gp.width / 2), base_y - gp.height))
    out = ART / f"panel_{name[:2]}.png"
    canvas.convert("RGB").save(out)
    return out


# ------------------------------------------------------------------------------------------------ pages
def page_one(c, pg, hero):
    pg.rect(0, 0, 210, 297, fill=BG1)
    for i, (_, hx) in enumerate(PALETTE):
        pg.rect(i * 21, 0, 21.05, 3.2, fill="#" + hx)
    spaced(pg, 12, 15.0, "THE GRIP COLLECTION", F_B, 7.2, "#9AA5B4", 1.5)
    spaced(pg, 198, 15.0, "PLA  ·  ONE COLOUR  ·  100 % SOLID", F_R, 6.8, "#9AA5B4", 1.0, anchor="r")
    pg.text(11.4, 38.0, "Ten grips.", F_B, 46, WHITE)
    pg.text(11.4, 55.4, "One perfect fit.", F_B, 46, LIME)
    pg.para(12, 61.4, "Ten 3D-printed grip sleeves for your pickleball paddle: one shape underneath, ten different "
            "surfaces on top. Print each in one solid PLA colour.", 150, F_R, 10.4, "#B5BFCC", leading=13.4)
    pg.image(hero, 0, 73, 210, HERO_H, quality=93)
    # names under the floor line
    pitch = PITCH
    for k, n in enumerate(NAMES):
        cx = 105 + (k - 4.5) * pitch
        pg.text(cx, 73 + HERO_BASE + 5.6, f"{k + 1:02d}", F_B, 6.4, LIME, anchor="c")
        pg.text(cx, 73 + HERO_BASE + 9.4, SHORT[n], F_B, 5.3, "#D5DBE4", anchor="c")

    # ---- the handle
    yb = 217.0
    heading(pg, 12, yb, "The handle", LIME, WHITE, 90, "#2A3442")
    wts = [PRT[n]["weight_g"]["PLA"] for n in NAMES]
    note = ("A slim sleeve that slides over your paddle handle: closed at the butt, open at the throat, 132.8 mm long and cut to "
            "the exact 32.06 × 26.04 mm bore of the reference handle. The fit is identical on all ten designs, only the surface "
            "changes, so you can swap textures freely. A smooth collar at each end keeps the edges kind to your hand.")
    yy = pg.para(12, yb + 3.6, note, 88, F_R, 8.3, "#C5CDD8", leading=11.0)
    tiles = [(f"{min(wts):.0f}–{max(wts):.0f} g", "PER GRIP, SOLID"), ("100 %", "INFILL"), ("0.20 mm", "LAYER HEIGHT"), ("1 colour", "PLA, NO SWAPS")]
    tw, gap = 20.5, 2.0
    ty = yy + 4.0
    for i, (big, small) in enumerate(tiles):
        x = 12 + i * (tw + gap)
        pg.rect(x, ty, tw, 15.0, fill="#1A212C", r=1.8)
        pg.text(x + tw / 2, ty + 7.0, big, F_B, 9.6, WHITE, anchor="c")
        spaced(pg, x + tw / 2, ty + 11.6, small, F_R, 4.6, "#8F9BAB", 0.4, anchor="c")

    # ---- colour options
    xc, wc = 108.0, 90.0
    heading(pg, xc, yb, "Choose your colour", LIME, WHITE, wc, "#2A3442")
    pg.text(xc, yb + 6.2, f"The whole grip prints in one solid colour.  Shown: {LABEL[SHOWCASE].title()}, mid-grip.", F_R, 6.6, "#9AA5B4")
    cw_, ch_ = 16.4, 19.6
    for i, (nm, hx) in enumerate(PALETTE):
        r_, c_ = divmod(i, 5)
        x = xc + c_ * (cw_ + 2.0)
        y = yb + 10.0 + r_ * 28.0
        pg.image(ASSETS / "options" / f"{nm.replace(' ', '_')}.png", x, y, cw_, ch_, quality=90, round_=1.8)
        pg.text(x + cw_ / 2, y + ch_ + 3.5, nm, F_B, 5.3, WHITE, anchor="c")
        pg.text(x + cw_ / 2, y + ch_ + 6.6, "#" + hx, F_R, 4.8, "#8F9BAB", anchor="c")
    pg.text(12, 290.5, "Renders of the print files.  Colours are typical PLA filament shades; your spool may differ slightly.  "
            "Designed to print upright, without supports.", F_R, 5.6, "#6E7A8A")


def page_two(c, pg):
    pg.rect(0, 0, 210, 297, fill=PAPER)
    for i, (_, hx) in enumerate(PALETTE):
        pg.rect(i * 21, 0, 21.05, 3.2, fill="#" + hx)
    spaced(pg, 12, 15.0, "THE COLLECTION  ·  TEN DESIGNS, ONE FIT", F_B, 7.0, MUTED, 1.3)
    pg.text(11.6, 35.0, "Ten ways to hold on.", F_B, 28, INK)
    pg.para(12, 39.6, "Two views and a close-up of every design, shown as it prints: one PLA colour, no paint, "
            "no multi-colour swaps.", 98, F_R, 9.0, MUTED, leading=11.8)
    xr = 120.0
    heading(pg, xr, 20.5, "Where the ideas come from", GREEN_INK, INK, 78)
    pg.para(xr, 24.0, "Each design borrows a pattern from somewhere else: braided rope, brickwork, cut gemstones, jigsaw pieces, "
            "neural networks, carbon cloth, dragonfly wings, contour maps, river pebbles and honeycomb. Every one is real 3D relief, "
            "so it reads in a single colour through light and shadow, and you feel it in the hand.", 78, F_R, 7.4, INK, leading=9.7)

    cwid, gap = 34.8, 3.0
    y0, pad_h, tile_h, pitch_y = 52.0, 66.0, 22.0, 116.0
    for k, n in enumerate(NAMES):
        r_, c_ = divmod(k, 5)
        x = 12 + c_ * (cwid + gap)
        y = y0 + r_ * pitch_y
        pg.image(make_panel(n), x, y, cwid, pad_h, quality=92, round_=2.4)
        ty = y + pad_h + 1.6
        pg.image(ASSETS / n / "surface.png", x, ty, cwid, tile_h, quality=90, round_=2.4, crop=(0.0, 0.18, 1.0, 0.82))
        ny = ty + tile_h + 5.2
        pg.text(x, ny, f"{k + 1:02d}", F_B, 7.6, GREEN_INK)
        pg.text(x + 5.6, ny, LABEL[n], F_B, 7.0, INK)
        col = ASSIGN[n]
        pg.circle(x + cwid - 1.6, ny - 1.3, 1.45, fill="#" + COLOUR[col], stroke="#B8B2A8", sw_=0.2)
        pg.para(x, ny + 1.7, INSPIRE[n], cwid, F_R, 6.4, MUTED, leading=7.9, max_lines=4)
        assert len(wrap(INSPIRE[n], F_R, 6.4, cwid)) <= 4, n
        pg.text(x, ny + 17.0, f"{PRT[n]['weight_g']['PLA']:.1f} g  ·  {col}", F_B, 5.9, INK)
    pg.text(12, 290.6, "Every design prints in any of the ten PLA colours on page 1.   100 % infill  ·  0.20 mm layers  ·  "
            "printed upright, butt end down.", F_R, 5.8, SUBTLE)


def main():
    ART.mkdir(parents=True, exist_ok=True)
    hero = make_hero()
    c = new_canvas(OUT, "Pickleball Paddle Grips - Collection Brochure", subject="Ten single-colour PLA grip designs",
                   keywords="pickleball, grip, 3D print, PLA")
    pg = Page(c)
    page_one(c, pg, hero)
    c.showPage()
    pg = Page(c)
    page_two(c, pg)
    c.showPage()
    c.save()
    print("wrote", OUT, f"{OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
