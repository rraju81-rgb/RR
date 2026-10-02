# Side-Slide Shingle Rack: a Hot Wheels stand where any car comes out on its own

## The problem with the current stands
In the reference stands the cards overlap vertically: each card shows only its
car window, and the card above hides its header. The cards are also held by one
shared frame. To take out a card in the middle or at the bottom you have to
remove everything above it.

## Why a pull-straight-out stand can't work
If card *n* is covered at the top by the lower edge of card *n-1*, then card *n*
can't move toward you until *n-1* moves. That is geometry, not a detail. With
the big overlap the reference stands use (55 mm visible out of about 165 mm),
only two fixes work:

1. Remove the overlap, so each card is fully visible. This wastes wall space and
   loses the look of the stack.
2. Stop the cards sharing a plane, and let each one leave in a direction nothing
   blocks. The direction is sideways.

This design takes option 2.

## The concept
```
 side view (z out of the wall)             front view
   wall | card0 card1 card2 ...              +--------+
        |  |     |     |                      | card 7 |  <- top card, frontmost
        |  |  |     |                          |========|  ledge 7 (gutter)
        |  |     |                             | card 6 |
        shingled 4.6 mm apart in depth          |========|
                                                ...
   ledge = shelf with a slot ("gutter") that     card slides out to the RIGHT
   holds only that card's bottom edge            (left end is a stop)
```
* **Shingled depth.** Card *j* stands in its own vertical plane, 4.6 mm in front
  of card *j-1*. There is about 1.4 mm of air between neighbouring cards, so
  they never touch.
* **Ledge per card.** Each card's bottom edge sits in its own gutter, cut into a
  ledge that cantilevers off a left spine. The spine is the only structural
  element. Cards overlap exactly as in the reference stand. The car windows stay
  unobstructed.
* **Nothing in front.** There is no front frame, bezel or bar. You can see and
  touch every card.
* **Removal.** Put a thumb on the card's right edge, which overhangs the ledge by
  8 mm, and slide it right. Only that card moves. To insert one, slide it in
  from the right until it hits the left stop. A small detent bump stops cards
  creeping out.
* **Mounting.** A 3 mm wall plate with three keyholes screws to the wall.

## Dimensions (defaults, edit the first block of the `.scad` file)
| Item | Value |
|---|---|
| Cards | 8 (parametric) |
| Card | 105 x 165 x 1.2 mm (measure yours) |
| Visible strip per card (pitch) | 55 mm |
| Depth step between cards | 4.6 mm |
| Overall size (8 cards) | about 111 x 559 x 40 mm |
| Gutter | 1.8 mm wide (card plus 0.3 mm clearance each side), 6 mm deep |

The script asserts that the ledge wall does not hit the card behind it and that
the blister fits under the next ledge up. A blister taller than about 49 mm
would need a larger pitch.

## Making it
* **3D print (prototype and small batch):** PETG or PLA, print flat on its back
  (the plate face on the bed). The staircase of ledges needs no supports if the
  ledge undersides stay within 45 degrees. If they don't, print on its side.
* **Production:** injection-moulded ABS or PC. Keep the ledge beam about 8 mm deep
  so it doesn't flex.
* **Cost idea:** one 2-card base module can be clipped to another, so buyers can
  extend the rack.

## Open items (need your input or a real test)
* **Card dimensions.** The card and blister sizes above are estimates. Measure
  a few real cards, including Premium and Mainline, since the thicknesses differ.
* **Unverified.** I couldn't run OpenSCAD here, so the model hasn't been rendered
  or printed. Render it (F6) and check the echoed size and assertions first.
* **Side access.** The rack needs about 100 mm of free wall space to its right
  for sliding cards out. If that doesn't suit, a mirrored version (exit left) is
  a one-line change.
* **Alternatives.** A flip-up hinged version or a removal-by-tilt version would
  keep the stack closer to the wall, but each disturbs the neighbouring cards,
  which is the original complaint.

## STL files
`python3 build_stl.py` writes the models (needs `pip install trimesh manifold3d numpy`):
* `rack_8slot.stl`: full rack, 111 x 559 x 40 mm. It is taller than most printers
  can take, so split it or have it made in sections.
* `rack_2slot_test.stl`: two slots, 111 x 229 x 12.5 mm. Print this first to check
  card fit, gutter clearance and the slide-out feel.

Both meshes are watertight. They are laid with the wall plate on the bed. Neither
has been sliced or printed yet.

## Rack sizes
The design is parametric in `N`. Pitch (55 mm) and depth step (4.6 mm) don't
change, so every size uses the same ledge, gutter and keyholes. Only the spine
height and the number of ledges change.

