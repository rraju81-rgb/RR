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

## Regenerate / customise
Every dimension is a parameter in the `P` dict at the top of `build_spoiler.py`.
```bash
blender -b -P build_spoiler.py -- --render
```
(The GLB exporter needs `numpy` on Blender's Python path.)

## Manufacturing notes
- The model is solid. For a moulded ABS part, shell it to ~2.5 mm wall thickness in your CAD tool.
- 98 cm is longer than most 3D printer beds. Split it into 3–4 sections with alignment pins,
  or print it diagonally on a large-format printer. ASA or ABS is recommended for UV and heat resistance.
- Dimensions were set from the listed 98 cm length and proportions read off the product photos;
  check the fit against your vehicle before production.
