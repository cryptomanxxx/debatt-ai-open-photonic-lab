"""OPA-NL-009: independent timing boundary and 64-symbol streams."""
import csv
import itertools
import json
import time
from pathlib import Path
import numpy as np
from nonlinear_activation_v002 import dataset
from nonlinear_activation_v003 import receiver, rng, accuracy
from nonlinear_activation_v006 import solve, folds, response, sha, LOSS, NOISE, K1

OUT=Path("results/opa-nl-009")
# All no-bleaching: fixed unbleached loss, tau_ext=10 ps, Us=3 fJ.
CASES={"C1":(0.,-.8,1.),"C2":(0.,-.8,.8),"C3":(0.,-.7,.8)}
TAU=10.
US=3.
NS=1/np.sqrt(.373)-1
K=1/TAU
COUP=np.sqrt(K/2)
DURATIONS=tuple(range(10,51,5))+(200,)
GAPS=(0.,20.)
RESPONSES=(0.,5.,50.)
STREAMS=8
SYMBOLS=64
N=STREAMS*SYMBOLS
HISTORIES=("cold","stream")

def rhs(a,q,s,b,d,h,tr):
    u=abs(a)**2
    x=u/US
    eq=x/(1+x)
    delta=d+h*(q if tr else eq)
    da=K*(-(1+NS+b*x)/2+1j*delta)*a+COUP*s
    dq=(eq-q)/tr if tr else np.zeros_like(q)
    # Power in mW = fJ/ps. Both ports and internal absorption.
    drop=COUP*a
    refl=s-drop
    pa=K*(NS+b*x)*u
    return da,dq,abs(refl)**2,abs(drop)**2,pa

def segment(a,q,s,b,d,h,tr,duration,dt):
    """RK4 with stage-matched energy quadrature; input constant within segment."""
    e=np.zeros((3,)+a.shape)
    if duration==0:return a,q,e
    steps=int(np.ceil(duration/dt))
    dt=duration/steps
    for _ in range(steps):
        k1,j1,*p1=rhs(a,q,s,b,d,h,tr)
        k2,j2,*p2=rhs(a+dt*k1/2,q+dt*j1/2,s,b,d,h,tr)
        k3,j3,*p3=rhs(a+dt*k2/2,q+dt*j2/2,s,b,d,h,tr)
        k4,j4,*p4=rhs(a+dt*k3,q+dt*j3,s,b,d,h,tr)
        a=a+dt*(k1+2*k2+2*k3+k4)/6
        q=q+dt*(j1+2*j2+2*j3+j4)/6
        e+=dt*(np.asarray(p1)+2*np.asarray(p2)+2*np.asarray(p3)+np.asarray(p4))/6
    return a,q,e

def simulate(z,b,d,h,tr,on,gap,dt):
    # z shape (weight set, channel, parallel stream, symbol).
    # Leading history axis: each cold slot starts at zero; stream carries state.
    shape=(2,)+z.shape[:-1]
    a=np.zeros(shape,complex);q=np.zeros(shape)
    out=np.empty((2,)+z.shape,complex)
    energies=np.zeros((2,z.shape[0],6)) # input, reflection, drop, absorption, initial, final
    max_balance=0.;min_q=0.;max_q=0.
    for j in range(z.shape[-1]):
        a[0]=0;q[0]=0
        s=np.broadcast_to(z[...,j],shape)
        initial=abs(a)**2
        a,q,e=segment(a,q,s,b,d,h,tr,on,dt)
        out[...,j]=COUP*a*np.sqrt(LOSS)
        a,q,eg=segment(a,q,np.zeros_like(s),b,d,h,tr,gap,dt)
        e+=eg
        incident=abs(s)**2*on
        final=abs(a)**2
        balance=abs(incident+initial-e.sum(axis=0)-final)/(1+incident+initial)
        max_balance=max(max_balance,float(balance.max()))
        min_q=min(min_q,float(q.min()));max_q=max(max_q,float(q.max()))
        for k,v in enumerate((incident,e[0],e[1],e[2],initial,final)):
            energies[:,:,k]+=v.sum(axis=(2,3))
    return out,energies,max_balance,min_q,max_q

