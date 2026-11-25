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
    """A3 sheet of the LH housing (cabin side view matches the OEM photos)."""
    H = ds.build_housing().mirror("YZ").val().wrapped
    fig = plt.figure(figsize=(16.54, 11.69), dpi=150)   # A3 landscape
    ax = fig.add_axes([0.03, 0.05, 0.94, 0.91])
    ax.set_aspect("equal")
    ax.axis("off")
    TOPY, SIDEX = 96.0, 158.0
    draw_view(ax, H, (0, -1, 0), (1, 0, 0))                 # front
    draw_view(ax, H, (0, 0, 1), (1, 0, 0), dy=TOPY)         # top
    draw_view(ax, H, (1, 0, 0), (0, 1, 0), dx=SIDEX)        # right (front end)
    lh = lambda p: (-p[0], p[1])                            # native -> LH
    face = ds.loop_points("face")
    fx0, fx1 = -max(p[0] for p in face), -min(p[0] for p in face)
    fz0, fz1 = min(p[1] for p in face), max(p[1] for p in face)
    clips = {c["name"]: c for c in ds.TRACE["clips"]}
    top, bot = lh(clips["top"]["tip"]), lh(clips["bottom"]["tip"])
    fro, rea = lh(clips["front"]["tip"]), lh(clips["rear"]["tip"])
    sx, sz = lh(ds.SCREW)
    pvx = -ds.PIVOT[0]
    slx = -ds.SLOT_X
    # --- front view dimensions
    dim(ax, (fx0, fz0), (fx1, fz0), -22, f"{fx1 - fx0:.1f}  visible face")
    dim(ax, (rea[0], rea[1]), (fro[0], fro[1]), -66 - (rea[1] + fro[1]) / 2,
        f"{fro[0] - rea[0]:.1f}  clip tip to clip tip")
    dim(ax, (fx0, fz0), (fx0, fz1), -16, f"{fz1 - fz0:.1f}", horiz=False)
    dim(ax, (fro[0], bot[1]), (fro[0], top[1]), 18,
        f"{top[1] - bot[1]:.1f}  clip to clip", horiz=False)
    dim(ax, (0, fz1), (sx, fz1), 16, f"{abs(sx):.1f}", fs=6.5)
    dim(ax, (0, fz1 + 8), (pvx, fz1 + 8), 14, f"{pvx:.1f}", fs=6.5)
    ax.plot([0, 0], [-48, 56], color=HID, lw=0.4, ls="-.")
    ax.plot([-105, 115], [0, 0], color=HID, lw=0.4, ls="-.")
    note(ax, (sx - 4, sz - 4), (-120, -56),
         f"door-card screw: hole {ds.SCREW_HOLE_D:.0f}, head counterbore "
         f"{ds.SCREW_HEAD_D:.1f}, seat Y{ds.SCREW_SEAT_Y:.0f} (verify)")
    note(ax, (sx + 9, sz + 6), (-120, 64),
         f"magnetic badge {ds.BADGE_W:.0f} x {ds.BADGE_H:.0f} covers the "
         f"screw (2 + 2 magnets {ds.MAGNET[0]:.0f}x{ds.MAGNET[1]:.0f})")
    note(ax, (slx, -ds.SLOT_LEN / 2 + 1), (20, -56),
         f"strap slot {ds.SLOT_LEN:.1f} x {ds.SLOT_W:.0f} "
         f"({ds.STRAP_W:.0f} mm webbing)")
    note(ax, (pvx, 26), (60, 64), "pivot axis (OEM position)")
    note(ax, top, (top[0] - 70, top[1] + 10),
         f"OEM-position snap clips (4), at Y{ds.CLIP_Y:.0f}")
    ax.text(62, -46, "front of car  >>", fontsize=7, color=HID)
    # --- top view
    dim(ax, (fx1 + 6, TOPY), (fx1 + 6, TOPY + ds.DEPTH), 20,
        f"{ds.DEPTH:.0f}", horiz=False)
    ax.plot(pvx, TOPY + ds.PIVOT[1], marker="+", color=DIM, ms=8, mew=0.8)
    note(ax, (pvx, TOPY + ds.PIVOT[1]), (pvx - 10, TOPY + 58),
         f"pivot  Y{ds.PIVOT[1]:.0f}")
    cx0, cx1 = -ds.CHANNEL_X[1], -ds.CHANNEL_X[0]
    note(ax, ((cx0 + cx1) / 2, TOPY + ds.CABLE_Y), (fro[0] - 10, TOPY + 66),
         f"cable anchor slider, adj. {ds.SLIDER_TRAVEL:.1f} mm, "
         f"cable axis Y{ds.CABLE_Y:.1f}")
    # --- title block
    k = ds.TRACE["px_per_mm"]
    ax.text(118, -78,
            "DOOR STRAP MODULE v3 - Hyundai i20 N (BC3) front doors\n"
            "Housing, LH shown (RH = mirror). Units mm. Third-angle projection\n"
            "Face: your outlines on the in-car photos, perspective-rectified\n"
            f"Housing, clips, screw, pivot: OEM photos at {k:.2f} px/mm\n"
            f"(OEM overall {ds.TRACE['overall_mm']:.0f} mm, clip-to-clip "
            f"{ds.TRACE['clip_height_mm']:.0f} mm). Measure yours and re-run\n"
            "oem_trace.py --overall MM (--face-length MM) to rescale.",
            fontsize=7.2, color=INK, va="top", ha="left",
            bbox=dict(boxstyle="square,pad=0.6", fc="white", ec=INK, lw=0.6))
    ax.text(-60, TOPY + 72, "TOP", fontsize=9, color=INK, weight="bold")
    ax.text(-60, 70, "FRONT (cabin side)", fontsize=9, color=INK,
            weight="bold")
    ax.text(SIDEX - 6, 70, "FRONT END", fontsize=9, color=INK, weight="bold")
    gz = ds.GROOVE_Z
    pitch = (gz[-1] - gz[0]) / max(len(gz) - 1, 1)
    ax.text(-128, 124, f"grooves: {len(gz)} x R{ds.GROOVE_R:.1f}, depth "
            f"{ds.GROOVE_R - ds.GROOVE_E:.1f}, pitch {pitch:.1f} (measured)\n"
            "face crown: R160 vertical / R1500 horizontal",
            fontsize=6.5, color=INK, va="top")
    ax.set_xlim(-135, 240)
    ax.set_ylim(-118, 172)
    fig.savefig(os.path.join(OUT, "drawing_housing.png"), dpi=150,
                facecolor="white")
    fig.savefig(os.path.join(OUT, "drawing_housing.pdf"), facecolor="white")
    plt.close(fig)


