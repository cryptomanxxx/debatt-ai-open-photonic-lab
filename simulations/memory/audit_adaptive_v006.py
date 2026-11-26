"""Read-only W-002E audit; aggregate records cannot identify individual states."""
import argparse
import csv
import hashlib
import itertools
import json
import math
from collections import defaultdict
from pathlib import Path

RUN=45905192736
ARTIFACT=15157223437
SOURCE="f153327f6ab4d440936ef6fe001a0f544f021276"
DIGEST="c48d503dc640f32ad330c22f9a5d422afe8bbf2816861848497126a638de81fe"
FILES={"development.csv","heldout.csv","summary.csv","result.json","environment-lock.txt","installed-packages.json"}
REFS=(4,16)
CADENCES=(1,4,16)
POLICIES=("always","adaptive")
GATES=(1.,2.,3.)
SEEDS=tuple(range(22001,22017))
DEV=tuple(range(21001,21005))
PARAMS=("program_sigma","read_sigma","common_sigma","independent_ref_sigma","correlated_ref_sigma","adc_bits")
GRID=tuple(itertools.product((0.,.005,.01),(0.,.005,.01),(0.,.005,.02),(0.,.005,.02),(0.,.01),(8,12)))
N=32768
STATE_N=2048
TARGET=.001


def require(ok,msg):
    if not ok:
        raise ValueError(msg)


def close(a,b):
    return math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-12)


def flag(s):
    require(s in ("True","False"),"boolean value")
    return s=="True"


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


def read(root,name):
    with (root/name).open(newline="") as f:
        yield from csv.DictReader(f)


def key(r):
    return (int(r["seed"]),*(float(r[x]) for x in PARAMS[:-1]),int(r["adc_bits"]))


def check_rates(ser,ber,worst):
    require(all(math.isfinite(x) for x in (ser,ber,worst)),"nonfinite rates")
    require(0<=ser<=1 and ser/4<=ber+1e-12 and ber<=ser+1e-12,"rate bounds")
    require(ser<=worst+1e-12 and 0<=worst<=min(1,ser*16)+1e-12,"worst bounds")
    require(all(close(x,round(x)) for x in (ser*N,ber*4*N,worst*STATE_N)),"count grid")
    return worst<=TARGET


def selected_gates(rows):
    losses={}
    for r in rows:
        k=(int(r["references"]),int(r["cadence"]),float(r["gate"]))
        v=int(r["symbol_errors"])
        require(k not in losses and 0<=v<=len(DEV)*len(GRID)*N,"development row")
        losses[k]=(v,flag(r["selected"]))
    require(set(losses)==set(itertools.product(REFS,CADENCES,GATES)),"development coverage")
    chosen={}
    for n,c in itertools.product(REFS,CADENCES):
        g=min(GATES,key=lambda g:(losses[n,c,g][0],-g))
        require(all(losses[n,c,x][1]==(x==g) for x in GATES),"development selection")
        chosen[n,c]=g
    return chosen


def parse_row(r,chosen):
    k=key(r); n=int(r["references"]); c=int(r["cadence"]); p=r["policy"]
    require(n in REFS and c in CADENCES and p in POLICIES,"configuration")
    require((r["gate"]=="" if p=="always" else float(r["gate"])==chosen[n,c]),"frozen gate")
    ser,ber,worst=(float(r[x]) for x in ("ser","ber","worst_state_ser"))
    bser,bber,bworst=(float(r["baseline_"+x]) for x in ("ser","ber","worst_state_ser"))
    cp=check_rates(ser,ber,worst); bp=check_rates(bser,bber,bworst)
    require(int(r["samples"])==N and close(int(r["symbol_errors"]),ser*N)
            and close(int(r["bit_errors"]),ber*4*N),"error counts")
    require(cp==flag(r["point_pass"]) and bp==flag(r["baseline_pass"])
            and flag(r["rescued"])==(not bp and cp) and flag(r["regressed"])==(bp and not cp),"point decisions")
    acq=64//c; extra=acq*n*8; enabled=int(r["enabled_steps"])
    require(int(r["acquisitions"])==acq and int(r["reference_reads"])==extra
            and int(r["calibration_reference_reads"])==n*8 and close(r["read_overhead"],extra/N)
            and 0<=enabled<=64 and enabled%c==0,"read accounting")
    clip=int(r["data_clipped"])
    residual=float(r["mean_abs_residual"]); drift=float(r["baseline_mean_abs_drift"])
    require(0<=clip<=N and math.isfinite(residual) and math.isfinite(drift)
            and residual>=0 and drift>=0,"drift diagnostics")
    if enabled==0:
        require(close(residual,drift) and close(ser,bser) and close(ber,bber)
                and close(worst,bworst),"disabled correction identity")
    return k,(n,c,p),dict(ser=ser,ber=ber,worst=worst,passed=cp,
        baseline=(bser,bber,bworst,bp,clip,drift),extra=extra,enabled=enabled,residual=residual)


def aggregate(items):
    return dict(trajectories=len(items),baseline_pass=sum(x["baseline"][3] for x in items),
        corrected_pass=sum(x["passed"] for x in items),
        rescued=sum(not x["baseline"][3] and x["passed"] for x in items),
        regressed=sum(x["baseline"][3] and not x["passed"] for x in items),
        mean_ser=sum(x["ser"] for x in items)/len(items),
        baseline_mean_ser=sum(x["baseline"][0] for x in items)/len(items),
        mean_worst_ser=sum(x["worst"] for x in items)/len(items),
        baseline_mean_worst_ser=sum(x["baseline"][2] for x in items)/len(items),
        mean_abs_residual=sum(x["residual"] for x in items)/len(items),
        mean_enabled_steps=sum(x["enabled"] for x in items)/len(items),
        read_overhead=items[0]["extra"]/N)


