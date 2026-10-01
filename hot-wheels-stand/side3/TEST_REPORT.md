# Side-mechanism rack v3 (frame + swing): test report

Run: `python3 side3_test.py 1 2 3 4 5 6` and `python3 side3_stress.py 3 5` (results in `side3/qa_N.json`, `side3/stress_N.json`). Computational (CAD) tests only; nothing has been printed.

## What changed from the previous side design, and why
The previous design printed each side as one print-in-place module (cheek, bars, arms, pins). Slicing it showed **4,400 mm2 and 3,700 mm2 of floating layers** (the cheek hung 4.5 mm above the bars with nothing under it), so it could not be printed without supports. It also needed a separate frame and a tie bar (4 parts).

| | before | now |
|---|---|---|
| printed parts | 4 (module R, module L, wall frame, tie bar) | **3 printed parts, 2 designs**: `frame` (one piece, cheeks included) and `swing` (printed twice, mirrored) |
| hinges | print-in-place pins through a floating cheek | 4 x M4 bolts + nylock nuts |
| tie bar | printed square bar + screw | 6 mm dowel, glued |
| spring post | printed on the bar (cannot print on the bed face) | M4 hex bolt stud, head sunk in a hex pocket |
| support-free | no | yes (see T3) |

## Results
| Stalls | Reach mm | Frame print mm | Swing print mm | Fits 300 mm bed | Overlaps, 0 to 90 deg | Moving g | Spring N/mm | Spring force N |
|---|---|---|---|---|---|---|---|---|
| 1 | 66 | 184 x 192 | 46 x 82 | yes | 0 (31 poses) | 89 | 0.0018 | 0.19 to 0.29 |
| 2 | 115 | 184 x 192 | 46 x 131 | yes | 0 (31 poses) | 160 | 0.0049 | 0.47 to 0.79 |
| 3 | 163 | 184 x 202 | 46 x 179 | yes | 0 (31 poses) | 232 | 0.0098 | 1.03 to 1.66 |
| 4 | 210 | 184 x 245 | 53 x 226 | yes | 0 (31 poses) | 307 | 0.0151 | 1.91 to 2.86 |
| 5 | 256 | 184 x 291 | 60 x 272 | yes | 0 (31 poses) | 384 | 0.0206 | 3.12 to 4.39 |
| 6 | 306 | 184 x 341 | 66 x 322 | NO (needs ~340 mm bed) | 0 (31 poses) | 465 | 0.0253 | 4.37 to 6.03 |

* **T1 Closure:** the arm-to-bar joints close to 1e-13 mm at every size (the parallelogram is exact).
* **T2 Interference:** exact boolean overlap and minimum gap for every non-rigid pair, including bolts, nuts, washers, dowel, studs and spring rod, every 3 deg from 0 to 90 deg: **0 overlaps at all six sizes.** N=3 tightest gap 0.30 mm (hinge pin head to a card edge); dowel to bar 0.15 mm (glued).
* **T2b 1 deg sweep and stress variants** (N=3 and N=5): 1 deg sweep (91 poses), card 2.0 mm thick, blister 22 mm deep, card 180 mm tall, blister 90 mm wide: **0 overlaps in all of them.**
* **T3 Printability (slicing, 0.4 mm layers, 0.6 mm reach):**
  * frame (back face down): worst floating area 15.5 mm2, max unsupported span 1.2 mm: effectively none (the 45 degree underside of the open-stop lug).
  * swing (bar outer face down): the only unsupported layers are each arm's first layers, which **bridge about 18 mm between the two bars** (strip 12 mm wide) 834 mm2 at N=3. The arm sits 0.5 mm above the bars (a print-in-place gap). Pin heads are 45 degree cones. This is a normal bridge; use bridging cooling, 0.2 mm layers.
* **T4 Structural (40 g cards, PETG: 22 MPa in-layer, 10 MPa across layers):** arm pins carry the weakest load. With a 10 N push on one card in its plane: pin bending 2.79 MPa, safety factor 3.59 across layers. Hinge bearing SF 35.2, bolt shear SF 452.
* **T5 Tolerance (Monte Carlo, 0.1 mm position sigma, 0.08 mm diameter sigma):** probability that a pin binds in its arm hole = 0.0%; 1st-percentile remaining play 0.10 mm (0.4 mm radial clearance).
* **T6 Counterbalance spring:** without a spring the swing is released from rest only above the friction holding angle and hits the open stop at about 2.42 m/s (N=3, no friction). The fitted spring (k 0.0098 N/mm, F = k x length) leaves a residual torque of 0.7 N mm, so the swing stays where it is released at 10, 45 and 80 deg, with hinge friction of only about 1 N mm.
* **T7 Open and close:** closed position is set by magnets, open position by the stop lug on the cheek (B1 rests on it at 90 deg).

## What is NOT verified
* No physical print yet. Print a **1-stall swing and frame** first (about 100 g) and check: bolt fit in the 4.4 mm holes, arm pins free after printing (0.4 mm radial clearance, bridging of the arm underside), card slide in the cradle grooves.
* The 0.5 mm vertical gap between bars and arms depends on your printer; raise `X_B0` by 0.1 to widen it.
* Hinge friction is set by the nylock nut. If the swing drifts, tighten a little; if it feels stiff, back off. The spring rate must be within about 10% of the table value.
* Card weight 40 g and PETG allowables are assumed. Card hang geometry (105 x 165 mm, 85 x 36 x 16 blister) is assumed from earlier measurements.
* The 6-stall frame (341 mm) and swing (318 mm) exceed a 300 mm bed; 1 to 5 stalls fit.
