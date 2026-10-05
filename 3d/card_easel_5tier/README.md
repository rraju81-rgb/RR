# 5-tier folding card easel (print-in-place, 1 hinge)

This is a redesign of `table_easel_3card_folding.stl`.

| File | Use |
|---|---|
| `card_easel_5tier_print_in_place.stl` | **Print this one.** Lay it flat as exported. No supports. |
| `card_easel_5tier_preview_standing.stl` | Preview only: the easel folded open, as it stands on a table. |
| `card_easel.py` | Parametric source. Run `python3 card_easel.py` to regenerate. Needs `manifold3d`, `trimesh`, `numpy`. |

## Changes from the original
1. **Back support is 40 mm wide instead of 119 mm.** The ribbed base is now a 40 mm leg. It has a full-width hinge bar and a foot pad at the end.
2. **One hinge instead of two.** The top (kickstand) hinge and the kickstand panel are gone. The bottom hinge stays.
   - The angle is now held by a V-shaped stop under the hinge. The chamfered ends of the panel and the base close flush at 75° (a 15° lean back), so the panel can't fall back.
   - Why the old outer hinge failed: the three panels were stacked on top of each other with 0.5 mm air gaps and a bridged round pin. Those layers sag and fuse.
3. **5 card ledges** (was 3). The tiers step down 4.5 mm each going up. The lower cards stand in front and the top 36 mm of every card behind shows.
4. **Better to print:**
   - Every part lies flat on the bed and nothing is stacked.
   - There are no bridges. The old card shelves spanned about 100 mm in the air with hooked lips.
   - The cone-pin hinge has only 45° overhangs, with 0.4 mm clearance.
   - The V-stop faces are 52.5° overhangs, 4 mm tall.
   - Diamond windows cut weight and print time.

## Key numbers
- Print footprint is 119 × 249 × 25.5 mm. It fits 250 mm and 256 mm beds; on smaller beds, shorten `TIER_PITCH` or `LEG_L`.
- About 118 cm³ of plastic at 100% fill. At 15% infill it is far less.
- A single tier fits cards or top-loaders up to **4.5 mm** thick (`STEP`).
- Checked in the script: 0.4 mm clearance between the parts through the whole 0–105° fold. They collide (the stop engages) just past 105°. The easel stands on the hinge knuckles and the foot pad, with the centre of mass between them.

## Print settings
- PLA or PETG, 0.2 mm layers, 3 walls, 15–20% infill, **no supports**.
- Use **no brim** at the hinge, and keep first-layer squish low so the knuckles don't fuse.
- After printing, flex the hinge gently a few times to break it free.
