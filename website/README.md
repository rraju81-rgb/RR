# Business website: Carbon Fibre & 3D Printing

A static website in plain HTML, CSS and JavaScript. There is no build step and no framework, so you can open the files, edit the text, and upload the folder to any web host.

## The pages

| File | What it is |
| --- | --- |
| `index.html` | **Page 1.** The start page, split diagonally into Carbon Fibre and 3D Printing. Choosing one plays a transition into that division: carbon strips weave across the screen, or the screen is printed layer by layer. |
| `carbon-fibre.html` | **Pages 2 to 4 for carbon fibre.** Landing section, then Products / Custom parts / Contact in three equal columns, then a scrolling gallery of finished work with contact details at the bottom. |
| `3d-printing.html` | The same structure for 3D printing, with "Models we print" in the first column. |
| `assets/css/styles.css` | All styling. Colours and fonts are defined at the top. |
| `assets/js/main.js` | Transitions, animations, gallery, lightbox and the enquiry form. |
| `assets/img/` | The logo mark (`logo-mark.svg`) and gallery images (`work/`). |

## Preview on your computer

Double-click `index.html`, or run a small local server from this folder:

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000 in your browser.

## Make it yours

### 1. Business details

Use find-and-replace across the three HTML files:

| Placeholder | Replace with |
| --- | --- |
| `RR` | Your business name (logo text, page titles, footer, and `data-brand="RR"` on the forms) |
| `+00 0000 000000` | Your phone number, written the way you want it shown |
| `tel:+000000000000` | Your phone number with country code, digits only after the `+` |
| `000000000000` | Your WhatsApp number: country code and number, digits only (for example `919876543210`). It appears in the `wa.me/…` links and in `data-whatsapp` on the forms. |
| `hello@example.com` | Your email address |
| `Workshop address, City` | Your address |
| `Mon to Sat, 9:00 to 18:00` | Your opening hours |
| `https://www.instagram.com/` | Your Instagram profile link |

### 2. Logo

Replace `assets/img/logo-mark.svg` with your own logo. A square image works best. The file is used in the header, the footer, the page transitions and the browser tab icon. If your logo is a PNG, save it as `assets/img/logo-mark.png` and change `logo-mark.svg` to `logo-mark.png` in the HTML files and in `assets/js/main.js`.

### 3. Gallery photos

The galleries currently show sample illustrations marked "SAMPLE IMAGE". To use your own photos:

1. Put each photo in `assets/img/work/`. Landscape 4:3 works best, about 1200 × 900 pixels, saved as JPG or WebP and kept under 300 KB.
2. In `carbon-fibre.html` or `3d-printing.html`, find the `<li class="work-card">` lines. Each line is one picture. Change `src` to your file name, write a short `alt` text describing the photo, and edit the two caption words (the name of the part and its category).
3. Copy a line to add a picture, or delete one to remove it. Each page has two rows that scroll in opposite directions and loop automatically, however many photos you add.

### 4. Products, services and wording

All text is in the HTML and can be edited directly: the product range, the custom-part steps, materials, file formats and descriptions.

## How the contact form works

The site has no server, so the form does not send anything by itself. When a visitor fills it in and presses **WhatsApp** or **Email**, their WhatsApp (or email app) opens with the message already written and addressed to you. They press send there. They can attach photos or files in that app.

If you would rather receive submissions directly by email, a form service such as Formspree or Netlify Forms can be connected later.

## Put it online

Any static web host works. The simplest options:

- **Netlify Drop:** go to https://app.netlify.com/drop and drag this `website` folder onto the page. You get a live link straight away and can connect your own domain in the site settings.
- **Cloudflare Pages or Vercel:** create a new project, set the root (output) directory to `website`, and leave the build command empty.
- **GitHub Pages:** this folder sits inside the 6thGear app repository, so the cleanest route is to copy the `website` folder into a repository of its own and enable Pages there (Settings → Pages → Deploy from a branch).

## Design notes

- **Colours:** aramid gold (`--aramid`) is the carbon fibre accent and hot-nozzle orange (`--nozzle`) is the 3D printing accent. Both are set at the top of `styles.css`.
- **Fonts:** headings use Archivo at its widest setting, labels use IBM Plex Mono. Both load from Google Fonts.
- **Accessibility:** works with a keyboard and screen readers, and passes an automated axe-core check on every page at desktop and phone sizes.
- **Reduced motion:** visitors who turn on "reduce motion" on their device get no transitions or auto-scrolling, and the gallery becomes a row they can swipe.
