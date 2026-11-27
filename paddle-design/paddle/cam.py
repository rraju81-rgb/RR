"""Compact 3-axis CAM: tools, toolpaths and G-code posts (used for the aluminium stack mould).

Coordinates are the machine coordinates of one set-up, in mm: X along the plate, Y across it, Z up
with Z0 on the top face of the stock.  An operation is a list of moves ('G0' | 'G1', x, y, z, feed)
or a drilling cycle.  Cutting chains are linked here: ramped entries into material, short links at
depth where the link stays inside the region already being cut, otherwise a retract to a low plane
(Z+3) or, where the link passes near an obstacle that stands on the plate (bolt heads, clamps), to a
high plane.

Strategies
  raster_pocket   2.5-D clearing: zig-zag passes along X inside the tool-centre region of each level,
                  then the region's boundary (climb), each chain entered on a ramp
  contour         finishing loop at one depth with a straight lead-in / lead-out in cleared space
  profile         outside profile through the plate: continuous ramping laps, then a finishing lap
  trace           grooves and vents: the tool centre on the path, several depth passes
  raster3d        3-D finishing: given passes of (x, y, z) points (from a drop cutter)
  drill           spot / peck / ream cycles (G81 / G83 / G85), expanded for controls without cycles

Posts: 'iso' (Fanuc / Haas style: O-number, M6, G43, canned cycles, M8) writes one program per
set-up; 'generic' (GRBL, LinuxCNC, Mach3) writes one file per tool with plain G0/G1 only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.polygon import orient

RAPID = {"vmc": 15000.0, "router": 6000.0}       # mm/min, for the cycle-time estimate
TOOL_CHANGE_S = {"vmc": 8.0, "router": 150.0}    # s, automatic changer / manual change + touch-off


# ------------------------------------------------------------------------------------------ tools
@dataclass(frozen=True)
class Tool:
    n: int
    kind: str                 # flat | ball | taper | spot | drill | ream
    d: float                  # cutting diameter (taper: tip diameter)
    flute: float              # length of cut
    desc: str
    flutes: int = 3
    taper: float = 0.0        # taper: degrees per side
    shank: float = 0.0        # shank diameter (0: same as d)
    stickout: float = 0.0     # minimum stick-out from the holder
    holder_d: float = 42.0    # holder / collet nut diameter (collision check)

    @property
    def r(self) -> float:
        return self.d / 2

    @property
    def reach(self) -> float:
        """Largest cutting radius (taper: at the top of the flutes)."""
        if self.kind == "taper":
            return self.r + self.flute * math.tan(math.radians(self.taper))
        return self.r

    def profile(self, dist):
        """Height of the cutting surface above the tip at radial distance dist (inf beyond the cutter)."""
        dist = np.asarray(dist, dtype=float)
        out = np.full(dist.shape, np.inf)
        if self.kind == "ball":
            m = dist <= self.r
            out[m] = self.r - np.sqrt(np.maximum(self.r ** 2 - dist[m] ** 2, 0.0))
        elif self.kind == "taper":
            t = math.tan(math.radians(self.taper))
            out[dist <= self.r] = 0.0
            m = (dist > self.r) & (dist <= self.reach)
            out[m] = (dist[m] - self.r) / t
        elif self.kind in ("drill", "spot"):
            half = 59.0 if self.kind == "drill" else 45.0          # 118 deg drill point, 90 deg spot drill
            m = dist <= self.r
            out[m] = dist[m] / math.tan(math.radians(half))
        else:                                                       # flat end mill, reamer
            out[dist <= self.r] = 0.0
        return out


@dataclass(frozen=True)
class Cut:
    """Cutting data of one tool on one machine profile."""
    rpm: int
    feed: float               # mm/min
    plunge: float             # mm/min: plunge, ramp and drilling feed
    ap: float = 0.0           # step-down
    ae: float = 0.0           # step-over
    peck: float = 0.0         # drilling: peck depth (Q)
    ramp_deg: float = 3.0     # ramp entry angle


# ------------------------------------------------------------------------------------------ set-up
@dataclass
class Obstacle:
    """Something standing on the stock top: the tool centre keeps r + tool radius + 2 away below z_top."""
    x: float
    y: float
    r: float
    z_top: float
    name: str = ""


@dataclass
class Setup:
    low_z: float = 3.0        # retract plane for links clear of obstacles
    high_z: float = 12.0      # above bolt heads
    clear_z: float = 30.0     # start, end, tool changes
    obstacles: list = field(default_factory=list)

    def link_z(self, p, q, tool: Tool) -> float:
        """Retract height for a link from p to q (plan)."""
        if not self.obstacles:
            return self.low_z
        ln = LineString([p, q]) if math.dist(p, q) > 1e-9 else Point(p)
        for ob in self.obstacles:
            if ob.z_top > self.low_z - 0.5 and ln.distance(Point(ob.x, ob.y)) < ob.r + tool.reach + 2.0:
                return max(self.high_z, ob.z_top + 3.0) if ob.z_top + 3.0 <= self.clear_z else self.clear_z
        return self.low_z


@dataclass
class Op:
    name: str
    tool: Tool
    cut: Cut
    moves: list = field(default_factory=list)      # ('G0' | 'G1', x, y, z, f)
    cycle: dict | None = None                      # drilling: kind, points, z, r, q, f
    stop: str = ""                                 # program stop (M0) with this message before the op
    note: str = ""


# ------------------------------------------------------------------------------------------ helpers
def parts(g) -> list:
    if g is None or g.is_empty:
        return []
    return list(getattr(g, "geoms", [g]))


def polygons(g) -> list[Polygon]:
    return [p for p in parts(g) if p.geom_type == "Polygon" and p.area > 1e-6]


def climb_rings(region) -> list[list[tuple[float, float]]]:
    """Boundary loops of a tool-centre region, oriented for climb milling with a clockwise spindle:
    outer boundaries counter-clockwise (pocket walls outside), island boundaries clockwise."""
    out = []
    for p in polygons(region):
        p = orient(p.simplify(0.003, preserve_topology=True), 1.0)
        out.append(list(p.exterior.coords)[:-1])
        out += [list(i.coords)[:-1] for i in p.interiors]
    return [r for r in out if len(r) >= 3]


def simplify_path(pts: list, tol: float = 0.003) -> list:
    """Drop near-collinear points of an open 3-D polyline (Ramer-Douglas-Peucker)."""
    if len(pts) < 3:
        return list(pts)
    a = np.asarray(pts, dtype=float)
    keep = np.zeros(len(a), dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(a) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        p, q = a[i], a[j]
        v = q - p
        L = np.linalg.norm(v)
        seg = a[i + 1:j] - p
        if L < 1e-12:
            dist = np.linalg.norm(seg, axis=1)
        else:
            dist = np.linalg.norm(np.cross(seg, v / L), axis=1)
        k = int(np.argmax(dist))
        if dist[k] > tol:
            keep[i + 1 + k] = True
            stack += [(i, i + 1 + k), (i + 1 + k, j)]
    return [tuple(x) for x in a[keep]]


def _ring_point(ring, s):
    """Point at arc length s along a closed ring (list of (x, y)), and the segment index."""
    n = len(ring)
    acc = 0.0
    for i in range(n):
        p, q = ring[i], ring[(i + 1) % n]
        L = math.dist(p, q)
        if acc + L >= s:
            t = (s - acc) / L if L > 0 else 0.0
            return (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])), i
        acc += L
    return ring[0], 0


def _ring_length(ring) -> float:
    return sum(math.dist(ring[i], ring[(i + 1) % len(ring)]) for i in range(len(ring)))


def ring_from(ring, k: int):
    """The ring started at vertex k."""
    return ring[k:] + ring[:k]


# ------------------------------------------------------------------------------------------ toolpath builder
class Path:
    """Moves of one operation with position tracking and the set-up's linking rules."""

    def __init__(self, tool: Tool, cut: Cut, setup: Setup):
        self.t, self.c, self.s = tool, cut, setup
        self.moves: list = []
        self.x = self.y = None
        self.z = setup.clear_z

    # primitive moves
    def g0(self, x=None, y=None, z=None):
        x = self.x if x is None else x
        y = self.y if y is None else y
        z = self.z if z is None else z
        if x is None or y is None:                # not positioned yet: the first travel() goes in at clear_z
            return
        if (x, y, z) != (self.x, self.y, self.z):
            self.moves.append(("G0", x, y, z, 0.0))
            self.x, self.y, self.z = x, y, z

    def g1(self, x, y, z, f=None):
        f = self.c.feed if f is None else f
        if self.x is not None and abs(x - self.x) < 1e-6 and abs(y - self.y) < 1e-6 and abs(z - self.z) < 1e-6:
            return
        self.moves.append(("G1", x, y, z, f))
        self.x, self.y, self.z = x, y, z

    # linking
    def travel(self, x, y, z_from: float):
        """Go to (x, y) and down to z_from (above the material) by the right retract plane."""
        if self.x is None:                       # first move of the op: straight over, at the clearance height
            self.moves.append(("G0", x, y, self.s.clear_z, 0.0))
            self.x, self.y, self.z = x, y, self.s.clear_z
        elif math.hypot(x - self.x, y - self.y) > 1e-6:
            zl = max(self.s.link_z((self.x, self.y), (x, y), self.t), z_from)
            if self.z < zl:
                self.g0(z=zl)
            self.g0(x, y)
        if self.z > z_from:
            fast = z_from + 1.0
            if self.z > fast:
                self.g0(z=fast)
            self.g1(x, y, z_from, self.c.plunge)

    def retract(self, z=None):
        self.g0(z=self.s.low_z if z is None else z)

    def end(self):
        if self.moves:
            self.g0(z=self.s.clear_z)

    # entries
    def ramp_in(self, pts: list, z_from: float, z_to: float, closed: bool = False):
        """Enter the chain pts (2-D) at depth z_to: descend from z_from along its start at the ramp angle
        (back and forth on an open chain shorter than the ramp, round again on a closed one), then come
        back to pts[0] at depth along the same walk, so no ramp floor is left behind."""
        x0, y0 = pts[0]
        self.travel(x0, y0, z_from)
        drop = z_from - z_to
        if drop <= 1e-6:
            self.g1(x0, y0, z_to, self.c.plunge)
            return
        path = list(pts) + ([pts[0]] if closed else [])
        total = sum(math.dist(path[i], path[i + 1]) for i in range(len(path) - 1))
        if total < 0.5:                                        # nowhere to ramp: plunge
            self.g1(x0, y0, z_to, self.c.plunge)
            return
        L_need = drop / math.tan(math.radians(self.c.ramp_deg))
        walk, s, direction = [], 0.0, path
        while s < L_need - 1e-9:
            for i in range(len(direction) - 1):
                p, q = direction[i], direction[i + 1]
                L = math.dist(p, q)
                if L < 1e-9:
                    continue
                if s + L >= L_need:
                    t = (L_need - s) / L
                    walk.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]), z_to))
                    s = L_need
                    break
                s += L
                walk.append((q[0], q[1], z_from - drop * s / L_need))
            if not closed:
                direction = direction[::-1]
        fr = 0.7 * self.c.feed if self.c.feed > 0 else self.c.plunge
        for x, y, z in walk:
            self.g1(x, y, z, fr)
        for x, y, _ in walk[::-1][1:]:
            self.g1(x, y, z_to)
        self.g1(x0, y0, z_to)

    # chains
    def chain(self, pts: list, z: float, f=None):
        for x, y in pts:
            self.g1(x, y, z, f)


