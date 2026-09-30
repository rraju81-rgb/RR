#!/usr/bin/env python3
"""Render every image the specification sheets need (headless Chromium + three.js).

per grip -> specs/assets/<id>/
    hero.png      1400 x 2400   3/4 hero
    lineup.png    2800 x 1520   four-way turntable
    front.png / side.png / top.png   exact-scale orthographic views, 12 px per mm
    detail1.png   1700 x 1200   surface close-up (mid body)
    detail2.png   1700 x 1200   neck / rim / bore, raised camera
and specs/assets/<id>/ortho.json with the pixel <-> mm mapping of the three orthographic views.

usage: python3 render_spec_assets.py [--only 01 07 ...]
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
from grip_core import Frame  # noqa: E402

ROOT = R.ROOT
OUT = ROOT / "specs" / "assets"
SCALE = 12.0          # px per mm in the orthographic views
PAD = 1.5             # mm of white border around each orthographic view


def main(only=None, views=None):
    from playwright.sync_api import sync_playwright
    three = R.HERE / "node_modules" / "three"
    if not three.exists():
        sys.exit("run `npm install` in scripts/ first")
    F = Frame()
    tmp = Path(tempfile.mkdtemp())
    (tmp / "three").symlink_to(three, target_is_directory=True)
    shutil.copy(R.HERE / "render_page.html", tmp / "index.html")
    srv = R.serve(tmp)
    port = srv.server_address[1]
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=R.CHROMIUM, args=["--use-gl=angle", "--use-angle=swiftshader",
                                                                "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        for name, label, _ in DESIGNS:
            if only and not any(name.startswith(o) for o in only):
                continue
            d = OUT / name
            d.mkdir(parents=True, exist_ok=True)
            R.pack_mesh(F, name, tmp / f"{name}.bin")
            m = trimesh.load(ROOT / "stl" / f"{name}.stl", process=True)
            lo, hi = m.bounds
            ext = hi - lo
            xc, yc = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
            r, mt, cc = R.LOOK[name]["mat"]
            mat = f"&rough={r}&metal={mt}&clear={cc}"

            def shot(query, w, h, out):
                pg = b.new_page(viewport={"width": w, "height": h})
                pg.on("console", lambda msg: print("  [js]", msg.text) if msg.type == "error" and "404" not in msg.text else None)
                pg.goto(f"http://127.0.0.1:{port}/index.html?mesh={name}.bin&w={w}&h={h}{mat}&{query}")
                pg.wait_for_function("window.__done === true", timeout=300000)
                pg.locator("canvas").screenshot(path=str(out))
                pg.close()

            want = lambda v: not views or v in views
            if want("hero"):
                shot("mode=hero&fill=0.545&el=13", 1400, 2400, d / "hero.png")
            if want("lineup"):
                shot("mode=lineup&az=0&el=8", 2800, 1520, d / "lineup.png")
                # crop to the content (grips + pedestal + shadow) with a small margin
                from PIL import Image
                im = Image.open(d / "lineup.png").convert("RGB")
                a = np.asarray(im).astype(int)
                diff = np.abs(a - np.array([233, 230, 225])).sum(2) > 30
                rows, cols = np.where(diff.any(1))[0], np.where(diff.any(0))[0]
                mg = 60
                box = (max(cols.min() - mg, 0), max(rows.min() - mg, 0), min(cols.max() + mg, im.width), min(rows.max() + mg, im.height))
                im.crop(box).save(d / "lineup.png")
            if want("detail"):
                shot("mode=macro&zc=62&span=30&az=18&el=6&tx=0", 1700, 1200, d / "detail1.png")
                shot("mode=macro&zc=119&span=34&az=25&el=38&tx=0", 1700, 1200, d / "detail2.png")
            if not want("ortho"):
                print("assets", name, "(views: %s)" % ",".join(views), flush=True)
                continue
            ortho = {}
            views = {"front": (ext[0], ext[2], xc, yc, lo[2] + ext[2] / 2),      # horizontal x, vertical z
                     "side": (ext[1], ext[2], xc, yc, lo[2] + ext[2] / 2),       # horizontal y, vertical z
                     "top": (ext[0], ext[1], xc, yc, lo[2])}                     # horizontal x, vertical y
            for v, (wm, hm, cx, cy, cz) in views.items():
                W, H = int(round((wm + 2 * PAD) * SCALE)), int(round((hm + 2 * PAD) * SCALE))
                shot(f"mode=ortho&view={v}&scale={SCALE}&cx={cx}&cy={cy}&cz={cz}", W, H, d / f"{v}.png")
                ortho[v] = dict(w=W, h=H, scale=SCALE, cx=cx, cy=cy, cz=cz)
            (d / "ortho.json").write_text(json.dumps(dict(views=ortho, bbox_lo=lo.tolist(), bbox_hi=hi.tolist()), indent=1))
            print("assets", name, flush=True)
        b.close()
    srv.shutdown()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--views", nargs="*", help="subset of: hero lineup detail ortho")
    a = ap.parse_args()
    main(a.only, a.views)
