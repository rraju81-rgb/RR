"""Stress variants for side rack v3: python3 side3_stress.py [N ...] -> side3/stress_N.json"""
import sys, json
import side3_cad as C
import side3_test as T

VARIANTS = {"base_1deg_sweep": dict(step=1), "thick_card_2.0mm": dict(CARD_T=2.0, step=3), "deep_blister_22mm": dict(BLISTER_D=22.0, step=3),
            "tall_card_180mm": dict(CARD_H=180.0, step=3), "wide_blister_90mm": dict(BLISTER_W=90.0, step=3)}


def run(N):
    out = {}
    for name, v in VARIANTS.items():
        saved = {k: getattr(C, k) for k in v if k != "step"}
        for k, val in v.items():
            if k != "step": setattr(C, k, val)
        R, P = C.build(N)
        res = T.interference(R, P, step=v["step"])
        out[name] = dict(poses=res["poses"], overlaps=len(res["bad"]), first=res["bad"][:4])
        for k, val in saved.items(): setattr(C, k, val)
        print(N, name, out[name]["poses"], "poses,", out[name]["overlaps"], "overlaps", out[name]["first"], flush=True)
    json.dump(out, open(f"side3/stress_{N}.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    for N in [int(a) for a in sys.argv[1:]] or [3, 5]:
        run(N)
