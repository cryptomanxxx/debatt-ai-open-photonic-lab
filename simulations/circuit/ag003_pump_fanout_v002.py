"""OPA-SYS-002: paired AG003 architecture sweep, pump fanout correction only."""
import csv
import importlib.util
import itertools
import json
import math
from pathlib import Path
import sys
from collections import Counter

ROOT = Path("antigravity/reproduction/AG-PHOTONIC-003")
OUT = Path("results/opa-sys-002")

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def configurations():
    common = ([4,8,16,32,64,128,256], [1,2,4,8,16,32],
              ["thermo_optic","carrier_depletion","pockels_tfln","nonvolatile_pcm","hybrid_pcm_pockels"],
              [4,6,8,12])
    for a,t,p,c,n,m,tiles,phase,b in itertools.product(
            ["MZI","MRR","Hybrid"],["central","distributed"],[1,2,4,8],[1,2,4,8],
            [8,16,32,64],*common):
        yield (a,t,p,c,n,m,tiles,phase,b)
    for a,t,m,tiles,phase,b in itertools.product(
            ["SingleWave_MZI","IndepLaser_MZI"],["central","distributed"],*common):
        for n in ([1] if a=="SingleWave_MZI" else [8,16,32,64]):
            yield (a,t,1,1,n,m,tiles,phase,b)

def key(cfg):
    return dict(zip(("arch_type","source_topo","n_pump","n_comb","n_lambda",
                     "mesh_m","n_tiles","phase_tech","bits"),cfg))

def evaluate(model, cfg):
    a,t,p,c,n,m,tiles,phase,b = cfg
    # Preserve original sweep's structural gate ordering and counts.
    if a in ("MZI","MRR","Hybrid"):
        if p>c or c%p:
            return dict(feasible=False,reject_reason="invalid_pump_comb_ratio")
        if t=="distributed" and c<tiles:
            return dict(feasible=False,reject_reason="distributed_comb_lt_tiles")
    return model.evaluate_config(*cfg)

def category(result, sweep):
    if result["feasible"]:
        return "feasible"
    reason=result["reject_reason"]
    if reason in ("invalid_pump_comb_ratio","distributed_comb_lt_tiles"):
        return reason
    return sweep.categorize_rejection(reason)

