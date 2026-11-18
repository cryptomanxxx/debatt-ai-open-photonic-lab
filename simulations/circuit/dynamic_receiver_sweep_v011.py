"""OPA-NL-011: causal receiver bandwidth, LO and late integration sweep.
All readouts use the same state and noise trajectory; common segment Gaussian
latents pair resolutions, not an identical Brownian path.
"""
import csv
import itertools
import json
import time
from pathlib import Path
import numpy as np
from dynamic_receiver import hybrid, psd, coefficients, rk4_wave_step, noisy_step, deterministic
from nonlinear_activation_v002 import dataset
from nonlinear_activation_v003 import rng, R, Q
from nonlinear_activation_v006 import solve, folds, response, sha, NOISE, K1
from nonlinear_activation_v009 import CASES, TAU, US, NS, COUP, LOSS

OUT=Path("results/opa-nl-011")
TIMINGS=(("C2",35,0,0),("C2",35,0,5),("C2",37.5,0,5),("C2",40,0,5),
         ("C2",45,0,5),("C2",50,0,5),("C2",40,0,0),("C2",200,0,50))
FCS=(20,30,40,60,80,120)
LOS=(.1,1.,2.,3.)
READOUTS=("end","eighth_mean","quarter_mean","half_mean")
FRACTIONS=(0.,.125,.25,.5)
DTS=(.25,.125,.0625) # regression test only; actual grid aligned per timing
def grids(on):
    n=int(np.ceil(on/(8*.25)))
    return tuple(on/(8*n*2**level) for level in range(3))

def windows(means, lengths):
    """Last 1,2,3 segments cover 1/8,1/4,1/2; use physical durations."""
    return [sum(v*l for v,l in zip(means[-k:],lengths[-k:]))/sum(lengths[-k:])
            for k in (1,2,3)]
S=8; N=512; REPEATS=8
# Receiver numerical tolerances, fixed before execution; gate changes reported
# as numerical ambiguity rather than silently upgrading a scientific result.
FIELD_TOL=1e-6 # sqrt(mW), optical endpoints
CURRENT_TOL=2e-7 # A, clean end and mean
NOISY_TOL=5e-7 # A, common-latent electrical / combined decisions
DIODE_TOL=.002 # mW, sampled peak, midpoint and boundaries

from dynamic_receiver_sweep_v010 import segment_moments, transition

def verify_segment():
    """Independent step-by-step propagation of state and accumulated mean.
    Compare time-varying deterministic input and PSD, not just constant cases.
    """
    max_current=0.;max_cov=0.
    f=np.array([.01+.02j,-.04+.005j,.03-.01j,-.02-.04j,.07+.01j])
    offs=np.array([0.,.003,-.004])
    for fc,dt,lo in itertools.product(FCS,DTS,LOS):
        field=f[:,None,None]
        off=offs[:,None,None,None]
        A,M,u,v,xx,xy,yy=segment_moments(field,fc,dt,lo,off)
        a,m,c=coefficients(fc,dt);n=len(f)
        F=np.array([[a,0.],[m/n,1.]])
        D=np.diag([1.,1/n])
        for i,o in enumerate(offs):
            current,p,_,_=hybrid(f+o,lo)
            state=np.zeros(2);cov=np.zeros((2,2))
            for ii,ss in zip(current,psd(p,lo)):
                state=F@state+np.array([(1-a)*ii,(1-m)*ii/n])
                cov=F@cov@F.T+ss*(D@c@D.T)
            got=np.array([u[i,0,0,0],v[i,0,0,0]])
            got_cov=np.array([[xx[i,0,0,0],xy[i,0,0,0]],[xy[i,0,0,0],yy[i,0,0,0]]])
            max_current=max(max_current,float(np.max(abs(got-state))))
            max_cov=max(max_cov,float(np.max(abs(got_cov-cov))/np.max(abs(cov))))
        aa,mm,cc=coefficients(fc,dt*n)
        assert abs(A-aa)<1e-12 and abs(M-mm)<1e-12
    return max_current,max_cov

def batched_wave(z,w2,case,tr,on,gap,dt):
    """Two optical histories; receiver uses stream only. All ten weights batched."""
    no=round(on/dt); ng=round(gap/dt)
    a=np.zeros((2,)+z.shape[:-1],complex); q=np.zeros(a.shape)
    for j in range(z.shape[-1]):
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
        # Sum per weight/stream across activation channels, including both histories.
        terms=np.stack((incident,energy[0],energy[1],energy[2],initial,abs(a)**2),axis=-1).sum(axis=2)
        yield np.stack(fields),np.stack(edges),endpoint,cold,balance,excess,qlo,qhi,terms

