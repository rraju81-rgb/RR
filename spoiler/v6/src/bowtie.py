"""Bow-tie key geometry shared by s4_parts.py and s8_drawings.py."""
import numpy as np, trimesh, manifold3d as mf
from shapely.geometry import Polygon
XS = 650.0 / 3.0                  # seam planes x = +-216.67 mm
# bow-tie key parameters (mm)
L, W, N = 56.0, 24.0, 12.0        # length across seam, lobe width, neck width
R_CVX, R_CCV = 2.0, 3.0           # corner radii (lobe corners / neck)
DP = 6.5                          # pocket depth into the part (from underside plane)
CL = 0.15                         # key-to-pocket clearance per side
CF = 0.25                         # glue gap at the pocket floor
KEY_Z = [127.0, 164.0]            # key centres along the chord (z), both seams
def tomf(m):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
def totm(M):
    g = M.to_mesh(); V = np.asarray(g.vert_properties[:, :3], np.float64); F = np.asarray(g.tri_verts).copy()
    a = np.asarray(g.merge_from_vert); b = np.asarray(g.merge_to_vert)
    if len(a): r = np.arange(len(V)); r[a] = b; F = r[F]
    t = trimesh.Trimesh(V, F, process=True)
    return t
def bowtie_outline():
    P = Polygon([(0, N/2), (L/2, W/2), (L/2, -W/2), (0, -N/2), (-L/2, -W/2), (-L/2, W/2)])
    P = P.buffer(-R_CVX, join_style=1).buffer(R_CVX, join_style=1)      # round convex corners
    P = P.buffer(R_CCV, join_style=1).buffer(-R_CCV, join_style=1)      # round the concave neck
    return P.simplify(0.01)
def cs(poly):
    return mf.CrossSection([np.asarray(poly.exterior.coords)[:-1].astype(np.float64)], mf.FillRule.EvenOdd)
s2 = 1 / np.sqrt(2)
def pocket_local():
    P = bowtie_outline()
    M = cs(P).extrude(DP + 15.0).translate([0, 0, -15.0])               # w from -15 (outside) to DP
    M = M.trim_by_plane([-s2, 0, -s2], -(L / 2) * s2)                    # u + w <= L/2  (45 deg end bevel)
    M = M.trim_by_plane([s2, 0, -s2], -(L / 2) * s2)                     # -u + w <= L/2
    return M
def key_local():
    K = bowtie_outline().buffer(-CL, join_style=1)
    M = cs(K).extrude(DP - CF)                                           # w from 0 (outer face) to DP-CF
    M = M.trim_by_plane([-s2, 0, -s2], -(L / 2) * s2 + CL)               # bevels moved inward by CL
    M = M.trim_by_plane([s2, 0, -s2], -(L / 2) * s2 + CL)
    return M
