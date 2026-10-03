"""Builds pitch_report.pdf (2 x A4) and poster_1..5.png (1080x1350) from HTML with headless Chromium."""
import os, subprocess, pathlib
HERE = pathlib.Path(__file__).resolve().parent
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
NAME = "SWINGRACK"   # working product name - change here
FONTS = '<link href="fonts/fonts.css" rel="stylesheet">'   # Anton + Inter (SIL OFL), downloaded from Google Fonts
BASE_CSS = """
:root{--ink:#14161b;--asphalt:#1d2027;--orange:#ff6a13;--yellow:#ffc21a;--paper:#ffffff;--soft:#f3f4f6;--muted:#5b6170;}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Inter,DejaVu Sans,sans-serif;color:var(--ink);background:var(--paper)}
h1,h2,.display{font-family:Anton,Impact,'DejaVu Sans Condensed',sans-serif;font-weight:400;letter-spacing:.5px;text-transform:uppercase}
.stripe{background:repeating-linear-gradient(-45deg,var(--orange) 0 14px,var(--ink) 14px 28px)}
"""
TM = "Hot Wheels&reg; is a trademark of Mattel, Inc. This product is independent and is not affiliated with or endorsed by Mattel."

pitch = f"""<!doctype html><html><head><meta charset="utf-8"><title>{NAME} pitch</title>{FONTS}<style>{BASE_CSS}
@page{{size:A4;margin:0}}
.page{{width:210mm;height:297mm;position:relative;overflow:hidden;page-break-after:always;padding:14mm 14mm 12mm}}
.page:last-child{{page-break-after:auto}}
.top{{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:3px solid var(--ink);padding-bottom:4mm}}
.brand{{font-family:Anton,Impact,sans-serif;font-size:30pt;line-height:1}} .brand span{{color:var(--orange)}}
.tag{{font-size:9pt;color:var(--muted);text-align:right;line-height:1.35}}
h1{{font-size:30pt;line-height:1.05;margin:5mm 0 3mm}} h1 em{{font-style:normal;color:var(--orange)}}
h2{{font-size:15pt;margin:0 0 2.5mm;display:flex;align-items:center;gap:3mm}} h2::before{{content:"";width:6mm;height:3mm;background:var(--orange);display:inline-block}}
p,li{{font-size:9.2pt;line-height:1.45}} ul{{padding-left:4.5mm}} li{{margin-bottom:1.2mm}}
.lead{{font-size:10.5pt;line-height:1.45;color:#2b2f38;max-width:150mm}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:7mm}}
.card{{background:var(--soft);border-radius:3mm;padding:3.5mm 4.5mm}} .card li{{font-size:8.6pt;margin-bottom:.6mm}}
.hero{{display:grid;grid-template-columns:1.15fr 1fr;gap:6mm;margin:4mm 0}}
.hero figure{{background:var(--soft);border-radius:3mm;overflow:hidden;display:flex;flex-direction:column}}
.hero img{{width:100%;height:68mm;object-fit:contain;background:#fff}}
.hero .photo img{{object-fit:cover;object-position:50% 40%}}
figcaption{{font-size:8pt;color:var(--muted);padding:2mm 3mm}}
.steps{{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm;margin-top:3mm}}
.step{{background:var(--asphalt);color:#fff;border-radius:3mm;padding:4mm;position:relative}}
.step b.n{{font-family:Anton,sans-serif;font-size:22pt;color:var(--orange);display:block;line-height:1}}
.step h3{{font-size:10.5pt;margin:1.5mm 0 1mm}} .step p{{font-size:8.6pt;color:#d6d8de;line-height:1.45}}
.step img{{width:100%;height:21mm;object-fit:contain;background:#fff;border-radius:2mm;margin-top:2.5mm}}
table{{width:100%;border-collapse:collapse;font-size:9pt}} th{{background:var(--ink);color:#fff;text-align:left;padding:2mm}} td{{padding:1.3mm 2mm;border-bottom:1px solid #dde0e6}}
tr:nth-child(even) td{{background:var(--soft)}}
.feat{{display:grid;grid-template-columns:1fr 1fr;gap:3mm 6mm}}
.feat div{{border-left:3px solid var(--orange);padding:0.5mm 0 0.5mm 3mm}} .feat b{{display:block;font-size:9.8pt;margin-bottom:.6mm}} .feat span{{font-size:8.4pt;color:#3b404b;line-height:1.45;display:block}}
.foot{{position:absolute;left:14mm;right:14mm;bottom:5mm;font-size:7pt;color:var(--muted);display:flex;justify-content:space-between;border-top:1px solid #dde0e6;padding-top:2mm}}
.bar{{position:absolute;left:0;right:0;top:0;height:4mm}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:3mm;margin:4mm 0 4mm}}
.kpi{{background:var(--ink);color:#fff;border-radius:3mm;padding:3.5mm}} .kpi b{{font-family:Anton,sans-serif;font-size:20pt;color:var(--yellow);display:block;line-height:1.05;font-weight:400}} .kpi span{{font-size:8pt;color:#c9ccd3}}
.imgrow{{display:grid;grid-template-columns:1fr 1fr;gap:4mm;margin-top:3mm}} .imgrow img{{width:100%;height:31mm;object-fit:contain;background:var(--soft);border-radius:2mm}}
</style></head><body>
<section class="page"><div class="bar stripe"></div>
 <div class="top"><div class="brand">SWING<span>RACK</span></div><div class="tag">Product pitch &middot; 2026<br>Modular wall display for carded 1:64 die-cast</div></div>
 <h1>Your collection, on the wall.<br><em>Every card opens like a door.</em></h1>
 <p class="lead">{NAME} is a 3D-printed wall rack for carded die-cast cars. Each card gets its own swing-out ledge. The ledges are stacked and staggered so every name stays readable, and you can take any one card out without touching the others.</p>
 <div class="hero">
  <figure><img src="img/hero_closed.png"><figcaption>4-car kit, closed: the cards step forward 7 mm per row, so no card hides the one above it.</figcaption></figure>
  <figure class="photo"><img src="img/photo_prototype_wide.jpg"><figcaption>Early printed prototype holding real carded cars (photo by the designer).</figcaption></figure>
 </div>
 <div class="grid2">
  <div><h2>The problem</h2><ul>
   <li>Carded cars end up in boxes or on peg hooks, where they hang behind each other and the backs get bent.</li>
   <li>Getting one card off a crowded hook means unhooking the cards in front of it.</li>
   <li>Most shelf displays are built for loose cars, not for cards with a blister on the front.</li></ul></div>
  <div><h2>The solution</h2><ul>
   <li>One ledge per card, hinged on a vertical pin. Lift it 1 mm, swing it out, slide the card out.</li>
   <li>A slot with a low front lip and a tall back wall holds the card upright while its printed name stays visible.</li>
   <li>Modular: one wall strip carries up to 4 cars, and strips lock end-to-end for taller stacks.</li></ul></div>
 </div>
 <h2 style="margin-top:4mm">How it works</h2>
 <div class="steps">
  <div class="step"><b class="n">01</b><h3>Screw the strip to the wall</h3><p>Two or three 5 mm countersunk screws. Hook lips every 20 mm.</p><img src="img/frame_only.png"></div>
  <div class="step"><b class="n">02</b><h3>Drop a clip on a hook lip</h3><p>Hold it 6 mm above a lip, push it in and let go. It locks under its own weight. To remove it, lift and pull.</p><img src="img/hang_step3.png"></div>
  <div class="step"><b class="n">03</b><h3>Drop the ledge on the pin</h3><p>Slide a card into the slot. A small bump clicks the ledge shut and a stop nub keeps it at 0&deg;.</p><img src="img/hinge_closeup.png"></div>
 </div>
 <div class="foot"><span>{TM}</span><span>1 / 2</span></div>
</section>

<section class="page"><div class="bar stripe"></div>
 <div class="top"><div class="brand">SWING<span>RACK</span></div><div class="tag">Design, kits and next steps</div></div>
 <div class="kpis">
  <div class="kpi"><b>3</b><span>printed part types: strip, clip, ledge</span></div>
  <div class="kpi"><b>0</b><span>support material needed to print</span></div>
  <div class="kpi"><b>2&ndash;6</b><span>car kits, more by adding strips</span></div>
  <div class="kpi"><b>~6 mm</b><span>lift and pull to take a clip off</span></div>
 </div>
 <h2>Engineering that survived the test prints</h2>
 <div class="feat">
  <div><b>Hooks that can't snap</b><span>The hook lips run across the full 30 mm width of the strip, and the strip prints on its edge, so the layers run along each hook. The earlier pegs broke where they met the strip.</span></div>
  <div><b>Gravity lock, no tools</b><span>A 30 mm finger drops behind a lip. Side cheeks hug the strip so the clip can't twist. The bottom of the clip rests on the lip below it.</span></div>
  <div><b>No sagging ledge</b><span>A support pad sits under the closed ledge, and the barrel is 18 mm tall. A stop nub fits a notch in the ledge and holds it at 0&deg;. A bump-and-dimple detent keeps it closed.</span></div>
  <div><b>Names always visible</b><span>Each rack sits 7 mm further from the wall than the one below it. The 1 mm front lip leaves the card title in view.</span></div>
  <div><b>Stackable strips</b><span>A simple C-hook joint links strips end-to-end: press the next strip on from the front, then screw it down.</span></div>
  <div><b>Prints on any FDM printer</b><span>Every part was checked for overhangs: there are only two short bridges and no supports. 252 mm long strip, PLA or PETG.</span></div>
 </div>
 <div class="imgrow"><img src="img/parts.png"><img src="img/all_open.png"></div>
 <h2 style="margin-top:4mm">Kit line-up</h2>
 <table><tr><th>Kit</th><th>Wall strips</th><th>Hinge clips</th><th>Ledges</th><th>Stack height</th><th>Est. filament*</th></tr>
  <tr><td><b>2 cars</b></td><td>1</td><td>2 (depth 0&ndash;1)</td><td>2</td><td>119 mm</td><td>&le; 120 g</td></tr>
  <tr><td><b>3 cars</b></td><td>1</td><td>3 (depth 0&ndash;2)</td><td>3</td><td>179 mm</td><td>&le; 155 g</td></tr>
  <tr><td><b>4 cars</b></td><td>1</td><td>4 (depth 0&ndash;3)</td><td>4</td><td>239 mm</td><td>&le; 185 g</td></tr>
  <tr><td><b>5 cars</b></td><td>2</td><td>5 (depth 0&ndash;4)</td><td>5</td><td>299 mm</td><td>&le; 280 g</td></tr>
  <tr><td><b>6 cars</b></td><td>2</td><td>6 (depth 0&ndash;5)</td><td>6</td><td>359 mm</td><td>&le; 315 g</td></tr></table>
 <p style="font-size:7.5pt;color:var(--muted);margin-top:1.5mm">*Upper bound from STL volume printed 100% solid in PLA; real prints with normal infill use less. Fits cards about 105 &times; 165 mm with a blister up to 42 mm tall.</p>
 <div class="grid2" style="margin-top:3mm">
  <div class="card"><h2>Who it's for</h2><ul><li>Collectors who keep their cars carded.</li><li>Hobby and toy shops that want a neat counter or wall display.</li><li>Makers who buy printable files on Printables, Etsy and similar marketplaces.</li></ul></div>
  <div class="card"><h2>Next steps</h2><ul><li>Test print the v2 hook strip and clip, then do load and drop tests with full cards.</li><li>Launch the STL files and printed kits. Set prices after the cost test.</li><li>Add-ons: colour sets, snap-on name plates, an 8-car kit.</li></ul></div>
 </div>
 <div class="foot"><span>{TM}</span><span>2 / 2</span></div>
</section></body></html>"""

