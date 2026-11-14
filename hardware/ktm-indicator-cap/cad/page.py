#!/usr/bin/env python3
"""
Write docs/design-review.html: a self-contained review page with the 3D model,
the explanatory figures, the measurement guide, fabrication data and the check
results. Every number on the page is read from out/summary.json, so the page
cannot drift from the model.

Run after build.py and figures.py:   python3 page.py [output.html]
"""
from __future__ import annotations

import datetime
import html
import json
import sys
from pathlib import Path

from build import OUT

DOCS = OUT.parent / "docs"
REPO = "https://github.com/rraju81-rgb/RR/blob/claude/intelligent-pasteur-ygki7k/hardware/ktm-indicator-cap/"
TREE = "https://github.com/rraju81-rgb/RR/tree/claude/intelligent-pasteur-ygki7k/hardware/ktm-indicator-cap/"
REFS = {
    "front": "https://www.bikersbillet.com/product/bikers-billet-ktm-adventure-390-front-indicator-bracket/",
    "rear": "https://www.bikersbillet.com/product/bikers-billet-ktm-adventure-390-rear-indicator-bracket/",
    "reel": "https://www.instagram.com/reel/DfbhKkZozDg/",
}
VIEWER_PARTS = ["CAP", "HOUSING", "LENS", "NECK", "SOCKET", "BOSS", "WASHER", "SCREW",
                "LINER_TOP", "LINER_BOTTOM", "LINER_BACK", "LINER_TIP"]

