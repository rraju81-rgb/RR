# MANTA top shell: design notes

## 1. Brief

Design **only the top shell** (the one-piece upper bodywork) of an endurance
prototype, inspired by the manta ray, for both top-class rule sets:
**LMH** (Le Mans Hypercar) and **LMDh** (Le Mans Daytona h).

The floor, plank, splitter, diffuser, survival cell, suspension and wheels are
out of scope. They appear in renders only as grey reference geometry. The
deliverable is the skin you could lift off the car (or put on a stand as a display
piece): nose, front fenders, canopy, sidepod tops, rear fenders, rear deck and
engine-cover fin. The rear wing, endplates and mirrors are designed too, but are
exported as separate optional parts.

## 2. From manta to bodywork

A manta is a flying wing: a wide, thin disc with a raised dorsal body, two
forward cephalic fins either side of a terminal mouth, five gill slits a side, a
small dorsal fin and a whip tail. Each element maps to something the car needs.

| # | Manta anatomy | MANTA top shell | What it does on the car |
|---|---|---|---|
| 1 | Cephalic fins (the two forward "horns") | Narrow blades that continue the front-fender crests forward to the very nose, finished in a contrast colour | Frame the main intake. They act as fences that keep the fender-top flow attached and stop it spilling into the mouth |
| 2 | Terminal mouth | Full-width intake between the horns, below a set-back upper lip, with the (separate) splitter as its lower lip | Radiator / brake cooling intake; air exits through the gills and the wheel-well vents |
| 3 | Five gill slits per side | Five curved slots over each front wheel (332 cm2 per side) with dark liners | The **mandatory openings above the front wheels** (wheel-well pressure relief, anti-lift) |
| 4 | Pectoral-fin leading edge | Thin swept edge from horn root to fender corner, with a light blade, overhanging an open wheel-well inlet | Headlight signature; feeds the front wheel well. The edge continues past the front wheel as an overhang above the wheel-well exit / radiator inlet |
| 5 | Dorsal body hump | Teardrop canopy (black glazing) rising from a flat "head" | Closed cockpit; windscreen and side glass |
| 6 | Pale shoulder patches | Swept white chevrons on the sidepod tops | Livery cue that makes the plan view read as a manta |
| 7 | Dorsal fin and whip tail | Engine-cover fin from the roof to a tail spike at the rear-most point | The **mandatory engine-cover fin** (yaw stability, anti-lift when sideways) |
| 8 | Pectoral-fin tips and trailing edge | Rear fenders sweep back into pointed tips; the deck between them ends in a concave crescent | Clean separation line at the tail; tips carry the endplates |
| 9 | Crescent planform | Optional single-element crescent wing with Gurney, hung from the fin and bridging the fin tips | Rear downforce and balance adjustment (one adjustable element) |

In plan view the shell is one continuous wing edge from the horns to the fin
tips: no notches behind the front wheels. The wheel-well exits sit under the
overhang, as gills sit under a manta's fin.

## 3. One design, two rule boxes

Everything is authored once in an LMDh-sized reference frame and mapped into
each class envelope (`manta/design.py`, `Variant.mx` / `Variant.mz`):

* **Longitudinal:** stations are mapped piecewise-linearly between the front-most
  point, the two axles and the rear-most point. That absorbs LMH's shorter
  overall length (5000 vs 5100 mm) and wheelbase (3100 vs 3148 mm) without
  re-drawing anything.
* **Vertical:** heights up to 800 mm (fenders, deck, wheel arches) are untouched,
  because they are set by the tyres, which are identical in both classes. Everything
  above 800 mm is stretched so the reference 1060 mm limit lands on the class limit.
  The LMH package therefore gets a taller canopy, fin and wing (1145 mm vs 1056 mm), as LMH cars do.

| | LMDh | LMH |
|---|---|---|
| Front overhang / wheelbase / rear overhang | 1000 / 3148 / 952 mm | 980 / 3100 / 920 mm |
| Roof height above reference plane | 1050 mm | 1137 mm |
| Front / rear track | 1650 / 1610 mm | 1650 / 1610 mm |
| Wheel centre above reference plane | 300 F / 290 R mm | same |
| Frontal area (shell + aero) | 1.46 m2 | 1.54 m2 |
| Skin area | 13.6 m2 | 13.6 m2 |

## 4. Regulation and packaging checks

`manta/checks.py` runs these on every build (`scripts/generate.py`, `pytest`), and
writes them to `exports/<class>/report.json`:

| Check | LMDh | LMH |
|---|---|---|
| Overall length | 5097 (max 5100) | 4998 (max 5000) |
| Overall width | 1998 (max 2000) | 1998 (max 2000) |
| Height above reference plane | 1056 (max 1060) | 1145 (max 1150) |
| Wheelbase | 3148 | 3100 (max 3150) |
| Wheels covered in plan view (except the mandatory louvres) | 100 % | 100 % |
| Tyre clearance, straight with +40 mm bump | 17 mm (min 15) | 17 mm |
| Tyre clearance, 12 deg lock with +15 mm bump | 18 mm (min 15) | 17 mm |
| Louvre area over each front wheel | 332 cm2 (assumed min 160) | 332 cm2 |
| Engine-cover fin side area | 0.27 m2, roof to x = 4099 | 0.34 m2, roof to x = 4019 |
| Helmet headroom (indicative 95th-percentile driver) | 51 mm | 132 mm |
| Skin manifold, no degenerate faces | yes | yes |
| Left/right symmetry | exact | exact |
| 3 mm solid watertight | yes | yes |

