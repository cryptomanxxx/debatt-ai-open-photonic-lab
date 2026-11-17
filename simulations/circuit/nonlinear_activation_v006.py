"""OPA-NL-006: conditional single-mode two-port resonant activation."""
import csv
import itertools
import json
import hashlib
from pathlib import Path
import numpy as np
from numpy.polynomial import Polynomial as Poly
from nonlinear_activation_v002 import dataset
from nonlinear_activation_v003 import receiver, rng, accuracy
from nonlinear_activation_v005 import transfer as distributed

OUT=Path("results/opa-nl-006")
ENDPOINTS=((.1,.4),(.15,.85),(.373,.4))
TAU=(2.,10.,50.) # external energy lifetime, ps
US=(.3,3.) # hypothetical intracavity saturation energy, fJ
TPA=(0.,.1) # dimensionless loss slope per normalized energy
DET=(0.,.5) # detuning / external decay rate
SHIFT=(0.,1.) # saturating resonance shift / external decay rate
NOISE=.0031622776601683794
DRIVES=(.1,1.)
K1=K2=.5
LOSS=10**(-.1)
KEYS=("low","high","tau_ext_ps","usat_fj","tpa","detuning","shift")

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def rates(x,ns,sa,b,d,h):
    g=1+ns+sa/(1+x)+b*x
    delta=d+h*x/(1+x)
    gp=-sa/(1+x)**2+b
    dp=h/(1+x)**2
    return g,delta,gp,dp

def response(x,ns,sa,b,d,h):
    g,delta,gp,dp=rates(x,ns,sa,b,d,h)
    f=x*((g/2)**2+delta**2)
    deriv=(g/2+x*gp)*g/2+delta*(delta+2*x*dp)
    return f,deriv,-g-x*gp

def folds(ns,sa,b,d,h):
    # F(x)=N(x)/(1+x)^2. Roots of F' from exact polynomial numerator.
    x=Poly([0,1]); den=1+x
    gn=(1+ns+b*x)*den+sa
    dn=d*den+h*x
    n=x*(gn*gn/4+dn*dn)
    q=n.deriv()*den-2*n
    roots=q.roots()
    real=sorted(float(z.real) for z in roots if abs(z.imag)<1e-7 and z.real>0)
    if any(abs(response(z,ns,sa,b,d,h)[1])>1e-6 for z in real):
        raise ValueError("fold residual")
    if any(abs(a-b)<1e-7 for a,b in zip(real,real[1:])):
        raise ValueError("near-degenerate stationary roots")
    return real

def solve(p,tau,us,ns,sa,b,d,h):
    """Enumerate roots on monotone intervals; choose lowest for diagnostics.
    All positive roots lie at x<=4*target since total loss >=1.
    """
    p=np.asarray(p,dtype=float)
    target=K1*p*tau/us
    ff=folds(ns,sa,b,d,h)
    bound=max(1.,4*float(np.max(target))+1.,*(z+1 for z in ff))
    limits=[0.]+ff+[bound]
    chosen=np.full_like(p,np.inf)
    count=np.zeros_like(p,dtype=int)
    stable=np.zeros_like(p,dtype=int)
    for l,r in zip(limits,limits[1:]):
        fl=response(l,ns,sa,b,d,h)[0]
        fr=response(r,ns,sa,b,d,h)[0]
        # Half-open at interior fold: avoid double counting identical roots.
        # Explicitly retain a near-fold flag below for marginal stability.
        mask=(target>=min(fl,fr))&(target<=max(fl,fr))
        if l!=0:
            mask &= target!=fl
        if not np.any(mask):continue
        v=target[mask]
        lo=np.full_like(v,l);hi=np.full_like(v,r)
        for _ in range(56):
            mid=(lo+hi)/2
            fm=response(mid,ns,sa,b,d,h)[0]
            left=(fm<v) if fr>fl else (fm>v)
            lo=np.where(left,mid,lo);hi=np.where(left,hi,mid)
        root=(lo+hi)/2
        root=np.where(v==0,0.,root)
        _,det,tr=response(root,ns,sa,b,d,h)
        count[mask]+=1
        stable[mask]+=(det>1e-9)&(tr< -1e-9)
        chosen[mask]=np.minimum(chosen[mask],root)
    if np.any(count<1):raise ValueError("no root")
    g,delta,_,_=rates(chosen,ns,sa,b,d,h)
    amp=np.sqrt(K1*K2)/(g/2-1j*delta)
    reflect=1-K1/(g/2-1j*delta)
    absorb=K1*(g-1)/((g/2)**2+delta**2)
    residual=np.max(abs(response(chosen,ns,sa,b,d,h)[0]-target)/(1+target))
    balance=np.max(abs(abs(amp)**2+abs(reflect)**2+absorb-1))
    # Linearized relaxation of the instantaneous material closure.
    _,det,tr=response(chosen,ns,sa,b,d,h)
    eigmax=(tr/2+np.sqrt((tr/2)**2-det+0j).real)/tau
    return amp,chosen*us,count,stable,eigmax,float(residual),float(balance)

