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
