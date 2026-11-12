# Polo Oettinger-style roof spoiler v7: 4 equal pieces with bow-tie keys

v7 is the same solid spoiler as v6, cut into **four equal pieces of 325 mm** instead of three pieces of 433 mm, because the v6 pieces warped in printing. The shape, the underside and the car coordinates are unchanged: X is the width of the car, Y is up, +Z points to the rear. The overall size is still 1,300 × 147 × 292 mm.

## What changed from v6

| | v6 | v7 |
|---|---|---|
| Pieces | 3, each 433 mm long | **4, each 325 mm long** |
| Cuts | x = ±216.7 mm | x = −325, 0 and +325 mm |
| Print height, standing on end | 433 mm | **325 mm** |
| Largest piece | 1,042 cm³ | 792 cm³ |
| Bow-tie keys | 4 (2 per seam) | 6 (2 per seam) |
| Supports under the fins start | 225 mm above the bed | 116 mm above the bed |

The key is the same as in v6, and all six are identical. Only the pocket positions moved. The underside has a V-shaped kink line where the roof meets the tailgate, and that line curves forward towards the sides. Each pocket now sits fully on one flat facet, at least 3 mm clear of the kink:
- centre seam: keys at z = 132 and 165 mm;
- outer seams: keys at z = 123 and 161 mm.

## Files

`print/` holds bed-ready files, already oriented and centred on a 420 × 420 mm bed:

| File | Qty | Print size (mm) | Orientation | Supports |
|---|---|---|---|---|
| `v7_1_LEFT_END.stl` | 1 | 135 × 288 × 325 | Standing on its cut face, fin at the top | Tree supports, build plate only, 55° threshold. About 31 cm² under the fin, 116–325 mm up. |
| `v7_2_LEFT_MID.stl` | 1 | 48 × 272 × 325 | Standing on its centre-seam face | None |
| `v7_3_RIGHT_MID.stl` | 1 | 48 × 272 × 325 | Standing on its centre-seam face | None |
| `v7_4_RIGHT_END.stl` | 1 | 135 × 288 × 325 | Standing on its cut face, fin at the top | As for LEFT_END |
| `v7_BOWTIE_KEY_x6.stl` | 6 (+2 spare) | 56 × 23 × 6.25 | Flat, car-side face on the bed | None |
| `v7_BOWTIE_KEYS_plate_of_8.stl` | 1 plate | 242 × 53 × 6.25 | 8 keys on one plate | None |

`assembled/` holds the same 4 pieces (`P1`–`P4`, left to right) and 6 keys in car coordinates, in their fitted positions. Load them together in the slicer to check the assembly.

`docs/` holds the figures: the assembled view, the exploded underside, the seam close-ups, the bed layouts, the key drawing and the print-height comparison with v6.

`src/` holds the scripts. Running `sh v7/src/run_all.sh` from `spoiler/` rebuilds everything in under a minute.

## Checks on the delivered files

- Every part is one closed, watertight body with consistent winding, **zero self-intersections** and no zero-area faces.
- The middle pieces are 325.00 mm long and the end pieces 324.96 mm, because the body is 1,299.92 mm wide.
- Each key sits in its pocket with **0.15 mm clearance** to both pieces and no overlap. There is a 0.25 mm glue gap at the pocket floor.
- The key's outer face is flush with the underside to within **±0.10 mm**.
- The skin left above each pocket floor is at least **6.4 mm** for the front keys and **9.6 mm** for the rear keys.
- The four pieces put back together reproduce the solid spoiler exactly. The only material missing is the 33 cm³ of the six pockets, which the keys fill.
- Every piece fits a 420 × 420 × 500 mm volume with 175 mm spare in height.

## Printing without warping

**What the 4-piece cut does and doesn't do.** Each print is 25% lower and the heaviest piece is 24% lighter, so prints are shorter and the fin supports are about half as tall. The footprint on the bed is unchanged: it is still the spoiler's cross-section, a thin strip about 270 mm long with only 23–25 cm² touching the bed. A long, thin footprint lifts at its two ends first. So the cut helps, but the material and the settings below matter more.

