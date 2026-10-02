"""SIMPLE print-ready rack system (replaces the compliant-mechanism version).
Usage: python3 build_simple.py   -> simple/*.stl, simple/kit_<N>_cars/ for N = 2..6   (every STL is in PRINT orientation, +z up)

Parts (nothing thin, nothing that has to flex):
  wall_strip   25 mm dovetail rail, 5 mm screw holes, dovetail joint on both ends, 4.5 mm peg holes every 20 mm
  hinge_clip   plate with two dovetail jaws + solid footing block + 6 mm pin. One 4.6 mm hole through the plate.
  lock_peg     4 mm peg: pushed through the clip's hole into a peg hole of the strip = clip cannot slide. Pull it out to move the clip.
  ledge        barrel with a plain 6.8 mm hole (turns freely), floor, tall back wall, low front lip, 2 front corner supports,
               a small bump on its underside that clicks into a dimple in the clip's footing when the ledge is closed
Needs: pip install trimesh manifold3d numpy matplotlib.  Units mm.
Assembly frame: x right, y up, z out of the wall; strip front face z = 0, strip centre x = 0; clip foot bottom y = 0."""
import os
import numpy as np
import trimesh

# ---- card (measure these) ----
card_w, card_h, card_t, blister_h, blister_y0, blister_dx = 105, 165, 1.2, 42, 8, 12

# ---- wall strip ----
strip_w, strip_h, strip_t = 25.0, 240.0, 4.0           # front width, length, thickness; rear width = 17 (45 degree sides)
hole_d, csk_d, hole_ys = 5.0, 9.0, (20.0, 120.0, 220.0)  # 5 mm screw holes, 45 degree countersink, mirrored about the middle
dt_root, dt_tip, dt_len, z_fit = 4.0, 7.5, 7.0, 0.12     # dovetail joint (half widths, length, clearance)
peg_hole_r, peg_hole_depth = 2.3, 3.0                   # peg holes in the strip: every 20 mm at x = 0, y = 12 + 20 k

# ---- clip ----
clr = 1.0                                              # jaw clearance per side (roomy so it slides on)
plate_z0, plate_t, arm_t = 0.9, 3.0, 2.4
clip_y0, clip_y1 = -10.0, 28.0
foot_h = 3.5
pin_x, pin_d = -5.0, 6.0
peg_y = 22.0                                           # lock hole height above the foot bottom (above the ledge, clear of the card)
peg_r, peg_head_r, peg_head_h = 2.0, 3.5, 3.0

# ---- ledge ----
ledge_h, gutter_d, slop = 12.0, 6.0, 0.3
rear_wall, front_wall = 4.0, 3.5
rear_h, front_h = 16.0, 3.0                            # tall back wall / low front lip above the gutter bottom
corner_h, corner_len, corner_gap = 7.0, 9.0, 0.15      # front corner supports
thumb_out, end_stop, wall_x0 = 8.0, 9.0, 17.0
bar_r, hole_clr = 5.4, 0.4                              # barrel radius, radial clearance around the pin
step = 6.0                                             # depth step between racks
bump_x, bump_r = 7.0, 1.0                              # closed-position click: bump on top of the clip's footing ...
dimple_r = 1.3                                         # ... and dimple in the ledge underside

gw = card_t + 2 * slop
rext, fext = rear_wall + gw / 2, front_wall + gw / 2
ledge_len = end_stop + card_w - thumb_out
ly0 = foot_h + 0.4
ly1 = ly0 + ledge_h
hz = plate_z0 + plate_t + 0.7 + bar_r + 0.5
assert step >= rext + 0.6 + 0.4
def hz_j(j): return hz + j * step

# ------------------------------------------------------------------ helpers
def box(x0, x1, y0, y1, z0, z1): return trimesh.creation.box(bounds=[[x0, y0, z0], [x1, y1, z1]])
def cylz(x, y, z0, z1, r, n=48):
    m = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=n); m.apply_translation([x, y, (z0 + z1) / 2]); return m