TEMPLATE = r"""<title>390 Adventure Indicator Cap</title>
<meta name="claude:viewport-fit-sides" content="cover">
<meta name="description" content="Design review for a bolt-on stainless cap that rehouses a loose or broken 390 Adventure indicator.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600&family=Barlow+Condensed:wght@500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: a drawing title block, then a review sheet: the 3D model beside its notes, figures and tables full width below */
:root{
  --bg:#eceff3; --paper:#ffffff; --ink:#14181f; --ink-2:#4b5361; --rule:#d3d8df; --rule-2:#e5e8ed;
  --dim:#1f4e9c; --amber:#d98c00; --ok:#1d7a43; --ok-bg:#e2f1e7; --warn:#b3261e; --warn-bg:#fbeae8;
  --view-bg:#f6f7f9; --code-bg:#eef1f5;
  --fig-ink:#14181f; --fig-ref:#868c97; --fig-steel:#c5cad2; --fig-foam:#5b6472; --fig-housing:#23262d;
  --fig-lens:#f6a300; --fig-lens-edge:#b87400; --fig-dim:#1f4e9c; --fig-down:#0a7d3c; --fig-up:#c22727;
  --fig-bg:#ffffff; --fig-inv:#e9ecf1;
  --display:"Barlow Condensed","Arial Narrow",Arial,sans-serif;
  --body:Barlow,"Segoe UI",Roboto,Arial,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#0e1115; --paper:#161a20; --ink:#e7eaef; --ink-2:#a3abb7; --rule:#2b313a; --rule-2:#21262e;
    --dim:#8db3ff; --amber:#ffb52e; --ok:#5fcf8f; --ok-bg:#15301f; --warn:#ff8a80; --warn-bg:#3a1a18;
    --view-bg:#12161b; --code-bg:#1f242c;
    --fig-ink:#e7eaef; --fig-ref:#7d8693; --fig-steel:#8e98a6; --fig-foam:#46505c; --fig-housing:#2c3139;
    --fig-lens:#f6a300; --fig-lens-edge:#ffb52e; --fig-dim:#8db3ff; --fig-down:#4fc483; --fig-up:#ff7b72;
    --fig-bg:#161a20; --fig-inv:#e9ecf1;
    color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --bg:#0e1115; --paper:#161a20; --ink:#e7eaef; --ink-2:#a3abb7; --rule:#2b313a; --rule-2:#21262e;
  --dim:#8db3ff; --amber:#ffb52e; --ok:#5fcf8f; --ok-bg:#15301f; --warn:#ff8a80; --warn-bg:#3a1a18;
  --view-bg:#12161b; --code-bg:#1f242c;
  --fig-ink:#e7eaef; --fig-ref:#7d8693; --fig-steel:#8e98a6; --fig-foam:#46505c; --fig-housing:#2c3139;
  --fig-lens:#f6a300; --fig-lens-edge:#ffb52e; --fig-dim:#8db3ff; --fig-down:#4fc483; --fig-up:#ff7b72;
  --fig-bg:#161a20; --fig-inv:#e9ecf1;
  color-scheme:dark;
}
*{box-sizing:border-box}
.wrap>*,section>*,.split>*,.model>*,.two>*,.top>*,figure{min-width:0}
html{-webkit-text-size-adjust:100%}
body{background:var(--bg);color:var(--ink);font:400 16px/1.55 var(--body)}
a{color:var(--dim);text-underline-offset:2px}
a:focus-visible,button:focus-visible,input:focus-visible+span{outline:2px solid var(--dim);outline-offset:2px}
.wrap{max-width:1180px;margin:0 auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:24px 64px;display:grid;gap:44px}
h1,h2,h3{font-family:var(--display);font-weight:600;line-height:1.08;text-wrap:balance;margin:0}
h1{font-size:clamp(36px,5.4vw,58px);letter-spacing:.005em}
h2{font-size:clamp(26px,3vw,32px)}
h3{font-size:19px;letter-spacing:.01em}
p,ul,ol,dl,figure{margin:0}
code{font-family:var(--mono);font-size:.88em;background:var(--code-bg);padding:1px 5px;border-radius:2px;overflow-wrap:anywhere}
.eyebrow{font:600 12px/1.2 var(--body);letter-spacing:.14em;text-transform:uppercase;color:var(--ink-2)}
.muted{color:var(--ink-2)}

/* title block */
.top{display:grid;gap:14px}
.tb{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(0,1fr);border:1.5px solid var(--ink);background:var(--paper)}
.tb-main{padding:26px 28px 24px;display:grid;gap:14px;align-content:start;border-right:1.5px solid var(--ink)}
.lede{font-size:18.5px;line-height:1.5;max-width:56ch}
.tb-cells{display:grid;grid-template-columns:1fr 1fr;align-content:stretch}
.tb-cells div{padding:11px 14px;border-bottom:1px solid var(--rule);display:grid;gap:3px;align-content:start}
.tb-cells div:nth-child(even){border-left:1px solid var(--rule)}
.tb-cells div:nth-last-child(-n+2){border-bottom:0}
.tb-cells dt{font:600 11px/1.2 var(--body);letter-spacing:.13em;text-transform:uppercase;color:var(--ink-2)}
.tb-cells dd{margin:0;font:500 15px/1.35 var(--mono);font-variant-numeric:tabular-nums}
.status{display:grid;grid-template-columns:auto 1fr;gap:12px;align-items:start;padding:13px 16px;background:var(--warn-bg);border-left:4px solid var(--warn)}
.status b{color:var(--warn)}
.status .mark{font:600 13px/1.5 var(--mono);color:var(--warn)}
.toc{display:flex;flex-wrap:wrap;gap:6px 20px;font-size:15px}
@media (max-width:760px){.tb{grid-template-columns:1fr}.tb-main{border-right:0;border-bottom:1.5px solid var(--ink);padding:20px}}

/* sections */
section{display:grid;gap:18px;scroll-margin-top:16px}
.head{display:grid;gap:8px;max-width:72ch}
.head p{color:var(--ink-2)}
.split{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(0,1fr);gap:28px;align-items:start}
.narrow{max-width:920px}
@media (max-width:920px){.split{grid-template-columns:1fr}}

/* viewer */
.model{display:grid;grid-template-columns:minmax(0,1.65fr) minmax(0,1fr);gap:28px;align-items:start}
@media (max-width:920px){.model{grid-template-columns:1fr}}
.viewer-card{background:var(--paper);border:1px solid var(--rule);min-width:0}
.viewer{position:relative;width:100%;max-width:100%;aspect-ratio:4/3;background:var(--view-bg);overflow:hidden}
@media (max-width:560px){.viewer{aspect-ratio:1/1}}
.viewer canvas{position:absolute;inset:0;width:100%;height:100%;display:block;touch-action:none;cursor:grab}
.viewer canvas:active{cursor:grabbing}
.fallback{position:absolute;inset:0;display:grid;place-items:center;padding:14px}
.fallback svg{width:100%;height:100%}
.vhint{position:absolute;left:10px;bottom:8px;font:500 12px/1.3 var(--body);color:var(--ink-2);pointer-events:none}
.toolbar{display:flex;flex-wrap:wrap;gap:10px 18px;padding:12px;border-top:1px solid var(--rule);align-items:center}
.seg{display:inline-flex;flex-wrap:wrap;border:1px solid var(--rule)}
.seg button{border:0;border-right:1px solid var(--rule)}
.seg button:last-child{border-right:0}
button{font:500 14px/1 var(--body);color:var(--ink);background:var(--paper);border:1px solid var(--rule);padding:9px 12px;min-height:36px;cursor:pointer;border-radius:0}
button:hover{background:var(--rule-2)}
button[aria-pressed="true"]{background:var(--ink);color:var(--paper)}
.toggles{display:flex;flex-wrap:wrap;gap:8px 16px;font-size:14px}
.toggles label{display:inline-flex;gap:7px;align-items:center;cursor:pointer;min-height:28px}
.toggles input{accent-color:var(--dim);width:16px;height:16px;margin:0}
.actions{display:flex;gap:8px;margin-left:auto}
@media (max-width:560px){.actions{margin-left:0}}
.notes{display:grid;gap:16px;align-content:start;min-width:0}
.legend{list-style:none;padding:0;display:grid;gap:9px;font-size:15px}
.legend li{display:grid;grid-template-columns:18px 1fr;gap:10px;align-items:start}
.sw{width:18px;height:12px;margin-top:5px;border:1px solid var(--ink-2)}
.facts{display:grid;grid-template-columns:auto 1fr;gap:6px 14px;font-size:15px;border-top:1px solid var(--rule);padding-top:14px}
.facts dt{color:var(--ink-2)}
.facts dd{margin:0;font-family:var(--mono);font-variant-numeric:tabular-nums}

/* figures, tables, lists */
.figbox{background:var(--paper);border:1px solid var(--rule);padding:12px;overflow-x:auto}
.figbox svg{display:block;width:100%;height:auto;min-width:560px}
figcaption{font-size:14px;color:var(--ink-2);margin-top:8px}
.points{list-style:none;padding:0;display:grid;gap:16px}
.points li{display:grid;gap:3px;padding-left:14px;border-left:2px solid var(--rule)}
.points b{font-weight:600}
.tablebox{overflow-x:auto;background:var(--paper);border:1px solid var(--rule)}
table{border-collapse:collapse;width:100%;font-size:14.5px}
th,td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--rule-2);vertical-align:top}
th{font:600 11.5px/1.25 var(--body);letter-spacing:.1em;text-transform:uppercase;color:var(--ink-2);white-space:nowrap}
tr:last-child td{border-bottom:0}
td.num{font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}
.tag{font-family:var(--mono);font-weight:500;color:var(--dim);white-space:nowrap}
.pill{display:inline-block;font:600 11px/1 var(--body);letter-spacing:.08em;text-transform:uppercase;padding:4px 7px}
.pill.ok{color:var(--ok);background:var(--ok-bg)}
.pill.no{color:var(--warn);background:var(--warn-bg)}
.dn{color:var(--fig-down);font-weight:600}
.up{color:var(--fig-up);font-weight:600}
ol.steps{list-style:none;padding:0;counter-reset:s;display:grid;gap:12px;max-width:76ch}
ol.steps li{counter-increment:s;display:grid;grid-template-columns:2.1em 1fr;gap:6px}
ol.steps li::before{content:counter(s);font:600 15px/1.55 var(--mono);color:var(--dim)}
.files{display:grid;grid-template-columns:minmax(0,max-content) 1fr;gap:8px 18px;font-size:15px}
.files dt{font-family:var(--mono);font-size:14px;overflow-wrap:anywhere}
.files dd{margin:0;color:var(--ink-2)}
@media (max-width:620px){.files{grid-template-columns:1fr;gap:2px}.files dd{margin-bottom:10px}}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px;align-items:start}
.cmd{font-family:var(--mono);font-size:14px;background:var(--code-bg);padding:12px 14px;overflow-x:auto;white-space:pre;margin:0}
footer{border-top:1px solid var(--rule);padding-top:16px;font-size:14px;color:var(--ink-2);display:grid;gap:6px}
@media (prefers-reduced-motion: reduce){*{scroll-behavior:auto}}
</style>

<div class="wrap">
  <div class="top">
    <header class="tb">
      <div class="tb-main">
        <p class="eyebrow">Design review &middot; fit-check stage</p>
        <h1>390 Adventure Indicator Cap</h1>
        <p class="lede">A bent stainless sleeve that slides over a loose or broken indicator head, grips it through a foam liner and bolts to the screw boss beside the lamp socket. The original lamp keeps working, so you don't have to buy a new indicator.</p>
      </div>
      <dl class="tb-cells">
        <div><dt>Drawing</dt><dd>IC-390A-01</dd></div>
        <div><dt>Revision</dt><dd>A</dd></div>
        <div><dt>Material</dt><dd>@@MAT_SHORT@@</dd></div>
        <div><dt>Mass</dt><dd>@@MASS@@ g</dd></div>
        <div><dt>Flat blank</dt><dd>@@BLANK@@ mm</dd></div>
        <div><dt>Bends</dt><dd>@@NBENDS@@</dd></div>
        <div><dt>Fixing</dt><dd>1 &times; M@@SCREW@@, existing boss</dd></div>
        <div><dt>Left / right</dt><dd>@@HAND@@</dd></div>
      </dl>
    </header>
    <p class="status"><span class="mark">REV A</span><span><b>Lamp and mount sizes are scaled from product photos, not measured.</b> Take the ten measurements in <a href="#measure">Measure first</a> and make the card fit check in <a href="#make">Make it</a> before any metal is cut.</span></p>
    <nav class="toc" aria-label="On this page"><a href="#model">3D model</a><a href="#holds">How it holds</a><a href="#measure">Measure first</a><a href="#make">Make it</a><a href="#fit">Fit it</a><a href="#checks">Checks</a><a href="#files">Files</a><a href="#refs">References</a></nav>
  </div>

  <section id="model" aria-labelledby="h-model">
    <h2 id="h-model" class="eyebrow" style="font:600 12px/1.2 var(--body);letter-spacing:.14em">3D model</h2>
    <div class="model">
      <div class="viewer-card">
        <div class="viewer" id="viewer" role="img" aria-label="3D model of the cap fitted on the indicator lamp">
          <div class="fallback" id="fallback" hidden>@@FIG_ISO@@</div>
          <span class="vhint" id="vhint">Drag to turn &middot; scroll or pinch to zoom &middot; right-drag to pan</span>
        </div>
        <div class="toolbar" id="viewer-tools">
          <div class="seg" role="group" aria-label="View">
            <button type="button" data-view="iso" aria-pressed="true">Iso</button><button type="button" data-view="top" aria-pressed="false">Top</button><button type="button" data-view="lens" aria-pressed="false">Lens side</button><button type="button" data-view="tip" aria-pressed="false">Tip</button><button type="button" data-view="back" aria-pressed="false">Back</button>
          </div>
          <div class="toggles">
            <label><input type="checkbox" id="t-lamp" checked><span>Lamp</span></label>
            <label><input type="checkbox" id="t-liner" checked><span>Foam liner</span></label>
            <label><input type="checkbox" id="t-hw" checked><span>Screw</span></label>
            <label><input type="checkbox" id="t-cut"><span>Cut at tab</span></label>
            <label><input type="checkbox" id="t-black"><span>Black finish</span></label>
          </div>
          <div class="actions"><button type="button" id="b-slide">Slide on</button><button type="button" id="b-blink" aria-pressed="false">Blink</button></div>
        </div>
      </div>
      <aside class="notes">
        <h2>What you are looking at</h2>
        <p>The cap (steel) sits on the stock LED indicator head (black housing, clear lens). Its ear bolts to the screw boss beside the lamp socket, using the screw that is already there. <b>Slide on</b> shows how it fits; <b>Cut at tab</b> slices through a keeper tab so you can see the liner.</p>
        <ul class="legend">
          <li><span class="sw" style="background:#bcc3cc"></span><span>Cap, @@MAT_SHORT@@</span></li>
          <li><span class="sw" style="background:#4f5662"></span><span>EPDM foam liner, stuck inside the cap</span></li>
          <li><span class="sw" style="background:#1c1e22"></span><span>Stock indicator head (schematic)</span></li>
          <li><span class="sw" style="background:#dfe6ee"></span><span>Clear lens; its lit face stays uncovered (<b>Blink</b> lights it)</span></li>
          <li><span class="sw" style="background:#5d636c;opacity:.6"></span><span>Stalk, socket and screw boss on the bike (schematic)</span></li>
        </ul>
        <dl class="facts">
          <dt>Formed size</dt><dd>@@ENV@@ mm</dd>
          <dt>Inside height</dt><dd>@@HC@@ mm</dd>
          <dt>Back wall taper</dt><dd>@@TAPER@@&deg;, follows the lamp</dd>
          <dt>Ear slot</dt><dd>@@SLOT@@ mm, &plusmn;@@ADJ@@ adjust</dd>
          <dt>Aluminium option</dt><dd>@@ALU_MASS@@ g in 2.0 mm 5052</dd>
        </dl>
      </aside>
    </div>
  </section>

  <section id="holds" aria-labelledby="h-holds">
    <div class="head">
      <p class="eyebrow">How it holds</p>
      <h2 id="h-holds">Steel on the four faces that don't light up</h2>
      <p>The stock head sits on a flexible rubber stalk. When the stalk tears or its mount cracks, the head droops or hangs on its wires. The cap takes the stalk out of the load path: the head is held by the cap, and the cap by a screw.</p>
    </div>
    <div class="split">
      <figure><div class="figbox">@@FIG_SECTION@@</div><figcaption>Section through a keeper tab, @@CUT_X@@ mm from the root face of the head. Liner shown at its squeezed thickness.</figcaption></figure>
      <ul class="points">
        <li><b>Grips four faces, leaves the lens open.</b><span>Top, bottom, back and tip are steel. The lit face of the lens is never covered, so the indicator still shows across its full width.</span></li>
        <li><b>Foam does the gripping.</b><span>Self-adhesive EPDM: @@FOAM@@. It is squeezed by a fifth to a third, which takes up the lamp's size spread and vibration and keeps steel off the plastic.</span></li>
        <li><b>Tabs stop it sliding off.</b><span>Four keeper tabs hook @@HOOK@@ mm over the sloped strip above and below the lens. They touch only that strip, never the lit face.</span></li>
        <li><b>One screw takes the load.</b><span>The ear sits on the boss beside the socket and reuses its screw (M@@SCREW@@ assumed). The slot allows &plusmn;@@ADJ@@ mm to line it up.</span></li>
        <li><b>Same part on both sides.</b><span>The cap is symmetric top to bottom, so you turn it over for the other side. Front and rear use the same lamp, so the channel is identical; only the ear changes if the screws sit in different places.</span></li>
      </ul>
    </div>
  </section>

  <section id="measure" aria-labelledby="h-measure">
    <div class="head">
      <p class="eyebrow">Measure first</p>
      <h2 id="h-measure">Ten numbers decide the fit</h2>
      <p>The model runs on estimates scaled from photos. Measure each value on your bike with calipers, put it in <code>cad/params.py</code> and run <code>python3 build.py</code>. The part, the flat blank, the drawings and every check are rebuilt from them.</p>
    </div>
    <figure class="narrow"><div class="figbox">@@FIG_MEASURE@@</div></figure>
    <div class="tablebox"><table>
      <thead><tr><th>Ref</th><th>What</th><th>Model value</th><th>How to measure</th></tr></thead>
      <tbody>@@MEASURE_ROWS@@</tbody>
    </table></div>
    <p class="muted">M1 to M5 set the channel. M7 to M9 place the ear. If the front and rear screws give different M7 to M9, you need two versions; they share the same blank apart from the ear.</p>
  </section>

  <section id="make" aria-labelledby="h-make">
    <div class="head">
      <p class="eyebrow">Make it</p>
      <h2 id="h-make">Card first, then steel</h2>
      <p>A card copy costs nothing and shows a wrong measurement before the laser does.</p>
    </div>
    <ol class="steps">
      <li><span>Update <code>cad/params.py</code> with your measurements and run <code>python3 build.py</code>. Every check must pass.</span></li>
      <li><span>Print <code>out/template_1to1.pdf</code> at 100 %. Check the 100 mm bar with a ruler, glue it to 1 mm card, cut, fold and try it on the lamp.</span></li>
      <li><span>Send <code>out/cap_blank.dxf</code> to a laser cutter: layer CUT only, @@MAT_LONG@@, deburred.</span></li>
      <li><span>Bend B1 to B8 in order. B7 and B8 form a channel @@HC@@ mm inside: use a gooseneck punch, or bend over a @@HC@@ mm form block in a vice.</span></li>
      <li><span>Finish: bead blast and black textured powder coat to match the lamp body, or leave it brushed. The liner gaps absorb the coating.</span></li>
    </ol>
    <figure class="narrow"><div class="figbox">@@FIG_BLANK@@</div><figcaption>Flat blank, outside face up, @@BLANK@@ mm, @@CUTLEN@@ mm of cut, @@PIERCES@@ pierces. Bend lines are bend centre lines.</figcaption></figure>
    <div class="two">
      <div class="tablebox"><table>
        <thead><tr><th>Bend</th><th>Feature</th><th>Direction</th><th>Angle</th><th>Length</th><th>Allowance</th></tr></thead>
        <tbody>@@BEND_ROWS@@</tbody>
      </table></div>
      <div class="tablebox"><table>
        <thead><tr><th>Qty</th><th>Item</th></tr></thead>
        <tbody>
          <tr><td class="num">1</td><td>Cap, laser cut and bent, @@MAT_LONG@@ (or 2.0 mm aluminium 5052-H32, @@ALU_MASS@@ g)</td></tr>
          <tr><td class="num">1</td><td>EPDM closed-cell foam tape, self-adhesive, 1 mm, 2 strips (plates and tabs)</td></tr>
          <tr><td class="num">1</td><td>EPDM foam tape, 2 mm, 1 strip (back wall)</td></tr>
          <tr><td class="num">1</td><td>EPDM foam tape, 3 mm, 1 pad (tip wall)</td></tr>
          <tr><td class="num">1</td><td>Stainless button-head screw M@@SCREW@@, the original length plus @@PLUS@@ mm</td></tr>
          <tr><td class="num">1</td><td>Stainless washer M@@SCREW@@, 12 to 15 mm outside diameter</td></tr>
        </tbody>
      </table></div>
    </div>
    <p class="muted">Bend allowance = angle &times; (R + K &middot; t), with inside radius @@R@@ mm and K @@K@@. If your bend shop works to a different K-factor, change it in <code>params.py</code> and rebuild: the inside sizes stay the same and the blank adjusts.</p>
  </section>

  <section id="fit" aria-labelledby="h-fit">
    <div class="head">
      <p class="eyebrow">Fit it</p>
      <h2 id="h-fit">Ten minutes with a hex key</h2>
    </div>
    <ol class="steps">
      <li><span>If the head has torn off its stalk, repair the wiring first (solder and heat-shrink, or a new connector) and check that it flashes.</span></li>
      <li><span>Clean the inside of the cap and stick the foam strips to the cap, not to the lamp: 1 mm on the plates and tabs, 2 mm on the back wall, 3 mm on the tip wall.</span></li>
      <li><span>Hold the head in its normal position. Slide the cap over it from the tip until the ear meets the boss. The tabs drop over the sloped edge of the lens.</span></li>
      <li><span>Fit the screw and washer through the ear slot into the boss. Snug it, about 2 N&middot;m for a screw into plastic. Don't use threadlocker in plastic; it can crack the boss.</span></li>
      <li><span>Push the lamp tip in every direction: it should not move. Check from in front of and behind the bike that the whole lens lights.</span></li>
    </ol>
  </section>

  <section id="checks" aria-labelledby="h-checks">
    <div class="head">
      <p class="eyebrow">Checks</p>
      <h2 id="h-checks">What <code>build.py</code> proves on every rebuild</h2>
      <p>These run against the lamp model. They show the part is consistent with the numbers it was built from. Whether those numbers match your bike is what the measurements and the card check settle.</p>
    </div>
    <div class="tablebox"><table>
      <thead><tr><th>Check</th><th>Result</th><th>Needs</th><th></th></tr></thead>
      <tbody>@@CHECK_ROWS@@</tbody>
    </table></div>
  </section>

  <section id="files" aria-labelledby="h-files">
    <div class="head">
      <p class="eyebrow">Files</p>
      <h2 id="h-files">Everything is generated from one parameter file</h2>
      <p>In the repository under <a href="@@TREE@@" target="_blank" rel="noopener">hardware/ktm-indicator-cap</a>.</p>
    </div>
    <div class="two">
      <dl class="files">@@FILE_ROWS@@</dl>
      <div style="display:grid;gap:10px;min-width:0">
        <h3>Rebuild</h3>
        <pre class="cmd">pip install cadquery ezdxf shapely
cd hardware/ktm-indicator-cap/cad
python3 build.py          # part, blank, checks
python3 build.py --alu    # aluminium variant
python3 drawing.py        # drawings (SVG)
python3 figures.py        # figures
python3 page.py           # this page</pre>
        <p class="muted">PDFs: <code>node svg2pdf.js ../out/*.svg</code> (needs Playwright).</p>
      </div>
    </div>
  </section>

  <section id="refs" aria-labelledby="h-refs">
    <div class="head">
      <p class="eyebrow">References</p>
      <h2 id="h-refs">Where the idea comes from</h2>
      <p>Bikers Billet sell <a href="@@REF_FRONT@@" target="_blank" rel="noopener">front</a> and <a href="@@REF_REAR@@" target="_blank" rel="noopener">rear</a> brackets for the 2025 390 Adventure that do the same job: a folded steel cover over the lamp, held by one screw. A rider's <a href="@@REF_REEL@@" target="_blank" rel="noopener">install reel</a> shows the black rear version blending in with the lamp. This design keeps that idea and changes the details: a foam liner instead of steel on plastic, tabs that touch only the lens edge, a slotted ear with adjustment, and one symmetric part for both sides.</p>
    </div>
  </section>

  <footer>
    <p>Independent design. Not a KTM part; not affiliated with KTM or Bikers Billet.</p>
    <p>Drawing IC-390A-01 rev A. Generated from the model by <code>cad/page.py</code> on @@DATE@@.</p>
  </footer>
</div>

<script type="application/json" id="model-data">@@DATA@@</script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>
(function () {
  "use strict";
  var host = document.getElementById("viewer");
  var fallback = document.getElementById("fallback");
  var tools = document.getElementById("viewer-tools");
  function showFallback() {
    fallback.hidden = false;
    tools.hidden = true;
    document.getElementById("vhint").hidden = true;
  }
  if (!window.THREE || !THREE.OrbitControls) { showFallback(); return; }
  var renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true });
    if (!renderer.getContext()) throw new Error("no context");
  } catch (e) { showFallback(); return; }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.localClippingEnabled = true;
  host.insertBefore(renderer.domElement, host.firstChild);

  var DATA = JSON.parse(document.getElementById("model-data").textContent);
  var CUT_X = @@CUT_X@@;
  function b64(s, T) {
    var bin = atob(s), u8 = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
    return new T(u8.buffer);
  }

  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(28, 4 / 3, 1, 5000);
  camera.up.set(0, 0, 1);
  scene.add(new THREE.HemisphereLight(0xf2f5fa, 0x30343b, 0.9));
  var key = new THREE.DirectionalLight(0xffffff, 0.85); key.position.set(120, -160, 220); scene.add(key);
  var fill = new THREE.DirectionalLight(0xdfe7ff, 0.35); fill.position.set(-180, 120, 60); scene.add(fill);
  var rim = new THREE.DirectionalLight(0xffffff, 0.3); rim.position.set(-60, 200, -120); scene.add(rim);

  var clip = [];
  var cutPlane = new THREE.Plane(new THREE.Vector3(1, 0, 0), -CUT_X);
  var STEEL = 0xbcc3cc, BLACK = 0x2a2d33;
  var M = {
    steel: new THREE.MeshStandardMaterial({ color: STEEL, metalness: 0.45, roughness: 0.38 }),
    housing: new THREE.MeshStandardMaterial({ color: 0x1c1e22, metalness: 0.05, roughness: 0.6 }),
    lens: new THREE.MeshStandardMaterial({ color: 0xdfe6ee, emissive: 0x000000, metalness: 0.1, roughness: 0.15, transparent: true, opacity: 0.5 }),
    foam: new THREE.MeshStandardMaterial({ color: 0x4f5662, roughness: 1, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 }),
    context: new THREE.MeshStandardMaterial({ color: 0x5d636c, roughness: 0.85, transparent: true, opacity: 0.5, depthWrite: false, polygonOffset: true, polygonOffsetFactor: 2, polygonOffsetUnits: 2 }),
    screw: new THREE.MeshStandardMaterial({ color: 0xd3d7dd, metalness: 0.6, roughness: 0.3 })
  };
  var capEdge = new THREE.LineBasicMaterial({ color: 0x14181f, transparent: true, opacity: 0.6 });
  var ctxEdge = new THREE.LineBasicMaterial({ color: 0x9aa1ab, transparent: true, opacity: 0.55 });
  var mats = [M.steel, M.housing, M.lens, M.foam, M.context, M.screw, capEdge, ctxEdge];
  mats.forEach(function (m) { m.clippingPlanes = clip; if (m.isMeshStandardMaterial) m.side = THREE.DoubleSide; });

  function part(name, mat, emat) {
    var p = DATA.parts[name];
    var grp = new THREE.Group();
    if (!p) return grp;
    var g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(b64(p.pos, Float32Array), 3));
    g.setAttribute("normal", new THREE.BufferAttribute(b64(p.nrm, Float32Array), 3));
    g.setIndex(new THREE.BufferAttribute(b64(p.idx, Uint32Array), 1));
    grp.add(new THREE.Mesh(g, mat));
    if (emat) {
      var e = new THREE.BufferGeometry();
      e.setAttribute("position", new THREE.BufferAttribute(b64(p.edges, Float32Array), 3));
      grp.add(new THREE.LineSegments(e, emat));
    }
    return grp;
  }
  var capG = new THREE.Group(), linerG = new THREE.Group(), lampG = new THREE.Group(), bikeG = new THREE.Group(), hwG = new THREE.Group();
  capG.add(part("CAP", M.steel, capEdge));
  ["LINER_TOP", "LINER_BOTTOM", "LINER_BACK", "LINER_TIP"].forEach(function (n) { linerG.add(part(n, M.foam, null)); });
  capG.add(linerG);
  lampG.add(part("HOUSING", M.housing, ctxEdge));
  lampG.add(part("LENS", M.lens, ctxEdge));
  ["NECK", "SOCKET", "BOSS"].forEach(function (n) { bikeG.add(part(n, M.context, ctxEdge)); });
  hwG.add(part("WASHER", M.screw, capEdge));
  hwG.add(part("SCREW", M.screw, capEdge));
  [capG, lampG, bikeG, hwG].forEach(function (g) { scene.add(g); });

  var box = new THREE.Box3().setFromObject(capG).union(new THREE.Box3().setFromObject(lampG));
  var target = box.getCenter(new THREE.Vector3());
  var radius = box.getBoundingSphere(new THREE.Sphere()).radius;

  var controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.screenSpacePanning = true;
  controls.minDistance = radius * 0.8;
  controls.maxDistance = radius * 12;
  var queued = false;
  function render() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(function () { queued = false; renderer.render(scene, camera); });
  }
  controls.addEventListener("change", render);

  var VIEWS = { iso: [1, -1.35, 0.85], top: [0, -0.0001, 1], lens: [0, -1, 0.0001], tip: [1, 0, 0.0001], back: [-0.45, 1, 0.5], cut: [-1, -0.6, 0.45] };
  var current = "iso";
  function setView(name) {
    current = name;
    var d = new THREE.Vector3().fromArray(VIEWS[name]).normalize();
    var vf = THREE.MathUtils.degToRad(camera.fov);
    var hf = 2 * Math.atan(Math.tan(vf / 2) * camera.aspect);
    var dist = radius / Math.sin(Math.min(vf, hf) / 2) * (name === "cut" ? 0.72 : 0.86);
    camera.position.copy(target).addScaledVector(d, dist);
    controls.target.copy(target);
    controls.update();
    document.querySelectorAll("[data-view]").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.view === name)); });
    render();
  }
  document.querySelectorAll("[data-view]").forEach(function (b) { b.addEventListener("click", function () { setView(b.dataset.view); }); });

  function resize() {
    var w = host.clientWidth, h = host.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    render();
  }
  if (window.ResizeObserver) new ResizeObserver(resize).observe(host); else window.addEventListener("resize", resize);

  function applyTheme() {
    var bg = getComputedStyle(document.documentElement).getPropertyValue("--view-bg").trim() || "#f6f7f9";
    try { renderer.setClearColor(new THREE.Color(bg), 1); } catch (e) { renderer.setClearColor(0xf6f7f9, 1); }
    render();
  }
  try { matchMedia("(prefers-color-scheme: dark)").addEventListener("change", applyTheme); } catch (e) {}
  new MutationObserver(applyTheme).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

  function $(id) { return document.getElementById(id); }
  $("t-lamp").addEventListener("change", function (e) { lampG.visible = e.target.checked; render(); });
  $("t-liner").addEventListener("change", function (e) { linerG.visible = e.target.checked; render(); });
  $("t-hw").addEventListener("change", function (e) { hwG.visible = e.target.checked; render(); });
  $("t-black").addEventListener("change", function (e) {
    var on = e.target.checked;
    M.steel.color.setHex(on ? BLACK : STEEL);
    M.steel.metalness = on ? 0.1 : 0.45;
    M.steel.roughness = on ? 0.8 : 0.38;
    capEdge.color.setHex(on ? 0x8a919c : 0x14181f);
    render();
  });
  $("t-cut").addEventListener("change", function (e) {
    clip.length = 0;
    if (e.target.checked) clip.push(cutPlane);
    mats.forEach(function (m) { m.needsUpdate = true; });
    if (e.target.checked) setView("cut"); else render();
  });

  var reduce = matchMedia("(prefers-reduced-motion: reduce)");
  var anim = null;
  function slideOn() {
    if (anim) cancelAnimationFrame(anim);
    var T = reduce.matches ? 0 : 2400, t0 = performance.now();
    var showHw = $("t-hw").checked;
    function ease(k) { return 1 - Math.pow(1 - k, 3); }
    function step(now) {
      var k = T ? Math.min(1, (now - t0) / T) : 1;
      var kc = Math.min(1, k / 0.7), ks = Math.max(0, Math.min(1, (k - 0.75) / 0.25));
      capG.position.x = 95 * (1 - ease(kc));
      hwG.visible = showHw && k >= 0.75;
      hwG.position.x = 14 * (1 - ease(ks));
      renderer.render(scene, camera);
      anim = k < 1 ? requestAnimationFrame(step) : null;
    }
    anim = requestAnimationFrame(step);
  }
  $("b-slide").addEventListener("click", slideOn);

  var blinkTimer = null;
  function setBlink(on) {
    $("b-blink").setAttribute("aria-pressed", String(on));
    clearInterval(blinkTimer);
    blinkTimer = null;
    M.lens.emissive.setHex(0x000000);
    M.lens.color.setHex(0xdfe6ee);
    M.lens.opacity = 0.5;
    render();
    if (!on) return;
    var lit = false, n = 0;
    blinkTimer = setInterval(function () {          /* 90 flashes a minute, stops by itself after 12 s */
      lit = !lit;
      M.lens.emissive.setHex(lit ? 0xff9a00 : 0x000000);
      M.lens.color.setHex(lit ? 0xffb020 : 0xdfe6ee);
      M.lens.opacity = lit ? 0.92 : 0.5;
      render();
      if (++n >= 36) setBlink(false);
    }, 333);
  }
  $("b-blink").addEventListener("click", function () { setBlink($("b-blink").getAttribute("aria-pressed") !== "true"); });

  applyTheme();
  resize();
  setView("iso");
})();
</script>
"""


