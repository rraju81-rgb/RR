# 390 Adventure indicator cap

A bent stainless sleeve that slides over a loose or broken indicator head on a 2025+ KTM 390 Adventure, grips it through a foam liner and bolts to the screw boss beside the lamp socket. The original lamp keeps working, so you don't have to buy a new indicator. The same part fits the left and right lamps. Front and rear use the same lamp, so only the fixing ear may need to differ between them.

Drawing **IC-390A-01 rev A**. Status: **fit-check stage**.

> **Rev A is built on lamp and mount sizes scaled from product photos, not measured on a bike.**
> Take the ten measurements below and make the card fit check before you cut any metal.

![Cap on the lamp](docs/fig_iso.svg)

| | |
|---|---|
| Material | 1.5 mm stainless 304 (options: 2.0 mm aluminium 5052-H32, 3D-printed, forged carbon) |
| Mass | 68.6 g stainless, 31 g aluminium, 14 g forged carbon |
| Formed size | 85.5 × 53.9 × 24.6 mm |
| Flat blank | 118.3 × 84.4 mm, 8 bends, 563 mm of cut |
| Fixing | 1 × M5 into the existing boss beside the socket, slotted ±2 mm |
| Left / right | same part, turned over |

Interactive 3D review page: [`docs/design-review.html`](docs/design-review.html). Open it in a browser; it needs internet access to load three.js.

## How it holds the lamp

The stock head sits on a flexible rubber stalk. When the stalk tears or its mount cracks, the head droops or hangs on its wires. The cap takes the stalk out of the load path: the cap holds the head, and one screw holds the cap.

![Section through a keeper tab](docs/fig_section.svg)

- **Grips four faces, leaves the lens open.** Top, bottom, back and tip are steel. The lit face of the lens is never covered.
- **Foam does the gripping.** Self-adhesive EPDM: 1 mm on the plates, 2 mm on the back wall, 3 mm at the tip, squeezed by a fifth to a third. It takes up the lamp's size spread and vibration and keeps steel off the plastic.
- **Tabs stop it sliding off.** Four keeper tabs hook 2 mm over the sloped strip above and below the lens. They touch only that strip.
- **One screw takes the load.** The ear sits on the boss beside the socket and reuses its screw.
- **Same part on both sides.** The cap is symmetric top to bottom. Front and rear use the same lamp, so the channel is identical; only the ear changes if their screws sit in different places.

## Measure first

![What to measure](docs/fig_measure.svg)

| Ref | What | Model value (mm) | How to measure |
|---|---|---|---|
| M1 | Head length | 74 | Root face of the head (where the stalk enters) to the tip, along the black housing |
| M2 | Head height | 20 | Top face to bottom face of the head |
| M3 | Housing depth at the root | 26 | Lens/housing joint line to the back face, at the root end |
| M4 | Housing depth at the tip | 14 | The same, at the tip |
| M5 | Lens edge chamfer | 4.5 × 3.0 | The sloped strip above the lit face: how far it runs back (a) and drops (b) |
| M6 | Stalk length | 8 | Root face of the head to the face of the socket (clearance only) |
| M7 | Boss face position | 8 | Along the lamp, from the head's root face back to the face the ear will sit on |
| M8 | Screw distance behind the lamp | 14 | Back face of the head (at the root) to the screw centre, square to the lamp |
| M9 | Screw height | 0 | Screw centre above (+) or below (−) mid-height of the head |
| M10 | Screw | M5 | Thread and length of the screw already in that boss |

M1 to M5 set the channel; M7 to M9 place the ear. Put your numbers in [`cad/params.py`](cad/params.py) and rebuild. If the front and rear screws give different M7 to M9, make two versions; they share the same blank apart from the ear. The build refuses, with a reason, if the ear can't reach the screw you entered.

## Make it

1. Update `cad/params.py` and run `python3 build.py`. All 16 checks must pass.
2. Print [`out/template_1to1.pdf`](out/template_1to1.pdf) at 100 %, check the 100 mm bar, glue it to 1 mm card, cut, fold and try it on the lamp.
3. Laser cut [`out/cap_blank.dxf`](out/cap_blank.dxf), layer `CUT` only, in 1.5 mm stainless 304. Deburr.
4. Bend B1 to B8 in order. B7 and B8 form a channel 21.6 mm inside: use a gooseneck punch, or bend over a 21.6 mm form block in a vice.
5. Finish: bead blast and black textured powder coat to match the lamp body, or leave it brushed.

![Flat blank](docs/fig_blank.svg)

