"""OPA-G-003: four null-biased MZMs, coherent signed readout.
Dimensionless single-carrier behavioral model, not a calibrated device.
"""
import csv
import json
import sys
from itertools import permutations, product
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "circuit"))
from mzi import mzi
from ray_box_v001 import face_oracle, workloads
from side_test_v002 import side_test

OUT = Path(__file__).resolve().parents[2] / "results" / "opa-g-003"
SEED = 20261126
SCALES = (0.05, 0.15, 0.30, 0.60)
THRESHOLDS = (0., 0.005, 0.02, 0.05, 0.1)


def field(x, scale, bias=0.):
    """Null-port signed field after common phase removal, normalized by scale.
    Bias is a half-differential phase in rad. Exact sine, not intensity.
    """
    return np.sin(scale*x + bias)/scale


def optical(x, scale, bias, phase, loss, noise):
    """Signed normalized balanced coherent receiver; loss is power dB.
    Ideal split/combination and reference amplitude absorbed into gain.
    """
    f = field(x, scale, bias)
    p = f[:, 0]*f[:, 1]*10**(-loss[0]/20)*np.exp(1j*phase[0])
    q = f[:, 2]*f[:, 3]*10**(-loss[1]/20)*np.exp(1j*phase[1])
    z = p+q
    # Balanced difference at ideal 50:50 combiner, unit reference.
    # Direct square-law detection alone cannot distinguish opposite signs.
    return (abs(1+z)**2-abs(1-z)**2)/4 + noise


def ideal(x):
    return x[:,0]*x[:,1]+x[:,2]*x[:,3]


def operands(case):
    """Electronic reflection, guards, and positive per-ray normalization.
    Return None for guard rejection, empty list for unconditional acceptance.
    """
    o,d,lo,hi=map(lambda a:np.asarray(a,dtype=float),case)
    sign=np.where(d<0,-1.,1.)
    l=np.where(sign<0,-hi,lo)-sign*o
    u=np.where(sign<0,-lo,hi)-sign*o
    v=abs(d)
    active=np.flatnonzero(v)
    if np.any((v==0)&((l>0)|(u<0))) or np.any(u[active]<0):
        return None
    if len(active)<2:
        return []
    spatial=max(np.max(abs(l)),np.max(abs(u)))
    directional=np.max(v)
    if spatial==0:
        spatial=1.
    return [(u[i]/spatial,v[j]/directional,-l[j]/spatial,v[i]/directional)
            for i,j in permutations(active,2)]


def dataset(cases):
    xs=[]; groups=[]; truth=[]; guards=[]
    for case in cases:
        ref=face_oracle(*case)
        truth.append(ref)
        op=operands(case)
        guards.append(-1 if op is None else 1 if not op else 0)
        groups.append((len(xs),len(xs)+(len(op) if op else 0)))
        if op:
            xs.extend(op)
    return np.asarray(xs,dtype=float).reshape(-1,4),groups,np.array(truth),np.array(guards)


def classify(y,groups,guards,truth,threshold):
    # A threshold window is a hypothetical additional confidence readout,
    # not information available from the single zero-threshold ADC alone.
    raw=[]; hybrid=[]; fallback=0
    for (a,b),g,t in zip(groups,guards,truth):
        if g:
            p=g>0
            raw.append(p);hybrid.append(p)
        else:
            values=y[a:b]
            p=bool(np.all(values>=0))
            raw.append(p)
            # Conservative ray-level fallback on any uncertain side.
            ambiguous=bool(np.any(abs(values)<=threshold))
            fallback+=int(ambiguous)
            hybrid.append(bool(t) if ambiguous else p)
    raw=np.asarray(raw);hybrid=np.asarray(hybrid)
    return dict(fp=int(np.sum(raw&~truth)),fn=int(np.sum(~raw&truth)),
                hybrid_fp=int(np.sum(hybrid&~truth)),
                hybrid_fn=int(np.sum(~hybrid&truth)),fallback=fallback)


