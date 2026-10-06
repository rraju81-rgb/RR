"""4-page sales pitch for SlideRack Fold (fixed rack + print-in-place kickstand), 3 / 5 / 6 cards."""
import json
src = open('make_pitch.py').read().split('# ======================= WALL-MOUNT PITCH')[0]
exec(src)
MD = '/home/user/RR/3d-models/'
R = {N: json.load(open(MD + f'right_fixed_rack_{N}card_kickstand_report.json')) for N in (3, 5, 6)}
K = {r['name'].split(' (')[0]: r for r in pr['lines']['kickstand']}
TB = {r['name'].split(' (')[0]: r for r in pr['lines']['table']}
f3, f5, f6, duo = K['SlideRack Fold 3'], K['SlideRack Fold 5'], K['SlideRack Fold 6'], K['Fold Duo']
t3, t5 = TB['Tabletop Set 3'], TB['Tabletop Set 5']
s = [Paragraph('PRODUCT PITCH · TABLETOP DISPLAY · FOLDING', TAG),
     Paragraph('SlideRack Fold', H1),
     Paragraph('An open-frame card rack with a fold-out stand, printed in one piece. Cards slide in from the side, '
               'the stand flips out to a fixed 35°, and the whole thing folds flat for the shelf or the post.', SUB),
     Spacer(1, 3*mm), img(I + 'k_hero.png', w=178*mm),
     Paragraph('SlideRack Fold 3, 5 and 6, each loaded with carded 1:64 cars.', CAP), Spacer(1, 2*mm),
     Paragraph('Why collectors will buy it', H2)]
s += bl(['<b>Shows the card, not the rack.</b> There is no back panel. Each card rests on a slim ledge, and the cards overlap like roof tiles, so the whole card and its art stay visible.',
         '<b>Swap a car in three seconds.</b> Slide a card in from the open end until it meets the stop, and slide it out the same way. The stand never has to be picked up or taken apart.',
         '<b>Stands up, folds flat.</b> One flip of the leg and it stands at a fixed, stable lean. Fold it back and the stand is 31–45 mm thick for a drawer, a shelf or a courier box.',
         '<b>One part, nothing to assemble.</b> The hinge prints already working, so there are no screws, glue or loose pins to lose.'])
s += [Paragraph('The range', H2),
      tbl([['Model', 'Cards', 'Size open (W × D × H)', 'Weight', 'Price'],
           ['SlideRack Fold 3', '3', ' × '.join(f'{v:.0f}' for v in R[3]['standing_W_D_H_mm']) + ' mm', f"{R[3]['mass_stand_g']} g", rs(f3['price'])],
           ['SlideRack Fold 5', '5', ' × '.join(f'{v:.0f}' for v in R[5]['standing_W_D_H_mm']) + ' mm', f"{R[5]['mass_stand_g']} g", rs(f5['price'])],
           ['SlideRack Fold 6', '6', ' × '.join(f'{v:.0f}' for v in R[6]['standing_W_D_H_mm']) + ' mm', f"{R[6]['mass_stand_g']} g", rs(f6['price'])],
           ['Fold Duo (3 + 5)', '8', 'both of the above', f"{R[3]['mass_stand_g'] + R[5]['mass_stand_g']} g", rs(duo['price'])]],
          [44*mm, 16*mm, 56*mm, 24*mm, 34*mm]),
      Paragraph('Heights exclude the cards: the top card stands about 145 mm above the rack. Prices include 18 % GST.', SM),
      PageBreak()]
# ---- page 2: how it works
s += [Paragraph('How it works', H1), Paragraph('Three moves: open the stand, slide the cards in, fold it away.', SUB), Spacer(1, 2*mm),
      grid([img(I + 'k_slide.png', w=78*mm), img(I + 'k_back.png', w=78*mm)], [89*mm, 89*mm]),
      Paragraph('Left: a card sliding in from the open end. Right: the fold-out stand, seen from behind.', CAP), Paragraph('1 · Slide-in ledges', H2)]
s += bl(['Every ledge has a 1.8 mm groove that holds the card\'s bottom edge, and a 22 mm back wall that the card leans on.',
         'Ledges sit 55 mm apart and step 4.6 mm forward each level. Every card clears the one below, and each car stays fully visible.',
         'Cards go in from the open end and stop against the solid end wall at exactly 108 mm. That fits the standard 108 × 165 mm carded 1:64 blister.'])
s += [Paragraph('2 · A stand with exactly two positions', H2)]
s += bl([f'The 80 mm leg swings from flat (0°) to a hard stop at 35°. The rack then leans back {R[6]["lean_deg"]}–{R[3]["lean_deg"]}°, so the cards face the viewer.',
         'A tab on the hinge lands flat on the end wall, and the rack\'s own weight presses it shut. Nothing to adjust, nothing to slip.',
         f'Stable when fully loaded: a forward tip angle of at least {min(R[N]["tip_front_deg"] for N in R)}°, backward at least {min(R[N]["tip_rear_deg"] for N in R)}° and sideways at least {min(R[N]["tip_sideways_deg"] for N in R)}°. It survives a nudge on a desk or shelf.'])
