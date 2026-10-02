"""Print-ready kits for 2, 3, 4, 5 and 6 car displays.  python3 build_kits.py -> clip/kit_<N>_cars/
Each kit: wall_strip.stl (one, or two for 5-6 cars), N same-height hinge clips (hinge_clip_j0..), N ledges, two print plates
(clips standing in a row, ledges standing in a column), an assembled demo and a preview."""
import os, shutil
import numpy as np, trimesh, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import build_clip as bc
from build_clip import *

src = open("render_clip.py").read()
exec(src[src.index("def raster("):src.index("def panel(")])

base = build_strip()
for N in (2, 3, 4, 5, 6):
    d = f"clip/kit_{N}_cars"; os.makedirs(d, exist_ok=True)
    clips = [build_clip(1, j) for j in range(N)]
    ledge = build_ledge(0)
    two = N > 4                                  # 5 and 6 cars need a second strip, joined by the dovetail tongue
    strips = [base] + ([place(base, 0, 240)] if two else [])
    for f in os.listdir(d):
        if f.startswith("wall_strip"): os.remove(f"{d}/{f}")
    to_print(base, "strip_up").export(f"{d}/wall_strip.stl")
    for j, c in enumerate(clips): to_print(c, "clip").export(f"{d}/hinge_clip_j{j}.stl")
    to_print(ledge, "ledge").export(f"{d}/ledge_x{N}.stl")
    # plate 1: clips standing in a row
    row, x = [], 0.0
    for c in clips:
        p = to_print(c, "clip"); p.apply_translation([x, 0, 0]); row.append(p); x += p.extents[0] + 6
    plate1 = trimesh.util.concatenate(row); plate1.export(f"{d}/plate_clips.stl")
    # plate 2: N ledges standing, side by side along y
    col, y = [], 0.0
    for _ in range(N):
        p = to_print(ledge, "ledge"); p.apply_translation([0, y, 0]); col.append(p); y += p.extents[1] + 8
    plate2 = trimesh.util.concatenate(col); plate2.export(f"{d}/plate_ledges.stl")
    # assembled demo
    asm = list(strips)
    for j in range(N):
        yy = 20.0 + 60.0 * j
        asm += [place(clips[j], 0, yy), place(ledge_at(j, 0, True), 0, yy)]
    trimesh.util.concatenate(asm).export(f"{d}/assembled_demo.stl")
    # fit checks
    def vol(a, b):
        i = trimesh.boolean.intersection([a, b], engine="manifold"); return round(i.volume, 3) if len(i.faces) else 0
    st_of = lambda j: strips[0] if 20.0 + 60 * j + 20 <= 240 else strips[-1]
    fit = max(max(vol(place(clips[j], 0, 20.0 + 60 * j), st_of(j)), vol(place(ledge_at(j, 0, True), 0, 20.0 + 60 * j), place(clips[j], 0, 20.0 + 60 * j))) for j in range(N))
    top = 20.0 + 60 * (N - 1) + 30
    open60 = [place(ledge_at(j, 60, True), 0, 20.0 + 60 * j) for j in range(N)]
    nb = max(vol(open60[i], open60[i + 1]) for i in range(N - 1))
    print(f"{N} cars: plate1 {np.round(plate1.extents,1)} plate2 {np.round(plate2.extents,1)} top {top} mm, strips {len(strips)}  closed-fit {fit}  open60 neighbours {nb}")
    # preview
    grey, orange, dk = (0.75, 0.75, 0.78), (0.95, 0.6, 0.1), (0.3, 0.3, 0.35)
    fig, axs = plt.subplots(1, 3, figsize=(15, 6), dpi=100)
    ms = list(strips); cs = [grey] * len(strips)
    for j in range(N): ms += [place(clips[j], 0, 20.0 + 60 * j), place(ledge_at(j, 0, True), 0, 20.0 + 60 * j)]; cs += [dk, orange]
    axs[0].imshow(raster(ms, cs, 12, 28, (420, 560), [[-50, 0, -5], [130, 240 * len(strips), 70]])); axs[0].set_title(f"{N} cars, closed")
    angs = ([0, 40, 75, 20, 60, 30])[:N]
    ms = list(strips); cs = [grey] * len(strips)
    for j in range(N): ms += [place(clips[j], 0, 20.0 + 60 * j), place(ledge_at(j, angs[j], True), 0, 20.0 + 60 * j)]; cs += [dk, orange]
    axs[1].imshow(raster(ms, cs, 50, 30, (420, 560), [[-50, 0, -5], [130, 240 * len(strips), 120]])); axs[1].set_title("ledges open")
    axs[2].imshow(raster(row, [dk] * N, 28, 25, (420, 560))); axs[2].set_title("print plate: clips j0.. standing")
    for a in axs: a.axis("off")
    fig.savefig(f"{d}/preview.png", bbox_inches="tight"); plt.close(fig)
    open(f"{d}/BOM.md", "w").write(f"""# {N}-car display kit
| Part | File | Qty | Print |
|---|---|---|---|
| Wall strip (25 mm dovetail rail, 5 mm screw holes, 5 mm ratchet teeth) | wall_strip.stl | {2 if two else 1} | rear face down (flat, teeth up) |
| Hinge clip with ratchet pawl + release tab, depth j = 0..{N-1} | hinge_clip_j0..j{N-1}.stl | 1 each | standing, brim, all 36 mm tall |
| Ledge | ledge_x{N}.stl | {N} | standing |
Plates: plate_clips.stl (all clips) and plate_ledges.stl ({N} ledges) are laid out for a 256 mm bed.
Mount: screw the strip to the wall, slide each clip onto the strip from the BOTTOM end and push it up: it clicks one 5 mm step at a time and cannot slide back down. Foot of clip j at y = 20 + 60 j mm. To lower a clip, pull its release tab (top, front) forward and slide it down,
drop each ledge on the pin. Clip j0 is the lowest rack. The total height of the stack is {top:.0f} mm ({'two identical strips: push the second strip down over the two tabs of the first strip' if two else 'fits one 240 mm strip'}).
""")
