"""Webbing strap mesh (for renders / viewer only - the strap is sewn webbing).

The band follows a closed path in the XY plane: it wraps the strap pin,
runs out through the face slot as two layers and forms the pull loop.
Width (25 mm) is along Z.  Returns vertices, quad faces and UVs.
"""
from __future__ import annotations

import math
import numpy as np

import door_strap as ds


def _resample(pts, step):
    pts = np.asarray(pts, float)
    seg = np.linalg.norm(np.diff(np.vstack([pts, pts[:1]]), axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    total = s[-1]
    n = max(int(total / step), 16)
    t = np.linspace(0, total, n, endpoint=False)
    closed = np.vstack([pts, pts[:1]])
    x = np.interp(t, s, closed[:, 0])
    y = np.interp(t, s, closed[:, 1])
    return np.column_stack([x, y])


def _chaikin(pts, it=2):
    for _ in range(it):
        p = pts
        q = np.roll(p, -1, axis=0)
        pts = np.empty((2 * len(p), 2))
        pts[0::2] = 0.75 * p + 0.25 * q
        pts[1::2] = 0.25 * p + 0.75 * q
    return pts


def strap_path(pose_deg=ds.POSE_REST, loop_len=62.0, bend=1.0):
    """Closed centre-line of the webbing (LH unit, loop curls rearwards)."""
    t = ds.STRAP_T
    rc = ds.PIN_D / 2 + t / 2
    cx, cy = ds.lever_point(ds.STRAP_PIN_LF, pose_deg)
    rest_y = ds.lever_point(ds.STRAP_PIN_LF, ds.POSE_REST)[1]
    pull = rest_y - cy                         # loop moves out as pin moves in
    sx = ds.SLOT_X
    sy = ds.face_y(sx, 0) + ds.FACE_T / 2
    g = 1.4                                    # layer offset in the slot
    pts = []
    # wrap round the far side of the pin (0 -> 180 deg, CCW)
    for a in np.linspace(0, math.pi, 24):
        pts.append((cx + rc * math.cos(a), cy + rc * math.sin(a)))
    # leg B down to the slot
    pts += [(sx - g, sy + 2.6), (sx - g, sy - 2.6)]
    # outer loop: spine goes out (-Y) then bends rearwards (-X)
    spine = []
    straight = 6.0 + pull
    for u in np.linspace(0, 1, 40):
        if u < 0.25:
            k = u / 0.25
            spine.append((0.0, -2.6 - straight * k))
        else:
            k = (u - 0.25) / 0.75
            ang = bend * math.radians(70) * k          # bend angle
            r = loop_len / (bend * math.radians(70) + 1e-9)
            spine.append((-(r - r * math.cos(ang)),
                          -2.6 - straight - r * math.sin(ang)))
    spine = np.array(spine) + np.array([sx, sy])
    tang = np.gradient(spine, axis=0)
    tang /= np.linalg.norm(tang, axis=1)[:, None]
    nrm = np.column_stack([tang[:, 1], -tang[:, 0]])  # right-hand normal
    w = np.interp(np.linspace(0, 1, len(spine)), [0, 0.12, 0.45, 1.0],
                  [g, 2.2, 5.5, 6.5])
    side_b = spine + nrm * w[:, None] * (-1)
    side_a = spine + nrm * w[:, None]
    # make sure side_b is the -X side at the slot
    if side_b[0, 0] > side_a[0, 0]:
        side_a, side_b = side_b, side_a
    pts += [tuple(p) for p in side_b[1:]]
    # end cap (semicircle around the spine end)
    end, tdir = spine[-1], tang[-1]
    c0 = side_b[-1] - end
    for a in np.linspace(0, math.pi, 18)[1:-1]:
        # rotate c0 towards side_a through the tip direction
        ca, sa = math.cos(a), math.sin(a)
        v = c0 * ca + tdir * np.linalg.norm(c0) * sa
        pts.append(tuple(end + v))
    pts += [tuple(p) for p in side_a[::-1][:-1]]
    # leg A back up to the pin
    pts += [(sx + g, sy - 2.6), (sx + g, sy + 2.6)]
    return np.array(pts)


def strap_mesh(pose_deg=ds.POSE_REST, z_range=None, mirror=False,
               step=0.7):
    w = ds.STRAP_W
    t = ds.STRAP_T
    z0, z1 = z_range if z_range else (-w / 2, w / 2)
    path = _chaikin(_resample(strap_path(pose_deg), step * 2), 2)
    n = len(path)
    tang = np.roll(path, -1, axis=0) - np.roll(path, 1, axis=0)
    tang /= np.linalg.norm(tang, axis=1)[:, None]
    nrm = np.column_stack([-tang[:, 1], tang[:, 0]])
    seg = np.linalg.norm(np.diff(np.vstack([path, path[:1]]), axis=0), axis=1)
    u = np.concatenate([[0], np.cumsum(seg)[:-1]])
    outer = path - nrm * (t / 2)      # right-hand side = outside of the loop
    inner = path + nrm * (t / 2)
    V, UV, F = [], [], []
    # ring order per sample: outer-bottom, outer-top, inner-top, inner-bottom
    for i in range(n):
        for (p, z) in ((outer[i], z0), (outer[i], z1), (inner[i], z1),
                       (inner[i], z0)):
            V.append((p[0], p[1], z))
        UV += [(u[i] / 25.0, 0.0), (u[i] / 25.0, 1.0), (u[i] / 25.0, 1.0),
               (u[i] / 25.0, 0.0)]
    V = np.array(V)
    for i in range(n):
        j = (i + 1) % n
        a, b = 4 * i, 4 * j
        F.append((a + 0, b + 0, b + 1, a + 1))   # outer face
        F.append((a + 1, b + 1, b + 2, a + 2))   # top edge
        F.append((a + 2, b + 2, b + 3, a + 3))   # inner face
        F.append((a + 3, b + 3, b + 0, a + 0))   # bottom edge
    F = np.array(F)
    if mirror:
        V[:, 0] *= -1
        F = F[:, ::-1]
    return V, F, np.array(UV)


def write_obj(path, V, F, UV=None, name="strap"):
    with open(path, "w") as f:
        f.write(f"o {name}\n")
        for v in V:
            f.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")
        if UV is not None:
            for t in UV:
                f.write(f"vt {t[0]:.4f} {t[1]:.4f}\n")
        f.write("s 1\n")
        for q in F:
            if UV is not None:
                f.write("f " + " ".join(f"{k + 1}/{k + 1}" for k in q) + "\n")
            else:
                f.write("f " + " ".join(str(k + 1) for k in q) + "\n")