def cyly(x, z, y0, y1, r, n=64):
    m = trimesh.creation.cylinder(radius=r, height=y1 - y0, sections=n)
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])); m.apply_translation([x, (y0 + y1) / 2, z]); return m
def union(ms): return trimesh.boolean.union(ms, engine="manifold")
def diff(a, bs): return trimesh.boolean.difference([a, union(bs)], engine="manifold")
def inter(ms): return trimesh.boolean.intersection(ms, engine="manifold")
def hull(pts): return trimesh.convex.convex_hull(np.array(pts, float))
def prism_y(poly_xz, y0, y1): return hull([(x, y, z) for y in (y0, y1) for x, z in poly_xz])
def prism_z(poly_xy, z0, z1): return hull([(x, y, z) for z in (z0, z1) for x, y in poly_xy])
def prism_x(poly_zy, x0, x1): return hull([(x, y, z) for x in (x0, x1) for z, y in poly_zy])
def sphere(x, y, z, r):
    m = trimesh.creation.icosphere(subdivisions=2, radius=r); m.apply_translation([x, y, z]); return m

def offset_convex(poly, d):
    P = np.array(poly, float); c = P.mean(0); n = len(P); lines = []
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]; t = (b - a) / np.linalg.norm(b - a); nrm = np.array([t[1], -t[0]])
        if np.dot(nrm, (a + b) / 2 - c) < 0: nrm = -nrm
        lines.append((a + nrm * d, t))
    out = []
    for i in range(n):
        (p1, t1), (p2, t2) = lines[i - 1], lines[i]
        out.append(tuple(p1 + t1 * np.linalg.solve(np.array([t1, -t2]).T, p2 - p1)[0]))
    return out

def to_print(m, kind):
    R = trimesh.transformations.rotation_matrix
    T = {"strip": np.eye(4), "clip": R(np.pi / 2, [1, 0, 0]), "ledge": R(np.pi / 2, [1, 0, 0]), "peg": np.eye(4)}[kind]
    m = m.copy(); m.apply_transform(T); m.apply_translation(-m.bounds[0]); return m

def place(m, x, y, z=0.0): m = m.copy(); m.apply_translation([x, y, z]); return m

def overhang_report(m, thresh_deg=43.0, bed_tol=0.05):
    n = m.face_normals; bad = (n[:, 2] < -np.cos(np.radians(thresh_deg))) & (m.triangles_center[:, 2] > bed_tol)
    return round(float(m.area_faces[bad].sum()), 1)

# ------------------------------------------------------------------ wall strip
def build_strip(grow=0.0):
    r = strip_w / 2; rr = r - strip_t; g = grow
    s = prism_y([(-r - g, g), (r + g, g), (rr + g, -strip_t), (-rr - g, -strip_t)], 0, strip_h)
    zpoly = [(-dt_root, 0.0), (dt_root, 0.0), (dt_tip, dt_len), (-dt_tip, dt_len)]
    male = inter([prism_y([(-r, 0), (r, 0), (rr, -strip_t), (-rr, -strip_t)], strip_h - 0.01, strip_h + dt_len),
                  prism_z([(x, strip_h + y) for x, y in zpoly], -strip_t - 1, 1)])
    s = union([s, male]); cuts = [prism_z(offset_convex(zpoly, z_fit), -strip_t - 1, 1)]          # female dovetail in the bottom end
    for y in hole_ys:                                                                             # screw holes + countersink
        cuts.append(cylz(0, y, -strip_t - 1, 1, hole_d / 2, 48))
        zc0 = -(csk_d - hole_d) / 2
        cuts += [hull([(r_ * np.cos(a), y + r_ * np.sin(a), z_) for r_, z_ in ((hole_d / 2, zc0), (csk_d / 2, 0.0)) for a in np.linspace(0, 2 * np.pi, 48, endpoint=False)]),
                 cylz(0, y, 0, 1, csk_d / 2, 48)]
    for y in np.arange(12.0, strip_h - 5, 20.0):                                                  # peg holes
        cuts.append(cylz(0, y, -peg_hole_depth, 1, peg_hole_r, 40))
    return diff(s, cuts)

