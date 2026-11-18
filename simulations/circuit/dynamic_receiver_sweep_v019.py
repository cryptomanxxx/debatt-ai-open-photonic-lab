"""OPA-NL-019: noise-aware margin-oriented receiver exploration at 42 ps."""
import hashlib
import subprocess
import sys
import csv
import itertools
import json
import time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from dynamic_receiver import hybrid, psd, coefficients, rk4_wave_step, noisy_step, deterministic
from nonlinear_activation_v002 import dataset
from nonlinear_activation_v003 import rng, R, Q
from nonlinear_activation_v006 import solve, folds, response, sha, NOISE, K1
from nonlinear_activation_v009 import CASES, TAU, US, NS, COUP, LOSS

OUT=Path("results/opa-nl-019")
SETTINGS=((42,2.,120),(42,3.,120))
TIMINGS=(("C2",42,0,5),)
ANCHORS=("end","eighth_mean","quarter_mean","half_mean")
READOUTS=ANCHORS+("frozen_ridge16","fresh_ridge16","margin16_balanced","margin16_low")
FRACTIONS=(0.,.125,.25,.5)
PRIMARY=(42,2.,120,"margin16_balanced")
MARGIN_METHODS=("margin16_balanced","margin16_low")
TEMPERATURE=.10
LAMBDA=.01

def methods(on):
    assert on==42
    return READOUTS

def taps_for(method):
    return 0 if method in ANCHORS else 16

def paired_anchors(on,method):
    assert on==42
    extra={"fresh_ridge16":("frozen_ridge16",),
           "margin16_balanced":("fresh_ridge16","frozen_ridge16"),
           "margin16_low":("fresh_ridge16","frozen_ridge16","margin16_balanced")}
    return ANCHORS+extra.get(method,())

CAL_DOMAINS=tuple(range(10704,10709))
TEST_DOMAINS=tuple(range(10714,10719))
PANELS={"exploratory":TEST_DOMAINS}
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

from dynamic_receiver_sweep_v013 import run_case, make_data, digest
from dynamic_receiver_sweep_v012 import verify_eight_segments
from dynamic_receiver_sweep_v017 import features, decide, fit
from dynamic_receiver_sweep_v018 import verify_causality

def calibration_arrays(raw,target,labels):
    # Feature, arm, group, repeat, stream, symbol -> group, repeat, stream, symbol, feature.
    X=np.moveaxis(features(raw,16)[:,2],0,-1)
    assert X.shape==(10,8,8,64,16)
    assert labels.shape==(10,8,64) and np.all(np.isin(labels,[0,1]))
    signed=2*np.asarray(labels,dtype=np.float64)-1
    Y=np.broadcast_to(signed[:,None,:,:],X.shape[:-1])
    assert np.array_equal(Y[:,0],signed) and np.array_equal(Y[:,-1],signed)
    T=np.broadcast_to(target[:,None],raw.shape[2:])
    scale=max(float(np.sqrt(np.mean(T*T))),1e-12)
    return X.reshape(10,-1,16)/scale,Y.reshape(10,-1),scale

def group_weights(drives,method):
    assert len(drives)==10 and sum(d==.1 for d in drives)==5 and sum(d==1. for d in drives)==5
    assert method in MARGIN_METHODS
    w=np.array([.1 if method=="margin16_balanced" else (.16 if d==.1 else .04) for d in drives])
    assert np.isclose(w.sum(),1.,rtol=0,atol=1e-15)
    return w

def margin_objective(c,X,Y,w):
    # X [group, examples, features], Y [group, examples].
    signed=(X@c)*Y/TEMPERATURE
    losses=np.logaddexp(0.,-signed).mean(axis=1)
    value=float(w@losses+LAMBDA*np.dot(c,c)/2)
    factor=-Y*expit(-signed)/TEMPERATURE
    grad=np.einsum("g,gn,gnf->f",w,factor,X,optimize=True)/X.shape[1]+LAMBDA*c
    return value,grad

