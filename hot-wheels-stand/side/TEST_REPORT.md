# Side-mechanism rack (4 printed parts): test report

Run with `python3 side_test.py` and `python3 side_stress.py`. All figures come from the CAD meshes in `side_cad.py`. Nothing has been printed or assembled.

## What changed from the previous version

| | Previous fold-down rack | This version |
|---|---|---|
| Printed parts per rack | 12 to 22 (arms, bars, spacers, posts, ...) plus 4N + 8 bolts and nuts | **4**: module_R, module_L (mirror), wall_frame, tie_bar |
| Joint bolts and nuts | 4 per card plus 8 | none: pins are printed in place (0.4 mm clearance) |
| What moves | a full-width panel with a top bar, 466 mm long at 6 stalls | two side linkages only; the bars end just above the last card |
| How far it sticks out when open | panel length (232 to 466 mm) | bar length (66 to 302 mm) |
| Wall base | two cheeks 48 mm deep plus posts | cheek 30 mm deep, folded into each module |

| Stalls | Old open reach (mm) | New open reach (mm) | Saved |
|---|---|---|---|
| 1 | 232 | 66 | 72% |
| 2 | 280 | 115 | 59% |
| 3 | 329 | 163 | 50% |
| 4 | 375 | 210 | 44% |
| 5 | 421 | 256 | 39% |
| 6 | 466 | 302 | 35% |

The row of standing cards still needs about 45 mm per stall of depth when open, so the reach cannot drop below roughly 45 mm x stalls plus 36 mm.

## What was tested

1. **Kinematic closure:** at every degree from 0 to 90, each cross-arm pin lands exactly on the B1 and B2 hole centres, and every arm keeps its direction (cards stay upright).
2. **Interference:** exact boolean intersection of every pair of parts that can meet, at 2 degree steps (46 poses) for every size. This includes cards with blisters, cradles, arms, pins, both bars, cheeks, frame, fingers, tie bar and washer, and the spring rods.
3. **Print-in-place clearance:** the smallest gap between separate bodies inside one module at the printed (closed) pose. It has to stay above 0.3 mm or the pins fuse in the print.
4. **Stress variants:** card 1.6 mm thick, blister 20 mm deep, card 180 mm tall, all three combined, and a 1 degree sweep of the 6-stall rack (91 poses). No intersections.
5. **Tolerance (Monte Carlo, 20 000 trials, 0.10 mm hole position error):** pin offset against the 0.4 mm pin clearance.
6. **Gravity torque, spring counterbalance and swing simulation** (cards assumed 40 g each).

## Results

| Stalls | Frame height (mm) | Poses | Intersections | Closure error (mm) | Print-in-place min gap (mm) | Pin offset 95th pct (mm, limit 0.40) | Trials over limit |
|---|---|---|---|---|---|---|---|
| 1 | 222 | 46 | 0 | 1e-14 | 0.38 | 0.00 | 0.0% |
| 2 | 270 | 46 | 0 | 2e-14 | 0.38 | 0.17 | 0.0% |
| 3 | 319 | 46 | 0 | 5e-14 | 0.38 | 0.31 | 0.8% |
| 4 | 365 | 46 | 0 | 3e-14 | 0.38 | 0.31 | 0.7% |
| 5 | 411 | 46 | 0 | 4e-14 | 0.38 | 0.33 | 1.1% |
| 6 | 456 | 46 | 0 | 6e-14 | 0.38 | 0.33 | 1.0% |

The 0.4 mm open stop and the magnet gap are the designed clearances. Cards resting on their cradle floor and the tie bar in its square holes (0.2 mm close fit) touch by design and are not counted.

## Gravity and counterbalance

The panel is lighter than before (no full-length panel and top bar), so the torque is lower. Without springs it still falls open and hits the stop at 1.7 to 3.2 m/s at its free end.

| Stalls | Moving mass (g) | Peak gravity torque (N m) | Free-end speed at the stop, no springs (m/s) | Spring rate each (N/mm) | Spring force closed to open (N each) | Residual torque (N m) | Hinge friction to stay put if the spring is off by +-10% / +-20% (N mm) |
|---|---|---|---|---|---|---|---|
| 1 | 87 | 0.02 | 1.71 | 0.0016 | 0.2 to 0.2 | 0.0001 | 2.1 / 4.2 |
| 2 | 158 | 0.08 | 2.06 | 0.0047 | 0.4 to 0.8 | 0.0003 | 7.7 / 15.3 |
| 3 | 230 | 0.17 | 2.4 | 0.0096 | 1.0 to 1.6 | 0.0007 | 16.6 / 33.2 |
| 4 | 305 | 0.29 | 2.69 | 0.0150 | 1.9 to 2.8 | 0.0013 | 29.1 / 58.2 |
| 5 | 383 | 0.45 | 2.94 | 0.0205 | 3.1 to 4.4 | 0.0020 | 45.2 / 90.4 |
| 6 | 462 | 0.65 | 3.18 | 0.0264 | 4.6 to 6.2 | 0.0028 | 65.0 / 130.0 |

Two extension springs (one per side) from a post on each B1 bar to a tab on the frame, straight above the hinge, cancel the gravity torque almost exactly (the fitted residual is under 3 N mm). Printed pins give almost no friction, so keep the spring within about 10% and expect the panel to drift if it is not: tune it by picking the spring. A friction hinge is not possible here because the pins print in place.

## Problems the tests found, and what changed

| Found | Fix |
|---|---|
| The tie bar through the two bars, first placed 14 mm above the hinge, hit the first cross arm at 80 to 90 degrees. | Moved the tie bar to a tail below the hinge. |
| The closed-position stop block was swept by the tail of the bar at 20 degrees. | Removed it: the two magnets self-centre the panel at 0 degrees. |
| The open-stop block collided with the tie bar head at 62 to 68 degrees. | Moved the stop block 18 to 30 mm forward of the hinge. |
| With 1 stall the spring post and the magnet finger collided. | Spring post height now stays at least 14 mm below the magnet. |
| The first stop block touched the second bar at 88 degrees (zero gap). | Stop block shortened. |

## Not tested (needs a real build)

* Nothing has been printed. Print-in-place pins with 0.4 mm clearance and 45 degree cone heads depend on your printer; print a 1-stall module first.
* The 0.4 mm gap over the bars and arms is bridged in the layer above it. If it fuses, raise `GAP` and the layer clearances in `side_cad.py`.
* Card mass (40 g) and spring availability are assumptions. The panel stops at about 90.8 degrees.
* Sideways play: each joint has up to 0.4 mm of clearance, so a card can tilt about 0.6 degrees (its top moves about 1.7 mm).
* Large modules (6 stalls: bars about 300 mm) need a large print bed or diagonal placement.
