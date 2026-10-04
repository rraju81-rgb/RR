"""Hook-strip system (v3): wall strip with full-width integrated hook lips + compact solid hinge clip that drops onto a lip.
Usage: python3 build_board.py   -> board/*.stl, board/kit_<N>_cars/ (N = 2..6); every STL is in PRINT orientation (+z up)

  wall_strip   30 x 6 mm strip, 240 mm pitch. Every 20 mm a hook LIP runs across the full 30 mm width (shelf + upturned lip,
               with a 45 deg fillet under the lip so only 2.5 mm overhangs). Printed FLAT, back on the bed. 5 mm countersunk screw holes.
               C-interlock on the ends (front view, full thickness): the top end is a C (post + arm + down-turned tip), the bottom end
               of the next strip wraps around it; locked up/down/left/right, press the next strip on from the front.
  hinge_clip   one solid block behind the pin whose flat front face backs the cards of the racks below; DOUBLE LOCK: two 30 mm fingers drop behind
               BOTH lips of a lip pair (20 mm apart) at once: a plain L-on-L hook at each lip; cheeks hug the strip.
               Remove: lift ~6 mm and pull toward you. Wide solid footing the ledge sits on, 8 mm pin running
               the full ledge height, detent bump; the solid fill right behind the ledge is the 0 degree stop (no small nubs). Nothing sticks into the card lane: cards start 15 mm from the pin.
  ledge        18 mm tall barrel, solid full-height hinge block, tall back wall from the hinge block on, 1 mm front lip (card name visible),
               4 mm front corner supports, detent dimple underneath.
Loading: open the ledges above, swing the ledge 10-40 degrees (lift it ~1 mm over the detent), slide the card down into the slot.
Needs: pip install trimesh manifold3d numpy matplotlib.  Units mm.
Assembly frame: x right, y up, z out of the wall; strip front face z = 0, strip centre x = 0."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "legacy"))
import trimesh
from build_simple import box, cylz, cyly, union, diff, inter, hull, prism_z, sphere, offset_convex, place   # geometry helpers only

# ---- card (measure these) ----
card_w, card_h, card_t, blister_h, blister_y0, blister_dx = 105, 165, 1.2, 42, 8, 12

# ---- wall strip ----
strip_w, strip_h, strip_t = 30.0, 400.0, 6.0                    # one 40 cm strip (also exported as two halves)
hole_d, csk_d = 5.0, 9.0
lap, jc = 14.0, 0.2                                              # C-interlock (front view): overlap length, clearance
pitch, n_slots, B0 = 54.0, 7, 43.5                                # rack pitch (was 60), clip positions on the strip, first hook lip
hook_ys = [B0 + pitch * j for j in range(n_slots)]               # clip j hangs on the lip at hook_ys[j] ...
pair_d = 20.0                                                    # lip pair: upper (hook) lip + lower lip 20 mm below; the clip hooks onto BOTH (double lock)
lip_ys = sorted(set([b - pair_d for b in hook_ys] + hook_ys))    # no other lips
hole_ys = tuple(hook_ys[j] + 21.5 for j in (0, 1, 4, 5))         # 4 screws in the free gaps, symmetric top / bottom (65, 119, 281, 335)
split_y = hook_ys[2] + 14.0                                      # 2-piece version: C-interlock in the free gap at 165.5 (halves 179.5 / 234.5 mm)
shelf_h, groove, lip_t, lip_up = 4.0, 3.5, 2.5, 5.0              # shelf height, groove behind the lip, lip thickness, lip height above shelf
lip_d = groove + lip_t                                           # hook sticks out 6 mm

# ---- clip ----
g = 0.3                                                          # running clearance
body_t, arm_t = 4.0, 3.5
zb0 = lip_d + g; zb1 = zb0 + body_t                              # solid block z range (in front of the lips)
b_loc = 7.5                                                      # shelf bottom of the engaged lip, in clip coordinates (foot bottom = 0)
bear_y = b_loc - pair_d                                          # bottom of the lower lip, clip coordinates
clip_y0 = bear_y + shelf_h + 0.3                                 # clip ends at the bottom of the lower finger (on the print bed)
clip_y1 = b_loc + shelf_h + lip_up + g + arm_t
cheek_x, cheek_t, cheek_z0 = strip_w / 2 + 0.2, 3.0, -3.0
# FRICTION BUMP: each side edge of the strip has a thin spring wall (1 mm, 20 mm long, freed by a 0.8 mm slot) with a small
# bump on it. When the clip drops into place the bump clicks into a V-groove inside each cheek. Lifting the clip pushes the
# bump back in (wall flexes ~0.25 mm, ~10 N per side by beam estimate), so the clip can't creep up when a ledge is lifted
# over its detent, yet a firm lift still takes it off. Prints flat (strip) / standing (clip) without supports.
bump_y, bump_h = b_loc - 6.0, 0.45                               # bump centre in clip coords (between the two lips), bump height
spring_w, spring_slot, spring_l = 1.0, 0.8, 20.0
x_min = -(cheek_x + cheek_t)                                     # print bed face
lift = lip_up + g                                                # lift needed to unhook
foot_h = 3.5                                                     # (ledge underside sits at ly0; footing top is flush with it)
pin_x, pin_d = -14.6, 8.0
collar_r, collar_h = 5.2, 1.2
foot_x1, foot_z1 = 9.0, 2.0                                       # wide footing under the ledge's hinge block (x from pin, z above the pin axis)

# ---- ledge ----
ledge_h, gutter_d, slop = 12.0, 9.0, 0.3
bar_h = 18.0                                                     # barrel height (taller = less sag)
rear_wall, front_wall = 4.0, 3.5
rear_h, front_h = 19.0, 1.0                                      # front lip 3 mm lower so the card name shows
corner_h, corner_len, corner_gap = 14.0, 9.0, 0.1                # tall front corner posts hold the card upright
thumb_out, end_stop, extra_len = 8.0, 15.0, 10.0              # card starts 15 mm from the pin: clear of the hinge above
bar_r, hole_clr = 6.6, 0.2
step = 7.0
bump_x, bump_r, dimple_r = 7.0, 1.0, 1.3

gw = card_t + 2 * slop
rext, fext = rear_wall + gw / 2, front_wall + gw / 2
ledge_len = end_stop + card_w - thumb_out + extra_len
ly0 = foot_h + 0.4
ly1 = ly0 + ledge_h
gb = ly1 - gutter_d
hz = zb1 + 0.7 + bar_r + 0.5 + 0.6
assert step >= rext + 0.6 + 1.0
def hz_j(j): return hz + j * step
def zf_j(j):                                                       # front of the solid block: just behind the lowest card that passes in front of it
    return hz_j(0) - card_t / 2 - 0.5 if j else hz - bar_r - 0.4
def to_print(m, kind):
    R = trimesh.transformations.rotation_matrix
    T = {"strip": np.eye(4), "clip": R(np.pi / 2, [1, 0, 0]), "ledge": R(np.pi / 2, [1, 0, 0])}[kind]
    m = m.copy(); m.apply_transform(T); m.apply_translation(-m.bounds[0]); return m

def overhang_report(m, thresh_deg=43.0, bed_tol=0.05):
    n = m.face_normals; bad = (n[:, 2] < -np.cos(np.radians(thresh_deg))) & (m.triangles_center[:, 2] > bed_tol)
    return round(float(m.area_faces[bad].sum()), 1)

def prism_yz(poly_yz, x0, x1):  # profile in the y-z plane extruded along x
    return hull([(x, y, z) for x in (x0, x1) for y, z in poly_yz])

def teardrop(cx, cy, r, z, n=40):  # circle in x-y with a 45 degree point toward +x (= up when printed)
    pts = [(cx + r * np.cos(a), cy + r * np.sin(a), z) for a in np.linspace(0, 2 * np.pi, n, endpoint=False)]
    return pts + [(cx + r * np.sqrt(2), cy, z)]

# ------------------------------------------------------------------ wall strip
def c_red(y0, grow=0.0):
    """Top end of a strip (red in the sketch): left post + top arm + down-turned tip = a C that opens downward-right.
    The bottom end of the next strip (yellow) is the strip minus this shape grown by the clearance, so it fills the C
    and wraps over the arm: the two hook into each other (locked up/down and left/right). Full thickness; prints flat."""
    hw, t, e = strip_w / 2, strip_t, (1.0 if grow else 0.0)
    parts = [box(-hw - e, -hw + 7, y0 - e, y0 + lap, -t - e, e),                # post (left edge)
             box(-hw - e, 7, y0 + 9, y0 + lap, -t - e, e),                      # arm (towards the right, stops 8 mm short of the edge)
             box(3, 7, y0 + 5, y0 + lap, -t - e, e)]                            # down-turned tip
    if grow:
        parts = [box(m.bounds[0][0] - grow, m.bounds[1][0] + grow, m.bounds[0][1] - grow, m.bounds[1][1] + grow, m.bounds[0][2], m.bounds[1][2]) for m in parts]
    return union(parts)

def build_strip():
    hw, t = strip_w / 2, strip_t
    body = box(-hw, hw, 0, strip_h, -t, 0)
    top = None
    cuts = []
    for y in hole_ys:
        cuts += [cylz(0, y, -t - 1, 1, hole_d / 2, 48),
                 hull([(r_ * np.cos(a), y + r_ * np.sin(a), z_) for r_, z_ in ((hole_d / 2, -(csk_d - hole_d) / 2), (csk_d / 2, 0.0), (csk_d / 2, 1.0)) for a in np.linspace(0, 2 * np.pi, 48, endpoint=False)])]
    lips = []
    for b in lip_ys:
        lips += [box(-hw, hw, b, b + shelf_h, -0.01, lip_d), box(-hw, hw, b, b + shelf_h + lip_up, groove, lip_d)]   # plain L: shelf + upright lip
    bumps = []
    for b in hook_ys:                                              # spring walls + bumps on both side edges (friction bump)
        yc = b - b_loc + bump_y
        for sgn in (-1, 1):
            x0 = sgn * (hw - spring_w)
            cuts.append(box(min(x0, x0 - sgn * spring_slot), max(x0, x0 - sgn * spring_slot), yc - spring_l / 2, yc + spring_l / 2, -t - 1, lip_d + 1))
            bumps.append(hull([(sgn * hw - sgn * 0.01, yc + dy, z_) for dy in (-bump_h - 0.6, bump_h + 0.6) for z_ in (-t, 0)] +
                              [(sgn * (hw + bump_h), yc + dy, z_) for dy in (-0.6, 0.6) for z_ in (-t, 0)]))
    return union([diff(union([body] + lips), cuts)] + bumps)

def split_strip(full):
    """two printable halves joined by the C-interlock at split_y (lower half carries the C, upper half wraps it)"""
    hw, t = strip_w / 2, strip_t
    lower = union([inter([full, box(-hw - 1, hw + 1, -1, split_y, -t - 1, 20)]), inter([full, c_red(split_y)])])
    upper = diff(inter([full, box(-hw - 1, hw + 1, split_y, strip_h + 1, -t - 1, 20)]), [c_red(split_y, jc)])
    return lower, upper

# ------------------------------------------------------------------ hinge clip
def build_clip(j=0):
    h = hz_j(j); b = b_loc; zf = zf_j(j)
    fz0, fz1 = 0.2, groove - 0.2                                  # finger z range: snug in the 3.5 mm groove
    xs = pin_x + foot_x1
    parts = [box(-cheek_x, cheek_x, b + shelf_h, clip_y1, fz0, fz1),                        # finger (rests on the shelf)
             box(-cheek_x, cheek_x, clip_y1 - arm_t, clip_y1, fz0, zb1),                    # bridge over the lip
             box(-cheek_x, cheek_x, bear_y + shelf_h + 0.3, bear_y + shelf_h + lip_up + g + arm_t, fz0, fz1),   # DOUBLE LOCK: 2nd finger behind the lower lip
             box(-cheek_x, cheek_x, bear_y + shelf_h + lip_up + g, bear_y + shelf_h + lip_up + g + arm_t, fz0, zb1),   # ... and its bridge over that lip
             box(x_min, cheek_x + cheek_t, clip_y0, clip_y1, zb0, zf),                      # solid block, flat face backs the cards behind
             box(x_min, -cheek_x, clip_y0, clip_y1, cheek_z0, zb1), box(cheek_x, cheek_x + cheek_t, clip_y0, clip_y1, cheek_z0, zb1),   # cheeks
             diff(box(x_min, xs, clip_y0, clip_y1, zf - 0.1, h - rext - 0.3),                # solid fill right up behind the ledge = 0 degree stop
                  [cyly(pin_x, h, ly0 - 0.05, clip_y1 + 1, bar_r + 0.4, 64)]),
             box(x_min, xs, clip_y0, ly0 - 0.05, zf - 0.1, h + foot_z1), cyly(pin_x, h, clip_y0, ly0 - 0.05, bar_r, 64),   # wide footing: the ledge sits on it
             cyly(pin_x, h, ly0 - 0.15, ly0 + bar_h + 3.5, pin_d / 2, 64),                  # pin runs the full height of the ledge
             hull([(pin_x + r_ * np.cos(a), y_, h + r_ * np.sin(a)) for r_, y_ in ((collar_r, ly0 - 0.15), (pin_d / 2, ly0 + collar_h - 0.15)) for a in np.linspace(0, 2 * np.pi, 64, endpoint=False)]),
             sphere(pin_x + bump_x, ly0 - 0.3, h, bump_r)]
    grooves = [hull([(sgn * (cheek_x - 0.5), bump_y + dy, z_) for dy in (-bump_h - 1.3, bump_h + 1.3) for z_ in (cheek_z0 - 0.5, 0.5)] +
                    [(sgn * (strip_w / 2 + bump_h + 0.2), bump_y + dy, z_) for dy in (-0.9, 0.9) for z_ in (cheek_z0 - 0.5, 0.5)]) for sgn in (-1, 1)]
    return diff(union(parts), grooves)                            # double L lock; V-grooves catch the strip's friction bumps

# ------------------------------------------------------------------ ledge (pin axis at x = 0, z = 0)
def build_ledge():
    z_snug = -gw / 2 + card_t + corner_gap
    top = gb + rear_h
    body = [cyly(0, 0, ly0, ly0 + bar_h, bar_r), box(0, end_stop, ly0, top, -rext, fext),          # solid full-height hinge block (was the weak neck)
            box(0, ledge_len, ly0, gb, -rext, fext),
            box(end_stop - 0.01, ledge_len, gb - 0.01, top, -rext, -gw / 2),                        # tall back wall starts at the hinge block
            box(end_stop - 0.01, ledge_len, gb - 0.01, gb + front_h, gw / 2, fext),
            box(end_stop - 0.01, end_stop + corner_len, gb - 0.01, gb + corner_h, z_snug, fext), box(ledge_len - corner_len, ledge_len, gb - 0.01, gb + corner_h, z_snug, fext)]
    lead = [hull([(x_, y_, z_) for x_ in (x0 - 0.1, x0 + corner_len + 0.1) for y_, z_ in ((gb + corner_h + 0.1, z_snug - 0.1), (gb + corner_h + 0.1, z_snug + 2.0), (gb + corner_h - 2.0, z_snug - 0.1))])
            for x0 in (end_stop - 0.01, ledge_len - corner_len)]                           # 2 mm lead-in at the top of each post
    cs = hull([(r_ * np.cos(a), y_, r_ * np.sin(a)) for r_, y_ in ((collar_r + 0.3, ly0 - 0.01), (pin_d / 2 + hole_clr, ly0 + collar_h + 0.3)) for a in np.linspace(0, 2 * np.pi, 56, endpoint=False)])
    return diff(union(body), [cyly(0, 0, ly0 - 1, top + 1, pin_d / 2 + hole_clr, 56), cs, sphere(bump_x, ly0 - 0.1, 0, dimple_r)] + lead)

def ledge_at(j, ang=0.0, lift_=0.0):
    l = build_ledge(); l.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-ang), [0, 1, 0]))
    l.apply_translation([pin_x, lift_, hz_j(j)]); return l

def clip_y(j):                                                    # foot y of clip j on the 400 mm strip
    return hook_ys[j] - b_loc

# second (upper) strip: racks restart at depth 0. The upper strip must start this far above the lower one so its first card
# begins above the top of the lower strip's last card (depths can't go back down 6-5-4..: the blisters would hit the card below
# and every car would be hidden behind it).
upper_offset = hook_ys[n_slots - 1] - hook_ys[0] + card_h + 2.0   # 491 mm  -> 91 mm of bare wall between the two strips

def scene(N, strip_m, clips, ang=None):
    ns = 1
    asm = [strip_m]
    for j in range(N):
        y = clip_y(j); a = 0 if ang is None else ang[j]
        asm += [place(clips[j], 0, y), place(ledge_at(j, a, 1.0 if a else 0.0), 0, y)]
    return asm, ns

if __name__ == "__main__":
    os.makedirs("board", exist_ok=True)
    for f in os.listdir("board"):
        if f.endswith(".stl") or f.endswith(".zip"): os.remove(f"board/{f}")
    strip = build_strip(); ledge = build_ledge(); clips = [build_clip(j) for j in range(n_slots)]
    half1, half2 = split_strip(strip)
    out = {"wall_strip_400": to_print(strip, "strip"), "wall_strip_400_part1": to_print(half1, "strip"), "wall_strip_400_part2": to_print(half2, "strip"),
           "ledge": to_print(ledge, "ledge")}
    for j, c in enumerate(clips): out[f"hinge_clip_j{j}"] = to_print(c, "clip")
    for n, m in out.items():
        m.export(f"board/{n}.stl"); print(f"{n:15s} watertight={m.is_watertight} size={np.round(m.extents, 1)} overhang>45deg={overhang_report(m)} mm2")
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    src = open("render_clip.py").read(); exec(src[src.index("def raster("):src.index("def panel(")])
    grey, orange, dk = (0.75, 0.75, 0.78), (0.95, 0.6, 0.1), (0.3, 0.3, 0.35)
    for N in (2, 3, 4, 5, 6, 7):
        d = f"board/kit_{N}_cars"; os.makedirs(d, exist_ok=True)
        for f in os.listdir(d): os.remove(f"{d}/{f}")
        asm, ns = scene(N, strip, clips)
        trimesh.util.concatenate(asm).export(f"{d}/assembled_demo.stl")
        for n in ("wall_strip_400", "wall_strip_400_part1", "wall_strip_400_part2"): out[n].export(f"{d}/{n}.stl")
        to_print(ledge, "ledge").export(f"{d}/ledge.stl")
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
        axs[0].imshow(raster(asm, cols, 12, 28, (420, 640), [[-50, 0, -5], [130, strip_h, 60]])); axs[0].set_title(f"{N} cars"); axs[0].axis("off")
        asm2, _ = scene(N, strip, clips, ang=[0, 40, 75, 20, 60, 30, 50][:N])
        axs[1].imshow(raster(asm2, cols, 50, 30, (420, 640), [[-50, 0, -5], [130, strip_h, 110]])); axs[1].set_title("ledges open"); axs[1].axis("off")
        fig.savefig(f"{d}/preview.png", bbox_inches="tight"); plt.close(fig)
        open(f"{d}/BOM.md", "w").write(f"""# {N}-car display kit (hook strip + solid hinge clips)
