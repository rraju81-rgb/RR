> **Everything below is inside [`HotWheels_Racks_All_Designs_and_Models.zip`](HotWheels_Racks_All_Designs_and_Models.zip) in this folder (52.9 MB).** Unzip it and open `OVERVIEW.pdf` first: it is this index with a picture of every design.

# Hot Wheels racks: all designs and models

Every Hot Wheels rack and stand designed in six Claude Code sessions between 30 Sep and 6 Oct 2026, gathered from six branches of `rraju81-rgb/RR` into one archive, `HotWheels_Racks_All_Designs_and_Models.zip`. It holds 982 files (473 STL models plus drawings, renders, documents and build scripts) in 7 folders, plus this index, `OVERVIEW.pdf` (the same index with a picture of every design) and `MANIFEST.csv` (where each file came from).

Nothing was redesigned or regenerated: every file is a byte-for-byte copy of its version in git (the branch tip, or for folder 7 the commit just before it was deleted). Each folder keeps its source's layout, so the build scripts inside still run.

## Start here: the three products in the 2026 catalogue

| Product | What it is | Print these | Drawings and sales |
|---|---|---|---|
| **PITLANE GARAGE** (sales kit: SWING) | Lift-off wall rack, 6 cars, right- and left-hand | `2_PITLANE_wall_racks/liftoff/right_wall_body_PRINT.stl` + `right_ledges_all_6_PRINT.stl` (`left_…` for the twin) | `2_PITLANE_wall_racks/blueprint/blueprint.pdf`, `2_PITLANE_wall_racks/marketing/sales_pitch.pdf` |
| **PITLANE GRID** (sales kit: SLIDE) | Fixed slide-in wall rack, 6 cars, right- and left-hand | `2_PITLANE_wall_racks/fixed/right_fixed_rack_PRINT.stl`, `left_fixed_rack_PRINT.stl` | same as GARAGE |
| **PITLANE PODIUM 3 / 5 / 6** (SlideRack Fold) | Tabletop rack with a print-in-place kickstand | `3_SlideRack_wall_tabletop_PODIUM/3d-models/right_fixed_rack_{3,5,6}card_kickstand_PRINT.stl` | `3_SlideRack_wall_tabletop_PODIUM/pitch/SlideRack_Fold_Blueprint.pdf`, `SlideRack_Fold_Pitch.pdf` |

The customer catalogue for all three is `1_PITLANE_catalogue_2026/PITLANE_Catalogue_2026.pdf`.

## Folders

| Folder | What's inside | Files | Came from |
|---|---|---|---|
| `1_PITLANE_catalogue_2026/` | The customer catalogue and product renders for the three current products: GARAGE, GRID and PODIUM. | 35 (11.2 MB) | `claude/blissful-euler-vesn65`, 6 Oct 2026 |
| `2_PITLANE_wall_racks/` | GARAGE (lift-off) and GRID (fixed) wall racks, the fused one-piece rack, the strip + hinge-clip system v13, earlier clip/modular/v2 systems, blueprints and the sales kit. | 294 (36.0 MB) | `claude/great-goodall-ea8ddx`, 2–6 Oct 2026 |
| `3_SlideRack_wall_tabletop_PODIUM/` | PODIUM 3/5/6 (SlideRack Fold), the SlideRack wall racks and table feet, every tabletop stand and easel version, the SlideRack pitches, blueprint and project report. | 229 (27.3 MB) | `claude/sleepy-davinci-i3wfex`, 4–6 Oct 2026 |
| `4_card_easel_5tier/` | A one-hinge, print-in-place 5-card easel. | 6 (1.4 MB) | `claude/epic-hopper-bpk2z8`, 5 Oct 2026 |
| `5_car_groove_wall_rack/` | The original 6-slot rack rebuilt with 36 mm grooves for loose (uncarded) cars. | 4 (0.3 MB) | `claude/wizardly-pascal-2uqtgr`, 4 Oct 2026 |
| `6_early_concepts/` | The first designs: side-slide shingle rack, lift-off tray, fold-down linkage rack, side-mechanism racks, accordion hook rack and flat-fold hook tiles. | 374 (42.4 MB) | `claude/hot-wheels-stand-redesign-5ga25n`, 30 Sep – 1 Oct 2026 |
| `7_rejected_FanOut_rack_v2/` | The rail-guided accordion rack and its brochure, deleted from its branch as rejected. Kept here so the archive is complete. | 40 (4.6 MB) | `claude/hot-wheels-stand-redesign-5ga25n`, 1 Oct 2026 |

