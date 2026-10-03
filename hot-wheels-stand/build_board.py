"""Hook-strip system (v2): wall strip with full-width integrated hook lips + compact solid hinge clip that drops onto a lip.
Usage: python3 build_board.py   -> board/*.stl, board/kit_<N>_cars/ (N = 2..6); every STL is in PRINT orientation (+z up)

  wall_strip   30 x 5 mm strip, 240 mm long. Every 20 mm a hook LIP runs across the full 30 mm width (shelf + upturned lip, like a French cleat).
               Printed standing on its long edge, so every hook profile lies in the layer plane: no pegs to snap off. 5 mm countersunk screw holes
               (teardrop, printable sideways), dovetail joint on both ends for stacking.
  hinge_clip   one solid block behind the pin: a 30 mm wide finger drops behind a strip lip (gravity lock); two side cheeks hug the strip so
               it cannot twist; the block bottom bears on the lip below. Lift 5.3 mm and pull to remove. Support arm under the closed ledge
               (stops the ledge sagging) with a stop nub that the ledge's notch hits at 0 degrees. Printed standing: no supports, the finger
               bridges between the cheeks.
  ledge        barrel, 9 mm deep slot, tall back wall, low front lip, front corner supports, stop notch underneath.
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
strip_w, strip_h, strip_t = 30.0, 240.0, 5.0
hole_d, csk_d, hole_ys = 5.0, 9.0, (20.0, 120.0, 220.0)
dt_root, dt_tip, dt_len, z_fit = 4.0, 7.5, 7.0, 0.12             # dovetail joint
lip_ys = [26.0 + 20.0 * k for k in range(11)]                    # bottom of each hook shelf (26 .. 226); screw holes sit in the gaps
shelf_h, groove, lip_t, lip_up = 4.0, 3.5, 2.5, 5.0              # shelf height, groove behind the lip, lip thickness, lip height above shelf
lip_d = groove + lip_t                                           # hook sticks out 6 mm

# ---- clip ----
g = 0.3                                                          # running clearance
body_t, arm_t = 4.0, 3.5
zb0 = lip_d + g; zb1 = zb0 + body_t                              # solid block z range (in front of the lips)
b_loc = 7.5                                                      # shelf bottom of the engaged lip, in clip coordinates (foot bottom = 0)
clip_y0 = b_loc - 15.5                                           # block bottom bears on the front of the lip below
clip_y1 = b_loc + shelf_h + lip_up + g + arm_t
cheek_x, cheek_t, cheek_z0 = strip_w / 2 + g, 3.0, -3.0
x_min = -(cheek_x + cheek_t)                                     # print bed face
lift = lip_up + g                                                # lift needed to unhook
foot_h = 3.5
pin_x, pin_d = -14.6, 8.0
collar_r, collar_h = 5.2, 1.2
arm_len, nub_x, nub_w, nub_h, nub_d = 20.4, 15.0, 2.6, 1.2, 2.8  # sag support arm (45 deg gusset) + 0 degree stop nub (x from pin)

# ---- ledge ----
ledge_h, gutter_d, slop = 12.0, 9.0, 0.3
rear_wall, front_wall = 4.0, 3.5
rear_h, front_h = 19.0, 4.0
corner_h, corner_len, corner_gap = 7.0, 9.0, 0.15
thumb_out, end_stop, wall_x0, extra_len = 8.0, 9.0, 17.0, 10.0
bar_r, hole_clr = 6.6, 0.4
step = 6.0
bump_x, bump_r, dimple_r = 7.0, 1.0, 1.3

gw = card_t + 2 * slop
rext, fext = rear_wall + gw / 2, front_wall + gw / 2
ledge_len = end_stop + card_w - thumb_out + extra_len
ly0 = foot_h + 0.4
ly1 = ly0 + ledge_h
gb = ly1 - gutter_d
hz = zb1 + 0.7 + bar_r + 0.5 + 0.6
assert step >= rext + 0.6 + 0.4
def hz_j(j): return hz + j * step
K0 = 1                                                           # clip j hangs on lip 1 + 3 j  (60 mm pitch)
def to_print(m, kind):
    R = trimesh.transformations.rotation_matrix
    T = {"strip": R(-np.pi / 2, [0, 1, 0]), "clip": R(np.pi / 2, [1, 0, 0]), "ledge": R(np.pi / 2, [1, 0, 0])}[kind]
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
def build_strip():
    hw = strip_w / 2
    s = box(-hw, hw, 0, strip_h, -strip_t, 0)
    zpoly = [(-dt_root - dt_len, 0.0), (dt_root, 0.0), (dt_root + dt_len, dt_len), (-dt_root, dt_len)]   # 45 deg parallelogram: locks in y, prints on edge without overhang
    male = prism_z([(x, strip_h + y) for x, y in zpoly], -strip_t, 0)
    cuts = [prism_z(offset_convex(zpoly, z_fit), -strip_t - 1, 1)]
    for y in hole_ys:
        cuts += [hull(teardrop(0, y, hole_d / 2, -strip_t - 1) + teardrop(0, y, hole_d / 2, 1)),
                 hull(teardrop(0, y, hole_d / 2, -(csk_d - hole_d) / 2) + teardrop(0, y, csk_d / 2, 0.0) + teardrop(0, y, csk_d / 2, 1))]
    lips = []
    for b in lip_ys:
        lips += [box(-hw, hw, b, b + shelf_h, -0.01, lip_d), box(-hw, hw, b, b + shelf_h + lip_up, groove, lip_d)]
    return diff(union([s, male] + lips), cuts)

# ------------------------------------------------------------------ hinge clip
def build_clip(j=0):
    h = hz_j(j); b = b_loc
    fz0, fz1 = g, groove - g                                      # finger z range (in the groove)
    parts = [box(-cheek_x, cheek_x, b + shelf_h, clip_y1, fz0, fz1),                        # finger (rests on the shelf)
             box(-cheek_x, cheek_x, clip_y1 - arm_t, clip_y1, fz0, zb1),                    # bridge over the lip
             box(x_min, cheek_x + cheek_t, clip_y0, clip_y1, zb0, zb1),                     # solid block
             box(x_min, -cheek_x, clip_y0, clip_y1, cheek_z0, zb1), box(cheek_x, cheek_x + cheek_t, clip_y0, clip_y1, cheek_z0, zb1),   # cheeks
             box(x_min, pin_x + 8.6, clip_y0, foot_h, zb1 - 0.1, h), cyly(pin_x, h, clip_y0, foot_h, bar_r, 64),                         # footing, solid down to the bed
             box(pin_x, pin_x + 8.6, clip_y0, foot_h, zb1 - 0.1, h + fext),
             box(pin_x + 6.0, pin_x + 8.6, clip_y0, ly0 - 0.1, h - rext, h + fext),
             hull([(pin_x + 8.5, clip_y0, z_) for z_ in (h - rext, h + fext)] + [(pin_x + 8.5, ly0 - 0.1, z_) for z_ in (h - rext, h + fext)]
                  + [(pin_x + arm_len, ly0 - 0.1, z_) for z_ in (h - rext, h + fext)]),   # sag support arm under the closed ledge (45 deg underside)
             box(pin_x + nub_x, pin_x + nub_x + nub_w, ly0 - 0.2, ly0 - 0.1 + nub_h, h - rext, h - rext + nub_d),   # 0 degree stop nub
             cyly(pin_x, h, foot_h - 0.1, ly1 + 2.0, pin_d / 2, 64),
             hull([(pin_x + r_ * np.cos(a), y_, h + r_ * np.sin(a)) for r_, y_ in ((collar_r, foot_h - 0.1), (pin_d / 2, foot_h + collar_h)) for a in np.linspace(0, 2 * np.pi, 64, endpoint=False)]),
             sphere(pin_x + bump_x, foot_h - 0.2, h, bump_r)]
    return union(parts)

# ------------------------------------------------------------------ ledge (pin axis at x = 0, z = 0)
def build_ledge():
    z_snug = -gw / 2 + card_t + corner_gap
    body = [cyly(0, 0, ly0, ly1, bar_r), box(0, end_stop, ly0, ly1, -rext, fext), box(0, ledge_len, ly0, gb, -rext, fext),
            box(wall_x0, ledge_len, gb - 0.01, gb + rear_h, -rext, -gw / 2), box(end_stop - 0.01, ledge_len, gb - 0.01, gb + front_h, gw / 2, fext),
            box(end_stop - 0.01, end_stop + corner_len, gb - 0.01, gb + corner_h, z_snug, fext), box(ledge_len - corner_len, ledge_len, gb - 0.01, gb + corner_h, z_snug, fext)]
    cs = hull([(r_ * np.cos(a), y_, r_ * np.sin(a)) for r_, y_ in ((collar_r + 0.3, ly0 - 0.01), (pin_d / 2 + hole_clr, ly0 + collar_h + 0.3)) for a in np.linspace(0, 2 * np.pi, 56, endpoint=False)])
    notch = box(nub_x - 0.8, nub_x + nub_w + 0.8, ly0 - 1, ly0 + nub_h + 0.3, -rext - 1, -rext + nub_d + 0.25)   # open to the back: nub slides out when opening
    return diff(union(body), [cyly(0, 0, ly0 - 1, ly1 + 1, pin_d / 2 + hole_clr, 56), cs, sphere(bump_x, ly0 + 0.2, 0, dimple_r), notch])

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
| Wall strip with hook lips | wall_strip.stl | {ns} | standing on its long edge (as exported), brim, no supports |
| Hinge clip, depth j = 0..{N-1} | hinge_clip_j0..j{N-1}.stl | 1 each | standing (as exported), no supports (finger bridges 31 mm between the cheeks) |
| Ledge | ledge.stl | {N} | standing (as exported) |
Mount: screw the strip(s) to the wall (second strip: press it straight onto the first strip's dovetail from the front first).
Hang each clip: hold it 6 mm above its hook lip (clip j uses lip {K0}, {K0 + 3}, {K0 + 6}, ... counted from the bottom, starting at 0), push it against the strip
with the two cheeks either side of the strip, and let it drop - the finger falls behind the lip. To remove: lift 6 mm and pull toward you.
Drop each ledge on its pin. It rests on the support arm; the nub under it stops it at 0 degrees and the bump holds it closed
(lift the ledge about 1 mm to swing it open). Stack height {top:.0f} mm.
""")
        print(f"kit {N}: strips {ns}, top {top:.0f} mm")
