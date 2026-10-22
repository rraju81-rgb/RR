"""Sealed lightening cavity for the solid grip body.

The grip is a solid sleeve (paddle slot + screw hole).  To bring the weight down without touching the outside, the thick
side walls are hollowed:  the cavity is everything at least CORE_WALL inside the solid (so every outer wall, slot wall,
screw-hole wall and the floor keep >= CORE_WALL of material), made printable without supports:

  * thin slivers are removed (cavity at least 2 x OPEN_R thick),
  * cavity ceilings are limited to 45 degrees (one voxel in per layer) except for flat bridges up to BRIDGE mm wide,
  * the surface is smoothed (marching cubes on a lightly blurred mask).

The cavity is added to the STL as an inward-facing shell (a closed void inside the part); nothing outside changes.
"""
import numpy as np
import trimesh
from scipy import ndimage as ndi
from skimage import measure
from skimage.draw import polygon as _poly

VOX = 0.20            # mm; equals the 0.20 mm layer height, so one voxel in per layer = 45 degrees
CORE_WALL = 1.2       # mm of material kept around the cavity (3 x 0.4 mm perimeters)
OPEN_R = 1.0          # mm: cavity at least 2 mm thick
BRIDGE = 4.0          # mm: widest flat (unsloped) ceiling allowed
MARGIN = 0.10         # mm: extra erosion that absorbs voxel / smoothing error (measured 3D wall ends up >= ~1.15 mm)
KEEP_Z, KEEP_Y = 8.0, 9.8   # mm: no cavity under the slot floor (z < KEEP_Z = base + 3, |y| < KEEP_Y): the screw head bears on that floor
SOLID_BOTTOM = 5.0          # mm: the bottom 5 mm is solid all over (no cavity below z = 5): a heavy, void-free base that prints cleanly around the screw hole
HEAD_SOLID_FROM = 100.0     # mm: no cavity above this height - the head (top ~33 mm) is fully solid; it cracked when hollow as the paddle neck pried it


def occupancy(mesh, vox=VOX):
    """Boolean voxel grid (z, y, x) of the solid: sections at the mid-plane of every layer, centre-in-polygon rasterised.
    Returns (occ, (x0, y0)) with voxel (k, j, i) centred at x0 + i*vox, y0 + j*vox, z = (k - 0.5)*vox (k = 0 is an empty pad layer)."""
    lo, hi = mesh.bounds
    x0, y0 = np.floor(lo[0] / vox) * vox - 2 * vox, np.floor(lo[1] / vox) * vox - 2 * vox
    nx, ny = int(np.ceil((hi[0] - x0) / vox)) + 3, int(np.ceil((hi[1] - y0) / vox)) + 3
    nz = int(np.ceil(hi[2] / vox))
    zs = (np.arange(nz) + 0.5) * vox
    occ = np.zeros((nz + 2, ny, nx), bool)
    for k, s in enumerate(mesh.section_multiplane(plane_origin=[0, 0, 0], plane_normal=[0, 0, 1], heights=zs)):
        if s is None:
            continue
        m = np.zeros((ny, nx), bool)
        for p in s.polygons_full:
            e = np.asarray(p.exterior.coords)
            rr, cc = _poly((e[:, 1] - y0) / vox, (e[:, 0] - x0) / vox, (ny, nx))
            layer = np.zeros((ny, nx), bool)
            layer[rr, cc] = True
            for i in p.interiors:
                h = np.asarray(i.coords)
                rr, cc = _poly((h[:, 1] - y0) / vox, (h[:, 0] - x0) / vox, (ny, nx))
                layer[rr, cc] = False
            m |= layer
        occ[k + 1] = m
    return occ, (x0, y0)


