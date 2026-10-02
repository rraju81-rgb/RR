"""IKEA-style hook-in board system (peg board + keyhole hinge clip). No sliding mechanism, nothing flexes.
Usage: python3 build_board.py   -> board/*.stl, board/kit_<N>_cars/ (N = 2..6); every STL is in PRINT orientation (+z up)

  wall_strip   30 x 5 mm board strip, 240 mm long: round-headed pegs every 20 mm (like a pegboard / keyhole hanger), 5 mm countersunk screw holes,
               dovetail joint on both ends for stacking. Print rear face down, pegs up, no supports.
  hinge_clip   plate with two KEYHOLES (big round hole with a narrow slot above it). Push the clip onto two neighbouring pegs and let go:
               it drops 7 mm, the pegs sit at the top of the slots and the clip hangs there (gravity lock, like IKEA SKADIS hooks).
               To remove: lift it 7 mm and pull it off. Solid footing block + 8 mm pin for the ledge. Print standing, no supports.
  ledge        plain barrel (turns freely), 9 mm deep slot, tall back wall, low front lip, front corner supports. 10 mm longer than before.
Needs: pip install trimesh manifold3d numpy matplotlib.  Units mm.
Assembly frame: x right, y up, z out of the wall; strip front face z = 0, strip centre x = 0."""
import os, sys
import numpy as np
sys.path.insert(0, "legacy")
import trimesh
from build_simple import box, cylz, cyly, union, diff, inter, hull, prism_y, prism_z, prism_x, sphere, offset_convex, place   # geometry helpers only

# ---- card (measure these) ----
card_w, card_h, card_t, blister_h, blister_y0, blister_dx = 105, 165, 1.2, 42, 8, 12

# ---- board strip ----
strip_w, strip_h, strip_t = 30.0, 240.0, 5.0
hole_d, csk_d, hole_ys = 5.0, 9.0, (20.0, 120.0, 220.0)         # screw holes sit exactly between two pegs
dt_root, dt_tip, dt_len, z_fit = 4.0, 7.5, 7.0, 0.12             # dovetail joint
peg_ys = [30.0 + 20.0 * k for k in range(11)]                    # 30 .. 230
peg_r, peg_stem, peg_cone, peg_top, peg_head_r = 2.5, 3.9, 2.0, 0.5, 4.5   # stem, 45 degree cone under the head, flat top, head radius

# ---- clip ----
plate_z0, plate_t = 0.4, 3.0
pe = plate_z0 + plate_t
clip_y0, clip_y1 = -4.0, 64.0
plate_x0, plate_x1, neck_x1 = -22.0, 9.0, -6.0                  # upper plate / lower neck (the neck stays clear of the pegs at x = 0)
key_y = (30.0, 50.0)                                            # round hole centres (pegs 20 mm apart), above the foot
key_round, key_slot_w, key_travel, key_slot_end = 4.9, 5.6, 7.0, 2.7
foot_h = 3.5
pin_x, pin_d = -14.0, 8.0
collar_r, collar_h = 5.2, 1.2

# ---- ledge ----
ledge_h, gutter_d, slop = 12.0, 9.0, 0.3
rear_wall, front_wall = 4.0, 3.5
rear_h, front_h = 19.0, 4.0
corner_h, corner_len, corner_gap = 7.0, 9.0, 0.15
thumb_out, end_stop, wall_x0, extra_len = 8.0, 9.0, 17.0, 10.0   # extra_len: ledge is 10 mm longer
bar_r, hole_clr = 6.6, 0.4
step = 6.0
bump_x, bump_r, dimple_r = 7.0, 1.0, 1.3

gw = card_t + 2 * slop
rext, fext = rear_wall + gw / 2, front_wall + gw / 2
ledge_len = end_stop + card_w - thumb_out + extra_len
ly0 = foot_h + 0.4
ly1 = ly0 + ledge_h
hz = pe + 0.7 + bar_r + 0.5 + 0.6
assert step >= rext + 0.6 + 0.4
def hz_j(j): return hz + j * step
FOOT0 = 13.0                                                      # foot y of clip 0; clip j hangs at 13 + 60 j (its pegs are 37 and 57 mm above the foot)

def to_print(m, kind):
    R = trimesh.transformations.rotation_matrix
    T = {"strip": np.eye(4), "clip": R(np.pi / 2, [1, 0, 0]), "ledge": R(np.pi / 2, [1, 0, 0])}[kind]
    m = m.copy(); m.apply_transform(T); m.apply_translation(-m.bounds[0]); return m

def overhang_report(m, thresh_deg=43.0, bed_tol=0.05):
    n = m.face_normals; bad = (n[:, 2] < -np.cos(np.radians(thresh_deg))) & (m.triangles_center[:, 2] > bed_tol)
    return round(float(m.area_faces[bad].sum()), 1)