| Cards | File | Size (W x H x D, mm) | Fits a 256 mm bed? |
|---|---|---|---|
| 2 (test) | `rack_2slot_test.stl` | 111 x 229 x 12.5 | yes |
| 3 | `rack_3slot.stl` | 111 x 284 x 17 | no |
| 4 | `rack_4slot.stl` | 111 x 339 x 22 | no |
| 5 | `rack_5slot.stl` | 111 x 394 x 26 | no |
| 6 | `rack_6slot.stl` | 111 x 449 x 31 | no |
| 8 | `rack_8slot.stl` | 111 x 559 x 40 | no |

Previews: `preview_3_4_5_6.png`, plus `preview_<N>slot.png` per size. To make
another size, change `N` in `side_slide_rack.scad`, or add it to the list in
`build_stl.py`.

## Lift-off tray version (from the hand sketches)
The sketches show a wall frame with a rack that hinges down at the bottom. A
hinge can't do this. A panel hinged at its bottom edge and dropped to horizontal
ends up with its front face pointing at the floor, so you would see the backs of
the cards. This version keeps the frame and the open-flat idea but replaces the
hinge with a lift-off tray:

* **Frame** (`frame_<N>slot.stl`): U-shaped wall frame with a back plate, two side
  posts, a top bar and two countersunk screw holes in the top bar. Three printed
  pegs on the back plate carry the tray.
* **Tray** (`tray_<N>slot.stl`): the side-slide rack from above, now with a full-width
  back plate. Its three keyholes hang on the pegs.
* **Hanging:** push the tray onto the pegs through the big keyholes, then let it
  drop 12 mm. The top bar leaves 14 mm of headroom for this.
* **Opening:** lift the tray 12 mm and pull it toward you. Lay it flat on a table: the
  cards face up in their rows, and any card slides out sideways.
* **While hung:** the right frame post stops cards sliding out. Cards are removed
  with the tray off the wall.

| Cards | Tray (mm) | Frame (mm) |
|---|---|---|
| 3 | 120 x 284 x 17 | 145 x 316 x 22 |
| 4 | 120 x 339 x 22 | 145 x 371 x 27 |
| 5 | 120 x 394 x 26 | 145 x 426 x 31 |
| 6 | 120 x 449 x 31 | 145 x 481 x 36 |

`python3 build_liftoff.py` makes the files, `python3 render_liftoff.py 4` makes the
preview (`preview_liftoff_4slot.png`). The generator also checks that tray and
frame don't overlap in either the hung or the insertion pose (0 mm3 overlap for
3 to 6 cards).

Not tested: peg and keyhole fit, how firmly the tray hangs, and any printing.
The frame is bigger than most print beds, so print it in sections or have it made
elsewhere. A hinged variant would only work with the cards on the inside of a
door, with a see-through cover.

## Fold-down stand-up rack (CAD for 1 to 6 stalls)
The design from your photos and sketches. Closed, the cards overlap in a column behind a
frame (photo 1). The frame hinges down at the bottom and the cards stand upright, one behind
another (photo 2). Closing folds them back into the column.

**Mechanism: a parallelogram linkage, no gears.** The panel (B1) is hinged on the wall frame at H.
A second pair of bars (B2) is hinged behind it at F, which sits 18 mm above and D mm behind H.
B2 is a copy of B1 shifted by that offset, so H, B1, B2 and F form a parallelogram at every
joint. One cross arm per card per side joins B1 to B2 and always stays parallel to F-H. The arms
only translate while the panel turns 90 degrees, so each card sitting in its cradle stays upright.
Closed, the card bases are 45 mm apart up the panel. Open, they are 45 mm apart along it. Gears
were rejected because backlash would add up along the chain and tilt the far cards.

* **Cards on the inner side:** between the panel and the wall. A panel that drops open turns its
  outside face down, so cards on the outside would end up under it.
* **Depth step 6.5 mm:** each card sits that much deeper than the one in front. Open, the step
  becomes height, so the back cards stand a little higher and show above the front ones.
* **Cradles:** each card edge slides into a slot in the arm's cradle and rests on a floor. When
  the panel is open any card lifts straight out of its slot with nothing above it.
* **Wall frame:** two posts with hinge cheeks, a top crossbar with magnets that holds the panel
  closed, a bottom crossbar, an open stop at 90 degrees, and two spring anchors.
* **Counterbalance:** an unbraked panel falls open and hits the stop at 2.8 to 4.4 m/s at its free
  end. Two extension springs (one per side) cancel the gravity torque almost exactly, because both
  follow sin(angle). Spring rates and the hinge friction needed are in the test report.

**Testing:** every size passes closure, interference (zero intersections at every 2 degrees),
tolerance, stress variants and a 1 degree sweep. The tests also found four design faults that were fixed. See
`foldout/TEST_REPORT.md`. Nothing has been printed or assembled yet.

