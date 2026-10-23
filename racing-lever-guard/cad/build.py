"""Build every part, run the fit checks and export STEP / STL.

    python build.py            # checks + exports into ../exports
    python build.py --check    # checks only
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
    "steel": 7.90,
}


def mass_g(shape: cq.Shape, material: str) -> float:
    return shape.Volume() / 1000.0 * DENSITY[material]


def rot_x(wp: cq.Workplane, deg: float) -> cq.Workplane:
    return wp.rotate((0, 0, 0), (1, 0, 0), deg)


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
            if frozenset({n1, n2}) in allowed:
                continue
            v = parts[n1].intersect(parts[n2]).Volume()
            worst = max(worst, v)
            if v > 1e-3:
                rep.check(f"{n1} x {n2}", False, f"overlap {v:.3f} mm3")
    rep.check("no unintended overlaps", worst <= 1e-3, f"worst {worst:.4f} mm3")

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
    d_adapter_grip = parts["adapter"].distance(ref["ref_grip"])
    rep.check("adapter seats on bar end", d_adapter_grip < 0.05, f"{d_adapter_grip:.2f} mm to grip end")

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

    bb = parts["blade"].BoundingBox()
    info.update(
        {
            "blade_path_length_mm": round(p.blade_path_len, 1),
            # ISO 7380 M5 head (2.75) on a 1 mm washer on top of the blade
            "protrusion_beyond_bar_end_mm": round(p.blade_seat_x + p.blade_t + 1.0 + 2.75, 2),
            "reach_ahead_of_bar_axis_mm": round(bb.ymax, 1),
            "coverage_inboard_of_bar_end_mm": round(-bb.xmin, 1),
            "blade_inner_face_ahead_of_bar_axis_mm": {
                f"{s:+.0f}": {
                    "run_start": round(p.run_point(0, p.blade_t / 2)[1] + s, 1),
                    "run_tip": round(p.run_point(p.front_len - p.tip_r, p.blade_t / 2)[1] + s, 1),
                }
                for s in (-p.adjust, 0, p.adjust)
            },
            "overall_envelope_mm": [
                round(bb.xmax - min(bb.xmin, -p.spigot_len), 1),
                round(bb.ymax + p.body_d / 2, 1),
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
    bb = wp.val().BoundingBox()
    return wp.translate((-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))


def export_all(p: lg.Params, pp: lg.Params) -> dict:
    step_dir, stl_dir = EXPORTS / "step", EXPORTS / "stl"
    step_dir.mkdir(parents=True, exist_ok=True)
    stl_dir.mkdir(parents=True, exist_ok=True)

    catalogue = [
        ("01_bar_end_adapter", lg.adapter(p), "al6061"),
        ("01b_bar_end_adapter_oem_thread", lg.adapter(p, spigot=False), "al6061"),
        ("02_guard_arm", lg.arm(p), "al6061"),
        ("03_guard_blade_4mm_carbon", lg.blade(p), "carbon"),
        ("03b_guard_blade_6mm_3dprint", lg.blade(pp), "pa12cf"),
    ]
    for size, (_, (lo, hi)) in lg.SLEEVES.items():
        catalogue.append((f"04_expander_sleeve_{size}_bar_id_{lo:g}-{hi:g}", lg.expander_sleeve(p, size), "tpu"))
    for size, (_, (lo, hi)) in lg.SLEEVES.items():
        catalogue.append((f"05_expander_cone_{size}_bar_id_{lo:g}-{hi:g}", lg.expander_cone(p, size), "al6061"))

    masses = {}
    for name, wp, mat in catalogue:
        cq.exporters.export(wp, str(step_dir / f"{name}.step"))
        cq.exporters.export(
            to_print_pose(name, wp), str(stl_dir / f"{name}.stl"), tolerance=0.02, angularTolerance=0.1
        )
        masses[name] = {"material": mat, "grams": round(mass_g(wp.val(), mat), 1)}
        print(f"  exported {name}  ({masses[name]['grams']} g {mat})")

    for label, with_ref in (("assembly_right_guard", False), ("assembly_right_guard_on_reference_bar", True)):
        assy = lg.assembly(p, with_reference=with_ref, size="M")
        try:
            assy.export(str(step_dir / f"{label}.step"))
        except AttributeError:
            assy.save(str(step_dir / f"{label}.step"))
        print(f"  exported {label}")
    return masses


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="run the checks only")
    args = ap.parse_args()

    p, pp = lg.Params(), lg.PRINT_PARAMS
    print("== checks: carbon / aluminium blade (4 mm) ==")
    rep, info = run_checks(p)
    print("== checks: 3D-printed blade (6 mm) ==")
    rep6, info6 = run_checks(pp)
    if args.check:
        return 0 if rep.ok and rep6.ok else 1

    print("== exports ==")
    masses = export_all(p, pp)
    hw = sum(mass_g(wp.val(), "steel") for n, wp, _ in lg.guard_parts(p) if n.startswith(("m5", "m6")))
    per_side = (
        masses["01_bar_end_adapter"]["grams"]
        + masses["02_guard_arm"]["grams"]
        + masses["03_guard_blade_4mm_carbon"]["grams"]
        + masses["04_expander_sleeve_M_bar_id_15-17"]["grams"]
        + masses["05_expander_cone_M_bar_id_15-17"]["grams"]
        + hw
    )
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
        },
        "checks_4mm": info,
        "checks_6mm": info6,
        "masses": masses,
        "hardware_grams_per_side": round(hw, 1),
        "mass_per_side_grams_carbon_blade": round(per_side, 1),
        "all_checks_passed": rep.ok and rep6.ok,
    }
    (EXPORTS / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"== {'ALL CHECKS PASSED' if summary['all_checks_passed'] else 'SOME CHECKS FAILED'} ==")
    return 0 if summary["all_checks_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
