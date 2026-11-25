"""write v15/README.md from the build's reports (run from spoiler/ after p1-p5)"""
import sys, json; sys.path.insert(0, 'v15/src')
from layout import STEM, IDS, T_SKIN, LAND_T, LAND, OPEN_H, K_WALL, LAND_BACK
import numpy as np
V = json.load(open('v15/out/validation.json')); P = json.load(open('v15/out/print_report.json'))
J = json.load(open('v15/out/joints.json')); C = json.load(open('v15/out/core_report.json'))
V14 = json.load(open('v14/out/validation.json'))
vol = {k: V['meshes'][k]['volume_cm3'] for k in IDS}; tot = sum(vol.values())
vol14 = {k: V14['meshes'][k]['volume_cm3'] for k in IDS}; tot14 = sum(vol14.values())
th = {k: V['thickness'][k]['max_mm'] for k in IDS}
rear = J['span']['-216.7 rear']; front = J['span']['-216.7 front']
ch = {k: J['chord'][k]['pins_x'] for k in J['chord']}
npin = P['PIN']['n_needed']; nprint = P['PIN']['print_count']
ov = {k: P[k]['overhang_gt55_cm2'] for k in IDS}
us = {k: P[k]['unsupported_gt45_cm2'] for k in IDS}
fmt = lambda v: ', '.join('%g' % round(z, 1) for z in v)
pz = lambda j: ' and '.join('%g' % round(p[0], 1) for p in j['pins_zy'])
an = lambda n: 'an' if str(int(round(n)))[0] == '8' or int(round(n)) in (11, 18) else 'a'
wall_deg = np.degrees(np.arctan(1.0 / K_WALL))
rows = '\n'.join(f"| {k[1]} | `{STEM[k]}` | {lab} | {vol[k]:.0f} cm³ | {vol14[k]:.0f} cm³ |" for k, lab in zip(IDS, [
    'left section, rear', 'left section, front (with the left fin)', 'centre section, rear',
    'centre section, front', 'right section, rear', 'right section, front (with the right fin)']))
