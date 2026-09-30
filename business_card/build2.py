import pymupdf, random
from helpers import qr_path, bars
import math
W, H = 95, 57
PDF = "/root/.claude/uploads/f98fce44-f9e3-595b-8e05-8e3c5a668cf3/93fe2289-Cardfront.pdf"
pg = pymupdf.open(PDF)[0]
dr = pg.get_drawings()

def dpath(x):
    d = ""; last = None
    def mv(p):
        nonlocal d, last
        if last is None or abs(last[0]-p.x) > .01 or abs(last[1]-p.y) > .01:
            if d and last is not None: pass
            d += f"M{p.x:.2f} {p.y:.2f}"
    for it in x["items"]:
        t = it[0]
        if t == "l":
            mv(it[1]); d += f"L{it[2].x:.2f} {it[2].y:.2f}"; last = (it[2].x, it[2].y)
        elif t == "c":
            mv(it[1]); d += f"C{it[2].x:.2f} {it[2].y:.2f} {it[3].x:.2f} {it[3].y:.2f} {it[4].x:.2f} {it[4].y:.2f}"; last = (it[4].x, it[4].y)
        elif t == "re":
            r = it[1]; d += f"M{r.x0:.2f} {r.y0:.2f}H{r.x1:.2f}V{r.y1:.2f}H{r.x0:.2f}z"; last = None
        elif t == "qu":
            q = it[1]; d += f"M{q.ul.x:.2f} {q.ul.y:.2f}L{q.ur.x:.2f} {q.ur.y:.2f}L{q.lr.x:.2f} {q.lr.y:.2f}L{q.ll.x:.2f} {q.ll.y:.2f}z"; last = None
    if x.get("closePath"): d += "z"
    return d

# PDF -> page mm (design fills page height; centred)
S = 57 / 600.0
CX, CY = 527.25, 301.28
T = f"translate({W/2} {H/2}) scale({S}) translate({-CX} {-CY})"
lines = "".join(f'<path d="{dpath(x)}" stroke-width="{x.get("width") or 1}" fill="none"/>' for x in dr[25:67])
logo = "".join(f'<path d="{dpath(x)}" fill-rule="{"evenodd" if x.get("even_odd") else "nonzero"}"/>' for x in dr[1:5])
word = "".join(f'<path d="{dpath(x)}"/>' for x in dr[5:25])
# logo 262..795 x 192..366 ; wordmark 273..782 x 393..410
def place(inner, bx0, by0, k, tx, ty):   # put pdf point (bx0,by0) at mm (tx,ty), scale k mm/pt
    return f'<g transform="translate({tx} {ty}) scale({k}) translate({-bx0} {-by0})">{inner}</g>'
K = 36 / 533.0
logo_g = place(logo, 262, 192, K, 10, 9.6)
word_g = place(word, 273, 393, 34.4/509.0, 10.8, 23.6)

# hexagon QR panel (flat-top, points left/right)
def hexpts(cx, cy, R):
    return " ".join(f"{cx+R*math.cos(math.radians(a)):.3f},{cy+R*math.sin(math.radians(a)):.3f}" for a in range(0, 360, 60))
hcx, hcy = 70.5, 28.5
qa = qr_path("https://instagram.com/c6_customization", hcx-10, hcy-13, 20)

front = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}mm" height="{H}mm">
<defs>
 <linearGradient id="scrim" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#000" stop-opacity=".78"/><stop offset=".72" stop-color="#000" stop-opacity=".6"/><stop offset="1" stop-color="#000" stop-opacity="0"/></linearGradient>
