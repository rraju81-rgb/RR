"""Printable clip system: 25 mm dovetail wall strip + slide-on hinge clip with a self-locking snap hinge.
Usage: python3 build_clip.py   -> clip/*.stl  (every STL is exported in PRINT orientation, +z up)
Design rules (after the user's feedback that the hook version could not be printed):
  * every part is a straight extrusion in its print direction (pillars, plates, a 45 degree dovetail), so no supports
  * wall strip: 25 mm wide dovetail rail, printed front face down. The clip slides on from the top and cannot be pulled
    off forwards (45 degree jaws behind the rail head). No separate hooks, no slots.
  * hinge lock: no extra part. A flexible tongue on the clip has a bump that snaps into a groove in the ledge barrel when
    the ledge is closed; opening pushes the tongue aside.
  * height lock (zip-tie style ratchet): the strip has 6 mm sawtooth steps, the clip has a spring pawl. The clip clicks upward one step at a time
    and cannot slide down; pull the release tab on the clip to let it slide down.
  * the ledge just drops onto the clip's pin (also removable). Rack depth step j is built into the ledge, so the clip is one part.
Needs: pip install trimesh manifold3d numpy.  Units mm.
Assembly frame: x right, y up, z out of the wall; strip front face is z = 0, strip centre x = 0."""
import os
import numpy as np
import trimesh

# ---- card (measure these) ----
card_w, card_h, card_t, blister_h = 105, 165, 1.2, 42

# ---- wall strip (<= 1 inch wide) ----
strip_w, strip_h, strip_t = 25.0, 240.0, 4.0      # front width, length, thickness (rear width = strip_w - 2*strip_t: 45 degree sides)
hole_d, csk_d = 5.0, 10.0                          # 5 mm screw hole, 45 degree countersink
hole_ys = (20.0, 120.0, 220.0)                      # mirrored about the middle
# ratchet teeth (zip-tie style): sawtooth steps every 6 mm along the front face, vertical wall on the low side (locks against sliding down), 14 degree ramp on the high side
tooth_p, tooth_d = 6.0, 1.5                           # pitch, depth
tooth_x0, tooth_x1 = 5.6, 10.8                       # tooth lane
tooth_y0, tooth_y1 = 18.0, 240.0                      # first wall at y = 15 (clear of the female Z), last ramp ends at the strip end
# stacking: Z-lock (zig-zag joint) - male Z on the top end, matching female Z in the bottom end of the next strip
z_h, z_x0, z_x1 = 8.0, 2.0, -6.0                    # Z-lock (zig-zag joint): height, x where the diagonal starts at the bottom / ends at the top (45 degrees)
z_fit = 0.12                                       # clearance of the female Z around the male Z


# ---- clip ----
clr = 0.45                                          # clearance between clip and rail
plate_z0, plate_t, arm_t = 0.5, 3.0, 2.4
clip_y0, clip_y1 = -10.0, 28.0                      # clip plate length (gusset below the foot runs down to clip_y0)
leaf_t, leaf_x0, leaf_x1, slit = 2.0, 5.0, 11.4, 1.6     # pawl leaf cut into the plate: thickness, x range, slit width (root at the bottom, free end on top)
pawl_y, pawl_h, pawl_out, pawl_w = 16.0, 1.9, 1.2, 4.6  # pawl tip: lower (locking) face at y = 15 above the foot, height, how far it reaches into the teeth, width
leaf_len = 24.0                                         # pawl leaf runs from the plate's lower part up to y = 22 above the foot; the plate frame closes around its top (no free-standing parts)
tab_h, tab_out = 6.0, 4.0                               # release tab: a thumb ridge on the leaf's front face (height, how far it sticks out of the leaf), 45 degree underside

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

def intersection_(ms): return trimesh.boolean.intersection(ms, engine="manifold")

def offset_convex(poly, d):
    """grow a convex polygon outward by d (line-offset / intersect)"""
    P = np.array(poly, float); c = P.mean(0); n = len(P); lines = []
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]; t = (b - a) / np.linalg.norm(b - a); nrm = np.array([t[1], -t[0]])
        if np.dot(nrm, (a + b) / 2 - c) < 0: nrm = -nrm
        lines.append((a + nrm * d, t))
    out = []
    for i in range(n):
        (p1, t1), (p2, t2) = lines[i - 1], lines[i]
        A = np.array([t1, -t2]).T; k = np.linalg.solve(A, p2 - p1); out.append(tuple(p1 + t1 * k[0]))
    return out

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
         "strip": np.eye(4), "strip_up": np.eye(4)}[kind]       # clip: +y up. ledge: gutter opens upward. strip: rear face down (ratchet teeth face up, 45 degree rail sides)
    m = m.copy(); m.apply_transform(T); m.apply_translation(-m.bounds[0]); return m

