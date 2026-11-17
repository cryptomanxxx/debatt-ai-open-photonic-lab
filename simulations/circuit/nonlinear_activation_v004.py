"""OPA-NL-004: conditional absorber requirements, not device calibration."""
import csv
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np
from nonlinear_activation_v001 import absorber
from nonlinear_activation_v002 import dataset
from nonlinear_activation_v003 import receiver, rng, accuracy

OUT=Path("results/opa-nl-004")
PSAT=(.01,.03,.1,.3,1.,3.,10.,30.,100.)
DEPTH=(.013,.027,.1,.3,.5,.7)
THIGH=(.4,.85)
PHASE=(0.,10.,30.)
SEEDS=(1301,1302,1303,1304,1305)
DRIVES=(.1,1.)
NOISE=.0031622776601683794

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def field(e,psat,depth,high,phase):
    q=abs(e)**2/psat
    t=10**(-.1)*(high-depth/(1+q))
    return e*np.sqrt(t)*np.exp(1j*np.deg2rad(phase)*q/(1+q))

def state(p,psat,tau,dt,b):
    # db/dt=(p/psat*(1-b)-b)/tau, exact constant-input step.
    q=p/psat
    eq=q/(1+q)
    return eq+(b-eq)*np.exp(-(1+q)*dt/tau)

