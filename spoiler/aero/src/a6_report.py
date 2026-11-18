"""Aero test, step 6: write aero/README.md from aero/results/aero_results.json (no numbers typed by hand).
Run from spoiler/:  python3 aero/src/a6_report.py"""
import json
A = json.load(open('aero/results/aero_results.json')); n, w, d = A['no_spoiler'], A['with_spoiler'], A['delta']
sp = A.get('spoiler_alone', {})
def sg(x, f='{:.0f}'): return ('+' if x >= 0 else '−') + f.format(abs(x))
def pct(a, b): return 100.0 * (b - a) / abs(a) if a else float('nan')
r100, r130, r160 = A['at_100'], A['at_130'], A['at_160']
rows = [('Drag coefficient Cd', f"{n['Cd']:.3f}", f"{w['Cd']:.3f}", f"{sg(d['Cd'], '{:.3f}')} ({sg(pct(n['Cd'], w['Cd']), '{:.1f}')} %)"),
        ('Drag at 100 km/h', f"{n['drag_N']:.0f} N", f"{w['drag_N']:.0f} N", f"{sg(d['drag_N'])} N"),
        ('Total lift coefficient Cl', f"{n['Cl']:+.3f}", f"{w['Cl']:+.3f}", sg(d['Cl'], '{:.3f}')),
        ('Lift, front axle, 100 km/h', f"{n['lift_front_N']:+.0f} N", f"{w['lift_front_N']:+.0f} N", f"{sg(d['lift_front_N'])} N"),
        ('Lift, rear axle, 100 km/h', f"{n['lift_rear_N']:+.0f} N", f"{w['lift_rear_N']:+.0f} N", f"{sg(d['lift_rear_N'])} N"),
        ('Friction share of drag', f"{100 * n['drag_friction_N'] / n['drag_N']:.0f} %", f"{100 * w['drag_friction_N'] / w['drag_N']:.0f} %", '')]
tab = '| | Without spoiler | With spoiler | Change |\n|---|---|---|---|\n' + '\n'.join(f'| {a} | {b} | {c} | {e} |' for a, b, c, e in rows)
spd = '| Speed | Drag without → with | Front-axle lift without → with | Rear-axle lift without → with |\n|---|---|---|---|\n'
for kmh, r in ((100, r100), (130, r130), (160, r160)):
    spd += (f"| {kmh} km/h | {r['no_spoiler']['drag_N']:.0f} → {r['with_spoiler']['drag_N']:.0f} N | "
            f"{r['no_spoiler']['lift_front_N']:+.0f} → {r['with_spoiler']['lift_front_N']:+.0f} N | {r['no_spoiler']['lift_rear_N']:+.0f} → {r['with_spoiler']['lift_rear_N']:+.0f} N |\n")
conv = '| Iteration | Cd without | Cd with | Rear-axle Cl without | Rear-axle Cl with |\n|---|---|---|---|---|\n'
for t in sorted(n['convergence'], key=float):
    conv += f"| {t} | {n['convergence'][t]['Cd']:.4f} | {w['convergence'][t]['Cd']:.4f} | {n['convergence'][t]['Clr']:+.4f} | {w['convergence'][t]['Clr']:+.4f} |\n"
