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
<div class="quote"><b>The pitch (30 seconds):</b> &ldquo;Collectors keep their best cars carded, then hide them in boxes or crush them on peg hooks. PITLANE gives every card its own swing-out garage on the wall. You can see every name, take any one card out without touching the others, and add racks as your collection grows. It snaps together with no tools. One 40 cm strip holds up to 7 cars, at about the price of a few mainline cars.&rdquo;</div>
<div class="g2" style="margin-top:3mm">
 <div class="img ph"><img src="img/photo_prototype_7rack.jpg"><div class="cap">Real printed prototype loaded with real carded cars (designer&rsquo;s photo).</div></div>
 <div class="img"><img src="img/hero_7.png"><div class="cap">Current design: 7 cars on one 40 cm strip (CAD render, cards shown as blanks).</div></div>
</div>
<h2>What&rsquo;s in the box (7-car kit)</h2>
<div class="g3">
 <div class="card"><b>1&times; wall strip, 40 cm</b><p>One piece, or two halves that lock with a C-interlock. Fixed with 4 screws. Hook-lip pairs every 54 mm.</p></div>
 <div class="card"><b>7&times; hinge clips</b><p>Each clip double-hooks behind two lips and clicks onto a friction bump. Each one sits 7 mm deeper than the one below. No tools.</p></div>
 <div class="card"><b>7&times; swing ledges</b><p>8 mm pin running the full height, a 0&deg; stop, a click detent and 14 mm corner posts that keep the card upright.</p></div>
</div>
<h2>Why it wins</h2>
<ul><li><b>Grab one, leave the rest:</b> other displays make you unhook the cards in front. Here each card has its own door.</li>
<li><b>Names stay readable:</b> a 1 mm front lip and stepped rows mean nothing covers the card title.</li>
<li><b>Built for real prints:</b> every part prints without supports, and every lock was redesigned after real test prints failed.</li>
<li><b>Grows with the collection:</b> buy the strip once and add racks for about $6 each.</li></ul>
{foot(1)}</section>

<section class="page"><div class="bar track"></div>
<div class="top"><div class="logo">PIT<b>LANE</b></div><span>Product analysis</span></div>
<h2>Market</h2>
<p>Adult collectors now drive the die-cast market: an estimated 58% of revenue, worth about $4.2&ndash;5.8 billion worldwide in 2025 and growing 5&ndash;6% a year. North America is the largest region at about 38%. Many collectors keep their cars <b>carded</b> (mint in package), which is the segment PITLANE serves.</p>
<h2>Competition and prices (Oct 2026)</h2>
<table><tr><th>Product</th><th>What it does</th><th>Price</th><th>PITLANE advantage</th></tr>
<tr><td>Etsy 3D-printed hooks and card stands</td><td>Static hooks or stands; cards hang flat or in rows</td><td>$2.75&ndash;$12.86 (e.g. 20 hangers $12.86, 4-pack $12)</td><td>Swing-out access, rows that step forward, double-lock clip</td></tr>
<tr><td>Official collector &ldquo;case strips&rdquo; (Target)</td><td>5 clear sleeves, 10 cars each, stacked</td><td>$9.99 for 50 cars</td><td>Each card visible and removable on its own; no plastic sleeves</td></tr>
<tr><td>Wall cabinets / display cases</td><td>Loose (uncarded) cars behind glass</td><td>$36&ndash;$124 (24&ndash;56 cars)</td><td>Made for <i>carded</i> cars; much cheaper per wall metre</td></tr></table>
<p class="src" style="font-size:7pt;margin-top:1mm">Sources: <a href="https://www.etsy.com/market/hotwheels_carded_display">Etsy carded displays</a>, <a href="https://www.etsy.com/listing/1675476376/die-cast-wall-display-for-standard">Etsy 20-hanger display</a>, <a href="https://www.target.com/p/hot-wheels-collector-case-strips/-/A-95007268">Target collector case strips</a>, <a href="https://www.walmart.com/c/kp/hot-wheels-display">Walmart displays</a>, <a href="https://marketintelo.com/report/die-cast-collectibles-market">Market Intelo</a>, <a href="https://www.intelmarketresearch.com/diecast-model-car-market-33549">Intel Market Research</a>.</p>
<h2>SWOT</h2>
<div class="sw">
 <div class="s"><h3>Strengths</h3><ul><li>A genuinely new mechanism: swing-out door for each card</li><li>Every name visible; rows step out 7 mm</li><li>No supports, low cost per unit, modular</li><li>Designer is a collector, with real-print testing</li></ul></div>
 <div class="w"><h3>Weaknesses</h3><ul><li>Fits standard mainline cards only (~105 &times; 165 mm, blister &le; 42 mm)</li><li>Print time per kit is high (estimate 12&ndash;18 h)</li><li>Ledges above must be opened to load a lower card</li><li>The newest version (friction bump, L-lock) is not yet test-printed</li></ul></div>
 <div class="o"><h3>Opportunities</h3><ul><li>Sell the STL files too: zero marginal cost</li><li>Colour editions (orange track, black and white)</li><li>Premium / long-card ledge, Matchbox and Mini GT variants</li><li>Hobby-shop wall displays (B2B)</li></ul></div>
 <div class="t"><h3>Threats</h3><ul><li>Cheap static hooks at $3&ndash;13</li><li>Copycats on file marketplaces</li><li>Trademark: never use &ldquo;Hot Wheels&rdquo; as your brand, only &ldquo;fits Hot Wheels&reg; cards&rdquo;</li><li>Shipping cost of a 40 cm part</li></ul></div>
