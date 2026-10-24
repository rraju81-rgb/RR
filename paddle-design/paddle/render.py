"""2-D presentation render of the paddles (SVG, rasterised by Chromium).

The face artwork (carbon weave, edge guard, accent line, the printed grip)
is drawn once in paddle coordinates (mm, y up) and placed on the board through
an affine matrix: plain scaling for the front views, the projected face plane
for the 3/4 views.  The silhouette is always the exact CAD outline.
"""
from __future__ import annotations

import math
from xml.sax.saxutils import escape

from .geometry import Line, Outline
from .grip import PADDLE_GRIP, face_path
from .pictorial import project, three_quarter
from .svgkit import f, fmt

SANS = "Inter, 'DejaVu Sans', Arial, sans-serif"

THEMES = {
    "elongated": {"accent": "#c8f03c", "accent_dark": "#7da11a", "grip": "#17181a"},
    "hybrid": {"accent": "#ff6b3d", "accent_dark": "#b8401c", "grip": "#17181a"},
}


def model_path(o: Outline) -> str:
    """Outline path in raw model coordinates (to be used inside a y-flipping transform)."""
    s0 = o.segments[0]
    d = [f"M{f(s0.p0[0])},{f(s0.p0[1])}"]
    for s in o.segments:
        x, y = s.p1
        if isinstance(s, Line):
            d.append(f"L{f(x)},{f(y)}")
        else:
            large = 1 if abs(s.sweep) > math.pi else 0
            d.append(f"A{f(s.r)},{f(s.r)} 0 {large} {1 if s.sweep > 0 else 0} {f(x)},{f(y)}")
    return " ".join(d) + "Z"


def inset_polyline(o: Outline, dist: float, y_min: float) -> str:
    """Polyline offset `dist` mm inside the outline, kept only where y > y_min (blade)."""
    ring = o.polyline(1.0)
    n = len(ring)
    pts = []
    for i in range(n):
        (x0, y0), (x1, y1), (x2, y2) = ring[i - 1], ring[i], ring[(i + 1) % n]
        nx1, ny1 = -(y1 - y0), x1 - x0                 # inward normal of a CCW loop
        nx2, ny2 = -(y2 - y1), x2 - x1
        l1, l2 = math.hypot(nx1, ny1) or 1, math.hypot(nx2, ny2) or 1
        nx, ny = nx1 / l1 + nx2 / l2, ny1 / l1 + ny2 / l2
        ln = math.hypot(nx, ny) or 1
        pts.append((x1 + dist * nx / ln, y1 + dist * ny / ln))
    # rotate so the open run starts in the handle, then keep the blade part
    start = min(range(n), key=lambda i: (ring[i][1], ring[i][0]))
    pts = pts[start:] + pts[:start]
    keep = [p for p in pts if p[1] > y_min]
    return " ".join(f"{f(x)},{f(y)}" for x, y in keep)


