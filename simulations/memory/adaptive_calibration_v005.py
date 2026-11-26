"""Conditional chronological memory calibration; no material or time calibration."""
import argparse
import csv
import itertools
import json
from pathlib import Path
import numpy as np
from multilevel_cell_v001 import codebook, observe, thresholds, decode, metrics, TARGET

STEPS=64
WRITES=32
REF_READS=8
DEV=tuple(range(21001,21005))
TEST=tuple(range(22001,22017))
GRID=list(itertools.product((0.,.005,.01), (0.,.005,.01),
    (0.,.005,.02), (0.,.005,.02), (0.,.01), (8,12)))
REFS=(4,16)
CADENCES=(1,4,16)
GATES=(1.,2.,3.)
FLOOR=.002


def trajectory(seed,ps,rs,ds,mm,shared,adc):
    a,b,c,d=[np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(4)]
    ideal=codebook(4)[:,None]
    cal,_=observe(np.clip(ideal+ps*a.normal(size=(16,256)),0,1),
                  rs*a.normal(size=(16,256)),0,adc)
    bounds=thresholds(cal.mean(axis=1))
    if bounds is None:
        raise ValueError("invalid calibration")
    # Same programmed cells retained throughout the trajectory.
    stored=np.clip(ideal+ps*b.normal(size=(16,WRITES)),0,1)
    common=np.zeros(STEPS)
    correlated=np.zeros(STEPS)
    individual=np.zeros((STEPS,16))
    for t in range(1,STEPS):
        common[t]=.95*common[t-1]+np.sqrt(1-.95**2)*ds*c.normal()
        correlated[t]=.95*correlated[t-1]+np.sqrt(1-.95**2)*shared*c.normal()
        individual[t]=.95*individual[t-1]+np.sqrt(1-.95**2)*mm*c.normal(size=16)
    data,clip=observe(stored[None,:,:],rs*b.normal(size=(STEPS,16,WRITES)),
                      common[:,None,None],adc)
    ref_stored=np.clip(.5+ps*d.normal(size=(16,1)),0,1)
    ref_cal,_=observe(ref_stored,rs*d.normal(size=(16,REF_READS)),0,adc)
    refs,rclip=observe(ref_stored[None,:,:],rs*d.normal(size=(STEPS,16,REF_READS)),
                        common[:,None,None]+correlated[:,None,None]+individual[:,:,None],adc)
    changes=refs.mean(axis=2)-ref_cal.mean(axis=1)[None,:]
    return bounds,data,changes,rclip,common,int(clip.sum())


def corrections(changes,clipped,n,cadence,gate):
    """Only sample the current/past scheduled reference blocks; no labels or true drift."""
    offsets=np.zeros(STEPS)
    enabled=np.zeros(STEPS,dtype=bool)
    last=0.
    active=False
    for t in range(STEPS):
        if t%cadence==0:
            x=changes[t,:n]
            mean=float(x.mean())
            uncertainty=max(FLOOR,float(x.std(ddof=1))/np.sqrt(n))
            # Always policy still rejects clipped reference acquisition.
            active=not bool(clipped[t,:n].any()) and (gate is None or abs(mean)>gate*uncertainty)
            last=mean if active else 0.
        offsets[t]=last
        enabled[t]=active
    return offsets,enabled


def evaluate(bounds,data,offset):
    truth=np.broadcast_to(np.arange(16)[None,:,None],data.shape)
    pred=decode(data-offset[:,None,None],bounds)
    _,m=metrics(truth,pred,4)
    m["point_pass"]=m["worst_state_ser"]<=TARGET
    return m


def write(out,name,rows):
    with (out/name).open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)


