"""Exporters: binary STL, OBJ + MTL, and glTF binary (GLB).

STL / OBJ are written in design coordinates and millimetres
(x rearward, y right, z up). GLB follows the glTF convention:
metres, +Y up, +Z toward the front of the car, +X to the car's left.
"""

from __future__ import annotations

import json
import struct

import numpy as np

from .mesh import Part

# PBR look used by the GLB / viewer (base colour linear-ish sRGB)
MATERIALS = {
    "paint": dict(color=(0.020, 0.055, 0.105), metallic=0.35, roughness=0.32, clearcoat=1.0),
    "glass": dict(color=(0.010, 0.012, 0.016), metallic=0.0, roughness=0.05, alpha=0.82),
    "carbon": dict(color=(0.018, 0.018, 0.020), metallic=0.2, roughness=0.42),
    "headlight": dict(color=(0.9, 0.95, 1.0), metallic=0.0, roughness=0.2, emissive=(1.0, 1.0, 1.0)),
    "taillight": dict(color=(0.6, 0.02, 0.02), metallic=0.0, roughness=0.3, emissive=(1.0, 0.03, 0.02)),
    "edge": dict(color=(0.012, 0.014, 0.018), metallic=0.1, roughness=0.6),
    "marking": dict(color=(0.86, 0.89, 0.92), metallic=0.1, roughness=0.3, clearcoat=1.0),
    "tyre": dict(color=(0.025, 0.025, 0.025), metallic=0.0, roughness=0.85),
    "rim": dict(color=(0.08, 0.08, 0.09), metallic=0.8, roughness=0.35),
    "floor": dict(color=(0.03, 0.03, 0.035), metallic=0.1, roughness=0.6),
}


