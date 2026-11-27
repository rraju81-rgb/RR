"""CNC machining of the stack mould (PB-MO-003) in aluminium: set-ups, tools, cutting data, toolpaths.

Drawings: PB-MO-004 (machining blueprint of the plates) and PB-MO-005 (CNC machining diagram).
Programs (tools/export_cnc.py):

  OP 00  FIXTURE      20 mm fixture plate carrying the mould's own bolt pattern (tapped M6 with a drill
                      relief), the 2 dowel holes, 6 clamp-stud holes and a relief groove under the profile
  OP 10  each blank   blank on the fixture, dowel pins not fitted yet, toe clamps on the waste: spot,
                      drill the 18 bolt holes, drill and ream the 2 dowel holes (all through)
  OP 20  MAIN A       main plate top face up, on the 2 pins, 18 bolts: Elongated cavity, groove, vents, notches
  OP 30  MAIN B       turned over about X onto the same pins: Hybrid cavity, groove, vents, notches, profile
  OP 20  TOP / BOTTOM clamp plate, teeth side up, on the pins, toe clamps on the waste: seat face, teeth,
                      ramps, notches; M0, fit the bolts; outer profile

Machine coordinates (all set-ups, G54): X along the plate = paddle y, X0 at the butt reference (the rib
starts at X5, the handle points to -X); Y = -paddle x, Y0 on the centre line; Z0 on the top of the
stock (the parting face of the main plate, the uncut top of a clamp-plate blank).  Every machined face
is symmetric about Y0, so turning the main plate over about X keeps the same program frame.

Each face is a floor (the cavity floor, or a clamp plate's seat face) at Z-10 with teeth 8.4 mm tall:
their sides lean 1.5 deg (the web draft) and finish with a 1.5 deg tapered end mill in one pass; their
handle ends are 45 deg ramps finished with a ball nose from a drop cutter; elsewhere 2.5-D.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import shapely
from shapely.affinity import rotate
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from . import cam, wave
from .cam import Cut, Obstacle, Op, Path, Setup, Tool
from .geometry import CONSTRUCTION as C
from .geometry import Outline
from .mould import BOTTOM, MOULD, TOP, layout, ring, union_ring, vent_span

BLUEPRINT_NO, DIAGRAM_NO = "PB-MO-004", "PB-MO-005"
M = MOULD
MATERIAL = "ALUMINIUM 6061-T651 OR CAST TOOLING PLATE (ALCA 5 / MIC-6)"
STOCK_T = {"main": M.main, "clamp": 20.0}             # blank thickness: main plate at size, clamp blank 20
BLANK = (-25.0, -130.0, 420.0, 130.0)                 # X0, Y0, X1, Y1 of every mould blank (machine)
FIXTURE = (-65.0, -160.0, 460.0, 160.0)               # fixture plate, 20 mm thick
FIXTURE_T = 20.0
CLAMPS = [(40.0, 122.0), (110.0, 122.0), (415.0, 125.0), (40.0, -122.0), (110.0, -122.0), (415.0, -125.0)]
CLAMP_R = 15.0                                        # toe-clamp envelope on the blank (radius)
STUDS = [(40.0, 147.0), (110.0, 147.0), (437.0, 143.0), (40.0, -147.0), (110.0, -147.0), (437.0, -143.0)]
BOLT_HEAD = dict(r=5.0, h=6.0)                        # M6 socket head cap screw
STOCK_WALL, STOCK_FLOOR = 0.3, 0.2                    # finishing allowances left by roughing
RELIEF_D = 1.5                                        # fixture relief groove depth (profile breaks 0.5 into it)


# ------------------------------------------------------------------------------------------ tools and cutting data
TOOLS = {t.n: t for t in (
    Tool(1, "flat", 10.0, 32.0, "D10 3FL CARBIDE END MILL, LOC 32 (LONG), ALU - CLEARING + PROFILES", stickout=40.0),
    Tool(2, "flat", 8.0, 20.0, "D8 3FL CARBIDE END MILL, LOC 20, ALU - CAVITY ROUGHING", stickout=26.0),
    Tool(3, "flat", 6.0, 16.0, "D6 3FL CARBIDE END MILL, LOC 16, ALU - FLOORS, WALLS, NOTCHES", stickout=24.0),
    Tool(4, "taper", 3.0, 12.0, "TAPERED END MILL 1.5 DEG/SIDE, TIP D3 FLAT, LOC 12, SHANK D6 - TEETH SIDES",
         taper=1.5, shank=6.0, stickout=22.0),
    Tool(5, "ball", 6.0, 12.0, "D6 BALL NOSE 2FL CARBIDE - 45 DEG RAMPS", flutes=2, stickout=24.0),
    Tool(6, "flat", 2.0, 6.0, "D2 2FL CARBIDE END MILL, LOC 6 - GROOVES, VENTS", flutes=2, shank=4.0, stickout=14.0),
    Tool(7, "spot", 10.0, 5.0, "D10 90 DEG SPOT DRILL, CARBIDE", flutes=2),
    Tool(8, "drill", 6.6, 40.0, "D6.6 DRILL 5XD (M6 CLEARANCE)", flutes=2, stickout=45.0),
    Tool(9, "drill", 5.8, 40.0, "D5.8 DRILL 5XD (DOWEL PILOT)", flutes=2, stickout=45.0),
    Tool(10, "ream", 6.0, 40.0, "D6 H7 MACHINE REAMER", flutes=6, stickout=45.0),
    Tool(11, "drill", 5.0, 30.0, "D5.0 DRILL (M6 TAP DRILL) - FIXTURE", flutes=2, stickout=35.0),
    Tool(12, "drill", 8.5, 30.0, "D8.5 DRILL (M10 TAP DRILL) - FIXTURE", flutes=2, stickout=35.0),
)}

# cutting data per machine profile and use ("vmc": rigid vertical machining centre, flood coolant, 10k rpm;
# "router": rigid gantry router with a 2.2 kW 24k spindle, mist / air blast)
CUTS = {
    "vmc": {
        "rough_clamp": Cut(8000, 1500, 400, ap=2.05, ae=5.0), "profile": Cut(8000, 700, 400, ap=4.0),
        "relief": Cut(8000, 900, 400, ap=1.5),
        "rough": Cut(10000, 1400, 450, ap=2.05, ae=3.2), "cbore": Cut(10000, 0, 300),
        "floor": Cut(10000, 1000, 350, ap=0.2, ae=3.6), "wall": Cut(10000, 900, 350),
        "notch": Cut(10000, 900, 300, ap=2.5, ae=2.5),
        "taper": Cut(10000, 600, 200), "semi": Cut(10000, 1800, 400, ae=1.0), "ball": Cut(10000, 1500, 400, ae=0.25),
        "groove": Cut(10000, 300, 100, ap=0.5, ramp_deg=2.0), "vent": Cut(10000, 300, 100, ap=0.4, ramp_deg=2.0),
        "spot": Cut(3500, 0, 250), "drill66": Cut(4500, 0, 450, peck=3.0), "drill58": Cut(5000, 0, 450, peck=3.0),
        "ream": Cut(1200, 0, 240), "drill50": Cut(5500, 0, 450, peck=3.0), "drill85": Cut(3500, 0, 350, peck=3.0),
    },
    "router": {
        "rough_clamp": Cut(16000, 1000, 300, ap=1.0, ae=4.0), "profile": Cut(16000, 600, 300, ap=1.0),
        "relief": Cut(16000, 800, 300, ap=0.75),
        "rough": Cut(18000, 1100, 300, ap=1.0, ae=3.0), "cbore": Cut(16000, 0, 150),
        "floor": Cut(18000, 900, 250, ap=0.2, ae=3.0), "wall": Cut(18000, 800, 250),
        "notch": Cut(18000, 800, 250, ap=1.25, ae=2.5),
        "taper": Cut(18000, 450, 150), "semi": Cut(18000, 1200, 300, ae=1.0), "ball": Cut(18000, 1000, 300, ae=0.25),
        "groove": Cut(24000, 400, 100, ap=0.25, ramp_deg=2.0), "vent": Cut(24000, 400, 100, ap=0.2, ramp_deg=2.0),
        "spot": Cut(8000, 0, 150), "drill66": Cut(6000, 0, 240, peck=2.0), "drill58": Cut(6000, 0, 240, peck=2.0),
        "ream": Cut(6000, 0, 300), "drill50": Cut(6000, 0, 240, peck=2.0), "drill85": Cut(6000, 0, 180, peck=2.0),
    },
}


# ------------------------------------------------------------------------------------------ frames
def to_m(g):
    """Paddle plan (x across, y along) -> machine plan (X = y, Y = -x)."""
    return rotate(g, -90, origin=(0, 0))


def pt_m(x: float, y: float) -> tuple[float, float]:
    return (y, -x)


def ring_m(r, tol: float = 0.003) -> list[tuple[float, float]]:
    """A shapely ring in paddle coordinates as a machine-plan point list (open), simplified to tol."""
    r = Polygon(r).simplify(tol, preserve_topology=True).exterior
    return [pt_m(x, y) for x, y in list(r.coords)[:-1]]


def loop_coords(poly, tol: float = 0.003, clockwise: bool = False) -> list[tuple[float, float]]:
    """Exterior of a shapely polygon (machine plan) as an open point list, simplified, oriented."""
    ext = poly.simplify(tol, preserve_topology=True).exterior
    pts = list(ext.coords)[:-1]
    if ext.is_ccw == clockwise:
        pts = pts[::-1]
    return pts


# ------------------------------------------------------------------------------------------ teeth
Z_FLOOR = -C.core_t                      # cavity floor / clamp-plate seat face
Z_TOP = -(C.core_t - M.teeth)            # tooth tips: -1.6


@dataclass
class Teeth:
    """The teeth standing on one machined face, in paddle plan coordinates and machine depth Z.

    side -1: main plate (the paddle's bottom flutes, rib z = Z + h); +1: clamp plate (top flutes,
    rib z = -h - Z).  A tooth at depth Z is the flute's x-interval at that rib height, from the ramp
    (y = solid_to + runout * (Z - Z_FLOOR) / core_t) to the frame's inner edge."""
    o: Outline
    side: int
    inner: Polygon = field(init=False)
    polys: list = field(init=False)

    def __post_init__(self):
        self.inner = Polygon(self.o.polyline(0.2)).buffer(-C.frame_w, join_style="round", quad_segs=32)
        self.polys = wave.channel_polygons(self.o.spec.width / 2 + C.rib_pitch, self.side)

    def zrib(self, Z: float) -> float:
        return Z + M.h if self.side < 0 else -M.h - Z

    @staticmethod
    def y_ramp(Z: float) -> float:
        return C.solid_to + C.runout_len * (Z - Z_FLOOR) / C.core_t

    def intervals(self, Z: float) -> list[tuple[float, float]]:
        z = self.zrib(Z)
        out = []
        for p in self.polys:
            seg = p.intersection(LineString([(-1e4, z), (1e4, z)]))
            for g in cam.parts(seg):
                if g.length > 1e-6:
                    xs = [c[0] for c in g.coords]
                    out.append((min(xs), max(xs)))
        return out

    def slices(self, Z: float):
        """Union of the tooth cross-sections at depth Z (paddle plan)."""
        if Z > Z_TOP + 1e-9:
            return Polygon()
        y0 = self.y_ramp(Z)
        return unary_union([box(a, y0, b, 1000.0) for a, b in self.intervals(Z)]).intersection(self.inner)

    def footprints(self) -> list[Polygon]:
        return cam.polygons(self.slices(Z_FLOOR + 1e-4))

    def tooth_table(self) -> list[dict]:
        """Per tooth: base and tip x-intervals (paddle x), length range in y."""
        base, tip = self.intervals(Z_FLOOR + 1e-4), self.intervals(Z_TOP - 1e-4)
        rows = []
        for (a0, b0) in base:
            t = min(tip, key=lambda iv: abs((iv[0] + iv[1]) - (a0 + b0)))
            fp = box(a0, self.y_ramp(Z_FLOOR), b0, 1000).intersection(self.inner)
            if fp.is_empty or fp.area < 1.0:
                continue
            x0, y0, x1, y1 = fp.bounds
            rows.append(dict(x_base=(round(max(a0, x0), 3), round(min(b0, x1), 3)), x_tip=(round(t[0], 3), round(t[1], 3)),
                             y_from=round(y0, 2), y_to=round(y1, 2), clipped=bool(a0 < x0 - 1e-3 or b0 > x1 + 1e-3)))
        return rows