def compare(items):
    pairs=len(items)
    return dict(trajectories=pairs,
        adaptive_pass=sum(b["passed"] for a,b in items),
        always_pass=sum(a["passed"] for a,b in items),
        adaptive_only_pass=sum(not a["passed"] and b["passed"] for a,b in items),
        always_only_pass=sum(a["passed"] and not b["passed"] for a,b in items),
        both_pass=sum(a["passed"] and b["passed"] for a,b in items),
        both_fail=sum(not a["passed"] and not b["passed"] for a,b in items),
        adaptive_lower_ser=sum(b["ser"]<a["ser"] for a,b in items),
        adaptive_higher_ser=sum(b["ser"]>a["ser"] for a,b in items),
        adaptive_lower_ser_higher_worst=sum(b["ser"]<a["ser"] and b["worst"]>a["worst"] for a,b in items),
        adaptive_lower_ser_lost_pass=sum(b["ser"]<a["ser"] and a["passed"] and not b["passed"] for a,b in items),
        mean_ser_delta=sum(b["ser"]-a["ser"] for a,b in items)/pairs,
        mean_worst_delta=sum(b["worst"]-a["worst"] for a,b in items)/pairs,
        read_overhead=items[0][0]["extra"]/N)


def write(out,name,rows):
    with (out/name).open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)


def analyze(root,out):
    verify(root)
    report=json.loads((root/"result.json").read_text())
    require(report["passed"] is True and report["experiment"]=="OPA-W-002E"
            and report["physical_measurement"] is False and report["material_fit"] is False
            and report["development_seeds"]==list(DEV) and report["heldout_seeds"]==list(SEEDS)
            and report["scenarios"]==len(GRID) and report["steps"]==64
            and report["writes_per_state"]==32,"source scope")
    chosen=selected_gates(read(root,"development.csv"))
    expected={(s,*params) for s in SEEDS for params in GRID}
    configs=set(itertools.product(REFS,CADENCES,POLICIES))
    data=defaultdict(dict)
    for r in read(root,"heldout.csv"):
        k,c,x=parse_row(r,chosen)
        require(k in expected and c not in data[k],"trajectory identity")
        data[k][c]=x
    require(set(data)==expected and len(data)==report["heldout_trajectories"]==5184,"trajectory coverage")
    groups=defaultdict(list); pairs=defaultdict(list); strata=defaultdict(list)
    for k,records in sorted(data.items()):
        require(set(records)==configs,"policy coverage")
        base=records[4,1,"always"]["baseline"]
        for c,x in records.items():
            require(x["baseline"]==base,"baseline mismatch")
            groups[c].append(x)
        for n,c in itertools.product(REFS,CADENCES):
            a,b=records[n,c,"always"],records[n,c,"adaptive"]
            require(a["extra"]==b["extra"],"unmatched cost")
            pairs[n,c].append((a,b))
            for label,v in zip(PARAMS,k[1:]):
                strata[n,c,label,v].append((a,b))
            strata[n,c,"joint_common_correlated",str((k[3],k[5]))].append((a,b))
    require(sum(map(len,groups.values()))==report["paired_rows"]==62208,"row count")
    source={(x["references"],x["cadence"],x["policy"]):x for x in report["summary"]}
    source_csv={}
    for r in read(root,"summary.csv"):
        k=(int(r["references"]),int(r["cadence"]),r["policy"])
        require(k not in source_csv,"duplicate summary")
        source_csv[k]=r
    require(set(source)==set(source_csv)==configs,"summary coverage")
    summaries=[]
    for (n,c,p),items in sorted(groups.items()):
        x=aggregate(items)
        for f in ("trajectories","baseline_pass","corrected_pass","rescued","regressed",
                  "mean_ser","baseline_mean_ser","read_overhead"):
            require(close(x[f],source[n,c,p][f]) and close(x[f],source_csv[n,c,p][f]),"summary mismatch")
        summaries.append(dict(references=n,cadence=c,policy=p,**x))
    paired=[dict(references=n,cadence=c,**compare(items)) for (n,c),items in sorted(pairs.items())]
    sliced=[dict(references=n,cadence=c,parameter=label,value=v,**compare(items))
            for (n,c,label,v),items in sorted(strata.items())]
    write(out,"policy_summary.csv",summaries);write(out,"matched.csv",paired);write(out,"strata.csv",sliced)
    return dict(passed=True,experiment="OPA-W-002F",verified_files=len(FILES),
        trajectories=len(data),paired_policy_rows=62208,matched_comparisons=31104,
        selected_gates=[dict(references=n,cadence=c,gate=g) for (n,c),g in sorted(chosen.items())],
        matched=paired,strata_rows=len(sliced),physical_measurement=False,material_fit=False,
        limitations=["Aggregate archive audit only; no raw samples, per-state identities or estimator replay",
            "Tail metric is worst state over a trajectory, not probability of future failure",
            "Correlated mismatch strata are descriptive, not causal identification",
            "No new policy selection or held-out tuning; no physical energy or time"])


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