**Files** (`foldout/N<n>/` for n = 1 to 6): wall posts, crossbars, panel, b2, spacers, arms
(`arm_<card>_<L|R>.stl`, laid flat for printing), `assembly_closed.stl`, `assembly_open.stl` and a
`BOM.md`. Previews: `foldout/preview_N<n>_closed.png`, `_open.png`, `_poses.png`,
`foldout/foldout_N4_open.gif`.

| Stalls | Panel length (mm) | Depth behind panel (mm) |
|---|---|---|
| 1 | 232 | 32 |
| 2 | 280 | 32 |
| 3 | 329 | 33 |
| 4 | 375 | 39 |
| 5 | 421 | 46 |
| 6 | 466 | 52 |

Regenerate with `python3 foldout_export.py`, test with `python3 foldout_test.py` and
`python3 foldout_stress.py`, preview with `python3 foldout_render.py <N> [--gif]`
(code: `foldout_cad.py`, `foldout_test.py`, `foldout_stress.py`, `foldout_report.py`).

**Limits:**
* The panel and wall posts are longer than most print beds. Print them in sections, or cut the
  bars from 6 mm plywood or acrylic.
* Card mass (40 g) and printed hinge friction are assumptions. The ±10% spring tolerance needs
  adjustable hinge friction.
* Each joint has 0.4 mm of clearance, so a card can tilt about 0.6 degrees.
* The 55 mm and 42 mm card numbers in the earlier side-slide and lift-off models were never
  updated to the 45 mm and 35 mm measured from your photo. This design uses the measured values.


## Side-mechanism rack: 4 printed parts (replaces the fold-down rack above)
Requested changes: at most 4 parts, and the base should not stick out; the moving mechanism should
sit only in the sides. This version does that.

* **4 printed parts per rack:** `module_R`, `module_L` (a mirror image), `wall_frame`, `tie_bar`.
* **Each side module is a single print.** Cheek, two bars, one cross arm per card and all pins print
  in place with 0.4 mm clearances, so there are no joint bolts or nuts. The pins print on the lower
  layer and rise through the hole above, with 45 degree cone heads, so no supports are needed.
* **Only the sides move.** There is no full-width panel any more. The bars end just above the last
  card, so the open reach drops from 232 to 466 mm (old) to 66 to 302 mm (new), 35 to 72% less.
  The tie bar (a 6 mm square bar through both bars, below the hinge) keeps the two sides moving together.
* **Wall frame:** a thin U-frame behind the modules. It carries the magnet fingers that hold the
  panel closed, the two spring anchors and the screw holes. The magnets self-centre the panel at 0 degrees.
* **Hardware:** 2 extension springs, 4 magnets (6 x 2 mm), wall screws, 1 M3 screw and washer.

**Tests** (see `side/TEST_REPORT.md`): every size passes closure (3e-14 mm), zero intersections at every
2 degrees from 0 to 90, and the stress variants and a 1 degree sweep. The smallest gap between separate bodies
in a module is 0.38 mm, which is the pin-to-hole gap, so the pins should not fuse in the print. The tests
also found five faults while developing this version, all fixed. Nothing has been printed yet.

| Stalls | Open reach (mm) | Frame height (mm) | Module print size (mm) |
|---|---|---|---|
| 1 | 66 | 222 | 71 x 94 x 44 |
| 2 | 115 | 270 | 71 x 143 x 44 |
| 3 | 163 | 319 | 72 x 191 x 44 |
| 4 | 210 | 365 | 78 x 238 x 44 |
| 5 | 256 | 411 | 84 x 284 x 44 |
| 6 | 302 | 456 | 91 x 330 x 44 |

Files: `side/N<n>/` (the 4 STLs, `BOM.md`, and `assembly/` closed and open views for looking only),
previews `side/preview_N<n>_closed.png`, `_open.png`, `_poses.png`, and `side/side_N4_open.gif`.
Regenerate with `python3 side_export.py`, test with `python3 side_test.py` and `python3 side_stress.py`,
preview with `python3 side_render.py <N> [--gif]`. Code: `side_cad.py`.

**Limits:** print a 1-stall module first to check that the print-in-place pins move freely on your printer.
Printed pins give almost no friction, so the spring has to be tuned (about 10%), or the panel drifts.
The 5 and 6 stall modules need a large bed or diagonal placement.


## Accordion hook rack (simple, printable; replaces the earlier linkage designs)
You said the earlier mechanisms had too many parts that fail and cannot be printed. This one is a
scissor (lazy-tongs) frame on the wall. The frame is the whole mechanism, the cards hang from printed
round pegs, and every part is flat or lies on its side with no supports.

* **Open:** the pegs sit 114.5 mm apart, so every card hangs in a row, fully visible, and lifts straight off.
* **Folded:** the frame collapses to a 40 mm peg pitch for storage, with the cards off.
* **Gravity opens it** and holds it open against a stop at the bottom of the plate's slot.
* **Four printed designs and nothing else but wall screws:** `link`, `pivot_pin`, `hook_pin`, `wall_plate`.
  No springs, no magnets, no joint bolts, no print-in-place gaps. Pins are snap pins: push them in from the front until the barb clicks.
