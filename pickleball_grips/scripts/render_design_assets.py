#!/usr/bin/env python3
"""Richer per-design artwork for the ten design brochures (headless Chromium + three.js, plus brochure_geometry).

per design -> brochure/assets/<id>/
    hero_a..d.png   transparent full-length renders, four turns (az 32, 125, 215, 305)   [a, b come from render_brochure_assets.py]
    surface.png     mid-body close-up                                                      [from render_brochure_assets.py]
    surface2.png    lower-body close-up in raking light
    rim.png         neck, rim and bore seen from above
    cutaway.png     quadrant cutaway - the solid wall as a section
    swatch.png      the unrolled surface as a lit relief
    row.png         the grip in all ten PLA colours (orthographic, transparent)
    paddle.png      the grip fitted to an illustrative generic paddle (transparent)
and brochure/assets/paddle.bin (the shared paddle mesh).

usage: python3 render_design_assets.py [--only 01 07 ...] [--skip hero rim surface2 cutaway swatch row paddle]
"""
import argparse
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_grips as R  # noqa: E402
import brochure_geometry as G  # noqa: E402
from designs import DESIGNS  # noqa: E402
from render_brochure_assets import PALETTE, COLOUR, ASSIGN, PLA, BG_TILE, DARK_EXP, pack_white  # noqa: E402

OUT = R.ROOT / "brochure" / "assets"
DARK = {"06_carbon_matrix"}                    # black PLA: lift the exposure a little in the renders
SWATCH_TINT = {"06_carbon_matrix": "9AA3B0"}         # black PLA would make the unrolled picture unreadable
SWATCH_EXAG = {"09_ergo_contour": 4.0}              # gentle relief: exaggerate the slopes (the brochure says so)
TURNS = {"a": 32, "b": 125, "c": 215, "d": 305}


def main(only=None, skip=()):
    from playwright.sync_api import sync_playwright
    three = R.HERE / "node_modules" / "three"
    if not three.exists():
        sys.exit("run `npm install` in scripts/ first")
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    (tmp / "three").symlink_to(three, target_is_directory=True)
    shutil.copy(R.HERE / "render_page.html", tmp / "index.html")
    if "paddle" not in skip:
        G.make_paddle(OUT / "paddle.bin")
    shutil.copy(OUT / "paddle.bin", tmp / "paddle.bin")
    srv = R.serve(tmp)
    port = srv.server_address[1]
    r_, m_, c_ = PLA
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=R.CHROMIUM, args=["--use-gl=angle", "--use-angle=swiftshader",
                                                                "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])

        def shot(mesh, query, w, h, out, transparent=False, exp=1.0):
            pg = b.new_page(viewport={"width": w, "height": h})
            pg.on("console", lambda msg: print("  [js]", msg.text) if msg.type == "error" and "404" not in msg.text else None)
            pg.goto(f"http://127.0.0.1:{port}/index.html?mesh={mesh}.bin&w={w}&h={h}&rough={r_}&metal={m_}&clear={c_}&tm=neutral&exp={exp}&{query}")
            pg.wait_for_function("window.__done === true", timeout=300000)
            pg.locator("canvas").screenshot(path=str(out), omit_background=transparent)
            pg.close()

        for name, label, _ in DESIGNS:
            if only and not any(name.startswith(o) for o in only):
                continue
            d = OUT / name
            d.mkdir(parents=True, exist_ok=True)
            tint = COLOUR[ASSIGN[name]]
            pack_white(name, tmp / f"{name}.bin")
            dark = name in DARK
            if "hero" not in skip:
                for tag in ("c", "d"):
                    shot(name, f"mode=hero&fill=0.56&el=13&az={TURNS[tag]}&tint={tint}&bg=none&sh=0", 1100, 1900, d / f"hero_{tag}.png", True, exp=DARK_EXP.get(name, 1.0))
            if "swatch" not in skip:
                G.make_swatch(name, SWATCH_TINT.get(name, tint), d / "swatch.png", exag=SWATCH_EXAG.get(name, 1.0))
            if "rim" not in skip:
                shot(name, f"mode=macro&zc=126&span=54&az=25&el=58&tx=0&tint={tint}&bg={BG_TILE}", 1000, 1000, d / "rim.png", exp=1.5 if dark else 1.0)
            if name.startswith("07") and "surface" not in skip:                 # windows: a dark-backed close-up for the dark page
                shot(name, f"mode=macro&zc=62&span=34&az=18&el=8&tx=0&tint={tint}&bg=1A212C", 1000, 1000, d / "surface_dark.png")
            if "surface2" not in skip:
                shot(name, f"mode=macro&zc=50&span=30&az=-55&el=3&tx=0&tint={tint}&bg={BG_TILE}", 1000, 1000, d / "surface2.png", exp=1.7 if dark else 1.0)
            if "cutaway" not in skip:
                G.make_cutaway(name, tmp / f"{name}_cut.bin")
                shot(f"{name}_cut", f"mode=hero&fill=0.56&el=8&az=68&tint={tint}&bg=none&sh=0", 1100, 1922, d / "cutaway.png", True, exp=1.4 if dark else 1.0)
            if "row" not in skip:
                tints = ",".join(h for _, h in PALETTE)
                shot(name, f"mode=row&tints={tints}&gap=50&scale=7&az=32&el=9&bg=none", 3640, 1130, d / "row.png", True)
            if "paddle" not in skip:
                shot(name, f"mode=macro&mesh2=paddle.bin&fov=18&zc=132&span=282&az=24&el=4&tx=0&tint={tint}&bg=none&rough2=0.38&clear2=0.55",
                     1100, 1922, d / "paddle.png", True, exp=1.25 if dark else 1.0)
            print("design assets", name, flush=True)
        b.close()
    srv.shutdown()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--skip", nargs="*", default=[])
    a = ap.parse_args()
    main(a.only, a.skip)