def loss_rates(low,high):
    return 1/np.sqrt(high)-1,1/np.sqrt(low)-1/np.sqrt(high)

def main():
    prior={}
    for exp,names in (("opa-nl-003",("weights.json","result.json")),
                      ("opa-nl-005",("summary.csv","result.json","transfer.csv"))):
        root=Path("results")/exp
        prov=json.loads((root/"provenance.json").read_text())
        for name in names:
            p=root/name;prior[p]=sha(p)
            if prior[p]!=prov["files"][name]["sha256"]:
                raise ValueError("archive digest mismatch")
    weights=[r for r in json.loads(Path("results/opa-nl-003/weights.json").read_text()) if r["kind"]=="absorber"]
    cases=list(itertools.product(ENDPOINTS,TAU,US,TPA,DET,SHIFT))
    # Actual sample powers solved directly, not interpolated across folds.
    data=[]; powers=[]
    for rec in weights:
        seed,drive=rec["seed"],rec["drive_mw"]
        w1,w2=np.array(rec["w1"]),np.array(rec["w2"])
        x,y=dataset(seed,44,2048)
        z=np.sqrt(drive)*(w1@x)
        draw=rng(seed,45).normal(size=(8,8,len(y)))
        rxdraw=rng(seed,46).normal(size=(8,len(y)))
        noise=NOISE*np.einsum("ij,rjn->rin",w2,draw)[:,0,:]
        data.append((seed,drive,z,y,w2,noise,rxdraw))
        powers.append(abs(z).ravel()**2)
    grid=np.r_[0.,np.geomspace(1e-8,4.,512)]
    allp=np.concatenate([grid]+powers)
    if allp.max()>4:raise ValueError("power outside study range")
    def evaluate(a,z,y,w2,noise,rxdraw):
        clean=(w2@a).ravel()
        i,s,_,pp,pm,*_=receiver(clean[None,:]+noise,.1,1.,3.,15.)
        sensed=i+s*rxdraw
        return dict(clean_accuracy=accuracy(clean.real,y),receiver_accuracy=accuracy(sensed,y),
            worst_repeat=float(np.min(np.mean((sensed>0)==y,axis=1))),
            output_uw=float(np.mean(abs(clean)**2)*1000),
            min_signed_field=float(np.min((2*y-1)*clean.real)),
            peak_diode_mw=float(max(np.max(pp),np.max(pm))*1000),
            passivity_excess=float(max(np.max(np.sum(abs(a)**2,axis=0)-np.sum(abs(z)**2,axis=0)),
                np.max(abs(clean)**2-np.sum(abs(a)**2,axis=0)))))
    rows=[];curves=[];audits=[];refs=[]
    for seed,drive,z,y,w2,noise,rxdraw in data:
        for name,ps,l,h,b,ph in (("A",.03,.1,.4,0.,0.),("B",.1,.1,.4,.1,0.),("C",.1,.15,.85,.1,10.)):
            a=distributed(z,ps,l,h,b,ph,128)
            refs.append(dict(seed=seed,drive_mw=drive,reference=name,**evaluate(a,z,y,w2,noise,rxdraw)))
    for (low,high),tau,us,b,d,h in cases:
        ns,sa=loss_rates(low,high)
        params=dict(zip(KEYS,(low,high,tau,us,b,d,h)))
        amp,u,n,st,eig,res,bal=solve(allp,tau,us,ns,sa,b,d,h)
        ff=folds(ns,sa,b,d,h)
        fp=[response(x,ns,sa,b,d,h)[0]*us/(K1*tau) for x in ff]
        # Conservative global single-valued screen across 0..4 mW:
        # reject every fold in range even if the sampled points miss it.
        fold_in_range=any(0<=v<=4 for v in fp)
        grid_ok=bool(not fold_in_range and np.all(n[:len(grid)]==1) and
                     np.all(st[:len(grid)]==1) and np.all(eig[:len(grid)]<0))
        audits.append(dict(**params,fold_count=len(ff),fold_in_range=fold_in_range,
            fold_powers_mw=json.dumps(fp),grid_unique_stable=grid_ok,
            max_roots=int(n.max()),max_stable_roots=int(st.max()),
            residual=res,balance=bal,peak_transmission=float(np.max(abs(amp)**2)),
            min_relaxation_rate_per_ps=float(-eig.max())))
        for p,a,en,nr,sr,ev in zip(grid[::8],amp[:len(grid):8],u[:len(grid):8],
                                    n[:len(grid):8],st[:len(grid):8],eig[:len(grid):8]):
            curves.append(dict(**params,input_mw=float(p),transmission=float(abs(a)**2),
                phase_rad=float(np.angle(a)),energy_fj=float(en),roots=int(nr),
                stable_roots=int(sr),max_eigen_real_per_ps=float(ev)))
        offset=len(grid)
        for seed,drive,z,y,w2,noise,rxdraw in data:
            sl=slice(offset,offset+z.size);offset+=z.size
            a=z*amp[sl].reshape(z.shape)*np.sqrt(LOSS)
            eligible=bool(grid_ok and np.all(n[sl]==1) and np.all(st[sl]==1) and np.all(eig[sl]<0))
            rows.append(dict(**params,seed=seed,drive_mw=drive,unique_stable=eligible,
                ambiguous_inputs=int(np.sum(n[sl]>1)),peak_energy_fj=float(u[sl].max()),
                peak_input_mw=float(np.max(abs(z)**2)),**evaluate(a,z,y,w2,noise,rxdraw)))
    groups={}
    for row in rows:
        groups.setdefault(tuple(row[k] for k in ("drive_mw",)+KEYS),[]).append(row)
    summary=[]
    for k,rs in groups.items():
        summary.append(dict(zip(("drive_mw",)+KEYS,k),seeds=len(rs),
            mean_accuracy=float(np.mean([r["receiver_accuracy"] for r in rs])),
            worst_repeat=min(r["worst_repeat"] for r in rs),
            min_clean=min(r["clean_accuracy"] for r in rs),
            all_unique_stable=all(r["unique_stable"] for r in rs),
            screen_pass=all(r["unique_stable"] and r["clean_accuracy"]>=.95 and
                r["worst_repeat"]>=.95 and r["peak_diode_mw"]<=2 for r in rs)))
    # Independent linear resonator, endpoint and bistability checks.
    pp=np.array([0.,.01,.3,4.])
    amp,u,n,st,ev,res,bal=solve(pp,10.,.3,.2,0.,0.,.5,0.)
    exact=.5/(.6-.5j)
    ns,sa=loss_rates(.1,.4)
    ends=solve(np.array([0.,1e8]),10.,.3,ns,sa,0.,0.,0.)[0]
    stress_folds=folds(.1,20.,0.,0.,0.)
    mid=np.mean([response(x,.1,20.,0.,0.,0.)[0] for x in stress_folds])
    stress_p=mid*.3/(K1*10.)
    stress=solve(np.array([stress_p]),10.,.3,.1,20.,0.,0.,0.)
    # Compare analytic Jacobian invariants against finite differences.
    x=1.7;ns,sa,b,d,h=.2,2.,.1,.5,1.
    def ode(v):
        xx=v@v;g,delta,*_=rates(xx,ns,sa,b,d,h)
        return np.array([-g*v[0]/2-delta*v[1],delta*v[0]-g*v[1]/2])
    v=np.array([np.sqrt(x),0.]);eps=1e-5
    jac=np.column_stack([(ode(v+dv)-ode(v-dv))/(2*eps) for dv in np.eye(2)*eps])
    _,det,tr=response(x,ns,sa,b,d,h)
    checks=dict(linear_transfer=bool(np.allclose(amp,exact,atol=1e-12)),
        linear_energy=bool(np.allclose(u,K1*pp*10/(.6**2+.5**2),atol=1e-10)),
        linear_stability=bool(np.all(n==1) and np.all(st==1) and np.allclose(ev,-.06)),
        endpoint_limits=bool(np.allclose(abs(ends)**2,[.1,.4],atol=1e-8)),
        bistability_stress=bool(len(stress_folds)==2 and stress[2][0]==3 and stress[3][0]==2),
        jacobian=bool(abs(np.linalg.det(jac)-det)<1e-8 and abs(np.trace(jac)-tr)<1e-8),
        root_residual=all(a["residual"]<1e-10 for a in audits),
        port_balance=all(a["balance"]<1e-12 for a in audits),
        passive=all(a["peak_transmission"]<=1+1e-12 for a in audits) and
                all(r["passivity_excess"]<=1e-9 for r in rows+refs),
        counts=len(rows)==1440 and len(summary)==288 and len(audits)==144 and len(curves)==9360,
        weights=len(weights)==10 and all(r["seeds"]==5 for r in summary),
        references=len(refs)==30,
        finite=all(np.isfinite(r["min_signed_field"]) for r in rows+refs),
        prior_immutable=all(sha(p)==v for p,v in prior.items()))
    result=dict(experiment="OPA-NL-006",checks=checks,failures=[k for k,v in checks.items() if not v],
        rows=len(rows),configurations=len(summary),references=refs,
        stress=dict(input_mw=float(stress_p),roots=int(stress[2][0]),stable_roots=int(stress[3][0])),
        max_residual=max(a["residual"] for a in audits),max_balance=max(a["balance"] for a in audits),
        ambiguous_cavities=sum(not a["grid_unique_stable"] for a in audits),
        screens=[dict(drive_mw=d,low=l,high=h,passed=sum(r["screen_pass"] for r in summary
                    if r["drive_mw"]==d and r["low"]==l and r["high"]==h),tested=48)
                 for d,(l,h) in itertools.product(DRIVES,ENDPOINTS)],
        limitations=["Hypothetical single-mode symmetric two-port cavity, no calibrated material or geometry.",
            "Instantaneous saturation closure; no carrier recovery, pulse train or thermal dynamics.",
            "External lifetime is not loaded lifetime; no symbol rate or energy advantage inferred.",
            "Frozen weights and conditional receiver; no retraining. Lowest root is diagnostic only for ambiguous cases."])
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
