"""Conditional four-bit memory drift compensation, not a physical GSSe fit."""
import argparse
import csv
import itertools
import json
from pathlib import Path
import numpy as np
from multilevel_cell_v001 import codebook, observe, thresholds, decode, metrics, TARGET, WRITES, READS

SEEDS = tuple(range(11001,11017))
SIGMAS = (0., .002, .005, .01, .02)
DRIFTS = (0., .005, .02)
ADCS = (6,8,12)
REF_COUNTS = (1,4,16)
MISMATCH = (0., .005, .02)
REF_READS = 8


def samples(seed):
    a,b,c = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(3)]
    shape=(16,WRITES,1)
    readshape=(16,WRITES,READS)
    return (a.normal(size=shape),a.normal(size=readshape),
            b.normal(size=shape),b.normal(size=readshape),float(b.normal()),
            c.normal(size=(16,1)),c.normal(size=(16,REF_READS)),
            c.normal(size=(16,REF_READS)),c.normal(size=(16,1)))


def prepare(ps,rs,ds,adc,draw):
    cw,cr,vw,vr,common,rw,rc,rv,rm=draw
    ideal=codebook(4)[:,None,None]
    cal,_=observe(np.clip(ideal+ps*cw,0,1),rs*cr,0,adc)
    bounds=thresholds(cal.mean(axis=(1,2)))
    if bounds is None:
        raise ValueError("invalid calibration; no silent exclusion")
    drift=ds*common
    values,clip=observe(np.clip(ideal+ps*vw,0,1),rs*vr,drift,adc)
    truth=np.broadcast_to(np.arange(16)[:,None,None],values.shape)
    # Persistent reference programming error shared between calibration and use.
    stored=np.clip(.5+ps*rw,0,1)
    ref_cal,_=observe(stored,rs*rc,0,adc)
    return bounds,values,truth,drift,int(clip.sum()),stored,ref_cal


def correction(stored,ref_cal,rv,rm,rs,drift,mismatch,adc,n):
    # Reference cells see the same common offset plus cell-specific mismatch.
    # No use of data labels or true drift in estimator.
    ref_val,clip=observe(stored[:n],rs*rv[:n],drift+mismatch*rm[:n],adc)
    estimate=float(np.mean(ref_val-ref_cal[:n]))
    return estimate,int(clip.sum())


def score(values,truth,bounds,estimate):
    c,m=metrics(truth,decode(values-estimate,bounds),4)
    if int(c.sum())!=16*WRITES*READS:
        raise ValueError("sample coverage")
    return m


def paired_outcome(a,b):
    return ("both_pass" if a and b else "rescued" if b else "regressed" if a else "both_fail")


def run(out):
    rows=[]; base_rows=[]; totals={}
    for seed,ps,rs,ds,adc in itertools.product(SEEDS,SIGMAS,SIGMAS,DRIFTS,ADCS):
        # Shared standardized draws across sweep settings; new seeds vs W-002A.
        draw=samples(seed)
        bounds,values,truth,drift,clip,stored,ref_cal=prepare(ps,rs,ds,adc,draw)
        base=score(values,truth,bounds,0.)
        bp=base["worst_state_ser"]<=TARGET
        key=dict(seed=seed,program_sigma=ps,read_sigma=rs,drift_sigma=ds,adc_bits=adc)
        base_rows.append(dict(**key,actual_drift=drift,data_clipped=clip,
                              **base,point_screen=bp))
        for n,mm in itertools.product(REF_COUNTS,MISMATCH):
            estimate,rclip=correction(stored,ref_cal,draw[7],draw[8],rs,drift,mm,adc,n)
            corrected=score(values,truth,bounds,estimate)
            cp=corrected["worst_state_ser"]<=TARGET
            outcome=paired_outcome(bp,cp)
            ref_reads=n*REF_READS
            data_reads=base["samples"]
            row=dict(**key,references=n,mismatch_sigma=mm,actual_drift=drift,
                     estimated_drift=estimate,residual_drift=drift-estimate,
                     data_clipped=clip,reference_clipped=rclip,
                     baseline_ser=base["ser"],baseline_ber=base["ber"],
                     baseline_worst_state_ser=base["worst_state_ser"],
                     baseline_pass=bp,corrected_pass=cp,outcome=outcome,
                     data_reads=data_reads,reference_reads=ref_reads,
                     calibration_reference_reads=ref_reads,
                     read_overhead_fraction=ref_reads/data_reads,
                     useful_read_fraction=data_reads/(data_reads+ref_reads),
                     **corrected)
            rows.append(row)
            k=(n,mm)
            if k not in totals:
                totals[k]=dict(both_pass=0,rescued=0,regressed=0,both_fail=0)
            totals[k][outcome]+=1
            if ps==rs==ds==mm==0 and (not bp or not cp or estimate!=0):
                raise ValueError("ideal control")
    expected=len(SEEDS)*len(SIGMAS)**2*len(DRIFTS)*len(ADCS)
    if len(base_rows)!=expected or len(rows)!=expected*len(REF_COUNTS)*len(MISMATCH):
        raise ValueError("grid coverage")
    summaries=[]
    for (n,mm),counts in sorted(totals.items()):
        if sum(counts.values())!=expected:
            raise ValueError("paired coverage")
        summaries.append(dict(references=n,mismatch_sigma=mm,**counts,
            baseline_pass=counts["both_pass"]+counts["regressed"],
            corrected_pass=counts["both_pass"]+counts["rescued"],
            net_pass_gain=counts["rescued"]-counts["regressed"]))
    def write(name,data):
        with (out/name).open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    write("baseline.csv",base_rows);write("paired.csv",rows);write("summary.csv",summaries)
    return dict(passed=True,experiment="OPA-W-002C",baseline_panels=expected,
                paired_rows=len(rows),seeds=list(SEEDS),summary=summaries,
                point_target=TARGET,physical_measurement=False,material_fit=False,
                read_energy_J=None,reference_write_energy_J=None,
                retention_seconds=None,
                limitations=["One shared additive offset per validation panel",
                    "Reference mismatch is additive, not a measured material distribution",
                    "No data labels used for compensation; frozen calibration",
                    "Read overhead assumes one reference acquisition per complete panel",
                    "Calibration reads counted separately; no hardware latency or energy inferred",
                    "Shared draws across configurations; descriptive point screen only"])


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
