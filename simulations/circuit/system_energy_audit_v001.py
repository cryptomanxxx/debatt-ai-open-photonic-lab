"""OPA-SYS-001: independent accounting audit of AG003, not a device benchmark."""
import csv
import json
import math
from pathlib import Path

SOURCE = Path("antigravity/reproduction/AG-PHOTONIC-003/original/report.json")
OUT = Path("results/opa-sys-001")

def db(ratio):
    return 10 * math.log10(ratio)

def linear(loss_db):
    return 10 ** (loss_db / 10)

def split(n, excess):
    return db(n) + math.ceil(math.log2(n)) * excess

def path_terms(c, optical, phase):
    """Reconstruct AG003 MZI path convention, independent of feasibility."""
    m, n = c["mesh_m"], c["n_lambda"]
    if "MZI" not in c["arch_type"]:
        raise ValueError("MZI only")
    stage_cm = {"thermo_optic": .02, "nonvolatile_pcm": .01,
                "carrier_depletion": .10}.get(c["phase_tech"], .15)
    central = c["source_topo"] == "central"
    comb = c["arch_type"] != "IndepLaser_MZI"
    return {
        "pump_rejection": optical["pump_reject_il_db"] if comb else 0.,
        "comb_rolloff": optical["comb_nonunif_db_per_64"] * math.log2(n) / 6 if comb else 0.,
        "distribution_split": split(max(1, c["n_tiles"] / c["n_comb"]), optical["splitter_excess_db"]) if central else 0.,
        "distribution_waveguide": optical["wg_loss_db_cm"] * (1.5 if central else .2),
        "mux_demux": optical["mux_demux_il_db"] if n > 1 else 0.,
        "tile_split": split(m, optical["splitter_excess_db"]),
        "modulator": optical["mod_il_db"],
        "mesh": (2*m+1) * (optical["mzi_il_db"] + 2*phase["il_db"]),
        "tile_waveguide": ((2*m+2)*stage_cm+.5)*optical["wg_loss_db_cm"],
        "detector_split": 3.,
    }

def pump_for_lines(line_mw, n_lambda, combs, efficiency, coupling_db, excess_db):
    """One pump feeding equal comb branches. Fanout counted exactly once."""
    return line_mw * n_lambda / efficiency * linear(coupling_db + split(combs, excess_db))

def candidate_power(c, optical, system, phase, workload, pump_mw):
    """Reconstruct unrounded distributed independent-laser MZI budget."""
    assert c["arch_type"] == "IndepLaser_MZI" and c["source_topo"] == "distributed"
    m, n, tiles, bits = (c[k] for k in ("mesh_m","n_lambda","n_tiles","bits"))
    d, batch, layers = (workload[k] for k in ("layer_dim","batch_size","num_layers"))
    macs = 3*layers*batch*d*d
    optical_macs = 2*layers*batch*d*d
    electronic_macs = layers*batch*d*d
    t_opt = optical_macs/(tiles*m*m*min(n,batch)*system["f_mod_ghz"]*1e9)
    t_el = electronic_macs/100e12
    reloads = layers*math.ceil(d/m)**2/tiles
    assert tiles*m*m < layers*d*d
    t_reload = reloads*phase["settling_ns"]*1e-9
    # Match the original overlap assumption; serial bound separately reported.
    t = max(t_opt,t_el)+t_reload
    ps = 2*tiles*m*m
    conv = optical_macs/m
    scale = 2**(bits-8) if bits <= 8 else 2**(1.5*(bits-8))
    p = {
        "laser": tiles*pump_mw*1e-3/optical["laser_wpe"],
        "phase_static": ps*phase["static_mw"]*1e-3/2,
        "phase_dynamic": ps*phase["sw_energy_pj"]*1e-12*reloads/tiles/t,
        "converters_drivers": conv*((system["dac_pj_per_conv_8b"]+system["adc_pj_per_conv_8b"])*scale+system["mod_driver_pj_per_sym"])*1e-12/t,
        "tia": tiles*m*n*system["tia_mw_per_ch"]*1e-3*(.2+.8*t_opt/t),
        "calibration": tiles*m*m*system["calib_mw_per_ring_or_mzi"]*1e-3,
        "electronic_compute": (electronic_macs+10*layers*d*d)*system["elec_mac_pj"]*1e-12/t,
        "sram": macs*.05*bits/8*system["sram_pj_per_byte"]*1e-12/t,
        "hbm": layers*d*d*48*system["hbm_pj_per_byte"]*1e-12/t,
    }
    chip = sum(v for k,v in p.items() if k not in ("laser","hbm"))
    card = sum(p.values())
    p["cooling_proxy"] = card*(system["pue_cooling_factor"]-1)
    total = sum(p.values())
    tops = 2*macs/t/1e12
    return dict(components_w=p, chip_w=chip, card_proxy_w=card,
                system_proxy_w=total, tops=tops, topsw=tops/total,
                energy_j=total*t, pj_per_mac=total*t/macs*1e12,
                step_s=t, serial_step_s=t_opt+t_el+t_reload,
                useful_macs=macs)

