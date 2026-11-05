import numpy as np

def part_ends(faces, ang_deg=3.0, min_total=60):
    """Group joint faces of one part into 'ends': faces sharing a normal direction.
    Each end: n (unit), levels: list of (offset along n relative to outermost level, face dict)."""
    ends = []
    for f in sorted(faces, key=lambda f: -f['area']):
        for e in ends:
            if np.dot(e['n'], f['n']) > np.cos(np.radians(ang_deg)):
                e['faces'].append(f); break
        else:
            ends.append(dict(n=f['n'].copy(), faces=[f]))
    out = []
    for e in ends:
        tot = sum(f['area'] for f in e['faces'])
        if tot < min_total:
            continue
        dmax = max(f['d'] for f in e['faces'])
        e['levels'] = sorted([(round(dmax - f['d'], 1), f['area']) for f in e['faces']])
        e['total'] = tot
        out.append(e)
    return out
