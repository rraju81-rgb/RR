"""PITLANE sales kit: sales_pitch.pdf (3 x A4: pitch, product analysis, pricing & go-to-market) and meta_ad_1..5.png (1080x1350)."""
import os, subprocess, pathlib
HERE = pathlib.Path(__file__).resolve().parent
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
FONTS = '<link href="fonts/fonts.css" rel="stylesheet">'
TM = "Hot Wheels&reg; is a trademark of Mattel, Inc. PITLANE is an independent product, not affiliated with or endorsed by Mattel. Fits standard 1:64 blister cards."
CSS = """
:root{--ink:#14161b;--asphalt:#1b1e25;--orange:#ff6a13;--yellow:#ffc21a;--soft:#f3f4f6;--muted:#5b6170}
*{box-sizing:border-box;margin:0;padding:0} body{font-family:Inter,sans-serif;color:var(--ink);background:#fff}
h1,h2,.d{font-family:Anton,Impact,sans-serif;font-weight:400;text-transform:uppercase;letter-spacing:.4px}
.track{background:repeating-linear-gradient(90deg,var(--orange) 0 26px,#ff8c42 26px 52px)}
.logo{font-family:Anton,sans-serif;letter-spacing:1px}.logo b{color:var(--orange);font-weight:400}
"""
DOC = CSS + """
@page{size:A4;margin:0} .page{width:210mm;height:297mm;padding:13mm 14mm 12mm;position:relative;overflow:hidden;page-break-after:always}
.page:last-child{page-break-after:auto}
.bar{position:absolute;left:0;right:0;top:0;height:5mm}
.top{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:3px solid var(--ink);padding-bottom:3mm;margin-top:2mm}
.top .logo{font-size:28pt;line-height:1} .top span{font-size:8.5pt;color:var(--muted);text-align:right}
h1{font-size:27pt;line-height:1.05;margin:5mm 0 3mm} h1 em{font-style:normal;color:var(--orange)}
h2{font-size:13.5pt;margin:5mm 0 2mm;display:flex;gap:2.5mm;align-items:center} h2:before{content:"";width:5mm;height:2.6mm;background:var(--orange)}
p,li,td,th{font-size:9pt;line-height:1.45} ul{padding-left:4.5mm} li{margin-bottom:.9mm}
.lead{font-size:10.5pt}
.quote{background:var(--asphalt);color:#fff;border-radius:3mm;padding:4.5mm 5mm;font-size:10.5pt;line-height:1.5;margin:3mm 0}
.quote b{color:var(--yellow)}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:5mm} .g3{display:grid;grid-template-columns:repeat(3,1fr);gap:3.5mm}
.card{background:var(--soft);border-radius:3mm;padding:3.5mm 4mm}
.img{background:#fff;border:1px solid #e3e5ea;border-radius:3mm;overflow:hidden} .img img{width:100%;height:60mm;object-fit:contain;display:block}
.img.ph img{object-fit:cover} .cap{font-size:7.5pt;color:var(--muted);padding:1.5mm 2.5mm}
table{width:100%;border-collapse:collapse;margin-top:1.5mm} th{background:var(--ink);color:#fff;text-align:left;padding:1.6mm 2mm;font-size:8.3pt}
td{padding:1.4mm 2mm;border-bottom:1px solid #e1e3e8;font-size:8.3pt;vertical-align:top} tr:nth-child(even) td{background:#f7f8fa}
.price{font-family:Anton,sans-serif;font-size:21pt;color:var(--orange);line-height:1}
.tier{border:2px solid #e3e5ea;border-radius:3mm;padding:3.5mm;position:relative} .tier.hot{border-color:var(--orange)}
.tier .tag{position:absolute;top:-3mm;right:3mm;background:var(--orange);color:#fff;font-size:7pt;font-weight:800;padding:.6mm 2mm;border-radius:2mm}
.tier h3{font-size:10pt;margin-bottom:1mm} .tier p{font-size:8pt;color:#3b404b}
.sw{display:grid;grid-template-columns:1fr 1fr;gap:3mm} .sw div{border-radius:3mm;padding:3mm 3.5mm} .sw h3{font-size:9.5pt;margin-bottom:1mm}
.s{background:#e8f6ee}.w{background:#fdeceb}.o{background:#e9f1fd}.t{background:#fff4e0}
.foot{position:absolute;left:14mm;right:14mm;bottom:6mm;font-size:6.6pt;color:var(--muted);border-top:1px solid #e1e3e8;padding-top:1.5mm;display:flex;justify-content:space-between}
.src a{color:var(--muted)}
"""
def foot(n): return f'<div class="foot"><span>{TM}</span><span>{n} / 3</span></div>'
doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>PITLANE sales pitch</title>{FONTS}<style>{DOC}</style></head><body>
<section class="page"><div class="bar track"></div>
<div class="top"><div class="logo">PIT<b>LANE</b></div><span>Sales pitch &amp; product analysis<br>Swing-out wall garage for carded 1:64 cars</span></div>
<h1>Every car gets its own garage.<br><em>Every card stays on show.</em></h1>
<p class="lead">PITLANE is a 3D-printed wall system for carded die-cast cars. One 40 cm strip holds up to 7 cars, and each card sits in its own swing-out ledge. Lift a ledge, swing it open, slide the card in, swing it shut. The cards step out 7 mm per row, so every name stays visible and no card covers another.</p>
<div class="quote"><b>The pitch (30 seconds):</b> &ldquo;Collectors keep their best cars carded, then hide them in boxes or crush them on peg hooks. PITLANE gives every card its own swing-out garage on the wall. You can see every name, take any one card out without touching the others, and add racks as your collection grows. It snaps together with no tools. One 40 cm strip holds up to 7 cars, for about the price of one mainline car per slot.&rdquo;</div>
<div class="g2" style="margin-top:3mm">
 <div class="img ph"><img src="img/photo_prototype_7rack.jpg"><div class="cap">Real printed prototype loaded with real carded cars (designer&rsquo;s photo).</div></div>
 <div class="img"><img src="img/hero_7.png"><div class="cap">Current design: 7 cars on one 40 cm strip (CAD render, cards shown as blanks).</div></div>
