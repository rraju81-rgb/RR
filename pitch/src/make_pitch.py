import json
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont('DV', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))       # has the ₹ glyph
pdfmetrics.registerFont(TTFont('DVB', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
I = '/home/user/RR/pitch/'; RP = '/home/user/RR/report/'
pr = json.load(open('pricing.json')); A = pr['assumptions']
ub = json.load(open('/home/user/RR/3d-models/table_universal_base_report.json'))
ft = json.load(open('/home/user/RR/3d-models/table_feet_report.json'))
INK, ACC, MUTED = colors.HexColor('#1d2433'), colors.HexColor('#e8841e'), colors.HexColor('#5a6070')
ss = getSampleStyleSheet()
H1 = ParagraphStyle('H1', fontName='DVB', fontSize=21, leading=25, textColor=INK, spaceAfter=3)
H2 = ParagraphStyle('H2', fontName='DVB', fontSize=12.5, leading=16, textColor=INK, spaceBefore=5, spaceAfter=3)
B = ParagraphStyle('B', fontName='DV', fontSize=9.2, leading=12.8, textColor=INK, spaceAfter=3)
SUB = ParagraphStyle('SUB', parent=B, fontSize=11.5, leading=15, textColor=MUTED)
TAG = ParagraphStyle('TAG', parent=B, fontName='DVB', fontSize=9.5, textColor=ACC)
CAP = ParagraphStyle('CAP', parent=B, fontSize=7.8, leading=10, textColor=MUTED, alignment=1)
SM = ParagraphStyle('SM', parent=B, fontSize=7.2, leading=9.4, textColor=MUTED)
BUL = ParagraphStyle('BUL', parent=B, leftIndent=10, spaceAfter=1.5)
HP = ParagraphStyle('HP', parent=B, fontName='DVB', fontSize=8, leading=10, textColor=colors.white)
CP = ParagraphStyle('CP', parent=B, fontSize=8, leading=10)
def img(p, w=None, h=None):
    iw, ih = ImageReader(p).getSize()
    if w is None: w = h*iw/ih
    if h is None: h = w*ih/iw
    if h is not None and w is not None and abs(w/h - iw/ih) > 1e-3: h = w*ih/iw
    return Image(p, width=w, height=h)
def imgh(p, h): iw, ih = ImageReader(p).getSize(); return Image(p, width=h*iw/ih, height=h)
def bl(items): return [Paragraph(t, BUL, bulletText='•') for t in items]
def tbl(rows, widths, head=True, bold_rows=()):
    rows = [[Paragraph(str(c), HP if head and i == 0 else CP) if not hasattr(c, 'wrap') else c for c in r] for i, r in enumerate(rows)]
    t = Table(rows, colWidths=widths)
    st = [('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#c9ced8')),
          ('TOPPADDING', (0, 0), (-1, -1), 2.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5)]
    if head: st.append(('BACKGROUND', (0, 0), (-1, 0), INK))
    t.setStyle(TableStyle(st)); return t
def grid(cells, widths):
    t = Table([cells], colWidths=widths); t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2)])); return t
rs = lambda v: f'₹{v:,}'
def price_table(line):
    rows = [['Product', 'Price (incl. 18% GST)', 'Print time*', 'Unit cost*', 'Profit direct (D2C)', 'Profit on Amazon / Flipkart']]
    for r in pr['lines'][line]:
        rows.append([r['name'], rs(r['price']), f"{r['print_h']} h", rs(r['unit_cost']), f"{rs(r['d2c_profit'])} ({r['d2c_margin']}%)", f"{rs(r['marketplace_profit'])} ({r['marketplace_margin']}%)"])
    return tbl(rows, [52*mm, 25*mm, 18*mm, 19*mm, 28*mm, 32*mm])
ASSUME = (f"*Model assumptions: PLA at {rs(A['pla_per_kg'])}/kg (Indian retail ₹699–₹965/kg); printed mass {int(A['printed_mass_factor']*100)} % of the solid model (3 walls, 15 % infill); "
          f"{A['g_per_hour']} g/h print rate; machine cost {rs(A['machine_per_hour'])}/h (power + wear); finishing {rs(A['finishing_per_part'])}/part; {int(A['waste']*100)} % waste allowance; "
          f"packaging {rs(A['packaging'])} and shipping {rs(A['shipping'])} per order (add-ons ship free with a main item); payment gateway {int(A['d2c_fee']*100)} % (D2C) or "
          f"{int(A['marketplace_fee']*100)} % all-in marketplace fees; GST 18 % (HSN 3926 under GST 2.0). Profit is after GST, fees, shipping and unit cost.")
