# pi.XL 3D Printing — website

Large format 3D printing, Bangalore · Instagram [@pi.xl3dprinting](https://instagram.com/pi.xl3dprinting) · pixldprinting@gmail.com
Live: https://pi-xl-static-website.vercel.app/

A fast, dependency-free static site (HTML + CSS + vanilla JS). No build step.

## Sections

| Section | Based on |
| --- | --- |
| Hero: "How big can one print be?" with the 5.2× cubes | Instagram carousel, slide 1 |
| The Volume Gap: litre bars + big 5.2× | Carousel, slide 2 |
| Will it fit? checker | Visitors enter L × W × H and see one piece vs. pieces on a 256 mm printer |
| One print vs many prints | Poster page 1 layout |
| Their 5 steps vs our 2 steps | Poster page 2 layout (illustrations are inline SVG in `index.html`) |
| Display Shelf with ideas pop-up | Carousel, slide 4 |
| Ready to print it big? 10% off, 4 steps, order form | Carousel, slide 5 |

The poster can be downloaded from the site: `assets/pixl-one-print-vs-many-poster.pdf`.

## Brand assets (`assets/brand/`)

Generated from the logo: a circular cut-out (transparent outside the badge) in several sizes.
- `pixl-logo-{64,128,256,512}.webp`: header, footer, structured data
- `favicon-48.png`, `apple-touch-icon.png`: browser tab and home-screen icons
- `og-image.jpg`: preview image when the link is shared on WhatsApp/Instagram/etc.

## Preview locally

```bash
cd website
python3 -m http.server 8000   # then open http://localhost:8000
```

## Deploy to Vercel

In the `pi-xl-static-website` project, connect this repo and set **Root Directory** to `website`
(Framework preset: **Other**, no build command). `vercel.json` adds security headers and caching.

## Before launch

- **WhatsApp number**: `main.js` → `CONFIG.whatsapp` is still the placeholder `919999999999`. Use country code + number, digits only.
- Instagram handle and email are also in `CONFIG`; every link on the page updates from there.

## How ordering works

Nothing is stored on the site. **Order on WhatsApp** opens WhatsApp with the customer's name, category, size, material and details already typed.
**DM on Instagram** copies the same message and opens a chat with @pi.xl3dprinting for them to paste it into.
