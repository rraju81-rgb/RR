"""Writes the STL set for every size. python3 foldout_export.py [N ...]
foldout/N<n>/: wall_post_L/R, wall_top_crossbar, wall_bottom_crossbar, panel, b2, spacer (x4),
arm_<j>_L/R (laid flat for printing), assembly_closed.stl, assembly_open.stl, BOM.md"""
import sys, os, json
import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix
import foldout_cad as C

def flat_x_up(m):
    m = m.copy()
    m.apply_transform(rotation_matrix(-np.pi / 2, [0, 1, 0]))     # x axis -> up
    b = m.bounds
    m.apply_translation([-(b[0][0] + b[1][0]) / 2, -(b[0][1] + b[1][1]) / 2, -b[0][2]])
    return m

def export(N, results):
    R, P = C.build(N)
    d = f"foldout/N{N}"
    os.makedirs(d, exist_ok=True)
    names = {"post_L": "wall_post_L", "post_R": "wall_post_R", "top_crossbar": "wall_top_crossbar",
             "bottom_crossbar": "wall_bottom_crossbar", "panel": "panel", "b2": "b2"}
    for k, v in names.items():
        P[k]["mesh"].export(f"{d}/{v}.stl")
    P["spacerH_R"]["mesh"].export(f"{d}/spacer_x4.stl")
    for j in range(N):
        for tag in ("L", "R"):
            flat_x_up(P[f"arm{j}_{tag}"]["mesh"]).export(f"{d}/arm_{j}_{tag}.stl")
    for phi, nm in ((0, "closed"), (90, "open")):
        pm = C.posed(R, P, phi)
        meshes = list(pm.values()) + [C.spring_mesh(R, phi, 1), C.spring_mesh(R, phi, -1)]
        trimesh.util.concatenate(meshes).export(f"{d}/assembly_{nm}.stl")
    r = results.get(str(N), {})
    sp = r.get("spring", {})
    lf = 60.0
    bom = f"""# {N}-stall fold-down rack: bill of materials and settings
Printed (PETG): see the STL files. The arms are exported flat (plate on the bed). The panel and the
wall posts are longer than most print beds; print them in sections, or cut the bars from 6 mm plywood or acrylic.
Overall: panel length {R.L:.0f} mm, depth behind the panel D = {R.D:.1f} mm, open reach about {R.L:.0f} mm.

| Item | Qty | Notes |
|---|---|---|
| Joint bolts M3 x 14 + M3 nut | {4 * N} | arm joints (nut sits in the pocket in the arm) |
| Hinge bolts M3 x 20 + lock nut + 2 spring washers | 4 | hinge H and B2 pivot F; tighten the H pair for hinge friction |
| Spring-post bolts M3 x 22 | 2 | on the panel bar at height {C.A_SP:.0f} mm |
| Extension springs | 2 | rate {sp.get('k_N_per_mm', 0):.4f} N/mm each, free length about {lf:.0f} mm, initial tension about {sp.get('k_N_per_mm', 0) * lf:.2f} N each (initial tension = rate x free length) |
| Magnets 6 x 2 mm | 4 | two on the panel top bar, two on the wall crossbar (pockets 6.2 mm) |
| Wall screws M4 + plugs | 4 | in the post holes at heights {R.d_sp + 20:.0f} mm and {R.L - 30:.0f} mm |
| Spacer tubes (printed) | 4 | spacer_x4.stl |

Spring tensions: {sp.get('force_closed_N_each', 0):.1f} N when closed rising to {sp.get('force_open_N_each', 0):.1f} N when open (each).
Wall anchor height {R.d_sp:.0f} mm. Hinge friction needed to stay put with a spring error of +-10%: {r.get('spring_tolerance_friction_Nmm', {}).get('+-10%', '?')} N mm.
"""
    open(f"{d}/BOM.md", "w").write(bom)

if __name__ == "__main__":
    results = json.load(open("foldout_test_results.json")) if os.path.exists("foldout_test_results.json") else {}
    for N in [int(a) for a in sys.argv[1:]] or [1, 2, 3, 4, 5, 6]:
        export(N, results)
        print("exported", N, len(os.listdir(f"foldout/N{N}")), "files")