Status labels used below: **In 2026 catalogue**: one of the three products in the PITLANE 2026 catalogue; **Alternative**: finished design that is not in the catalogue; **Superseded**: replaced by a later design; kept for reference; **Early concept**: first-week concept, before the PITLANE and SlideRack lines; **Rejected**: rejected and deleted from its branch; kept so nothing is lost; **Documents**: catalogue, drawings or sales material; **Your reference files**: files you supplied that later designs were built from.

## Every design, folder by folder

### 1. PITLANE 2026 catalogue (`1_PITLANE_catalogue_2026/`)

From `claude/blissful-euler-vesn65`, 6 Oct 2026. 35 files. Paths below are inside this folder.

**PITLANE 2026 catalogue** · _Documents_  
10-page A4 customer catalogue: cover, range overview, product spreads, bundles, fit guide and how to order. Renames the products: SWING → GARAGE, SLIDE → GRID, SlideRack Fold → PODIUM.  
13 annotated renders (2400 × 1800) plus clean JPG versions for listings and ads; Three.js source to re-render.  
Files: `PITLANE_Catalogue_2026.pdf`, `images/`, `images/clean/`, `README.md`

### 2. PITLANE wall racks (`2_PITLANE_wall_racks/`)

From `claude/great-goodall-ea8ddx`, 2–6 Oct 2026. 294 files. Paths below are inside this folder.

**PITLANE GARAGE (sales kit: SWING), lift-off wall rack, right + left** · _In 2026 catalogue_  
Each ledge drops onto its own hinge pin and lifts off to swap a card. Right- and left-hand versions mount back to back (left one 27.5 mm lower) as a 12-car twin.  
6 cars per rack · 350 mm wall mount, 20 mm spine · 55 mm pitch · opens to 135°, stops 3° past closed · remove a ledge: close, lift 15.5 mm, pull.  
Files: `liftoff/right_wall_body_PRINT.stl`, `liftoff/right_ledges_all_6_PRINT.stl`, `liftoff/right_ledge_1_PRINT.stl`, `liftoff/left_wall_body_PRINT.stl`, `liftoff/left_ledges_all_6_PRINT.stl`, `liftoff/pair_assembled_demo.stl`, `liftoff/README.md`

**PITLANE GRID (sales kit: SLIDE), fixed slide-in wall rack, right + left** · _In 2026 catalogue_  
The same rack with no hinges: ledges are solid with the wall mount and cards slide in from the open end (from the right on the right-hand rack, from the left on the left-hand one).  
6 cars per rack · 350 mm · one print each, lying on the spine's flat back edge · 3 mm screw holes · twin: back to back, left rack 27.5 mm lower.  
Files: `fixed/right_fixed_rack_PRINT.stl`, `fixed/left_fixed_rack_PRINT.stl`, `fixed/pair_assembled_demo.stl`, `fixed/README.md`

**Fused one-piece rack with print-in-place hinges** · _Alternative_  
Spine, knuckles and pins are one solid; each ledge turns on a 5 mm pin. Two snap-off tabs per ledge hold it while printing, then break free on the first swing. Not in the catalogue.  
130 × 350 × 36.9 mm · 6 ledges, 55 mm pitch · opens to 120° · print the _PRINT file on its left side, brim, no supports.  
Files: `fused/pitlane_fused_rack_PRINT.stl`, `fused/pitlane_fused_rack.stl`, `fused/README.md`

