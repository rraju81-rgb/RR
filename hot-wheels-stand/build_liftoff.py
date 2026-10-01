"""Lift-off tray version: wall frame + removable tray (the side-slide rack).
Writes frame_<N>slot.stl and tray_<N>slot.stl for N = 3..6.
The tray hangs on three pegs on the frame's back plate (keyhole fit). Lift it up
12 mm and pull it forward, lay it flat on a table with the cards facing up.
Needs: pip install trimesh manifold3d numpy"""
import numpy as np
import trimesh
import build_stl as b

fw        = 12.0     # frame post / top bar width
gap       = 0.5      # clearance between tray plate and the posts
fplate_t  = 3.0      # frame back plate thickness
top_gap   = 14.0     # clear space above the tray (needed to lift it off the pegs)
top_bar_h = 14.0
post_extra = 2.0     # posts stand this far in front of the tray's front face
stem_d, head_d, head_h = 4.2, 8.6, 2.2   # peg: head chamfered 45 degrees, no supports

plate_w = b.spine_w + b.card_w + 1.0     # tray plate spans the card width

def frustum(x, y, z0, z1, d0, d1, n=48):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    v = [[x + d0 / 2 * np.cos(t), y + d0 / 2 * np.sin(t), z0] for t in a] + \
        [[x + d1 / 2 * np.cos(t), y + d1 / 2 * np.sin(t), z1] for t in a] + \
        [[x, y, z0], [x, y, z1]]
    f = []
    for k in range(n):
        k2 = (k + 1) % n
        f += [[k, k2, n + k2], [k, n + k2, n + k]]       # side
        f += [[2 * n, k2, k], [2 * n + 1, n + k, n + k2]] # caps
    m = trimesh.Trimesh(np.array(v), np.array(f))
    m.fix_normals()
    return m

def tray(N):
    return b.build(N, plate_w=plate_w)          # plate on z = 0..3

def peg_ys(N):
    return sorted({b.ledge_h + 18, (N // 2 - 1) * b.pitch + b.ledge_h + 18,
                   (N - 1) * b.pitch + b.ledge_h + 18})

def frame(N):
    H = (N - 1) * b.pitch + b.ledge_h - b.gutter_d + b.card_h + 5   # tray height
    tray_depth = b.zc(N - 1) + b.card_t + b.slop + b.front_wall + b.back_t
    depth = tray_depth + post_extra
    x0, x1 = -gap - fw, plate_w + gap + fw
    ytop = H + top_gap + top_bar_h
    parts = [
        b.box(x0, x1, -4, ytop, -fplate_t, 0),                               # back plate
        b.box(x0, -gap, -4, ytop, -fplate_t, depth),                         # left post
        b.box(plate_w + gap, x1, -4, ytop, -fplate_t, depth),                # right post
        b.box(x0, x1, ytop - top_bar_h, ytop, -fplate_t, 12),                # top bar
    ]
    for y in [v + 12 for v in peg_ys(N)]:   # peg sits at the TOP of each keyhole slot (hung pose)
        x = b.spine_w / 2
        parts.append(b.cyl(x, y, -0.5, b.back_t + 0.3 + 0.01, stem_d, 32))
        parts.append(frustum(x, y, b.back_t + 0.3, b.back_t + 0.3 + head_h, stem_d, head_d))
    f = b.union(parts)
    # two countersunk wall screws in the top bar (heads above the tray, accessible)
    cuts = []
    for x in (x0 + 30, x1 - 30):
        y = ytop - top_bar_h / 2
        cuts += [b.cyl(x, y, -fplate_t - 1, 13, 4.5, 24), b.cyl(x, y, 3, 13, 9.5, 32)]
    f = trimesh.boolean.difference([f, b.union(cuts)], engine="manifold")
    return f, ytop

if __name__ == "__main__":
    for N in (3, 4, 5, 6):
        t = tray(N)
        f, ytop = frame(N)
        t.export(f"tray_{N}slot.stl")
        f.export(f"frame_{N}slot.stl")
        print(N, "tray", np.round(t.extents, 1), t.is_watertight,
              "| frame", np.round(f.extents, 1), f.is_watertight)
