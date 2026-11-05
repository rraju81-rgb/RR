# F1 front wing — 3-piece version

The original split model (`f1+wing+with+rings+removed+FINAL_stls`: 43 printable parts
`obj_1 … obj_43` plus 6 × `Ring_F1-006`) was reassembled digitally and merged into
the three sections from the colour-coded photos:

| Section | File | Made from original parts | Size at 100 % |
|---|---|---|---|
| **Body** (red) | `stl/1_body_RED.stl` | obj_3 (tip) → 2 → 39 → 40 → 1 (rear) | 849 × 227 × 185 mm |
| **Wings** (green) | `stl/2_wing_GREEN.stl` — **waiting for obj_37** | 4 full-width elements, 27 parts (see below) | ≈ 1113 × 511 × 99 mm |
| **End plate** (blue) | `stl/3_endplate_A_BLUE.stl` | obj_11 + obj_12 | 259 × 193 × 67 mm |
| **End plate** (blue) | `stl/3_endplate_B_BLUE.stl` | obj_16 + obj_41 | 250 × 203 × 72 mm |

Wing elements (each runs the full width, passing under the nose):

| Element | Parts, end plate A → end plate B |
|---|---|
| 1 | obj_10, 36, 35, **20**, 27, 28, 13 |
| 2 | obj_9, 32, 31, **4**, 29, 30, 14 |
| 3 | obj_7, 23, 24, **5**, 33, 34, 43 |
| 4 | obj_6, 26, 25, **37 (missing)**, 38, 42 |

End plate A takes the element ends obj_6 / 7 / 9 / 10, end plate B takes obj_13 / 14 / 42 / 43.
The two end plates are mirror images of each other, so print one of each.

Every merged piece is a single watertight solid (checked after re-loading the STL the way a
slicer does: no open edges, no non-manifold edges, one body).

## Not included (unchanged)

These parts have no cut face that matches anything; they are glued-on extras, so print them
from your original set if you use them: obj_8 & obj_19 (pair), obj_15 & obj_17 (pair),
obj_18, obj_21, obj_22 and the six `Ring_F1-006` (obj_44–49).

## Choosing a scale

The STLs are the same size as your original parts. **Scale all three sections by the same
percentage** in the slicer so the end plates and body still fit the wing:

| Printer bed | Largest scale (the wing is the limit) | Wing span / nose length |
|---|---|---|
| 220 × 220 × 250 (Sovol SV06) | 23 % | ≈ 26 cm / 20 cm |
| 256 × 256 × 256 (Bambu A1 / P1 / X1) | 26 % | ≈ 29 cm / 22 cm |
| 300 × 300 × 340 (Sovol SV06 Plus) | 31 % | ≈ 35 cm / 26 cm |

These assume the piece lies flat and is rotated on the bed; tilting the wing can gain a few
percent. Wall thickness at 100 %: body 6.2 mm, wing elements 6–9 mm, end plates 5–8.5 mm. At
23 % the thinnest wall, the body, is about 1.4 mm (3 perimeters with a 0.4 mm nozzle). All
pieces have curved overhangs, so print with supports.

## What changed compared with the original parts

* **Joints filled.** The castellated / tabbed joints had 0.1–0.4 mm fit clearance on the tab
  sides. Those slits were filled so each section prints as one solid with no seam gaps.
* **Wing webs.** The four wing elements never touch each other (3–9 mm slot gaps); in the
  original they were held together only by the end plates. Small 5 mm thick webs (at 100 %)
  now tie neighbouring elements together, so the wing is one rigid piece: 3 webs near each
  end plate, where real F1 wings have slot-gap separators, and 2 at the centre under the
  nose.
* All other geometry is the original. The end plate stubs still meet the wing element ends
  exactly as before.

## How it was made (`tools/`)

The parts had been exported in print orientation (laid out on slicer plates), so they were
first put back together:

1. **Cut faces.** Every flat, sharp-edged face that crosses a part is a joint candidate
   (`faces.py`, `ends.py`).
2. **Matching.** The ends of each part are compared in 2D against mirror-image ends of the
   other parts, including tab/notch complementarity, and scored by whether the skin
   surface continues across the cut (`run_endmatch.py`, `stub_links2.py`). True joints
   score < 0.3° of skin kink; false ones 4–36°.
3. **Exact alignment.** Both sides of a cut share boundary vertices, so each joint is
   refined by ICP on those vertices (`refine.py`). Then a global least-squares fit over all
   joints closes the loops through the two end plates (`solve_poses.py`; worst joint
   residual 0.03 mm).
4. **Merging.** The groups are boolean-unioned with manifold3d, with clearance slits filled
   and healed (`merge.py`, `finalize.py`). The wing webs come from `bridges.py`. The result
   is oriented on its most stable resting face and exported (`export_all.py`).

To re-run: put the original STLs in a folder, then from `tools/` run
`F1_PARTS_DIR=<folder> python3 <script>.py` in this order: `match_all.py`, `run_endmatch.py`,
`assemble.py`, `stub_links2.py`, `solve_poses.py`, `bridges.py`, `export_all.py`.
Requires `trimesh`, `manifold3d`, `shapely`, `scipy` and `numpy`.
