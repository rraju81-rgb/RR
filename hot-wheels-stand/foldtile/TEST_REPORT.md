# Flat-fold hook tile rack: test report

Idea taken from the flat, card-sized print-in-place folding phone stand (https://www.printables.com/model/59748-credit-card-sized-foldable-mobile-stand; I could not open the page from here, so I used its described idea: a flat print-in-place folding part that is about 6 mm thick when folded).

## The design
* **One printed part per card.** A tile is a slab 112 x 24 x 8 mm screwed to the wall (2 screws). Print 3 tiles for a 3-car rack, 5 for a 5-car rack, or any number; tiles lock side by side with a tongue and groove at 112 mm pitch. Stack rows 185 mm apart for a grid.
* **Flat-fold hook arm, printed in place.** The arm lies flush in a pocket in the tile face. Swing it out and it stops at about 90 degrees, pointing out of the wall. The card hangs on it through the hang hole.
* **The hinge axis is vertical**, so a card's weight cannot fold the arm back, and no stop has to carry the load.
* **Thin:** 8 mm folded or empty; about 31 mm deep with a card hung. The tile is hidden behind the card (the card's top edge lines up with the tile's top edge).
* **No hardware** except wall screws. No bolts, springs, magnets or snaps.

## Results (`python3 foldtile_test.py`)
| Test | Result |
|---|---|
| T1 Integrity | tile and arm both watertight; print footprint 115 x 24 x 8 mm (fits any bed); 26.4 g of filament per tile |
| T2 Hinge | arm swings freely from 0 to 89 degrees, first contact (the stop) at 90 degrees; smallest arm-to-tile gap over the swing 0.33 mm |
| T3 Card fit | arm cross-section diagonal 6.02 mm: fits hang holes of 6.5 mm and larger (**not** 6.0 mm). A hung card never touches the tile or arm at any depth along the arm; card-to-card gap 7.0 mm; joined tiles do not overlap |
| T4 Printability | front face down, 0.4 mm layers: worst floating area 10.4 mm2 over a 1.3 mm span (the screw countersink); the arm lies on the bed. The pocket ceiling bridges a 5 mm gap (102 mm2). **No supports.** |
| T5 Structural (40 g card, PETG) | arm bending 0.64 MPa with the card (safety factor 34.4); a 10 N downward pull on one arm gives 16.3 MPa (safety factor 1.3), so the arm will break at about 13 N: a card tears first. Pin shear SF 9.9 at 10 N. |
| T6 Tolerance (Monte Carlo) | pin binds 2.7%, pocket binds 1.7%; arm does not fit a 7 mm hole 0%. If an arm is stiff, work it back and forth by hand or run a 3.5 mm drill through the pin hole. |

## Not verified
* **Nothing has been printed.** Print one tile first and check: the arm frees up, swings smoothly, and the card hangs.
* The **hang-hole size (7 mm, 12 mm below the card top) is an assumption.** The arm needs a hole of at least 6.5 mm.
* The arm hinge relies on bridging a 5 mm span for the pocket ceiling and on 0.4 mm clearances; printers differ.
* The tile is hidden behind a card only if the card's top edge is at the tile's top edge; if your cards hang lower, the tile will show.
* Card weight and PETG strength figures are assumed.
