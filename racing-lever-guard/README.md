# Racing Lever Guard: universal carbon + CNC lever protector

![Racing lever guard on a handlebar](docs/renders/hero.png)

Parametric CAD for a universal **racing handguard / brake and clutch lever protector**, modelled on the
[Darpan Sarvan "Racing Handguard/Lever Protector Carbon Finish Universal Fit For All Bikes"](https://darpansarvanstore.com/product/racing-handguard-lever-protector-carbon-finish-universal-fit-for-all-bikes/):
an anodised CNC-aluminium bar-end mount and arm with a carbon-finish guard blade that fits any
7/8" (22.2 mm) handlebar with an open end. The blade is 6 mm thick with a gusset filling the inside
of the bend. An optional moulded wind guard, styled after motocross handguards, clamps onto the
blade and slides along it.

| ![Wind guard seen from the front](docs/renders/wind_guard_front.png) | ![Exploded view](docs/renders/exploded.png) |
|---|---|
| ![Gusset inside the bend](docs/renders/bend_gusset_detail.png) | ![Wind guard clamp from below](docs/renders/wind_guard_mount_detail.png) |

![Anodise colours: red, blue, gold, black, silver](docs/renders/colours.png)

## About the reference product

The store page could not be opened from the build environment (its network policy blocks the
site), so its content was read through web-search results. The listing gives:

- price ₹1,499; "made from high-quality CNC aluminum and carbon fiber pattern"
- universal fit: Honda, Yamaha, KTM, Royal Enfield, Kawasaki and others; "plug-and-play
  installation with all necessary fittings included"
- colours black, blue, gold, red, silver

It publishes **no dimensions, drawings or bar sizes**. The geometry here follows the standard
construction of this product class (bar-end adapter, indexed arm, carbon blade in front of the
lever), with sizes taken from comparable universal guards (see [Research](#research-dimensions-of-comparable-guards)).
Every dimension is one named parameter in `cad/lever_guard.py`, so the shape can be matched to the
real part once it is in hand: measure it or send close-up photos, change the numbers, rebuild.

## What is in this folder

| Path | Contents |
|---|---|
| `exports/step/` | STEP for every part, plus the assembled guard with and without a reference handlebar (CNC, CAD) |
| `exports/stl/` | STL for every part, already turned to its 3D-print orientation |
| `docs/drawings/lever_guard_drawings.pdf` | 6 dimensioned A3 sheets: general arrangement, adapter, arm, blade with gusset, expander set, wind guard and clamp |
| `docs/renders/` | Rendered views, including all five anodise colours |
| `docs/viewer.html` | Interactive 3D viewer: turn the arm in its 10° steps, slide the blade and the wind guard, change colour, explode |
| `exports/summary.json` | Key numbers, masses and fit-check results written by the build |
| `cad/lever_guard.py` | The parametric model (all parts, hardware and reference bike parts) |
| `cad/build.py` | Fit checks and STEP/STL export |
| `cad/drawings.py` | Drawing generator (hidden-line projections of the solids, dimensioned) |
| `tools/` | Scene export, viewer template and the headless render script |

## How the design works

| No. | Part | Material / finish | Qty per side | Mass |
|---|---|---|---|---|
| LG-01 | Bar-end adapter: Ø32 body, Ø12.4 spigot, 36-tooth face serration | 6061-T6, hard anodised (black / blue / gold / red / silver) | 1 | 25.9 g |
| LG-01b | Adapter without spigot, for bars with a threaded OEM bar-end insert | 6061-T6, hard anodised | (alternative) | 24.5 g |
| LG-02 | Guard arm: serrated hub + neck carrying the blade | 6061-T6, hard anodised | 1 | 37.8 g |
| LG-03 | Guard blade, 6 mm, with gusset inside the bend | 3K 2×2 twill carbon, forged-carbon gusset, gloss clear | 1 | 33.9 g |
| LG-03b | Guard blade, 8 mm, printable | PA12-CF / PETG-CF, carbon hydro-dip | (alternative) | 31.4 g |
| LG-04 | Expander sleeve S / M / L | TPU 95A or NBR 70A | 1 | 2–3 g |
| LG-05 | Expander cone nut S / M / L, M6 | 6061-T6 or zinc-plated steel | 1 | 2–4 g |
| LG-06 / 06b | Wind guard shell, right / left (mirror pair; optional) | HDPE or PP, injection moulded, colour to order (or printed ASA / PA12) | 1 | 55 g |
| LG-07 | Wind guard clamp half, same part used twice (optional) | 6061-T6, hard anodised | 2 | 14.9 g each |
| H1 | Socket cap screw M6 × 45, ISO 4762 | A2-70 or 10.9 black | 1 | |
| H2 | Button head screw M5 × 14, ISO 7380 (M5 × 16 with LG-03b) | A2-70 | 2 | |
| H3 | Washer M5, ISO 7089 | A2 | 2 | |
| H4 | Socket cap screw M4 × 25, ISO 4762, fitted from below (wind guard) | A2-70 | 2 | |
| H5 | Nyloc nut M4, DIN 985, captive in the upper clamp half (wind guard) | A2 | 2 | |
| H6 | Compression sleeve Ø6 / Ø4.2 × 3, pressed into the shell's flange (wind guard) | aluminium | 2 | |

About 123 g per side with the carbon blade and steel screws, 218 g with the wind guard.

1. **Mount.** The adapter sits on the open bar end. Inside the bar, one M6 bolt pulls the cone
   nut into the slit elastomer sleeve, which grips the bar bore. Three sleeve sizes cover bar
   IDs from 13 to 19 mm. Bikes that keep a threaded OEM insert use the flat adapter LG-01b and a
   bolt into that thread instead.
2. **Angle.** Adapter and arm meet on a 36-tooth Hirth face serration (90° teeth, radial crests
   and roots). The arm seats only in **10° steps**, so it cannot creep round when the guard is
   hit. The CAD check confirms zero overlap in every step and a clash half a tooth out.
3. **Reach.** The blade is bolted to the arm through a 27.3 mm slot: **±5 mm** toward or away
   from the lever.
4. **Blade.** The 6 × 22 mm carbon section turns 87° on an R18 centre line and runs 100 mm
   inboard in front of the lever. The run is toed out 3° so its gap follows a lever that
   converges on the bar. The gap leaves room for the blade to flex in a hit before it can press
   the lever.
5. **Crash strength at the bend.** When the bike falls, the blade is loaded hardest where it
   leaves the arm and turns into the bend. The strip is now 6 mm thick instead of 4 mm, which
   makes it 2.25× as strong all along in the lever plane, where a fall bends it. A gusset also
   fills the inside of the bend. Its edge leaves the seat face on an R4 blend just past the end
   of the arm's neck, follows an R38.3 arc and runs out tangentially 14 mm along the run, so
   there is no corner or step for a crack to start from. It clears the arm at every slot
   position. The section across the bend goes from 6.0 to 9.7 mm, about 2.6× the bending
   strength of a plain 6 mm bend. The straight seat between the end of the arm's neck and the
   gusset cannot take a gusset, because the blade slides ±5 mm along the arm there. It stays a
   plain 6 mm section with the adjustment slot running through it, so it is now the weakest part
   of the blade. It is shortest (under 1 mm) with the blade slid fully toward the lever and up
   to 10 mm long with it slid fully away.
6. **Wind guard.** A moulded shell in the style of a motocross handguard. Its flat flange is held
   between two identical clamp halves that wrap the blade run. From the flange it bends up into
   a shield that stands in front of the hand, convex to the wind and curling back over the
   knuckles. Seen from the front it is tall at the outboard end and sweeps down to a rounded,
   pointed tip past the brake perch. A crease runs diagonally from the outboard top to the tip,
   like the spine on the reference guards; it also stiffens the shell. Two M4 screws, put in
   from below, squeeze the clamp halves onto the blade's top and bottom edges. Their nyloc nuts
   sit captive in the upper half, and two aluminium sleeves in the flange carry the clamp load,
   so the plastic does not creep. Loosen the screws and the guard slides 45 mm along the run;
   tighten them where it sits. There are no holes in the blade, and it fits without taking the
   guard off.
7. **Left and right.** Every part except the wind guard shell is symmetric about the lever plane,
   so the clutch-side guard is the same set of parts with the arm turned over. Like any
   handguard, the shell comes as a mirror-image pair (LG-06 right, LG-06b left).

## Key dimensions

| Feature | Value |
|---|---|
| Envelope without the wind guard (along the bar, screw heads to blade tip × ahead of the bar axis × tall) | 123.8 × 89.9 × 32 mm |
| Length along the bar with the wind guard (screw heads to shell tip, guard slid fully outboard) | 252 mm |
| Blade centre-line length | 162.6 mm (35.3 straight + 87° bend on R18 + 100 straight) |
| Blade section | 22 × 6 mm carbon (22 × 8 mm printed) |
| Section across the bend | 9.7 mm with the gusset (6.0 mm plain) |
| Run covers the lever inboard of the bar end | 90 mm |
| Sticks out past the bar end | 33.75 mm (to the M5 screw heads) |
| Blade face ahead of the bar axis, start of run (slot −5 / 0 / +5) | 57.6 / 62.6 / 67.6 mm |
| Wind guard shell | 230 mm long, 3 mm wall; on the bike 60–101 mm ahead of the bar axis, from 50 mm below to 49 mm above it; slides 45 mm along the run |
| Adapter body / spigot | Ø32 × 12 / Ø12.4 × 6 mm |
| Angle steps | 36 teeth → 10° |
| Fore-aft adjustment | ±5 mm |
| Bar fit | 7/8" (22.2 mm) bars, inside diameter 13–19 mm, or OEM threaded insert |

All dimensions are on the drawings in `docs/drawings/`.

## Fitment ("universal")

| Bar inside diameter | Use | Typical bars |
|---|---|---|
| 13–15 mm | Sleeve S + cone S | Aluminium clip-ons, tapered alloy bars |
| 15–17 mm | Sleeve M + cone M | Thin-wall steel and alloy bars |
| 17–19 mm | Sleeve L + cone L | Steel tubular bars |
| Threaded OEM insert | Flat adapter LG-01b + a bolt that suits the insert thread (often M6, check yours) | Bikes sold with bar-end weights |

- The bar end must be open. Remove the OEM bar-end weight; trim a closed grip end.
- Set the arm on the serration step nearest the lever's angle. The 22 mm tall blade covers the
  remaining ±5° offset.
- Slide the blade until there is **at least 10 mm all round the lever**. With the reference
  sport-bike lever in the CAD the closest gap is 11.3 / 16.3 / 21.3 mm at slot −5 / 0 / +5
  (10.3 / 15.3 / 20.3 mm with the 8 mm printed blade).
- With the wind guard fitted, keep the blade slot at −4 or more. At −5 the clamp's lip comes within
  9.7 mm of the reference lever. With the blade at the middle of its slot, the wind guard keeps
  14.5 mm from the lever, 26 mm from the brake perch and 20 mm from a Ø100 mm gloved-hand
  envelope round the grip, anywhere along its travel.
- The shell reaches 218–263 mm inboard of the bar end (depending on where it is slid) and 101 mm
  ahead of the bar axis. Turn the bars lock to lock and check the fork, fairing, tank, mirrors and
  fluid reservoir before riding. Slide it outboard if anything is close.
- Factory hand guards have to come off first.

## Install

1. Measure the bar's inside diameter and pick the sleeve and cone size (table above).
2. Thread the M6 × 45 bolt through the arm and adapter, then the sleeve, and start it in the cone
   nut. Push the stack into the bar until the adapter seats on the bar end.
3. Turn the arm to the lever's angle, settle it into the serration and tighten the M6 bolt to
   **8 N·m** with medium threadlocker.
4. Fit the blade with the two M5 × 14 screws and washers. Set the gap, then tighten to **4 N·m**.
5. Wind guard (optional): press the two aluminium sleeves into the shell's flange. Hold one clamp
   half above the blade run and one below, with the flange between their front blocks and the
   nyloc nuts in the upper half's pockets. Fit the two M4 × 25 screws from below, slide the
   guard to where you want it and tighten to **2.5 N·m**.
6. Pull the lever through its full travel, use the reach adjuster across its range, and turn the
   bars lock to lock. Nothing may touch the guard, the fairing, the tank or the mirrors.
7. Re-check all torques after the first ride.

## Research: dimensions of comparable guards

| Source | Published figure | Used for |
|---|---|---|
| [Universal carbon-texture lever guard](https://www.amazon.com/Handguard-Motorcycle-Protector-Universal-Modification/dp/B0H3NW88B1) | aluminium with carbon texture, 13–19 mm bars, ~160 mm long | bar-ID range, overall length (blade 162.6 mm) |
| [Ysyqkn lever guards](https://www.walmart.com/ip/17212813508) | aluminium, 175 mm long, bar ID ≥ 17 mm | overall length range |
| [XWYINGAN carbon + aluminium guard](https://www.amazon.com/XWYINGAN-Universal-Handlebar-Protector-Motorcycle/dp/B0F4K9C1HM) | 7/8" bars, 135 mm; a 17.5 cm / 180 g variant | length, mass target |
| [LighTech carbon lever protection](https://www.wrs.it/en/adjustments-e-adapters/374630-carbon-brake-lever-protection-132mm-lightech-yamaha-r1-m-2020-2025-8052393423296.html) | 132 mm from bar-end mount to the lever end; carbon blade, coloured alloy end piece | construction, reach |
| [Voca lever guards](https://maxiscoot.com/en/product/lever-guards-voca-red-291507) | adjustable 130 / 148 mm, 14 mm bar ID | adjustable reach (±5 mm slot) |
| [Stage6 R/T lever guards](https://stage6-racing.com/en/product/lever-guards-cnc-stage6-r-t-set/) | inserts for alloy bars (14–14.5 mm) and steel bars (17–17.5 mm); angle continuously adjustable | sleeve sizes, angle adjustment |
| [R&G universal lever guard](https://www.sportsbikeshop.co.uk/motorcycle_parts/content_prod/666871) | expanding fit, 13–21 mm bar ID | expander concept |
| [Highsider lever protectors](https://www.louis-moto.com/en/highsider-lever-protectors-cnc-black-pair-60152580) | 7/8" and 1" bars, ID 12–22 mm | bar-ID range |
| [Womet-Tech ProGuard](https://tstindustries.com/products/womet-tech-proguard-universal-brake-lever-guard) | 16–20 mm ID, CNC aluminium + Delrin, expansion hardware | expander concept |
| [Oxford racing lever guard](https://firestormmotorcycles.com.au/oxford-delrin-racing-universal-motorcycle-lever-gu) | 22 mm bars, 12–18 mm expansion bolts | bar-ID range |
| [Woodcraft lever guard guide](https://ducatiomaha.com/products/woodcraft-lever-hand-guards) | at least 10 mm clearance round the lever end | clearance rule (CAD check) |
| [Twisted Throttle / R&G carbon guard](https://twistedthrottle.com/shop/protection/lever-guards/rg-racing-carbon-fibre-lever-guard-for-hollow-tube-bars-13-15mm/) | carbon arm for 13–15 mm hollow bars | carbon blade construction |

## Making the parts

**CNC (LG-01, LG-02, LG-05).** 6061-T6: Ø35 bar for the adapter and cone, 15 mm plate
(60 × 34 mm blank) for the arm. The serration can be cut with a 90° V-cutter on a 4th axis or indexed in 10° steps.
Hard anodise after machining in black, blue, gold, red or silver. Break all sharp edges 0.2–0.5 mm.

**Carbon blade (LG-03).** Lay up a 6.0 ± 0.2 mm skin of 3K 2×2 twill (prepreg or wet layup) over a
male tool. Keep the plies continuous round the bend, and fill the gusset with forged (chopped)
carbon in the same cure. Then CNC-trim the outline and slot from the STEP. For a *carbon finish*
on a cheaper part, machine the blade from 25 mm 6061-T6 plate and hydro-dip it with a carbon
pattern. The gusset rules out bending it from strip.

**Wind guard (LG-06, LG-07).** The shell is a moulded part like a motocross handguard. Injection
mould it in HDPE or PP, in any colour, from the STEP files: `06_wind_guard_shell_RH` for the
right side and `06b_wind_guard_shell_LH` for the left. Break the edges R1. For one-offs, print
it (see below). Machine the clamp half from 6061-T6 and anodise it to match the arm; it is a
single part used twice.

**3D print.** For prototypes or low cost:
- `03b_guard_blade_8mm_3dprint.stl`: PA12-CF or PETG-CF, lying flat, 6 walls, 50 % gyroid.
  Hydro-dip or wrap it for the carbon look, and use M5 × 16 screws.
- Wind guard shells `06` / `06b`: ASA or PA12, 100 % infill (3 mm wall). Print with the flange
  flat on the bed and tree supports under the bend and the top edge.
- Adapter, arm and wind guard clamp halves: PA12-CF, 100 % infill, for a test fit only. Ride on
  aluminium parts.
- Sleeve: TPU 95A, 100 % infill.

The STLs are already turned to these orientations.

## Changing the design

```bash
python -m venv .venv && . .venv/bin/activate
pip install cadquery matplotlib
cd cad
python build.py          # fit checks + STEP/STL + exports/summary.json
python build.py --check  # fit checks + summary.json only (leaves STEP/STL untouched)
python drawings.py ../docs/drawings/lever_guard_drawings.pdf
```

The parameters most likely to change when matching the real part, all in `Params` in
`cad/lever_guard.py`:

| Parameter | Default | Effect |
|---|---|---|
| `front_len` | 100 | length of the run in front of the lever |
| `bend_r` | 18 | bend radius (centre line); moves the run toward or away from the lever |
| `front_toe_deg` | 3 | angle of the run relative to the bar |
| `blade_h`, `blade_t` | 22, 6 | blade section |
| `haunch_len`, `haunch_seat_gap`, `haunch_blend_r` | 14, 1, 4 | where the gusset's edge runs out on the run / crosses the seat face / blend radius into the seat face |
| `shell_len`, `shell_crest`, `shell_crease` | 230, 84, (60, −4) | wind guard length, height and crease line (outboard end, tip) |
| `lever_deg` | 30 | lever angle below horizontal; sets "up" and "forward" for the wind guard |
| `clamp_pos` | 15 | wind guard clamp position along the run (15–60 mm from the bend) |
| `body_d`, `pitch_x` | 32, 12 | adapter diameter and length outside the bar |
| `teeth` | 36 | serration teeth (360 / teeth = angle step) |
| `adjust` | 5 | slot travel each way |

The viewer and renders are rebuilt with `tools/scene.py`, `tools/make_viewer.py` and
`tools/render.mjs` (Node + Playwright).

## CAD checks (`cad/build.py`)

All pass for both blade versions:

- every part is one valid solid
- serration meshes with 0.000 mm³ overlap at 0°, 10° and 50°, and clashes half a tooth out
- no unintended overlap between any two parts (threads excluded)
- the blade, gusset included, clears the arm, adapter and screws at slot −5 and +5
- section across the bend 9.7 mm with the gusset against 6.0 mm plain (bending strength ×2.6)
- the gusset's R4 blend starts past the end of the arm's neck even with the blade at slot −5
  (by ≥ 0.17 mm), and its edge is tangent all along
- M6 thread engagement in the cone nut 8.5 mm; M5 engagement in the arm 7 mm (≥ 1.2 d)
- blade ≥ 10 mm from the reference lever at the nominal slot position; adapter, arm and screws ≥ 27 mm
- with the blade at the nominal slot position and the wind guard at either end of its travel,
  the wind guard sits on the blade with no overlap. Its clamp halves bear on the blade edges, and
  it stays ≥ 13.5 mm from the lever, ≥ 26 mm from the perch, ≥ 20 mm from a Ø100 mm gloved-hand
  envelope round the grip and ≥ 45 mm from the grip.
- finger room between grip and blade run ≥ 40 mm
- each sleeve and cone slides into the smallest bar of its range

## Safety

This is a protection accessory, not a certified crash part. Fit it only to bars with sound ends,
check the lever's full travel and the steering lock after fitting, and replace a guard that has
been hit: carbon can crack inside without showing it.
