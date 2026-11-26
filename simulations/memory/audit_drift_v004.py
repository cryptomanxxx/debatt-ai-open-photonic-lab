"""Read-only W-002C archive audit and acquisition-count sensitivity."""
import argparse
import csv
import hashlib
import itertools
import json
import math
from collections import defaultdict, Counter
from pathlib import Path

RUN=45903062662
ARTIFACT=15156368734
SOURCE="f5064f96dc487c6ac9cca48fbbd7ab9c2bad91f3"
DIGEST="f20271f78a3d7e85b6d56d771c4f333eccd390f4f744f8ea7ab349509dce199b"
FILES={"baseline.csv","paired.csv","summary.csv","result.json","environment-lock.txt","installed-packages.json"}
SEEDS=tuple(range(11001,11017))
SIGMAS=(0.,.002,.005,.01,.02)
DRIFTS=(0.,.005,.02)
ADCS=(6,8,12)
REFS=(1,4,16)
MISMATCH=(0.,.005,.02)
TARGET=.001
READS=65536
OUTCOMES=("both_pass","rescued","regressed","both_fail")


def require(ok,msg):
    if not ok:
        raise ValueError(msg)


def close(a,b):
    return math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-12)


def verify(root):
    p=json.loads((root/"archive-provenance.json").read_text())
    require((p["workflow_run_id"],p["artifact_id"],p["source_head_sha"],p["artifact_sha256"])
            ==(RUN,ARTIFACT,SOURCE,DIGEST),"archive identity")
    require(set(p["files"])==FILES,"file set")
    for n,f in p["files"].items():
        b=(root/n).read_bytes()
        require(len(b)==f["bytes"],n+" size")
        require(hashlib.sha256(b).hexdigest()==f["sha256"],n+" SHA256")
        require(hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()==f["git_blob_sha1"],n+" blob")


def key(r):
    return (int(r["seed"]),float(r["program_sigma"]),float(r["read_sigma"]),
            float(r["drift_sigma"]),int(r["adc_bits"]))


def flag(s):
    require(s in ("True","False"),"boolean value")
    return s=="True"


def outcome(a,b):
    return "both_pass" if a and b else "rescued" if b else "regressed" if a else "both_fail"


def metric(r):
    n,se,be=(int(r[x]) for x in ("samples","symbol_errors","bit_errors"))
    worst=float(r["worst_state_ser"])
    require(n==READS and 0<=se<=n and se<=be<=4*se,"error counts")
    require(close(r["ser"],se/n) and close(r["ber"],be/(4*n)),"rate arithmetic")
    require(0<=worst<=1 and worst+1e-12>=se/n and worst<=min(1,se/4096)+1e-12
            and close(worst*4096,round(worst*4096)),"worst-state bounds")
    return worst<=TARGET


def read_rows(root,name):
    with (root/name).open(newline="") as f:
        yield from csv.DictReader(f)


def aggregate(items):
    counts=Counter(x["outcome"] for x in items)
    return dict(panels=len(items),**{k:counts[k] for k in OUTCOMES},
                baseline_pass=counts["both_pass"]+counts["regressed"],
                corrected_pass=counts["both_pass"]+counts["rescued"],
                net_pass_gain=counts["rescued"]-counts["regressed"],
                mean_abs_residual=sum(abs(x["residual"]) for x in items)/len(items),
                mean_abs_uncorrected=sum(abs(x["drift"]) for x in items)/len(items),
                mean_ser_delta=sum(x["delta"] for x in items)/len(items))


def cost(n,block,ratio):
    # One acquisition of 8 reads per reference per block; calibration separate.
    extra=n*8*math.ceil(READS/block)
    return dict(extra_reads=extra,read_overhead=extra/READS,
                conditional_dynamic_read_energy_ratio=1+ratio*extra/READS)


def frontier(rows):
    # Non-dominated for higher passes, fewer regressions, fewer extra reads.
    def dominates(a,b):
        av=(a["corrected_pass"],-a["regressed"],-a["extra_reads"])
        bv=(b["corrected_pass"],-b["regressed"],-b["extra_reads"])
        return all(x>=y for x,y in zip(av,bv)) and any(x>y for x,y in zip(av,bv))
    return [r for r in rows if not any(dominates(q,r) for q in rows)]


