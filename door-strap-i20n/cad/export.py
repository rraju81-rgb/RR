"""Build every part and export deliverables + render meshes.

usage:  python export.py [render_mesh_dir]
"""
import json
import math
import os
import sys
import time

import cadquery as cq
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import door_strap as ds          # noqa: E402
import door_mockup              # noqa: E402
import strap                    # noqa: E402

ROOT = os.path.dirname(HERE)
STEP_DIR = os.path.join(ROOT, "step")
STL_DIR = os.path.join(ROOT, "stl")
WEB_DIR = os.path.join(ROOT, "web")
MESH_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "_mesh")
for d in (STEP_DIR, STL_DIR, WEB_DIR, MESH_DIR):
    os.makedirs(d, exist_ok=True)

COLORS = {  # name: (r, g, b, metallic, roughness)
    "housing": (0.03, 0.03, 0.035, 0.0, 0.55),
    "badge": (0.02, 0.02, 0.022, 0.0, 0.25),
    "lever": (0.09, 0.09, 0.095, 0.0, 0.7),
    "slider": (0.09, 0.09, 0.095, 0.0, 0.7),
    "pivot_pin": (0.8, 0.8, 0.82, 1.0, 0.25),
    "strap_pin": (0.8, 0.8, 0.82, 1.0, 0.25),
    "washers": (0.8, 0.8, 0.82, 1.0, 0.3),
    "clamp_screw": (0.75, 0.75, 0.78, 1.0, 0.3),
    "insert": (0.78, 0.6, 0.25, 1.0, 0.3),
    "cable_sheath": (0.015, 0.015, 0.015, 0.0, 0.6),
    "cable_inner": (0.7, 0.7, 0.72, 1.0, 0.35),
    "strap": (0.62, 0.02, 0.025, 0.0, 0.85),
    "trim": (0.03, 0.03, 0.032, 0.0, 0.6),
}


def stl(shape, path, tol=0.02, ang=0.1):
    cq.exporters.export(shape, path, exportType="STL", tolerance=tol,
                        angularTolerance=ang)


def step(shape, path):
    cq.exporters.export(shape, path, exportType="STEP")


def to_bed(shape, rx=0.0):
    """Rotate about X by rx (deg) and drop onto the build plate (z=0)."""
    s = shape.rotate((0, 0, 0), (1, 0, 0), rx) if rx else shape
    bb = s.val().BoundingBox()
    return s.translate((-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2,
                        -bb.zmin))


def strap_tri(pose, mirror=False, z_range=None):
    V, F, UV = strap.strap_mesh(pose, z_range=z_range, mirror=mirror)
    tris = np.vstack([F[:, [0, 1, 2]], F[:, [0, 2, 3]]])
    return trimesh.Trimesh(V, tris, process=False), (V, F, UV)


