import json
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.utils import ImageReader

R = '/home/user/RR/report/'; M = '/home/user/RR/3d-models/'
ub = json.load(open(M + 'table_universal_base_report.json'))
ez = json.load(open(M + 'table_easel_folding_report.json'))
ft = json.load(open(M + 'table_feet_report.json'))

INK, ACC, MUTED, LIGHT = colors.HexColor('#1d2433'), colors.HexColor('#e8841e'), colors.HexColor('#5a6070'), colors.HexColor('#eef1f6')
ss = getSampleStyleSheet()
H1 = ParagraphStyle('H1', parent=ss['Heading1'], fontName='Helvetica-Bold', fontSize=20, textColor=INK, spaceAfter=4, leading=24)
H2 = ParagraphStyle('H2', parent=ss['Heading2'], fontName='Helvetica-Bold', fontSize=13, textColor=INK, spaceBefore=6, spaceAfter=3)
B = ParagraphStyle('B', parent=ss['BodyText'], fontName='Helvetica', fontSize=9.6, leading=13.2, textColor=INK, spaceAfter=4)
SM = ParagraphStyle('SM', parent=B, fontSize=8, leading=10.5, textColor=MUTED)
CAP = ParagraphStyle('CAP', parent=SM, alignment=1, spaceAfter=6)
BUL = ParagraphStyle('BUL', parent=B, leftIndent=10, bulletIndent=0, spaceAfter=2)
TAG = ParagraphStyle('TAG', parent=B, fontName='Helvetica-Bold', fontSize=10, textColor=ACC, spaceAfter=2)

def img(path, width):
    w, h = ImageReader(path).getSize(); return Image(path, width=width, height=width*h/w)
def bullets(items): return [Paragraph(t, BUL, bulletText='•') for t in items]
HEADP = ParagraphStyle('hp', parent=B, fontName='Helvetica-Bold', fontSize=8.4, leading=10.4, textColor=colors.white)
CELLP = ParagraphStyle('cp', parent=B, fontSize=8.4, leading=10.6)
def table(rows, widths, head=True):
    rows = [[(Paragraph(c, HEADP if (head and i == 0) else CELLP) if isinstance(c, str) else c) for c in r] for i, r in enumerate(rows)]
    t = Table(rows, colWidths=widths)
    st = [('FONT', (0, 0), (-1, -1), 'Helvetica', 8.4), ('TEXTCOLOR', (0, 0), (-1, -1), INK), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
          ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#c9ced8')), ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]
    if head: st += [('BACKGROUND', (0, 0), (-1, 0), INK), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 8.4)]
    t.setStyle(TableStyle(st)); return t
P = lambda s: Paragraph(s, ParagraphStyle('c', parent=B, fontSize=8.4, leading=10.6))

def footer(c, d):
    c.saveState(); c.setFont('Helvetica', 7.5); c.setFillColor(MUTED)
    c.drawString(18*mm, 10*mm, 'SlideRack: modular card display system for carded diecast cars, project & pitch report')
    c.drawRightString(A4[0] - 18*mm, 10*mm, f'{d.page} / 5'); c.restoreState()

