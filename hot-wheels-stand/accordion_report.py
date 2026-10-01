"""Writes accordion/TEST_REPORT.md from accordion_test_results.json."""
import json
r = json.load(open("accordion_test_results.json"))
Ns = sorted(r, key=int)
L = ["# Accordion hook rack: test report\n",
     "Run with `python3 accordion_test.py`, `python3 accordion_stress.py`. Figures come from the CAD meshes in `accordion_cad.py`. Nothing has been printed yet.\n",
     "## What it is\n",
     "A lazy-tongs (scissor) frame on the wall. The frame is the whole mechanism. Cards hang from printed round pegs on the bottom row of hinge points. "
     "Pulled open, the hooks sit 114.5 mm apart, so every card hangs in a row, fully visible, and lifts straight off its peg. "
     "Folded, the frame collapses to a 40 mm hook pitch for storage (cards off).\n",
     "**Four printed designs, no hardware except wall screws:** link, pivot pin, hook pin, wall plate. "
     "No springs, no magnets, no joint bolts, no print-in-place gaps. Every part is flat or lies on its side and needs no supports.\n",
     "| Stalls | Links | Pivot pins | Hook pins | Plate | Pieces in total | Width open / folded (mm) | Height open / folded (mm) |", "|---|---|---|---|---|---|---|---|"]
for n in Ns:
    x = r[n]
    L.append(f"| {n} | {x['links']} | {x['pivot_pins']} | {x['hook_pins']} | 1 | {x['links'] + x['pivot_pins'] + x['hook_pins'] + 1} | {x['rack_width_open']:.0f} / {x['rack_width_closed']:.0f} | {x['height_open']:.0f} / {x['height_closed']:.0f} |")
L += ["\nThe largest printed part is the 130 mm link, so any printer works; the plate is at most 155 mm tall.\n",
      "## What was tested\n",
      "1. **Closure:** at every degree from 14 to 70, every link end lands on the node it is meant to join (centre pivots and both rows).",
      "2. **Interference:** exact boolean intersection between every pair of parts that can meet (links, pins, hooks, plate, screw heads and cards with blisters) at 2 degree steps (29 poses). Cards are on the rack whenever the hooks are at least 107 mm apart (up to 24 degrees); the folded states are tested with the cards off.",
      "3. **Gaps:** smallest gap between separate parts (pin to hole 0.2 mm, set by design).",
      "4. **Stress variants (6 and 4 stalls):** card 112 mm wide, 2.0 mm thick, blister 22 mm deep, card 190 mm tall, hang hole 9 mm and 5.5 mm. No intersections.",
      "5. **Pin forces at the open stop** (worst case, link weights and 40 g cards, rigid-body equilibrium).",
      "6. **Droop from pin clearance:** linear program for the worst-case downward shift of the last hook when every pin sits against its hole wall.\n",
      "## Results\n",
      "| Stalls | Closure error (mm) | Poses | Intersections | Smallest gap (mm) | Max pin force (N) | Wall reaction at the plate (N) | Droop of last hook (mm), 0.2 mm / 0.4 mm slack |",
      "|---|---|---|---|---|---|---|---|"]
for n in Ns:
    x = r[n]; st = x["statics_open"]; dr = x["droop_mm"]
    tg = x["tightest"][0][0] if x["tightest"] else "-"
    L.append(f"| {n} | {x['closure_err_mm']:.0e} | {x['poses']} | {len(x['interference_bad'])} | {tg} | {st.get('max_pin_N', 0):.1f} | {st.get('wall_H0_N', 0):.1f} | " + (f"{dr['slack_0.2']} / {dr['slack_0.4']}" if dr else "-") + " |")
L += ["\nPin shear at 56 N (6 stalls) on a 4 mm pin is 4.5 MPa, about an eighth of PETG's strength. A link is held at its centre by the crossing pivot, so its buckling load is about 500 N, nine times the worst force.\n",
      "## Honest limits\n",
      "* **Droop.** Pin clearance adds up along the frame. With 0.2 mm clearance the last hook can sit 4 to 14 mm lower than the first (more stalls, more droop). Cards then hang a little lower to the right. To reduce it, print holes tight (a ream through 4.4 mm holes helps), or tilt the wall plate up by 1 degree on the 5 and 6 stall racks.",
      "* **Cards cannot stay on while folded.** The hooks are 114.5 mm apart open and 40 mm folded; cards are 105 mm wide. A staggered stack of cards on the pegs is not possible, because each front hook stem would have to pass through the cards behind it. Take the cards off first (they lift straight off).",
      "* **Gravity opens the rack and holds it open.** The upper row is the free one, so its weight pulls it down to the open stop. Folding holds only if you tie it (a rubber band or the cards' cardboard).",
      "* **Wide when open:** 677 mm for 6 stalls. It is a wall rack, not a shelf; the protrusion is only about 37 mm (6.4 mm plate + peg + card blister).",
      "* **Hang hole size is assumed** (7 mm hole, 12 mm below the card top). Check one real card: the 5 mm peg needs a hole of at least 5.5 mm.\n",
      "## Problems the tests found, and what changed\n",
      "| Found | Fix |", "|---|---|",
      "| The retaining barb of the pin sat inside the plate's front part instead of behind it (collision at the H0 hole and the slot). | Barb moved to the pin's rear tip; the plate got a rear groove for it. |",
      "| The first hook was a 3.5 mm blade, which does not fit through a card's round hang hole. | Replaced by a 5 mm round peg. |",
      "| A centre pivot hit the edge of the plate at 66 to 68 degrees. | Plate narrowed from 44 to 32 mm; screws moved in. |",
      "| The slot's rear groove ended exactly at the slot ends, so the barb collided at the open stop. | Groove extended 4.5 mm past each end. |",
      "| A staggered card stack (cards on the rack while folded) would need each hook stem to pass through the cards behind it. | Dropped: cards hang in one plane and come off before folding. |\n",
      "## Not tested (needs a real print)\n",
      "* Barb snap-in force and the kerf (1 mm) flexing in PETG; print one pin first.",
      "* Droop in practice and the real hang-hole size of your cards.",
      "* Pins are loose by design (0.2 mm), so the frame wobbles a little sideways; a 0.1 mm clearance is tighter but may bind on some printers."]
open("accordion/TEST_REPORT.md", "w").write("\n".join(L) + "\n")
print("report written")
