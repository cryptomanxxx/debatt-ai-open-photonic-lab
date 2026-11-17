"""OPA-NL-005: conditional distributed saturable-loss waveguide, not a material fit."""
import csv
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np
from nonlinear_activation_v002 import dataset
from nonlinear_activation_v003 import receiver, rng, accuracy
from nonlinear_activation_v004 import field

OUT=Path("results/opa-nl-005")
PSAT=(.03,.1,.3,1.,3.)
TPA=(0.,.1,1.) # integrated coefficient in inverse mW
PHASE=(0.,10.,30.) # maximum integrated bleaching phase in degrees
# Endpoints before extra 1 dB loss; not measured material constants.
ENDPOINTS=((.1,.4),(.15,.85),(.373,.4))
NOISE=.0031622776601683794
SEEDS=(1301,1302,1303,1304,1305)
DRIVES=(.1,1.)
LENGTH_UM=75. # illustrative length, not calibration to Reep et al.

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def propagate(p,psat,low,high,tpa,phase,steps):
    """Normalized position u=z/L. Integrate log(P/P0), phase.
    Log-power integration preserves positivity even at zero input.
    """
    a=-np.log(high)
    b=np.log(high/low)
    logt=np.zeros_like(p,dtype=float)
    phi=np.zeros_like(p,dtype=float)
    dt=1./steps
    def rhs(v):
        q=p*np.exp(v)
        bleach=q/(psat+q)
        return -a-b*(1-bleach)-tpa*q,np.deg2rad(phase)*bleach
    for _ in range(steps):
        k1,f1=rhs(logt)
        k2,f2=rhs(logt+dt*k1/2)
        k3,f3=rhs(logt+dt*k2/2)
        k4,f4=rhs(logt+dt*k3)
        logt+=dt*(k1+2*k2+2*k3+k4)/6
        phi+=dt*(f1+2*f2+2*f3+f4)/6
    return np.exp(logt),phi

def transfer(e,psat,low,high,tpa,phase,steps):
    t,phi=propagate(abs(e)**2,psat,low,high,tpa,phase,steps)
    return e*np.sqrt(t*10**(-.1))*np.exp(1j*phi)

