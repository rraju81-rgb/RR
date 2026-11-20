"""v10 step 2: cut each cored section into its front and rear part, and make the joints.
  Span seams (x = -216.67 and +216.67), front segment and rear segment each: two dowel-pin holes and between them a
  30-degree TONGUE on the side part and a matching GROOVE in the centre part. In print these faces stand upright, so the
  holes are teardrop-shaped (pointed towards the top of the print) and the tongue/groove ends taper at 45 degrees.
  Front/rear cuts (one per section): both parts print standing on this face, so both faces get a GROOVE, and loose
  double-sided SPLINES sit between them, with dowel pins between and beyond the splines (round holes, pointed ends).
Writes v10/assembled/*.stl (parts, splines and pins in place, car coordinates), v10/out/pin_local.stl, joints.json.
Run from spoiler/:  python3 v10/src/p2_parts.py"""
import sys, os, json; sys.path.insert(0, 'v10/src'); sys.path.insert(0, 'v6/src')
import numpy as np, trimesh, manifold3d as mf
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
from shapely.geometry import Polygon
from matplotlib.path import Path as MPath
from bowtie import tomf, totm
from check import report
from p1_core import weld, keep_main, clean_written, decimate_clean, written_folds
from layout import (OUT, ASM, XS, SECTIONS, chord_plane, part_id, IDS, STEM, SEC, HALF_OF, CHAMFER_DEG, TONGUE_BASE, TONGUE_H,
                    CLEAR, GROOVE_EXTRA, END_DEG, MIN_SKIN_TONGUE, PIN_D, HOLE_D, HOLE_DEPTH, PIN_L, HOLE_CHAMFER, MIN_SKIN_PIN,
                    PIN_GAP, CORNER_KEEP, C0)
TAN = np.tan(np.radians(CHAMFER_DEG)); TE = np.tan(np.radians(END_DEG)); CLEAR_END = 0.30
Y = np.array([0.0, 1.0, 0.0])

class Frame:
    """seam plane through p0 with unit normal n (from part A to part B); in-plane axes e1 = n x Y and e2 = Y"""
    def __init__(self, p0, n):
        self.p0 = np.asarray(p0, float); self.n = np.asarray(n, float) / np.linalg.norm(n)
        self.e2 = Y.copy(); self.e1 = np.cross(self.n, Y); self.e1 /= np.linalg.norm(self.e1)
    def to2(self, P):
        d = np.asarray(P) - self.p0; return np.column_stack([d @ self.e1, d @ self.e2])
    def to3(self, uv, h=0.0):
        uv = np.atleast_2d(uv); return self.p0 + uv[:, :1] * self.e1 + uv[:, 1:2] * self.e2 + np.atleast_1d(h)[:, None] * self.n

def seam_profile(m, fr, side):
    """largest polygon of m's section just inside the seam face (side -1: part A, +1: part B), in (u, v)"""
    s = m.section(plane_origin=fr.p0 + side * 0.05 * fr.n, plane_normal=fr.n)
    polys = sorted([Polygon(fr.to2(d)).buffer(0) for d in s.discrete], key=lambda p: -p.area)
    return polys[0]

def midline(P, h=0.05):
    """the skin's midline (u, v) from low u to high u, the skin thickness along it, and arc length"""
    u0, v0, u1, v1 = P.bounds
    nu, nv = int((u1 - u0) / h) + 8, int((v1 - v0) / h) + 8
    uu, vv = np.meshgrid(u0 - 4 * h + np.arange(nu) * h, v0 - 4 * h + np.arange(nv) * h, indexing='ij')
    mask = MPath(np.asarray(P.exterior.coords)).contains_points(np.column_stack([uu.ravel(), vv.ravel()])).reshape(uu.shape)
    D = ndi.distance_transform_edt(mask) * h
    sk = skeletonize(mask)
    iu, iv = np.nonzero(sk); us = uu[iu, 0]; bins = np.floor((us - u0) / 0.5).astype(int)
    pts, th = [], []
    for b in np.unique(bins):                                            # topmost skeleton point per 0.5 mm (legs branch off below)
        k = np.flatnonzero(bins == b); j = k[np.argmax(iv[k])]
        pts.append((uu[iu[j], 0], vv[0, iv[j]])); th.append(2 * D[iu[j], iv[j]])
    pts = np.array(pts); th = np.array(th)
    sm = np.column_stack([ndi.uniform_filter1d(pts[:, 0], 9, mode='nearest'), ndi.uniform_filter1d(pts[:, 1], 9, mode='nearest')])
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(sm, axis=0), axis=1))]
    return sm, ndi.minimum_filter1d(th, 5), s