POSTER_CSS = BASE_CSS + """
html,body{width:1080px;height:1350px;overflow:hidden}
.p{width:1080px;height:1350px;position:relative;overflow:hidden;background:var(--asphalt);color:#fff;padding:80px}
.brand{font-family:Anton,sans-serif;font-size:40px;letter-spacing:1px} .brand span{color:var(--orange)}
.kicker{display:inline-block;background:var(--orange);color:var(--ink);font-weight:800;font-size:24px;padding:10px 20px;border-radius:8px;letter-spacing:1px;text-transform:uppercase}
h1{font-size:112px;line-height:.95;margin:26px 0 18px} h1 em{font-style:normal;color:var(--orange)}
.sub{font-size:32px;line-height:1.35;color:#d9dbe1;max-width:860px}
.stripe-b{position:absolute;left:0;right:0;bottom:0;height:22px}
.fine{position:absolute;left:80px;right:80px;bottom:44px;font-size:15px;color:#8e93a0}
.tile{background:#fff;border-radius:22px;overflow:hidden}
.tile img{width:100%;height:100%;object-fit:contain;display:block}
"""
def poster(body, light=False):
    bg = "background:#f4f4f2;color:var(--ink)" if light else ""
    return f'<!doctype html><html><head><meta charset="utf-8"><title>poster</title>{FONTS}<style>{POSTER_CSS}</style></head><body><div class="p" style="{bg}">{body}<div class="stripe-b stripe"></div></div></body></html>'

