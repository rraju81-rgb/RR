# PITLANE fixed sliding rack — right + left hand

Same rack as `fused/reference/rack_6ledge_130_3mmholes.stl` (449 mm, 6 ledges, 55 mm pitch, same ledge/slot, chamfered
corner posts) with **no hinge**: each ledge is solid with the 20 mm wide wall mount and the spine end is a solid end stop.
Cards slide into the slot from the open end — from the right on `right_fixed_rack_PRINT.stl`, from the left on the mirrored
`left_fixed_rack_PRINT.stl`. Mount back to back, left rack 27.5 mm lower (as `pair_assembled_demo.stl`).

Print as exported, lying on the spine's flat back edge (same orientation as your reference). One piece each, 3 mm screw holes.

Checked: ledges identical to the reference except the chamfers; cards in place and the whole slide-in path (105 mm) are
clear; the two racks and their cards never touch.

Rebuild: `python3 build_fixed.py`
