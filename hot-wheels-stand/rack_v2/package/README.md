# Accordion Card Rack (3-car and 5-car), sale package

Contents per size (`3car/`, `5car/`): `stl/` printable parts, `assembly_*.stl` reference models, `preview_*.png`, `fold_animation.gif`.

## Bill of materials (generic hardware)
| Item | 3-car | 5-car |
|---|---|---|
| M4x16 ISO 7380 button-head bolt (stainless) | 5 | 9 |
| M4x20 ISO 7380 button-head bolt (rail) | 4 | 6 |
| M4 DIN 985 nylon-lock nut | 9 | 15 |
| M4 washer, front (OD 9) | 6 | 10 |
| M4 washer, rear | 5 | 9 |
| M4 countersunk wall screw + anchor | 8 | 12 |
| printed link A (`link_A_x*.stl`) | 3 | 5 |
| printed link B with hook (`link_B_x*.stl`) | 3 | 5 |
| printed rail segments | 2 | 3 |

(Counts come from `bolt_count()` in `rack_cad.py`.)

## Print guide
PETG (PLA is acceptable indoors). 0.4 mm nozzle, 0.2 mm layers, 4 walls, 40% gyroid infill, **no supports**.
- Links: print flat as exported. The hook peg stands up.
- Rail segments: exported front-face-down (the nut groove faces up). Do not rotate.
- Ream every link hole and rail hole with a 4.5 mm drill if the bolt does not turn freely.
- Test coupon first: print one link A, one link B and one rail segment, and check the M4 bolt fit.

## Assembly
1. Slide M4 nuts into the rear groove of the rail (open ends) before joining the segments; seat the pivot nut in the hex pocket.
2. Screw the rail to the wall, level, through the countersunk holes.
3. Build the lattice flat on a table: bolt link A and link B pairs at the centres and upper nodes (nut behind link A, washers both sides), then attach the bottom nodes through the rail slot.
4. Tighten nylock nuts until snug, then back off 1/8 turn so the joints swing freely.
5. Open fully, hang one card per hook through its hang hole. **Remove cards before folding.**

## Selling note
Do not use the trademarked product name in listings or titles; call it a "die-cast car card display rack" or "collector card rack". Cards, hardware and brand names belong to their owners. Verify the hang hole of the card you target.

See `../QA_REPORT.md` for the test results and the list of what has not been physically verified.