def defs_for(o: Outline, key: str, theme: dict) -> str:
    cell = 2.6
    tows = []
    for r in range(4):
        for c in range(4):
            horiz = (c - r) % 4 < 2
            g = f"url(#tow{'H' if horiz else 'V'}-{key})"
            tows.append(f'<rect x="{f(c * cell)}" y="{f(r * cell)}" width="{f(cell)}" height="{f(cell)}" fill="{g}"/>')
    return f"""
<linearGradient id="towH-{key}" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#1d1f22"/><stop offset="0.45" stop-color="#3b3f45"/><stop offset="1" stop-color="#1a1c1f"/>
</linearGradient>
<linearGradient id="towV-{key}" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="#16181a"/><stop offset="0.55" stop-color="#2c2f34"/><stop offset="1" stop-color="#141517"/>
</linearGradient>
<pattern id="carbon-{key}" width="{f(4 * cell)}" height="{f(4 * cell)}" patternUnits="userSpaceOnUse"
         patternTransform="rotate(45)">{''.join(tows)}</pattern>
<pattern id="grip-{key}" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(-62)">
  <rect width="14" height="14" fill="{theme['grip']}"/>
  <rect y="0" width="14" height="1.3" fill="#000" opacity="0.55"/>
  <rect y="1.3" width="14" height="0.7" fill="#fff" opacity="0.07"/>
  <circle cx="3.5" cy="5.5" r="0.45" fill="#000" opacity="0.6"/><circle cx="10.5" cy="5.5" r="0.45" fill="#000" opacity="0.6"/>
  <circle cx="7" cy="10" r="0.45" fill="#000" opacity="0.6"/><circle cx="0" cy="10" r="0.45" fill="#000" opacity="0.6"/>
</pattern>
<linearGradient id="sheen-{key}" gradientUnits="userSpaceOnUse" x1="-120" y1="400" x2="120" y2="120">
  <stop offset="0" stop-color="#fff" stop-opacity="0.16"/><stop offset="0.38" stop-color="#fff" stop-opacity="0.03"/>
  <stop offset="0.55" stop-color="#fff" stop-opacity="0.10"/><stop offset="0.7" stop-color="#fff" stop-opacity="0"/>
  <stop offset="1" stop-color="#000" stop-opacity="0.18"/>
</linearGradient>
<linearGradient id="gripshade-{key}" gradientUnits="userSpaceOnUse" x1="-21" y1="0" x2="21" y2="0">
  <stop offset="0" stop-color="#000" stop-opacity="0.45"/><stop offset="0.35" stop-color="#fff" stop-opacity="0.10"/>
  <stop offset="0.6" stop-color="#fff" stop-opacity="0.04"/><stop offset="1" stop-color="#000" stop-opacity="0.5"/>
</linearGradient>
<linearGradient id="accent-{key}" gradientUnits="userSpaceOnUse" x1="-15" y1="0" x2="15" y2="0">
  <stop offset="0" stop-color="{theme['accent_dark']}"/><stop offset="0.4" stop-color="{theme['accent']}"/>
  <stop offset="1" stop-color="{theme['accent_dark']}"/>
</linearGradient>
<clipPath id="clip-{key}"><path d="{model_path(o)}"/></clipPath>
<clipPath id="blade-{key}"><rect x="-200" y="{f(o.spec.handle_length - 1.5)}" width="400" height="400"/></clipPath>
"""


def face_art(o: Outline, key: str, theme: dict) -> str:
    """Face artwork in model coordinates (y up)."""
    sp = o.spec
    L, t = sp.length, sp.handle_length
    a = sp.width / 2
    path = model_path(o)
    grip = face_path(PADDLE_GRIP[sp.key])
    name_y = o.pts["side_lo"][1] + 14
    return f"""
<g clip-path="url(#clip-{key})">
  <rect x="{f(-a - 5)}" y="-5" width="{f(2 * a + 10)}" height="{f(L + 10)}" fill="url(#carbon-{key})"/>
  <rect x="{f(-a - 5)}" y="-5" width="{f(2 * a + 10)}" height="{f(L + 10)}" fill="url(#sheen-{key})"/>
  <g clip-path="url(#blade-{key})">
    <polyline points="{inset_polyline(o, 11.0, t + 6)}" fill="none" stroke="{theme['accent']}" stroke-width="1.4"
              stroke-linejoin="round" opacity="0.95"/>
    <polyline points="{inset_polyline(o, 14.0, t + 9)}" fill="none" stroke="{theme['accent']}" stroke-width="0.5"
              stroke-linejoin="round" opacity="0.55"/>
    <path d="{path}" fill="none" stroke="#0d0e10" stroke-width="9"/>
    <path d="{path}" fill="none" stroke="#3a3d42" stroke-width="2.2" stroke-opacity="0.9"/>
  </g>
  <g transform="translate(0 {f(name_y)}) scale(1 -1)">
    <text x="0" y="0" font-family="{SANS}" font-size="9.5" font-weight="700" letter-spacing="2.2"
          text-anchor="middle" fill="{theme['accent']}">{escape(sp.name)}</text>
  </g>
  <g transform="translate(0 {f(name_y - 8.5)}) scale(1 -1)">
    <text x="0" y="0" font-family="{SANS}" font-size="4.2" letter-spacing="1.2" text-anchor="middle"
          fill="#d9dde2" opacity="0.75">{fmt(sp.length)} × {fmt(sp.width)} × {fmt(sp.thickness)} mm</text>
  </g>
</g>
<path d="{path}" fill="none" stroke="#000" stroke-width="0.6" stroke-opacity="0.85"/>
<path d="{grip}" fill="url(#grip-{key})"/>
<path d="{grip}" fill="url(#gripshade-{key})"/>
<path d="{grip}" fill="none" stroke="#000" stroke-width="0.5" stroke-opacity="0.9"/>
"""