def main():
    root=Path("results/opa-nl-003")
    prov=json.loads((root/"provenance.json").read_text())
    names=("weights.json","result.json","receiver.csv")
    before={n:sha(root/n) for n in names}
    if any(before[n]!=prov["files"][n]["sha256"] for n in names):
        raise ValueError("archive mismatch")
    weights=json.loads((root/"weights.json").read_text())
    weights=[w for w in weights if w["kind"]=="absorber"]
    e=np.linspace(-2,2,1001)
    checks={"baseline_transfer":bool(np.allclose(field(e,1,.7,.85,0),absorber(e,1,1),atol=1e-13))}
    checks["phase_equivariance"]=bool(np.allclose(field(e*np.exp(.4j),1,.7,.85,30),field(e,1,.7,.85,30)*np.exp(.4j)))
    checks["state_equilibrium"]=bool(abs(state(.3,1,10,1000,0)-.3/1.3)<1e-12)
    checks["state_semigroup"]=bool(abs(state(.3,1,10,20,.2)-state(.3,1,10,10,state(.3,1,10,10,.2)))<1e-12)
    checks["state_recovery"]=bool(abs(state(0,1,10,10,1)-np.exp(-1))<1e-12)
    rows=[]; base=[]; curves=[]; dynamic=[]
    for ps,d,h,ph in itertools.product(PSAT,DEPTH,THIGH,PHASE):
        if d>=h:continue
        a=field(e,ps,d,h,ph)
        curves.append(dict(psat_mw=ps,depth=d,high=h,phase_deg=ph,passive=bool(np.all(abs(a)<=abs(e)+1e-12))))
    for rec in weights:
        seed,drive=rec["seed"],rec["drive_mw"]
        w1,w2=np.array(rec["w1"]),np.array(rec["w2"])
        # Fresh independent held-out samples, same bounded XOR distribution.
        x,y=dataset(seed,24,2048)
        z=np.sqrt(drive)*(w1@x)
        draw=rng(seed,25).normal(size=(8,8,len(y)))
        rxdraw=rng(seed,26).normal(size=(8,len(y)))
        noise=NOISE*np.einsum("ij,rjn->rin",w2,draw)[:,0,:]
        for ps,d,h,ph in itertools.product(PSAT,DEPTH,THIGH,PHASE):
            if d>=h:continue
            a=field(z,ps,d,h,ph)
            clean=(w2@a).ravel()
            ep=clean[None,:]+noise
            i,s,_,pp,pm,*_=receiver(ep,.1,1.,3.,15.)
            sensed=i+s*rxdraw
            row=dict(seed=seed,drive_mw=drive,psat_mw=ps,depth=d,high=h,phase_deg=ph,
                clean_accuracy=accuracy(clean.real,y),
                receiver_accuracy=accuracy(sensed,y),
                worst_repeat_accuracy=float(np.min(np.mean((sensed>0)==y,axis=1))),
                mean_output_uw=float(np.mean(abs(clean)**2)*1000),
                min_signed_real_field=float(np.min((2*y-1)*clean.real)),
                peak_input_mw=float(np.max(abs(z)**2)),
                peak_diode_mw=float(max(np.max(pp),np.max(pm))*1000),
                passivity_excess_mw=float(max(np.max(np.sum(abs(a)**2,axis=0)-np.sum(abs(z)**2,axis=0)),np.max(abs(clean)**2-np.sum(abs(a)**2,axis=0)))))
            rows.append(row)
            if (ps,d,h,ph)==(1.,.7,.85,0.):base.append(row)
        print("completed",seed,drive,flush=True)
    # Dimensionless transient requirements: illustrative lumped rate law,
    # not a fit to pump-probe FWHM or physical pulse propagation.
    for q,tau,period in itertools.product((.1,1.,10.),(1.,10.,100.),(10.,100.,1000.)):
        on=state(q,1.,tau,period/2,0.)
        off=state(0.,1.,tau,period/2,on)
        dynamic.append(dict(power_over_psat=q,tau_ps=tau,period_ps=period,
            on_state=on,off_state=off,equilibrium=q/(1+q),
            fractional_equilibrium=on/(q/(1+q)),residual_fraction=off/on))
    groups={}
    for r in rows:
        key=tuple(r[k] for k in ("drive_mw","psat_mw","depth","high","phase_deg"))
        groups.setdefault(key,[]).append(r)
    summary=[]
    for key,rs in groups.items():
        summary.append(dict(zip(("drive_mw","psat_mw","depth","high","phase_deg"),key),
            seeds=len(rs),mean_accuracy=float(np.mean([r["receiver_accuracy"] for r in rs])),
            worst_repeat=min(r["worst_repeat_accuracy"] for r in rs),
            all_clean95=all(r["clean_accuracy"]>=.95 for r in rs),
            screen_pass=all(r["worst_repeat_accuracy"]>=.95 and r["clean_accuracy"]>=.95 and r["peak_diode_mw"]<=2 for r in rs)))
    checks.update(weights=len(weights)==10,rows=len(rows)==2700,groups=len(summary)==540,
        baseline_count=len(base)==10,passivity=all(r["passivity_excess_mw"]<=1e-9 for r in rows) and all(r["passive"] for r in curves),
        finite=all(np.isfinite(r["min_signed_real_field"]) for r in rows),
        dynamic_count=len(dynamic)==27,prior_immutable=before=={n:sha(root/n) for n in names})
    result=dict(experiment="OPA-NL-004",checks=checks,failures=[k for k,v in checks.items() if not v],
        rows=len(rows),configurations=len(summary),baseline=base,
        screens=[dict(drive_mw=d,passed=sum(r["screen_pass"] for r in summary if r["drive_mw"]==d),
            tested=sum(r["drive_mw"]==d for r in summary)) for d in DRIVES],
        limitations=["Hypothetical lumped transmission and phase envelope, not material fit.",
        "Published pulse energies, peak powers and pump-probe widths are not mapped to CW Psat or recovery tau.",
        "Frozen weights, fresh held-out draws; no retraining or actual device qualification.",
        "Dynamic state illustration is separate from static classifier; no speed inference.",
        "Receiver assumptions inherited from NL003; no system energy claim."])
    OUT.mkdir(parents=True,exist_ok=True)
    for name,data in (("metrics",rows),("summary",summary),("transfer_checks",curves),("dynamics",dynamic)):
        with (OUT/(name+".csv")).open("w",newline="") as f:
            wr=csv.DictWriter(f,fieldnames=list(data[0]));wr.writeheader();wr.writerows(data)
    (OUT/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,allow_nan=False))
    for p in sorted(OUT.iterdir()):
        if p.is_file():print(p.name,p.stat().st_size,sha(p))
    if result["failures"]:raise SystemExit("implementation checks failed")

if __name__=="__main__":main()