def resample(pts, s, s0, s1, n):
    t = np.linspace(s0, s1, n)
    return np.column_stack([np.interp(t, s, pts[:, 0]), np.interp(t, s, pts[:, 1])])

def frames2(q):
    t = np.gradient(q, axis=0); t /= np.linalg.norm(t, axis=1, keepdims=True)
    return np.column_stack([-t[:, 1], t[:, 0]])

def prism(fr, pts, s, levels, direction, n=200):
    """closed solid swept along the midline; levels [(h, width, (s_start, s_end)), ...] from one side to the other, h
    measured along direction*n from the seam face"""
    rails = []
    for h, w, (sa, sb) in levels:
        q = resample(pts, s, sa, sb, n); nn = frames2(q)
        hh = np.full(n, direction * h)
        rails.append((fr.to3(q + nn * (w / 2), hh), fr.to3(q - nn * (w / 2), hh)))
    ring = [r[0] for r in rails] + [r[1] for r in rails[::-1]]
    K = len(ring); V = np.vstack(ring); F = []
    for i in range(n - 1):
        for k in range(K):
            k2 = (k + 1) % K; a0, a1, b0, b1 = k * n + i, k2 * n + i, k * n + i + 1, k2 * n + i + 1
            F += [[a0, b0, b1], [a0, b1, a1]]
    for i in (0, n - 1):
        for k in range(1, K - 1): F.append([i, k * n + i, (k + 1) * n + i] if i == 0 else [i, (k + 1) * n + i, k * n + i])
    m = trimesh.Trimesh(V, np.array(F), process=True)
    if m.volume < 0: m.invert()
    assert m.is_watertight and m.is_winding_consistent and m.is_volume, 'prism is not a closed solid'
    return m

SMALL = (3.0, 1.7)                    # smaller tongue for the thin front band (skin 6-8 mm): same 30-degree flanks

def tongue(fr, pts, s, t0, t1, direction, size=(TONGUE_BASE, TONGUE_H)):
    b, h = size; wt = b - 2 * h * TAN
    return prism(fr, pts, s, [(-0.5, b + 2 * 0.5 * TAN, (t0 - 0.5 * TE, t1 + 0.5 * TE)),
                              (h, wt, (t0 + h * TE, t1 - h * TE))], direction)

def groove(fr, pts, s, t0, t1, direction, size=(TONGUE_BASE, TONGUE_H)):
    """direction: into the female part"""
    b, h = size; gd = h + GROOVE_EXTRA; gm = b + 2 * CLEAR
    return prism(fr, pts, s, [(-0.5, gm + 2 * 0.5 * TAN, (t0 - CLEAR_END - 0.5 * TE, t1 + CLEAR_END + 0.5 * TE)),
                              (gd, gm - 2 * gd * TAN, (t0 - CLEAR_END + gd * TE, t1 + CLEAR_END - gd * TE))], direction)

def spline(fr, pts, s, t0, t1):
    wt = TONGUE_BASE - 2 * TONGUE_H * TAN; de = TONGUE_H * TE
    return prism(fr, pts, s, [(-TONGUE_H, wt, (t0 + de, t1 - de)), (0.0, TONGUE_BASE, (t0, t1)), (TONGUE_H, wt, (t0 + de, t1 - de))], 1.0)

def _place(M, R, t):
    return M.transform(np.column_stack([R, t]))

def hole_round(fr, uv):
    """vertical-in-print pin hole through the seam: round, 30-degree lead-in at the face, pointed ends (no bridge)"""
    r = HOLE_D / 2; lead = HOLE_CHAMFER / TAN
    prof = np.array([[0, -HOLE_DEPTH - r], [r, -HOLE_DEPTH], [r, -lead], [r + HOLE_CHAMFER, 0], [r, lead], [r, HOLE_DEPTH],
                     [0, HOLE_DEPTH + r]], float)
    M = mf.Manifold.revolve(mf.CrossSection([prof], mf.FillRule.EvenOdd), 48)
    R = np.column_stack([fr.e2, fr.e1, fr.n])                             # proper rotation: local z -> n
    return _place(M, R, fr.to3(uv)[0])

