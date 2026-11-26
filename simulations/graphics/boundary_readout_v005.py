"""OPA-G-003B: exact boundary stress and empirical confidence readout.
Reuses G-003 normalized optics; no physical device or performance claims.
"""
import csv
import json
from fractions import Fraction
from itertools import permutations
from pathlib import Path

import numpy as np
from photonic_side_v004 import dataset, ideal, optical
from ray_box_v001 import face_oracle, workloads

OUT = Path(__file__).resolve().parents[2] / "results" / "opa-g-003b"
SEED = 20261127
N = 128
EXPONENTS = (4, 8, 12, 16, 24, 40)
CONFIGS = (
    ("scale_only", .15, 0., 0., 0., 0.),
    ("large_scale", .6, 0., 0., 0., 0.),
    ("noise_only", .15, 0., 0., 0., .005),
    ("combined", .15, .01, .15, 1., .005),
)


def boundary(seed):
    """Dyadic edge tangencies with controlled signed displacement.
    Vary box dimensions, translation, reflection, permutation and active axes.
    """
    rng = np.random.default_rng(seed)
    cases, labels = [], []
    for exponent in (0, *EXPONENTS):
        for direction in ((0,) if exponent == 0 else (-1, 1)):
            for k in range(N):
                w = rng.integers(1, 9, 3).astype(float) / 4
                lo = -w
                hi = w
                # Enter x at t=1; exit y at t=1-delta/w_y.
                delta = direction * 2.**(-exponent) if exponent else 0.
                o = np.array([-2*w[0], delta, 0.])
                d = np.array([w[0], w[1], w[2]/4 if k % 2 else 0.])
                sign = rng.choice([-1., 1.], 3)
                shift = rng.integers(-16, 17, 3)/4
                order = rng.permutation(3)
                cases.append(tuple(a[order] for a in (
                    sign*o+shift, sign*d, lo+shift, hi+shift)))
                labels.append((exponent, direction, 3 if k % 2 else 2))
    return cases, labels


def exact_geometry(case):
    """Exact guards and normalized determinants on represented inputs."""
    o,d,lo,hi = [tuple(Fraction(float(x)) for x in a) for a in case]
    l = [(-hi[i]+o[i] if d[i]<0 else lo[i]-o[i]) for i in range(3)]
    u = [(-lo[i]+o[i] if d[i]<0 else hi[i]-o[i]) for i in range(3)]
    v = list(map(abs,d))
    active = [i for i in range(3) if v[i]]
    if any(not v[i] and (l[i]>0 or u[i]<0) for i in range(3)) or any(u[i]<0 for i in active):
        return -1, []
    if len(active)<2:
        return 1, []
    scale = max(map(abs,l+u)) or Fraction(1)
    speed = max(v)
    return 0, [(u[i]*v[j]-l[j]*v[i])/(scale*speed)
               for i,j in permutations(active,2)]


def prepare(cases):
    x, groups, truth, guards = dataset(cases)
    exact = [exact_geometry(c) for c in cases]
    assert all(g == eg for g,(eg,_) in zip(guards,exact))
    assert all(bool(t)==(eg>0 if eg else min(m)>=0)
               for t,(eg,m) in zip(truth,exact))
    assert all(b-a==len(m) for (a,b),(_,m) in zip(groups,exact))
    return x, groups, truth, guards, exact


def minima(y, groups):
    return np.array([np.min(y[a:b]) for a,b in groups])


def counts(pred, truth):
    return int(np.sum(pred & ~truth)), int(np.sum(~pred & truth))