def ramp_passes(teeth: Teeth, footprint: Polygon, tool: Tool, ae: float, offset: float, walls=None,
                grid: float = 0.05, step: float = 0.1) -> list[list[tuple[float, float, float]]]:
    """Ball-nose passes along y over one tooth's 45 deg ramp (paddle plan), z from a drop cutter on the
    exact surface + offset: the tooth, the floor around it and, outside `walls` (the cavity outline of a
    main-plate face), the plate top at Z0.  Each pass starts just before the tooth at its x.  Zig-zag."""
    x0, y0f, x1, _ = footprint.bounds
    base = [iv for iv in teeth.intervals(Z_FLOOR + 1e-4) if iv[1] > x0 + 1e-3 and iv[0] < x1 - 1e-3]
    tip = [iv for iv in teeth.intervals(Z_TOP - 1e-4) if iv[1] > x0 + 1e-3 and iv[0] < x1 - 1e-3]
    (a0, b0), (a1, b1) = base[0], min(tip, key=lambda iv: abs(iv[0] + iv[1] - base[0][0] - base[0][1]))
    r = tool.r
    ys_start = teeth.y_ramp(Z_FLOOR) - r - 1.0
    ys_end = teeth.y_ramp(Z_TOP) + r + 1.0
    gx = np.arange(x0 - r - 0.5, x1 + r + 0.5 + grid, grid)
    gy = np.arange(ys_start - r - 0.5, ys_end + r + 0.5 + grid, grid)
    X, Y = np.meshgrid(gx, gy)
    dz = Z_TOP - Z_FLOOR
    zl = np.where(a1 > a0, Z_FLOOR + (X - a0) / max(a1 - a0, 1e-9) * dz, np.inf)     # left side (leans in)
    zr = np.where(b1 < b0, Z_FLOOR + (b0 - X) / max(b0 - b1, 1e-9) * dz, np.inf)     # right side
    zramp = Z_FLOOR + (Y - teeth.y_ramp(Z_FLOOR)) / (teeth.y_ramp(Z_TOP) - teeth.y_ramp(Z_FLOOR)) * dz
    h = np.minimum.reduce([np.full_like(X, Z_TOP), zl, zr, zramp])
    inside = (X >= a0) & (X <= b0) & shapely.contains_xy(teeth.inner, X, Y)
    h = np.where(inside, np.maximum(h, Z_FLOOR), Z_FLOOR)
    if walls is not None:
        h = np.where(shapely.contains_xy(walls, X, Y), h, 0.0)
    n = int(round(r / grid))
    oy, ox = np.mgrid[-n:n + 1, -n:n + 1] * grid
    dd = np.hypot(ox, oy)
    prof = tool.profile(dd)
    xs = list(np.arange(max(a0, x0), min(b0, x1) + 1e-9, ae))
    if xs[-1] < min(b0, x1) - 0.02:
        xs.append(min(b0, x1))
    y_top = teeth.y_ramp(Z_TOP)
    keep = []
    for xc in xs:                          # skip passes where the frame cuts the tooth off above its ramp
        cut = footprint.intersection(LineString([(xc, -1e3), (xc, 1e3)]))
        if not cut.is_empty and cut.bounds[1] < y_top - 0.05:
            keep.append((xc, max(ys_start, cut.bounds[1] - r - 1.0)))
    passes = []
    for k, (xc, y_from) in enumerate(keep):
        ix = int(round((xc - gx[0]) / grid))
        pts = []
        for yc in np.arange(y_from, ys_end + 1e-9, step):
            iy = int(round((yc - gy[0]) / grid))
            win = h[iy - n:iy + n + 1, ix - n:ix + n + 1]
            z = float(np.max(win - prof))
            pts.append((float(xc), float(yc), z + offset))
        passes.append(pts if k % 2 == 0 else pts[::-1])
    return passes


