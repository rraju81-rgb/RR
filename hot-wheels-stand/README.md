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
