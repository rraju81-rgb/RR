"""Card-size variants for the accordion rack. python3 accordion_stress.py"""
import accordion_cad as C
import accordion_test as T

def run(label, N, **over):
    saved = {k: getattr(C, k) for k in over}
    for k, v in over.items():
        setattr(C, k, v)
    try:
        A = C.Acc(N); Tm = C.build_templates(); plate = C.wall_plate(A)
        res = T.interference(A, Tm, plate=plate)
        print(f"{label:34s} N={N} poses={res['poses']} with cards={res['with_cards']} bad={len(res['bad'])}", res["bad"][:2], flush=True)
        return len(res["bad"])
    finally:
        for k, v in saved.items():
            setattr(C, k, v)

if __name__ == "__main__":
    n = 0
    n += run("wider card (112 mm)", 6, CARD_W=112.0)
    n += run("thicker card (2.0 mm)", 6, CARD_T=2.0)
    n += run("deeper blister (22 mm)", 6, BLISTER_D=22.0)
    n += run("taller card (190 mm)", 6, CARD_H=190.0)
    n += run("hang hole 9 mm", 4, CARD_HOLE_D=9.0)
    n += run("hang hole at 5.5 mm (tight)", 4, CARD_HOLE_D=5.5)
    print("TOTAL failures:", n)
