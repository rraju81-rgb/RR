#!/usr/bin/env python3
"""Render presentation images and dimensioned drawing sheets into renders/.

Needs the exports (run scripts/generate.py first), Node.js and Playwright with
Chromium (headless WebGL via SwiftShader).

    python scripts/make_figures.py            # everything
    python scripts/make_figures.py --skip-photos
"""

from __future__ import annotations

import argparse
import contextlib
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from manta.build import build_variant  # noqa: E402
from manta.design import VARIANTS  # noqa: E402

OUT = ROOT / "renders"
TMP = ROOT / "renders" / "_raw"
GROUND_Z = -52.0
INK = "#1d2733"
RULE = "#d23c3c"


# ---------------------------------------------------------------------------
# rendering helpers
# ---------------------------------------------------------------------------

def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def http_server(root: Path):
    port = _free_port()
    proc = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
                            cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            with contextlib.suppress(OSError), socket.create_connection(("127.0.0.1", port), 0.2):
                break
            time.sleep(0.1)
        yield port
    finally:
        proc.terminate()


def render(port, w, h, jobs):
    TMP.mkdir(parents=True, exist_ok=True)
    cmd = ["node", str(ROOT / "scripts" / "render_views.cjs"), str(port), str(TMP), str(w), str(h)]
    cmd += [f"{n}|{q}" for n, q in jobs]
    subprocess.run(cmd, check=True)


def to_jpg(name, out_name=None, crop=None, quality=90):
    im = Image.open(TMP / f"{name}.png").convert("RGB")
    if crop:
        im = im.crop(crop)
    im.save(OUT / f"{out_name or name}.jpg", quality=quality, optimize=True)


# ---------------------------------------------------------------------------
# orthographic views + drawing sheet
# ---------------------------------------------------------------------------

ORTHO = {
    # name: (pixel w, pixel h, width in mm, centre (x, y, z) in design mm)
    "side": (2400, 860, 5700.0, None),
    "top": (2400, 1000, 5700.0, None),
    "front": (1100, 900, 2500.0, None),
    "back": (1100, 900, 2500.0, None),
}


def ortho_jobs(key, xc):
    jobs = []
    meta = {}
    for view, (pw, ph, ow, _) in ORTHO.items():
        oh = ow * ph / pw
        if view == "side":
            c = (xc, 0.0, 480.0)
            ext = (xc - ow / 2, xc + ow / 2, c[2] - oh / 2, c[2] + oh / 2)
        elif view == "top":
            c = (xc, 0.0, 500.0)
            ext = (xc - ow / 2, xc + ow / 2, -oh / 2, oh / 2)
        else:
            c = (xc, 0.0, 500.0)
            ext = (-ow / 2, ow / 2, c[2] - oh / 2, c[2] + oh / 2)
        oc = f"{-c[1] / 1000:.4f},{c[2] / 1000:.4f},{-c[0] / 1000:.4f}"
        q = (f"variant={key}&ortho={view}&ow={ow / 1000:.4f}&oc={oc}&context=0&appendages=1"
             f"&bg=white&ground=0&look=livery")
        jobs.append((f"{key}_ortho_{view}", q))
        meta[view] = (pw, ph, ext)
    return jobs, meta


def dim_h(ax, x0, x1, y, text, ext_from=None, color=INK, fs=8.5):
    ax.annotate("", xy=(x0, y), xytext=(x1, y),
                arrowprops=dict(arrowstyle="<|-|>", lw=0.8, color=color, shrinkA=0, shrinkB=0,
                                mutation_scale=7))
    ax.text((x0 + x1) / 2, y + 22, text, ha="center", va="bottom", fontsize=fs, color=color,
            bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.85))
    if ext_from is not None:
        for x, y0 in zip((x0, x1), ext_from):
            ax.plot([x, x], [y0, y], lw=0.5, color=color, alpha=0.6)