u3, u5 = ub['3card_on_universal_base'], ub['5card_on_universal_base']
story = []
# ---------------- page 1: cover ----------------
story += [Paragraph('PROJECT &amp; PITCH REPORT', TAG),
          Paragraph('SlideRack: a modular, side-loading display for carded diecast cars', H1),
          Paragraph('Wall rack, hinged wall rack and interchangeable tabletop stands, all 3D-printable at home without supports.', ParagraphStyle('sub', parent=B, fontSize=11, textColor=MUTED)),
          Spacer(1, 4*mm), img(R + 'fig_hero.png', 174*mm),
          Paragraph('Figure 1. The product family: 6-card wall rack (left), 3- and 5-card racks on one universal tabletop base. Orange: a card sliding in from the open side.', CAP),
          Paragraph('Summary', H2),
          Paragraph('Collectors who keep their cars <b>in the original blister cards</b> need a display that shows the car, protects the card and lets them swap cars quickly. '
                    'SlideRack holds standard mainline cards (108 × 165 mm) on shallow ledges that step out from the wall by 4.6 mm per tier. '
                    'Each card stands in a groove and tucks 0.4 mm behind the ledge above it, so the car and its name stay visible while cards overlap like roof tiles. '
                    'Cards <b>slide in from the open end of each ledge</b> and stop against a solid wall, with no clips, no glue and no opening of a case. '
                    'The same rack design hangs on a wall, stands on clip-on feet, or drops into a single universal base that takes either a 3-card or a 5-card rack.', B),
          table([['Key figure', 'Value'],
                 ['Card fit', '108 mm card in a 108.3 mm clear groove (130 mm ledge); 10 mm front corner supports'],
                 ['Display density', '55 mm of wall height per card (card itself is 165 mm), i.e. three times denser than hanging cards edge to edge'],
                 ['Mounting', '6 mm wall plate, three 3 mm screw holes; table feet and universal base are optional add-ons'],
                 ['Stability (tabletop, loaded)', f"tips at {u3['full']['tip_front']}° (3 cards) / {u5['full']['tip_front']}° (5 cards) forward, {u3['full']['tip_rear']}° / {u5['full']['tip_rear']}° backward"],
                 ['Printing', 'every part prints without supports; the hinged versions print fully assembled (print-in-place)']],
                [45*mm, 129*mm]),
          PageBreak()]
# ---------------- page 2: problem + inspiration ----------------
story += [Paragraph('1. The problem and the design inspiration', H1),
          Paragraph('The problem', H2),
          Paragraph('A carded car is a flat, light object (about 40 g) that is easily bent at the corners and has a 25–40 mm deep blister on the front. '
                    'The options commonly sold today each solve part of the job:', B)]
story += bullets(['<b>Clamshell protector cases</b> (single-card PET shells) protect the card very well, but each car needs its own case, and the cases still need a shelf, pegs or a wall system to be displayed.',
                  '<b>Multi-car wall cases</b> show many cars at once, but they are bulky and need to be opened to change a car; they take a full card height of wall per row.',
                  '<b>Simple 3D-printed hangers and peg strips</b> are cheap and open, but usually support the card at one point (the hang tab or a thin rail) and let cards swing or bow.'])
story += [Paragraph('The design goal set for this project: <b>full-width support of the card, quick side loading, high density on the wall, and a single home-printable part per function.</b>', B),
          Paragraph('Design inspiration and evolution', H2),
          Paragraph('The design grew in short iterations from four reference models, each contributing one idea:', B)]
story += bullets(['<b>An existing 6-slot wall rack:</b> the shingled C-channel slots (55 mm pitch, 4.6 mm step), which let cards overlap without hiding the car.',
                  '<b>A stand-alone ledge:</b> the ledge profile with a back wall, a narrow card groove, a low front lip and raised corner supports. It became the profile of every tier.',
                  '<b>An adjustable drawing-pad stand:</b> its nested print-in-place hinges inspired the hinged wall rack and the folding easel.',
                  '<b>A picture-frame holder:</b> a V-slot, two leaning back rests and two feet. Its simplicity set the shape of the universal tabletop base.'])
story += [Spacer(1, 2*mm), img(R + 'fig_evolution.png', 174*mm),
          Paragraph('Figure 2. Design evolution: (1) original slot rack, (2) six identical ledges sized to the card, 6 mm plate, 3 mm holes, (3) hinged ledges with stop and snap detent, (4) tabletop rack on the universal base.', CAP),
          Paragraph('Each step was driven by testing a real print: the ledge length was corrected after measuring cards (12 cm was too short, 13 cm fits the full card), the corner supports were raised to 10 mm to stop card corners tipping forward, '
                    'and the closed-end tabletop stands were redesigned because cards must be loaded from the side.', B),
          PageBreak()]
# ---------------- page 3: how it works ----------------
story += [Paragraph('2. How it works', H1),
          img(R + 'fig_geometry.png', 150*mm),
          Paragraph('Figure 3. Left: side section of the wall rack. Each tier sits 55 mm higher and 4.6 mm further from the wall; a card in one groove passes 0.4 mm behind the next ledge. Right: top view of one ledge; the card enters from the open end and stops at the solid end.', CAP),
          Paragraph('Card holding', H2)]
