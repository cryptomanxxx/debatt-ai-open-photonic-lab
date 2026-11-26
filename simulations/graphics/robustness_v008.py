"""G-004B2: prospective optical robustness, separate selection and confirmation."""
import csv
import hashlib
import json
import tempfile
from pathlib import Path
import numpy as np
from electronic_baseline_v006 import panels, compile_kernel, errors, digest
from boundary_readout_v005 import CONFIGS, exact_geometry
from photonic_side_v004 import dataset, optical, ideal
from matched_optical_v007 import SOURCE, decisions

OUT=Path(__file__).resolve().parents[2]/"results/opa-g-004b2"
SEEDS={"calibration":20261301,"development":20261302,"heldout":20261303}
NOISE_SEED=20261304
REPEATS=10
SCENARIOS=(*CONFIGS,("drift_quantization",.15,.01,.15,1.,.005))
CANDIDATES=("max_min","max_min_125","max_min_150","max_min_200","side_max")
POLICIES=(*CANDIDATES,"all_optical_fallback","electronic_only")
COLS=[f"{v}_{ax}" for v in ("o","d","lo","hi") for ax in "xyz"]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def extra(seed):
    rng=np.random.default_rng(seed+700)
    n=1024
    lo=rng.integers(-32,33,(n,3))/8
    hi=lo+rng.integers(1,17,(n,3))/8
    o=lo+rng.integers(-16,17,(n,3))/8
    d=rng.integers(-8,9,(n,3))/8
    d[:,0]=rng.choice([-1.,1.],n)*np.exp2(-rng.integers(12,45,n))
    yield "near_parallel",np.stack((o,d,lo,hi),axis=1)
    # Dyadic anisotropy preserves represented coordinates; avoids overflow.
    scale=np.exp2(rng.integers(-20,21,(n,3)))
    yield "dynamic_range",np.stack((o*scale,d*scale,lo*scale,hi*scale),axis=1)

def freeze():
    prior=SOURCE/"workload.csv"
    manifest=json.loads((SOURCE/"archive-provenance.json").read_text())
    assert sha(prior)==manifest["files"]["workload.csv"]["sha256"]
    with prior.open(newline="") as f:
        old={tuple(float(row[c]) for c in COLS) for row in csv.DictReader(f)}
    seen=set(old); data={}; meta=[]
    path=OUT/"workload.csv"
    with path.open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["split","panel","pair_id",*COLS,"hit","guard","side_tests"])
        for split,seed in SEEDS.items():
            for panel,cases in (*panels(seed),*extra(seed)):
                kept=[]
                for case in cases:
                    key=tuple(map(float,case.flat))
                    if key not in seen:
                        seen.add(key);kept.append(case)
                a=np.ascontiguousarray(kept,dtype="<f8").reshape(-1,4,3)
                assert len(a)>0
                x,g,t,guards=dataset(a)
                exact=[exact_geometry(case) for case in a]
                assert all(eg==gg and (eg>0 if eg else min(ms)>=0)==bool(label)
                    for (eg,ms),gg,label in zip(exact,guards,t))
                assert all(b-a==len(ms) for (a,b),(_,ms) in zip(g,exact))
                side_truth=np.array([float(m) for _,ms in exact for m in ms])
                min_truth=np.array([float(min(ms)) for eg,ms in exact if eg==0])
                assert len(x)==len(side_truth)
                for i,(case,label,guard,(u,v)) in enumerate(zip(a,t,guards,g)):
                    w.writerow([split,panel,i,*map(repr,map(float,case.flat)),int(label),int(guard),v-u])
                data[split,panel]=(a,x,g,t,guards,side_truth,min_truth)
                meta.append(dict(split=split,panel=panel,seed=seed,generated=len(cases),samples=len(a),
                    removed=len(cases)-len(a),hits=int(t.sum()),misses=int((~t).sum()),
                    guards=int((guards!=0).sum()),optical=int((guards==0).sum()),side_tests=len(x),
                    input_sha256=digest(a),label_sha256=digest(t.astype("u1"))))
    assert len(seen)-len(old)==sum(len(v[0]) for v in data.values())
    with path.open(newline="") as f:
        reader=csv.DictReader(f)
        for (split,panel),(a,x,g,t,guards,_,_) in data.items():
            for i,case in enumerate(a):
                row=next(reader)
                assert (row["split"],row["panel"],int(row["pair_id"]))==(split,panel,i)
                assert np.array_equal(np.array([float(row[c]) for c in COLS]),case.ravel())
                assert int(row["hit"])==int(t[i]) and int(row["guard"])==int(guards[i])
                assert int(row["side_tests"])==g[i][1]-g[i][0]
        assert next(reader,None) is None
    (OUT/"workload-manifest.json").write_text(json.dumps(dict(seeds=SEEDS,prior_sha256=sha(prior),
        csv_sha256=sha(path),panels=meta),indent=2)+"\n")
    return data

