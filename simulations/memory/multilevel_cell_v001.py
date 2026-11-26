"""OPA-W-002A: hypothetical multilevel intensity storage, not a material fit."""
import argparse
import csv
import json
import math
from pathlib import Path
import numpy as np

LOW, HIGH = .2, .8
WRITES = 512
READS = 8
SEEDS = (1027, 2039, 3049, 4057, 5069, 6073, 7087, 8093)
SIGMAS = (0., .002, .005, .01, .02)
DRIFTS = (0., .005, .02)
ADC_BITS = (6, 8, 12)
TARGET = .001  # numerical screen only, not a qualified physical BER


def codebook(bits):
    return np.linspace(LOW, HIGH, 2**bits)


def observe(stored, noise, drift, adc_bits):
    analog = stored + noise + drift
    clipped = (analog < 0) | (analog > 1)
    scale = 2**adc_bits - 1
    return np.rint(np.clip(analog, 0, 1)*scale)/scale, clipped


def thresholds(centers):
    centers = np.asarray(centers)
    if not np.all(np.isfinite(centers)) or np.any(np.diff(centers) <= 0):
        return None
    return (centers[:-1]+centers[1:])/2


def decode(values, boundaries):
    # Ties go to the higher state; no hidden ideal-state correction.
    return np.searchsorted(boundaries, values, side="right")


def metrics(truth, predicted, bits):
    levels = 2**bits
    counts = np.bincount((truth*levels+predicted).ravel(),
                         minlength=levels**2).reshape(levels, levels)
    hamming = np.array([i.bit_count() for i in range(levels)])
    xor = np.bitwise_xor(np.arange(levels)[:, None], np.arange(levels))
    total = int(counts.sum())
    errors = int(total-np.trace(counts))
    bit_errors = int(np.sum(counts*hamming[xor]))
    state_errors = 1-np.diag(counts)/counts.sum(axis=1)
    return counts, dict(samples=total, symbol_errors=errors,
                        bit_errors=bit_errors, ser=errors/total,
                        ber=bit_errors/(total*bits),
                        worst_state_ser=float(state_errors.max()))


def draws(bits, seed):
    # Independent calibration and validation RNG streams. Shared standardized
    # draws across sweep settings for paired sensitivity, not new independent trials.
    a,b = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(2)]
    shape=(2**bits, WRITES, 1)
    readshape=(2**bits, WRITES, READS)
    return (a.normal(size=shape),a.normal(size=readshape),
            b.normal(size=shape),b.normal(size=readshape),float(b.normal()))


def evaluate(bits, ps, rs, ds, adc, randoms):
    cwrite,cread,vwrite,vread,common=randoms
    ideal=codebook(bits)[:,None,None]
    # Programming error stays fixed across repeated reads of the same write.
    calstored=np.clip(ideal+ps*cwrite,0,1)
    valstored=np.clip(ideal+ps*vwrite,0,1)
    cal,_=observe(calstored,rs*cread,0,adc)
    values,clipped=observe(valstored,rs*vread,ds*common,adc)
    programmed_clip=int(np.count_nonzero((ideal+ps*vwrite<0)|(ideal+ps*vwrite>1)))
    centers=cal.mean(axis=(1,2))
    bounds=thresholds(centers)
    info=dict(calibration_valid=bounds is not None, common_drift=ds*common,
              receiver_clipped=int(clipped.sum()), programming_clipped=programmed_clip,
              calibration_centers=centers.tolist(),
              thresholds=None if bounds is None else bounds.tolist())
    if bounds is None:
        return info,None,None
    truth=np.broadcast_to(np.arange(2**bits)[:,None,None],values.shape)
    pred=decode(values,bounds)
    confusion,m=metrics(truth,pred,bits)
    # Independent write events within a panel conditional on its common drift;
    # all eight reads in each write cluster may be correlated. Do not treat
    # repeated reads as IID for confidence. Exact conservative zero-event
    # upper bound only when no write has ANY erroneous read.
    any_error=np.any(pred!=truth,axis=2)
    n_writes=any_error.size
    bad_writes=int(any_error.sum())
    # One-sided Hoeffding bound for mean independent bounded write-cluster
    # error fractions, conditional on calibration and drift. Equal state counts.
    radius=math.sqrt(math.log(20)/(2*n_writes))
    m.update(writes=n_writes,bad_writes=bad_writes,
             ser_hoeffding_upper95=min(1.,m["ser"]+radius),
             zero_bad_write_upper95=(1-.05**(1/n_writes) if bad_writes==0 else None))
    # A conditional point screen only; no confidence or physical qualification.
    m["point_screen"]=m["worst_state_ser"]<=TARGET
    info["validation_means"]=values.mean(axis=(1,2)).tolist()
    info["validation_std"]=values.std(axis=(1,2)).tolist()
    return info,confusion,m


