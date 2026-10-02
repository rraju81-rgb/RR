"""Printable clip system: 25 mm dovetail wall strip + slide-on hinge clip with a self-locking snap hinge.
Usage: python3 build_clip.py   -> clip/*.stl  (every STL is exported in PRINT orientation, +z up)
Design rules (after the user's feedback that the hook version could not be printed):
  * every part is a straight extrusion in its print direction (pillars, plates, a 45 degree dovetail), so no supports
  * wall strip: 25 mm wide dovetail rail, printed front face down. The clip slides on from the top and cannot be pulled
    off forwards (45 degree jaws behind the rail head). No separate hooks, no slots.
  * lock: no extra part. A flexible tongue on the clip has a bump that snaps into a groove in the ledge barrel when
    the ledge is closed; opening pushes the tongue aside. A small nub on the clip also clicks into dimples in the strip,
    so the clip stays at the height you put it.
  * the ledge just drops onto the clip's pin (also removable). Rack depth step j is built into the ledge, so the clip is one part.
Needs: pip install trimesh manifold3d numpy.  Units mm.
Assembly frame: x right, y up, z out of the wall; strip front face is z = 0, strip centre x = 0."""
import os
import numpy as np
import trimesh

# ---- card (measure these) ----
card_w, card_h, card_t, blister_h = 105, 165, 1.2, 42

# ---- wall strip (<= 1 inch wide) ----
strip_w, strip_h, strip_t = 18.0, 240.0, 4.0      # front width, length, thickness (rear width = strip_w - 2*strip_t: 45 degree sides)
hole_d, csk_d = 5.0, 10.0                          # 5 mm screw hole, 45 degree countersink
hole_ys = (20.0, 120.0, 220.0)                      # mirrored about the middle
dimple_ys = [10.0 + 20 * k for k in range(12)]      # clip nub clicks into these (20 mm pitch)
dimple_r, dimple_depth = 1.0, 0.6
stopper_h, stopper_z = 10.0, 3.6                       # bottom stopper block on the base strip (clip foot ends up at y = 20)
# press-fit stacking: two flat tabs stick out of the top end and push into two pockets in the bottom end of the next strip
tab_hw0, tab_hw1, tab_len = 2.5, 3.5, 8.0           # dovetail tongue: half width at the root and at the tip, length (full strip thickness)
press = 0.10                                         # tab is this much wider than its pocket (total), pocket is 0.4 deeper

# ---- clip ----
clr = 0.45                                          # clearance between clip and rail
plate_z0, plate_t, arm_t = 0.5, 3.0, 2.6
clip_y0, clip_y1 = -10.0, 20.0                      # clip plate length (gusset below the foot runs down to clip_y0)
nub_r, nub_h = 0.9, 0.65

# ---- ledge / hinge ----
ledge_h, gutter_d, slop = 12.0, 6.0, 0.3
rear_wall = front_wall = 3.2
thumb_out = 8.0
step = 5.4                                           # depth step between neighbouring racks (built into ledge_j)
card_w, card_h, card_t, blister_h = 105, 165, 1.2, 42
gw = card_t + 2 * slop
half_d = rear_wall + gw / 2
end_stop = 9.0
ledge_len = end_stop + card_w - thumb_out
pin_d, pin_clr = 4.0, 0.3
bar_r = 4.4
foot_h = 3.5
pin_x = -5.0                                         # pin axis (clip coordinates, x=0 is the strip centre)
ly0 = foot_h + 0.4                                   # ledge sits on the foot flange
ly1 = ly0 + ledge_h

# ---- snap lock ----
tg_t, tg_h = 1.0, 8.0
tg_x = pin_x - 5.2 - tg_t                            # tongue left face
bump_r, groove_r = 1.4, 1.6
relief_r, relief_a0, relief_a1 = 3.5, 85.0, 160.0       # barrel relief (barrel-frame angles, deg from +x toward +z)                          # bump tip pokes 0.6 mm into the barrel's path

assert step >= rear_wall + slop + card_t + 0.4
hz = plate_z0 + plate_t + 0.7 + bar_r                # pin axis stand-off from the strip front face

