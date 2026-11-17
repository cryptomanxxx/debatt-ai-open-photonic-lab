"""OPA-NL-007: paired complex-transfer ablations and detuning tolerance."""
import csv
import itertools
import json
from pathlib import Path
import numpy as np
from nonlinear_activation_v002 import dataset
from nonlinear_activation_v003 import receiver, rng, accuracy
from nonlinear_activation_v005 import transfer as distributed
from nonlinear_activation_v006 import solve, folds, response, loss_rates, sha, LOSS, NOISE, K1

OUT=Path("results/opa-nl-007")
# W1/W2/W3 from NL006; S1/S2 are perfect common-drive controls.
BASE={"W1":(.373,.4,2.,3.,0.,-.5,1.),
      "W2":(.373,.4,10.,3.,0.,-.5,1.),
      "W3":(.373,.4,10.,3.,.1,-.5,1.),
      "S1":(.1,.4,10.,.3,0.,0.,0.),
      "S2":(.15,.85,10.,.3,0.,0.,0.)}
MODES=("full","amplitude_only","phase_only","linear","no_bleaching","no_shift","no_bleaching_no_shift")
DET=(-.8,-.7,-.6,-.55,-.5,-.45,-.4,-.3,-.2,0.,.2)
SHIFT=(0.,.5,.8,1.,1.2,1.5)
GRID=np.r_[0.,np.geomspace(1e-8,4.,512)]

def cavity(p,params,mode):
    low,high,tau,us,b,d,h=params
    ns,sa=loss_rates(low,high)
    if mode in ("no_bleaching","no_bleaching_no_shift"):
        ns+=sa;sa=0.
    if mode in ("no_shift","no_bleaching_no_shift"):
        h=0.
    amp,u,n,st,eig,res,bal=solve(p,tau,us,ns,sa,b,d,h)
    fp=[response(x,ns,sa,b,d,h)[0]*us/(K1*tau) for x in folds(ns,sa,b,d,h)]
    stable=bool(not any(0<=v<=4 for v in fp) and np.all(n==1) and np.all(st==1) and np.all(eig<0))
    return amp,u,dict(stable=stable,residual=res,balance=bal,
        max_roots=int(n.max()),min_relaxation_per_ps=float(-eig.max()),
        folds_in_range=sum(0<=v<=4 for v in fp))

def ablate(h,h0,mode):
    if mode=="amplitude_only":return abs(h)*np.exp(1j*np.angle(h0))
    if mode=="phase_only":return abs(h0)*np.exp(1j*np.angle(h))
    if mode=="linear":return np.full_like(h,h0)
    return h

