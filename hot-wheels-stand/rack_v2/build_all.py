"""Builds the sale package: python3 build_all.py  -> package/{3car,5car}/ (STLs, previews, gif)"""
import os, numpy as np
import trimesh
from PIL import Image
import rack_cad as C, raster

COLS = [(0.85, 0.2, 0.15), (0.15, 0.45, 0.85), (0.95, 0.6, 0.1), (0.2, 0.65, 0.35), (0.6, 0.25, 0.7)]
tw = lambda p: np.column_stack([p[:, 0], -p[:, 2], p[:, 1]])


def color(n):
    if n.startswith("card"): return COLS[(int(n[4:]) - 1) % 5]
    if n[0] == "A": return (0.82, 0.84, 0.88)
    if n[0] == "B": return (0.60, 0.64, 0.72)
    if n == "rail": return (0.30, 0.31, 0.34)
    if n.startswith("nut") or n.startswith("bolt") or n.startswith("washer"): return (0.15, 0.15, 0.18)
    return (0.4, 0.4, 0.4)


def items(R, rail, th, cards):
    P = C.assembly(R, th, cards, rail, True)
    out = [(m, color(n)) for n, (m, g) in P.items()]
    out += [(m, (0.1, 0.1, 0.12)) for m in C.hardware_fixed(R).values()]
    return out


for N, tag in ((3, "3car"), (5, "5car")):
    R = C.Rack(N); d = f"package/{tag}"; os.makedirs(d + "/stl", exist_ok=True)
    rail = C.rail_full(R)
    # printable parts in print orientation
    C.link_A().export(f"{d}/stl/link_A_x{N}.stl")
    C.link_B().apply_translation([0, 0, -C.ZB0]) if False else None
    b = C.link_B(); b.apply_translation([0, 0, -C.ZB0]); b.export(f"{d}/stl/link_B_x{N}.stl")
    for i, s in enumerate(C.rail_segments(R)):
        s = s.copy(); s.apply_transform(np.diag([1, 1, -1, 1])); s.apply_translation([0, 0, -s.bounds[0][2]])
        s.invert() if s.volume < 0 else None
        s.export(f"{d}/stl/rail_segment_{i + 1}of{len(C.segment_cuts(R)) - 1}.stl")
    for nm, th, cards in (("open_with_cards", C.TH_MIN, True), ("folded", C.TH_MAX, False)):
        P = C.assembly(R, th, cards, rail, False)
        trimesh.util.concatenate([m for n, (m, g) in P.items()]).export(f"{d}/assembly_{nm}.stl")
    s = 1.35 if N == 3 else 0.95
    it = items(R, rail, C.TH_MIN, True)
    raster.crop(raster.render(it, tw, 8, -22, (1600, 900), s)[0]).save(f"{d}/preview_open.png")
    raster.crop(raster.render(it, tw, 0, 0, (1600, 900), s)[0]).save(f"{d}/preview_front.png")
    raster.crop(raster.render(items(R, rail, C.TH_MAX, False), tw, 8, -22, (900, 900), 1.2)[0]).save(f"{d}/preview_folded.png")
    # gif: fold animation (cards off), fixed framing
    center = None; frames = []
    for th in list(np.linspace(C.TH_MIN, C.TH_MAX, 14)) + list(np.linspace(C.TH_MAX, C.TH_MIN, 14)):
        im, c = raster.render(items(R, rail, th, False), tw, 8, -22, (1100, 700), s * 0.8, center)
        center = center or c; frames.append(Image.fromarray(im) if not isinstance(im, Image.Image) else im)
    frames[0].save(f"{d}/fold_animation.gif", save_all=True, append_images=frames[1:], duration=90, loop=0)
    print(tag, os.listdir(d))
