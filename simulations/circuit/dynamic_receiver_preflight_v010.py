"""NL010 preflight: receiver primitives and full archived NL009 data audit.

No classification sweep or new timing claims in this stage.
"""
import csv
import hashlib
import json
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from dynamic_receiver import hybrid, psd, coefficients, deterministic, noisy_step, waveform
from nonlinear_activation_v009 import CASES, simulate
from nonlinear_activation_v003 import R

OUT=Path("results/opa-nl010-preflight")
ARCHIVE=Path("results/opa-nl-009")
WEIGHTS=Path("results/opa-nl-003/weights.json")
WEIGHT_PROV=Path("results/opa-nl-003/provenance.json")
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(name):
    with (ARCHIVE/name).open(newline="") as f:
        yield from csv.DictReader(f)

def audit():
    manifest=json.loads((ARCHIVE/"provenance.json").read_text())["files"]
    before={ARCHIVE/n:sha(ARCHIVE/n) for n in manifest}
    before[WEIGHTS]=sha(WEIGHTS)
    if any(before[ARCHIVE/n]!=v["sha256"] or (ARCHIVE/n).stat().st_size!=v["bytes"] for n,v in manifest.items()):
        raise ValueError("NL009 evidence mismatch")
    if before[WEIGHTS]!=json.loads(WEIGHT_PROV.read_text())["files"]["weights.json"]["sha256"]:
        raise ValueError("weight archive mismatch")
    keys=("candidate","response_ps","on_ps","gap_ps","drive_mw")
    group=lambda r:tuple(r[k] for k in keys)
    summary={}
    for r in read("summary.csv"):
        k=group(r)+(r["history"],)
        if k in summary:raise ValueError("duplicate summary")
        summary[k]=r["screen_pass"]=="True"
    paired=Counter()
    for k,v in summary.items():
        if k[-1]=="cold":
            paired[str((v,summary[k[:-1]+("stream",)]))]+=1
    metrics={}; position=defaultdict(lambda:[0,0.,0.,float("inf"),0.])
    residual=0.
    for r in read("metrics.csv"):
        k=group(r)+(r["history"],r["seed"])
        if k in metrics:raise ValueError("duplicate metrics")
        metrics[k]=r
        en=[float(r[x+"_fj"]) for x in ("input","initial","reflection","drop","absorption","final")]
        residual=max(residual,abs(en[0]+en[1]-sum(en[2:]))/(1+en[0]+en[1]))
    seen=set(); position_counts=Counter()
    for r in read("positions.csv"):
        k=group(r)+(r["history"],r["seed"]); p=int(r["symbol"])
        if k not in metrics or not 0<=p<64 or (k,p) in seen:raise ValueError("position key")
        seen.add((k,p)); position_counts[k]+=1
        if p<8 or p>=56:
            v=position[k+("first8" if p<8 else "last8",)]
            v[0]+=1;v[1]+=float(r["clean_accuracy"])
            v[3]=min(v[3],float(r["min_signed_projected_margin"]))
            v[4]=max(v[4],float(r["max_memory_field"]))
    positions=[]
    for k,v in sorted(position.items()):
        assert v[0]==8
        m=metrics[k[:-1]]
        assert abs(v[1]/8-float(m[k[-1]+"_accuracy"]))<1e-12
        assert abs(v[4]-float(m[k[-1]+"_memory"]))<1e-12
        positions.append(dict(zip(keys+("history","seed","window"),k),
            accuracy=v[1]/8,min_signed_projected_margin=v[3],max_memory_field=v[4]))
    trace_counts=Counter(); trace_seen=set(); trace_first=True
    for r in read("traces.csv"):
        k=group(r)+(r["seed"],); p=int(r["symbol"])
        if not 0<=p<64 or (k,p) in trace_seen or k[:-1]+("stream",k[-1]) not in metrics:raise ValueError("trace key")
        trace_seen.add((k,p));trace_counts[k]+=1
        if p==0:trace_first &= r["cold_real"]==r["stream_real"] and r["cold_imag"]==r["stream_imag"]
    checks=dict(archive_counts=len(summary)==720 and len(metrics)==3600 and len(seen)==230400
        and len(trace_seen)==115200 and len(positions)==7200,
        archive_pairs=dict(paired)=={"(True, True)":123,"(True, False)":29,"(False, True)":1,"(False, False)":207},
        archive_position_coverage=len(position_counts)==3600 and set(position_counts.values())=={64},
        archive_trace_coverage=len(trace_counts)==1800 and set(trace_counts.values())=={64} and trace_first,
        archive_immutable=all(sha(p)==v for p,v in before.items()))
    with (OUT/"nl009_position_windows.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(positions[0]));w.writeheader();w.writerows(positions)
    return checks,dict(paired=dict(paired),max_aggregate_energy_residual=residual,
        position_windows=len(positions),trace_rows=len(trace_seen))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    checks,archive=audit()
    field=np.array([-.03,0.,.03,.02j])
    i,ps,pp,pm=hybrid(field,.1,0.,0.)
    checks["hybrid"]=bool(np.allclose(pp+pm,ps+.1e-3,rtol=1e-12,atol=1e-18)
        and np.allclose(i,2*R*field.real*np.sqrt(.1)*1e-3,atol=1e-18))
    checks["phase"]=bool(np.max(abs(hybrid(field[:3],.1,0.,90.)[0]))<1e-17)
    errors=[]
    for fc in (1,5,10,20,40,80):
        for dt in (.0625,.125,.25,10.,35.):
            a,m,c=coefficients(fc,dt)
            lam=2*np.pi*fc*1e9;t=dt*1e-12;x=lam*t
            exact_end=lam/4*(-np.expm1(-2*x))
            exact_cross=(-np.expm1(-x))**2/(4*t)
            # independent analytic variance for moderate x; small x checked by composition
            exact_mean=(t-2*(-np.expm1(-x))/lam+(-np.expm1(-2*x))/(2*lam))/(2*t*t)
            errors.extend([abs(c[0,0]/exact_end-1),abs(c[0,1]/exact_cross-1)])
            if x>.01:errors.append(abs(c[1,1]/exact_mean-1))
            ah,mh,ch=coefficients(fc,dt/2)
            # two independent half-step noises; second mean depends on first end.
            A=np.array([[ah,0],[mh/2,.5]])
            B=np.diag([1.,.5])
            composed=A@ch@A.T+B@ch@B.T
            errors.append(float(np.max(abs(composed-c))/np.max(abs(c))))
            e1,j1=deterministic(.3,-.2,ah,mh);e2,j2=deterministic(e1,-.2,ah,mh)
            e,j=deterministic(.3,-.2,a,m)
            errors.extend([abs(e-e2),abs(j-(j1+j2)/2)])
            if np.linalg.eigvalsh(c).min()<=0:raise ValueError("nonpositive covariance")
    checks["analytic_covariance_and_nested_composition"]=max(errors)<1e-8
    fc=20.;dt=10.;a,m,c=coefficients(fc,dt);S=float(psd(0.,.1))
    stationary=S*np.pi*fc*1e9/2
    # Independent ensemble of 200000 stationary transitions, fixed tolerance 2%.
    rg=np.random.default_rng(101010)
    x=rg.normal(size=200000)*np.sqrt(stationary)
    g=rg.normal(size=(2,len(x)))
    end,mean=noisy_step(x,0.,S,a,m,np.linalg.cholesky(c),*g)
    lag=float(np.mean(x*end)/stationary)
    expected_mean=m*m*stationary+S*c[1,1]
    checks["stationary_noise"]=bool(abs(np.var(end)/stationary-1)<.02 and abs(lag-a)<.02
        and abs(np.var(mean)/expected_mean-1)<.02)
    # Fixed synthetic optical sequence; independent NL009 endpoints and energy audit.
    z=np.array([[[.3,-.5,.7],[-.2,.4,-.6]],[[.1,.2,-.3],[.3,-.2,.1]]])
    w=np.array([[.6,-.4]])
    wave=list(waveform(z,w,CASES["C2"],5.,35.,20.,.25))
    old,_,_,_,_=simulate(z[None,...],*CASES["C2"],5.,35.,20.,.25)
    expected=(w@old[1,0].reshape(2,-1)).reshape(2,3)
    endpoints=np.stack([v[1] for v in wave],axis=-1)
    checks["waveform_endpoint"]=bool(np.max(abs(endpoints-expected))<1e-12)
    checks["waveform_balance_passivity"]=all(v[2]<1e-6 and v[3]<1e-9 and v[0].shape==(220,2) for v in wave)
    # A slow receiver retains positive state after a short negative input.
    a,m,_=coefficients(1.,5.)
    checks["slow_receiver_memory"]=deterministic(1.,-1.,a,m)[0]>0
    a,m,_=coefficients(80.,200.)
    checks["high_cutoff_long_step"]=abs(deterministic(0.,1.,a,m)[0]-1)<1e-12
    checks={k:bool(v) for k,v in checks.items()}
    result=dict(experiment="OPA-NL010-PREFLIGHT",checks=checks,failures=[k for k,v in checks.items() if not v],
        archive=archive,max_covariance_composition_error=max(errors),noise_lag=lag,
        expected_noise_lag=float(np.exp(-2*np.pi*20e9*10e-12)),
        noise_variance_ratio=float(np.var(end)/stationary),
        limitations=["Preflight only; no classification sweep, no measured hardware."])
    (OUT/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,allow_nan=False))
    if result["failures"]:raise SystemExit("preflight failed")
if __name__=="__main__":main()