* The cards hang in one plane. A staggered stack of cards on the rack is not possible with hooks, so remove the cards before folding.

| Stalls | Links | Pivot pins | Hook pins | Plate | Width open / folded (mm) |
|---|---|---|---|---|---|
| 1 | 0 | 0 | 1 | 1 | 105 / 30 |
| 2 | 2 | 2 | 2 | 1 | 219 / 70 |
| 3 | 4 | 4 | 3 | 1 | 334 / 111 |
| 4 | 6 | 6 | 4 | 1 | 448 / 151 |
| 5 | 8 | 8 | 5 | 1 | 563 / 191 |
| 6 | 10 | 10 | 6 | 1 | 677 / 232 |

**Tests** (`accordion/TEST_REPORT.md`): every size closes exactly (1e-13 mm), has zero intersections at every
2 degrees from 14 to 70 (cards on whenever the pegs are 107 mm or more apart), and passes six card-size and
hang-hole variants. The tests found four design faults, all fixed (see the report). The main limit is droop: pin clearance adds up
along the frame, so the last hook can sit 4 to 14 mm lower than the first.

Files: `accordion/parts/` (link, pivot_pin, hook_pin: same for every size), `accordion/N<n>/` (wall_plate.stl,
BOM.md, assembly/ for viewing), previews `accordion/preview_N<n>_open.png`, `_folded.png`, `_front.png`,
`accordion/accordion_N4.gif`. Regenerate with `python3 accordion_export.py`, test with `python3 accordion_test.py`
and `python3 accordion_stress.py`, preview with `python3 accordion_render.py <N> [--gif]`. Code: `accordion_cad.py`.

Assumed, not measured: the card's hang hole (7 mm, 12 mm below the top edge). Check one real card first.


## Side rack v3: one frame + one swing design (3 printed parts, bolted hinges)

The earlier "4 print-in-place parts" side rack could not be printed without supports (slicing showed a floating cheek), so it is superseded by `side3/`.

* **Frame** (1 print): wall plate with both hinge cheeks, magnet fingers, spring tabs and the 90 degree stop. Prints back face down.
* **Swing** (2 prints, mirrored): both bars and one cross arm per card. Prints with the bar face on the bed; the arm pins are print-in-place (0.4 mm radial clearance).
* **Hinges:** four M4 bolts with nylock nuts. A 6 mm dowel ties the two swings; two M4 stud bolts carry the counterbalance springs.
* Sizes 1 to 6 stalls; 1 to 5 fit a 300 mm bed. 0 overlaps over 0 to 90 degrees at every size, plus stress variants.

Files: `side3/N<n>/` (`frame.stl`, `swing_R.stl`, `swing_L.stl`, `BOM.md`, `assembly/`), previews, `side3/TEST_REPORT.md`.
Code: `side3_cad.py`, `side3_test.py`, `side3_stress.py`, `side3_print.py`, `side3_export.py`.

## Flat-fold hook tile rack (latest design)

Based on the flat print-in-place folding phone stand idea. **One printed part per card**: a thin 8 mm tile screwed to the wall with a flat hook arm that lies flush when folded and swings out 90 degrees to hold a card through its hang hole. No hardware except wall screws. 3-car = 3 tiles, 5-car = 5 tiles, grids by stacking rows.

Files: `foldtile/` (`stl/hook_tile_print.stl`, `assembly_*`, previews, `arm_fold_animation.gif`, `BOM.md`, `TEST_REPORT.md`). Code: `foldtile_cad.py`, `foldtile_test.py`, `foldtile_render.py`. The earlier `side3/` design is superseded.


## v2: thicker frame, smaller screw holes, hinged "door" ledges (`build_v2.py`, `v2/`)

Run `python3 build_v2.py` (needs `trimesh manifold3d numpy`) to regenerate every file in `v2/`.
Nothing here has been sliced or printed. Card sizes are still estimates (edit the top of `build_v2.py`).

**Frame changes (both variants):** wall plate 3 -> 5 mm, spine 14 -> 18 mm, ledge height 10 -> 12 mm,
ledge walls 2.4 -> 3.2 mm, card step 4.6 -> 5.4 mm. The keyhole (9 mm head + 4.5 mm slot) is replaced by a
3.5 mm countersunk screw hole (7 mm head). Holes are mirrored about the plate centre: the bottom hole and top
hole sit the same distance from the bottom/top edge (33.5 mm in the thick frame, 37.9 mm in the hinged one).
Racks with 4+ cards get a third hole in the nearest ledge gap to the middle.

