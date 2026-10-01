"""Extra stress tests: card-size variants and a 1-degree sweep. Run: python3 foldout_stress.py"""
import json
import foldout_cad as C
import foldout_test as T

def run(label, N, **over):
    saved = {k: getattr(C, k) for k in over}
    for k, v in over.items():
        setattr(C, k, v)
    try:
        R, P = C.build(N)
        step = over.pop("_step", 2) if False else 2
        res = T.interference(R, P, step=2)
        hw = lambda n: n.startswith(("pin", "spacer", "springpost"))
        bad = [b for b in res["bad"]]
        print(f"{label:46s} N={N} bad={len(bad)} max_vol={res['max_vol']:.3f}", bad[:2])
        return len(bad)
    finally:
        for k, v in saved.items():
            setattr(C, k, v)

if __name__ == "__main__":
    n = 0
    n += run("thicker card (1.6 mm)", 6, CARD_T=1.6)
    n += run("deeper blister (20 mm)", 6, BLISTER_D=20.0)
    n += run("taller card (180 mm)", 6, CARD_H=180.0)
    n += run("thick + deep + tall combined", 4, CARD_T=1.6, BLISTER_D=20.0, CARD_H=180.0)
    # fine sweep: 1-degree steps for the largest rack
    R, P = C.build(6)
    res = T.interference(R, P, step=1)
    print(f"1-degree sweep N=6: poses={res['poses']} bad={len(res['bad'])} max_vol={res['max_vol']:.3f}")
    n += len(res["bad"])
    print("TOTAL failures:", n)
