# Tabletop Hot Wheels card stands

Two tabletop versions of the wall rack. Both use the wall rack's tier geometry unchanged: 55 mm pitch,
each tier 4.6 mm further forward than the one below, the same ledge profile, a 1.8 mm groove narrowing
to 1.3 mm behind the 10 mm corner supports, and a 4 mm front lip. The cards shingle exactly as they do
on the printed wall rack.

| | **A: Easel** (`table_stand_A_easel.stl`) | **B: A-frame** (`table_stand_B_aframe.stl`) |
|---|---|---|
| Use | Desk against a wall, one viewing side | Free-standing (table centre, shelf), both sides |
| Cards | 4 (one face, 4 tiers) | 6 (two faces, 3 tiers each) |
| Size W × D × H | 121 × 121 × 189 mm | 121 × 141 × 226 mm |
| Filament (solid, PLA) | ~240 g | ~364 g |
| Card face tilt | 15° back | 15° back on each face |

## Design decisions

- **Card fits fully inside.** The card is 108 mm wide. The opening between the end walls is 111 mm,
  leaving 1.5 mm clearance each side. Unlike the wall rack, the ledges are held at both ends, so there is
  no single-sided cantilever.
- **Face tilt 15°.** Gravity keeps each card seated in its groove and leaning on the card or panel
  behind it. At 0–5° cards can rock forward. Above about 20° the shingled cards slide down onto each
  other and the stand gets deep.
- **Back panel.** On the wall rack the wall itself holds the card stack. Here a 3 mm panel takes that
  role, sized to cover the bottom card (165 mm). Higher cards lean on the cards below them, as on the
  wall.
- **How the ledges attach.** The cards pass between each ledge and the panel, so ledges can only attach
  outside the card width. 5 mm end brackets at both ends tie every ledge to the panel.
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
| A empty | 71 mm | 46 / 75 mm | 33° / 46° | 0.6 N |
| A full (4 cards) | 101 mm | 38 / 83 mm | 21° / 39° | 0.8 N |
| B empty | 82 mm | 71 / 71 mm | 41° / 41° | 1.1 N |
| B full (6 cards) | 97 mm | 71 / 71 mm | 36° / 36° | 1.9 N |
| B one face full | 91 mm | 59 / 83 mm | 33° / 42° | 1.2 N |

Both pass a 15° tip check, the usual rule of thumb for freestanding furniture items, in every load case.
The easel's weak direction is forward: that is where the cards are. Its rear foot position (62 mm behind
the leg's top attachment) was chosen for this. The A-frame is symmetric and is stiffer to bumps.
Optional: 4 small rubber bumpers under the base corners stop it sliding.

## Printing

- **Orientation:** on its side (an end wall on the bed), the same way you printed the wall rack. Every
  panel, ledge, leg and the base runs the full width, so they print as vertical walls. The only overhangs
  are the end brackets on the top end, which bridge at most about 20 mm between the panel and each
  ledge. No supports are needed.
- **Bed:** A needs 121 × 189 mm. B needs 141 × 226 mm, which fits a 256 mm bed (Bambu, Prusa XL). On a
  250 × 210 mm bed, place it diagonally.
- **Print height:** 121 mm for both.
- **Settings:** 3 walls, 15 % infill. The 3 mm panels print essentially solid.

## Files

- `build_table_stands.py` builds both stands and writes `table_stands_report.json`, which holds the
  analysis numbers above.
- `render_table_stands.py` writes `table_stands_preview.png`.