# ------------------------------------------------------------------ board strip
def peg(y):
    ring = lambda r_, z_: [(r_ * np.cos(a), y + r_ * np.sin(a), z_) for a in np.linspace(0, 2 * np.pi, 40, endpoint=False)]
    return union([cylz(0, y, -0.5, peg_stem + 0.01, peg_r, 40), hull(ring(peg_r, peg_stem) + ring(peg_head_r, peg_stem + peg_cone)),
                  cylz(0, y, peg_stem + peg_cone - 0.01, peg_stem + peg_cone + peg_top, peg_head_r, 40)])

def build_strip(grow=0.0):
    hw = strip_w / 2
    s = box(-hw - grow, hw + grow, 0, strip_h, -strip_t, grow)
    zpoly = [(-dt_root, 0.0), (dt_root, 0.0), (dt_tip, dt_len), (-dt_tip, dt_len)]
    male = prism_z([(x, strip_h + y) for x, y in zpoly], -strip_t, 0)
    cuts = [prism_z(offset_convex(zpoly, z_fit), -strip_t - 1, 1)]                                   # female dovetail
    for y in hole_ys:
        cuts += [cylz(0, y, -strip_t - 1, 1, hole_d / 2, 48),
                 hull([(r_ * np.cos(a), y + r_ * np.sin(a), z_) for r_, z_ in ((hole_d / 2, -(csk_d - hole_d) / 2), (csk_d / 2, 0.0)) for a in np.linspace(0, 2 * np.pi, 48, endpoint=False)]),
                 cylz(0, y, 0, 1, csk_d / 2, 48)]
    s = diff(union([s, male]), cuts)
    return union([s] + [peg(y) for y in peg_ys])

# ------------------------------------------------------------------ hinge clip
def keyhole(ky):
    r = key_round
    round_part = prism_z([(-r, ky - r), (r, ky - r), (r, ky + r), (key_slot_w / 2, ky + r + (r - key_slot_w / 2)), (-key_slot_w / 2, ky + r + (r - key_slot_w / 2)), (-r, ky + r)], pe - 3.5, pe + 1)   # 45 degree roof
    slot = prism_z([(-key_slot_w / 2, ky + r), (key_slot_w / 2, ky + r), (key_slot_w / 2, ky + key_travel + key_slot_end), (-key_slot_w / 2, ky + key_travel + key_slot_end)], pe - 3.5, pe + 1)
    return [round_part, slot]

def build_clip(j=0):
    h = hz_j(j)
    parts = [prism_z([(plate_x0, 15.0), (neck_x1, 15.0), (plate_x1, 30.0), (plate_x1, clip_y1), (plate_x0, clip_y1)], plate_z0, pe), box(plate_x0, neck_x1, clip_y0, 20.0, plate_z0, pe),         # upper plate with the keyholes + neck down to the foot
             box(pin_x - bar_r, pin_x + bar_r, clip_y0, foot_h, pe - 0.1, h), cyly(pin_x, h, clip_y0, foot_h, bar_r),             # solid footing block
             box(pin_x, pin_x + 8.6, clip_y0, foot_h, pe - 0.1, h + 2.5),
             cyly(pin_x, h, foot_h - 0.1, ly1 + 2.0, pin_d / 2, 48),                                                              # pin
             hull([(pin_x + r_ * np.cos(a), y_, h + r_ * np.sin(a)) for r_, y_ in ((collar_r, foot_h - 0.1), (pin_d / 2, foot_h + collar_h)) for a in np.linspace(0, 2 * np.pi, 48, endpoint=False)]),
             sphere(pin_x + bump_x, foot_h - 0.2, h, bump_r)]
    cuts = sum([keyhole(k) for k in key_y], [])
    return diff(union(parts), cuts)

# ------------------------------------------------------------------ ledge (pin axis at x = 0, z = 0)
def build_ledge():
    gb = ly1 - gutter_d; z_snug = -gw / 2 + card_t + corner_gap
    body = [cyly(0, 0, ly0, ly1, bar_r), box(0, end_stop, ly0, ly1, -rext, fext), box(0, ledge_len, ly0, gb, -rext, fext),
            box(wall_x0, ledge_len, gb - 0.01, gb + rear_h, -rext, -gw / 2), box(end_stop - 0.01, ledge_len, gb - 0.01, gb + front_h, gw / 2, fext),
            box(end_stop - 0.01, end_stop + corner_len, gb - 0.01, gb + corner_h, z_snug, fext), box(ledge_len - corner_len, ledge_len, gb - 0.01, gb + corner_h, z_snug, fext)]
    cs = hull([(r_ * np.cos(a), y_, r_ * np.sin(a)) for r_, y_ in ((collar_r + 0.3, ly0 - 0.01), (pin_d / 2 + hole_clr, ly0 + collar_h + 0.3)) for a in np.linspace(0, 2 * np.pi, 56, endpoint=False)])
    return diff(union(body), [cyly(0, 0, ly0 - 1, ly1 + 1, pin_d / 2 + hole_clr, 56), cs, sphere(bump_x, ly0 + 0.2, 0, dimple_r)])