def verify_margin_gradient():
    rng=np.random.default_rng(190190)
    X=rng.normal(size=(10,23,16));Y=rng.choice([-1.,1.],size=(10,23));c=rng.normal(size=16)*.1
    drives=[.1,1.]*5
    max_error=0.
    for method in MARGIN_METHODS:
        w=group_weights(drives,method)
        value,grad=margin_objective(c,X,Y,w)
        manual=sum(w[g]*np.mean(np.logaddexp(0.,-Y[g]*(X[g]@c)/TEMPERATURE)) for g in range(10))+LAMBDA*np.dot(c,c)/2
        assert abs(value-manual)<1e-12
        for i in range(16):
            e=np.zeros(16);e[i]=1e-6
            approx=(margin_objective(c+e,X,Y,w)[0]-margin_objective(c-e,X,Y,w)[0])/(2e-6)
            max_error=max(max_error,abs(approx-grad[i]))
    # Exact axis and label-broadcast regression on uniquely distinguishable groups.
    raw=rng.normal(size=(9,3,10,8,8,64));labels=rng.integers(0,2,size=(10,8,64))
    target=rng.normal(size=(10,8,64))
    xx,yy,scale=calibration_arrays(raw,target,labels)
    for g,rep,stream,symbol in ((0,0,0,0),(3,5,2,17),(9,7,7,63)):
        j=(rep*8+stream)*64+symbol
        assert np.array_equal(xx[g,j],features(raw,16)[:,2,g,rep,stream,symbol]/scale)
        assert yy[g,j]==2*int(labels[g,stream,symbol])-1
    assert max_error<1e-6
    return max_error

def fit_margin(X,Y,scale,drives,method):
    w=group_weights(drives,method)
    zero=np.zeros(16)
    initial,_=margin_objective(zero,X,Y,w)
    opt=minimize(margin_objective,zero,args=(X,Y,w),jac=True,method="L-BFGS-B",
                 options=dict(maxiter=500,ftol=1e-12,gtol=1e-8,maxls=50))
    c=np.asarray(opt.x,dtype="<f8")
    value,grad=margin_objective(c,X,Y,w)
    grad_inf=float(np.max(abs(grad)))
    assert opt.success and c.shape==(16,) and np.all(np.isfinite(c)) and np.linalg.norm(c)>0
    assert np.isfinite(value) and grad_inf<=1e-5 and value<initial
    c.setflags(write=False)
    return c,dict(taps=16,lambda_=LAMBDA,scale_a=scale,calibration_rows=int(Y.size),
        objective_name="weighted_logistic_margin",temperature=TEMPERATURE,group_weights=w.tolist(),
        optimizer_success=bool(opt.success),optimizer_status=int(opt.status),optimizer_message=str(opt.message),
        iterations=int(opt.nit),function_evaluations=int(opt.nfev),objective_initial=initial,
        objective_final=value,gradient_inf=grad_inf,sha256=digest(c),coefficients=c.tolist())

def write_csv(name,rows):
    with (OUT/name).open("w",newline="") as f:
        wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)

def group_analysis(groups):
    bykey={(g["on_ps"],g["lo_mw"],g["fc_ghz"],g["readout"],g["drive_mw"]):g for g in groups}
    pairs=[]
    for on,lo,fc in SETTINGS:
        for method in READOUTS:
            a,b=(bykey[on,lo,fc,method,d] for d in (.1,1.))
            p=dict(candidate="C2",on_ps=on,gap_ps=0,response_ps=5,lo_mw=lo,fc_ghz=fc,readout=method,
                cadence_gsymbol_s=1000/on,combined_worst_low=a["combined_worst"],combined_worst_high=b["combined_worst"],
                maximin=min(a["combined_worst"],b["combined_worst"]),
                passes_both_drives=a["confirmed_combined_pass"] and b["confirmed_combined_pass"])
            p["robustness_target_met"]=p["passes_both_drives"] and p["maximin"]>=.96
            pairs.append(p)
    return pairs

PINS={
    (42,2.,120):"b8d9df37a73688d153ba724dc1768aa83171be426f468aa4643f276a1654cba7",
    (42,3.,120):"7c05c69ac3e19e7486aaebe801d3e08bcb64299a6605a18c2e771145c5916174",
}