def dim_v(ax, x, y0, y1, text, ext_from=None, color=INK, fs=8.5, side="right"):
    ax.annotate("", xy=(x, y0), xytext=(x, y1),
                arrowprops=dict(arrowstyle="<|-|>", lw=0.8, color=color, shrinkA=0, shrinkB=0,
                                mutation_scale=7))
    dx = 30 if side == "right" else -30
    ax.text(x + dx, (y0 + y1) / 2, text, ha="left" if side == "right" else "right", va="center",
            rotation=90, fontsize=fs, color=color, bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.85))
    if ext_from is not None:
        for y, x0 in zip((y0, y1), ext_from):
            ax.plot([x0, x], [y, y], lw=0.5, color=color, alpha=0.6)


def callout(ax, x, y, n, dx=0, dy=0):
    ax.plot([x, x + dx], [y, y + dy], lw=0.7, color=RULE)
    ax.add_patch(Circle((x + dx, y + dy), 62, fc=RULE, ec="white", lw=1.0, zorder=5))
    ax.text(x + dx, y + dy, str(n), ha="center", va="center", color="white", fontsize=8,
            fontweight="bold", zorder=6)


FEATURES = [
    "Cephalic-fin horns frame the mouth (contrast colour)",
    "Mouth: full-width intake between the horns",
    "Five gill-slit louvres over each front wheel (mandatory openings)",
    "Pectoral leading edge with light blade, open wheel-well inlet below",
    "Dorsal canopy hump (windscreen + side glass)",
    "Shoulder chevrons (manta dorsal markings)",
    "Engine-cover fin rising into a tail spike",
    "Crescent trailing edge with pectoral-fin tips",
    "Crescent rear wing bridging the fin tips (optional part)",
]


