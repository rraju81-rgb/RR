#!/usr/bin/env python3
"""renders/fit_overlay.png - cross-sections of every grip over the reference outlines.

black  : the measured paddle tongue, 30 x 16 mm   -> sits inside the 30.2 x 16.0 mm slot of every grip
grey   : the reference bore (from the 3MF)        -> now filled; the two white side pockets are the sealed hollow core
dashed : reference crest envelope (bore + 3.5 mm)  -> no grip exceeds it
colour : the grip's section at mid-height (z = 64)
"""
import sys
import warnings
from pathlib import Path

import matplotlib
import numpy as np
import trimesh
from shapely.geometry import Polygon, box

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grip_core import Frame, PADDLE_W, PADDLE_T  # noqa: E402
from designs import DESIGNS  # noqa: E402
from verify_fitment import section_solid  # noqa: E402
from extract_reference_profile import load_3mf_mesh, section_polys  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
Z = 64.0


def main():
    F = Frame()
    cav = Polygon(F.ring)
    ref = load_3mf_mesh(ROOT / "reference" / "PickleballGrip_1.3mf")
    ref_polys = section_polys(ref, Z)
    env = cav.buffer(F.crest, 32)
    fig, axs = plt.subplots(2, 5, figsize=(20, 8.6))
    cols = plt.cm.tab10.colors
    for k, (ax, (name, label, _)) in enumerate(zip(axs.flat, DESIGNS)):
        m = trimesh.load(ROOT / "stl" / f"{name}.stl", process=True)
        m.merge_vertices()
        solid, _ = section_solid(m, Z)
        for g in (solid.geoms if hasattr(solid, "geoms") else [solid]):
            ax.fill(*g.exterior.xy, color=cols[k], alpha=0.35, lw=0)
            ax.plot(*g.exterior.xy, color=cols[k], lw=1.2)
            for h in g.interiors:
                ax.fill(*h.xy, color="white", lw=0)
                ax.plot(*h.xy, color=cols[k], lw=1.0)
        ax.plot(*env.exterior.xy, "k--", lw=0.8, label="reference crest envelope")
        ax.plot(*ref_polys[1].exterior.xy, color="#8A93A0", ls=(0, (3, 2)), lw=1.0, label="reference bore (now solid)")
        tongue = box(-PADDLE_W / 2, -PADDLE_T / 2, PADDLE_W / 2, PADDLE_T / 2)
        ax.plot(*tongue.exterior.xy, "k-", lw=1.6, label=f"paddle tongue {PADDLE_W:.0f} x {PADDLE_T:.0f} mm")
        ax.set_aspect("equal")
        ax.set_xlim(-22, 22)
        ax.set_ylim(-19.5, 19.5)
        ax.set_title(f"{label}\nsection at z = {Z:.0f} mm", fontsize=11)
        ax.grid(alpha=0.25)
        if k == 0:
            ax.legend(loc="lower left", fontsize=7)
    fig.suptitle("Fitment overlay - paddle slot and sealed hollow core (white) in a solid body around the 30 x 16 mm tongue (black); the outer skin stays inside the reference envelope (dashed)",
                 fontsize=14)
    plt.tight_layout()
    out = ROOT / "renders" / "fit_overlay.png"
    plt.savefig(out, dpi=90)
    print("wrote", out)


if __name__ == "__main__":
    main()
