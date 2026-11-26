"""W-002G diagnostic replay, not original W-002E evidence or a new policy."""
import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np
from adaptive_calibration_v005 import trajectory, corrections, TEST, GRID, REFS, CADENCES, STEPS, WRITES
from multilevel_cell_v001 import decode, metrics, TARGET
from audit_adaptive_v006 import verify, read, selected_gates, parse_row, require, close

SOURCE_BLOBS={"adaptive_calibration_v005.py":"94508ac151f19103b70c8a694116327a0f416577",
              "multilevel_cell_v001.py":"26b7ffb6172db8a1d0b4550c7f546fae0180ff7e"}
PARAMS=("program_sigma","read_sigma","common_sigma","independent_ref_sigma","correlated_ref_sigma","adc_bits")


def verify_source():
    for name,digest in SOURCE_BLOBS.items():
        b=Path(__file__).with_name(name).read_bytes()
        require(hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()==digest,
                "source blob mismatch: "+name)


def score(bounds,data,off):
    truth=np.broadcast_to(np.arange(16)[None,:,None],data.shape)
    pred=decode(data-off[:,None,None],bounds)
    conf,m=metrics(truth,pred,4)
    bad=pred!=truth
    step=bad.sum(axis=2)
    counts=step.sum(axis=0)
    require(np.array_equal(counts,conf.sum(axis=1)-np.diag(conf)),"state count agreement")
    require(int(counts.sum())==m["symbol_errors"],"symbol count agreement")
    require(close(counts.max()/(STEPS*WRITES),m["worst_state_ser"]),"worst state agreement")
    return m,counts,step,conf


def state_stats(counts,baseline):
    # All ties retained, including zero-error states.
    return counts>2, (counts>2)&(baseline<=2), (counts<=2)&(baseline>2), counts==counts.max()


def writer(stack,out,name,fields):
    f=stack.enter_context((out/name).open("w",newline=""))
    w=csv.writer(f);w.writerow(fields);return w


