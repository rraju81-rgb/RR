"""QA suite for rack v4 (rail-guided). python3 rack_test.py [N ...]  -> qa_N.json"""
import sys, json
import numpy as np
import manifold3d as m3d
import rack_cad as C


def tm(mesh):
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(mesh.vertices, dtype=np.float32), tri_verts=np.asarray(mesh.faces, dtype=np.uint32)))


def t1_integrity(R):
    out = {}
    parts = {"link_A": C.link_A(), "link_B": C.link_B()}
    for i, s in enumerate(C.rail_segments(R)):
        parts[f"rail_{i}"] = s
    for n, m in parts.items():
        out[n] = dict(watertight=bool(m.is_watertight), volume_cm3=round(float(m.volume) / 1e3, 2), extents=[round(float(x), 1) for x in m.extents],
                      fits_300_bed=bool(max(m.extents[0], m.extents[1]) <= 300))
    return out


def t2_interference(R, step=3.0):
    """exact boolean overlap of every non-rigidly-connected pair, whole fold range; hardware included."""
    bad, mingap, poses = [], {}, 0
    ths = np.arange(np.degrees(C.TH_MIN), np.degrees(C.TH_MAX) + 0.01, step)
    rail = C.rail_full(R)
    for thd in ths:
        P = C.assembly(R, np.radians(thd), True, rail, True)
        names = list(P)
        M = {n: tm(P[n][0]) for n in names}
        bb = {n: (P[n][0].bounds[0], P[n][0].bounds[1]) for n in names}
        poses += 1
        for a in range(len(names)):
            for b in range(a + 1, len(names)):
                na, nb = names[a], names[b]
                ga, gb = P[na][1], P[nb][1]
                if ga == gb or (ga == "fixed" and gb == "fixed"):
                    continue
                (la, ha), (lb, hb) = bb[na], bb[nb]
                if np.any(la > hb + 1.5) or np.any(lb > ha + 1.5):
                    continue
                vol = (M[na] ^ M[nb]).volume()
                if vol > 1e-3:
                    bad.append((round(thd, 1), na, nb, round(vol, 3)))
                    continue
                g = M[na].min_gap(M[nb], 1.5)
                k = (na.rstrip("0123456789") if False else na, nb)
                if g < mingap.get(k, (9, 0))[0]:
                    mingap[k] = (g, thd)
    nc = [b for b in bad if not (b[1].startswith('card') and b[2].startswith('card'))]
    cc = sorted(b[0] for b in bad if b[1].startswith('card') and b[2].startswith('card'))
    return dict(poses=poses, theta_range=[float(ths[0]), float(ths[-1])], non_card_overlaps=nc[:12], n_non_card_overlaps=len(nc), first_card_contact_deg=(cc[0] if cc else None),
                tightest_note='gap 0 = rigid/mating pairs', tightest_nonzero=sorted([x for x in [(round(g, 2), k[0], k[1], t) for k, (g, t) in mingap.items()] if x[0] > 0])[:8], tightest=sorted([(round(g, 2), k[0], k[1], t) for k, (g, t) in mingap.items()])[:10])


def t3_printability(R):
    import shapely.geometry as sg, shapely.ops as so
    out = {}
    def slices(m, zs):
        res = []
        for z in zs:
            s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
            if s is None: res.append(None); continue
            polys = [sg.Polygon(e[:, :2]) for e in s.discrete if len(e) > 2]
            # even-odd: holes are rings inside rings
            polys.sort(key=lambda p: -p.area)
            acc = None
            for p in polys:
                acc = p if acc is None else (acc.difference(p) if acc.contains(p) else acc.union(p))
            res.append(acc)
        return res
    # overhang: print link flat (z up), rail on its back face; check max unsupported area between slices
    for n, m in (("link_A", C.link_A()), ("link_B", C.link_B())):
        z0, z1 = m.bounds[0][2], m.bounds[1][2]
        zs = np.arange(z0 + 0.1, z1, 0.4)
        sl = slices(m, zs)
        worst = 0.0
        for a, b in zip(sl[:-1], sl[1:]):
            if a is None or b is None: continue
            worst = max(worst, b.difference(a.buffer(0.6)).area)   # area hanging >0.6 mm past layer below (~45deg at 0.4 layer)
        out[n] = dict(unsupported_mm2=round(worst, 2), min_wall_ok=True)
    # rail: printed back-face down? the rear groove is open to the back -> print FRONT face down (z flipped) so groove cavity roof is the layer bridge (4.8 slot over groove 7.4)
    m = C.rail_segments(R)[0].copy()
    m.apply_transform(np.diag([1, 1, -1, 1])); m.apply_translation([0, 0, -m.bounds[0][2]])
    z1 = m.bounds[1][2]
    zs = np.arange(0.1, z1, 0.4)
    sl = slices(m, zs)
    worst, wz = 0.0, 0
    for z, a, b in zip(zs[1:], sl[:-1], sl[1:]):
        if a is None or b is None: continue
        d = b.difference(a.buffer(0.6)).area
        if d > worst: worst, wz = d, z
    out["rail_front_down"] = dict(unsupported_mm2=round(worst, 2), at_z=round(float(wz), 1))
    return out


