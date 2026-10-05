# Tabletop Hot Wheels card stands

## Recommended: one universal base, two interchangeable racks

`table_base_universal.stl` (119 g, 119 × 141 × 143 mm, prints upright, no supports) holds **either**
`table_rack_3card.stl` or `table_rack_5card.stl`. Both racks have the same bottom edge and the same edge
ribs, so they drop into the same slot and rest on the same 140 mm back rests. The 140 mm height stays
32 mm below the top of the 3-card rack's panel. The base's feet and 8 mm front toe are sized for the
taller 5-card rack.

The gusset under each back rest now follows the leaning back rest down to the floor, which closes the
wedge-shaped gap of the first version. The slot also sits directly on the table: its lowest corner touches
the table, and the wedge under its tilted floor is filled solid. That lowers the rack by 3 mm and removes
the raised gap under the front lip.

| On the universal base | Standing W × D × H | Tip angle front / back, full | Tip angle front / back, empty |
|---|---|---|---|
| 3-card rack | 119 × 141 × 175 mm | 27.2° / 51.5° | 35.2° / 58.1° |
| 5-card rack | 119 × 141 × 250 mm | 21.1° / 36.8° | 27.4° / 43.8° |

Checked (`table_universal_base_report.json`):

- The bases computed for the two racks are identical (0 mm³ difference).
- Each rack seats in the base without interference.
- No card touches the rack or the base, and every card's side-slide path is clear.

Preview: `table_universal_base_preview.png`. Built by `build_table_base_universal.py`.

## Card rack + frame-holder base, size-matched bases (earlier)

| Cards | Rack (prints on its side) | Base (prints upright) | Standing W × D × H | Filament |
|---|---|---|---|---|
| 3 | `table_rack_3card.stl`, 185 g | `table_base_3card.stl`, 106 g | 119 × 96 × 178 mm | 291 g |
| 5 | `table_rack_5card.stl`, 273 g | `table_base_5card.stl`, 129 g | 119 × 150 × 253 mm | 402 g |

**Rack.** The card rack has the same tiers as before: 55 mm pitch with 4.6 mm shingle, solid left stop
wall, open right end for sliding cards in, and 10 mm corner supports. The back support plates are gone.
Instead, the 3 mm panel back is stiffened by a grid of 5 mm ribs:

- two 10 mm edge ribs, which rest on the base's back rests,
- one centre rib,
- four cross ribs.

The ribs that run up the panel have a 45° chamfer on the side that faces up in the print, so the rack
prints on its side, stop wall down, with no supports. The STL is already in that orientation.

**Base.** The base follows `reference_FrameHolder.stl` (converted from the FrameHolder.step you shared):

- A slot whose floor is square to the card face, with a low front lip. The lip is in front of the bottom
  ledge, so it never touches the card path.
- Two 10 × 6 mm back rests at the ends, leaning back 15° and sitting right behind the rack's edge ribs.
- Two feet running back, each joined to its back rest with a triangular gusset.
- The 5-card base has an 8 mm front toe.

It prints upright, as the frame holder does, with no supports. The rack just drops into the slot and
lifts out to change position or go flat in a drawer.

**Checked** (`table_rack_base_report.json`):

- The rack and base don't overlap, and the rack settles onto the slot and back rests.
- No card touches the rack or the base.
- Every card's side-slide path is clear.

| Tip angle front / back | 3 cards | 5 cards |
|---|---|---|
| Empty | 27.7° / 43.8° | 27.2° / 45.8° |
| Full | 21.0° / 37.4° | 21.0° / 38.8° |

Preview: `table_rack_base_preview.png`. Built by `build_table_rack_base.py`.

---

## Other designs

There are three current designs. All of them use the wall rack's card tiers: 55 mm pitch, each tier
4.6 mm further forward, the 1.8 mm groove narrowing to 1.3 mm behind the 10 mm corner supports, and the
4 mm front lip. In all three, cards **slide in from the open right end** and stop against a **solid
left end wall**. The card is 108 mm and the ledge 111 mm. All three are single prints, printed on their
side with the left end wall on the bed, and need no supports.

