"""OPA-SYS-005: paired gain-policy sweep, identical configuration grid."""
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from ag003_pump_fanout_v002 import load, configurations, key, category

ROOT = Path("antigravity/reproduction/AG-PHOTONIC-003")
OUT = Path("results/opa-sys-005")
BASE = Path("results/opa-sys-004")
POLICIES = ("legacy", "fixed_max", "optimized")

def evaluate(model, cfg, policy=None):
    a,t,p,c,n,m,tiles,phase,b=cfg
    if a in ("MZI","MRR","Hybrid"):
        if p>c or c%p:
            return dict(feasible=False,reject_reason="invalid_pump_comb_ratio")
        if t=="distributed" and c<tiles:
            return dict(feasible=False,reject_reason="distributed_comb_lt_tiles")
    kwargs=dict(corrected_receiver=True,corrected_laser_limit=True)
    if policy is not None:
        kwargs["gain_policy"]=policy
    return model.evaluate_config(*cfg,**kwargs)

def config_key(r):
    return tuple(r["config"][k] for k in key(("",)*9))

def close(a,b):
    return math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-12)

def check_link(r, params, audit):
    d=r["gain_details"]
    c=r["config"]
    o=params.OPTICAL_PARAMS
    v=lambda k:o[k].val
    g=10**(d["gain_db"]/10)
    loss=10**(d["downstream_loss_db"]/10)
    up=10**(d["upstream_loss_db"]/10)
    n=c["n_lambda"]
    independent=c["arch_type"]=="IndepLaser_MZI"
    sources=(c["n_tiles"] if c["source_topo"]=="distributed" else 1) if independent else c["n_pump"]
    boosters=sources if independent else c["n_comb"]
    band=v("comb_channel_spacing_ghz")*1e9
    ase=10**(v("amp_nf_db")/10)*params.H_PLANCK*params.NU_0*(g-1)*band*1e3
    signal=d["signal_in_per_line_mw"]
    split=1 if independent else c["n_comb"]/c["n_pump"]
    coupling=10**((v("coupler_il_db")+math.ceil(math.log2(split))*v("splitter_excess_db"))/10)*split
    required=signal*up*n*coupling/(1 if independent else v("comb_eff"))
    floor=0 if independent else 1.5*v("comb_threshold_mw")*coupling
    launch=max(required,floor)
    surplus=n*signal*(launch/required-1)
    out=n*(signal*g+ase)
    amp=boosters*out*1e-3/v("amp_wpe") if g>1 else 0
    laser=sources*launch*1e-3/v("laser_wpe")
    rate=params.SYSTEM_PARAMS["f_mod_ghz"].val
    target=10**((6.02*(c["bits"]+.5)+1.76+v("xtalk_penalty_db"))/10)
    actual,_=audit.snr(d["rx_signal_mw"]*1e-3,v("pd_responsivity"),.7*rate*1e9,
        v("tia_noise_pa_rt_hz"),v("laser_rin_db_hz"),20.,d["rx_ase_mw"]*1e-3,band,params.Q_E)
    return all((close(signal*g,d["signal_out_per_line_mw"]),close(signal*g/loss,d["rx_signal_mw"]),
        close(ase,d["ase_out_per_line_mw"]),close(ase/loss,d["rx_ase_mw"]),close(actual,target),
        close(launch,d["source_bank_mw"]),close(surplus,d["discarded_surplus_mw_per_bank"]),
        d["source_count"]==sources,d["booster_count"]==(boosters if g>1 else 0),
        close(d["booster_output_mw"],out if g>1 else 0),
        launch<=d["source_limit_mw"],g==1 or out<=d["saturation_limit_mw"],
        close(amp,d["amplifier_electric_w"]),close(laser,d["laser_electric_w"]),
        close(amp+laser,d["optical_electric_w"])))

