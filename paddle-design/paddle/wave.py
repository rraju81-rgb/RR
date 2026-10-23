"""Wave-rib geometry shared by the solid model and the drawings (pure math, mm).

The rib centre line is z = A cos(2 pi x / pitch) (a crest, i.e. a top bond land, on the
paddle centre line x = 0).  Its two surfaces are offset by half the wall thickness along
the normal; where a surface passes the face-sheet plane z = +-core_t / 2 it is cut flat,
which forms the bond lands.
"""
from __future__ import annotations

import math

import numpy as np

from .geometry import CONSTRUCTION as C


def surface_point(u: float, s: int, amp: float | None = None) -> tuple[float, float]:
    """(x, z) of the upper (s = +1) / lower (s = -1) rib surface at centre-line parameter u."""
    A = C.rib_amp if amp is None else amp
    k = 2 * math.pi / C.rib_pitch
    z = A * math.cos(k * u)
    d = -A * k * math.sin(k * u)
    n = math.sqrt(1 + d * d)
    return u - s * C.rib_t / 2 * d / n, z + s * C.rib_t / 2 / n


def channel_bounds(x_half: float, s: int, amp: float | None = None) -> list[tuple[float, float]]:
    """Centre-line parameter intervals of the open flutes on side s (+1 top, -1 bottom) for |x| <= x_half.

    A flute on side s lies between two bond lands of that side; its ends are the roots of
    s * z_surface(u) = core_t / 2."""
    zlim = C.core_t / 2

    def g(u: float) -> float:                  # > 0 where the rib surface reaches the face sheet (land)
        return s * surface_point(u, s, amp)[1] - zlim
    us = np.linspace(-x_half, x_half, int(2 * x_half / C.rib_pitch * 400) + 1)
    gv = np.array([g(u) for u in us])
    roots = []
    for i in range(len(us) - 1):
        if (gv[i] > 0) != (gv[i + 1] > 0):
            a, b = us[i], us[i + 1]
            for _ in range(60):
                m = (a + b) / 2
                if (g(m) > 0) == (gv[i] > 0):
                    a = m
                else:
                    b = m
            roots.append((a + b) / 2)
    bounds = ([-x_half] if gv[0] <= 0 else []) + roots + ([x_half] if gv[-1] <= 0 else [])
    return list(zip(bounds[0::2], bounds[1::2]))


def land_width(amp: float | None = None) -> float:
    """Width of one bond land (the flat cut crest) in the face-sheet plane."""
    # the land centred on x = 0 ends where the flute to its right begins
    right = min(iv[0] for iv in channel_bounds(1.5 * C.rib_pitch, +1, amp) if iv[0] > 0)
    return 2 * surface_point(right, +1, amp)[0]


def land_intervals(x_half: float, s: int) -> list[tuple[float, float]]:
    """x intervals of the bond lands on side s within |x| <= x_half (face-sheet plane)."""
    edges = [-x_half]
    for a, b in channel_bounds(x_half + C.rib_pitch, s):
        edges += [surface_point(a, s)[0], surface_point(b, s)[0]]
    edges.append(x_half)
    out = []
    for lo, hi in zip(edges[0::2], edges[1::2]):
        lo, hi = max(lo, -x_half), min(hi, x_half)
        if hi > lo + 1e-6:
            out.append((lo, hi))
    return out


def wall_polygon(x0: float, x1: float, n: int = 400) -> list[tuple[float, float]]:
    """Cross-section (x, z) of the wave wall between x0 and x1, clipped flat at the face sheets."""
    h = C.core_t / 2
    us = np.linspace(x0, x1, n)
    top = [surface_point(u, +1) for u in us]
    bot = [surface_point(u, -1) for u in us]
    top = [(x, min(z, h)) for x, z in top if x0 <= x <= x1]
    bot = [(x, max(z, -h)) for x, z in bot if x0 <= x <= x1]
    return top + bot[::-1]


def under_land_wall(amp: float | None = None) -> float:
    """Wall thickness left under the middle of a land (crest): core_t/2 - (A - t/2)."""
    return C.core_t / 2 - ((C.rib_amp if amp is None else amp) - C.rib_t / 2)
