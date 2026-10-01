"""Writes the 4 printed parts for every size. python3 side_export.py [N ...]
side/N<n>/: module_R.stl, module_L.stl, wall_frame.stl, tie_bar.stl, BOM.md  (+ assembly/ for viewing)"""
import sys, os, json
import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix
import side_cad as C

def module_mesh(P, tag):
    parts = [d["mesh"] for n, d in P.items() if d.get("module") == tag]
    return trimesh.util.concatenate(parts)

def print_orient(m, sign):
    """card side (x = +-47.5) down on the bed"""
    m = m.copy()
    m.apply_transform(rotation_matrix(-np.pi / 2 * sign, [0, 1, 0]))
    b = m.bounds
    m.apply_translation([-(b[0][0] + b[1][0]) / 2, -(b[0][1] + b[1][1]) / 2, -b[0][2]])
    return m

def export(N, results):
    R, P = C.build(N)
    d = f"side/N{N}"
    os.makedirs(d + "/assembly", exist_ok=True)
    mR = print_orient(module_mesh(P, "R"), 1)
    mL = print_orient(module_mesh(P, "L"), -1)
    mR.export(f"{d}/module_R.stl")
    mL.export(f"{d}/module_L.stl")
    P["frame"]["mesh"].export(f"{d}/wall_frame.stl")
    P["tie"]["mesh"].export(f"{d}/tie_bar.stl")
    for phi, nm in ((0, "closed"), (90, "open")):
        pm = C.posed(R, P, phi)
        trimesh.util.concatenate(list(pm.values()) + [C.spring_mesh(R, phi, 1), C.spring_mesh(R, phi, -1)]).export(f"{d}/assembly/assembly_{nm}.stl")
    r = results.get(str(N), {})
    sp = r.get("spring", {})
    lf = 50.0
    open(f"{d}/BOM.md", "w").write(f"""# {N}-stall rack: parts and hardware
**4 printed parts:** `module_R.stl`, `module_L.stl` (mirror image), `wall_frame.stl`, `tie_bar.stl`.
Each module is ONE print: cheek, two bars, {N} cross arms and all pins print in place (0.4 mm clearances).
Print with the card side down (the files are already laid that way). Module size {mR.extents[0]:.0f} x {mR.extents[1]:.0f} x {mR.extents[2]:.0f} mm.

| Hardware | Qty | Notes |
|---|---|---|
| Extension spring | 2 | rate {sp.get('k_N_per_mm', 0):.4f} N/mm, free length about {lf:.0f} mm, initial tension about {sp.get('k_N_per_mm', 0) * lf:.2f} N; force {sp.get('force_closed_N_each', 0):.1f} N closed to {sp.get('force_open_N_each', 0):.1f} N open. Hooks on the post of each bar and the frame tab (anchor height {R.d_sp:.0f} mm) |
| Magnet 6 x 2 mm | 4 | pockets in the top of each bar and in the frame fingers |
| Wall screw M4 + plug | 10 | 3 per module flange (through frame and flange) and 2 per frame post |
| M3 x 10 screw + washer | 1 | holds the tie bar |

Open reach (how far the bars stick out of the wall plane): {R.Lb:.0f} mm. Depth behind the bars when closed: {R.D + 12:.0f} mm.
Assembly: screw the frame to the wall, screw each module onto the frame post, slide the tie bar through the square holes
in both bars (head on the right), fit the washer and screw on the left, fit the springs and magnets.
""")

if __name__ == "__main__":
    results = json.load(open("side_test_results.json")) if os.path.exists("side_test_results.json") else {}
    for N in [int(a) for a in sys.argv[1:]] or [1, 2, 3, 4, 5, 6]:
        export(N, results)
        print("exported", N, sorted(f for f in os.listdir(f"side/N{N}") if f.endswith(".stl")))
