# Fixed card rack – v2 (strength + print fixes)

| File | What it is |
|---|---|
| `left_fixed_rack_PRINT_v2.stl` | **Print this** – modified left rack |
| `right_fixed_rack_PRINT_v2.stl` | **Print this** – modified right rack (exact mirror of left) |
| `original/` | The STLs as received, untouched |
| `modify_rack.py` | Script that produces v2 from `original/` (all dimensions are parameters at the top) |
| `before_after.png` | Visual comparison (original vs v2, with tier-6 cross-section) |

Print orientation is unchanged (rail flat on the bed, arms pointing up, 32 × 350 × 136 mm).

## What changed

### 1. Card slot no longer breaks off – root rebuilt + chamfers
Root cause found in the original mesh: the gusset under each card-slot lip was
**floating 0.1 mm above the block** (z 27.6 → 27.7), and there was a loose
0.1 mm sliver at z ≈ 36.5. So the lip was only attached at its back wall,
which is exactly where it snapped .

* Lip + gusset rebuilt as one solid that is fused into the block.
* 2.5 mm 45° chamfer added at the foot of the lip.
* 0.5 mm chamfers in both bottom corners of the card slot. This removes the sharp
  notch where cracks start. The card now sits about 0.5 mm higher in the slot.
* 3 mm × 45° chamfer where the 2.4 mm arm plate meets the block on the rail side
  (1.2 mm on the first tier, where there is less room). The card side of the
  plate is left flat so the card still lies flush against it.

### 2. Spacer blocks (upper stacks)
The spacer blocks under tiers 4, 5 and 6 are **solid with a flat top**. The
lightening cut-outs tried earlier were filled back in at your request so the
blocks look smooth. The rail-side 3 mm root chamfer of each arm sits on that flat
top. The curved-scoop version can be switched back on with `SPACER_SCOOP = True`
in `modify_rack.py`. Part volume is 153.1 cm³, about the same as the original
152.5 cm³ (the chamfers add a little).

### 3. Edges supported for faster, cleaner printing
* The three mounting holes are now 45° teardrops, so the hole tops don't sag.
* The 0.45 mm flat ledge where the groove narrows into the tip slot (z 127)
  is now a 45° ramp.
* The floating sliver and gap from point 1 are gone, so no stray "air" layers.
* Overhang area steeper than 45°: **187 mm² → ~3 mm²**. The remaining 3 mm² is
  0.05 mm boolean overlap seams, thinner than a single printed line.

Both v2 files are single, watertight, manifold solids.

## Regenerating
```bash
pip install trimesh manifold3d numpy scipy networkx
python3 modify_rack.py
```