| Bend | Feature | Direction (outside face up) | Angle | Length | Allowance |
|---|---|---|---|---|---|
| B1–B4 | Keeper tabs | away from you | 35.0° | 12.0 | 1.30 |
| B5 | Tip wall | away from you | 80.8° | 17.0 | 3.00 |
| B6 | Ear | towards you | 80.8° | 17.0 | 3.00 |
| B7, B8 | Top and bottom plates | away from you | 90.0° | 76.5 | 3.35 |

Bend allowance = angle × (R + K·t), inside radius 1.5 mm, K 0.42. If your bend shop works to a different K-factor, change it in `params.py` and rebuild: the inside sizes stay the same and the blank adjusts.

### Parts per lamp

| Qty | Item |
|---|---|
| 1 | Cap, laser cut and bent |
| 1 | EPDM closed-cell foam tape, self-adhesive, 1 mm (plates and tabs) |
| 1 | EPDM foam tape, 2 mm (back wall) |
| 1 | EPDM foam tape, 3 mm (tip wall) |
| 1 | Stainless button-head screw M5, the original length plus 3 mm |
| 1 | Stainless washer M5, 12 to 15 mm outside diameter |

## Fit it

1. If the head has torn off its stalk, repair the wiring first and check that it flashes.
2. Stick the foam strips inside the cap, not on the lamp.
3. Hold the head in its normal position and slide the cap on from the tip until the ear meets the boss. The tabs drop over the sloped edge of the lens.
4. Fit the screw and washer through the ear slot. Snug it, about 2 N·m for a screw into plastic. No threadlocker in plastic; it can crack the boss.
5. Push the lamp tip in every direction: it should not move. Check from in front of and behind the bike that the whole lens lights.

## 3D-printed version: print flat, then fold

![Flat part, its underside, and the folded cap](out/print/preview.png)

A plastic version you can print flat and fold into the cap. Every bend line has a V-groove cut almost through the plate. The thin web left under each groove is the hinge, and the groove's angle matches the bend, so **each fold stops at the right angle when its groove closes**. The inside of the folded part matches the steel version, so it fits the lamp and liner the same way.

![How a V-groove folds](docs/fig_groove.svg)

