"""Modular side-slide rack: SKADIS-style slotted wall board + separate hinge/latch modules + ledges.
Usage: python3 build_modular.py   -> modular/*.stl
  board_tile.stl            140 x 240 slotted board (5 x 15 mm slots, 20 mm grid), 6 symmetric screw holes
  hinge_module_j<N>.stl     hook-in hinge + latch unit, N = card position (sets how far the pin stands out)
  ledge.stl                 card ledge (barrel, end stop, gutter); one design for every position
  hinge_pin.stl             4 mm pin, drops through the module's lugs and the ledge barrel
  latch_bar.stl             swivel bar, presses onto the module's latch post
  demo_assembly.stl         board + 3 hinged racks, for checking only
Needs: pip install trimesh manifold3d numpy.  Units mm.
Frame: x right, y up, z out of the wall. Board front face is z = 0; the board is z -5..0, rear standoffs -8..-5."""
import os
import numpy as np
import trimesh

# ---- card (measure these) ----
card_w, card_h, card_t, blister_h = 105, 165, 1.2, 42

# ---- board (SKADIS-like) ----
slot_w, slot_h, grid = 5.0, 15.0, 20.0
board_w, board_h, board_t = 140, 240, 5
standoff, rim = 3.0, 6.0            # rear standoff (room for the hook prongs) and rim width
hole_d, csk_d = 3.5, 7.0

# ---- hook (module -> board slot) ----
hook_w   = 4.4
stem_y   = (-7.3, -1.5)             # stem rests on the slot bottom (slot centre = 0)
prong_y  = (-13.5, -1.5)
prong_z  = (-7.4, -5.2)
hook_dx  = -10.0                    # hooks sit 10 mm left of the pin axis
hook_gap = 40.0                     # two hooks, one slot pitch (2 grid steps) apart
plate_t, plate_clr = 3.0, 0.2

# ---- ledge / hinge ----
ledge_h, gutter_d, slop = 12.0, 6.0, 0.3
rear_wall = front_wall = 3.2
thumb_out = 8.0
step = 5.4                          # depth step between neighbouring racks (>= rear+slop+card_t+0.4)
gw = card_t + 2 * slop
half_d = rear_wall + gw / 2         # ledge half depth (z) around the pin axis
end_stop = 9.0                      # x from pin to start of gutter
ledge_len = end_stop + card_w - thumb_out
pin_d, pin_clr = 4.0, 0.3
bar_r, lug_h, lug_gap = 4.4, 3.5, 0.4
lug_hole_r = pin_d / 2 + 0.15

# ---- latch ----
lat_x, lat_up, lat_len, lat_tail = 6.0, 6.0, 11.0, 4.0
lat_w, lat_t, lat_clr = 3.4, 1.8, 0.6
post_r, bump_r = 1.5, 1.8
bar_hole_r = 1.65

assert step >= rear_wall + slop + card_t + 0.4
assert ledge_h - gutter_d + blister_h <= 80   # rack pitch is 2 slot pitches = 80 mm

yc = hook_gap / 2                   # ledge centre height, relative to the lower hook
ly0, ly1 = yc - ledge_h / 2, yc + ledge_h / 2

def box(x0, x1, y0, y1, z0, z1):
    return trimesh.creation.box(bounds=[[x0, y0, z0], [x1, y1, z1]])

def cylz(x, y, z0, z1, r, n=48):
    m = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=n)
    m.apply_translation([x, y, (z0 + z1) / 2]); return m

def cyly(x, z, y0, y1, r, n=64):
    m = trimesh.creation.cylinder(radius=r, height=y1 - y0, sections=n)
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    m.apply_translation([x, (y0 + y1) / 2, z]); return m

def union(ms): return trimesh.boolean.union(ms, engine="manifold")
def diff(a, bs): return trimesh.boolean.difference([a, union(bs)], engine="manifold")

def hz_of(j): return plate_clr + plate_t + bar_r + 0.8 + j * step