def lever_sheet():
    lev = ds.build_lever()
    rest = ds.pose_lever(lev, ds.POSE_REST).val().wrapped
    full = ds.pose_lever(lev, ds.POSE_FULL).val().wrapped
    px, py = ds.PIVOT
    fig = plt.figure(figsize=(11.69, 8.27), dpi=150)   # A4 landscape
    ax = fig.add_axes([0.04, 0.08, 0.92, 0.86])
    ax.set_aspect("equal")
    ax.axis("off")
    import numpy as np
    xs = np.linspace(px - 46, px + 54, 200)
    ax.plot(xs, [ds.face_y(x, 0) for x in xs], color=INK, lw=1.0)
    ax.plot(xs, [ds.face_y(x, 0) + ds.FACE_T for x in xs], color=INK, lw=0.6)
    ax.text(px + 4, -7, "face (occupant side)", fontsize=8, color=INK)
    vis, _ = hlr(full, (0, 0, 1), (1, 0, 0))
    for x, y in vis:
        ax.plot(x, y, color=DIM, lw=0.6, alpha=0.8)
    draw_view(ax, rest, (0, 0, 1), (1, 0, 0), hidden=False, lw=0.9)
    sr = ds.lever_point(ds.STRAP_PIN_LF, ds.POSE_REST)
    sf = ds.lever_point(ds.STRAP_PIN_LF, ds.POSE_FULL)
    hr = ds.lever_point(ds.HOOK_LF, ds.POSE_REST)
    hf = ds.lever_point(ds.HOOK_LF, ds.POSE_FULL)
    for (a, b, c) in ((sr, "strap pin (rest)", (px + 30, 41)),
                      (sf, "strap pin (full pull)", (px + 36, 15)),
                      (hr, "cable nipple (rest)", (px - 28, 40)),
                      (hf, "cable nipple (full)", (px + 7, 44))):
        ax.plot(*a, marker="o", ms=3, color=INK)
        note(ax, a, c, b)
    ax.plot([px, sr[0]], [py, sr[1]], color=HID, lw=0.5, ls="-.")
    ax.plot([px, hr[0]], [py, hr[1]], color=HID, lw=0.5, ls="-.")
    ax.add_patch(Arc((px, py), 2 * ds.STRAP_ARM, 2 * ds.STRAP_ARM,
                     theta1=ds.STRAP_ARM_MID - 20, theta2=ds.STRAP_ARM_MID + 20,
                     color=DIM, lw=0.6))
    ax.text(px + 33, py + 13, f"{ds.LEVER_ROT:.0f} deg", color=DIM, fontsize=8)
    ax.text(px - 45, 22,
            f"R{ds.STRAP_ARM:.0f} strap arm, R{ds.HOOK_R:.0f} cable arm\n"
            f"cable travel {ds.CABLE_TRAVEL:.1f} mm, strap travel "
            f"{math.dist(sr, sf):.1f} mm\n"
            f"force ratio {ds.STRAP_ARM / ds.HOOK_R:.2f} : 1",
            fontsize=8, color=INK, va="top")
    ax.plot([px - 41, px + 29], [ds.CABLE_Y, ds.CABLE_Y], color=HID, lw=0.5,
            ls="--")
    ax.text(px - 40, ds.CABLE_Y + 1.2, "cable axis (to latch via front end)",
            fontsize=7, color=HID)
    ax.text(px - 45, 55, "LEVER KINEMATICS - top view, section Z=0 (RH)\n"
            "black = rest (cable tension), red = full pull",
            fontsize=10, color=INK, va="top", weight="bold")
    ax.set_xlim(px - 46, px + 54)
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