# ---------------------------------------------------------------- wall strip
def build_strip():
    """25 mm dovetail rail (front 25 wide, rear 17 wide, 4 thick) with a male Z-lock (zig-zag joint) on the top end and the matching female Z in the bottom end,
    three 5 mm countersunk screw holes (mirrored about the middle) and a ratchet lane (6 mm sawtooth steps) for the clip's spring pawl."""
    r = strip_w / 2; rr = r - strip_t
    s = prism_y([(-r, 0), (r, 0), (rr, -strip_t), (-rr, -strip_t)], 0, strip_h)
    r2 = strip_w / 2
    zpoly = [(z_x0, 0.0), (r2, 0.0), (r2, z_h), (z_x1, z_h)]                              # male Z (quadrilateral: bottom bar, diagonal, top bar) at the strip's top end
    male = intersection_([prism_y([(-r, 0), (r, 0), (rr, -strip_t), (-rr, -strip_t)], strip_h - 0.01, strip_h + z_h),
                          prism_z([(x, strip_h + y) for x, y in zpoly], -strip_t - 1, 1)])
    s = union([s, male]); cuts = []
    fem = offset_convex([(x, y) for x, y in zpoly], z_fit)                                  # female Z in the bottom end, same shape, slightly larger
    cuts.append(prism_z(fem, -strip_t - 1, 1))
    for y in hole_ys:
        cuts.append(cylz(0, y, -strip_t - 1, 1, hole_d / 2, 48))
        zc0 = -(csk_d - hole_d) / 2
        pts = [(r_ * np.cos(a), y + r_ * np.sin(a), z_) for r_, z_ in ((hole_d / 2, zc0), (csk_d / 2, 0.0)) for a in np.linspace(0, 2 * np.pi, 48, endpoint=False)]
        cuts += [hull(pts), cylz(0, y, 0, 1, csk_d / 2, 48)]
    teeth = [prism_x([(0.5, y), (-tooth_d, y), (0.0, y + tooth_p), (0.5, y + tooth_p)], tooth_x0, tooth_x1) for y in np.arange(tooth_y0, tooth_y1 - 1e-6, tooth_p)]
    cuts.append(union(teeth))
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
    cuts = []
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
        lx0, lx1 = leaf_x0, leaf_x1
        ltop = o + leaf_len
        yb = o + pawl_y
        parts.append(prism_x([(plate_z0 + 0.05, yb), (plate_z0 - pawl_out - 0.5, yb), (plate_z0 + 0.05, yb + pawl_h)], (lx0 + lx1) / 2 - pawl_w / 2, (lx0 + lx1) / 2 + pawl_w / 2))   # pawl tip: vertical face below, ramp above
        zt0 = plate_z0 + leaf_t
        parts.append(prism_x([(zt0 - 0.05, ltop - tab_h), (zt0 + tab_out, ltop - tab_h + tab_out), (zt0 + tab_out, ltop), (zt0 - 0.05, ltop)], lx0, lx1))   # release tab: thumb ridge inside the plate, 45 degree underside
        cuts += [box(lx0 - slit, lx0, o, ltop + slit, plate_z0 - 1.0, pe + 0.1),                       # slit left
                 box(lx1, lx1 + slit, o, ltop + slit, plate_z0 - 1.0, pe + 0.1),                       # slit right
                 box(lx0 - slit, lx1 + slit, ltop, ltop + slit, plate_z0 - 1.0, pe + 0.1),             # slit above the free end (the plate frame closes over it)
                 box(lx0, lx1, o, ltop, plate_z0 + leaf_t, pe + 0.1)]                                   # front recess leaves the 1.4 mm leaf
    return diff(union(parts), cuts) if cuts else union(parts)

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
    for i in range(strips): asm.append(place(strip_m, 0, 240.0 * i))
    for k in STACKS[N]:
        asm.append(place(clips[k], 0, y))
        for m in range(k): asm.append(place(ledge_at(j), 0, y + 60.0 * m)); j += 1
        y += 60.0 * k
    return asm

if __name__ == "__main__":
    os.makedirs("clip", exist_ok=True)
    strip_m = build_strip(); clips = {1: build_clip(1), 2: build_clip(2), 3: build_clip(3)}   # x2/x3 (legacy multi-station) are built for the demos only
    ledges = [build_ledge(j) for j in range(6)]
    out = {"wall_strip": to_print(strip_m, "strip")}
    out["ledge"] = to_print(ledges[0], "ledge")
    for j in range(6): out[f"hinge_clip_j{j}"] = to_print(build_clip(1, j), "clip")
    for n, m in out.items():
        m.export(f"clip/{n}.stl"); oa, lv = overhang_report(m)
        print(f"{n:14s} watertight={m.is_watertight} size={np.round(m.extents, 1)} overhang>45deg={oa} mm2 z={lv}")
    for N in (2, 3, 4, 5, 6):      # separate clip per rack, depth grows with the rack number
        strips = 1 if N <= 4 else 2
        asm = [place(strip_m, 0, 240.0 * i) for i in range(strips)]
        for jj in range(N):
            y = 20.0 + 60.0 * jj
            asm += [place(build_clip(1, jj), 0, y), place(ledge_at(jj, 0, True), 0, y)]
        trimesh.util.concatenate(asm).export(f"clip/separate_{N}_cars_demo.stl")
