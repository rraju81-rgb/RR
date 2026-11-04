import numpy as np, trimesh, matplotlib, sys
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from trimesh.ray.ray_pyembree import RayMeshIntersector
def hgrid(mesh, xs, zs, top=True):
    R = RayMeshIntersector(mesh)
    X, Z = np.meshgrid(xs, zs, indexing='ij')
    O = np.column_stack([X.ravel(), np.full(X.size, 200.0 if top else -200.0), Z.ravel()])
    D = np.tile([0, -1.0 if top else 1.0, 0], (len(O), 1))
    loc, ir, it = R.intersects_location(O, D, multiple_hits=False)
    Y = np.full(X.size, np.nan); Y[ir] = loc[:, 1]; return Y.reshape(X.shape)
if __name__ == '__main__':
    out = sys.argv[-1]; paths = sys.argv[1:-1]
    xs = np.arange(-600, 601, 1.0); zs = np.arange(120, 262, 0.25)
    fig, axs = plt.subplots(len(paths), 1, figsize=(16, 5 * len(paths)))
    axs = np.atleast_1d(axs)
    for ax, p in zip(axs, paths):
        Y = hgrid(trimesh.load(p), xs, zs)
        d2 = np.full_like(Y, np.nan); d2[:, 1:-1] = (Y[:, 2:] - 2 * Y[:, 1:-1] + Y[:, :-2]) / 0.25 ** 2
        im = ax.imshow(np.clip(d2.T, -0.15, 0.15), origin='lower', aspect='auto', extent=[xs[0], xs[-1], zs[0], zs[-1]], cmap='RdBu')
        ax.set_title(p + '  top surface d2y/dz2'); plt.colorbar(im, ax=ax)
    plt.tight_layout(); plt.savefig(out, dpi=60)