</div>
<h2>Who buys it</h2>
<ul><li><b>Adult carded collectors</b> (25&ndash;45) with 20&ndash;200 cards and a wall to fill. This is the main ad audience.</li>
<li><b>Parents</b> buying a tidy display for a child&rsquo;s collection (gift season: Nov&ndash;Dec).</li>
<li><b>Makers</b> who print their own and buy the STL files on Printables, MakerWorld and Cults3D.</li></ul>
{foot(2)}</section>

<section class="page"><div class="bar track"></div>
<div class="top"><div class="logo">PIT<b>LANE</b></div><span>Pricing &amp; go-to-market</span></div>
<h2>Cost to make (estimate)</h2>
<table><tr><th>Item</th><th>4-car kit</th><th>7-car kit</th><th>Basis</th></tr>
<tr><td>Filament (PLA/PETG at about $20/kg)</td><td>$3.40&ndash;4.00</td><td>$5.40&ndash;6.20</td><td>From the STL files: 281 g / 449 g if fully solid; real prints about 60&ndash;70% of that</td></tr>
<tr><td>Power and printer wear</td><td>$1.50</td><td>$2.50</td><td>About $0.15/h &times; 10&ndash;16 h of printing</td></tr>
<tr><td>4 screws, wall plugs, packaging</td><td>$2.00</td><td>$2.50</td><td>Box for a 40 cm strip (or ship the 2-piece strip)</td></tr>
<tr><td><b>Total cost</b></td><td><b>&asymp; $7&ndash;8</b></td><td><b>&asymp; $10&ndash;11</b></td><td>Excludes your time and shipping (charge shipping separately)</td></tr></table>
<h2>Recommended prices (USD)</h2>
<div class="g3" style="grid-template-columns:repeat(4,1fr)">
 <div class="tier"><h3>STL files</h3><div class="price">$7.99</div><p>All parts and kits, print at home. Launch at $5.99. Sell on Etsy digital, Cults3D and MakerWorld.</p></div>
 <div class="tier"><h3>Starter (4 cars)</h3><div class="price">$29.99</div><p>40 cm strip + 4 clips + 4 ledges. Room to add 3 more.</p></div>
 <div class="tier hot"><span class="tag">BEST VALUE</span><h3>Full strip (7 cars)</h3><div class="price">$39.99</div><p>Fully loaded. $5.71 per car. Launch at $34.99.</p></div>
 <div class="tier"><h3>Add-on rack</h3><div class="price">$6.99</div><p>One clip + one ledge. Bundle of 3 for $17.99.</p></div>