def limit_roofs(cand, vox=VOX, bridge=BRIDGE):
    """Trim cavity ceilings so nothing overhangs by more than 45 degrees (1 voxel per layer), flat bridges <= `bridge` mm.
    Works top -> bottom: a layer may only keep voxels within one voxel of the layer above, plus 'seeds' - the core of each
    flat ceiling patch, as wide as an allowed bridge."""
    cross = ndi.generate_binary_structure(2, 1)
    out = np.zeros_like(cand)
    half = max(1.0, bridge / 2 / vox)
    for k in range(cand.shape[0] - 2, -1, -1):
        allowed = ndi.binary_dilation(out[k + 1], structure=cross) & cand[k]
        top = cand[k] & ~cand[k + 1]
        if top.any():
            lab, n = ndi.label(top)
            d = ndi.distance_transform_edt(top)
            dmax = np.r_[0.0, ndi.maximum(d, lab, index=np.arange(1, n + 1))]
            allowed |= top & (d >= np.maximum(dmax[lab] - half, 1.0))
        out[k] = allowed
    return out


def core_mask(occ, origin=None, vox=VOX, wall=CORE_WALL):
    d = ndi.distance_transform_edt(occ, sampling=vox) - vox / 2          # distance to the nearest empty voxel, centre -> surface
    cand = d >= wall + MARGIN
    if origin is not None:                                               # keep the floor under the slot, around the screw, solid
        ys = origin[1] + np.arange(occ.shape[1]) * vox
        zs = (np.arange(occ.shape[0]) - 0.5) * vox
        cand[np.ix_(zs < KEEP_Z, np.abs(ys) < KEEP_Y)] = False
        cand[zs >= HEAD_SOLID_FROM] = False
        cand[zs < SOLID_BOTTOM] = False
    core = ndi.distance_transform_edt(cand, sampling=vox) >= OPEN_R        # opening: drop cavity thinner than 2 x OPEN_R
    cand &= ndi.distance_transform_edt(~core, sampling=vox) <= OPEN_R
    return limit_roofs(cand, vox)


def cavity_mesh(mask, origin, vox=VOX, sigma=0.7):
    """Closed, inward-facing (cavity) mesh of the boolean mask via marching cubes on a lightly blurred copy."""
    x0, y0 = origin
    pad = np.pad(mask, 2).astype(np.float32)
    f = ndi.gaussian_filter(pad, sigma)
    v, fc, _, _ = measure.marching_cubes(f, 0.5)                          # index space (z, y, x), voxel centres at integers
    V = np.c_[x0 + (v[:, 2] - 2) * vox, y0 + (v[:, 1] - 2) * vox, (v[:, 0] - 2 - 0.5) * vox]
    m = trimesh.Trimesh(V, fc, process=False)
    if m.volume > 0:                       # make the shell inward-facing (normals point into the cavity), i.e. negative volume
        m.invert()
    return m


def lighten(V, Fc, wall=CORE_WALL, simplify=0.04):
    """Return (V2, F2, info): the body with the sealed cavity added as an inward-facing shell."""
    import manifold3d as m3d
    body = trimesh.Trimesh(V, Fc, process=False)
    occ, origin = occupancy(body)
    mask = core_mask(occ, origin, wall=wall)
    if not mask.any():
        return V, Fc, dict(cavity_cm3=0.0, shells=0)
    cav = cavity_mesh(mask, origin)
    # collapse the flat stair-free regions marching cubes over-tessellates (tolerance well below the nozzle)
    mm = m3d.Manifold(m3d.Mesh(np.asarray(cav.vertices[:, :3], np.float32), np.asarray(cav.faces[:, ::-1], np.uint32)))   # outward-facing copy
    mm = mm.simplify(simplify)
    out = mm.to_mesh()
    cv = np.asarray(out.vert_properties[:, :3], np.float64)
    cf = np.asarray(out.tri_verts, np.int32)[:, ::-1]                      # back to inward-facing
    V2 = np.vstack([V, cv])
    F2 = np.vstack([Fc, cf + len(V)])
    info = dict(cavity_cm3=float(mask.sum() * VOX ** 3 / 1000), cavity_tris=int(len(cf)), shells=int(ndi.label(mask)[1]))
    return V2, F2, info