def main():
    rng=np.random.default_rng(SEED)
    tests={}
    # Reuse repository ideal MZI matrix; remove common phase for push-pull.
    angles=np.linspace(-0.6,0.6,101)
    measured=np.array([mzi(2*t,0)[0,0]/(1j*np.exp(1j*t)) for t in angles])
    tests["mzi_signed_field"]=bool(np.max(abs(measured-np.sin(angles)))<1e-12)
    probe=np.array([[1,1,0,0],[-1,1,0,0],[1,1,-1,1],[0,0,0,0]],float)
    y=optical(probe,0.15,np.zeros(4),np.zeros(2),np.zeros(2),0.)
    tests["signed_readout"]=bool(y[0]>0 and y[1]<0 and abs(y[2])<1e-12 and y[3]==0)
    # Separate calibration and evaluation samples. Fit scalar gain/offset
    # only, without using evaluation labels; residual quantile is empirical.
    calibration=rng.uniform(-1,1,(8192,4))
    validation=rng.uniform(-1,1,(8192,4))
    lo,hi=(-1,-1,-1),(1,1,1)
    grid=[(o,d,lo,hi) for o in product(range(-2,3),repeat=3)
          for d in product((-1,0,1),repeat=3)]
    translated=[]
    for _ in range(4096):
        a=rng.integers(-512,513,3)/256
        b=a+rng.integers(0,513,3)/256
        o=rng.integers(-1024,1025,3)/256
        d=rng.integers(-256,257,3)/256
        translated.append((o,d,a,b))
    datasets={n:dataset(c) for n,c in [("integer_grid",grid),("translated",translated),*workloads()]}
    for n,(x,groups,t,g) in datasets.items():
        # Float rounding at exact boundaries: explicit tolerance only for
        # this ideal reference check; actual optical decisions use zero.
        base=ideal(x)
        pred=classify(np.where(abs(base)<1e-14,0.,base),groups,g,t,0.)
        tests[n+"_ideal_geometry"]=pred["fp"]==pred["fn"]==0
    # Independent one-factor sweeps plus a combined illustrative stress.
    # These are assumptions, not paper-derived hardware tolerances.
    configs=[]
    for s in SCALES:
        configs.append((f"scale_{s}",s,0.,0.,0.,0.))
    for v in (0.002,0.01,0.03):
        configs.append((f"bias_{v}",0.15,v,0.,0.,0.))
    for v in (0.05,0.15,0.30):
        configs.append((f"phase_{v}",0.15,0.,v,0.,0.))
    for v in (0.25,1.,3.):
        configs.append((f"loss_{v}",0.15,0.,0.,v,0.))
    for v in (0.001,0.005,0.02):
        configs.append((f"noise_{v}",0.15,0.,0.,0.,v))
    configs.append(("combined",0.15,0.01,0.15,1.,0.005))
    rows=[]
    for name,s,b,p,l,n in configs:
        for repeat in range(3):
            # static bias and relative branch phase, nonnegative branch losses.
            bias=rng.uniform(-b,b,4)
            phase=np.array([0.,p])
            loss=np.array([0.,l])
            def read(x):
                return optical(x,s,bias,phase,loss,rng.normal(0,n,len(x)))
            raw=read(calibration)
            gain,offset=np.linalg.lstsq(np.column_stack([raw,np.ones(len(raw))]),
                                        ideal(calibration),rcond=None)[0]
            residual=abs(gain*raw+offset-ideal(calibration))
            q99=float(np.quantile(residual,0.99))
            valerr=abs(gain*read(validation)+offset-ideal(validation))
            coverage=float(np.mean(valerr<=q99))
            for workload,(x,groups,t,g) in datasets.items():
                vals=gain*read(x)+offset
                # Reuse identical noise realization across thresholds.
                for threshold in sorted(set((*THRESHOLDS,q99))):
                    row=classify(vals,groups,g,t,threshold)
                    rows.append(dict(scenario=name,repeat=repeat,workload=workload,
                        samples=len(t),hits=int(np.sum(t)),misses=int(np.sum(~t)),
                        side_tests=len(x),guard_cases=int(np.sum(g!=0)),
                        scale_rad=s,bias_bound_rad=b,relative_phase_rad=p,
                        differential_loss_db=l,noise_std_normalized=n,
                        gain=float(gain),offset=float(offset),
                        calibration_q99=q99,validation_coverage=coverage,
                        threshold=float(threshold),**row))
    tests["finite_calibration"]=all(np.isfinite(r["gain"]) and r["gain"]>0 and
                                    np.isfinite(r["calibration_q99"]) for r in rows)
    tests["fallback_never_adds_errors"]=all(r["hybrid_fp"]<=r["fp"] and
                                            r["hybrid_fn"]<=r["fn"] for r in rows)
    tests["count_bounds"]=all(0<=r["fp"]<=r["misses"] and 0<=r["fn"]<=r["hits"] and
                              0<=r["fallback"]<=r["samples"]-r["guard_cases"] for r in rows)
    tests["noise_and_loss_sweeps"]=all(any(r["scenario"].startswith(k) for r in rows)
                                       for k in ("noise_","loss_","phase_","bias_"))
    result=dict(experiment="opa-g-003",seed=SEED,checks=tests,passed=all(tests.values()),
                rows=len(rows),scenarios=len(configs),repeats=3,
                workload_samples={n:len(d[2]) for n,d in datasets.items()},
                limitations=["Illustrative normalized single-carrier model; no fitted device tolerances",
                             "Ideal balanced receiver and reference; no absolute optical power",
                             "Static scalar calibration, empirical residual coverage not a guaranteed bound",
                             "Hybrid confidence window requires extra comparator/readout and exact electronic fallback",
                             "No timing, energy, fabrication or measured hardware claims"])
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    with (OUT/"results.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    print(json.dumps(result,indent=2))
    if not result["passed"]:
        raise SystemExit("OPA-G-003 model gate failed")


if __name__=="__main__":
    main()
