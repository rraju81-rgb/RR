#!/usr/bin/env python3
"""CNC programs for machining the stack mould in aluminium (PB-MO-004 blueprint, PB-MO-005 diagram).

    python tools/export_cnc.py              # both machine profiles
    python tools/export_cnc.py --profile vmc

It writes to output/cnc/:
  iso/O0100_OP00_fixture_plate.nc ...   Fanuc / Haas style programs (VMC profile), one per set-up:
                                        tool changes, G43 tool lengths, canned drilling cycles, coolant
  generic/<program>/NN_Tn_*.nc          GRBL / LinuxCNC / Mach3 (router profile): one file per tool,
                                        plain G0 / G1, drilling expanded; touch off each tool at Z0
  cnc_report.json                       tools, operations, path lengths, cycle-time estimates
  toolpaths.json                        simplified toolpaths per operation, for the PB-MO-005 drawing
Verify the programs with tools/verify_cnc.py (stock-removal simulation against the mould STLs).
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from paddle import cam  # noqa: E402
from paddle.cam_mould import CUTS, TOOLS, programs  # noqa: E402

OUT = ROOT / "output" / "cnc"
POST = {"vmc": "iso", "router": "generic"}


def preview(op, setup, tol: float = 0.05) -> list:
    """Feed moves of an op as simplified polylines [[x, y, z], ...] (rapids split them)."""
    lines, cur = [], []
    for g, x, y, z, f in cam.op_moves(op, setup):
        if g == "G1":
            cur.append((x, y, z))
        else:
            if len(cur) > 1:
                lines.append(cur)
            cur = [(x, y, z)]
    if len(cur) > 1:
        lines.append(cur)
    out = []
    for ln in lines:
        s = cam.simplify_path(ln, tol)
        out.append([[round(a, 2) for a in p] for p in s])
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", choices=["vmc", "router", "both"], default="both")
    args = ap.parse_args()
    profs = ["vmc", "router"] if args.profile == "both" else [args.profile]
    OUT.mkdir(parents=True, exist_ok=True)
    report = dict(note="stack mould PB-MO-003 machined in aluminium: fixture plate, OP 10 drilling, main plate faces "
                       "A + B, clamp plates; machine coordinates X = paddle y, Y = -paddle x, Z0 = top of stock",
                  tools={n: dict(kind=t.kind, d=t.d, flute=t.flute, taper=t.taper, desc=t.desc, stickout=t.stickout)
                         for n, t in TOOLS.items()},
                  cuts={p: {k: vars(c) for k, c in CUTS[p].items()} for p in CUTS},
                  profiles={})
    previews = {}
    for prof in profs:
        t0 = time.time()
        post = POST[prof]
        d = OUT / post
        if d.exists():
            for f in sorted(d.rglob("*.nc"), reverse=True):
                f.unlink()
        d.mkdir(parents=True, exist_ok=True)
        rep = []
        for pr in programs(prof):
            ops_rep = []
            total = 0.0
            tools_used = []
            for op in pr.ops:
                mins, cut_len, rap_len = cam.op_time(op, pr.setup, prof)
                if not tools_used or tools_used[-1] != op.tool.n:
                    tools_used.append(op.tool.n)
                c = op.cut
                ops_rep.append(dict(name=op.name, tool=op.tool.n, rpm=c.rpm, feed=c.feed, plunge=c.plunge, ap=c.ap, ae=c.ae,
                                    minutes=round(mins, 2), cut_m=round(cut_len / 1000, 2), rapid_m=round(rap_len / 1000, 2),
                                    stop=op.stop))
                total += mins
                if prof == "vmc":
                    previews.setdefault(pr.key, []).append(dict(name=op.name, tool=op.tool.n,
                                                                lines=preview(op, pr.setup)))
            changes = len(tools_used) * cam.TOOL_CHANGE_S[prof] / 60
            entry = dict(number=pr.number, key=pr.key, title=pr.title, plate=pr.plate, stock_t=pr.stock_t, face=pr.face,
                         tools=tools_used, ops=ops_rep, minutes=round(total + changes, 1), files=[])
            if post == "iso":
                f = d / f"O{pr.number:04d}_{pr.key}.nc"
                f.write_text(cam.post_iso(pr.ops, pr.setup, pr.number, pr.title, pr.header), encoding="ascii")
                entry["files"].append(str(f.relative_to(ROOT)))
            else:
                sub = d / f"{pr.number:04d}_{pr.key}"
                sub.mkdir(parents=True, exist_ok=True)
                for k, (tool, text) in enumerate(cam.post_generic(pr.ops, pr.setup, pr.title, pr.header), 1):
                    f = sub / f"{k:02d}_T{tool.n}_{tool.kind}_D{tool.d:g}.nc"
                    f.write_text(text, encoding="ascii")
                    entry["files"].append(str(f.relative_to(ROOT)))
            rep.append(entry)
            print(f"{prof:6s} O{pr.number:04d} {pr.title:58s} {len(pr.ops):2d} ops, tools {tools_used}, "
                  f"~{entry['minutes']:.0f} min")
        report["profiles"][prof] = dict(post=post, programs=rep,
                                        total_hours=round(sum(e["minutes"] for e in rep) / 60, 1))
        print(f"{prof}: {report['profiles'][prof]['total_hours']} h machine time ({time.time() - t0:.0f} s to generate)")
    (OUT / "cnc_report.json").write_text(json.dumps(report, indent=1))
    if previews:
        (OUT / "toolpaths.json").write_text(json.dumps(previews, separators=(",", ":")))


if __name__ == "__main__":
    main()