# ------------------------------------------------------------------------------------------ plan helpers
def plate_outline(outlines) -> Polygon:
    return Polygon(union_ring(outlines, M.flange))


def notch_rect(n) -> Polygon:
    """Pry notch footprint (paddle plan): notch_w wide, notch_depth deep from the plate edge, 1 mm proud."""
    x, y, nx, ny = n
    cn = M.notch_depth / 2 - 0.5
    cx, cy = x - nx * cn, y - ny * cn
    tx, ty = -ny, nx
    L, W = (M.notch_depth + 1.0) / 2, M.notch_w / 2
    return Polygon([(cx + nx * L + tx * W, cy + ny * L + ty * W), (cx - nx * L + tx * W, cy - ny * L + ty * W),
                    (cx - nx * L - tx * W, cy - ny * L - ty * W), (cx + nx * L - tx * W, cy + ny * L - ty * W)])


def levels(z_from: float, z_to: float, ap: float) -> list[tuple[float, float]]:
    """Depth levels from z_from down to z_to in equal steps <= ap: [(z, z_above)]."""
    n = max(1, math.ceil((z_from - z_to) / ap - 1e-9))
    zs = [z_from - (z_from - z_to) * (k + 1) / n for k in range(n)]
    return list(zip(zs, [z_from] + zs[:-1]))