**Strip + hinge-clip system v13 (kits for 2–7 cars, 14-car column)** · _Superseded_  
A 40 cm wall strip with hook lips; a hinge clip per rack hangs on it with a double L lock and an anti-slip dome, and each ledge swings open. Replaced by GARAGE/GRID in the later sales kit.  
7 cars per 400 mm strip (one piece or two halves with a C-interlock) · 54 mm pitch · clips j0–j6 get deeper per rack so cards shingle · print plates per kit.  
Files: `board/kit_6_cars/`, `board/kit_7_cars/`, `board/column_14_cars_two_strips/`, `board/wall_strip_400.stl`, `blueprint/blueprint_board_v13.pdf`, `build_board.py`

**Zip-tie ratchet clip system (“FINAL system”, kits for 2–6 cars)** · _Superseded_  
Clips slide up a dovetail rail and click one tooth at a time like a zip tie; pull block to release. Came before the strip system above. Generators for earlier clip versions are in legacy/.  
25–27 mm rail strip, dovetail joints · clips j0–j5 with 8 mm pin · simplified ledge.  
Files: `simple/kit_4_cars/`, `simple/wall_strip.stl`, `legacy/build_simple.py`, `legacy/`

**Modular SKADIS-style board with hook-in hinge modules** · _Superseded_  
Slotted board tile plus hook-in hinge-and-latch modules, a pin and a swivel latch bar. Replaced because the hook/latch parts were too fiddly to print.  
140 × 240 × 5 mm board tile (3 racks per tile) · modules j0–j5 step 5.4 mm per rack.  
Files: `modular/`, `build_modular.py`

**v2 racks: thicker frame and hinged door ledges, with latch** · _Superseded_  
The side-slide rack with a thicker frame and countersunk holes, plus a version where every ledge is a door on its own pin, and a latched version with swivel bars.  
3–6 slots plus 2-slot test pieces · 5 mm wall plate · 4 mm hinge pins.  
Files: `v2/rack_6slot_hinged_latch.stl`, `v2/rack_2slot_test_hinged_latch.stl`, `v2/`, `build_v2.py`

**Blueprints and sales kit (GARAGE/GRID and the strip system)** · _Documents_  
blueprint.pdf: 2 × A3 drawings of the SWING (GARAGE) and SLIDE (GRID) racks. sales_pitch.pdf + 5 Meta ads sell those racks in INR. pitch_report.pdf and 5 posters show the older strip system.  
Prices in the sales kit: SLIDE ₹799, SWING ₹1,199 (launch ₹999), SWING twin ₹2,199, SLIDE twin ₹1,449, STL pack ₹499, spare ledge ₹99. Your prototype photos are in marketing/img/.  
Files: `blueprint/blueprint.pdf`, `marketing/sales_pitch.pdf`, `marketing/meta_ad_1.png`, `marketing/pitch_report.pdf`, `marketing/README.md`, `README.md`

### 3. SlideRack: wall, tabletop and PODIUM (`3_SlideRack_wall_tabletop_PODIUM/`)

From `claude/sleepy-davinci-i3wfex`, 4–6 Oct 2026. 229 files. Paths below are inside this folder.

**PITLANE PODIUM 3 / 5 / 6 (SlideRack Fold), tabletop rack with kickstand** · _In 2026 catalogue_  
The GRID fixed rack cut to 3, 5 or 6 ledges with a print-in-place kickstand on the back of the end wall. Folds flat; the leg has two positions, 0° and 35°.  
Heights 132 / 242 / 297 mm · ~103 / 178 / 207 g filament · one print each, end wall down, no supports · leg 80 × 6 mm.  
Files: `3d-models/right_fixed_rack_3card_kickstand_PRINT.stl`, `3d-models/right_fixed_rack_5card_kickstand_PRINT.stl`, `3d-models/right_fixed_rack_6card_kickstand_PRINT.stl`, `pitch/SlideRack_Fold_Blueprint.pdf`, `pitch/SlideRack_Fold_Pitch.pdf`, `3d-models/TABLETOP_STANDS.md`

