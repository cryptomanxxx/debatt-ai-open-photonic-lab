"""OPA-SYS-004: factorial paired sweep of two isolated model changes."""
import csv
import hashlib
import itertools
import json
import math
from collections import Counter
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from ag003_pump_fanout_v002 import load, configurations, key, category

ROOT = Path("antigravity/reproduction/AG-PHOTONIC-003")
OUT = Path("results/opa-sys-004")
BASE = Path("results/opa-sys-002")
VARIANTS = {"baseline": (False,False), "receiver_only": (True,False),
            "laser_only": (False,True), "combined": (True,True)}

def evaluate(model,cfg,flags=None):
    a,t,p,c,n,m,tiles,phase,b=cfg
    if a in ("MZI","MRR","Hybrid"):
        if p>c or c%p:
            return dict(feasible=False,reject_reason="invalid_pump_comb_ratio")
        if t=="distributed" and c<tiles:
            return dict(feasible=False,reject_reason="distributed_comb_lt_tiles")
    if flags is None:
        return model.evaluate_config(*cfg)
    return model.evaluate_config(*cfg,corrected_receiver=flags[0],corrected_laser_limit=flags[1])

def config_key(r):
    return tuple(r["config"][k] for k in key(("",)*9))

def main():
    verify=load("ag003_verify",ROOT/"import_snapshot.py")
    originals=verify.verify(ROOT/"original")
    source=(ROOT/"corrected/physics_model.py").read_bytes()
    load("params",ROOT/"original/params.py")
    load("physics_model",ROOT/"original/physics_model.py")
    sweep=load("ag003_original_sweep",ROOT/"original/sweep.py")
    base=load("ag003_stage1",ROOT/"corrected/physics_model.py")
    stage=load("ag003_stage2",ROOT/"stage2/physics_model.py")
    audit=load("ag003_receiver_audit",Path("simulations/circuit/ag003_receiver_audit_v003.py"))
    params=sys.modules["params"]
    archived=json.loads((BASE/"result.json").read_text())
    archived_candidates=json.loads((BASE/"corrected_feasible.json").read_text())
    archived_by_key={config_key(r):r for r in archived_candidates}
    counts={v:Counter() for v in VARIANTS}
    groups={v:Counter() for v in VARIANTS}
    feasible={v:[] for v in VARIANTS}
    transitions={v:Counter() for v in VARIANTS if v!="baseline"}
    unchanged=True
    laser_controls=True
    interaction_controls=True
    seen=set()
    OUT.mkdir(parents=True,exist_ok=True)
    fields=list(key(("",)*9))+[v+"_"+k for v in VARIANTS for k in ("status","topsw","pump_bank_mw")]
    with (OUT/"paired_changes.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader()
        for cfg in configurations():
            if cfg in seen:
                raise ValueError("duplicate configuration")
            seen.add(cfg)
            ref=evaluate(base,cfg)
            records={v:evaluate(stage,cfg,flags) for v,flags in VARIANTS.items()}
            unchanged &= records["baseline"]==ref
            if cfg[0]!="IndepLaser_MZI":
                laser_controls &= records["laser_only"]==ref
                interaction_controls &= records["combined"]==records["receiver_only"]
            statuses={v:category(r,sweep) for v,r in records.items()}
            for v,r in records.items():
                s=statuses[v]
                counts[v][s]+=1
                if r["feasible"]:
                    feasible[v].append(r)
                    groups[v][(cfg[0],cfg[-1])]+=1
                if v!="baseline":
                    transitions[v][(statuses["baseline"],s)]+=1
            if any(r!=ref for r in records.values()):
                row=key(cfg)
                for v,r in records.items():
                    row[v+"_status"]=statuses[v]
                    row[v+"_topsw"]=r.get("metrics",{}).get("eta_sys_topsw")
                    row[v+"_pump_bank_mw"]=r.get("metrics",{}).get("p_pump_opt_mw")
                writer.writerow(row)
    # Compare independent numeric roots at identical conventions (SYS003).
    roots=[]
    o=params.OPTICAL_PARAMS
    val=lambda k:o[k].val
    for bits,rate,band,ase in itertools.product((4,6,8,12),(5.,10.,25.),(25.,50.,100.),(0.,1.,10.)):
        r,tia,rin,xtalk=(val(k) for k in ("pd_responsivity","tia_noise_pa_rt_hz","laser_rin_db_hz","xtalk_penalty_db"))
        target=10**((6.02*(bits+.5)+1.76+xtalk)/10)
        expected=audit.solve(target,r,.7*rate*1e9,tia,rin,20.,ase*1e-6,band*1e9,params.Q_E)
        actual,_=stage.solve_min_rx_power_mw(bits,rate,r,tia,rin,xtalk,ase*1e-3,
                                               optical_bandwidth_hz=band*1e9,corrected_receiver=True)
        roots.append((actual is None and expected is None) or
                     (actual is not None and expected is not None and math.isclose(actual,expected*1e3,rel_tol=1e-9)))
    checks=dict(grid_count=len(seen)==330960, baseline_exact=unchanged,
        archived_counts=dict(counts["baseline"])==archived["corrected_counts"],
        archived_candidates=len(archived_by_key)==472 and {config_key(r):r for r in feasible["baseline"]}==archived_by_key,
        laser_only_non_independent_unchanged=laser_controls,
        combined_non_independent_equals_receiver=interaction_controls,
        receiver_independent_roots=len(roots)==108 and all(roots),
        all_variant_counts=all(sum(c.values())==len(seen) for c in counts.values()),
        original_immutable=verify.verify(ROOT/"original")==originals,
        stage1_immutable=(ROOT/"corrected/physics_model.py").read_bytes()==source)
    summaries={}
    for v,records in feasible.items():
        records.sort(key=lambda r:r["metrics"]["eta_sys_topsw"],reverse=True)
        (OUT/(v+"_feasible.json")).write_text(json.dumps(records,indent=2,allow_nan=False)+"\n")
        best={}
        for r in records:
            a,b=r["config"]["arch_type"],r["config"]["bits"]
            best.setdefault(a+":"+str(b),r)
        summaries[v]=dict(counts=dict(counts[v]),feasible_by_arch_bits=[
            dict(architecture=a,bits=b,count=n) for (a,b),n in sorted(groups[v].items())],
            best_by_arch_bits=best,best_overall=records[0] if records else None,
            best_comb_ge6=next((r for r in records if r["config"]["arch_type"] in ("MZI","MRR","Hybrid") and r["config"]["bits"]>=6),None))
    result=dict(experiment="OPA-SYS-004",checks=checks,failures=[k for k,v in checks.items() if not v],
        configurations=len(seen),variant_evaluations=len(seen)*len(VARIANTS),
        reference_evaluations=len(seen),stage1_sha256=hashlib.sha256(source).hexdigest(),
        variants=summaries,transitions={v:[dict(baseline=a,variant=b,count=n) for (a,b),n in sorted(c.items())] for v,c in transitions.items()},
        limitations=["Only receiver bandwidth ratio, arbitrary RIN margin and independent laser limit changed.",
            "Optical bandwidth still assumed equal to channel spacing; receiver model not calibrated.",
            "Laser limit assumes identical equal-power lasers; bank power and energy accounting unchanged.",
            "Legacy fixed maximum gain, saturation, source topology, LO omission and scheduling retained.",
            "No amplifier gain optimization or direct insertion of SYS003 link passes; no hardware or convergence claim.",
            "TOPS/W uses rounded legacy metrics and assumed system boundaries."])
    (OUT/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,allow_nan=False))
    if result["failures"]:
        raise SystemExit("failed checks: "+", ".join(result["failures"]))

if __name__=="__main__":
    main()