def obstacles(kind: str) -> list[Obstacle]:
    """What stands on the stock in a set-up: toe clamps on the blank's waste, bolt heads in the flange."""
    obs = [Obstacle(x, y, CLAMP_R, 25.0, "toe clamp") for x, y in CLAMPS]
    if kind == "bolted":
        obs += [Obstacle(*pt_m(x, y), BOLT_HEAD["r"] + 1.0, BOLT_HEAD["h"] + 0.5, "bolt head")
                for x, y in layout_cache()[1].bolts]
    return obs


_CACHE: dict = {}


def layout_cache():
    if "lay" not in _CACHE:
        from .geometry import DESIGNS, build
        outs = {sp.key: build(sp) for sp in DESIGNS}
        _CACHE["lay"] = (outs, layout((outs[TOP], outs[BOTTOM])))
    return _CACHE["lay"]


# ------------------------------------------------------------------------------------------ programs
@dataclass
class Program:
    number: int
    key: str               # file stem
    title: str
    plate: str             # main | clamp | fixture
    stock_t: float
    setup: Setup
    ops: list = field(default_factory=list)
    header: list = field(default_factory=list)
    face: str = ""          # the paddle whose cavity / teeth this face carries


def _p(tool: int, cut: Cut, setup: Setup) -> Path:
    return Path(TOOLS[tool], cut, setup)


