"""
sweep.py - Staged architecture sweep, Pareto front extraction, exclusion summary,
limiting-case validation, and sensitivity / ranking-reversal analysis (AG-PHOTONIC-003).
"""

import time
from collections import Counter
from typing import List, Dict, Any, Tuple
from params import SYSTEM_PARAMS, WORKLOAD
from physics_model import evaluate_config


def is_pareto_dominated(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """Return True if candidate `a` is strictly dominated by `b` on (eta_sys [max], sustained_tops [max], -latency [max], -area [max])."""
    ma, mb = a["metrics"], b["metrics"]
    ge_all = (
        mb["eta_sys_topsw"] >= ma["eta_sys_topsw"]
        and mb["sustained_tops"] >= ma["sustained_tops"]
        and mb["step_latency_ms"] <= ma["step_latency_ms"]
        and mb["chip_area_mm2"] <= ma["chip_area_mm2"]
    )
    gt_one = (
        mb["eta_sys_topsw"] > ma["eta_sys_topsw"]
        or mb["sustained_tops"] > ma["sustained_tops"]
        or mb["step_latency_ms"] < ma["step_latency_ms"]
        or mb["chip_area_mm2"] < ma["chip_area_mm2"]
    )
    return ge_all and gt_one


def extract_pareto_front(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    pareto = []
    # Sort descending by primary objective eta_sys_topsw for faster pruning
    sorted_cands = sorted(candidates, key=lambda x: x["metrics"]["eta_sys_topsw"], reverse=True)
    for c in sorted_cands:
        if not any(is_pareto_dominated(c, p) for p in pareto):
            pareto.append(c)
    return pareto


def categorize_rejection(reason: str) -> str:
    if "Invalid pump-to-comb" in reason or "Asymmetric pump" in reason:
        return "invalid_pump_comb_ratio"
    if "Distributed source" in reason:
        return "distributed_comb_lt_tiles"
    if "Comb bandwidth" in reason:
        return "comb_bandwidth_exceeded"
    if "dispersion" in reason:
        return "broadband_mzi_dispersion"
    if "reticle" in reason:
        return "area_exceeds_reticle"
    if "RIN-limited" in reason:
        return "rin_limited_snr"
    if "ASE-limited" in reason:
        return "ase_limited_snr"
    if "Optical link budget" in reason:
        return "optical_link_budget_exceeded"
    if "Endurance" in reason:
        return "pcm_endurance_exceeded"
    if "Throughput" in reason:
        return "below_min_throughput"
    if "Latency" in reason:
        return "above_max_latency"
    return "other"


def run_architecture_sweep() -> Dict[str, Any]:
    t0 = time.time()
    n_pumps = [1, 2, 4, 8]
    n_combs = [1, 2, 4, 8]
    n_lambdas = [8, 16, 32, 64]
    source_topos = ["central", "distributed"]
    mesh_ms = [4, 8, 16, 32, 64, 128, 256]
    n_tiles_list = [1, 2, 4, 8, 16, 32]
    phase_techs = ["thermo_optic", "carrier_depletion", "pockels_tfln", "nonvolatile_pcm", "hybrid_pcm_pockels"]
    bits_list = [4, 6, 8, 12]

    total_tested = 0
    feasible_list: List[Dict[str, Any]] = []
    reject_counts = Counter()
    reject_examples: Dict[str, str] = {}

    # 1. Comb-powered architectures: MZI, MRR, Hybrid
    for arch in ["MZI", "MRR", "Hybrid"]:
        for topo in source_topos:
            for np_ in n_pumps:
                for nc in n_combs:
                    # Fast structural pre-check (still count in total_tested & exclusions!)
                    if np_ > nc or (nc % np_ != 0) or (topo == "distributed" and nc < 1):
                        # Count the subspace size for accurate accounting
                        sub_n = len(n_lambdas) * len(mesh_ms) * len(n_tiles_list) * len(phase_techs) * len(bits_list)
                        total_tested += sub_n
                        cat = "invalid_pump_comb_ratio"
                        reject_counts[cat] += sub_n
                        reject_examples.setdefault(cat, f"N_pump={np_}, N_comb={nc}")
                        continue
                    for nt in n_tiles_list:
                        if topo == "distributed" and nc < nt:
                            sub_n = len(n_lambdas) * len(mesh_ms) * len(phase_techs) * len(bits_list)
                            total_tested += sub_n
                            cat = "distributed_comb_lt_tiles"
                            reject_counts[cat] += sub_n
                            reject_examples.setdefault(cat, f"distributed N_comb={nc} < N_tiles={nt}")
                            continue
                        for nl in n_lambdas:
                            for m in mesh_ms:
                                for pt in phase_techs:
                                    for b in bits_list:
                                        total_tested += 1
                                        res = evaluate_config(arch, topo, np_, nc, nl, m, nt, pt, b)
                                        if res["feasible"]:
                                            feasible_list.append(res)
                                        else:
                                            cat = categorize_rejection(res["reject_reason"])
                                            reject_counts[cat] += 1
                                            reject_examples.setdefault(cat, res["reject_reason"])

    # 2. Control baselines: IndepLaser_MZI and SingleWave_MZI
    for topo in source_topos:
        for nt in n_tiles_list:
            for m in mesh_ms:
                for pt in phase_techs:
                    for b in bits_list:
                        # SingleWave_MZI (N_lambda = 1)
                        total_tested += 1
                        res_sw = evaluate_config("SingleWave_MZI", topo, 1, 1, 1, m, nt, pt, b)
                        if res_sw["feasible"]:
                            feasible_list.append(res_sw)
                        else:
                            cat = categorize_rejection(res_sw["reject_reason"])
                            reject_counts[cat] += 1
                            reject_examples.setdefault(cat, res_sw["reject_reason"])

                        # IndepLaser_MZI across n_lambdas
                        for nl in n_lambdas:
                            total_tested += 1
                            res_il = evaluate_config("IndepLaser_MZI", topo, 1, 1, nl, m, nt, pt, b)
                            if res_il["feasible"]:
                                feasible_list.append(res_il)
                            else:
                                cat = categorize_rejection(res_il["reject_reason"])
                                reject_counts[cat] += 1
                                reject_examples.setdefault(cat, res_il["reject_reason"])

    # Sort feasible by primary objective: eta_sys_topsw
    feasible_list.sort(key=lambda x: x["metrics"]["eta_sys_topsw"], reverse=True)
    for idx, item in enumerate(feasible_list):
        item["id"] = f"CFG-{idx+1:04d}"

    pareto_front = extract_pareto_front(feasible_list)

    # Best per architecture type
    best_by_arch = {}
    for arch in ["MZI", "MRR", "Hybrid", "IndepLaser_MZI", "SingleWave_MZI"]:
        sub = [x for x in feasible_list if x["config"]["arch_type"] == arch]
        best_by_arch[arch] = sub[0] if sub else None

    # Best per phase_tech
    best_by_phase = {}
    for pt in phase_techs:
        sub = [x for x in feasible_list if x["config"]["phase_tech"] == pt]
        best_by_phase[pt] = sub[0] if sub else None

    # Best per precision (bits)
    best_by_bits = {}
    for b in bits_list:
        sub = [x for x in feasible_list if x["config"]["bits"] == b]
        best_by_bits[str(b)] = sub[0] if sub else None

    # Sensitivity analysis on top 10 candidates
    top_cands = feasible_list[:10]
    sensitivity_results = run_sensitivity_analysis(top_cands)

    # Limiting case & hand-calc validation
    validation = run_limiting_case_validation(feasible_list[0] if feasible_list else None)

    elapsed_s = round(time.time() - t0, 3)

    # Electronic baseline comparison
    elec_base = {
        "name": "Electronic_Systolic_GPU_TPU_Baseline",
        "eta_sys_topsw": SYSTEM_PARAMS["electronic_baseline_topsw"].val,
        "eta_sys_range": [SYSTEM_PARAMS["electronic_baseline_topsw"].low, SYSTEM_PARAMS["electronic_baseline_topsw"].high],
        "sustained_tops": SYSTEM_PARAMS["electronic_baseline_tops"].val,
        "pj_per_mac_sys": round(2.0 / SYSTEM_PARAMS["electronic_baseline_topsw"].val, 4),
    }

    return {
        "sweep_runtime_s": elapsed_s,
        "total_configurations_evaluated": total_tested,
        "total_feasible": len(feasible_list),
        "total_rejected": total_tested - len(feasible_list),
        "rejection_breakdown": dict(reject_counts),
        "rejection_examples": reject_examples,
        "electronic_baseline": elec_base,
        "pareto_front": pareto_front[:25],
        "top_15_overall": feasible_list[:15],
        "best_by_arch": best_by_arch,
        "best_by_phase_tech": best_by_phase,
        "best_by_bits": best_by_bits,
        "sensitivity_analysis": sensitivity_results,
        "energy_accounting_validation": validation,
    }


def run_sensitivity_analysis(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not candidates:
        return {"note": "No feasible candidates for sensitivity analysis."}

    scenarios = {
        "optimistic_low_loss_high_wpe": {
            "comb_eff": 0.25, "laser_wpe": 0.30, "mzi_il_db": 0.05, "hbm_pj_per_byte": 2.5, "amp_psat_mw": 500.0
        },
        "pessimistic_high_loss_low_wpe": {
            "comb_eff": 0.04, "laser_wpe": 0.12, "mzi_il_db": 0.35, "hbm_pj_per_byte": 8.0, "amp_psat_mw": 100.0
        },
        "reduced_mod_rate_5ghz": {"f_mod_ghz": 5.0},
        "high_mod_rate_20ghz": {"f_mod_ghz": 20.0},
        "low_hbm_energy_1pj": {"hbm_pj_per_byte": 1.0},
    }

    nominal_top_id = candidates[0]["id"]
    scenario_outcomes = {}
    ranking_reversals = []

    for sc_name, ov in scenarios.items():
        sc_rows = []
        for c in candidates:
            cfg = c["config"]
            r = evaluate_config(
                cfg["arch_type"], cfg["source_topo"], cfg["n_pump"], cfg["n_comb"],
                cfg["n_lambda"], cfg["mesh_m"], cfg["n_tiles"], cfg["phase_tech"],
                cfg["bits"], cfg["cadence_steps"], param_overrides=ov
            )
            sc_rows.append({
                "id": c["id"],
                "arch": f"{cfg['arch_type']}-{cfg['phase_tech']}-M{cfg['mesh_m']}-T{cfg['n_tiles']}-L{cfg['n_lambda']}-B{cfg['bits']}",
                "feasible": r["feasible"],
                "eta_sys_topsw": r["metrics"]["eta_sys_topsw"] if r["feasible"] else 0.0,
                "reject_reason": r.get("reject_reason"),
            })
        feasible_sc = [x for x in sc_rows if x["feasible"]]
        feasible_sc.sort(key=lambda x: x["eta_sys_topsw"], reverse=True)
        winner_id = feasible_sc[0]["id"] if feasible_sc else None
        if winner_id != nominal_top_id:
            ranking_reversals.append({
                "scenario": sc_name,
                "nominal_winner": nominal_top_id,
                "new_winner": winner_id,
                "reason": "Nominal winner either became infeasible or was overtaken under perturbed parameters."
            })
        scenario_outcomes[sc_name] = {
            "feasible_count_out_of_10": len(feasible_sc),
            "winner_id": winner_id,
            "top_3": feasible_sc[:3],
        }

    return {
        "nominal_top_id": nominal_top_id,
        "scenarios": scenario_outcomes,
        "ranking_reversals": ranking_reversals,
    }


def run_limiting_case_validation(top_cand: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    # Check 1: Power conservation sum == p_system_w
    if top_cand:
        pb = top_cand["power_breakdown_w"]
        pb_sum = sum(pb.values())
        p_sys = top_cand["metrics"]["p_system_w"]
        rel_err = abs(pb_sum - p_sys) / max(p_sys, 1e-9)
        checks.append({
            "check": "power_conservation_sum",
            "expected_w": p_sys,
            "sum_components_w": round(pb_sum, 3),
            "rel_error": round(rel_err, 5),
            "passed": rel_err < 0.01,
        })

        # Check 2: 2 OPs/MAC identity: eta_sys_topsw * pj_per_mac_sys == 2.0
        prod = top_cand["metrics"]["eta_sys_topsw"] * top_cand["metrics"]["pj_per_mac_sys"]
        checks.append({
            "check": "two_ops_per_mac_identity",
            "eta_x_pj_per_mac": round(prod, 4),
            "expected": 2.0,
            "passed": abs(prod - 2.0) < 0.01,
        })

    # Check 3: Zero-passive-loss limiting case strictly reduces path loss vs nominal
    r_nom = evaluate_config("MZI", "central", 1, 1, 8, 8, 1, "pockels_tfln", 4)
    r_ideal = evaluate_config(
        "MZI", "central", 1, 1, 8, 8, 1, "pockels_tfln", 4,
        param_overrides={"mzi_il_db": 0.0, "wg_loss_db_cm": 0.0, "mod_il_db": 0.0, "mux_demux_il_db": 0.0, "coupler_il_db": 0.0}
    )
    checks.append({
        "check": "low_loss_limit_reduces_path_loss",
        "feasible": r_ideal["feasible"],
        "nominal_path_loss_db": r_nom["metrics"]["total_path_loss_db"] if r_nom["feasible"] else None,
        "low_loss_path_loss_db": r_ideal["metrics"]["total_path_loss_db"] if r_ideal["feasible"] else None,
        "passed": r_ideal["feasible"] and (not r_nom["feasible"] or r_ideal["metrics"]["total_path_loss_db"] < r_nom["metrics"]["total_path_loss_db"]),
    })
    return {"checks": checks, "all_passed": all(c["passed"] for c in checks)}


if __name__ == "__main__":
    import json
    out = run_architecture_sweep()
    print(f"Tested: {out['total_configurations_evaluated']}, Feasible: {out['total_feasible']}, Runtime: {out['sweep_runtime_s']}s")
    print("Rejections:", out["rejection_breakdown"])
    if out["top_15_overall"]:
        print("Top 1:", json.dumps(out["top_15_overall"][0], indent=2))