method = open('aero/src/report_method.md').read()
md = f"""# Wind test (CFD): the car with and without the roof spoiler

A computer simulation of air flowing over the car at **100 km/h**, once without the spoiler and once with the final
spoiler fitted, everything else identical. It answers: what does the spoiler do to drag, and to lift on each axle?

## Results

{tab}

Lift is positive upwards: a negative change is extra downforce. Drag and lift grow with the square of the speed:

{spd}
**The spoiler on its own** (the forces on its surface alone): drag {sp.get('drag_N', float('nan')):+.1f} N, lift {sp.get('lift_N', float('nan')):+.1f} N at 100 km/h.
Most of the change comes from how the spoiler alters the flow over the roof, the rear window and the tailgate, not from the force on the part itself.

## What it means

- **Rear-axle lift drops by {abs(d['lift_rear_N']):.0f} N at 100 km/h** ({abs(r130['with_spoiler']['lift_rear_N'] - r130['no_spoiler']['lift_rear_N']):.0f} N at 130 km/h): the rear axle goes from slight lift to downforce.
  The front axle hardly changes ({sg(d['lift_front_N'])} N), so the aerodynamic balance moves rearwards, which makes the car steadier at speed.
- **Drag rises by {d['drag_N']:.0f} N at 100 km/h ({sg(pct(n['Cd'], w['Cd']), '{:.0f}')} %)**: the kicked-up lip throws the roof flow higher, so the wake behind
  the tailgate is taller (see `results/midplane_speed.png`). That costs about {d['drag_N'] * A['U_ms'] / 1000:.1f} kW more power at 100 km/h.
  This is the usual trade-off of a ducktail lip: rear downforce for some drag.
- **Load on the part itself is small:** the airflow pushes the spoiler down onto the roof ({sp.get('lift_N', 0):+.0f} N) and back ({sp.get('drag_N', 0):+.1f} N)
  at 100 km/h, about {abs(sp.get('lift_N', 0)) * 2.56:.0f} N down and {abs(sp.get('drag_N', 0)) * 2.56:.0f} N back at 160 km/h. That is tiny for VHB tape, and it presses the part
  onto the tape rather than pulling it off.
- **How sure:** without the spoiler the steady solution keeps a small wake oscillation: between iterations 900 and 1500,
  Cd moves within {n['band']['Cd'][0]:.3f}–{n['band']['Cd'][1]:.3f} and the rear-axle lift coefficient within {n['band']['Clr'][0]:+.3f} to {n['band']['Clr'][1]:+.3f}. With the spoiler it is steadier.
  Both changes are several times larger than that band.

## Pictures

- `results/midplane_speed.png`: air speed on the car's centre line, around the roof and tailgate, without and with the spoiler.
- `results/cp_surface.png`: surface pressure on the car (blue = suction, red = pressure), without and with the spoiler.
- `results/forces_summary.png`: drag and axle lift at 100 and 130 km/h.
- `results/convergence.png`: the coefficients every 300 iterations; they must settle before the numbers count.

## Convergence

{conv}
{method}
## How far to trust it

- **Use the changes, not the absolute values.** The car is our modelled Polo-class body, not a scan or VW's CAD: the
  underbody is smooth, the wheel arches simple, there is no engine bay airflow or radiator. A real car has more drag
  and more lift than this model. The difference with and without the spoiler is the useful number.
- Steady RANS with a k-ω SST model on one mesh of 0.74–0.87 M cells (half car). That is a typical "first look" setup;
  a finer mesh, a mesh-independence study, or transient simulation could move the numbers by a few per cent.
- No wind tunnel or road test has been done. Confirm on the car (for example, coast-down or a tuft test on the rear window).

## Files

| File | What it is |
|---|---|
| `results/aero_results.json` | All numbers above, plus the convergence history |
| `results/*.png` | The pictures |
| `src/a1_geometry.py` | CFD surfaces in metres (car body, original body, spoiler, mirrors, wheels) |
| `src/a2_case.py` | Writes the OpenFOAM case for one variant |
| `src/a3_run.sh`, `src/a3_solve.sh` | Mesh and solve; solve again on an existing mesh |
| `src/foamread.py`, `src/a4_forces.py` | Read the OpenFOAM results and integrate the forces |
| `src/a5_figures.py`, `src/a6_report.py` | Figures and this report |

To rerun from `spoiler/` (about 1 hour on 4 cores): `python3 aero/src/a1_geometry.py`, then for each variant
`bash aero/src/a3_run.sh no_spoiler` / `with_spoiler` and `python3 aero/src/a4_forces.py <variant>`, then
`python3 aero/src/a5_figures.py` and `python3 aero/src/a6_report.py`. The raw OpenFOAM cases (several GB) stay in
`aero/out/`, which is not in git.
"""
open('aero/README.md', 'w').write(md)
print(md[:1500])