| File | Description |
|---|---|
| `v2/rack_<N>slot_thick.stl` | v1 design with the thicker frame and new holes (N = 3, 4, 5, 6; `2slot_test` for fit checks) |
| `v2/rack_<N>slot_hinged.stl` | each ledge is a separate door on its own vertical pin |

**Hinge (the circled spot):** the fixed spine block is replaced by two lugs per ledge, bolted to the plate, with a
4 mm pin between them. The ledge has a barrel that turns on the pin (0.3 mm radial and 0.4 mm vertical clearance),
so each ledge swings outward like a door. The STL has N+1 separate bodies (plate with lugs and pins, plus each ledge),
so it is a print-in-place hinge: print with the plate face down, no supports needed for the pins in theory, but this is untested.
Test swing 0-90 degrees outward in software: no interference between ledges, lugs and plate.

**Limitation:** a ledge can only swing with its card loaded if no card sits in front of it. Cards are stacked in
shingled planes, so a loaded lower ledge would hit the cards in front of it. In practice, slide the card out first or swing
the top ledge. Nothing holds a ledge closed yet apart from the card in the gutter; a latch or magnet pocket could be added.

### Latch (`v2/rack_<N>slot_hinged_latch.stl`)
Each ledge gets a swivel bar: a 3 mm post on the plate (x = 16 mm, 6 mm above the ledge) carries a 3.4 x 1.8 mm bar
held by a cap. Hanging down, the bar sits 0.6 mm in front of the ledge's end stop and blocks the swing (it hangs
down by gravity, so the default state is latched). Flip it up 180 degrees to open the ledge. The post is at x < 18 mm, so
it never touches the card or its blister. Print-in-place: 2N+1 separate bodies (plate with posts, N ledges, N bars),
0.3 mm clearance on the post. Checked in software: bars rotate freely 0-180 degrees, a latched ledge is blocked,
an unlatched ledge swings 0-90 degrees without interference. Not printed yet; the 2-card test piece
`rack_2slot_test_hinged_latch.stl` is the one to try first. A 1.5 mm post is thin; use PETG or print it solid.

## Modular system (`build_modular.py`, `modular/`)
A SKADIS-style slotted wall board plus separate, hook-in hinge modules, so you can add as many racks as you like.
Run `python3 build_modular.py` to regenerate all STLs; `python3 render_modular.py` for the previews.

| File | What it is |
|---|---|
| `board_tile.stl` | 140 x 240 x 5 mm board, 5 x 15 mm slots on a 20 mm grid, 3 mm rear standoff (room for the hook prongs). 6 countersunk 3.5 mm screw holes, mirrored top/bottom and left/right. Fits a 256 mm bed. Stack tiles for more height |
| `hinge_module_j<N>.stl` | **hinge + latch in one unit.** Two hooks go into slots 40 mm apart in one column; it carries the hinge lugs and the latch post. N = 0..5 sets how far the pin stands out, so each rack sits one card step (5.4 mm) in front of the last |
| `ledge.stl` | the card ledge, one design for every position |
| `hinge_pin.stl` | 4 mm pin: drops through the top lug, the ledge barrel and into the bottom lug |
| `latch_bar.stl` | swivel bar, pushes onto the module's latch post (snap ring holds it). Hangs down = latched, flip up = open |
| `demo_assembly.stl` | board plus three assembled racks, for viewing only |

**Mounting a rack:** push the module's hooks into two slots in the same column with the module 7 mm higher, then slide it down.
Racks sit 80 mm apart (every second slot pair). Rack i uses module `j = i`, so the bottom rack is j0, the next j1, and so on.
Fit the ledge between the lugs, drop in the pin from the top, then press the bar onto the post.
Each tile holds 3 racks at that pitch (slot pairs 20/60, 100/140, 180/220). Racks above the third go on a second tile.

Checked in software (no collisions): hooks insert and slide down into the slots, pin/ledge/lugs fit, a ledge swings 0-90 degrees with the bar up,
the bar blocks it when down. Not printed yet. Print orientation: hooks and plate on the bed (rear face down), ledge flat, pin standing.

## Printable clip system (`build_clip.py`, `clip/`) - replaces the hook version for printing
The hook/latch-bar modules were too fiddly to print. This version needs no supports and no extra parts.
Run `python3 build_clip.py` (needs `trimesh manifold3d numpy`); `python3 render_clip.py` for previews.
Every STL is exported in **print orientation** (z up).

| File | Print orientation | Notes |
|---|---|---|
| `clip/wall_strip.stl` | front (wide) face down | 18 mm wide x 240 mm dovetail rail, 4 mm thick, 3 countersunk 3.5 mm screw holes mirrored about the middle (20/120/220 mm). Dimples every 20 mm |
| `clip/hinge_clip.stl` | standing | slides on the rail from the top, cannot be pulled off forward (45 degree jaws). Carries the pin and the snap tongue. One part for every rack |
| `clip/ledge_j0.stl` ... `ledge_j5.stl` | standing | drops onto the pin. j sets the depth step (5.4 mm per step) so cards shingle. 80 mm of swing past the detent |