def prepare_coefficients(weights):
    fixed={}; evidence=[]
    archived={n:json.loads(Path("results/opa-nl-"+n+"/coefficients.json").read_text()) for n in ("014","015","016","017","018")}
    z,w,labels,noise,seeds,drives,_=make_data(weights,CAL_DOMAINS,512)
    receivers=tuple((lo,fc) for _,lo,fc in SETTINGS)
    raw,_,end,_,_,_,_=run_case(z,w,noise,seeds,CASES["C2"],42,0,5,grids(42)[-1],CAL_DOMAINS,receivers)
    for on,lo,fc in SETTINGS:
        records=[]
        for n in archived:
            matches=[r for r in archived[n] if (r["candidate"],r["on_ps"],r["gap_ps"],r["response_ps"],r["lo_mw"],r["fc_ghz"],r["readout"])==
                     ("C2",on,0,5,lo,fc,"ridge16")]
            assert len(matches)==1
            record=matches[0];c=np.asarray(record["coefficients"],dtype="<f8")
            assert c.shape==(16,) and np.all(np.isfinite(c))
            assert digest(c)==record["sha256"]==PINS[on,lo,fc]
            records.append(record)
        assert all(r["coefficients"]==records[0]["coefficients"] for r in records)
        c.setflags(write=False);vectors=[c]
        evidence.append(dict(records[-1],readout="frozen_ridge16",source="archived_NL018",
            source_readout="ridge16",objective_name="inherited_ridge_reconstruction"))
        target=hybrid(end,lo)[0]
        X,Y,scale=calibration_arrays(raw[lo,fc],target,labels)
        fresh,info=fit(raw[lo,fc],target,16,.01)
        assert info["scale_a"]==scale and info["calibration_rows"]==40960
        vectors.append(fresh)
        common=dict(candidate="C2",on_ps=on,gap_ps=0,response_ps=5,lo_mw=lo,fc_ghz=fc,
            domains=list(CAL_DOMAINS),source="NL019_calibration")
        evidence.append(dict(**common,readout="fresh_ridge16",objective_name="ridge_reconstruction",**info))
        for method in MARGIN_METHODS:
            c,info=fit_margin(X,Y,scale,drives,method)
            vectors.append(c)
            evidence.append(dict(**common,readout=method,calibration_group_seeds=list(map(int,seeds)),
                calibration_group_drives=list(map(float,drives)),**info))
        fixed[on,lo,fc]=tuple(vectors)
    assert len(evidence)==8 and sum(r["source"]=="NL019_calibration" for r in evidence)==6
    assert set(fixed)==set(SETTINGS) and all(len(v)==4 for v in fixed.values())
    assert all(not c.flags.writeable for v in fixed.values() for c in v)
    for record in evidence:
        v=np.asarray(record["coefficients"])
        norm=float(np.linalg.norm(v));assert norm>0
        record["l2_norm"]=norm
        record["normalized_direction"]=(v/norm).tolist()
        record["lag_block_l2_norms"]=[float(np.linalg.norm(v[i:i+8])) for i in (0,8)]
    return fixed,evidence