SOURCES = ("Sources (accessed Oct 2026): competitor listings on Amazon.in (searches 'hot wheels wall mount', 'hot wheels display'); Garage64 wall display (amazon.in/dp/B0G1J8THXC); "
           "dams3dprinting 5-rack stand on Flipkart; PLA prices (magicdrop.in, price-history.in); GST 2.0 slabs (cleartax.in, eximpe.com HSN 3926 at 18 %); Amazon.in zero referral fee under ₹300 "
           "(outlookbusiness.com); Shiprocket rates from ₹20/500 g (shiprocket.in); India diecast community (diecastcollectiveindia.com, toycollectorsindia.com, indiandiecasthub.com); "
           "regional diecast-market growth (verifiedmarketreports.com). Hot Wheels and Matchbox are trademarks of Mattel, Inc.; SlideRack is an independent working name, not affiliated with Mattel.")
GTM_COMMON = ['<b>Instagram + WhatsApp (D2C):</b> short reels of a card sliding in and the 3-second swap; a WhatsApp catalogue for orders. This is where Indian collectors already buy and trade, e.g. the Diecast Collective India crews.',
              '<b>Amazon.in and Flipkart:</b> search reach for gift buyers. List as <i>"display for 1:64 carded cars"</i>. Do not put a car brand in the product name; use it only as a compatibility note.',
              '<b>Diecast retailers as resellers:</b> Toy Collectors India, Indian Diecast Hub, Zoomsters, Daily Diecast. Bundle a stand with a car purchase, or offer a store display unit.',
              '<b>Collector meets and expos:</b> live demos sell a side-loading display better than photos; take pre-orders on the spot.']
def footer(title):
    def f(c, d):
        c.saveState(); c.setFont('DV', 7.2); c.setFillColor(MUTED)
        c.drawString(16*mm, 9*mm, title); c.drawRightString(A4[0] - 16*mm, 9*mm, f'{d.page} / 4'); c.restoreState()
    return f
def build(path, title, story):
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=16*mm, rightMargin=16*mm, topMargin=13*mm, bottomMargin=15*mm, title=title, author='SlideRack')
    doc.build(story, onFirstPage=footer(title), onLaterPages=footer(title))
    from pypdf import PdfReader; print(path.split('/')[-1], 'pages', len(PdfReader(path).pages))

# ======================= WALL-MOUNT PITCH =======================
W = {r['name']: r for r in pr['lines']['wall']}
s = [Paragraph('PRODUCT PITCH · WALL-MOUNT DISPLAY', TAG),
     Paragraph('SlideRack Wall', H1),
     Paragraph('Six carded cars on a 13 × 45 cm strip of wall. Cards slide in from the side and swap in seconds. Add clip-on feet and the same rack stands on a desk.', SUB),
     Spacer(1, 3*mm),
     grid([imgh(I + 'w_hero.png', 112*mm), imgh(I + 'w_table.png', 112*mm)], [89*mm, 89*mm]),
     Paragraph('Left: on the wall with six cards. Right: the same rack on its clip-on table feet.', CAP),
     Paragraph('Why collectors want it', H2)]
s += bl(['<b>Keeps cars carded.</b> The card stands in a groove along its full width, with 10 mm supports at both corners. Nothing clips, presses or bends the card.',
         '<b>Side loading.</b> Slide a card in from the open end and it stops at the closed end. Swapping a car takes seconds, with no case to open.',
         '<b>Three times denser.</b> Each card tucks behind the ledge above, so the car and its name show in just 55 mm of wall height (a card is 165 mm).',
         '<b>Wall or desk.</b> The same rack screws to the wall (3 screws) or drops into two clip-on feet.'])