story += bullets(['The card stands in a 1.8 mm groove between a 22 mm back wall and a 4 mm front lip. At both ends a 10 mm corner support narrows the groove to 1.3 mm and holds the card corners upright.',
                  'Because every tier steps 4.6 mm forward, the upper part of each card (the header) slides behind the next ledge and the card above. Only the car, the blister and the name show, so a 165 mm card uses only 55 mm of wall.',
                  'The groove is open at the tip of the ledge. A card is slid in sideways and stops against the solid end, and it is removed the same way, with no tools.'])
story += [Paragraph('Hinged wall rack (print-in-place)', H2),
          img(R + 'fig_hinge.png', 132*mm),
          Paragraph('Figure 4. Each ledge swings on its own hinge: two ledge knuckles around one fixed knuckle, joined by 45° cone pins with 0.4 mm clearance. The rack prints fully assembled.', CAP)]
story += bullets(['<b>Load path:</b> the ledge settles 0.4 mm onto the fixed knuckle and a shelf under its root, so all weight goes through the mount into the wall screws. The pin only guides the swing.',
                  '<b>Backward stop:</b> a tooth under the ledge runs in a slot and stops the ledge 1.5–2° past closed.',
                  '<b>Snap detent:</b> a 0.6 mm bump sits in a pocket under the ledge when closed. Gravity and the cars hold it there, and lifting the ledge slightly releases it, so no part has to flex.',
                  f"<b>Clip-on table feet</b> let the same wall rack stand on a table. They hold it with 0.35 mm play, and it tips at {ft['hinged']['stability_full']['tip_front_deg']}° forward with 6 cards. They never block the side-loading path."])
story += [PageBreak()]
# ---------------- page 4: tabletop + validation ----------------
story += [Paragraph('3. Tabletop system and engineering validation', H1),
          Paragraph('One base, two racks', H2),
          Paragraph('For desks and shelves, the card tiers are built on a 3 mm panel stiffened by a grid of 5 mm ribs on its back. The panel sits in a separate base modelled on a picture-frame holder: '
                    'a slot square to the card face, a low front lip, two back rests leaning 15° and two feet with gussets that follow the back rests down to the floor. '
                    'Both the 3-card and the 5-card rack have the same bottom edge and edge ribs, so <b>one universal base takes either rack</b>. Swap the rack, keep the base. '
                    'A folding 3-card easel with two print-in-place hinges and four angle settings (10–25°) is also part of the family.', B),
          Paragraph('Validation method', H2),
          Paragraph('Every design was built as a parametric model and checked by computer before printing. Each check is a solid-geometry intersection, so a result of 0 mm³ means the parts truly do not touch:', B),
          table([['Check', 'Result'],
                 [P('Card clearance: every card in place, and every card on its sliding path from 150 mm outside the rack'), P('0 mm³ overlap on all wall, hinged and tabletop versions')],
                 [P('Print-in-place clearance (hinged rack, folding easel)'), P('No contact as printed, and none after a 0.3 mm shift in any direction')],
                 [P('Hinge motion'), P('Free from 0° to 110° on all six hinged ledges; backward stop engages at 2°; detent holds at closed')],
                 [P('Folding easel'), P(f"Unfolds without collision; at 10°, 15°, 20° and 25° the base lies flat, the foot sits in its groove and the cards are clear; tips forward at {ez['display']['10']['tip_front_deg']}–{ez['display']['25']['tip_front_deg']}°")],
                 [P('Universal base'), P('The bases computed for the 3- and 5-card racks are identical (0 mm³ difference); each rack seats without interference')],
                 [P('Stability (centre of mass with 30 g car + 10 g card per slot, tip angle to the base edge)'),
                  P(f"3-card: {u3['full']['tip_front']}° forward / {u3['full']['tip_rear']}° back; 5-card: {u5['full']['tip_front']}° / {u5['full']['tip_rear']}° (target ≥ 18°)")]],
                [80*mm, 94*mm]),
          Spacer(1, 3*mm), Paragraph('Printing', H2),
          table([['Part', 'Orientation', 'Filament (PLA)', 'Notes'],
                 ['6-ledge wall rack (130 mm)', 'on its back or side', '≈ 155 g', 'single part, 3 mm screw holes'],
                 ['Hinged wall rack (134 mm)', 'on its side', '≈ 174 g', '7 bodies printed assembled; test one hinge first'],
                 ['3-card / 5-card tabletop rack', 'on its stop wall', f"{u3['rack_g']} g / {u5['rack_g']} g", 'ribs chamfered 45°, no supports'],
                 ['Universal base', 'upright', f"{u3['base_g']} g", 'no supports'],
                 ['Folding 3-card easel', 'folded, on its side', '≈ 338 g', 'two print-in-place hinges']],
                [50*mm, 36*mm, 28*mm, 60*mm]),
          Paragraph('Recommended: 0.2 mm layers, 3 walls, 15 % infill. Filament figures assume solid parts and are upper bounds.', SM),
          PageBreak()]