def _op(name: str, path: Path, **kw) -> Op:
    path.end()
    return Op(name, path.t, path.c, moves=path.moves, **kw)


def cavity_face(o: Outline, prof: str, setup: Setup, outlines, lay) -> list[Op]:
    """Main plate face: pocket of paddle o with its bottom-flute teeth, groove, vents, notches."""
    K = CUTS[prof]
    teeth = Teeth(o, -1)
    pocket = to_m(Polygon(o.polyline(0.2)))
    t2, t3, t4, t5, t6 = (TOOLS[n] for n in (2, 3, 4, 5, 6))
    ops = []

    # T2 roughing: open to the tooth tips, then around the teeth (wall 0.3, floor 0.2 left)
    p = _p(2, K["rough"], setup)
    lv = [(z, pocket.buffer(-(t2.r + STOCK_WALL)), za) for z, za in levels(0.0, Z_TOP, K["rough"].ap)]
    for z, za in levels(Z_TOP, Z_FLOOR + STOCK_FLOOR, K["rough"].ap):
        isl = to_m(teeth.slices(z))
        lv.append((z, cam.minus_islands(pocket.buffer(-(t2.r + STOCK_WALL)), isl, t2.r + STOCK_WALL), za))
    cam.raster_pocket(p, lv)
    ops.append(_op(f"ROUGH {o.spec.name} CAVITY TO Z{Z_FLOOR + STOCK_FLOOR:g}, TEETH +{STOCK_WALL:g}", p))

    # T3: floor, the pocket wall, the notches
    feet = to_m(teeth.slices(Z_FLOOR + 1e-4))
    floor_r = cam.minus_islands(pocket.buffer(-(t3.r + STOCK_WALL)), feet, t3.r + STOCK_WALL)
    p = _p(3, K["floor"], setup)
    cam.raster_pocket(p, [(Z_FLOOR, floor_r, Z_FLOOR + STOCK_FLOOR)])
    ops.append(_op(f"FINISH CAVITY FLOOR Z{Z_FLOOR:g}", p))
    p = _p(3, K["wall"], setup)
    wall = cam.climb_rings(pocket.buffer(-t3.r, join_style="mitre", mitre_limit=10.0))[0]
    if not cam.contour(p, wall, Z_FLOOR, floor_r, lead=2.0, gap=STOCK_WALL):
        raise RuntimeError("no lead-in found for the cavity wall")
    ops.append(_op("FINISH CAVITY WALL (FULL DEPTH, CLIMB)", p))
    p = _p(3, K["notch"], setup)
    for n in lay.notches:
        rect = to_m(notch_rect(n))
        cam.raster_pocket(p, [(z, rect.buffer(-t3.r, join_style="mitre"), za)
                              for z, za in levels(0.0, -M.notch_h, K["notch"].ap)])
    ops.append(_op(f"PRY NOTCHES {M.notch_w:g} X {M.notch_depth:g} X {M.notch_h:g} DEEP", p))

    # T4: tooth sides (1.5 deg) in one pass at the floor, climb (clockwise round each tooth)
    p = _p(4, K["taper"], setup)
    for fp in cam.polygons(feet):
        ringcw = loop_coords(fp.buffer(t4.r, join_style="round", quad_segs=16), clockwise=True)
        if not cam.contour(p, ringcw, Z_FLOOR, floor_r, lead=2.5, gap=t3.r + STOCK_WALL - t4.r):
            raise RuntimeError("no lead-in found for a tooth")
    ops.append(_op("FINISH TOOTH SIDES 1.5 DEG (TAPERED TOOL, CLIMB)", p))

    # T5: 45 deg ramps, semi-finish then finish
    for use, off in (("semi", 0.25), ("ball", 0.0)):
        p = _p(5, K[use], setup)
        for fp in teeth.footprints():
            passes = ramp_passes(teeth, fp, t5, K[use].ae, off, walls=Polygon(o.polyline(0.2)))
            cam.raster3d(p, [[(*pt_m(x, y), z) for x, y, z in ps] for ps in passes])
        ops.append(_op(("SEMI-FINISH" if use == "semi" else "FINISH") + " 45 DEG TOOTH RAMPS (BALL)", p))

    # T6: overflow groove and vents
    p = _p(6, K["groove"], setup)
    g = ring_m(ring(o, M.land + M.groove_w / 2))
    cam.trace_closed(p, g, [z for z, _ in levels(0.0, -M.groove_d, K["groove"].ap)])
    ops.append(_op(f"OVERFLOW GROOVE {M.groove_w:g} X {M.groove_d:g}", p))
    p = _p(6, K["vent"], setup)
    for v in lay.vents:
        a, b = vent_span(o, v)
        cam.trace_open(p, [pt_m(*a), pt_m(*b)], [z for z, _ in levels(0.0, -M.vent_d, K["vent"].ap)])
    ops.append(_op(f"VENTS {M.vent_w:g} X {M.vent_d:g}", p))
    return ops