def box(x0, x1, y0, y1, z0, z1): return trimesh.creation.box(bounds=[[x0, y0, z0], [x1, y1, z1]])
def cylz(x, y, z0, z1, r, n=48):
    m = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=n); m.apply_translation([x, y, (z0 + z1) / 2]); return m
def cyly(x, z, y0, y1, r, n=64):
    m = trimesh.creation.cylinder(radius=r, height=y1 - y0, sections=n)
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    m.apply_translation([x, (y0 + y1) / 2, z]); return m
def union(ms): return trimesh.boolean.union(ms, engine="manifold")
def diff(a, bs): return trimesh.boolean.difference([a, union(bs)], engine="manifold")
def hz_j(j): return hz + j * step

def hull(pts): return trimesh.convex.convex_hull(np.array(pts, float))

def prism_x(poly_zy, x0, x1):
    """prism with polygon given in (z, y), extruded along x"""
    return hull([(x, y, z) for x in (x0, x1) for z, y in poly_zy])

def prism_z(poly_xy, z0, z1):
    """convex polygon in (x, y) extruded along z"""
    return hull([(x, y, z) for z in (z0, z1) for x, y in poly_xy])

def prism_y(poly_xz, y0, y1):
    """prism with convex polygon given in (x, z), extruded along y"""
    return hull([(x, y, z) for y in (y0, y1) for x, z in poly_xz])

def to_print(m, kind):
    R = trimesh.transformations.rotation_matrix
    T = {"clip": R(np.pi / 2, [1, 0, 0]), "ledge": R(np.pi / 2, [1, 0, 0]), "pin": np.eye(4),
         "strip": R(np.pi, [1, 0, 0]), "strip_up": np.eye(4)}[kind]       # clip: +y up. ledge: gutter opens upward. strip: front face down
    m = m.copy(); m.apply_transform(T); m.apply_translation(-m.bounds[0]); return m

# ---------------------------------------------------------------- wall strip
def build_strip(base=False):
    """base=True: bottom strip of a stack. A stopper block closes the bottom end so a clip slides down onto it and stops with its foot at y = 20."""
    r = strip_w / 2; rr = r - strip_t
    s = prism_y([(-r, 0), (r, 0), (rr, -strip_t), (-rr, -strip_t)], 0, strip_h)      # dovetail: wide at the front
    tabs = [prism_z([(-tab_hw0, strip_h - 0.01), (tab_hw0, strip_h - 0.01), (tab_hw1, strip_h + tab_len), (-tab_hw1, strip_h + tab_len)], -strip_t, 0)]   # dovetail tongue, wider at the tip
    stop = [box(-strip_w / 2, strip_w / 2, 0, stopper_h, 0, stopper_z)] if base else []     # self stopper
    s = union([s] + tabs + stop)
    cuts = []
    if not base:        # dovetail pocket in the bottom end, through the whole thickness, 0.05 mm narrower per side than the tongue (press fit)
        h = lambda y: tab_hw0 + (tab_hw1 - tab_hw0) * y / tab_len - press / 2
        cuts.append(prism_z([(-h(-1.0), -1.0), (h(-1.0), -1.0), (h(tab_len + 0.4), tab_len + 0.4), (-h(tab_len + 0.4), tab_len + 0.4)], -strip_t - 1, 1))
    for y in hole_ys:
        cuts.append(cylz(0, y, -strip_t - 1, 1, hole_d / 2, 48))
        zc0 = -(csk_d - hole_d) / 2                                   # countersink: clean frustum, 45 degrees
        pts = [(r_ * np.cos(a), y + r_ * np.sin(a), z_) for r_, z_ in ((hole_d / 2, zc0), (csk_d / 2, 0.0)) for a in np.linspace(0, 2 * np.pi, 48, endpoint=False)]
        cuts += [hull(pts), cylz(0, y, 0, 1, csk_d / 2, 48)]
    for y in dimple_ys[(1 if base else 0):]:
        d = trimesh.creation.icosphere(subdivisions=2, radius=dimple_r); d.apply_translation([0, y, dimple_r - dimple_depth]); cuts.append(d)
    return diff(s, cuts)

