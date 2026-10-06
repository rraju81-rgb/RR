# PITLANE lift-off rack (separate ledges)

Same rack as `fused/reference/rack_6ledge_130_3mmholes.stl` (130 mm wide, 6 ledges, 55 mm pitch, same ledge profile and card slot,
3 mm screw holes, chamfered front corner posts), but the **ledges are printed separately** and drop onto hinge pins taken from
`reference/LiftOffHinge.stl`:

* **Wall body** (`wall_body_PRINT.stl`, 464 x 17 x 36.6 mm, one piece): spine + stand-offs + the hinge's **pin half**
  (Ø10 x 15 knuckle with Ø5 x 15 pin) fused under every ledge. The spine is 15 mm taller than your STL (bottom ledge needs its
  knuckle below it). Screw holes moved up 15 mm with everything else (y = 43 / 153 / 318 from the bottom).
* **Ledges** (`ledge_1..6_PRINT.stl` or all on one plate `ledges_all_6_PRINT.stl`): your ledge + the hinge's **socket half**
  (Ø10.2 x 15 ring, Ø5.5 hole = 0.25 mm clearance on the pin). The STL's flat screw leaves are replaced by a solid web.

## Use
Mount the wall body, then lower each ledge's ring over its pin until it sits on the knuckle. To remove: swing closed,
**lift 15.5 mm, pull forward**. Ledges swing open up to 135°; they stop at closed against the stand-off (bottom ledge against the spine).

## Print
* Ledges: as exported, standing on their bottom face — ring vertical like your hinge STL, no supports.
* Wall body: as exported, lying on its side. Pins print horizontal on a thin snap-off fin (break it off / file flush).
  Only small bridges (cradle arches); no supports needed.

## Checked (boolean collision tests)
No overlap wall/ledges or ledge/ledge assembled; swing 0 → 135° free on all ledges, stop ~3° past closed; lift path free to
15.5 mm (+ ~1.5 mm spare), then straight pull-out free; pins fully clear of rings after the lift.

Rebuild: `python3 build_liftoff.py`