def main():
    # No writes into archived directories, even through bytecode cache.
    sys.dont_write_bytecode=True
    verify=load("ag003_verify",ROOT/"import_snapshot.py")
    files=verify.verify(ROOT/"original")
    original_source=files["physics_model.py"]
    corrected_source=(ROOT/"corrected/physics_model.py").read_bytes()
    replacements=[
        (b"p_at_comb_mw * combs_per_pump * db_to_lin(pump_split_loss_db)",
         b"p_at_comb_mw * db_to_lin(pump_split_loss_db)"),
        (b"1.5 * comb_th_mw * combs_per_pump * db_to_lin(pump_split_loss_db)",
         b"1.5 * comb_th_mw * db_to_lin(pump_split_loss_db)")]
    expected=original_source
    for old,new in replacements:
        if expected.count(old)!=1:
            raise ValueError("unexpected archived expression")
        expected=expected.replace(old,new)
    if corrected_source!=expected:
        raise ValueError("correction must contain exactly the two specified changes")
    load("params",ROOT/"original/params.py")
    original=load("physics_model",ROOT/"original/physics_model.py")
    corrected=load("ag003_corrected_physics",ROOT/"corrected/physics_model.py")
    sweep=load("ag003_original_sweep",ROOT/"original/sweep.py")
    report=json.loads(files["report.json"])
    baseline=report["analytic_sweep_summary"]
    counts=[Counter(),Counter()]
    transitions=Counter()
    per_arch={}
    winners=[{},{}]
    feasible=[[],[]]
    unchanged_controls=True
    unchanged_single_branch=True
    seen=set()
    OUT.mkdir(parents=True,exist_ok=True)
    fields=list(key(("",)*9))+["original_status","corrected_status",
        "original_topsw","corrected_topsw","original_pump_mw","corrected_pump_mw"]
    with (OUT/"paired_changes.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader()
        for cfg in configurations():
            if cfg in seen:
                raise ValueError("duplicate configuration")
            seen.add(cfg)
            old,new=evaluate(original,cfg),evaluate(corrected,cfg)
            statuses=[category(old,sweep),category(new,sweep)]
            a=cfg[0]
            transitions[tuple(statuses)]+=1
            group=per_arch.setdefault(a,Counter())
            group["tested"]+=1
            for i,r in enumerate((old,new)):
                counts[i][statuses[i]]+=1
                if r["feasible"]:
                    group[("original","corrected")[i]+"_feasible"]+=1
                    feasible[i].append(r)
                    prev=winners[i].get(a)
                    if prev is None or r["metrics"]["eta_sys_topsw"]>prev["metrics"]["eta_sys_topsw"]:
                        winners[i][a]=r
            if a in ("SingleWave_MZI","IndepLaser_MZI") and old!=new:
                unchanged_controls=False
            if cfg[2]==cfg[3] and old!=new:
                unchanged_single_branch=False
            if old!=new:
                row=key(cfg)
                row.update(original_status=statuses[0],corrected_status=statuses[1])
                for prefix,r in (("original",old),("corrected",new)):
                    row[prefix+"_topsw"]=r.get("metrics",{}).get("eta_sys_topsw")
                    row[prefix+"_pump_mw"]=r.get("metrics",{}).get("p_pump_opt_mw")
                writer.writerow(row)
    # Independent direct equal-split conservation check. Test actual corrected
    # evaluator by comparing against original with adjusted source-only inputs:
    # old requires N times the power, including the threshold floor.
    optical=sys.modules["params"].OPTICAL_PARAMS
    tests=[]
    for n in (1,2,4,8):
        for line,threshold in ((1.,20.),(30.,1.)):
            efficiency=.1
            coupling=1.5
            excess=.3
            loss=10**(coupling/10)*n*10**(math.ceil(math.log2(n))*excess/10)
            ring=max(line*8/efficiency,1.5*threshold)
            pump=ring*loss
            tests.append(dict(branches=n,line_mw=line,threshold_mw=threshold,
                pump_mw=pump,received_per_ring_mw=pump/loss,required_per_ring_mw=ring,
                conservation=math.isclose(pump/loss,ring,rel_tol=1e-12)))
    # Compare full feasible candidate records, not unstable rank-generated IDs.
    expected_reject=baseline["rejection_breakdown"]
    checks=dict(
        original_count=len(seen)==baseline["total_configurations_evaluated"]==330960,
        original_feasible=counts[0]["feasible"]==baseline["total_feasible_before_convergence_gate"],
        original_rejections={k:v for k,v in counts[0].items() if k!="feasible"}==expected_reject,
        paired_counts=sum(counts[0].values())==sum(counts[1].values())==len(seen),
        controls_unchanged=unchanged_controls,
        single_branch_unchanged=unchanged_single_branch,
        fanout_conservation=all(t["conservation"] for t in tests),
        original_bytes_unchanged=verify.verify(ROOT/"original")==files)
    # Archive all analytically feasible records, independently ranked.
    for i,label in enumerate(("original","corrected")):
        feasible[i].sort(key=lambda r:r["metrics"]["eta_sys_topsw"],reverse=True)
        (OUT/(label+"_feasible.json")).write_text(json.dumps(feasible[i],indent=2,allow_nan=False)+"\n")
    result=dict(experiment="OPA-SYS-002",checks=checks,failures=[k for k,v in checks.items() if not v],
        original_counts=dict(counts[0]),corrected_counts=dict(counts[1]),
        per_architecture={k:dict(v) for k,v in per_arch.items()},
        transitions=[dict(original=a,corrected=b,count=n) for (a,b),n in sorted(transitions.items())],
        newly_feasible=sum(n for (a,b),n in transitions.items() if a!="feasible" and b=="feasible"),
        newly_rejected=sum(n for (a,b),n in transitions.items() if a=="feasible" and b!="feasible"),
        original_best_by_arch=winners[0],corrected_best_by_arch=winners[1],
        original_best=feasible[0][0] if feasible[0] else None,
        corrected_best=feasible[1][0] if feasible[1] else None,
        fanout_examples=tests,
        limitations=[
            "Only two pump fanout expressions changed; all other original model limitations remain.",
            "Analytic feasibility only; no AI convergence gate or physical device validation.",
            "Rank IDs are not stable across sweeps; compare full configuration keys.",
            "Equal splitter assumption and original amplifier, receiver, timing, power and area models retained.",
            "Fanout examples are algebraic controls, not measured devices.",
            "Electronic baseline remains an assumption, not a matched measured benchmark."])
    (OUT/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,allow_nan=False))
    if result["failures"]:
        raise SystemExit("paired sweep failed: "+", ".join(result["failures"]))

if __name__=="__main__":
    main()