# ------------------------------------------------------------------------------------------ strategies
def raster_segments(R, ae: float) -> list[list]:
    """Raster lines along X inside region R, step ae in Y: rows of [(x0, y), (x1, y)] segments."""
    rows = []
    if R.is_empty:
        return rows
    minx, miny, maxx, maxy = R.bounds
    n = max(1, math.ceil((maxy - miny) / ae))
    ys = np.linspace(miny + 1e-3, maxy - 1e-3, n + 1) if n > 0 else [0.5 * (miny + maxy)]
    for y in ys:
        line = LineString([(minx - 1.0, y), (maxx + 1.0, y)])
        segs = []
        for g in parts(line.intersection(R)):
            if g.geom_type == "LineString" and g.length > 0.05:
                (xa, _), (xb, _) = g.coords[0], g.coords[-1]
                segs.append(sorted([(xa, y), (xb, y)]))
        rows.append(sorted(segs))
    return rows


def _boundary_rings(R) -> list:
    """(ring, doubled line, length) for every boundary loop of R, for walks along the boundary."""
    out = []
    for poly in polygons(R):
        for rg in [poly.exterior] + list(poly.interiors):
            c = list(rg.coords)
            out.append((rg, LineString(c + c[1:]), rg.length))
    return out


def _boundary_walk(rings, a, b, limit: float):
    """Points from a to b along the shorter way round the boundary loop through both, if <= limit."""
    from shapely.ops import substring
    pa, pb = Point(a), Point(b)
    for rg, line2, L in rings:
        if rg.distance(pa) < 2e-3 and rg.distance(pb) < 2e-3:
            d1, d2 = rg.project(pa), rg.project(pb)
            fwd, bwd = (d2 - d1) % L, (d1 - d2) % L
            if min(fwd, bwd) > limit:
                return None
            seg = substring(line2, d1, d1 + fwd) if fwd <= bwd else substring(line2, d1 + L, d1 + L - bwd)
            pts = list(seg.coords)
            return pts[1:-1] + [b], min(fwd, bwd)
    return None


