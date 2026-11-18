"""OPA-NL-012: fixed causal equalization, independent calibration and tests."""
import hashlib
import subprocess
import sys
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

OUT=Path("results/opa-nl-012")
TIMINGS=(("C2",40,0,5),("C2",45,0,5),("C2",50,0,5),("C2",40,0,0))
FCS=(20,30,40,60,80,120)
LOS=(1.,2.,3.)
READOUTS=("end","eighth_mean","quarter_mean","half_mean","ridge8","ridge16","ridge16_strong")
FRACTIONS=(0.,.125,.25,.5,1.,1.,1.)
CAL_DOMAINS=(10004,10005,10006,10007,10008)
TEST_DOMAINS=(10014,10015,10016,10017,10018)
S=8; REPEATS=8
from dynamic_receiver_sweep_v011 import (grids, batched_wave, peak_and_hybrid, eligible,
    row_metrics, pass_gate, verify_segment, verify_partition, verify_stationary)
# Receiver numerical tolerances, fixed before execution; gate changes reported
# as numerical ambiguity rather than silently upgrading a scientific result.
FIELD_TOL=1e-6 # sqrt(mW), optical endpoints
CURRENT_TOL=2e-7 # A, clean end and mean
NOISY_TOL=5e-7 # A, common-latent electrical / combined decisions
DIODE_TOL=.002 # mW, sampled peak, midpoint and boundaries

from dynamic_receiver_sweep_v010 import segment_moments, transition

