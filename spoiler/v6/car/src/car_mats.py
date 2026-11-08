"""Material zones on the procedural body, by face position/normal (car-relative s = from front bumper, h = height)."""
import numpy as np
from matplotlib.path import Path
from car_body import s_of, h_of, PLAN_CAB, tumble_cab
MAT = ['paint', 'glass', 'trim_black', 'plastic_black', 'tail_lamp', 'head_lamp', 'grille_chrome', 'rev_lamp']
def plan_halfwidth(poly, s):
    P = np.asarray(poly)
    # max |x| of the polygon at each s (sample the outline)
    ss = P[:, 1]; xx = np.abs(P[:, 0])
    bins = np.linspace(ss.min(), ss.max(), 400); hw = np.zeros(len(bins))
    for i, b in enumerate(bins):
        m = np.abs(ss - b) < (bins[1] - bins[0]) * 1.5
        hw[i] = xx[m].max() if m.any() else 0
    return np.interp(s, bins, hw)
DLO = Path(np.array([(1262, 990), (1420, 1105), (1600, 1235), (1790, 1365), (1872, 1402), (2300, 1412), (2800, 1404), (3150, 1386),
                     (3225, 1318), (3290, 1200), (3332, 1072), (3338, 1040), (2500, 1012), (1900, 996)]))
def classify(m):
    c = m.triangles_center; n = m.face_normals
    x, y, z = c[:, 0], c[:, 1], c[:, 2]; s = s_of(z); h = h_of(y); ax = np.abs(x)
    mat = np.zeros(len(c), np.int32)
    cab_hw = plan_halfwidth(PLAN_CAB, s) * tumble_cab(h, s)
    # windshield (faces looking forward/up, inside the A-pillars)
    ws = (s > 1150) & (s < 1895) & (h > 975) & (h < 1402 - 0.00011 * ax ** 2) & (-n[:, 2] > 0.40) & (ax < cab_hw - 70)
    # rear window (faces looking rearward, inside the D-pillars), under/behind the spoiler
    rw = (s > 3585) & (s < 3810) & (h > 1018) & (h < 1360) & (n[:, 2] > 0.30) & (ax < cab_hw - 95)
    # side glass inside the DLO outline, faces looking sideways
    side = (np.abs(n[:, 0]) > 0.42) & DLO.contains_points(np.column_stack([s, h]))
    bpil = side & (np.abs(s - (2228 + (h - 1000) * 0.10)) < 38)
    mat[ws | rw | (side & ~bpil)] = 1
    mat[bpil] = 2
    # DLO surround strip (black seal) just outside the side glass top/rear
    # tail lamps: rear corners
    tl_rear = (s > 3760) & (ax > 500) & (h > 868 + (845 - ax) * 0.07) & (h < 1004 - (845 - ax) * 0.16) & (n[:, 2] > 0.12)
    tl_side = (s > 3690) & (h > 880 + (3971 - s) * 0.03) & (h < 1003) & (np.abs(n[:, 0]) > 0.45)
    tl = tl_rear | tl_side
    mat[tl] = 4
    # clear reverse-lamp strip in the inner part of each tail lamp
    mat[tl_rear & (ax < 640) & (h < 948)] = 7
    # head lamps: front corners, below the hood edge
    hl = (s < 420) & (ax > 300) & (ax < 790) & (h > 650 + (ax - 300) * 0.07) & (h < 758 + (ax - 300) * 0.03) & ((-n[:, 2] > 0.15) | (np.abs(n[:, 0]) > 0.5))
    mat[hl & (mat == 0)] = 5
    # grille band + lower intake (black), chrome bar
    gr = (s < 170) & (ax < 300) & (h > 652) & (h < 742) & (-n[:, 2] > 0.3)
    mat[gr] = 3
    mat[(s < 170) & (ax < 300) & (np.abs(h - 700) < 6) & (-n[:, 2] > 0.3)] = 6
    li = (s < 260) & (h > 262) & (h < 470) & (ax < 560 - (470 - h) * 0.35) & (-n[:, 2] > 0.25)
    mat[li] = 3
    # rear lower diffuser + sills/underbody
    mat[(s > 3800) & (h < 372 + 0.0 * ax) & (n[:, 2] > -0.3)] = 3
    mat[(n[:, 1] < -0.6) & (h < 230)] = 3
    return mat