def run(out):
    # Development chooses gate separately for each reference/cadence hardware
    # option, using total symbol error, then larger gate as fixed tie-break.
    loss={(n,c,g):0 for n,c,g in itertools.product(REFS,CADENCES,GATES)}
    for seed,params in itertools.product(DEV,GRID):
        bounds,data,changes,clip,_,_=trajectory(seed,*params)
        for n,c,g in loss:
            off,_=corrections(changes,clip,n,c,g)
            loss[n,c,g]+=evaluate(bounds,data,off)["symbol_errors"]
    chosen={(n,c):min(GATES,key=lambda g:(loss[n,c,g],-g))
            for n,c in itertools.product(REFS,CADENCES)}
    devrows=[dict(references=n,cadence=c,gate=g,symbol_errors=v,selected=g==chosen[n,c])
             for (n,c,g),v in sorted(loss.items())]
    rows=[]
    for seed,params in itertools.product(TEST,GRID):
        ps,rs,ds,mm,shared,adc=params
        bounds,data,changes,clip,common,data_clip=trajectory(seed,*params)
        base=evaluate(bounds,data,np.zeros(STEPS))
        key=dict(seed=seed,program_sigma=ps,read_sigma=rs,common_sigma=ds,
                 independent_ref_sigma=mm,correlated_ref_sigma=shared,adc_bits=adc)
        for n,c in itertools.product(REFS,CADENCES):
            for policy,g in (("always",None),("adaptive",chosen[n,c])):
                off,on=corrections(changes,clip,n,c,g)
                m=evaluate(bounds,data,off)
                acquisitions=len(range(0,STEPS,c))
                ref_reads=acquisitions*n*REF_READS
                rows.append(dict(**key,references=n,cadence=c,policy=policy,gate=g,
                    **m,baseline_ser=base["ser"],baseline_ber=base["ber"],
                    baseline_worst_state_ser=base["worst_state_ser"],
                    baseline_pass=base["point_pass"],
                    rescued=not base["point_pass"] and m["point_pass"],
                    regressed=base["point_pass"] and not m["point_pass"],
                    enabled_steps=int(on.sum()),acquisitions=acquisitions,
                    reference_reads=ref_reads,calibration_reference_reads=n*REF_READS,
                    data_clipped=data_clip,read_overhead=ref_reads/m["samples"],
                    mean_abs_residual=float(np.abs(common-off).mean()),
                    baseline_mean_abs_drift=float(np.abs(common).mean())))
                if ps==rs==ds==mm==shared==0 and (m["ser"]!=0 or np.any(off)):
                    raise ValueError("ideal control")
    expected=len(TEST)*len(GRID)
    if len(rows)!=expected*len(REFS)*len(CADENCES)*2:
        raise ValueError("coverage")
    summary=[]
    for n,c,p in itertools.product(REFS,CADENCES,("always","adaptive")):
        subset=[r for r in rows if (r["references"],r["cadence"],r["policy"])==(n,c,p)]
        if len(subset)!=expected:
            raise ValueError("matched coverage")
        summary.append(dict(references=n,cadence=c,policy=p,trajectories=len(subset),
            baseline_pass=sum(r["baseline_pass"] for r in subset),
            corrected_pass=sum(r["point_pass"] for r in subset),
            rescued=sum(r["rescued"] for r in subset),regressed=sum(r["regressed"] for r in subset),
            mean_ser=sum(r["ser"] for r in subset)/len(subset),
            baseline_mean_ser=sum(r["baseline_ser"] for r in subset)/len(subset),
            read_overhead=subset[0]["read_overhead"]))
    write(out,"development.csv",devrows);write(out,"heldout.csv",rows);write(out,"summary.csv",summary)
    return dict(passed=True,experiment="OPA-W-002E",development_seeds=list(DEV),
        heldout_seeds=list(TEST),scenarios=len(GRID),steps=STEPS,writes_per_state=WRITES,
        heldout_trajectories=expected,paired_rows=len(rows),summary=summary,
        physical_measurement=False,material_fit=False,step_seconds=None,read_energy_J=None,
        limitations=["AR(1) offsets are hypothetical; no retention law or physical time scale",
          "Same programmed cells retained; repeated reads and scenarios are correlated",
          "Gate selection uses development labels only; test labels are scoring only",
          "Correlated reference offsets can fool the gate; no oracle or guaranteed improvement",
          "Adaptive policy still pays every scheduled reference read; no claimed energy saving",
          "Point screen is descriptive, not statistical qualification"])


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
