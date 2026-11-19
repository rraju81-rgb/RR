#!/bin/sh
# Rebuild the v9 package: six equal pieces, cored to a skin no thicker than 10 mm, pin-and-chamfer joints.
# Run from the spoiler/ folder:  sh v9/src/run_all.sh        (about 10 minutes on 4 cores)
# v9 starts from the same solid body as v6-v8 (v6/out/E2.stl) and the car body under it (v6/car/out/), which it uses to
# tell the underside from the visible surfaces; both are built first if missing.
set -e
[ -f v6/out/E2.stl ] || sh v6/src/run_all.sh
[ -f v6/car/out/car_body_conf.ply ] || python3 v6/car/src/car_build_all.py
mkdir -p v9/out v9/print v9/assembled v9/docs
python3 v9/src/p1_core.py         # six slices, cored from underneath (skin 8.5 mm, seal rim, fin tips)  -> out/cored_P*.stl
python3 v9/src/p2_joints.py       # pins, chamfered tongue and groove, centre spline                       -> assembled/
python3 v9/src/p3_validate.py     # meshes, thickness <= 10 mm, overlaps, clearances, hole walls          (stops if a check fails)
python3 v9/src/p4_place.py        # bed placement for 420 x 420 x 500                                      -> print/
python3 v9/src/p5_figures.py      # figures                                                                -> docs/
python3 v9/src/p6_package.py      # zip of README + print/ + assembled/ + docs/                            -> Polo_spoiler_v9_print_package.zip