def esc(s):
    return html.escape(str(s), quote=True)


def build_page(out_path: Path):
    sm = json.loads((OUT / "summary.json").read_text())
    alu = json.loads((OUT / "alu" / "summary.json").read_text())
    viewer = json.loads((OUT / "viewer_data.json").read_text())
    viewer["parts"] = {k: v for k, v in viewer["parts"].items() if k in VIEWER_PARTS}
    figs = {n: (DOCS / f"{n}.svg").read_text() for n in ("fig_section", "fig_measure", "fig_blank", "fig_iso")}

    P = sm["params"]
    lamp, mount, cap = P["lamp"], P["mount"], P["cap"]
    D = sm["derived"]
    env = sm["formed_envelope"]["size"]
    hook = next((r["value"] for r in sm["checks"] if r["check"].startswith("Tab hook depth")), "2 mm").split()[0]

    measure = [
        ("M1", "Head length", f"{lamp['L']:.0f}", "From the root face of the head (where the stalk enters) to the tip, along the black housing."),
        ("M2", "Head height", f"{lamp['H']:.0f}", "Top face to bottom face of the head."),
        ("M3", "Housing depth at the root", f"{lamp['D_root']:.0f}", "From the line where the lens meets the black housing to the back face, at the root end."),
        ("M4", "Housing depth at the tip", f"{lamp['D_tip']:.0f}", "The same, at the tip."),
        ("M5", "Lens edge chamfer", f"{lamp['lens_run']:.1f} &times; {lamp['lens_drop']:.1f}",
         "The sloped strip above the lit face: how far it runs back (a) and how far it drops (b)."),
        ("M6", "Stalk length", f"{lamp['neck_len']:.0f}", "Root face of the head to the face of the socket. Used for clearance only."),
        ("M7", "Boss face position", f"{mount['G_ear']:.0f}", "Along the lamp, from the head's root face back to the face the ear will sit on."),
        ("M8", "Screw distance behind the lamp", f"{mount['screw_behind_back']:.0f}", "From the back face of the head (at the root) to the screw centre, square to the lamp."),
        ("M9", "Screw height", f"{mount['screw_dz']:+.0f}", "Screw centre above (+) or below (&minus;) the mid-height of the head."),
        ("M10", "Screw", f"M{mount['screw_d']:.0f}", "Thread size and length of the screw already in that boss."),
    ]
    measure_rows = "".join(
        f'<tr><td class="tag">{r}</td><td>{w}</td><td class="num">{v}</td><td>{h}</td></tr>' for r, w, v, h in measure)

    bend_rows = "".join(
        f'<tr><td class="tag">{b["id"]}</td><td>{esc(b["feature"].replace("_", " ").title())}</td>'
        f'<td><span class="{"dn" if b["direction"] == "DOWN" else "up"}">{"Away" if b["direction"] == "DOWN" else "Towards"}</span></td>'
        f'<td class="num">{b["angle"]:.1f}&deg;</td><td class="num">{b["length"]:.1f}</td><td class="num">{b["allowance"]:.2f}</td></tr>'
        for b in sm["bends"])

    check_rows = "".join(
        f'<tr><td>{esc(r["check"])}</td><td class="num">{esc(r["value"])}</td><td class="num">{esc(r["requirement"])}</td>'
        f'<td><span class="pill {"ok" if r["ok"] else "no"}">{"pass" if r["ok"] else "fail"}</span></td></tr>'
        for r in sm["checks"])

    files = [
        ("cad/params.py", "Every dimension and design choice. Edit this."),
        ("cad/build.py", "Rebuilds the part, runs the checks, writes the files below."),
        ("out/cap_blank.dxf", "Laser profile (layer CUT) with bend lines and notes."),
        ("out/cap_formed.step", "Formed part for the bend shop or your CAD."),
        ("out/cap_blank.step", "Flat blank as a solid."),
        ("out/cap_formed.stl", "Print it as a fit gauge. Too thin to use printed."),
        ("out/drawing_formed.pdf", "A3 drawing of the formed part."),
        ("out/drawing_blank.pdf", "A3 drawing of the blank with the bend table."),
        ("out/template_1to1.pdf", "A4 card template at 1:1 for the fit check."),
        ("out/alu/", "The same set for 2.0 mm aluminium 5052-H32."),
        ("out/assembly_reference.step", "Cap, schematic lamp and screw together."),
    ]
    file_rows = "".join(
        f'<dt><a href="{(TREE if p.endswith("/") else REPO) + p}" target="_blank" rel="noopener">{p}</a></dt><dd>{w}</dd>'
        for p, w in files)

    gz, gb, gt = cap["gap_z"], cap["gap_back"], cap["gap_tip"]
    plus = 3 if cap["t"] <= 1.5 else 4
    rep = {
        "MAT_SHORT": f"SS304, {cap['t']:.1f} mm",
        "MAT_LONG": f"{cap['t']:.1f} mm stainless 304",
        "MASS": f"{sm['mass_g']:.1f}",
        "BLANK": f"{sm['blank']['width']:.1f} &times; {sm['blank']['height']:.1f}",
        "NBENDS": str(len(sm["bends"])),
        "SCREW": f"{mount['screw_d']:.0f}",
        "HAND": "same part" if abs(mount["screw_dz"]) < 1e-9 else "mirror pair",
        "ENV": " &times; ".join(f"{v:.1f}" for v in env),
        "HC": f"{D['cavity_height']:.1f}",
        "TAPER": f"{D['taper_deg']:.1f}",
        "SLOT": f"{cap['ear_slot_w']:.1f} &times; {cap['ear_slot_len']:.1f}",
        "ADJ": f"{(cap['ear_slot_len'] - cap['ear_slot_w']) / 2:.0f}",
        "ALU_MASS": f"{alu['mass_g']:.0f}",
        "CUT_X": f"{cap['tab_x'][0]:.0f}",
        "FOAM": f"1 mm on the plates (squeezed to {gz:.1f}), 2 mm on the back wall ({gb:.1f}), 3 mm at the tip ({gt:.1f})",
        "HOOK": hook,
        "CUTLEN": f"{sm['blank']['cut_length']:.0f}",
        "PIERCES": str(sm["blank"]["pierces"]),
        "R": f"{cap['r']:.1f}",
        "K": f"{cap['k']:.2f}",
        "PLUS": str(plus),
        "MEASURE_ROWS": measure_rows,
        "BEND_ROWS": bend_rows,
        "CHECK_ROWS": check_rows,
        "FILE_ROWS": file_rows,
        "TREE": TREE,
        "REF_FRONT": REFS["front"],
        "REF_REAR": REFS["rear"],
        "REF_REEL": REFS["reel"],
        "DATE": datetime.date.today().isoformat(),
        "FIG_SECTION": figs["fig_section"],
        "FIG_MEASURE": figs["fig_measure"],
        "FIG_BLANK": figs["fig_blank"],
        "FIG_ISO": figs["fig_iso"],
        "DATA": json.dumps(viewer, separators=(",", ":")),
    }
    page = TEMPLATE
    for k, v in rep.items():
        page = page.replace(f"@@{k}@@", v)
    left = [ln for ln in page.splitlines() if "@@" in ln]
    assert not left, f"unfilled markers: {left[:3]}"
    assert "</script" not in rep["DATA"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page)
    return out_path


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DOCS / "design-review.html"
    p = build_page(target)
    print(f"wrote {p} ({p.stat().st_size / 1024:.0f} KB)")