| Part | File | Qty | Print |
|---|---|---|---|
| Wall strip 400 mm, one piece (bed >= 400 mm) | wall_strip_400.stl | 1 | flat, back on the bed, no supports |\n| or: the same strip in two halves (180 + 234 mm, C-interlock) | wall_strip_400_part1.stl + part2.stl | 1 each | flat, back on the bed |
| Hinge clip, depth j = 0..{N-1} | hinge_clip_j0..j{N-1}.stl | 1 each | standing (as exported), no supports (finger bridges 31 mm between the cheeks) |
| Ledge | ledge.stl | {N} | standing (as exported) |
Mount: screw the strip to the wall with 4 countersunk screws (two-piece strip: press part 2 over the C on top of part 1, straight in from the front).
Hang each clip: hold it 6 mm above its hook lip (clips hang 54 mm apart: clip j on the upper lip of pair j, counted from the bottom), push it against the strip
with the two cheeks either side of the strip, and let it drop - both fingers fall behind both lips (double L lock). To remove: lift 6 mm, pull the clip toward you.
Drop each ledge on its pin. It rests on the wide footing; the clip's solid block stops it at 0 degrees and the bump holds it closed
(lift the ledge about 1 mm to swing it open). To load a card: open the ledges above, swing this ledge out 10-40 degrees and slide the card down into the slot. Stack height {top:.0f} mm.
""")
        print(f"kit {N}: strips {ns}, top {top:.0f} mm")

    # ---------------- two strips, one above the other: 7 + 7 racks, depths 0..6 then 0..6 again
    d = "board/column_14_cars_two_strips"; os.makedirs(d, exist_ok=True)
    for f in os.listdir(d): os.remove(f"{d}/{f}")
    asm = [strip, place(strip, 0, upper_offset)]
    for k in range(2):
        for j in range(n_slots):
            asm += [place(clips[j], 0, upper_offset * k + clip_y(j)), place(ledge_at(j, 0), 0, upper_offset * k + clip_y(j))]
    trimesh.util.concatenate(asm).export(f"{d}/assembled_demo.stl")
    fig, ax = plt.subplots(1, 1, figsize=(6, 9), dpi=100)
    ax.imshow(raster(asm, [grey, grey] + [dk, orange] * (2 * n_slots), 12, 28, (520, 820), [[-50, 0, -5], [130, upper_offset + strip_h, 80]])); ax.axis("off")
    ax.set_title(f"two 40 cm strips: 14 cars, upper strip starts {upper_offset:.0f} mm above the lower one")
    fig.savefig(f"{d}/preview.png", bbox_inches="tight"); plt.close(fig)
    open(f"{d}/BOM.md", "w").write(f"""# 14 cars on two 40 cm strips (7 + 7)
| Part | Qty |
|---|---|
| wall_strip_400.stl (or part1 + part2) | 2 |
| hinge_clip_j0 ... hinge_clip_j6 | 2 of each (one set per strip) |
| ledge.stl | 14 |
Mount the second strip directly above the first, same x, with its bottom end {upper_offset:.0f} mm above the bottom end of the first
(that leaves {upper_offset - strip_h:.0f} mm of bare wall between them). On each strip the clips go j0 at the bottom up to j6 at the top.
Why not 0-1-2-3-4-5-6-5-4-3-2-1-0: when the depth goes back down, a card sits in front of the rack above it, so the blister
of the upper card hits it and every car above is hidden behind it. Starting again at depth 0 needs the {upper_offset - strip_h:.0f} mm gap
so the last card of the lower strip ends before the first card of the upper strip begins.
""")
    print(f"column: upper strip offset {upper_offset:.0f} mm, gap {upper_offset - strip_h:.0f} mm")
