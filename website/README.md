# Carbon6 Studio website

The website for **Carbon6 Studio** and its two businesses, **Carbon6 Customization** (carbon fibre) and **pi.XL 3D Printing**. It is a static site in plain HTML, CSS and JavaScript. There is no build step and no framework, so you can open the files, edit the text, and upload the folder to any web host.

## The pages

| File | What it is |
| --- | --- |
| `index.html` | **Start page.** Split diagonally into Carbon6 Customization and pi.XL 3D Printing. Choosing one plays a transition into that business: carbon strips weave across the screen, or the screen is printed layer by layer. The badge on the seam keeps turning between the Carbon6 and pi.XL logos, and the 3D printer prints a different model each time it finishes. |
| `carbon-fibre.html` | **Carbon6 Customization.** Landing section, Our work (a rolling gallery of work and products), Custom parts, and one Talk to us page with the contact details and a message form. |
| `3d-printing.html` | **pi.XL 3D Printing.** The same order, with the PITLANE range and prices in the gallery. |
| `assets/css/styles.css` | All styling. Colours and fonts are defined at the top. |
| `assets/js/main.js` | Transitions, the 3D printer animation, gallery, lightbox and the message form. |
| `assets/img/` | Logos, favicons, Carbon6 product pictures (`products/`) and gallery pictures (`work/`). |

## How the products work

There is no separate products page. The products live in two places:

1. **Our work.** Product pictures sit in the gallery alongside past work. Selecting any picture opens it larger with a button such as **Ask about automotive parts** or **Order GARAGE · ₹799**.
2. **Talk to us.** Under "I'm interested in" the form lists the range of the business chosen above it as buttons. The gallery button jumps here with that product already picked, and the WhatsApp message names it.

## Where the content came from

- **Carbon 6 logo:** converted from `Carbon 6 logo.ai` in Google Drive into `carbon6-logo.svg` and `carbon6-mark.svg` (white, for dark backgrounds) and the `-ink` versions (dark, for light backgrounds). The car on its own (`carbon6-mark`) is used in the headers, the badge and the favicon.
- **pi.XL logo:** the round pi.XL 3D Printing logo you supplied, cropped to its circle: `pixl-logo.webp` (start page), `pixl-logo-160.webp` (header, badge and transition) and `favicon-pixl.png`.
- **Contact details:** both businesses use **+91 99006 11996** for WhatsApp and calls. Instagram: @c6_customization (from the Carbon 6 business card) and @pi.xl3dprinting.
- **pi.XL products, prices and photos:** from `PITLANE_Catalogue_2026_v4.pdf` in Google Drive.

## What is still a placeholder

- **Carbon6 Customization pictures.** The gallery pictures on the carbon fibre page are sample illustrations marked "SAMPLE IMAGE". Replace them with photos of your parts (see below).
- **Carbon6 product range.** The six product groups (Automotive, Motorcycle, Cycling, Drones & RC, Sheets/tubes/profiles, Accessories) are general categories. Edit them to match what you actually sell.

## Editing

### Contact details

To change the number, use find-and-replace across the HTML files:

| Find | What it is |
| --- | --- |
| `919900611996` | WhatsApp and phone links, and the number each form option sends to (digits only, with country code) |
| `+91&nbsp;99006&nbsp;11996` | The number as shown on the page |
| `c6_customization` / `pi.xl3dprinting` | Instagram handles |

To give the two businesses different numbers again, change the number on the page you want and in that business's `<option>` (`data-whatsapp`) in the form on both pages.

### Products

- **In the gallery:** each picture is one `<li class="work-card">` line. Three settings on that line drive its button: `data-item-type` (`Carbon fibre` or `3D printing`), `data-item-product` (the product it is about) and `data-item-cta` (the button text).
- **In the form:** each product is one `<label class="chip">` inside `<fieldset class="picker">`. There is one set per business (`data-picker-set="carbon"` and `"print"`), and both pages carry both sets.
- A gallery button picks the chip whose `value` matches its `data-item-product` exactly, so keep the two the same.
- **pi.XL prices** appear in three places: the gallery caption, the chip (its label and `value`) and the gallery button text. Change all three when a price changes.

### Gallery photos

1. Put each photo in `assets/img/work/` as a JPG or WebP, about 1100 pixels on the long side and under 300 KB.
2. Find the `<li class="work-card">` lines in the page. Each line is one picture. Change `src`, the `width` and `height` to the photo's size, the `alt` text, and the two caption lines.
3. If the photo is not 4:3, also set its shape on the line, for example `style="--ar: 800 / 1100"` for an upright photo. The rows scroll in opposite directions and loop automatically, however many pictures you add.

### The message form

There is no server. The form writes the visitor's message into WhatsApp: who they are, what they are looking for (**Carbon fibre** or **3D printing**), the product they picked and their details. The visitor presses send in WhatsApp and can attach photos there.

### The 3D printer models

The printer on the start page and the pi.XL page cycles through: spiral vase, helical gear, a pi.XL sign, twisted vase, chess rook and a PITLANE podium. The models are defined in `PRINT_MODELS` in `assets/js/main.js`. The layer speed is set per page with `data-layer-ms` on the printer (higher is slower).

## Preview on your computer

Double-click `index.html`, or run a small local server from this folder:

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000.

## Put it online

Any static web host works:

- **Netlify Drop:** go to https://app.netlify.com/drop and drag this `website` folder onto the page. You get a live link straight away and can connect your own domain in the site settings.
- **Cloudflare Pages or Vercel:** create a new project, set the root (output) directory to `website`, and leave the build command empty.
- **GitHub Pages:** this folder sits inside the 6thGear app repository, so the cleanest route is to copy the `website` folder into a repository of its own and enable Pages there (Settings → Pages → Deploy from a branch).

## Design notes

- **Colours:** aramid gold (`--aramid`) is the carbon fibre accent and hot-nozzle orange (`--nozzle`) is the 3D printing accent, set at the top of `styles.css`.
- **Fonts:** headings use Archivo at its widest setting, labels use IBM Plex Mono. Both load from Google Fonts.
- **Accessibility:** works with a keyboard and screen readers, and passes an automated axe-core check on every page at desktop and phone sizes.
- **Reduced motion:** visitors who turn on "reduce motion" get no transitions or auto-scrolling, the printer shows a finished model, the badge fades between the two logos instead of turning, and the gallery becomes a row they can swipe.