def matrix(a: float, b: float, c: float, d: float, e: float, f_: float) -> str:
    return f"matrix({f(a)} {f(b)} {f(c)} {f(d)} {f(e)} {f(f_)})"


def front_view(o: Outline, key: str, theme: dict, cx: float, top: float, s: float) -> str:
    L = o.spec.length
    m = matrix(s, 0, 0, -s, cx, top + L * s)
    shadow = matrix(s, 0, 0, -s, cx + 9, top + L * s + 13)
    return (f'<g transform="{shadow}" filter="url(#soft)" opacity="0.35"><path d="{model_path(o)}" fill="#000"/></g>'
            f'<g transform="{m}">{face_art(o, key, theme)}</g>')


def three_quarter_view(o: Outline, key: str, theme: dict, centre: tuple[float, float], s: float,
                       yaw: float, pitch: float, roll: float) -> str:
    fr = three_quarter(yaw, pitch, roll)
    pic = project(o, fr, step=1.5)
    U, V, W = fr
    u0, v0, u1, v1 = pic.bbox
    ox = centre[0] - (u0 + u1) / 2 * s
    oy = centre[1] + (v0 + v1) / 2 * s
    zf = o.spec.thickness / 2 * (1 if W[2] > 0 else -1)
    light = (-0.45, 0.55, 0.70)
    ln = math.sqrt(sum(c * c for c in light))
    light = tuple(c / ln for c in light)

    def S(p):
        return f"{f(ox + p[0] * s)},{f(oy - p[1] * s)}"

    walls = []
    sil = []
    for w in pic.walls:
        k = max(0.0, sum(a * b for a, b in zip(w.normal, light)))
        g = int(22 + 70 * k)
        col = f"#{g:02x}{g + 2:02x}{g + 5:02x}"
        pts = " ".join(S(p) for p in w.quad)
        walls.append(f'<polygon points="{pts}" fill="{col}" stroke="{col}" stroke-width="0.6"/>')
        sil.append(f'<polygon points="{pts}" fill="#000"/>')
    face_pts = " ".join(S(p) for p in pic.face)
    m = matrix(s * U[0], -s * V[0], s * U[1], -s * V[1], ox + s * U[2] * zf, oy - s * V[2] * zf)
    shadow = (f'<g transform="translate(10 16)" filter="url(#soft)" opacity="0.32">{"".join(sil)}'
              f'<polygon points="{face_pts}" fill="#000"/></g>')
    return shadow + "".join(walls) + f'<g transform="{m}">{face_art(o, key + "-q", theme)}</g>'


def dim_h(x0: float, x1: float, y: float, label: str) -> str:
    """Light dimension line with the label set in a gap of the line."""
    c, xm, g = "#8c8f94", (x0 + x1) / 2, 38
    return (f'<g stroke="{c}" stroke-width="1"><line x1="{f(x0)}" y1="{f(y)}" x2="{f(xm - g)}" y2="{f(y)}"/>'
            f'<line x1="{f(xm + g)}" y1="{f(y)}" x2="{f(x1)}" y2="{f(y)}"/>'
            f'<line x1="{f(x0)}" y1="{f(y - 7)}" x2="{f(x0)}" y2="{f(y + 7)}"/>'
            f'<line x1="{f(x1)}" y1="{f(y - 7)}" x2="{f(x1)}" y2="{f(y + 7)}"/></g>'
            f'<text x="{f(xm)}" y="{f(y + 5)}" font-family="{SANS}" font-size="15" font-weight="600" '
            f'text-anchor="middle" fill="#55585e">{label}</text>')


def dim_v(x: float, y0: float, y1: float, label: str) -> str:
    c, ym, g = "#8c8f94", (y0 + y1) / 2, 38
    return (f'<g stroke="{c}" stroke-width="1"><line x1="{f(x)}" y1="{f(y0)}" x2="{f(x)}" y2="{f(ym - g)}"/>'
            f'<line x1="{f(x)}" y1="{f(ym + g)}" x2="{f(x)}" y2="{f(y1)}"/>'
            f'<line x1="{f(x - 7)}" y1="{f(y0)}" x2="{f(x + 7)}" y2="{f(y0)}"/>'
            f'<line x1="{f(x - 7)}" y1="{f(y1)}" x2="{f(x + 7)}" y2="{f(y1)}"/></g>'
            f'<text x="{f(x + 5)}" y="{f(ym)}" font-family="{SANS}" font-size="15" font-weight="600" '
            f'text-anchor="middle" fill="#55585e" transform="rotate(-90 {f(x + 5)} {f(ym)})">{label}</text>')


