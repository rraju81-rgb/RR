"""Small SVG toolkit for technical drawings (ISO 128 / 129 conventions).

Sheet coordinates are millimetres with the origin at the top-left corner and
y pointing down, so an SVG written by :class:`Doc` prints at true size.
Model geometry (y up) is placed on the sheet through a :class:`View`.
"""
from __future__ import annotations

import math
from xml.sax.saxutils import escape

from .geometry import Line, Outline, Pt

FONT = "'DejaVu Sans', 'Liberation Sans', Arial, Helvetica, sans-serif"
TXT_DIM = 3.5        # dimension / note text height (font size, mm)
ARROW_L, ARROW_W = 3.0, 1.0

STYLE = f"""
  .vis  {{ fill:none; stroke:#000; stroke-width:0.5; stroke-linejoin:round; stroke-linecap:round }}
  .thin {{ fill:none; stroke:#000; stroke-width:0.25; stroke-linecap:round }}
  .xthin{{ fill:none; stroke:#000; stroke-width:0.13 }}
  .ctr  {{ fill:none; stroke:#000; stroke-width:0.25; stroke-dasharray:9 1.6 1.6 1.6 }}
  .hid  {{ fill:none; stroke:#000; stroke-width:0.25; stroke-dasharray:2.4 1.2 }}
  .phan {{ fill:none; stroke:#000; stroke-width:0.25; stroke-dasharray:9 1.6 1.6 1.6 1.6 1.6 }}
  .cut  {{ fill:none; stroke:#000; stroke-width:0.7; stroke-linecap:butt }}
  .frame{{ fill:none; stroke:#000; stroke-width:0.7 }}
  .arrow{{ fill:#000; stroke:none }}
  text  {{ font-family:{FONT} }}
"""


def f(v: float) -> str:
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def fmt(v: float, nd: int = 1) -> str:
    """Dimension value: drop a trailing .0 (ISO 129 style)."""
    s = f"{v:.{nd}f}"
    return s[:-2] if s.endswith(".0") else s


def text_w(s: str, size: float) -> float:
    return 0.6 * size * len(s)


def readable(rot: float) -> float:
    """Normalise a text rotation (degrees, SVG sense) so the text never reads upside down."""
    rot = (rot + 180) % 360 - 180
    if rot > 90:
        rot -= 180
    elif rot <= -90:
        rot += 180
    return rot


def above(rot: float, dist: float) -> Pt:
    """Offset that moves rotated text `dist` mm 'up' relative to its own baseline."""
    t = math.radians(rot)
    return (dist * math.sin(t), -dist * math.cos(t))