def drawing_sheet(key, meta, report, build):
    v = build.variant
    r = v.rules
    d = build.design
    fig = plt.figure(figsize=(16.5, 11.7), dpi=150)  # A3 landscape
    gs = fig.add_gridspec(3, 3, height_ratios=[0.86, 1.0, 0.62], width_ratios=[1.0, 1.0, 0.92],
                          left=0.03, right=0.985, top=0.95, bottom=0.03, hspace=0.12, wspace=0.06)
    ax_side = fig.add_subplot(gs[0, :2])
    ax_top = fig.add_subplot(gs[1, :2])
    ax_front = fig.add_subplot(gs[0, 2])
    ax_back = fig.add_subplot(gs[1, 2])
    ax_info = fig.add_subplot(gs[2, :])
    for ax, view in ((ax_side, "side"), (ax_top, "top"), (ax_front, "front"), (ax_back, "back")):
        pw, ph, ext = meta[view]
        img = Image.open(TMP / f"{key}_ortho_{view}.png").convert("RGB")
        ax.imshow(np.asarray(img), extent=ext, origin="upper", interpolation="lanczos")
        ax.set_xlim(ext[0], ext[1])
        ax.set_ylim(ext[2], ext[3])
        ax.set_aspect("equal")
        ax.axis("off")

    V = np.vstack([build.parts[k].vertices for k in ("top_shell_skin", "dorsal_fin", "rear_wing",
                                                      "endplates", "mirrors")])
    x_min, x_max = V[:, 0].min(), V[:, 0].max()
    z_max = V[:, 2].max()

    # ---- side view ---------------------------------------------------------
    ax = ax_side
    ax.add_patch(Rectangle((x_min, 0), r.max_length, r.max_height, fill=False, ls=(0, (6, 4)),
                           ec=RULE, lw=0.9))
    ax.text(x_min + r.max_length - 10, r.max_height + 18, f"{r.key.upper()} box  {r.max_length:.0f} x "
            f"{r.max_height:.0f} mm", color=RULE, fontsize=8, ha="right", va="bottom")
    ax.plot([x_min - 300, x_max + 300], [GROUND_Z, GROUND_Z], color=INK, lw=0.8)
    ax.plot([x_min - 300, x_max + 300], [0, 0], color=INK, lw=0.5, ls=":")
    ax.text(x_min - 280, 8, "reference plane", fontsize=7, color=INK, va="bottom")
    for xw, zw, tyre in ((0.0, v.wheel_z_front, r.front_tyre), (v.x_rear_axle, v.wheel_z_rear, r.rear_tyre)):
        ax.add_patch(Circle((xw, zw), tyre.radius, fill=False, ec="#7a8794", lw=0.8, ls="--"))
        ax.plot([xw], [zw], "+", color="#7a8794", ms=6)
        ax.text(xw, zw - tyre.radius - 40, tyre.code, ha="center", va="top", fontsize=7, color="#5a6774")
    yb = GROUND_Z - 150
    dim_h(ax, x_min, x_max, yb - 140, f"overall {x_max - x_min:.0f}", ext_from=(300, 300))
    dim_h(ax, 0, v.x_rear_axle, yb, f"wheelbase {v.wheelbase:.0f}", ext_from=(v.wheel_z_front, v.wheel_z_rear))
    dim_h(ax, x_min, 0, yb, f"{-x_min:.0f}")
    dim_h(ax, v.x_rear_axle, x_max, yb, f"{x_max - v.x_rear_axle:.0f}")
    dim_v(ax, x_max + 170, 0, z_max, f"{z_max:.0f}", ext_from=(x_max, x_max))
    ax.set_title("SIDE (left-hand side, front to the left)", fontsize=9, loc="left", color=INK)
    callout(ax, d.v.mx(-960.0), 440, 1, dx=-60, dy=330)
    callout(ax, 1750, 1040, 5, dx=-180, dy=180)
    callout(ax, 3000, 1010, 7, dx=0, dy=190)

    # ---- top view ----------------------------------------------------------
    ax = ax_top
    for s in (1, -1):
        ax.plot([x_min - 200, x_max + 200], [s * r.max_width / 2] * 2, color=RULE, lw=0.8, ls=(0, (6, 4)))
    for xw, tyre, track in ((0.0, r.front_tyre, v.front_track), (v.x_rear_axle, r.rear_tyre, v.rear_track)):
        for s in (1, -1):
            ax.add_patch(Rectangle((xw - tyre.radius, s * track / 2 - tyre.width / 2), 2 * tyre.radius,
                                   tyre.width, fill=False, ec="#7a8794", lw=0.7, ls="--"))
    dim_v(ax, x_max + 170, -r.max_width / 2, r.max_width / 2,
          f"{report['measured']['width']:.0f} (max {r.max_width:.0f})")
    dim_v(ax, -650, -v.front_track / 2, v.front_track / 2, f"track {v.front_track:.0f}", side="left")
    dim_v(ax, v.x_rear_axle + 420, -v.rear_track / 2, v.rear_track / 2, f"track {v.rear_track:.0f}")
    ax.set_title("PLAN (front to the left)", fontsize=9, loc="left", color=INK)
    callout(ax, d.v.mx(-970.0), 478, 1, dx=-120, dy=300)
    callout(ax, 114, 860, 3, dx=0, dy=330)
    callout(ax, d.v.mx(-700.0), -700, 4, dx=-150, dy=-300)
    callout(ax, 1400, 790, 6, dx=0, dy=300)
    callout(ax, d.v.mx(3880.0), 560, 8, dx=280, dy=200)
    callout(ax, d.v.mx(3820.0), -600, 9, dx=340, dy=-250)

    # ---- front / rear views --------------------------------------------------
    for ax, title, s_y in ((ax_front, "FRONT", -1), (ax_back, "REAR", 1)):
        ax.plot([-1150, 1150], [GROUND_Z, GROUND_Z], color=INK, lw=0.8)
        for (tyre, track, zw) in ((r.front_tyre, v.front_track, v.wheel_z_front),) if title == "FRONT" else \
                ((r.rear_tyre, v.rear_track, v.wheel_z_rear),):
            for s in (1, -1):
                ax.add_patch(Rectangle((s * track / 2 - tyre.width / 2, zw - tyre.radius), tyre.width,
                                       2 * tyre.radius, fill=False, ec="#7a8794", lw=0.7, ls="--"))
        ax.add_patch(Rectangle((-r.max_width / 2, 0), r.max_width, r.max_height, fill=False,
                               ls=(0, (6, 4)), ec=RULE, lw=0.8))
        dim_h(ax, -r.max_width / 2, r.max_width / 2, GROUND_Z - 150, f"{r.max_width:.0f}")
        ax.set_title(title, fontsize=9, loc="left", color=INK)
    callout(ax_front, 0, 190, 2, dx=0, dy=-330)

    # ---- info block -----------------------------------------------------------
    ax = ax_info
    ax.axis("off")
    m = report["metrics"]
    title = f"MANTA  |  top shell  |  {r.name} package"
    ax.text(0.0, 0.98, title, fontsize=15, fontweight="bold", color=INK, va="top", transform=ax.transAxes)
    ax.text(0.0, 0.83, "manta-ray inspired upper bodywork  -  dimensions in mm, reference plane z = 0  -  "
            "concept design, not homologated", fontsize=8.5, color="#55616d", va="top", transform=ax.transAxes)
    rows = [("Length / width / height", f"{report['measured']['length']:.0f} / {report['measured']['width']:.0f} / "
             f"{report['measured']['height']:.0f}  (max {r.max_length:.0f} / {r.max_width:.0f} / {r.max_height:.0f})"),
            ("Wheelbase / tracks", f"{v.wheelbase:.0f} / {v.front_track:.0f} F, {v.rear_track:.0f} R"),
            ("Tyres", f"{r.front_tyre.code} F, {r.rear_tyre.code} R  (710 mm OD)"),
            ("Frontal area (shell + wing)", f"{m['frontal_area_m2']:.2f} m2"),
            ("Skin area / est. mass", f"{m['skin_area_m2']:.1f} m2  /  ~{m['skin_area_m2'] * 2.2:.0f} kg at 2.2 kg/m2 CFRP"),
            ("Gill louvres per side", f"{m['louvre_area_per_side_cm2']:.0f} cm2 (5 slots)"),
            ("Engine-cover fin", f"{m['fin_side_area_m2']:.2f} m2 side area"),
            ("Regulation checks", f"{sum(c['pass'] for c in report['checks'])}/{len(report['checks'])} pass "
             "(see exports/<class>/report.json)")]
    for i, (k, val) in enumerate(rows):
        y = 0.66 - i * 0.085
        ax.text(0.0, y, k, fontsize=8.5, color="#55616d", transform=ax.transAxes, va="top")
        ax.text(0.17, y, val, fontsize=8.5, color=INK, transform=ax.transAxes, va="top")
    ax.text(0.53, 0.83, "Manta-ray design language", fontsize=10, fontweight="bold", color=INK,
            transform=ax.transAxes, va="top")
    for i, f in enumerate(FEATURES, start=1):
        y = 0.71 - (i - 1) * 0.075
        ax.add_patch(Circle((0.535, y - 0.022), 0.012, transform=ax.transAxes, fc=RULE, ec="none"))
        ax.text(0.535, y - 0.022, str(i), transform=ax.transAxes, color="white", fontsize=7, ha="center",
                va="center", fontweight="bold")
        ax.text(0.55, y, f, fontsize=8.5, color=INK, transform=ax.transAxes, va="top")
    fig.savefig(OUT / f"{key}_drawing.png", dpi=150, facecolor="white")
    plt.close(fig)


