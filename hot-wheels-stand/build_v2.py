"""Side-Slide Shingle Rack v2: thicker frame, smaller screw holes, symmetric mounting holes,
plus a hinged ("door") variant where each ledge swings on its own vertical pin.
Usage: python3 build_v2.py   -> v2/rack_<N>slot_thick.stl, v2/rack_<N>slot_hinged.stl
Needs: pip install trimesh manifold3d numpy
Orientation: wall plate face on the print bed (z up = out of the wall), units mm."""
import os
import numpy as np
import trimesh

# ---- card (measure these) ----
card_w, card_h, card_t, blister_h = 105, 165, 1.2, 42
pitch = 55

# ---- thicker frame (v1 values in brackets) ----
back_t     = 5      # wall plate thickness (3)
spine_w    = 18     # spine / end stop width (14)
ledge_h    = 12     # ledge height (10)
gutter_d   = 6
slop       = 0.3
rear_wall  = 3.2    # (2.4)
front_wall = 3.2    # (2.4)
thumb_out  = 8
step       = 5.4    # depth step between cards (4.6), needs >= rear_wall+slop+card_t+0.4

# ---- smaller screw holes (v1: 9 mm head / 4.5 mm slot) ----
hole_d, csk_d = 3.5, 7.0   # through hole and countersink head diameter

# ---- hinge ----
hx        = spine_w / 2    # pin x
pin_d     = 4.0
pin_clr   = 0.3            # radial clearance pin <-> barrel
bar_r     = 4.4            # barrel / lug outer radius
lug_h     = 3.5            # height (y) of each fixed lug
lug_gap   = 0.4            # vertical clearance barrel <-> lug

# ---- latch: swivel bar per ledge. A post on the plate carries a bar that hangs down in front of the
# ledge's end stop (blocks the swing). Flip it up to open. Sits at x < spine_w so the card never touches it.
lat_x      = spine_w - 2.0  # post x
lat_up     = 6.0            # post height above the ledge top
lat_len    = 11.0           # bar length below the pivot (reaches 5 mm onto the ledge front)
lat_tail   = 4.0            # grip tail above the pivot
lat_w      = 3.4            # bar width
lat_t      = 1.8            # bar thickness
lat_clr    = 0.6            # air gap between ledge front face and bar
post_r     = 1.5
lat_hole_r = post_r + 0.3

gw = card_t + 2 * slop
ledge_w = spine_w + card_w - thumb_out
assert step >= rear_wall + slop + card_t + 0.4
assert ledge_h - gutter_d + blister_h <= pitch

def box(x0, x1, y0, y1, z0, z1):
    return trimesh.creation.box(bounds=[[x0, y0, z0], [x1, y1, z1]])

def cyly(x, z, y0, y1, r, sections=64):
    """cylinder with its axis along y"""
    m = trimesh.creation.cylinder(radius=r, height=y1 - y0, sections=sections)
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    m.apply_translation([x, (y0 + y1) / 2, z])
    return m

def cylz(x, y, z0, z1, r, sections=48):
    m = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=sections)
    m.apply_translation([x, y, (z0 + z1) / 2])
    return m

def union(ms):
    return trimesh.boolean.union(ms, engine="manifold")

def diff(a, bs):
    return trimesh.boolean.difference([a, union(bs)], engine="manifold")

def plate_height(N, ybase):
    return ybase + (N - 1) * pitch + ledge_h - gutter_d + card_h + 5

def hole_ys(N, ybase):
    """Mounting holes: one in the first gap above the bottom ledge, its mirror image near the
    top, and (tall racks) one in the middle, snapped to the centre of the nearest ledge gap."""
    H = plate_height(N, ybase)
    yb = ybase + (ledge_h + pitch) / 2          # centre of gap 0-1
    ys = [yb, H - yb]
    if N >= 4:
        k = int(round((H / 2 - ybase - ledge_h / 2 - pitch / 2) / pitch))
        k = min(max(k, 0), N - 2)
        ys.insert(1, ybase + k * pitch + (ledge_h + pitch) / 2)
    return ys, H

def zc(j, base):
    return base + j * step

def ledge_body(j, y0, base):
    """ledge: floor + rear/front wall + gutter, from x=x_start to ledge_w"""
    z0 = zc(j, base) - slop - rear_wall
    z1 = zc(j, base) + card_t + slop + front_wall
    zg0, zg1 = zc(j, base) - slop, zc(j, base) + card_t + slop
    return z0, z1, zg0, zg1

def build_thick(N):
    """v1 design with the thicker frame and symmetric countersunk holes."""
    base = rear_wall + slop   # rear wall of the lowest ledge starts at the plate face
    ys, H = hole_ys(N, 0)
    parts = [box(0, spine_w, 0, H, -back_t, 0)]
    for j in range(N):
        y0 = j * pitch
        z0, z1, zg0, zg1 = ledge_body(j, y0, base)
        parts += [
            box(0, spine_w, y0, y0 + ledge_h, 0, z1),
            box(spine_w, ledge_w, y0, y0 + ledge_h - gutter_d, z0, z1),
            box(spine_w, ledge_w, y0, y0 + ledge_h, z0, zg0),
            box(spine_w, ledge_w, y0, y0 + ledge_h, zg1, z1),
        ]
        bump = trimesh.creation.icosphere(subdivisions=2, radius=0.7)
        bump.apply_translation([spine_w + card_w - thumb_out - 12, y0 + ledge_h - gutter_d + 2, zg0 - 0.4])
        parts.append(bump)
    rack = union(parts)
    return diff(rack, screw_holes(ys))