**Self-locking hinge (no extra part):** a thin tongue on the clip has a bump that snaps into a groove in the ledge barrel when the
ledge is closed. A firm pull opens it (tongue flexes 0.6 mm), and after about 25 degrees the barrel is cut back so the tongue relaxes
and the ledge swings freely to about 75-80 degrees. Closing it clicks back into the groove. The clip also has a small nub that clicks into the
strip's dimples so it holds its height; place racks at any dimple (60 mm pitch recommended).

Checked in software: clip slides over the strip with no collisions and cannot be pulled forward; the ledge clears the clip and strip from
closed to 75 degrees; neighbouring open ledges at 60 mm pitch do not touch; overhang analysis in print orientation shows nothing steeper than 45 degrees
except the countersinks/dimples (cones) and a few mm2 on the snap bump. Not printed yet. If the tongue is too stiff or too loose, change `tg_t` (tongue thickness) or `bump_r` in `build_clip.py`.
The strip stays within 1 inch wide; the clip is 31 mm because it wraps around the strip.


### Stack variants for 2, 3, 4, 5 and 6 cars, and stackable strips
The hinge clip now comes with several hinge stations on one clip (one station per card, 60 mm apart, one nub per station),
so one clip hangs a whole stack. Pieces are limited to 3 stations (150 mm tall) so they print standing on a 31 x 16 mm footprint (use a brim).

| Cars | Wall strips | Clip pieces | Ledges |
|---|---|---|---|
| 2 | 1 | `hinge_clip_x2` | `ledge_j0`, `ledge_j1` |
| 3 | 1 | `hinge_clip_x3` | `ledge_j0..j2` |
| 4 | 1 | `hinge_clip_x2` x 2 | `ledge_j0..j3` |
| 5 | 2 | `hinge_clip_x3` + `hinge_clip_x2` | `ledge_j0..j4` |
| 6 | 2 | `hinge_clip_x3` x 2 | `ledge_j0..j5` |

`hinge_clip_x1` is a single station. Put the first clip at a dimple (foot at y = 20 mm, 60 mm steps) and each following piece 60 mm per card above the last,
so the pitch stays 60 mm across pieces. `clip/stack_<N>_cars_demo.stl` shows each assembled stack (viewing only).

**Press-fit stacking:** each `wall_strip` now has two flat 5 x 8 x 2 mm tabs on its top end and two matching pockets in its bottom end (open to the front).
Push the next strip down over the tabs (tab is 0.1 mm wider than the pocket) and screw it up. Strips stay on a 240 mm pitch, so the dimple pitch and rack pitch continue across the joint.
The strip is 248 mm long including the tabs. The pocket roof is a 5 mm bridge when printed front face down.

Checked in software for every stack: clips slide over the strips, closed ledges clear everything, neighbouring ledges open to 60 degrees do not touch.
Not printed yet; if the tabs are too tight or loose change `press` in `build_clip.py`.


### Update: narrower clip, easier fit
The first clip was 31.5 mm wide and fit too tightly. Changes: the rail is now 18 mm wide (4 mm thick, 45 degree sides) and the whole clip is 24.9 mm wide, so
the clip is also inside 1 inch. Clearances were opened up: 0.55 mm each side on the dovetail (was 0.35), 0.5 mm in front of the rail (was 0.3), so the clip slides on by hand with about
0.4 mm of play and still cannot be pulled forward more than 0.5 mm. The nub on the clip now just touches the rail (0.15 mm) and clicks into the dimples, so it holds a position without binding.
The pin moved 2 mm toward the middle so the snap tongue stays inside the narrower clip; the snap lock itself is unchanged (closed ledge clicks into the barrel groove, free after about 25 degrees).
The press-fit tabs on the strip are now two 3 mm wide tabs. If it is still too tight on your printer, raise `clr` in `build_clip.py` (0.45 -> 0.6) and reprint only the clip.
Print the clip standing with a brim (its footprint is small).

### Update: 5 mm screw holes
The three screw holes in `wall_strip.stl` (at 20, 120 and 220 mm, mirrored about the middle) are now 5 mm through holes with a clean 10 mm, 45 degree countersink
(the old countersink was built from a cone that came out with broken faces in some viewers). Printed holes usually come out 0.1-0.3 mm small; change `hole_d` / `csk_d` in `build_clip.py` to adjust.

