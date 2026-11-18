"""Fill the spec sheet template with the part geometry and the CFD results, then export PDF + PNG.
Run from spoiler/:  python3 spec/src/build_spec.py"""
import json, datetime, subprocess, os
from PIL import Image
G = json.load(open('aero/out/spoiler_geometry.json')) if os.path.exists('aero/out/spoiler_geometry.json') else json.load(open('spec/spoiler_geometry.json'))
A = json.load(open('aero/results/aero_results.json'))
n, w = A['no_spoiler'], A['with_spoiler']
def row(label, a, b, fmt, unit='', better_low=True):
    d = b - a
    m = lambda x: fmt.format(x).replace('-', '−')
    return f'<tr><td>{label}</td><td>{m(a)}{unit}</td><td>{m(b)}{unit}</td><td class="d">{"+" if d >= 0 else "−"}{fmt.format(abs(d))}{unit}</td></tr>'
rows = [row('DRAG COEFF. Cd', n['Cd'], w['Cd'], '{:.3f}'),
        row('DRAG', n['drag_N'], w['drag_N'], '{:.0f}', ' N'),
        row('LIFT, REAR AXLE', n['lift_rear_N'], w['lift_rear_N'], '{:.0f}', ' N'),
        row('LIFT, FRONT AXLE', n['lift_front_N'], w['lift_front_N'], '{:.0f}', ' N')]
r130 = A['at_130']; d130 = r130['with_spoiler']['lift_rear_N'] - r130['no_spoiler']['lift_rear_N']
dd130 = r130['with_spoiler']['drag_N'] - r130['no_spoiler']['drag_N']
note = (f"At 130 km/h: rear-axle lift {'+' if d130 >= 0 else '−'}{abs(d130):.0f} N, drag {'+' if dd130 >= 0 else '−'}{abs(dd130):.0f} N. Lift: positive = up, negative = downforce. "
        f"OpenFOAM steady RANS (k-ω SST), half car, moving ground, rotating wheels, {A['cells']['with_spoiler'] / 1e6:.2f} M cells. "
        "Modelled Polo-class body with a smooth underbody: use the changes, not the absolute values.")
html = open('spec/spec_sheet.tpl.html').read()
for k, v in dict(W=f"{G['W']:.0f}", D=f"{G['D']:.0f}", H=f"{G['H']:.0f}", CHORD='267', TMAX=f"{G['max_thickness_mm']:.1f}", LIP=f"{G['lip_slope_deg']:.0f}",
                 PLAN=f"{G['plan_area_m2']:.2f}", SPEED='100', AERO_ROWS='\n        '.join(rows), AERO_NOTE=note,
                 DATE=datetime.date.today().strftime('%b %Y').upper()).items():
    html = html.replace('{{' + k + '}}', v)
assert '{{' not in html, html[html.index('{{') - 40: html.index('{{') + 40]
open('spec/spec_sheet.html', 'w').write(html)
# hero image for the 210 x 72 mm box, cropped from the brochure hero render
im = Image.open('v6/car/renders/hero_blue.jpg' if os.path.exists('v6/car/renders/hero_blue.jpg') else 'v6/car/renders/hero_blue.png').convert('RGB')
W, H = im.size; h = int(W * 84 / 210); y0 = int(min(max(0.535 * H - h / 2, 0), H - h))
im.crop((0, y0, W, y0 + h)).save('spec/img/hero.jpg', quality=90, optimize=True)
subprocess.run('NODE_PATH=$(npm root -g) node spec/src/export.js', shell=True, check=True)