def raster_pocket(p: Path, levels: list, link_max: float | None = None, finish_rings: bool = True) -> None:
    """levels: [(z, R, z_above)]: tool-centre region R at depth z, material over R already gone down to
    z_above.  Zig-zag rows along X; the end of a row links at depth to the next row by a straight move
    inside R (up to 3 x step-over, slower beyond 1.2 x) or along R's boundary (up to 4 x); otherwise
    a new chain starts with a ramp.  Then the boundary loops of R (climb)."""
    ae = p.c.ae
    link_max = 3.0 * ae if link_max is None else link_max
    for z, R, z_above in levels:
        if R is None or R.is_empty:
            continue
        R = R.simplify(0.003, preserve_topology=True)
        Rb = R.buffer(1e-3)
        rings = _boundary_rings(R)
        rows = raster_segments(R, ae)
        segs = [(ri, s) for ri, row in enumerate(rows) for s in row]
        left = set(range(len(segs)))
        by_row: dict[int, list[int]] = {}
        for k, (ri, _) in enumerate(segs):
            by_row.setdefault(ri, []).append(k)
        cur = (p.x, p.y) if p.x is not None else None
        chains = []                                             # [(x, y, feed factor)]
        while left:
            if cur is None:
                k = min(left, key=lambda k: (segs[k][1][0][1], segs[k][1][0][0]))
            else:
                k = min(left, key=lambda k: min(math.dist(cur, segs[k][1][0]), math.dist(cur, segs[k][1][1])))
            a, b = segs[k][1]
            if cur is not None and math.dist(cur, b) < math.dist(cur, a):
                a, b = b, a
            chain = [(*a, 1.0), (*b, 1.0)]
            left.discard(k)
            ri = segs[k][0]
            while True:
                end = chain[-1][:2]
                best = None
                for rj in (ri - 1, ri + 1):
                    for kk in by_row.get(rj, []):
                        if kk not in left:
                            continue
                        for s0, e0 in (segs[kk][1], segs[kk][1][::-1]):
                            L = math.dist(end, s0)
                            if L > 4.0 * ae or (best is not None and L >= best[0]):
                                continue
                            if L <= link_max and Rb.covers(LineString([end, s0])):
                                link = [(*s0, 1.0 if L <= 1.2 * ae else 0.6)]
                                best = (L, kk, link, e0, rj)
                                continue
                            walk = _boundary_walk(rings, end, s0, 4.0 * ae)
                            if walk is not None and (best is None or walk[1] < best[0]):
                                best = (walk[1], kk, [(*q, 0.8) for q in walk[0]], e0, rj)
                if best is None:
                    break
                _, kk, link, e0, rj = best
                chain += link + [(*e0, 1.0)]
                left.discard(kk)
                ri = rj
            chains.append(chain)
            cur = chain[-1][:2]
        for chain in chains:
            p.ramp_in([q[:2] for q in chain], z_above + 0.2, z)
            for x, y, fk in chain[1:]:
                p.g1(x, y, z, p.c.feed * fk)
        if finish_rings:
            for ring in climb_rings(R):
                k = min(range(len(ring)), key=lambda i: math.dist((p.x, p.y), ring[i])) if p.x is not None else 0
                ring = ring_from(ring, k)
                p.ramp_in(ring, z_above + 0.2, z, closed=True)
                p.chain(ring[1:] + [ring[0]], z)
        p.retract()


