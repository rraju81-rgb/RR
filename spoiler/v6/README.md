# Polo Oettinger-style roof spoiler v6: 3 solid pieces with bow-tie keys

Built from `spoiler/input/v5_TOP.stl` + `v5_BOTTOM.stl`, in the same car coordinates and origin:
X is the width of the car, Y is up, +Z points to the rear. The overall size is unchanged at 1,300 × 147 × 292 mm.

## What changed from v5

| You asked for | What v6 does |
|---|---|
| **1 cm thick** | The part is now **solid**: one body, with no hollow cavity and no separate bottom plate. The spoiler is only 19 mm thick at its thickest, so 10 mm walls from the top and the bottom would meet in the middle. Wall count and infill are set in the slicer (see below). |
| **3 pieces instead of 4** | It is cut at x = ±216.7 mm into LEFT, CENTRE and RIGHT pieces, each 433 mm long. Each one stands on its cut face on the Kobra 3 Max (420 × 420 × 500 mm). |
| **Steps on the top of the back part, keep it flat** | v5 had a step line running the full width across the top surface of the rear part (z ≈ 170–182 mm). It was up to **0.95 mm** high, left over from v5's hollow construction. It has been smoothed into the surrounding surface over a 60 mm wide band, and the shape on either side is unchanged. The stepped glue ledges where the old bottom plate sat are also gone, because the part is now one solid piece. See `docs/v6_rear_step_before_after.png`. |
| **Bow-tie locking** | Each seam has 2 bow-tie (double-dovetail) keys in pockets on the hidden underside, where the part is 13–19 mm thick. All 4 keys are identical. They drop in from below and finish flush with the underside, so the roof tape covers them. |

## Files

`print/` holds bed-ready files, already oriented and centred on a 420 × 420 mm bed:

| File | Qty | Print size (mm) | Orientation | Supports |
|---|---|---|---|---|
| `v6_LEFT_end_piece.stl` | 1 | 155 × 287 × 433 | Standing on its cut face, fin at the top | Tree supports, build plate only, 55° threshold. About 31 cm² on the inner face of the fin and the underside of the fin root, 225–433 mm up. |
| `v6_CENTRE_piece.stl` | 1 | 46 × 269 × 433 | Standing on its left cut face | None |
| `v6_RIGHT_end_piece.stl` | 1 | 155 × 287 × 433 | Standing on its cut face, fin at the top | As for LEFT |
| `v6_BOWTIE_KEY_x4.stl` | 4 (+2 spare) | 56 × 23 × 6.25 | Flat, car-side face on the bed | None |
| `v6_BOWTIE_KEYS_plate_of_6.stl` | 1 plate | 180 × 53 × 6.25 | 6 keys on one plate | None |

`assembled/` holds the same parts in car coordinates (`L`, `C`, `R`, `KEY_1`–`KEY_4`). Load them together in the slicer to check the assembly.

`docs/` holds the renders, the key drawing and the before/after of the step. The scripts are on the GitHub branch in `spoiler/v6/src/`: running `sh v6/src/run_all.sh` from `spoiler/` rebuilds everything from the v5 STLs in about a minute.

## Checks on the delivered files

- Every part is one closed, watertight body with consistent winding, **zero self-intersections** and no zero-area faces.
- Each key sits in its pocket with **0.15 mm clearance on every side** and no overlap with either piece. There is a 0.25 mm glue gap at the pocket floor.
- The key's outer face is flush with the underside to within **±0.08 mm**.
- The skin left above each pocket floor is at least **6.5 mm** for the front keys and **9.7 mm** for the rear keys.
- The three pieces put back together reproduce the solid spoiler exactly. The only material missing is the 22 cm³ of the four pockets, which the keys fill.
- Every piece fits a 420 × 420 × 500 mm volume with at least 66 mm spare in height.

## Printing (Kobra 3 Max)

- **Material:** ASA is the best choice, because a roof gets hot in the sun. PETG works. **Don't use PLA**, which softens at around 55–60 °C.
- **Walls and infill:** the part is thin, so walls make up most of the volume.

  | Setting | Use | Material for the set (+30 g of keys) |
  |---|---|---|
  | 5 walls + 20% gyroid | Good default | about 2.3 kg PETG / 1.9 kg ASA |
  | 8 walls + 30% gyroid | Extra stiff | about 3.3 kg PETG / 2.7 kg ASA |
  | 100% solid | | about 3.7 kg PETG / 3.2 kg ASA |

- **Layers:** 0.2 mm layers, 0.4 mm nozzle. Turn on elephant-foot compensation (0.15–0.2 mm), so the cut faces don't get a lip and the seams close tight.
- **Placement:** the pieces are 433 mm tall and narrow.
  - Use a 12–15 mm brim and print one piece at a time.
  - The files already put the long chord along the bed's Y axis, which is the direction a bed-slinger moves. Don't rotate them.
  - Lower the bed (Y) acceleration to about 1,500–2,000 mm/s² for the upper half of the print.
- **Seam:** place the seam on the underside (the face that sits on the car).
- **Keys:** print in the same material, 100% infill, flat on the large face. Test-fit one key before printing the set. If it's tight, sand the key's flanks lightly; don't touch the pockets.

## Assembly

1. Remove the brim, then lightly sand the cut faces flat. Dry-fit the 3 pieces and the 4 keys on the car, with cling film on the paint.
2. Glue CENTRE + LEFT first:
   - Spread adhesive on both cut faces and push the pieces together on the car (or on a matching jig), so the top surfaces line up.
   - Put glue in the two pockets and on the keys, then press the keys in from underneath until they are flush.
   - Adhesive: for ASA, ABS/ASA slurry in acetone or a structural methacrylate. For PETG, a 2K epoxy or methacrylate.
3. Glue RIGHT the same way once the first joint has set.
4. Fill and sand the two seam lines on top, then prime and paint.
5. Mount as before:
   - Clean with IPA, use 3M 94 primer, and use VHB 5952 (or automotive tape ≥ 1.1 mm) on the underside.
   - Run the tape continuously along the front edge and under the fins.
   - Install at 15–25 °C and leave it 72 h before washing or highway use.

## Limits

- The underside still follows the car model from VW dimension data, including the roof-edge bend at z ≈ 180–188 mm. It is not a scan, so dry-fit before bonding.
- The ends of the rear lip next to the fins keep their original notch shape. That is a design feature, not a step.
- The two thin blades (front and rear edges, 3–10 mm thick) are joined by the glued butt face only. The bow-tie keys sit in the thick roof-contact zone, because there is no room for a pocket in the blades.
