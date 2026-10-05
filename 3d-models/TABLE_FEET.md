# Clip-on table feet for the wall racks

Two small feet turn either wall rack into a tabletop stand. Cards still slide in **from the side**, along
the groove's open tip end, so they are quick to swap. The rack drops into the feet and lifts straight
out to go back on the wall. Nothing is glued or screwed.

| Rack | Left foot (spine socket) | Right foot (ledge cradle) |
|---|---|---|
| `rack_6ledge_130_3mmholes.stl` (plain, 130 mm) | `table_foot_left_plain.stl` | `table_foot_right_plain.stl` |
| `rack_v2_hinged_134.stl` (hinged, 134 mm) | `table_foot_left_hinged.stl` | `table_foot_right_hinged.stl` |

Each foot is 195 mm long (front to back) by 26 mm wide. Each prints flat with no supports and weighs
about 33–60 g.

## How it works

- **Left foot:** a 15 mm deep socket around the bottom of the spine, sized to the rack's actual shape
  plus 0.3 mm clearance. It stays left of the card groove (x < 20 mm), so the bottom card can go fully
  home.
- **Right foot:** a 12 mm deep cradle under the bottom ledge's tip end. It grips the ledge from below,
  behind the back wall and in front of the lip, and never enters the groove. A 4 mm end stop just past
  the tip stops the rack sliding sideways. The stop is only 2.6 mm high, below the groove floor (3 mm),
  so cards pass over it.
- **Hinged rack:** the spine shelf hangs 4.4 mm below the ledges, so the right foot is 4.4 mm taller to
  keep the rack level. The cradle also holds the bottom ledge closed.
- **Load path:** the rack's weight goes into the feet through the socket floor and the cradle floor.
  Triangular ribs stiffen both feet.

## Checks (`verify_table_feet.py`, results in `table_feet_report.json`)

- **Seated:** no overlap between rack and feet. The rack rests on the pocket floors.
- **Play:** 0.35 mm in each direction along the ledges (±x) and front/back (±z). The rack is held in
  both directions on both axes.
- **Lift-out:** raised 16.5 mm, the rack is clear of both feet.
- **Side slide:** a card sliding in from the tip side along the bottom groove hits nothing (0 mm³).
- **Card fully home:** a card sitting fully in the bottom groove is clear of the left foot.
- **Stability, rack + 6 loaded cards:**
  - Plain: tip angle 30.0° front, 30.8° back, 22.5° sideways.
  - Hinged: tip angle 30.8° front, 31.4° back, 23.8° sideways.

## Feet or tabletop stand?

The tabletop stands (`TABLETOP_STANDS.md`) now also load cards from the side. Use the feet when you want
one rack that moves between wall and table. Use stand A or B for a dedicated desk piece that leans the
cards back 15°.
