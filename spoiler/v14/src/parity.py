"""Inside test on a voxel grid by ray parity, shared by the corner blend (e3_corners), the underside fairing
(e4_underside), the coring (p1_core) and the thickness check (thickness).

Each column of voxels is tested with one ray along +y from below the solid; the voxels between the 1st and 2nd hit, the
3rd and 4th, ... are inside. The rays run about a micron off the column centres: a ray exactly along the mesh's edges
(on the plane of an earlier splice, say, which can coincide with a grid plane) may count a crossing twice or not at all.
A column whose count is still odd is cast again with another offset, and the test fails if one stays odd: a column is
never skipped. (Skipping them, as before, left five columns at x = -411 'outside' in v14's first faired body, which put
narrow nicks in its top surface.)"""
import numpy as np

NUDGES = ((1.23e-3, 0.71e-3), (-0.97e-3, 1.49e-3), (0.53e-3, -1.31e-3))   # ray offsets from the column centres (mm)

def fill_inside(R, xs, zs, y0, ny, jy):
    """inside[i, j, k] (shape len(xs), ny, len(zs)) for the columns at (xs[i], zs[k]); R: a RayMeshIntersector of the
    closed mesh; rays start at y = y0, below it; jy(y): the index of the first voxel counted as above y (the caller's
    rounding)."""
    X, Z = np.meshgrid(xs, zs, indexing='ij'); X, Z = X.ravel(), Z.ravel()
    inside = np.zeros((len(xs), ny, len(zs)), bool)
    todo = np.arange(X.size)
    for dx, dz in NUDGES:
        O = np.column_stack([X[todo] + dx, np.full(len(todo), float(y0)), Z[todo] + dz])
        loc, ir, _ = R.intersects_location(O, np.tile([0, 1.0, 0], (len(O), 1)), multiple_hits=True)
        order = np.lexsort((loc[:, 1], ir)); ir, ys = ir[order], loc[order, 1]
        odd = np.bincount(ir, minlength=len(todo)) % 2 == 1
        if len(ir):
            st = np.flatnonzero(np.r_[True, ir[1:] != ir[:-1]]); en = np.r_[st[1:], len(ir)]
            for s, e in zip(st, en):
                if odd[ir[s]]: continue                                  # cast again with the next offset
                i, k = np.unravel_index(todo[ir[s]], (len(xs), len(zs)))
                for a, b in zip(ys[s:e:2], ys[s + 1:e:2]): inside[i, jy(a):jy(b), k] = True
        todo = todo[odd]
        if not len(todo): break
    assert not len(todo), 'inside test: %d ray columns still have an odd number of hits' % len(todo)
    return inside