def clamp_face(o: Outline, prof: str, setup: Setup, outlines, lay) -> list[Op]:
    """Clamp plate, teeth side up: seat face at Z-10 with the paddle's top-flute teeth, notches."""
    K = CUTS[prof]
    teeth = Teeth(o, +1)
    plate = to_m(plate_outline(outlines)).buffer(1.0)               # 1 mm into the profile kerf
    t1, t3, t4, t5 = (TOOLS[n] for n in (1, 3, 4, 5))
    ops = []
    p = _p(1, K["rough_clamp"], setup)
    lv = [(z, plate.buffer(-t1.r), za) for z, za in levels(0.0, Z_TOP, K["rough_clamp"].ap)]
    for z, za in levels(Z_TOP, Z_FLOOR + STOCK_FLOOR, K["rough_clamp"].ap):
        lv.append((z, cam.minus_islands(plate.buffer(-t1.r), to_m(teeth.slices(z)), t1.r + STOCK_WALL), za))
    cam.raster_pocket(p, lv)
    ops.append(_op(f"FACE TOOTH TIPS Z{Z_TOP:g}, CLEAR TO SEAT Z{Z_FLOOR + STOCK_FLOOR:g}", p))

    feet = to_m(teeth.slices(Z_FLOOR + 1e-4))
    seat_r = cam.minus_islands(plate.buffer(-t3.r), feet, t3.r + STOCK_WALL)
    p = _p(3, K["floor"], setup)
    cam.raster_pocket(p, [(Z_FLOOR, seat_r, Z_FLOOR + STOCK_FLOOR)])
    ops.append(_op(f"FINISH SEAT FACE Z{Z_FLOOR:g}", p))
    p = _p(3, K["notch"], setup)
    for n in lay.notches:
        rect = to_m(notch_rect(n))
        cam.raster_pocket(p, [(z, rect.buffer(-t3.r, join_style="mitre"), za)
                              for z, za in levels(Z_FLOOR, Z_FLOOR - M.notch_h, K["notch"].ap)])
    ops.append(_op(f"PRY NOTCHES {M.notch_w:g} X {M.notch_depth:g} X {M.notch_h:g} DEEP IN THE SEAT", p))

    p = _p(4, K["taper"], setup)
    for fp in cam.polygons(feet):
        ringcw = loop_coords(fp.buffer(t4.r, join_style="round", quad_segs=16), clockwise=True)
        if not cam.contour(p, ringcw, Z_FLOOR, seat_r, lead=2.5, gap=t3.r + STOCK_WALL - t4.r):
            raise RuntimeError("no lead-in found for a tooth")
    ops.append(_op("FINISH TOOTH SIDES 1.5 DEG (TAPERED TOOL, CLIMB)", p))
    for use, off in (("semi", 0.25), ("ball", 0.0)):
        p = _p(5, K[use], setup)
        for fp in teeth.footprints():
            passes = ramp_passes(teeth, fp, t5, K[use].ae, off)
            cam.raster3d(p, [[(*pt_m(x, y), z) for x, y, z in ps] for ps in passes])
        ops.append(_op(("SEMI-FINISH" if use == "semi" else "FINISH") + " 45 DEG TOOTH RAMPS (BALL)", p))
    return ops


