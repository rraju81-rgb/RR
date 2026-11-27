# Universal M-Style Rear Spoiler – 98 cm (Hatchback & Sedan)

Parametric 3D model of the universal "M-Style" roof/hatch spoiler, shaped from the
reference product photos (gloss black ABS, adhesive-tape mount).

![3/4 front](output/render_front_3q.png)
![Tip detail](output/render_tip_detail.png)

## Design features (matched to the photos)
- **98 cm** tip-to-tip blade, bowed in plan (tips swept forward 30 mm) and in elevation
  (tips drop 16 mm) so it follows the roof/trunk crown.
- **Stepped outer wings**: centre chord 72 mm, outer chord 100 mm, joined by an angled step
  at ~40 % of the half-span; the outer wings also sit 6 mm higher.
- Thin wedge blade: 15 mm rounded mounting nose → 2.2 mm trailing edge with a 4 mm ducktail kick
  (gives the crease line along the top).
- **Angle-cut tips** that turn down into solid **end plates** (24 mm drop).
- Flat **adhesive pad** on the underside (front 38 % of the chord) for 3M double-sided tape.

## Overall size
| | mm |
|---|---|
| Length | 980 |
| Depth (fore/aft, incl. plan curvature) | 123 |
| Height (incl. end-plate drop and crown) | 55 |

## Files (`output/`)
- `m_style_spoiler_98cm.stl` – for 3D printing / CNC / mould making (units: mm)
- `m_style_spoiler_98cm.obj` + `.mtl` – for CAD/3D apps (mm)
- `m_style_spoiler_98cm.glb` – for web/AR viewers (metres)
- `render_*.png` – studio renders

## 3-piece version (loose dowel pins)
![Exploded](output/render_exploded.png)
![Joint](output/render_joint_detail.png)

The spoiler is split into three equal 326.7 mm sections. Each joint face has two blind holes,
and **separate printed pins** bridge the joint, so no part has anything sticking out.

| File | Size (mm) | Notes |
|---|---|---|
| `m_style_spoiler_98cm_piece_l.stl` | 326.7 × 123 × 55 | 2 holes (inner end) |
| `m_style_spoiler_98cm_piece_c.stl` | 326.7 × 76 × 17 | 2 holes at each end |
| `m_style_spoiler_98cm_piece_r.stl` | 326.7 × 123 × 55 | 2 holes (inner end) |
| `m_style_spoiler_98cm_pin.stl` | Ø6 × 24 | a single pin |
| `m_style_spoiler_98cm_pins_x5.stl` | 5 pins | print set: 4 needed + 1 spare |

- **Pins**: Ø6 × 24 mm, 0.8 mm chamfer on both ends so they slide in either way round.
  Print them **standing upright** (as laid out in the set file) for the strongest pins.
- **Holes**: Ø6.3 mm (0.15 mm radial clearance), 12.8 mm deep in each face, with a 0.5 mm
  countersink at the mouth. The extra 0.8 mm depth is a glue pocket.
- Pins sit 11 mm and 27 mm back from the nose at mid-thickness. That leaves 3.9 mm of wall around
  the front pin and 2.9 mm around the rear pin.
- **Assembly**: push the pins into one piece, dry-fit, then glue the pins and faces
  (epoxy, CA, or ABS/acetone slurry for ABS) and clamp. Sand and paint over the seams.
- Print each body piece lying on its flat mounting pad.
- If the pins fit too tight or loose, change `clearance` in the `S` dict and rebuild.
  `--split-renders-only` redraws just the exploded and joint views; `--no-split` skips the split.

## Regenerate / customise
Every dimension is a parameter in the `P` dict at the top of `build_spoiler.py`.
```bash
blender -b -P build_spoiler.py -- --render
```
(The GLB exporter needs `numpy` on Blender's Python path.)

## Manufacturing notes
- The model is solid. For a moulded ABS part, shell it to ~2.5 mm wall thickness in your CAD tool.
- 98 cm is longer than most 3D printer beds, so use the 3-piece version above.
  ASA or ABS is recommended for UV and heat resistance.
- Dimensions were set from the listed 98 cm length and proportions read off the product photos;
  check the fit against your vehicle before production.