def run(output):
    rows=[]; conf=[]; calibration=[]
    for bits in (1,4):
        for seed in SEEDS:
            randoms=draws(bits,seed)
            for ps in SIGMAS:
                for rs in SIGMAS:
                    for ds in DRIFTS:
                        for adc in ADC_BITS:
                            key=dict(bits=bits,seed=seed,program_sigma=ps,
                                     read_sigma=rs,drift_sigma=ds,adc_bits=adc)
                            info,c,m=evaluate(bits,ps,rs,ds,adc,randoms)
                            calibration.append(dict(**key,**info))
                            row=dict(**key,calibration_valid=info["calibration_valid"],
                                     common_drift=info["common_drift"],
                                     receiver_clipped=info["receiver_clipped"],
                                     programming_clipped=info["programming_clipped"])
                            fields=("samples","symbol_errors","bit_errors","ser","ber",
                                    "worst_state_ser","writes","bad_writes",
                                    "ser_hoeffding_upper95","zero_bad_write_upper95","point_screen")
                            row.update({f:None if m is None else m[f] for f in fields})
                            rows.append(row)
                            if c is not None:
                                if int(c.sum())!=2**bits*WRITES*READS:
                                    raise ValueError("confusion coverage")
                                for i in range(2**bits):
                                    for j in range(2**bits):
                                        conf.append(dict(**key,true=i,predicted=j,count=int(c[i,j])))
    expected=2*len(SEEDS)*len(SIGMAS)**2*len(DRIFTS)*len(ADC_BITS)
    if len(rows)!=expected or len(calibration)!=expected:
        raise ValueError("sweep coverage")
    ideal=[x for x in rows if x["program_sigma"]==x["read_sigma"]==x["drift_sigma"]==0]
    if len(ideal)!=2*len(SEEDS)*len(ADC_BITS) or not all(x["ser"]==0 for x in ideal):
        raise ValueError("ideal control")
    def write(name,data):
        with (output/name).open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(data[0]))
            writer.writeheader(); writer.writerows(data)
    write("panels.csv",rows)
    write("confusion.csv",conf)
    (output/"calibration.json").write_text(json.dumps(calibration,allow_nan=False)+"\n")
    summary={}
    for bits in (1,4):
        subset=[x for x in rows if x["bits"]==bits]
        summary[str(bits)]=dict(panels=len(subset),
            valid=sum(x["calibration_valid"] for x in subset),
            point_screen_pass=sum(x["point_screen"] is True for x in subset),
            point_screen_fail=sum(x["point_screen"] is False for x in subset),
            invalid=sum(not x["calibration_valid"] for x in subset))
    return dict(passed=True,experiment="OPA-W-002A",panel_count=len(rows),
                confusion_rows=len(conf),seeds=list(SEEDS),writes_per_state=WRITES,
                reads_per_write=READS,codebook_interval=[LOW,HIGH],
                program_read_sigmas=list(SIGMAS),drift_sigmas=list(DRIFTS),
                adc_bits=list(ADC_BITS),worst_state_ser_point_target=TARGET,
                summary=summary,physical_measurement=False,material_fit=False,
                write_energy_J=None,retention_seconds=None,endurance_cycles=None,
                limitations=["Hypothetical normalized transmission, not a GSSe fit",
                    "Calibration at zero drift, one shared Gaussian offset per validation panel",
                    "Natural binary state labels; no ECC or Gray mapping",
                    "Repeated reads and shared sweep draws are not independent trials",
                    "Hoeffding bound conditional on calibration and drift; no simultaneous coverage",
                    "Point target is not a statistical qualification or physical BER guarantee",
                    "No time-dependent drift law, measured write energy, retention or endurance"])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    try:
        report=run(args.output)
    except Exception as exc:
        report=dict(passed=False,error=str(exc),physical_measurement=False)
    (args.output/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report,indent=2))
    return 0 if report["passed"] else 1


if __name__=="__main__":
    raise SystemExit(main())
