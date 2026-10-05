# Tabletop Hot Wheels card stands

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
