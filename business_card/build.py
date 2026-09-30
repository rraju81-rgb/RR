import random, barcode, qrcode
W, H = 95, 57            # 89x51 trim + 3mm bleed each side

def qr_path(url, x, y, size):
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0)
    q.add_data(url); q.make(fit=True)
    m = q.get_matrix(); n = len(m); c = size / n
    d = "".join(f"M{x+j*c:.3f} {y+i*c:.3f}h{c:.3f}v{c:.3f}h-{c:.3f}z"
                for i, r in enumerate(m) for j, v in enumerate(r) if v)
    return d

def bars(text, x, y, w, h):
    bits = barcode.Code128(text).build()[0]
    c = w / len(bits); out = []; i = 0
    while i < len(bits):
        if bits[i] == "1":
            j = i
            while j < len(bits) and bits[j] == "1": j += 1
            out.append(f"M{x+i*c:.3f} {y}h{(j-i)*c:.3f}v{h}h-{(j-i)*c:.3f}z"); i = j
        else: i += 1
    return "".join(out), len(bits)

def brackets(x1, y1, x2, y2, l, col, sw=.22):
    return (f'<g stroke="{col}" stroke-width="{sw}" fill="none" stroke-linecap="square">'
            f'<path d="M{x1} {y1+l}V{y1}H{x1+l}"/><path d="M{x2-l} {y1}H{x2}V{y1+l}"/>'
            f'<path d="M{x1} {y2-l}V{y2}H{x1+l}"/><path d="M{x2-l} {y2}H{x2}V{y2-l}"/></g>')

# ---------- FRONT : CARBON FIBRE (black) ----------
cell = .55
weave = ""
for i in range(4):
    for j in range(4):
        warp = (i + j) % 4 < 2
        weave += (f'<rect x="{j*cell}" y="{i*cell}" width="{cell}" height="{cell}" fill="url(#{"gw" if warp else "gf"})"/>')
qa = qr_path("https://instagram.com/c6_customization", 64, 10.5, 21)
front = f'''
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}mm" height="{H}mm">
<defs>
 <linearGradient id="gw" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#050505"/><stop offset=".5" stop-color="#2b2b2b"/><stop offset="1" stop-color="#050505"/></linearGradient>
 <linearGradient id="gf" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#0a0a0a"/><stop offset=".5" stop-color="#1c1c1c"/><stop offset="1" stop-color="#0a0a0a"/></linearGradient>
 <pattern id="cf" width="{cell*4}" height="{cell*4}" patternUnits="userSpaceOnUse">{weave}</pattern>
 <linearGradient id="sheen" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".42" stop-color="#fff" stop-opacity=".0"/><stop offset=".52" stop-color="#fff" stop-opacity=".13"/><stop offset=".62" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
 <linearGradient id="vig" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#000" stop-opacity=".0"/><stop offset="1" stop-color="#000" stop-opacity=".55"/></linearGradient>
</defs>
<rect width="{W}" height="{H}" fill="#050505"/>
<rect width="{W}" height="{H}" fill="url(#cf)"/>
<rect width="{W}" height="{H}" fill="url(#sheen)"/>
<rect width="{W}" height="{H}" fill="url(#vig)"/>
{brackets(7,7,88,50,3,"#d9d9d9")}
<g font-family="JetBrains Mono" fill="#8c8c8c" font-size="1.6" letter-spacing=".18">
 <text x="10" y="12.6">01 / CARBON FIBRE</text>
</g>
<text x="9.6" y="25.2" font-family="Michroma" font-size="13" fill="#fff" letter-spacing="-.2">C6</text>
<text x="10" y="29.6" font-family="Michroma" font-size="2.35" fill="#bdbdbd" letter-spacing=".62">CUSTOMIZATION</text>
<text x="10" y="33.2" font-family="JetBrains Mono" font-size="1.55" fill="#7d7d7d" letter-spacing=".2">CUSTOM CARBON FIBRE FABRICATION</text>
<path d="M10 35.6H55" stroke="#5a5a5a" stroke-width=".18"/>
<text x="10" y="40.4" font-family="Michroma" font-size="3.0" fill="#fff" letter-spacing=".12">RAKSHITH RAJU C</text>
<text x="10" y="44.2" font-family="Space Grotesk" font-weight="500" font-size="2.5" fill="#e6e6e6" letter-spacing=".25">+91 99006 11996</text>
<text x="10" y="47.7" font-family="Space Grotesk" font-size="2.2" fill="#a8a8a8" letter-spacing=".05">carbon6customization@gmail.com</text>
<!-- QR tile -->
<rect x="62.2" y="8.7" width="24.6" height="24.6" fill="#fff"/>
<path d="{qa}" fill="#000"/>
<text x="64" y="36.6" font-family="JetBrains Mono" font-weight="500" font-size="1.75" fill="#fff" letter-spacing=".05">@c6_customization</text>
<text x="64" y="39.4" font-family="JetBrains Mono" font-size="1.45" fill="#7d7d7d" letter-spacing=".22">SCAN  ▸  INSTAGRAM</text>
<g fill="#fff"><rect x="64" y="44.2" width="1.3" height="1.3"/><rect x="66.1" y="44.2" width="1.3" height="1.3" opacity=".5"/><rect x="68.2" y="44.2" width="1.3" height="1.3" opacity=".25"/></g>
</svg>'''