# ------------------------------------------------------------------ clip
def build_clip(j=0):
    h = hz_j(j); pe = plate_z0 + plate_t
    r = strip_w / 2 + clr + 0.1; ax = r + 0.3 + arm_t; zt = -strip_t + 0.8
    parts = [box(-ax, ax, clip_y0, clip_y1, plate_z0, pe)]
    for sg in (1, -1):                                         # dovetail jaws
        x1, x2 = r + plate_z0, r + zt
        parts.append(prism_y([(sg * x1, plate_z0), (sg * x2, zt), (sg * (x2 + arm_t), zt), (sg * ax, -0.3), (sg * ax, plate_z0 + 0.1)], clip_y0, clip_y1))
    parts += [box(pin_x - bar_r, pin_x + bar_r, clip_y0, foot_h, pe - 0.1, h), cyly(pin_x, h, clip_y0, foot_h, bar_r),     # solid footing block (prints on the bed)
              box(pin_x, pin_x + 8.6, clip_y0, foot_h, pe - 0.1, h + 2.5),                                                  # ... extended under the ledge's end stop
              cyly(pin_x, h, foot_h - 0.1, ly1 + 2.0, pin_d / 2, 48),                                                        # pin
              sphere(pin_x + bump_x, foot_h - 0.2, h, bump_r)]                                                               # bump for the closed ledge
    c = -peg_r - 0.3                                            # lock hole: round with a 45 degree roof (prints without support)
    cuts = [cylz(0, peg_y, plate_z0 - 0.1, pe + 0.1, peg_r + 0.3, 40), prism_z([(-1.64, peg_y + 1.64), (1.64, peg_y + 1.64), (0, peg_y + 3.25)], plate_z0 - 0.1, pe + 0.1)]
    return diff(union(parts), cuts)

# ------------------------------------------------------------------ ledge (pin axis at x = 0, z = 0)
def build_ledge():
    gb = ly1 - gutter_d; z_snug = -gw / 2 + card_t + corner_gap
    body = [cyly(0, 0, ly0, ly1, bar_r), box(0, end_stop, ly0, ly1, -rext, fext), box(0, ledge_len, ly0, gb, -rext, fext),
            box(wall_x0, ledge_len, gb - 0.01, gb + rear_h, -rext, -gw / 2),                         # tall back wall
            box(end_stop - 0.01, ledge_len, gb - 0.01, gb + front_h, gw / 2, fext),                  # low front lip
            box(end_stop - 0.01, end_stop + corner_len, gb - 0.01, gb + corner_h, z_snug, fext),     # front corner supports
            box(ledge_len - corner_len, ledge_len, gb - 0.01, gb + corner_h, z_snug, fext)]
    return diff(union(body), [cyly(0, 0, ly0 - 1, ly1 + 1, pin_d / 2 + hole_clr, 56), sphere(bump_x, ly0 + 0.2, 0, dimple_r)])   # dimple for the clip's bump

def ledge_at(j, ang=0.0, lift=0.0):
    l = build_ledge(); l.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-ang), [0, 1, 0]))
    l.apply_translation([pin_x, lift, hz_j(j)]); return l

# ------------------------------------------------------------------ lock peg (axis z, head at the bottom)
def build_peg():
    shaft = plate_t + plate_z0 + peg_hole_depth - 0.4
    return union([cylz(0, 0, 0, peg_head_h, peg_head_r, 48), cylz(0, 0, peg_head_h - 0.01, peg_head_h + shaft, peg_r, 40)])

def peg_at(foot_y):                                   # assembled: head on the plate front, shaft through clip into the strip
    p = build_peg(); p.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))     # shaft toward -z
    p.apply_translation([0, foot_y + peg_y, plate_z0 + plate_t + peg_head_h]); return p

# ------------------------------------------------------------------ exports and kits
FOOT0 = 30.0                                          # first clip foot (peg hole y = 52 = 12 + 20*2)

def stack_scene(N, strip_m, clips, ledge_l=None, ang=None):
    n_strips = 1 if FOOT0 + 60 * (N - 1) + clip_y1 <= strip_h else 2
    asm = [place(strip_m, 0, 240.0 * i) for i in range(n_strips)]
    for j in range(N):
        y = FOOT0 + 60.0 * j
        asm += [place(clips[j], 0, y), place(ledge_at(j, 0 if ang is None else ang[j]), 0, y), peg_at(y)]
    return asm, n_strips

