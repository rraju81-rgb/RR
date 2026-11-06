# F1 front wing — 4 print files for a 420 × 420 × 450 mm printer

Your split model (`f1+wing+with+rings+removed+FINAL_stls`: 43 printable parts plus 6 rings)
was reassembled digitally and merged into four print files. **All four are scaled to 52 %** so
that every file fits a **420 × 420 × 450 mm** build volume. They are oriented ready to print.

| # | File (`stl/`) | Size on the bed | Original parts in it |
|---|---|---|---|
| 1 | `1_body.stl` | 119 × 118 × **435** mm (standing) | obj_3 (tip), 2, 39, 40, 1 (rear) |
| 2 | `2_left_wing.stl` | 274 × 270 × 42 mm | obj_10, 36, 35, 9, 32, 31, 7, 23, 24, 6, 26, 25 + left halves of obj_20, 4, 5 |
| 3 | `3_right_wing.stl` | 277 × 280 × 41 mm | obj_27, 28, 13, 29, 30, 14, 33, 34, 43, 37\*, 38, 42 + right halves of obj_20, 4, 5 |
| 4 | `4_end_plates.stl` | 214 × 135 × 38 mm (both plates) | left: obj_11 + 12 · right: obj_16 + 41 |

\* obj_37 was never uploaded. It was rebuilt as the mirror image of its twin, obj_25 (see below).

Every file was re-loaded the way a slicer does: watertight, no non-manifold edges, one solid per
piece (two in the end plate file), and no hairline gaps left from the old joints.

Left and right are as the driver sees them. The lowest wing element (the main plane) is at the
front.

## Printing

* **Body:** stand it on its rear opening, tip up, as it is in the file. That way nothing needs
  supporting inside the hollow nose. Use a brim, because it is 435 mm tall with a ~3.2 mm wall.
  The very tip may want light supports.
* **Wings and end plates:** these lie flat. The aerofoils and the end plate stubs are curved,
  so use supports (tree or organic supports work well).
* Wall thickness at 52 %: body ≈ 3.2 mm, wing elements ≈ 3–4.8 mm, end plates ≈ 2.4–4.4 mm.
* The two wing halves meet at the centre line, under the nose. Glue them there, glue the end
  plates onto the wing tips (the stubs mate with the element ends exactly as before), then glue
  the nose on top.
* The small extras that are not part of these four files (obj_8, 19, 15, 17, 18, 21, 22 and the
  6 `Ring_F1-006`) are unchanged. Print them from your original files **at 52 %** so they match.

## What changed compared with the original parts

* **Joints filled:** the tabbed joints had 0.1–0.4 mm fit clearance. Those gaps were filled, so
  each file prints as one solid with no seam gaps.
* **Wing split in two:** the three full-width elements were cut on the car's centre line (through
  the middle of centre pieces obj_4, 5 and 20) to give separate left and right wings. The top
  flap already stops about 10 cm either side of the centre in the original design, where the
  nose sits.
* **Webs:** the four wing elements never touched each other. Each wing half now has 6 small webs
  (5 mm thick at full size, about 2.6 mm at 52 %), 15 cm and 44 cm from the centre, that tie its
  elements into one rigid piece.
* **obj_37 rebuilt:** the missing top-flap piece is the twin of obj_25. Its mirror image fits
  onto obj_38 with 99.2 % cross-section overlap and a 0.4° surface kink, so the joint is
  seamless.
* **Nose base:** the nose's rear rim was uneven by 3.3 mm. 3.2 mm was trimmed off at full size
  (1.7 mm at 52 %) so the whole rim sits flat on the bed.

## Other printers / scales

`stl/full_size/` holds the same pieces at 100 % (your original size), lying flat:
`1_body.stl` (untrimmed), `2_left_wing.stl`, `3_right_wing.stl`, `4a_end_plate_left.stl`,
`4b_end_plate_right.stl`. To repackage for another build volume, run from the working folder
of the pipeline below:

```
python3 tools/package_build_volume.py --bed X Y Z --full stl/full_size --out <folder>
```

It picks the largest common scale that fits (the standing nose is usually the limit).

## How it was made (`tools/`)

The parts had been exported in print orientation (laid out on slicer plates), so they were
first put back together:

1. **Cut faces:** every flat, sharp-edged face that crosses a part is a joint candidate
   (`faces.py`, `ends.py`).
2. **Matching:** the ends of each part are compared in 2D against mirror-image ends of the
   other parts, including tab/notch fit. Each candidate is then scored by whether the skin
   surface continues across the cut (`run_endmatch.py`, `stub_links2.py`). True joints show
   < 0.3° of kink; false ones 4–36°.
3. **Exact alignment:** both sides of a cut share boundary vertices, so each joint is refined
   by ICP (`refine_joints.py`). A global least-squares fit over all joints then closes the loops
   through the two end plates (`solve_poses.py`; the worst joint is off by 0.03 mm).
4. **Merging:** pieces are boolean-unioned with manifold3d, with the clearance slits filled and
   healed (`merge.py`, `finalize.py`, `export_all.py`). The wing halves, webs and the rebuilt
   obj_37 come from `build_left_right.py`. Final scaling and orientation is done by
   `package_build_volume.py`.

Run order, from an empty working folder, with `F1_PARTS_DIR` pointing at the original STLs:
`match_all.py`, `run_endmatch.py`, `assemble.py`, `refine_joints.py`, `stub_links2.py`,
`solve_poses.py`, `make_bridges.py`, `export_all.py`, `build_left_right.py`, then
`package_build_volume.py`. Requires `trimesh`, `manifold3d`, `shapely`, `scipy`, `numpy`.