def peak_and_hybrid(field,edges,no,lo,offset):
    """Midpoint and boundary peaks; both sides of held-noise discontinuity."""
    peak=np.zeros((2,field.shape[1]))
    err=0.
    chunks=[(field[:no],offset),(edges[:no+1],offset)]
    if no<len(field):
        chunks.extend(((field[no:],np.zeros_like(offset)),(edges[no:],np.zeros_like(offset))))
    for f,off in chunks:
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
    no=round(on/dt); ng=round(gap/dt); W=len(seeds); symbols=z.shape[-1]
    assert ng==0 and no%8==0 and np.isclose(no*dt,on)
    bounds=(0,no//2,3*no//4,7*no//8,no)
    lengths=np.diff(bounds)*dt
    shape=(2,W,REPEATS,S)
    # Common independent initial and segment latents across LO, cutoff, arms,
    # timings, drive and all three resolutions; independent streams/repeats.
    init=np.stack([rng(seed,97).normal(size=(REPEATS,S)) for seed in seeds])
    draws=np.stack([rng(seed,98).normal(size=(64,4,2,REPEATS,S)) for seed in seeds],axis=3)
    # draws [symbol,segment,innovation,weight,repeat,stream]
    states={}; clean_states={}; results={}; peaks={}; grid_fields=[]
    for lo,fc in itertools.product(LOS,FCS):
        states[lo,fc]=np.broadcast_to(init*np.sqrt(psd(0.,lo)*np.pi*fc*1e9/2),shape).copy()
        clean_states[lo,fc]=np.zeros((W,S))
        results[lo,fc]=np.empty((4,3,W,REPEATS,S,symbols)) # readout, clean/electrical/combined
        peaks[lo]=np.zeros((2,W))
    endfields=np.empty((W,S,symbols),complex); coldfields=np.empty_like(endfields)
    balance=0.;excess=-np.inf; hybrid_error=0.;qlo=0.;qhi=0.
    terms_total=np.zeros((2,W,S,6))
    for j,(field,edges,end,cold,bal,exc,ql,qh,terms) in enumerate(batched_wave(z,w,case,tr,on,gap,dt)):
        endfields[...,j]=end;coldfields[...,j]=cold
        grid_fields.append(edges[::round(grids(on)[0]/dt)].copy())
        terms_total+=terms
        balance=max(balance,bal);excess=max(excess,exc);qlo=min(qlo,ql);qhi=max(qhi,qh)
        offset=np.stack((np.zeros_like(noise[...,j]),noise[...,j]))
        for lo in LOS:
            peak,err=peak_and_hybrid(field,edges,no,lo,offset)
            peaks[lo]=np.maximum(peaks[lo],peak);hybrid_error=max(hybrid_error,err)
            for fc in FCS:
                key=lo,fc; state=states[key]; clean=clean_states[key]
                means=[]; cmeans=[]
                for seg,(start,stop) in enumerate(zip(bounds[:-1],bounds[1:])):
                    state,clean,mean,cmean=transition(state,clean,field[start:stop],fc,dt,lo,offset,draws[j,seg])
                    means.append(mean); cmeans.append(cmean)
                for k,(val,cval) in enumerate(zip([state]+windows(means,lengths),[clean]+windows(cmeans,lengths))):
                    results[key][k,0,...,j]=np.broadcast_to(cval[:,None,:],(W,REPEATS,S))
                    results[key][k,1:,...,j]=val
                states[key]=state;clean_states[key]=clean
    return results,peaks,endfields,coldfields,np.stack(grid_fields),terms_total,dict(balance=balance,mvm_excess=excess,hybrid_error=hybrid_error,q_min=qlo,q_max=qhi)

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

def verify_partition():
    """Independent augmented state [end, four window sums] covariance.
    Compare split segment moments to single-step propagation at all cutoffs.
    """
    max_det=0.;max_cov=0.
    f=np.array([.01+.02j,-.04+.005j,.03-.01j,-.02-.04j,.07+.01j,.02j,-.01,.06])
    lengths=(4,2,1,1)
    for fc,lo,dt in itertools.product(FCS,LOS,DTS):
        offset=np.array([[[[.003]]]])
        current,p,_,_=hybrid(f+.003,lo)
        a,m,c=coefficients(fc,dt)
        # Four output coordinates are end, final eighth, quarter and half mean.
        def propagate(split):
            state=np.zeros(4); cov=np.zeros((4,4));start=0
            for seg,n in enumerate(split):
                stop=start+n
                # contribution of this segment to each late window
                weights=np.array([0.,n if start>=7 else 0.,n/2 if start>=6 else 0.,n/4 if start>=4 else 0.])
                if len(split)==8:
                    A,M=a,m; u=(1-a)*current[start];v=(1-m)*current[start]
                    xx,xy,yy=(psd(p[start],lo)*c)[0,0],(psd(p[start],lo)*c)[0,1],(psd(p[start],lo)*c)[1,1]
                else:
                    A,M,u,v,xx,xy,yy=segment_moments(f[start:stop,None,None],fc,dt,lo,offset)
                    u,v,xx,xy,yy=(float(x.item()) for x in (u,v,xx,xy,yy))
                F=np.eye(4);F[:,0]=weights*M;F[0,0]=A
                D=np.stack((np.array([1.,0.,0.,0.]),weights),axis=1)
                state=F@state+D@np.array([u,v])
                cov=F@cov@F.T+D@np.array([[xx,xy],[xy,yy]])@D.T
                start=stop
            return state,cov
        x,cx=propagate(lengths);y,cy=propagate((1,)*8)
        max_det=max(max_det,float(np.max(abs(x-y))))
        max_cov=max(max_cov,float(np.max(abs(cx-cy))/np.max(abs(cy))))
        # NL010 anchor: half-mean and end after two four-step transitions.
        A,M,u,v,xx,xy,yy=segment_moments(f[4:,None,None],fc,dt,lo,offset)
        A0,M0,u0,v0,*_=segment_moments(f[:4,None,None],fc,dt,lo,offset)
        max_det=max(max_det,abs(x[0]-float((A*u0+u).item())),abs(x[3]-float((M*u0+v).item())))
        assert np.allclose(windows([1.,2.,3.,4.],np.array(lengths)),[4.,3.5,2.75])
    return max_det,max_cov

def verify_stationary():
    # Independent synthetic long sequence; fixed tolerances, burn-in unnecessary
    # because initial state has the exact stationary distribution.
    fc,dt,lo=40.,5.,3.
    a,m,c=coefficients(fc,dt); spectrum=float(psd(0.,lo))
    stationary=spectrum*np.pi*fc*1e9/2
    rg=np.random.default_rng(110110)
    n=8192; streams=64
    state=rg.normal(size=streams)*np.sqrt(stationary)
    end=[];means=[];old=[]
    factor=np.linalg.cholesky(c)
    for _ in range(n):
        old.append(state)
        state,mean=noisy_step(state,0.,spectrum,a,m,factor,*rg.normal(size=(2,streams)))
        end.append(state);means.append(mean)
    e=np.asarray(end);o=np.asarray(old);j=np.asarray(means)
    var_ratio=float(np.var(e)/stationary)
    lag=float(np.mean(e*o)/stationary)
    mean_ratio=float(np.var(j)/(m*m*stationary+spectrum*c[1,1]))
    # Constant and step analytic checks at higher cutoff/LO.
    aa,mm,_=coefficients(120.,40.)
    v,j0=deterministic(0.,1.,aa,mm)
    assert abs(v-(1-aa))<1e-14 and abs(j0-(1-mm))<1e-14
    assert abs(var_ratio-1)<.02 and abs(lag-a)<.02 and abs(mean_ratio-1)<.02
    return dict(variance_ratio=var_ratio,lag=lag,expected_lag=float(a),mean_variance_ratio=mean_ratio)

def group_analysis(groups,keys):
    bykey={tuple(g[k] for k in keys):g for g in groups}
    pairs=[]
    for g in groups:
        if g["drive_mw"]!=.1:continue
        h=bykey[tuple(g[k] for k in keys[:-1])+(1.,)]
        pairs.append(dict(**{k:g[k] for k in keys[:-1]},cadence_gsymbol_s=g["cadence_gsymbol_s"],
            combined_worst_low=g["combined_worst"],combined_worst_high=h["combined_worst"],
            maximin=min(g["combined_worst"],h["combined_worst"]),
            confirmed_both=g["confirmed_combined_pass"] and h["confirmed_combined_pass"]))
    best=[]
    for name,on,gap,tr in TIMINGS:
        a=[p for p in pairs if (p["candidate"],p["on_ps"],p["gap_ps"],p["response_ps"])==(name,on,gap,tr)]
        score=max(p["maximin"] for p in a)
        best.extend(p for p in a if p["maximin"]==score)
    return pairs,best

def main():
    start=time.monotonic(); OUT.mkdir(parents=True,exist_ok=True)
    prior={}
    for exp in ("opa-nl-010","opa-nl-009","opa-nl-003"):
        root=Path("results")/exp
        manifest=json.loads((root/"provenance.json").read_text())["files"]
        for name,v in manifest.items():
            if exp=="opa-nl-003" and name!="weights.json":continue
            p=root/name;prior[p]=sha(p)
            if prior[p]!=v["sha256"]:raise ValueError("archive mismatch")
    weights=[r for r in json.loads(Path("results/opa-nl-003/weights.json").read_text()) if r["kind"]=="absorber"]
    seeds=[];drives=[];z=[];w=[];y=[];noise=[];launch=[];inputs=[]
    for r in weights:
        seed,drive=r["seed"],r["drive_mw"];w1=np.array(r["w1"]);w2=np.array(r["w2"])
        x,labels=dataset(seed,94,N);order=rng(seed,95).permutation(N)
        x=x[:,order];labels=labels[order]
        inputs.append(x.copy());launch.append(float(drive*np.mean(np.sum(x*x,axis=0))))
        z.append((np.sqrt(drive)*(w1@x)).reshape(8,S,64));w.append(w2.ravel())
        y.append(labels.reshape(S,64));seeds.append(seed);drives.append(drive)
        noise.append((NOISE*np.einsum("c,rcn->rn",w2.ravel(),rng(seed,96).normal(size=(REPEATS,8,N)))).reshape(REPEATS,S,64))
    z,w,y,noise=map(np.asarray,(z,w,y,noise))
    checks=dict(weights=len(weights)==10 and len(set(zip(seeds,drives)))==10,
        balanced=bool(np.all(y.sum(axis=(1,2))==256)),power_domain=bool(np.max(abs(z)**2)<=4),
        paired_inputs=all((np.array_equal(y[i],y[j]) and np.array_equal(inputs[i],inputs[j])) for i in range(10) for j in range(10) if seeds[i]==seeds[j]))
    if not all(checks.values()):raise ValueError("dataset preflight")
    err_current,err_cov=verify_segment()
    checks['segment_regression']=err_current<1e-15 and err_cov<1e-9
    partition_det,partition_cov=verify_partition()
    noise_regression=verify_stationary()
    checks['stationary_noise_regression']=True
    checks['partition_regression']=partition_det<1e-15 and partition_cov<1e-9
    if not checks['segment_regression'] or not checks['partition_regression']:raise ValueError('segment regression')
    # Full ten-weight 200 ps slot at the finest resolution as runtime calibration.
    pilot_start=time.monotonic()
    run_case(z[...,:1],w,y[...,:1],noise[...,:1],seeds,CASES['C2'],200,0,50,grids(200)[-1])
    pilot_seconds=time.monotonic()-pilot_start
    step_budget=sum(64*round((on+gap)/dt) for _,on,gap,_ in TIMINGS for dt in grids(on))
    print('Pilot seconds',pilot_seconds,'step budget',step_budget,'linear estimated seconds',pilot_seconds*step_budget/3200,flush=True)
    rows=[];audits=[];conv=[];resolution_groups=[];resolution_rows=[]
    for name,on,gap,tr in TIMINGS:
        case=CASES[name];stable=eligible(z,case);prev=None
        for level,dt in enumerate(grids(on)):
            res,peak,end,cold,grid,terms,diag=run_case(z,w,y,noise,seeds,case,on,gap,tr,dt)
            meta=dict(candidate=name,on_ps=on,gap_ps=gap,response_ps=tr,dt_ps=dt,resolution_level=level,cadence_gsymbol_s=1000/(on+gap))
            audits.append(dict(**meta,**diag,first_symbol_error=float(np.max(abs(end[...,0]-cold[...,0])))))
            local=[]
            for (lo,fc),values in res.items():
                for k,readout in enumerate(READOUTS):
                    for i,(seed,drive) in enumerate(zip(seeds,drives)):
                        rr=dict(**meta,lo_mw=lo,fc_ghz=fc,enbw_ghz=np.pi*fc/2,readout=readout,
                            integration_ps=on*FRACTIONS[k],seed=seed,drive_mw=drive,stationary_eligible=stable,
                            unfiltered_accuracy=float(np.mean((end[i].real>0)==y[i])),
                            cold_unfiltered_accuracy=float(np.mean((cold[i].real>0)==y[i])),
                            max_optical_memory_field=float(np.max(abs(end[i]-cold[i]))),
                            electrical_peak_diode_mw=float(peak[lo][0,i]),combined_peak_diode_mw=float(peak[lo][1,i]),
                            launch_mw=launch[i],lo_electric_lower_mw=lo/.20,
                            signal_electric_lower_mw=launch[i]/.20,
                            signal_plus_lo_electric_lower_mw=(launch[i]+lo)/.20,
                            **{name+"_fj":float(terms[1,i,:,j].sum()) for j,name in enumerate(("input","reflection","drop","absorption","initial","final"))},
                            **row_metrics(values[k,:,i],y[i]))
                        rr.update(electrical_pass=pass_gate(rr,"electrical"),combined_pass=pass_gate(rr,"combined"))
                        local.append(rr)
            flags={}
            for lo,fc,readout,drive in itertools.product(LOS,FCS,READOUTS,(.1,1.)):
                g=[v for v in local if (v["lo_mw"],v["fc_ghz"],v["readout"],v["drive_mw"])==(lo,fc,readout,drive)]
                assert len(g)==5
                group=dict(**meta,lo_mw=lo,fc_ghz=fc,readout=readout,drive_mw=drive,seeds=5,
                    stationary_eligible=all(v["stationary_eligible"] for v in g),
                    unfiltered_min=min(v["unfiltered_accuracy"] for v in g),
                    clean_min=min(v["clean_filtered_accuracy"] for v in g),
                    combined_peak_diode_mw=max(v["combined_peak_diode_mw"] for v in g),
                    electrical_worst=min(v["electrical_worst"] for v in g),
                    combined_worst=min(v["combined_worst"] for v in g),
                    electrical_pass=all(v["electrical_pass"] for v in g),
                    combined_pass=all(v["combined_pass"] for v in g))
                resolution_groups.append(group);flags[lo,fc,readout,drive]=(group["electrical_pass"],group["combined_pass"])
            if prev is not None:
                old,op,oe,of,og,oldflags,oldrows=prev
                conv.append(dict(**meta,coarse_dt_ps=dt*2,
                    field_error=float(max(np.max(abs(end-oe)),np.max(abs(cold-of)))),
                    waveform_grid_error=float(np.max(abs(grid-og))),
                    clean_current_error=float(max(np.max(abs(res[k][:,0]-old[k][:,0])) for k in res)),
                    noisy_current_error=float(max(np.max(abs(res[k][:,1:]-old[k][:,1:])) for k in res)),
                    peak_error_mw=float(max(np.max(abs(peak[k]-op[k])) for k in peak)),
                    changed_group_gates=sum(flags[k]!=oldflags[k] for k in flags),
                    changed_seed_gates=sum((a["electrical_pass"],a["combined_pass"])!=(b["electrical_pass"],b["combined_pass"]) for a,b in zip(local,oldrows))))
            prev=(res,peak,end,cold,grid,flags,local)
            resolution_rows.extend(local)
            if level==2:rows.extend(local)
            print(name,on,gap,tr,dt,"elapsed",round(time.monotonic()-start,1),flush=True)
    groups=[dict(r) for r in resolution_groups if r["resolution_level"]==2]
    # Flag any final-resolution gate disagreement explicitly, not a physics failure.
    middle={(r["candidate"],r["on_ps"],r["gap_ps"],r["response_ps"],r["lo_mw"],r["fc_ghz"],r["readout"],r["drive_mw"]):r for r in resolution_groups if r["resolution_level"]==1}
    keys=("candidate","on_ps","gap_ps","response_ps","lo_mw","fc_ghz","readout","drive_mw")
    for g in groups:
        p=middle[tuple(g[k] for k in keys)]
        g["numerically_stable_gate"]=bool(g["combined_pass"]==p["combined_pass"] and g["electrical_pass"]==p["electrical_pass"])
        g["confirmed_combined_pass"]=g["combined_pass"] and g["numerically_stable_gate"]
    common=[g for g in groups if g["drive_mw"]==.1 and g["confirmed_combined_pass"] and any(
        h["drive_mw"]==1 and h["confirmed_combined_pass"] and all(g[k]==h[k] for k in keys[:-1]) for h in groups)]
    common.sort(key=lambda g:-g['cadence_gsymbol_s'])
    pairs,best=group_analysis(groups,keys)
    fastest=[g for g in common if g['cadence_gsymbol_s']==common[0]['cadence_gsymbol_s']] if common else []
    for g in groups:
        reasons=[]
        if not g["stationary_eligible"]:reasons.append("stationary")
        if g["unfiltered_min"]<.95:reasons.append("unfiltered")
        if g["clean_min"]<.95:reasons.append("clean_filtered")
        if g["combined_worst"]<.95:reasons.append("combined_noise")
        if g["combined_peak_diode_mw"]>2:reasons.append("diode")
        if not g["numerically_stable_gate"]:reasons.append("resolution")
        g["failure_reasons"]=";".join(reasons)
    checks.update(counts=len(rows)==7680 and len(groups)==1536 and len(audits)==24 and len(conv)==16 and len(resolution_groups)==4608 and len(resolution_rows)==23040 and len(pairs)==768,
        unique_keys=len({tuple(r[k] for k in keys)+ (r["seed"],) for r in rows})==7680 and len({tuple(r[k] for k in keys)+(r["seed"],r["resolution_level"]) for r in resolution_rows})==23040,
        optical_balance=all(r["balance"]<1e-6 and r["mvm_excess"]<1e-9 and r["q_min"]>=-1e-10 and r["q_max"]<=1+1e-10 for r in audits),
        hybrid=all(r["hybrid_error"]<1e-15 for r in audits),
        aggregate_energy_balance=all(abs(r["input_fj"]+r["initial_fj"]-r["reflection_fj"]-r["drop_fj"]-r["absorption_fj"]-r["final_fj"])/(1+r["input_fj"]+r["initial_fj"])<1e-6 for r in resolution_rows),
        unique_group_keys=len({tuple(r[k] for k in keys)+(r["resolution_level"],) for r in resolution_groups})==4608,
        first_symbol=all(r["first_symbol_error"]<1e-12 for r in audits),
        convergence=all(r["field_error"]<FIELD_TOL and r["clean_current_error"]<CURRENT_TOL
            and r["waveform_grid_error"]<FIELD_TOL and r["noisy_current_error"]<NOISY_TOL and r["peak_error_mw"]<DIODE_TOL for r in conv),
        finite=all(np.isfinite(v) for r in rows+audits+conv for v in r.values() if isinstance(v,(int,float))),
        archive_immutable=all(sha(p)==v for p,v in prior.items()))
    checks={k:bool(v) for k,v in checks.items()}
    result=dict(experiment="OPA-NL-011",checks=checks,failures=[k for k,v in checks.items() if not v],
        rows=len(rows),groups=len(groups),rng_domains=[94,95,96,97,98],resolution_groups=len(resolution_groups),
        fastest_common_confirmed_passes=fastest,stationary_noise_regression=noise_regression,
        best_maximin_by_timing=best,partition_current_error=partition_det,partition_covariance_error=partition_cov,
        common_confirmed_passes=common,combined_confirmed_groups=sum(g["confirmed_combined_pass"] for g in groups),
        ambiguous_groups=sum(not g["numerically_stable_gate"] for g in groups),
        tolerances=dict(field=FIELD_TOL,current=CURRENT_TOL,noisy=NOISY_TOL,diode_mw=DIODE_TOL),
        convergence=conv,segment_regression_current_error=err_current,segment_regression_covariance_error=err_cov,
        pilot_seconds=pilot_seconds,step_budget=step_budget,elapsed_seconds=time.monotonic()-start,
        limitations=["Piecewise midpoint current and PSD; exact segment-level covariance and common Gaussian latents, not Brownian path coupling.",
          "All eight timings evaluated at aligned dt <= .0625 ps; groups with gate disagreement excluded from confirmed passes.",
          "Hypothetical electrical PSD and symbol-held optical field noise; no measured receiver, BER, hardware throughput or wall-plug claim."])
    for name,items in (("metrics.csv",rows),("summary.csv",groups),("resolution_groups.csv",resolution_groups),("resolution_metrics.csv",resolution_rows),("convergence.csv",conv),("optical_audit.csv",audits),("common_drive_pairs.csv",pairs)):
        write_csv(name,items)
    (OUT/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,allow_nan=False))
    for p in sorted(OUT.iterdir()):
        if p.is_file():print(p.name,p.stat().st_size,sha(p))
    if result["failures"]:raise SystemExit("implementation checks failed")
if __name__=="__main__":main()
