"""Unit cost and channel margin model for the Indian market (all ₹, prices GST-inclusive)."""
import json
A = dict(pla_per_kg=900, g_per_hour=25, machine_per_hour=12, finishing_per_part=20, waste=0.10, printed_mass_factor=0.75,
         packaging=30, shipping=70, gst=0.18, d2c_fee=0.02, marketplace_fee=0.15)
# grams from the verified models (solid upper bound); parts = printed parts to finish
P = {
 'wall':  [('SlideRack Wall 6',            155, 1, 649),
           ('Table Feet (pair, add-on)',     68, 2, 199),
           ('Wall 6 + Table Feet bundle',   223, 3, 799),
           ('SlideRack Wall Pro (hinged)',  174, 1, 949)],
 'kickstand': [('SlideRack Fold 3 (3-card, kickstand)',   137, 1, 549),
               ('SlideRack Fold 5 (5-card, kickstand)',   237, 1, 749),
               ('SlideRack Fold 6 (6-card, kickstand)',   276, 1, 849),
               ('Fold Duo (3 + 5)',                       374, 2, 1199)],
 'table': [('Tabletop Set 3 (base + 3-card rack)',  304, 2, 899),
           ('Tabletop Set 5 (base + 5-card rack)',  392, 2, 1199),
           ('Collector Combo (base + 3 + 5 racks)', 577, 3, 1699),
           ('Extra 3-card rack',                    185, 1, 549),
           ('Extra 5-card rack',                    273, 1, 749)]}
def cost(g, parts):
    g = g*A['printed_mass_factor']                       # 3 walls / 15 % infill vs the solid model
    fil = g/1000*A['pla_per_kg']; hrs = g/A['g_per_hour']; mach = hrs*A['machine_per_hour']
    return dict(grams=round(g), print_h=round(hrs, 1), filament=round(fil), machine=round(mach), finishing=parts*A['finishing_per_part'],
                unit_cost=round((fil + mach + parts*A['finishing_per_part'])*(1 + A['waste'])))
def margin(price, unit, addon=False):
    net = price/(1 + A['gst']); gst = price - net
    out = {}
    for ch, fee in [('d2c', A['d2c_fee']), ('marketplace', A['marketplace_fee'])]:
        ship = 0 if addon else A['shipping'] + A['packaging']
        prof = net - fee*price - ship - unit
        out[ch] = dict(profit=round(prof), margin_pct=round(100*prof/net))
    return round(gst), out
rep = {'assumptions': A, 'lines': {}}
for line, items in P.items():
    rows = []
    for name, g, parts, price in items:
        c = cost(g, parts); addon = 'add-on' in name
        cands = sorted(set(p for h in range(1, 40) for p in (h*100 - 51, h*100 - 1) if p > 0))
        for p in cands:
            gst, m = margin(p, c['unit_cost'], addon)
            if m['d2c']['margin_pct'] >= 25 and m['marketplace']['margin_pct'] >= 10: price = p; break
        floor_price = price
        if 'Pro' in name: price = 749          # positioned as premium: assembled hinges, higher print-failure / QC risk
        gst, m = margin(price, c['unit_cost'], addon); c['cost_floor_price'] = floor_price
        rows.append(dict(name=name, price=price, gst=gst, **c, **{f'{k}_profit': v['profit'] for k, v in m.items()}, **{f'{k}_margin': v['margin_pct'] for k, v in m.items()}))
        print(f"{name:40s} ₹{price:5d}  {g:4d} g  {c['print_h']:5.1f} h  cost ₹{c['unit_cost']:4d}  D2C ₹{m['d2c']['profit']:4d} ({m['d2c']['margin_pct']}%)  Mkt ₹{m['marketplace']['profit']:4d} ({m['marketplace']['margin_pct']}%)")
    rep['lines'][line] = rows
json.dump(rep, open('pricing.json', 'w'), indent=1)