# ---------- BACK : 3D PRINTING (white) ----------
qb = qr_path("https://instagram.com/pi.xl3dprinting", 10, 10.5, 21)
bc, nbits = bars("YELACHENAHALLI PLR 114", 12.5, 38.6, 70, 6.6)
random.seed(7)
px = ""
cs = 1.5
for ci in range(0, 26):
    for ri in range(0, 7):
        x = W - ci * cs - cs; y = ri * cs
        p = (1 - ci/26) * (1 - ri/7) ** .7
        if random.random() < p * 1.05 and ci < 24:
            g = random.choice(["#111","#3a3a3a","#6b6b6b","#9a9a9a","#c4c4c4"])
            px += f'<rect x="{x:.2f}" y="{y:.2f}" width="{cs-.22}" height="{cs-.22}" fill="{g}" opacity="{.35+.65*random.random():.2f}"/>'
lines = "".join(f'<rect x="0" y="{y*.3:.2f}" width="{W}" height=".09"/>' for y in range(0, int(H/.3)))
back = f'''
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}mm" height="{H}mm">
<defs>
 <linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity="1"/></linearGradient>
 <mask id="m"><rect width="{W}" height="{H}" fill="url(#fade)"/></mask>
</defs>
<rect width="{W}" height="{H}" fill="#f4f4f4"/>
<g fill="#9a9a9a" opacity=".32" mask="url(#m)">{lines}</g>
{px}
{brackets(7,7,88,50,3,"#1a1a1a")}
<!-- QR tile -->
<rect x="8.2" y="8.7" width="24.6" height="24.6" fill="#fff" stroke="#111" stroke-width=".22"/>
<path d="{qb}" fill="#000"/>
<text x="10" y="36.6" font-family="JetBrains Mono" font-weight="500" font-size="1.75" fill="#111" letter-spacing=".05">@pi.xl3dprinting</text>
<text x="10" y="39.4" font-family="JetBrains Mono" font-size="1.45" fill="#7d7d7d" letter-spacing=".22" opacity="0">.</text>
<text x="85" y="12.6" text-anchor="end" font-family="JetBrains Mono" font-size="1.6" fill="#777" letter-spacing=".18">02 / 3D PRINTING</text>
<text x="85.6" y="22.6" text-anchor="end" font-family="Michroma" font-size="8.6" fill="#0c0c0c" letter-spacing="-.2">PI<tspan fill="#8a8a8a">.</tspan>XL</text>
<text x="85" y="27" text-anchor="end" font-family="Michroma" font-size="2.35" fill="#444" letter-spacing=".62">3D PRINTING</text>
<text x="85" y="31.6" text-anchor="end" font-family="Space Grotesk" font-weight="500" font-size="2.5" fill="#111" letter-spacing=".25">+91 99006 11996</text>
<text x="85" y="35.1" text-anchor="end" font-family="Space Grotesk" font-size="2.2" fill="#555" letter-spacing=".05">pixldprinting@gmail.com</text>
<!-- address barcode -->
<rect x="10" y="37.2" width="75" height="9.2" fill="#fff"/>
<path d="{bc}" fill="#000"/>
<text x="10" y="49" font-family="JetBrains Mono" font-size="1.5" fill="#333" letter-spacing=".12">NEAR YELACHENAHALLI METRO STN · OPP PILLAR NO. 114</text>
<text x="85" y="49" text-anchor="end" font-family="JetBrains Mono" font-size="1.5" fill="#888" letter-spacing=".12">▸ ADDRESS</text>
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
open("card.html", "w").write(f"<!doctype html><meta charset=utf-8><style>{css}</style>"
    f"<div class=p>{front}</div><div class=p>{back}</div>")
print("bits", nbits)
