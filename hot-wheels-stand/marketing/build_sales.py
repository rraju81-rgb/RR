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
<div class="top"><div class="logo">PIT<b>LANE</b></div><span>Sales pitch &amp; product analysis<br>Wall racks for carded 1:64 cars &middot; 2026 range</span></div>
<h1>Every card on show.<br><em>Any card out in seconds.</em></h1>
<p class="lead">PITLANE is a 3D-printed wall rack for carded die-cast cars. One 35 cm rack holds 6 cards in stepped rows, so every name stays readable. It comes in two models, and each one comes in a right-hand and a left-hand version. Hang one of each back to back and you get a 12-car centrepiece.</p>
<div class="quote"><b>The pitch (30 seconds):</b> &ldquo;Collectors keep their best cars carded, then hide them in boxes or crush them on peg hooks. PITLANE puts six cards on a 35 cm rail, each row stepped forward so every name shows. On SWING, every card has its own door: swing it out, swap the card, swing it shut, and lift any shelf off its pin to clean it. On SLIDE, every card has its own lane: just slide it in from the side. Add a mirrored left rack and the wall holds twelve.&rdquo;</div>
<div class="g2" style="margin-top:3mm">
 <div class="img"><img src="img/v2_swing_open.png" style="height:48mm"><div class="cap">SWING twin (right + left): one door open on each side. CAD render, cards shown as blanks.</div></div>
 <div class="img"><img src="img/v2_slide_pair.png" style="height:48mm"><div class="cap">SLIDE twin: cards slide in from the right on one rack and from the left on the other.</div></div>
</div>
<h2>The range</h2>
<div class="g3">
 <div class="card"><b>PITLANE SWING (6 cars)</b><p>One 35 cm wall mount (20 mm wide) with 6 hinge pins. Each of the 6 ledges drops onto its own pin. Swing it out to load. Lift 15.5 mm to take it off. It stops at closed and opens to 135&deg;.</p></div>
 <div class="card"><b>PITLANE SLIDE (6 cars)</b><p>A one-piece rack with no moving parts. Every ledge has a solid end stop, and the card slides into the 1.8 mm slot from the open end. The lowest-cost way to display 6 cards.</p></div>
 <div class="card"><b>TWIN = right + left (12 cars)</b><p>A mirrored left-hand rack hangs back to back with the right one, half a row (27.5 mm) lower. The shelves alternate, so opening one side never touches the other.</p></div>
</div>
<h2>Why it wins</h2>
<ul><li><b>Grab one, leave the rest:</b> on hook displays you unhook the cards in front first. On PITLANE each card has its own door (SWING) or its own lane (SLIDE).</li>
<li><b>Names stay readable:</b> the rows step out 4.6 mm, and a low front lip with chamfered corner posts keeps the card title clear.</li>
<li><b>Nothing falls off:</b> the wall mount is one solid piece with the pins built in. There are no clips to come loose while you hang it.</li>
<li><b>Built for real prints:</b> every part prints without supports. The pins have a chamfered root for strength.</li></ul>
{foot(1)}</section>

