import trimesh, numpy as np
U = lambda *m: trimesh.boolean.union(list(m), engine='manifold')
PITCH, STEP = 55.0, 4.6           # arm spacing (Y) and tier step out from the wall (Z) per slot
rack = trimesh.load('rack_6slot_wide.stl')
ledge = trimesh.load('ledge_120.stl')

# ledge prep: fill hinge bore, stand it up (ledge Z -> up, ledge Y -> out of wall), groove at z 3.7..5.5
bore = trimesh.creation.cylinder(radius=4.6, height=18.0, sections=96); bore.apply_translation([6.6, 6.6, 9.0])
ledge = U(ledge, bore)
ledge.apply_transform(np.array([[1,0,0,0],[0,0,1,0],[0,-1,0,11.2],[0,0,0,1]], float))

# strip all six arms, keep the 3 mm spine back plate
cuts = []
for k in range(6):
    y0 = PITCH*k
    cuts += [trimesh.creation.box(bounds=[[14,y0-0.001,-1],[200,y0+10.001,40]]),
             trimesh.creation.box(bounds=[[-1,y0-0.001,3],[14.001,y0+10.001,40]])]
body = trimesh.boolean.difference([rack, U(*cuts)], engine='manifold')

parts = [body]
for k in range(6):
    l = ledge.copy(); l.apply_translation([0, PITCH*k, STEP*k])
    # back face of each ledge sits where the old arm's back was (z = 1.3 + 4.6k; wall at z=0 for the bottom one),
    # keeping the 0.4 mm clearance for the widget standing in the ledge below
    zback = 0.0 if k == 0 else 1.3 + STEP*k
    l = trimesh.boolean.intersection([l, trimesh.creation.box(bounds=[[-5,-5,zback],[200,500,60]])], engine='manifold')
    parts.append(l)
    if k:  # spine block tying the ledge's end boss back to the wall plate (x 0..14 only, outside the widget area)
        parts.append(trimesh.creation.box(bounds=[[0, PITCH*k, 0],[14, PITCH*k+22, zback+2.4]]))
out = U(*parts)
print(out.is_watertight, np.round(out.bounds,2).tolist(), round(out.volume,1), len(out.split()))
out.export('rack_6ledge_120.stl')
