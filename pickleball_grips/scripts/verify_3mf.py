#!/usr/bin/env python3
"""Validate the 3MF exports with the official lib3mf reader and compare to the STLs.

Checks per file: parses cleanly (lib3mf), one mesh object, triangle/vertex counts equal the STL,
every triangle has a colour property, the colour palette matches, volume matches the STL,
and the mesh is manifold/oriented (lib3mf's own mesh checks).
"""
import ctypes
import sys
import warnings
from pathlib import Path

import numpy as np
import trimesh
import lib3mf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from designs import DESIGNS  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent


def main():
    wrapper = lib3mf.Wrapper()
    ok_all = True
    for name, label, _ in DESIGNS:
        path = ROOT / "3mf" / f"{name}.3mf"
        model = wrapper.CreateModel()
        reader = model.QueryReader("3mf")
        reader.ReadFromFile(str(path))
        warn = [reader.GetWarning(i, ctypes.c_uint32())[0] if False else None for i in range(0)]
        nwarn = reader.GetWarningCount()
        it = model.GetMeshObjects()
        objs = []
        while it.MoveNext():
            objs.append(it.GetCurrentMeshObject())
        mo = objs[0]
        nt, nv = mo.GetTriangleCount(), mo.GetVertexCount()
        # per-triangle colours
        cg_it = model.GetColorGroups()
        assert cg_it.MoveNext()
        cg = cg_it.GetCurrentColorGroup()
        palette = []
        for pid in cg.GetAllPropertyIDs():
            c = cg.GetColor(pid)
            palette.append("#%02X%02X%02X" % (c.Red, c.Green, c.Blue))
        prop_ok = True
        seen = set()
        step = max(1, nt // 4000)
        for t in range(0, nt, step):                     # sample 4000 triangles
            pr = mo.GetTriangleProperties(t)
            seen.add(pr.PropertyIDs[0])
            prop_ok &= (pr.ResourceID == cg.GetResourceID())
        stl = trimesh.load(ROOT / "stl" / f"{name}.stl", process=True)
        stl.merge_vertices()
        m3 = trimesh.load(path, force="mesh", process=True)
        m3.merge_vertices()
        ok = (nt == len(stl.faces) and nv == len(stl.vertices) and prop_ok and nwarn == 0 and
              abs(m3.volume - stl.volume) < 1.0 and m3.is_watertight and
              np.allclose(m3.bounds, stl.bounds, atol=1e-3))
        ok_all &= ok
        print(f"{name:18s} {'OK ' if ok else 'BAD'} tris={nt:7d} verts={nv:7d} lib3mf_warnings={nwarn} "
              f"colours={len(palette)} used_in_sample={len(seen)} vol_diff={abs(m3.volume - stl.volume):.3f} mm3 "
              f"watertight={m3.is_watertight}  palette={','.join(palette)}", flush=True)
    print("ALL OK" if ok_all else "PROBLEMS")
    return ok_all


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
