# Polo Oettinger-style roof spoiler v8: 6 pieces, no supports

v8 is v7 with each **end piece split in two along its length**, as marked: a front half (with the fin tip) and a rear half. The two middle pieces are the same as v7 apart from one key pocket at each outer end (see Keys). The shape, the underside and the car coordinates are the same as v6 and v7: X is the width of the car, Y is up, +Z points to the rear. The overall size is still 1,300 × 147 × 292 mm.

## Why the split helps

Each half has a flat cut face, and it prints lying on that face:

| Left or right end piece | v7, one piece | v8 front half | v8 rear half |
|---|---|---|---|
| Print height | 325 mm | **134 mm** | **155 mm** |
| Area on the bed | 25 cm² | **31 cm²** | **31 cm²** |
| Supports | 79 cm² under the fin | **none** | **none** (only 6.5 mm bridges over the key pockets) |
| Volume | 673 cm³ | 306 cm³ | 357 cm³ |

The whole spoiler now prints **without supports**. The middle pieces still stand 325 mm tall on their centre-seam face, as in v7, and need none either.

## Where the cut is

- **The cut is the flat plane z = 100 mm.** It runs from the middle of each end piece's seam face, straight out along the piece, and leaves through the fin's rear edge at |x| = 592 mm.
- **Why there:** the four lines you drew agree on that path but wander across the chord, between z = 30 and z = 165 mm. Averaged along the length, they sit at z = 80–100 mm. z = 100 is in that band, stays 11 mm clear of the seam's front key pocket, and cuts where the part is 12–16 mm thick.
- **Comparison:** see `docs/v8_cut_vs_marks.png`, which shows your lines against the cut from the same viewpoints you drew on.
- **To move the cut:** change `CUT_Z` in `src/layout.py` and run `sh v8/src/run_all.sh`.

## Files

`print/` holds bed-ready files, already oriented and centred on a 420 × 420 mm bed:

| File | Qty | Print size (mm) | On the bed | Supports |
|---|---|---|---|---|
| `v8_1F_LEFT_END_FRONT.stl` | 1 | 80 × 350 × 134 | Flat cut face | None |
| `v8_1R_LEFT_END_REAR.stl` | 1 | 59 × 283 × 155 | Flat cut face | None |
| `v8_2_LEFT_MID.stl` | 1 | 48 × 272 × 325 | Centre-seam face | None |
| `v8_3_RIGHT_MID.stl` | 1 | 48 × 272 × 325 | Centre-seam face | None |
| `v8_4R_RIGHT_END_REAR.stl` | 1 | 59 × 283 × 155 | Flat cut face | None |
| `v8_4F_RIGHT_END_FRONT.stl` | 1 | 80 × 350 × 134 | Flat cut face | None |
| `v8_BOWTIE_KEY_x8.stl` | 8 (+2 spare) | 56 × 23 × 6.25 | Flat, car-side face down | None |
| `v8_BOWTIE_KEY_THIN_x2.stl` | 2 (+2 spare) | 56 × 23 × **3.75** | Flat, car-side face down | None |
| `v8_BOWTIE_KEYS_plate_10_standard_4_thin.stl` | 1 plate | 242 × 113 × 6.25 | All keys plus spares on one plate: 10 standard in the first three rows, 4 thin in the last row | None |

Print either the two key files or the plate, not both. The standard key is the same as in v6 and v7, so standard keys you have already printed fit. The thin key has the same bow-tie outline and is only 3.75 mm thick. It goes in the two shallow pockets where the front halves meet the middle pieces (see Keys below).

A front half and a rear half fit on the bed together, if you'd rather print one end in a single job.

`assembled/` holds the 6 pieces and 10 keys in car coordinates, in their fitted positions. Load them together in the slicer to check the assembly.

`docs/` holds the figures:
- the assembled views;
- your lines against the cut;
- the exploded underside;
- a close-up of the new lengthwise joint;
- the end piece's inner end in your slicer view, with one key into each half (`v8_end_piece_keys.png`);
- the bed layouts;
- the v7-versus-v8 end piece.

`src/` holds the scripts. Running `sh v8/src/run_all.sh` from `spoiler/` rebuilds everything in under a minute. `data/` keeps your marked images and the lines traced from them in 3D.

## Keys

There are **10 bow-tie keys: 8 standard and 2 thin**. Every key sits on the hidden underside, under the mounting tape.

| Joint | Keys | Position |
|---|---|---|
| Centre seam (left middle to right middle) | 2 standard | z = 132 and 165 mm, as v7 |
| Each outer seam (end piece to middle piece) | 1 standard into the **rear half** | z = 161 mm, as before |
| | 1 **thin** into the **front half** (new) | z = 80 mm |
| Each end piece's lengthwise cut (front half to rear half) | 2 standard | \|x\| = 400 and 430 mm |

