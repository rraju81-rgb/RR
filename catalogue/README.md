# PITLANE: 2026 catalogue and product images

| File | What it is |
|---|---|
| `PITLANE_Catalogue_2026.pdf` | A 10-page A4 customer catalogue: cover, range overview, product spreads, bundles, fit guide and how to order |
| `images/*.png` | 13 annotated product renders (2400 × 1800) showing how each product works, what it does and its main advantages |
| `images/clean/*.jpg` | The same renders without labels, for listings, Reels and ads |
| `source/` | Three.js scene, render script and catalogue HTML, so you can re-render and rebuild |

The renders are built from the dimensions in the blueprints (`blueprint.pdf`, `SlideRack_Fold_Blueprint.pdf`). The card art is generic and made up for these images. It shows no real brand.

## Product names

The umbrella brand stays **PITLANE**, the name already in the sales pitch. Each product gets a motorsport name that says what it does:

| Working name | New name | Why |
|---|---|---|
| PITLANE SWING (wall rack, swing-out ledges) | **PITLANE GARAGE** | Every card gets its own door, like a pit garage |
| PITLANE SLIDE (wall rack, one piece) | **PITLANE GRID** | Cards line up in lanes, like a starting grid |
| SlideRack Fold 3 / 5 / 6 (tabletop) | **PITLANE PODIUM 3 / 5 / 6** | A tiered desk stand for showing off your best cars |
| Twin (right + left) | **GARAGE Twin**, **GRID Twin** | |
| Fold Duo (3 + 5) | **PODIUM Duo** | |

Alternatives if a name is taken:
- GARAGE: HANGAR, PADDOCK
- GRID: RAIL, LANES
- PODIUM: GRANDSTAND, KICKSTAND

Before you register any name, check it on the IP India trademark search (classes 20 and 28) and check that the domain or social handle is free. Never put "Hot Wheels" in the brand name; use "fits Hot Wheels® cards" only as a compatibility note.

## Rebuilding

```bash
cd source/render && npm ci            # installs three.js
npx http-server -p 8123 . &           # serve the scene
node shoot.mjs <outDir> all both      # every shot, annotated and clean
```

`index.html` expects a `fonts/` folder with the Google Font *Archivo*. The catalogue HTML expects `img/` and `fonts/` next to it. Run `node source/pdf.mjs <abs path to catalogue.html> <out.pdf>` to print it to PDF.