def side_comparison(builds):
    fig, ax = plt.subplots(figsize=(14, 4.6), dpi=150)
    colors = {"lmdh": "#1f6fb2", "lmh": "#d2691e"}
    for key, b in builds.items():
        parts = [b.parts[k] for k in ("top_shell_skin", "dorsal_fin", "rear_wing", "endplates")]
        V = np.vstack([p.vertices for p in parts])
        res = 4.0
        x0, z0 = -1100.0, -50.0
        img = Image.new("1", (int(5400 / res), int(1300 / res)), 0)
        from PIL import ImageDraw
        dr = ImageDraw.Draw(img)
        for p in parts:
            T = (p.vertices[p.faces][:, :, [0, 2]] - [x0, z0]) / res
            for tri in T:
                dr.polygon([tuple(q) for q in tri], fill=1)
        mask = np.array(img, float)
        xs = x0 + res * np.arange(mask.shape[1])
        zs = z0 + res * np.arange(mask.shape[0])
        ax.contour(xs, zs, mask, levels=[0.5], colors=[colors[key]], linewidths=1.4)
        r = b.variant.rules
        ax.add_patch(Rectangle((V[:, 0].min(), 0), r.max_length, r.max_height, fill=False,
                               ec=colors[key], lw=0.8, ls=(0, (5, 4))))
        ax.plot([], [], color=colors[key], label=f"{r.name}: {np.ptp(V[:, 0]):.0f} x {V[:, 2].max():.0f} mm "
                f"(box {r.max_length:.0f} x {r.max_height:.0f})")
    ax.axhline(0, color=INK, lw=0.5, ls=":")
    ax.set_aspect("equal")
    ax.set_xlim(-1150, 4250)
    ax.set_ylim(-60, 1250)
    ax.legend(loc="upper left", fontsize=8.5, frameon=False)
    ax.set_xlabel("x from front axle [mm]")
    ax.set_ylabel("z above reference plane [mm]")
    ax.set_title("Same MANTA design language, packaged to two rule boxes (side silhouettes)", fontsize=10,
                 loc="left")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(OUT / "lmdh_vs_lmh_side.png", facecolor="white")
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-photos", action="store_true")
    ap.add_argument("--skip-drawings", action="store_true")
    args = ap.parse_args(argv)
    OUT.mkdir(exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    builds = {k: build_variant(VARIANTS[k]) for k in ("lmdh", "lmh")}
    with http_server(ROOT) as port:
        if not args.skip_photos:
            photo = []
            for k in ("lmdh", "lmh"):
                photo += [(f"{k}_hero", f"variant={k}&view=hero"),
                          (f"{k}_rear", f"variant={k}&view=rear"),
                          (f"{k}_display", f"variant={k}&view=hero&stand=1"),
                          (f"{k}_display_rear", f"variant={k}&view=rear&stand=1")]
            photo += [("lmdh_front", "variant=lmdh&view=low"),
                      ("lmdh_top", "variant=lmdh&view=top&context=0"),
                      ("lmdh_clay", "variant=lmdh&view=hero&look=clay"),
                      ("lmdh_nose", "variant=lmdh&context=0&appendages=0&cam=-1.75,1.25,2.35"
                                    "&target=0,0.42,0.15&fov=34")]
            render(port, 1800, 1000, photo)
            for name, _ in photo:
                to_jpg(name)
        if not args.skip_drawings:
            jobs, metas = [], {}
            for k, b in builds.items():
                V = b.shell.vertices
                xc = 0.5 * (V[:, 0].min() + V[:, 0].max())
                j, meta = ortho_jobs(k, xc)
                metas[k] = meta
                jobs += j
            for view in ORTHO:
                pw, ph = ORTHO[view][:2]
                render(port, pw, ph, [jb for jb in jobs if jb[0].endswith("_" + view)])
            for k, b in builds.items():
                report = json.loads((ROOT / "exports" / k / "report.json").read_text())
                drawing_sheet(k, metas[k], report, b)
            side_comparison(builds)
    print("figures written to", OUT)


if __name__ == "__main__":
    main()