**Outer seams, as you marked them.** In the first v8 both keys at each outer seam (z = 123 and 161 mm) were in the rear half, so the front half was held to the middle piece by glue only. The key at z = 123 is gone. Its replacement is in the front half, so each half of the end piece now has its own key into the middle piece. `docs/v8_end_piece_keys.png` shows this from the same viewpoint as your screenshot.

**Why the front-half key is thin, and why it sits at z = 80.**
- The front of the spoiler is thin there: 9 mm at the middle of your green mark (z ≈ 70 mm) and about 13 mm at the cut.
- A standard key's 6.5 mm pocket would leave only 1–2.5 mm of plastic between the pocket and the painted top surface, wherever it went in the front half.
- The thin key has the same bow-tie outline in a 4.0 mm pocket. At z = 80 it leaves at least 4.0 mm over the pocket, and the pocket stays 7.8 mm clear of the cut between the halves.
- At the middle of your mark, even the thin pocket would leave only about 3 mm. So z = 80 is the closest to your mark that the plastic allows.

**Lengthwise cuts:** |x| = 400 and 430 mm. Further in, the front half is too thin over the pocket. Further out, the underside bends towards the fin, so a key wouldn't sit flush.

## Checks on the delivered files

- Every part is one closed, watertight body with consistent winding, **zero self-intersections** and no zero-area faces. This was checked on the bed-ready files as written, too.
- Each key sits in its pocket with **0.15 mm clearance** to exactly the two pieces it joins, and no overlap. There is a 0.25 mm glue gap at the pocket floor.
- Every key's outer face is flush with the underside to within **±0.12 mm**.
- The material left over each pocket is at least:
  - **6.8 mm** for the standard keys at the cross seams;
  - **4.0 mm** for the thin keys;
  - **4.6 mm** at the lengthwise cuts.
- The six pieces put back together reproduce the solid spoiler exactly. The only material missing is the 52 cm³ of the ten pockets, which the keys fill.
- Every piece fits a 420 × 420 × 500 mm volume.

## Printing

- **Supports:** turn them off. Your slicer may flag the key pockets. They print without support:
  - on the rear halves, 6.5 mm bridges;
  - near the inner end of the front halves, a 4 mm bridge (the thin key's pocket).
- **Brim:** 8–10 mm is enough for the halves, because they are low. Use 15–20 mm for the 325 mm middle pieces, as in v7.
- **Elephant-foot compensation:** 0.15–0.2 mm. The bed face of every piece is a glue face.
- **Material and anti-warp settings:** as in `../v7/README.md`:
  - ASA only inside an enclosure on the open Kobra 3 Max;
  - PETG prints fine in the open;
  - first layer 0.25–0.30 mm and slow, part fan off for ASA;
  - 5 walls + 20% gyroid;
  - 0.2 mm layers, seam on the underside.
- **Keys:** print in the same material at 100% infill, flat on the large face. Test-fit one of each kind before printing the set. If one is tight, sand the key's flanks lightly; don't touch the pockets.

Material is the same as v7: roughly 2.3 kg in PETG or 1.9 kg in ASA with 5 walls and 20% gyroid.

## Assembly

1. **Each end first:**
   - Lightly sand the two cut faces flat and dry-fit the front half to the rear half with its two keys.
   - Spread adhesive on both cut faces and press the halves together. The top surfaces must line up along the whole cut.
   - Put glue in the two pockets and on the keys, then press the keys in from underneath until flush.
   - Let it set. Each end is now one piece, like the v7 end piece.
   - Adhesive: for ASA, ABS/ASA slurry in acetone or a structural methacrylate. For PETG, a 2K epoxy or methacrylate.
2. **Centre seam:** glue LEFT_MID to RIGHT_MID with its two keys, on the car or on a matching jig.
3. **The ends:** add the left end, then the right end, to the middle, one seam at a time.
   - Each outer seam has two keys: a standard key in the rear half's pocket, and a **thin key** in the front half's shallow pocket.
   - A standard key in the shallow pocket would stand 2.5 mm proud, so you can't mix them up unnoticed.
4. **Finish:** fill and sand the seam lines on top (three across and two lengthwise), then prime and paint.
5. **Mount as for v6 and v7:**
   - Clean with IPA, use 3M 94 primer, and use VHB 5952 (or automotive tape ≥ 1.1 mm) on the underside.
   - Run the tape continuously along the front edge and under the fins.
   - Install at 15–25 °C and leave it 72 h before washing or highway use.

## Limits

- There are five seams to fill and sand instead of three. The two lengthwise seams run along the top of the end pieces and down the fins.
- The lengthwise joints rely mostly on glue: about 280 mm of cut face, 10–16 mm wide, plus two keys. The fin part of the cut is glued only, because the fin is too thin for a key.
- The front halves meet the middle pieces at the thin front blade. That joint has only a thin key (3.75 mm instead of 6.25 mm), because the plastic is 9–12 mm thick there.
- The underside still follows the car model from VW dimension data. It is not a scan, so dry-fit before bonding.