def board(outlines: list[Outline]) -> tuple[str, float, float]:
    """Both paddles: front faces with dimensions, 3/4 views and spec captions."""
    W, H = 1800.0, 1140.0
    s = 2.0                                            # px per mm on the front views
    defs = ['<filter id="soft" x="-20%" y="-20%" width="140%" height="140%">'
            '<feGaussianBlur stdDeviation="9"/></filter>',
            '<radialGradient id="bg" cx="0.5" cy="0.42" r="0.75"><stop offset="0" stop-color="#fbfbf9"/>'
            '<stop offset="1" stop-color="#dfe0dc"/></radialGradient>']
    body = [f'<rect width="{f(W)}" height="{f(H)}" fill="url(#bg)"/>',
            f'<text x="70" y="78" font-family="{SANS}" font-size="38" font-weight="700" fill="#1c1d20">'
            'Pickleball paddle designs</text>',
            f'<text x="70" y="112" font-family="{SANS}" font-size="19" fill="#5d6066">'
            'Elongated &amp; Hybrid  ·  39 cm overall  ·  26 cm blade + 13 cm handle  ·  3 cm handle  '
            '·  1.6 cm thick</text>']
    slots = [(330.0, 650.0), (1230.0, 1550.0)]
    captions = {
        "elongated": ("Square head · R48 tip corners", "R25 shoulders · 30° taper · R15 throat"),
        "hybrid": ("Domed head · R150 crown, R30 shoulders", "R25 shoulders · 30° taper · R15 throat"),
    }
    top = 182.0
    for o, (fx, qx) in zip(outlines, slots):
        sp = o.spec
        key = sp.key
        th = THEMES[key]
        defs.append(defs_for(o, key, th))
        defs.append(defs_for(o, key + "-q", th))
        body.append(front_view(o, key, th, fx, top, s))
        body.append(three_quarter_view(o, key, th, (qx, top + 330), 1.42, yaw=-38, pitch=14, roll=-9))
        a = sp.width / 2 * s
        body.append(dim_h(fx - a, fx + a, top - 34, f"{fmt(sp.width)} mm"))
        body.append(dim_v(fx - a - 44, top, top + sp.length * s, f"{fmt(sp.length)} mm"))
        hb = top + (sp.length - sp.handle_length) * s
        body.append(f'<line x1="{f(fx + 26)}" y1="{f(hb)}" x2="{f(fx + 80)}" y2="{f(hb)}" stroke="#8c8f94" '
                    f'stroke-dasharray="5 4"/>'
                    f'<text x="{f(fx + 86)}" y="{f(hb - 6)}" font-family="{SANS}" font-size="13" fill="#6b6e74">'
                    f'blade {fmt(sp.blade_length)}</text>'
                    f'<text x="{f(fx + 86)}" y="{f(hb + 17)}" font-family="{SANS}" font-size="13" fill="#6b6e74">'
                    f'handle {fmt(sp.handle_length)} × {fmt(sp.handle_width)}</text>')
        cy = top + sp.length * s + 66
        c1, c2 = captions[key]
        body.append(
            f'<rect x="{f(fx - 190)}" y="{f(cy - 32)}" width="10" height="70" rx="2" fill="{th["accent"]}"/>'
            f'<text x="{f(fx - 166)}" y="{f(cy)}" font-family="{SANS}" font-size="30" font-weight="700" '
            f'fill="#1c1d20">{sp.name.title()}</text>'
            f'<text x="{f(fx - 166)}" y="{f(cy + 28)}" font-family="{SANS}" font-size="17" fill="#45484e">'
            f'{fmt(sp.length)} × {fmt(sp.width)} × {fmt(sp.thickness)} mm  ·  {c1}</text>'
            f'<text x="{f(fx - 166)}" y="{f(cy + 52)}" font-family="{SANS}" font-size="17" fill="#45484e">'
            f'{c2}  ·  face {o.area / 100:.0f} cm²</text>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{f(W)}" height="{f(H)}" viewBox="0 0 {f(W)} {f(H)}">'
           f'<defs>{"".join(defs)}</defs>{"".join(body)}</svg>')
    return svg, W, H
