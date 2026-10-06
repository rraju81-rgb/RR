"""Shorten the wall strip of both wall-mount racks so it ends just above the top card.
Top ledge floor starts at y = 275, a card stands 3 mm up on the floor and is 165 mm tall -> card top at 443 mm.
The strip is cut at 445 mm (2 mm above the card). Holes (y = 28, 138, 303) and ledges are untouched.
Run after build_6ledge_130_3mmholes.py / build_v2_hinged_134.py."""
import numpy as np, trimesh
Y_TOP = 445.0
for f in ('rack_6ledge_130_3mmholes.stl', 'rack_v2_hinged_134.stl'):
    m = trimesh.load(f); before = m.bounds.copy()
    keep = trimesh.creation.box(bounds=[[-50, -50, -50], [250, Y_TOP, 100]])
    out = trimesh.boolean.intersection([m, keep], engine='manifold')
    lost = m.volume - out.volume
    print(f, np.round(before[:, 1], 1).tolist(), '->', np.round(out.bounds[:, 1], 1).tolist(),
          'removed', round(lost, 1), 'mm3', out.is_watertight, len(out.split()))
    out.export(f)
