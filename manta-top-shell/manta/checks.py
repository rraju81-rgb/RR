"""Automated regulation and geometry checks for a built variant.

These checks encode the dimensional envelope of each class (see regs.py for
the caveat on sources) plus packaging sanity checks that any top shell must
pass: wheels covered in plan view, tyre clearance under bump and steer,
mandatory front-wheel openings, engine-cover fin, cockpit headroom, and mesh
integrity of the exported surfaces / solids.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from .curves import polygon_area
from .design import FIN_X_ROOT
from .mesh import Part
from .solid import edge_face_counts, thicken

BUMP_STRAIGHT = 40.0  # mm, straight-line full bump
BUMP_STEER = 15.0  # mm, bump combined with full lock
STEER_DEG = 12.0  # full lock used for the clearance check
TYRE_CLEARANCE = 15.0  # mm minimum gap to the tyre envelope
TYRE_SHOULDER_R = 45.0  # rounded tyre shoulder radius
HELMET_RADIUS = 150.0  # helmet (incl. HANS margin) radius
HEADROOM_MIN = 50.0  # outer skin above helmet top


def _check(name, value, ok, detail=""):
    return dict(name=name, value=value, pass_=bool(ok), detail=detail)


def tyre_penetration(points, xw, yc, zw, R, W, steer_deg=0.0, bump=0.0):
    """Signed distance (approx., mm) of points from a rounded-shoulder tyre.

    Negative = inside the tyre. The tyre is steered about a vertical axis
    through the wheel centre and raised by ``bump``.
    """
    p = np.asarray(points, float)
    a = np.radians(steer_deg)
    dx, dy, dz = p[:, 0] - xw, p[:, 1] - yc, p[:, 2] - (zw + bump)
    # rotate into the wheel frame
    lx = np.cos(a) * dx + np.sin(a) * dy
    ly = -np.sin(a) * dx + np.cos(a) * dy
    r = np.hypot(lx, dz)
    w = np.abs(ly)
    half = W / 2.0
    # distance to a rounded rectangle in (w, r) space: |w|<=half, r<=R, corner radius rr
    rr = TYRE_SHOULDER_R
    cw, cr = half - rr, R - rr
    qx = w - cw
    qy = r - cr
    outside = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0))
    inside = np.minimum(np.maximum(qx, qy), 0.0)
    return outside + inside - rr


def plan_silhouette(parts: list[Part], res=5.0):
    """Rasterised plan-view silhouette (x, y) of the given parts."""
    V = np.vstack([p.vertices for p in parts])
    x0, y0 = V[:, 0].min() - 10, V[:, 1].min() - 10
    x1, y1 = V[:, 0].max() + 10, V[:, 1].max() + 10
    w, h = int((x1 - x0) / res) + 1, int((y1 - y0) / res) + 1
    img = Image.new("1", (w, h), 0)
    dr = ImageDraw.Draw(img)
    for p in parts:
        T = p.vertices[p.faces][:, :, :2]
        T = ((T - [x0, y0]) / res)
        for tri in T:
            dr.polygon([tuple(q) for q in tri], fill=1)
    return np.array(img, bool), (x0, y0, res)


def projected_area(parts: list[Part], axes=(1, 2), res=4.0):
    V = np.vstack([p.vertices for p in parts])
    a, b = axes
    x0, y0 = V[:, a].min() - 5, V[:, b].min() - 5
    w = int((V[:, a].max() + 5 - x0) / res) + 1
    h = int((V[:, b].max() + 5 - y0) / res) + 1
    img = Image.new("1", (w, h), 0)
    dr = ImageDraw.Draw(img)
    for p in parts:
        T = (p.vertices[p.faces][:, :, [a, b]] - [x0, y0]) / res
        for tri in T:
            dr.polygon([tuple(q) for q in tri], fill=1)
    return np.array(img, bool).sum() * res * res / 1e6  # m^2


def mesh_integrity(part: Part):
    _, counts = edge_face_counts(part.faces)
    v = part.vertices
    f = part.faces
    area = 0.5 * np.linalg.norm(np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]), axis=1)
    return dict(non_manifold_edges=int((counts > 2).sum()),
                boundary_edges=int((counts == 1).sum()),
                degenerate_faces=int((area < 1e-6).sum()),
                finite=bool(np.isfinite(v).all()))


def run_checks(build) -> dict:
    v = build.variant
    rules = v.rules
    design = build.design
    P = build.parts
    skin = P["top_shell_skin"]
    shell_and_aero = [skin, P["dorsal_fin"], P["rear_wing"], P["endplates"], P["mirrors"]]
    allV = np.vstack([p.vertices for p in shell_and_aero])
    checks = []

    # 1. overall envelope ---------------------------------------------------
    length = allV[:, 0].max() - allV[:, 0].min()
    width = allV[:, 1].max() - allV[:, 1].min()
    height = allV[:, 2].max()
    checks.append(_check("Overall length", f"{length:.0f} mm (max {rules.max_length:.0f})",
                         length <= rules.max_length))
    checks.append(_check("Overall width", f"{width:.0f} mm (max {rules.max_width:.0f})",
                         width <= rules.max_width))
    checks.append(_check("Overall height above ref. plane", f"{height:.0f} mm (max {rules.max_height:.0f})",
                         height <= rules.max_height))
    checks.append(_check("Wheelbase", f"{v.wheelbase:.0f} mm ({rules.wheelbase_note})",
                         v.wheelbase <= rules.wheelbase_max + 1e-6))

    # 2. wheels covered in plan view (mandatory louvre openings excepted) ---
    sil, (x0, y0, res) = plan_silhouette([skin], res=3.0)
    filled_img = Image.fromarray(sil)
    dr = ImageDraw.Draw(filled_img)
    for lp in build.louvre_polys:
        dr.polygon([tuple(q) for q in (lp - [x0, y0]) / res], fill=1)
    sil_open = sil
    sil = np.array(filled_img, bool)
    cover = []
    through_louvres = []
    for (xw, tyre, track) in ((0.0, rules.front_tyre, v.front_track),
                              (v.x_rear_axle, rules.rear_tyre, v.rear_track)):
        for side in (1, -1):
            xs = np.linspace(xw - tyre.radius, xw + tyre.radius, 40)
            ys = side * np.linspace(track / 2 - tyre.width / 2, track / 2 + tyre.width / 2, 12)
            X, Y = np.meshgrid(xs, ys)
            ix = ((X - x0) / res).astype(int)
            iy = ((Y - y0) / res).astype(int)
            ok = (ix >= 0) & (iy >= 0) & (ix < sil.shape[1]) & (iy < sil.shape[0])
            covered = np.zeros_like(ok)
            covered[ok] = sil[iy[ok], ix[ok]]
            cover.append(covered.mean())
            seen = np.zeros_like(ok)
            seen[ok] = sil_open[iy[ok], ix[ok]]
            through_louvres.append(1.0 - seen.mean())
    checks.append(_check("Wheels covered in plan view", f"{100 * min(cover):.1f} % (min of 4)",
                         min(cover) >= 0.999,
                         f"apart from the mandatory louvres ({100 * max(through_louvres):.0f} % of the "
                         "front tyre footprint is visible through the gill slots)"))

    # 3. tyre clearance ----------------------------------------------------
    worst = {}
    for label, steer, bump in (("straight, +40 mm bump", 0.0, BUMP_STRAIGHT),
                               (f"{STEER_DEG:.0f} deg lock, +15 mm bump", STEER_DEG, BUMP_STEER)):
        dmin = np.inf
        for (xw, zw, tyre, track) in ((0.0, v.wheel_z_front, rules.front_tyre, v.front_track),
                                      (v.x_rear_axle, v.wheel_z_rear, rules.rear_tyre, v.rear_track)):
            st = steer if xw == 0.0 else 0.0
            for side in (1, -1):
                yc = side * track / 2
                near = (np.abs(skin.vertices[:, 0] - xw) < tyre.radius + 120) & \
                       (np.abs(skin.vertices[:, 1] - yc) < tyre.width / 2 + 160)
                for s in ((st, -st) if st else (0.0,)):
                    d = tyre_penetration(skin.vertices[near], xw, yc, zw, tyre.radius, tyre.width, s, bump)
                    if len(d):
                        dmin = min(dmin, float(d.min()))
        worst[label] = dmin
        checks.append(_check(f"Tyre clearance ({label})", f"{dmin:.0f} mm (min {TYRE_CLEARANCE:.0f})",
                             dmin >= TYRE_CLEARANCE))

    # 4. mandatory openings above the front wheels ------------------------
    right = [p for p in build.louvre_polys if p[:, 1].mean() > 0]
    area_cm2 = sum(abs(polygon_area(p)) for p in right) / 100.0
    over_wheel = all((np.abs(p[:, 0]).max() < rules.front_tyre.radius) for p in right)
    checks.append(_check("Front-wheel louvre area (per side)",
                         f"{area_cm2:.0f} cm2 in {len(right)} gill slots (assumed min {rules.min_front_louvre_area_cm2:.0f})",
                         area_cm2 >= rules.min_front_louvre_area_cm2 and over_wheel,
                         "projected plan area; all slots lie over the front tyre"))

    # 5. engine cover fin -------------------------------------------------
    fin = P["dorsal_fin"]
    fin_x0, fin_x1 = fin.vertices[:, 0].min(), fin.vertices[:, 0].max()
    prof = design.fin_profile()
    fin_area = abs(polygon_area(prof)) / 1e6
    on_cl = np.abs(fin.vertices[:, 1]).max() < 10.0
    checks.append(_check("Engine-cover fin", f"{fin_area:.2f} m2 side area, x {fin_x0:.0f}..{fin_x1:.0f} mm",
                         on_cl and fin_x1 >= v.x_rear_axle and fin_x0 <= v.mx(FIN_X_ROOT[0]) + 50,
                         "on the centre plane, from the roof to behind the rear axle"))

    # 6. cockpit headroom (indicative 95th-percentile helmet) -------------
    xh, yh = float(v.mx(1680.0)), 220.0
    helmet_top = 975.0
    roof = float(design.H(np.array([xh]), np.array([yh]))[0])
    checks.append(_check("Helmet headroom (indicative)", f"{roof - helmet_top:.0f} mm skin above helmet",
                         roof - helmet_top >= HEADROOM_MIN,
                         f"helmet top {helmet_top:.0f} mm at x={xh:.0f}, y={yh:.0f}"))

    # 7. mesh integrity ----------------------------------------------------
    mi = mesh_integrity(skin)
    sym = _symmetry_error(skin)
    checks.append(_check("Skin mesh is manifold & clean",
                         f"{mi['non_manifold_edges']} non-manifold edges, {mi['degenerate_faces']} degenerate faces",
                         mi["non_manifold_edges"] == 0 and mi["degenerate_faces"] == 0 and mi["finite"]))
    checks.append(_check("Left/right symmetry", f"{sym:.3f} mm max deviation", sym < 0.01))
    solid = thicken(skin, 3.0)
    ms = mesh_integrity(solid)
    checks.append(_check("3 mm solid is watertight",
                         f"{ms['boundary_edges']} open edges, {ms['non_manifold_edges']} non-manifold",
                         ms["boundary_edges"] == 0 and ms["non_manifold_edges"] == 0))

    # metrics (informational) ---------------------------------------------
    frontal = projected_area(shell_and_aero, axes=(1, 2))
    plan = projected_area([skin], axes=(0, 1), res=6.0)
    wetted = float(skin.face_areas().sum() / 1e6)
    ws = skin.face_areas()[skin.face_mat == skin.materials.index("glass")].sum() / 1e6
    metrics = dict(frontal_area_m2=round(frontal, 3), plan_area_m2=round(plan, 3),
                   skin_area_m2=round(wetted, 2), glazing_area_m2=round(float(ws), 3),
                   louvre_area_per_side_cm2=round(area_cm2, 1),
                   fin_side_area_m2=round(fin_area, 3),
                   min_tyre_clearance_mm={k: round(val, 1) for k, val in worst.items()},
                   skin_triangles=int(len(skin.faces)))
    for c in checks:
        c["pass"] = c.pop("pass_")
    return dict(class_key=rules.key, class_name=rules.name,
                envelope=dict(max_length=rules.max_length, max_width=rules.max_width,
                              max_height=rules.max_height),
                package=dict(wheelbase=v.wheelbase, x_front=v.x_front, x_rear=v.x_rear,
                             front_track=v.front_track, rear_track=v.rear_track,
                             front_tyre=rules.front_tyre.code, rear_tyre=rules.rear_tyre.code),
                measured=dict(length=round(length, 1), width=round(width, 1), height=round(height, 1)),
                checks=checks, metrics=metrics,
                sources=list(rules.sources), notes=list(rules.notes),
                caveat="Rule figures cross-checked from published specifications; verify against "
                       "the current FIA/ACO Technical Regulations before use.")


def _symmetry_error(part: Part):
    """Max distance from each mirrored vertex to the nearest original vertex."""
    from scipy.spatial import cKDTree

    v = part.vertices
    m = v * [1, -1, 1]
    d, _ = cKDTree(v).query(m[:: max(1, len(m) // 20000)])
    return float(d.max())