def contour(p: Path, ring: list, z: float, free, lead: float = 2.0, gap: float = 0.0, f=None) -> bool:
    """One finishing loop at depth z, started mid-edge with a straight lead-in / lead-out.  The plunge
    point lies in `free` (cleared to z for this tool centre); the lead segment may cross the `gap` between
    free and the ring (the finishing allowance).  ring is already oriented (climb)."""
    n = len(ring)
    Fq = free.buffer(1e-3)
    Fb = free.buffer(gap + 0.05)
    order = sorted(range(n), key=lambda i: -math.dist(ring[i], ring[(i + 1) % n]))   # long edges first
    for i in order:
        a, b = ring[i], ring[(i + 1) % n]
        L = math.dist(a, b)
        if L < 0.2:
            continue
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        tx, ty = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        for nx, ny in ((-ty, tx), (ty, -tx)):
            for ld in (lead, lead * 0.6, lead * 0.35):
                q = (m[0] + nx * ld, m[1] + ny * ld)
                if Fq.covers(Point(q)) and Fb.covers(LineString([q, m])):
                    loop = [m] + ring[i + 1:] + ring[:i + 1] + [m]
                    p.travel(q[0], q[1], z + 1.0)
                    p.g1(q[0], q[1], z, p.c.plunge)
                    p.g1(m[0], m[1], z, f)
                    p.chain(loop[1:], z, f)
                    p.g1(q[0], q[1], z, f)
                    p.retract()
                    return True
    return False


