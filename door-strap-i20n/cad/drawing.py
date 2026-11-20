"""Dimensioned 2-D drawings (hidden-line projections from the B-rep).

usage: python drawing.py <out_dir>
"""
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                       # noqa: E402
from matplotlib.patches import FancyArrowPatch, Arc   # noqa: E402
from OCP.BRepAdaptor import BRepAdaptor_Curve         # noqa: E402
from OCP.GCPnts import GCPnts_QuasiUniformDeflection  # noqa: E402
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt             # noqa: E402
from OCP.HLRAlgo import HLRAlgo_Projector             # noqa: E402
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape  # noqa: E402
from OCP.TopAbs import TopAbs_EDGE                    # noqa: E402
from OCP.TopExp import TopExp_Explorer                # noqa: E402
from OCP.TopoDS import TopoDS                         # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import door_strap as ds   # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "renders")
os.makedirs(OUT, exist_ok=True)
INK = "#1d1d1f"
DIM = "#c0392b"
HID = "#9a9a9e"


def hlr(shape, eye, xdir):
    algo = HLRBRep_Algo()
    algo.Add(shape)
    algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*eye),
                                            gp_Dir(*xdir))))
    algo.Update()
    algo.Hide()
    h = HLRBRep_HLRToShape(algo)
    vis = [h.VCompound(), h.OutLineVCompound(), h.Rg1LineVCompound()]
    hid = [h.HCompound(), h.OutLineHCompound()]

    def polylines(comps):
        out = []
        for c in comps:
            if c is None or c.IsNull():
                continue
            ex = TopExp_Explorer(c, TopAbs_EDGE)
            while ex.More():
                e = TopoDS.Edge_s(ex.Current())
                cur = BRepAdaptor_Curve(e)
                disc = GCPnts_QuasiUniformDeflection(cur, 0.02)
                if disc.IsDone() and disc.NbPoints() > 1:
                    pts = [disc.Value(i) for i in range(1, disc.NbPoints() + 1)]
                    out.append(([p.X() for p in pts], [p.Y() for p in pts]))
                ex.Next()
        return out
    return polylines(vis), polylines(hid)


def draw_view(ax, shape, eye, xdir, dx=0.0, dy=0.0, hidden=True, lw=0.8):
    vis, hid = hlr(shape, eye, xdir)
    if hidden:
        for x, y in hid:
            ax.plot([v + dx for v in x], [v + dy for v in y], color=HID,
                    lw=0.35, ls=(0, (3, 2)))
    for x, y in vis:
        ax.plot([v + dx for v in x], [v + dy for v in y], color=INK, lw=lw,
                solid_capstyle="round")


def dim(ax, p1, p2, off, text, horiz=True, fs=7.5, ext=1.5):
    """Linear dimension between p1 and p2 offset by `off` (mm)."""
    (x1, y1), (x2, y2) = p1, p2
    if horiz:
        yl = (y1 if off > 0 else y1) + off
        ax.plot([x1, x1], [y1, yl + math.copysign(ext, off)], color=DIM,
                lw=0.4)
        ax.plot([x2, x2], [y2, yl + math.copysign(ext, off)], color=DIM,
                lw=0.4)
        a = FancyArrowPatch((x1, yl), (x2, yl), arrowstyle="<|-|>",
                            mutation_scale=6, color=DIM, lw=0.6)
        ax.add_patch(a)
        ax.text((x1 + x2) / 2, yl + (1.2 if off > 0 else -1.2), text,
                ha="center", va="bottom" if off > 0 else "top", fontsize=fs,
                color=DIM)
    else:
        xl = x1 + off
        ax.plot([x1, xl + math.copysign(ext, off)], [y1, y1], color=DIM,
                lw=0.4)
        ax.plot([x2, xl + math.copysign(ext, off)], [y2, y2], color=DIM,
                lw=0.4)
        a = FancyArrowPatch((xl, y1), (xl, y2), arrowstyle="<|-|>",
                            mutation_scale=6, color=DIM, lw=0.6)
        ax.add_patch(a)
        ax.text(xl + (1.2 if off > 0 else -1.2), (y1 + y2) / 2, text,
                ha="left" if off > 0 else "right", va="center",
                rotation=90, fontsize=fs, color=DIM)