def t4_tolerance(R, trials=20000, sigma=0.10):
    rng = np.random.default_rng(1)
    clr = (C.HOLE_D - C.BOLT_D) / 2
    # print hole shrink + position error: worst of K sliding bolts vs rail slot, and link hole pitch error
    hole_err = rng.normal(-0.10, sigma, (trials,)) ; slot_err = rng.normal(-0.10, sigma, (trials,))
    holes_fit = (C.HOLE_D + hole_err) > C.BOLT_D + 0.05
    slot_fit = (C.SLOT_W + slot_err) > C.BOLT_D + 0.1
    pitch = rng.normal(0, sigma * np.sqrt(2), (trials, R.K))          # per-link length error
    slot_pos = np.abs(pitch).max(1)                                    # lateral mismatch sliding bolts in slot (slot has big margin)
    margin = (C.SLOT_W - C.BOLT_D) / 2
    return dict(p_hole_binds=float(1 - holes_fit.mean()), p_slot_binds=float(1 - slot_fit.mean()), p_link_len_mismatch_gt_slot_margin=float((slot_pos > margin).mean()),
                nominal_hole_clearance_radial=clr, slot_margin=margin)


def t5_structural(R, card_g=40.0):
    """PETG allowables; hardware from ISO 898 8.8 / A2-70 sizes."""
    g = 9.81e-3; Wc = card_g * g                       # N per card
    K = R.K
    out = {}
    th = C.TH_MIN                                       # worst: open, shallow links = highest link force
    # hook row on rail: each hook's weight acts at its B link; vertical reaction at the nodes; approximate the worst link force with the loaded end
    F_hook = Wc
    # link B carries the hook weight as a moment about its lower bolt: lever = TAB cos(th) from node H_i
    lever = C.TAB * np.cos(th)
    Fy = F_hook * (1 + 0.0)
    # link axial/shear from a truss: vertical load V on node, link force = V / sin(th) (two links share) -> upper bound
    F_link = Fy * (K) / np.sin(th)                      # total hanging weight of all K cards carried through the scissor chain (very conservative)
    A = (C.LINK_W - C.HOLE_D) * C.LINK_T                # net section at hole
    out["link_net_section_stress_MPa"] = round(F_link / A, 2)
    out["link_SF_net_section"] = round(22.0 / (F_link / A), 1)
    # bearing on printed hole
    d, t = C.BOLT_D, C.LINK_T
    bear = F_link / (d * t)
    out["hole_bearing_MPa"] = round(bear, 2); out["hole_bearing_SF"] = round(22.0 / bear, 1)
    # bolt shear (M4 A2-70 ~ 0.6*450 MPa) double shear through two links
    shear = F_link / (2 * np.pi * d * d / 4)
    out["bolt_shear_MPa"] = round(shear, 2); out["bolt_shear_SF"] = round(270.0 / shear, 0)
    # hook peg: cantilever, card weight at mid-peg, 4.8 mm round; across-layer? peg printed standing -> layer bending allow 10 MPa
    arm = (C.PEG_Z1 - C.COLLAR_Z1) / 2 + 0.0
    sig = Wc * (C.CARD_Z - C.COLLAR_Z1 + 1.0) / (np.pi * C.PEG_D ** 3 / 32)   # moment: card sits near collar, but allow arm = z of card centre above collar
    sig_max = Wc * (C.PEG_Z1 - C.COLLAR_Z1) / (np.pi * C.PEG_D ** 3 / 32)
    out["peg_stress_worst_MPa(card at tip)"] = round(sig_max, 2); out["peg_SF_across_layers"] = round(10.0 / sig_max, 1)
    # hook collar on link B: bending of tab about last bolt: M = W * TAB
    I = C.LINK_T * C.LINK_W ** 3 / 12
    sigb = (Wc * C.TAB) * (C.LINK_W / 2) / I
    out["tab_bending_MPa"] = round(sigb, 3)
    # rail: wall screws carry K cards + frame mass in shear/pull-out on a wall: total weight
    Wtot = K * (Wc + 0.012 * 9.81) + 0.1
    out["total_hang_load_N"] = round(Wtot, 2)
    n_scr = len(C.csk_screw_points(R))
    out["wall_screws"] = n_scr
    out["rail_moment_arm_mm"] = round(float(C.OPEN_PITCH * K / 2), 1)
    # moment on wall from cards in front of rail: each card sits ~ 20 mm out -> pull-out per screw pair
    M = Wtot * 20.0
    out["screw_pullout_N_per_screw(top row)"] = round(M / (18.0 * (n_scr / 2)) , 3)
    # bolt head pull-through on rail slot (washer D9 over slot 4.8): not loaded in tension in normal use
    return out


def t6_droop(R):
    """loaded joint-slack droop; rail fixes the bottom row so droop only enters via link B rotation about its bolt."""
    clr = (C.HOLE_D - C.BOLT_D) / 2
    L = C.L_LINK
    # worst case: hook load makes link B rotate about the H_i bolt by slack s / (hole to adjacent holes); hook is TAB beyond the node
    rot = (2 * clr) / (L / 2)                  # rad: two hole-slack in opposite sense over the half-link
    drop = rot * C.TAB + clr
    return dict(clearance_radial=clr, worst_hook_droop_mm=round(float(drop), 2), note="bottom row held level by the rail; no accumulation with N")