def write_stl(path, parts: list[Part], scale=1.0):
    tris = []
    for p in parts:
        tris.append(p.vertices[p.faces] * scale)
    T = np.vstack(tris).astype(np.float32)
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-30)
    rec = np.zeros(len(T), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"] = n
    rec["v"] = T
    with open(path, "wb") as f:
        header = b"MANTA top shell - binary STL - units mm - x rear, y right, z up"
        f.write(header.ljust(80, b" "))
        f.write(struct.pack("<I", len(T)))
        f.write(rec.tobytes())


def write_obj(path, parts: list[Part], mtl_name=None, precision=3):
    lines = ["# MANTA top shell - units: mm - x rearward, y right, z up"]
    if mtl_name:
        lines.append(f"mtllib {mtl_name}")
    off = 1
    used_mats = set()
    fmt = f"v {{:.{precision}f}} {{:.{precision}f}} {{:.{precision}f}}"
    for p in parts:
        lines.append(f"o {p.name}")
        lines.extend(fmt.format(*v) for v in p.vertices)
        for mi, m in enumerate(p.materials):
            sel = p.faces[p.face_mat == mi]
            if not len(sel):
                continue
            used_mats.add(m)
            lines.append(f"g {p.name}_{m}")
            lines.append(f"usemtl {m}")
            lines.extend(f"f {a + off} {b + off} {c + off}" for a, b, c in sel)
        off += len(p.vertices)
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    if mtl_name:
        mtl = []
        for m in sorted(used_mats):
            spec = MATERIALS.get(m, MATERIALS["carbon"])
            r, g, b = spec["color"]
            mtl += [f"newmtl {m}", f"Kd {r:.4f} {g:.4f} {b:.4f}", "Ks 0.5 0.5 0.5",
                    f"Ns {int(900 * (1 - spec['roughness']))}", f"d {spec.get('alpha', 1.0):.2f}", "illum 2", ""]
        with open(str(path).rsplit("/", 1)[0] + "/" + mtl_name, "w") as f:
            f.write("\n".join(mtl))


def to_gltf_coords(v_mm):
    """design (x rear, y right, z up) mm -> glTF (x left, y up, z front) m."""
    v = np.asarray(v_mm, float) / 1000.0
    return np.column_stack([-v[:, 1], v[:, 2], -v[:, 0]])


def write_glb(path, parts: list[Part], extras=None):
    """Write parts as separate nodes; one primitive per material."""
    bin_chunks = []
    offset = 0
    buffer_views, accessors, meshes, nodes, materials = [], [], [], [], []
    mat_index = {}

    def add_view(data: bytes, target):
        nonlocal offset
        pad = (-len(data)) % 4
        bin_chunks.append(data + b"\x00" * pad)
        buffer_views.append(dict(buffer=0, byteOffset=offset, byteLength=len(data), target=target))
        offset += len(data) + pad
        return len(buffer_views) - 1

    def material(name):
        if name in mat_index:
            return mat_index[name]
        spec = MATERIALS.get(name, MATERIALS["carbon"])
        m = dict(name=name, pbrMetallicRoughness=dict(
            baseColorFactor=[*spec["color"], spec.get("alpha", 1.0)],
            metallicFactor=spec["metallic"], roughnessFactor=spec["roughness"]))
        if "emissive" in spec:
            m["emissiveFactor"] = list(spec["emissive"])
            m["extensions"] = {"KHR_materials_emissive_strength": {"emissiveStrength": 3.0}}
        if spec.get("alpha", 1.0) < 1.0:
            m["alphaMode"] = "BLEND"
        if spec.get("clearcoat"):
            m.setdefault("extensions", {})["KHR_materials_clearcoat"] = {
                "clearcoatFactor": spec["clearcoat"], "clearcoatRoughnessFactor": 0.06}
        if name in ("tyre", "rim", "floor", "glass", "carbon", "edge"):
            m["doubleSided"] = True
        materials.append(m)
        mat_index[name] = len(materials) - 1
        return mat_index[name]

    for p in parts:
        pos = to_gltf_coords(p.vertices).astype(np.float32)
        # (x, y, z) -> (-y, z, -x) is a proper rotation, so winding is preserved.
        faces = p.faces
        if p.normals is not None:
            nrm = to_gltf_coords(p.normals * 1000.0).astype(np.float32)
            nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
        else:
            nrm = _vertex_normals(pos, faces).astype(np.float32)
        pv = add_view(pos.tobytes(), 34962)
        accessors.append(dict(bufferView=pv, componentType=5126, count=len(pos), type="VEC3",
                              min=pos.min(0).tolist(), max=pos.max(0).tolist()))
        pa = len(accessors) - 1
        nv = add_view(nrm.tobytes(), 34962)
        accessors.append(dict(bufferView=nv, componentType=5126, count=len(nrm), type="VEC3"))
        na = len(accessors) - 1
        prims = []
        for mi, mname in enumerate(p.materials):
            sel = faces[p.face_mat == mi]
            if not len(sel):
                continue
            idx = sel.astype(np.uint32).ravel()
            iv = add_view(idx.tobytes(), 34963)
            accessors.append(dict(bufferView=iv, componentType=5125, count=len(idx), type="SCALAR"))
            prims.append(dict(attributes=dict(POSITION=pa, NORMAL=na), indices=len(accessors) - 1,
                              material=material(mname)))
        meshes.append(dict(name=p.name, primitives=prims))
        nodes.append(dict(name=p.name, mesh=len(meshes) - 1,
                          extras=dict(is_shell=bool(p.is_shell))))

    used_ext = sorted({k for m in materials for k in m.get("extensions", {})})
    gltf = dict(asset=dict(version="2.0", generator="manta-top-shell"),
                scene=0, scenes=[dict(nodes=list(range(len(nodes))), extras=extras or {})],
                nodes=nodes, meshes=meshes, materials=materials, accessors=accessors,
                bufferViews=buffer_views, buffers=[dict(byteLength=offset)])
    if used_ext:
        gltf["extensionsUsed"] = used_ext
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * ((-len(js)) % 4)
    bin_data = b"".join(bin_chunks)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bin_data)))
        f.write(struct.pack("<II", len(js), 0x4E4F534A))
        f.write(js)
        f.write(struct.pack("<II", len(bin_data), 0x004E4942))
        f.write(bin_data)


def _vertex_normals(V, F):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    vn = np.zeros_like(V)
    for k in range(3):
        np.add.at(vn, F[:, k], fn)
    return vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-30)