def main():
    t0 = time.time()
    report = {"kinematics": ds.kinematics_table(17),
              "cable_travel_mm": ds.CABLE_TRAVEL,
              "slider_travel_mm": ds.SLIDER_TRAVEL}

    housing = ds.build_housing()
    lever0 = ds.build_lever()
    slider = ds.build_slider(0.0)
    badge = ds.build_badge()
    gauge = ds.build_fit_gauge(housing)
    print("built", round(time.time() - t0, 1), "s")

    parts_lh = {
        "housing_LH": housing,
        "lever_LH": ds.pose_lever(lever0, ds.POSE_REST),
        "fit_gauge_LH": gauge,
    }
    parts_rh = {k.replace("_LH", "_RH"): v.mirror("YZ")
                for k, v in parts_lh.items()}

    # ---------------- STEP: individual parts (assembly coordinates) --------
    for name, shp in {**parts_lh, **parts_rh}.items():
        step(shp, os.path.join(STEP_DIR, f"{name}.step"))
    step(slider, os.path.join(STEP_DIR, "cable_slider.step"))
    step(badge, os.path.join(STEP_DIR, "badge_insert.step"))

    # ---------------- STEP: coloured assemblies ----------------------------
    for side, mirror in (("LH", False), ("RH", True)):
        parts = ds.build_assembly(ds.POSE_REST, mirror=mirror,
                                  with_cable=False)
        assy = cq.Assembly(name=f"door_strap_{side}")
        for n, shp in parts.items():
            c = COLORS.get(n, (0.5, 0.5, 0.5, 0, 0.5))
            assy.add(shp, name=n, color=cq.Color(c[0], c[1], c[2]))
        assy.save(os.path.join(STEP_DIR, f"door_strap_{side}_assembly.step"))

    # ---------------- STL: print orientation -------------------------------
    stl(to_bed(housing, -90), os.path.join(STL_DIR, "housing_LH.stl"))
    stl(to_bed(housing.mirror("YZ"), -90), os.path.join(STL_DIR,
                                                         "housing_RH.stl"))
    stl(to_bed(lever0), os.path.join(STL_DIR, "lever_LH.stl"))
    stl(to_bed(lever0.mirror("YZ")), os.path.join(STL_DIR, "lever_RH.stl"))
    stl(to_bed(slider, 90), os.path.join(STL_DIR, "cable_slider_x2.stl"))
    stl(to_bed(badge, -90), os.path.join(STL_DIR, "badge_insert_x2.stl"),
        tol=0.01, ang=0.05)
    stl(to_bed(gauge, -90), os.path.join(STL_DIR, "fit_gauge_LH.stl"))
    stl(to_bed(gauge.mirror("YZ"), -90), os.path.join(STL_DIR,
                                                       "fit_gauge_RH.stl"))
    print("STEP/STL done", round(time.time() - t0, 1), "s")

    # ---------------- masses ----------------------------------------------
    rho = {"housing": 1.15, "lever": 1.30, "slider": 1.30, "badge": 1.15}
    vols = {"housing": housing.val().Volume(), "lever": lever0.val().Volume(),
            "slider": slider.val().Volume(), "badge": badge.val().Volume()}
    report["volumes_cm3"] = {k: v / 1000 for k, v in vols.items()}
    report["mass_g"] = {k: vols[k] / 1000 * rho[k] for k in vols}
    bb = housing.val().BoundingBox()
    report["housing_bbox"] = [bb.xlen, bb.ylen, bb.zlen]

    # ---------------- render meshes ---------------------------------------
    def dump(scene, parts, strap_pose=None, mirror=False, strap_z=None):
        d = os.path.join(MESH_DIR, scene)
        os.makedirs(d, exist_ok=True)
        for n, shp in parts.items():
            stl(shp, os.path.join(d, f"{n}.stl"), tol=0.01, ang=0.06)
        if strap_pose is not None:
            V, F, UV = strap.strap_mesh(strap_pose, z_range=strap_z,
                                        mirror=mirror)
            strap.write_obj(os.path.join(d, "strap.obj"), V, F, UV)

    for side, mirror in (("LH", False), ("RH", True)):
        for pose_name, pose in (("rest", ds.POSE_REST),
                                ("full", ds.POSE_FULL)):
            parts = ds.build_assembly(pose, mirror=mirror, with_cable=True)
            dump(f"{side}_{pose_name}", parts, pose, mirror)

    # cut-away (Z < 7) for the mechanism view, LH only
    cutter = ds.box(-200, 200, -100, 100, -100, 7.0)
    for pose_name, pose in (("rest", ds.POSE_REST), ("full", ds.POSE_FULL)):
        parts = ds.build_assembly(pose, mirror=False, with_cable=True)
        cut = {}
        for n, shp in parts.items():
            try:
                c = shp.intersect(cutter)
                if c.val().Volume() > 1e-3:
                    cut[n] = c
            except Exception:
                pass
        dump(f"cut_{pose_name}", cut, pose, False,
             strap_z=(-ds.STRAP_W / 2, 7.0))

    # door-trim mock-up
    trim = door_mockup.build_trim()
    dump("trim", {"trim": trim})
    print("render meshes done", round(time.time() - t0, 1), "s")

    # ---------------- GLB for the web viewer (LH, rest) --------------------
    scene = trimesh.Scene()
    parts = ds.build_assembly(ds.POSE_REST, mirror=False, with_cable=True)
    for n, shp in parts.items():
        p = os.path.join(MESH_DIR, "LH_rest", f"{n}.stl")
        m = trimesh.load(p)
        c = COLORS[n]
        m.visual = trimesh.visual.TextureVisuals(
            material=trimesh.visual.material.PBRMaterial(
                name=n, baseColorFactor=[c[0], c[1], c[2], 1.0],
                metallicFactor=c[3], roughnessFactor=c[4]))
        scene.add_geometry(m, node_name=n, geom_name=n)
    sm, _ = strap_tri(ds.POSE_REST)
    c = COLORS["strap"]
    sm.visual = trimesh.visual.TextureVisuals(
        material=trimesh.visual.material.PBRMaterial(
            name="strap", baseColorFactor=[c[0], c[1], c[2], 1.0],
            metallicFactor=0.0, roughnessFactor=c[4]))
    scene.add_geometry(sm, node_name="strap", geom_name="strap")
    # glTF is Y-up, metres: Z-up -> Y-up puts the face towards +Z (viewer)
    T = trimesh.transformations.rotation_matrix(math.radians(-90), [1, 0, 0])
    scene.apply_transform(T)
    scene.apply_scale(0.001)
    scene.export(os.path.join(WEB_DIR, "door_strap_LH.glb"))

    # ---------------- checks ----------------------------------------------
    checks = {}
    for f in sorted(os.listdir(STL_DIR)):
        m = trimesh.load(os.path.join(STL_DIR, f))
        checks[f] = dict(watertight=bool(m.is_watertight),
                         volume_cm3=round(m.volume / 1000, 2),
                         extents=[round(x, 1) for x in m.extents])
    report["stl_checks"] = checks
    with open(os.path.join(ROOT, "build_report.json"), "w") as f:
        json.dump(report, f, indent=1)
    print(json.dumps({k: report[k] for k in
                      ("mass_g", "housing_bbox", "stl_checks")}, indent=1))
    print("all done", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