<section class="page"><div class="bar track"></div>
<div class="top"><div class="logo">PIT<b>LANE</b></div><span>Product analysis</span></div>
<h2>Market</h2>
<p>Adult collectors now drive the die-cast market worldwide (an estimated 58% of revenue, a $4.2&ndash;5.8 billion market growing 5&ndash;6% a year). India&rsquo;s collector scene is young and growing fast: mainline cars sell for roughly &#8377;200&ndash;450 each online, and collectors who keep cars <b>carded</b> have few wall options made for cards.</p>
<h2>Competition and prices in India (Oct 2026)</h2>
<table><tr><th>Product</th><th>What it does</th><th>Price</th><th>PITLANE advantage</th></tr>
<tr><td>3D-printed card hooks (Etsy India)</td><td>Static hooks; cards hang flat, one behind another</td><td>&#8377;277&ndash;302</td><td>Stepped rows, every name visible, each card on its own</td></tr>
<tr><td>Wall-mount 1:64 stands (direct sellers)</td><td>Printed stands for loose cars, packs of 12&ndash;48</td><td>&#8377;550&ndash;1,690</td><td>Made for <i>carded</i> cars</td></tr>
<tr><td>Modular 3D-printed wall case (Etsy India)</td><td>4 cars per module (&asymp; &#8377;415 per car)</td><td>&#8377;1,658+</td><td>6 cars from &#8377;799 (SLIDE, &#8377;133 per car)</td></tr>
<tr><td>Display STL files (Etsy India)</td><td>Print-at-home files</td><td>&#8377;1,188</td><td>All PITLANE files for &#8377;499</td></tr></table>
<p class="src" style="font-size:7pt;margin-top:1mm">Sources: <a href="https://www.etsy.com/in-en/market/hot_wheels_display_3d_printed">Etsy India: 3D-printed displays</a>, <a href="https://www.etsy.com/in-en/listing/1855211793/hot-wheels-display-case-3d-printed">Etsy India: modular wall case</a>, <a href="https://www.etsy.com/in-en/listing/4296116586/3d-printing-modular-car-display-hot">Etsy India: display STL</a>, <a href="https://modmusestore.com/products/hot-wheels-wall-mount-3d-printed-display-stand-1-64-scale">ModMuse wall stand</a>, <a href="https://pricehistory.app/p/esun-pla-3d-printing-filament-1-75mm-iblWdqG5">eSUN PLA+ price in India</a>, <a href="https://magicdrop.in/drops/cheap-hot-wheels">Hot Wheels prices in India</a>.</p>
<h2>SWOT</h2>
<div class="sw">
 <div class="s"><h3>Strengths</h3><ul><li>Two models at two price points, from one design</li><li>A one-piece wall mount: nothing comes loose while you hang it</li><li>Ledges come off for cleaning and can be replaced or sold as spares</li><li>Right + left twin: a symmetric 12-car wall feature</li></ul></div>
 <div class="w"><h3>Weaknesses</h3><ul><li>Fits standard mainline cards only (~105 &times; 165 mm, blister &le; 42 mm)</li><li>Cards on the top rows stand above the 35 cm rack</li><li>SLIDE needs about 11 cm of free wall on its open side to load a card</li><li>The newest pin chamfer and 20 mm wall mount are not yet test-printed</li></ul></div>
 <div class="o"><h3>Opportunities</h3><ul><li>STL sales: zero marginal cost</li><li>Colour editions (orange track, black and white, a two-colour twin)</li><li>Spare and colour-swap ledges for SWING</li><li>Hobby-shop wall displays (B2B), Matchbox and Mini GT variants</li></ul></div>
 <div class="t"><h3>Threats</h3><ul><li>Cheap static hooks at &#8377;277&ndash;302</li><li>Copycats on file marketplaces</li><li>Trademark: never use &ldquo;Hot Wheels&rdquo; as your brand, only &ldquo;fits Hot Wheels&reg; cards&rdquo;</li><li>Pins can snap if the ledges are forced (offer spare ledges and wall mounts)</li></ul></div>
</div>
<h2>Who buys it</h2>
<ul><li><b>Adult carded collectors</b> (18&ndash;40, metro and Tier-1 cities) with 20&ndash;200 cards: SWING and the twins.</li>
<li><b>Parents and gift buyers</b>: SLIDE at &#8377;799 is an easy gift (Diwali and Christmas, Oct&ndash;Dec).</li>
<li><b>Makers</b> with their own 3D printer: the STL pack.</li></ul>
{foot(2)}</section>

<section class="page"><div class="bar track"></div>
<div class="top"><div class="logo">PIT<b>LANE</b></div><span>Pricing &amp; go-to-market</span></div>
<h2>Cost to make (estimate, in rupees)</h2>
<table><tr><th>Item</th><th>SLIDE 6</th><th>SWING 6</th><th>SWING twin 12</th><th>Basis</th></tr>
<tr><td>Filament (PLA+ at &#8377;1,500/kg)</td><td>&#8377;198</td><td>&#8377;225</td><td>&#8377;450</td><td>From the STL files: 132 / 150 / 300 g printed (70% of fully solid)</td></tr>
<tr><td>Electricity</td><td>&#8377;13</td><td>&#8377;15</td><td>&#8377;30</td><td>150 W printer, &#8377;8/kWh, about 12 g/h: 11 / 12.5 / 25 h of printing</td></tr>
<tr><td>Failed-print allowance (15%)</td><td>&#8377;32</td><td>&#8377;36</td><td>&#8377;72</td><td>Reprints, nozzle wear</td></tr>
<tr><td>Box, screws + wall plugs, label</td><td>&#8377;60</td><td>&#8377;60</td><td>&#8377;80</td><td>The 35 cm part fits a standard courier box</td></tr>
<tr><td><b>Total cost</b></td><td><b>&asymp; &#8377;305</b></td><td><b>&asymp; &#8377;340</b></td><td><b>&asymp; &#8377;630</b></td><td>Excludes your time and courier (about &#8377;80&ndash;120 within India)</td></tr></table>
<h2>Recommended prices (INR)</h2>
<div class="g3" style="grid-template-columns:repeat(4,1fr)">
 <div class="tier"><h3>SLIDE &middot; 6 cars</h3><div class="price">&#8377;799</div><p>One-piece rack, right- or left-hand. &#8377;133 per car.</p></div>
 <div class="tier"><h3>SWING &middot; 6 cars</h3><div class="price">&#8377;1,199</div><p>Wall mount + 6 lift-off ledges. Launch offer &#8377;999.</p></div>
 <div class="tier hot"><span class="tag">BEST VALUE</span><h3>SWING twin &middot; 12</h3><div class="price">&#8377;2,199</div><p>Right + left, &#8377;183 per car. SLIDE twin &#8377;1,449.</p></div>
 <div class="tier"><h3>STL files / spares</h3><div class="price">&#8377;499</div><p>All models, print at home (launch &#8377;399). Spare ledge &#8377;99, or 3 for &#8377;249.</p></div>
</div>
<p style="margin-top:2.5mm"><b>Why these prices:</b> static hooks sell for &#8377;277&ndash;302 and a 4-car case for &#8377;1,658. SLIDE takes the gift and entry slot at &#8377;799. SWING is the premium functional product, and the twin is the hero offer. Sold direct (Instagram or WhatsApp, paid by UPI), SWING leaves about <b>&#8377;750</b> after cost and courier, and the SWING twin about <b>&#8377;1,450</b>. On Amazon or Flipkart, with about 20% in fees, SWING leaves about <b>&#8377;520</b>. Don&rsquo;t go below &#8377;999 for SWING or &#8377;699 for SLIDE: it starts to look like a cheap hook. <b>Free shipping on orders of &#8377;999 and up</b>; &#8377;79 below that.</p>
<h2>Go-to-market plan (India)</h2>
<ul><li><b>Week 0&ndash;2:</b> test-print the SWING twin. Film a 15-second Reel of one door swinging out and a ledge lifting off, plus a SLIDE card gliding in. Take photos of the twin on a real wall.</li>
<li><b>Launch:</b> sell direct on Instagram and WhatsApp with UPI payment. Post in Hot Wheels collector groups on Facebook and WhatsApp. Give 3&ndash;5 local collectors and YouTubers a free twin for honest reviews.</li>
<li><b>Marketplaces:</b> Amazon.in and Flipkart (SLIDE as the entry listing, SWING twin as the hero), Meesho (no commission), Etsy India (STL files and export orders).</li>
<li><b>Meta ads:</b> &#8377;300&ndash;500/day, ages 18&ndash;40, metro and Tier-1 cities, interests: Hot Wheels, die-cast, Matchbox, car culture. Test the 5 posters for a week, keep the 2 with the cheapest clicks, and retarget profile visitors with the twin ad. Push hardest from October to December.</li>
<li><b>Listing titles:</b> &ldquo;PITLANE SWING: Swing-Out Wall Rack for 6 Carded 1:64 Die-cast Cars, fits Hot Wheels&reg; &amp; Matchbox&reg; mainline cards, right or left hand&rdquo; and &ldquo;PITLANE SLIDE: 6-Card Slide-In Wall Rack&rdquo;.</li></ul>
<h2>Name</h2>
<p><b>PITLANE</b>: every card gets its own pit box, and the wall mount is the pit wall. The model names say what each one does: <b>SWING</b> doors swing out, <b>SLIDE</b> cards slide in. The orange stripe nods to the orange track. Before you register a name, check trademark and domain availability (India: the IP India trademark search, classes 20 and 28).</p>
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
ad(f"""<div class="pad" style="top:56px"><div class="logo">PIT<b>LANE</b></div><h1 style="margin-top:22px">Your cars deserve<br><em>a garage.</em></h1>
<div class="sub" style="margin-top:16px">12 carded cars, one wall, every name on show.</div></div>
<div class="tile pad" style="top:470px;height:640px;padding:14px"><img src="img/v2_swing_pair.png"></div>
<div class="pad" style="top:1150px"><div class="cta">SWING twin &middot; <b>&#8377;2,199</b> &middot; 12 cars</div></div>{FINE}"""),
ad(f"""<div class="pad" style="top:64px"><span class="kick">PITLANE SWING</span><h1 style="margin-top:22px">Grab one card.<br><em>Leave the rest.</em></h1></div>
<div class="tile pad" style="top:400px;height:640px;padding:18px"><img src="img/v2_swing_one.png"></div>
<div class="pad" style="top:1080px;display:flex;gap:18px">
 <div class="chip" style="flex:1"><b>1</b>Swing the door out</div><div class="chip" style="flex:1"><b>2</b>Slide the card in</div><div class="chip" style="flex:1"><b>3</b>Swing it shut</div></div>{FINE}"""),
ad(f"""<div class="pad" style="top:64px"><span class="kick">PITLANE SLIDE &middot; &#8377;799</span><h1 style="margin-top:22px">Slide it in.<br><em>Done.</em></h1>
<div class="sub" style="margin-top:16px;max-width:430px">One piece, no moving parts. Every card in its own lane, every name on show.</div></div>
<div class="tile" style="position:absolute;right:72px;top:380px;width:470px;height:880px;padding:16px"><img src="img/v2_slide_one.png"></div>
<div class="pad" style="top:620px;width:430px;display:flex;flex-direction:column;gap:18px">
 <div class="chip"><b>6 cars</b>on a 35 cm rack</div><div class="chip"><b>&#8377;133</b>per car</div><div class="chip"><b>Right or left</b>hand, or both</div></div>{FINE}"""),
ad(f"""<span></span><div class="pad" style="top:64px"><span class="kick">Engineered to stay put</span><h1 style="margin-top:22px;color:#141414;font-size:92px">One solid mount.<br><em>Lift-off doors.</em></h1></div>
<div class="pad" style="top:430px;height:430px;display:grid;grid-template-columns:1fr 1fr;gap:18px"><div class="tile" style="padding:10px;border:2px solid #e3e5ea"><img src="img/v2_liftoff.png"></div><div class="tile" style="padding:10px;border:2px solid #e3e5ea"><img src="img/v2_parts.png"></div></div>
<div class="pad" style="top:900px;display:flex;gap:18px">
 <div class="chip" style="flex:1;background:#fff;color:#141414;border-color:#e3e5ea"><b style="color:var(--orange)">0</b>clips to fall off</div>
 <div class="chip" style="flex:1;background:#fff;color:#141414;border-color:#e3e5ea"><b style="color:var(--orange)">15 mm</b>lift and the door comes off</div>
 <div class="chip" style="flex:1;background:#fff;color:#141414;border-color:#e3e5ea"><b style="color:var(--orange)">135&deg;</b>swing, stops at closed</div></div>
<div class="pad" style="top:1130px;font-size:28px;font-weight:700;color:#141414">Wall mount with pins built in, plus 6 drop-on ledges. No supports to print.</div>
<div class="fine" style="color:#6b7180">Fits standard 1:64 carded cars (Hot Wheels&reg;, Matchbox&reg;). Not affiliated with Mattel.</div>""", light=True),
ad(f"""<div class="pad" style="top:64px"><div class="logo">PIT<b>LANE</b></div><h1 style="margin-top:26px">Pick your<br><em>pit lane.</em></h1></div>
<div class="pad" style="top:430px;display:grid;grid-template-columns:1fr 1fr;gap:22px">
 <div class="chip" style="padding:28px"><span style="font-size:24px;color:#c9ccd3">SLIDE &middot; 6 cars</span><b style="font-size:72px;margin-top:6px">&#8377;799</b>One piece, slide-in lanes</div>
 <div class="chip" style="padding:28px"><span style="font-size:24px;color:#c9ccd3">SWING &middot; 6 cars</span><b style="font-size:72px;margin-top:6px">&#8377;1,199</b>Swing-out lift-off doors</div>
 <div class="chip" style="padding:28px;border:3px solid var(--orange)"><span style="font-size:24px;color:var(--orange);font-weight:800">BEST VALUE &middot; SWING twin</span><b style="font-size:72px;margin-top:6px">&#8377;2,199</b>12 cars, right + left</div>
 <div class="chip" style="padding:28px"><span style="font-size:24px;color:#c9ccd3">Print it yourself</span><b style="font-size:72px;margin-top:6px">&#8377;499</b>All STL files</div></div>
<div class="tile pad" style="top:950px;height:200px;padding:8px"><img src="img/v2_slide_pair.png"></div>
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