**SlideRack Wall 6 and Wall Pro (hinged)** · _Alternative_  
Wall 6: six fixed 130 mm ledges, cards slide in from the side. Wall Pro: print-in-place swing-out 134 mm ledges with a backward stop and snap detent. Sold in the SlideRack Wall pitch, not in the catalogue.  
445 mm wall strip · 55 mm pitch, 4.6 mm shingle · 6 mm plate, three 3 mm screw holes · pitch prices Wall 6 ₹499, Wall Pro ₹749.  
Files: `3d-models/rack_6ledge_130_3mmholes.stl`, `3d-models/rack_v2_hinged_134.stl`, `pitch/SlideRack_Wall_Mount_Pitch.pdf`

**Clip-on table feet for the wall racks** · _Alternative_  
Two small feet turn either SlideRack wall rack into a tabletop stand; the rack drops in and lifts straight out again.  
195 × 26 mm each, print flat, 33–60 g · plain and hinged versions · ₹199 in the pitch.  
Files: `3d-models/table_foot_left_plain.stl`, `3d-models/table_foot_right_plain.stl`, `3d-models/table_foot_left_hinged.stl`, `3d-models/table_foot_right_hinged.stl`, `3d-models/TABLE_FEET.md`

**Tabletop set: universal base + 3- and 5-card racks** · _Alternative_  
One base holds either rib-stiffened rack; the racks drop into the slot and lift out. Earlier size-matched bases are included too.  
Base 119 × 141 × 143 mm, 119 g · 3-card stands 175 mm tall, 5-card 250 mm · pitch prices Set 3 ₹799, Set 5 ₹999.  
Files: `3d-models/table_base_universal.stl`, `3d-models/table_rack_3card.stl`, `3d-models/table_rack_5card.stl`, `3d-models/table_base_3card.stl`, `pitch/SlideRack_Tabletop_Pitch.pdf`

**Kickstand easels v6–v11 (3 and 5 cards)** · _Superseded_  
The development line that led to PODIUM. TABLETOP_STANDS.md calls v9 the recommended easel; v10 and v11 came after it, and v11 prints as one piece with a print-in-place hinge like PODIUM's.  
Two leg positions (0° and 35°) · 25–26.5° lean · v8–v10 have a separate leg on a lift-off hinge.  
Files: `3d-models/table_easel_3card_kickstand_v11.stl`, `3d-models/table_easel_5card_kickstand_v11.stl`, `3d-models/table_easel_3card_kickstand_v9_panel.stl`, `3d-models/table_easel_3card_kickstand_v9_leg.stl`

**Folding easels v3–v5 (drawing-pad style)** · _Superseded_  
Panel, hinged base with grooves and a back leg; the groove you choose sets the tilt. v5 has 45° cone-jointed hinges that print without sagging.  
3- and 5-card · 3–4 tilt settings · print-in-place, folded flat on its side.  
Files: `3d-models/table_easel_3card_folding.stl`, `3d-models/table_easel_3card_folding_v5.stl`, `3d-models/table_easel_5card_folding_v5.stl`

**One-sided stands and the first tabletop stands (A easel, B A-frame)** · _Superseded_  
Fixed 15° card face with edge-framed leg and base; stands A and B were the first tabletop designs and are kept for reference.  
One-sided 3-card 119 × 113 × 170 mm, 5-card 119 × 132 × 245 mm · single prints on their side.  
Files: `3d-models/table_onesided_3card.stl`, `3d-models/table_onesided_5card.stl`, `3d-models/table_stand_A_easel.stl`, `3d-models/table_stand_B_aframe.stl`

