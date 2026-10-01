"""Stress tests for the side-mechanism rack: card-size variants and a 1-degree sweep. python3 side_stress.py"""
import side_cad as C
import side_test as T

def run(label, N, **over):
    saved = {k: getattr(C, k) for k in over}
    for k, v in over.items():
        setattr(C, k, v)
    try:
        R, P = C.build(N)
        res = T.interference(R, P, step=2)
        print(f"{label:40s} N={N} bad={len(res['bad'])} max_vol={res['max_vol']:.3f}", res["bad"][:2], flush=True)
        return len(res["bad"])
    finally:
        for k, v in saved.items():
            setattr(C, k, v)

if __name__ == "__main__":
    n = 0
    n += run("thicker card (1.6 mm)", 6, CARD_T=1.6)
    n += run("deeper blister (20 mm)", 6, BLISTER_D=20.0)
    n += run("taller card (180 mm)", 6, CARD_H=180.0)
    n += run("thick + deep + tall", 4, CARD_T=1.6, BLISTER_D=20.0, CARD_H=180.0)
    R, P = C.build(6)
    res = T.interference(R, P, step=1)
    print(f"1-degree sweep N=6: poses={res['poses']} bad={len(res['bad'])} max_vol={res['max_vol']:.3f}")
    n += len(res["bad"])
    print("TOTAL failures:", n)
