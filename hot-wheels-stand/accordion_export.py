"""Writes STLs for the accordion hook rack. python3 accordion_export.py
accordion/parts/: link.stl, pivot_pin.stl, hook_pin.stl   (same for every size, print the quantity in the BOM)
accordion/N<n>/:  wall_plate.stl, BOM.md, assembly/assembly_open.stl, assembly_folded.stl"""
import os, json
import numpy as np
import trimesh
import accordion_cad as C

def lay(m, M):
    m = m.copy()
    T = np.eye(4); T[:3, :3] = M
    m.apply_transform(T)
    b = m.bounds
    m.apply_translation([-(b[0][0] + b[1][0]) / 2, -(b[0][1] + b[1][1]) / 2, -b[0][2]])
    return m

SIDE = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float)      # pins/hooks lie on their side, kerf plane vertical

def export_all(results):
    T = C.build_templates()
    os.makedirs("accordion/parts", exist_ok=True)
    lay(T["link"], np.eye(3)).export("accordion/parts/link.stl")
    lay(T["pivot"], SIDE).export("accordion/parts/pivot_pin.stl")
    lay(T["hook"], SIDE).export("accordion/parts/hook_pin.stl")
    for N in range(1, 7):
        A = C.Acc(N)
        d = f"accordion/N{N}"
        os.makedirs(d + "/assembly", exist_ok=True)
        plate = C.wall_plate(A)
        lay(plate, np.eye(3)).export(f"{d}/wall_plate.stl")
        for tag, th, cards in (("open", C.TH_MIN, True), ("folded", C.TH_MAX, False)):
            parts = C.assembly(A, th, dict(T, plate=plate), with_cards=cards)
            trimesh.util.concatenate([m for m, g in parts.values()]).export(f"{d}/assembly/assembly_{tag}.stl")
        r = results.get(str(N), {})
        open(f"{d}/BOM.md", "w").write(f"""# {N}-stall accordion hook rack: print list
Four printed designs (the first three are the same for every size, in `accordion/parts/`):

| Part | File | Qty | How to print |
|---|---|---|---|
| Link | `link.stl` | {2 * A.K} | flat, 5 mm thick, no supports |
| Pivot pin | `pivot_pin.stl` | {2 * A.K} | already laid on its side; the slot in the barb must be vertical |
| Hook pin | `hook_pin.stl` | {N} | already laid on its side; no supports |
| Wall plate | `wall_plate.stl` | 1 | rear face down; the 8 mm groove bridges, no supports |

Hardware: {len(C.screw_points(A))} wall screws M4 (heads 8 mm), nothing else. Printing: PETG, 0.2 mm layers, 3 perimeters, 40% infill. Print links 100% infill if you can.

Size: width {r.get('rack_width_open', 0):.0f} mm open ({r.get('rack_width_closed', 0):.0f} mm folded), height {r.get('height_open', 0):.0f} mm open ({r.get('height_closed', 0):.0f} mm folded), hook spacing {A.w_open:.0f} mm open.
Assembly: screw the plate to the wall, lay the links out (every "/" link goes in the back layer, every "\\\\" link in the front layer), push each pin through
from the front until the barb clicks, hang the cards on the pegs.
""")
    print("exported")

if __name__ == "__main__":
    res = json.load(open("accordion_test_results.json")) if os.path.exists("accordion_test_results.json") else {}
    export_all(res)
