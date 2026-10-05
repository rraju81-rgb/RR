# Tabletop Hot Wheels card stands

Two tabletop versions of the wall rack. Both use the wall rack's tier geometry unchanged: 55 mm pitch,
each tier 4.6 mm further forward than the one below, the same ledge profile, a 1.8 mm groove narrowing
to 1.3 mm behind the 10 mm corner supports, and a 4 mm front lip. The cards shingle exactly as they do
on the printed wall rack.

| | **A: Easel** (`table_stand_A_easel.stl`) | **B: A-frame** (`table_stand_B_aframe.stl`) |
|---|---|---|
| Use | Desk against a wall, one viewing side | Free-standing (table centre, shelf), both sides |
| Cards | 4 (one face, 4 tiers) | 6 (two faces, 3 tiers each) |
| Size W × D × H | 119 × 121 × 189 mm | 119 × 141 × 227 mm |
| Filament (solid, PLA) | ~248 g | ~387 g |
| Card loading | Slide in from the open right end | Slide in from the open right end (both faces) |
| Card face tilt | 15° back | 15° back on each face |

## Design decisions

- **Cards slide in from the side.** The right end of every ledge is fully open. A card goes into the
  groove from the right and slides left until it meets the **solid 8 mm left end wall**, which stops it
  1.5 mm from home with the 108 mm card fully on the 111 mm ledge. Nothing joins the ledges to the panel
  at the right end, because any such link would cross the cards' slide path. So each ledge is held from
  the left wall, the same way the spine holds the ledges on the wall rack.
- **Face tilt 15°.** Gravity keeps each card seated in its groove and leaning on the card or panel
  behind it. At 0–5° cards can rock forward. Above about 20° the shingled cards slide down onto each
  other and the stand gets deep.
- **Back panel.** On the wall rack the wall itself holds the card stack. Here a 3 mm panel takes that
  role, sized to cover the bottom card (165 mm). Higher cards lean on the cards below them, as on the
  wall.
- **How the ledges attach.** The cards pass between each ledge and the panel, so a ledge can only
  attach outside the card's slide path. The left end wall ties every ledge to the panel. It is stepped to
  follow each tier's front edge.
- **Easel support.** Two 22 mm wide rear legs run from just below the panel top to a full-width base
  plate. The panel, legs and base form a rigid triangle. The legs sit only at the ends to save material.
- **A-frame apex height.** Cards on a leaning face extend past the panel top. If the panels meet too
  low, the top cards of the two faces cross in the air (this was found and fixed in the first draft,
  which had 4 + 4 cards). With 3 tiers per face and a 232 mm panel, the faces' cards never touch.
  Checked: 0 mm³ overlap.

## Stability

Assumed loads, per card: a 30 g car in the blister, 50 mm above the card bottom and 12 mm proud of the
face, plus 10 g of card and blister at the card's centre. The stand is counted as solid PLA. The tip
angle is how far the stand can be tilted before it falls.

| Case | CoM height | Margin front / rear | Tip angle front / rear | Push at top to tip |
|---|---|---|---|---|
| A empty | 73 mm | 46 / 75 mm | 32° / 46° | 0.6 N |
| A full (4 cards) | 102 mm | 38 / 83 mm | 21° / 39° | 0.8 N |
| B empty | 85 mm | 71 / 71 mm | 40° / 40° | 1.2 N |
| B full (6 cards) | 98 mm | 71 / 71 mm | 36° / 36° | 2.0 N |
| B one face full | 93 mm | 59 / 83 mm | 32° / 41° | 1.3 N |

The exact values are in `table_stands_report.json`. In that file, `side_slide_path_blocked_mm3 = 0`
confirms that each card's path from 150 mm right of the stand to its stop is clear.

Both pass a 15° tip check, the usual rule of thumb for freestanding furniture items, in every load case.
The easel's weak direction is forward: that is where the cards are. Its rear foot position (62 mm behind
the leg's top attachment) was chosen for this. The A-frame is symmetric and is stiffer to bumps.
Optional: 4 small rubber bumpers under the base corners stop it sliding.

## Printing

- **Orientation:** on its side, with the solid left end wall on the bed. Every panel, ledge, leg and
  the base rises straight up from that wall, and the open right end is the top of the print. There are
  no overhangs or bridges, so no supports are needed.
- **Bed:** A needs 121 × 189 mm. B needs 141 × 226 mm, which fits a 256 mm bed (Bambu, Prusa XL). On a
  250 × 210 mm bed, place it diagonally.
- **Print height:** 119 mm for both.
- **Settings:** 3 walls, 15 % infill. The 3 mm panels print essentially solid.

## Files

- `build_table_stands.py` builds both stands and writes `table_stands_report.json`, which holds the
  analysis numbers above.
- `render_table_stands.py` writes `table_stands_preview.png`.