def profile_op(outlines, prof: str, setup: Setup, depth: float, stop: str = "") -> Op:
    K = CUTS[prof]
    t1 = TOOLS[1]
    plate = to_m(plate_outline(outlines))
    rough = loop_coords(plate.buffer(t1.r + STOCK_WALL, join_style="round", quad_segs=32), clockwise=True)
    fin = loop_coords(plate.buffer(t1.r, join_style="round", quad_segs=32), clockwise=True)   # climb, plate side
    p = _p(1, K["profile"], setup)
    cam.profile(p, rough, -depth - 0.5, STOCK_WALL, fin)
    return _op(f"OUTER PROFILE THROUGH {depth:g} (+0.5 INTO THE FIXTURE RELIEF)", p, stop=stop)


def drill_ops(prof: str, t: float, lay) -> list[Op]:
    K = CUTS[prof]
    bolts = cam.order_points([pt_m(*b) for b in lay.bolts], start=(BLANK[0], 0.0))
    dowels = cam.order_points([pt_m(*d) for d in lay.dowels], start=bolts[-1])
    return [
        cam.drill("SPOT 18 BOLT HOLES (0.4 X 45 DEG CHAMFER)", TOOLS[7], K["spot"], "spot", bolts, -(M.bolt_d / 2 + 0.4)),
        cam.drill("SPOT 2 DOWEL HOLES", TOOLS[7], K["spot"], "spot", dowels, -(M.dowel_d / 2 + 0.4)),
        cam.drill(f"DRILL 18 X D{M.bolt_d:g} THRU (PECK)", TOOLS[8], K["drill66"], "peck", bolts, -(t + 2.5)),
        cam.drill("DRILL 2 X D5.8 THRU (DOWEL PILOT)", TOOLS[9], K["drill58"], "peck", dowels, -(t + 2.5)),
        cam.drill(f"REAM 2 X D{M.dowel_d:g} H7 THRU", TOOLS[10], K["ream"], "ream", dowels, -(t + 1.0)),
    ]


def fixture_ops(prof: str, outlines, lay, setup: Setup) -> list[Op]:
    K = CUTS[prof]
    bolts = cam.order_points([pt_m(*b) for b in lay.bolts], start=(FIXTURE[0], 0.0))
    dowels = [pt_m(*d) for d in lay.dowels]
    studs = cam.order_points(STUDS, start=bolts[-1])
    ops = [
        cam.drill("DRILL RELIEFS D8 X 4 DEEP AT THE 18 BOLT HOLES (PLUNGE)", TOOLS[2], K["cbore"], "spot", bolts, -4.0),
        cam.drill("SPOT THE 18 RELIEF FLOORS", TOOLS[7], K["spot"], "spot", bolts, -4.5),
        cam.drill("SPOT 2 DOWEL HOLES", TOOLS[7], K["spot"], "spot", dowels, -(M.dowel_d / 2 + 0.4)),
        cam.drill("SPOT 6 CLAMP-STUD HOLES", TOOLS[7], K["spot"], "spot", studs, -5.0),
        # blind holes: the fixture lies on the machine table
        cam.drill("DRILL 18 X D5.0 X 18 DEEP (M6 TAP DRILL, BLIND)", TOOLS[11], K["drill50"], "peck", bolts, -18.0),
        cam.drill("DRILL 6 X D8.5 X 18 DEEP (M10 TAP DRILL, BLIND)", TOOLS[12], K["drill85"], "peck", studs, -18.0),
        cam.drill("DRILL 2 X D5.8 X 14 DEEP (DOWEL PILOT, BLIND)", TOOLS[9], K["drill58"], "peck", dowels, -14.0),
        cam.drill(f"REAM 2 X D{M.dowel_d:g} H7 X 12 DEEP (PRESS FIT FOR M6 PINS)", TOOLS[10], K["ream"], "ream", dowels,
                  -12.0),
    ]
    # relief groove under the mould profile: covers the profile kerf (plate edge +0 .. +10.3) with margin
    plate = to_m(plate_outline(outlines))
    p = _p(1, K["relief"], setup)
    for off in (TOOLS[1].r - 2.0, TOOLS[1].r + STOCK_WALL + 2.0):
        rr = loop_coords(plate.buffer(off, join_style="round", quad_segs=32), clockwise=True)
        cam.trace_closed(p, rr, [z for z, _ in levels(0.0, -RELIEF_D, K["relief"].ap)])
    ops.append(_op(f"RELIEF GROOVE {RELIEF_D:g} DEEP UNDER THE PROFILE PATH", p))
    return ops


