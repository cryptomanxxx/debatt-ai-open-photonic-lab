"""OPA-NL-010: continuous TCMT and dynamic balanced receiver.

All seven timings at all three resolutions; exact joint segment covariance
for piecewise-constant midpoint PSD. Common segment-level Gaussian latents
pair resolutions (distributional coupling, not a common Brownian path).
"""
import csv
import itertools
import json
import time
from pathlib import Path
import numpy as np
from dynamic_receiver import hybrid, psd, coefficients, rk4_wave_step
from nonlinear_activation_v002 import dataset
from nonlinear_activation_v003 import rng, R
from nonlinear_activation_v006 import solve, folds, response, sha, NOISE, K1
from nonlinear_activation_v009 import CASES, TAU, US, NS, COUP, LOSS

OUT=Path("results/opa-nl-010")
TIMINGS=(("C2",35,0,0),("C2",40,0,5),("C2",50,0,5),("C2",200,0,50),
         ("C1",30,20,0),("C1",35,20,5),("C2",30,0,0))
FCS=(1,5,10,20,40,80)
LOS=(.1,1.)
READOUTS=("end","half_mean")
DTS=(.25,.125,.0625)
S=8; N=512; REPEATS=8
# Receiver numerical tolerances, fixed before execution; gate changes reported
# as numerical ambiguity rather than silently upgrading a scientific result.
FIELD_TOL=1e-6 # sqrt(mW), optical endpoints
CURRENT_TOL=2e-7 # A, clean end and mean
NOISY_TOL=5e-7 # A, common-latent electrical / combined decisions
DIODE_TOL=.002 # mW, sampled peak, midpoint and boundaries

def kernels(fc,dt,n):
    """Segment endpoint and average weights, incl. exact joint OU covariance."""
    a,m,c=coefficients(fc,dt)
    decay=np.exp(-2*np.pi*fc*1e9*dt*1e-12*np.arange(n-1,-1,-1))
    # step noise affects subsequent step means via preceding state.
    beta=m*(-np.expm1(-2*np.pi*fc*1e9*dt*1e-12*np.arange(n-1,-1,-1)))/((1-a)*n)
    A=np.exp(-2*np.pi*fc*1e9*dt*1e-12*n)
    M=m*(-np.expm1(-2*np.pi*fc*1e9*dt*1e-12*n))/((1-a)*n)
    weights=np.stack(((1-a)*decay,(1-m*decay)/n,
        c[0,0]*decay**2,
        decay*(beta*c[0,0]+c[0,1]/n),
        beta**2*c[0,0]+2*beta*c[0,1]/n+c[1,1]/n**2))
    return A,M,weights

def segment_moments(field,fc,dt,lo,offset):
    """field [step,weight,stream], offset [weight,repeat,stream].
    Return deterministic current moments and joint noise covariance for both
    electrical-only (offset=0) and combined arms. Avoid allocating time x repeats.
    """
    n=len(field); A,M,w=kernels(fc,dt,n)
    shape=field.shape[1:]
    # Real offset prior to loss and phase; optical power uses unrotated field.
    flat=field.reshape(n,-1)
    mat=np.stack((flat.real,flat.imag,abs(flat)**2),axis=0)
    v=np.einsum("kn,cnj->kcj",w,mat,optimize=True).reshape(5,3,*shape)
    sums=w.sum(axis=1)
    eta=10**(-3/10)*1e-3
    ph=np.deg2rad(15.)
    gain=2*R*np.sqrt(lo*1e-3*eta)
    o=offset
    # arms x weights x repeats x streams
    def current(k):
        return gain*((v[k,0,:,None,:]*np.cos(ph)-v[k,1,:,None,:]*np.sin(ph))[None,...]
                     +o*np.cos(ph)*sums[k])
    def covariance(k):
        power=eta*(v[k,2,:,None,:][None,...]+2*o*v[k,0,:,None,:][None,...]+o*o*sums[k])
        # PSD affine in optical power. Weighted integration, not PSD at average field.
        from nonlinear_activation_v003 import Q
        return psd(0.,lo)*sums[k]+2*Q*R*power
    return A,M,current(0),current(1),covariance(2),covariance(3),covariance(4)