The tyre envelope is a 710 mm tyre with rounded 45 mm shoulders, steered about the
wheel centre and raised by the bump travel. Every vertex of the skin must stay at
least 15 mm outside it.

**Sources and the caveat.** The FIA rule books (LMH and LMDh Technical
Regulations, Art. 3) could not be downloaded from the build environment
(network policy). The envelope numbers were cross-checked against published data:
Porsche 963 (5100 x 2000 x 1060 mm, 3148 mm wheelbase), Toyota GR010 Hybrid
(4900 x 2000 x 1150 mm), class summaries (LMH <= 5000 x 2000 mm), and Michelin
(29/71-18 F / 34/71-18 R for LMDh and post-2022 LMH; 31/71-18 all-round for legacy
4WD LMH). The **160 cm2 minimum louvre area** is an assumption carried over from
earlier ACO prototype rules. **Verify every figure against the current FIA
Technical Regulations before using this beyond concept work.** All numbers live
in one place, `manta/regs.py`.

Rule areas this concept does not cover: windscreen and visibility geometry,
door-aperture templates, lighting performance, mirror field of view, bodywork
deflection tests, and the aero performance window. In LMDh the greenhouse
belongs to the chassis supplier (Dallara, Ligier, Multimatic or Oreca), so fit
the canopy surface to that supplier's hard points.

## 5. How the surface is built

* **Crown:** a height field `H(x, y)` = deck + dorsal body + front-fender ridges
  + rear-fender ridges. Each bump uses the profile `(1 - t^n)^m`, which meets
  the deck *tangentially*. The surface is therefore C1 everywhere, with no
  smooth-max creases. A zebra-stripe check showed continuous reflection lines
  across every fillet.
* **Plan outline + skirt:** the crown stops at a plan outline (horns, pectoral
  edge, fenders, crescent tail). Along it a skirt rolls over a shoulder radius
  into a side wall (with undercut on the sidepods) down to a lower edge. Each
  control point sets that edge absolutely (wheel arches, splitter level) or as a
  lip depth below the crown edge (thin overhangs), and the two modes blend
  smoothly between points. Arches never cut into the shoulder roll, so the fender
  always reaches its full plan width.
* **Mesh:** constrained Delaunay triangulation of the plan (gill slots as holes;
  glazing and livery as region boundaries), refined so 3-D triangles stay near
  14 mm and get finer on steep or tight areas. Two regular vertex rows run along
  the outline. The model is built as a mirrored half, so it is exactly symmetric.
  Shading uses analytic normals from the gradient of `H`.
* **Appendages:** the fin and endplates are thin closed "lens" bodies; the wing is a
  lofted inverted cambered section (crescent sweep, 9.5 deg incidence, 14 mm Gurney).

## 6. Aerodynamic intent (qualitative, not yet simulated)

* The low, wide "head" and thin pectoral edges keep frontal area modest
  (1.46 m2 for LMDh, shell plus wing), while the horns fence the fender tops.
* Gill louvres and the long wheel-well exits under the overhang extract
  wheel-well air. That relieves front lift and gives front-axle balance trim.
* The sidepod undercut (up to 22 deg) feeds clean air to the rear of the car and
  the floor edge.
* The crescent trailing edge and wing tips sweep back to the endplates, which
  spreads the wing loading toward the tips, as a manta's fin does.

**Next steps:** run CFD on `*_top_shell_surface.stl` with a floor and wheels (for
example OpenFOAM snappyHexMesh at 250-330 km/h with ride-height sweeps). Then
correlate in a wind tunnel, and tune toward the ACO target window (about L/D 4
in the reference configuration) through the gill count, overhang lip depth and
wing incidence.

## 7. Manufacturing and the display piece

* **Full-scale part:** `generate.py` also writes a closed 3 mm skin
  (`*_top_shell_solid_3mm.stl`). With a typical race-car CFRP layup of about
  2.2 kg/m2, the 13.6 m2 skin comes to about **30 kg**, before inserts, closeouts and
  the fin.
* **Display model, like a "winner's shell" on a stand:** `*_display_1to5.stl`
  is the shell at 1:5 (about 1020 x 400 x 200 mm), watertight, with 2.5 mm walls.
  Wall thickness reduces locally where the curvature radius is smaller than
  the wall, so the inside never folds. The fin is a separate closed body that
  slicers merge. This is too big for most desktop printers: split it at the
  cockpit, or print 1:10 with `--print-scale 10 --print-wall 2`.
* **Finish used in the renders:** deep ocean blue with white horns and shoulder
  chevrons, black glazing, fin, wing and gill liners, raw-carbon inside.

## 8. Known limitations

* Concept-level surfaces as triangle meshes; there is no NURBS/STEP export yet. Rebuild
  class-A surfaces in Alias/CATIA from the meshes, or extend `manta/` with an
  OpenCascade B-spline fit of the same height field.
* No door shut lines, fasteners, quick-release points, or inner wheel-arch liners.
* Lights are represented as emissive zones only.