</defs>
<image href="assets/carbon.jpg" x="{W/2-(4200/2400*H)/2:.3f}" y="0" width="{4200/2400*H:.3f}" height="{H}" preserveAspectRatio="none"/>
<g transform="{T}" stroke="#fff" stroke-linecap="butt" opacity=".9">{lines}</g>
<rect x="0" y="0" width="52" height="{H}" fill="url(#scrim)"/>
<g fill="#fff">{logo_g}{word_g}</g>
<path d="M10 27.6H44" stroke="#777" stroke-width=".15"/>
<text x="10" y="33.2" font-family="Michroma" font-size="2.45" fill="#fff" letter-spacing=".1">RAKSHITH RAJU C</text>
<text x="10" y="36.4" font-family="JetBrains Mono" font-size="1.45" fill="#9a9a9a" letter-spacing=".22">FOUNDER &amp; CEO</text>
<text x="10" y="41.4" font-family="Space Grotesk" font-weight="500" font-size="2.5" fill="#f0f0f0" letter-spacing=".25">+91 99006 11996</text>
<text x="10" y="45.0" font-family="Space Grotesk" font-size="2.0" fill="#b5b5b5" letter-spacing=".04">carbon6customization@gmail.com</text>
<polygon points="{hexpts(hcx,hcy,19.2)}" fill="#fff"/>
<polygon points="{hexpts(hcx,hcy,17.9)}" fill="none" stroke="#111" stroke-width=".2" stroke-dasharray="14 3 6 3"/>
<path d="{qa}" fill="#000"/>
<text x="{hcx}" y="{hcy+12.4}" text-anchor="middle" font-family="JetBrains Mono" font-weight="600" font-size="1.65" fill="#000" letter-spacing=".03">@c6_customization</text>
</svg>'''

# ---------- BACK ----------
bx, by, bd = 10, 11.5, 34
qb = qr_path("https://instagram.com/pi.xl3dprinting", 50, 15.5, 17)
bc, nbits = bars("YELACHENAHALLI", 50.2, 43.2, 35.6, 4.2)
back = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}mm" height="{H}mm">
<defs>
 <radialGradient id="bgl" cx=".3" cy=".5" r=".9"><stop offset="0" stop-color="#fafafa"/><stop offset="1" stop-color="#dcdcdc"/></radialGradient>
 <filter id="sh" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy=".6" stdDeviation=".9" flood-color="#000" flood-opacity=".35"/></filter>
</defs>
<rect width="{W}" height="{H}" fill="url(#bgl)"/>
<g transform="{T}" stroke="#222" stroke-linecap="butt" opacity=".22">{lines}</g>
<circle cx="{bx+bd/2}" cy="{by+bd/2}" r="{bd/2+1.3}" fill="#fff" filter="url(#sh)"/>
<circle cx="{bx+bd/2}" cy="{by+bd/2}" r="{bd/2+1.3}" fill="none" stroke="#111" stroke-width=".18"/>
<image href="assets/badge_grey.png" x="{bx}" y="{by}" width="{bd}" height="{bd}"/>
<text x="50" y="12.6" font-family="JetBrains Mono" font-size="1.5" fill="#666" letter-spacing=".2">02 / 3D PRINTING</text>
<rect x="49" y="14.5" width="19" height="19" fill="#fff" stroke="#111" stroke-width=".2"/>
<path d="{qb}" fill="#000"/>
<text x="70.4" y="19.2" font-family="JetBrains Mono" font-size="1.2" fill="#777" letter-spacing=".25">SCAN</text>
<text x="70.4" y="22.0" font-family="JetBrains Mono" font-weight="600" font-size="1.3" fill="#111">@pi.xl3dprinting</text>
<text x="50" y="37.0" font-family="Space Grotesk" font-weight="500" font-size="2.45" fill="#111" letter-spacing=".22">+91 99006 11996</text>
<text x="50" y="40.4" font-family="Space Grotesk" font-size="2.0" fill="#444" letter-spacing=".04">pixldprinting@gmail.com</text>
<rect x="49" y="42.4" width="38" height="6.4" fill="#fff" stroke="#111" stroke-width=".15"/>
<path d="{bc}" fill="#000"/>
<text x="49.2" y="50.8" font-family="JetBrains Mono" font-size="1.2" fill="#333" letter-spacing=".06">NR YELACHENAHALLI METRO · OPP PILLAR NO.114</text>
</svg>'''

css = '''
@font-face{font-family:Michroma;src:url(fonts/michroma.ttf)}
@font-face{font-family:"Space Grotesk";src:url(fonts/spacegrotesk.ttf);font-weight:300 700}
@font-face{font-family:"JetBrains Mono";src:url(fonts/jbmono.ttf);font-weight:100 800}
@page{size:95mm 57mm;margin:0}
html,body{margin:0;padding:0}
.p{width:95mm;height:57mm;overflow:hidden;page-break-after:always;break-after:page}
.p svg{display:block}
'''
open("card_v2.html", "w").write(f"<!doctype html><meta charset=utf-8><style>{css}</style><div class=p>{front}</div><div class=p>{back}</div>")
print("barcode bits", nbits)