def profile(p: Path, ring_cw: list, z_final: float, stock: float, ring_finish: list | None = None) -> None:
    """Outside profile: ring_cw is the roughing loop (offset by tool radius + stock), clockwise.
    Continuous ramping laps down to z_final, one flat lap, then the finishing loop ring_finish."""
    ap = p.c.ap
    L = _ring_length(ring_cw)
    loop = ring_cw + [ring_cw[0]]
    n_laps = max(1, math.ceil(-z_final / ap))
    x0, y0 = loop[0]
    p.travel(x0, y0, 0.5)
    z_start, total = 0.5, n_laps * L
    s_acc = 0.0
    for lap in range(n_laps):
        for i in range(len(loop) - 1):
            a, b = loop[i], loop[i + 1]
            s_acc += math.dist(a, b)
            z = z_start + (z_final - z_start) * min(1.0, s_acc / total)
            p.g1(b[0], b[1], z)
    p.chain(loop[1:], z_final)                                 # flat lap at full depth
    if ring_finish:
        k = 0
        ring = ring_from(ring_finish, k)
        loop2 = ring + [ring[0]]
        # lead-in from the roughing kerf: the roughing loop point nearest the finishing start
        q = min(ring_cw, key=lambda c: math.dist(c, loop2[0]))
        p.retract()
        p.travel(q[0], q[1], z_final + 1.0)
        p.g1(q[0], q[1], z_final, p.c.plunge)
        p.chain(loop2, z_final)
        p.g1(q[0], q[1], z_final)
    p.retract()


