# UI/UX generation prompt — RR Business Hub dashboard (Next.js)

Paste the block below into v0, Lovable, Cursor, or Claude to generate the dashboard frontend.

---

Build the admin dashboard for **RR Business Hub**, an operations console for a workshop that runs two businesses side by side: **Carbon Fibre** (composites, custom parts) and **3D Printing** (FDM prints, prototypes). The user is a single owner-operator in India — non-technical, mobile-first, checking this between jobs on a workshop floor, not sitting at a desk.

## Stack

- Next.js (App Router) + TypeScript, dashboard under an `/admin` route group
- Tailwind CSS + shadcn/ui
- lucide-react for icons
- Charts: lightweight custom SVG/CSS, or Recharts if you prefer — no heavy chart library
- All data from typed mock files for now. Structure it so a real API/data layer can be swapped in later without touching components: keep data access in a single module, components take props.

## The one non-negotiable layout rule

**Both businesses are always visible in a 50/50 vertical split — Carbon Fibre on the left, 3D Printing on the right — on every section, at every breakpoint, including phones.** This is the entire point of the product. Never collapse to tabs, never stack the two businesses vertically, never hide one behind a selector. On narrow screens keep the two columns and let each column's content compress and wrap. The page must never scroll horizontally; wide content scrolls inside its own container.

## Businesses are data, not hardcoded

Define businesses in a config array so a third can be added later without a rewrite. Each entry carries: id, display name, tagline, accent colour token, and its own ordered stage list. Never write `if (business === 'carbonFibre')` in a component.

- Carbon Fibre — id `cf`, tagline "composites · custom parts", accent blue. Stages: Enquiry, Quoted, Material Prep, Layup, Vacuum & Cure, Trim & Finish, Quality Check, Delivered.
- 3D Printing — id `p3d`, tagline "FDM prints · prototypes", accent green. Stages: Enquiry, Quoted, Design & Slice, Printing, Post-Process, Quality Check, Packed, Delivered.

## Navigation — exactly five sections

A single persistent tab bar, numbered 1–5, horizontally scrollable on mobile: **Dashboard · Order Links · Operations Status · Inventory · Earnings**. Tab state in the URL so a section can be bookmarked. Each section renders the same component twice, once per business, inside the 50/50 split.

## Section 1 — Dashboard

Per business: four KPI tiles in a 2×2 grid — active orders (with count in production), earnings this month (with % change vs last month, up/down), pipeline value (total value of open orders), low-stock item count (red when above zero).

Below: a six-month earnings bar chart with the value labelled above each bar and month labels beneath a baseline rule.

Below that: an **Insights** card — 3–5 plain-language sentences generated from the data, each with a small leading icon. Examples of the tone: "Most money is coming through **Instagram** — ₹41,300 in the last 90 days." · "**Bike fairing panel** has been in **Layup** for 4.2d — this is where time is going." · "Low stock: **Hexagonal weave, Breather cloth**. Reorder before it blocks a job." Write these as full sentences that tell the owner what to *do*, never as bare metrics.

Finally: the three most recent payments, each with a channel dot, description, and amount.

## Section 2 — Order Links

Three cards per business, the first visually emphasised: **Business landing page**, **Custom project orders**, **Quote requests**. Each stores one URL and shows it in a monospace pill. Actions: Open (new tab), Copy (with a "Copied ✓" confirmation on the button), Preview (inline iframe), Edit. When empty, show an explicit invitation to attach a link, not a blank space. If a preview fails to load, explain that the destination blocks embedding and point to Open instead.

## Section 3 — Operations Status

The most important screen. Per business: filter pills (Active / Delivered / All) and a "New order" button, then a card per order.

Each order card shows: order name, client, value, a channel chip, current stage, and a **horizontal stage pipeline** — a row of dots connected by a line, one per stage, with completed stages filled in the business accent colour, the current stage as a ring with a soft halo, and future stages as hollow grey dots. Stage names sit beneath each dot, tiny, with the current one bold.

Below the pipeline, a row of small chips showing **time spent in each stage the order has passed through** ("Layup · 2d", "Quoted · 1.2d ⏳"). Mark the longest stage with an amber outline and the label "— longest". If the *current* stage has run 3 days or more, mark it with a red outline and "— stuck!". This is how the owner sees where time is going, so make it legible at a glance.

Actions per card: Back / Advance (the final transition reads "Deliver ✔"), Edit, Delete. Disable Back at the first stage and Advance at the last.

Leave a slot in the order card for a future 3D model preview thumbnail (3D Printing orders will eventually carry an uploaded STL) — reserve the space in the layout, don't build the viewer.

## Section 4 — Inventory

Per business: a summary line (total stock value, item count, low-stock count) and an "Add item" button. Items grouped into collapsible-looking categories, each category header showing its name, item count, and total value.

Each row: item name, a LOW badge when at or below its threshold, a − button, quantity with unit, a + button, then price per unit and line value, then edit and remove. Quantity turns red when low. The +/− steps by an amount that suits the unit: 0.5 for metres and kilograms, 10 for pieces, 1 otherwise. Never go below zero.

