"""Slicing-based printability check: unsupported area per layer, with a lookback window for the intended 0.5 mm print-in-place gaps."""
import numpy as np, trimesh
import shapely.geometry as sg
import shapely.ops as so


def _slice(m, z):
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if s is None:
        return None
    polys = sorted([sg.Polygon(e[:, :2]) for e in s.discrete if len(e) > 2], key=lambda p: -p.area)
    acc = None
    for p in polys:
        acc = p if acc is None else (acc.difference(p) if acc.contains(p) else acc.union(p))
    return acc


def analyse(m, layer=0.4, reach=0.6, gap_window=1.0):
    """returns dict: worst true overhang (area beyond `reach` mm of material within the previous `gap_window` mm), worst gap-bridged area, layers."""
    zs = np.arange(layer / 2, m.bounds[1][2], layer)
    sl = [_slice(m, z) for z in zs]
    n_win = int(round(gap_window / layer))
    true_worst, gap_worst, span_worst = (0.0, 0.0), (0.0, 0.0), (0.0, 0.0, 0.0)
    for i in range(1, len(zs)):
        cur = sl[i]
        if cur is None or sl[i - 1] is None and i == 1:
            continue
        prev = sl[i - 1]
        near = so.unary_union([s for s in sl[max(0, i - n_win):i] if s is not None]) if i else None
        if cur is None:
            continue
        reg = cur.difference(near.buffer(reach)) if near is not None else cur
        if reg.area > 1.0:
            lo, hi = 0.0, 40.0
            for _ in range(10):
                mid = (lo + hi) / 2
                if reg.buffer(-mid).is_empty: hi = mid
                else: lo = mid
            if 2 * hi > span_worst[0]: span_worst = (2 * hi, zs[i], reg.area)
        a_prev = cur.difference(prev.buffer(reach)).area if prev is not None else cur.area
        a_win = cur.difference(near.buffer(reach)).area if near is not None else cur.area
        if a_win > true_worst[0]:
            true_worst = (a_win, zs[i])
        bridged = max(a_prev - a_win, 0.0)
        if bridged > gap_worst[0]:
            gap_worst = (bridged, zs[i])
    return dict(true_overhang_mm2=round(true_worst[0], 1), at_z=round(float(true_worst[1]), 1), gap_bridged_mm2=round(gap_worst[0], 1), gap_at_z=round(float(gap_worst[1]), 1),
                max_unsupported_span_mm=round(span_worst[0], 1), span_at_z=round(float(span_worst[1]), 1), span_area=round(span_worst[2], 1), height=round(float(m.bounds[1][2]), 1), layers=len(zs))


if __name__ == "__main__":
    import sys, side3_cad as C
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    R = C.R3(N)
    for nm, m in (("frame", C.print_frame(R)), ("swing_R", C.print_swing(R, 1))):
        print(nm, analyse(m))