s += [Paragraph('The range', H2),
      tbl([['Product', 'What you get', 'Price'],
           ['SlideRack Wall 6', 'six-card wall rack, 3 screw holes', rs(W['SlideRack Wall 6']['price'])],
           ['Wall 6 + Table Feet', 'rack + clip-on feet for desk use', rs(W['Wall 6 + Table Feet bundle']['price'])],
           ['Table Feet (add-on)', 'turns an existing rack into a stand', rs(W['Table Feet (pair, add-on)']['price'])],
           ['SlideRack Wall Pro', 'every ledge swings out on a print-in-place hinge, with a stop and snap detent', rs(W['SlideRack Wall Pro (hinged)']['price'])]],
          [45*mm, 100*mm, 33*mm]),
      PageBreak()]
# page 2: design
s += [Paragraph('Design', H1),
      grid([imgh(I + 'w_bare_ann.png', 118*mm), [imgh(I + 'w_detail_ann.png', 76*mm)]], [80*mm, 98*mm]),
      Paragraph('Left: the rack with its main features. Right: one ledge close up, with a card halfway in.', CAP),
      Paragraph('Design details', H2)]
s += bl(['<b>One ledge profile, six times.</b> Each ledge has a 22 mm back wall, a 1.8 mm card groove, a 4 mm front lip and two 10 mm corner supports. Ledges are 130 mm long for a 108.3 mm clear groove, which fits the standard 108 × 165 mm card fully.',
         '<b>Shingled tiers.</b> Each ledge sits 55 mm higher and 4.6 mm further out than the one below, so each card passes 0.4 mm behind the next ledge.',
         '<b>Strong mount.</b> A 6 mm wall strip with three 3 mm screw holes. All the load goes into the wall through the strip.',
         '<b>Made to print at home.</b> One piece with no supports. It was refined over several test prints: ledge length, corner-support height and hole size all came from real measurements.'])
s += [tbl([['Specification', 'Value'], ['Overall size', '130 × 449 × 34 mm (W × H × D)'], ['Capacity', '6 standard carded cars'],
           ['Material and mass', f"PLA, about {round(155*A['printed_mass_factor'])} g printed"], ['Mounting', '3 × 3 mm screws (M3 / #4), 6 mm strip'],
           ['Table feet', f"2 clip-on feet, 195 mm deep; tips at {ft['plain']['stability_full']['tip_front_deg']}° forward with 6 cards"]], [45*mm, 133*mm]),
      PageBreak()]
# page 3: function
s += [Paragraph('How it works', H1), Paragraph('Load a card: slide it in from the side', H2),
      grid([img(I + 'w_slide_0.png', w=58*mm), img(I + 'w_slide_1.png', w=58*mm), img(I + 'w_slide_2.png', w=58*mm)], [59.3*mm]*3),
      Paragraph('1. Line the card up with the open end of the ledge.   2. Slide it along the groove; the corner supports guide it.   3. It stops against the closed end, fully seated.', CAP),
      Paragraph('Put it up, or put it on a desk', H2),
      grid([[Paragraph('<b>On the wall</b>', B)] + bl(['Mark the three holes with the strip held level.', 'Drive three 3 mm screws; their heads sit on the 6 mm strip.', 'Slide in up to six cards from the bottom up.']) +
            [Spacer(1, 2*mm), Paragraph('<b>On a desk</b>', B)] + bl(['Set the two clip-on feet on the table.', 'Drop the rack in: the spine into the socket, the bottom ledge into the cradle.', 'The 2.6 mm end stop sits below the groove floor, so cards still slide in from the side.']),
            img(I + 'w_feet.png', w=95*mm)], [82*mm, 96*mm]),
      Paragraph('Upgrade: SlideRack Wall Pro (hinged)', H2),
      grid([[Paragraph('Every ledge swings out on its own print-in-place hinge, which makes it easier to reach and clean behind. The ledge weight rests on the fixed knuckle and a shelf, so the load still goes into the wall. '
                       'A tooth-and-slot stop keeps the ledge from closing backwards, and a 0.6 mm bump in a pocket snaps it shut. It prints fully assembled.', B)],
            img(RP + 'fig_hinge.png', w=100*mm)], [76*mm, 102*mm]),
      PageBreak()]
