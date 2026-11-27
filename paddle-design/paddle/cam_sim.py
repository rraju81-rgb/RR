"""Stock-removal simulation of the generated G-code on a height map, and its comparison with the CAD.

The simulator reads the programs themselves (ISO with M6 / G43 / G81 / G83 / G85 / G28, or the generic
G0 / G1 files), sweeps each tool's real shape (flat, ball, 1.5 deg taper, 90 deg spot, 118 deg drill)
along every move and lowers the height map.  On the way it checks:
  rapids into material, flute length (depth of cut beyond the flutes), plunges into solid material,
  and the obstacles of the set-up (bolt heads, toe clamps) against the cutter.
The finished height map is compared with the mould STL cast from the machined side.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import numpy as np

from .cam import Tool

WORD = re.compile(r"([A-Z])\s*([-+]?\d*\.?\d+)")
HOME_Z = 200.0


@dataclass
class Grid:
    x0: float
    y0: float
    cell: float
    nx: int
    ny: int

    @classmethod
    def over(cls, x0, y0, x1, y1, cell=0.25):
        return cls(x0, y0, cell, int(math.ceil((x1 - x0) / cell)), int(math.ceil((y1 - y0) / cell)))

    def centres(self):
        xs = self.x0 + (np.arange(self.nx) + 0.5) * self.cell
        ys = self.y0 + (np.arange(self.ny) + 0.5) * self.cell
        return xs, ys

    def ij(self, x, y):
        return (y - self.y0) / self.cell - 0.5, (x - self.x0) / self.cell - 0.5


@dataclass
class Event:
    kind: str
    line: int
    text: str


@dataclass
class SimResult:
    H: np.ndarray
    events: list = field(default_factory=list)
    removed_cm3: dict = field(default_factory=dict)
    moves: int = 0


def parse(text: str, tool_for_file: int | None = None):
    """Yield (line no, tool, kind, p0, p1, feed) for every motion of a program; G28 retracts to HOME_Z."""
    pos = [0.0, 0.0, HOME_Z]
    known = [False, False, True]
    tool = tool_for_file
    motion = "G0"
    cyc = None                       # canned cycle: dict(code, z, r, q, f, ret)
    feed = 0.0
    out = []
    ret_mode = "G98"
    for ln, raw in enumerate(text.splitlines(), 1):
        s = re.sub(r"\(.*?\)", "", raw).strip().upper()
        if not s or s.startswith("%") or s.startswith("O"):
            continue
        words = WORD.findall(s)
        g = [float(v) for k, v in words if k == "G"]
        m = [float(v) for k, v in words if k == "M"]
        val = {k: float(v) for k, v in words if k not in "GM"}
        if 6 in m and "T" in val:
            tool = int(val["T"])
            continue
        if 91 in g and 28 in g:                       # G91 G28 Z0: home in Z
            out.append((ln, tool, "G0", tuple(pos), (pos[0], pos[1], HOME_Z), 0.0))
            pos[2] = HOME_Z
            continue
        if 91 in g:
            raise ValueError(f"line {ln}: incremental mode is not supported by the simulator")
        if "F" in val:
            feed = val["F"]
        for code in g:
            if code in (0, 1):
                motion = f"G{int(code)}"
                cyc = None
            elif code in (98, 99):
                ret_mode = f"G{int(code)}"
            elif code in (81, 83, 85):
                cyc = dict(code=int(code), z=val.get("Z"), r=val.get("R"), q=val.get("Q", 0.0), f=feed, ret=ret_mode,
                           init=pos[2])
            elif code == 80:
                cyc = None
        if cyc is not None and ("X" in val or "Y" in val or any(c in (81, 83, 85) for c in g)):
            if "Z" in val:
                cyc["z"] = val["Z"]
            if "R" in val:
                cyc["r"] = val["R"]
            x, y = val.get("X", pos[0]), val.get("Y", pos[1])
            seq = [("G0", (x, y, pos[2])), ("G0", (x, y, cyc["r"]))]
            z_cur = cyc["r"]
            if cyc["code"] == 83 and cyc["q"] > 0:
                depth = cyc["r"]
                while depth > cyc["z"] + 1e-9:
                    nxt = max(cyc["z"], depth - cyc["q"])
                    if depth < cyc["r"]:
                        seq.append(("G0", (x, y, depth + 0.5)))
                    seq.append(("G1", (x, y, nxt)))
                    seq.append(("G0", (x, y, cyc["r"])))
                    depth = nxt
            elif cyc["code"] == 85:
                seq += [("G1", (x, y, cyc["z"])), ("G1", (x, y, cyc["r"]))]
            else:
                seq += [("G1", (x, y, cyc["z"])), ("G0", (x, y, cyc["r"]))]
            back = cyc["init"] if cyc["ret"] == "G98" else cyc["r"]
            seq.append(("G0", (x, y, back)))
            for kind, p in seq:
                out.append((ln, tool, kind, tuple(pos), p, cyc["f"] if kind == "G1" else 0.0))
                pos = list(p)
            z_cur = back
            pos[2] = z_cur
            continue
        if any(k in val for k in "XYZ"):
            new = [val.get("X", pos[0]), val.get("Y", pos[1]), val.get("Z", pos[2])]
            if not (known[0] and known[1]) and motion == "G1":
                raise ValueError(f"line {ln}: feed move before X and Y are known")
            out.append((ln, tool, motion, tuple(pos), tuple(new), feed))
            pos = new
            for i, k in enumerate("XYZ"):
                if k in val:
                    known[i] = True
    return out


class Sim:
    def __init__(self, grid: Grid, H0: np.ndarray, tools: dict[int, Tool], obstacles=(), z_bottom: float = -1e3):
        self.g, self.H, self.tools = grid, H0.astype(np.float32).copy(), tools
        self.obstacles = list(obstacles)
        self.events: list[Event] = []
        self.removed: dict[int, float] = {}
        self.z_bottom = z_bottom
        self.n = 0

    def _window(self, xa, ya, xb, yb, reach):
        g = self.g
        i0 = max(0, int(math.floor((min(ya, yb) - reach - g.y0) / g.cell)))
        i1 = min(g.ny, int(math.ceil((max(ya, yb) + reach - g.y0) / g.cell)) + 1)
        j0 = max(0, int(math.floor((min(xa, xb) - reach - g.x0) / g.cell)))
        j1 = min(g.nx, int(math.ceil((max(xa, xb) + reach - g.x0) / g.cell)) + 1)
        return i0, i1, j0, j1

    def move(self, ln: int, tool: Tool, kind: str, p0, p1) -> None:
        self.n += 1
        x0, y0, z0 = p0
        x1, y1, z1 = p1
        # obstacles: cutter or shank against anything standing on the stock
        for ob in self.obstacles:
            if min(z0, z1) < ob.z_top:
                d = _seg_dist((ob.x, ob.y), (x0, y0), (x1, y1))
                if d < ob.r + max(tool.reach, tool.shank / 2 if tool.shank else 0.0):
                    self.events.append(Event("OBSTACLE", ln, f"T{tool.n} within {d:.1f} mm of {ob.name} at "
                                                            f"X{ob.x:.1f} Y{ob.y:.1f} below its top Z{ob.z_top:g}"))
        if min(z0, z1) > 0.5:                     # above the stock: nothing to sweep
            return
        vertical = abs(x1 - x0) + abs(y1 - y0) < 1e-6
        if kind == "G1" and vertical and z1 < z0 and tool.kind in ("flat", "ball", "taper"):
            depth = self._material_over(tool, x1, y1, z1)
            if depth > 0.3 * tool.d + 0.05:
                self.events.append(Event("PLUNGE INTO MATERIAL", ln, f"T{tool.n} plunging {depth:.2f} into solid at "
                                                                     f"X{x1:.2f} Y{y1:.2f}"))
        if vertical:                              # straight up or down: one sweep at the lowest point
            self._piece(ln, tool, kind, (x0, y0, min(z0, z1)), (x1, y1, min(z0, z1)))
            return
        dz = abs(z1 - z0)
        n = max(1, int(math.ceil(dz / 0.05))) if dz > 1e-9 else 1
        for k in range(n):
            a = (x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n, z0 + (z1 - z0) * k / n)
            b = (x0 + (x1 - x0) * (k + 1) / n, y0 + (y1 - y0) * (k + 1) / n, z0 + (z1 - z0) * (k + 1) / n)
            self._piece(ln, tool, kind, a, b)

    def _material_over(self, tool, x, y, z) -> float:
        """Height of material above z within the tool radius at (x, y)."""
        i0, i1, j0, j1 = self._window(x, y, x, y, tool.r)
        g = self.g
        X = g.x0 + (np.arange(j0, j1) + 0.5) * g.cell
        Y = g.y0 + (np.arange(i0, i1) + 0.5) * g.cell
        XX, YY = np.meshgrid(X, Y)
        m = np.hypot(XX - x, YY - y) <= tool.r
        return float(np.max(self.H[i0:i1, j0:j1][m] - z)) if m.any() else 0.0

    def _piece(self, ln, tool, kind, a, b):
        reach = tool.reach
        i0, i1, j0, j1 = self._window(a[0], a[1], b[0], b[1], reach)
        if i0 >= i1 or j0 >= j1:
            return
        g = self.g
        X = g.x0 + (np.arange(j0, j1) + 0.5) * g.cell
        Y = g.y0 + (np.arange(i0, i1) + 0.5) * g.cell
        XX, YY = np.meshgrid(X, Y)
        vx, vy = b[0] - a[0], b[1] - a[1]
        L2 = vx * vx + vy * vy
        if L2 > 1e-12:
            t = np.clip(((XX - a[0]) * vx + (YY - a[1]) * vy) / L2, 0.0, 1.0)
        else:
            t = np.zeros_like(XX)
        d = np.hypot(XX - (a[0] + t * vx), YY - (a[1] + t * vy))
        zt = a[2] + t * (b[2] - a[2])
        h = zt + tool.profile(d)
        Hw = self.H[i0:i1, j0:j1]
        over = Hw - h
        mx = float(np.max(over)) if over.size else -1.0
        if mx <= 1e-3:
            return
        if kind == "G0":
            self.events.append(Event("RAPID INTO STOCK", ln, f"T{tool.n} rapid {mx:.2f} mm into material at "
                                                           f"X{b[0]:.2f} Y{b[1]:.2f} Z{b[2]:.2f}"))
        else:
            inside = d <= tool.r + 1e-9
            if np.any(inside):
                depth = float(np.max((Hw - zt)[inside]))
                if depth > tool.flute + 0.05:
                    self.events.append(Event("BEYOND FLUTES", ln, f"T{tool.n} cutting {depth:.2f} deep, flutes "
                                                                  f"{tool.flute:g}, at X{b[0]:.2f} Y{b[1]:.2f}"))
        removed = np.clip(over, 0, None)
        self.removed[tool.n] = self.removed.get(tool.n, 0.0) + float(removed.sum()) * g.cell ** 2 / 1000.0
        np.minimum(Hw, h, out=Hw)

    def run(self, text: str, tool_for_file: int | None = None) -> None:
        for ln, tn, kind, p0, p1, f in parse(text, tool_for_file):
            if tn is None:
                if p0[2] >= HOME_Z - 1e-6 and p1[2] >= HOME_Z - 1e-6:
                    continue
                raise ValueError(f"line {ln}: motion before a tool is loaded")
            self.move(ln, self.tools[tn], kind, p0, p1)


def _seg_dist(p, a, b) -> float:
    vx, vy = b[0] - a[0], b[1] - a[1]
    L2 = vx * vx + vy * vy
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L2))
    return math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vy)


def cast(mesh, grid: Grid, to_paddle, from_below: bool, mask=None, chunk: int = 200_000) -> np.ndarray:
    """Heights (machine Z before the face offset) of a mesh cast along -z (or +z from below) at the grid
    centres; to_paddle(X, Y) -> mesh x, y.  NaN where the ray misses."""
    xs, ys = grid.centres()
    XX, YY = np.meshgrid(xs, ys)
    out = np.full(XX.shape, np.nan)
    sel = np.ones(XX.shape, bool) if mask is None else mask
    idx = np.flatnonzero(sel)
    mx, my = to_paddle(XX.ravel()[idx], YY.ravel()[idx])
    z0 = mesh.bounds[0][2] - 10.0 if from_below else mesh.bounds[1][2] + 10.0
    d = np.array([0.0, 0.0, 1.0 if from_below else -1.0])
    flat = out.ravel()
    for s in range(0, len(idx), chunk):
        o = np.column_stack([mx[s:s + chunk], my[s:s + chunk], np.full(min(chunk, len(idx) - s), z0)])
        loc, ray, _ = mesh.ray.intersects_location(o, np.tile(d, (len(o), 1)), multiple_hits=False)
        flat[idx[s + ray]] = loc[:, 2]
    return out


def compare(S: np.ndarray, T: np.ndarray, region: np.ndarray, tol: float = 0.03):
    """Gouge (sim below the lowest nearby target) and leftover (above the highest nearby target) maps;
    the 3 x 3 neighbourhood absorbs the half-cell uncertainty at vertical walls."""
    from scipy.ndimage import maximum_filter, minimum_filter
    lo, hi = minimum_filter(T, size=3), maximum_filter(T, size=3)
    gouge = np.where(region, lo - S, 0.0)
    left = np.where(region, S - hi, 0.0)
    return gouge, left, dict(max_gouge=float(gouge.max()), max_leftover=float(left.max()),
                             gouge_cells=int((gouge > tol).sum()), leftover_cells=int((left > tol).sum()),
                             cells=int(region.sum()))