def hole_teardrop(fr, uv, up):
    """horizontal-in-print pin hole: teardrop section pointed towards `up` (45-degree roof), flat ends, lead-in at the face"""
    r = HOLE_D / 2; lead = HOLE_CHAMFER / TAN
    a = np.linspace(0.25 * np.pi, 1.75 * np.pi, 41)                       # circle from +45 round to -45 degrees ...
    poly = np.vstack([[r * np.sqrt(2), 0.0], np.column_stack([r * np.cos(a), r * np.sin(a)])])   # ... and the tip at +x
    body = mf.CrossSection([poly], mf.FillRule.EvenOdd).extrude(2 * HOLE_DEPTH).translate([0, 0, -HOLE_DEPTH])
    prof = np.array([[0, -lead], [r, -lead], [r + HOLE_CHAMFER, 0], [r, lead], [0, lead]], float)
    M = body + mf.Manifold.revolve(mf.CrossSection([prof], mf.FillRule.EvenOdd), 48)
    up = np.asarray(up, float); up = up - (up @ fr.n) * fr.n; up /= np.linalg.norm(up)
    R = np.column_stack([up, np.cross(fr.n, up), fr.n])                   # local x -> up, local z -> n (det +1)
    return _place(M, R, fr.to3(uv)[0])

def pin_part():
    r = PIN_D / 2; ch = 0.4
    prof = np.array([[0, 0], [r - ch, 0], [r, ch], [r, PIN_L - ch], [r - ch, PIN_L], [0, PIN_L]], float)
    return totm(mf.Manifold.revolve(mf.CrossSection([prof], mf.FillRule.EvenOdd), 64))

def runs_of(ok, s):
    r = np.split(np.arange(len(ok)), np.flatnonzero(np.diff(ok.astype(int))) + 1)
    r = [x for x in r if ok[x[0]]]
    return sorted(r, key=lambda x: -(s[x[-1]] - s[x[0]]))

def wall_ok(parts, fr, uv, need=1.6):
    """thinnest wall round a hole at uv, along its depth, in both parts (circles of growing radius must stay inside)"""
    a = np.linspace(0, 2 * np.pi, 36, endpoint=False); dep = np.linspace(1.0, HOLE_DEPTH - 0.3, 12)
    w_min = 9.0
    for m, side in parts:
        for wall in np.arange(0.4, 3.01, 0.2):
            rr = HOLE_D / 2 + wall
            P = [fr.to3(np.column_stack([uv[0] + rr * np.cos(a), uv[1] + rr * np.sin(a)]), np.full(len(a), side * d)) for d in dep]
            if not m.contains(np.vstack(P)).all(): w_min = min(w_min, wall - 0.2); break
    return w_min >= need, w_min

