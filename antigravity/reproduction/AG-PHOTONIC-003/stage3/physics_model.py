"""
physics_model.py - Analytical physical, optical, electronic, and system model
for frequency-comb-powered photonic AI training accelerators (AG-PHOTONIC-003).
"""

import math
from typing import Dict, Any, Tuple, Optional
from params import (
    H_PLANCK, NU_0, Q_E, OPTICAL_PARAMS, PHASE_TECHS, SYSTEM_PARAMS, WORKLOAD
)

def db_to_lin(db: float) -> float:
    return 10.0 ** (db / 10.0)

def lin_to_db(lin: float) -> float:
    return 10.0 * math.log10(max(lin, 1e-30))

def get_param_val(p_dict: Dict[str, Any], key: str, mode: str = "val") -> float:
    p = p_dict[key]
    return getattr(p, mode) if hasattr(p, mode) else p

def converter_energy_pj(base_8b_pj: float, bits: int) -> float:
    if bits <= 8:
        return base_8b_pj * (2.0 ** (bits - 8))
    return base_8b_pj * (2.0 ** (1.5 * (bits - 8)))

def solve_min_rx_power_mw(
    bits: int,
    f_mod_ghz: float,
    responsivity: float,
    tia_noise_pa_rt_hz: float,
    rin_db_hz: float,
    xtalk_penalty_db: float,
    ase_power_mw: float = 0.0,
    optical_bandwidth_hz: Optional[float] = None,
    corrected_receiver: bool = False,
) -> Tuple[Optional[float], float]:
    """
    Solve for minimum received optical signal power (mW) per photodiode
    to achieve ENOB >= bits + 0.5.
    Returns (P_rx_min_mw or None if RIN/ASE-limited, target_snr_db).
    """
    target_enob = bits + 0.5
    target_snr_db = 6.02 * target_enob + 1.76 + xtalk_penalty_db
    snr_req = db_to_lin(target_snr_db)

    b_rx = 0.7 * f_mod_ghz * 1e9  # Receiver noise bandwidth (Hz)
    # Balanced detection (2 PDs per channel) provides ~20 dB common-mode RIN rejection
    cmrr_db = 20.0
    rin_lin = db_to_lin(rin_db_hz - cmrr_db)  # 1/Hz
    i_tia_sq = ((tia_noise_pa_rt_hz * 1e-12) ** 2) * b_rx  # A^2

    # ASE-spontaneous & signal-ASE beat noise terms if optical amp used
    p_ase_w = ase_power_mw * 1e-3
    i_ase = responsivity * p_ase_w
    # Signal-ASE beat: 4 * R^2 * P_sig * P_ase * (B_rx / B_opt), approx B_rx/B_opt ~ 0.2
    ratio = b_rx / optical_bandwidth_hz if corrected_receiver else 0.2
    beat_coeff = 4.0 * (responsivity ** 2) * p_ase_w * ratio
    sp_sp_noise = 2.0 * Q_E * i_ase * b_rx + (i_ase ** 2) * ratio

    # Quadratic in I_sig: I_sig^2 * (1 - snr_req * rin_lin * b_rx) - I_sig * snr_req * (2*q*b_rx + beat_coeff/R) - snr_req * (i_tia_sq + sp_sp_noise) = 0
    a = 1.0 - snr_req * rin_lin * b_rx
    if a <= (0.0 if corrected_receiver else 0.05):
        return None, target_snr_db  # RIN-limited, infeasible

    b = -snr_req * (2.0 * Q_E * b_rx + (beat_coeff / max(responsivity, 1e-6)))
    c = -snr_req * (i_tia_sq + sp_sp_noise)

    disc = b * b - 4.0 * a * c
    if disc < 0:
        return None, target_snr_db
    i_sig_min = (-b + math.sqrt(disc)) / (2.0 * a)
    p_rx_min_mw = (i_sig_min / responsivity) * 1e3
    return p_rx_min_mw, target_snr_db


