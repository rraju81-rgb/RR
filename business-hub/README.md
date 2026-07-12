# RR Business Hub — Carbon Fibre × 3D Printing

A single-file app to run both businesses from one screen. **Everything is always
shown in a 50-50 split** — Carbon Fibre on the left, 3D Printing on the right.

The whole app is one file: [`index.html`](index.html). No installation, no
server, no account — it runs in any browser (phone or computer) and saves your
data on the device itself.

## The 5 sections

| # | Tab | What it does |
|---|-----|--------------|
| 1 | **Dashboard** | Operations overview for both businesses: active orders, this-month earnings, pipeline value, low-stock count, 6-month earnings chart, and auto-generated insights (top platform, which stage is eating time, quotes to chase, stock to reorder). |
| 2 | **Order Links** | Attach your two business links (URL / hosted HTML landing page) plus dedicated links for **custom project orders** and **quote requests**. Open, copy, preview, or edit each link. |
| 3 | **Operations Status** | A stage-by-stage status bar for every order (Enquiry → … → Delivered, with stages tailored per business). Shows time spent in **each** stage, marks the longest one, and flags anything stuck 3+ days so you can see exactly where the process is slow. Advance/rewind orders with one tap. |
| 4 | **Inventory** | Stock with prices and totals. Pre-loaded categories: PLA filament colours, magnets (2 sizes), screws, LED lights for 3D printing; fabric types with metres left (2×2 twill, plain weave, hexagonal weave…), breather, peel-ply, resin system for carbon fibre. Low-stock alerts, quick +/− buttons, add anything you like. |
| 5 | **Earnings** | Totals and monthly trend per business, earnings by source (custom projects / quote orders / direct sales), and a dedicated **"Where payments come from"** section showing how much money arrives via Instagram, WhatsApp, Website, and Organic. |

## How to use it

**On your phone/computer:** download `index.html` and open it in a browser.
Bookmark it / "Add to Home Screen" and it behaves like an app.

**Online (recommended):** enable GitHub Pages for this repo
(*Settings → Pages → Deploy from branch*, pick this branch, folder `/ (root)`),
then open `https://<your-username>.github.io/rr/business-hub/`.

## Your data

- Saved automatically in the browser's local storage — it never leaves your device.
- **Backup** button downloads everything as a JSON file; **Restore** loads it on
  any other device. **Reset** returns to the sample data.
- The app ships with realistic sample data so every screen is alive — replace it
  with your real orders, stock, and payments as you go (or hit Reset ↺ after a
  Backup once you're familiar).

## Tips

- You can deep-link a tab: `index.html?tab=status` (valid: `dash`, `links`,
  `status`, `inventory`, `earnings`).
- Dark mode follows your device setting automatically.
