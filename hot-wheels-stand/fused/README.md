# PITLANE fused rack (one-piece wall rack with working hinges)
Built from the reference `reference/rack_6ledge_130_3mmholes.stl` by `python3 build_fused.py`.

- pitlane_fused_rack.stl: same frame as the reference (x right, y up, z out of the wall). 130 x 449 x 36.9 mm.
- pitlane_fused_rack_PRINT.stl: the same part laid on its LEFT SIDE (the spine's side face) on the bed. Print this one.

What changed vs the reference
- Wall spine, hinge knuckles and pins are ONE solid: nothing can fall off. Each ledge turns on a 5 mm pin (0.4 mm radial,
  0.5 mm axial gaps) between a bottom and a top knuckle: a print-in-place hinge. The ledge bodies are cut straight from the
  reference STL (same L profile, 22 mm tall, 55 mm pitch, 4.6 mm step, same 3 mm screw holes at y = 28 / 138 / 303).
- All ledges sit 2.7 mm further from the wall (depth 36.9 instead of 34.2) so the bottom ledge's barrel clears the wall.
- 45 deg x 6 mm chamfer on the inner top edge of both front corner posts of every ledge (as marked).
- Each ledge stops ~3 deg past closed (stand-off behind it), opens to 120 deg; cards load with the ledge opened up to 45 deg.
- Barrels have a 0.6 mm flat to sit on the bed; two 1.2 mm snap-off tabs per ledge hold it upright while printing.

Printing: PRINT file as exported, 0.2 mm layers, brim, no supports (the pins bridge 14 mm between knuckles; hole tops are
teardrops). After printing swing each ledge open firmly once: the two tabs snap and the hinge breaks free.
Checked on the CAD model: one watertight body; every gap >= 0.3 mm (no fusing); ledges swing 0-120 deg without hitting the
spine or each other; closed cards and blisters fit; ledge bodies identical to the reference except the chamfers.