if __name__ == "__main__":
    os.makedirs("simple", exist_ok=True)
    strip = build_strip(); ledge = build_ledge(); peg = build_peg(); clips = [build_clip(j) for j in range(6)]
    out = {"wall_strip": to_print(strip, "strip"), "ledge": to_print(ledge, "ledge"), "lock_peg": to_print(peg, "peg")}
    for j, c in enumerate(clips): out[f"hinge_clip_j{j}"] = to_print(c, "clip")
    for n, m in out.items():
        m.export(f"simple/{n}.stl")
        print(f"{n:15s} watertight={m.is_watertight} size={np.round(m.extents, 1)} overhang>45deg={overhang_report(m)} mm2")
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    src = open("render_clip.py").read(); exec(src[src.index("def raster("):src.index("def panel(")])
    grey, orange, dk, blue = (0.75, 0.75, 0.78), (0.95, 0.6, 0.1), (0.3, 0.3, 0.35), (0.2, 0.5, 0.85)
    for N in (2, 3, 4, 5, 6):
        d = f"simple/kit_{N}_cars"; os.makedirs(d, exist_ok=True)
        for f in os.listdir(d): os.remove(f"{d}/{f}")
        asm, ns = stack_scene(N, strip, clips)
        trimesh.util.concatenate(asm).export(f"{d}/assembled_demo.stl")
        to_print(strip, "strip").export(f"{d}/wall_strip.stl")
        for j in range(N): to_print(clips[j], "clip").export(f"{d}/hinge_clip_j{j}.stl")
        to_print(ledge, "ledge").export(f"{d}/ledge.stl"); to_print(peg, "peg").export(f"{d}/lock_peg.stl")
        # print plates (256 mm bed): clips in a row, ledges and pegs
        row, x = [], 0.0
        for j in range(N):
            p = to_print(clips[j], "clip"); p.apply_translation([x, 0, 0]); row.append(p); x += p.extents[0] + 6
        trimesh.util.concatenate(row).export(f"{d}/plate_clips.stl")
        col, y = [], 0.0
        for _ in range(N):
            p = to_print(ledge, "ledge"); p.apply_translation([0, y, 0]); col.append(p); y += p.extents[1] + 6
        trimesh.util.concatenate(col).export(f"{d}/plate_ledges.stl")
        pr, x = [], 0.0
        for _ in range(N):
            p = to_print(peg, "peg"); p.apply_translation([x, 0, 0]); pr.append(p); x += 2 * peg_head_r + 4
        trimesh.util.concatenate(pr).export(f"{d}/plate_pegs.stl")
        top = FOOT0 + 60.0 * (N - 1) + clip_y1
        fig, axs = plt.subplots(1, 2, figsize=(11, 6.5), dpi=100)
        axs[0].imshow(raster(asm, [grey] * ns + sum([[dk, orange, (0.9, 0.2, 0.2)] for _ in range(N)], []), 12, 28, (420, 640), [[-50, 0, -5], [130, 240 * ns, 60]])); axs[0].set_title(f"{N} cars"); axs[0].axis("off")
        asm2, _ = stack_scene(N, strip, clips, ang=[0, 40, 75, 20, 60, 30][:N])
        axs[1].imshow(raster(asm2, [grey] * ns + sum([[dk, orange, (0.9, 0.2, 0.2)] for _ in range(N)], []), 50, 30, (420, 640), [[-50, 0, -5], [130, 240 * ns, 110]])); axs[1].set_title("ledges open"); axs[1].axis("off")
        fig.savefig(f"{d}/preview.png", bbox_inches="tight"); plt.close(fig)
        open(f"{d}/BOM.md", "w").write(f"""# {N}-car display kit
| Part | File | Qty | Print |
|---|---|---|---|
| Wall strip | wall_strip.stl | {ns} | rear face down, no supports |
| Hinge clip, depth j = 0..{N-1} | hinge_clip_j0..j{N-1}.stl | 1 each | standing, brim, no supports |
| Lock peg | lock_peg.stl | {N} | head down |
| Ledge | ledge.stl | {N} | standing |
Plates: plate_clips.stl, plate_ledges.stl, plate_pegs.stl (256 mm bed).
Mount: screw the strip(s) to the wall (second strip: press it straight onto the first strip's dovetail from the front first). Slide each clip onto the strip from the top; clip j with its foot
at y = {FOOT0:.0f} + 60 j mm (its lock hole then lines up with a peg hole in the strip). Push a peg through the clip's hole into the strip hole. Drop each ledge on its pin. The closed ledge clicks into a dimple (lift the ledge about 1 mm to open it).
Stack height {top:.0f} mm.
""")
        print(f"kit {N}: strips {ns}, top {top:.0f} mm")