| File | Cards | Size W × D × H (standing) | Filament |
|---|---|---|---|
| `table_easel_3card_folding.stl` | 3 | 119 × 167 × 159–169 mm | ~338 g |
| `table_onesided_3card.stl` | 3 | 119 × 113 × 170 mm | ~269 g |
| `table_onesided_5card.stl` | 5 | 119 × 132 × 245 mm | ~378 g |

## Folding easel, 3 cards (print-in-place hinges)

The mechanism follows the adjustable drawing-pad stand. It has three bodies and two hinges:

1. **Card panel:** 3 tiers. The 170 mm panel covers the bottom card's full height.
2. **Base plate:** hinged at the bottom of the panel. It has 4 grooves across its top.
3. **Back leg:** hinged at the top of the panel, with a rounded foot along its bottom edge. It is a 3 mm
   web with 10 × 5 mm rails along its edges on the back face. The rails stop 12 mm short of the foot so
   they never touch the base.

**Using it:** swing the leg out, lower the base flat onto the table, then set the foot in a groove. The
groove you pick sets the card-face angle:

| Groove (from the hinge) | 66 mm | 92 mm | 118 mm | 143 mm |
|---|---|---|---|---|
| Card face tilt | 10° | 15° | 20° | 25° |
| Tip angle front / back (full) | 21.5° / 58° | 27.5° / 56° | 33° / 55° | 38° / 53° |

Fold it flat for storage or for printing. A 5° groove was rejected: with the face that upright, cards
can tip forward.

**The hinges:** each runs the full width, with 7 knuckles that alternate between the panel and the
moving part. A pin on the panel runs through bores in the moving part's knuckles. Clearances are 0.4 mm
axial and 0.45 mm radial. The stand prints folded flat, on its side, so every pin stands vertical, the
most reliable orientation for print-in-place hinges.

**Checked** (`verify_table_easel_folding.py`, results in `table_easel_folding_report.json`):

- As printed: the three bodies are separate, with no contact even when shifted 0.3 mm in any
  direction.
- Unfolding: no collisions while the leg swings out to 110° or the base folds down.
- At each of the four angles:
  - The base lies flat, and the panel's front edge rests on the table.
  - The foot sits in its groove with no other contact.
  - No card touches anything.

## One-sided stand, 3 or 5 cards

The card face is fixed at 15°. Behind it are a back leg and a base, built as **edge frames**: a 2 mm
web across the full width, with 10 mm wide, 5 mm high rails along all four edges. The load runs through
the edges, and the stand looks clean from behind (`table_onesided_rear_preview.png`).

- **Leg:** the rails are on its outer (back) face.
- **Base:** the rails are on its top face, starting just behind the card panel, so the bottom card
  never touches them.

The side rails have a 45° chamfer on their inner edge. In the side print, the top rail therefore builds
off the web without supports. The thin web is there for printing: separate open struts would leave the
top rail as a 170 mm unsupported bridge.

| | 3 cards | 5 cards |
|---|---|---|
| Tip angle front / back, full | 26.8° / 42° | 21.7° / 33° |
| Tip angle front / back, empty | 38° / 46° | 31° / 36° |
| Print footprint (on its side) | 113 × 169 mm | 132 × 244 mm, needs a 250 mm+ bed |

**Checked** (`table_onesided_report.json`):

- No card touches the stand.
- Every card's side-slide path is clear.
- The left wall stops every card.

The 5-card stand meets the 18° front-tip target without a front toe.

## Earlier versions

`table_stand_A_easel.stl` (4 cards, fixed rear legs) and `table_stand_B_aframe.stl` (double-sided) are
kept for reference. They are replaced by the designs above. Their analysis is in
`table_stands_report.json`, built by `build_table_stands.py`.