### Separate clip per rack, depth grows with the rack number (matches the circled hinges in the reference image)
`clip/hinge_clip_j0.stl` ... `hinge_clip_j5.stl`: one single-hinge clip per card. Clip `j` stands the pin out `j x 5.4 mm` further from the strip, so the clip block gets deeper
with every rack and the cards shingle. All clips use the same 24.9 mm width, the same slide-on dovetail fit, the same snap lock and the same plain ledge (`ledge_j0.stl` for every rack).
The strip is unchanged (18 mm, 5 mm holes, press-fit stacking). Racks up to 75 degrees open are free of the clip.
Deeper clips get a 45 degree gusset under the foot (the plate runs down past it) and a rigid wall behind the snap tongue so it stays a short 7 mm fin; they still print standing, no supports.
Place clip j with its foot at y = 20 + 60 j mm (nub in a dimple). `clip/separate_<N>_cars_demo.stl` (N = 2..6) shows each set assembled. Checked in software for j0..j5:
clip slides on the strip, closed ledge clears everything, swing 0-75 degrees is free apart from the snap detent, neighbouring open ledges do not touch.
The earlier multi-station clips (`hinge_clip_x2/x3`) with the stepped ledges `ledge_j0..j5` are still there as an alternative.

### Update: same-height clips, self stopper on the strip
- **Same height:** `hinge_clip_j0..j5` are now all exactly 30 mm tall (plate height identical, 24.9 mm wide). Only the depth grows with j. The long 45 degree gusset
  was replaced by a solid footing block that sits on the print bed under the foot flange, so deeper clips do not need a taller plate and still print without supports.
- **Self stopper:** new `clip/wall_strip_base.stl` is the bottom strip of a stack. A 10 mm stopper block closes the bottom of the rail, so the lowest clip slides down and stops
  by itself with its foot at y = 20 mm (nub in the 20 mm dimple, so the 60 mm rack pitch lines up). Print it rear face down (the stopper is on top). Strips above it are the plain
  `wall_strip.stl`. A one-strip stack (2-4 cars) uses only the base strip.
- **Stack tabs:** the press-fit tabs are now full strip thickness (two 2.6 mm wide tabs, pockets go all the way through), so they print on the bed with no bridge.
Checked in software: all six clips slide on the strip from the top, stop on the stopper (1 mm lower is blocked), closed ledges clear everything and neighbouring ledges open to 60 degrees do not touch.

### Print-ready kits for 2, 3 and 4 cars (`build_kits.py`, `clip/kit_<N>_cars/`)
Each kit folder has the base strip with stopper, the N same-height hinge clips (`hinge_clip_j0..`), the ledge (`ledge_x<N>.stl`, print N), two print plates
(`plate_clips.stl`, `plate_ledges.stl`, laid out for a 256 mm bed), `assembled_demo.stl`, `preview.png` and a `BOM.md`. The 4-car stack is 230 mm tall and fits one 240 mm strip.
Checked: clips slide on and rest on the stopper, closed ledges clear everything, neighbouring ledges open to 60 degrees do not touch.

### Update: dovetail strip joint, 5 and 6 car kits
The two thin press-fit tabs on the strip ends were replaced by one full-thickness **dovetail tongue** (5 mm wide at the root, 7 mm at the tip, 8 mm long) that fits a matching dovetail pocket in the next strip.
Push the upper strip onto the tongue from the front (the pocket goes right through, 0.1 mm press fit); the undercut stops the strips from sliding apart, and the tongue prints flat on the bed.
`build_kits.py` now also writes `clip/kit_5_cars/` and `clip/kit_6_cars/` (350 mm stack: base strip with stopper + `wall_strip_top.stl`, 6 clips j0..j5, 6 ledges, print plates, demo, BOM).
Checked: tongue/pocket press fit, strips cannot be pulled apart along the rail, all clips slide on and rest correctly across the joint, closed ledges clear, open ledges do not touch.

### Update: wall strip back to the 25 mm design (`wall_strip2.stl`), pockets on every strip, spring stops
- **Strip:** one `wall_strip.stl` for every position: 25 mm dovetail rail (front 25, rear 17, 4 thick), 5 mm countersunk screw holes at 20/120/220 mm, two 5 x 8 x 2 mm press-fit tabs on the top end and two matching
  pockets in the bottom end (so the lowest strip has pockets too, and any strip can be stacked on any other). The dovetail tongue, the separate base strip and the end block are gone.
- **Stoppers so the rack cannot slide:** the strip has 3 mm stop holes every 20 mm (at x = 6 mm, starting at y = 30 mm). Each clip has a spring leaf cut into its plate (1.4 mm thick, three slits) with a nub on the back.
  The nub snaps into a stop hole, which fixes the clip at that height; pushing or pulling the clip firmly flexes the leaf (about 0.4 mm) and moves it to the next hole. Put clip j with its foot at y = 20 + 60 j mm.
