"""3-D solid model (build123d / OpenCASCADE) of the sandwich paddle and its grip.

Global axes match the 2-D drawings: x across the face, y from the butt (y = 0 is
the bottom of the butt cap) to the tip, z through the thickness (z = 0 on the
mid-plane).  Lay-up: bottom CF face sheet z = -8..-4, wave-rib core -4..+4,
top CF face sheet +4..+8.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from build123d import (Align, Box, Compound, Cylinder, Edge, Face, Kind, Location, Part, Plane, Pos,
                       RectangleRounded, Rot, Vector, Wire, export_step, export_stl, extrude, fillet,
                       offset)

from . import wave
from .geometry import CONSTRUCTION as C
from .geometry import Line, Outline, PaddleSpec, grip_dims

# densities [g/cm^3]
DENSITY = {"cf": 1.55, "core": 1.18, "tpu": 1.21, "pu": 1.10, "steel": 7.9, "brass": 8.5}


@dataclass
class PartDef:
    name: str
    shape: object
    material: str          # key of DENSITY / render material
    colour: tuple[float, float, float]


def outline_face(o: Outline, z: float = 0.0) -> Face:
    edges = []
    for s in o.segments:
        if isinstance(s, Line):
            edges.append(Edge.make_line((s.p0[0], s.p0[1], z), (s.p1[0], s.p1[1], z)))
        else:
            m = s.point(0.5)
            edges.append(Edge.make_three_point_arc((s.p0[0], s.p0[1], z), (m[0], m[1], z), (s.p1[0], s.p1[1], z)))
    return Face(Wire(edges))


def flute_channel_faces(x_half: float, y0: float, ext: float = 1.0) -> list[tuple[int, Face]]:
    """XZ faces of the open flutes above and below the wave rib.

    Each channel is bounded by the rib surface between two bond lands (where the
    rib meets the face sheet) and is closed `ext` beyond the core faces, so that
    subtracting it from the solid core slab leaves exactly the clipped wave."""
    zlim = C.core_t / 2
    faces = []
    for s in (+1, -1):
        zt = s * (zlim + ext)
        for a, b in wave.channel_bounds(x_half, s):
            n = max(6, int((b - a) / C.rib_pitch * 60))
            pts = [Vector(*_xz(wave.surface_point(u, s), y0)) for u in np.linspace(a, b, n)]
            faces.append((s, Face(Wire([Edge.make_spline(pts),
                                        Edge.make_line(pts[-1], Vector(pts[-1].X, y0, zt)),
                                        Edge.make_line(Vector(pts[-1].X, y0, zt), Vector(pts[0].X, y0, zt)),
                                        Edge.make_line(Vector(pts[0].X, y0, zt), pts[0])]))))
    return faces


def _xz(p: tuple[float, float], y: float) -> tuple[float, float, float]:
    return p[0], y, p[1]


def _runout_region(s: int, y_start: float, length: float):
    """Half-space where flutes opening towards side s (+1 top, -1 bottom) may exist.

    With length > 0 the flute end is a chamfer: the flute starts at y_start next to the far
    face sheet but only at y_start + length next to the near one.  The solid throat zone thus
    runs out under each face sheet as a thin tapered wedge (like a scarfed adherend) instead of
    a square step, which lowers the peel peak in the bond line; at 45 deg it prints without support."""
    h, zz = C.core_t / 2, 12.0

    def y_at(z: float) -> float:
        return y_start + length * (s * z + h) / (2 * h)
    pts = [Vector(-200, y_at(-zz), -zz), Vector(-200, y_at(zz), zz), Vector(-200, 600, zz), Vector(-200, 600, -zz)]
    face = Face(Wire([Edge.make_line(pts[i], pts[(i + 1) % 4]) for i in range(4)]))
    return extrude(face, amount=400, dir=(1, 0, 0))


def _axial_cylinder(d: float, y0: float, length: float):
    return Pos(0, y0, 0) * Rot(-90, 0, 0) * Cylinder(d / 2, length, align=(Align.CENTER, Align.CENTER, Align.MIN))


def rib_core(o: Outline, with_hole: bool = True):
    """Closed perimeter frame + solid handle/throat zone + clipped sinusoidal wave rib, one part."""
    sp = o.spec
    f = outline_face(o, -C.core_t / 2)
    slab = extrude(f, amount=C.core_t)
    inner = offset(f, amount=-C.frame_w, kind=Kind.ARC)
    prism = extrude(inner.moved(Location((0, 0, -2))), amount=C.core_t + 4)
    y0, y1 = C.solid_to - 2, sp.length + 2
    voids = []
    for s in (+1, -1):
        chans = [extrude(fc, amount=y1 - y0, dir=(0, 1, 0))
                 for side, fc in flute_channel_faces(sp.width / 2 + C.rib_pitch, y0) if side == s]
        region = prism & (_runout_region(s, C.solid_to, C.runout_len) if C.runout_len > 0 else
                          Pos(0, (C.solid_to + 400) / 2, 0) * Box(400, 400 - C.solid_to, 40))
        voids.append((Part() + chans) & region)
    core = slab - voids[0] - voids[1]
    if with_hole:
        core = core - _axial_cylinder(C.insert_d, sp.cap_length, C.insert_depth) \
                    - _axial_cylinder(C.screw_relief_d, sp.cap_length, C.screw_relief_depth)
    return core


def face_sheet(o: Outline, top: bool, edge_r: float = 0.8):
    z0 = C.core_t / 2 if top else -C.core_t / 2 - C.face_t
    plate = extrude(outline_face(o, z0), amount=C.face_t)
    if edge_r:
        zo = z0 + C.face_t if top else z0               # exposed (outer) face
        edges = plate.edges().filter_by(lambda e: abs(e.center().Z - zo) < 1e-6 and
                                        abs(e.start_point().Z - zo) < 1e-6 and abs(e.end_point().Z - zo) < 1e-6)
        try:
            plate = fillet(edges, edge_r)
        except Exception:                                # keep the sharp edge if OCC cannot fillet
            pass
    return plate


def _rrect_prism(w: float, h: float, r: float, y0: float, y1: float):
    pl = Plane(origin=(0, y0, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0))
    return extrude(pl * RectangleRounded(w, h, r), amount=y1 - y0)


def grip_parts(sp: PaddleSpec) -> list[PartDef]:
    g = grip_dims(sp)
    y0 = sp.cap_length
    core_w, core_t = sp.handle_width + 2 * C.sleeve_clear, sp.thickness + 2 * C.sleeve_clear
    sleeve = (_rrect_prism(g["sleeve_w"], g["sleeve_t"], C.sleeve_r, y0, g["sleeve_top"]) -
              _rrect_prism(core_w, core_t, 0.6, y0 - 1, g["sleeve_top"] + 1))
    wrap = (_rrect_prism(g["wrap_w"], g["wrap_t"], g["wrap_r"], g["wrap_bot"], g["wrap_top"]) -
            _rrect_prism(g["sleeve_w"], g["sleeve_t"], C.sleeve_r, g["wrap_bot"] - 1, g["wrap_top"] + 1))
    collar = (_rrect_prism(g["collar_w"], g["collar_t"], g["collar_r"], g["collar_bot"], g["collar_top"]) -
              _rrect_prism(g["wrap_w"], g["wrap_t"], g["wrap_r"], g["collar_bot"] - 1, g["collar_top"] + 1))
    cap =(_rrect_prism(g["cap_w"], g["cap_t"], g["cap_r"], 0.0, y0 + C.cap_skirt) -
           _rrect_prism(g["sleeve_w"], g["sleeve_t"], C.sleeve_r, y0, y0 + C.cap_skirt + 1) -
           _axial_cylinder(C.cb_d, -1.0, 1.0 + C.cb_depth) - _axial_cylinder(C.cap_hole_d, -1.0, y0 + 2))
    try:
        bottom = cap.edges().filter_by(lambda e: abs(e.center().Y) < 1e-6 and e.length > 5)
        cap = fillet(bottom, 1.0)
    except Exception:
        pass
    # ISO 7380 M4 x 12 button head screw: head dk 7.6, k 2.2, socket 2.5 AF
    yb = C.cb_depth                                   # bearing face on the counterbore floor
    head = _axial_cylinder(7.6, yb - 2.2, 2.2)
    try:
        head = fillet(head.edges().filter_by(lambda e: abs(e.center().Y - (yb - 2.2)) < 1e-6), 1.6)
    except Exception:
        pass
    hexsock = Pos(0, yb - 2.2 - 0.01, 0) * Rot(-90, 0, 0) * \
        extrude(Plane.XY * _hexagon(2.5), amount=1.4)
    screw = head - hexsock + _axial_cylinder(4.0, yb, C.screw_len)
    insert = _axial_cylinder(C.insert_d, y0, 8.1) - _axial_cylinder(3.4, y0 - 1, 10.1)
    return [PartDef("grip_sleeve", sleeve, "tpu", (0.10, 0.10, 0.11)),
            PartDef("grip_wrap", wrap, "pu", (0.06, 0.06, 0.07)),
            PartDef("throat_collar", collar, "tpu", (0.9, 0.9, 0.9)),
            PartDef("butt_cap", cap, "tpu", (0.9, 0.9, 0.9)),
            PartDef("screw_M4x12_ISO7380", screw, "steel", (0.75, 0.75, 0.78)),
            PartDef("insert_M4_heatset", insert, "brass", (0.78, 0.6, 0.25))]


def _hexagon(af: float):
    from build123d import RegularPolygon
    return RegularPolygon(af / math.sqrt(3), 6)


def assembly(o: Outline) -> list[PartDef]:
    return [PartDef("face_sheet_top", face_sheet(o, True), "cf", (0.12, 0.12, 0.13)),
            PartDef("rib_core", rib_core(o), "core", (0.85, 0.85, 0.2)),
            PartDef("face_sheet_bottom", face_sheet(o, False), "cf", (0.12, 0.12, 0.13))] + grip_parts(o.spec)


def mass_properties(parts: list[PartDef], pivot_y: float = 100.0) -> dict:
    """Mass [g], balance point [mm from butt], swing weight [kg cm^2 about x at y = pivot_y]."""
    import trimesh
    total, my, iyy = 0.0, 0.0, 0.0
    per = {}
    for p in parts:
        v, f = tessellate(p.shape, 0.05)
        m = trimesh.Trimesh(v, f, process=True)
        rho = DENSITY[p.material] * 1e-3                      # g/mm^3
        vol = p.shape.volume                                  # exact B-rep volume; the mesh gives COM + inertia
        mass = vol * rho
        com = m.center_mass
        inertia = m.moment_inertia * rho * vol / m.volume     # g mm^2 about COM (density-scaled)
        ixx_c = inertia[0, 0]
        ixx_pivot = ixx_c + mass * ((com[1] - pivot_y) ** 2 + com[2] ** 2)
        per[p.name] = dict(volume_cm3=vol / 1000, mass_g=mass, watertight=bool(m.is_watertight))
        total += mass
        my += mass * com[1]
        iyy += ixx_pivot
    return dict(parts=per, mass_g=total, balance_mm=my / total, swing_weight_kgcm2=iyy * 1e-5)


def tessellate(shape, tol: float = 0.05, ang: float = 0.2):
    verts, tris = shape.tessellate(tol, ang)
    return np.array([(v.X, v.Y, v.Z) for v in verts]), np.array(tris)


def export(parts: list[PartDef], stem: str, outdir) -> None:
    from pathlib import Path
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    kids = []
    for p in parts:
        s = p.shape
        s.label = p.name
        kids.append(s)
        export_stl(s, str(outdir / f"{stem}_{p.name}.stl"), tolerance=0.03, angular_tolerance=0.15)
    export_step(Compound(children=kids, label=stem), str(outdir / f"{stem}_assembly.step"))