def header(prog: Program, prof: str) -> list[str]:
    return [f"{BLUEPRINT_NO} / {DIAGRAM_NO} STACK MOULD - CNC",
            f"MACHINE PROFILE: {prof.upper()} - CHECK FEEDS AND SPEEDS FOR YOUR MACHINE",
            f"MATERIAL: {MATERIAL if prog.plate != 'fixture' else 'ALUMINIUM 6061, 20 MM'}",
            f"STOCK: {BLANK[2] - BLANK[0]:g} X {BLANK[3] - BLANK[1]:g} X {prog.stock_t:g}" if prog.plate != "fixture" else
            f"STOCK: {FIXTURE[2] - FIXTURE[0]:g} X {FIXTURE[3] - FIXTURE[1]:g} X {FIXTURE_T:g}",
            "G54: X0 = PADDLE BUTT REFERENCE (HANDLE TOWARDS -X), Y0 = CENTRE LINE, Z0 = TOP OF STOCK",
            f"DOWEL PINS AT X{num_s(pt_m(*layout_cache()[1].dowels[0])[0])} Y+/-{num_s(abs(pt_m(*layout_cache()[1].dowels[0])[1]))}",
            "UNITS MM. VERIFY IN SIMULATION BEFORE RUNNING."]


def num_s(v: float) -> str:
    return f"{v:.2f}"


def programs(prof: str = "vmc") -> list[Program]:
    """All programs of the mould for one machine profile."""
    outlines, lay = layout_cache()
    pair = (outlines[TOP], outlines[BOTTOM])
    progs = []

    s0 = Setup(obstacles=[])
    pr = Program(100, "OP00_fixture_plate", "FIXTURE PLATE (OP 00)", "fixture", FIXTURE_T, s0)
    pr.ops = fixture_ops(prof, pair, lay, s0)
    progs.append(pr)

    s10 = Setup(obstacles=obstacles("clamped"))
    for num_, key, title, t in ((110, "OP10_main_plate_drill", "MAIN PLATE - OP 10 DRILL AND REAM", STOCK_T["main"]),
                                (210, "OP10_clamp_plates_drill", "CLAMP PLATES (TOP + BOTTOM) - OP 10 DRILL AND REAM",
                                 STOCK_T["clamp"])):
        pr = Program(num_, key, title, "main" if t == STOCK_T["main"] else "clamp", t, s10)
        pr.ops = drill_ops(prof, t, lay)
        progs.append(pr)

    sb = Setup(obstacles=obstacles("bolted"))
    pr = Program(120, "OP20_main_plate_face_A_elongated", f"MAIN PLATE - OP 20 FACE A ({outlines[TOP].spec.name})",
                 "main", STOCK_T["main"], sb, face=TOP)
    pr.ops = cavity_face(outlines[TOP], prof, sb, pair, lay)
    progs.append(pr)
    pr = Program(130, "OP30_main_plate_face_B_hybrid", f"MAIN PLATE - OP 30 FACE B ({outlines[BOTTOM].spec.name}) + PROFILE",
                 "main", STOCK_T["main"], sb, face=BOTTOM)
    pr.ops = cavity_face(outlines[BOTTOM], prof, sb, pair, lay) + [profile_op(pair, prof, sb, STOCK_T["main"])]
    progs.append(pr)

    sc = Setup(obstacles=obstacles("clamped"))
    for num_, key, title, face in ((220, "OP20_top_clamp_plate", "TOP CLAMP PLATE - OP 20 TEETH + PROFILE", TOP),
                                   (320, "OP20_bottom_clamp_plate", "BOTTOM CLAMP PLATE - OP 20 TEETH + PROFILE", BOTTOM)):
        pr = Program(num_, key, title, "clamp", STOCK_T["clamp"], sc, face=face)
        stop = (f"FIT THE {len(lay.bolts)} BOLTS M6 X 25 THROUGH THE FLANGE INTO THE FIXTURE (HEADS ON THE SEAT FACE), "
                "KEEP THE TOE CLAMPS ON THE WASTE, CYCLE START")
        pr.ops = clamp_face(outlines[face], prof, sc, pair, lay) + [profile_op(pair, prof, sc, STOCK_T["clamp"], stop)]
        progs.append(pr)
    for pr in progs:
        pr.header = header(pr, prof)
    return progs