</div>
<h2>What&rsquo;s in the box (7-car kit)</h2>
<div class="g3">
 <div class="card"><b>1&times; wall strip, 40 cm</b><p>One piece, or two halves that lock with a C-interlock. Fixed with 4 screws. Hook-lip pairs every 54 mm.</p></div>
 <div class="card"><b>7&times; hinge clips</b><p>Each clip double-hooks behind two lips, and two solid bumps click into notches in the strip (no springs). Each one sits 7 mm deeper than the one below. No tools.</p></div>
 <div class="card"><b>7&times; swing ledges</b><p>8 mm pin running the full height, a 0&deg; stop, a click detent and 14 mm corner posts that keep the card upright.</p></div>
</div>
<h2>Why it wins</h2>
<ul><li><b>Grab one, leave the rest:</b> other displays make you unhook the cards in front. Here each card has its own door.</li>
<li><b>Names stay readable:</b> a 1 mm front lip and stepped rows mean nothing covers the card title.</li>
<li><b>Built for real prints:</b> every part prints without supports, and every lock was redesigned after real test prints failed.</li>
<li><b>Grows with the collection:</b> buy the strip once and add racks for &#8377;199 each.</li></ul>
{foot(1)}</section>

<section class="page"><div class="bar track"></div>
<div class="top"><div class="logo">PIT<b>LANE</b></div><span>Product analysis</span></div>
<h2>Market</h2>
<p>Adult collectors now drive the die-cast market worldwide (an estimated 58% of revenue, a $4.2&ndash;5.8 billion market growing 5&ndash;6% a year). India&rsquo;s collector scene is young and growing fast: mainline cars sell for roughly &#8377;200&ndash;450 each online, and collectors who keep cars <b>carded</b> (mint in package) have few wall options made for cards. That gap is what PITLANE fills.</p>
<h2>Competition and prices in India (Oct 2026)</h2>
<table><tr><th>Product</th><th>What it does</th><th>Price</th><th>PITLANE advantage</th></tr>
<tr><td>3D-printed card hooks (Etsy India)</td><td>Static hooks; cards hang flat, one behind another</td><td>&#8377;277&ndash;302</td><td>Swing-out access, every card visible, rows step forward</td></tr>
<tr><td>Wall-mount 1:64 stands (direct sellers)</td><td>Printed stands for loose cars, packs of 12&ndash;48</td><td>&#8377;550&ndash;1,690</td><td>Made for <i>carded</i> cars, double-locked clips</td></tr>
<tr><td>Modular 3D-printed wall case (Etsy India)</td><td>4 cars per module</td><td>&#8377;1,658+</td><td>7 cars on one 40 cm strip for less</td></tr>
<tr><td>Display STL files (Etsy India)</td><td>Print-at-home files</td><td>&#8377;1,188</td><td>Our STL pack at &#8377;499</td></tr></table>
<p class="src" style="font-size:7pt;margin-top:1mm">Sources: <a href="https://www.etsy.com/in-en/market/hot_wheels_display_3d_printed">Etsy India: 3D-printed displays</a>, <a href="https://www.etsy.com/in-en/listing/1855211793/hot-wheels-display-case-3d-printed">Etsy India: modular wall case</a>, <a href="https://www.etsy.com/in-en/listing/4296116586/3d-printing-modular-car-display-hot">Etsy India: display STL</a>, <a href="https://modmusestore.com/products/hot-wheels-wall-mount-3d-printed-display-stand-1-64-scale">ModMuse wall stand</a>, <a href="https://pricehistory.app/p/esun-pla-3d-printing-filament-1-75mm-iblWdqG5">eSUN PLA+ price in India</a>, <a href="https://magicdrop.in/drops/cheap-hot-wheels">Hot Wheels prices in India</a>.</p>
<h2>SWOT</h2>
<div class="sw">
 <div class="s"><h3>Strengths</h3><ul><li>A genuinely new mechanism: swing-out door for each card</li><li>Every name visible; rows step out 7 mm</li><li>No supports, low cost per unit, modular</li><li>Designer is a collector, with real-print testing</li></ul></div>
 <div class="w"><h3>Weaknesses</h3><ul><li>Fits standard mainline cards only (~105 &times; 165 mm, blister &le; 42 mm)</li><li>Print time per kit is high (about 16 h for 4 cars, 26 h for 7)</li><li>Ledges above must be opened to load a lower card</li><li>The newest version (solid bump, L-lock) is not yet test-printed</li></ul></div>
 <div class="o"><h3>Opportunities</h3><ul><li>Sell the STL files too: zero marginal cost</li><li>Colour editions (orange track, black and white)</li><li>Premium / long-card ledge, Matchbox and Mini GT variants</li><li>Hobby-shop wall displays (B2B)</li></ul></div>
 <div class="t"><h3>Threats</h3><ul><li>Cheap static hooks at &#8377;277&ndash;302</li><li>Copycats on file marketplaces</li><li>Trademark: never use &ldquo;Hot Wheels&rdquo; as your brand, only &ldquo;fits Hot Wheels&reg; cards&rdquo;</li><li>Courier cost of a 40 cm part (ship the 2-piece strip)</li></ul></div>
