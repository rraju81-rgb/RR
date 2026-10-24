"""The printed grip family on the paddle: catalogue, STL loading and 2-D cuts for the drawings.

The ten grips come from branch claude/kind-volta-vs8ck6 (pickleball_grips, revision 8).  They share one
interface (paddle slot, solid base, M3 screw counterbore, head slits; see geometry.GRIP) and differ only
in the outer surface.  A grip STL is z-up with its butt face at z = 0 and the slot centred on the z axis,
slot width along x; on the paddle that axis becomes y (butt at y = 0) and the grip's y becomes -z.
"""
from __future__ import annotations

import functools
import subprocess
from pathlib import Path

import numpy as np

from .geometry import GRIP

ROOT = Path(__file__).resolve().parent.parent
GRIP_DIR = ROOT / "reference" / "grips"
GRIP_BRANCH = "origin/claude/kind-volta-vs8ck6"
DESIGNS = {"01_vortex_grip": "VORTEX GRIP", "02_cellular_mod": "CELLULAR MOD", "03_tessel_block": "TESSEL-BLOCK",
           "04_logic_grip": "LOGIC-GRIP", "05_neuro_tread": "NEURO-TREAD", "06_carbon_matrix": "CARBON MATRIX",
           "07_voronoi_core": "VORONOI-CORE", "08_topo_flow": "TOPO-FLOW", "09_ergo_contour": "ERGO-CONTOUR",
           "10_hexa_mod": "HEXA-MOD"}
DEFAULT = "06_carbon_matrix"                     # used on the drawings; every design has the same interface
PADDLE_GRIP = {"elongated": "06_carbon_matrix", "hybrid": "01_vortex_grip"}     # shown in the renders
TO_PADDLE = np.array([[1.0, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]])   # (x, y, z) -> (x, z, -y)


def stl_path(gid: str) -> Path:
    """Path of a grip STL, copied out of the grip branch the first time it is needed."""
    p = GRIP_DIR / f"{gid}.stl"
    if not p.exists():
        GRIP_DIR.mkdir(parents=True, exist_ok=True)
        src = f"{GRIP_BRANCH}:pickleball_grips/stl/{gid}.stl"
        r = subprocess.run(["git", "show", src], cwd=ROOT, capture_output=True)
        if r.returncode:
            raise FileNotFoundError(f"{p} is missing and `git show {src}` failed: {r.stderr.decode().strip()}")
        p.write_bytes(r.stdout)
    return p


def load(gid: str = DEFAULT):
    """Grip mesh in paddle coordinates (mm): butt face at y = 0, slot axis on x = z = 0."""
    import trimesh
    m = trimesh.load(stl_path(gid), force="mesh")
    m.apply_transform(TO_PADDLE)
    return m


def mass_g(mesh) -> float:
    """PLA mass at 100 % infill; the STL already holds the sealed hollow core as an inner shell."""
    return mesh.volume / 1000.0 * GRIP.pla_density


def silhouettes(mesh, step: float = 0.5) -> dict[str, np.ndarray]:
    """Outline of the grip in the face view (x against y) and the side view (z against y).

    Each is a closed polygon (N, 2) built from the extents of cross-sections every `step` mm."""
    ys = np.arange(step / 2, GRIP.length, step)
    secs = mesh.section_multiplane(plane_origin=[0, 0, 0], plane_normal=[0, 1, 0], heights=ys)
    face, side = [], []
    for y, s in zip(ys, secs):
        if s is None or not len(s.vertices):
            continue
        v3 = np.c_[s.vertices, np.zeros(len(s.vertices)), np.ones(len(s.vertices))] @ s.metadata["to_3D"].T
        face.append((y, v3[:, 0].min(), v3[:, 0].max()))
        side.append((y, v3[:, 2].min(), v3[:, 2].max()))
    out = {}
    for key, rows in (("face", face), ("side", side)):
        r = np.array(rows)
        y = np.r_[0.0, r[:, 0], GRIP.length]
        lo = np.r_[r[0, 1], r[:, 1], r[-1, 1]]
        hi = np.r_[r[0, 2], r[:, 2], r[-1, 2]]
        out[key] = np.vstack([np.c_[hi, y], np.c_[lo, y][::-1]])[:, [0, 1]]
    return out


def cross_section(mesh, y: float):
    """Shapely (Multi)Polygon of the grip cut at height y, in paddle (x, z) coordinates."""
    from shapely.geometry import MultiPolygon, Polygon
    s = mesh.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
    to_2d = np.array([[1.0, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]])      # (x, y, z) -> (x, z, y)
    p2, _ = s.to_2D(to_2D=to_2d)
    polys = [Polygon(p.exterior.coords, [i.coords for i in p.interiors]) for p in p2.polygons_full]
    return polys[0] if len(polys) == 1 else MultiPolygon(polys)


def long_section(mesh, x: float = 0.0):
    """Shapely (Multi)Polygon of the grip cut by the plane x = const, in paddle (y, z) coordinates."""
    from shapely.geometry import MultiPolygon, Polygon
    s = mesh.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
    to_2d = np.array([[0.0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, -x], [0, 0, 0, 1]])     # (x, y, z) -> (y, z, x)
    p2, _ = s.to_2D(to_2D=to_2d)
    polys = [Polygon(p.exterior.coords, [i.coords for i in p.interiors]) for p in p2.polygons_full]
    return polys[0] if len(polys) == 1 else MultiPolygon(polys)


@functools.lru_cache(maxsize=4)
def drawing_data(gid: str = DEFAULT) -> dict:
    """Everything the drawings need from one grip mesh (cached: slicing a 388 k-triangle mesh takes seconds)."""
    m = load(gid)
    sil = silhouettes(m)
    return dict(gid=gid, name=DESIGNS[gid], mass_g=mass_g(m), face=sil["face"], side=sil["side"],
                sec_e=cross_section(m, 70.0), sec_g=cross_section(m, 120.0), long=long_section(m))


def fit_test_section(z: float = 4.0):
    """Plan section of the fit-test coupon (three slots 15.6 / 16.0 / 16.4 mm), in its own x, y (mm)."""
    import trimesh
    from shapely.geometry import MultiPolygon, Polygon
    m = trimesh.load(stl_path("fit_test_slot"), force="mesh")
    p2, _ = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1]).to_2D(to_2D=np.eye(4))
    polys = [Polygon(p.exterior.coords, [i.coords for i in p.interiors]) for p in p2.polygons_full]
    return polys[0] if len(polys) == 1 else MultiPolygon(polys)


def face_path(gid: str = DEFAULT, tol: float = 0.15) -> str:
    """SVG path data of the grip's face-view outline in model coordinates (x, y; y up), simplified."""
    from shapely.geometry import Polygon
    poly = Polygon(drawing_data(gid)["face"]).simplify(tol)
    return "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in list(poly.exterior.coords)[:-1]) + " Z"
