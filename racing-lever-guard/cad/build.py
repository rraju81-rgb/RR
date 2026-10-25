"""Build every part, run the fit checks and export STEP / STL.

    python build.py            # checks + STEP/STL + summary.json into ../exports
    python build.py --check    # checks + summary.json only (leaves STEP/STL untouched)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import cadquery as cq

import lever_guard as lg

ROOT = Path(__file__).resolve().parent.parent
EXPORTS = ROOT / "exports"

DENSITY = {  # g/cm3
    "al6061": 2.70,
    "carbon": 1.55,
    "pa12cf": 1.10,
    "petgcf": 1.30,
    "tpu": 1.21,
    "hdpe": 0.95,
    "steel": 7.90,
}


def mass_g(shape: cq.Shape, material: str) -> float:
    return shape.Volume() / 1000.0 * DENSITY[material]


def _boxes_touch(a: cq.Shape, b: cq.Shape, tol: float = 0.05) -> bool:
    A, B = a.BoundingBox(), b.BoundingBox()
    return not (
        A.xmax < B.xmin - tol or B.xmax < A.xmin - tol
        or A.ymax < B.ymin - tol or B.ymax < A.ymin - tol
        or A.zmax < B.zmin - tol or B.zmax < A.zmin - tol
    )


def _half_space_x(shape: cq.Shape, x: float, inboard: bool) -> cq.Shape:
    box = cq.Solid.makeBox(600, 600, 600, cq.Vector(x - 600 if inboard else x, -300, -300))
    return shape.intersect(box)


# ------------------------------------------------------------------------------------------------
# checks
# ------------------------------------------------------------------------------------------------
class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, bool, str]] = []

    def check(self, name: str, ok: bool, detail: str) -> None:
        self.rows.append((name, ok, detail))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")

    @property
    def ok(self) -> bool:
        return all(ok for _, ok, _ in self.rows)


def run_checks(p: lg.Params) -> tuple[Report, dict]:
    rep = Report()
    info: dict = {}
    parts = {n: wp.val() for n, wp, _ in lg.guard_parts(p, size="M")}
    ref = {n: wp.val() for n, wp, _ in lg.reference_parts(p)}

    print("solids")
    for name, s in parts.items():
        n_solids = len(s.Solids())
        rep.check(f"{name} valid", s.isValid() and n_solids == 1, f"{n_solids} solid(s)")

    print("serration mesh (adapter <-> arm)")
    a, h = parts["adapter"], parts["arm"]
    for step in (0, 1, 5):
        arm_rot = h.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), step * 360 / p.teeth)
        overlap = a.intersect(arm_rot).Volume()
        gap = a.distance(arm_rot)
        rep.check(
            f"teeth mesh at {step * 360 / p.teeth:.0f} deg",
            overlap < 1e-3 and gap < 1e-3,
            f"overlap {overlap:.4f} mm3, gap {gap:.4f} mm",
        )
    arm_half = h.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 180 / p.teeth)
    rep.check(
        "teeth clash when half a tooth out",
        a.intersect(arm_half).Volume() > 1.0,
        f"overlap {a.intersect(arm_half).Volume():.1f} mm3 (so the arm can only sit in 10 deg steps)",
    )

    print("interference between guard parts")
    allowed = {  # intended overlaps: threads
        frozenset({"m5_screw_1", "arm"}),
        frozenset({"m5_screw_2", "arm"}),
        frozenset({"m6_bolt", "expander_cone"}),
    }
    names = list(parts)
    worst = 0.0
    for i, n1 in enumerate(names):
        for n2 in names[i + 1 :]:
            if frozenset({n1, n2}) in allowed or not _boxes_touch(parts[n1], parts[n2]):
                continue
            v = parts[n1].intersect(parts[n2]).Volume()
            worst = max(worst, v)
            if v > 1e-3:
                rep.check(f"{n1} x {n2}", False, f"overlap {v:.3f} mm3")
    rep.check("no unintended overlaps", worst <= 1e-3, f"worst {worst:.4f} mm3")
    for shift in (-p.adjust, p.adjust):  # the bend gusset must clear the arm across the slot
        b = lg.blade(p, shift).val()
        v = max(b.intersect(parts[n]).Volume() for n in ("arm", "adapter", "m5_screw_1", "m5_screw_2"))
        rep.check(f"blade at slot {shift:+.0f} clears arm, adapter and screws", v < 1e-3, f"overlap {v:.4f} mm3")

    print("thread engagement")
    m5_eng = p.hub_outer_x - (p.blade_seat_x + p.blade_t + 1.0 - p.m5_len)
    rep.check("M5 blade screws", m5_eng >= 1.2 * 5, f"{m5_eng:.1f} mm in the arm (>= 1.2 d)")
    tip = p.head_seat_x - p.m6_len
    cone_far = -p.spigot_len - p.sleeve_len - p.cone_land
    cone_near = -p.spigot_len - p.sleeve_len + p.sleeve_recess_depth
    m6_eng = cone_near - max(tip, cone_far)
    rep.check("M6 bolt in cone nut", m6_eng >= 1.2 * 6, f"{m6_eng:.1f} mm (>= 1.2 d), tip {cone_far - tip:+.1f} mm past the cone")
    info["m6_engagement_mm"] = round(m6_eng, 1)
    info["m5_engagement_mm"] = round(m5_eng, 1)

    print("bend gusset")
    plain, gusset = lg.bend_section(p, gusset=False), lg.bend_section(p)
    rep.check(
        "bend section with gusset",
        gusset >= 1.4 * plain,
        f"{gusset:.1f} mm across the bend vs {plain:.1f} mm plain (bending strength x{(gusset / plain) ** 2:.1f})",
    )
    start = lg.haunch_blend(p)[0][1] - p.adjust - p.neck_end  # blade at the slot end nearest the arm
    rep.check(
        f"gusset starts past the arm's neck at slot {-p.adjust:+.0f}",
        start >= 0.0,
        f"R{p.haunch_blend_r:g} blend into the seat face starts {start:.2f} mm past the neck",
    )
    info["gusset"] = {
        "radius_mm": round(lg.haunch_circle(p)[2], 1),
        "blend_radius_mm": p.haunch_blend_r,
        "section_plain_mm": round(plain, 1),
        "section_mm": round(gusset, 1),
        "strength_factor": round((gusset / plain) ** 2, 1),
    }

    print("lever clearance (reference sport-bike lever, see ref_lever)")
    lever = ref["ref_lever"]
    clear = {}
    for shift in (-p.adjust, 0.0, p.adjust):
        d = lg.blade(p, shift).val().distance(lever)
        clear[shift] = d
        if shift == 0.0:  # >= 10 mm all round the lever, as lever-guard fitting guides ask for
            rep.check("blade to lever, nominal slot position", d >= 10.0, f"{d:.1f} mm")
        else:
            print(f"  [info] blade to lever with the blade moved {shift:+.0f} mm: {d:.1f} mm")
    info["lever_clearance_mm"] = {f"{k:+.0f}": round(v, 1) for k, v in clear.items()}
    for name in ("adapter", "arm", "m6_bolt", "m5_screw_1", "m5_screw_2"):
        d = parts[name].distance(lever)
        rep.check(f"{name} to lever", d >= 10.0, f"{d:.1f} mm")
    # finger room: the run in front of the lever versus the grip the hand is wrapped around
    run = parts["blade"].intersect(cq.Solid.makeBox(400, 200, 100, cq.Vector(-400 + p.blade_cx - p.bend_r, -100, -50)))
    d_grip = run.distance(ref["ref_grip"])
    rep.check("finger room, grip to blade run", d_grip >= 40.0, f"{d_grip:.1f} mm")
    info["finger_room_mm"] = round(d_grip, 1)
    d_adapter_grip = parts["adapter"].distance(ref["ref_grip"])
    rep.check("adapter seats on bar end", d_adapter_grip < 0.05, f"{d_adapter_grip:.2f} mm to grip end")

    print("wind guard")
    lever_blade = _half_space_x(lever, -160.0, inboard=False)  # lever blade and tip
    perch = _half_space_x(lever, -160.0, inboard=True)  # pivot, master cylinder and clamp
    hand = cq.Solid.makeCylinder(50.0, 128.0, cq.Vector(-128, 0, 0), cq.Vector(1, 0, 0))  # gloved hand, Ø100 round the grip
    blade0 = parts["blade"]
    lever_gaps, perch_gaps, hand_gaps = [], [], []
    for pos in p.clamp_range:
        dp = {n: wp.val() for n, wp in lg.diffuser_parts(p, pos)}
        ov = max(s.intersect(blade0).Volume() for s in dp.values())
        rep.check(f"wind guard at {pos:g} mm sits on the blade", ov < 1e-3, f"overlap {ov:.4f} mm3")
        bear = max(dp["diffuser_clamp_upper"].distance(blade0), dp["diffuser_clamp_lower"].distance(blade0))
        rep.check(f"wind guard at {pos:g} mm: clamp halves bear on the blade edges", bear < 0.01, f"gap {bear:.3f} mm")
        dl = min(s.distance(lever_blade) for s in dp.values())
        dpp = min(s.distance(perch) for s in dp.values())
        dh = dp["diffuser_shell"].distance(hand)
        lever_gaps.append(round(dl, 1))
        perch_gaps.append(round(dpp, 1))
        hand_gaps.append(round(dh, 1))
        rep.check(f"wind guard at {pos:g} mm to lever", dl >= 10.0, f"{dl:.1f} mm")
        rep.check(f"wind guard at {pos:g} mm to brake perch", dpp >= 10.0, f"{dpp:.1f} mm")
        rep.check(f"wind guard at {pos:g} mm to a gloved hand (Ø100 round the grip)", dh >= 15.0, f"{dh:.1f} mm")
        dg = min(s.distance(ref["ref_grip"]) for s in dp.values())
        rep.check(f"wind guard at {pos:g} mm to grip", dg >= 30.0, f"{dg:.1f} mm")
    for shift in (-p.adjust, p.adjust):
        ds = {n: wp.val() for n, wp in lg.diffuser_parts(p, None, shift)}
        dl = min(s.distance(lever) for s in ds.values())
        dh = ds["diffuser_shell"].distance(hand)
        print(f"  [info] blade moved {shift:+.0f} mm: wind guard to lever {dl:.1f} mm, to the hand {dh:.1f} mm")
    # size on the bike (lever plane lever_deg below horizontal), default clamp position
    shell = dict((n, wp.val()) for n, wp in lg.diffuser_parts(p))["diffuser_shell"]
    bb = shell.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), -p.lever_deg).BoundingBox()
    info["diffuser"] = {
        "length_mm": p.shell_len,
        "ahead_of_bar_axis_mm": [round(bb.ymin, 1), round(bb.ymax, 1)],
        "above_bar_axis_mm": round(bb.zmax, 1),
        "below_bar_axis_mm": round(-bb.zmin, 1),
        "inboard_of_bar_end_mm": round(-bb.xmin, 1),
        "travel_mm": p.clamp_range[1] - p.clamp_range[0],
        "lever_clearance_mm": lever_gaps,
        "perch_clearance_mm": perch_gaps,
        "hand_clearance_mm": hand_gaps,
    }

    print("expander sleeves")
    for size, (od, (lo, hi)) in lg.SLEEVES.items():
        cone_big = od - 1.2
        travel = p.sleeve_recess_depth
        rise = (cone_big - lg.cone_small_d(p, size)) / 2
        rep.check(
            f"sleeve {size} ({lo:g}-{hi:g} mm bar ID)",
            od < lo and cone_big < lo,
            f"OD {od} slides into {lo:g}; cone taper {math.degrees(math.atan2(rise, travel)):.0f} deg",
        )

    # envelope from the parameters (OCC bounding boxes are padded by the tessellation)
    protrusion = p.blade_seat_x + p.blade_t + 1.0 + 2.75  # ISO 7380 M5 head on a 1 mm washer
    inboard = -(p.tip_x - p.blade_t / 2 * math.sin(math.radians(p.front_toe_deg)))
    reach = p.run_point(p.front_len, -p.blade_t / 2)[1]
    info.update(
        {
            "blade_path_length_mm": round(p.blade_path_len, 1),
            "protrusion_beyond_bar_end_mm": round(protrusion, 2),
            "reach_ahead_of_bar_axis_mm": round(reach, 1),
            "coverage_inboard_of_bar_end_mm": round(inboard, 1),
            "blade_inner_face_ahead_of_bar_axis_mm": {
                f"{s:+.0f}": {
                    "run_start": round(p.run_point(0, p.blade_t / 2)[1] + s, 1),
                    "run_tip": round(p.run_point(p.front_len - p.tip_r, p.blade_t / 2)[1] + s, 1),
                }
                for s in (-p.adjust, 0, p.adjust)
            },
            "overall_envelope_mm": [
                round(protrusion + inboard, 1),
                round(reach + p.body_d / 2, 1),
                round(max(p.blade_h, p.body_d), 1),
            ],
        }
    )
    return rep, info


# ------------------------------------------------------------------------------------------------
# exports
# ------------------------------------------------------------------------------------------------
def to_print_pose(name: str, wp: cq.Workplane) -> cq.Workplane:
    """Rotate each part into its recommended FDM orientation, sitting on Z = 0."""
    if name.startswith("01"):  # adapter: teeth up
        wp = wp.rotate((0, 0, 0), (0, 1, 0), -90)
    elif name.startswith("02"):  # arm: outer face on the bed, teeth up
        wp = wp.rotate((0, 0, 0), (0, 1, 0), 90)
    elif name.startswith(("04", "05")):  # sleeve / cone: large end down
        wp = wp.rotate((0, 0, 0), (0, 1, 0), -90)
    elif name.startswith("06b"):  # left-hand shell: flange on the bed, shield up like the right one
        wp = wp.rotate((0, 0, 0), (1, 0, 0), 180)
    elif name.startswith("07"):  # clamp half: outer face on the bed, cavity open upward
        wp = wp.rotate((0, 0, 0), (1, 0, 0), 180)
    bb = wp.val().BoundingBox()
    return wp.translate((-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))


def catalogue(p: lg.Params, pp: lg.Params) -> list[tuple[str, cq.Workplane, str]]:
    """Every exported part: (file name, solid, material). The wind guard parts are exported in
    their own run frame (shell flange flat on XY, clamp half with the blade run along X)."""
    parts = [
        ("01_bar_end_adapter", lg.adapter(p), "al6061"),
        ("01b_bar_end_adapter_oem_thread", lg.adapter(p, spigot=False), "al6061"),
        ("02_guard_arm", lg.arm(p), "al6061"),
        ("03_guard_blade_6mm_carbon", lg.blade(p), "carbon"),
        ("03b_guard_blade_8mm_3dprint", lg.blade(pp), "pa12cf"),
    ]
    for size, (_, (lo, hi)) in lg.SLEEVES.items():
        parts.append((f"04_expander_sleeve_{size}_bar_id_{lo:g}-{hi:g}", lg.expander_sleeve(p, size), "tpu"))
    for size, (_, (lo, hi)) in lg.SLEEVES.items():
        parts.append((f"05_expander_cone_{size}_bar_id_{lo:g}-{hi:g}", lg.expander_cone(p, size), "al6061"))
    parts += [
        ("06_wind_guard_shell_RH", lg.wind_guard_local(p), "hdpe"),
        ("06b_wind_guard_shell_LH", lg.wind_guard_local(p, left=True), "hdpe"),
        ("07_wind_guard_clamp_half", lg.clamp_half_local(p), "al6061"),
    ]
    return parts


def export_assembly_stl(p: lg.Params, stl_dir: Path) -> None:
    """The assembled guard as one STL each, in bike axes (X to the rider's right, Y forward, Z up;
    origin at the centre of the bar-end face, lever plane lever_deg below horizontal): right side
    with and without the wind guard, and the left side (mirror image, so it carries the left-hand
    shell)."""
    for label, wind in (("assembly_right_guard", True), ("assembly_right_guard_without_wind_guard", False)):
        shapes = [wp.val() for _, wp, _ in lg.guard_parts(p, size="M", diffuser=wind)]
        comp = cq.Compound.makeCompound(shapes).rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), -p.lever_deg)
        cq.exporters.export(cq.Workplane(obj=comp), str(stl_dir / f"{label}.stl"), tolerance=0.03, angularTolerance=0.15)
        print(f"  exported {label}.stl")
        if wind:
            cq.exporters.export(cq.Workplane(obj=comp.mirror("YZ")), str(stl_dir / "assembly_left_guard.stl"),
                                tolerance=0.03, angularTolerance=0.15)
            print("  exported assembly_left_guard.stl")


def export_all(p: lg.Params, parts) -> None:
    step_dir, stl_dir = EXPORTS / "step", EXPORTS / "stl"
    step_dir.mkdir(parents=True, exist_ok=True)
    stl_dir.mkdir(parents=True, exist_ok=True)
    for name, wp, _ in parts:
        cq.exporters.export(wp, str(step_dir / f"{name}.step"))
        cq.exporters.export(
            to_print_pose(name, wp), str(stl_dir / f"{name}.stl"), tolerance=0.02, angularTolerance=0.1
        )
        print(f"  exported {name}")

    export_assembly_stl(p, stl_dir)

    for label, with_ref in (("assembly_right_guard", False), ("assembly_right_guard_on_reference_bar", True)):
        assy = lg.assembly(p, with_reference=with_ref, size="M")
        try:
            assy.export(str(step_dir / f"{label}.step"))
        except AttributeError:
            assy.save(str(step_dir / f"{label}.step"))
        print(f"  exported {label}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="checks + summary.json only, no STEP / STL")
    args = ap.parse_args()

    p, pp = lg.Params(), lg.PRINT_PARAMS
    print(f"== checks: carbon / aluminium blade ({p.blade_t:g} mm) ==")
    rep, info = run_checks(p)
    print(f"== checks: 3D-printed blade ({pp.blade_t:g} mm) ==")
    rep_p, info_p = run_checks(pp)

    parts = catalogue(p, pp)
    masses = {n: {"material": m, "grams": round(mass_g(wp.val(), m), 1)} for n, wp, m in parts}
    if not args.check:
        print("== exports ==")
        export_all(p, parts)
    guard = {n: wp.val() for n, wp, _ in lg.guard_parts(p)}
    hw = sum(mass_g(s, "steel") for n, s in guard.items() if n.startswith(("m5", "m6")))
    hw_diffuser = sum(mass_g(s, "steel") for n, s in guard.items() if n.startswith("diffuser_screw"))
    per_side = (
        masses["01_bar_end_adapter"]["grams"]
        + masses["02_guard_arm"]["grams"]
        + masses["03_guard_blade_6mm_carbon"]["grams"]
        + masses["04_expander_sleeve_M_bar_id_15-17"]["grams"]
        + masses["05_expander_cone_M_bar_id_15-17"]["grams"]
        + hw
    )
    diffuser_kit = (
        masses["06_wind_guard_shell_RH"]["grams"] + 2 * masses["07_wind_guard_clamp_half"]["grams"] + hw_diffuser
    )
    info["diffuser"]["kit_grams"] = round(diffuser_kit, 1)
    summary = {
        "params": {k: getattr(p, k) for k in p.__dataclass_fields__},
        "derived": {
            "slot_length": p.slot_len,
            "screw_positions_y": p.screw_v,
            "bend_start_y": p.bend_start,
            "bend_angle_deg": p.bend_angle_deg,
            "run_start_centre_xy": [round(c, 2) for c in p.run_point(0)],
            "run_tip_centre_xy": [round(c, 2) for c in p.run_point(p.front_len)],
            "tip_x": round(p.tip_x, 2),
            "clamp_range": p.clamp_range,
        },
        "checks_carbon": info,
        "checks_print": info_p,
        "diffuser": {**info["diffuser"], "gusset": info["gusset"]},
        "masses": masses,
        "hardware_grams_per_side": round(hw, 1),
        "mass_per_side_grams_carbon_blade": round(per_side, 1),
        "mass_per_side_grams_with_diffuser": round(per_side + diffuser_kit, 1),
        "all_checks_passed": rep.ok and rep_p.ok,
    }
    (EXPORTS / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"== {'ALL CHECKS PASSED' if summary['all_checks_passed'] else 'SOME CHECKS FAILED'} ==")
    return 0 if summary["all_checks_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