</div>
<h2>Who buys it</h2>
<ul><li><b>Adult carded collectors</b> (18&ndash;40, metro and Tier-1 cities) with 20&ndash;200 cards and a wall to fill. This is the main ad audience.</li>
<li><b>Parents and gift buyers</b>: birthdays, plus the Diwali and Christmas gift season (Oct&ndash;Dec).</li>
<li><b>Makers</b> with their own 3D printer, who buy the STL files.</li></ul>
{foot(2)}</section>

<section class="page"><div class="bar track"></div>
<div class="top"><div class="logo">PIT<b>LANE</b></div><span>Pricing &amp; go-to-market</span></div>
<h2>Cost to make (estimate, in rupees)</h2>
<table><tr><th>Item</th><th>4-car kit</th><th>7-car kit</th><th>Basis</th></tr>
<tr><td>Filament (PLA+ at &#8377;1,500/kg)</td><td>&#8377;297</td><td>&#8377;474</td><td>From the STL files: about 198 g / 316 g printed (70% of fully solid)</td></tr>
<tr><td>Electricity</td><td>&#8377;20</td><td>&#8377;32</td><td>150 W printer, &#8377;8/kWh, 16 h / 26 h of printing at about 12 g/h</td></tr>
<tr><td>Failed-print allowance (15%)</td><td>&#8377;48</td><td>&#8377;76</td><td>Reprints, nozzle wear</td></tr>
<tr><td>Box, 4 screws + wall plugs, label</td><td>&#8377;60</td><td>&#8377;60</td><td>Ship the 2-piece strip to keep the box small</td></tr>
<tr><td><b>Total cost</b></td><td><b>&asymp; &#8377;425</b></td><td><b>&asymp; &#8377;640</b></td><td>Excludes your time and courier (about &#8377;80&ndash;120 within India)</td></tr></table>
<h2>Recommended prices (INR)</h2>
<div class="g3" style="grid-template-columns:repeat(4,1fr)">
 <div class="tier"><h3>STL files</h3><div class="price">&#8377;499</div><p>All parts and kits, print at home. Launch offer &#8377;399.</p></div>
 <div class="tier"><h3>Starter (4 cars)</h3><div class="price">&#8377;999</div><p>40 cm strip + 4 clips + 4 ledges. Room to add 3 more.</p></div>
 <div class="tier hot"><span class="tag">BEST VALUE</span><h3>Full strip (7 cars)</h3><div class="price">&#8377;1,499</div><p>Fully loaded: &#8377;214 per car. Launch offer &#8377;1,299.</p></div>
 <div class="tier"><h3>Add-on rack</h3><div class="price">&#8377;199</div><p>One clip + one ledge. 3 for &#8377;549.</p></div>
</div>
<p style="margin-top:2.5mm"><b>Why these prices:</b> static hooks sell for &#8377;277&ndash;302 and a 4-car modular case for &#8377;1,658. PITLANE sits above the hooks as a <i>functional premium</i> product but undercuts the case on price per car. Sell the 7-car strip at &#8377;1,499 with free shipping. Sold direct (Instagram or WhatsApp, paid by UPI), it leaves about <b>&#8377;750 per kit</b> after cost and courier. On Amazon or Flipkart, with about 20% in fees, it leaves about <b>&#8377;460</b>. Don&rsquo;t go below &#8377;1,199 for the full strip: it starts to look like a cheap hook. <b>Free shipping on orders of &#8377;999 and up</b>; &#8377;79 below that.</p>
<h2>Go-to-market plan (India)</h2>
<ul><li><b>Week 0&ndash;2:</b> test-print the newest parts. Film a 15-second Reel of a ledge swinging open (the hook for every ad) and take photos on a real wall.</li>
<li><b>Launch:</b> sell direct on Instagram and WhatsApp with UPI payment. Post in Hot Wheels collector groups on Facebook and WhatsApp. Give 3&ndash;5 local collectors and YouTubers a free strip for honest reviews.</li>
<li><b>Marketplaces:</b> Amazon.in and Flipkart (search reach), Meesho (no commission), Etsy India (STL files and export orders).</li>
<li><b>Meta ads:</b> &#8377;300&ndash;500/day, ages 18&ndash;40, metro and Tier-1 cities, interests: Hot Wheels, die-cast, Matchbox, car culture. Test the 5 posters for a week, keep the 2 with the cheapest clicks, and retarget profile visitors with the &ldquo;7 cars &#8377;1,499&rdquo; ad. Push hardest from October to December (Diwali and Christmas gifting).</li>
<li><b>Listing title:</b> &ldquo;PITLANE Swing-Out Wall Display for Carded 1:64 Die-cast Cars, fits Hot Wheels&reg; &amp; Matchbox&reg; mainline cards, 7-car 40 cm strip&rdquo;.</li></ul>
<h2>Name</h2>
<p><b>PITLANE</b>: every car gets its own garage door, like a pit box in the pit lane at a race, and the strip is the pit wall. The orange stripe nods to the orange track every collector remembers. Backups: <b>CardGarage</b>, <b>Swing Grid</b>. Before you register a name, check trademark and domain availability (India: the IP India trademark search, classes 20 and 28; plus Instagram handle and domain).</p>
{foot(3)}</section></body></html>"""

AD = CSS + """
html,body{width:1080px;height:1350px;overflow:hidden}
.ad{width:1080px;height:1350px;position:relative;overflow:hidden;background:var(--asphalt);color:#fff}
.pad{position:absolute;left:72px;right:72px}
.logo{font-size:44px}
.kick{display:inline-block;background:var(--orange);color:#141414;font-weight:800;font-size:23px;letter-spacing:1px;padding:9px 18px;border-radius:8px;text-transform:uppercase}
h1{font-size:104px;line-height:.95} h1 em{font-style:normal;color:var(--orange)}
.sub{font-size:30px;line-height:1.35;color:#d9dbe1}
.cta{display:inline-flex;align-items:center;gap:16px;background:#fff;color:#141414;font-weight:800;font-size:30px;padding:18px 30px;border-radius:14px}
.cta b{color:var(--orange)}
.tile{background:#fff;border-radius:22px;overflow:hidden} .tile img{width:100%;height:100%;object-fit:contain;display:block}
.trackbar{position:absolute;left:0;right:0;bottom:0;height:18px}
.fine{position:absolute;left:72px;right:72px;bottom:30px;font-size:14px;color:#8d929e}
.chip{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.18);border-radius:16px;padding:18px 22px;font-size:24px;line-height:1.3}
.chip b{display:block;font-family:Anton,sans-serif;font-weight:400;font-size:44px;color:var(--yellow)}
"""
def ad(body, light=False):
    st = ' style="background:#f4f4f2;color:#141414"' if light else ""
    return f'<!doctype html><html><head><meta charset="utf-8"><title>ad</title>{FONTS}<style>{AD}</style></head><body><div class="ad"{st}>{body}<div class="trackbar track"></div></div></body></html>'
FINE = '<div class="fine">Fits standard 1:64 carded cars (Hot Wheels&reg;, Matchbox&reg;). Not affiliated with Mattel.</div>'
ads = [
ad(f"""<img src="img/photo_prototype_7rack.jpg" style="position:absolute;left:0;top:0;width:1080px;height:860px;object-fit:cover;object-position:50% 40%">
<div style="position:absolute;left:0;right:0;top:600px;height:260px;background:linear-gradient(180deg,rgba(27,30,37,0),rgba(27,30,37,1))"></div>
<div class="pad" style="top:56px"><div class="logo" style="background:rgba(20,22,27,.75);display:inline-block;padding:8px 18px;border-radius:10px">PIT<b>LANE</b></div></div>
<div class="pad" style="top:820px"><h1>Your cars deserve<br><em>a garage.</em></h1>
<div class="sub" style="margin-top:20px">A swing-out wall display for carded die-cast. Every name on show.</div>
<div class="cta" style="margin-top:34px">Shop now &middot; from <b>&#8377;999</b></div></div>{FINE}"""),
ad(f"""<div class="pad" style="top:64px"><span class="kick">Swing it open</span><h1 style="margin-top:22px">Grab one card.<br><em>Leave the rest.</em></h1></div>
<div class="tile pad" style="top:400px;height:640px;padding:18px"><img src="img/one_open.png"></div>
<div class="pad" style="top:1080px;display:flex;gap:18px">
 <div class="chip" style="flex:1"><b>1</b>Lift the ledge 1 mm</div><div class="chip" style="flex:1"><b>2</b>Swing it out</div><div class="chip" style="flex:1"><b>3</b>Slide the card in</div></div>{FINE}"""),
ad(f"""<div class="pad" style="top:64px"><span class="kick">7 cars &middot; 40 cm</span><h1 style="margin-top:22px">Every name.<br><em>Every car.</em></h1>
<div class="sub" style="margin-top:16px;max-width:430px">Each row steps out 7 mm, so no card hides the one above it.</div></div>
<div class="tile" style="position:absolute;right:72px;top:380px;width:470px;height:880px;padding:16px"><img src="img/hero_7.png"></div>
<div class="pad" style="top:560px;width:430px;display:flex;flex-direction:column;gap:18px">
 <div class="chip"><b>54 mm</b>between racks</div><div class="chip"><b>14 mm</b>corner posts keep cards upright</div><div class="chip"><b>0 tools</b>clips hook on by hand</div></div>{FINE}"""),
ad(f"""<span></span><div class="pad" style="top:64px"><span class="kick">Engineered to stay put</span><h1 style="margin-top:22px;color:#141414;font-size:92px">Locks twice.<br><em>Lifts off by hand.</em></h1></div>
<div class="pad" style="top:430px;height:430px;display:grid;grid-template-columns:1fr 1fr;gap:18px"><div class="tile" style="padding:10px;border:2px solid #e3e5ea"><img src="img/hinge_closeup.png"></div><div class="tile" style="padding:10px;border:2px solid #e3e5ea"><img src="img/parts.png"></div></div>
<div class="pad" style="top:900px;display:flex;gap:18px">
 <div class="chip" style="flex:1;background:#fff;color:#141414;border-color:#e3e5ea"><b style="color:var(--orange)">2&times;</b>L-hooks behind two lips</div>
 <div class="chip" style="flex:1;background:#fff;color:#141414;border-color:#e3e5ea"><b style="color:var(--orange)">Click</b>solid bump clicks into the strip</div>
 <div class="chip" style="flex:1;background:#fff;color:#141414;border-color:#e3e5ea"><b style="color:var(--orange)">0</b>supports needed to print</div></div>
<div class="pad" style="top:1130px;font-size:28px;font-weight:700;color:#141414">Strip + clips + ledges. Real parts, printed and tested with real cars.</div>
<div class="fine" style="color:#6b7180">Fits standard 1:64 carded cars (Hot Wheels&reg;, Matchbox&reg;). Not affiliated with Mattel.</div>""", light=True),
ad(f"""<div class="pad" style="top:64px"><div class="logo">PIT<b>LANE</b></div><h1 style="margin-top:26px">Pick your<br><em>pit lane.</em></h1></div>
<div class="pad" style="top:430px;display:grid;grid-template-columns:1fr 1fr;gap:22px">
 <div class="chip" style="padding:28px"><span style="font-size:24px;color:#c9ccd3">Starter &middot; 4 cars</span><b style="font-size:72px;margin-top:6px">&#8377;999</b>40 cm strip, room for 3 more</div>
 <div class="chip" style="padding:28px;border:3px solid var(--orange)"><span style="font-size:24px;color:var(--orange);font-weight:800">BEST VALUE &middot; 7 cars</span><b style="font-size:72px;margin-top:6px">&#8377;1,499</b>Fully loaded 40 cm strip</div>
 <div class="chip" style="padding:28px"><span style="font-size:24px;color:#c9ccd3">Add-on rack</span><b style="font-size:72px;margin-top:6px">&#8377;199</b>One clip + one ledge</div>
 <div class="chip" style="padding:28px"><span style="font-size:24px;color:#c9ccd3">Print it yourself</span><b style="font-size:72px;margin-top:6px">&#8377;499</b>All STL files</div></div>
<div class="tile pad" style="top:950px;height:200px;padding:8px"><img src="img/photo_prototype_7rack.jpg" style="object-fit:cover"></div>
<div class="pad" style="top:1185px"><span class="cta" style="font-size:26px;padding:12px 24px">DM to order &middot; UPI &middot; free shipping over <b>&#8377;999</b></span></div>"""),
]
def run(a): subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=8000"] + a, check=True, capture_output=True)
os.chdir(HERE)
(HERE / "sales_pitch.html").write_text(doc)
run(["--no-pdf-header-footer", f"--print-to-pdf={HERE}/sales_pitch.pdf", f"file://{HERE}/sales_pitch.html"])
for i, h in enumerate(ads, 1):
    f = HERE / f"meta_ad_{i}.html"; f.write_text(h); run(["--window-size=1080,1350", f"--screenshot={HERE}/meta_ad_{i}.png", f"file://{f}"])
for f in HERE.glob("*.html"): f.unlink()
print("done")