posters = [
poster(f"""<div class="brand">SWING<span>RACK</span></div>
<h1 style="margin-top:40px">Your cars.<br><em>On the wall.</em></h1>
<div class="sub">A swing-out wall display for carded die-cast. Every card is visible, and each one opens like a door.</div>
<div class="tile" style="position:absolute;left:80px;right:80px;top:640px;height:560px;padding:20px"><img src="img/hero_closed.png"></div>
<div class="fine">{TM}</div>"""),
poster(f"""<div class="kicker">How it works</div>
<h1 style="font-size:96px">3 steps.<br><em>Zero tools*</em></h1>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:28px;margin-top:40px">
 {''.join(f'<div><div class="tile" style="height:330px;padding:12px"><img src="img/{im}"></div><div style="font-family:Anton,sans-serif;font-size:64px;color:var(--orange);margin-top:22px">0{i+1}</div><div style="font-size:30px;font-weight:800;margin:6px 0 8px">{t}</div><div style="font-size:23px;color:#c9ccd3;line-height:1.4">{d}</div></div>' for i,(im,t,d) in enumerate([("frame_only.png","Mount the strip","Screw it to the wall. Hook lips every 20 mm."),("hang_step3.png","Drop in the clip","Push it onto a lip and let go. It locks under its own weight."),("one_open.png","Swing &amp; slide","Lift the ledge 1 mm, swing it out and slide your card in.")]))}
</div>
<div class="fine">*A screwdriver for the wall strip, that's it. {TM}</div>"""),
poster(f"""<div class="kicker">Swing it open</div>
<h1 style="font-size:104px">Grab one card.<br><em>Leave the rest.</em></h1>
<div class="sub">Each ledge pivots on its own pin. A detent clicks it shut and a stop nub holds it level. No unhooking the whole row.</div>
<div class="tile" style="position:absolute;left:80px;right:80px;top:650px;height:560px;padding:20px"><img src="img/one_open.png"></div>
<div class="fine">{TM}</div>"""),
poster(f"""<div style="position:absolute;inset:0"><img src="img/photo_prototype_close.jpg" style="width:100%;height:100%;object-fit:cover;object-position:50% 35%"></div>
<div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(20,22,27,.0) 35%,rgba(20,22,27,.92) 72%)"></div>
<div style="position:absolute;left:80px;right:80px;bottom:120px">
 <div class="kicker">Tested with real cars</div>
 <h1 style="font-size:100px">Made by a collector.<br><em>For collectors.</em></h1>
 <div class="sub">Designed, printed and test-fitted with real carded cars, one iteration at a time.</div></div>
<div class="fine" style="color:#aab0bb">Photo: early printed prototype. {TM}</div>"""),
poster(f"""<div class="kicker" style="color:var(--ink)">Pick your kit</div>
<h1 style="font-size:104px;color:var(--ink)">2 to 6 cars.<br><em>Add more anytime.</em></h1>
<div style="display:grid;grid-template-columns:1fr 1.1fr;gap:40px;margin-top:30px;align-items:start">
 <div class="tile" style="height:720px;padding:14px;border:2px solid #e3e4e8"><img src="img/parts.png"></div>
 <div>{''.join(f'<div style="display:flex;justify-content:space-between;align-items:center;background:#fff;border:2px solid #e3e4e8;border-radius:16px;padding:20px 26px;margin-bottom:16px"><span style="font-family:Anton,sans-serif;font-size:46px">{n} CARS</span><span style="font-size:22px;color:#5b6170;text-align:right">{s} strip{"s" if s>1 else ""}<br>{h} mm tall</span></div>' for n,s,h in [(2,1,119),(3,1,179),(4,1,239),(5,2,299),(6,2,359)])}
 <div style="font-size:24px;font-weight:800;margin-top:10px">Prints with no supports &middot; PLA / PETG</div></div>
</div>
<div class="fine" style="color:#6b7180">{TM}</div>""", light=True),
]

def run(args): subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=8000"] + args, check=True, capture_output=True)
os.chdir(HERE)
pathlib.Path("pitch_report.html").write_text(pitch)
run(["--no-pdf-header-footer", f"--print-to-pdf={HERE}/pitch_report.pdf", f"file://{HERE}/pitch_report.html"])
for i, html in enumerate(posters, 1):
    f = HERE / f"poster_{i}.html"; f.write_text(html)
    run(["--window-size=1080,1350", f"--screenshot={HERE}/poster_{i}.png", f"file://{f}"])
print("done")
