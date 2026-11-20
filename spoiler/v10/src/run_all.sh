#!/bin/sh
# Rebuild the v10 package: six parts as marked (3 across x front/rear), cored to <= 10 mm, smooth grooved rim at the back,
# pinned 30-degree joints. Run from the spoiler/ folder:  sh v10/src/run_all.sh        (about 25 minutes on 4 cores)
# v10 starts from the same solid body as v6-v9 (v6/out/E2.stl) and the car body under it (v6/car/out/); both are built
# first if missing.
set -e
[ -f v6/out/E2.stl ] || sh v6/src/run_all.sh
[ -f v6/car/out/car_body_conf.ply ] || python3 v6/car/src/car_build_all.py
mkdir -p v10/out v10/print v10/assembled v10/docs
python3 v10/src/p1_core.py        # three sections cored (skin 8.5 mm) with the grooved rim and skirt        -> out/cored_L|C|R.stl
python3 v10/src/p2_parts.py       # front/rear cuts, pins, tongues and grooves, splines                    -> assembled/
python3 v10/src/p3_validate.py    # meshes, thickness <= 10 mm, overlaps, clearances, hole walls          (stops if a check fails)
python3 v10/src/p4_place.py       # bed placement for 420 x 420 x 500, each part on its cut face           -> print/
python3 v10/src/p5_figures.py     # figures                                                                -> docs/
python3 v10/src/p6_package.py     # zip of README + print/ + assembled/ + docs/                            -> Polo_spoiler_v10_print_package.zip