# ---------------------------------------------------------------- clip (origin: strip centre x=0, y=0 = bottom of the foot flange)
def build_clip(k=1, j=0):
    """clip with k hinge stations (j = depth step: the pin stands out j*step further, so racks shingle without a stepped ledge), 60 mm apart (one station per card). origin: strip centre x=0, y=0 = foot bottom of station 0"""
    pitch = 60.0
    hz = hz_j(j)                                                     # shadows the module-level hz
    pe = plate_z0 + plate_t
    cy0 = clip_y0                                                    # every clip has the same plate height
    y1 = pitch * (k - 1) + clip_y1
    r = strip_w / 2 + clr + 0.1; ax = r + 0.3 + arm_t              # jaw inner face runs parallel to the rail's 45 degree side, 0.25 mm off it
    parts = [box(-ax, ax, cy0, y1, plate_z0, plate_z0 + plate_t)]
    zt = -strip_t + 0.4                                              # jaw tip height (stays clear of the wall)
    for sgn in (1, -1):
        x1 = r + plate_z0; x2 = r + zt
        poly = [(sgn * x1, plate_z0), (sgn * x2, zt), (sgn * (x2 + arm_t), zt), (sgn * ax, -0.3), (sgn * ax, plate_z0 + 0.1)]
        parts.append(prism_y(poly, cy0, y1))
    z_front = hz + bar_r
    xl, xr = tg_x, pin_x + bar_r
    for m in range(k):
        o = pitch * m
        if m == 0:      # footing: a solid block that sits on the bed and carries the foot flange (no overhang, same plate height for every depth)
            parts += [box(xl, xr, cy0, o + foot_h, pe - 0.1, hz), cyly(pin_x, hz, cy0, o + foot_h, bar_r)]
        else:           # upper stations of a multi-station clip: foot flange + 45 degree gusset
            parts += [box(xl, xr, o, o + foot_h, pe - 0.1, hz), cyly(pin_x, hz, o, o + foot_h, bar_r),
                      prism_x([(pe - 0.1, o), (z_front, o), (pe - 0.1, o - (z_front - pe + 0.1))], xl, xr)]
        parts.append(cyly(pin_x, hz, o + foot_h - 0.1, o + ly1 + 2.0, pin_d / 2, 32))                                       # pin
        ty0 = o + foot_h - 0.1
        tz0 = max(pe - 0.1, hz - 6.0)                                                                                          # tongue is a 7 mm fin; deeper racks get a rigid wall behind it
        if hz - 6.0 > pe: parts.append(box(tg_x, tg_x + tg_t + 1.6, ty0, ty0 + tg_h + 0.1 + (ly0 + 1.5 - foot_h), pe - 0.1, hz - 6.0 + 0.1))
        parts += [box(tg_x, tg_x + tg_t, ty0, ty0 + tg_h + 0.1 + (ly0 + 1.5 - foot_h), tz0, hz + 1.0),   # tongue
                  cyly(tg_x + tg_t, hz, o + ly0 + 1.0, o + ly1 - 1.0, bump_r, 32)]
        nub = trimesh.creation.icosphere(subdivisions=2, radius=nub_r); nub.apply_translation([0, o + 10.0, plate_z0 + nub_r - nub_h]); parts.append(nub)
    return union(parts)

