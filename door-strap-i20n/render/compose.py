"""Composite Blender renders: gradient backgrounds, labels, mechanism panel.

usage: python compose.py <render_dir> <out_dir>
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cad"))
import door_strap as ds   # noqa: E402

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
FONT_DIR = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data",
                        "fonts", "ttf")


def font(size, bold=False):
    return ImageFont.truetype(os.path.join(
        FONT_DIR, "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), size)


def radial_bg(size, c0=(64, 64, 68), c1=(9, 9, 11), cx=0.45, cy=0.38):
    w, h = size
    y, x = np.mgrid[0:h, 0:w]
    d = np.sqrt(((x / w - cx) / 0.78) ** 2 + ((y / h - cy) / 0.78) ** 2)
    d = np.clip(d, 0, 1) ** 1.15
    arr = (np.array(c0)[None, None, :] * (1 - d[..., None])
           + np.array(c1)[None, None, :] * d[..., None]).astype("uint8")
    return Image.fromarray(arr, "RGB").convert("RGBA")


def comp(name):
    im = Image.open(os.path.join(SRC, name + ".png")).convert("RGBA")
    bg = radial_bg(im.size)
    bg.alpha_composite(im)
    return bg


def save(im, name, width=None, q=90):
    im = im.convert("RGB")
    if width and im.width != width:
        im = im.resize((width, round(im.height * width / im.width)),
                       Image.LANCZOS)
    im.save(os.path.join(OUT, name + ".jpg"), quality=q, optimize=True)


def project(p_mm, cam, tgt, lens, W, H, sensor=36.0):
    C, T, P = (np.array(cam, float), np.array(tgt, float),
               np.array(p_mm, float) / 1000.0)
    f = (T - C) / np.linalg.norm(T - C)
    z = -f
    x = np.cross([0, 0, 1], z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    d = P - C
    xc, yc, zc = d @ x, d @ y, d @ z
    s = lens / sensor
    return W / 2 + s * xc / (-zc) * W, H / 2 - s * yc / (-zc) * W


def callouts(im, anchors, fs=30, color=(235, 235, 238), line=(200, 30, 40)):
    """anchors: list of (label, (u, v)). Labels go to the nearest side."""
    d = ImageDraw.Draw(im)
    W, H = im.size
    f = font(fs)
    left = sorted([a for a in anchors if a[1][0] < W * 0.5], key=lambda a: a[1][1])
    right = sorted([a for a in anchors if a[1][0] >= W * 0.5],
                   key=lambda a: a[1][1])
    for side, items in (("L", left), ("R", right)):
        n = len(items)
        if not n:
            continue
        ys = np.linspace(H * 0.12, H * 0.9, n) if n > 1 else [items[0][1][1]]
        # keep labels near their anchors but evenly spaced
        ys = [0.5 * (yy + it[1][1]) for yy, it in zip(ys, items)]
        for k in range(1, n):
            ys[k] = max(ys[k], ys[k - 1] + fs * 1.9)
        for (label, (u, v)), yy in zip(items, ys):
            tw = d.textlength(label, font=f)
            if side == "L":
                tx, lx = 40, 40 + tw + 14
            else:
                tx, lx = W - 40 - tw, W - 40 - tw - 14
            d.line([(lx, yy), (u, v)], fill=line, width=3)
            d.ellipse([u - 7, v - 7, u + 7, v + 7], fill=line)
            d.text((tx, yy - fs * 0.6), label, font=f, fill=color)
    return im


def title(im, text, sub=None, fs=40):
    d = ImageDraw.Draw(im)
    d.text((40, 30), text, font=font(fs, True), fill=(245, 245, 247))
    if sub:
        d.text((42, 30 + fs * 1.3), sub, font=font(int(fs * 0.62)),
               fill=(190, 190, 196))
    return im


# --- simple composites ------------------------------------------------------
save(comp("hero"), "hero", 1400)
save(comp("front"), "front", 1600)
save(comp("back"), "back", 1600)
inst = Image.open(os.path.join(SRC, "installed.png")).convert("RGBA")
save(inst, "installed", 1600)

# --- exploded with call-outs ---------------------------------------------------
EXP_CAM = ((-0.30, 0.46, 0.27), (-0.030, 0.040, 0.006), 82.0)
OFF = {"lever": (8, 62, 0), "strap": (8, 62, 0), "washers": (8, 62, 0),
       "strap_pin": (8, 62, 38), "pivot_pin": (0, 0, 52),
       "slider": (-22, 52, 0), "clamp_screw": (-22, 84, 0),
       "insert": (-22, 30, 0), "cable_sheath": (-70, 52, 0),
       "cable_inner": (-70, 52, 0)}
sp = ds.lever_point(ds.STRAP_PIN_LF, ds.POSE_REST)
hk = ds.lever_point(ds.HOOK_LF, ds.POSE_REST)
px, py = ds.PIVOT
ANCH = {
    "housing": ((40, 38, 30), "Housing (LH) - crowned face, wave grooves"),
    "lever": ((px + 9, py + 10, 17), "Bell-crank lever - PET-CF"),
    "strap": ((sp[0] - 14, sp[1] - 4, 6), "25 mm webbing loop (sewn)"),
    "strap_pin": ((sp[0], sp[1], 17.5), "Strap pin  4 x 35 stainless"),
    "pivot_pin": ((px, py, 35.6), "Pivot pin  4 x 70 stainless"),
    "washers": ((px + 3, py, 26.8), "M4 thrust washers (2)"),
    "slider": ((ds.SLIDER_X_NOM + 4, 39.6, 9), "Cable-anchor slider (adjustable)"),
    "clamp_screw": ((ds.SLIDER_X_NOM, 39.0, -9), "M3 x 16 clamp screw"),
    "insert": ((ds.SLIDER_X_NOM, 22.0, -9), "M3 heat-set insert"),
    "cable_sheath": ((ds.SLIDER_X_NOM - 2, ds.CABLE_Y, 4),
                     "OEM release cable + sheath fitting"),
    "cable_inner": ((hk[0] + 3.5, hk[1], 3), "OEM cable nipple"),
}
if os.path.exists(os.path.join(SRC, "exploded.png")):
    ex = comp("exploded")
    W, H = ex.size
    anchors = []
    for n, (p, lab) in ANCH.items():
        o = OFF.get(n, (0, 0, 0))
        q = (p[0] + o[0], p[1] + o[1], p[2] + o[2])
        anchors.append((lab, project(q, *EXP_CAM, W, H)))
    callouts(ex, anchors, fs=30)
    title(ex, "Exploded view - LH unit, seen from the open back",
          "badge insert (front) not shown", fs=40)
    save(ex, "exploded", 1600)

# --- mechanism panel (orthographic top cut at Z=7) ----------------------------
def ortho_uv(x, y, W=1600, H=1250, cx=-20.0, cy=20.0, ppm=10.0):
    return W / 2 + (x - cx) * ppm, H / 2 - (y - cy) * ppm


panels = []
for pose_name, pose, head, sub in (
        ("rest", ds.POSE_REST, "AT REST",
         "latch spring holds the lever on its stop"),
        ("full", ds.POSE_FULL, "STRAP PULLED",
         f"lever +{ds.LEVER_ROT:.0f} deg  ->  cable pulled "
         f"{ds.CABLE_TRAVEL:.1f} mm, latch released")):
    im = comp(f"cut_{pose_name}")
    d = ImageDraw.Draw(im)
    spx, spy = ds.lever_point(ds.STRAP_PIN_LF, pose)
    hx, hy = ds.lever_point(ds.HOOK_LF, pose)
    a = [("Pivot pin", ortho_uv(px, py)),
         ("Strap pin", ortho_uv(spx, spy)),
         ("Cable nipple", ortho_uv(hx + 3.5, hy)),
         ("Sheath anchor slider", ortho_uv(ds.SLIDER_X_NOM, 34)),
         ("Webbing", ortho_uv(-8.5, -25 if pose_name == "rest" else -40)),
         ("Face", ortho_uv(25, 1.0)),
         ("Badge insert", ortho_uv(36, -0.8))]
    callouts(im, a, fs=28)
    # cable direction arrow
    u0, v0 = ortho_uv(-96, ds.CABLE_Y + 6)
    d.text((u0, v0 - 34), "to latch", font=font(26), fill=(210, 210, 215))
    if pose_name == "full":
        ua, va = ortho_uv(hx - ds.CABLE_TRAVEL - 2, hy + 9)
        ub, vb = ortho_uv(hx + 3, hy + 9)
        d.line([(ua, va), (ub, vb)], fill=(255, 200, 40), width=5)
        d.polygon([(ub + 14, vb), (ub - 6, vb - 10), (ub - 6, vb + 10)],
                  fill=(255, 200, 40))
        d.text((ua, va - 40), f"{ds.CABLE_TRAVEL:.1f} mm", font=font(26),
               fill=(255, 210, 80))
        ua, va = ortho_uv(-14, -10)
        ub, vb = ortho_uv(-14, -34)
        d.line([(ua, va), (ub, vb)], fill=(255, 200, 40), width=5)
        d.polygon([(ub, vb + 14), (ub - 10, vb - 6), (ub + 10, vb - 6)],
                  fill=(255, 200, 40))
        d.text((ub - 120, vb + 6), "pull", font=font(26), fill=(255, 210, 80))
    title(im, head, sub, fs=40)
    panels.append(im)
gap = 24
W = panels[0].width * 2 + gap
H = panels[0].height
sheet = Image.new("RGBA", (W, H), (9, 9, 11, 255))
sheet.paste(panels[0], (0, 0))
sheet.paste(panels[1], (panels[0].width + gap, 0))
save(sheet, "mechanism", 2000)
print("composited ->", OUT)
