#!/usr/bin/env python3
"""Single-colour PLA renders for the two-page brochure (headless Chromium + three.js).

Every render is white vertex colours x one PLA tint, i.e. exactly what a one-colour print looks like.

per design -> brochure/assets/<id>/
    hero_a.png / hero_b.png   transparent full-length renders, two azimuths (32 and 125 deg)
    surface.png               square surface close-up (opaque, page-2 tile)
and one showcase design in every PLA colour -> brochure/assets/options/<colour>.png  (colour-option chips)

usage: python3 render_brochure_assets.py [--only 01 07 ...] [--skip hero surface options]
"""
import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_grips as R  # noqa: E402
from designs import DESIGNS  # noqa: E402

ROOT = R.ROOT
OUT = ROOT / "brochure" / "assets"

# the PLA colour range offered (name, hex) - generic filament colours, not a brand
PALETTE = [
    ("Ultraviolet", "7B4DDB"), ("Court Blue", "2F6FDB"), ("Teal", "1FA59B"), ("Pickle Green", "5DB83A"),
    ("Citrus Yellow", "EBCB2E"), ("Sunset Orange", "F08A24"), ("Signal Red", "D7262E"), ("Arctic White", "ECECE9"),
    ("Slate Grey", "6B7480"), ("Jet Black", "1C1E22"),
]
COLOUR = dict(PALETTE)
# which colour each design is shown in (chosen so the texture reads well in one colour)
ASSIGN = {
    "01_vortex_grip": "Ultraviolet", "02_cellular_mod": "Arctic White", "03_tessel_block": "Sunset Orange",
    "04_logic_grip": "Court Blue", "05_neuro_tread": "Signal Red", "06_carbon_matrix": "Jet Black",
    "07_voronoi_core": "Pickle Green", "08_topo_flow": "Citrus Yellow", "09_ergo_contour": "Slate Grey",
    "10_hexa_mod": "Teal",
}
SHOWCASE = "03_tessel_block"                         # the design used for the colour-option chips
PLA = (0.42, 0.0, 0.22)                              # roughness, metalness, clearcoat: semi-gloss PLA
SURF = {"09_ergo_contour": dict(zc=66, az=0, el=2, span=38, exp=1.3, look=(0.36, 0.0, 0.3)),    # smooth design: graze the light to show the flutes
        "06_carbon_matrix": dict(zc=62, az=18, el=8, exp=1.7, look=(0.30, 0.0, 0.5))}     # black PLA: lift the exposure, glossier
BG_TILE = "E9E6E1"


def pack_white(name, out):
    m = trimesh.load(ROOT / "stl" / f"{name}.stl", process=True)
    m.merge_vertices()
    V, Fc = np.asarray(m.vertices), np.asarray(m.faces)
    col = np.full((len(Fc) * 3, 3), 255, np.uint8)
    R._write_bin(out, V[Fc].reshape(-1, 3), R.corner_normals(V, Fc), col)


def main(only=None, skip=()):
    from playwright.sync_api import sync_playwright
    three = R.HERE / "node_modules" / "three"
    if not three.exists():
        sys.exit("run `npm install` in scripts/ first")
    tmp = Path(tempfile.mkdtemp())
    (tmp / "three").symlink_to(three, target_is_directory=True)
    shutil.copy(R.HERE / "render_page.html", tmp / "index.html")
    srv = R.serve(tmp)
    port = srv.server_address[1]
    r_, m_, c_ = PLA
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=R.CHROMIUM, args=["--use-gl=angle", "--use-angle=swiftshader",
                                                                "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])

        def shot(mesh, query, w, h, out, transparent=False, look=None, exp=1.0):
            rr, mm_, cc = look or (r_, m_, c_)
            pg = b.new_page(viewport={"width": w, "height": h})
            pg.on("console", lambda msg: print("  [js]", msg.text) if msg.type == "error" and "404" not in msg.text else None)
            pg.goto(f"http://127.0.0.1:{port}/index.html?mesh={mesh}.bin&w={w}&h={h}&rough={rr}&metal={mm_}&clear={cc}&tm=neutral&exp={exp}&{query}")
            pg.wait_for_function("window.__done === true", timeout=300000)
            pg.locator("canvas").screenshot(path=str(out), omit_background=transparent)
            pg.close()

        for name, label, _ in DESIGNS:
            if only and not any(name.startswith(o) for o in only):
                continue
            d = OUT / name
            d.mkdir(parents=True, exist_ok=True)
            pack_white(name, tmp / f"{name}.bin")
            tint = COLOUR[ASSIGN[name]]
            if "hero" not in skip:
                for tag, az in (("a", 32), ("b", 125)):
                    shot(name, f"mode=hero&fill=0.56&el=13&az={az}&tint={tint}&bg=none&sh=0", 1100, 1900, d / f"hero_{tag}.png", True)
            if "surface" not in skip:
                s = SURF.get(name, dict(zc=62, az=18, el=8))
                shot(name, f"mode=macro&zc={s['zc']}&span={s.get('span', 34)}&az={s['az']}&el={s['el']}&tx=0&tint={tint}&bg={BG_TILE}",
                     1000, 1000, d / "surface.png", look=s.get("look"), exp=s.get("exp", 1.0))
            print("brochure assets", name, ASSIGN[name], flush=True)
        if "options" not in skip and (not only or any(SHOWCASE.startswith(o) for o in only)):
            d = OUT / "options"
            d.mkdir(parents=True, exist_ok=True)
            pack_white(SHOWCASE, tmp / "show.bin")
            for cname, hx in PALETTE:
                shot("show", f"mode=macro&zc=72&span=56&az=24&el=8&tx=0&tint={hx}&bg={BG_TILE}", 600, 720, d / f"{cname.replace(' ', '_')}.png")
            (d / "palette.json").write_text(json.dumps(PALETTE))
            print("brochure assets: colour options", flush=True)
        b.close()
    srv.shutdown()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--skip", nargs="*", default=[])
    a = ap.parse_args()
    main(a.only, a.skip)
