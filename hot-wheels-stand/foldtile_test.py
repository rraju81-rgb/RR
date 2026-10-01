"""QA suite for the flat-fold hook tile. python3 foldtile_test.py -> foldtile/qa.json"""
import json
import numpy as np
import manifold3d as m3d
import foldtile_cad as C
import side3_print as PR


def tm(mesh):
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(mesh.vertices, dtype=np.float32), tri_verts=np.asarray(mesh.faces, dtype=np.uint32)))


def t_stop_and_clearance():
    t = tm(C.tile())
    out = dict(free_to_deg=None, stop_deg=None, gaps={})
    prev_free = True
    first_hit = None
    mingap_0_88 = 1e9
    for a in np.arange(0, 111, 1.0):
        f = tm(C.flap(a))
        vol = (t ^ f).volume()
        if vol > 1e-3 and first_hit is None:
            first_hit = float(a)
        if a <= 85 and vol <= 1e-3:
            mingap_0_88 = min(mingap_0_88, t.min_gap(f, 2.0))
    out["first_contact_deg"] = first_hit
    out["min_gap_0_to_85_deg_mm"] = round(float(mingap_0_88), 3)
    return out


def t_hang_fit():
    """card hung on the arm out at the stop: hole vs arm section, card clear of the tile, neighbour card gap."""
    out = {}
    diag = float(np.hypot(C.FLAP_T, C.FLAP_H))
    out["arm_section_diagonal_mm"] = round(diag, 2)
    for hole in (6.0, 6.5, 7.0, 7.5, 8.0):
        out[f"fits_hole_{hole}"] = bool(diag + 0.1 <= hole)
    t, f = tm(C.tile()), tm(C.flap(90.0))
    res = {}
    for zb in (C.T + 0.5, C.T + 10.0, C.T + 20.0, C.T + 26.0):
        c = tm(C.card(C.XH, C.YH, zb))
        res[f"z_back_{zb:.1f}"] = dict(card_vs_tile=round((c ^ t).volume(), 3), card_vs_arm=round((c ^ f).volume(), 3))
    out["card_positions"] = res
    # neighbouring tile (x + 112) with its own card: gap between the two cards
    c0 = tm(C.card(C.XH, C.YH, C.T + 0.5)); c1 = tm(C.card(C.XH + C.W, C.YH, C.T + 0.5))
    out["card_to_card_gap_mm"] = round(float(c0.min_gap(c1, 20.0)), 2)
    # a card hung high on the arm tip must clear the NEXT tile's tongue region etc: arms out of both tiles
    t2 = tm(C.tile()).translate([C.W, 0, 0]); f2 = tm(C.flap(90.0)).translate([C.W, 0, 0])
    out["arm_vs_next_tile_mm"] = round(float(f.min_gap(t2, 5.0)), 2)
    out["tiles_overlap_when_joined_mm3"] = round((t ^ t2).volume(), 4)
    return out


def t_structural(card_g=40.0):
    W = card_g * 9.81e-3
    out = {}
    # arm bending (card weight at the middle of the hole, 22 mm out) in the layer plane (y load on the arm printed flat)
    Z = C.FLAP_T * C.FLAP_H ** 2 / 6.0
    for lbl, F in (("card_weight", W), ("pull_10N", 10.0)):
        s = F * 22.0 / Z
        out[f"arm_bending_MPa_{lbl}"] = round(s, 2); out[f"arm_SF_in_layer_{lbl}"] = round(22.0 / s, 1)
    # pin shear: the card load is carried by the pocket faces, pin sees a couple only; check the pin as the whole load path anyway
    out["pin_shear_MPa_pull_10N"] = round(10.0 / (np.pi * C.PIN_D ** 2 / 4), 2)
    out["pin_shear_SF"] = round(14.0 / (10.0 / (np.pi * C.PIN_D ** 2 / 4)), 1)
    # moment on the hinge: M = F*22, resisted by contact on pocket faces over arm thickness
    M = 10.0 * 22.0
    contact = M / (C.FLAP_T + 2 * 2.0)
    out["pocket_contact_force_N_at_10N"] = round(contact, 1)
    out["pocket_contact_MPa"] = round(contact / (8.0 * C.FLAP_T * 2), 2)
    # wall screws: card weight moment about the tile bottom edge; 2 screws 84 mm apart; pull-out = M/ (lever)
    n_cards_row = 1
    out["screw_shear_N_each_at_10N_card_pull"] = round(10.0 / 2, 1)
    out["screw_pullout_N_each_card_weight_plus_8mm_lever"] = round(W * 8.0 / 84.0, 3)
    return out


def t_tolerance(trials=20000, sigma=0.10, seed=1):
    rng = np.random.default_rng(seed)
    # radial pin clearance in the hole: pin dia and hole dia both vary; positions vary
    pin = C.PIN_D + rng.normal(0.1, 0.08, trials)          # PETG swell
    hole = C.HOLE_D + rng.normal(-0.1, 0.08, trials)       # holes print small
    off = np.hypot(rng.normal(0, sigma, trials), rng.normal(0, sigma, trials))
    play = (hole - pin) / 2 - off
    gap = C.CL + rng.normal(-0.1, 0.06, trials) - rng.normal(0, sigma, trials)     # arm to pocket clearance
    tab = C.FLAP_H + rng.normal(0.1, 0.08, trials)
    hole_card = 7.0
    section_diag = np.hypot(C.FLAP_T + rng.normal(0.1, 0.08, trials), tab)
    return dict(p_pin_binds=float((play <= 0).mean()), p_pocket_binds=float((gap <= 0.05).mean()), p_arm_does_not_fit_7mm_hole=float((section_diag >= hole_card).mean()),
                p_arm_does_not_fit_6p5_hole=float((section_diag >= 6.5).mean()), pin_play_p1_mm=round(float(np.percentile(play, 1)), 3))


def main():
    out = dict(sizes=dict(tile=[round(float(v), 1) for v in C.tile().extents], print=[round(float(v), 1) for v in C.print_assembly().extents]),
               watertight=dict(tile=bool(C.tile().is_watertight), arm=bool(C.flap().is_watertight)))
    out["T2_stop"] = t_stop_and_clearance()
    out["T3_hang"] = t_hang_fit()
    out["T4_print"] = PR.analyse(C.print_assembly())
    out["T5_structural"] = t_structural()
    out["T6_tolerance"] = t_tolerance()
    out["filament_g_per_tile"] = round(C.print_assembly().volume * 1.27e-3, 1)
    json.dump(out, open("foldtile/qa.json", "w"), indent=1, default=str)
    for k, v in out.items(): print(k, v)


if __name__ == "__main__":
    main()
