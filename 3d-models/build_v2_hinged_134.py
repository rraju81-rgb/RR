"""v2 + backward stop + snap detent: wall mount + 6 swing-out ledges on print-in-place hinges, one STL / one print (lying on its back)."""
import trimesh, numpy as np
from trimesh.creation import box, cylinder
from trimesh.transformations import rotation_matrix
OP = lambda op, *m: getattr(trimesh.boolean, op)(list(m), engine='manifold')

PITCH, STEP = 55.0, 4.6          # tier spacing (Y) and tier step out from the wall (Z)
G = 0.4                          # print-in-place clearance
R = 5.5                          # knuckle radius
CONE = 3.5                       # 45-degree cone-pin base radius
PLATE = 6.0                      # wall plate thickness
AX = 14.0 + G + R                # hinge axis X (just outboard of the 14 mm wide spine)
HOLES = [28.0, 138.0, 303.0]
SHELF, TOOTH = 4.4, 2.0          # shelf depth below the ledge, tooth length
TX0, TX1 = 30.0, 34.0           # tooth x-span (10-14 mm from the hinge axis)
BX, BZ, BUMP_R, BUMP_H = 27.0, 4.5, 1.6, 0.6   # detent bump position / size
A_TOP, F_BOT, F_TOP, B_BOT, TOP = 7.6, 8.0, 14.0, 14.4, 22.0   # knuckle stack, relative to tier base

def ycyl(r, y0, y1, x, z, sec=96):
    c = cylinder(radius=r, height=y1 - y0, sections=sec)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0]))
    c.apply_translation([x, (y0 + y1)/2, z]); return c

def ycone(r0, y0, direction, x, z):
    """45-degree cone along Y: radius r0 at y0, tip `direction` (+1/-1) after r0 mm."""
    c = trimesh.creation.cone(radius=r0, height=r0, sections=96)   # base at z=0, tip at z=r0
    c.apply_transform(trimesh.transformations.rotation_matrix(-direction*np.pi/2, [1, 0, 0]))
    c.apply_translation([x, y0, z]); return c

# ---------- fixed wall mount ----------
rack = trimesh.load('rack_6slot_wide.stl')
cuts = []
for k in range(6):
    y0 = PITCH*k
    cuts += [box(bounds=[[14, y0-.001, -1], [200, y0+10.001, 40]]), box(bounds=[[-1, y0-.001, 3], [14.001, y0+10.001, 40]])]
fixed = OP('difference', rack, OP('union', *cuts))
fixed = OP('union', fixed, box(bounds=[[0, 0, 0], [14, 449, PLATE]]))
for y in HOLES:                                   # keyholes -> plain 3 mm holes
    fixed = OP('union', fixed, box(bounds=[[2, y-5, 0], [12, y+15, PLATE]]))

# ---------- ledge template (stood up, groove aligned to the old slot) ----------
ledge = trimesh.load('ledge_134.stl')
bore = cylinder(radius=4.6, height=18.0, sections=96); bore.apply_translation([6.6, 6.6, 9.0])
ledge = OP('union', ledge, bore)
ledge.apply_transform(np.array([[1,0,0,0],[0,0,1,0],[0,-1,0,11.2],[0,0,0,1]], float))