def trace_closed(p: Path, ring: list, depths: list[float]) -> None:
    """Tool centre along a closed ring, one lap per depth, ramping down along the ring between laps."""
    k = min(range(len(ring)), key=lambda i: math.dist((p.x, p.y), ring[i])) if p.x is not None else 0
    ring = ring_from(ring, k)
    loop = ring + [ring[0]]
    z_prev = 0.2
    for z in depths:
        p.ramp_in(ring, z_prev, z, closed=True)
        p.chain(loop[1:], z)
        z_prev = z
    p.retract()


def trace_open(p: Path, line: list, depths: list[float]) -> None:
    """Tool centre along an open polyline: one pass per depth in alternating directions, each ramped in."""
    pts = list(line)
    z_prev, fwd = 0.2, True
    for z in depths:
        seq = pts if fwd else pts[::-1]
        p.ramp_in(seq, z_prev, z)
        p.chain(seq[1:], z)
        z_prev, fwd = z, not fwd
    p.retract()


def raster3d(p: Path, passes: list[list[tuple[float, float, float]]], link_max: float = 2.0) -> None:
    """3-D finishing passes (already safe tool-tip positions); consecutive passes linked at height."""
    for pts in passes:
        pts = simplify_path(pts)
        x0, y0, z0 = pts[0]
        if p.x is not None and math.hypot(x0 - p.x, y0 - p.y) <= link_max and abs(z0 - p.z) < 1.0:
            p.g1(x0, y0, z0)
        else:
            p.retract()
            p.travel(x0, y0, z0 + 1.0)
            p.g1(x0, y0, z0, p.c.plunge)
        for x, y, z in pts[1:]:
            p.g1(x, y, z)
    p.retract()


def drill(name: str, tool: Tool, cut: Cut, kind: str, points: list, z: float, r: float = 2.0, **kw) -> Op:
    """Drilling op: kind spot (G81), peck (G83) or ream (G85); z = depth of the tip."""
    return Op(name, tool, cut, cycle=dict(kind=kind, points=list(points), z=z, r=r, q=cut.peck, f=cut.plunge), **kw)


def order_points(pts: list, start=(0.0, 0.0)) -> list:
    """Nearest-neighbour order (short rapids between holes)."""
    left = list(pts)
    out, cur = [], start
    while left:
        k = min(range(len(left)), key=lambda i: math.dist(cur, left[i]))
        cur = left.pop(k)
        out.append(cur)
    return out


# ------------------------------------------------------------------------------------------ cycle expansion
def cycle_moves(op: Op, initial_z: float, from_z: float | None = None) -> list:
    """A drilling cycle as plain moves (for the generic post, the simulation and the time estimate).
    The first hole is approached level at from_z (the clearance height), then straight down."""
    c = op.cycle
    mv = []
    for k, (x, y) in enumerate(c["points"]):
        if k == 0 and from_z is not None:
            mv.append(("G0", x, y, from_z, 0.0))
        mv.append(("G0", x, y, initial_z, 0.0))
        mv.append(("G0", x, y, c["r"], 0.0))
        if c["kind"] == "peck" and c["q"] > 0:
            depth = c["r"]
            while depth > c["z"] + 1e-9:
                nxt = max(c["z"], depth - c["q"]) if depth == c["r"] else max(c["z"], depth - c["q"])
                start = depth + 0.5 if depth < c["r"] else c["r"]
                if depth < c["r"]:
                    mv.append(("G0", x, y, start, 0.0))
                mv.append(("G1", x, y, nxt, c["f"]))
                mv.append(("G0", x, y, c["r"], 0.0))
                depth = nxt
        elif c["kind"] == "ream":
            mv.append(("G1", x, y, c["z"], c["f"]))
            mv.append(("G1", x, y, c["r"], c["f"]))
        else:
            mv.append(("G1", x, y, c["z"], c["f"]))
            mv.append(("G0", x, y, c["r"], 0.0))
        mv.append(("G0", x, y, initial_z, 0.0))
    return mv


