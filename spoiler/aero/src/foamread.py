"""Minimal reader for OpenFOAM ASCII polyMesh and volFields (enough for forces and flow pictures)."""
import numpy as np, re, os

def _body(path):
    s = open(path).read()
    i = s.find('FoamFile'); j = s.find('}', i)
    return s[j + 1:] if i >= 0 else s

def _list_block(s, start=0):
    """returns (count, text inside the outer parentheses, end index) of the first 'N\\n(' list after start"""
    m = re.compile(r'(\d+)\s*\(').search(s, start)
    n = int(m.group(1)); i = m.end(); depth = 1; k = i
    # fast path: find the matching ')' by scanning for the last ')' of the block
    while depth:
        a = s.find('(', k); b = s.find(')', k)
        if a != -1 and a < b: depth += 1; k = a + 1
        else: depth -= 1; k = b + 1
    return n, s[i:k - 1], k

def read_points(case):
    s = _body(f'{case}/constant/polyMesh/points'); n, txt, _ = _list_block(s)
    a = np.array(txt.replace('(', ' ').replace(')', ' ').split(), dtype=np.float64)
    return a.reshape(n, 3)

def read_labels(path):
    s = _body(path); n, txt, _ = _list_block(s)
    return np.array(txt.split(), dtype=np.int64)

def read_faces(case):
    s = _body(f'{case}/constant/polyMesh/faces'); n, txt, _ = _list_block(s)
    flat = np.array(txt.replace('(', ' ').replace(')', ' ').split(), dtype=np.int64)
    # flat = [k, v0..vk-1, k, ...]
    starts = np.empty(n, np.int64); sizes = np.empty(n, np.int64); p = 0
    for i in range(n):
        k = flat[p]; starts[i] = p + 1; sizes[i] = k; p += k + 1
    return flat, starts, sizes

def read_boundary(case):
    s = _body(f'{case}/constant/polyMesh/boundary')
    out = {}
    for m in re.finditer(r'(\w+)\s*\{([^}]*)\}', s):
        d = m.group(2)
        nf = int(re.search(r'nFaces\s+(\d+)', d).group(1)); sf = int(re.search(r'startFace\s+(\d+)', d).group(1))
        tp = re.search(r'\btype\s+(\w+)', d).group(1)
        out[m.group(1)] = dict(nFaces=nf, startFace=sf, type=tp)
    return out

def face_geometry(P, flat, starts, sizes):
    """face centres, area vectors (OpenFOAM convention: right-hand rule of the vertex order)"""
    n = len(starts); C = np.zeros((n, 3)); S = np.zeros((n, 3))
    for k in np.unique(sizes):
        idx = np.nonzero(sizes == k)[0]
        V = P[flat[starts[idx][:, None] + np.arange(k)[None, :]]]          # (m, k, 3)
        c0 = V.mean(1)
        sumA = np.zeros((len(idx), 3)); sumAc = np.zeros((len(idx), 3)); sumAn = np.zeros(len(idx))
        for j in range(k):
            a = V[:, j]; b = V[:, (j + 1) % k]
            cr = np.cross(a - c0, b - c0)                                  # 2 x triangle area vector
            ar = np.linalg.norm(cr, axis=1)
            sumA += 0.5 * cr; sumAc += (0.5 * ar)[:, None] * (a + b + c0) / 3.0; sumAn += 0.5 * ar
        S[idx] = sumA; C[idx] = sumAc / np.maximum(sumAn, 1e-30)[:, None]
    return C, S

def cell_centres(Cf, Sf, owner, neighbour, ncells):
    """area-weighted mean of face centres per cell (close to the true centroid for layer prisms and hexes)"""
    A = np.linalg.norm(Sf, axis=1); nI = len(neighbour)
    w = np.concatenate([A, A[:nI]]); cid = np.concatenate([owner, neighbour])
    pts = np.concatenate([Cf, Cf[:nI]])
    W = np.bincount(cid, weights=w, minlength=ncells)
    return np.column_stack([np.bincount(cid, weights=w * pts[:, d], minlength=ncells) for d in range(3)]) / W[:, None]

def read_field(case, time, name, ncells, boundary):
    """returns (internal array, {patch: boundary value array or None})"""
    s = _body(f'{case}/{time}/{name}')
    vec = 'volVectorField' in open(f'{case}/{time}/{name}').read(3000)
    ncomp = 3 if vec else 1
    i = s.find('internalField')
    def parse_value(seg, n):
        m = re.match(r'\s*uniform\s+(\([^)]*\)|[-+0-9.eE]+)', seg)
        if m:
            v = np.array(m.group(1).strip('()').split(), float)
            return np.tile(v, (n, 1)) if ncomp == 3 else np.full(n, float(v[0]))
        cnt, txt, _ = _list_block(seg)
        a = np.array(txt.replace('(', ' ').replace(')', ' ').split(), float)
        return a.reshape(cnt, 3) if ncomp == 3 else a
    seg = s[i + len('internalField'):]
    internal = parse_value(seg[: seg.find(';', seg.find(')') if 'nonuniform' in seg[:40] else 0) + 1] if False else seg, ncells)
    bf = {}
    j = s.find('boundaryField')
    for pname, info in boundary.items():
        m = re.search(r'\b' + re.escape(pname) + r'\s*\{', s[j:])
        if not m: bf[pname] = None; continue
        k0 = j + m.end(); depth = 1; k = k0
        while depth:
            a = s.find('{', k); b = s.find('}', k)
            if a != -1 and a < b: depth += 1; k = a + 1
            else: depth -= 1; k = b + 1
        blk = s[k0:k - 1]
        vm = re.search(r'\bvalue\s+', blk)
        bf[pname] = parse_value(blk[vm.end():], info['nFaces']) if vm else None
    return internal, bf