# ---------------------------------------------------------------- ledge for rack position j (pin axis at x=0,z=0 ; body stepped back by j*step)
def build_ledge(j=0):
    oz = j * step
    body = [cyly(0, 0, ly0, ly1, bar_r),
            box(0, end_stop, ly0, ly1, -half_d, oz + half_d),
            box(0, ledge_len, ly0, ly1 - gutter_d, oz - half_d, oz + half_d),
            box(0, ledge_len, ly0, ly1, oz - half_d, oz - gw / 2), box(0, ledge_len, ly0, ly1, oz + gw / 2, oz + half_d)]
    cuts = [cyly(0, 0, ly0 - 1, ly1 + 1, pin_d / 2 + pin_clr, 48),
            cyly(-(bar_r + 0.8), 0, ly0 - 1, ly1 + 1, groove_r, 32)]
    # relief: once the ledge is a little open the barrel is cut back so the tongue relaxes (no constant drag)
    for a in np.arange(relief_a0, relief_a1, 5.0):
        q = [(r_ * np.cos(np.radians(b)), r_ * np.sin(np.radians(b))) for r_ in (relief_r, bar_r + 1.5) for b in (a, a + 5.0)]
        cuts.append(prism_y(q, ly0 - 1, ly1 + 1))
    return diff(union(body), cuts)

def ledge_at(j, ang=0.0, stagger_in_clip=False):
    l = build_ledge(0 if stagger_in_clip else j); l.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-ang), [0, 1, 0]))
    l.apply_translation([pin_x, 0, hz_j(j) if stagger_in_clip else hz]); return l

# ---------------------------------------------------------------- printability
def overhang_report(m, thresh_deg=43.0, bed_tol=0.05):
    n = m.face_normals; bad = (n[:, 2] < -np.cos(np.radians(thresh_deg))) & (m.triangles_center[:, 2] > bed_tol)
    if not bad.any(): return 0.0, None
    return round(m.area_faces[bad].sum(), 1), np.unique(np.round(m.triangles_center[bad, 2], 1))[:6].tolist()

def place(m, x, y): m = m.copy(); m.apply_translation([x, y, 0]); return m

STACKS = {2: [2], 3: [3], 4: [2, 2], 5: [3, 2], 6: [3, 3]}      # cars -> clip pieces (hinge stations per piece)

def stack_assembly(N, strips, clips, y0=20.0):
    """N racks, 60 mm apart, first clip foot at y0 (a multiple of 20 so the nubs sit in dimples)"""
    asm, y, j = [], y0, 0
    for i in range(strips): asm.append(place(strip_b if i == 0 else strip_m, 0, 240.0 * i))
    for k in STACKS[N]:
        asm.append(place(clips[k], 0, y))
        for m in range(k): asm.append(place(ledge_at(j), 0, y + 60.0 * m)); j += 1
        y += 60.0 * k
    return asm

if __name__ == "__main__":
    os.makedirs("clip", exist_ok=True)
    strip_m = build_strip(); strip_b = build_strip(True); clips = {1: build_clip(1), 2: build_clip(2), 3: build_clip(3)}
    ledges = [build_ledge(j) for j in range(6)]
    out = {"wall_strip": to_print(strip_m, "strip"), "wall_strip_base": to_print(strip_b, "strip_up")}
    for k, c in clips.items(): out[f"hinge_clip_x{k}"] = to_print(c, "clip")
    for j, l in enumerate(ledges): out[f"ledge_j{j}"] = to_print(l, "ledge")
    for j in range(6): out[f"hinge_clip_j{j}"] = to_print(build_clip(1, j), "clip")
    for n, m in out.items():
        m.export(f"clip/{n}.stl"); oa, lv = overhang_report(m)
        print(f"{n:14s} watertight={m.is_watertight} size={np.round(m.extents, 1)} overhang>45deg={oa} mm2 z={lv}")
    for N in (2, 3, 4, 5, 6):      # separate clip per rack, depth grows with the rack number
        strips = 1 if N <= 4 else 2
        asm = [place(strip_b if i == 0 else strip_m, 0, 240.0 * i) for i in range(strips)]
        for jj in range(N):
            y = 20.0 + 60.0 * jj
            asm += [place(build_clip(1, jj), 0, y), place(ledge_at(jj, 0, True), 0, y)]
        trimesh.util.concatenate(asm).export(f"clip/separate_{N}_cars_demo.stl")
    for N in STACKS:
        strips = 1 if N <= 4 else 2
        trimesh.util.concatenate(stack_assembly(N, strips, clips)).export(f"clip/stack_{N}_cars_demo.stl")
