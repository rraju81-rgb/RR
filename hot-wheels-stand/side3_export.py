"""Exports + previews + BOM for the side rack v3: python3 side3_export.py [N ...]"""
import sys, os, json
import numpy as np
import trimesh
from PIL import Image, ImageDraw
import side3_cad as C
import raster

COLS = [(0.85, 0.2, 0.15), (0.15, 0.45, 0.85), (0.95, 0.6, 0.1), (0.2, 0.65, 0.35), (0.6, 0.25, 0.7), (0.9, 0.85, 0.2)]
tw = lambda p: np.column_stack([p[:, 0], -p[:, 2], p[:, 1]])


def color(n):
    if n.startswith("card"): return COLS[int(n[4:]) % 6]
    if n.startswith("arm"): return (0.25, 0.55, 0.75)
    if n.startswith("b1"): return (0.80, 0.82, 0.86)
    if n.startswith("b2"): return (0.55, 0.60, 0.68)
    if n == "frame": return (0.30, 0.31, 0.35)
    return (0.10, 0.10, 0.12)


def items(R, P, phi, cards=True):
    pm = C.posed(R, P, phi)
    it = [(m, color(n)) for n, m in pm.items() if cards or not n.startswith("card")]
    for sg in (1, -1):
        it.append((C.spring_mesh(R, phi, sg), (0.95, 0.5, 0.1)))
    return it


def view(R, P, phi, elev, azim, size, scale, center=None):
    im, c = raster.render(items(R, P, phi), tw, elev, azim, size, scale, center)
    return raster.crop(im), c


def bom(N, q):
    sp, st, sz = q["spring"], q["structural"], q["print_sizes_mm"]
    L0 = 60.0
    return f"""# {N}-stall rack: parts and hardware
**3 printed parts** (2 designs): `frame.stl` (x1), `swing_R.stl` and `swing_L.stl` (mirror images). All three are already in print orientation, no supports.
Printed sizes: frame {sz['frame'][0]:.0f} x {sz['frame'][1]:.0f} x {sz['frame'][2]:.0f} mm, each swing {sz['swing'][0]:.0f} x {sz['swing'][1]:.0f} x {sz['swing'][2]:.0f} mm.
Filament about {q['filament_g']['frame']:.0f} g (frame) + 2 x {q['filament_g']['swing_each']:.0f} g (swings), PETG.

| Hardware | Qty | Notes |
|---|---|---|
| M4 x 20 button-head bolt (ISO 7380) | 4 | the four hinges (H and F, left and right) |
| M4 hex bolt x 25 | 2 | spring studs: head sits in the hex pocket on the inside of the swing bar |
| M4 nylon-lock nut | 6 | 4 hinges + 2 studs |
| M4 washer | 8 | one each side of every cheek |
| Dowel 6 mm x 134 mm (wood or aluminium) | 1 | ties the two swings together; glue into both bars (the holes are 6.3 mm) |
| Extension spring | 2 | rate {sp['k_N_per_mm']:.4f} N/mm, free length about {L0:.0f} mm hook to hook, initial tension about {sp['k_N_per_mm'] * L0:.2f} N. Force {sp['force_closed_N_each']:.2f} N closed to {sp['force_open_N_each']:.2f} N open. Hooks on the stud and on the frame tab (anchor height {q['spring_anchor_height']:.0f} mm) |
| Magnet 6 x 2 mm | 4 | pockets in the swing bars and the frame fingers (N-S facing) |
| Wall screw M4 + plug | 10 | 5 per side through the frame plate |

Open reach (how far the swings stick out of the wall plane): {q['open_reach']:.0f} mm. Moving mass with 40 g cards: {q['mass_moving_g']:.0f} g.

**Assembly**
1. Screw the frame to the wall (level, bottom of the cheeks at your chosen height).
2. Glue the dowel into the two swing bars (hole at the bottom, below the hinge) so the swings are a pair.
3. Fit the hinge bolts from the outside: washer, cheek, washer, swing bar, nylock nut. Tighten snug, then back off 1/8 turn so the swing moves freely under its own weight.
4. Fit the spring studs and hook the springs; drop in the magnets.
5. Slide each card into its cradle groove from the front edge.
"""


def export(N):
    R, P = C.build(N)
    q = json.load(open(f"side3/qa_{N}.json"))
    d = f"side3/N{N}"; os.makedirs(d + "/assembly", exist_ok=True)
    C.print_frame(R).export(f"{d}/frame.stl")
    C.print_swing(R, 1).export(f"{d}/swing_R.stl")
    C.print_swing(R, -1).export(f"{d}/swing_L.stl")
    for nm, phi in (("closed", 0), ("open", 90)):
        pm = C.posed(R, P, phi)
        trimesh.util.concatenate([m for n, m in pm.items() if not n.startswith("card")]).export(f"{d}/assembly/assembly_{nm}.stl")
    open(f"{d}/BOM.md", "w").write(bom(N, q))
    s = 1.35 if N <= 3 else (1.1 if N == 4 else 0.95)
    view(R, P, 0, 6, -28, (700, 1100), s)[0].save(f"side3/preview_N{N}_closed.png")
    view(R, P, 90, 24, -38, (1100, 900), s)[0].save(f"side3/preview_N{N}_open.png")
    ims = [view(R, P, p, 0, 90, (520, 800), s)[0] for p in (0, 30, 60, 90)]
    h = max(i.height for i in ims)
    out = Image.new("RGB", (sum(i.width for i in ims) + 30, h + 40), "white"); x, dr = 0, ImageDraw.Draw(out)
    for i, p in zip(ims, (0, 30, 60, 90)):
        out.paste(i, (x, 40 + h - i.height)); dr.text((x + 8, 12), f"swing {p} deg (side view, wall on the left)", fill=(20, 20, 20)); x += i.width + 10
    out.save(f"side3/preview_N{N}_poses.png")
    # print layout sheet
    fr, sw = C.print_frame(R), C.print_swing(R, 1)
    sheet = []
    for m, nm in ((fr, "frame"), (sw, "swing")):
        sheet.append((m.copy().apply_transform(np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]])), nm))
    print("exported", N)


def make_gif(N, step=6):
    R, P = C.build(N)
    s = 1.0 if N >= 4 else 1.25
    cs = [raster.render(items(R, P, p), tw, 20, -38, (1000, 900), s)[1] for p in (0, 90)]
    center = ((cs[0][0] + cs[1][0]) / 2, (cs[0][1] + cs[1][1]) / 2)
    seq = list(range(0, 91, step)) + [90] * 4 + list(range(90, -1, -step)) + [0] * 3
    frames = []
    for p in seq:
        im, _ = raster.render(items(R, P, p), tw, 20, -38, (1000, 900), s, center=center)
        ImageDraw.Draw(im).text((12, 10), f"{N} stalls, swing {p} deg", fill=(20, 20, 20))
        frames.append(im.convert("P", palette=Image.ADAPTIVE))
    frames[0].save(f"side3/side3_N{N}_open.gif", save_all=True, append_images=frames[1:], duration=110, loop=0)


if __name__ == "__main__":
    for N in [int(a) for a in sys.argv[1:] if a.isdigit()] or [1, 2, 3, 4, 5, 6]:
        export(N)
    if "--gif" in sys.argv:
        make_gif(3)
