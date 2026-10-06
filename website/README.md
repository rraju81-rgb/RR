# PrintBig — website

Large format 3D printing, Bangalore. A fast, dependency-free static site (HTML + CSS + vanilla JS). No build step.

The design follows the PrintBig Instagram carousel and the "One Print vs Many Prints" poster:

| Section | Source |
| --- | --- |
| Hero: "How big can one print be?" with the 5.2× cubes | Carousel slide 1 |
| The Volume Gap: litre bars + big 5.2× | Carousel slide 2 |
| Will it fit? checker | New: visitors enter L × W × H and see one piece vs. pieces on a 256 mm printer |
| One Print Beats Many, 5 steps vs 2, head-to-head table | Carousel slide 3 + poster pages 1–3 |
| Display Shelf with ideas pop-up | Carousel slide 4 + previous site's field guides |
| Swipe the story (the carousel itself) | `assets/carousel/slide-1…5.webp` |
| Ready to Print Big? 10% off, 4 steps, order form | Carousel slide 5 |

The poster is downloadable from the site at `assets/printbig-one-print-vs-many-poster.pdf`.

## Preview locally

```bash
cd website
python3 -m http.server 8000   # then open http://localhost:8000
```

## Deploy to Vercel

1. In your Vercel project, connect this repo.
2. Set **Root Directory** to `website`. Framework preset: **Other**. Leave the build command empty.
3. Deploy. `vercel.json` adds security headers and caching.

## Before launch

- **WhatsApp number**: `main.js` → `CONFIG.whatsapp` is still the placeholder `919999999999`. Use country code + number, digits only.
- Instagram handle and email are also in `CONFIG`; every link on the page updates from there.
- **Domain**: once you have one, update the canonical/OG URLs in `index.html`, plus `robots.txt` and `sitemap.xml`.
- **Updating the carousel**: replace the files in `assets/carousel/` (keep the names) and update each image's `alt` text in `index.html`.

## How ordering works

Nothing is stored on the site. **Order on WhatsApp** opens WhatsApp with the customer's name, category, size, material and details already typed.
**DM @printbig.in** copies the same message and opens an Instagram chat for them to paste it into.
