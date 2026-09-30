#!/usr/bin/env python3
"""Render the grip STLs to PNG (headless Chromium + three.js) and build the catalog sheet.

Colours are a *preview only*: every vertex is coloured from the design's colour map
(data/<id>_colors.npz); the STL files themselves are single-material.

usage:  python3 render_grips.py [--only 01 07 ...] [--views hero lineup detail] [--catalog]
needs:  pip install playwright trimesh numpy pillow   +   `npm install` in this folder
"""
import argparse
import functools
import http.server
import shutil
import socketserver
import struct
import sys
import tempfile
import threading
import warnings
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grip_core import Frame  # noqa: E402
from designs import DESIGNS  # noqa: E402

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CHROMIUM = "/opt/pw-browsers/chromium"

# per-design material (roughness, metalness, clearcoat) and collar/foot preview colour
LOOK = {
    "01_vortex_grip":   dict(mat=(0.42, 0.0, 0.35), collar=(150, 102, 214)),
    "02_cellular_mod":  dict(mat=(0.55, 0.0, 0.10), collar=(150, 150, 146)),
    "03_tessel_block":  dict(mat=(0.40, 0.0, 0.25), collar=(128, 128, 126)),
    "04_logic_grip":    dict(mat=(0.45, 0.0, 0.20), collar=(150, 156, 162)),
    "05_neuro_tread":   dict(mat=(0.62, 0.0, 0.05), collar=(28, 28, 30)),
    "06_carbon_matrix": dict(mat=(0.30, 0.2, 0.60), collar=(38, 38, 42)),
    "07_voronoi_core":  dict(mat=(0.40, 0.0, 0.30), collar=(138, 84, 228)),
    "08_topo_flow":     dict(mat=(0.50, 0.0, 0.10), collar=(150, 96, 60)),
    "09_ergo_contour":  dict(mat=(0.42, 0.0, 0.40), collar=(66, 66, 72)),
    "10_hexa_mod":      dict(mat=(0.48, 0.0, 0.15), collar=(118, 122, 128)),
}
INNER = np.array([46, 46, 50], np.uint8)


def color_vertices(F, V, name):
    z_rows = None
    d = np.load(ROOT / "data" / f"{name}_colors.npz")
    rgb, zr = d["rgb"], d["z"]
    S, z, off = F.locate(V)
    i = np.round(S / (F.L / F.N)).astype(int) % F.N
    j = np.clip(np.round((z - zr[0]) / (zr[1] - zr[0])).astype(int), 0, len(zr) - 1)
    c = rgb[j, i].astype(float)
    collar = np.array(LOOK[name]["collar"], float)
    w = F.zone_window(np.clip(z, zr[0], zr[-1]))
    outside = (z < zr[0]) | (z > zr[-1])
    w = np.where(outside, 0.0, w)
    c = c * w[:, None] + collar * (1 - w[:, None])
    c[off < 0.03] = INNER                        # bore / floor
    return np.clip(c, 0, 255).astype(np.uint8)


def corner_normals(V, Fc, angle=42.0):
    """Per-corner smooth normals with a crease angle: each triangle corner averages (angle-weighted)
    only the neighbouring faces within `angle` degrees of its own face, so hard edges stay crisp and
    curved surfaces stay smooth.  Returns (T*3, 3) float32 aligned with Fc.ravel()."""
    tri = V[Fc]
    e1, e2 = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
    fn = np.cross(e1, e2)
    ln = np.linalg.norm(fn, axis=1, keepdims=True)
    fn = fn / np.where(ln > 0, ln, 1)
    ang = np.empty((len(Fc), 3))
    for k in range(3):
        a, b = tri[:, (k + 1) % 3] - tri[:, k], tri[:, (k + 2) % 3] - tri[:, k]
        na, nb = np.linalg.norm(a, axis=1), np.linalg.norm(b, axis=1)
        ang[:, k] = np.arccos(np.clip(np.einsum("ij,ij->i", a, b) / np.maximum(na * nb, 1e-12), -1, 1))
    verts = Fc.ravel()
    face = np.repeat(np.arange(len(Fc)), 3)
    w = ang.ravel()
    order = np.argsort(verts, kind="stable")
    sv = verts[order]
    starts = np.r_[0, np.flatnonzero(np.diff(sv)) + 1]
    counts = np.diff(np.r_[starts, len(sv)])
    out = fn[face].astype(np.float32)                             # default: flat face normal (fan centres etc.)
    small = counts <= 24
    keep = np.repeat(small, counts)                               # corners belonging to ordinary vertices
    order_s = order[keep]
    counts_s = counts[small]
    starts_s = np.r_[0, np.cumsum(counts_s)[:-1]]
    maxd = counts_s.max()
    slot = np.arange(len(order_s)) - np.repeat(starts_s, counts_s)
    grp = np.repeat(np.arange(len(starts_s)), counts_s)
    idx = np.full((len(starts_s), maxd), -1, np.int64)
    idx[grp, slot] = order_s                                      # corner ids per vertex
    valid = idx >= 0
    cf = np.where(valid, face[np.maximum(idx, 0)], 0)
    cn = fn[cf]                                                   # (V, maxd, 3)
    cw = np.where(valid, w[np.maximum(idx, 0)], 0.0)
    cosT = np.cos(np.radians(angle))
    B = 20000
    for s0 in range(0, len(starts_s), B):
        sl = slice(s0, s0 + B)
        n, wt, vd = cn[sl], cw[sl], valid[sl]
        dots = np.einsum("vid,vjd->vij", n, n)
        mask = (dots > cosT) & vd[:, None, :] & vd[:, :, None]
        acc = np.einsum("vij,vjd->vid", mask * wt[:, None, :], n)
        acc /= np.maximum(np.linalg.norm(acc, axis=2, keepdims=True), 1e-12)
        out[idx[sl][vd]] = acc[vd]
    return out


