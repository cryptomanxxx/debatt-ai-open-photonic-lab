"""G-004B: frozen G-004A workload, optical readout and conditional break-even.
No hardware power measurement. Fallback uses the tested compiled CPU method.
"""
import csv
import hashlib
import json
import tempfile
from pathlib import Path

import numpy as np
from photonic_side_v004 import dataset, optical, ideal
from boundary_readout_v005 import CONFIGS, exact_geometry
from electronic_baseline_v006 import compile_kernel, errors

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "results/ci-originals/opa-g-004a/45841325612-15128251841"
OUT = ROOT / "results/opa-g-004b"
SEED = 20261204
REPEATS = 3
PANELS = ("uniform", "translated", "boundary", "scene_like")
# Explicit hypothetical sensitivity axes, not component specifications.
SIDE_PJ = (1., 10., 100.)
GUARD_PJ = (1., 10.)
CPU_PJ = (10., 100., 1000.)
UTILIZATION = (.1, 1.)
STATIC_W = (.01, .1)
SIDE_RATE = 1e9


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load():
    provenance = json.loads((SOURCE/"archive-provenance.json").read_text())
    for name in ("workload.csv","workload-manifest.json","results.csv","result.json"):
        data = (SOURCE/name).read_bytes()
        meta = provenance["files"][name]
        assert len(data)==meta["bytes"] and sha(data)==meta["sha256"]
    manifest=json.loads((SOURCE/"workload-manifest.json").read_text())
    assert sha((SOURCE/"workload.csv").read_bytes())==manifest["csv_sha256"]
    groups={}
    with (SOURCE/"workload.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            key=(row["split"],row["panel"])
            items=groups.setdefault(key,[])
            assert int(row["pair_id"])==len(items)
            case=[float(row[f"{v}_{ax}"]) for v in ("o","d","lo","hi") for ax in "xyz"]
            items.append((case,int(row["hit"]),int(row["guard"]),int(row["side_tests"])))
    data={}
    for m in manifest["panels"]:
        key=(m["split"],m["panel"])
        items=groups[key]
        a=np.array([v[0] for v in items],dtype="<f8").reshape(-1,4,3)
        t=np.array([v[1] for v in items],dtype=bool)
        x,g,truth,guards=dataset(a)
        assert len(a)==m["samples"] and sha(a.tobytes())==m["input_sha256"]
        assert sha(t.astype("u1").tobytes())==m["label_sha256"]
        assert np.array_equal(t,truth) and np.array_equal(guards,[v[2] for v in items])
        assert all(b-a==v[3] for (a,b),v in zip(g,items))
        assert len(x)==m["side_tests"]
        exact=[exact_geometry(case) for case in a]
        assert all(eg==guard and (eg>0 if eg else min(margins)>=0)==bool(label)
                   for (eg,margins),guard,label in zip(exact,guards,t))
        margins=np.array([float(min(ms)) for eg,ms in exact if eg==0])
        data[key]=(a,t,x,g,guards,margins)
    assert set(data)=={(s,p) for s in ("calibration","development","heldout") for p in PANELS}
    return data


def decisions(y, groups, guards, q, policy):
    raw=guards>0
    fallback=np.zeros(len(guards),bool)
    mins=[]
    for i,((a,b),guard) in enumerate(zip(groups,guards)):
        if guard:
            continue
        v=y[a:b]
        minimum=float(np.min(v))
        mins.append(minimum)
        raw[i]=minimum>=0
        fallback[i]=(np.any(abs(v)<=q) if policy=="any_side" else
                     abs(minimum)<=q if policy=="min_window" else
                     policy=="all_optical_fallback")
    return raw,fallback,np.array(mins)


def write(name,rows):
    with (OUT/name).open("w",newline="") as stream:
        w=csv.DictWriter(stream,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)


def main():
    data=load()
    checks={"frozen_input_and_label_identity":True}
    rows=[];cost=[]
    with tempfile.TemporaryDirectory() as tmp:
        cpu,compiler=compile_kernel(tmp)
        if cpu is None:
            raise RuntimeError("Compiled fallback required")
        fallback_predictions={k:cpu(np.ascontiguousarray(v[0],dtype=np.float64)) for k,v in data.items()}
        for k,v in data.items():
            checks["cpu_"+ "_".join(k)]=bool(np.array_equal(fallback_predictions[k],v[1]))
        for j,(scenario,s,b,p,l,n) in enumerate(CONFIGS):
            for rep in range(REPEATS):
                rng=np.random.default_rng(np.random.SeedSequence([SEED,j,rep]))
                bias=rng.uniform(-b,b,4)
                def read(x):
                    return optical(x,s,bias,np.array([0.,p]),np.array([0.,l]),rng.normal(0,n,len(x)))
                u=rng.uniform(-1,1,(8192,4))
                r=read(u)
                gain,offset=np.linalg.lstsq(np.column_stack([r,np.ones(len(r))]),ideal(u),rcond=None)[0]
                assert np.isfinite(gain) and gain>0 and np.isfinite(offset)
                uq=float(np.quantile(abs(gain*r+offset-ideal(u)),.99))
                cal_res=[]
                for panel in PANELS:
                    _,t,x,g,guards,exact=data["calibration",panel]
                    _,_,mins=decisions(gain*read(x)+offset,g,guards,0,"raw")
                    cal_res.extend(abs(mins-exact))
                gq=float(np.quantile(cal_res,.99))
                # Frozen conservative maximum is a separate calibration-only candidate,
                # not a statistical guarantee; no held-out tuning.
                gmax=float(max(cal_res))
                for split in ("development","heldout"):
                    for panel in PANELS:
                        key=(split,panel)
                        a,t,x,g,guards,exact=data[key]
                        cp=fallback_predictions[key]
                        y=gain*read(x)+offset
                        for policy,q,mode in [("raw",0.,"raw"),
                            ("uniform_q99_any",uq,"any_side"),("uniform_q99_min",uq,"min_window"),
                            ("geometry_q99_any",gq,"any_side"),("geometry_q99_min",gq,"min_window"),
                            ("geometry_max_min",gmax,"min_window"),("all_optical_fallback",0.,"all_optical_fallback"),
                            ("electronic_only",0.,"electronic_only")]:
                            raw,f,mins=decisions(y,g,guards,q,mode)
                            pred=np.where(f,cp,raw)
                            if mode=="electronic_only":
                                pred=cp;raw=cp;f[:]=False
                            opt=int(np.sum(guards==0)) if mode!="electronic_only" else 0
                            sides=len(x) if opt else 0
                            fb=int(np.sum(f))
                            err=errors(pred,t);rawerr=errors(raw,t)
                            rows.append(dict(scenario=scenario,repeat=rep,split=split,panel=panel,policy=policy,
                                threshold=q,gain=float(gain),offset=float(offset),
                                **err,raw_fp=rawerr["fp"],raw_fn=rawerr["fn"],
                                guard_cases=len(t)-int(np.sum(guards==0)) if opt else 0,
                                optical=opt,side_tests=sides,fallback=fb,
                                correct=len(t)-err["fp"]-err["fn"],
                                coverage=float(np.mean(abs(mins-exact)<=q)) if len(exact) and opt else None))
        # Strict global quality gate across every held-out panel and repeat per
        # scenario/policy. A single failure makes the whole candidate ineligible.
        eligible={}
        for row in rows:
            if row["split"]=="heldout":
                k=(row["scenario"],row["policy"])
                eligible[k]=eligible.get(k,True) and row["fp"]==row["fn"]==0
        for row in rows:
            row["matched_quality"]=eligible[(row["scenario"],row["policy"])]
            if row["split"]!="heldout":
                continue
            N=row["samples"]; F=row["fallback"]; S=row["side_tests"]
            for side in SIDE_PJ:
                for guard in GUARD_PJ:
                    for cpu_pj in CPU_PJ:
                        for util in UTILIZATION:
                            for static in STATIC_W:
                                # Partial sensitivity only: side dynamic lumps four DAC/driver
                                # lanes, detector/TIA and two comparisons into one input.
                                # Static source/idle proxy amortized at assumed side rate.
                                # CPU energy/test is hypothetical, not inferred from timing.
                                electronic=N*cpu_pj
                                if row["policy"]=="electronic_only":
                                    total=electronic;static_pj=0.;dynamic_pj=0.;guard_total=0.;fallback_total=0.
                                else:
                                    static_pj=static*S/(SIDE_RATE*util)*1e12
                                    dynamic_pj=S*side
                                    guard_total=N*guard
                                    fallback_total=F*cpu_pj
                                    total=static_pj+dynamic_pj+guard_total+fallback_total
                                correct=row["correct"]
                                cost.append(dict(scenario=row["scenario"],repeat=row["repeat"],panel=row["panel"],
                                    policy=row["policy"],matched_quality=row["matched_quality"],
                                    side_pj=side,guard_pj=guard,cpu_pj=cpu_pj,utilization=util,static_w=static,
                                    dynamic_pj=dynamic_pj,static_pj=static_pj,guard_total_pj=guard_total,
                                    fallback_total_pj=fallback_total,total_partial_pj=total,
                                    partial_pj_per_correct=total/correct if correct else None,
                                    electronic_reference_pj=electronic,
                                    max_unmodeled_overhead_pj=electronic-total if row["matched_quality"] else None))
    checks["accounting"]=all(r["samples"]==r["hits"]+r["misses"] and
        0<=r["fallback"]<=r["optical"] and 0<=r["correct"]<=r["samples"] and
        r["fp"]<=r["misses"] and r["fn"]<=r["hits"] for r in rows)
    checks["all_fallback_control"]=all(r["fp"]==r["fn"]==0 and r["fallback"]==r["optical"]
        for r in rows if r["policy"]=="all_optical_fallback")
    checks["electronic_control"]=all(r["fp"]==r["fn"]==r["side_tests"]==r["fallback"]==0
        for r in rows if r["policy"]=="electronic_only")
    checks["finite_costs"]=all(np.isfinite(r["total_partial_pj"]) and r["total_partial_pj"]>=0 for r in cost)
    checks["cost_identity"]=all(np.isclose(r["total_partial_pj"],
        r["electronic_reference_pj"] if r["policy"]=="electronic_only" else
        r["dynamic_pj"]+r["static_pj"]+r["guard_total_pj"]+r["fallback_total_pj"]) for r in cost)
    OUT.mkdir(parents=True,exist_ok=True)
    write("results.csv",rows);write("cost-sensitivity.csv",cost)
    result=dict(experiment="opa-g-004b",checks=checks,passed=all(checks.values()),
        seed=SEED,repeats=REPEATS,rows=len(rows),cost_rows=len(cost),compiler=compiler,
        quality_gate=[dict(scenario=k[0],policy=k[1],eligible=v) for k,v in sorted(eligible.items())],
        workload_source=str(SOURCE.relative_to(ROOT)),gpu="not_run",energy="not_measured",
        limitations=["Normalized optical behavior; no physical tolerance or guaranteed confidence bound",
            "Actual compiled CPU fallback validated on frozen workload; no measured hybrid timing",
            "Partial illustrative energy sensitivity only; no measured CPU or optical power",
            "Side cost lumps conversion/driver/receiver/comparators; no selected physical components",
            "Static laser/LO and idle proxy; assumed rate and utilization, not measured",
            "DMA/BVH memory, normalization beyond guard proxy, digital aggregation, calibration, tuning, host and cooling not accounted separately",
            "No full-system ranking or claimed energy advantage"])
    (OUT/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if not result["passed"]:
        raise SystemExit("G-004B numerical gate failed")


if __name__=="__main__":
    main()