prow = '\n'.join(f"| `{STEM[k]}.stl` | {' × '.join('%.0f' % v for v in P[k]['print_extent_mm'])} | stands on {P[k]['stands_on']} |" for k in IDS)
text = f"""# Polo Oettinger-style roof spoiler v15: a thin {T_SKIN:.0f} mm shell, open underneath, smooth all over

v15 is v14 with the closed underside taken out again, as marked in blue on the v14 cut faces:

- **Thinner.** In v14 every part was a skin, a cavity and a closed underside one over the other, so its cut faces showed the whole depth of the spoiler, up to 19 mm. v15 is a **{T_SKIN:.0f} mm shell** under every visible surface (as thin as the spoiler's own front edge) and open underneath. It is thicker only where it has to be: {LAND_T} mm joint lands along the cuts for the pins and tongues. The six parts weigh in at **{tot:,.0f} cm³** of plastic, down from {tot14:,.0f} cm³ in v14 and 2,194 cm³ in v13.
- **Smooth and simple underneath, with no brim at the back.** Seen from below there is the front band, one opening, and the shell round the back edge, nothing else:
  - the front band (where the spoiler is thinner than {OPEN_H:.0f} mm, 49–85 mm deep) stays closed, and the opening starts on it with a {wall_deg:.0f}° ramp up into the {T_SKIN:.0f} mm ceiling, along one clean, crisp line;
  - at the back there is no band, no ramp and no strip: the opening runs right to the line where the underside leaves the car, and the {T_SKIN:.0f} mm shell wraps round the back edge as a smooth offset of the outside, so the rear side seen from below is as smooth as the top;
  - there is no brim, no lip, no slot and no channel.
- **Unchanged:** the outside shape, including v14's blended ducktail lip ends; the six parts and the way they print; the seven-file print set; the joints; and the 10 mm limit.

![underside, v14 and v15](docs/v15_back_v14_v15.png)

## 1. The shell

![sections](docs/v15_shell.png)

- **Skin:** {T_SKIN:.0f} mm under every visible surface: the top, the front edge, the spoiler's own underside behind the back edge (under the ducktail lip), and the fins' outer faces.
- **Open underneath** through the faces that sit on the car (in front of the line where the underside leaves the car at the back) and through the fins' pillar side.
- **Front band:** solid where the spoiler is thinner than {OPEN_H:.0f} mm. That is the band at the front, 49–85 mm deep, where the VHB tape goes.
- **The opening** starts on the front band with a {wall_deg:.0f}° ramp up to the {T_SKIN:.0f} mm ceiling, so it never starts with a step, and the ramp meets the underside along one clean, crisp line, a smooth curve across the whole span.
- **The back edge:** no band and no ramp. The opening runs right back to the line where the underside leaves the car, and behind it the {T_SKIN:.0f} mm shell wraps round the back edge: it follows the top over the back edge, then the ducktail lip's own underside back to that line, everywhere {T_SKIN:.0f} mm from the outside. Inside, the shell is a smooth offset of the outer surface. The shell's edge along that line sits on the car and takes the adhesive bead.
- **Joint lands:** along every cut (the span seams and the front/rear cuts) the skin is {LAND_T} mm thick for {LAND[0]:.0f} mm. It then tapers smoothly back to {T_SKIN:.0f} mm by {LAND[1]:.0f} mm from the cut, so the pin holes and grooves have walls all round. From below they show as gentle swells along the cuts. The span seams' lands stop {LAND_BACK:.0f} mm before the back edge, so the shell is {T_SKIN:.0f} mm all round the back edge.
- **Smooth everywhere:** the whole inside comes from one smooth field, so the ramp runs into the ceiling in a soft curve and the inside follows the outside round the back edge. The only edges are the crisp line where the ramp meets the underside and the shell's own edge at the back. There are no voxel steps, no slots and no ledges.
- **Fins:** parts 2 and 6 are hollowed from the pillar side, as before. That face sits against the car's pillar.

## 2. The cut faces, v14 and v15

![cut faces](docs/v15_cut_v14_v15.png)

The faces you marked: in v14 a cut face showed the skin, the cavity and the closed underside, the whole depth of the spoiler. In v15 it shows the {LAND_T} mm joint land over the opening, plus the solid front band and, at the back, the {T_SKIN:.0f} mm shell round the back edge.

## 3. The six parts

![parts](docs/v15_parts.png)

| Part | File | Where | Volume | v14 |
|---|---|---|---|---|
{rows}
| | | **Total** | **{tot:,.0f} cm³** | {tot14:,.0f} cm³ |

- **Across the span:** cuts at x = ±216.7 mm. The centre section is 433 mm wide; each side section is 433 mm including its fin.
- **Front/rear:** one flat, vertical cut per section. It runs at z = 122 mm across the centre and slopes to z = 100 mm at the ends.
- **Symmetry:** the left and right parts are exact mirror images.
- **Weight:** {tot:,.0f} cm³ of part is about {tot * 0.96 / 1000:.1f} kg in ASA or {tot * 1.14 / 1000:.1f} kg in PETG, plus primer and paint. With 4 walls the {T_SKIN:.0f} mm shell prints practically solid, so this is about 90% of solid plastic; v14's thicker parts were more infill.

![sections](docs/v15_sections.png)

## 4. Thickness: 10 mm at most

Greatest thickness per part, measured as the largest sphere that fits inside. The thickest places are the joint lands; the shell itself is {T_SKIN:.0f} mm.

| Part | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| mm | {' | '.join('%.1f' % th[k] for k in IDS)} |

## 5. Joints: dowel pins at every seam, 30° tongues across the span

![joints](docs/v15_joints.png)

The pins and tongues sit in the joint lands, the {LAND_T} mm thickening of the skin along each cut. Every hole has at least 1.6 mm of wall all round.

**Span seams** (x = ±216.7 mm; tongue on the side part, groove in the centre part):

- **Rear segment** (parts 1|3 and 3|5): {len(rear['pins_zy'])} × 3 mm pin{'s' if len(rear['pins_zy']) > 1 else ''} at z = {pz(rear)} mm, and {an(rear['tongue_length'])} {rear['tongue_length']:.0f} mm tongue ({rear['tongue_size'][0]} mm wide, {rear['tongue_size'][1]} mm tall, sides 30° off the joining direction).
- **Front segment** (parts 2|4 and 4|6): {len(front['pins_zy'])} pin{'s' if len(front['pins_zy']) > 1 else ''} at z = {pz(front)} mm and {an(front['tongue_length'])} {front['tongue_length']:.0f} mm tongue ({front['tongue_size'][0]} wide, {front['tongue_size'][1]} tall, same 30° sides).
- **Printing:** these faces stand upright when printed. The holes are teardrop-shaped, pointed towards the top of the print, and the tongue and groove ends taper at 45°.

**Front/rear cuts** (parts 2|1, 4|3, 6|5): dowel pins only, about every 80 mm, with round holes and pointed ends:
- {len(ch['C'])} pins on the centre cut, at x = {fmt(sorted(ch['C']))} mm;
- {len(ch['L'])} pins on each side cut, at x = ±{fmt(sorted(abs(v) for v in ch['L']))} mm.

**Pins and fit:**
- {npin} pins in all, 3 × 18 mm, in 3.3 mm holes 9.5 mm deep each side, with a 30° lead-in. They are all the same: print `v15_PIN_3x18.stl` {nprint} times ({npin} + {nprint - npin} spare), or use 3 mm steel dowels or rod cut to 18 mm.
- At least {V['pin_walls_min_mm']} mm of wall around every hole.
- Measured clearance round the tongues: {min(V['clearance'].values()):.2f} mm at least.

![joint detail](docs/v15_joint_detail.png)

## Print files

`print/` holds the whole print set, seven files, bed-ready for a 420 × 420 mm bed (Anycubic Kobra 3 Max). Each part stands on its cut face, set across the bed's diagonal.

| File | Print size (mm) | Notes |
|---|---|---|
{prow}
| `v15_PIN_3x18.stl` | 3 × 18 | the pin, standing on end: print {nprint} ({npin} + {nprint - npin} spare); skip if using metal pins |

![bed layouts](docs/v15_bed_layouts.png)

**Supports: only inside the back edge of parts 1, 3 and 5.** Standing on its front cut face, each rear part has its back edge at the top of the print, and with no band or ramp under it any more the shell's edge there hangs free: {us['P1']:.0f} cm² on parts 1 and 5 and {us['P3']:.0f} cm² on part 3 have nothing below them. Use tree supports from the build plate only, at about 45°. They grow up through the open underside to the inside of the back edge, so they touch only the edge that is glued to the car, never a face you see. Parts 2, 4 and 6 print without support (their {us['P2']:.0f}–{us['P4']:.0f} cm² of steep faces are scattered facets a slicer bridges); if your slicer flags the fin tip on parts 2 and 6, allow a small tree support there.

**Settings:** ASA (UV-stable) or PETG; 0.25–0.28 mm layers with a 0.4 mm nozzle; 4 walls (at {T_SKIN:.0f} mm the shell is then solid), 20–25% gyroid infill for the lands and the front band; an 8–10 mm slicer brim (the bed-adhesion setting, not part of the model) on every part. A thin shell this size can lift at the corners while printing, so keep that brim and an enclosure.

## Assembly

1. **Dry-fit.** At each front/rear cut, push the pins into the rear part's holes, then press the front part on. At the span seams, push the pins into the centre parts and slide the side parts on along the span.
2. **Glue.** Epoxy, or for ASA, ABS/ASA cement, on both faces of each joint (the shell's cut faces, the lands and the front band), in the holes, and in the grooves and on the tongues of the span seams. Join each front/rear pair first (1+2, 3+4, 5+6), then the three sections at the span seams. For extra strength, a strip of glass cloth and epoxy across each joint on the inside of the shell, where it is never seen.
3. **Finish.** Fill the seam lines, prime and paint.

## Mounting

- **Front band:** two strips of 12 mm 3M VHB tape on the solid front band. The 1.5 mm tape gap is built into the underside.
- **Back edge:** run a 3 mm bead of PU adhesive (Sikaflex or similar) along the shell's back edge, the edge of the shell that sits on the car along the line where the underside leaves it, then press the spoiler on. It sits on the car with the same 1.5 mm gap, so the bead spreads to a thin, even seal along the edge and a little way up inside the shell.
- **Fins:** a thin bead or 6 mm tape on the edges that touch the pillars.

## Checks on the delivered files

`src/p3_validate.py` checks every part and pin, and stops if a check fails. Results are in `out/validation.json`.

- **Meshes:** all watertight, with consistent winding, one body each, no self-intersections and no zero-area faces. The print files are checked again as written (float32 STL).
- **Thickness:** {min(th.values()):.1f}–{max(th.values()):.1f} mm at most per part.
- **Fit:** no part overlaps a neighbour or a pin; tongue clearance as above; pin-hole walls at least {V['pin_walls_min_mm']} mm.
- **Seams:** the outer outlines of neighbouring parts match to within a few mm² (from the 0.02 mm decimation).

## Files and rebuilding

- `print/`: the print set, the six parts and the pin (above). The zip `Polo_spoiler_v15_print_package.zip` holds the same seven models plus this README and its figures.
- The scripts also write the parts and the pins in place on the car to `out/assembled/`, for the checks, figures and renders. These working copies are not part of the print set and are not stored in the repository.
- `docs/`: the figures above and `rim_v15.png`, a studio render of the back edge at part 3's end.
- `src/`: the scripts. `sh v15/src/run_all.sh` from `spoiler/` rebuilds everything in about an hour. v15 cores the same outer body as v14 (`v14/out/E4.stl`), which the v14 scripts build first if it is missing.
- **To change the design:** edit `src/layout.py`.
  - Shell: `T_SKIN` (the skin), `OPEN_H` and `K_WALL` (where the opening starts at the front, and its ramp).
  - Joint lands: `LAND_T`, `LAND`, `LAND_BACK`. Cut lines: `C0`, `C1`. Pins on the front/rear cuts: `CUT_PIN_PITCH`.

**Limits.**
- The underside comes from a car model built from VW's published dimensions, not from a scan. Dry-fit on the car before gluing, as with earlier versions.
- v11 found that on the owner's own Polo GTI model the rear edge stands 10–30 mm off. If that model is true to the car, refit the underside first; the parts are then rebuilt on it by the same scripts.
"""
open('v15/README.md', 'w').write(text); print('wrote v15/README.md', len(text.splitlines()), 'lines')