def main():
    original = json.loads(SOURCE.read_text())
    params = original["parameter_provenance"]
    def values(d):
        return {k: v["val"] if isinstance(v,dict) and "val" in v else v for k,v in d.items()}
    o, s = values(params["optical"]), values(params["system"])
    candidate = original["rankings_and_pareto_candidates"]["best_convergent_overall"]
    c = candidate["config"]
    phase = values(params["phase_shifter_techs"][c["phase_tech"]])
    w = params["workload"]
    # Evaluate the exact historical rejected nominal configuration regardless of feasibility.
    fixed = dict(c, arch_type="MZI", source_topo="central", n_pump=1,
                 n_comb=1,n_lambda=8,mesh_m=8,n_tiles=1,bits=4)
    nominal = path_terms(fixed,o,phase)
    zero = dict(o, **{k:0. for k in ("mzi_il_db","wg_loss_db_cm","mod_il_db","mux_demux_il_db","coupler_il_db")})
    low = path_terms(fixed,zero,phase)
    loss_nom, loss_low = sum(nominal.values()),sum(low.values())
    candidate_loss = sum(path_terms(c,o,phase).values())
    # Receiver power inferred from rounded archived launch, not a new receiver model.
    pump = candidate["metrics"]["p_pump_opt_mw"]
    base = candidate_power(c,o,s,phase,w,pump)
    baseline = s["electronic_baseline_topsw"]
    rows = []
    for loss_reduction in (0.,3.,6.,9.,12.):
        for hbm in (.25,.5,1.):
            for wpe in (.2,.3,.5):
                q = candidate_power(c,dict(o,laser_wpe=wpe),
                    dict(s,hbm_pj_per_byte=s["hbm_pj_per_byte"]*hbm),phase,w,
                    pump/linear(loss_reduction))
                rows.append(dict(loss_reduction_db=loss_reduction,hbm_multiplier=hbm,
                                 laser_wpe=wpe,system_proxy_w=q["system_proxy_w"],
                                 topsw=q["topsw"],exceeds_modeled_reference=q["topsw"]>baseline))
    fanout = []
    for n in (1,2,4,8):
        corrected = pump_for_lines(1.,8,n,.1,o["coupler_il_db"],o["splitter_excess_db"])
        # Original formula multiplies by combs both in power and splitting dB.
        historical = corrected*n
        fanout.append(dict(combs_per_pump=n,corrected_mw=corrected,
                           original_formula_mw=historical,ratio=historical/corrected))
    target = candidate["metrics"]
    checks = {
        "fixed_configuration_strict_loss_decrease": loss_nom > loss_low,
        "loss_removed_matches_terms": math.isclose(loss_nom-loss_low,
             sum(nominal[k]-low[k] for k in nominal),abs_tol=1e-12),
        "low_loss_matches_archived_rounded": abs(loss_low-18.63)<=.0051,
        "candidate_loss_matches": abs(candidate_loss-target["total_path_loss_db"])<=.0051,
        "candidate_power_matches_rounded_input": abs(base["system_proxy_w"]-target["p_system_w"])<.01,
        "candidate_throughput_matches": abs(base["tops"]-target["sustained_tops"])<.001,
        "two_ops_per_mac": math.isclose(base["topsw"]*base["pj_per_mac"],2.,rel_tol=1e-12),
        "fanout_ideal_conservation": all(math.isclose(pump_for_lines(1.,8,n,.1,0.,0.),80*n) for n in (1,2,4,8)),
        "fanout_single_branch_equivalence": fanout[0]["ratio"]==1.,
        "sweep_count": len(rows)==45,
        "all_positive": all(r["system_proxy_w"]>0 and math.isfinite(r["topsw"]) for r in rows),
    }
    report = dict(experiment="OPA-SYS-001",source=str(SOURCE),
        checks=checks,failures=[k for k,v in checks.items() if not v],
        fixed_loss=dict(config=fixed,nominal_terms_db=nominal,low_terms_db=low,
            nominal_db=loss_nom,low_db=loss_low,removed_db=loss_nom-loss_low,
            nominal_feasibility="not evaluated by this audit"),
        candidate=dict(id=candidate["id"],config=c,loss_db=candidate_loss,
            inferred_pump_mw=pump,accounting=base,
            break_even_power_w=base["tops"]/baseline,
            modeled_reference_topsw=baseline),
        pump_fanout=fanout,sensitivity=rows,
        limitations=[
            "Analytic accounting audit of archived assumptions, not independent parameter measurement.",
            "Candidate launch power is rounded original input; no new SNR, LO, amplifier or convergence model.",
            "Path convention includes assumed detector splitting and per-stage phase loss; not a validated optical transfer.",
            "Coupling loss is upstream of path; setting it to zero does not change reported path loss.",
            "Pump fanout comparison isolates a duplicated ideal splitter factor, not full comb feasibility.",
            "Chip and card/system proxies retain original boundary; host, additional idle power and workload accuracy unknown.",
            "Overlap assumed; serial latency bound reported, not a scheduler simulation.",
            "Sensitivity holds workload, receiver power and throughput fixed; no claim of feasible hardware or matched task accuracy.",
            "Electronic reference is an archived assumption, not a measured GPU benchmark.",
        ])
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    with (OUT/"sensitivity.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(dict(checks=checks,fixed_loss=report["fixed_loss"],candidate=report["candidate"],fanout=fanout),indent=2))
    if report["failures"]:
        raise SystemExit("OPA-SYS-001 accounting checks failed")

if __name__ == "__main__":
    main()