def screw_holes(ys):
    cuts = []
    for y in ys:
        cuts.append(cylz(hx, y, -back_t - 1, 1, hole_d / 2, 32))
        # countersink: cone from hole_d at depth to csk_d at the front face of the plate
        cone = trimesh.creation.cone(radius=csk_d / 2, height=(csk_d - hole_d) / 2, sections=32)
        cone.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))  # tip down
        cone.apply_translation([hx, y, -(csk_d - hole_d) / 2 + (csk_d - hole_d) / 2 * 0])
        cuts.append(cone)
        cuts.append(cylz(hx, y, 0, 1, csk_d / 2, 32))
    return cuts

def build_hinged(N, parts_out=False, latch=False):
    """Plate + fixed lugs + pins (one body) and N free-swinging ledges. Each ledge swings out
    (+z) around a vertical pin at x = hx, like a door."""
    ybase = lug_h + lug_gap + 0.5      # room under ledge 0 for its lower lug
    base = bar_r + 0.8 + 0.6 - 0.6     # zc(0): barrel clears the plate by 0.8
    ys, H = hole_ys(N, ybase)
    fixed = [box(0, spine_w, 0, H, -back_t, 0)]
    ledges = []
    bars = []
    for j in range(N):
        y0 = ybase + j * pitch
        z0, z1, zg0, zg1 = ledge_body(j, y0, base)
        hz = (z0 + z1) / 2
        yl0, yl1 = y0 - lug_gap - lug_h, y0 + ledge_h + lug_gap + lug_h
        for a, b in ((yl0, y0 - lug_gap), (y0 + ledge_h + lug_gap, yl1)):   # fixed lugs
            fixed.append(box(hx - bar_r, hx + bar_r, a, b, -0.01, hz))
            fixed.append(cyly(hx, hz, a, b, bar_r))
        fixed.append(cyly(hx, hz, yl0, yl1, pin_d / 2, 32))                    # pin (fixed to lugs)
        # swinging ledge: barrel + body from the pin to the right
        body = [cyly(hx, hz, y0, y0 + ledge_h, bar_r),
                box(hx, ledge_w, y0, y0 + ledge_h - gutter_d, z0, z1),
                box(hx, ledge_w, y0, y0 + ledge_h, z0, zg0),
                box(hx, ledge_w, y0, y0 + ledge_h, zg1, z1),
                box(hx, spine_w, y0, y0 + ledge_h, z0, z1)]                     # end stop
        bump = trimesh.creation.icosphere(subdivisions=2, radius=0.7)
        bump.apply_translation([spine_w + card_w - thumb_out - 12, y0 + ledge_h - gutter_d + 2, zg0 - 0.4])
        body.append(bump)
        ledge = diff(union(body), [cyly(hx, hz, y0 - 1, y0 + ledge_h + 1, pin_d / 2 + pin_clr, 48)])
        ledges.append((ledge, hz, y0))
        if latch:
            yp = y0 + ledge_h + lat_up
            zb0 = z1 + lat_clr; zb1 = zb0 + lat_t
            fixed.append(cylz(lat_x, yp, -0.01, zb1 + 0.3 + 1.2, post_r, 32))      # post
            fixed.append(cylz(lat_x, yp, zb1 + 0.3, zb1 + 1.5, post_r + 1.2, 32))  # retaining cap
            bar = union([box(lat_x - lat_w / 2, lat_x + lat_w / 2, yp - lat_len, yp + lat_tail, zb0, zb1),
                         cylz(lat_x, yp, zb0, zb1, lat_w / 2 + 0.6, 32)])
            bar = diff(bar, [cylz(lat_x, yp, zb0 - 1, zb1 + 1, lat_hole_r, 32)])
            bars.append((bar, (lat_x, yp)))
    fixed = diff(union(fixed), screw_holes(ys))
    fixed.apply_translation([0, 0, back_t]); [l[0].apply_translation([0, 0, back_t]) for l in ledges]
    [b[0].apply_translation([0, 0, back_t]) for b in bars]
    if parts_out == 'latch':
        return fixed, [(l, hz + back_t, y0) for l, hz, y0 in ledges], bars
    if parts_out:
        return fixed, [(l, hz + back_t, y0) for l, hz, y0 in ledges]
    return trimesh.util.concatenate([fixed] + [l[0] for l in ledges] + [b[0] for b in bars])

if __name__ == "__main__":
    os.makedirs("v2", exist_ok=True)
    for N in (2, 3, 4, 5, 6):
        tag = "2slot_test" if N == 2 else f"{N}slot"
        t = build_thick(N)
        t.apply_translation([0, 0, back_t])
        t.export(f"v2/rack_{tag}_thick.stl")
        h = build_hinged(N)
        h.export(f"v2/rack_{tag}_hinged.stl")
        hl = build_hinged(N, latch=True); hl.export(f"v2/rack_{tag}_hinged_latch.stl")
        print(tag, "latch:", hl.is_watertight, "bodies:", len(hl.split(only_watertight=False)))
        print(tag, "thick:", t.is_watertight, np.round(t.extents, 1), "| hinged:",
              h.is_watertight, np.round(h.extents, 1), "bodies:", len(h.split(only_watertight=False)),
              "holes y:", np.round(hole_ys(N, lug_h + lug_gap + 0.5)[0], 1))