moving, fixed_parts, info = [], [fixed], []
for k in range(6):
    y0 = PITCH*k
    zb = 0.0 if k == 0 else 1.3 + STEP*k          # back face of this tier's ledge
    az = zb + R                                   # hinge axis Z (knuckle tangent to the ledge back)
    L = ledge.copy(); L.apply_translation([0, y0, STEP*k])
    L = OP('intersection', L, box(bounds=[[AX, y0-1, zb], [300, y0+30, 60]]))   # drop old end boss

    # moving: ledge + two knuckles, cone sockets, clearance around the fixed knuckle
    m = OP('union', L, ycyl(R, y0, y0+A_TOP, AX, az), ycyl(R, y0+B_BOT, y0+TOP, AX, az))
    clear = OP('union', ycyl(R+G, y0+A_TOP, y0+B_BOT, AX, az),
               box(bounds=[[0, y0+A_TOP, -1], [AX+G, y0+B_BOT, 60]]))
    sock = OP('union', ycone(CONE+G*np.sqrt(2), y0+F_BOT, -1, AX, az), ycone(CONE+G*np.sqrt(2), y0+F_TOP, +1, AX, az))
    m = OP('difference', m, OP('union', clear, sock))

    # fixed: knuckle + cone pins + bracket back to the plate (full 22 mm tall where the ledge can't reach)
    f = OP('union', ycyl(R, y0+F_BOT, y0+F_TOP, AX, az),
           ycone(CONE, y0+F_BOT, -1, AX, az), ycone(CONE, y0+F_TOP, +1, AX, az),
           box(bounds=[[0, y0+F_BOT, 0], [AX, y0+F_TOP, az]]),
           box(bounds=[[0, y0, 0], [14.0 - G, y0+TOP, az]]))

    # ---- v3: back-stop shelf (tooth + fence) and gravity snap detent under the ledge root ----
    rot = lambda mesh, th: mesh.apply_transform(rotation_matrix(np.radians(-th), [0, 1, 0], point=[AX, 0, az])) or mesh
    zf = zb + (9.0 if k == 0 else 7.7)                        # ledge floor front edge
    shelf = OP('union',
               box(bounds=[[0, y0-SHELF, 0], [21.3, y0-G, zf]]),          # stays out of the widget zone (x>21.7, z<zb)
               box(bounds=[[21.3, y0-SHELF, zb], [40, y0-G, zf]]),
               box(bounds=[[0, y0-SHELF, 0], [14.0, y0+0.01, az]]))       # ties the shelf into the bracket
    tooth = box(bounds=[[TX0, y0-TOOTH, zb+2.5], [TX1, y0+0.5, zb+5.0]])  # hangs under the ledge floor
    swept = []
    for th in range(0, 132, 2):                                   # channel = tooth sweep (+0.4) while opening only
        t = box(bounds=[[TX0-G, y0-TOOTH-G, zb+2.5-G], [TX1+G, y0+G, zb+5.0+G]]); swept.append(rot(t, th))
    shelf = OP('difference', shelf, OP('union', *swept))
    bump = ycone(BUMP_R, y0-G, +1, BX, zb+BZ); bump.apply_scale(1)       # 45deg cone ...
    bump = OP('intersection', bump, box(bounds=[[0, y0-G, 0], [200, y0-G+BUMP_H, 60]]))   # ... cut to 0.6 mm tall
    f = OP('union', f, shelf, bump)
    m = OP('union', m, tooth)
    m = OP('difference', m, ycyl(BUMP_R+G, y0-1, y0-G+BUMP_H+G, BX, zb+BZ))   # detent pocket in the floor
    fixed_parts.append(f); moving.append(m); info.append((k, round(zb, 2), round(az, 2)))

fixed = OP('union', *fixed_parts)
for y in HOLES:
    h = cylinder(radius=1.5, height=PLATE+4, sections=64); h.apply_translation([7, y, PLATE/2])
    fixed = OP('difference', fixed, h)

out = trimesh.util.concatenate([fixed] + moving)
print('tiers (k, back z, axis z):', info, ' axis x:', AX)
print('fixed watertight', fixed.is_watertight, 'vol', round(fixed.volume, 1))
for i, m in enumerate(moving): print(' ledge', i, m.is_watertight, round(m.volume, 1), len(m.split()))
print('bounds', np.round(out.bounds, 2).tolist())
out.export('rack_v2_hinged_134.stl')
trimesh.util.concatenate(moving).export('_moving.stl'); fixed.export('_fixed.stl')
np.save('_axes.npy', np.array([[AX, PITCH*k, (0.0 if k == 0 else 1.3+STEP*k)+R] for k in range(6)]))