def transition(state,clean_state,field,fc,dt,lo,offset,g):
    A,M,u,v,xx,xy,yy=segment_moments(field,fc,dt,lo,offset)
    # Clean arm uses the zero-offset deterministic moments.
    clean_end=A*clean_state+u[0,:,0,:]
    clean_mean=M*clean_state+v[0,:,0,:]
    l0=np.sqrt(xx); l1=xy/l0
    var=yy-l1*l1
    if np.any(var<=0) or not np.all(np.isfinite(var)):
        raise ValueError("invalid joint segment covariance")
    end=A*state+u+l0*g[0][None,...]
    mean=M*state+v+l1*g[0][None,...]+np.sqrt(var)*g[1][None,...]
    return end,clean_end,mean,clean_mean

def batched_wave(z,w2,case,tr,on,gap,dt):
    """Two optical histories; receiver uses stream only. All ten weights batched."""
    no=round(on/dt); ng=round(gap/dt)
    a=np.zeros((2,)+z.shape[:-1],complex); q=np.zeros(a.shape)
    for j in range(64):
        a[0]=0;q[0]=0
        initial=abs(a)**2; energy=np.zeros((3,)+a.shape)
        s=np.broadcast_to(z[...,j],a.shape)
        fields=[]; edges=[]; excess=-np.inf; qlo=0.;qhi=0.
        project=lambda f: np.einsum("wc,wcs->ws",w2,f)
        edges.append(project(COUP*a[1]*np.sqrt(LOSS)))
        for k in range(no+ng):
            inc=s if k<no else np.zeros_like(s)
            a,q,mid,en=rk4_wave_step(a,q,inc,*case,tr,dt)
            energy+=en
            f=project(mid[1]); fields.append(f)
            edges.append(project(COUP*a[1]*np.sqrt(LOSS)))
            excess=max(excess,float(np.max(abs(f)**2-np.sum(abs(mid[1])**2,axis=1))))
            qlo=min(qlo,float(q.min()));qhi=max(qhi,float(q.max()))
            if k==no-1:
                endpoint=edges[-1]
                cold=project(COUP*a[0]*np.sqrt(LOSS))
        incident=abs(s)**2*on
        balance=float(np.max(abs(incident+initial-energy.sum(axis=0)-abs(a)**2)/(1+incident+initial)))
        yield np.stack(fields),np.stack(edges),endpoint,cold,balance,excess,qlo,qhi

def peak_and_hybrid(field,edges,no,lo,offset):
    """Midpoint and boundary peaks; both sides of held-noise discontinuity."""
    peak=np.zeros((2,field.shape[1]))
    err=0.
    for f,off in ((field[:no],offset),(edges[:no+1],offset),
                  (field[no:],np.zeros_like(offset)),(edges[no:],np.zeros_like(offset))):
        if not len(f):continue
        # chunk to bound memory during 200 ps controls
        for chunk in np.array_split(f,max(1,int(np.ceil(len(f)/256)))):
            e=chunk[:,None,:,None,:]+off[None,...]
            _,p,pp,pm=hybrid(e,lo)
            err=max(err,float(np.max(abs(pp+pm-p-lo*1e-3))))
            peak=np.maximum(peak,np.maximum(pp,pm).max(axis=(0,3,4))*1e3)
    return peak,err

def eligible(z,case):
    b,d,h=case
    p=np.r_[0.,np.geomspace(1e-8,4.,512),abs(z).ravel()**2]
    _,_,n,st,eig,_,_=solve(p,TAU,US,NS,0.,b,d,h)
    fp=[response(x,NS,0.,b,d,h)[0]*US/(K1*TAU) for x in folds(NS,0.,b,d,h)]
    return bool(not any(0<=v<=4 for v in fp) and np.all(n==1) and np.all(st==1) and np.all(eig<0))