class Doc:
    def __init__(self, w: float, h: float, title: str = ""):
        self.w, self.h, self.title = w, h, title
        self.defs: list[str] = []
        self.body: list[str] = []

    def add(self, el: str) -> None:
        self.body.append(el)

    def svg(self) -> str:
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{f(self.w)}mm" height="{f(self.h)}mm" '
                f'viewBox="0 0 {f(self.w)} {f(self.h)}">\n<title>{escape(self.title)}</title>\n'
                f'<defs>\n<style>{STYLE}</style>\n' + "\n".join(self.defs) + "\n</defs>\n"
                f'<rect x="0" y="0" width="{f(self.w)}" height="{f(self.h)}" fill="#fff"/>\n')
        return head + "\n".join(self.body) + "\n</svg>\n"

    # -- primitives -------------------------------------------------------
    def line(self, p: Pt, q: Pt, cls: str = "thin", extra: str = "") -> None:
        self.add(f'<line x1="{f(p[0])}" y1="{f(p[1])}" x2="{f(q[0])}" y2="{f(q[1])}" class="{cls}" {extra}/>')

    def poly(self, pts: list[Pt], cls: str = "thin", closed: bool = False, extra: str = "") -> None:
        tag = "polygon" if closed else "polyline"
        s = " ".join(f"{f(x)},{f(y)}" for x, y in pts)
        self.add(f'<{tag} points="{s}" class="{cls}" {extra}/>')

    def path(self, d: str, cls: str = "vis", extra: str = "") -> None:
        self.add(f'<path d="{d}" class="{cls}" {extra}/>')

    def rect(self, x: float, y: float, w: float, h: float, cls: str = "thin", extra: str = "") -> None:
        self.add(f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" class="{cls}" {extra}/>')

    def circle(self, c: Pt, r: float, cls: str = "thin", extra: str = "") -> None:
        self.add(f'<circle cx="{f(c[0])}" cy="{f(c[1])}" r="{f(r)}" class="{cls}" {extra}/>')

    def text(self, p: Pt, s: str, size: float = TXT_DIM, anchor: str = "middle", rot: float = 0.0,
             weight: str = "normal", fill: str = "#000", extra: str = "") -> None:
        tr = f' transform="rotate({f(rot)} {f(p[0])} {f(p[1])})"' if rot else ""
        self.add(f'<text x="{f(p[0])}" y="{f(p[1])}" font-size="{f(size)}" text-anchor="{anchor}" '
                 f'font-weight="{weight}" fill="{fill}"{tr} {extra}>{escape(s)}</text>')

    def arrow(self, tip: Pt, d: Pt, length: float = ARROW_L, width: float = ARROW_W) -> None:
        """Filled arrowhead with its tip at `tip`, pointing along unit vector `d`."""
        bx, by = tip[0] - d[0] * length, tip[1] - d[1] * length
        nx, ny = -d[1] * width / 2, d[0] * width / 2
        self.poly([tip, (bx + nx, by + ny), (bx - nx, by - ny)], "arrow", closed=True)

    # -- dimensions (sheet coordinates) -------------------------------------
    def dim_linear(self, p1: Pt, p2: Pt, axis: str, at: float, label: str, *, gap: float = 1.0,
                   over: float = 2.0, outside: bool = False, shift: float = 0.0, size: float = TXT_DIM) -> None:
        """Horizontal (axis='x') or vertical (axis='y') dimension with extension lines.

        `at` is the sheet y (axis x) or sheet x (axis y) of the dimension line.
        """
        i = 0 if axis == "x" else 1          # measured coordinate
        j = 1 - i
        for p in (p1, p2):
            d = at - p[j]
            if abs(d) > gap + 0.2:
                s = math.copysign(1, d)
                a = list(p); a[j] = p[j] + s * gap
                b = list(p); b[j] = at + s * over
                self.line(tuple(a), tuple(b), "thin")
        lo, hi = sorted((p1[i], p2[i]))

        def P(u: float) -> Pt:
            return (u, at) if axis == "x" else (at, u)

        if outside:
            ext = 7.0
            self.line(P(lo - ext), P(hi + ext), "thin")
            self.arrow(P(lo), (1, 0) if axis == "x" else (0, 1))
            self.arrow(P(hi), (-1, 0) if axis == "x" else (0, -1))
        else:
            self.line(P(lo), P(hi), "thin")
            self.arrow(P(lo), (-1, 0) if axis == "x" else (0, -1))
            self.arrow(P(hi), (1, 0) if axis == "x" else (0, 1))
        mid = (lo + hi) / 2 + shift
        if axis == "x":
            self.text((mid, at - 1.0), label, size)
        else:
            self.text((at - 1.0, mid), label, size, rot=-90)

    def dim_aligned(self, p1: Pt, p2: Pt, offset: float, label: str, size: float = TXT_DIM) -> None:
        """Dimension parallel to p1-p2, offset to the left of the p1->p2 direction."""
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        L = math.hypot(dx, dy)
        u = (dx / L, dy / L)
        n = (u[1], -u[0])
        q1 = (p1[0] + n[0] * offset, p1[1] + n[1] * offset)
        q2 = (p2[0] + n[0] * offset, p2[1] + n[1] * offset)
        s = math.copysign(1, offset)
        for p, q in ((p1, q1), (p2, q2)):
            self.line((p[0] + n[0] * s * 1.0, p[1] + n[1] * s * 1.0), (q[0] + n[0] * s * 2, q[1] + n[1] * s * 2))
        self.line(q1, q2)
        self.arrow(q1, (-u[0], -u[1]))
        self.arrow(q2, u)
        ang = readable(math.degrees(math.atan2(u[1], u[0])))
        o = above(ang, 1.0)
        self.text(((q1[0] + q2[0]) / 2 + o[0], (q1[1] + q2[1]) / 2 + o[1]), label, size, rot=ang)

    def leader_note(self, tip: Pt, knee: Pt, label: str, size: float = TXT_DIM, arrow: bool = True,
                    dot: bool = False) -> None:
        """Leader from `tip` to `knee`, then a short horizontal shoulder carrying the text."""
        self.line(tip, knee)
        dx, dy = tip[0] - knee[0], tip[1] - knee[1]
        L = math.hypot(dx, dy) or 1.0
        if arrow:
            self.arrow(tip, (dx / L, dy / L))
        if dot:
            self.circle(tip, 0.5, "arrow")
        s = 1 if knee[0] >= tip[0] else -1
        w = text_w(label, size) + 1.5
        end = (knee[0] + s * w, knee[1])
        self.line(knee, end)
        self.text(((knee[0] + end[0]) / 2, knee[1] - 0.9), label, size)


class View:
    """Places model geometry (mm, y up) on the sheet at origin `o` with scale `s`."""

    def __init__(self, doc: Doc, origin: Pt, scale: float):
        self.d, self.o, self.s = doc, origin, scale

    def P(self, p: Pt) -> Pt:
        return (self.o[0] + p[0] * self.s, self.o[1] - p[1] * self.s)

    def outline_path(self, o: Outline) -> str:
        """SVG path data of an outline (true arcs)."""
        segs = o.segments
        x, y = self.P(segs[0].p0)
        d = [f"M{f(x)},{f(y)}"]
        for s in segs:
            x, y = self.P(s.p1)
            if isinstance(s, Line):
                d.append(f"L{f(x)},{f(y)}")
            else:
                large = 1 if abs(s.sweep) > math.pi else 0
                sweep = 0 if s.sweep > 0 else 1      # model CCW (y up) -> SVG sweep-flag 0
                r = s.r * self.s
                d.append(f"A{f(r)},{f(r)} 0 {large} {sweep} {f(x)},{f(y)}")
        return " ".join(d) + " Z"

    def line(self, p: Pt, q: Pt, cls: str = "thin") -> None:
        self.d.line(self.P(p), self.P(q), cls)

    def centre_mark(self, c: Pt, size: float = 2.5, cls: str = "thin") -> None:
        x, y = self.P(c)
        self.d.line((x - size, y), (x + size, y), cls)
        self.d.line((x, y - size), (x, y + size), cls)

    def dim_radius(self, c: Pt, r: float, ang: float, label: str, length: float, side: str = "out",
                   size: float = TXT_DIM, shoulder: float | None = None) -> None:
        """Radius dimension; `ang` in model degrees (CCW from +x).

        side='out': leader outside the arc, arrow pointing at the centre.
        side='in' : leader on the centre side, arrow pointing away from the centre.
        """
        a = math.radians(ang)
        u = (math.cos(a), -math.sin(a))                      # outward radial, sheet coords
        tip = self.P((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
        sgn = 1 if side == "out" else -1
        knee = (tip[0] + sgn * u[0] * length, tip[1] + sgn * u[1] * length)
        self.d.line(tip, knee)
        self.d.arrow(tip, (-sgn * u[0], -sgn * u[1]))
        hs = 1 if knee[0] >= tip[0] else -1
        if shoulder is not None:
            hs = shoulder
        w = text_w(label, size) + 1.5
        end = (knee[0] + hs * w, knee[1])
        self.d.line(knee, end)
        self.d.text(((knee[0] + end[0]) / 2, knee[1] - 0.9), label, size)

    def dim_radius_from_centre(self, c: Pt, r: float, ang: float, label: str, size: float = TXT_DIM) -> None:
        """Radius dimension drawn from the (marked) centre to the arc, text along the line."""
        a = math.radians(ang)
        C = self.P(c)
        tip = self.P((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
        self.d.line(C, tip)
        u = (math.cos(a), -math.sin(a))
        self.d.arrow(tip, u)
        rot = readable(-ang)
        o = above(rot, 1.0)
        self.d.text(((C[0] + tip[0]) / 2 + o[0], (C[1] + tip[1]) / 2 + o[1]), label, size, rot=rot)

    def dim_angle(self, v: Pt, a1: float, a2: float, rad: float, label: str, size: float = TXT_DIM,
                  text_r: float | None = None) -> None:
        """Angular dimension about model point v from model angle a1 to a2 (degrees, CCW)."""
        V = self.P(v)

        def pt(a: float) -> Pt:
            t = math.radians(a)
            return (V[0] + rad * math.cos(t), V[1] - rad * math.sin(t))

        p1, p2 = pt(a1), pt(a2)
        large = 1 if (a2 - a1) % 360 > 180 else 0
        self.d.path(f"M{f(p1[0])},{f(p1[1])} A{f(rad)},{f(rad)} 0 {large} 0 {f(p2[0])},{f(p2[1])}", "thin")
        t1, t2 = math.radians(a1), math.radians(a2)
        self.d.arrow(p1, (math.sin(t1), math.cos(t1)))
        self.d.arrow(p2, (-math.sin(t2), -math.cos(t2)))
        tr = text_r if text_r is not None else rad + 2.5
        am = math.radians((a1 + a2) / 2)
        self.d.text((V[0] + tr * math.cos(am), V[1] - tr * math.sin(am) + size * 0.35), label, size)

    def section_line(self, y: float, x0: float, x1: float, label: str, size: float = 5.0, up: bool = False) -> None:
        """Cutting plane across the view at model height y, viewed towards -y (arrows point down) or +y (up)."""
        a, b = self.P((x0, y)), self.P((x1, y))
        k = -1 if up else 1
        self.d.line(a, b, "ctr")
        for p, s in ((a, 1), (b, -1)):
            self.d.line(p, (p[0] + s * 6, p[1]), "cut")
            tail = (p[0] + s * 3, p[1])
            self.d.line(tail, (tail[0], tail[1] + k * 6), "thin")
            self.d.arrow((tail[0], tail[1] + k * 7.5), (0, k), 3.0, 1.4)
            self.d.text((p[0] - s * 1.0, p[1] - 1.5), label, size, anchor="end" if s > 0 else "start",
                        weight="bold")


def hatch_pattern(doc: Doc, pid: str = "hatch", pitch: float = 1.6, angle: float = 45) -> str:
    doc.defs.append(
        f'<pattern id="{pid}" width="{f(pitch)}" height="{f(pitch)}" patternUnits="userSpaceOnUse" '
        f'patternTransform="rotate({f(angle)})"><line x1="0" y1="0" x2="0" y2="{f(pitch)}" '
        f'stroke="#000" stroke-width="0.18"/></pattern>')
    return f"url(#{pid})"


def frame_iso(doc: Doc, left: float = 20, m: float = 10, zones: bool = True) -> tuple[float, float, float, float]:
    """ISO 5457-style frame with grid reference zones. Returns the inner frame box."""
    x0, y0, x1, y1 = left, m, doc.w - m, doc.h - m
    doc.rect(x0, y0, x1 - x0, y1 - y0, "frame")
    if zones:
        z = 5.0                                   # zone strip width
        doc.rect(x0 + z, y0 + z, x1 - x0 - 2 * z, y1 - y0 - 2 * z, "thin")
        nx, ny = 8, 6
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            if 0 < i < nx:
                doc.line((x, y0), (x, y0 + z)); doc.line((x, y1 - z), (x, y1))
        for i in range(nx):
            x = x0 + (x1 - x0) * (i + 0.5) / nx
            doc.text((x, y0 + 3.7), str(i + 1), 3.0); doc.text((x, y1 - 1.3), str(i + 1), 3.0)
        for k in range(ny + 1):
            y = y0 + (y1 - y0) * k / ny
            if 0 < k < ny:
                doc.line((x0, y), (x0 + z, y)); doc.line((x1 - z, y), (x1, y))
        for k in range(ny):
            y = y0 + (y1 - y0) * (k + 0.5) / ny + 1.1
            doc.text((x0 + 2.5, y), "ABCDEF"[k], 3.0); doc.text((x1 - 2.5, y), "ABCDEF"[k], 3.0)
        return x0 + z, y0 + z, x1 - z, y1 - z
    return x0, y0, x1, y1


def projection_symbol_first_angle(doc: Doc, x: float, y: float, h: float = 7.0) -> None:
    """ISO 5456-2 first-angle symbol, centred vertically on y, starting at x."""
    R, r = h / 2, h / 4
    cx = x + R
    doc.circle((cx, y), R, "thin")
    doc.circle((cx, y), r, "thin")
    x0 = cx + R + 3.0
    L = h * 1.1
    doc.poly([(x0, y - R), (x0 + L, y - r), (x0 + L, y + r), (x0, y + R)], "thin", closed=True)
    doc.line((cx - R - 1.2, y), (x0 + L + 1.2, y), "ctr")
