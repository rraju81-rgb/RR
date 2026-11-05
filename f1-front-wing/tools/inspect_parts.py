"""Print per-part stats for a folder of STL files (bbox, volume, watertight)."""
import sys, re, glob, os
import numpy as np
import trimesh

def part_id(path):
    m = re.search(r'obj_(\d+)_.*\.obj_(\d+)\.stl$', os.path.basename(path))
    return (int(m.group(1)), int(m.group(2))) if m else (9999, 9999)

files = sorted(glob.glob(os.path.join(sys.argv[1], '*.stl')), key=part_id)
print(f"{'obj':>4} {'tris':>6} {'wt':>3} {'vol_cm3':>8}  {'min (x,y,z)':>26}  {'max (x,y,z)':>26}  {'size (x,y,z)':>24}")
for f in files:
    m = trimesh.load(f, force='mesh', process=True)
    lo, hi = m.bounds
    sz = hi - lo
    print(f"{part_id(f)[0]:>4} {len(m.faces):>6} {('Y' if m.is_watertight else 'n'):>3} {m.volume/1000:>8.1f}  "
          f"{lo[0]:8.1f},{lo[1]:8.1f},{lo[2]:8.1f}  {hi[0]:8.1f},{hi[1]:8.1f},{hi[2]:8.1f}  {sz[0]:7.1f},{sz[1]:7.1f},{sz[2]:7.1f}")