def prepare(data,j,rep):
    name,s,b,p,l,n=SCENARIOS[j]
    rng=np.random.default_rng(np.random.SeedSequence([NOISE_SEED,j,rep,0]))
    bias=rng.uniform(-b,b,4)
    def read(x,stage,panel):
        # Independent streams by split and panel; paired across candidate policies.
        gen=np.random.default_rng(np.random.SeedSequence([NOISE_SEED,j,rep,stage,panel]))
        q=x
        drift=np.zeros(4)
        if name=="drift_quantization":
            q=np.rint(x*2047)/2047 # signed normalized 12-bit operand grid
            if stage>=2:
                drift=gen.uniform(-.002,.002,4)
        y=optical(q,s,bias+drift,np.array([0.,p]),np.array([0.,l]),gen.normal(0,n,len(x)))
        return y,q
    u=rng.uniform(-1,1,(8192,4))
    y,_=read(u,0,1)
    gain,offset=np.linalg.lstsq(np.column_stack([y,np.ones(len(y))]),ideal(u),rcond=None)[0]
    assert np.isfinite(gain) and gain>0 and np.isfinite(offset)
    mr=[];sr=[]
    for i,((split,panel),(_,x,g,t,guards,st,mt)) in enumerate(data.items()):
        if split!="calibration":continue
        y,_=read(x,1,i)
        y=gain*y+offset
        _,_,mins=decisions(y,g,guards,0,"raw")
        mr.extend(abs(mins-mt));sr.extend(abs(y-st))
    mx=float(max(mr));sx=float(max(sr))
    thresholds=dict(zip(CANDIDATES,[mx,mx*1.25,mx*1.5,mx*2,sx]))
    return read,float(gain),float(offset),thresholds

def evaluate(data,cp,models,split):
    rows=[]
    for (j,rep),(read,gain,offset,qs) in models.items():
        name=SCENARIOS[j][0]
        for i,((sp,panel),(a,x,g,t,guards,st,mt)) in enumerate(data.items()):
            if sp!=split:continue
            y,q=read(x,2 if sp=="development" else 3,i)
            y=gain*y+offset
            quant,_,_=decisions(ideal(q),g,guards,0,"raw")
            unquant,_,_=decisions(ideal(x),g,guards,0,"raw")
            qe=errors(quant,t);ue=errors(unquant,t)
            # Direct decision changes from operand quantization, distinct from raw input rounding.
            changed=int(np.sum(quant!=unquant))
            cpu=cp[sp,panel];ce=errors(cpu,t)
            for policy in POLICIES:
                threshold=qs.get(policy,0.)
                mode=("any_side" if policy=="side_max" else "min_window") if policy in CANDIDATES else policy
                raw,f,_=decisions(y,g,guards,threshold,mode)
                pred=np.where(f,cpu,raw)
                opt=int(np.sum(guards==0));sides=len(x)
                if policy=="electronic_only":
                    pred=raw=cpu;f[:]=False;opt=sides=0
                e=errors(pred,t);re=errors(raw,t)
                rows.append(dict(split=sp,scenario=name,repeat=rep,panel=panel,policy=policy,
                    threshold=threshold,gain=gain,offset=offset,**e,
                    raw_fp=re["fp"],raw_fn=re["fn"],cpu_fp=ce["fp"],cpu_fn=ce["fn"],
                    ideal_operand_fp=ue["fp"],ideal_operand_fn=ue["fn"],
                    quantized_operand_fp=qe["fp"],quantized_operand_fn=qe["fn"],
                    quantization_decision_changes=changed,
                    guards=len(t)-int(np.sum(guards==0)) if opt else 0,
                    optical=opt,side_tests=sides,fallback=int(f.sum())))
    return rows

