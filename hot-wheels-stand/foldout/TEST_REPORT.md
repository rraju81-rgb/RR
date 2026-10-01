# Fold-down rack: test report

Run with `python3 foldout_test.py`, `python3 foldout_stress.py`. All figures come from the CAD meshes in `foldout_cad.py`.

## What was tested

1. **Kinematic closure.** At every degree from 0 to 90, each cross-arm pin has to land on the hole centre of the panel bar (B1) and of the B2 bar, and every arm has to keep its direction (pure translation, so every card stays upright).
2. **Interference.** Exact boolean intersection volume between every pair of parts that can meet, at 2 degree steps (46 poses) for every size. This covers panel, B2 bars, arms, cradles, cards with blisters, bolts, spacers, wall frame, cheeks, stops and the spring rods.
3. **Clearance.** Minimum gap between parts that are not meant to touch.
4. **Stress variants (6 stalls and 4 stalls):** card 1.6 mm thick, blister 20 mm deep, card 180 mm tall, all three combined, and a 1 degree sweep of the 6-stall rack (91 poses). Result: no intersection in any of them.
5. **Printing tolerance (Monte Carlo, 20 000 trials, hole position error 0.10 mm standard deviation).** The parallelogram has one arm per card, so it is over-constrained. This checks that the pin-to-hole offset stays inside the 0.4 mm clearance of a 3.8 mm hole around a 3.0 mm bolt.
6. **Statics and dynamics.** Gravity torque at the hinge versus opening angle (cards assumed 40 g each, printed parts at PETG density), spring counterbalance fit, and a swing simulation.

## Results

| Stalls | Panel length (mm) | Closure error (mm) | Arm direction error | Poses tested | Intersections | Tightest non-contact gap (mm) | Pin offset 95th pct (mm, limit 0.40) | Trials over limit |
|---|---|---|---|---|---|---|---|---|
| 1 | 232 | 1e-14 | 0 | 46 | 0 | 0.4 | 0.00 | 0.0% |
| 2 | 280 | 2e-14 | 0 | 46 | 0 | 0.4 | 0.17 | 0.0% |
| 3 | 329 | 3e-14 | 0 | 46 | 0 | 0.4 | 0.31 | 0.8% |
| 4 | 375 | 4e-14 | 0 | 46 | 0 | 0.4 | 0.31 | 0.7% |
| 5 | 421 | 4e-14 | 0 | 46 | 0 | 0.4 | 0.33 | 1.1% |
| 6 | 466 | 6e-14 | 0 | 46 | 0 | 0.4 | 0.33 | 1.0% |

The 0.4 to 0.5 mm gaps are the designed ones (magnet gap at the top crossbar, and the layer gap between arms and bars). Cards resting in their cradles, bolt heads against bars, spacers, the panel on its stop at 90 degrees and the spring ends touch by design and are not counted.

## Gravity and counterbalance

Without help the panel falls open: the gravity torque grows with the sine of the opening angle, and the free end hits the stop at about 2.8 to 4.4 m/s (hinge friction 0). Hinge friction alone cannot fix this: it would need to be most of the peak torque, far more than a printed hinge gives.

| Stalls | Moving mass (g) | Peak gravity torque (N m) | Free-end speed at the stop, no braking (m/s) | Closing effort at free end (N) |
|---|---|---|---|---|
| 1 | 175 | 0.15 | 2.84 | 0.7 |
| 2 | 252 | 0.25 | 3.29 | 0.9 |
| 3 | 328 | 0.38 | 3.66 | 1.2 |
| 4 | 408 | 0.55 | 3.94 | 1.5 |
| 5 | 490 | 0.76 | 4.19 | 1.8 |
| 6 | 574 | 1.01 | 4.38 | 2.2 |

**Fix: two extension springs** (one per side) from a post on the panel bar (height 64 mm) to an anchor on the wall frame straight above the hinge. Gravity torque follows sin(angle), and a spring whose force is proportional to its length gives the same sin(angle) curve, so the match is close to exact (fitted residual below 5 N mm). Spring force F = c0 + rate x length. The fit gives c0 near zero, i.e. initial tension about equal to rate times free length.

| Stalls | Anchor height (mm) | Rate per spring (N/mm) | Force closed to open (N each) | Residual torque (N m) | Hinge friction needed to stay put at any angle if the spring is off by +-10% / +-20% (N mm) |
|---|---|---|---|---|---|
| 1 | 150 | 0.0080 | 0.7 to 1.3 | 0.0007 | 15.3 / 30.6 |
| 2 | 150 | 0.0130 | 1.1 to 2.1 | 0.0011 | 25.0 / 50.0 |
| 3 | 165 | 0.0181 | 1.8 to 3.2 | 0.0017 | 38.3 / 76.6 |
| 4 | 185 | 0.0233 | 2.8 to 4.6 | 0.0024 | 55.2 / 110.4 |
| 5 | 210 | 0.0283 | 4.1 to 6.2 | 0.0033 | 75.9 / 151.9 |
| 6 | 235 | 0.0335 | 5.7 to 8.1 | 0.0044 | 100.6 / 201.3 |

With the spring tuned within +-10%, a hinge friction of 15 to 100 N mm (adjusted by the hinge bolt and spring washers) holds the panel at any angle and it moves by hand with well under 1 N at the free end. A spring more than 20% off needs more friction, up to about 200 N mm for 6 stalls, or the panel drifts.

## Problems the tests found, and the changes made

| Found | Fix |
|---|---|
| The tie bar joining the two B2 bars at their far end swung through the cards (4 to 28 degrees). | Moved the tie bar to the pivot end. |
| Each card's cradle overlapped the neighbouring arm's plate by 0.5 mm; on 6 stalls they collided at about 74 degrees. | Cradle now stops 0.5 mm short of the arm layer and is joined by a neck inside its own arm only. |
| The wall cheek and anchor were too close to the spring rod on 1 to 3 stalls (74 to 90 degrees). | Cheek trimmed to 28 mm high and the anchor raised to at least 150 mm. |
| Without springs the panel hits the stop at 2.8 to 4.4 m/s. | Added the counterbalance springs above. |
| The first hole size (3.7 mm) left only 0.35 mm of clearance for the over-constrained parallelogram. | Now 3.8 mm holes for 3.0 mm bolts. |

## Not tested (needs a real build)

* Nothing has been printed or assembled. Friction, stiffness of printed bars and the real mass of cards are assumptions (cards 40 g).
* Sideways play: each joint has up to 0.4 mm of clearance, so a card can tilt about 0.6 degrees, which moves its top by about 1.7 mm.
* Spring and magnet part numbers, and the fit of the nuts in their pockets, need to be checked with real parts.
