# Brochure: Polo roof spoiler

A two-page A4 brochure for the roof spoiler, branded Carbon 6 Customization and 3D printed by pi.XL 3D Printing. It describes the current build, v9: six equal sections, cored so no wall is thicker than 10 mm, joined with dowel pins and 30° chamfered tongue-and-groove joints.

**Page 1 shows the owner's own car with our spoiler on it.** The owner's photo (`photo/owner_car_original.png`, as received) had a different, larger wing on the car. That wing was removed and our spoiler was rendered into the photo from its 3D model, from a camera solved to match the photo (`photo/owner_car_with_spoiler.png`; how it is made is in `../car/README.md`, "Owner's photo with the spoiler"). The fine print on page 2 says that the spoiler was added digitally and that the other images are renders.

`prep_photo.py` crops the composite for the hero box. The photo received is only 510 × 392 px, so it is upscaled 4× and looks soft in print. With the full-size original from the phone, the composite has to be redone at that size (the camera carries over; the old wing's outline needs tracing again), then run `python3 prep_photo.py` and export again.

The page 2 car pictures are outdoor renders styled after that photo: blue metallic paint, gloss-black spoiler, mirror caps and 18" multi-spoke wheels, smoked tail lamps, a black diffuser with twin exhaust, under an overcast sky by a lake. The car is still our own Polo-class 3D model (`../car/`), not Volkswagen's CAD data, and it carries no VW badges. The sky and asphalt are Poly Haven CC0 assets (`../car/env/`).

| File | What it is |
|---|---|
| `Polo_Roof_Spoiler_Brochure.pdf` | The brochure: 2 × A4, with embedded fonts and vector text. |
| `brochure_page1.png`, `brochure_page2.png` | The pages as images (about 2060 × 2920 px), for WhatsApp or Instagram. |
| `brochure.html` | Source of both pages: all text and layout. |
| `img/` | The images as placed on the pages: `hero_owner_car.jpg` from the owner's photo with the spoiler composited in (`prep_photo.py`), and the renders `side_blue`, `top_rear_blue`, `detail_fin_blue` (`blend_photo.py`) and `joints_v9` (`blend_scene.py`, one joint opened: the tongue and its two pins), made by `prep_images.py` from `../car/renders/`. |
| `photo/` | The owner's photo of their car, as received (`owner_car_original.png`), and with the old wing replaced by our spoiler (`owner_car_with_spoiler.png`). |
| `assets/` | Carbon 6 logo (white and dark versions), pi.XL logo, QR codes, and fonts with their licence files. |
| `make_qr.py` | Makes the two QR codes. |
| `export.js` | Writes the PDF and the page images from `brochure.html`. |

## Changing the brochure

1. Edit the text in `brochure.html`. If the phone number or Instagram handle changes, also change `make_qr.py` and run it: `python3 make_qr.py`.
2. If the renders changed (`sh ../car/src/render_photo.sh` from `spoiler/`), run `python3 prep_images.py`.
3. Export with `NODE_PATH=$(npm root -g) node export.js`. This needs Node.js with Playwright and its Chromium.

Run steps 1 and 3 from this folder. `prep_images.py` works from any folder.

## Check before you share or print it

- **Contact details** were taken from the Carbon 6 business card files:
  - +91 99006 11996
  - carbon6customization@gmail.com
  - Instagram @c6_customization
  - pi.XL: @pi.xl3dprinting
  - Address: near Yelachenahalli Metro, opposite Pillar No. 114, Bangalore
- **QR codes:** WhatsApp opens https://wa.me/919900611996 and Instagram opens https://instagram.com/c6_customization. Both were decoded from the exported page images, but scan them once with a phone too.
- **Product claims:**
  - PETG or ASA.
  - About 1.5–2 kg painted. That is an estimate for v9 (2,180 cm³ of part, 4 walls and 20–25% gyroid: about 1.4 kg in ASA or 1.7 kg in PETG), plus primer and paint. Check it against your slicer.
  - 72 h before the first wash.
  - "Made for the Polo" assumes the dry-fit on a real 6R / 6C confirms the fit. The spoiler's underside comes from a car model built from VW's dimension data, not from a scan.
- **Printing:** the PDF is RGB with no bleed. That is fine for an office or digital printer. A print shop may want 3 mm bleed and CMYK, so ask them first.
- **Disclaimers:** the fine print says that page 1 is a photo with the spoiler added digitally, and that the other images are 3D renders. The trademark note (VW, Polo, 3M, VHB) is at the bottom of page 2.
- **The page-1 photo:** it is the owner's car, but the spoiler on it is a render: no printed part was photographed. Replace it with a real photo once a printed spoiler is fitted.

The fonts (Michroma, Space Grotesk, JetBrains Mono) are all under the SIL Open Font License, so they can be embedded and printed freely. The licence texts are in `assets/fonts/`.