def run(root,out):
    from contextlib import ExitStack
    from collections import defaultdict
    verify(root);verify_source()
    chosen=selected_gates(read(root,"development.csv"))
    archived={}
    for row in read(root,"heldout.csv"):
        k,c,x=parse_row(row,chosen)
        require((k,c) not in archived,"duplicate archived row")
        archived[k,c]=x
    expected={(s,*p) for s in TEST for p in GRID}
    configs=[(0,0,"fixed"),*itertools.product(REFS,CADENCES,("always","adaptive"))]
    require(set(archived)=={(k,c) for k in expected for c in configs[1:]},"archive coverage")
    totals=defaultdict(lambda:np.zeros((16,7),dtype=np.int64))
    confusion=defaultdict(lambda:np.zeros((16,16),dtype=np.int64))
    times=defaultdict(lambda:np.zeros((STEPS,16),dtype=np.int64))
    matches=0;state_rows=0;diagnostic_rows=0
    fields=["seed",*PARAMS,"references","cadence","policy"]
    with ExitStack() as stack:
        sw=writer(stack,out,"state_counts.csv",fields+["state","errors","baseline_errors","worst_tie","fails","new_failure","rescued_state"])
        dw=writer(stack,out,"diagnostics.csv",fields+["step","actual_common_drift","applied_offset","enabled","acquired","reference_mean_change","reference_std_change","reference_clipped","symbol_errors"])
        for seed,params in itertools.product(TEST,GRID):
            k=(seed,*params)
            bounds,data,changes,clip,common,data_clip=trajectory(seed,*params)
            bm,bc,bs,bconf=score(bounds,data,np.zeros(STEPS))
            for n,c,p in configs:
                if p=="fixed":
                    off=np.zeros(STEPS);on=np.zeros(STEPS,dtype=bool)
                    m,counts,steps,conf=bm,bc,bs,bconf
                else:
                    off,on=corrections(changes,clip,n,c,None if p=="always" else chosen[n,c])
                    m,counts,steps,conf=score(bounds,data,off)
                    x=archived[k,(n,c,p)]
                    base=x["baseline"]
                    require(all(close(m[f],x[q]) for f,q in (("ser","ser"),("ber","ber"),("worst_state_ser","worst"))),"replay corrected metrics: "+str((k,n,c,p)))
                    require(all(close(bm[f],base[i]) for i,f in enumerate(("ser","ber","worst_state_ser"))),"replay baseline metrics")
                    require((m["worst_state_ser"]<=TARGET)==x["passed"] and (bm["worst_state_ser"]<=TARGET)==base[3],"replay decisions")
                    require(data_clip==base[4] and int(on.sum())==x["enabled"] and close(np.abs(common-off).mean(),x["residual"]) and close(np.abs(common).mean(),base[5]),"replay diagnostics")
                    matches+=1
                fail,new,rescued,worst=state_stats(counts,bc)
                config=(n,c,p)
                # state totals: reads, errors, failing trajectories, new failures,
                # rescued states, worst ties, uniquely worst (nonzero).
                totals[config]+=np.column_stack((np.full(16,STEPS*WRITES),counts,fail,new,rescued,worst,
                    worst & (worst.sum()==1) & (counts>0)))
                confusion[config]+=conf
                times[config]+=steps
                for i in range(16):
                    sw.writerow([*k,*config,i,int(counts[i]),int(bc[i]),int(worst[i]),int(fail[i]),int(new[i]),int(rescued[i])])
                    state_rows+=1
                for t in range(STEPS):
                    acquired=p!="fixed" and t%c==0
                    ref=changes[t,:n] if acquired else None
                    dw.writerow([*k,*config,t,float(common[t]),float(off[t]),int(on[t]),int(acquired),
                        "" if ref is None else float(ref.mean()),"" if ref is None else float(ref.std(ddof=1)),
                        "" if ref is None else int(clip[t,:n].sum()),int(steps[t].sum())])
                    diagnostic_rows+=1
        a=writer(stack,out,"state_summary.csv",["references","cadence","policy","state","reads","errors","failing_trajectories","new_failures","rescued_states","worst_ties","unique_nonzero_worst"])
        b=writer(stack,out,"confusion_summary.csv",["references","cadence","policy","true_state","predicted_state","count"])
        d=writer(stack,out,"step_state_summary.csv",["references","cadence","policy","step","state","reads","errors"])
        for config in configs:
            for i in range(16):
                a.writerow([*config,i,*map(int,totals[config][i])])
                require(int(confusion[config][i].sum())==len(expected)*STEPS*WRITES,"aggregate state coverage")
                require(int(times[config][:,i].sum())==int(totals[config][i,1]),"aggregate time coverage")
                for j in range(16):
                    b.writerow([*config,i,j,int(confusion[config][i,j])])
                for t in range(STEPS):
                    d.writerow([*config,t,i,len(expected)*WRITES,int(times[config][t,i])])
    require(matches==62208 and state_rows==len(expected)*13*16 and diagnostic_rows==len(expected)*13*64,"replay coverage")
    return dict(passed=True,experiment="OPA-W-002G",diagnostic_replay=True,
                source_blobs=SOURCE_BLOBS,verified_archived_policy_rows=matches,
                trajectories=len(expected),state_rows=state_rows,diagnostic_rows=diagnostic_rows,
                configurations=len(configs),numpy_version=np.__version__,physical_measurement=False,
                material_fit=False,limitations=["New replay outputs, not original historical observations",
                "Aggregate agreement does not prove historical sample identity",
                "Per-step state counts aggregated over trajectories; per-trajectory state counts retained",
                "Reference acquisition diagnostics are model values, not measurements",
                "No new gate selection, independent validation or physical time scale"])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive",type=Path);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    try:
        result=run(a.archive,a.output)
    except Exception as e:
        result=dict(passed=False,error=str(e),diagnostic_replay=True)
    (a.output/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2))
    return 0 if result["passed"] else 1


if __name__=="__main__":
    raise SystemExit(main())
