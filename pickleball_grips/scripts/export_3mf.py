#!/usr/bin/env python3
"""Export colored 3MF versions of the grips  ->  ../3mf/<id>.3mf

Each triangle carries a colour from the design's print palette via the 3MF Materials
extension (<m:colorgroup> + per-triangle pid/p1 - the same mechanism the reference
PickleballGrip_1.3mf uses).  Geometry is identical to stl/<id>.stl (same coordinates,
millimetres, z up, bore centred near the origin).  The bore, floor and butt take the
design's collar colour so no colour change is buried inside the part.

usage: python3 export_3mf.py [--only 01 07 ...]
"""
import argparse
import sys
import warnings
import zipfile
from io import BytesIO
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grip_core import Frame  # noqa: E402
from designs import DESIGNS  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent

NS = ('xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
      'xmlns:m="http://schemas.microsoft.com/3dmanufacturing/material/2015/02"')
CONTENT_TYPES = ('<?xml version="1.0" encoding="utf-8"?>\n'
                 '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
                 '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
                 '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
                 '<Default Extension="png" ContentType="image/png"/>\n</Types>')
RELS = ('<?xml version="1.0" encoding="utf-8"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        '<Relationship Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel" Target="/3D/3dmodel.model" Id="rel0"/>\n'
        '<Relationship Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail" '
        'Target="/Metadata/thumbnail.png" Id="rel1"/>\n</Relationships>')


def triangle_classes(F, V, faces, d):
    """Colour class per triangle: look up the design's class map at the triangle centroid."""
    cls, zr, collar = d["cls"], d["z"], int(d["collar"])
    cen = V[faces].mean(1)
    S, z, off = F.locate(cen)
    i = np.round(S / (F.L / F.N)).astype(int) % F.N
    j = np.clip(np.round((z - zr[0]) / (zr[1] - zr[0])).astype(int), 0, len(zr) - 1)
    c = cls[j, i].astype(int)
    in_zone = (z >= zr[0]) & (z <= zr[-1]) & (F.zone_window(np.clip(z, zr[0], zr[-1])) > 0.5)
    c = np.where(in_zone, c, collar)              # foot, collars, taper, butt
    c = np.where(off < 0.03, collar, c)           # bore wall and floor
    return c


def write_3mf(path, V, faces, cls, palette, title, thumb):
    hexes = ["#%02X%02X%02XFF" % tuple(int(x) for x in p) for p in palette]
    used = np.unique(cls)
    remap = {int(u): k for k, u in enumerate(used)}                    # drop unused palette entries
    idx = np.array([remap[int(c)] for c in cls]) if len(used) < len(palette) else cls
    hexes = [hexes[int(u)] for u in used]
    out = ['<?xml version="1.0" encoding="utf-8"?>\n<model unit="millimeter" xml:lang="en-US" ' + NS + '>\n',
           f'<metadata name="Title">{title}</metadata>\n'
           '<metadata name="Description">Pickleball paddle grip sleeve - fitment matched to PickleballGrip_1.3mf. '
           'Colours are per-triangle (3MF Materials extension).</metadata>\n'
           '<metadata name="Designer">Claude Code</metadata>\n',
           '<resources>\n<m:colorgroup id="2">\n']
    out += [f'<m:color color="{h}"/>\n' for h in hexes]
    out.append(f'</m:colorgroup>\n<object id="1" name="{title}" type="model" pid="2" pindex="0">\n<mesh>\n<vertices>\n')
    out.append("".join(f'<vertex x="{x:.6f}" y="{y:.6f}" z="{z:.6f}"/>\n' for x, y, z in V))
    out.append("</vertices>\n<triangles>\n")
    out.append("".join(f'<triangle v1="{a}" v2="{b}" v3="{c}" pid="2" p1="{k}"/>\n'
                       for (a, b, c), k in zip(faces.tolist(), idx.tolist())))
    out.append('</triangles>\n</mesh>\n</object>\n</resources>\n<build>\n<item objectid="1"/>\n</build>\n</model>\n')
    buf = BytesIO()
    thumb.save(buf, "PNG")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("3D/3dmodel.model", "".join(out))
        z.writestr("Metadata/thumbnail.png", buf.getvalue())
    return len(used), hexes


def main(only=None):
    F = Frame()
    (ROOT / "3mf").mkdir(exist_ok=True)
    for name, label, _ in DESIGNS:
        if only and not any(name.startswith(o) for o in only):
            continue
        m = trimesh.load(ROOT / "stl" / f"{name}.stl", process=True)
        m.merge_vertices()
        V, faces = np.asarray(m.vertices), np.asarray(m.faces)
        npz = np.load(ROOT / "data" / f"{name}_colors.npz")
        d = {k: npz[k] for k in npz.files}
        cls = triangle_classes(F, V, faces, d)
        hero = ROOT / "renders" / f"{name}_hero.png"
        thumb = Image.open(hero).convert("RGB")
        thumb.thumbnail((256, 440))
        n, hexes = write_3mf(ROOT / "3mf" / f"{name}.3mf", V, faces, cls, d["palette"], label.title(), thumb)
        share = np.bincount(cls, minlength=len(d["palette"])) / len(cls) * 100
        print(f"{name:18s} {(ROOT / '3mf' / f'{name}.3mf').stat().st_size / 1e6:5.1f} MB  {n} colours  "
              + "  ".join(f"{h[:7]}={s:.0f}%" for h, s in zip(["#%02X%02X%02X" % tuple(p) for p in d["palette"]], share) if s > 0),
              flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    main(ap.parse_args().only)