**Earlier SlideRack wall-rack iterations** · _Superseded_  
The steps from the original 6-slot rack to Wall 6 / Wall Pro: arms lengthened 111 → 126 mm, all six slots as ledges, 3 mm holes and 6 mm plate, first hinged versions, 120 mm ledges.  
See report/SlideRack_Project_Pitch_Report.pdf for the evolution.  
Files: `3d-models/rack_6slot_wide.stl`, `3d-models/rack_5slot_ledge_wide.stl`, `3d-models/rack_6ledge_wide_3mmholes.stl`, `3d-models/rack_v2_hinged_stop_detent.stl`, `3d-models/rack_6ledge_120_3mmholes.stl`, `report/SlideRack_Project_Pitch_Report.pdf`

**Files you supplied as references** · _Your reference files_  
The inputs the SlideRack session built on: your frame holder (converted from FrameHolder.step), your lift-off hinge, the GRID right rack before its 35 cm trim, and the original 6-slot rack with your ledge.  
rack_6slot.stl is the first session's 6-slot side-slide rack (folder 6); ledge.stl is your ledge.  
Files: `3d-models/reference_FrameHolder.stl`, `3d-models/reference_LiftOffHinge.stl`, `3d-models/reference_right_fixed_rack_PRINT.stl`, `3d-models/rack_6slot.stl`, `3d-models/ledge.stl`

### 4. 5-tier folding card easel (`4_card_easel_5tier/`)

From `claude/epic-hopper-bpk2z8`, 5 Oct 2026. 6 files. Paths below are inside this folder.

**5-tier folding card easel (one hinge, print-in-place)** · _Alternative_  
A redesign of the folding easel v3: a 40 mm leg instead of the full-width base, one hinge with a V-stop that sets a 15° lean, and 5 ledges. Not in the catalogue.  
Print footprint 119 × 249 × 25.5 mm, flat, no supports · cards or top-loaders up to 4.5 mm thick.  
Files: `card_easel_5tier_print_in_place.stl`, `card_easel_5tier_preview_standing.stl`, `card_easel.py`, `README.md`

### 5. Car-groove wall rack (`5_car_groove_wall_rack/`)

From `claude/wizardly-pascal-2uqtgr`, 4 Oct 2026. 4 files. Paths below are inside this folder.

**6-slot wall rack with car grooves (loose cars)** · _Alternative_  
The original 6-slot rack rebuilt for uncarded cars: each ledge is a 36 mm groove with a chamfered lip, an end stop and a retaining bump. Left: the original; right: this version.  
Frame 6 mm thick × 20 mm wide (was 3 × 14) · keyholes replaced by 3 mm countersunk holes · 4.6 mm step per slot. No preview came with it; this one was rendered for the overview.  
Files: `rack_6slot_v2.stl`, `build_rack.py`, `source/rack_6slot_original.stl`, `source/ledge.stl`

### 6. Early concepts (`6_early_concepts/`)

From `claude/hot-wheels-stand-redesign-5ga25n`, 30 Sep – 1 Oct 2026. 374 files. Paths below are inside this folder.

**Side-slide shingle rack (2–8 cards)** · _Early concept_  
The first design: every card on its own ledge, shingled 4.6 mm apart, so any card slides out sideways without moving the others. Its 6-slot STL is the “original rack” later sessions started from.  
55 mm pitch · 105 × 165 mm cards · keyhole wall plate · OpenSCAD source side_slide_rack.scad.  
Files: `rack_6slot.stl`, `rack_2slot_test.stl`, `rack_8slot.stl`, `side_slide_rack.scad`, `README.md`

**Lift-off tray version** · _Early concept_  
A U-shaped wall frame with pegs; the side-slide rack hangs on it as a tray that lifts off and lies flat on a table.  
3–6 cards · tray 120 mm wide, frame 145 mm.  
Files: `frame_4slot.stl`, `tray_4slot.stl`, `build_liftoff.py`