s += [grid([img(I + 'k_hinge.png', w=70*mm), img(I + 'k_fold.png', w=70*mm)], [89*mm, 89*mm]),
      Paragraph('Left: the hinge open at its 35° stop. Right: folded flat for storage or shipping.', CAP), PageBreak()]
# ---- page 3: why it wins + manufacturing
s += [Paragraph('Why it wins', H1), Paragraph('Lighter, faster to make and cheaper than our own base-and-rack set, with no extra parts.', SUB), Spacer(1, 2*mm),
      tbl([['', 'SlideRack Fold 3', 'Tabletop Set 3 (base + rack)', 'SlideRack Fold 5', 'Tabletop Set 5 (base + rack)'],
           ['Parts to print', '1', '2', '1', '2'],
           ['Print time*', f"{f3['print_h']} h", f"{t3['print_h']} h", f"{f5['print_h']} h", f"{t5['print_h']} h"],
           ['Unit cost*', rs(f3['unit_cost']), rs(t3['unit_cost']), rs(f5['unit_cost']), rs(t5['unit_cost'])],
           ['Price', rs(f3['price']), rs(t3['price']), rs(f5['price']), rs(t5['price'])],
           ['Folds flat', 'yes, 31 mm', 'no (2 pieces)', 'yes, 40 mm', 'no (2 pieces)']],
          [34*mm, 34*mm, 38*mm, 34*mm, 38*mm]), Spacer(1, 2*mm)]
s += bl([f'<b>{round(100*(1 - f3["print_h"]/t3["print_h"]))} % less print time</b> than the 3-card base set, and {round(100*(1 - f5["print_h"]/t5["print_h"]))} % less for the 5-card. That means more units per printer per day.',
         f'<b>{rs(t3["price"] - f3["price"])}–{rs(t5["price"] - f5["price"])} cheaper</b> for the buyer, while the D2C margin stays at {f5["d2c_margin"]}–{f3["d2c_margin"]} %.',
         '<b>Against the market:</b> carded wall hangers sell at ₹299–₹519 but hide half the card and need drilling. Tabletop racks at ₹349–₹564 hold loose cars, not cards. A 3D-printed 5-rack card stand on Flipkart is ₹1,500; SlideRack Fold 5 is ' + rs(f5['price']) + ' and folds flat.',
         '<b>Gift-ready:</b> it folds flat into a slim box, ships in the cheapest courier slab, and needs no instructions.'])
s += [Paragraph('Made to be made', H2),
      grid([img(I + 'k_print.png', w=80*mm), Paragraph(
          '• <b>One print, no supports:</b> it prints as it lies, end wall on the bed. There is nothing to remove, sand or assemble.<br/>'
          '• <b>A hinge that does not fuse:</b> the leg and pin both start on the bed, the gaps are 0.6–0.8 mm, and every surface above a gap is a 45° cone. A gentle swing frees it.<br/>'
          '• <b>Checked in software:</b> no contact even with a 0.45 mm shift, a free swing to 34.8°, a hard stop at 35.0°, and watertight STLs. The blueprint and tolerances are in <i>SlideRack_Fold_Blueprint.pdf</i>.<br/>'
          '• <b>Scales with demand:</b> each size is the same design with more ledges, so a print farm runs one job per SKU.', B)], [84*mm, 94*mm]),
      Paragraph('The 5-card model as it comes off the printer: one piece, with the stand folded.', CAP), PageBreak()]
# ---- page 4: market, pricing, go-to-market
s += [Paragraph('Market, pricing and go-to-market (India)', H1),
      Paragraph('Priced under the gift threshold, with margin on every channel.', SUB), Spacer(1, 1*mm), price_table('kickstand'),
      Paragraph(ASSUME, SM), Spacer(1, 1*mm), img(I + 'k_blueprint.png', w=150*mm),
      Paragraph('From the blueprint set: hinge detail, with the gaps that let it print in one piece.', CAP),
      Paragraph('Where to sell', H2)]
s += bl(GTM_COMMON + ['<b>Launch offer:</b> Fold Duo (3 + 5) at ' + rs(duo['price']) + ', ' + rs(f3['price'] + f5['price'] - duo['price']) + ' off buying both. It is the natural upgrade for anyone who outgrows one rack.'])
s += [Paragraph(SOURCES, SM)]
build('/home/user/RR/pitch/SlideRack_Fold_Pitch.pdf', 'SlideRack Fold: folding tabletop display pitch', s)