</div>
<p style="margin-top:2.5mm"><b>Why these prices:</b> static Etsy hooks sell for $3&ndash;13 and glass cabinets for $36&ndash;124. PITLANE sits between them as a <i>functional premium</i> product at about $5&ndash;6 per car. At $39.99 on Etsy (roughly $4.40 in fees) the 7-car kit leaves about <b>$24&ndash;25 margin</b> before your time. Don&rsquo;t go below $29.99 for the full strip: it signals a cheap hook, which this isn&rsquo;t.</p>
<h2>Go-to-market plan</h2>
<ul><li><b>Week 0&ndash;2:</b> test-print the v12 parts, film a 15 s video of a ledge swinging open (the hook for every ad) and take photos on a real wall.</li>
<li><b>Launch:</b> list on Etsy (physical + digital) and on MakerWorld/Printables with a free single rack to build reviews. Post the video to r/HotWheels and to Instagram and TikTok collector groups.</li>
<li><b>Meta ads:</b> $10&ndash;15/day, ages 25&ndash;45, interests: Hot Wheels, die-cast, Matchbox, car culture. Test the 5 posters, keep the 2 cheapest per click, retarget site visitors with the &ldquo;Full strip $39.99&rdquo; ad.</li>
<li><b>Listing title:</b> &ldquo;PITLANE Swing-Out Wall Display for Carded 1:64 Die-cast Cars, fits Hot Wheels&reg; &amp; Matchbox&reg; mainline cards, 7-car 40 cm strip&rdquo;.</li></ul>
<h2>Name</h2>
<p><b>PITLANE</b>: each ledge is a garage that swings open, like the pit lane at a race. The orange stripe nods to the orange track every collector remembers. Backups: <b>CardGarage</b>, <b>Swing Grid</b>. Before you register a name, check trademark and domain availability (e.g. USPTO TESS, your local registry, the Etsy shop name).</p>
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
<div class="cta" style="margin-top:34px">Shop now &middot; from <b>$29.99</b></div></div>{FINE}"""),
ad(f"""<div class="pad" style="top:64px"><span class="kick">Swing it open</span><h1 style="margin-top:22px">Grab one card.<br><em>Leave the rest.</em></h1></div>
<div class="tile pad" style="top:400px;height:640px;padding:18px"><img src="img/open_7.png"></div>
<div class="pad" style="top:1080px;display:flex;gap:18px">
 <div class="chip" style="flex:1"><b>1</b>Lift the ledge 1 mm</div><div class="chip" style="flex:1"><b>2</b>Swing it out</div><div class="chip" style="flex:1"><b>3</b>Slide the card in</div></div>{FINE}"""),
ad(f"""<div class="pad" style="top:64px"><span class="kick">7 cars &middot; 40 cm</span><h1 style="margin-top:22px">Every name.<br><em>Every car.</em></h1>
<div class="sub" style="margin-top:16px;max-width:430px">Each row steps out 7 mm, so no card hides the one above it.</div></div>
<div class="tile" style="position:absolute;right:72px;top:380px;width:470px;height:880px;padding:16px"><img src="img/hero_7.png"></div>
<div class="pad" style="top:560px;width:430px;display:flex;flex-direction:column;gap:18px">
 <div class="chip"><b>54 mm</b>between racks</div><div class="chip"><b>14 mm</b>corner posts keep cards upright</div><div class="chip"><b>0 tools</b>clips hook on by hand</div></div>{FINE}"""),
ad(f"""<span></span><div class="pad" style="top:64px"><span class="kick">Engineered to stay put</span><h1 style="margin-top:22px;color:#141414;font-size:92px">Locks twice.<br><em>Lifts off by hand.</em></h1></div>
<div class="tile pad" style="top:430px;height:430px;padding:10px;border:2px solid #e3e5ea"><img src="../board/double_lock_detail.png"></div>
<div class="pad" style="top:900px;display:flex;gap:18px">
 <div class="chip" style="flex:1;background:#fff;color:#141414;border-color:#e3e5ea"><b style="color:var(--orange)">2&times;</b>L-hooks behind two lips</div>
 <div class="chip" style="flex:1;background:#fff;color:#141414;border-color:#e3e5ea"><b style="color:var(--orange)">Click</b>friction bump stops creep</div>
 <div class="chip" style="flex:1;background:#fff;color:#141414;border-color:#e3e5ea"><b style="color:var(--orange)">0</b>supports needed to print</div></div>
<div class="pad" style="top:1130px;font-size:28px;font-weight:700;color:#141414">Strip + clips + ledges. Real parts, printed and tested with real cars.</div>
<div class="fine" style="color:#6b7180">Fits standard 1:64 carded cars (Hot Wheels&reg;, Matchbox&reg;). Not affiliated with Mattel.</div>""", light=True),
ad(f"""<div class="pad" style="top:64px"><div class="logo">PIT<b>LANE</b></div><h1 style="margin-top:26px">Pick your<br><em>pit lane.</em></h1></div>
<div class="pad" style="top:430px;display:grid;grid-template-columns:1fr 1fr;gap:22px">
 <div class="chip" style="padding:28px"><span style="font-size:24px;color:#c9ccd3">Starter &middot; 4 cars</span><b style="font-size:72px;margin-top:6px">$29.99</b>40 cm strip, room for 3 more</div>
 <div class="chip" style="padding:28px;border:3px solid var(--orange)"><span style="font-size:24px;color:var(--orange);font-weight:800">BEST VALUE &middot; 7 cars</span><b style="font-size:72px;margin-top:6px">$39.99</b>Fully loaded 40 cm strip</div>
 <div class="chip" style="padding:28px"><span style="font-size:24px;color:#c9ccd3">Add-on rack</span><b style="font-size:72px;margin-top:6px">$6.99</b>One clip + one ledge</div>
 <div class="chip" style="padding:28px"><span style="font-size:24px;color:#c9ccd3">Print it yourself</span><b style="font-size:72px;margin-top:6px">$7.99</b>All STL files</div></div>
<div class="tile pad" style="top:950px;height:200px;padding:8px"><img src="img/photo_prototype_7rack.jpg" style="object-fit:cover"></div>
<div class="pad" style="top:1185px"><span class="cta" style="font-size:26px;padding:12px 24px">Shop now &rarr;</span></div>"""),
]
def run(a): subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=8000"] + a, check=True, capture_output=True)
os.chdir(HERE)
(HERE / "sales_pitch.html").write_text(doc)
run(["--no-pdf-header-footer", f"--print-to-pdf={HERE}/sales_pitch.pdf", f"file://{HERE}/sales_pitch.html"])
for i, h in enumerate(ads, 1):
    f = HERE / f"meta_ad_{i}.html"; f.write_text(h); run(["--window-size=1080,1350", f"--screenshot={HERE}/meta_ad_{i}.png", f"file://{f}"])
for f in HERE.glob("*.html"): f.unlink()
print("done")