# ---------------------------------------------------------------- board
def slot_centres():
    out = []
    for i in range(board_w // 20):
        x = 10 + 20 * i
        y0 = 20 if i % 2 == 0 else 40
        out += [(x, y) for y in np.arange(y0, board_h - 10, 40)]
    return out

def hole_centres():
    return [(x, y) for x in (60, 80) for y in (12, board_h / 2, board_h - 12)]

def build_board():
    parts = [box(0, board_w, 0, board_h, -board_t, 0)]
    parts += [box(0, rim, 0, board_h, -board_t - standoff, -board_t), box(board_w - rim, board_w, 0, board_h, -board_t - standoff, -board_t),
              box(0, board_w, 0, rim, -board_t - standoff, -board_t), box(0, board_w, board_h - rim, board_h, -board_t - standoff, -board_t)]
    parts += [cylz(x, y, -board_t - standoff, -board_t, 7) for x, y in hole_centres()]
    b = union(parts)
    cuts = [box(x - slot_w / 2, x + slot_w / 2, y - slot_h / 2, y + slot_h / 2, -board_t - standoff - 1, 1) for x, y in slot_centres()]
    for x, y in hole_centres():
        cuts.append(cylz(x, y, -board_t - standoff - 1, 1, hole_d / 2, 32))
        cone = trimesh.creation.cone(radius=csk_d / 2, height=(csk_d - hole_d) / 2, sections=32)
        cone.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
        cuts.append(cone); cuts.append(cylz(x, y, 0, 1, csk_d / 2, 32))
    return diff(b, cuts)

# ---------------------------------------------------------------- hinge module
# origin: x = pin axis, y = centre of the lower hook slot, z = board front face
def build_module(j):
    hz = hz_of(j)
    z_plate0 = plate_clr
    parts = [box(-14, 14, -8, hook_gap + 8, z_plate0, z_plate0 + plate_t)]
    for k in (0, 1):
        y = k * hook_gap
        parts.append(box(hook_dx - hook_w / 2, hook_dx + hook_w / 2, y + stem_y[0], y + stem_y[1], prong_z[1], z_plate0 + 0.5))
        parts.append(box(hook_dx - hook_w / 2, hook_dx + hook_w / 2, y + prong_y[0], y + prong_y[1], prong_z[0], prong_z[1] + 0.01))
    # lugs: below and above the ledge, with the pin hole
    lugs = [(ly0 - lug_gap - lug_h, ly0 - lug_gap), (ly1 + lug_gap, ly1 + lug_gap + lug_h)]
    for a, b in lugs:
        parts += [box(-bar_r, bar_r, a, b, z_plate0 + plate_t - 0.1, hz), cyly(0, hz, a, b, bar_r)]
    # latch post with a snap ring at the top
    yp = ly1 + lat_up
    zb0 = hz + half_d + lat_clr; zb1 = zb0 + lat_t
    parts += [cylz(lat_x, yp, z_plate0 + plate_t - 0.1, zb1 + 1.0, post_r, 32), cylz(lat_x, yp, zb1 + 0.15, zb1 + 1.0, bump_r, 32)]
    m = union(parts)
    cuts = [cyly(0, hz, ly1 + lug_gap - 1, lugs[1][1] + 1, lug_hole_r, 32),                  # through the top lug
            cyly(0, hz, lugs[0][0] + 1.0, ly0 - lug_gap + 1, lug_hole_r, 32)]                # blind in the bottom lug
    return diff(m, cuts)

# ---------------------------------------------------------------- ledge (pin axis at x=0, z=0)
def build_ledge():
    body = [cyly(0, 0, ly0, ly1, bar_r),
            box(0, ledge_len, ly0, ly1 - gutter_d, -half_d, half_d),
            box(0, ledge_len, ly0, ly1, -half_d, -gw / 2),
            box(0, ledge_len, ly0, ly1, gw / 2, half_d),
            box(0, end_stop, ly0, ly1, -half_d, half_d)]
    bump = trimesh.creation.icosphere(subdivisions=2, radius=0.7)
    bump.apply_translation([ledge_len - 12, ly1 - gutter_d + 2, -gw / 2 - 0.4]); body.append(bump)
    return diff(union(body), [cyly(0, 0, ly0 - 1, ly1 + 1, pin_d / 2 + pin_clr, 48)])

def build_pin():
    y0, y1 = ly0 - lug_gap - lug_h + 1.2, ly1 + lug_gap + lug_h
    return union([cylz(0, 0, 0, y1 - y0, pin_d / 2, 32),
                  cylz(0, 0, y1 - y0, y1 - y0 + 2.0, 3.2, 32)])      # printed standing (z = pin axis)

def pin_at(hz):
    p = build_pin(); y0 = ly0 - lug_gap - lug_h + 1.2
    p.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0]))   # pin axis z -> y
    p.apply_translation([0, y0, hz]); return p

# ---------------------------------------------------------------- latch bar (pivot at origin, hangs along -y)
def build_bar():
    bar = union([box(-lat_w / 2, lat_w / 2, -lat_len, lat_tail, 0, lat_t), cylz(0, 0, 0, lat_t, lat_w / 2 + 0.6, 32)])
    return diff(bar, [cylz(0, 0, -1, lat_t + 1, bar_hole_r, 32)])

def bar_at(j, ang=0):
    hz = hz_of(j); zb0 = hz + half_d + lat_clr
    b = build_bar()
    b.apply_transform(trimesh.transformations.rotation_matrix(np.radians(ang), [0, 0, 1]))
    b.apply_translation([lat_x, ly1 + lat_up, zb0]); return b

def place(mesh, x, y): m = mesh.copy(); m.apply_translation([x, y, 0]); return m

if __name__ == "__main__":
    os.makedirs("modular", exist_ok=True)
    board = build_board(); board.export("modular/board_tile.stl")
    ledge, pin, bar = build_ledge(), build_pin(), build_bar()
    ledge.export("modular/ledge.stl"); pin.export("modular/hinge_pin.stl"); bar.export("modular/latch_bar.stl")
    mods = [build_module(j) for j in range(6)]
    for j, m in enumerate(mods): m.export(f"modular/hinge_module_j{j}.stl")
    asm = [board]
    for i in range(3):                       # three racks at 80 mm pitch in slot column 0, pin at x = 20
        j, x, y = i, 20.0, 20.0 + 80 * i
        parts = [mods[j], pin_at(hz_of(j)), bar_at(j)]
        l = ledge.copy(); l.apply_translation([0, 0, hz_of(j)]); parts.append(l)
        asm += [place(p, x, y) for p in parts]
    trimesh.util.concatenate(asm).export("modular/demo_assembly.stl")
    for n, m in [("board", board), ("ledge", ledge), ("pin", pin), ("bar", bar)] + [(f"module_j{j}", m) for j, m in enumerate(mods)]:
        print(f"{n:10s} watertight={m.is_watertight} bodies={len(m.split(only_watertight=False))} size={np.round(m.extents, 1)}")