**Material on the Kobra 3 Max.** This printer has an open frame and a bed that reaches 90 °C.
- **ASA** shrinks more as it cools, and on an open printer it lifts off the bed and can split between layers. Print it only inside an enclosure. A tent or a box over the printer is enough.
- **PETG** shrinks much less and prints well on an open printer.
- The trade-off is heat on the car. PETG starts to soften at about 80 °C and ASA at about 100 °C, and a dark part on a roof in strong sun can get close to PETG's limit. ASA in an enclosure is the better part. PETG is the easier print.
- Don't use PLA.

The v6 notes recommended ASA without saying it needs an enclosure on this printer. That was incomplete, and it is the most likely reason the v6 pieces warped if they were printed in ASA.

**Settings that hold the base down:**

| Setting | Use |
|---|---|
| Brim | 15–20 mm wide, no gap to the part. "Mouse ears" on the two thin ends of the footprint also work. |
| First layer | 0.25–0.30 mm high, 20–30 mm/s, on a clean bed with glue stick or bed adhesive. |
| Bed temperature | PETG 75–85 °C. ASA 90 °C. |
| Part cooling fan | ASA: off, or at most 20%. PETG: 30–50%, and off for the first few layers. |
| Draughts | No fan or air conditioning blowing on the printer. For ASA, turn on the slicer's draft shield as well as using the enclosure. |
| Walls and infill | 5 walls + 20% gyroid, as in v6. Don't go heavier: more plastic means more shrink force. |
| Plate | One piece per print. |
| Elephant-foot compensation | 0.15–0.20 mm, so the cut faces have no lip and the seams close tight. |

The other v6 settings still apply:
- 0.2 mm layers with a 0.4 mm nozzle;
- the seam on the underside;
- lower bed (Y) acceleration, about 1,500–2,000 mm/s², for the upper half of the print;
- the files put the long chord along the bed's Y axis, so don't rotate them.

**Keys:** print in the same material at 100% infill, flat on the large face. Test-fit one key before printing the set. If it's tight, sand the key's flanks lightly; don't touch the pockets.

Material for the set is about the same as v6: roughly 2.3 kg in PETG or 1.9 kg in ASA with 5 walls and 20% gyroid.

## Assembly

1. Remove the brim, then lightly sand the cut faces flat. Dry-fit the 4 pieces and the 6 keys on the car, with cling film on the paint.
2. Glue the centre seam first, LEFT_MID to RIGHT_MID:
   - Spread adhesive on both cut faces and push the pieces together on the car (or on a matching jig), so the top surfaces line up.
   - Put glue in the two pockets and on the keys, then press the keys in from underneath until they are flush.
   - Adhesive: for ASA, ABS/ASA slurry in acetone or a structural methacrylate. For PETG, a 2K epoxy or methacrylate.
3. Once that has set, add LEFT_END and then RIGHT_END the same way, one seam at a time.
4. Fill and sand the three seam lines on top, then prime and paint.
5. Mount as for v6:
   - Clean with IPA, use 3M 94 primer, and use VHB 5952 (or automotive tape ≥ 1.1 mm) on the underside.
   - Run the tape continuously along the front edge and under the fins.
   - Install at 15–25 °C and leave it 72 h before washing or highway use.

## Limits

- There are three seams to fill and sand instead of two, and one of them is on the centre line of the car.
- The underside still follows the car model from VW dimension data, including the roof-edge bend at z ≈ 177–188 mm. It is not a scan, so dry-fit before bonding.
- The ends of the rear lip next to the fins keep their original notch shape. That is a design feature, not a step.
- The two thin blades (front and rear edges, 3–10 mm thick) are joined by the glued butt face only. The bow-tie keys sit in the thick roof-contact zone, because there is no room for a pocket in the blades.