def evaluate_config(
    arch_type: str,          # "MZI", "MRR", "Hybrid", "IndepLaser_MZI", "SingleWave_MZI"
    source_topo: str,        # "central", "distributed"
    n_pump: int,
    n_comb: int,
    n_lambda: int,
    mesh_m: int,
    n_tiles: int,
    phase_tech: str,
    bits: int,
    cadence_steps: int = 1,  # Weight update cadence (1 = every step)
    param_overrides: Optional[Dict[str, float]] = None,
    sensitivity_mode: str = "val",  # "val", "low", "high"
    corrected_receiver: bool = False,
    corrected_laser_limit: bool = False,
    gain_policy: str = "legacy",
) -> Dict[str, Any]:
    """
    Evaluate a single candidate configuration. Returns full metrics dict,
    including feasibility status, rejection reason, BOM, power breakdown,
    chip-only & full-system TOPS/W, peak & sustained TOPS, area, latency.
    """
    ov = param_overrides or {}
    def gp(d, k):
        if k in ov:
            return ov[k]
        return get_param_val(d, k, sensitivity_mode)

    pt = PHASE_TECHS[phase_tech]
    def gpt(k):
        if f"{phase_tech}.{k}" in ov:
            return ov[f"{phase_tech}.{k}"]
        v = pt[k]
        return getattr(v, sensitivity_mode) if hasattr(v, sensitivity_mode) else v

    # --- 1. Structural & Physical Feasibility Pre-checks ---
    if arch_type == "SingleWave_MZI" and n_lambda != 1:
        return {"feasible": False, "reject_reason": "SingleWave control requires N_lambda=1"}

    if arch_type == "IndepLaser_MZI":
        # Independent laser array: no nonlinear microcombs (N_comb=0 conceptually, N_pump = N_lambda*sources)
        pass
    else:
        if n_pump > n_comb:
            return {"feasible": False, "reject_reason": f"Invalid pump-to-comb: N_pump ({n_pump}) > N_comb ({n_comb})"}
        if n_comb % n_pump != 0:
            return {"feasible": False, "reject_reason": f"Asymmetric pump split: N_comb ({n_comb}) % N_pump ({n_pump}) != 0"}

    if source_topo == "distributed" and arch_type != "IndepLaser_MZI":
        if n_comb < n_tiles:
            return {"feasible": False, "reject_reason": f"Distributed source requires N_comb ({n_comb}) >= N_tiles ({n_tiles})"}

    # Comb bandwidth & FSR check
    comb_bw_thz = gp(OPTICAL_PARAMS, "comb_bw_thz")
    ch_spacing_ghz = gp(OPTICAL_PARAMS, "comb_channel_spacing_ghz")
    if arch_type != "IndepLaser_MZI" and n_lambda > 1:
        req_bw_thz = (n_lambda * ch_spacing_ghz) / 1000.0
        if req_bw_thz > comb_bw_thz:
            return {"feasible": False, "reject_reason": f"Comb bandwidth exceeded: {req_bw_thz:.2f} THz > {comb_bw_thz:.2f} THz"}

    # MRR requires N_lambda >= 1; if MRR weight bank, vector length is N_lambda
    # Check wavelength-dependent MZI phase dispersion penalty
    # Across total WDM bandwidth, delta_lambda ~ req_bw_thz * 0.008 nm/GHz * 1000
    # For MZI directional coupler / arm imbalance, effective phase error ~ 0.015 rad per THz
    bw_span_thz = (n_lambda * ch_spacing_ghz) / 1000.0
    disp_phase_err_rad = 0.012 * bw_span_thz if "MZI" in arch_type or arch_type == "Hybrid" else 0.004 * bw_span_thz
    if disp_phase_err_rad > (math.pi / (2.0 ** (bits - 1))) and "MZI" in arch_type and n_lambda > 32 and bits >= 12:
        # Dispersion limits effective precision on broadband MZI unless compensated
        return {"feasible": False, "reject_reason": f"Broadband MZI dispersion ({disp_phase_err_rad:.3f} rad) exceeds {bits}-bit phase tolerance"}

    # --- 2. Component Counts (Exact BOM) & Area ---
    if "MZI" in arch_type:
        # SVD two-mesh (U, V^T) + Sigma diagonal (M MZIs)
        mzis_per_tile = mesh_m * (mesh_m - 1) + mesh_m
        mrr_weights_per_tile = 0
        ps_per_tile = 2 * mzis_per_tile
        mods_per_tile = mesh_m * n_lambda
        pds_per_tile = 2 * mesh_m * n_lambda  # Balanced coherent/differential detection per wavelength
        dacs_per_tile = mesh_m * n_lambda
        adcs_per_tile = mesh_m * n_lambda
        l_stage_cm = 0.02 if phase_tech == "thermo_optic" else (0.01 if phase_tech == "nonvolatile_pcm" else (0.10 if phase_tech == "carrier_depletion" else 0.15))
        path_len_cm = (2 * mesh_m + 2) * l_stage_cm + 0.5  # routing
        mesh_stage_depth = 2 * mesh_m + 1
    elif arch_type == "MRR":
        # Broadcast-and-weight: M rows x N_lambda weight rings
        mzis_per_tile = 0
        mrr_weights_per_tile = mesh_m * n_lambda
        ps_per_tile = mrr_weights_per_tile  # 1 tuning element per weight ring
        mods_per_tile = n_lambda  # N_lambda wavelength modulators broadcast to M rows
        pds_per_tile = 2 * mesh_m  # M balanced PD pairs summing N_lambda wavelengths
        dacs_per_tile = n_lambda
        adcs_per_tile = mesh_m
        path_len_cm = (n_lambda * 0.005) + (mesh_m * 0.005) + 0.4
        mesh_stage_depth = 0
    elif arch_type == "Hybrid":
        # Hybrid: MZI spatial unitary (1 mesh M*(M-1)/2) + MRR WDM diagonal/weight bank (M * N_lambda)
        mzis_per_tile = (mesh_m * (mesh_m - 1)) // 2
        mrr_weights_per_tile = mesh_m * n_lambda
        ps_per_tile = 2 * mzis_per_tile + mrr_weights_per_tile
        mods_per_tile = mesh_m * n_lambda
        pds_per_tile = 2 * mesh_m * n_lambda
        dacs_per_tile = mesh_m * n_lambda
        adcs_per_tile = mesh_m * n_lambda
        l_stage_cm = 0.02 if phase_tech == "thermo_optic" else (0.01 if phase_tech == "nonvolatile_pcm" else (0.10 if phase_tech == "carrier_depletion" else 0.15))
        path_len_cm = (mesh_m + 1) * l_stage_cm + (n_lambda * 0.005) + 0.5
        mesh_stage_depth = mesh_m
    else:
        return {"feasible": False, "reject_reason": f"Unknown arch_type: {arch_type}"}

    total_mzis = mzis_per_tile * n_tiles
    total_weight_rings = mrr_weights_per_tile * n_tiles
    total_ps = ps_per_tile * n_tiles
    total_mods = mods_per_tile * n_tiles
    total_pds = pds_per_tile * n_tiles
    total_dacs = dacs_per_tile * n_tiles
    total_adcs = adcs_per_tile * n_tiles

    # Area estimation (mm^2)
    ps_area_mm2 = gpt("area_um2") * 1e-6
    mrr_area_mm2 = 0.0025  # 50um x 50um ring pitch
    mod_area_mm2 = 0.05
    pd_area_mm2 = 0.01
    comb_area_mm2 = 0.25 if arch_type != "IndepLaser_MZI" else 0.0
    elec_tile_area_mm2 = 0.5 + 0.002 * (dacs_per_tile + adcs_per_tile)

    chip_area_mm2 = (
        total_ps * ps_area_mm2 * 1.3  # 1.3x waveguide routing overhead
        + total_weight_rings * mrr_area_mm2
        + total_mods * mod_area_mm2
        + total_pds * pd_area_mm2
        + (n_comb if arch_type != "IndepLaser_MZI" else 0) * comb_area_mm2
        + n_tiles * elec_tile_area_mm2
    )
    reticle_limit = gp(SYSTEM_PARAMS, "reticle_limit_mm2")
    if chip_area_mm2 > reticle_limit:
        return {"feasible": False, "reject_reason": f"Area exceeds reticle limit: {chip_area_mm2:.1f} mm^2 > {reticle_limit:.1f} mm^2"}

    # --- 3. Optical Link Budget & Power Conservation ---
    f_mod_ghz = gp(SYSTEM_PARAMS, "f_mod_ghz")
    resp = gp(OPTICAL_PARAMS, "pd_responsivity")
    tia_noise = gp(OPTICAL_PARAMS, "tia_noise_pa_rt_hz")
    rin_db = gp(OPTICAL_PARAMS, "laser_rin_db_hz")
    xtalk_db = gp(OPTICAL_PARAMS, "xtalk_penalty_db")

    # Optical loss from comb output to a single photodiode (dB)
    coupler_il = gp(OPTICAL_PARAMS, "coupler_il_db")
    splitter_ex = gp(OPTICAL_PARAMS, "splitter_excess_db")
    mux_il = gp(OPTICAL_PARAMS, "mux_demux_il_db") if n_lambda > 1 else 0.0
    wg_loss_db_cm = gp(OPTICAL_PARAMS, "wg_loss_db_cm")
    mod_il = gp(OPTICAL_PARAMS, "mod_il_db")
    mzi_il = gp(OPTICAL_PARAMS, "mzi_il_db") + (2.0 * gpt("il_db") if "MZI" in arch_type or arch_type == "Hybrid" else 0.0)
    mrr_thru = gp(OPTICAL_PARAMS, "mrr_thru_il_db")
    mrr_drop = gp(OPTICAL_PARAMS, "mrr_drop_il_db")

    # Splitting from combs to tiles
    if source_topo == "central":
        tiles_per_comb = max(1, n_tiles / max(n_comb, 1))
        dist_split_db = lin_to_db(tiles_per_comb) + math.ceil(math.log2(max(tiles_per_comb, 1))) * splitter_ex
        dist_wg_db = wg_loss_db_cm * 1.5  # 1.5 cm central routing
    else:
        dist_split_db = 0.0
        dist_wg_db = wg_loss_db_cm * 0.2

    # Tile internal splitting & mesh loss
    if "MZI" in arch_type:
        tile_split_db = lin_to_db(mesh_m) + math.ceil(math.log2(max(mesh_m, 1))) * splitter_ex
        mesh_loss_db = mesh_stage_depth * mzi_il + lin_to_db(mesh_m) * 0.0  # unitary preserves power, split/recombine ~3dB
        # Balanced coherent detection splits signal 50/50 (+3 dB)
        det_split_db = 3.0
    elif arch_type == "MRR":
        # Each wavelength modulator broadcasts to M rows
        tile_split_db = lin_to_db(mesh_m) + math.ceil(math.log2(max(mesh_m, 1))) * splitter_ex
        mesh_loss_db = (n_lambda - 1) * mrr_thru + mrr_drop + gpt("il_db")
        det_split_db = 3.0
    else:  # Hybrid
        tile_split_db = lin_to_db(mesh_m) + math.ceil(math.log2(max(mesh_m, 1))) * splitter_ex
        mesh_loss_db = mesh_stage_depth * mzi_il + (n_lambda - 1) * mrr_thru + mrr_drop + gpt("il_db")
        det_split_db = 3.0

    wg_tile_db = wg_loss_db_cm * path_len_cm
    nonunif_db = gp(OPTICAL_PARAMS, "comb_nonunif_db_per_64") * (math.log2(max(n_lambda, 1)) / 6.0) if (arch_type != "IndepLaser_MZI" and n_lambda > 1) else 0.0
    reject_il = gp(OPTICAL_PARAMS, "pump_reject_il_db") if arch_type != "IndepLaser_MZI" else 0.0

    total_path_loss_db = (
        reject_il + nonunif_db + dist_split_db + dist_wg_db
        + mux_il + tile_split_db + mod_il + mesh_loss_db + wg_tile_db + det_split_db
    )

    # Solve minimum Rx power without optical amplifier
    p_rx_min_mw, target_snr_db = solve_min_rx_power_mw(
        bits, f_mod_ghz, resp, tia_noise, rin_db, xtalk_db, ase_power_mw=0.0,
        optical_bandwidth_hz=ch_spacing_ghz*1e9, corrected_receiver=corrected_receiver
    )
    if p_rx_min_mw is None:
        return {"feasible": False, "reject_reason": f"RIN-limited: cannot reach {target_snr_db:.1f} dB SNR at {bits}-bit"}

    # Required power per comb line at comb output
    p_line_req_mw = p_rx_min_mw * db_to_lin(total_path_loss_db)

    # Check if optical amplification is needed
    used_amp = False
    amp_elec_w = 0.0
    laser_max_mw = gp(OPTICAL_PARAMS, "laser_max_power_mw")
    # Keep aggregate bank power for WPE; only the limit changes.
    if corrected_laser_limit and arch_type == "IndepLaser_MZI":
        laser_max_mw *= n_lambda
    comb_eff = gp(OPTICAL_PARAMS, "comb_eff") if arch_type != "IndepLaser_MZI" else 1.0
    comb_th_mw = gp(OPTICAL_PARAMS, "comb_threshold_mw")

    def calc_pump_req_mw(p_line_mw: float) -> float:
        if arch_type == "IndepLaser_MZI":
            # No comb; each wavelength has its own laser, total optical power per comb-equiv = n_lambda * p_line
            return p_line_mw * n_lambda * db_to_lin(coupler_il)
        combs_per_pump = n_comb / n_pump
        pump_split_loss_db = coupler_il + lin_to_db(combs_per_pump) + math.ceil(math.log2(max(combs_per_pump, 1))) * splitter_ex
        p_comb_total_mw = p_line_mw * n_lambda
        p_at_comb_mw = p_comb_total_mw / comb_eff
        return p_at_comb_mw * db_to_lin(pump_split_loss_db)

    p_pump_req_mw = calc_pump_req_mw(p_line_req_mw)

    # Check comb threshold
    if arch_type != "IndepLaser_MZI":
        combs_per_pump = n_comb / n_pump
        pump_split_loss_db = coupler_il + lin_to_db(combs_per_pump) + math.ceil(math.log2(max(combs_per_pump, 1))) * splitter_ex
        min_pump_for_th_mw = 1.5 * comb_th_mw * db_to_lin(pump_split_loss_db)
        p_pump_opt_mw = max(p_pump_req_mw, min_pump_for_th_mw)
    else:
        p_pump_opt_mw = p_pump_req_mw

    gain_details = None
    if gain_policy == "legacy":
        if p_pump_opt_mw > laser_max_mw:
            # Try inline optical amplification (EDFA/SOA)
            max_gain_db = gp(OPTICAL_PARAMS, "amp_max_gain_db")
            nf_db = gp(OPTICAL_PARAMS, "amp_nf_db")
            psat_mw = gp(OPTICAL_PARAMS, "amp_psat_mw")
            amp_wpe = gp(OPTICAL_PARAMS, "amp_wpe")

            # Booster EDFA/SOA placed after comb + pump-rejection filter, before demux/splitters/mesh
            needed_gain_db = max_gain_db
            g_lin = db_to_lin(needed_gain_db)
            n_sp = 0.5 * db_to_lin(nf_db)
            # ASE power in signal bandwidth (~50 GHz)
            b_opt_hz = gp(OPTICAL_PARAMS, "comb_channel_spacing_ghz") * 1e9
            p_ase_mw = 2.0 * n_sp * H_PLANCK * NU_0 * (g_lin - 1.0) * b_opt_hz * 1e3
            downstream_loss_db = max(0.0, total_path_loss_db - reject_il - nonunif_db)
            # Re-solve Rx power with ASE attenuated by downstream passive loss
            p_rx_ase_mw, _ = solve_min_rx_power_mw(
                bits, f_mod_ghz, resp, tia_noise, rin_db, xtalk_db, ase_power_mw=p_ase_mw / db_to_lin(downstream_loss_db),
                optical_bandwidth_hz=b_opt_hz, corrected_receiver=corrected_receiver
            )
            if p_rx_ase_mw is None:
                return {"feasible": False, "reject_reason": f"Link loss {total_path_loss_db:.1f} dB: ASE-limited even with {needed_gain_db:.1f} dB amp"}

            p_line_amp_mw = (p_rx_ase_mw * db_to_lin(total_path_loss_db)) / g_lin
            p_pump_amp_mw = calc_pump_req_mw(p_line_amp_mw)
            if arch_type != "IndepLaser_MZI":
                p_pump_amp_mw = max(p_pump_amp_mw, min_pump_for_th_mw)

            # Check amplifier saturation (total WDM power at amp output per comb/tile)
            num_amps = n_comb if arch_type != "IndepLaser_MZI" else n_tiles
            total_amp_out_mw = p_line_amp_mw * g_lin * n_lambda * (n_comb / num_amps if arch_type != "IndepLaser_MZI" else 1.0)
            if p_pump_amp_mw > laser_max_mw or total_amp_out_mw > psat_mw:
                return {"feasible": False, "reject_reason": f"Optical link budget failed: loss={total_path_loss_db:.1f} dB, req_pump={p_pump_amp_mw:.1f} mW, amp_out={total_amp_out_mw:.1f} mW"}

            used_amp = True
            p_pump_opt_mw = p_pump_amp_mw
            amp_elec_w = num_amps * (total_amp_out_mw * 1e-3) / amp_wpe


    elif gain_policy in ("fixed_max", "optimized"):
        # Same optical topology as SYS004 except explicit booster count matches
        # the source banks. Gain after pump rejection AND spectral roll-off.
        upstream_loss_db = reject_il + nonunif_db
        downstream_loss_db = total_path_loss_db - upstream_loss_db
        upstream = db_to_lin(upstream_loss_db)
        downstream = db_to_lin(downstream_loss_db)
        source_count = (n_tiles if source_topo == "distributed" else 1) if arch_type == "IndepLaser_MZI" else n_pump
        booster_count = source_count if arch_type == "IndepLaser_MZI" else n_comb
        max_gain_db = gp(OPTICAL_PARAMS, "amp_max_gain_db")
        nf = db_to_lin(gp(OPTICAL_PARAMS, "amp_nf_db"))
        psat = gp(OPTICAL_PARAMS, "amp_psat_mw")
        amp_wpe = gp(OPTICAL_PARAMS, "amp_wpe")
        laser_wpe = gp(OPTICAL_PARAMS, "laser_wpe")
        b_opt_hz = ch_spacing_ghz * 1e9
        # Retain passive option in both corrected variants. Fixed-max uses
        # the same passive-first policy as the legacy model.
        gains = [0.0, max_gain_db] if gain_policy == "fixed_max" else sorted(set(
            [0.0, max_gain_db] + [float(i) for i in range(1, math.ceil(max_gain_db))]))
        options = []
        for gain_db in gains:
            g = db_to_lin(gain_db)
            ase_out = nf * H_PLANCK * NU_0 * (g - 1.0) * b_opt_hz * 1e3
            rx, _ = solve_min_rx_power_mw(
                bits, f_mod_ghz, resp, tia_noise, rin_db, xtalk_db,
                ase_power_mw=ase_out/downstream, optical_bandwidth_hz=b_opt_hz,
                corrected_receiver=corrected_receiver)
            if rx is None:
                continue
            signal_out = rx * downstream
            signal_in = signal_out / g
            requested = calc_pump_req_mw(signal_in * upstream)
            launch = requested
            if arch_type != "IndepLaser_MZI":
                launch = max(requested, min_pump_for_th_mw)
            if launch > laser_max_mw:
                continue
            # Explicit attenuation of surplus comb light before the booster.
            # Ideal adjustable attenuation is an assumption, not free energy:
            # full threshold pump remains charged; dissipated light reported.
            surplus = 0.0 if requested == 0 else n_lambda * signal_in * (launch/requested - 1.0)
            amp_out = n_lambda * (signal_out + ase_out)
            if gain_db > 0 and amp_out > psat:
                continue
            # Retain full optical-output/WPE proxy, not incremental lower
            # bound. Out-of-band ASE and idle/attenuator cost remain unknown.
            amp_w = booster_count * amp_out * 1e-3 / amp_wpe if gain_db > 0 else 0.0
            laser_w = source_count * launch * 1e-3 / laser_wpe
            details = dict(gain_db=gain_db, booster_count=booster_count if gain_db>0 else 0,
                source_count=source_count, source_bank_mw=launch,
                upstream_loss_db=upstream_loss_db, downstream_loss_db=downstream_loss_db,
                signal_in_per_line_mw=signal_in, signal_out_per_line_mw=signal_out,
                ase_out_per_line_mw=ase_out, rx_signal_mw=rx, rx_ase_mw=ase_out/downstream,
                booster_output_mw=amp_out if gain_db>0 else 0.0,
                discarded_surplus_mw_per_bank=surplus,
                laser_electric_w=laser_w, amplifier_electric_w=amp_w,
                optical_electric_w=laser_w+amp_w, source_limit_mw=laser_max_mw,
                saturation_limit_mw=psat)
            options.append(details)
            if gain_policy == "fixed_max" and gain_db == 0:
                break
        if not options:
            return {"feasible": False, "reject_reason": f"Optical link budget failed: loss={total_path_loss_db:.1f} dB, no admissible gain"}
        gain_details = min(options,key=lambda x:(x["optical_electric_w"],x["gain_db"]))
        used_amp = gain_details["gain_db"] > 0
        amp_elec_w = gain_details["amplifier_electric_w"]
        p_pump_opt_mw = gain_details["source_bank_mw"]
    else:
        raise ValueError("unknown gain policy")

    # --- 4. Throughput, Workload Mapping, and Latency ---
    D = WORKLOAD["layer_dim"]
    B_batch = WORKLOAD["batch_size"]
    L_layers = WORKLOAD["num_layers"]
    n_steps = WORKLOAD["training_steps"]

    # Useful MACs per training step: Forward + Backward + Weight Gradient = 3 * L * B * D^2
    useful_macs_per_step = 3.0 * L_layers * B_batch * (D ** 2)

    # Peak photonic MACs/s
    f_mod_hz = f_mod_ghz * 1e9
    if "MZI" in arch_type or arch_type == "Hybrid":
        # WDM batch parallelism: N_lambda batch vectors simultaneously on M x M matrix
        effective_batch_par = min(n_lambda, B_batch)
        peak_macs_per_s_photonic = n_tiles * (mesh_m ** 2) * effective_batch_par * f_mod_hz
        # Photonic handles Fwd + Bwd (2/3 of MACs); Weight-gradient (1/3) is electronic systolic
        photonic_mac_frac = 2.0 / 3.0
    else:  # MRR
        # Independent wavelength-specific weights: M dot products of length N_lambda
        peak_macs_per_s_photonic = n_tiles * mesh_m * n_lambda * f_mod_hz
        # If phase_tech can fast-modulate (Pockels/Carrier), MRR can do all 3 phases; else 2/3
        photonic_mac_frac = 1.0 if gpt("can_fast_modulate") else (2.0 / 3.0)

    peak_photonic_tops = (peak_macs_per_s_photonic * 2.0) * 1e-12
    peak_elec_tops = 200.0 if photonic_mac_frac < 1.0 else 0.0
    peak_tops = peak_photonic_tops + peak_elec_tops

    # Compute time per step (photonic + electronic wgrad + weight reload/settling stalls)
    photonic_macs_step = useful_macs_per_step * photonic_mac_frac
    elec_macs_step = useful_macs_per_step * (1.0 - photonic_mac_frac)

    t_photonic_s = photonic_macs_step / peak_macs_per_s_photonic
    # Assume matched electronic wgrad/accum unit (~200 TMAC/s = 400 TOPS peak)
    t_elec_s = elec_macs_step / 100e12
    # Weight tile reloads per step: L_layers * ceil(D/M)^2 / N_tiles
    if "MZI" in arch_type or arch_type == "Hybrid":
        blocks_per_layer = math.ceil(D / mesh_m) ** 2
    else:
        blocks_per_layer = math.ceil(D / mesh_m) * math.ceil(D / n_lambda)

    reloads_per_step = (L_layers * blocks_per_layer) / n_tiles
    settling_s = gpt("settling_ns") * 1e-9
    # Weight programming latency per step (amortized over cadence_steps if weights held, but tiled blocks MUST reload!)
    # If total on-chip weight capacity >= L_layers * D^2, weights stay resident and only update every cadence_steps!
    on_chip_weight_cap = n_tiles * (mesh_m ** 2 if "MZI" in arch_type or arch_type == "Hybrid" else mesh_m * n_lambda)
    weights_resident = on_chip_weight_cap >= (L_layers * D * D)
    if weights_resident:
        t_reload_s = (1.0 / cadence_steps) * settling_s
        updates_per_step = 1.0 / cadence_steps
    else:
        t_reload_s = reloads_per_step * settling_s
        updates_per_step = reloads_per_step

    # Endurance check (e.g., PCM 1e7 cycles)
    total_cycles = n_steps * updates_per_step
    endurance = pt["endurance_cycles"]
    if total_cycles > endurance:
        return {"feasible": False, "reject_reason": f"Endurance exceeded: {total_cycles:.2e} updates > {endurance:.2e} ({phase_tech})"}

    t_step_s = max(t_photonic_s, t_elec_s) + t_reload_s
    step_latency_ms = t_step_s * 1e3
    sustained_macs_per_s = useful_macs_per_step / t_step_s
    sustained_tops = (sustained_macs_per_s * 2.0) * 1e-12

    if sustained_tops < WORKLOAD["min_throughput_tops"]:
        return {"feasible": False, "reject_reason": f"Throughput below min constraint: {sustained_tops:.2f} TOPS < {WORKLOAD['min_throughput_tops']} TOPS"}
    if step_latency_ms > WORKLOAD["max_step_latency_ms"]:
        return {"feasible": False, "reject_reason": f"Latency above max constraint: {step_latency_ms:.2f} ms > {WORKLOAD['max_step_latency_ms']} ms"}

    # --- 5. Power & Energy Accounting (Chip-only vs Full-System) ---
    laser_wpe = gp(OPTICAL_PARAMS, "laser_wpe")
    if arch_type == "IndepLaser_MZI":
        # Independent laser array: n_tiles * n_lambda lasers (or shared)
        num_lasers = n_tiles if source_topo == "distributed" else 1
        p_laser_elec_w = num_lasers * (p_pump_opt_mw * 1e-3) / laser_wpe
    else:
        p_laser_elec_w = n_pump * (p_pump_opt_mw * 1e-3) / laser_wpe

    p_comb_stab_w = (n_comb * gp(SYSTEM_PARAMS, "comb_stabilization_mw") * 1e-3) if arch_type != "IndepLaser_MZI" else 0.0

    # Phase shifter static + dynamic power
    p_ps_static_w = total_ps * gpt("static_mw") * 1e-3 * 0.5  # average pi/2 bias
    e_ps_sw_j_step = total_ps * (gpt("sw_energy_pj") * 1e-12) * (updates_per_step / max(n_tiles, 1))
    p_ps_dyn_w = e_ps_sw_j_step / t_step_s

    # Active duty cycle of photonic array during step
    photonic_duty = t_photonic_s / t_step_s

    # Modulator drivers, DACs, ADCs, TIAs (only active during photonic_duty for dynamic power; TIA has static bias)
    dac_e_j = converter_energy_pj(gp(SYSTEM_PARAMS, "dac_pj_per_conv_8b"), bits) * 1e-12
    adc_e_j = converter_energy_pj(gp(SYSTEM_PARAMS, "adc_pj_per_conv_8b"), bits) * 1e-12
    drv_e_j = gp(SYSTEM_PARAMS, "mod_driver_pj_per_sym") * 1e-12

    n_conv_ops_step = photonic_macs_step / (mesh_m if "MZI" in arch_type or arch_type == "Hybrid" else n_lambda)
    e_dac_step = n_conv_ops_step * dac_e_j
    e_adc_step = n_conv_ops_step * adc_e_j
    e_drv_step = n_conv_ops_step * drv_e_j
    p_conv_drv_w = (e_dac_step + e_adc_step + e_drv_step) / t_step_s
    p_tia_w = total_pds * 0.5 * gp(SYSTEM_PARAMS, "tia_mw_per_ch") * 1e-3 * (0.2 + 0.8 * photonic_duty)

    # Calibration & thermal stabilization control
    p_calib_w = (total_mzis + total_weight_rings) * gp(SYSTEM_PARAMS, "calib_mw_per_ring_or_mzi") * 1e-3

    # Electronic accumulation, optimizer, & weight-gradient compute
    e_elec_mac_step = elec_macs_step * gp(SYSTEM_PARAMS, "elec_mac_pj") * 1e-12
    # Optimizer (AdamW ~ 10 ops per weight per step)
    e_opt_step = (L_layers * D * D * 10.0) * gp(SYSTEM_PARAMS, "elec_mac_pj") * 1e-12
    p_elec_compute_w = (e_elec_mac_step + e_opt_step) / t_step_s

    # Memory traffic (SRAM activations + HBM weights/optimizer states)
    bytes_per_val = bits / 8.0
    sram_bytes_step = useful_macs_per_step * 0.05 * bytes_per_val  # tiled reuse factor 20x
    hbm_bytes_step = L_layers * D * D * 12.0 * 4.0  # FP32 master weights + Adam m, v read/write
    e_mem_step = sram_bytes_step * gp(SYSTEM_PARAMS, "sram_pj_per_byte") * 1e-12 + hbm_bytes_step * gp(SYSTEM_PARAMS, "hbm_pj_per_byte") * 1e-12
    p_mem_w = e_mem_step / t_step_s

    # Chip-only power (excludes off-chip laser/amp WPE, HBM, cooling; includes on-chip PS, conv, TIA, calib, elec compute, SRAM)
    p_chip_only_w = (
        p_ps_static_w + p_ps_dyn_w + p_conv_drv_w + p_tia_w + p_calib_w + p_elec_compute_w
        + (sram_bytes_step * gp(SYSTEM_PARAMS, "sram_pj_per_byte") * 1e-12) / t_step_s
    )
    p_total_no_cool_w = p_laser_elec_w + amp_elec_w + p_comb_stab_w + p_chip_only_w + (hbm_bytes_step * gp(SYSTEM_PARAMS, "hbm_pj_per_byte") * 1e-12) / t_step_s
    pue = gp(SYSTEM_PARAMS, "pue_cooling_factor")
    p_system_w = p_total_no_cool_w * pue
    p_cooling_w = p_system_w - p_total_no_cool_w

    eta_chip_topsw = sustained_tops / p_chip_only_w
    eta_sys_topsw = sustained_tops / p_system_w
    pj_per_mac_sys = (p_system_w * t_step_s / useful_macs_per_step) * 1e12
    j_per_step_sys = p_system_w * t_step_s

    return {
        "feasible": True,
        "reject_reason": None,
        "config": {
            "arch_type": arch_type,
            "source_topo": source_topo,
            "n_pump": n_pump,
            "n_comb": n_comb,
            "n_lambda": n_lambda,
            "mesh_m": mesh_m,
            "n_tiles": n_tiles,
            "phase_tech": phase_tech,
            "bits": bits,
            "cadence_steps": cadence_steps,
        },
        "metrics": {
            "eta_sys_topsw": round(eta_sys_topsw, 4),
            "eta_chip_topsw": round(eta_chip_topsw, 4),
            "pj_per_mac_sys": round(pj_per_mac_sys, 4),
            "j_per_step_sys": round(j_per_step_sys, 4),
            "sustained_tops": round(sustained_tops, 3),
            "peak_tops": round(peak_tops, 3),
            "peak_photonic_tops": round(peak_photonic_tops, 3),
            "step_latency_ms": round(step_latency_ms, 4),
            "chip_area_mm2": round(chip_area_mm2, 2),
            "p_system_w": round(p_system_w, 3),
            "p_chip_only_w": round(p_chip_only_w, 3),
            "total_path_loss_db": round(total_path_loss_db, 2),
            "p_pump_opt_mw": round(p_pump_opt_mw, 2),
            "used_amp": used_amp,
            "target_snr_db": round(target_snr_db, 2),
            "photonic_mac_frac": round(photonic_mac_frac, 3),
            "weights_resident": weights_resident,
        },
        "power_breakdown_w": {
            "laser_wpe": round(p_laser_elec_w, 3),
            "comb_stab": round(p_comb_stab_w, 3),
            "optical_amp": round(amp_elec_w, 3),
            "ps_static": round(p_ps_static_w, 3),
            "ps_dynamic": round(p_ps_dyn_w, 3),
            "conv_and_drv": round(p_conv_drv_w, 3),
            "tia": round(p_tia_w, 3),
            "calibration": round(p_calib_w, 3),
            "elec_compute_opt": round(p_elec_compute_w, 3),
            "memory_sram_hbm": round(p_mem_w, 3),
            "cooling_pue": round(p_cooling_w, 3),
        },
        **({"gain_details": gain_details} if gain_details is not None else {}),
        "bom": {
            "pump_lasers": n_pump if arch_type != "IndepLaser_MZI" else (n_tiles * n_lambda if source_topo == "distributed" else n_lambda),
            "comb_rings": n_comb if arch_type != "IndepLaser_MZI" else 0,
            "weight_rings": total_weight_rings,
            "mzis": total_mzis,
            "phase_shifters": total_ps,
            "modulators": total_mods,
            "photodiodes": total_pds,
            "dacs": total_dacs,
            "adcs": total_adcs,
        }
    }
