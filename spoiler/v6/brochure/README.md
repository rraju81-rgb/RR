# Brochure: Polo roof spoiler

A two-page A4 brochure for the v6 roof spoiler, branded Carbon 6 Customization and 3D printed by pi.XL 3D Printing.

| File | What it is |
|---|---|
| `Polo_Roof_Spoiler_Brochure.pdf` | The brochure: 2 × A4, with embedded fonts and vector text. |
| `brochure_page1.png`, `brochure_page2.png` | The pages as images (about 2060 × 2920 px), for WhatsApp or Instagram. |
| `brochure.html` | Source of both pages: all text and layout. |
| `img/` | The renders as placed on the pages (made by `prep_images.py` from `../car/renders/`). |
| `assets/` | Carbon 6 logo (white and dark versions), pi.XL logo, QR codes, and fonts with their licence files. |
| `make_qr.py` | Makes the two QR codes. |
| `export.js` | Writes the PDF and the page images from `brochure.html`. |

## Changing the brochure

1. Edit the text in `brochure.html`. If the phone number or Instagram handle changes, also change `make_qr.py` and run it: `python3 make_qr.py`.
2. If the renders changed, run `python3 prep_images.py`.
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
  - About 2–2.5 kg painted. The slicer estimate is 1.9 kg in ASA or 2.3 kg in PETG with 5 walls and 20% gyroid (see `../README.md`), plus primer and paint.
  - 72 h before the first wash.
  - "Made for the Polo" assumes the dry-fit on a real 6R / 6C confirms the fit. The spoiler's underside comes from a car model built from VW's dimension data, not from a scan.
- **Printing:** the PDF is RGB with no bleed. That is fine for an office or digital printer. A print shop may want 3 mm bleed and CMYK, so ask them first.
- **Disclaimers:** the images are labelled as 3D renders. The trademark note (VW, Polo, 3M, VHB) is at the bottom of page 2.

The fonts (Michroma, Space Grotesk, JetBrains Mono) are all under the SIL Open Font License, so they can be embedded and printed freely. The licence texts are in `assets/fonts/`.