if __name__ == '__main__':
    os.makedirs(ASM, exist_ok=True)
    for f in os.listdir(ASM): os.remove(f'{ASM}/{f}')
    cored = {sec: trimesh.load(f'{OUT}/cored_{sec}.stl') for sec, _, _ in SECTIONS}
    # 1. cut each section into its front and rear part
    part = {}
    for sec, x0, x1 in SECTIONS:
        n, d = chord_plane(sec); M = tomf(cored[sec])
        part[part_id(sec, 'rear')] = M.trim_by_plane(list(n), d)
        part[part_id(sec, 'front')] = M.trim_by_plane(list(-n), -d)
    ops = {pid: {'add': [], 'cut': []} for pid in IDS}
    loose_pins, loose_splines, rep = [], [], {'span': {}, 'chord': {}}
    tm = {pid: totm(part[pid]) for pid in IDS}
    foot = HOLE_D / 2 + HOLE_CHAMFER + 1.0
    # 2. span seams: tongue on the side part (L: P1/P2, R: P5/P6), groove in the centre part
    for xs_, side_sec in ((-XS, 'L'), (XS, 'R')):
        fr = Frame([xs_, 0.0, 0.0], [1.0, 0.0, 0.0])                       # n = +x: A on the left, B on the right
        for half in ('front', 'rear'):
            S_, C_ = part_id(side_sec, half), part_id('C', half)
            A, B = (S_, C_) if xs_ < 0 else (C_, S_)
            P = seam_profile(tm[A], fr, -1)
            pts, th, s = midline(P)                                       # u = z here (e1 = x cross y = z)
            zc = C0
            # keep CORNER_KEEP from the front/rear cut (u = z ~ 122 at this seam)
            okc = (pts[:, 0] < zc - CORNER_KEEP) if half == 'front' else (pts[:, 0] > zc + CORNER_KEEP)
            run = runs_of((th >= MIN_SKIN_PIN) & okc, s)[0]
            sa, sb = s[run[0]] + foot + 2.0, s[run[-1]] - foot - 2.0
            up = np.array([0, 0, 1.0]) if half == 'rear' else np.array([0, 0, -1.0])   # print up for this half
            gap = HOLE_D / 2 + HOLE_CHAMFER + PIN_GAP
            def find_pin(target, step):
                for k in range(40):
                    v = target + k * step
                    uv = resample(pts, s, v, v, 1)[0]
                    good, w = wall_ok([(tm[A], -1), (tm[B], +1)], fr, uv)
                    if good: return (v, uv, w)
                raise RuntimeError(f'span seam {xs_} {half}: no place for a pin')
            size = (TONGUE_BASE, TONGUE_H)
            if sb - sa > 2 * gap + 25:                                    # two pins, standard tongue between them
                pin_s = [find_pin(sa, +1.0), find_pin(sb, -1.0)]
                t0 = pin_s[0][0] + gap; t1 = pin_s[1][0] - gap
            else:                                                         # thin front band: one pin, small tongue in front of it
                pin_s = [find_pin(sb, -1.0)]
                okt = (th >= SMALL[0] + 3.0) & (s < pin_s[0][0] - gap)
                rt = runs_of(okt, s)[0]
                t0 = s[rt[0]] + 1.0; t1 = pin_s[0][0] - gap; size = SMALL
            under = th[(s >= t0) & (s <= t1)]
            need = MIN_SKIN_TONGUE if size[0] == TONGUE_BASE else SMALL[0] + 3.0
            assert t1 - t0 > 20 and under.min() >= need - 0.05, f'span seam {xs_} {half}: tongue {t1 - t0:.0f} mm, skin {under.min():.2f}'
            direction = +1.0 if S_ == A else -1.0                         # tongue points from the side part into the centre part
            ops[S_]['add'].append(tongue(fr, pts, s, t0, t1, direction, size))
            ops[C_]['cut'].append(groove(fr, pts, s, t0, t1, direction, size))
            for v, uv, w in pin_s:
                H = hole_teardrop(fr, uv, up); ops[A]['cut'].append(H); ops[B]['cut'].append(H)
                loose_pins.append(dict(center=fr.to3(uv)[0].tolist(), axis=fr.n.tolist()))
            rep['span']['%+.1f %s' % (xs_, half)] = dict(parts=[A, B], tongue_on=S_, groove_in=C_,
                pins_zy=[[round(float(v), 1) for v in uv] for _, uv, _ in pin_s], pin_walls_mm=[round(w, 1) for *_, w in pin_s],
                tongue_z=[round(float(np.interp(t, s, pts[:, 0])), 1) for t in (t0, t1)], tongue_length=round(float(t1 - t0), 1), tongue_size=list(size),
                skin_under_tongue_min=round(float(under.min()), 2))
            print('span %+.1f %-5s %s|%s: pins at z=%s (walls %s mm), tongue %.0f mm on %s' % (xs_, half, A, B,
                  [round(float(uv[0]), 1) for _, uv, _ in pin_s], [round(w, 1) for *_, w in pin_s], t1 - t0, S_), flush=True)
    # 3. front/rear cuts: groove in both faces, loose splines between pins
    for sec, x0, x1 in SECTIONS:
        n, d = chord_plane(sec)
        xm = 0.5 * (x0 + x1); p0 = np.array([xm, 0.0, (d - n[0] * xm) / n[2]])
        fr = Frame(p0, n)                                                  # A = front part, B = rear part
        A, B = part_id(sec, 'front'), part_id(sec, 'rear')
        P = seam_profile(tm[A], fr, -1)
        pts, th, s = midline(P)
        X3 = fr.to3(pts)[:, 0]                                             # x of each midline point
        okc = (np.abs(X3 - (-XS)) > CORNER_KEEP + foot) & (np.abs(X3 - XS) > CORNER_KEEP + foot)
        run = runs_of((th >= MIN_SKIN_PIN) & okc, s)[0]
        sa, sb = s[run[0]] + foot + 2.0, s[run[-1]] - foot - 2.0
        npin = 3 if sb - sa > 180 else 2
        targets = list(np.linspace(sa, sb, npin))
        pin_s = []
        for j, target in enumerate(targets):
            done = False
            for k in range(60):
                for sgn in ((+1,) if j == 0 else (-1,) if j == npin - 1 else (+1, -1)):
                    v = target + sgn * k * 1.0
                    uv = resample(pts, s, v, v, 1)[0]
                    good, w = wall_ok([(tm[A], -1), (tm[B], +1)], fr, uv)
                    if good: pin_s.append((v, uv, w)); done = True; break
                if done: break
            if not done: print(f'   chord {sec}: no good place near s={target:.0f}, pin dropped')
        assert len(pin_s) >= 2, f'chord seam {sec}: fewer than 2 pins'
        sp = []
        for (va, uva, _), (vb, uvb, _) in zip(pin_s[:-1], pin_s[1:]):
            t0 = va + HOLE_D / 2 + HOLE_CHAMFER + PIN_GAP; t1 = vb - HOLE_D / 2 - HOLE_CHAMFER - PIN_GAP
            under = th[(s >= t0) & (s <= t1)]
            if t1 - t0 < 25 or under.min() < MIN_SKIN_TONGUE:
                # shorten to the part of the stretch where the skin is thick enough
                okk = (th >= MIN_SKIN_TONGUE) & (s >= t0) & (s <= t1)
                rr = runs_of(okk, s)
                if not rr or s[rr[0][-1]] - s[rr[0][0]] < 25: continue
                t0, t1 = s[rr[0][0]] + 1.0, s[rr[0][-1]] - 1.0; under = th[(s >= t0) & (s <= t1)]
            ops[A]['cut'].append(groove(fr, pts, s, t0, t1, -1.0)); ops[B]['cut'].append(groove(fr, pts, s, t0, t1, +1.0))
            loose_splines.append(spline(fr, pts, s, t0, t1)); sp.append((t0, t1, float(under.min())))
        for v, uv, w in pin_s:
            H = hole_round(fr, uv); ops[A]['cut'].append(H); ops[B]['cut'].append(H)
            loose_pins.append(dict(center=fr.to3(uv)[0].tolist(), axis=fr.n.tolist()))
        rep['chord'][sec] = dict(parts=[A, B], plane_normal=[round(float(v), 4) for v in n], plane_d=round(float(d), 2),
            pins_x=[round(float(fr.to3(uv)[0][0]), 1) for _, uv, _ in pin_s], pin_walls_mm=[round(w, 1) for *_, w in pin_s],
            splines=[dict(length=round(t1 - t0, 1), x=[round(float(fr.to3(resample(pts, s, t, t, 1))[0][0]), 1) for t in (t0, t1)],
                          skin_min=round(mn, 2)) for t0, t1, mn in sp])
        print('chord %s %s|%s: pins at x=%s (walls %s), splines %s' % (sec, A, B, rep['chord'][sec]['pins_x'], rep['chord'][sec]['pin_walls_mm'],
              [s_['length'] for s_ in rep['chord'][sec]['splines']]), flush=True)
    # 4. finish the parts
    for pid in IDS:
        M = part[pid]
        for a in ops[pid]['add']: M = M + tomf(a)
        for cu in ops[pid]['cut']: M = M - (cu if isinstance(cu, mf.Manifold) else tomf(cu))
        try: base = keep_main(weld(totm(M)))
        except AssertionError: base = keep_main(totm(M))
        out, perc = decimate_clean(base, pid)
        nsx = written_folds(out, pid)
        print('   %s: %d faces -> %d (%.0f%%), folded faces in the written file: %d' % (pid, len(base.faces), len(out.faces), 100 * perc, nsx), flush=True)
        nb = len(out.split(only_watertight=False))
        out.export(f'{ASM}/{STEM[pid]}.stl')
        print(pid, STEM[pid], 'watertight', out.is_watertight, 'volume %.1f cm3' % (out.volume / 1000), 'bodies', nb, flush=True)
        assert nb == 1
    pin = pin_part(); pin.export(f'{OUT}/pin_local.stl')
    for i, sp_ in enumerate(loose_splines): sp_.export(f'{ASM}/v10_SPLINE_{i + 1:02d}.stl')
    for i, p in enumerate(loose_pins):                                    # pins in place (assembled view)
        a = np.asarray(p['axis']); c = np.asarray(p['center'])
        b1 = np.cross(a, Y); b1 /= np.linalg.norm(b1); b2 = np.cross(a, b1)
        T = np.eye(4); T[:3, :3] = np.column_stack([b1, b2, a]); T[:3, 3] = c - a * PIN_L / 2
        if np.linalg.det(T[:3, :3]) < 0: T[:3, 0] *= -1
        q = pin.copy(); q.apply_transform(T); q.export(f'{ASM}/v10_PIN_{i + 1:02d}.stl')
    rep['n_pins'] = len(loose_pins); rep['n_splines'] = len(loose_splines)
    rep['spline_lengths'] = [round(float(np.ptp(sp_.vertices @ np.r_[1.0, 0, 0])), 1) for sp_ in loose_splines]
    json.dump(rep, open(f'{OUT}/joints.json', 'w'), indent=1)
    print('pins: %d, splines: %d' % (len(loose_pins), len(loose_splines)))
