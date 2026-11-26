"""Conditional tail-aware calibration, selected only on fresh development seeds."""
import argparse
import csv
import itertools
import json
from pathlib import Path
import numpy as np
from adaptive_calibration_v005 import trajectory, corrections, GRID, REFS, CADENCES, STEPS, WRITES, REF_READS, FLOOR
from multilevel_cell_v001 import decode, metrics, TARGET
from state_replay_v007 import verify_source
from audit_adaptive_v006 import require

DEV=tuple(range(31001,31005))
TEST=tuple(range(32001,32017))
OLD_GATES={(n,c):2. if (n,c)==(4,4) else 3. for n,c in itertools.product(REFS,CADENCES)}
# Fixed acquisition schedule. A zero gain candidate still pays acquisition cost.
CANDIDATES=((0.,0.,0.),*itertools.product((1.,2.,3.),(.5,1.),(0.,.95)))
PARAMS=("program_sigma","read_sigma","common_sigma","independent_ref_sigma","correlated_ref_sigma","adc_bits")
N=STEPS*16*WRITES


def tail_offsets(changes,clipped,n,c,candidate):
    """Causal dead-zone shrinkage with optional age decay; no test labels or drift."""
    gate,gain,decay=candidate
    offsets=np.zeros(STEPS)
    last=0.
    for t in range(STEPS):
        age=t%c
        if age==0:
            x=changes[t,:n]
            mean=float(x.mean())
            uncertainty=max(FLOOR,float(x.std(ddof=1))/np.sqrt(n))
            last=0. if clipped[t,:n].any() else gain*np.sign(mean)*max(0.,abs(mean)-gate*uncertainty)
        offsets[t]=last*(decay**age if decay else 1.)
    return offsets


def score(bounds,data,off):
    truth=np.broadcast_to(np.arange(16)[None,:,None],data.shape)
    pred=decode(data-off[:,None,None],bounds)
    conf,m=metrics(truth,pred,4)
    state=conf.sum(axis=1)-np.diag(conf)
    require(int(state.sum())==m["symbol_errors"] and int(conf.sum())==N,"state coverage")
    return m,state


def objective(m,state,base_pass):
    passed=m["worst_state_ser"]<=TARGET
    # Maximize point passes first, then minimize lost baseline passes,
    # then worst-state error counts and finally total symbol errors.
    return np.array([-int(passed),int(base_pass and not passed),int(state.max()),m["symbol_errors"]],dtype=np.int64)


def choose(losses):
    return min(losses,key=lambda candidate:(tuple(losses[candidate]),candidate))


def write(out,name,rows):
    with (out/name).open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)