def assess(rows,policy):
    selected=[r for r in rows if r["policy"]==policy]
    scenarios={}
    for r in selected:
        v=scenarios.setdefault(r["scenario"],[0,0])
        v[0]+=r["fallback"];v[1]+=r["optical"]
    rates={k:f/o if o else 1. for k,(f,o) in scenarios.items()}
    zero=all(r["fp"]==r["fn"]==r["cpu_fp"]==r["cpu_fn"]==0 for r in selected)
    useful=all(f<o for f,o in scenarios.values())
    return dict(policy=policy,zero_errors_and_cpu_matched=zero,
        useful_every_scenario=useful,eligible=zero and useful,
        worst_scenario_fallback=max(rates.values()),scenario_fallback=rates,
        worst_panel_fallback=max((r["fallback"]/r["optical"] for r in selected if r["optical"]),default=None))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    data=freeze()
    with tempfile.TemporaryDirectory() as tmp:
        cpu,compiler=compile_kernel(tmp)
        assert cpu is not None
        cp={k:cpu(np.ascontiguousarray(v[0],dtype=np.float64)) for k,v in data.items()}
        models={(j,rep):prepare(data,j,rep) for j in range(len(SCENARIOS)) for rep in range(REPEATS)}
        dev=evaluate(data,cp,models,"development")
        candidates=[assess(dev,p) for p in CANDIDATES]
        eligible=[v for v in candidates if v["eligible"]]
        winner=min(eligible,key=lambda v:v["worst_scenario_fallback"])["policy"] if eligible else None
        # Persist development-only choice before any heldout optical evaluation.
        selection=dict(selected=winner,candidates=candidates,tie_order=list(CANDIDATES))
        (OUT/"selection.json").write_text(json.dumps(selection,indent=2)+"\n")
        held=evaluate(data,cp,models,"heldout")
    confirmation=assess(held,winner) if winner else None
    rows=dev+held
    checks=dict(frozen_disjoint_roundtrip=True,
        complete_rows=len(rows)==2*6*len(SCENARIOS)*REPEATS*len(POLICIES),
        accounting=all(r["samples"]==r["hits"]+r["misses"] and 0<=r["fallback"]<=r["optical"]
            and r["fp"]<=r["misses"] and r["fn"]<=r["hits"] for r in rows),
        electronic_control=all(r["fp"]==r["cpu_fp"] and r["fn"]==r["cpu_fn"] and r["side_tests"]==0
            for r in rows if r["policy"]=="electronic_only"),
        all_fallback_control=all(r["fallback"]==r["optical"] for r in rows if r["policy"]=="all_optical_fallback"))
    with (OUT/"results.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    report=dict(experiment="opa-g-004b2",checks=checks,passed=all(checks.values()),
        scientific_gate=bool(confirmation and confirmation["eligible"]),confirmation=confirmation,
        selected=winner,development=candidates,heldout_diagnostics=[assess(held,p) for p in CANDIDATES],
        compiler=compiler,calibration_cpu_errors={p:errors(cp["calibration",p],v[3])
            for (s,p),v in data.items() if s=="calibration"},
        repeats=REPEATS,noise_seed=NOISE_SEED,rows=len(rows),gpu="not_run",energy="not_measured",
        limitations=["Synthetic geometries, repeated noise is not independent geometry",
            "Normalized 12-bit operand quantization, not raw coordinate quantization or actual DAC ENOB",
            "Hypothetical per-panel bias drift ±.002 rad after calibration",
            "Compiled CPU mismatch disqualifies candidate on that panel; no oracle substitution",
            "Calibration per modeled device/repeat, no scenario-dependent policy selector",
            "No energy ranking, hybrid timing or physical measurements"])
    (OUT/"result.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if not report["passed"]:raise SystemExit("G-004B2 implementation gate failed")

if __name__=="__main__":
    main()