def main():
    start=time.monotonic(); OUT.mkdir(parents=True,exist_ok=True)
    prior={}
    for exp in ("opa-nl-018","opa-nl-017","opa-nl-016","opa-nl-015","opa-nl-014","opa-nl-013","opa-nl-012","opa-nl-011","opa-nl-010","opa-nl-009","opa-nl-003"):
        root=Path("results")/exp
        manifest_path=root/"provenance.json"
        prior[manifest_path]=sha(manifest_path)
        manifest=json.loads(manifest_path.read_text())["files"]
        for name,v in manifest.items():
            if exp=="opa-nl-003" and name!="weights.json":continue
            p=root/name;prior[p]=sha(p)
            if prior[p]!=v["sha256"]:raise ValueError("archive mismatch")
    weights=[r for r in json.loads(Path("results/opa-nl-003/weights.json").read_text()) if r["kind"]=="absorber"]
    with (OUT/"nl018_seed_analysis.json").open("w") as out:
        subprocess.run([sys.executable,"research/analyze_nl018.py"],stdout=out,check=True)
    assert json.loads((OUT/"nl018_seed_analysis.json").read_text())["verified"] is True
    assert len(weights)==10 and len({(r["seed"],r["drive_mw"]) for r in weights})==10
    # Pin the actual five NL003 archived absorber seeds, not NL002 training seeds.
    assert all({r["seed"] for r in weights if r["drive_mw"]==d}=={1301,1302,1303,1304,1305} for d in (.1,1.))
    prior_domains=set(range(100,132))|set(range(10004,10009))|set(range(10014,10019))|{1,2,3,4,11,12,13,14,15,24,25,26,34,35,36,44,45,46,54,55,56,64,65,66,67,74,75,76,77,84,85,86,87,88,94,95,96,97,98,999}
    prior_domains.update(range(10104,10109));prior_domains.update(range(10114,10119))
    prior_domains.update(range(10204,10209));prior_domains.update(range(10214,10219))
    prior_domains.update(range(10304,10309));prior_domains.update(range(10314,10319))
    prior_domains.update(range(10404,10409));prior_domains.update(range(10414,10419))
    prior_domains.update(range(10504,10509));prior_domains.update(range(10514,10519))
    prior_domains.update(range(10604,10609));prior_domains.update(range(10614,10619))
    domains_flat=list(CAL_DOMAINS)+list(TEST_DOMAINS)
    assert len(set(domains_flat))==10 and not set(domains_flat)&prior_domains
    checks=dict(weights=True,balanced=True,power_domain=True,paired_inputs=True,
        disjoint_domains=True,archive_seed_audit=True,causality=verify_causality())
    err_current,err_cov=verify_segment()
    partition_det,partition_cov=verify_eight_segments()
    noise_regression=verify_stationary()
    checks.update(segment_regression=err_current<1e-15 and err_cov<1e-9,
        partition_regression=partition_det<1e-15 and partition_cov<1e-9,stationary_noise_regression=True)
    if not all(checks.values()):raise ValueError("preflight")
    gradient_error=verify_margin_gradient()
    checks["margin_gradient_regression"]=gradient_error<1e-6
    # Complete all fits and persist immutable vectors before generating test inputs.
    fixed_all,coefficient_records=prepare_coefficients(weights)
    step_budget=sum(256*round(42/dt) for dt in grids(42))+64*round(42/grids(42)[-1])
    (OUT/"coefficients.json").write_text(json.dumps(coefficient_records,indent=2,allow_nan=False)+"\n")
    frozen_file_hash=sha(OUT/"coefficients.json")
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
                    for method,c in zip(methods(on)[4:],coefs):
                        coefficient_hashes.add((panel,on,tr,level,*k,method,digest(c)))
                        assert not c.flags.writeable
                meta=dict(panel=panel,candidate=name,on_ps=on,gap_ps=gap,response_ps=tr,dt_ps=dt,resolution_level=level,cadence_gsymbol_s=1000/(on+gap))
                audits.append(dict(**meta,**diag,first_symbol_error=float(np.max(abs(end[...,0]-cold[...,0])))))
                local=[]
                for (lo,fc),values in res.items():
                    for k,readout in enumerate(methods(on)):
                        for i,(seed,drive) in enumerate(zip(seeds,drives)):
                            rr=dict(**meta,lo_mw=lo,fc_ghz=fc,enbw_ghz=np.pi*fc/2,readout=readout,
                                integration_ps=on*(FRACTIONS[k] if k<4 else 1.),feature_history_ps=on*max(0,taps_for(readout)//8-1),taps=taps_for(readout),
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
                            norm=float(np.linalg.norm(fixed[lo,fc][k-4])) if k>=4 else 1.
                            rr["coefficient_l2_norm"]=norm
                            rr["normalized_electrical_noise_variance_a2"]=rr["electrical_noise_variance_a2"]/norm**2
                            rr["normalized_electrical_noise_amplification"]=rr["electrical_noise_amplification"]/norm**2
                            rr["clean_target_rmse_a"]=float(np.sqrt(np.mean((values[k,0,i,0]-target)**2)))
                            for rep_idx in range(REPEATS):
                                rr[f"combined_correct_r{rep_idx}"]=int(np.sum((values[k,2,i,rep_idx]>0)==y[i]))
                            if level==2 and k>=4:
                                # Exact paired correct/incorrect counts, not independent
                                # differences of marginal worst-repeat accuracies.
                                eq=(values[k,2,i]>0)==y[i]
                                for anchor in paired_anchors(on,readout):
                                    ak=methods(on).index(anchor)
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
                for (lo,fc),readout,drive in itertools.product(receivers,methods(on),(.1,1.)):
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
            # Release references held by the convergence comparison and last receiver loop.
            if level==2:
                del old,op,oe,of,og,oldflags,oldrows
            del prev,res,peak,end,cold,grid,values
    groups=[dict(r) for r in resolution_groups if r["resolution_level"]==2]
    # Flag any final-resolution gate disagreement explicitly, not a physics failure.
    middle={(r["panel"],r["candidate"],r["on_ps"],r["gap_ps"],r["response_ps"],r["lo_mw"],r["fc_ghz"],r["readout"],r["drive_mw"]):r for r in resolution_groups if r["resolution_level"]==1}
    keys=("panel","candidate","on_ps","gap_ps","response_ps","lo_mw","fc_ghz","readout","drive_mw")
    for g in groups:
        p=middle[tuple(g[k] for k in keys)]
        g["numerically_stable_gate"]=bool(g["combined_pass"]==p["combined_pass"] and g["electrical_pass"]==p["electrical_pass"])
        g["confirmed_combined_pass"]=g["combined_pass"] and g["numerically_stable_gate"]
    pairs=group_analysis(groups)
    by_endpoint={(p["on_ps"],p["lo_mw"],p["fc_ghz"],p["readout"]):p for p in pairs}
    primary=by_endpoint[PRIMARY]
    references=[p for p in pairs if p["readout"]=="frozen_ridge16"]
    passes=[p for p in pairs if p["passes_both_drives"]]
    for g in groups:
        reasons=[]
        if not g["stationary_eligible"]:reasons.append("stationary")
        if g["unfiltered_min"]<.95:reasons.append("unfiltered")
        if g["clean_min"]<.95:reasons.append("clean_filtered")
        if g["combined_worst"]<.95:reasons.append("combined_noise")
        if g["combined_peak_diode_mw"]>2:reasons.append("diode")
        if not g["numerically_stable_gate"]:reasons.append("resolution")
        g["failure_reasons"]=";".join(reasons)
        g["electrical_failure_reasons"]=";".join(x for x,failed in (("stationary",not g["stationary_eligible"]),("unfiltered",g["unfiltered_min"]<.95),("clean_filtered",g["clean_min"]<.95),("electrical_noise",g["electrical_worst"]<.95),("diode",any(r["electrical_peak_diode_mw"]>2 for r in rows if tuple(r[k] for k in keys)==tuple(g[k] for k in keys))),("resolution",not g["numerically_stable_gate"])) if failed)
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
    expected_seed_keys={(panel,"C2",on,0,5,lo,fc,method,drive,seed) for panel in PANELS for on,lo,fc in SETTINGS for method,drive,seed in itertools.product(methods(on),(.1,1.),range(1301,1306))}
    expected_paired_keys={k+(anchor,rep) for k in expected_seed_keys if k[-3] not in ANCHORS for anchor in paired_anchors(k[2],k[-3]) for rep in range(REPEATS)}
    checks["frozen_file_unchanged"]=sha(OUT/"coefficients.json")==frozen_file_hash
    checks.update(paired_marginals=paired_ok and paired_keys==expected_paired_keys,counts=len(rows)==160 and len(groups)==32 and len(audits)==3 and len(conv)==2 and len(resolution_groups)==96 and len(resolution_rows)==480 and len(pairs)==16 and len(coefficient_records)==8 and len(paired_readouts)==3520,
        paired_counts=all(sum(r[k] for k in ('both_correct','equalizer_only','anchor_only','neither'))==N for r in paired_readouts),
        unique_keys=set(seed_index)==expected_seed_keys and {tuple(r[k] for k in keys)+(r["seed"],r["resolution_level"]) for r in resolution_rows}=={k+(level,) for k in expected_seed_keys for level in range(3)},
        frozen_coefficients=coefficient_hashes=={(panel,v["on_ps"],v["response_ps"],level,v["lo_mw"],v["fc_ghz"],v["readout"],v["sha256"]) for v in coefficient_records for level in range(3) for panel in PANELS},
        optical_balance=all(r["balance"]<1e-6 and r["mvm_excess"]<1e-9 and r["q_min"]>=-1e-10 and r["q_max"]<=1+1e-10 for r in audits),
        hybrid=all(r["hybrid_error"]<1e-15 for r in audits),
        aggregate_energy_balance=all(abs(r["input_fj"]+r["initial_fj"]-r["reflection_fj"]-r["drop_fj"]-r["absorption_fj"]-r["final_fj"])/(1+r["input_fj"]+r["initial_fj"])<1e-6 for r in resolution_rows),
        unique_group_keys=len({tuple(r[k] for k in keys)+(r["resolution_level"],) for r in resolution_groups})==96,
        first_symbol=all(r["first_symbol_error"]<1e-12 for r in audits),
        convergence=all(r["field_error"]<FIELD_TOL and r["clean_current_error"]<CURRENT_TOL
            and r["waveform_grid_error"]<FIELD_TOL and r["noisy_current_error"]<NOISY_TOL and r["peak_error_mw"]<DIODE_TOL for r in conv),
        finite=all(np.isfinite(v) for r in resolution_rows+audits+conv for v in r.values() if isinstance(v,(int,float))),
        archive_immutable=all(sha(p)==v for p,v in prior.items()))
    checks={k:bool(v) for k,v in checks.items()}
    result=dict(experiment="OPA-NL-019",checks=checks,failures=[k for k,v in checks.items() if not v],
        rows=len(rows),groups=len(groups),calibration_domains=CAL_DOMAINS,test_domains=TEST_DOMAINS,examples_per_seed_panel=N,resolution_groups=len(resolution_groups),
        calibration_examples_per_seed=512,margin_gradient_error=gradient_error,
        historical_references=references,primary_endpoint=primary,
        independent_confirmation_passed=False,historical_cadence_gsymbol_s=1000/42,
        stationary_noise_regression=noise_regression,
        all_common_drive_pairs=pairs,partition_current_error=partition_det,partition_covariance_error=partition_cov,
        common_exploratory_passes=passes,combined_passing_groups=sum(g["confirmed_combined_pass"] for g in groups),
        ambiguous_groups=sum(not g["numerically_stable_gate"] for g in groups),
        tolerances=dict(field=FIELD_TOL,current=CURRENT_TOL,noisy=NOISY_TOL,diode_mw=DIODE_TOL),
        convergence=conv,segment_regression_current_error=err_current,segment_regression_covariance_error=err_cov,
        step_budget=step_budget,elapsed_seconds=time.monotonic()-start,
        limitations=["Piecewise midpoint current and PSD; exact segment-level covariance and common Gaussian latents, not Brownian path coupling.",
          "Both receiver settings evaluated at aligned dt <= .0625 ps; groups with gate disagreement excluded from confirmed passes.",
          "One exploratory panel. No independent confirmation or speed promotion; historical 42 ps confirmation qualified by NL018 failures. Coefficient scale affects current and noise variance but not sign decisions.",
          "Hypothetical electrical PSD and symbol-held optical field noise; no measured receiver, BER, hardware throughput or wall-plug claim."])
    # Aggregate exact paired gains per drive/setting/readout, not independent trials.
    from collections import defaultdict
    totals=defaultdict(lambda:[0,0,0,0])
    for r in paired_readouts:
        k=tuple(r[name] for name in ("panel","on_ps","lo_mw","fc_ghz","drive_mw","readout","anchor"))
        for i,name in enumerate(("both_correct","equalizer_only","anchor_only","neither")):
            totals[k][i]+=r[name]
    paired_summary=[]
    for k,(both,eq,base,neither) in sorted(totals.items()):
        paired_summary.append(dict(zip(("panel","on_ps","lo_mw","fc_ghz","drive_mw","readout","anchor"),k),
            both_correct=both,equalizer_only=eq,anchor_only=base,neither=neither,
            net_correct=eq-base,accuracy_delta=(eq-base)/(both+eq+base+neither)))
    coefficient_summary=[dict(on_ps=r["on_ps"],lo_mw=r["lo_mw"],fc_ghz=r["fc_ghz"],
        readout=r["readout"],source=r["source"],sha256=r["sha256"],taps=r["taps"],lambda_=r["lambda_"],
        objective_name=r["objective_name"],l2_norm=r["l2_norm"],normalized_direction=json.dumps(r["normalized_direction"]),
        lag0_l2=r["lag_block_l2_norms"][0],lag1_l2=r["lag_block_l2_norms"][1],
        condition=r.get("condition",""),calibration_rmse_a=r.get("calibration_rmse_a",""),
        objective_initial=r.get("objective_initial",""),objective_final=r.get("objective_final",""),
        gradient_inf=r.get("gradient_inf",""),iterations=r.get("iterations","")) for r in coefficient_records]
    checks["paired_summary_counts"]=len(paired_summary)==88 and all(sum(r[k] for k in ("both_correct","equalizer_only","anchor_only","neither"))==81920 for r in paired_summary)
    result["matched_margin_comparisons"]=[r for r in paired_summary if r["readout"] in MARGIN_METHODS and r["anchor"] in ("fresh_ridge16","frozen_ridge16")]
    result["matched_recalibration_comparisons"]=[r for r in paired_summary if r["readout"]=="fresh_ridge16" and r["anchor"]=="frozen_ridge16"]
    result["matched_weighting_comparisons"]=[r for r in paired_summary if r["readout"]=="margin16_low" and r["anchor"]=="margin16_balanced"]
    checks["matched_comparison_counts"]=len(result["matched_margin_comparisons"])==16 and len(result["matched_recalibration_comparisons"])==4 and len(result["matched_weighting_comparisons"])==4
    checks["endpoint_coverage"]=set(by_endpoint)=={(on,lo,fc,m) for on,lo,fc in SETTINGS for m in READOUTS}
    checks["optimizer_checks"]=sum(r.get("optimizer_success") is True and r["gradient_inf"]<=1e-5 and r["objective_final"]<r["objective_initial"] for r in coefficient_records)==4
    contrasts=[]
    for on,lo,fc in SETTINGS:
        fresh=by_endpoint[on,lo,fc,"fresh_ridge16"]
        for method in MARGIN_METHODS:
            p=by_endpoint[on,lo,fc,method]
            matched=[r for r in result["matched_margin_comparisons"] if (r["on_ps"],r["lo_mw"],r["fc_ghz"],r["readout"],r["anchor"],r["drive_mw"])==(on,lo,fc,method,"fresh_ridge16",.1)]
            assert len(matched)==1
            delta=p["combined_worst_low"]-fresh["combined_worst_low"]
            net=matched[0]["net_correct"]
            limiting=[r for r in rows if (r["on_ps"],r["lo_mw"],r["fc_ghz"],r["readout"],r["drive_mw"])==(on,lo,fc,method,.1) and r["combined_worst"]==p["combined_worst_low"]]
            contrasts.append(dict(**p,low_worst_delta_vs_fresh=delta,low_net_vs_fresh=net,
                limiting_seed_repeats=[dict(seed=r["seed"],repeats=[i for i in range(REPEATS) if r[f"combined_correct_r{i}"]/N==r["combined_worst"]]) for r in limiting],
                qualifies=bool(p["robustness_target_met"] and delta>0 and net>0)))
    ranked=sorted([p for p in contrasts if p["qualifies"]],key=lambda p:(p["lo_mw"],-p["maximin"],MARGIN_METHODS.index(p["readout"])))
    checks["contrast_coverage"]=len(contrasts)==4
    result["margin_contrasts"]=contrasts
    result["primary_contrast"]=next(p for p in contrasts if (p["on_ps"],p["lo_mw"],p["fc_ghz"],p["readout"])==PRIMARY)
    result["checks"]={k:bool(v) for k,v in checks.items()}
    result["failures"]=[k for k,v in checks.items() if not v]
    result["ranked_qualifying_candidates"]=ranked if not result["failures"] else []
    result["proposed_confirmation_candidate"]=ranked[0] if ranked and not result["failures"] else None
    write_csv("paired_summary.csv",paired_summary)
    write_csv("coefficient_summary.csv",coefficient_summary)
    for r in resolution_rows:
        for arm in ("electrical","combined"):
            r[arm+"_failure_reasons"]=";".join(x for x,failed in (
                ("stationary",not r["stationary_eligible"]),("unfiltered",r["unfiltered_accuracy"]<.95),
                ("clean_filtered",r["clean_filtered_accuracy"]<.95),(arm+"_noise",r[arm+"_worst"]<.95),
                ("diode",r[arm+"_peak_diode_mw"]>2)) if failed)
    for name,items in (("metrics.csv",rows),("summary.csv",groups),("resolution_groups.csv",resolution_groups),("resolution_metrics.csv",resolution_rows),("convergence.csv",conv),("optical_audit.csv",audits),("common_drive_pairs.csv",pairs),("paired_readouts.csv",paired_readouts)):
        write_csv(name,items)
    # Coefficient artifact was written before test generation; never rewrite it.
    (OUT/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,allow_nan=False))
    for p in sorted(OUT.iterdir()):
        if p.is_file():print(p.name,p.stat().st_size,sha(p))
    if result["failures"]:raise SystemExit("implementation checks failed")
if __name__=="__main__":main()