def run(out):
    verify_source()
    require(not set(DEV)&set(TEST),"seed overlap")
    configs=list(itertools.product(REFS,CADENCES))
    losses={cfg:{a:np.zeros(4,dtype=np.int64) for a in CANDIDATES} for cfg in configs}
    for seed,params in itertools.product(DEV,GRID):
        b,d,x,clip,_,_=trajectory(seed,*params)
        bm,_=score(b,d,np.zeros(STEPS))
        bp=bm["worst_state_ser"]<=TARGET
        for n,c in configs:
            for a in CANDIDATES:
                m,state=score(b,d,tail_offsets(x,clip,n,c,a))
                losses[n,c][a]+=objective(m,state,bp)
    chosen={cfg:choose(losses[cfg]) for cfg in configs}
    development=[]
    for (n,c),options in losses.items():
        for a,v in options.items():
            development.append(dict(references=n,cadence=c,gate=a[0],gain=a[1],decay=a[2],
                passes=int(-v[0]),regressions=int(v[1]),worst_errors=int(v[2]),symbol_errors=int(v[3]),
                selected=a==chosen[n,c]))
    write(out,"development.csv",development)
    rows=[]; summaries={}; states={}
    # One row per trajectory/configuration, with all four methods on identical observations.
    for seed,params in itertools.product(TEST,GRID):
        b,d,x,clip,common,_=trajectory(seed,*params)
        bm,bs=score(b,d,np.zeros(STEPS));bp=bm["worst_state_ser"]<=TARGET
        for n,c in configs:
            a=chosen[n,c]
            offsets={"fixed":np.zeros(STEPS),"always":corrections(x,clip,n,c,None)[0],
                     "adaptive":corrections(x,clip,n,c,OLD_GATES[n,c])[0],
                     "tail":tail_offsets(x,clip,n,c,a)}
            row=dict(seed=seed,**dict(zip(PARAMS,params)),references=n,cadence=c,
                reference_reads=(STEPS//c)*n*REF_READS,calibration_reference_reads=n*REF_READS)
            for p,off in offsets.items():
                m,s=(bm,bs) if p=="fixed" else score(b,d,off)
                passed=m["worst_state_ser"]<=TARGET
                row.update({p+"_symbol_errors":m["symbol_errors"],p+"_bit_errors":m["bit_errors"],
                    p+"_worst_errors":int(s.max()),p+"_pass":passed,
                    p+"_residual":float(np.abs(common-off).mean())})
                k=n,c,p
                if k not in summaries:
                    summaries[k]=np.zeros(6,dtype=np.int64)
                    states[k]=np.zeros((16,3),dtype=np.int64)
                summaries[k]+=np.array([1,int(passed),int(not bp and passed),int(bp and not passed),
                    m["symbol_errors"],int(s.max())])
                states[k]+=np.column_stack((s,s>2,(s>2)&(bs<=2)))
                if not any(params[:-1]):
                    require(m["symbol_errors"]==0 and not np.any(off),"ideal control")
            rows.append(row)
    expected=len(TEST)*len(GRID)
    require(len(rows)==expected*len(configs),"held-out coverage")
    summary=[];state_rows=[]
    for (n,c,p),v in sorted(summaries.items()):
        require(v[0]==expected,"policy coverage")
        summary.append(dict(references=n,cadence=c,policy=p,trajectories=int(v[0]),passes=int(v[1]),
            rescued=int(v[2]),regressed=int(v[3]),mean_ser=float(v[4]/(expected*N)),
            mean_worst_ser=float(v[5]/(expected*STEPS*WRITES)),
            reference_reads=0 if p=="fixed" else STEPS//c*n*REF_READS,
            calibration_reference_reads=0 if p=="fixed" else n*REF_READS))
        for i,s in enumerate(states[n,c,p]):
            state_rows.append(dict(references=n,cadence=c,policy=p,state=i,
                reads=expected*STEPS*WRITES,errors=int(s[0]),failing_trajectories=int(s[1]),new_failures=int(s[2])))
    write(out,"heldout.csv",rows);write(out,"summary.csv",summary);write(out,"state_summary.csv",state_rows)
    return dict(passed=True,experiment="OPA-W-002H",development_seeds=list(DEV),heldout_seeds=list(TEST),
        scenarios=len(GRID),development_trajectories=len(DEV)*len(GRID),heldout_trajectories=expected,
        matched_rows=len(rows),candidates_per_configuration=len(CANDIDATES),summary=summary,
        physical_measurement=False,material_fit=False,step_seconds=None,read_energy_J=None,
        limitations=["Hypothetical drift model unchanged from W-002E",
            "Tail objective chosen before fresh held-out evaluation; no guarantee of positive gain",
            "Common reference-only mismatch is not identifiable from reference agreement",
            "All scheduled reference acquisitions charged even for zero gain",
            "Shared scenario draws and repeated cell reads are correlated; point screen only"])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    try:
        result=run(a.output)
    except Exception as e:
        result=dict(passed=False,error=str(e))
    (a.output/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2))
    return 0 if result["passed"] else 1


if __name__=="__main__":
    raise SystemExit(main())