def run_case(z,w,y,noise,seeds,case,on,gap,tr,dt):
    no=round(on/dt); ng=round(gap/dt); W=len(seeds)
    shape=(2,W,REPEATS,S)
    # Common independent initial and segment latents across LO, cutoff, arms,
    # timings, drive and all three resolutions; independent streams/repeats.
    init=np.stack([rng(seed,87).normal(size=(REPEATS,S)) for seed in seeds])
    draws=np.stack([rng(seed,88).normal(size=(64,3,2,REPEATS,S)) for seed in seeds],axis=3)
    # draws [symbol,segment,innovation,weight,repeat,stream]
    states={}; clean_states={}; results={}; peaks={}
    for lo,fc in itertools.product(LOS,FCS):
        states[lo,fc]=np.broadcast_to(init*np.sqrt(psd(0.,lo)*np.pi*fc*1e9/2),shape).copy()
        clean_states[lo,fc]=np.zeros((W,S))
        results[lo,fc]=np.empty((2,3,W,REPEATS,S,64)) # readout, clean/electrical/combined
        peaks[lo]=np.zeros((2,W))
    endfields=np.empty((W,S,64),complex); coldfields=np.empty_like(endfields)
    balance=0.;excess=-np.inf; hybrid_error=0.;qlo=0.;qhi=0.
    for j,(field,edges,end,cold,bal,exc,ql,qh) in enumerate(batched_wave(z,w,case,tr,on,gap,dt)):
        endfields[...,j]=end;coldfields[...,j]=cold
        balance=max(balance,bal);excess=max(excess,exc);qlo=min(qlo,ql);qhi=max(qhi,qh)
        offset=np.stack((np.zeros_like(noise[...,j]),noise[...,j]))
        for lo in LOS:
            peak,err=peak_and_hybrid(field,edges,no,lo,offset)
            peaks[lo]=np.maximum(peaks[lo],peak);hybrid_error=max(hybrid_error,err)
            for fc in FCS:
                key=lo,fc; state=states[key]; clean=clean_states[key]
                for seg,(start,stop) in enumerate(((0,no//2),(no//2,no),(no,no+ng))):
                    if start==stop:continue
                    off=offset if seg<2 else np.zeros_like(offset)
                    state,clean,mean,cmean=transition(state,clean,field[start:stop],fc,dt,lo,off,draws[j,seg])
                    if seg==1:
                        for k,(val,cval) in enumerate(((state,clean),(mean,cmean))):
                            results[key][k,0,...,j]=np.broadcast_to(cval[:,None,:],(W,REPEATS,S))
                            results[key][k,1:,...,j]=val
                states[key]=state;clean_states[key]=clean
    return results,peaks,endfields,coldfields,dict(balance=balance,mvm_excess=excess,hybrid_error=hybrid_error,q_min=qlo,q_max=qhi)

def row_metrics(values,y):
    # values [arm,repeat,stream,symbol], y [stream,symbol]
    correct=(values>0)==y[None,None,...]
    rep=correct.mean(axis=(-2,-1))
    clean=values[0,0]; electrical=values[1]-clean
    # Electrical-only residual, independent of deterministic signal.
    lag0=electrical[...,:-1].ravel();lag1=electrical[...,1:].ravel()
    return dict(clean_filtered_accuracy=float(rep[0,0]),electrical_accuracy=float(rep[1].mean()),
        electrical_worst=float(rep[1].min()),combined_accuracy=float(rep[2].mean()),combined_worst=float(rep[2].min()),
        min_clean_signed_current_a=float(np.min((2*y-1)*clean)),
        min_combined_signed_current_a=float(np.min((2*y-1)[None,...]*values[2])),
        electrical_noise_variance_a2=float(np.var(electrical)),
        electrical_lag1=float(np.corrcoef(lag0,lag1)[0,1]),
        first8_combined_accuracy=float(correct[2,...,:8].mean()),
        last8_combined_accuracy=float(correct[2,...,-8:].mean()))

def pass_gate(r,arm):
    return bool(r["stationary_eligible"] and r["unfiltered_accuracy"]>=.95
        and r["clean_filtered_accuracy"]>=.95 and r[arm+"_worst"]>=.95
        and r[arm+"_peak_diode_mw"]<=2.)

def write_csv(name,rows):
    with (OUT/name).open("w",newline="") as f:
        wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)

def main():
    start=time.monotonic(); OUT.mkdir(parents=True,exist_ok=True)
    prior={}
    for exp in ("opa-nl-009","opa-nl-003"):
        root=Path("results")/exp
        manifest=json.loads((root/"provenance.json").read_text())["files"]
        for name,v in manifest.items():
            if exp=="opa-nl-003" and name!="weights.json":continue
            p=root/name;prior[p]=sha(p)
            if prior[p]!=v["sha256"]:raise ValueError("archive mismatch")
    weights=[r for r in json.loads(Path("results/opa-nl-003/weights.json").read_text()) if r["kind"]=="absorber"]
    seeds=[];drives=[];z=[];w=[];y=[];noise=[]
    for r in weights:
        seed,drive=r["seed"],r["drive_mw"];w1=np.array(r["w1"]);w2=np.array(r["w2"])
        x,labels=dataset(seed,84,N);order=rng(seed,85).permutation(N)
        x=x[:,order];labels=labels[order]
        z.append((np.sqrt(drive)*(w1@x)).reshape(8,S,64));w.append(w2.ravel())
        y.append(labels.reshape(S,64));seeds.append(seed);drives.append(drive)
        noise.append((NOISE*np.einsum("c,rcn->rn",w2.ravel(),rng(seed,86).normal(size=(REPEATS,8,N)))).reshape(REPEATS,S,64))
    z,w,y,noise=map(np.asarray,(z,w,y,noise))
    checks=dict(weights=len(weights)==10 and len(set(zip(seeds,drives)))==10,
        balanced=bool(np.all(y.sum(axis=(1,2))==256)),power_domain=bool(np.max(abs(z)**2)<=4),
        paired_inputs=all(np.array_equal(y[i],y[j]) for i in range(10) for j in range(10) if seeds[i]==seeds[j]))
    if not all(checks.values()):raise ValueError("dataset preflight")
    rows=[];audits=[];conv=[];resolution_groups=[]; all_results={}
    for name,on,gap,tr in TIMINGS:
        case=CASES[name];stable=eligible(z,case);prev=None
        for dt in DTS:
            res,peak,end,cold,diag=run_case(z,w,y,noise,seeds,case,on,gap,tr,dt)
            meta=dict(candidate=name,on_ps=on,gap_ps=gap,response_ps=tr,dt_ps=dt,cadence_gsymbol_s=1000/(on+gap))
            audits.append(dict(**meta,**diag,first_symbol_error=float(np.max(abs(end[...,0]-cold[...,0])))))
            local=[]
            for (lo,fc),values in res.items():
                for k,readout in enumerate(READOUTS):
                    for i,(seed,drive) in enumerate(zip(seeds,drives)):
                        rr=dict(**meta,lo_mw=lo,fc_ghz=fc,enbw_ghz=np.pi*fc/2,readout=readout,
                            integration_ps=on/2 if k else 0.,seed=seed,drive_mw=drive,stationary_eligible=stable,
                            unfiltered_accuracy=float(np.mean((end[i].real>0)==y[i])),
                            cold_unfiltered_accuracy=float(np.mean((cold[i].real>0)==y[i])),
                            max_optical_memory_field=float(np.max(abs(end[i]-cold[i]))),
                            electrical_peak_diode_mw=float(peak[lo][0,i]),combined_peak_diode_mw=float(peak[lo][1,i]),
                            **row_metrics(values[k,:,i],y[i]))
                        rr.update(electrical_pass=pass_gate(rr,"electrical"),combined_pass=pass_gate(rr,"combined"))
                        local.append(rr)
            flags={}
            for lo,fc,readout,drive in itertools.product(LOS,FCS,READOUTS,(.1,1.)):
                g=[v for v in local if (v["lo_mw"],v["fc_ghz"],v["readout"],v["drive_mw"])==(lo,fc,readout,drive)]
                assert len(g)==5
                group=dict(**meta,lo_mw=lo,fc_ghz=fc,readout=readout,drive_mw=drive,seeds=5,
                    clean_min=min(v["clean_filtered_accuracy"] for v in g),
                    electrical_worst=min(v["electrical_worst"] for v in g),
                    combined_worst=min(v["combined_worst"] for v in g),
                    electrical_pass=all(v["electrical_pass"] for v in g),
                    combined_pass=all(v["combined_pass"] for v in g))
                resolution_groups.append(group);flags[lo,fc,readout,drive]=(group["electrical_pass"],group["combined_pass"])
            if prev is not None:
                old,op,oe,of,oldflags,oldrows=prev
                conv.append(dict(**meta,coarse_dt_ps=dt*2,
                    field_error=float(max(np.max(abs(end-oe)),np.max(abs(cold-of)))),
                    clean_current_error=float(max(np.max(abs(res[k][:,0]-old[k][:,0])) for k in res)),
                    noisy_current_error=float(max(np.max(abs(res[k][:,1:]-old[k][:,1:])) for k in res)),
                    peak_error_mw=float(max(np.max(abs(peak[k]-op[k])) for k in peak)),
                    changed_group_gates=sum(flags[k]!=oldflags[k] for k in flags),
                    changed_seed_gates=sum((a["electrical_pass"],a["combined_pass"])!=(b["electrical_pass"],b["combined_pass"]) for a,b in zip(local,oldrows))))
            prev=(res,peak,end,cold,flags,local)
            if dt==DTS[-1]:rows.extend(local)
            print(name,on,gap,tr,dt,"elapsed",round(time.monotonic()-start,1),flush=True)
    groups=[dict(r) for r in resolution_groups if r["dt_ps"]==DTS[-1]]
    # Flag any final-resolution gate disagreement explicitly, not a physics failure.
    middle={(r["candidate"],r["on_ps"],r["gap_ps"],r["response_ps"],r["lo_mw"],r["fc_ghz"],r["readout"],r["drive_mw"]):r for r in resolution_groups if r["dt_ps"]==DTS[1]}
    keys=("candidate","on_ps","gap_ps","response_ps","lo_mw","fc_ghz","readout","drive_mw")
    for g in groups:
        p=middle[tuple(g[k] for k in keys)]
        g["numerically_stable_gate"]=bool(g["combined_pass"]==p["combined_pass"] and g["electrical_pass"]==p["electrical_pass"])
        g["confirmed_combined_pass"]=g["combined_pass"] and g["numerically_stable_gate"]
    common=[g for g in groups if g["drive_mw"]==.1 and g["confirmed_combined_pass"] and any(
        h["drive_mw"]==1 and h["confirmed_combined_pass"] and all(g[k]==h[k] for k in keys[:-1]) for h in groups)]
    checks.update(counts=len(rows)==1680 and len(groups)==336 and len(audits)==21 and len(conv)==14 and len(resolution_groups)==1008,
        unique_keys=len({tuple(r[k] for k in keys)+ (r["seed"],) for r in rows})==1680,
        optical_balance=all(r["balance"]<1e-6 and r["mvm_excess"]<1e-9 and r["q_min"]>=-1e-10 and r["q_max"]<=1+1e-10 for r in audits),
        hybrid=all(r["hybrid_error"]<1e-15 for r in audits),
        first_symbol=all(r["first_symbol_error"]<1e-12 for r in audits),
        convergence=all(r["field_error"]<FIELD_TOL and r["clean_current_error"]<CURRENT_TOL
            and r["noisy_current_error"]<NOISY_TOL and r["peak_error_mw"]<DIODE_TOL for r in conv),
        finite=all(np.isfinite(v) for r in rows+audits+conv for v in r.values() if isinstance(v,(int,float))),
        archive_immutable=all(sha(p)==v for p,v in prior.items()))
    checks={k:bool(v) for k,v in checks.items()}
    result=dict(experiment="OPA-NL-010",checks=checks,failures=[k for k,v in checks.items() if not v],
        rows=len(rows),groups=len(groups),rng_domains=[84,85,86,87,88],resolution_groups=len(resolution_groups),
        common_confirmed_passes=common,combined_confirmed_groups=sum(g["confirmed_combined_pass"] for g in groups),
        ambiguous_groups=sum(not g["numerically_stable_gate"] for g in groups),
        tolerances=dict(field=FIELD_TOL,current=CURRENT_TOL,noisy=NOISY_TOL,diode_mw=DIODE_TOL),
        convergence=conv,elapsed_seconds=time.monotonic()-start,
        limitations=["Piecewise midpoint current and PSD; exact segment-level covariance and common Gaussian latents, not Brownian path coupling.",
          "All seven timings confirmed at .0625 ps; groups with gate disagreement excluded from confirmed passes.",
          "Hypothetical electrical PSD and symbol-held optical field noise; no measured receiver, BER, hardware throughput or wall-plug claim."])
    for name,items in (("metrics.csv",rows),("summary.csv",groups),("resolution_groups.csv",resolution_groups),("convergence.csv",conv),("optical_audit.csv",audits)):
        write_csv(name,items)
    (OUT/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,allow_nan=False))
    for p in sorted(OUT.iterdir()):
        if p.is_file():print(p.name,p.stat().st_size,sha(p))
    if result["failures"]:raise SystemExit("implementation checks failed")
if __name__=="__main__":main()
