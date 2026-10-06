# Marketing material
Rebuild: `python3 marketing/make_renders.py && python3 marketing/build_marketing.py`
- pitch_report.pdf: 2-page A4 pitch.
- poster_1..5.png: 1080 x 1350 social posts (Instagram portrait).
- img/: product renders (generated from build_board.py) and the designer's own prototype photos with real carded cars.
- Product name "SWINGRACK" is a placeholder; change `NAME` in build_marketing.py and the brand text in the templates.
- Fonts: Anton and Inter (SIL Open Font License), from Google Fonts.
Hot Wheels is a trademark of Mattel; keep the disclaimer and don't use Mattel logos as your own branding.

## Sales kit for the 2026 range (SWING + SLIDE racks)
Rebuild: `python3 marketing/make_renders_v2.py && python3 marketing/build_sales.py`
- sales_pitch.pdf (3 x A4) and meta_ad_1..5.png now sell the current models: PITLANE SWING (lift-off hinge, 6 cars),
  PITLANE SLIDE (fixed slide-in, 6 cars) and the right + left twins (12 cars). Prices in INR:
  SLIDE ₹799, SWING ₹1,199 (launch ₹999), SWING twin ₹2,199, SLIDE twin ₹1,449, STL pack ₹499, spare ledge ₹99.
- img/v2_*.png: renders from build_liftoff.py / build_fixed.py.
- pitch_report.pdf and poster_1..5.png still show the older strip + clip system.