def op_moves(op: Op, setup: Setup) -> list:
    return cycle_moves(op, setup.low_z + 2.0, setup.clear_z) if op.cycle else op.moves


def op_time(op: Op, setup: Setup, profile_name: str) -> tuple[float, float, float]:
    """(minutes, cutting length mm, rapid length mm)."""
    t, cut_len, rap_len = 0.0, 0.0, 0.0
    prev = None
    for g, x, y, z, f in op_moves(op, setup):
        if prev is not None:
            L = math.dist(prev, (x, y, z))
            if g == "G0":
                rap_len += L
                t += L / RAPID[profile_name]
            else:
                cut_len += L
                t += L / max(f, 1.0)
        prev = (x, y, z)
    return t, cut_len, rap_len


# ------------------------------------------------------------------------------------------ posts
def num(v: float) -> str:
    """Coordinate with a decimal point (Fanuc reads 'X10' as 10 µm on some controls)."""
    s = f"{v:.3f}".rstrip("0")
    if s in ("-0.", "-.", ""):
        s = "0."
    return s


def _ascii(s: str) -> str:
    rep = {"Ø": "D", "°": " DEG", "×": "X", "–": "-", "—": "-", "±": "+/-", "≥": ">=", "≤": "<=", "µ": "U", "(": "[",
           ")": "]"}
    return "".join(rep.get(ch, ch) for ch in s).encode("ascii", "replace").decode().upper()


def comment(s: str, width: int = 70) -> str:
    """A comment block, wrapped into several (...) lines of at most `width` characters (some controls and
    senders limit the line length)."""
    words, lines, cur = _ascii(s).split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width - 2:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}" if cur else w
    lines.append(cur)
    return "\n".join(f"({ln})" for ln in lines)


def _motion_lines(moves: list, state: dict) -> list[str]:
    out = []
    for g, x, y, z, f in moves:
        words = []
        if state.get("g") != g:
            words.append(g)
            state["g"] = g
        for ax, v in (("X", x), ("Y", y), ("Z", z)):
            if v is not None and (state.get(ax) is None or abs(state[ax] - v) > 5e-4):
                words.append(ax + num(v))
                state[ax] = v
        if g == "G1" and (state.get("F") is None or abs(state["F"] - f) > 0.5):
            words.append("F" + num(round(f)))
            state["F"] = f
        if len(words) > (1 if words and words[0] in ("G0", "G1") else 0):
            out.append(" ".join(words))
    return out