def main():
    tests = {}
    cal_cases, cal_labels = boundary(SEED)
    val_cases, val_labels = boundary(SEED+1)
    cal_x, cal_groups, cal_t, cal_g, cal_exact = prepare(cal_cases)
    x, groups, truth, guards, exact = prepare(val_cases)
    labels = np.array(val_labels)
    tests["all_boundary_rays_optical"] = bool(np.all(cal_g==0) and np.all(guards==0))
    tests["exact_boundary_labels"] = bool(np.array_equal(truth,labels[:,1]<=0) and
        all(np.sign(float(min(m)))==-label[1] for (_,m),label in zip(exact,val_labels)) and
        all(np.sign(float(min(m)))==-label[1] for (_,m),label in zip(cal_exact,cal_labels)))
    tests["two_and_three_active_axes"] = all(b-a==k*(k-1) for (a,b),(_,_,k) in zip(groups,val_labels))
    # Independent random draws can coincide in discrete geometry. Remove overlap
    # from held-out data before any fitting or evaluation, including tangencies.
    cal_keys = {tuple(tuple(a) for a in c) for c in cal_cases}
    keep = [i for i,c in enumerate(val_cases) if tuple(tuple(a) for a in c) not in cal_keys]
    val_cases = [val_cases[i] for i in keep]
    val_labels = [val_labels[i] for i in keep]
    x,groups,truth,guards,exact = prepare(val_cases)
    labels = np.array(val_labels)
    tests["distinct_geometry_splits"] = not cal_keys & {tuple(tuple(a) for a in c) for c in val_cases}
    tests["held_out_all_strata"] = all(np.any(np.all(labels==l,axis=1)) for l in set(cal_labels))
    # Guards are separate; historical near_face never reaches optics.
    guard_report = {}
    for name,cases in workloads():
        _,_,t,g,_ = prepare(cases)
        guard_report[name] = dict(samples=len(t),guard_accept=int(np.sum(g==1)),
            guard_reject=int(np.sum(g==-1)),optical=int(np.sum(g==0)))
        tests[name+"_guard_agreement"] = bool(np.all(t[g!=0]==(g[g!=0]>0)))
    tests["near_face_guard_only"] = guard_report["near_face"]["optical"]==0
    exact_min = np.array([float(min(m)) for _,m in exact])
    cal_min = np.array([float(min(m)) for _,m in cal_exact])
    base = minima(ideal(x),groups)
    tests["float_margin_agreement"] = bool(np.max(abs(base-exact_min))<1e-14)
    rows=[]
    def record(name,repeat,stage,policy,y,threshold,uncertain,coverage=None):
        for exponent,direction,k in sorted(set(val_labels)):
            mask=np.all(labels==(exponent,direction,k),axis=1)
            raw=y>=0
            hybrid=np.where(uncertain,truth,raw)
            fp,fn=counts(raw[mask],truth[mask])
            hfp,hfn=counts(hybrid[mask],truth[mask])
            n=int(np.sum(mask))
            rows.append(dict(scenario=name,repeat=repeat,stage=stage,policy=policy,
                exponent=exponent,displacement_sign=direction,active_axes=k,
                optical_rays=n,side_tests=n*k*(k-1),hits=int(np.sum(truth[mask])),
                misses=int(np.sum(~truth[mask])),fp=fp,fn=fn,hybrid_fp=hfp,hybrid_fn=hfn,
                fallback=int(np.sum(uncertain[mask])),threshold=threshold,
                calibration_coverage_target=.99 if coverage is not None else None,
                heldout_ray_margin_coverage=coverage))
    no=np.zeros(len(truth),bool)
    record("ideal",-1,"float","none",base,0.,no)
    record("ideal",-1,"float","epsilon_diagnostic",base,1e-14,abs(base)<=1e-14)
    for j,(name,s,b,p,l,n) in enumerate(CONFIGS):
        for repeat in range(3):
            rng=np.random.default_rng(np.random.SeedSequence([SEED,j,repeat]))
            bias=rng.uniform(-b,b,4)
            phase=np.array([0.,p]); loss=np.array([0.,l])
            def read(a):
                return optical(a,s,bias,phase,loss,rng.normal(0,n,len(a)))
            uniform=rng.uniform(-1,1,(8192,4))
            raw=read(uniform)
            gain,offset=np.linalg.lstsq(np.column_stack([raw,np.ones(len(raw))]),ideal(uniform),rcond=None)[0]
            tests[f"{name}_{repeat}_calibration"]=bool(np.isfinite(gain) and gain>0 and np.isfinite(offset))
            uq=float(np.quantile(abs(gain*raw+offset-ideal(uniform)),.99))
            cal_y=gain*read(cal_x)+offset
            gq=float(np.quantile(abs(minima(cal_y,cal_groups)-cal_min),.99))
            # Same held-out physical samples for raw, gain-only and affine decisions.
            val=read(x)
            y=gain*val+offset
            mins=minima(y,groups)
            record(name,repeat,"raw","none",minima(val,groups),0.,no)
            record(name,repeat,"gain_only","none",minima(gain*val,groups),0.,no)
            record(name,repeat,"affine","none",mins,0.,no)
            for tag,q in (("uniform_side_q99",uq),("geometry_ray_q99",gq)):
                coverage=float(np.mean(abs(mins-exact_min)<=q))
                any_side=np.array([np.any(abs(y[a:b])<=q) for a,b in groups])
                min_window=abs(mins)<=q
                tests[f"{name}_{repeat}_{tag}_subset"]=bool(np.all(~min_window|any_side))
                record(name,repeat,"affine",tag+"_any_side",mins,q,any_side,coverage)
                record(name,repeat,"affine",tag+"_min_window",mins,q,min_window,coverage)
    tests["accounting"]=all(r["hits"]+r["misses"]==r["optical_rays"] and
        0<=r["hybrid_fp"]<=r["fp"]<=r["misses"] and
        0<=r["hybrid_fn"]<=r["fn"]<=r["hits"] and
        0<=r["fallback"]<=r["optical_rays"] for r in rows)
    tests["ideal_diagnostic"]=all(r["hybrid_fp"]==r["hybrid_fn"]==0 for r in rows
                                  if r["policy"]=="epsilon_diagnostic")
    report=dict(experiment="opa-g-003b",seed=SEED,checks=tests,passed=all(tests.values()),
        calibration_rays=len(cal_cases),heldout_optical_rays=len(truth),
        removed_overlap=N*(1+2*len(EXPONENTS))-len(truth),guard_report=guard_report,
        rows=len(rows),scenarios=len(CONFIGS),repeats=3,
        limitations=["Synthetic boundary stress, not production workload",
        "Exact rational oracle on represented inputs; no device precision guarantee",
        "Empirical q99 not a simultaneous or distribution-free safety bound",
        "Minimum-window policy requires two comparator thresholds per side and electronic aggregation",
        "Exact fallback is optimistic; no physical latency, energy or hardware measurement"])
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(report,indent=2)+"\n")
    with (OUT/"results.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    print(json.dumps(report,indent=2))
    if not report["passed"]:
        raise SystemExit("OPA-G-003B numerical gate failed")


if __name__=="__main__":
    main()