# page 4: market
s += [Paragraph('Indian market and pricing', H1), Paragraph('Where it fits', H2)]
s += bl(['<b>A growing collector base.</b> Collector stores report 1,000+ buyers across Mumbai, Delhi, Bangalore and Chennai, and analysts rank India among the fastest-growing diecast markets (about 7.4 % CAGR to 2034 for the region).',
         '<b>Current choices are basic.</b> Carded wall hangers on Amazon.in sell for ₹299–₹519 and mostly hold cards on thin strips or by the hang tab. Acrylic cases cost ₹3,998 or more.',
         f"<b>SlideRack Wall sits at {rs(W['SlideRack Wall 6']['price'])}:</b> the top of the hanger range, justified by full-width card support, side loading, three-times density and the desk option."])
s += [img(I + 'chart_wall.png', w=118*mm), Paragraph('Pricing and margin per unit', H2), price_table('wall'), Paragraph(ASSUME, SM),
      Paragraph('How to sell it', H2)]
s += bl(GTM_COMMON + [f"<b>Launch offer:</b> bundle the Wall 6 with Table Feet at {rs(W['Wall 6 + Table Feet bundle']['price'])} to show off the wall-or-desk idea. Under ₹300, Amazon.in charges no referral fee, so Table Feet at {rs(W['Table Feet (pair, add-on)']['price'])} also work as a cheap first purchase."])
s += [Paragraph(SOURCES, SM)]
build('/home/user/RR/pitch/SlideRack_Wall_Mount_Pitch.pdf', 'SlideRack Wall: wall-mount display pitch', s)

# ======================= TABLETOP PITCH =======================
T = {r['name']: r for r in pr['lines']['table']}
u3, u5 = ub['3card_on_universal_base'], ub['5card_on_universal_base']
s = [Paragraph('PRODUCT PITCH · TABLETOP DISPLAY', TAG),
     Paragraph('SlideRack Desk: one base, two racks', H1),
     Paragraph('A 3-card or 5-card rack drops into the same universal stand. Cards slide in from the side; swap the whole rack in a second.', SUB),
     Spacer(1, 3*mm), img(I + 't_hero.png', w=178*mm),
     Paragraph('The 3-card rack (front) and the 5-card rack (back), each on the same universal base.', CAP),
     Paragraph('Why collectors want it', H2)]
s += bl(['<b>Interchangeable.</b> One base takes either rack. Buy a second rack, rotate a themed set, and store the spare rack flat.',
         '<b>Side loading.</b> Each ledge is open at one end. Cards slide in and stop at a solid wall, so nothing has to be opened.',
         '<b>Stable by design.</b> Leaning back 15°, a fully loaded stand tips only at ' + f"{u3['full']['tip_front']}° (3-card) and {u5['full']['tip_front']}° (5-card) forward.",
         '<b>Clean and simple.</b> The base copies a proven picture-frame-holder shape. Both parts print without supports.'])
s += [Paragraph('The range', H2),
      tbl([['Product', 'What you get', 'Price'],
           ['Tabletop Set 3', 'universal base + 3-card rack', rs(T['Tabletop Set 3 (base + 3-card rack)']['price'])],
           ['Tabletop Set 5', 'universal base + 5-card rack', rs(T['Tabletop Set 5 (base + 5-card rack)']['price'])],
           ['Collector Combo', 'universal base + 3-card + 5-card racks', rs(T['Collector Combo (base + 3 + 5 racks)']['price'])],
           ['Extra rack', '3-card or 5-card rack for your base', f"{rs(T['Extra 3-card rack']['price'])} / {rs(T['Extra 5-card rack']['price'])}"]],
          [45*mm, 100*mm, 33*mm]),
      PageBreak()]
s += [Paragraph('Design', H1),
      grid([imgh(I + 't_explode_ann.png', 112*mm), imgh(I + 't_back_ann.png', 112*mm)], [89*mm, 89*mm]),
      Paragraph('Left: the rack lifts straight out of the universal base. Right: the rib grid on the rack back sits on the base’s two back rests.', CAP),
      Paragraph('Design details', H2)]
s += bl(['<b>Card rack.</b> The same ledges as the wall rack (55 mm pitch, 4.6 mm step, 10 mm corner supports) on a 3 mm panel with a solid stop wall at one end and an open end at the other. A grid of 5 mm ribs stiffens the back.',
         '<b>Universal base.</b> A slot square to the card face with a low front lip; two 10 × 6 mm back rests at 15°; two feet whose gussets follow the back rests down to the floor. The slot sits on the table with no gap underneath.',
         '<b>One base, two racks.</b> Both racks share the same bottom edge and edge ribs, so the base for the 3-card and the 5-card rack is the same part.'])