**Fold-down stand-up rack (parallelogram linkage, 1–6 stalls)** · _Early concept_  
Cards overlap in a column behind a frame; the frame folds down and every card stands upright. Springs counterbalance it and magnets hold it closed.  
Panel 232–466 mm · full test report in foldout/TEST_REPORT.md.  
Files: `foldout/N4/`, `foldout/TEST_REPORT.md`, `foldout_cad.py`

**Side-mechanism rack (4 printed parts per rack)** · _Early concept_  
The fold-down idea with the mechanism moved into two print-in-place side modules. Replaced by side rack v3 because one part could not print without supports.  
1–6 stalls · open reach 66–302 mm.  
Files: `side/N4/`, `side/TEST_REPORT.md`, `side_cad.py`

**Accordion hook rack (lazy-tongs frame)** · _Early concept_  
A scissor frame on the wall; cards hang from printed pegs and lift straight off. Four printed designs plus wall screws.  
1–6 stalls · pegs 114.5 mm apart open, 40 mm folded.  
Files: `accordion/parts/`, `accordion/N4/`, `accordion/TEST_REPORT.md`

**Side rack v3 (one frame + one swing, bolted hinges)** · _Early concept_  
Three printed parts per rack with M4 bolted hinges and spring counterbalance; prints without supports.  
1–6 stalls; 1–5 fit a 300 mm bed.  
Files: `side3/N4/`, `side3/TEST_REPORT.md`, `side3_cad.py`

**Flat-fold hook tile rack (last design of that session)** · _Early concept_  
One print-in-place tile per card: a thin wall tile with a hook arm that folds flush and swings out 90° to hold a card by its hang hole.  
8 mm tile · no hardware except wall screws · rows of 3 or 5, grids by stacking.  
Files: `foldtile/stl/hook_tile_print.stl`, `foldtile/BOM.md`, `foldtile/TEST_REPORT.md`

### 7. Rejected: FanOut rack (`7_rejected_FanOut_rack_v2/`)

From `claude/hot-wheels-stand-redesign-5ga25n (commit e4ba979, deleted in 4da973e)`, 1 Oct 2026. 40 files. Paths below are inside this folder.

**FanOut card rack (rail-guided accordion, 3 and 5 cars)** · _Rejected_  
A printed wall rail carries a bolted scissor frame; each card hangs from its own hook, and the rail keeps the hooks level as it opens. Deleted from its branch as rejected on 1 Oct 2026; kept here only so nothing is lost.  
3-car and 5-car packages · M4 bolts and nylock nuts · 2-page brochure · QA report (CAD checks only).  
Files: `package/3car/stl/`, `package/5car/stl/`, `brochure/FanOut_Card_Rack_Brochure.pdf`, `QA_REPORT.md`

## Documents

| File | What it is |
|---|---|
| `1_PITLANE_catalogue_2026/PITLANE_Catalogue_2026.pdf` | Customer catalogue: GARAGE, GRID and PODIUM, bundles, fit guide and how to order. (10 pages, A4) |
| `2_PITLANE_wall_racks/blueprint/blueprint.pdf` | Drawings of the SWING (GARAGE) and SLIDE (GRID) racks: twin elevations, operation sequence, hinge and ledge sections. (2 pages, A3) |
| `2_PITLANE_wall_racks/blueprint/blueprint_board_v13.pdf` | Drawings of the strip + hinge-clip system v13. (2 pages, A3) |
| `2_PITLANE_wall_racks/marketing/pitch_report.pdf` | Pitch for the older strip + clip system. (2 pages, A4) |
| `2_PITLANE_wall_racks/marketing/sales_pitch.pdf` | Sales pitch for SWING, SLIDE and the twins, with costs and INR prices. (3 pages, A4) |
| `3_SlideRack_wall_tabletop_PODIUM/pitch/SlideRack_Fold_Blueprint.pdf` | PODIUM drawings: general arrangement per size, hinge detail, specification, print settings and tolerances. (5 pages, A3) |
| `3_SlideRack_wall_tabletop_PODIUM/pitch/SlideRack_Fold_Pitch.pdf` | PODIUM (SlideRack Fold 3/5/6): design, comparison, Indian pricing and go-to-market. (4 pages, A4) |
| `3_SlideRack_wall_tabletop_PODIUM/pitch/SlideRack_Tabletop_Pitch.pdf` | 3- and 5-card racks on the universal base, with Indian market research and pricing. (4 pages, A4) |
| `3_SlideRack_wall_tabletop_PODIUM/pitch/SlideRack_Wall_Mount_Pitch.pdf` | Wall 6, the table feet and the hinged Wall Pro, with Indian market research and pricing. (4 pages, A4) |
| `3_SlideRack_wall_tabletop_PODIUM/report/SlideRack_Project_Pitch_Report.pdf` | Project and pitch report for the SlideRack wall and tabletop line, including the design evolution. (5 pages, A4) |
| `7_rejected_FanOut_rack_v2/brochure/FanOut_Card_Rack_Brochure.pdf` | Brochure for the rejected FanOut rack. (2 pages, A4) |

