# Accordion hook rack: test report

Run with `python3 accordion_test.py`, `python3 accordion_stress.py`. Figures come from the CAD meshes in `accordion_cad.py`. Nothing has been printed yet.

## What it is

A lazy-tongs (scissor) frame on the wall. The frame is the whole mechanism. Cards hang from printed round pegs on the bottom row of hinge points. Pulled open, the hooks sit 114.5 mm apart, so every card hangs in a row, fully visible, and lifts straight off its peg. Folded, the frame collapses to a 40 mm hook pitch for storage (cards off).

**Four printed designs, no hardware except wall screws:** link, pivot pin, hook pin, wall plate. No springs, no magnets, no joint bolts, no print-in-place gaps. Every part is flat or lies on its side and needs no supports.

| Stalls | Links | Pivot pins | Hook pins | Plate | Pieces in total | Width open / folded (mm) | Height open / folded (mm) |
|---|---|---|---|---|---|---|---|
| 1 | 0 | 0 | 1 | 1 | 2 | 105 / 30 | 41 / 123 |
| 2 | 2 | 2 | 2 | 1 | 7 | 219 / 70 | 41 / 123 |
| 3 | 4 | 4 | 3 | 1 | 12 | 334 / 111 | 41 / 123 |
| 4 | 6 | 6 | 4 | 1 | 17 | 448 / 151 | 41 / 123 |
| 5 | 8 | 8 | 5 | 1 | 22 | 563 / 191 | 41 / 123 |
| 6 | 10 | 10 | 6 | 1 | 27 | 677 / 232 | 41 / 123 |

The largest printed part is the 130 mm link, so any printer works; the plate is at most 155 mm tall.

## What was tested

1. **Closure:** at every degree from 14 to 70, every link end lands on the node it is meant to join (centre pivots and both rows).
2. **Interference:** exact boolean intersection between every pair of parts that can meet (links, pins, hooks, plate, screw heads and cards with blisters) at 2 degree steps (29 poses). Cards are on the rack whenever the hooks are at least 107 mm apart (up to 24 degrees); the folded states are tested with the cards off.
3. **Gaps:** smallest gap between separate parts (pin to hole 0.2 mm, set by design).
4. **Stress variants (6 and 4 stalls):** card 112 mm wide, 2.0 mm thick, blister 22 mm deep, card 190 mm tall, hang hole 9 mm and 5.5 mm. No intersections.
5. **Pin forces at the open stop** (worst case, link weights and 40 g cards, rigid-body equilibrium).
6. **Droop from pin clearance:** linear program for the worst-case downward shift of the last hook when every pin sits against its hole wall.

## Results

| Stalls | Closure error (mm) | Poses | Intersections | Smallest gap (mm) | Max pin force (N) | Wall reaction at the plate (N) | Droop of last hook (mm), 0.2 mm / 0.4 mm slack |
|---|---|---|---|---|---|---|---|
| 1 | 0e+00 | 29 | 0 | 0.2 | 0.0 | 0.0 | - |
| 2 | 0e+00 | 29 | 0 | 0.19 | 2.0 | 2.2 | 3.61 / 6.42 |
| 3 | 1e-14 | 29 | 0 | 0.19 | 8.4 | 6.5 | 8.27 / 9.87 |
| 4 | 6e-14 | 29 | 0 | 0.19 | 19.5 | 13.3 | 8.89 / 11.66 |
| 5 | 1e-13 | 29 | 0 | 0.19 | 35.4 | 22.4 | 9.74 / 13.41 |
| 6 | 1e-13 | 29 | 0 | 0.19 | 56.1 | 33.9 | 10.69 / 14.21 |

Pin shear at 56 N (6 stalls) on a 4 mm pin is 4.5 MPa, about an eighth of PETG's strength. A link is held at its centre by the crossing pivot, so its buckling load is about 500 N, nine times the worst force.

## Honest limits

* **Droop.** Pin clearance adds up along the frame. With 0.2 mm clearance the last hook can sit 4 to 14 mm lower than the first (more stalls, more droop). Cards then hang a little lower to the right. To reduce it, print holes tight (a ream through 4.4 mm holes helps), or tilt the wall plate up by 1 degree on the 5 and 6 stall racks.
* **Cards cannot stay on while folded.** The hooks are 114.5 mm apart open and 40 mm folded; cards are 105 mm wide. A staggered stack of cards on the pegs is not possible, because each front hook stem would have to pass through the cards behind it. Take the cards off first (they lift straight off).
* **Gravity opens the rack and holds it open.** The upper row is the free one, so its weight pulls it down to the open stop. Folding holds only if you tie it (a rubber band or the cards' cardboard).
* **Wide when open:** 677 mm for 6 stalls. It is a wall rack, not a shelf; the protrusion is only about 37 mm (6.4 mm plate + peg + card blister).
* **Hang hole size is assumed** (7 mm hole, 12 mm below the card top). Check one real card: the 5 mm peg needs a hole of at least 5.5 mm.

## Problems the tests found, and what changed

| Found | Fix |
|---|---|
| The retaining barb of the pin sat inside the plate's front part instead of behind it (collision at the H0 hole and the slot). | Barb moved to the pin's rear tip; the plate got a rear groove for it. |
| The first hook was a 3.5 mm blade, which does not fit through a card's round hang hole. | Replaced by a 5 mm round peg. |
| A centre pivot hit the edge of the plate at 66 to 68 degrees. | Plate narrowed from 44 to 32 mm; screws moved in. |
| The slot's rear groove ended exactly at the slot ends, so the barb collided at the open stop. | Groove extended 4.5 mm past each end. |
| A staggered card stack (cards on the rack while folded) would need each hook stem to pass through the cards behind it. | Dropped: cards hang in one plane and come off before folding. |

## Not tested (needs a real print)

* Barb snap-in force and the kerf (1 mm) flexing in PETG; print one pin first.
* Droop in practice and the real hang-hole size of your cards.
* Pins are loose by design (0.2 mm), so the frame wobbles a little sideways; a 0.1 mm clearance is tighter but may bind on some printers.
