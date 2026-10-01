"""Writes foldout/TEST_REPORT.md from foldout_test_results.json."""
import json
r = json.load(open("foldout_test_results.json"))
Ns = sorted(r, key=int)
L = []
L.append("# Fold-down rack: test report\n")
L.append("Run with `python3 foldout_test.py`, `python3 foldout_stress.py`. All figures come from the CAD meshes in `foldout_cad.py`.\n")
L.append("## What was tested\n")
L.append("1. **Kinematic closure.** At every degree from 0 to 90, each cross-arm pin has to land on the hole centre of the panel bar (B1) and of the B2 bar, and every arm has to keep its direction (pure translation, so every card stays upright).")
L.append("2. **Interference.** Exact boolean intersection volume between every pair of parts that can meet, at 2 degree steps (46 poses) for every size. This covers panel, B2 bars, arms, cradles, cards with blisters, bolts, spacers, wall frame, cheeks, stops and the spring rods.")
L.append("3. **Clearance.** Minimum gap between parts that are not meant to touch.")
L.append("4. **Stress variants (6 stalls and 4 stalls):** card 1.6 mm thick, blister 20 mm deep, card 180 mm tall, all three combined, and a 1 degree sweep of the 6-stall rack (91 poses). Result: no intersection in any of them.")
L.append("5. **Printing tolerance (Monte Carlo, 20 000 trials, hole position error 0.10 mm standard deviation).** The parallelogram has one arm per card, so it is over-constrained. This checks that the pin-to-hole offset stays inside the 0.4 mm clearance of a 3.8 mm hole around a 3.0 mm bolt.")
L.append("6. **Statics and dynamics.** Gravity torque at the hinge versus opening angle (cards assumed 40 g each, printed parts at PETG density), spring counterbalance fit, and a swing simulation.\n")
L.append("## Results\n")
L.append("| Stalls | Panel length (mm) | Closure error (mm) | Arm direction error | Poses tested | Intersections | Tightest non-contact gap (mm) | Pin offset 95th pct (mm, limit 0.40) | Trials over limit |")
L.append("|---|---|---|---|---|---|---|---|---|")
for n in Ns:
    x = r[n]
    tg = x["tightest"][0][0] if x["tightest"] else "-"
    L.append(f"| {n} | {x['L']:.0f} | {x['closure_pin_err']:.0e} | {x['closure_dir_err']:.0f} | {x['poses_tested']} | {len(x['interference_bad'])} | {tg} | {x['tol_p95_offset']:.2f} | {x['tol_fail_rate'] * 100:.1f}% |")
L.append("\nThe 0.4 to 0.5 mm gaps are the designed ones (magnet gap at the top crossbar, and the layer gap between arms and bars). Cards resting in their cradles, bolt heads against bars, spacers, the panel on its stop at 90 degrees and the spring ends touch by design and are not counted.\n")
L.append("## Gravity and counterbalance\n")
L.append("Without help the panel falls open: the gravity torque grows with the sine of the opening angle, and the free end hits the stop at about 2.8 to 4.4 m/s (hinge friction 0). Hinge friction alone cannot fix this: it would need to be most of the peak torque, far more than a printed hinge gives.\n")
L.append("| Stalls | Moving mass (g) | Peak gravity torque (N m) | Free-end speed at the stop, no braking (m/s) | Closing effort at free end (N) |")
L.append("|---|---|---|---|---|")
for n in Ns:
    x = r[n]
    v0 = x["opening_by_friction_Nmm"]["0"]["impact_m_s"]
    L.append(f"| {n} | {x['mass_moving_g']:.0f} | {x['tau_max_Nm']:.2f} | {v0} | {x['lift_force_N_at_free_end']:.1f} |")
L.append("\n**Fix: two extension springs** (one per side) from a post on the panel bar (height 64 mm) to an anchor on the wall frame straight above the hinge. Gravity torque follows sin(angle), and a spring whose force is proportional to its length gives the same sin(angle) curve, so the match is close to exact (fitted residual below 5 N mm). Spring force F = c0 + rate x length. The fit gives c0 near zero, i.e. initial tension about equal to rate times free length.\n")
L.append("| Stalls | Anchor height (mm) | Rate per spring (N/mm) | Force closed to open (N each) | Residual torque (N m) | Hinge friction needed to stay put at any angle if the spring is off by +-10% / +-20% (N mm) |")
L.append("|---|---|---|---|---|---|")
for n in Ns:
    x = r[n]; sp = x["spring"]; tf = x["spring_tolerance_friction_Nmm"]
    L.append(f"| {n} | {max(round(0.5 * x['L'] / 5) * 5, 150)} | {sp['k_N_per_mm']:.4f} | {sp['force_closed_N_each']:.1f} to {sp['force_open_N_each']:.1f} | {sp['resid_max_Nm']:.4f} | {tf['+-10%']} / {tf['+-20%']} |")
L.append("\nWith the spring tuned within +-10%, a hinge friction of 15 to 100 N mm (adjusted by the hinge bolt and spring washers) holds the panel at any angle and it moves by hand with well under 1 N at the free end. A spring more than 20% off needs more friction, up to about 200 N mm for 6 stalls, or the panel drifts.\n")
L.append("## Problems the tests found, and the changes made\n")
L.append("| Found | Fix |")
L.append("|---|---|")
L.append("| The tie bar joining the two B2 bars at their far end swung through the cards (4 to 28 degrees). | Moved the tie bar to the pivot end. |")
L.append("| Each card's cradle overlapped the neighbouring arm's plate by 0.5 mm; on 6 stalls they collided at about 74 degrees. | Cradle now stops 0.5 mm short of the arm layer and is joined by a neck inside its own arm only. |")
L.append("| The wall cheek and anchor were too close to the spring rod on 1 to 3 stalls (74 to 90 degrees). | Cheek trimmed to 28 mm high and the anchor raised to at least 150 mm. |")
L.append("| Without springs the panel hits the stop at 2.8 to 4.4 m/s. | Added the counterbalance springs above. |")
L.append("| The first hole size (3.7 mm) left only 0.35 mm of clearance for the over-constrained parallelogram. | Now 3.8 mm holes for 3.0 mm bolts. |\n")
L.append("## Not tested (needs a real build)\n")
L.append("* Nothing has been printed or assembled. Friction, stiffness of printed bars and the real mass of cards are assumptions (cards 40 g).")
L.append("* Sideways play: each joint has up to 0.4 mm of clearance, so a card can tilt about 0.6 degrees, which moves its top by about 1.7 mm.")
L.append("* Spring and magnet part numbers, and the fit of the nuts in their pockets, need to be checked with real parts.")
open("foldout/TEST_REPORT.md", "w").write("\n".join(L) + "\n")
print("written")