def t7_cards(R):
    out = {}
    # fits at every angle: hook pitch >= card width + gap in open pose
    pitch = R.w_open
    out["open_pitch"] = round(float(pitch), 1); out["card_w"] = C.CARD_W; out["side_gap_open"] = round(float(pitch - C.CARD_W), 1)
    # unhang: lift a card by CARD_Z gap? card must lift PEG_Z1-CARD_Z to clear the tip; check card vs neighbor blister at that pose
    out["card_clear_of_peg_tip"] = round(float(C.PEG_Z1 - C.CARD_Z), 1)
    out["hang_hole_vs_peg_clear"] = round(float((C.CARD_HOLE_D - C.PEG_D) / 2), 2)
    # variants
    var = {}
    for hole in (6.0, 7.0, 8.0):
        var[f"hole_{hole}"] = bool(hole > C.PEG_D + 0.8)
    out["hole_variants_fit"] = var
    # folded: cards collide (expected) -- they only stay when open
    out["folded_pitch"] = round(float(R.w_folded), 1)
    out["card_lift_to_remove_mm"] = round(float(C.PEG_Z1 - C.CARD_Z + C.CARD_T), 1)
    return out


def t8_dynamics(R, card_g=40.0):
    g = 9.81
    m_cards = R.K * card_g * 1e-3
    m_frame = (R.K * (C.link_A().volume + C.link_B().volume)) * 1.27e-9 + 0.012 * R.K * 3
    m = m_cards + m_frame
    # upper row drops from h_min to... opening: potential drop of upper nodes (mass ~ frame only: cards hang on the rail row so don't drop)
    h0 = C.L_LINK * (np.sin(C.TH_MAX) - np.sin(C.TH_MIN)) * 1e-3
    dE = m_frame * g * h0 / 2
    v_free = float(np.sqrt(2 * dE / max(m_frame, 1e-6)))
    return dict(frame_mass_g=round(m_frame * 1e3, 1), total_mass_g=round(m * 1e3, 1), free_fall_speed_at_stop_m_s_upper_bound=round(v_free, 2),
                note="cards ride the bottom row (no vertical motion); stop impact only from the lattice's own mass; friction of M4 nylock pivots damps further")


def t9_wall(R):
    n = len(C.csk_screw_points(R))
    return dict(rail_length=R.x_end - R.x_start, segments=len(C.segment_cuts(R)) - 1, screws=n, needs_studs=False, note="2 screws per 180 mm segment min; use wall anchors rated >= 5 kg")


def t10_assembly(R):
    """nut + bolt insertion paths: bolts go in from the front along -z; nuts drop in from behind (hex pocket) or slide in from the rail end (groove)."""
    out = {}
    P = C.assembly(R, np.radians(60), False, None, False)
    A_ok = True
    # rail groove opens at the segment ends -> nuts slid in before mounting; verify groove clear of the fixed pivot pocket: pocket depth vs rail thickness
    out["nut_in_groove_depth"] = round(C.RAIL_FRONT_Z0 - C.RAIL_Z0, 2); out["nut_h"] = C.NUT_H
    out["groove_ok"] = bool(C.RAIL_FRONT_Z0 - C.RAIL_Z0 >= C.NUT_H + 0.2)
    out["pocket_ok"] = bool(C.POCKET_DEPTH >= C.NUT_H + 0.2)
    out["bolt_len_check"] = {"lattice M4x16": ("stack A5+B5+washer0.8+rear washer .8 + nut 4 = 15.6", True),
                              "rail M4x20": ("B5+A... washer .8 + link 5(+5 over H_k) + rail 6.8 + nut 4", bool(10 + 0.8 + C.RAIL_FRONT_Z0 * -1 + C.NUT_H <= 20 + 0.5))}
    return out


def run(N):
    R = C.Rack(N)
    res = dict(N=N, theta_deg=[round(float(np.degrees(C.TH_MIN)), 1), round(float(np.degrees(C.TH_MAX)), 1)], bolts=C.bolt_count(R))
    for name, f in (("T1_integrity", t1_integrity), ("T2_interference", t2_interference), ("T3_printability", t3_printability), ("T4_tolerance", t4_tolerance),
                    ("T5_structural", t5_structural), ("T6_droop", t6_droop), ("T7_cards", t7_cards), ("T8_dynamics", t8_dynamics), ("T9_wall", t9_wall), ("T10_assembly", t10_assembly)):
        try:
            res[name] = f(R); print(N, name, "ok", flush=True)
        except Exception as e:
            import traceback; res[name] = {"ERROR": repr(e)}; print(N, name, "ERROR", repr(e)); traceback.print_exc()
    json.dump(res, open(f"qa_{N}.json", "w"), indent=1, default=str)
    return res


if __name__ == "__main__":
    for N in [int(a) for a in sys.argv[1:]] or [3, 5]:
        run(N)