def main():
    verify=load("ag003_verify",ROOT/"import_snapshot.py")
    originals=verify.verify(ROOT/"original")
    frozen={p:p.read_bytes() for p in (ROOT/"corrected/physics_model.py",ROOT/"stage2/physics_model.py")}
    params=load("params",ROOT/"original/params.py")
    load("physics_model",ROOT/"original/physics_model.py")
    sweep=load("ag003_original_sweep",ROOT/"original/sweep.py")
    base=load("ag003_stage2",ROOT/"stage2/physics_model.py")
    stage=load("ag003_stage3",ROOT/"stage3/physics_model.py")
    audit=load("ag003_receiver_audit",Path("simulations/circuit/ag003_receiver_audit_v003.py"))
    archived=json.loads((BASE/"result.json").read_text())["variants"]["combined"]
    archived_candidates=json.loads((BASE/"combined_feasible.json").read_text())
    counts={v:Counter() for v in POLICIES}
    feasible={v:[] for v in POLICIES}
    groups={v:Counter() for v in POLICIES}
    transitions={v:Counter() for v in POLICIES[1:]}
    seen=set()
    exact=True
    dominance=True
    link_checks=True
    passive_checks=True
    checked_links=0
    OUT.mkdir(parents=True,exist_ok=True)
    fields=list(key(("",)*9))+[v+"_"+k for v in POLICIES for k in
        ("status","topsw","system_w","gain_db","pump_bank_mw","downstream_loss_db","amp_out_mw")]
    with (OUT/"paired_changes.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader()
        for cfg in configurations():
            if cfg in seen:
                raise ValueError("duplicate configuration")
            seen.add(cfg)
            ref=evaluate(base,cfg)
            records={v:evaluate(stage,cfg,v) for v in POLICIES}
            exact &= records["legacy"]==ref
            fixed,opt=records["fixed_max"],records["optimized"]
            if fixed["feasible"]:
                dominance &= opt["feasible"] and opt["gain_details"]["optical_electric_w"]<=fixed["gain_details"]["optical_electric_w"]+1e-9
            for v,r in records.items():
                s=category(r,sweep)
                counts[v][s]+=1
                if r["feasible"]:
                    feasible[v].append(r)
                    groups[v][(cfg[0],cfg[-1])]+=1
                    if v!="legacy":
                        checked_links+=1
                        link_checks &= check_link(r,params,audit)
                        if r["gain_details"]["gain_db"]==0:
                            d=r["gain_details"]
                            passive_checks &= d["ase_out_per_line_mw"]==0 and d["amplifier_electric_w"]==0 and d["booster_count"]==0
                if v!="legacy":
                    transitions[v][(category(ref,sweep),s)]+=1
            if any(r!=ref for r in records.values()):
                row=key(cfg)
                for v,r in records.items():
                    m=r.get("metrics",{})
                    d=r.get("gain_details",{})
                    row.update({v+"_status":category(r,sweep),v+"_topsw":m.get("eta_sys_topsw"),
                        v+"_system_w":m.get("p_system_w"),v+"_gain_db":d.get("gain_db"),
                        v+"_pump_bank_mw":m.get("p_pump_opt_mw"),
                        v+"_downstream_loss_db":d.get("downstream_loss_db"),v+"_amp_out_mw":d.get("booster_output_mw")})
                writer.writerow(row)
    checks=dict(grid_count=len(seen)==330960,legacy_exact=exact,
        archived_counts=dict(counts["legacy"])==archived["counts"],
        archived_candidates=len(archived_candidates)==886 and {config_key(r):r for r in feasible["legacy"]}=={config_key(r):r for r in archived_candidates},
        all_counts=all(sum(c.values())==len(seen) for c in counts.values()),
        optimized_dominates_fixed=dominance,
        independent_link_accounting=checked_links>0 and link_checks,
        passive_zero_ase_and_amp=passive_checks,
        original_immutable=verify.verify(ROOT/"original")==originals,
        previous_stages_immutable=all(p.read_bytes()==b for p,b in frozen.items()))
    summaries={}
    for v,records in feasible.items():
        records.sort(key=lambda r:r["metrics"]["eta_sys_topsw"],reverse=True)
        (OUT/(v+"_feasible.json")).write_text(json.dumps(records,indent=2,allow_nan=False)+"\n")
        best={}
        for r in records:
            c=r["config"]
            best.setdefault(c["arch_type"]+":"+str(c["bits"]),r)
        summaries[v]=dict(counts=dict(counts[v]),feasible_by_arch_bits=[
            dict(architecture=a,bits=b,count=n) for (a,b),n in sorted(groups[v].items())],
            best_by_arch_bits=best,best_overall=records[0] if records else None,
            best_comb_ge6=next((r for r in records if r["config"]["arch_type"] in ("MZI","MRR","Hybrid") and r["config"]["bits"]>=6),None),
            gain_histogram=dict(Counter(str(r["gain_details"]["gain_db"]) for r in records if "gain_details" in r)))
    result=dict(experiment="OPA-SYS-005",checks=checks,failures=[k for k,v in checks.items() if not v],
        configurations=len(seen),policy_evaluations=len(seen)*len(POLICIES),reference_evaluations=len(seen),
        checked_links=checked_links,stage2_sha256=hashlib.sha256(frozen[ROOT/"stage2/physics_model.py"]).hexdigest(),
        variants=summaries,transitions={v:[dict(baseline=a,variant=b,count=n) for (a,b),n in sorted(c.items())] for v,c in transitions.items()},
        limitations=["Gain grid 0 to nominal maximum in 1 dB steps; no continuous optimum or gain-dependent NF calibration.",
            "Explicit corrected booster plane after pump rejection and roll-off; same nominal legacy path-loss components.",
            "Ideal attenuation discards threshold surplus; full pump power charged, attenuator costs not modeled.",
            "Full in-band optical output divided by WPE remains a conditional proxy, not measured amplifier electricity.",
            "Out-of-band ASE, idle power, filter shape, saturation dynamics, PD saturation, coherent LO and topology gaps remain.",
            "Analytical feasibility only; no convergence, hardware or matched electronic benchmark."])
    (OUT/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,allow_nan=False))
    if result["failures"]:
        raise SystemExit("failed checks: "+", ".join(result["failures"]))

if __name__=="__main__":
    main()