def main():
    prior={}
    for exp,names in (("opa-nl-003",("weights.json","result.json")),
                      ("opa-nl-005",("summary.csv","result.json")),
                      ("opa-nl-006",("summary.csv","result.json","transfer.csv"))):
        root=Path("results")/exp
        prov=json.loads((root/"provenance.json").read_text())
        for name in names:
            p=root/name;prior[p]=sha(p)
            if prior[p]!=prov["files"][name]["sha256"]:raise ValueError("archive mismatch")
    weights=[r for r in json.loads(Path("results/opa-nl-003/weights.json").read_text()) if r["kind"]=="absorber"]
    data=[]
    for rec in weights:
        seed,drive=rec["seed"],rec["drive_mw"]
        w1,w2=np.array(rec["w1"]),np.array(rec["w2"])
        x,y=dataset(seed,54,2048)
        z=np.sqrt(drive)*(w1@x)
        noise=NOISE*np.einsum("ij,rjn->rin",w2,rng(seed,55).normal(size=(8,8,len(y))))[:,0,:]
        rx=rng(seed,56).normal(size=(8,len(y)))
        data.append((seed,drive,z,y,w2,noise,rx))
    allp=np.concatenate([GRID]+[abs(z).ravel()**2 for _,_,z,*_ in data])
    if allp.max()>4:raise ValueError("input outside range")
    def evaluate(a,z,y,w2,noise,rx):
        clean=(w2@a).ravel()
        i,s,_,pp,pm,*_=receiver(clean[None,:]+noise,.1,1.,3.,15.)
        sensed=i+s*rx
        # Clean receiver projection includes fixed phase offset, unlike pre-RX clean gate.
        return dict(clean_accuracy=accuracy(clean.real,y),
            projected_accuracy=accuracy((clean*np.exp(1j*np.deg2rad(15))).real,y),
            receiver_accuracy=accuracy(sensed,y),
            worst_repeat=float(np.min(np.mean((sensed>0)==y,axis=1))),
            output_uw=float(np.mean(abs(clean)**2)*1000),
            min_signed_field=float(np.min((2*y-1)*clean.real)),
            min_projected_field=float(np.min((2*y-1)*(clean*np.exp(1j*np.deg2rad(15))).real)),
            peak_diode_mw=float(max(np.max(pp),np.max(pm))*1000),
            passivity_excess=float(max(np.max(np.sum(abs(a)**2,axis=0)-np.sum(abs(z)**2,axis=0)),
                np.max(abs(clean)**2-np.sum(abs(a)**2,axis=0)))))
    rows=[];audits=[];curves=[];refs=[]
    checks={}
    for seed,drive,z,y,w2,noise,rx in data:
        for name,ps,l,h,b,ph in (("A",.03,.1,.4,0.,0.),("B",.1,.1,.4,.1,0.),("C",.1,.15,.85,.1,10.)):
            refs.append(dict(seed=seed,drive_mw=drive,reference=name,
                **evaluate(distributed(z,ps,l,h,b,ph,128),z,y,w2,noise,rx)))
    cases=[("mechanism",name,params,mode) for name,params in BASE.items() for mode in MODES]
    cases += [("tolerance",name,BASE[name][:5]+(d,h),mode)
              for name,d,h,mode in itertools.product(("W2","W3"),DET,SHIFT,("full","no_bleaching"))]
    cache={}
    for family,name,params,mode in cases:
        phys=mode if mode in ("no_bleaching","no_shift","no_bleaching_no_shift") else "full"
        cachekey=(params,phys)
        if cachekey not in cache:
            cache[cachekey]=cavity(allp,params,phys)
        h,u,audit=cache[cachekey]
        gain=ablate(h,h[0],mode)
        # In diagnostic modes the energy/stability are of the parent cavity, not the ablated transfer.
        low,high,tau,us,b,d,shift=params
        meta=dict(family=family,candidate=name,mode=mode,low=low,high=high,
                  tau_ext_ps=tau,usat_fj=us,tpa=b,detuning=d,shift=shift)
        diagnostic=mode in ("amplitude_only","phase_only","linear")
        audits.append(dict(**meta,diagnostic=diagnostic,**audit,
            max_gain=float(np.max(abs(gain))),min_gain=float(np.min(abs(gain)))))
        for p,g,en in zip(GRID[::8],gain[:len(GRID):8],u[:len(GRID):8]):
            curves.append(dict(**meta,input_mw=float(p),transmission=float(abs(g)**2),
                phase_rad=float(np.angle(g)),parent_energy_fj=float(en)))
        offset=len(GRID)
        for seed,drive,z,y,w2,noise,rx in data:
            sl=slice(offset,offset+z.size);offset+=z.size
            g=gain[sl].reshape(z.shape)
            a=z*g*np.sqrt(LOSS)
            rows.append(dict(**meta,seed=seed,drive_mw=drive,parent_stable=audit["stable"],
                peak_parent_energy_fj=float(u[sl].max()),peak_input_mw=float(np.max(abs(z)**2)),
                transmission_swing=float(np.ptp(abs(g)**2)),phase_swing_rad=float(np.ptp(np.angle(g))),
                **evaluate(a,z,y,w2,noise,rx)))
    fields=("family","candidate","mode","low","high","tau_ext_ps","usat_fj","tpa","detuning","shift","drive_mw")
    grouped={}
    for r in rows:grouped.setdefault(tuple(r[k] for k in fields),[]).append(r)
    summary=[]
    for k,rs in grouped.items():
        summary.append(dict(zip(fields,k),seeds=len(rs),
            mean_accuracy=float(np.mean([r["receiver_accuracy"] for r in rs])),
            worst_repeat=min(r["worst_repeat"] for r in rs),
            min_clean=min(r["clean_accuracy"] for r in rs),
            min_projected=min(r["projected_accuracy"] for r in rs),
            all_parent_stable=all(r["parent_stable"] for r in rs),
            screen_pass=all(r["parent_stable"] and r["clean_accuracy"]>=.95 and
                r["worst_repeat"]>=.95 and r["peak_diode_mw"]<=2 for r in rs)))
    # Independent identities for numerical ablation and constant-loss TCMT.
    h=np.array([.3-.2j,.5+.1j,.2+.3j])
    aa=ablate(h,h[0],"amplitude_only");ph=ablate(h,h[0],"phase_only")
    checks["amplitude_identity"]=bool(np.allclose(abs(aa),abs(h)) and np.allclose(np.angle(aa),np.angle(h[0])))
    checks["phase_identity"]=bool(np.allclose(abs(ph),abs(h[0])) and np.allclose(np.angle(ph),np.angle(h)))
    checks["linear_identity"]=bool(np.all(ablate(h,h[0],"linear")==h[0]))
    p=np.array([0.,.1,1.,4.])
    q,_,_=cavity(p,BASE["W2"],"no_bleaching_no_shift")
    ns,sa=loss_rates(.373,.4)
    checks["constant_loss_linear_limit"]=bool(np.allclose(q,.5/((1+ns+sa)/2+.5j),atol=1e-12))
    checks["low_power_match"]=all(np.allclose(cavity(np.array([0.]),v,"full")[0],
        cavity(np.array([0.]),v,"no_bleaching")[0],atol=1e-12) for v in BASE.values())
    checks["root_residual"]=all(a["residual"]<1e-10 for a in audits)
    checks["port_balance"]=all(a["balance"]<1e-12 for a in audits)
    checks["passivity"]=all(a["max_gain"]<=1+1e-12 for a in audits) and all(r["passivity_excess"]<=1e-9 for r in rows+refs)
    checks["counts"]=len(cases)==299 and len(rows)==2990 and len(summary)==598 and len(curves)==19435 and len(audits)==299
    checks["weights"]=len(weights)==10 and all(r["seeds"]==5 for r in summary)
    checks["references"]=len(refs)==30
    checks["finite"]=all(np.isfinite(r["min_projected_field"]) for r in rows+refs)
    checks["prior_immutable"]=all(sha(p)==v for p,v in prior.items())
    # Duplicate nominal points must reproduce across mechanism/tolerance families.
    checks["nominal_replay"]=all(next(s for s in summary if s["family"]=="mechanism" and
        all(s[k]==r[k] for k in fields[1:]))["worst_repeat"]==r["worst_repeat"]
        for r in summary if r["family"]=="tolerance" and r["detuning"]==-.5 and r["shift"]==1.)
    result=dict(experiment="OPA-NL-007",checks=checks,failures=[k for k,v in checks.items() if not v],
        rows=len(rows),configurations=len(summary),references=refs,
        mechanism=[r for r in summary if r["family"]=="mechanism"],
        tolerance_screens=[dict(candidate=n,mode=mode,drive_mw=d,
          passed=sum(r["screen_pass"] for r in summary if r["family"]=="tolerance" and
              r["candidate"]==n and r["mode"]==mode and r["drive_mw"]==d),tested=66)
          for n,mode,d in itertools.product(("W2","W3"),("full","no_bleaching"),(.1,1.))],
        limitations=["Diagnostic amplitude/phase ablations are not physical port models.",
          "Physical no-bleaching controls retain unbleached linear loss; nonlinear detuning remains hypothetical.",
          "Instantaneous closure, frozen drive-specific weights, fixed receiver phase; no measured device or speed/energy claim."])
    OUT.mkdir(parents=True,exist_ok=True)
    for name,items in (("metrics",rows),("summary",summary),("transfer",curves),("cavity_audit",audits),("references",refs)):
        with (OUT/(name+".csv")).open("w",newline="") as f:
            wr=csv.DictWriter(f,fieldnames=list(items[0]));wr.writeheader();wr.writerows(items)
    (OUT/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,allow_nan=False))
    for p in sorted(OUT.iterdir()):
        if p.is_file():print(p.name,p.stat().st_size,sha(p))
    if result["failures"]:raise SystemExit("implementation checks failed")

if __name__=="__main__":main()
