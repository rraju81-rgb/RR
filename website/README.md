# PiXL 3D Printing — website

A fast, dependency-free static site (HTML + CSS + vanilla JS). No build step.

## Preview locally

```bash
cd website
python3 -m http.server 8000   # then open http://localhost:8000
```

## Deploy to Vercel

1. In Vercel, import this repo (or point your existing `pi-xl-static-website` project at it).
2. Set **Root Directory** to `website`. Framework preset: **Other**. Leave the build command empty.
3. Deploy. `vercel.json` adds security headers and caching.

## Before launch: replace the placeholders

| What | Where |
| --- | --- |
| Email address | `main.js` → `CONFIG.email` (the page's email links update automatically) and the JSON-LD block in `index.html` |
| WhatsApp number | `index.html`, the two `https://wa.me/910000000000` links (format: country code + number, no `+`) |
| Phone and city | `index.html`, the contact list and the JSON-LD block |
| Prices | `main.js` → `CONFIG.ratePerCm3`, `setupFee`, `minPerPart`, `finishPerPart` |
| Gallery tiles | `index.html` `#work` section. Swap each `<div class="tile-art">` for an `<img src="assets/…" alt="…" loading="lazy" width="800" height="600">` |
| Testimonials | `index.html` `#reviews`. Use real reviews, then remove the "Sample testimonials" note |
| Domain | `index.html` canonical/OG URLs, `robots.txt`, `sitemap.xml` |

## Receiving quote requests (with file uploads)

Out of the box, the contact form opens the visitor's email app with the details filled in.
To receive submissions directly, including the uploaded STL/STEP file:

1. Create a free form at [Formspree](https://formspree.io) (or Web3Forms / Getform).
2. Paste its endpoint into `main.js` → `CONFIG.formEndpoint`.

These three services are already allowed in the Content-Security-Policy in `vercel.json`.
If you use a different one, add its domain to `connect-src`.