def ledge_at(j, ang=0.0, lift=0.0):
    l = build_ledge(); l.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-ang), [0, 1, 0]))
    l.apply_translation([pin_x, lift, hz_j(j)]); return l

def clip_y(j): return FOOT0 + 60.0 * j                            # hanging position

def scene(N, strip_m, clips, ang=None):
    ns = 1 if clip_y(N - 1) + clip_y1 <= strip_h else 2
    asm = [place(strip_m, 0, 240.0 * i) for i in range(ns)]
    for j in range(N):
        y = clip_y(j); asm += [place(clips[j], 0, y), place(ledge_at(j, 0 if ang is None else ang[j], 1.0 if ang and ang[j] else 0.0), 0, y)]
    return asm, ns

if __name__ == "__main__":
    os.makedirs("board", exist_ok=True)
    strip = build_strip(); ledge = build_ledge(); clips = [build_clip(j) for j in range(6)]
    out = {"wall_strip": to_print(strip, "strip"), "ledge": to_print(ledge, "ledge")}
    for j, c in enumerate(clips): out[f"hinge_clip_j{j}"] = to_print(c, "clip")
    for n, m in out.items():
        m.export(f"board/{n}.stl"); print(f"{n:15s} watertight={m.is_watertight} size={np.round(m.extents, 1)} overhang>45deg={overhang_report(m)} mm2")
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    src = open("render_clip.py").read(); exec(src[src.index("def raster("):src.index("def panel(")])
    grey, orange, dk = (0.75, 0.75, 0.78), (0.95, 0.6, 0.1), (0.3, 0.3, 0.35)
    for N in (2, 3, 4, 5, 6):
        d = f"board/kit_{N}_cars"; os.makedirs(d, exist_ok=True)
        for f in os.listdir(d): os.remove(f"{d}/{f}")
        asm, ns = scene(N, strip, clips)
        trimesh.util.concatenate(asm).export(f"{d}/assembled_demo.stl")
        to_print(strip, "strip").export(f"{d}/wall_strip.stl"); to_print(ledge, "ledge").export(f"{d}/ledge.stl")
        for j in range(N): to_print(clips[j], "clip").export(f"{d}/hinge_clip_j{j}.stl")
        row, x = [], 0.0
        for j in range(N):
            p = to_print(clips[j], "clip"); p.apply_translation([x, 0, 0]); row.append(p); x += p.extents[0] + 6
        trimesh.util.concatenate(row).export(f"{d}/plate_clips.stl")
        col, y = [], 0.0
        for _ in range(N):
            p = to_print(ledge, "ledge"); p.apply_translation([0, y, 0]); col.append(p); y += p.extents[1] + 6
        trimesh.util.concatenate(col).export(f"{d}/plate_ledges.stl")
        top = clip_y(N - 1) + clip_y1
        fig, axs = plt.subplots(1, 2, figsize=(11, 6.5), dpi=100)
        cols = [grey] * ns + [dk, orange] * N
        axs[0].imshow(raster(asm, cols, 12, 28, (420, 640), [[-50, 0, -5], [130, 240 * ns, 60]])); axs[0].set_title(f"{N} cars"); axs[0].axis("off")
        asm2, _ = scene(N, strip, clips, ang=[0, 40, 75, 20, 60, 30][:N])
        axs[1].imshow(raster(asm2, cols, 50, 30, (420, 640), [[-50, 0, -5], [130, 240 * ns, 110]])); axs[1].set_title("ledges open"); axs[1].axis("off")
        fig.savefig(f"{d}/preview.png", bbox_inches="tight"); plt.close(fig)
        open(f"{d}/BOM.md", "w").write(f"""# {N}-car display kit (peg board + keyhole clips)
| Part | File | Qty | Print |
|---|---|---|---|
| Board strip with pegs | wall_strip.stl | {ns} | rear face down, pegs up, no supports |
| Hinge clip (keyholes), depth j = 0..{N-1} | hinge_clip_j0..j{N-1}.stl | 1 each | standing, brim, no supports |
| Ledge | ledge.stl | {N} | standing |
Mount: screw the strip(s) to the wall (second strip: press it straight onto the first strip's dovetail from the front first). Hang each clip: hold it so its two big round holes are over two
neighbouring pegs (clip j: pegs at y = {FOOT0 + 37:.0f} + 60 j and +20 mm), push it onto the pegs and let go - it drops 7 mm and hangs. To take it off lift it 7 mm and pull it toward you.
Drop each ledge on its pin. The closed ledge clicks onto the bump on the clip's footing (lift it about 1 mm to open it). Stack height {top:.0f} mm.
""")
        print(f"kit {N}: strips {ns}, top {top:.0f} mm")
