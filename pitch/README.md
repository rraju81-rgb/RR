# SlideRack pitches and Indian market research

| File | What |
|---|---|
| `SlideRack_Wall_Mount_Pitch.pdf` | 4 pages: wall rack + wall rack on clip-on table feet (+ hinged Pro). Covers design, function, Indian market and pricing. |
| `SlideRack_Tabletop_Pitch.pdf` | 4 pages: 3- and 5-card racks on the universal base. Covers design, function, Indian market and pricing. |
| `*.png` | product renders (z-buffer renderer in `src/rlib.py`), annotated design shots, price charts |
| `src/pricing.py`, `src/pricing.json` | unit-cost and channel-margin model; every price in the pitches comes from here |

## Market research summary (India, Oct 2026)

**Demand.**
- Indian online diecast stores report 1,000+ collectors across Mumbai, Delhi, Bangalore and Chennai.
- The community is organised on Instagram, through groups such as the Diecast Collective India network.
- Industry reports name India among the fastest-growing diecast markets: the region grows at about 7.4 % CAGR to 2034.

**Competition.**
- Carded wall hangers on Amazon.in: ₹299–₹519.
- Acrylic multi-car wall cases: ₹3,998 and up.
- Tabletop racks: ₹349–₹564, mostly for loose cars.
- A 3D-printed 5-rack card stand on Flipkart: ₹1,500.

**Cost inputs.**

| Input | Value | Basis |
|---|---|---|
| PLA filament | ₹699–₹965/kg (₹900 used) | researched |
| GST | 18 % | researched: HSN 3926 under GST 2.0 (22 Sep 2025) |
| Amazon.in referral fee | 0 % under ₹300 | researched: since April 2025 |
| Shipping | from ₹20 per 500 g on Shiprocket (₹70 used for national delivery) | researched |
| Print speed | 25 g/h | assumption |
| Machine cost | ₹12/h | assumption |
| Printed mass | 75 % of the solid model | assumption |

**Prices.** Each price is the lowest ₹x49 / ₹x99 price that gives at least a 25 % margin direct and at least
10 % on a marketplace. The exception is the hinged Pro, which is priced as a premium.

| Product | Price |
|---|---|
| Wall 6 | ₹499 |
| Table Feet | ₹199 |
| Wall 6 + Feet | ₹699 |
| Wall Pro (hinged) | ₹749 |
| Tabletop Set 3 | ₹799 |
| Tabletop Set 5 | ₹999 |
| Collector Combo | ₹1,349 |
| Extra racks | ₹549 / ₹749 |

**Channels.**
- Instagram and WhatsApp, selling direct.
- Amazon.in and Flipkart. List as "for 1:64 carded cars" and keep car brands out of the product name.
- Indian diecast retailers as resellers.
- Collector meets.

Sources: Amazon.in and Flipkart listings, magicdrop.in, price-history.in, cleartax.in, eximpe.com,
outlookbusiness.com, shiprocket.in, diecastcollectiveindia.com, toycollectorsindia.com, indiandiecasthub.com,
verifiedmarketreports.com.