def main():
    prior={}
    for exp,names in (("opa-nl-003",("weights.json","result.json")),
                      ("opa-nl-004",("summary.csv","result.json"))):
        root=Path("results")/exp
        prov=json.loads((root/"provenance.json").read_text())
        for name in names:
            p=root/name
            prior[p]=sha(p)
            if prior[p]!=prov["files"][name]["sha256"]:
                raise ValueError("archive digest mismatch")
    weights=[r for r in json.loads(Path("results/opa-nl-003/weights.json").read_text()) if r["kind"]=="absorber"]
    configs=list(itertools.product(ENDPOINTS,PSAT,TPA,PHASE))
    # Logarithmic grid covers all actual per-channel powers (verified below).
    grid=np.r_[0.,np.geomspace(1e-12,4.,2048)]
    table={}; curves=[]; convergence=[]
    for (low,high),ps,tpa,ph in configs:
        t32,f32=propagate(grid,ps,low,high,tpa,ph,32)
        t64,f64=propagate(grid,ps,low,high,tpa,ph,64)
        t128,f128=propagate(grid,ps,low,high,tpa,ph,128)
        # Interpolation error assessed against independent off-grid points.
        mid=np.sqrt(grid[1:-1]*grid[2:])
        tm,fm=propagate(mid,ps,low,high,tpa,ph,128)
        ti=np.interp(mid,grid,t128);fi=np.interp(mid,grid,f128)
        key=(low,high,ps,tpa,ph)
        table[key]=(t128,f128)
        convergence.append(dict(low=low,high=high,psat_mw=ps,tpa_per_mw=tpa,phase_deg=ph,
            coarse_error=float(max(np.max(abs(t32-t64)),np.max(abs(f32-f64)))),
            fine_error=float(max(np.max(abs(t64-t128)),np.max(abs(f64-f128)))),
            interpolation_error=float(max(np.max(abs(ti-tm)),np.max(abs(fi-fm)))),
            passive=bool(np.all((t128>0)&(t128<=1)) and np.all(f128>=-1e-12) and np.all(f128<=np.deg2rad(ph)+1e-12))))
        for p,t,f in zip(grid[::32],t128[::32],f128[::32]):
            curves.append(dict(low=low,high=high,psat_mw=ps,tpa_per_mw=tpa,phase_deg=ph,input_mw=float(p),
                               transmission=float(t),phase_rad=float(f)))
    # Independent analytic limits.
    p=np.array([0.,.01,.3,1.,4.])
    t,f=propagate(p,.3,.4,.4,0.,0.,128)
    checks={"linear_beer_lambert":bool(np.allclose(t,.4,atol=1e-12)),
            "zero_phase":bool(np.all(f==0))}
    a=-np.log(.4)
    t,_=propagate(p,.3,.4,.4,1.,0.,128)
    exact=np.exp(-a)/(1+p*(1-np.exp(-a))/a)
    checks["analytic_tpa"]=bool(np.max(abs(t-exact))<1e-7)
    t,_=propagate(np.array([0.,1e9]),.3,.1,.4,0.,0.,128)
    checks["endpoint_limits"]=bool(np.allclose(t,[.1,.4],atol=1e-8))
    e=np.array([-1.,0.,1.])
    checks["phase_equivariance"]=bool(np.allclose(transfer(e*np.exp(.4j),.3,.1,.4,.1,10.,128),
        transfer(e,.3,.1,.4,.1,10.,128)*np.exp(.4j)))
    checks["convergence"]=all(r["fine_error"]<1e-6 and r["interpolation_error"]<1e-4 for r in convergence)
    checks["transfer_passivity"]=all(r["passive"] for r in convergence)
    rows=[]; refs=[]
    for rec in weights:
        seed,drive=rec["seed"],rec["drive_mw"]
        w1,w2=np.array(rec["w1"]),np.array(rec["w2"])
        x,y=dataset(seed,34,2048)
        z=np.sqrt(drive)*(w1@x)
        p=abs(z)**2
        if p.max()>grid[-1]:raise ValueError("input outside transfer grid")
        draw=rng(seed,35).normal(size=(8,8,len(y)))
        rxdraw=rng(seed,36).normal(size=(8,len(y)))
        noise=NOISE*np.einsum("ij,rjn->rin",w2,draw)[:,0,:]
        def evaluate(a):
            clean=(w2@a).ravel()
            ep=clean[None,:]+noise
            i,s,_,pp,pm,*_=receiver(ep,.1,1.,3.,15.)
            sensed=i+s*rxdraw
            return dict(clean_accuracy=accuracy(clean.real,y),receiver_accuracy=accuracy(sensed,y),
                worst_repeat=float(np.min(np.mean((sensed>0)==y,axis=1))),
                mean_output_uw=float(np.mean(abs(clean)**2)*1000),
                min_signed_real_field=float(np.min((2*y-1)*clean.real)),
                peak_input_mw=float(p.max()),
                peak_diode_mw=float(max(np.max(pp),np.max(pm))*1000),
                passivity_excess_mw=float(max(np.max(np.sum(abs(a)**2,axis=0)-np.sum(p,axis=0)),
                    np.max(abs(clean)**2-np.sum(abs(a)**2,axis=0)))))
        for name,ps,dep,h in (("NL003",1.,.7,.85),("NL004",.3,.3,.4)):
            refs.append(dict(seed=seed,drive_mw=drive,reference=name,**evaluate(field(z,ps,dep,h,0.))))
        for key,(t,f) in table.items():
            low,high,ps,tpa,ph=key
            a=z*np.sqrt(np.interp(p,grid,t)*10**(-.1))*np.exp(1j*np.interp(p,grid,f))
            rows.append(dict(seed=seed,drive_mw=drive,low=low,high=high,psat_mw=ps,tpa_per_mw=tpa,phase_deg=ph,**evaluate(a)))
    groups={}
    keys=("drive_mw","low","high","psat_mw","tpa_per_mw","phase_deg")
    for r in rows:
        groups.setdefault(tuple(r[k] for k in keys),[]).append(r)
    summary=[]
    for key,rs in groups.items():
        summary.append(dict(zip(keys,key),seeds=len(rs),mean_accuracy=float(np.mean([r["receiver_accuracy"] for r in rs])),
            worst_repeat=min(r["worst_repeat"] for r in rs),
            min_clean=min(r["clean_accuracy"] for r in rs),
            screen_pass=all(r["clean_accuracy"]>=.95 and r["worst_repeat"]>=.95 and r["peak_diode_mw"]<=2 for r in rs)))
    checks.update(weights=len(weights)==10,rows=len(rows)==1350,groups=len(summary)==270,
        seeds=all(r["seeds"]==5 for r in summary),references=len(refs)==20,
        passivity=all(r["passivity_excess_mw"]<=1e-9 for r in rows+refs),
        finite=all(np.isfinite(r["min_signed_real_field"]) for r in rows+refs),
        prior_immutable=all(sha(p)==v for p,v in prior.items()))
    result=dict(experiment="OPA-NL-005",checks=checks,failures=[k for k,v in checks.items() if not v],
        rows=len(rows),configurations=len(summary),references=refs,
        max_fine_error=max(r["fine_error"] for r in convergence),
        max_interpolation_error=max(r["interpolation_error"] for r in convergence),
        screens=[dict(drive_mw=d,low=l,high=h,passed=sum(r["screen_pass"] for r in summary if r["drive_mw"]==d and r["low"]==l and r["high"]==h),tested=45)
                 for d,(l,h) in itertools.product(DRIVES,ENDPOINTS)],
        limitations=["Conditional steady-state propagation, not a calibrated graphene model or cavity simulation.",
                     "75 um illustrative length; integrated coefficients are derived from hypothetical endpoint transmissions.",
                     "No measured TPA coefficient, modal overlap, recovery or pulse dynamics; no retraining.",
                     "Fixed inherited coherent receiver; no hardware throughput or system energy claim."])
    OUT.mkdir(parents=True,exist_ok=True)
    for name,data in (("metrics",rows),("summary",summary),("references",refs),("convergence",convergence),("transfer",curves)):
        with (OUT/(name+".csv")).open("w",newline="") as f:
            wr=csv.DictWriter(f,fieldnames=list(data[0]));wr.writeheader();wr.writerows(data)
    (OUT/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,allow_nan=False))
    for p in sorted(OUT.iterdir()):
        if p.is_file():print(p.name,p.stat().st_size,sha(p))
    if result["failures"]:raise SystemExit("implementation checks failed")

if __name__=="__main__":main()