| | |
|---|---|
| Print this | [`out/print/cap_print_flat.stl`](out/print/cap_print_flat.stl), already lying outside face down |
| Reference | [`out/print/cap_print_folded.stl`](out/print/cap_print_folded.stl), what it becomes after folding (don't print it) |
| Flat size | 123.5 × 91.5 × 2.4 mm, 18.7 g |
| Folded size | 86.4 × 55.5 × 26.4 mm (walls 2.4 mm instead of 1.5, so 1.8 mm bigger outside; same inside) |

### Print settings

- **Material:** PETG or ASA. Avoid PLA: it cracks at the folds and softens in the sun.
- **Layers:** 0.2 mm, so each 0.6 mm web is exactly 3 layers.
- **Walls:** solid; 100 % infill, 4 or more perimeters.
- **Supports and orientation:** no supports. Print it as exported, outside face down. The ear's groove is on the underside; its sides slope about 40°, which prints fine.
- **Optional:** set the bottom-layer line direction across the two long grooves (B7, B8); lines that cross a hinge are stronger.

### Fold it

1. Warm one groove at a time with a heat gun, or dip it in hot water (about 85 °C for PETG), until it bends easily.
2. Fold until the groove closes, then hold it while it cools. Grooves on the top face fold up towards you; the ear groove (B6) is underneath and folds down.
3. Fold in this order: tabs B1–B4, tip wall B5, ear B6, then the two long plates B7 and B8.
4. Run thin CA glue or epoxy into each closed groove from the inside. The web alone is a hinge; the glue makes the corners rigid.
5. Fit the foam liner and the screw as for the steel cap. Use a screw 4 mm longer than the original (2.4 mm ear plus washer).

| Groove | Feature | Fold | V angle | Opening (mm) | On | Fold direction |
|---|---|---|---|---|---|---|
| B1 | Top Tab1 | 35.0° | 37.0° | 1.20 | top | up, towards you |
| B2 | Top Tab2 | 35.0° | 37.0° | 1.20 | top | up, towards you |
| B3 | Bottom Tab1 | 35.0° | 37.0° | 1.20 | top | up, towards you |
| B4 | Bottom Tab2 | 35.0° | 37.0° | 1.20 | top | up, towards you |
| B5 | Tip | 80.8° | 82.8° | 3.17 | top | up, towards you |
| B6 | Ear | 80.8° | 82.8° | 3.17 | underside | down, away from you |
| B7 | Top | 90.0° | 92.0° | 3.73 | top | up, towards you |
| B8 | Bottom | 90.0° | 92.0° | 3.73 | top | up, towards you |

All grooves are 1.8 mm deep, leaving a 0.6 mm web. They are cut 2° wider than the fold so slight over-extrusion can't stop a fold short. `python3 printed.py` rebuilds this version and runs the fit checks on the folded result (all pass), plus print checks: web thickness, narrowest groove against the nozzle width, bed size, and a closed-mesh check on both STLs.

## Carbon-fibre version: split mould

![The mould closed, opened, and the cap sliding off the middle mould](out/mould/preview.png)

A three-piece mould for making the cap in forged carbon. It is split the way the part looks from above with the lug at the top: a **top piece** (the back), a **middle mould** (the inside) and a **bottom piece** (the front).

The carbon part is the first model (1.5 mm wall, same inside, same fit) with the bent-out fixing ear replaced by a solid lug in the same place, on the same screw:

- 5 mm thick, with a round end (R8.5) around the screw;
- the same 5.5 × 9.5 mm slot, so you keep the ±2 mm adjustment;
- at least 3.75 mm of wall around the slot.

It needs an M5 button-head screw 6 mm longer than the original, with a washer. The finished part weighs about 14 g, against 68.6 g for the stainless cap. The steel, aluminium and printed versions keep the bent ear.

| Piece | Forms | Comes off |
|---|---|---|
| Top piece | the back of the cap, the lug, the top and bottom faces, and the tip end | backwards, away from the lamp |
| Middle mould | every inside surface, including under the keeper tabs, plus the lug's slot (a pin on an arm that runs behind the back wall) | last: the cap slides off it along the lamp, the way it slides off the lamp |
| Bottom piece | the front: the keeper tabs, their rounded corners, and the front edges | forwards |

What comes out of the mould:

- **Keeper tabs:** finished, rounded corners included.
- **Slashes:** the three slashes in each face can't be moulded. They are closed slots across the way both outer pieces come off, so either piece would lock in them. The faces come out plain. Cut the slashes afterwards if you want them (3 mm wide, centred 28, 38 and 48 mm from the root face, at 60° to the lamp axis; `out/mould/part_carbon.stl` shows them), or leave them off.
- **Corner specks:** two specks of extra carbon, under 1 mm³ each, sit at the back corner of the tip end. The corner relief there leans slightly forwards and would otherwise hook the top piece. Leave them.

The block is 113.5 × 77.9 × 64.6 mm:

| Piece | Size (mm) |
|---|---|
| Top piece (wraps round the tip end) | 113.5 × 77.9 × 64.6 |
| Bottom piece | 99.5 × 22.9 × 64.6 |
| Middle mould | 121.5 × 52.3 × 27.6 |

Hardware: 4 × M6 bolts 90 mm long (or threaded rod) with washers and nuts, and 2 × 6 mm dowel pins. Two keys on the middle mould sit in notches in the top and bottom pieces, so it can't slide while the mould is shut.

![Plan and section of the mould](docs/fig_mould_section.svg)

### Making the mould

- **3D print:** resin (SLA) gives the best surface. On FDM, use PETG or ASA at 0.12 mm layers, then sand (400 to 1200 grit) and seal with a thin epoxy coat. Use room-temperature-cure epoxy in printed moulds; they soften around 60 °C.
- **Print orientation (already set in the STLs):** the top piece lies on its back and the bottom piece on its front, both with the cavity facing up. The middle mould lies on its front face.
- **The slot pin:** the pin on the middle mould's arm sticks out 5 mm sideways when printed. Give it a small support, or print the middle mould in resin.
- **CNC:** machine it from aluminium using the STEP files (assembly position, same coordinates as the part). Hot-cure resin or prepreg needs an aluminium mould.
- **Release:** 3 to 5 coats of mould wax, then PVA. Nothing has draft, so the release agent matters.
- **Handle with care:** the middle mould has two thin ledges (1.5 × 2.3 mm) at the tip end that fill the gaps between the tip wall and the plates.

### Moulding forged carbon

Work with the top piece lying on its back, cavity up.

1. Mix the charge: about 10.4 g of chopped carbon tow (10 to 25 mm long) and 6.7 g of laminating epoxy. That includes a fifth extra for flash.
2. Wax and PVA every piece. Pack wetted fibre into the top piece's lug pocket and over the floor of its cavity: that floor becomes the back wall.
3. Lower the middle mould in, handle outside the block. Its slot pin presses down into the lug. Push it down onto the fibre.
4. Fill the two 1.5 mm gaps either side of the middle mould (they become the top and bottom faces) and the gap at the tip end. Overfill rather than underfill. These gaps run the same way the mould closes, so closing doesn't squeeze them. Pack them firmly with short, well-wetted tow, or slide in strips of wetted carbon cloth.
5. Heap fibre over the front edges where the keeper tabs go. Close the bottom piece on the dowels and tighten the four bolts evenly. Excess resin runs into the groove and out of the ends.
6. Cure as the epoxy says, typically 24 h at room temperature. Then demould:
   - unbolt and lift the bottom piece off;
   - lift the middle mould, with the cap on it, out of the top piece;
   - hold the middle mould by its handle and slide the cap off along the lamp, towards the tip end.
7. Finish: trim the flash, cut the slashes if you want them, then sand and clear coat with a UV-resistant lacquer.

For a woven look, lay one ply of 2×2 twill on the cavity faces before the forged fill.

`python3 mould.py` rebuilds the mould from `params.py`, so it follows any change to the lamp measurements. It re-runs the checks (28 of 28 pass):

- the finished carbon part passes the same fit checks as the steel cap, plus rules for carbon: wall at least 1.5 mm, inside radius at least 1 mm, at least 3 mm of lug around the slot, lug at least 4 mm thick;
- the cavity contains all of the finished part, and the only extra material is the slashes and the two corner specks;
- each piece is one valid solid;
- no two pieces overlap, and pieces plus part fill the block with no voids;
- each step clears: bottom piece off, top piece off (in either order), cap slides off the middle mould. The same paths in reverse are the loading steps.

## Files

| Path | What |
|---|---|
| `cad/params.py` | Every dimension and design choice. Edit this. |
| `cad/build.py` | Rebuilds the part, runs the checks, writes `out/` |
| `cad/model.py`, `cad/sheetmetal.py` | Cap geometry; a small fold/unfold sheet-metal kernel on CadQuery |
| `cad/drawing.py`, `cad/figures.py`, `cad/page.py` | Drawings, figures and the review page |
| `out/cap_blank.dxf` | Laser profile (layer `CUT`), bend lines, notes |
| `out/cap_formed.step`, `out/cap_blank.step` | Formed part and flat blank |
| `out/cap_formed.stl` | Formed part as a mesh in mm: 4,420 triangles, closed and manifold. Print it as a fit gauge; 1.5 mm walls are too thin for a working plastic cap. Preview: `out/cap_formed_stl_preview.png` |
| `out/drawing_formed.pdf`, `out/drawing_blank.pdf` | A3 drawings |
| `out/template_1to1.pdf` | A4 card template at 1:1 |
| `out/alu/` | The same set for 2.0 mm aluminium |
| `out/print/` | 3D-printed version: flat STL with fold grooves, folded STL, checks |
| `cad/printed.py` | Builds the printed version |
| `out/mould/` | Split mould for carbon fibre: top, middle and bottom piece STLs ready to print, STEPs for CNC, assembly, the finished carbon part (STL, STEP), checks |
| `cad/mould.py` | Builds the mould |
| `out/summary.json` | Every derived number and check result |

### Rebuild

```bash
pip install cadquery ezdxf shapely
```

```bash
cd hardware/ktm-indicator-cap/cad
```

```bash
python3 build.py && python3 build.py --alu && python3 printed.py && python3 mould.py && python3 drawing.py && python3 figures.py && python3 page.py
```

PDFs come from the SVGs with `node svg2pdf.js ../out/drawing_formed.svg ../out/drawing_blank.svg ../out/template_1to1.svg` (needs Playwright).

### What the checks cover

`build.py` checks the part against the lamp model on every rebuild: no overlap with the lamp, stalk, socket or boss; the liner gaps; tab clearance and hook depth; that it slides on from the tip without touching; that nothing sits in front of the lens; top/bottom symmetry; and sheet-metal rules for flange length, slot width, hole-to-bend distance and corner radii. These prove the part matches the numbers it was built from. Whether those numbers match your bike is what the measurements and the card check settle.

## References

Bikers Billet sell [front](https://www.bikersbillet.com/product/bikers-billet-ktm-adventure-390-front-indicator-bracket/) and [rear](https://www.bikersbillet.com/product/bikers-billet-ktm-adventure-390-rear-indicator-bracket/) brackets for the 2025 390 Adventure that do the same job, and a rider's [install reel](https://www.instagram.com/reel/DfbhKkZozDg/) shows the black rear version on the bike. This design keeps the idea and changes the details: a foam liner instead of steel on plastic, tabs that touch only the lens edge, a slotted ear with adjustment, and one symmetric part for both sides.

Independent design. Not a KTM part; not affiliated with KTM or Bikers Billet.