Each folder's own README is the full design log for that folder: dimensions, what was checked in CAD, what was test-printed and what changed between versions. The longest is `2_PITLANE_wall_racks/README.md`; `3_SlideRack_wall_tabletop_PODIUM/3d-models/TABLETOP_STANDS.md` covers every tabletop design.

## How the designs connect

- The first session's 6-slot side-slide rack (`6_early_concepts/rack_6slot.stl`) is the “original rack” the SlideRack session (folder 3, `3d-models/rack_6slot.stl`) and the car-groove session (folder 5, `source/rack_6slot_original.stl`) started from. The three files are identical.
- SlideRack's Wall 6 rack went to the PITLANE session as `2_PITLANE_wall_racks/fused/reference/rack_6ledge_130_3mmholes.stl` (449 mm tall, before SlideRack trimmed it to 445 mm). The fused, lift-off (GARAGE) and fixed (GRID) racks are all built from it.
- GRID's right-hand rack went back to the SlideRack session as `3d-models/reference_right_fixed_rack_PRINT.stl` (449 mm, before PITLANE trimmed it to 350 mm) and became PODIUM 3 / 5 / 6.
- Your `LiftOffHinge.stl` is in both folders (`2_…/liftoff/reference/`, `3_…/3d-models/reference_LiftOffHinge.stl`): GARAGE and the kickstand easels v8–v10 use its pin and socket.
- The catalogue renames the products: SWING → GARAGE, SLIDE → GRID, SlideRack Fold → PODIUM.

## What was left out

- 3 Python cache files (`.pyc`).
- 8 ZIP files from inside the branches (`accordion_stl.zip`, `foldout_cad_stls.zip`, `side_cad_stls.zip`, `side3_stl.zip`, `foldtile_package.zip`, both `kits_2_to_6_cars.zip`, and FanOut's `rack_v4_sale_package.zip`). Every file in them is already here as a loose file, byte for byte; the one exception, a README in the FanOut package, is an older wording of `7_rejected_FanOut_rack_v2/package/README.md`.
- In-between revisions that a session overwrote or deleted as it went, such as the clip-system iterations of 2 Oct, lift-off rack v1 and the v8 lock pin. Their final forms are here; the in-between versions are still in the git history of their branches (most of them on `claude/great-goodall-ea8ddx`).
- The Flutter app code that shares these branches.

## Checking and rebuilding

`MANIFEST.csv` lists every file with its source branch, commit, original path, git blob SHA-1 and size. `git hash-object <file>` on any file gives its `git_blob_sha1`.

To regenerate models, run a folder's build scripts from inside that folder. Most need `pip install trimesh manifold3d numpy`; some also need `shapely` or `scipy`. The catalogue renders need Node and three.js (see `1_PITLANE_catalogue_2026/README.md`).
