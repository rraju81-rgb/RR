"""Blueprint (technical drawing set) for the SlideRack Fold family, drawn from the verified models."""
import os, sys, json, numpy as np, trimesh
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle, Polygon, Arc
sys.path.insert(0, '/home/user/RR/3d-models')
MD = '/home/user/RR/3d-models/'; OUT = '/home/user/RR/pitch/'
BGC, LN, DM, HL, ACC = '#0f2a4a', '#e8f1ff', '#9fd0ff', '#5d7fa6', '#ffb347'
CFG = {3: (121, 27.5), 5: (176, 25.0), 6: (176, 24.5)}
plt.rcParams.update({'font.family': 'DejaVu Sans', 'text.color': LN})
def load(N):
    YH, A = CFG[N]
    os.environ.update(KS_N=str(N), KS_YH=str(YH), KS_ALPHA=str(A), KS_RACK=MD + 'reference_right_fixed_rack_PRINT.stl')
    sys.modules.pop('build_right_fixed_rack_kickstand', None); import build_right_fixed_rack_kickstand as E
    m = trimesh.load(MD + f'right_fixed_rack_{N}card_kickstand_PRINT.stl'); m.apply_transform(E.TO_RACK)
    P, L = sorted(m.split(), key=lambda b: -b.volume)
    return E, P, L, json.load(open(MD + f'right_fixed_rack_{N}card_kickstand_report.json'))
def edges(m, i, j, ang=25):
    e = m.face_adjacency_edges[m.face_adjacency_angles > np.radians(ang)]
    return m.vertices[e][:, :, [i, j]]
def draw(ax, m, i, j, sgn=(1, 1), off=(0, 0), color=LN, lw=0.55, ls='-'):
    s = edges(m, i, j)*np.array(sgn) + np.array(off)
    for a, b in s: ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=lw, ls=ls, solid_capstyle='round')
def dim(ax, p, q, off, text, vertical=False, fs=7.5):
    p, q = np.array(p, float), np.array(q, float)
    if vertical:
        x = p[0] + off; ax.plot([p[0], x + np.sign(off)*2], [p[1], p[1]], color=DM, lw=0.4); ax.plot([q[0], x + np.sign(off)*2], [q[1], q[1]], color=DM, lw=0.4)
        ax.annotate('', (x, p[1]), (x, q[1]), arrowprops=dict(arrowstyle='<->', color=DM, lw=0.6, shrinkA=0, shrinkB=0))
        ax.text(x - np.sign(off)*1.5, (p[1] + q[1])/2, text, color=DM, fontsize=fs, rotation=90, ha='center', va='center',
                bbox=dict(fc=BGC, ec='none', pad=0.5))
    else:
        y = p[1] + off; ax.plot([p[0], p[0]], [p[1], y + np.sign(off)*2], color=DM, lw=0.4); ax.plot([q[0], q[0]], [q[1], y + np.sign(off)*2], color=DM, lw=0.4)
        ax.annotate('', (p[0], y), (q[0], y), arrowprops=dict(arrowstyle='<->', color=DM, lw=0.6, shrinkA=0, shrinkB=0))
        ax.text((p[0] + q[0])/2, y, text, color=DM, fontsize=fs, ha='center', va='center', bbox=dict(fc=BGC, ec='none', pad=0.5))
def sheet(title, sub, num, total):
    fig = plt.figure(figsize=(16.54, 11.69)); fig.patch.set_facecolor(BGC)
    ax0 = fig.add_axes([0, 0, 1, 1]); ax0.set_xlim(0, 420); ax0.set_ylim(0, 297); ax0.axis('off')
    ax0.add_patch(Rectangle((8, 8), 404, 281, fill=False, ec=LN, lw=1.2)); ax0.add_patch(Rectangle((10, 10), 400, 277, fill=False, ec=LN, lw=0.4))
    # title block
    tb = [(290, 10, 120, 34)]
    ax0.add_patch(Rectangle((290, 10), 120, 34, fill=False, ec=LN, lw=0.8))
    for yy in (21, 32): ax0.plot([290, 410], [yy, yy], color=LN, lw=0.4)
    ax0.plot([360, 360], [10, 21], color=LN, lw=0.4)
    ax0.text(293, 38, 'SLIDERACK FOLD', fontsize=11, weight='bold', va='center')
    ax0.text(293, 26.5, title, fontsize=8.5, va='center')
    ax0.text(293, 15.5, sub, fontsize=6.5, va='center')
    ax0.text(363, 15.5, f'SHEET {num} / {total}   ·   UNITS: mm   ·   A3', fontsize=6.0, va='center')
    ax0.text(12, 13, 'Third-angle projection · drawn from the verified STL models · do not scale the print; use the dimensions', fontsize=6, color=HL)
    return fig, ax0