def evaluate(clean,y,noise,rx):
    i,s,_,pp,pm,*_=receiver(clean[None,:]+noise,.1,1.,3.,15.)
    sensed=i+s*rx
    projected=(clean*np.exp(1j*np.deg2rad(15))).real
    return dict(clean_accuracy=accuracy(clean.real,y),projected_accuracy=accuracy(projected,y),
        receiver_accuracy=accuracy(sensed,y),worst_repeat=float(np.min(np.mean((sensed>0)==y,axis=1))),
        output_uw=float(np.mean(abs(clean)**2)*1000),
        min_projected_field=float(np.min((2*y-1)*projected)),
        peak_diode_mw=float(max(np.max(pp),np.max(pm))*1000))

def screen(r):
    return bool(r["stationary_eligible"] and r["clean_accuracy"]>=.95 and
                r["worst_repeat"]>=.95 and r["peak_diode_mw"]<=2)

def boundary_targets(flags):
    """Flags map timing tuples to four drive/history group decisions."""
    targets={(tr,on,gap) for tr,gap in itertools.product(RESPONSES,GAPS)
             for on in (10,50,200)}
    changes=[]
    for tr,gap in itertools.product(RESPONSES,GAPS):
        for lo,hi in zip(DURATIONS[:-2],DURATIONS[1:-1]):
            if flags[tr,lo,gap]!=flags[tr,hi,gap]:
                targets.update(((tr,lo,gap),(tr,hi,gap)))
                changes.append((tr,lo,hi,gap))
    return targets,changes