- **Clip width:** the clip wraps the 25 mm rail, so it is 31.5 mm wide again (same height 30 mm for every depth).
- 5 and 6 car kits use two identical strips (second strip pushed down over the first strip's tabs). All kits regenerated (`build_kits.py`).
Checked: nub sits in a stop hole with no interference, flexes between holes, clip cannot be pulled forward more than 0.5 mm, ledges clear, tabs press into the pockets of the next strip. Not printed yet.

### Update: zip-tie style ratchet lock (replaces the spring nub and stop holes)
- **Strip:** a lane of 5 mm sawtooth steps runs along the front face (x = 6 .. 10.8 mm, from y = 15 to the top end). Each step has a vertical wall on its low side and a 13 degree ramp on its high side, like a zip tie.
  The two press-fit tabs are now full strip thickness (two 5 x 8 x 4 mm tabs, pockets go all the way through), so the strip prints flat with its REAR face down, teeth facing up, with no overhangs.
- **Clip:** the spring leaf is now a pawl: a 1.4 mm leaf with a small tooth at its tip that sits in the step lane. The clip clicks upward one step (5 mm) at a time and the pawl's vertical face stops it sliding down.
  Pull the release tab (above the top of the clip plate, sticks out to the front) toward you to lift the pawl; then the clip slides down freely. Push the tab back and it locks at the next step.
- **Fitting:** slide the clips on from the BOTTOM end of the strip and push them up (sliding on from the top needs the release tab held). Foot of clip j at y = 20 + 60 j mm (the tip then sits at a tooth wall).
- Clips are now 36 mm tall (30 mm plate plus the release tab); same for every depth. Kits rebuilt. The old multi-station clips and stepped ledges were removed.
Checked: pushing a seated clip down is blocked (tip hits the wall), pushing it up rides the ramp and drops into the next step at 5 mm, with the tip removed the clip slides down freely, ledges still clear.
Not printed yet; if the pawl is too stiff or too loose change `leaf_t` (1.4) or `tooth_d` (1.2) in `build_clip.py`.

### Update: release tab built into the clip body
The release tab no longer sticks out above the plate. The pawl leaf now ends inside the plate (free end at 22 mm above the foot) and the plate frame closes around it (side posts and a 3 mm bridge above a 1 mm slit),
so nothing stands free. The thumb tab is a small 45 degree ridge on the leaf's front face, 1.1 mm proud of the plate, near its top: hook a finger or nail behind it and pull toward you to lift the pawl, then slide the clip down.
The plate is 36 mm tall (same as before). Checked again: lock blocks sliding down, ramp rides up and drops at 5 mm, ledges clear; kits rebuilt.

### Update: sturdier pawl and a pull block (the 1.4 mm leaf with 1 mm slits failed to print)
- **Leaf:** now 2.0 mm thick and 6.4 mm wide with 1.6 mm slits (every wall is at least 4 perimeters), root at the bottom so it prints upward from the plate, free end closed in by the plate frame (plate is 28 mm above the foot, clip 38 mm tall).
- **Pull block:** a solid 6.4 x 6 x 4 mm block with a 45 degree underside at the top of the leaf, standing 3 mm proud of the plate front. Grab it with two fingers and pull toward you to lift the pawl; the clip then slides down.
- **Teeth:** bigger: 6 mm pitch, 1.5 mm deep, pawl tip 4.6 mm wide and 1.9 mm high. Foot of clip j stays at y = 20 + 60 j mm (60 is a multiple of 6, so the tip always lands on a wall).
- If it is still too stiff, thin the leaf (`leaf_t` 2.0 -> 1.8); too soft, thicken it. Kits rebuilt. Checked: lock blocks sliding down, ramp rides up and drops at 6 mm, ledges clear.

### Update: Z-lock (zig-zag joint) at the top and bottom of every wall strip
The tabs and pockets were replaced by a zig-zag "Z" interlock like the reference drawing. The top end of each strip carries the male Z (an 8 mm high quadrilateral: bottom bar, a 45 degree diagonal and a top bar,
extruded through the full strip thickness), and the bottom end has the matching female Z with 0.12 mm clearance. Strip length stays 248 mm (240 mm pitch).
- **Assembly:** hold the next strip in front of the first one and press it straight toward the wall (along z); the joint closes with no force. Then screw it up.
- **Locking:** the diagonal is an undercut, so the strips cannot be pulled apart along the rail (checked: any upward move of 0.3-4 mm collides) and cannot be slid down either; they separate only by pulling forward (z) again.
  The joint does not hold sideways to the left, which the wall screws and the clip take.
- It prints flat (rear face down) with no overhangs, no thin parts. The bottom end of the lowest strip also has the female Z, so any strip can sit on any other. Kits rebuilt (5 and 6 cars use two identical strips).
Change `z_h` (8), `z_x0`/`z_x1` (2/-6) or `z_fit` (0.12) in `build_clip.py` to size or tighten the joint.