Seed the mock data with the workshop's real stock: 3D Printing — PLA filament by colour (Black, White, Red, Blue, Grey, Silk Gold) in kg; neodymium magnets in 5×2 mm and 10×3 mm; screws M2×8, M3×10, M3×16, M4×12 in pieces; LED strips (warm 5 V, WS2812B) in metres and LED modules. Carbon Fibre — fabrics in metres (2×2 Twill 3K, Plain weave 3K, Hexagonal weave, Kevlar hybrid); consumables (peel-ply, breather cloth, vacuum bagging film, sealant tape); resin system (epoxy resin, hardener, release wax). Units: m, kg, pcs, rolls, tin, sets, g.

## Section 5 — Earnings

Per business: two hero figures (total earned, this month). Then the six-month trend chart. Then **Earnings by source** — horizontal bars for Custom project / Quote order / Direct sale / Other with amount and percentage.

Then the section that matters most: **"Where payments come from — by platform"**. Horizontal bars for Instagram, WhatsApp, Website, Organic, each in its own fixed colour, showing amount, share of total, and number of payments. Add a one-line note: the tallest bar is where the buyers actually are.

Finally a payment log: channel chip, note, date, source, amount, delete.

## Design system — use these exact values

Light mode: page `#f9f9f7`, surface `#fcfcfb`, primary ink `#0b0b0b`, secondary ink `#52514e`, muted `#898781`, hairline grid `#e1e0d9`, baseline `#c3c2b7`, border `rgba(11,11,11,.10)`.

Dark mode: page `#0d0d0d`, surface `#1a1a19`, ink `#ffffff`, secondary `#c3c2b7`, muted `#898781`, grid `#2c2c2a`, baseline `#383835`, border `rgba(255,255,255,.10)`.

Business accents — Carbon Fibre `#2a78d6` light / `#3987e5` dark; 3D Printing `#1baf7a` light / `#199e70` dark.

Payment channels (fixed, never reassigned) — Instagram `#e87ba4` light / `#d55181` dark; WhatsApp `#008300` both; Website `#2a78d6` / `#3987e5`; Organic `#eda100` / `#c98500`.

Status — good `#0ca30c`, warning `#fab219`, serious `#ec835a`, critical `#d03b3b`. These are reserved for state only and must never be used as a series colour.

Typography: system UI sans throughout (`system-ui, -apple-system, "Segoe UI", sans-serif`). No display or serif face, no webfonts. Base size fluid, roughly 12.5–14.5px — this is a dense operational tool, not a marketing page. Uppercase micro-labels at ~0.68rem with 0.08em letter-spacing for section headers and KPI labels. Headline numbers at ~1.25rem, weight 800, tight tracking. Use `font-variant-numeric: tabular-nums` anywhere digits stack in columns.

Surfaces: 14px radius on panels, 11px on cards, 8px on buttons, 99px on chips. Hairline 1px borders, not shadows — at most a `0 1px 2px rgba(11,11,11,.05)` shadow in light mode, none in dark. Generous internal padding, tight gaps between rows.

Money in Indian Rupees. Exact values in lists (`₹24,000`); abbreviated for headline figures (`₹33.8k`, `₹1.2L`).

Dark mode must be defined at token level: full light palette on `:root`, dark values re-declared under `prefers-color-scheme: dark` **and** under an explicit `dark` class/attribute so a manual toggle wins in both directions. Style components through tokens only.

## Interaction and UX rules

Every action responds instantly — this is used on a workshop floor with thin signal, so optimistic local updates, never a spinner blocking a tap. Include a small sync-status indicator in the header with three states (synced / pending / offline) ready to be wired to a backend later.

Guard every destructive action behind a confirmation. Show meaningful empty states with a next action, never a blank panel. Forms open as modals with clear labels, sensible defaults, and validation. Primary actions must be reachable in at most two taps from any section. Give keyboard focus a visible ring and respect `prefers-reduced-motion`.

## Accessibility

Meaning is never carried by colour alone — every coloured dot or bar sits beside a text label. Maintain contrast in both themes. Charts need accessible labels and a text alternative for their values.

## Do not

- Do not break the 50/50 split for any reason at any breakpoint.
- Do not use a dual-axis chart, a pie or donut chart, or gradient-filled bars.
- Do not use emoji as section markers, giant hero sections, purple-to-blue gradients, or the generic AI-dashboard look — this is a dense working tool with hairline rules and real data density.
- Do not add a sidebar, a settings page, a notifications centre, or any section beyond the five specified.
- Do not build a customer-facing view. This is the owner's console only.
- Do not add heavy dependencies, animation libraries, or a state management library.

## Deliver

Clean component structure with the two business panels rendered from one reusable component, typed mock data covering roughly 8 orders, 30 inventory items and 18 payments across both businesses with realistic Indian workshop values, and full responsive behaviour verified at 390px and 1400px wide.
