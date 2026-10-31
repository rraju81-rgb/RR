#!/usr/bin/env python3
"""Build the great hammerhead shark sculpture.

    python3 build.py                     # both styles, final quality (0.2 mm voxels)
    python3 build.py --res 0.5           # quick draft
    python3 build.py --style pure        # only the anatomical shark
    python3 build.py --bend 0            # straight (no swimming curve)

Outputs (./output):
    hammerhead_shark.stl              anatomical shark, single watertight solid
    hammerhead_shark_f1.stl           same shark with F1 cues (cockpit, halo, ...)
    display_stand.stl                 engraved plinth + post with locating peg
    hammerhead_shark_on_stand.stl     shark fused onto the stand (one-piece print)
    *_display.glb                     full-colour previews (shark + stand)
    *_preview.ply                     colour-painted shark meshes (not committed)
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np
import manifold3d as m3d
import trimesh
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D  # noqa: E402
import sdf  # noqa: E402

BELLY = (238, 236, 228)
PALETTES = {
    "pure": {"top": (100, 106, 102), D.EYE: (116, 96, 38), D.PUPIL: (12, 12, 12), D.GILL: (66, 36, 40),
             D.MOUTH: (112, 46, 56), D.TEETH: (248, 246, 238), D.NOSTRIL: (58, 58, 56)},
    "f1": {"top": (92, 112, 130), D.EYE: (236, 176, 32), D.PUPIL: (12, 12, 12), D.GILL: (60, 20, 26),
           D.MOUTH: (112, 46, 56), D.TEETH: (248, 246, 238), D.NOSTRIL: (58, 58, 56),
           D.CARBON: (34, 36, 40), D.HALO: (60, 64, 70), D.HELMET: (252, 204, 24), D.VISOR: (20, 26, 38),
           D.INTAKE: (10, 10, 12), D.ACCENT: (255, 104, 16)},
}

STAND_CLEARANCE = 14.0   # gap between the lowest fin tip and the base
BASE_H = 5.0
BASE_RX, BASE_RY = 60.0, 38.0
PEG_R, SOCKET_R, PEG_LEN, SOCKET_DEPTH = 1.9, 2.1, 5.0, 5.6
NAMEPLATE = (("GREAT HAMMERHEAD", 4.6, False), ("Sphyrna mokarran", 3.4, True))
ENGRAVE = 0.6
STAND_RGB = (40, 42, 46)


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


# ------------------------------------------------------------- geometry
def swim_bend(v, tail=12.0, head=2.5):
    """Bend the straight model along a swimming curve (carangiform).

    The spine is displaced sideways by c(x): the tail swings by ``tail`` mm,
    the head turns slightly the other way.  Cross-sections stay normal to
    the spine.
    """
    x0, x1, xn = 185.0, 205.0, D.TL
    x = v[:, 0]
    c = np.zeros_like(x)
    dc = np.zeros_like(x)
    m = x < x0
    c[m] = tail * ((x0 - x[m]) / x0) ** 2
    dc[m] = -2.0 * tail * (x0 - x[m]) / x0**2
    m = x > x1
    c[m] = -head * ((x[m] - x1) / (xn - x1)) ** 2
    dc[m] = -2.0 * head * (x[m] - x1) / (xn - x1) ** 2
    th = np.arctan(dc)
    out = v.copy()
    out[:, 0] = x - v[:, 1] * np.sin(th)
    out[:, 1] = c + v[:, 1] * np.cos(th)
    return out


def manifold_from(verts, faces):
    return m3d.Manifold(m3d.Mesh(vert_properties=np.ascontiguousarray(verts, np.float32),
                                 tri_verts=np.ascontiguousarray(faces, np.uint32)))


def to_trimesh(man):
    m = man.to_mesh()
    return trimesh.Trimesh(np.asarray(m.vert_properties)[:, :3], np.asarray(m.tri_verts), process=False)


def report(name, man):
    tm = to_trimesh(man)
    lo, hi = tm.bounds
    log(f"{name}: {man.num_tri()} tris, watertight={tm.is_watertight}, shells={len(man.decompose())}, "
        f"volume={man.volume() / 1000:.1f} cm3, size={np.round(hi - lo, 1)} mm")
    return tm


# ---------------------------------------------------------------- paint
def paint(verts, faces, vlab, style):
    pal = PALETTES[style]
    tm = trimesh.Trimesh(verts, faces, process=False)
    n = tm.vertex_normals
    x, z, nz = verts[:, 0], verts[:, 2], n[:, 2]
    zline = np.interp(x, [0, 40, 70, 120, 180, 215, 240], [12.0, 6.0, 0.6, 0.2, 0.0, -0.6, -1.2])
    t_skin = 0.5 + 0.45 * (z - zline) + 1.1 * nz
    t_fin = 0.5 + 0.04 * (z - zline) + 1.8 * nz
    t_head = 0.5 + 0.30 * (z - D.head_mid_z(verts[:, 1])) + 1.8 * nz
    t_vfin = 0.12 + 0.45 * np.clip(nz, 0, None)            # pelvic / anal fins: pale
    t = np.select([vlab == D.FIN, vlab == D.HEAD, vlab == D.VFIN], [t_fin, t_head, t_vfin], t_skin)
    t = np.clip(t, 0.0, 1.0)
    t = t * t * (3 - 2 * t)
    top, bel = np.array(pal["top"], float), np.array(BELLY, float)
    cols = (bel[None] * (1 - t[:, None]) + top[None] * t[:, None]).astype(np.uint8)
    for lab, col in pal.items():
        if isinstance(lab, int) and lab not in D.SKIN_LABELS:
            cols[vlab == lab] = col
    tm.visual.vertex_colors = np.hstack([cols, np.full((len(cols), 1), 255, np.uint8)])
    return tm


# ---------------------------------------------------------------- stand
def support_point(man):
    """Centre of mass (x, y) and the belly height directly beneath it."""
    tm = to_trimesh(man)
    com = tm.center_mass
    hits, _, _ = tm.ray.intersects_location([[com[0], com[1], -200.0]], [[0, 0, 1]])
    zb = float(hits[:, 2].min())
    return float(com[0]), float(com[1]), zb


def text_solid(text, size, depth, italic=False):
    """Extruded vector text (DejaVu Sans Bold outlines via matplotlib)."""
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath

    fp = FontProperties(family="DejaVu Sans", weight="bold", style="italic" if italic else "normal")
    polys = []
    for p in TextPath((0, 0), text, size=size, prop=fp).to_polygons():
        p = np.asarray(p, float)
        if len(p) > 1 and np.allclose(p[0], p[-1]):
            p = p[:-1]
        if len(p) >= 3:
            polys.append(p)
    cs = m3d.CrossSection(polys, m3d.FillRule.EvenOdd)
    x0, y0, x1, y1 = cs.bounds()
    cs = cs.translate((-(x0 + x1) / 2, -(y0 + y1) / 2))
    return m3d.Manifold.extrude(cs, depth)


def make_stand(px, py, z_contact):
    """Elliptical plinth with an engraved nameplate, a tapered post and a peg."""
    base = m3d.Manifold.cylinder(BASE_H, 1.0, 0.92, 200).scale((BASE_RX, BASE_RY, 1.0)).translate((px, py, 0.0))
    # nameplate faces a viewer on the +Y side (reads along -X)
    cuts = []
    for (text, size, italic), dy in zip(NAMEPLATE, (20.5, 26.6)):
        t = text_solid(text, size, ENGRAVE + 0.05, italic).rotate((0.0, 0.0, 180.0))
        cuts.append(t.translate((px, py + dy, BASE_H - ENGRAVE)))
    base = m3d.Manifold.batch_boolean([base] + cuts, m3d.OpType.Subtract)
    post_h = z_contact - BASE_H + 0.6
    post = m3d.Manifold.cylinder(post_h, 3.4, 2.7, 72).translate((px, py, BASE_H - 0.6))
    peg = m3d.Manifold.cylinder(PEG_LEN, PEG_R, PEG_R - 0.15, 48).translate((px, py, z_contact - 0.01))
    return m3d.Manifold.batch_boolean([base, post, peg], m3d.OpType.Add)


def transfer_paint(man, painted):
    """Colour a (simplified/booleaned) solid from the painted raw mesh."""
    tm = to_trimesh(man)
    _, idx = cKDTree(painted.vertices).query(tm.vertices)
    tm.visual.vertex_colors = np.asarray(painted.visual.vertex_colors)[idx]
    return tm


def solid_colour(man, rgb):
    tm = to_trimesh(man)
    tm.visual.vertex_colors = np.tile(np.array([*rgb, 255], np.uint8), (len(tm.vertices), 1))
    return tm


# ----------------------------------------------------------------- main
def build_style(style, args):
    log(f"[{style}] sampling SDF at {args.res} mm")
    prog = D.build_program(style)
    field, labels, origin = sdf.sample_half(prog, D.GRID_LO, D.GRID_HI, args.res)
    verts, faces, vlab = sdf.mesh_field(field, labels, origin, args.res)
    del field, labels
    log(f"[{style}] marching cubes: {len(faces)} tris")
    if args.bend:
        verts = swim_bend(verts, tail=args.bend)
    man = manifold_from(verts, faces)
    if man.status() != m3d.Error.NoError:
        raise SystemExit(f"mesh not manifold: {man.status()}")
    shells = man.decompose()
    solids = [p for p in shells if p.volume() > 0]
    if len(solids) != len(shells):          # fill enclosed voids (inside-out shells)
        log(f"[{style}] filled {len(shells) - len(solids)} internal void(s)")
        man = m3d.Manifold.batch_boolean(solids, m3d.OpType.Add)
    if args.simplify > 0:
        man = man.simplify(args.simplify)
    return man, paint(verts, faces, vlab, style)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=float, default=0.2, help="voxel size in mm")
    ap.add_argument("--style", choices=["pure", "f1", "both"], default="both")
    ap.add_argument("--bend", type=float, default=12.0, help="tail swing of the swimming curve (mm)")
    ap.add_argument("--simplify", type=float, default=0.01, help="simplify tolerance (mm)")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "output"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    styles = ["pure", "f1"] if args.style == "both" else [args.style]
    stand_frame = None
    for style in styles:
        shark, preview = build_style(style, args)
        name = "hammerhead_shark" if style == "pure" else "hammerhead_shark_f1"

        # display frame: lowest fin tip STAND_CLEARANCE above the base top
        lift = BASE_H + STAND_CLEARANCE - shark.bounding_box()[2]
        if stand_frame is None:
            px, py, zb = support_point(shark.translate((0, 0, lift)))
            stand_frame = (px, py, zb)
            stand = make_stand(px, py, zb)
            report("display_stand", stand)
            to_trimesh(stand).export(os.path.join(args.out, "display_stand.stl"))
            stand_painted = solid_colour(stand, STAND_RGB)
        px, py, zb = stand_frame
        shark_d = shark.translate((0, 0, lift))
        socket = m3d.Manifold.cylinder(SOCKET_DEPTH + 1.0, SOCKET_R, SOCKET_R, 48).translate((px, py, zb - 1.0))
        shark_s = shark_d - socket

        if style == "pure":
            on_stand = m3d.Manifold.batch_boolean([shark_d, make_stand(px, py, zb + 1.5)], m3d.OpType.Add)
            report("hammerhead_shark_on_stand", on_stand)
            to_trimesh(on_stand).export(os.path.join(args.out, "hammerhead_shark_on_stand.stl"))

        # print file: shark resting at z=0 (keeps the stand socket)
        bb = shark_s.bounding_box()
        tm = report(name, shark_s.translate((0, 0, -bb[2])))
        tm.export(os.path.join(args.out, f"{name}.stl"))
        # colour previews (display frame): PLY of the shark, GLB of shark + stand
        preview.apply_translation((0, 0, lift))
        painted = transfer_paint(shark_s, preview)
        painted.export(os.path.join(args.out, f"{name}_preview.ply"))
        trimesh.util.concatenate([painted, stand_painted]).export(os.path.join(args.out, f"{name}_display.glb"))
        log(f"wrote {name}.stl, {name}_preview.ply, {name}_display.glb")
    log("done")


if __name__ == "__main__":
    main()