s += [grid([img(I + 't_base_side.png', w=86*mm),
            tbl([['Specification', '3-card set', '5-card set'], ['Standing size (W × D × H)', '119 × 141 × 175 mm', '119 × 141 × 250 mm'],
                 ['Printed mass', f"{round((u3['rack_g'] + u3['base_g'])*A['printed_mass_factor'])} g", f"{round((u5['rack_g'] + u5['base_g'])*A['printed_mass_factor'])} g"],
                 ['Tip angle, loaded (fwd / back)', f"{u3['full']['tip_front']}° / {u3['full']['tip_rear']}°", f"{u5['full']['tip_front']}° / {u5['full']['tip_rear']}°"],
                 ['Print', 'rack on its side; base upright', 'no supports']], [36*mm, 27*mm, 27*mm])], [88*mm, 92*mm]),
      Paragraph('Base side view: the slot sits on the table, and the gussets run from each back rest down to its foot.', CAP),
      PageBreak()]
s += [Paragraph('How it works', H1), Paragraph('Load a card: slide it in from the side', H2),
      grid([img(I + 't_slide.png', w=96*mm), [Paragraph('<b>1.</b> Hold the card upright at the open end of a ledge.', B), Paragraph('<b>2.</b> Slide it into the groove; the 10 mm corner supports keep it upright.', B),
                                              Paragraph('<b>3.</b> Push until it stops at the solid wall. The card is held along its whole bottom edge and leans on the card behind.', B),
                                              Paragraph('To remove a card, slide it back out the same way.', B)]], [98*mm, 80*mm]),
      Paragraph('Swap racks in one second', H2),
      grid([[Paragraph('The rack simply rests in the base: in the slot at the bottom, against the two back rests behind. Lift it out and drop in the other rack. No screws, no clips.', B)] +
            bl(['<b>3-card rack:</b> small desks, gifts, a monthly favourites line-up.', '<b>5-card rack:</b> a series or theme on one stand.', '<b>Spare rack:</b> stores flat in a drawer, cards still loaded.']),
            img(I + 't_hero.png', w=96*mm)], [80*mm, 98*mm]),
      Paragraph('Verified before printing', H2)]
s += bl(['Both racks sit in the same base without interference, and the two base designs are identical.',
         'No card touches the rack or the base, and every card’s side-sliding path is clear on both racks.',
         'Stability was checked with a full load of cars (30 g car + 10 g card per slot), with tip angles computed from the centre of mass.'])
s += [PageBreak(), Paragraph('Indian market and pricing', H1), Paragraph('Where it fits', H2)]
s += bl(['<b>A desk-and-shelf collector segment.</b> Indian collectors buy from online diecast stores and meet through Instagram communities and local meets. Desk displays are popular for gifts and rotating favourites.',
         '<b>Current choices.</b> Tabletop racks on Amazon.in cost ₹349–₹564, but most hold loose cars, not carded ones. A 3D-printed 5-rack card stand lists at ₹1,500 on Flipkart.',
         f"<b>SlideRack Desk</b> undercuts that printed stand ({rs(T['Tabletop Set 5 (base + 5-card rack)']['price'])} for 5 cards). It adds side loading, an interchangeable rack and verified stability."])
s += [img(I + 'chart_table.png', w=118*mm), Paragraph('Pricing and margin per unit', H2), price_table('table'), Paragraph(ASSUME, SM), Paragraph('How to sell it', H2)]
s += bl(GTM_COMMON + [f"<b>Upsell path:</b> start with Set 3 ({rs(T['Tabletop Set 3 (base + 3-card rack)']['price'])}), then add an extra rack ({rs(T['Extra 5-card rack']['price'])} for 5 cards), or buy the Collector Combo ({rs(T['Collector Combo (base + 3 + 5 racks)']['price'])})."])
s += [Paragraph(SOURCES, SM)]
build('/home/user/RR/pitch/SlideRack_Tabletop_Pitch.pdf', 'SlideRack Desk: tabletop display pitch', s)