def analyze(root,out):
    verify(root)
    report=json.loads((root/"result.json").read_text())
    require(report["passed"] is True and report["physical_measurement"] is False
            and report["material_fit"] is False and report["point_target"]==TARGET,"source scope")
    expected=set(itertools.product(SEEDS,SIGMAS,SIGMAS,DRIFTS,ADCS))
    base={}
    for r in read_rows(root,"baseline.csv"):
        k=key(r)
        require(k in expected and k not in base,"baseline key")
        require(metric(r)==flag(r["point_screen"]),"baseline decision")
        require(math.isfinite(float(r["actual_drift"])),"baseline drift")
        base[k]=r
    require(set(base)==expected and len(base)==3600==report["baseline_panels"],"baseline coverage")
    seen=set();groups=defaultdict(list);slices=defaultdict(list);combos=defaultdict(list)
    for r in read_rows(root,"paired.csv"):
        k=key(r);n=int(r["references"]);mm=float(r["mismatch_sigma"])
        ident=k+(n,mm)
        require(k in base and n in REFS and mm in MISMATCH and ident not in seen,"pair key")
        seen.add(ident);b=base[k]
        bp=flag(b["point_screen"]);cp=metric(r)
        require(bp==flag(r["baseline_pass"]) and cp==flag(r["corrected_pass"])
                and r["outcome"]==outcome(bp,cp),"pair decision")
        for field in ("ser","ber","worst_state_ser"):
            require(close(r["baseline_"+field],b[field]),"matched baseline "+field)
        drift,estimate,residual=(float(r[x]) for x in ("actual_drift","estimated_drift","residual_drift"))
        require(close(drift,b["actual_drift"]) and close(residual,drift-estimate),"drift accounting")
        require(int(r["data_clipped"])==int(b["data_clipped"]) and 0<=int(r["reference_clipped"])<=n*8,"clipping")
        require(int(r["data_reads"])==READS and int(r["reference_reads"])==n*8
                and int(r["calibration_reference_reads"])==n*8
                and close(r["read_overhead_fraction"],n*8/READS)
                and close(r["useful_read_fraction"],READS/(READS+n*8)),"read accounting")
        item=dict(outcome=outcome(bp,cp),residual=residual,drift=drift,delta=float(r["ser"])-float(b["ser"]))
        groups[n,mm].append(item)
        for label,value in zip(("program_sigma","read_sigma","drift_sigma","adc_bits"),k[1:]):
            slices[n,mm,label,value].append(item)
        combos[n,mm,*k[1:]].append(item)
    require(seen=={k+(n,m) for k in expected for n in REFS for m in MISMATCH}
            and len(seen)==32400==report["paired_rows"],"paired coverage")
    summaries=[];strata=[];combination_rows=[];cost_rows=[];frontiers=[]
    source={(x["references"],x["mismatch_sigma"]):x for x in report["summary"]}
    source_csv={}
    for r in read_rows(root,"summary.csv"):
        k=(int(r["references"]),float(r["mismatch_sigma"]))
        require(k not in source_csv,"duplicate summary")
        source_csv[k]=r
    require(set(source)==set(source_csv)==set(groups),"summary coverage")
    for (n,m),items in sorted(groups.items()):
        a=aggregate(items)
        for f in (*OUTCOMES,"baseline_pass","corrected_pass","net_pass_gain"):
            require(a[f]==source[n,m][f]==int(source_csv[n,m][f]),"summary mismatch")
        summaries.append(dict(references=n,mismatch_sigma=m,**a))
    for (n,m,label,v),items in sorted(slices.items()):
        strata.append(dict(references=n,mismatch_sigma=m,parameter=label,value=v,**aggregate(items)))
    for (n,m,ps,rs,ds,adc),items in sorted(combos.items()):
        require(len(items)==16,"combination seed coverage")
        combination_rows.append(dict(references=n,mismatch_sigma=m,program_sigma=ps,
             read_sigma=rs,drift_sigma=ds,adc_bits=adc,**aggregate(items)))
    for m in MISMATCH:
        candidates=[dict(references=0,mismatch_sigma=m,corrected_pass=sum(flag(r["point_screen"]) for r in base.values()),regressed=0,extra_reads=0)]
        candidates.extend(dict(references=r["references"],mismatch_sigma=m,
             corrected_pass=r["corrected_pass"],regressed=r["regressed"],extra_reads=r["references"]*8)
             for r in summaries if r["mismatch_sigma"]==m)
        frontiers.extend(frontier(candidates))
    for n,block,ratio in itertools.product((0,*REFS),(256,1024,4096,65536),(.5,1.,2.,10.)):
        cost_rows.append(dict(references=n,data_reads_per_acquisition=block,
             assumed_reference_to_data_read_energy_ratio=ratio,**cost(n,block,ratio)))
    for name,rows in (("summary.csv",summaries),("strata.csv",strata),
                      ("combinations.csv",combination_rows),("frontier.csv",frontiers),("cost.csv",cost_rows)):
        with (out/name).open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return dict(passed=True,experiment="OPA-W-002D",verified_files=len(FILES),
        baseline_panels=len(base),paired_rows=len(seen),summary=summaries,frontier=frontiers,
        combination_rows=len(combination_rows),cost_rows=len(cost_rows),
        physical_measurement=False,material_fit=False,
        limitations=["Audit of archived aggregate counts, no raw state samples or confusion matrices",
            "No new estimator fitted; no adaptive selection or held-out policy validation",
            "Cadence sweep is count/conditional energy accounting only, not a drift-time simulation",
            "No measured energy, area, latency or retention; no probability inference across shared seeds"])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive",type=Path);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    try:
        result=analyze(a.archive,a.output)
    except Exception as e:
        result=dict(passed=False,error=str(e))
    (a.output/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2))
    return 0 if result["passed"] else 1


if __name__=="__main__":
    raise SystemExit(main())