def post_iso(ops: list[Op], setup: Setup, number: int, title: str, header: list[str]) -> str:
    """Fanuc / Haas style program for one set-up.  The modal state (motion, position, feed) carries over
    from op to op, so an op that keeps the tool starts with its own positioning rapid."""
    L = ["%", f"O{number:04d} ({_ascii(title)[:60]})"]
    L += [comment(h) for h in header]
    L += ["G90 G94 G17 G21 G40 G49 G80", "G91 G28 Z0.", "G90"]
    tool_now = None
    st = {"g": None, "X": None, "Y": None, "Z": None, "F": None}
    for i, op in enumerate(ops):
        L.append(comment(f"OP {i + 1}: {op.name}"))
        t, c = op.tool, op.cut
        moves = op.moves if not op.cycle else []
        x0, y0 = (moves[0][1], moves[0][2]) if moves else op.cycle["points"][0]
        if op.stop:
            L += ["M9", "M5", "G91 G28 Z0.", "G90", comment(op.stop), "M0"]
        if tool_now != t.n or op.stop:
            if tool_now is not None and tool_now != t.n and not op.stop:
                L += ["M9", "M5", "G91 G28 Z0.", "G90"]
            if tool_now != t.n:
                L += [comment(f"T{t.n} {t.desc}"), f"T{t.n} M6"]
            L += ["G54", f"S{c.rpm} M3", f"G0 X{num(x0)} Y{num(y0)}", f"G43 H{t.n} Z{num(setup.clear_z)}", "M8"]
            st = {"g": "G0", "X": x0, "Y": y0, "Z": setup.clear_z, "F": None}
            tool_now = t.n
        else:
            L.append(f"S{c.rpm}")
        if op.cycle:
            cy = op.cycle
            init = setup.low_z + 2.0
            if st["X"] is None or abs(st["X"] - x0) > 5e-4 or abs(st["Y"] - y0) > 5e-4:
                if st["Z"] is None or st["Z"] < setup.clear_z - 1e-6:
                    L.append(f"G0 Z{num(setup.clear_z)}")
                L.append(f"G0 X{num(x0)} Y{num(y0)}")
            L.append(f"G0 Z{num(init)}")
            code = {"spot": "G81", "peck": "G83", "ream": "G85"}[cy["kind"]]
            for k, (x, y) in enumerate(cy["points"]):
                if k == 0:
                    q = f" Q{num(cy['q'])}" if cy["kind"] == "peck" else ""
                    L.append(f"G98 {code} X{num(x)} Y{num(y)} Z{num(cy['z'])} R{num(cy['r'])}{q} F{num(round(cy['f']))}")
                else:
                    L.append(f"X{num(x)} Y{num(y)}")
            L += ["G80", f"G0 Z{num(setup.clear_z)}"]
            st = {"g": "G0", "X": cy["points"][-1][0], "Y": cy["points"][-1][1], "Z": setup.clear_z, "F": None}
        else:
            L += _motion_lines(moves, st)
    L += ["M9", "M5", "G91 G28 Z0.", "G90", "M30", "%"]
    return "\n".join(L) + "\n"


def post_generic(ops: list[Op], setup: Setup, title: str, header: list[str]) -> list[tuple[Tool, str]]:
    """GRBL / LinuxCNC / Mach3: one file per tool, plain G0 / G1, drilling expanded, no M6 / G43 / M8."""
    groups: list[list[Op]] = []
    for op in ops:
        if groups and groups[-1][0].tool.n == op.tool.n and not op.stop:
            groups[-1].append(op)
        else:
            groups.append([op])
    files = []
    for gi, grp in enumerate(groups, 1):
        t, c = grp[0].tool, grp[0].cut
        L = [comment(f"{title} - FILE {gi}/{len(groups)}: T{t.n} {t.desc}")]
        L += [comment(h) for h in header]
        if grp[0].stop:
            L.append(comment("BEFORE THIS FILE: " + grp[0].stop))
        L += [comment(f"FIT T{t.n}, TOUCH IT OFF AT Z0 = TOP OF THE STOCK, THEN RUN"), "G90 G94 G17 G21",
              f"G0 Z{num(setup.clear_z)}", f"S{c.rpm} M3", "G4 P4"]
        state = {"g": "G0", "X": None, "Y": None, "Z": setup.clear_z}
        for op in grp:
            L.append(comment(op.name))
            if op.cycle:
                L += _motion_lines(cycle_moves(op, setup.low_z + 2.0, setup.clear_z), state)
            else:
                L += _motion_lines(op.moves, state)
        L += [f"G0 Z{num(setup.clear_z)}", "M5", "M30"]
        files.append((t, "\n".join(L) + "\n"))
    return files


# ------------------------------------------------------------------------------------------ geometry helpers
def minus_islands(R, islands, d: float):
    """Region R minus islands grown by d (round)."""
    if islands is None or islands.is_empty:
        return R
    return R.difference(islands.buffer(d, join_style="round", quad_segs=16))