def note(ax, xy, xytext, text, fs=7):
    ax.annotate(text, xy=xy, xytext=xytext, fontsize=fs, color=INK,
                arrowprops=dict(arrowstyle="-", color=INK, lw=0.5,
                                shrinkA=0, shrinkB=0),
                ha="left", va="center")


def housing_sheet():
    H = ds.build_housing().val().wrapped
    fig = plt.figure(figsize=(16.54, 11.69), dpi=150)   # A3 landscape
    ax = fig.add_axes([0.03, 0.06, 0.94, 0.9])
    ax.set_aspect("equal")
    ax.axis("off")
    # front view at origin (X right, Z up)
    draw_view(ax, H, (0, -1, 0), (1, 0, 0))
    # top view above (X right, Y up: face at the bottom)
    TOPY = 70.0
    draw_view(ax, H, (0, 0, 1), (1, 0, 0), dy=TOPY)
    # right side view (viewer at +X): Y right, Z up
    SIDEX = 135.0
    draw_view(ax, H, (1, 0, 0), (0, 1, 0), dx=SIDEX)
    # section through the pivot (Y-Z plane seen from +X) -> mechanism layout
    L, Hh = ds.FACE_L, ds.FACE_H_REAR
    # --- front view dims
    xr, xf = -L / 2, L / 2
    dim(ax, (xr, -Hh / 2), (xf, -Hh / 2), -22, f"{L:.0f}  (visible face)")
    e0, e1 = ds.EARS[0][0], ds.EARS[1][0]
    dim(ax, (e0, 0), (e1, 0), -75, f"{e1 - e0:.0f}  (screw ears, verify)")
    dim(ax, (e0 - ds.EAR_W / 2, -4), (e1 + ds.EAR_W / 2, -4), -88,
        f"{e1 - e0 + ds.EAR_W:.0f}  overall")
    dim(ax, (xr, -ds.FACE_H_REAR / 2), (xr, ds.FACE_H_REAR / 2), -14,
        f"{ds.FACE_H_REAR:.0f}", horiz=False)
    dim(ax, (xf, -ds.FACE_H_FRONT / 2), (xf, ds.FACE_H_FRONT / 2), 22,
        f"{ds.FACE_H_FRONT:.0f}", horiz=False)
    sx = ds.SLOT_X
    dim(ax, (0, ds.SLOT_LEN / 2), (sx, ds.SLOT_LEN / 2), 30,
        f"{abs(sx):.0f}", fs=6.5)
    note(ax, (sx, -ds.SLOT_LEN / 2 + 1), (-52, -49),
         f"strap slot {ds.SLOT_LEN:.1f} x {ds.SLOT_W:.0f}  (25 mm webbing)")
    bx0, bx1 = ds.BADGE_X
    note(ax, (bx1 - 3, -ds.BADGE_H / 2 + 2), (22, -49),
         f"badge pocket {bx1 - bx0:.0f} x {ds.BADGE_H:.0f} x 1.0-3.0 deep")
    note(ax, (ds.PIVOT[0], 30), (-128, 46),
         f"pivot axis X{ds.PIVOT[0]:.0f} / Y{ds.PIVOT[1]:.0f}  (pin 4 x 70)")
    ax.plot([0, 0], [-45, 45], color=HID, lw=0.4, ls="-.")
    ax.plot([-95, 95], [0, 0], color=HID, lw=0.4, ls="-.")
    for z in ds.GROOVE_Z:
        pass
    ax.text(-128, 100, "grooves: 6 x R5.5, depth 1.2, pitch 11.5\n"
            "face crown: R160 vertical / R1500 horizontal",
            fontsize=6.5, color=INK, va="top")
    # --- top view dims
    dim(ax, (xf, TOPY + 0), (xf, TOPY + ds.DEPTH), 26, f"{ds.DEPTH:.0f}",
        horiz=False)
    dim(ax, (xr - ds.FLANGE_W, TOPY + ds.FLANGE_Y0),
        (xr - ds.FLANGE_W, TOPY + ds.FLANGE_Y0 + ds.FLANGE_T), -20,
        f"flange {ds.FLANGE_Y0:.0f}-{ds.FLANGE_Y0 + ds.FLANGE_T:.1f}",
        horiz=False, fs=6.5)
    dim(ax, (e1, TOPY + ds.EAR_Y[1]), (e1, TOPY), 16,
        f"ear face Y{ds.EAR_Y[1]:.0f}", horiz=False, fs=6.5)
    px, py = ds.PIVOT
    ax.plot(px, TOPY + py, marker="+", color=DIM, ms=8, mew=0.8)
    note(ax, (px, TOPY + py), (-30, TOPY + 52),
         f"pivot {px:.0f}, {py:.0f}")
    cx0, cx1 = ds.CHANNEL_X
    note(ax, ((cx0 + cx1) / 2, TOPY + ds.CABLE_Y), (-110, TOPY + 52),
         f"cable anchor slider, adj. {ds.SLIDER_TRAVEL:.1f} mm\n"
         f"cable axis Y{ds.CABLE_Y:.1f}  Z0")
    # --- side view dims
    dim(ax, (SIDEX, -ds.FACE_H_REAR / 2 - ds.FLANGE_W),
        (SIDEX, ds.FACE_H_REAR / 2 + ds.FLANGE_W), -10,
        f"{ds.FACE_H_REAR + 2 * ds.FLANGE_W:.0f} (flange)", horiz=False,
        fs=6.5)
    # title block
    ax.text(95, -95,
            "DOOR STRAP MODULE  -  Hyundai i20 N (BC3) front doors\n"
            "Housing, LH shown (RH = mirror).  Units: mm.  Projection: third angle\n"
            "Material: tough ABS-like resin (SLA) or PET-CF.  Mass ~86 g\n"
            "Red dimensions marked 'verify' are vehicle-interface ESTIMATES",
            fontsize=7.5, color=INK, va="top", ha="left",
            bbox=dict(boxstyle="square,pad=0.6", fc="white", ec=INK, lw=0.6))
    ax.text(-60, TOPY + 66, "TOP", fontsize=9, color=INK, weight="bold")
    ax.text(-60, 50, "FRONT (occupant side)", fontsize=9, color=INK,
            weight="bold")
    ax.text(SIDEX - 10, 50, "RIGHT", fontsize=9, color=INK, weight="bold")
    ax.set_xlim(-130, 215)
    ax.set_ylim(-110, 140)
    fig.savefig(os.path.join(OUT, "drawing_housing.png"), dpi=150,
                facecolor="white")
    fig.savefig(os.path.join(OUT, "drawing_housing.pdf"), facecolor="white")
    plt.close(fig)


