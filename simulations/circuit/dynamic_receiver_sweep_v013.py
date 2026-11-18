"""OPA-NL-013: independent confirmation with archived frozen coefficients; no fitting."""
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

OUT=Path("results/opa-nl-013")
SETTINGS=((45,1.,60),(45,2.,60),(50,1.,20))
TIMINGS=(("C2",45,0,5),("C2",50,0,5))
READOUTS=("end","eighth_mean","quarter_mean","half_mean","ridge8","ridge16","ridge16_strong")
FRACTIONS=(0.,.125,.25,.5,1.,1.,1.)
PANELS={"A":(10104,10105,10106,10107,10108),"B":(10114,10115,10116,10117,10118)}
N=2048
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

def run_case(z,w,noise,seeds,case,on,gap,tr,dt,domains,receivers):
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
    for lo,fc in receivers:
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
        for lo in sorted({key[0] for key in receivers}):
            peak,err=peak_and_hybrid(field,edges,no,lo,offset)
            peaks[lo]=np.maximum(peaks[lo],peak);hybrid_error=max(hybrid_error,err)
            for fc in sorted(key[1] for key in receivers if key[0]==lo):
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
    c.setflags(write=False)
    frozen=digest(c)
    decide(changed,[c[:8],c,c])
    assert digest(c)==frozen
    return True

from dynamic_receiver_sweep_v012 import verify_eight_segments

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

PINS={
    (45,1.,60):("1f21ed5381aefa68f2ac7ec8eae6189b4332c93d07bcf4977c7ebb433985d08d","1cf055e0bb853b437070171a1ee9135716f61a760a2421dca1e9ca6da57f794f","64db2504804993c2f4a9db888957f186179b09807b45c4e468c31c376b7e0623"),
    (45,2.,60):("6b5dd601fc801b904deedb05b7784d9ae1955cfbccc61532147d7c6f3f3b15c3","1e462161c94f12ad8dd2ed6a6bc317f3073fae0da125141fd8d395bc9159e8cb","06d73bfc95e3e1b6fd05367104509cf61c5f191a5a96a0c6e169f51b318aef9a"),
    (50,1.,20):("84b210baa61ecac14b3b0b0a28e705c018d91b971a1114a458d7b613a1796e8e","83faf818f67ccc216a7a8102b5908f9ac354a5c3a71affe5d571bf9a95d2fba4","094e3cdae57127e28438151cde43dc54632d2889718cf182bc8726cd10d34c4d"),
}

def load_fixed():
    archive=json.loads(Path("results/opa-nl-012/coefficients.json").read_text())
    fixed={}; records=[]
    for setting,pins in PINS.items():
        on,lo,fc=setting
        coefs=[]
        for method,pin in zip(READOUTS[4:],pins):
            matches=[c for c in archive if (c["candidate"],c["on_ps"],c["gap_ps"],c["response_ps"],
                c["lo_mw"],c["fc_ghz"],c["readout"])==("C2",on,0,5,lo,fc,method)]
            assert len(matches)==1
            record=matches[0];coef=np.asarray(record["coefficients"],dtype="<f8")
            assert coef.shape==(8 if method=="ridge8" else 16,) and np.all(np.isfinite(coef))
            assert digest(coef)==pin==record["sha256"]
            coef.setflags(write=False);coefs.append(coef);records.append(record)
        fixed[setting]=tuple(coefs)
    assert set(fixed)==set(SETTINGS) and len(records)==9
    return fixed,records