def run_case(z,w,noise,seeds,case,on,gap,tr,dt,domains):
    no=round(on/dt); ng=round(gap/dt); W=len(seeds); symbols=z.shape[-1]
    assert ng==0 and no%8==0 and np.isclose(no*dt,on)
    bounds=tuple(k*no//8 for k in range(9))
    shape=(2,W,REPEATS,S)
    # Common independent initial and segment latents across LO, cutoff, arms,
    # timings, drive and all three resolutions; independent streams/repeats.
    init=np.stack([rng(seed,domains[3]).normal(size=(REPEATS,S)) for seed in seeds])
    draws=np.stack([rng(seed,domains[4]).normal(size=(symbols,8,2,REPEATS,S)) for seed in seeds],axis=3)
    # draws [symbol,segment,innovation,weight,repeat,stream]
    states={}; clean_states={}; results={}; peaks={}; grid_fields=[]
    for lo,fc in itertools.product(LOS,FCS):
        states[lo,fc]=np.broadcast_to(init*np.sqrt(psd(0.,lo)*np.pi*fc*1e9/2),shape).copy()
        clean_states[lo,fc]=np.zeros((W,S))
        results[lo,fc]=np.empty((9,3,W,REPEATS,S,symbols)) # readout, clean/electrical/combined
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
                for k,(val,cval) in enumerate(zip([state]+means,[clean]+cmeans)):
                    results[key][k,0,...,j]=np.broadcast_to(cval[:,None,:],(W,REPEATS,S))
                    results[key][k,1:,...,j]=val
                states[key]=state;clean_states[key]=clean
    return results,peaks,endfields,coldfields,np.stack(grid_fields),terms_total,dict(balance=balance,mvm_excess=excess,hybrid_error=hybrid_error,q_min=qlo,q_max=qhi)

def features(raw, taps):
    # raw: endpoint followed by eight current-symbol means; final axis is time.
    now=raw[1:]
    if taps==8:return now
    prev=np.zeros_like(now)
    prev[...,1:]=now[...,:-1]
    return np.concatenate((now,prev),axis=0)

def digest(coef):
    return hashlib.sha256(np.asarray(coef,dtype="<f8").tobytes()).hexdigest()

def fit(raw,target,taps,lam):
    # No labels or test inputs accepted. Combined calibration arm only.
    x=features(raw,taps)[:,2].reshape(taps,-1).T
    # target [weight,stream,symbol]; repeat axis paired with features.
    y=np.broadcast_to(target[:,None],raw.shape[2:]).reshape(-1)
    scale=max(float(np.sqrt(np.mean(y*y))),1e-12)
    X=x/scale; Y=y/scale
    aug=np.vstack((X,np.sqrt(len(X)*lam)*np.eye(taps)))
    rhs=np.concatenate((Y,np.zeros(taps)))
    coef,_,rank,sv=np.linalg.lstsq(aug,rhs,rcond=None)
    assert rank==taps and np.all(np.isfinite(coef))
    coef.setflags(write=False)
    return coef,dict(taps=taps,lambda_=lam,scale_a=scale,calibration_rows=len(X),
        singular_values=sv.tolist(),condition=float(sv[0]/sv[-1]),
        calibration_rmse_a=float(np.sqrt(np.mean((x@coef-y)**2))),sha256=digest(coef),coefficients=coef.tolist())

def decide(raw,coefs):
    anchors=[raw[0],raw[-1],raw[-2:].mean(axis=0),raw[-4:].mean(axis=0)]
    equalized=[np.einsum("f,f...->...",c,features(raw,len(c)),optimize=True) for c in coefs]
    return np.stack(anchors+equalized)

def verify_causality():
    rg=np.random.default_rng(120120)
    raw=rg.normal(size=(9,3,2,8,8,6))
    c=np.arange(1,17,dtype=float)/16
    coefs=[np.eye(8)[-1],c,c]
    v=decide(raw,coefs)
    assert np.array_equal(v[4],v[1])
    assert np.all(features(raw,16)[8:,...,0]==0)
    assert np.array_equal(features(raw,16)[8:,...,1:],raw[1:,...,:-1])
    changed=raw.copy();changed[...,3:]+=1000
    assert np.array_equal(v[...,:3],decide(changed,coefs)[...,:3])
    changed=raw.copy();changed[...,0,:]+=1000
    assert np.array_equal(v[...,1:,:],decide(changed,coefs)[...,1:,:])
    target=rg.normal(size=(2,8,6))
    coef,info=fit(raw,target,16,.01)
    assert not coef.flags.writeable and info["sha256"]==digest(coef)
    # The fitting interface accepts no labels; test-data perturbation cannot
    # change the immutable calibration vector used in decisions.
    frozen=digest(coef)
    decide(changed,[coef[:8],coef,coef])
    assert digest(coef)==frozen
    return True

def verify_eight_segments():
    # Independent covariance propagation for endpoint and all eight means.
    f=np.linspace(-.05,.08,16)+1j*np.linspace(.02,-.01,16)
    off=np.array([[[[.003]]]])
    maxdet=0.;maxcov=0.
    for fc,lo,dt in itertools.product(FCS,LOS,(.25,.125,.0625)):
        current,p,_,_=hybrid(f+.003,lo)
        a,m,c=coefficients(fc,dt)
        def prop(split):
            state=np.zeros(9);cov=np.zeros((9,9));start=0
            for n in split:
                k=start//2+1
                if n==1:
                    A,M=a,m;u=(1-a)*current[start];v=(1-m)*current[start]
                    C=psd(p[start],lo)*c
                else:
                    A,M,u,v,xx,xy,yy=segment_moments(f[start:start+n,None,None],fc,dt,lo,off)
                    u,v,xx,xy,yy=(float(x.item()) for x in (u,v,xx,xy,yy))
                    C=np.array([[xx,xy],[xy,yy]])
                F=np.eye(9);F[0,0]=A;F[k,0]=M*n/2
                D=np.zeros((9,2));D[0,0]=1;D[k,1]=n/2
                state=F@state+D@np.array([u,v]);cov=F@cov@F.T+D@C@D.T
                start+=n
            return state,cov
        x,cx=prop([2]*8);y,cy=prop([1]*16)
        maxdet=max(maxdet,float(np.max(abs(x-y))))
        maxcov=max(maxcov,float(np.max(abs(cx-cy))/np.max(abs(cy))))
    return maxdet,maxcov

def make_data(weights,domains,n):
    seeds=[];drives=[];z=[];w=[];y=[];noise=[];launch=[];inputs=[]
    for r in weights:
        seed,drive=r["seed"],r["drive_mw"];w1=np.array(r["w1"]);w2=np.array(r["w2"])
        x,labels=dataset(seed,domains[0],n);order=rng(seed,domains[1]).permutation(n)
        x=x[:,order];labels=labels[order]
        inputs.append(x.copy());launch.append(float(drive*np.mean(np.sum(x*x,axis=0))))
        z.append((np.sqrt(drive)*(w1@x)).reshape(8,S,n//S));w.append(w2.ravel())
        y.append(labels.reshape(S,n//S));seeds.append(seed);drives.append(drive)
        noise.append((NOISE*np.einsum("c,rcn->rn",w2.ravel(),rng(seed,domains[2]).normal(size=(REPEATS,8,n)))).reshape(REPEATS,S,n//S))
    z,w,y,noise=map(np.asarray,(z,w,y,noise))
    assert np.all(y.sum(axis=(1,2))==n//2) and np.max(abs(z)**2)<=4
    assert all(np.array_equal(inputs[i],inputs[j]) for i in range(10) for j in range(10) if seeds[i]==seeds[j])
    return z,w,y,noise,seeds,drives,launch

def write_csv(name,rows):
    with (OUT/name).open("w",newline="") as f:
        wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)

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
    for exp in ("opa-nl-011","opa-nl-010","opa-nl-009","opa-nl-003"):
        root=Path("results")/exp
        manifest=json.loads((root/"provenance.json").read_text())["files"]
        for name,v in manifest.items():
            if exp=="opa-nl-003" and name!="weights.json":continue
            p=root/name;prior[p]=sha(p)
            if prior[p]!=v["sha256"]:raise ValueError("archive mismatch")
    weights=[r for r in json.loads(Path("results/opa-nl-003/weights.json").read_text()) if r["kind"]=="absorber"]
    # The full seed archive audit is an implementation prerequisite.
    with (OUT/"nl011_seed_analysis.json").open("w") as out:
        subprocess.run([sys.executable,"research/analyze_nl011.py"],stdout=out,check=True)
    assert len(weights)==10 and len({(r["seed"],r["drive_mw"]) for r in weights})==10
    assert set(CAL_DOMAINS).isdisjoint(TEST_DOMAINS)
    cz,cw,cy,cn,seeds,drives,cl=make_data(weights,CAL_DOMAINS,512)
    z,w,y,noise,ts,td,launch=make_data(weights,TEST_DOMAINS,1024)
    assert seeds==ts and drives==td and np.array_equal(w,cw)
    checks=dict(weights=True,balanced=True,power_domain=True,paired_inputs=True,
        disjoint_domains=True,archive_seed_audit=True,causality=verify_causality())
    err_current,err_cov=verify_segment()
    partition_det,partition_cov=verify_eight_segments()
    noise_regression=verify_stationary()
    checks.update(segment_regression=err_current<1e-15 and err_cov<1e-9,
        partition_regression=partition_det<1e-15 and partition_cov<1e-9,stationary_noise_regression=True)
    if not all(checks.values()):raise ValueError("preflight")
    pilot_start=time.monotonic()
    run_case(z[...,:1],w,noise[...,:1],seeds,CASES['C2'],50,0,5,grids(50)[-1],TEST_DOMAINS)
    pilot_seconds=time.monotonic()-pilot_start
    step_budget=sum(128*round(on/dt) for _,on,_,_ in TIMINGS for dt in grids(on))+sum(64*round(on/grids(on)[-1]) for _,on,_,_ in TIMINGS)
    print("Pilot seconds",pilot_seconds,"step budget",step_budget,flush=True)
    calibration=[]; coefficient_hashes=set(); paired_readouts=[]
    rows=[];audits=[];conv=[];resolution_groups=[];resolution_rows=[]
    for name,on,gap,tr in TIMINGS:
        case=CASES[name];stable=eligible(z,case);prev=None
        # Fit only on calibration trajectory at finest resolution, before test run.
        cal,_,ce,_,_,_,_=run_case(cz,cw,cn,seeds,case,on,gap,tr,grids(on)[-1],CAL_DOMAINS)
        fixed={}
        for (lo,fc),raw in cal.items():
            target=hybrid(ce,lo)[0]
            fits=[fit(raw,target,taps,lam) for taps,lam in ((8,.01),(16,.01),(16,.1))]
            fixed[lo,fc]=tuple(c for c,_ in fits)
            for method,(_,info) in zip(READOUTS[4:],fits):
                calibration.append(dict(candidate=name,on_ps=on,gap_ps=gap,response_ps=tr,lo_mw=lo,fc_ghz=fc,
                    readout=method,domains=list(CAL_DOMAINS),**info))
        del cal,raw

        for level,dt in enumerate(grids(on)):
            raw,peak,end,cold,grid,terms,diag=run_case(z,w,noise,seeds,case,on,gap,tr,dt,TEST_DOMAINS)
            res={k:decide(raw.pop(k),fixed[k]) for k in tuple(raw)}
            del raw
            for k,coefs in fixed.items():
                for method,c in zip(READOUTS[4:],coefs):
                    coefficient_hashes.add((on,tr,level,*k,method,digest(c)))
                    assert not c.flags.writeable
            meta=dict(candidate=name,on_ps=on,gap_ps=gap,response_ps=tr,dt_ps=dt,resolution_level=level,cadence_gsymbol_s=1000/(on+gap))
            audits.append(dict(**meta,**diag,first_symbol_error=float(np.max(abs(end[...,0]-cold[...,0])))))
            local=[]
            for (lo,fc),values in res.items():
                for k,readout in enumerate(READOUTS):
                    for i,(seed,drive) in enumerate(zip(seeds,drives)):
                        rr=dict(**meta,lo_mw=lo,fc_ghz=fc,enbw_ghz=np.pi*fc/2,readout=readout,
                            integration_ps=on*FRACTIONS[k],feature_history_ps=on if k>=5 else 0.,taps=0 if k<4 else (8 if k==4 else 16),
                            segment_rate_gsegment_s=8*1000/on if k>=4 else 0.,
                            coefficient_sha256=digest(fixed[lo,fc][k-4]) if k>=4 else '',seed=seed,drive_mw=drive,stationary_eligible=stable,
                            unfiltered_accuracy=float(np.mean((end[i].real>0)==y[i])),
                            cold_unfiltered_accuracy=float(np.mean((cold[i].real>0)==y[i])),
                            max_optical_memory_field=float(np.max(abs(end[i]-cold[i]))),
                            electrical_peak_diode_mw=float(peak[lo][0,i]),combined_peak_diode_mw=float(peak[lo][1,i]),
                            launch_mw=launch[i],lo_electric_lower_mw=lo/.20,
                            signal_electric_lower_mw=launch[i]/.20,
                            signal_plus_lo_electric_lower_mw=(launch[i]+lo)/.20,
                            **{name+"_fj":float(terms[1,i,:,j].sum()) for j,name in enumerate(("input","reflection","drop","absorption","initial","final"))},
                            **row_metrics(values[k,:,i],y[i]))
                        baseline=values[0,:,i]
                        anchor_var=float(np.var(baseline[1]-baseline[0,0]))
                        target=hybrid(end[i],lo)[0]
                        rr["electrical_noise_amplification"]=rr["electrical_noise_variance_a2"]/anchor_var
                        rr["clean_target_rmse_a"]=float(np.sqrt(np.mean((values[k,0,i,0]-target)**2)))
                        for rep_idx in range(REPEATS):
                            rr[f"combined_correct_r{rep_idx}"]=int(np.sum((values[k,2,i,rep_idx]>0)==y[i]))
                        if level==2 and k>=4:
                            # Exact paired correct/incorrect counts, not independent
                            # differences of marginal worst-repeat accuracies.
                            eq=(values[k,2,i]>0)==y[i]
                            for ak,anchor in enumerate(READOUTS[:4]):
                                ac=(values[ak,2,i]>0)==y[i]
                                for ri in range(REPEATS):
                                    paired_readouts.append(dict(**meta,lo_mw=lo,fc_ghz=fc,drive_mw=drive,seed=seed,
                                        readout=readout,anchor=anchor,repeat=ri,
                                        both_correct=int(np.sum(eq[ri]&ac[ri])),
                                        equalizer_only=int(np.sum(eq[ri]&~ac[ri])),
                                        anchor_only=int(np.sum(~eq[ri]&ac[ri])),
                                        neither=int(np.sum(~eq[ri]&~ac[ri]))))
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
    checks.update(counts=len(rows)==5040 and len(groups)==1008 and len(audits)==12 and len(conv)==8 and len(resolution_groups)==3024 and len(resolution_rows)==15120 and len(pairs)==504 and len(calibration)==216 and len(paired_readouts)==69120,
        paired_counts=all(sum(r[k] for k in ('both_correct','equalizer_only','anchor_only','neither'))==1024 for r in paired_readouts),
        unique_keys=len({tuple(r[k] for k in keys)+ (r["seed"],) for r in rows})==5040 and len({tuple(r[k] for k in keys)+(r["seed"],r["resolution_level"]) for r in resolution_rows})==15120,
        frozen_coefficients=coefficient_hashes=={(v["on_ps"],v["response_ps"],level,v["lo_mw"],v["fc_ghz"],v["readout"],v["sha256"]) for v in calibration for level in range(3)},
        optical_balance=all(r["balance"]<1e-6 and r["mvm_excess"]<1e-9 and r["q_min"]>=-1e-10 and r["q_max"]<=1+1e-10 for r in audits),
        hybrid=all(r["hybrid_error"]<1e-15 for r in audits),
        aggregate_energy_balance=all(abs(r["input_fj"]+r["initial_fj"]-r["reflection_fj"]-r["drop_fj"]-r["absorption_fj"]-r["final_fj"])/(1+r["input_fj"]+r["initial_fj"])<1e-6 for r in resolution_rows),
        unique_group_keys=len({tuple(r[k] for k in keys)+(r["resolution_level"],) for r in resolution_groups})==3024,
        first_symbol=all(r["first_symbol_error"]<1e-12 for r in audits),
        convergence=all(r["field_error"]<FIELD_TOL and r["clean_current_error"]<CURRENT_TOL
            and r["waveform_grid_error"]<FIELD_TOL and r["noisy_current_error"]<NOISY_TOL and r["peak_error_mw"]<DIODE_TOL for r in conv),
        finite=all(np.isfinite(v) for r in rows+audits+conv for v in r.values() if isinstance(v,(int,float))),
        archive_immutable=all(sha(p)==v for p,v in prior.items()))
    checks={k:bool(v) for k,v in checks.items()}
    result=dict(experiment="OPA-NL-012",checks=checks,failures=[k for k,v in checks.items() if not v],
        rows=len(rows),groups=len(groups),calibration_domains=list(CAL_DOMAINS),test_domains=list(TEST_DOMAINS),resolution_groups=len(resolution_groups),
        fastest_common_confirmed_passes=fastest,stationary_noise_regression=noise_regression,
        best_maximin_by_timing=best,partition_current_error=partition_det,partition_covariance_error=partition_cov,
        common_confirmed_passes=common,combined_confirmed_groups=sum(g["confirmed_combined_pass"] for g in groups),
        ambiguous_groups=sum(not g["numerically_stable_gate"] for g in groups),
        tolerances=dict(field=FIELD_TOL,current=CURRENT_TOL,noisy=NOISY_TOL,diode_mw=DIODE_TOL),
        convergence=conv,segment_regression_current_error=err_current,segment_regression_covariance_error=err_cov,
        pilot_seconds=pilot_seconds,step_budget=step_budget,elapsed_seconds=time.monotonic()-start,
        limitations=["Piecewise midpoint current and PSD; exact segment-level covariance and common Gaussian latents, not Brownian path coupling.",
          "All four timings evaluated at aligned dt <= .0625 ps; groups with gate disagreement excluded from confirmed passes.",
          "Hypothetical electrical PSD and symbol-held optical field noise; no measured receiver, BER, hardware throughput or wall-plug claim."])
    for name,items in (("metrics.csv",rows),("summary.csv",groups),("resolution_groups.csv",resolution_groups),("resolution_metrics.csv",resolution_rows),("convergence.csv",conv),("optical_audit.csv",audits),("common_drive_pairs.csv",pairs),("paired_readouts.csv",paired_readouts)):
        write_csv(name,items)
    (OUT/"coefficients.json").write_text(json.dumps(calibration,indent=2,allow_nan=False)+"\n")
    (OUT/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,allow_nan=False))
    for p in sorted(OUT.iterdir()):
        if p.is_file():print(p.name,p.stat().st_size,sha(p))
    if result["failures"]:raise SystemExit("implementation checks failed")
if __name__=="__main__":main()