def _write_bin(out, pos, nor, col):
    idx = np.arange(len(pos), dtype=np.uint32)
    with open(out, "wb") as f:
        f.write(struct.pack("<II", len(pos), len(idx) // 3))
        f.write(pos.astype(np.float32).tobytes())
        f.write(nor.astype(np.float32).tobytes())
        f.write(col.astype(np.uint8).tobytes())
        f.write(b"\0" * ((-f.tell()) % 4))
        f.write(idx.tobytes())


def pack_mesh(F, name, out):
    """STL -> render buffer: per-corner crease-aware normals, preview colours from the colour map."""
    m = trimesh.load(ROOT / "stl" / f"{name}.stl", process=True)
    m.merge_vertices()
    V, Fc = np.asarray(m.vertices), np.asarray(m.faces)
    col = color_vertices(F, V, name)
    _write_bin(out, V[Fc].reshape(-1, 3), corner_normals(V, Fc), col[Fc.ravel()])


def pack_mesh_3mf(name, out):
    """Pack the mesh straight from the exported 3MF (flat per-triangle print-palette colours)."""
    import re
    import zipfile
    with zipfile.ZipFile(ROOT / "3mf" / f"{name}.3mf") as z:
        xml = z.read("3D/3dmodel.model").decode()
    pal = np.array([[int(h[i:i + 2], 16) for i in (0, 2, 4)] for h in re.findall(r'<m:color color="#([0-9A-F]{6})FF"/>', xml)], np.uint8)
    V = np.array(re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', xml), float)
    T = np.array(re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)" pid="2" p1="(\d+)"', xml), int)
    faces, k = T[:, :3], T[:, 3]
    _write_bin(out, V[faces].reshape(-1, 3), corner_normals(V, faces), np.repeat(pal[k], 3, axis=0))


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(root):
    root = str(root)
    handler = functools.partial(Quiet, directory=root)
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def render(names, views, size, source="stl"):
    from playwright.sync_api import sync_playwright
    three = HERE / "node_modules" / "three"
    if not three.exists():
        sys.exit("run `npm install` in scripts/ first (three.js is needed for rendering)")
    F = Frame()
    tmp = Path(tempfile.mkdtemp())
    (tmp / "three").symlink_to(three, target_is_directory=True)
    shutil.copy(HERE / "render_page.html", tmp / "index.html")
    srv = serve(tmp)
    port = srv.server_address[1]
    (ROOT / "renders").mkdir(exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROMIUM, args=["--use-gl=angle", "--use-angle=swiftshader",
                                                                "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        for name in names:
            (pack_mesh if source == "stl" else (lambda F_, n, o: pack_mesh_3mf(n, o)))(F, name, tmp / f"{name}.bin")
            r, mt, cc = LOOK[name]["mat"]
            for v in views:
                w, h = {"hero": size, "lineup": (1400, 760), "detail": (1000, 1000)}[v]
                if v == "hero":
                    w, h = size
                pg = b.new_page(viewport={"width": w, "height": h})
                pg.on("console", lambda m: print("  [js]", m.text) if m.type == "error" else None)
                extra = "&az=28&el=10&zc=66" if v == "detail" else ""
                pg.goto(f"http://127.0.0.1:{port}/index.html?mesh={name}.bin&mode={v}&w={w}&h={h}"
                        f"&rough={r}&metal={mt}&clear={cc}{extra}")
                pg.wait_for_function("window.__done === true", timeout=240000)
                out = ROOT / "renders" / (f"{name}_{v}.png" if source == "stl" else f"{name}_3mf.png")
                pg.locator("canvas").screenshot(path=str(out))
                pg.close()
                print("rendered", out.name, flush=True)
        b.close()
    srv.shutdown()


def font(sz, bold=True):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              str(Path(__import__("matplotlib").get_data_path()) / "fonts/ttf" / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"))):
        if Path(p).exists():
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


BLURB = {
    "01_vortex_grip": "Braided over/under helical straps\nfor dynamic multi-point contact.",
    "02_cellular_mod": "Staggered stacked cells; red cells are\nrecessed pockets for swappable inserts.",
    "03_tessel_block": "Faceted triangular pyramids in\nstaggered rows for enhanced traction.",
    "04_logic_grip": "Seamlessly interlocking jigsaw\nergonomic puzzle pieces.",
    "05_neuro_tread": "Bio-inspired raised neural network\nover a dimpled adaptive base.",
    "06_carbon_matrix": "2/2 twill weave with smooth\nselective reinforcement patches.",
    "07_voronoi_core": "Voronoi rib lattice, windows cut\nthrough for weight saving and airflow.",
    "08_topo_flow": "Continuous undulating contour ridges\nmimicking wood grain and terrain.",
    "09_ergo_contour": "Palm swell, four finger flutes and a\nthumb rest for hand conformance.",
    "10_hexa_mod": "Modular hex pads on four height\nlevels, colour-coded (red = tallest).",
}


def catalog(names, suffix="hero", out_name="catalog.png", subtitle=None):
    """Two rows of five: hero renders + captions (echoes the layout of the request image)."""
    cw, ch = 560, 900
    W, Hh = cw * 5, 150 + 2 * (ch + 250)
    sheet = Image.new("RGB", (W, Hh), (233, 230, 225))
    d = ImageDraw.Draw(sheet)
    title = "PICKLEBALL PADDLE GRIPS - ONE FITMENT, TEN SURFACES"
    d.text((W // 2, 62), title, fill=(20, 20, 20), font=font(58), anchor="mm")
    d.text((W // 2, 118), subtitle or "All ten share the reference cavity (32.06 x 26.04 mm bore, 5 mm floor, 132.82 mm tall), foot flare and top taper",
           fill=(70, 70, 70), font=font(26, False), anchor="mm")
    label = {n: l for n, l, _ in DESIGNS}
    for k, name in enumerate(names):
        r, c = divmod(k, 5)
        x0, y0 = c * cw, 150 + r * (ch + 250)
        im = Image.open(ROOT / "renders" / f"{name}_{suffix}.png").convert("RGB")
        im.thumbnail((cw - 20, ch))
        sheet.paste(im, (x0 + (cw - im.width) // 2, y0))
        d.text((x0 + cw // 2, y0 + ch + 34), label[name], fill=(15, 15, 15), font=font(44), anchor="mm")
        for li, line in enumerate(BLURB[name].split("\n")):
            d.text((x0 + cw // 2, y0 + ch + 92 + li * 34), line, fill=(60, 60, 60), font=font(25, False), anchor="mm")
    out = ROOT / "renders" / out_name
    sheet.save(out)
    print("wrote", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--views", nargs="*", default=["hero", "lineup", "detail"])
    ap.add_argument("--size", nargs=2, type=int, default=[700, 1200])
    ap.add_argument("--catalog", action="store_true")
    ap.add_argument("--source", choices=["stl", "3mf"], default="stl", help="3mf: render the exported 3MF's own colours (hero only)")
    a = ap.parse_args()
    names = [n for n, _, _ in DESIGNS if not a.only or any(n.startswith(o) for o in a.only)]
    if a.source == "3mf":
        if a.views:
            render(names, ["hero"], tuple(a.size), source="3mf")
        if a.catalog:
            catalog([n for n, _, _ in DESIGNS], "3mf", "catalog_3mf.png", "Rendered from the exported .3mf files - per-triangle print-palette colours")
    else:
        if a.views:
            render(names, a.views, tuple(a.size))
        if a.catalog:
            catalog([n for n, _, _ in DESIGNS])