# ---------------- page 5: market + advantages ----------------
story += [Paragraph('4. Market position and advantages', H1),
          Paragraph('How SlideRack compares', H2),
          table([['', 'Clamshell protector cases', 'Multi-car wall cases', 'Printed hangers / peg strips', 'SlideRack'],
                 [P('Card support'), P('full, enclosed'), P('full, enclosed'), P('tab or thin rail'), P('full-width groove + 10 mm corner supports')],
                 [P('Changing a car'), P('open the shell'), P('open the case'), P('lift off'), P('<b>slide out sideways</b>')],
                 [P('Wall space per card'), P('full card height'), P('full card height'), P('full card height'), P('<b>55 mm (about 1/3)</b>')],
                 [P('Wall and table use'), P('needs a second product'), P('wall only'), P('wall only'), P('<b>wall, table feet, or universal base</b>')],
                 [P('Make it yourself'), P('no'), P('no'), P('yes'), P('<b>yes, no supports, parametric</b>')],
                 [P('Dust protection'), P('yes'), P('yes'), P('no'), P('no (can be combined with clamshells)')]],
                [30*mm, 34*mm, 34*mm, 34*mm, 42*mm]),
          Paragraph('Advantages', H2)]
story += bullets(['<b>Fast, tool-free swaps.</b> Cards slide in and out from the side. Nothing to open, clip or unscrew.',
                  '<b>Three times the density.</b> The shingle layout shows the car and its name in 55 mm of height instead of a full 165 mm card.',
                  '<b>One system, many uses.</b> The same tier geometry works as a wall rack, a hinged wall rack, a rack on table feet, a folding easel, and interchangeable 3- and 5-card racks on one base.',
                  '<b>Designed for home printing.</b> Every part prints without supports. The hinged parts print assembled. A full 6-card wall rack uses about 155 g of filament.',
                  '<b>Verified before printing.</b> Clearances, motion, card paths and stability are all checked numerically, which shortens the print-and-try loop.',
                  '<b>Gentle on cards.</b> The card is held along its whole bottom edge and at both corners, never at the hang tab.'])
story += [Paragraph('Next steps', H2)]
story += bullets(['Print one hinge and one universal base as a tolerance test on the target printer, then adjust clearances (0.4 mm today) if needed.',
                  'Add variants for long cards and premium cards (wider than 108 mm) by changing one width parameter.',
                  'Offer printed kits and print files, and optionally clear front covers for dust protection.'])
story += [Spacer(1, 2*mm),
          Paragraph('Market references (retrieved October 2026): Protech SSCAR carded-car storage cases (walmart.com/ip/193695882); Sterling and EVORETRO clamshell protector cases for mainline and premium cards, '
                    'mainline card size 4.25 × 6.5 in (walmart.com/ip/782260352, topshelfco.ca); modular 3D-printed carded-car wall hanger (makerworld.com/models/2572456). '
                    'Hot Wheels and Matchbox are trademarks of Mattel, Inc.; SlideRack is an independent working name and is not affiliated with Mattel.', SM)]

doc = SimpleDocTemplate('/home/user/RR/report/SlideRack_Project_Pitch_Report.pdf', pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=15*mm, bottomMargin=16*mm,
                        title='SlideRack project and pitch report', author='SlideRack project')
doc.build(story, onFirstPage=footer, onLaterPages=footer)
from pypdf import PdfReader
print('pages', len(PdfReader('/home/user/RR/report/SlideRack_Project_Pitch_Report.pdf').pages))