def group_analysis(groups):
    bykey={(g["panel"],g["on_ps"],g["lo_mw"],g["fc_ghz"],g["readout"],g["drive_mw"]):g for g in groups}
    pairs=[]
    for on,lo,fc in SETTINGS:
        for method in READOUTS:
            selected=[bykey[p,on,lo,fc,method,d] for p in PANELS for d in (.1,1.)]
            row=dict(candidate="C2",on_ps=on,gap_ps=0,response_ps=5,lo_mw=lo,fc_ghz=fc,readout=method,
                     cadence_gsymbol_s=1000/on)
            for g in selected:
                suffix=g["panel"]+("_low" if g["drive_mw"]==.1 else "_high")
                row["combined_worst_"+suffix]=g["combined_worst"]
                row["confirmed_"+suffix]=g["confirmed_combined_pass"]
            row["maximin"]=min(g["combined_worst"] for g in selected)
            row["confirmed_both_panels"]=all(g["confirmed_combined_pass"] for g in selected)
            pairs.append(row)
    return pairs

def main():
    start=time.monotonic(); OUT.mkdir(parents=True,exist_ok=True)
    prior={}
    for exp in ("opa-nl-012","opa-nl-011","opa-nl-010","opa-nl-009","opa-nl-003"):
        root=Path("results")/exp
        manifest_path=root/"provenance.json"
        prior[manifest_path]=sha(manifest_path)
        manifest=json.loads(manifest_path.read_text())["files"]
        for name,v in manifest.items():
            if exp=="opa-nl-003" and name!="weights.json":continue
            p=root/name;prior[p]=sha(p)
            if prior[p]!=v["sha256"]:raise ValueError("archive mismatch")
    weights=[r for r in json.loads(Path("results/opa-nl-003/weights.json").read_text()) if r["kind"]=="absorber"]
    with (OUT/"nl012_seed_analysis.json").open("w") as out:
        subprocess.run([sys.executable,"research/analyze_nl012.py"],stdout=out,check=True)
    assert len(weights)==10 and len({(r["seed"],r["drive_mw"]) for r in weights})==10
    assert all({r["seed"] for r in weights if r["drive_mw"]==d}=={1201,1202,1203,1204,1205} for d in (.1,1.))
    prior_domains=set(range(100,132))|set(range(10004,10009))|set(range(10014,10019))|{1,2,3,4,11,12,13,14,15,24,25,26,34,35,36,44,45,46,54,55,56,64,65,66,67,74,75,76,77,84,85,86,87,88,94,95,96,97,98,999}
    domains_flat=[x for domains in PANELS.values() for x in domains]
    assert len(set(domains_flat))==10 and not set(domains_flat)&prior_domains
    fixed_all,coefficient_records=load_fixed()
    checks=dict(weights=True,balanced=True,power_domain=True,paired_inputs=True,
        disjoint_domains=True,archive_seed_audit=True,causality=verify_causality())
    err_current,err_cov=verify_segment()
    partition_det,partition_cov=verify_eight_segments()
    noise_regression=verify_stationary()
    checks.update(segment_regression=err_current<1e-15 and err_cov<1e-9,
        partition_regression=partition_det<1e-15 and partition_cov<1e-9,stationary_noise_regression=True)
    if not all(checks.values()):raise ValueError("preflight")
    z,w,y,noise,seeds,drives,launch=make_data(weights,PANELS["A"],N)
    pilot_start=time.monotonic()
    run_case(z[...,:1],w,noise[...,:1],seeds,CASES['C2'],45,0,5,grids(45)[-1],PANELS["A"],((1.,60),(2.,60)))
    pilot_seconds=time.monotonic()-pilot_start
    step_budget=2*sum(256*round(on/dt) for _,on,_,_ in TIMINGS for dt in grids(on))
    print("Pilot seconds",pilot_seconds,"step budget",step_budget,flush=True)
    coefficient_hashes=set(); paired_readouts=[]
    rows=[];audits=[];conv=[];resolution_groups=[];resolution_rows=[]
    for panel,domains in PANELS.items():
        z,w,y,noise,seeds,drives,launch=make_data(weights,domains,N)
        for name,on,gap,tr in TIMINGS:
            case=CASES[name];stable=eligible(z,case);prev=None
            receivers=tuple((lo,fc) for dur,lo,fc in SETTINGS if dur==on)
            fixed={(lo,fc):fixed_all[on,lo,fc] for lo,fc in receivers}
            for level,dt in enumerate(grids(on)):
                raw,peak,end,cold,grid,terms,diag=run_case(z,w,noise,seeds,case,on,gap,tr,dt,domains,receivers)
                res={k:decide(raw.pop(k),fixed[k]) for k in tuple(raw)}
                del raw
                for k,coefs in fixed.items():
                    for method,c in zip(READOUTS[4:],coefs):
                        coefficient_hashes.add((panel,on,tr,level,*k,method,digest(c)))
                        assert not c.flags.writeable
                meta=dict(panel=panel,candidate=name,on_ps=on,gap_ps=gap,response_ps=tr,dt_ps=dt,resolution_level=level,cadence_gsymbol_s=1000/(on+gap))
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
                                for ak,anchor in list(enumerate(READOUTS[:4]))+([(4,"ridge8")] if k==5 else []):
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
                for (lo,fc),readout,drive in itertools.product(receivers,READOUTS,(.1,1.)):
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
    middle={(r["panel"],r["candidate"],r["on_ps"],r["gap_ps"],r["response_ps"],r["lo_mw"],r["fc_ghz"],r["readout"],r["drive_mw"]):r for r in resolution_groups if r["resolution_level"]==1}
    keys=("panel","candidate","on_ps","gap_ps","response_ps","lo_mw","fc_ghz","readout","drive_mw")
    for g in groups:
        p=middle[tuple(g[k] for k in keys)]
        g["numerically_stable_gate"]=bool(g["combined_pass"]==p["combined_pass"] and g["electrical_pass"]==p["electrical_pass"])
        g["confirmed_combined_pass"]=g["combined_pass"] and g["numerically_stable_gate"]
    pairs=group_analysis(groups)
    confirmed=[p for p in pairs if p["confirmed_both_panels"]]
    primary=next(p for p in pairs if (p["on_ps"],p["lo_mw"],p["fc_ghz"],p["readout"])==(45,1.,60,"ridge16"))
    secondary=next(p for p in pairs if (p["on_ps"],p["lo_mw"],p["fc_ghz"],p["readout"])==(45,1.,60,"ridge8"))
    for g in groups:
        reasons=[]
        if not g["stationary_eligible"]:reasons.append("stationary")
        if g["unfiltered_min"]<.95:reasons.append("unfiltered")
        if g["clean_min"]<.95:reasons.append("clean_filtered")
        if g["combined_worst"]<.95:reasons.append("combined_noise")
        if g["combined_peak_diode_mw"]>2:reasons.append("diode")
        if not g["numerically_stable_gate"]:reasons.append("resolution")
        g["failure_reasons"]=";".join(reasons)
    seed_index={tuple(r[k] for k in keys)+(r["seed"],):r for r in rows}
    paired_keys=set();paired_ok=True
    for r in paired_readouts:
        k=tuple(r[x] for x in keys)+(r["seed"],)
        anchor=dict(r,readout=r["anchor"])
        ak=tuple(anchor[x] for x in keys)+(r["seed"],)
        rk=k+(r["anchor"],r["repeat"])
        n=[r[x] for x in ("both_correct","equalizer_only","anchor_only","neither")]
        col=f'combined_correct_r{r["repeat"]}'
        paired_ok &= rk not in paired_keys and min(n)>=0 and n[0]+n[1]==seed_index[k][col] and n[0]+n[2]==seed_index[ak][col]
        paired_keys.add(rk)
    checks.update(paired_marginals=paired_ok and len(paired_keys)==6240,counts=len(rows)==420 and len(groups)==84 and len(audits)==12 and len(conv)==8 and len(resolution_groups)==252 and len(resolution_rows)==1260 and len(pairs)==21 and len(coefficient_records)==9 and len(paired_readouts)==6240,
        paired_counts=all(sum(r[k] for k in ('both_correct','equalizer_only','anchor_only','neither'))==N for r in paired_readouts),
        unique_keys=len({tuple(r[k] for k in keys)+ (r["seed"],) for r in rows})==420 and len({tuple(r[k] for k in keys)+(r["seed"],r["resolution_level"]) for r in resolution_rows})==1260,
        frozen_coefficients=coefficient_hashes=={(panel,v["on_ps"],v["response_ps"],level,v["lo_mw"],v["fc_ghz"],v["readout"],v["sha256"]) for v in coefficient_records for level in range(3) for panel in PANELS},
        optical_balance=all(r["balance"]<1e-6 and r["mvm_excess"]<1e-9 and r["q_min"]>=-1e-10 and r["q_max"]<=1+1e-10 for r in audits),
        hybrid=all(r["hybrid_error"]<1e-15 for r in audits),
        aggregate_energy_balance=all(abs(r["input_fj"]+r["initial_fj"]-r["reflection_fj"]-r["drop_fj"]-r["absorption_fj"]-r["final_fj"])/(1+r["input_fj"]+r["initial_fj"])<1e-6 for r in resolution_rows),
        unique_group_keys=len({tuple(r[k] for k in keys)+(r["resolution_level"],) for r in resolution_groups})==252,
        first_symbol=all(r["first_symbol_error"]<1e-12 for r in audits),
        convergence=all(r["field_error"]<FIELD_TOL and r["clean_current_error"]<CURRENT_TOL
            and r["waveform_grid_error"]<FIELD_TOL and r["noisy_current_error"]<NOISY_TOL and r["peak_error_mw"]<DIODE_TOL for r in conv),
        finite=all(np.isfinite(v) for r in resolution_rows+audits+conv for v in r.values() if isinstance(v,(int,float))),
        archive_immutable=all(sha(p)==v for p,v in prior.items()))
    checks={k:bool(v) for k,v in checks.items()}
    result=dict(experiment="OPA-NL-013",checks=checks,failures=[k for k,v in checks.items() if not v],
        rows=len(rows),groups=len(groups),panel_domains=PANELS,examples_per_seed_panel=N,resolution_groups=len(resolution_groups),
        primary_endpoint=primary,secondary_endpoint=secondary,stationary_noise_regression=noise_regression,
        all_panel_pairs=pairs,partition_current_error=partition_det,partition_covariance_error=partition_cov,
        common_confirmed_passes=confirmed,combined_confirmed_groups=sum(g["confirmed_combined_pass"] for g in groups),
        ambiguous_groups=sum(not g["numerically_stable_gate"] for g in groups),
        tolerances=dict(field=FIELD_TOL,current=CURRENT_TOL,noisy=NOISY_TOL,diode_mw=DIODE_TOL),
        convergence=conv,segment_regression_current_error=err_current,segment_regression_covariance_error=err_cov,
        pilot_seconds=pilot_seconds,step_budget=step_budget,elapsed_seconds=time.monotonic()-start,
        limitations=["Piecewise midpoint current and PSD; exact segment-level covariance and common Gaussian latents, not Brownian path coupling.",
          "All three receiver settings evaluated at aligned dt <= .0625 ps; groups with gate disagreement excluded from confirmed passes.",
          "Hypothetical electrical PSD and symbol-held optical field noise; no measured receiver, BER, hardware throughput or wall-plug claim."])
    for name,items in (("metrics.csv",rows),("summary.csv",groups),("resolution_groups.csv",resolution_groups),("resolution_metrics.csv",resolution_rows),("convergence.csv",conv),("optical_audit.csv",audits),("two_panel_pairs.csv",pairs),("paired_readouts.csv",paired_readouts)):
        write_csv(name,items)
    (OUT/"coefficients.json").write_text(json.dumps(coefficient_records,indent=2,allow_nan=False)+"\n")
    (OUT/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,allow_nan=False))
    for p in sorted(OUT.iterdir()):
        if p.is_file():print(p.name,p.stat().st_size,sha(p))
    if result["failures"]:raise SystemExit("implementation checks failed")
if __name__=="__main__":main()