def view(fig, rect, xl, yl, label):
    ax = fig.add_axes(rect); ax.set_facecolor(BGC); ax.set_xlim(*xl); ax.set_ylim(*yl); ax.set_aspect('equal'); ax.axis('off')
    ax.text(0.0, 1.0, label, transform=ax.transAxes, fontsize=8.5, weight='bold', color=ACC, va='bottom')
    return ax
pages = []
with PdfPages(OUT + 'SlideRack_Fold_Blueprint.pdf') as pdf:
    total = 5
    for pg, N in enumerate((3, 5, 6), start=1):
        E, P, L, r = load(N); YH, A = CFG[N]; Ht = E.YTOP
        fig, ax0 = sheet(f'{N}-CARD RACK · GENERAL ARRANGEMENT', f'lean {A}° · leg 0° / 35° · {r["mass_stand_g"]} g PLA · one print', pg, total)
        sc = 230/max(Ht, 250)                                  # figure-mm per model-mm (approx.)
        # FRONT view (look at the card face): x right, y up
        h_mm = 250*sc*1.0
        axF = view(fig, [0.05, 0.12, 0.30, 0.80], (-25, 165), (-30, Ht + 25), 'FRONT VIEW (card face)')
        draw(axF, L, 0, 1, color=HL, ls='--', lw=0.5); draw(axF, P, 0, 1)
        dim(axF, (0, 0), (136, 0), -14, '136 (ledge length)')
        dim(axF, (0, 0), (0, Ht), -15, f'{Ht:.0f} overall', vertical=True)
        dim(axF, (136, 0), (136, 55), 10, '55 pitch', vertical=True)
        dim(axF, (0, Ht), (28, Ht), 8, '28 stop')
        dim(axF, (28, Ht), (136, Ht), 8, '108 card slot')
        axF.annotate('cards slide in\nfrom this end', (140, 30 + 55*(N//2)), (150, 60 + 55*(N//2)), color=ACC, fontsize=7, arrowprops=dict(arrowstyle='->', color=ACC))
        axF.annotate(f'hinge on the back\nof the end wall, {YH:.0f} up', (5, YH), (-24, YH - 40), color=ACC, fontsize=6.5, arrowprops=dict(arrowstyle='->', color=ACC, lw=0.6))
        # SIDE view (from the open end): z right (forward), y up; leg folded solid + open dashed
        axS = view(fig, [0.37, 0.12, 0.27, 0.80], (-90, 60), (-30, Ht + 25), 'SIDE VIEW (from the open end)')
        draw(axS, P, 2, 1); draw(axS, L, 2, 1, color=LN)
        Lo = L.copy().apply_transform(E.rot(E.PSI)); draw(axS, Lo, 2, 1, color=ACC, ls='--', lw=0.5)
        dim(axS, (0, 0), (0, 22), 50, '22 ledge', vertical=True)
        dim(axS, (-6.6, YH), (-6.6, 0), -70, f'{YH:.0f} hinge axis', vertical=True)
        zs = [4.6*k for k in range(N)]
        dim(axS, (0, Ht), (32 - 4.6*(6 - N), Ht), 8, f'{32 - 4.6*(6 - N):.1f} depth')
        dim(axS, (-12.6, 40), (-0.6, 40), -6, '6 leg')
        axS.text(-85, 6, f'leg open 35° (dashed) → rack leans {A}°', color=ACC, fontsize=7)
        axS.text(-85, -2, '4.6 forward step per ledge', color=DM, fontsize=7)
        # BACK view (stand side): x mirrored, y up
        axB = view(fig, [0.66, 0.30, 0.30, 0.62], (-165, 25), (-30, Ht + 25), 'BACK VIEW (stand folded)')
        draw(axB, P, 0, 1, sgn=(-1, 1), color=HL, lw=0.45); draw(axB, L, 0, 1, sgn=(-1, 1), color=ACC, lw=0.7)
        dim(axB, (-80, r['foot_Z_min'] + 16), (0, r['foot_Z_min'] + 16), -26, '80 leg width')
        dim(axB, (0, YH), (0, 0), 12, f'{YH:.0f}', vertical=True)
        # spec box
        ax0.text(280, 70, '\n'.join([f'Cards: {N} carded 1:64 cars (108 × 165 mm card)', f'Stand open: {r["standing_W_D_H_mm"][0]:.0f} × {r["standing_W_D_H_mm"][1]:.0f} × {r["standing_W_D_H_mm"][2]:.0f} mm (W × D × H, w/o cards)',
               f'Tip angle loaded: fwd {r["tip_front_deg"]}° · back {r["tip_rear_deg"]}° · side {r["tip_sideways_deg"]}°', f'Material: PLA, {r["mass_stand_g"]} g printed (est.)',
               'Print: on its side, end wall down, no supports']), fontsize=6.6, va='top', color=LN, linespacing=1.5)
        pdf.savefig(fig, facecolor=BGC); plt.close(fig)
    # HINGE DETAIL
    E, P, L, r = load(5)
    fig, ax0 = sheet('PRINT-IN-PLACE HINGE · DETAIL', 'same hinge on all three sizes · 2 positions: 0° and 35°', 4, total)
    axA = view(fig, [0.05, 0.14, 0.42, 0.78], (E.YH - 22, E.YH + 16), (-3, 34), 'SECTION A–A  along the hinge axis, as printed (scale ≈ 6:1)')
    for m, col, alpha in [(P, LN, 0.9), (L, ACC, 0.9)]:
        s = m.section(plane_origin=[0, 0, E.H['z']], plane_normal=[0, 0, 1])
        pl = s.to_planar(to_2D=np.array([[0, 1, 0, 0], [1, 0, 0, 0], [0, 0, 1, -E.H['z']], [0, 0, 0, 1]], float))[0]
        for poly in pl.polygons_full:
            x, y = poly.exterior.xy; axA.fill(x, y, color=col, alpha=0.18, lw=0); axA.plot(x, y, color=col, lw=0.8)
            for h in poly.interiors: x, y = h.xy; axA.plot(x, y, color=col, lw=0.8)
    yc = E.YH
    axA.axhline(0, color=HL, lw=0.8); axA.text(yc - 21, -2.2, 'print bed', fontsize=7, color=HL)
    dim(axA, (yc - 2.5, 30), (yc + 2.5, 30), 2.5, 'Ø5 pin')
    dim(axA, (yc - 6, 0), (yc + 6, 0), -2, 'Ø12 leg barrel', fs=7)
    for (y0, y1, xx, t) in [(0, 18, yc + 9.5, '18 leg barrel'), (18.8, 28, yc + 9.5, '9.2 rack barrel')]:
        axA.annotate('', (xx, y0), (xx, y1), arrowprops=dict(arrowstyle='<->', color=DM, lw=0.6, shrinkA=0, shrinkB=0))
        axA.plot([yc + 6, xx + 0.5], [y0, y0], color=DM, lw=0.4); axA.plot([yc + 5, xx + 0.5], [y1, y1], color=DM, lw=0.4)
        axA.text(xx + 0.8, (y0 + y1)/2, t, color=DM, fontsize=7.5, va='center')
    axA.text(yc - 21, 30.5, 'gaps: 0.7 round the pin · 0.8 on every 45° cone · 0.6 leg to rack\nnothing prints flat over a gap → no fusing', fontsize=7.5, color=ACC, va='top')
    axA.text(yc - 12, 24, 'rack barrel Ø10\n(fixed, with the pin)', fontsize=7, color=LN, ha='right')
    axA.text(yc - 12, 9, 'leg barrel\n(moves)', fontsize=7, color=ACC, ha='right')
    axA.text(yc - 5.5, 1.6, 'cone foot = end stop', fontsize=6.5, color=LN)
    # side: stop tab
    axS = view(fig, [0.52, 0.14, 0.42, 0.78], (-40, 25), (E.YH - 45, E.YH + 22), 'SECTION B–B  through the leg barrel: the 35° stop')
    for m, M, col, ls in [(P, np.eye(4), LN, '-'), (L, np.eye(4), HL, '--'), (L, E.rot(E.PSI), ACC, '-')]:
        s = m.copy().apply_transform(M).section(plane_origin=[9, 0, 0], plane_normal=[1, 0, 0])
        if s is None: continue
        for e in s.discrete: axS.plot(e[:, 2], e[:, 1], color=col, lw=0.8, ls=ls)
    axS.add_patch(Arc((E.H['z'], E.YH), 50, 50, theta1=-90 - 35, theta2=-90, color=ACC, lw=0.8))
    axS.text(E.H['z'] - 20, E.YH - 30, '35°', color=ACC, fontsize=9)
    axS.text(-38, E.YH + 17, 'dashed: folded (0°) · solid orange: open (35°)\nthe stop tab lands flat on the end wall;\nthe rack\'s weight presses it shut', fontsize=7, color=LN, va='top')
    pdf.savefig(fig, facecolor=BGC); plt.close(fig)
    # SPEC SHEET
    fig, ax0 = sheet('SPECIFICATION · PRINT SETTINGS · TOLERANCES', 'values from the verification reports in 3d-models/', 5, total)
    R = {N: json.load(open(MD + f'right_fixed_rack_{N}card_kickstand_report.json')) for N in (3, 5, 6)}
    rows = [('Model', '3-card', '5-card', '6-card'), ('File', *[f'right_fixed_rack_{N}card_kickstand_PRINT.stl' for N in (3, 5, 6)]),
            ('Rack height (mm)', '132', '242', '297'), ('Ledges · pitch · step', '3 · 55 · 4.6', '5 · 55 · 4.6', '6 · 55 · 4.6'),
            ('Hinge axis height (mm)', *[f"{R[N]['hinge_y']:.0f}" for N in (3, 5, 6)]), ('Lean when open', *[f"{R[N]['lean_deg']}°" for N in (3, 5, 6)]),
            ('Stand open W × D × H (mm)', *[' × '.join(f'{v:.0f}' for v in R[N]['standing_W_D_H_mm']) for N in (3, 5, 6)]),
            ('Tip angle fwd / back / side (loaded)', *[f"{R[N]['tip_front_deg']}° / {R[N]['tip_rear_deg']}° / {R[N]['tip_sideways_deg']}°" for N in (3, 5, 6)]),
            ('Printed mass (PLA, est.)', *[f"{R[N]['mass_stand_g']} g" for N in (3, 5, 6)]), ('Loaded mass (cars + cards)', *[f"{R[N]['mass_loaded_g']} g" for N in (3, 5, 6)])]
    y = 262
    for i, row in enumerate(rows):
        for j, c in enumerate(row):
            ax0.text(20 + [0, 95, 190, 285][j], y, c, fontsize=7.4 if i else 8, weight='bold' if i == 0 or j == 0 else 'normal', color=ACC if i == 0 else LN)
        ax0.plot([18, 400], [y - 3.5, y - 3.5], color=HL, lw=0.3); y -= 10
    notes = ['PRINT SETTINGS', '• Orientation: as in the STL, end wall flat on the bed. No supports, no brim needed.', '• PLA, 0.2 mm layers, 3 walls, 15 % infill. Keep the hinge region at ≤ 40 mm/s outer wall.',
             '• Do not use "detect thin walls" gap fill in the hinge; first layer must not be over-squished (elephant foot closes the 0.8 mm foot gap).',
             '• After printing: hold the rack, rotate the leg gently 0° → 35° a few times to break the hinge free.', '',
             'TOLERANCES / CLEARANCES', '• Pin Ø5.0 in bore Ø6.4: 0.7 mm radial.   • 45° cone faces: 0.8 mm normal gap.   • Leg strip to rack back: 0.6 mm.',
             '• Leg axial play on the pin: about 1.1 mm / 1.6 mm.   • Smallest gap anywhere: 0.6 mm; no contact with any 0.45 mm shift.',
             '• Leg range: free 0°–34.8°, hard stop at 35.0°; cannot fold past 0° (rests on the rack).', '',
             'USE', '• Unfold the leg to its stop and stand the rack on its bottom ledge. Slide each card in from the open end until it meets the 28 mm stop.',
             '• Fold the leg flat to store or ship: the whole stand is then 30–45 mm thick.']
    yy = 150
    for t in notes:
        ax0.text(20, yy, t, fontsize=7.6 if t.isupper() else 7.2, weight='bold' if t.isupper() else 'normal', color=ACC if t.isupper() else LN); yy -= 8
    pdf.savefig(fig, facecolor=BGC); plt.close(fig)
print('ok')
