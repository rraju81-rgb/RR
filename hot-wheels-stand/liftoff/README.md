# PITLANE lift-off rack (separate ledges) — right + left hand

Same rack as `fused/reference/rack_6ledge_130_3mmholes.stl` (6 ledges, 55 mm pitch, same ledge profile and card slot,
chamfered front corner posts), ledges printed separately and dropped onto hinge pins from `reference/LiftOffHinge.stl`.

## v2 changes
* **Pin-root chamfer** (1 mm x 45°) where the pin meets the knuckle; the ledge ring has a matching chamfer in its hole.
* **Print fin under the pin removed** (the pin prints horizontal without it).
* **Wall mount 20 mm wide** (was 14): widened 6 mm on the back edge, ledges unchanged. Screw holes on the spine centre line.
* **Left-hand version** (`left_*`): mirror image, cards load from the left. Mount the two spines back to back with the
  left rack **27.5 mm (half a pitch) lower** than the right one, so the ledges alternate as in your sketch.

## Files
| file | what |
|---|---|
| `right_wall_body_PRINT.stl` / `left_wall_body_PRINT.stl` | wall mount with 6 pins, 464 x 20 mm (+ brackets), print on its flat back edge |
| `right_ledge_N_PRINT.stl`, `right_ledges_all_6_PRINT.stl` (and `left_…`) | ledges, print standing on their bottom face, no supports |
| `pair_assembled_demo.stl` | both racks mounted as intended (check only, don't print) |

## Use
Lower each ledge's ring over its pin. Remove: close it, lift 15.5 mm, pull forward. Opens to 135°, stops ~3° past closed.

## Checked (boolean collision tests)
* each rack: no overlaps; swing 0–135° free; lift + pull-out path free; cards in place clear.
* pair (spines touching, half-pitch stagger), ledge **and loaded card**: opening any ledge on one side, at any angle up to
  120°, never touches the other side. Opening one on each side at the same time is clear up to 75°; at 90° both the blisters
  meet in the middle — leave a 20 mm gap between the two spines if you want both fully open together.