def main():
    started=time.monotonic()
    prior={}
    for exp,names in (("opa-nl-003",("weights.json","result.json")),
                      ("opa-nl-007",("summary.csv","result.json","transfer.csv")),
                      ("opa-nl-008",("summary.csv","result.json","metrics.csv","traces.csv","convergence.csv","references.csv","environment-lock.txt","installed-packages.json"))):
        root=Path("results")/exp
        prov=json.loads((root/"provenance.json").read_text())
        for name in names:
            p=root/name;prior[p]=sha(p)
            if prior[p]!=prov["files"][name]["sha256"]:raise ValueError("archive mismatch")
    weights=[r for r in json.loads(Path("results/opa-nl-003/weights.json").read_text()) if r["kind"]=="absorber"]
    data=[]
    for r in weights:
        seed,drive=r["seed"],r["drive_mw"]
        w1,w2=np.array(r["w1"]),np.array(r["w2"])
        x,y=dataset(seed,74,N)
        # Explicit permutation independent of labels, shared across drives/cases.
        order=rng(seed,75).permutation(N);x=x[:,order];y=y[order]
        z=np.sqrt(drive)*(w1@x)
        noise=NOISE*np.einsum("ij,rjn->rin",w2,rng(seed,76).normal(size=(8,8,N)))[:,0,:]
        rx=rng(seed,77).normal(size=(8,N))
        data.append((seed,drive,z,y,w2,noise,rx))
    z=np.stack([r[2].reshape(8,STREAMS,SYMBOLS) for r in data])
    if np.max(abs(z)**2)>4:raise ValueError("outside prior power domain")
    checks={};rows=[];audits=[];refs=[];traces=[];positions=[];confirmations=[];boundaries=[]
    baseline={key:(False,)*4 for key in itertools.product(RESPONSES,DURATIONS,GAPS)}
    targets,changes=boundary_targets(baseline)
    expected={(tr,on,gap) for tr,on,gap in itertools.product(RESPONSES,(10,50,200),GAPS)}
    baseline[5.,30,0.]=(True,False,False,False)
    extra_targets,extra_changes=boundary_targets(baseline)
    checks["boundary_selector_regression"]=(targets==expected and not changes and
        extra_targets==expected|{(5.,25,0.),(5.,30,0.),(5.,35,0.)} and
        extra_changes==[(5.,25,30,0.),(5.,30,35,0.)])
    checks["all_stream_first_symbol_match"]=True
    checks["independent_dataset_layout"]=all(len(y)==N and np.count_nonzero(y)==N//2
        for _,_,_,y,_,_,_ in data) and all(
        np.array_equal(a[3],bb[3]) for a in data for bb in data if a[0]==bb[0])
    # Worst-case integration work: all 180 timing cases confirmed at .125 ps.
    # Record exact grid step count and a short representative calibration on
    # the actual runner; not a guaranteed wall-clock bound.
    step_budget=sum(SYMBOLS*(int(np.ceil(on/dt))+int(np.ceil(gap/dt)))
        for _,tr,on,gap,dt in itertools.product(CASES,RESPONSES,DURATIONS,GAPS,(.5,.25,.125)))
    pilot_start=time.monotonic()
    simulate(z[...,:1],*CASES["C1"],5.,50.,20.,.125)
    pilot_seconds=time.monotonic()-pilot_start
    print("RK4 step budget",step_budget,"pilot seconds",pilot_seconds,
          "worst-case linear estimate seconds",step_budget*pilot_seconds/560,flush=True)
    # Analytic linear step including phase, with zero initial state.
    s=np.array([.3,-.7]);a0=np.zeros(2,complex);q0=np.zeros(2)
    a,_,e=segment(a0,q0,s,0.,-.8,0.,0.,50.,.25)
    lam=K*(-(1+NS)/2-0.8j)
    exact=COUP*s*np.expm1(lam*50)/lam
    checks["linear_step"]=bool(np.max(abs(a-exact))<1e-8)
    # Independent pointwise differential energy identity.
    aa=np.array([.3+.4j,-.5+.2j]);qq=np.array([.2,.7])
    da,_,pr,pt,pa=rhs(aa,qq,s,.1,-.8,1.5,5.)
    checks["differential_balance"]=bool(np.max(abs(2*np.real(np.conj(aa)*da)-(abs(s)**2-pr-pt-pa)))<1e-12)
    steady_errors=[]
    for name,(b,d,h) in CASES.items():
        powers=np.r_[0.,np.geomspace(1e-8,4.,512),abs(z).ravel()**2]
        H,u,n,st,eig,res,bal=solve(powers,TAU,US,NS,0.,b,d,h)
        fp=[response(x,NS,0.,b,d,h)[0]*US/(K1*TAU) for x in folds(NS,0.,b,d,h)]
        stable=bool(not any(0<=v<=4 for v in fp) and np.all(n==1) and np.all(st==1) and np.all(eig<0))
        ref=(z*H[513:].reshape(z.shape)*np.sqrt(LOSS))
        for i,(seed,drive,_,y,w2,noise,rx) in enumerate(data):
            clean=(w2@ref[i].reshape(8,N)).ravel()
            refs.append(dict(candidate=name,seed=seed,drive_mw=drive,stationary_eligible=stable,
                **evaluate(clean,y,noise,rx)))
        # Compare long constant excitation against independent all-root steady solver.
        ss=np.array([-.1,.3,1.,-np.sqrt(3.)])
        hh,*_=solve(abs(ss)**2,TAU,US,NS,0.,b,d,h)
        for tr in RESPONSES:
            aa,qq,_=segment(np.zeros_like(ss,complex),np.zeros_like(ss),ss,b,d,h,tr,1500.,.5)
            error=float(np.max(abs(COUP*aa-ss*hh)))
            steady_errors.append(error)
        cached={};flags={}
        for tr,on,gap in itertools.product(RESPONSES,DURATIONS,GAPS):
            begin=len(rows)
            coarse,ec,bc,qcmin,qcmax=simulate(z,b,d,h,tr,on,gap,.5)
            fine,ef,bf,qmin,qmax=simulate(z,b,d,h,tr,on,gap,.25)
            # Compare normalized absolute field and integrated energy errors.
            field_error=float(np.max(abs(fine-coarse)))
            energy_error=float(np.max(abs(ef-ec)/(1+abs(ef))))
            meta=dict(candidate=name,tpa=b,detuning=d,shift=h,response_ps=tr,on_ps=on,gap_ps=gap)
            audits.append(dict(**meta,stationary_eligible=stable,field_error=field_error,
                energy_error=energy_error,max_balance=max(bc,bf),q_min=min(qmin,qcmin),q_max=max(qmax,qcmax)))
            checks["all_stream_first_symbol_match"] &= bool(np.array_equal(fine[0,...,0],fine[1,...,0]))
            cached[tr,on,gap]=(fine,ef)
            for i,(seed,drive,_,y,w2,noise,rx) in enumerate(data):
                stat=(w2@ref[i].reshape(8,N)).ravel()
                cold=(w2@fine[0,i].reshape(8,N)).ravel()
                stream=(w2@fine[1,i].reshape(8,N)).ravel()
                for j,history in enumerate(HISTORIES):
                    f=fine[j,i].reshape(8,N)
                    clean=(w2@f).ravel()
                    en=ef[j,i]
                    rows.append(dict(**meta,seed=seed,drive_mw=drive,history=history,
                        stationary_eligible=stable,max_field_error_vs_steady=float(np.max(abs(clean-stat))),
                        max_memory_field=float(np.max(abs(clean-cold))),
                        input_fj=float(en[0]),reflection_fj=float(en[1]),drop_fj=float(en[2]),
                        absorption_fj=float(en[3]),initial_fj=float(en[4]),final_fj=float(en[5]),
                        mvm_excess=float(np.max(abs(clean)**2-np.sum(abs(f)**2,axis=0))),
                        **evaluate(clean,y,noise,rx)))
                    projected=(clean*np.exp(1j*np.deg2rad(15))).real
                    margin=((2*y-1)*projected).reshape(STREAMS,SYMBOLS)
                    correct=((clean.real>0)==y).reshape(STREAMS,SYMBOLS)
                    memory=abs(clean-cold).reshape(STREAMS,SYMBOLS)
                    for pos in range(SYMBOLS):
                        positions.append(dict(**meta,seed=seed,drive_mw=drive,history=history,
                            symbol=pos,clean_accuracy=float(correct[:,pos].mean()),
                            min_signed_projected_margin=float(margin[:,pos].min()),
                            max_memory_field=float(memory[:,pos].max())))
                    rows[-1].update(first8_accuracy=float(correct[:,:8].mean()),
                        last8_accuracy=float(correct[:,-8:].mean()),
                        first8_memory=float(memory[:,:8].max()),
                        last8_memory=float(memory[:,-8:].max()))
                # One fixed stream per weight set, first and last symbol included.
                for j in range(SYMBOLS):
                    k=j
                    traces.append(dict(**meta,seed=seed,drive_mw=drive,symbol=j,label=int(y[k]),
                        cold_real=float(cold[k].real),cold_imag=float(cold[k].imag),
                        stream_real=float(stream[k].real),stream_imag=float(stream[k].imag),
                        steady_real=float(stat[k].real),steady_imag=float(stat[k].imag)))
            flags[tr,on,gap]=tuple(all(screen(r) for r in rows[begin:]
                if r["drive_mw"]==drive and r["history"]==history)
                for drive,history in itertools.product((.1,1.),HISTORIES))
        targets,changes=boundary_targets(flags)
        boundaries.extend(dict(candidate=name,response_ps=tr,lower_ps=lo,upper_ps=hi,gap_ps=gap)
            for tr,lo,hi,gap in changes)
        for tr,on,gap in sorted(targets):
            fine,ef=cached[tr,on,gap]
            extra,ee,be,qlo,qhi=simulate(z,b,d,h,tr,on,gap,.125)
            decisions=[]
            for drive,history in itertools.product((.1,1.),HISTORIES):
                results=[]
                for i,(seed,dd,_,y,w2,noise,rx) in enumerate(data):
                    if dd!=drive:continue
                    f=extra[HISTORIES.index(history),i].reshape(8,N)
                    clean=(w2@f).ravel()
                    results.append(screen(dict(stationary_eligible=stable,**evaluate(clean,y,noise,rx))))
                decisions.append(all(results))
            confirmations.append(dict(candidate=name,response_ps=tr,on_ps=on,gap_ps=gap,
                field_error=float(np.max(abs(extra-fine))),
                energy_error=float(np.max(abs(ee-ef)/(1+abs(ee)))),max_balance=be,
                q_min=qlo,q_max=qhi,gate_agrees=tuple(decisions)==flags[tr,on,gap]))
        print(name,"completed; elapsed seconds",round(time.monotonic()-started,1),flush=True)
    keys=("candidate","tpa","detuning","shift","response_ps","on_ps","gap_ps","drive_mw","history")
    grouped={}
    for r in rows:grouped.setdefault(tuple(r[k] for k in keys),[]).append(r)
    summary=[]
    for key,rs in grouped.items():
        summary.append(dict(zip(keys,key),seeds=len(rs),mean_accuracy=float(np.mean([r["receiver_accuracy"] for r in rs])),
            worst_repeat=min(r["worst_repeat"] for r in rs),min_clean=min(r["clean_accuracy"] for r in rs),
            min_projected=min(r["projected_accuracy"] for r in rs),
            max_memory_field=max(r["max_memory_field"] for r in rs),
            max_field_error_vs_steady=max(r["max_field_error_vs_steady"] for r in rs),
            screen_pass=all(r["stationary_eligible"] and r["clean_accuracy"]>=.95 and
                r["worst_repeat"]>=.95 and r["peak_diode_mw"]<=2 for r in rs)))
    checks["steady_limit"]=max(steady_errors)<1e-7
    checks["energy_balance"]=all(r["max_balance"]<1e-6 for r in audits)
    checks["field_convergence"]=all(r["field_error"]<1e-5 for r in audits)
    checks["energy_convergence"]=all(r["energy_error"]<1e-5 for r in audits)
    checks["state_bounds"]=all(r["q_min"]>=-1e-10 and r["q_max"]<=1+1e-10 for r in audits)
    checks["mvm_contraction"]=all(r["mvm_excess"]<=1e-9 for r in rows)
    checks["counts"]=len(rows)==3600 and len(summary)==720 and len(audits)==180 and len(refs)==30 and len(traces)==115200 and len(positions)==230400
    checks["extra_convergence"]=all(r["field_error"]<1e-5 and r["energy_error"]<1e-5
        and r["max_balance"]<1e-6 and r["q_min"]>=-1e-10 and r["q_max"]<=1+1e-10
        and r["gate_agrees"] for r in confirmations)
    checks["boundary_controls"]=all(any(r["candidate"]==name and r["response_ps"]==tr
        and r["on_ps"]==on and r["gap_ps"]==gap for r in confirmations)
        for name,tr,on,gap in itertools.product(CASES,RESPONSES,(10,50,200),GAPS))
    checks["weights"]=len(weights)==10 and len({(r["seed"],r["drive_mw"]) for r in weights})==10 and all(r["seeds"]==5 for r in summary)
    checks["cold_memory_zero"]=all(r["max_memory_field"]==0 for r in rows if r["history"]=="cold")
    checks["first_symbol_match"]=all(r["cold_real"]==r["stream_real"] and r["cold_imag"]==r["stream_imag"] for r in traces if r["symbol"]==0)
    checks["finite"]=all(np.isfinite(v) for r in rows+audits+refs+positions+traces+confirmations for v in r.values() if isinstance(v,(float,int)))
    checks["prior_immutable"]=all(sha(p)==v for p,v in prior.items())
    result=dict(experiment="OPA-NL-009",checks=checks,failures=[k for k,v in checks.items() if not v],
        rows=len(rows),configurations=len(summary),references=refs,steady_max_error=max(steady_errors),
        max_balance=max(r["max_balance"] for r in audits),max_field_error=max(r["field_error"] for r in audits),
        max_energy_error=max(r["energy_error"] for r in audits),
        screens=[dict(candidate=n,drive_mw=d,history=h,passed=sum(r["screen_pass"] for r in summary
            if r["candidate"]==n and r["drive_mw"]==d and r["history"]==h),tested=60)
            for n,d,h in itertools.product(CASES,(.1,1.),HISTORIES)],
        boundaries=boundaries,confirmation_count=len(confirmations),rng_domains=[74,75,76,77],
        rk4_worst_case_steps=step_budget,pilot_seconds=pilot_seconds,
        stream_passes=[r for r in summary if r["history"]=="stream" and r["screen_pass"]],
        limitations=["Phenomenological finite index response, no material calibration or pulse propagation geometry.",
          "Rectangular signed envelopes, end-of-on sampling, 8 independent 64-symbol streams; cold reset is diagnostic.",
          "Fixed 1 GHz noise model is not a receiver bandwidth/throughput validation; no physical bit rate or energy advantage."])
    OUT.mkdir(parents=True,exist_ok=True)
    for name,items in (("metrics",rows),("summary",summary),("convergence",audits),("references",refs),("traces",traces),("positions",positions),("confirmation",confirmations)):
        with (OUT/(name+".csv")).open("w",newline="") as f:
            wr=csv.DictWriter(f,fieldnames=list(items[0]));wr.writeheader();wr.writerows(items)
    (OUT/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,allow_nan=False))
    for p in sorted(OUT.iterdir()):
        if p.is_file():print(p.name,p.stat().st_size,sha(p))
    if result["failures"]:raise SystemExit("implementation checks failed")

if __name__=="__main__":main()
