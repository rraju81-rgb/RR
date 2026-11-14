"""Hidden-line projection of solids to 2D polylines (thin wrapper over OpenCascade HLR)."""
from __future__ import annotations

import numpy as np
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.BRepLib import BRepLib
from OCP.GCPnts import GCPnts_QuasiUniformDeflection
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS

# eye direction (from the part towards the viewer) and the screen x-axis, in lamp coordinates
VIEWS = {
    "top": ((0, 0, 1), (1, 0, 0)),        # plan: x right, y up (back of lamp up)
    "lens": ((0, -1, 0), (1, 0, 0)),      # looking at the lens: x right, z up
    "back": ((0, 1, 0), (-1, 0, 0)),      # looking at the back wall
    "tip": ((1, 0, 0), (0, 1, 0)),        # end view from the tip: y right, z up
    "root": ((-1, 0, 0), (0, -1, 0)),     # end view from the bike side
}


def iso_view(eye, up=(0, 0, 1)):
    eye = np.asarray(eye, float)
    eye = eye / np.linalg.norm(eye)
    x = np.cross(up, eye)
    x = x / np.linalg.norm(x)
    return tuple(eye), tuple(x)


def _polylines(compound, deflection):
    out = []
    if compound is None or compound.IsNull():
        return out
    BRepLib.BuildCurves3d_s(compound)
    exp = TopExp_Explorer(compound, TopAbs_EDGE)
    while exp.More():
        edge = TopoDS.Edge_s(exp.Current())
        curve = BRepAdaptor_Curve(edge)
        disc = GCPnts_QuasiUniformDeflection(curve, deflection)
        if disc.IsDone() and disc.NbPoints() >= 2:
            pts = [(disc.Value(i).X(), disc.Value(i).Y()) for i in range(1, disc.NbPoints() + 1)]
            out.append(pts)
        exp.Next()
    return out


def project(shapes: dict, eye, xdir, deflection=0.02, hidden=False):
    """Project several named shapes together (they hide each other).

    Returns {name: {"visible": [polyline...], "hidden": [polyline...]}} in mm, screen coordinates.
    """
    algo = HLRBRep_Algo()
    for s in shapes.values():
        algo.Add(s.wrapped)
    algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*eye), gp_Dir(*xdir))))
    algo.Update()
    algo.Hide()
    hs = HLRBRep_HLRToShape(algo)
    result = {}
    for name, s in shapes.items():
        vis = []
        for getter in (hs.VCompound, hs.Rg1LineVCompound, hs.OutLineVCompound):
            vis += _polylines(getter(s.wrapped), deflection)
        hid = []
        if hidden:
            for getter in (hs.HCompound, hs.OutLineHCompound):
                hid += _polylines(getter(s.wrapped), deflection)
        result[name] = {"visible": vis, "hidden": hid}
    return result


def to_screen(point, eye, xdir):
    """Project a 3D point with the same convention as `project`."""
    eye = np.asarray(eye, float)
    eye = eye / np.linalg.norm(eye)
    x = np.asarray(xdir, float)
    x = x - eye * np.dot(x, eye)
    x = x / np.linalg.norm(x)
    y = np.cross(eye, x)
    p = np.asarray(point, float)
    return float(p @ x), float(p @ y)


def bounds(proj):
    xs, ys = [], []
    for part in proj.values():
        for kind in ("visible", "hidden"):
            for pl in part[kind]:
                for x, y in pl:
                    xs.append(x)
                    ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)