def lever_sheet():
    lev = ds.build_lever()
    rest = ds.pose_lever(lev, ds.POSE_REST).val().wrapped
    full = ds.pose_lever(lev, ds.POSE_FULL).val().wrapped
    fig = plt.figure(figsize=(11.69, 8.27), dpi=150)   # A4 landscape
    ax = fig.add_axes([0.04, 0.08, 0.92, 0.86])
    ax.set_aspect("equal")
    ax.axis("off")
    # face outline for context (section at Z=0)
    import numpy as np
    xs = np.linspace(-70, 70, 200)
    ax.plot(xs, [ds.face_y(x, 0) for x in xs], color=INK, lw=1.0)
    ax.plot(xs, [ds.face_y(x, 0) + ds.FACE_T for x in xs], color=INK,
            lw=0.6)
    ax.text(-30, -7, "face (occupant side)", fontsize=8, color=INK)
    # lever in rest (ink) and full pull (red, hidden lines off)
    vis, _ = hlr(full, (0, 0, 1), (1, 0, 0))
    for x, y in vis:
        ax.plot(x, y, color=DIM, lw=0.6, alpha=0.8)
    draw_view(ax, rest, (0, 0, 1), (1, 0, 0), hidden=False, lw=0.9)
    px, py = ds.PIVOT
    sr = ds.lever_point(ds.STRAP_PIN_LF, ds.POSE_REST)
    sf = ds.lever_point(ds.STRAP_PIN_LF, ds.POSE_FULL)
    hr = ds.lever_point(ds.HOOK_LF, ds.POSE_REST)
    hf = ds.lever_point(ds.HOOK_LF, ds.POSE_FULL)
    for (a, b, c) in ((sr, "strap pin (rest)", (-4, 41)),
                      (sf, "strap pin (full pull)", (2, 15)),
                      (hr, "cable nipple (rest)", (-62, 40)),
                      (hf, "cable nipple (full)", (-27, 44))):
        ax.plot(*a, marker="o", ms=3, color=INK)
        note(ax, a, c, b)
    ax.plot([px, sr[0]], [py, sr[1]], color=HID, lw=0.5, ls="-.")
    ax.plot([px, hr[0]], [py, hr[1]], color=HID, lw=0.5, ls="-.")
    ax.add_patch(Arc((px, py), 2 * ds.STRAP_ARM, 2 * ds.STRAP_ARM,
                     theta1=ds.STRAP_ARM_MID - 20, theta2=ds.STRAP_ARM_MID + 20,
                     color=DIM, lw=0.6))
    ax.text(px + 33, py + 13, f"{ds.LEVER_ROT:.0f} deg", color=DIM, fontsize=8)
    ax.text(-79, 22,
            f"R{ds.STRAP_ARM:.0f} strap arm, R{ds.HOOK_R:.0f} cable arm\n"
            f"cable travel {ds.CABLE_TRAVEL:.1f} mm, strap travel "
            f"{math.dist(sr, sf):.1f} mm\n"
            f"force ratio {ds.STRAP_ARM / ds.HOOK_R:.2f} : 1",
            fontsize=8, color=INK, va="top")
    ax.plot([-75, -5], [ds.CABLE_Y, ds.CABLE_Y], color=HID, lw=0.5, ls="--")
    ax.text(-74, ds.CABLE_Y + 1.2, "cable axis (to latch, rearwards)",
            fontsize=7, color=HID)
    ax.text(-79, 55, "LEVER KINEMATICS - top view, section Z=0\n"
            "black = rest (cable tension), red = full pull",
            fontsize=10, color=INK, va="top", weight="bold")
    ax.set_xlim(-80, 20)
    ax.set_ylim(-12, 58)
    fig.savefig(os.path.join(OUT, "drawing_lever.png"), dpi=150,
                facecolor="white")
    plt.close(fig)


def kinematics_chart():
    rows = ds.kinematics_table(41)
    fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=160)
    sx = [r["strap"] for r in rows]
    ax.plot(sx, [r["cable"] for r in rows], color=DIM, lw=2,
            label="cable pull (mm)")
    ax.plot(sx, [r["rot"] for r in rows], color=INK, lw=1.4, ls="--",
            label="lever angle (deg)")
    ax.axhspan(8, 10, color="#f1c40f", alpha=0.18, lw=0)
    ax.text(1, 9, "assumed latch release window - verify on your car", fontsize=7,
            va="center")
    ax.set_xlabel("strap pulled out of the face (mm)")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_xlim(0, max(sx))
    ax.set_ylim(0, 42)
    ax.set_title("Strap -> cable transfer (rest to full pull)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "kinematics.png"), facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    housing_sheet()
    lever_sheet()
    kinematics_chart()
    print("drawings written to", OUT)
