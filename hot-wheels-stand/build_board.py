"""Hook-strip system (v3): wall strip with full-width integrated hook lips + compact solid hinge clip that drops onto a lip.
Usage: python3 build_board.py   -> board/*.stl, board/kit_<N>_cars/ (N = 2..6); every STL is in PRINT orientation (+z up)

  wall_strip   30 x 6 mm strip, 240 mm pitch. Every 20 mm a hook LIP runs across the full 30 mm width (shelf + upturned lip,
               with a 45 deg fillet under the lip so only 2.5 mm overhangs). Printed FLAT, back on the bed. 5 mm countersunk screw holes.
               C-interlock on the ends (front view, full thickness): the top end is a C (post + arm + down-turned tip), the bottom end
               of the next strip wraps around it; locked up/down/left/right, press the next strip on from the front.
  hinge_clip   one solid block behind the pin whose flat front face backs the cards of the racks below; a 30 mm finger drops behind a strip
               lip (gravity lock, lift ~6 mm and pull to remove); cheeks hug the strip. Wide solid footing the ledge sits on, 8 mm pin running
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
strip_w, strip_h, strip_t = 30.0, 240.0, 6.0
hole_d, csk_d, hole_ys = 5.0, 9.0, (20.0, 120.0, 220.0)
lap, jc = 14.0, 0.2                                              # C-interlock (front view): overlap length, clearance
fil_z, fil_y = 1.0, 2.5                                          # 45 deg fillet under the lip so the strip prints flat (lip overhang only 2.5 mm)
lip_ys = [26.0 + 20.0 * k for k in range(11)]                    # bottom of each hook shelf (26 .. 226); screw holes sit in the gaps
shelf_h, groove, lip_t, lip_up = 4.0, 3.5, 2.5, 5.0              # shelf height, groove behind the lip, lip thickness, lip height above shelf
lip_d = groove + lip_t                                           # hook sticks out 6 mm

# ---- clip ----
g = 0.3                                                          # running clearance
body_t, arm_t = 4.0, 3.5
zb0 = lip_d + g; zb1 = zb0 + body_t                              # solid block z range (in front of the lips)
b_loc = 7.5                                                      # shelf bottom of the engaged lip, in clip coordinates (foot bottom = 0)
clip_y0 = b_loc - 14.5                                           # block bottom bears on the front of the lip below
clip_y1 = b_loc + shelf_h + lip_up + g + arm_t
cheek_x, cheek_t, cheek_z0 = strip_w / 2 + 0.2, 3.0, -3.0
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
corner_h, corner_len, corner_gap = 4.0, 9.0, 0.15
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
K0 = 1                                                           # clip j hangs on lip 1 + 3 j  (60 mm pitch)
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

def lip_fillet(b, grow=0.0):                                     # 45 deg fillet in the groove under the lip (y-z triangle across the width)
    tri = [(b + shelf_h, fil_z), (b + shelf_h, groove), (b + shelf_h + fil_y, groove)]
    if grow:                                                     # triangle offset outward by `grow` (45 deg corners)
        tri = [(y + dy, z + dz) for (y, z), (dy, dz) in zip(tri, ((-grow, -grow * 2.414), (-grow, grow), (grow * 2.414, grow)))]
    hw = strip_w / 2 + (1.0 if grow else 0.0)
    return hull([(x, y, z) for x in (-hw, hw) for y, z in tri])

def build_strip():
    hw, t = strip_w / 2, strip_t
    body = diff(box(-hw, hw, 0, strip_h, -t, 0), [c_red(0.0, jc)])                                       # yellow: wraps the C of the strip below
    top = inter([c_red(strip_h), box(-hw, hw, strip_h - 0.01, strip_h + lap, -t, 0)])                     # red: the C itself
    cuts = []
    for y in hole_ys:
        cuts += [cylz(0, y, -t - 1, 1, hole_d / 2, 48),
                 hull([(r_ * np.cos(a), y + r_ * np.sin(a), z_) for r_, z_ in ((hole_d / 2, -(csk_d - hole_d) / 2), (csk_d / 2, 0.0), (csk_d / 2, 1.0)) for a in np.linspace(0, 2 * np.pi, 48, endpoint=False)])]
    lips = []
    for b in lip_ys:
        lips += [box(-hw, hw, b, b + shelf_h, -0.01, lip_d), box(-hw, hw, b, b + shelf_h + lip_up, groove, lip_d), lip_fillet(b)]
    return diff(union([body, top] + lips), cuts)

# ------------------------------------------------------------------ hinge clip
def build_clip(j=0):
    h = hz_j(j); b = b_loc; zf = zf_j(j)
    fz0, fz1 = g, groove - g                                      # finger z range (in the groove)
    xs = pin_x + foot_x1
    parts = [box(-cheek_x, cheek_x, b + shelf_h, clip_y1, fz0, fz1),                        # finger (rests on the shelf)
             box(-cheek_x, cheek_x, clip_y1 - arm_t, clip_y1, fz0, zb1),                    # bridge over the lip
             box(x_min, cheek_x + cheek_t, clip_y0, clip_y1, zb0, zf),                      # solid block, flat face backs the cards behind
             box(x_min, -cheek_x, clip_y0, clip_y1, cheek_z0, zb1), box(cheek_x, cheek_x + cheek_t, clip_y0, clip_y1, cheek_z0, zb1),   # cheeks
             diff(box(x_min, xs, clip_y0, clip_y1, zf - 0.1, h - rext - 0.3),                # solid fill right up behind the ledge = 0 degree stop
                  [cyly(pin_x, h, ly0 - 0.05, clip_y1 + 1, bar_r + 0.4, 64)]),
             box(x_min, xs, clip_y0, ly0 - 0.05, zf - 0.1, h + foot_z1), cyly(pin_x, h, clip_y0, ly0 - 0.05, bar_r, 64),   # wide footing: the ledge sits on it
             cyly(pin_x, h, ly0 - 0.15, ly0 + bar_h + 3.5, pin_d / 2, 64),                  # pin runs the full height of the ledge
             hull([(pin_x + r_ * np.cos(a), y_, h + r_ * np.sin(a)) for r_, y_ in ((collar_r, ly0 - 0.15), (pin_d / 2, ly0 + collar_h - 0.15)) for a in np.linspace(0, 2 * np.pi, 64, endpoint=False)]),
             sphere(pin_x + bump_x, ly0 - 0.3, h, bump_r)]
    return diff(union(parts), [lip_fillet(b_loc, g)])

# ------------------------------------------------------------------ ledge (pin axis at x = 0, z = 0)
def build_ledge():
    z_snug = -gw / 2 + card_t + corner_gap
    top = gb + rear_h
    body = [cyly(0, 0, ly0, ly0 + bar_h, bar_r), box(0, end_stop, ly0, top, -rext, fext),          # solid full-height hinge block (was the weak neck)
            box(0, ledge_len, ly0, gb, -rext, fext),
            box(end_stop - 0.01, ledge_len, gb - 0.01, top, -rext, -gw / 2),                        # tall back wall starts at the hinge block
            box(end_stop - 0.01, ledge_len, gb - 0.01, gb + front_h, gw / 2, fext),
            box(end_stop - 0.01, end_stop + corner_len, gb - 0.01, gb + corner_h, z_snug, fext), box(ledge_len - corner_len, ledge_len, gb - 0.01, gb + corner_h, z_snug, fext)]
    cs = hull([(r_ * np.cos(a), y_, r_ * np.sin(a)) for r_, y_ in ((collar_r + 0.3, ly0 - 0.01), (pin_d / 2 + hole_clr, ly0 + collar_h + 0.3)) for a in np.linspace(0, 2 * np.pi, 56, endpoint=False)])
    return diff(union(body), [cyly(0, 0, ly0 - 1, top + 1, pin_d / 2 + hole_clr, 56), cs, sphere(bump_x, ly0 - 0.1, 0, dimple_r)])

def ledge_at(j, ang=0.0, lift_=0.0):
    l = build_ledge(); l.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-ang), [0, 1, 0]))
    l.apply_translation([pin_x, lift_, hz_j(j)]); return l

def clip_y(j):                                                    # global foot y of clip j (strips repeat every 240 mm)
    k = K0 + 3 * j; s, kk = divmod(k, 12)
    return 240.0 * s + lip_ys[kk] - b_loc

def scene(N, strip_m, clips, ang=None):
    ns = 1 if clip_y(N - 1) + clip_y1 <= strip_h else 2
    asm = [place(strip_m, 0, 240.0 * i) for i in range(ns)]
    for j in range(N):
        y = clip_y(j); a = 0 if ang is None else ang[j]
        asm += [place(clips[j], 0, y), place(ledge_at(j, a, 1.0 if a else 0.0), 0, y)]
    return asm, ns

if __name__ == "__main__":
    os.makedirs("board", exist_ok=True)
    for f in os.listdir("board"):
        if f.endswith(".stl") or f.endswith(".zip"): os.remove(f"board/{f}")
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
        open(f"{d}/BOM.md", "w").write(f"""# {N}-car display kit (hook strip + solid hinge clips)
| Part | File | Qty | Print |
|---|---|---|---|
| Wall strip with hook lips | wall_strip.stl | {ns} | flat, back on the bed (as exported), no supports |
| Hinge clip, depth j = 0..{N-1} | hinge_clip_j0..j{N-1}.stl | 1 each | standing (as exported), no supports (finger bridges 31 mm between the cheeks) |
| Ledge | ledge.stl | {N} | standing (as exported) |
Mount: screw the strip(s) to the wall (second strip: press its bottom end over the C on top of the first strip, straight in from the front, then screw it).
Hang each clip: hold it 6 mm above its hook lip (clip j uses lip {K0}, {K0 + 3}, {K0 + 6}, ... counted from the bottom, starting at 0), push it against the strip
with the two cheeks either side of the strip, and let it drop - the finger falls behind the lip. To remove: lift 6 mm and pull toward you.
Drop each ledge on its pin. It rests on the wide footing; the clip's solid block stops it at 0 degrees and the bump holds it closed
(lift the ledge about 1 mm to swing it open). To load a card: open the ledges above, swing this ledge out 10-40 degrees and slide the card down into the slot. Stack height {top:.0f} mm.
""")
        print(f"kit {N}: strips {ns}, top {top:.0f} mm")
