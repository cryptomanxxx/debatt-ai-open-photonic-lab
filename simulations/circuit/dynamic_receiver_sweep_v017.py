"""OPA-NL-017: exploratory causal extended-history receiver sweep."""
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

OUT=Path("results/opa-nl-017")
SETTINGS=((40,3.,120),(41,3.,80),(41,3.,120),(42,2.,120),(42,3.,120))
TIMINGS=tuple(("C2",on,0,5) for on in (40,41,42))
ANCHORS=("end","eighth_mean","quarter_mean","half_mean")
CONTROL=ANCHORS+("ridge8","ridge16","ridge16_strong")
READOUTS=ANCHORS+("frozen_ridge16","frozen_ridge16_midlow","ridge16","ridge16_midlow",
                 "ridge24","ridge24_midlow","ridge32","ridge32_midlow")
FRACTIONS=(0.,.125,.25,.5)
FRESH={"ridge16":(16,.01),"ridge16_midlow":(16,.003),"ridge24":(24,.01),
       "ridge24_midlow":(24,.003),"ridge32":(32,.01),"ridge32_midlow":(32,.003)}

def methods(on):
    return CONTROL if on==42 else READOUTS

def taps_for(method):
    if method in ANCHORS:return 0
    if method=="ridge8":return 8
    return FRESH.get(method,(16,None))[0]

def anchors(method):
    extra={"ridge16":("frozen_ridge16",),"ridge16_midlow":("frozen_ridge16_midlow",),
           "ridge24":("ridge16",),"ridge24_midlow":("ridge16_midlow",),
           "ridge32":("ridge16","ridge24"),"ridge32_midlow":("ridge16_midlow","ridge24_midlow")}
    return ANCHORS+extra.get(method,())

def paired_anchors(on,method):
    if on==42:return ANCHORS+(("ridge8",) if method=="ridge16" else ())
    return anchors(method)

CAL_DOMAINS=tuple(range(10504,10509))
TEST_DOMAINS=tuple(range(10514,10519))
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

from dynamic_receiver_sweep_v013 import (run_case, make_data, digest, features as inherited_features,
    decide as inherited_decide, verify_causality as inherited_causality)
from dynamic_receiver_sweep_v012 import fit as inherited_fit, verify_eight_segments

def features(raw,taps):
    # Time is the last axis; all other axes, including stream, stay separate.
    assert taps in (8,16,24,32) and raw.shape[0]==9
    now=raw[1:]
    if taps==8:return now
    blocks=[now]
    for lag in range(1,taps//8):
        prev=np.zeros_like(now)
        if lag<now.shape[-1]:
            prev[...,lag:]=now[...,:-lag]
        blocks.append(prev)
    return np.concatenate(blocks,axis=0)

def decide(raw,coefs):
    anchor=[raw[0],raw[-1],raw[-2:].mean(axis=0),raw[-4:].mean(axis=0)]
    # Apply identical contraction for short and long receivers.
    eq=[np.einsum("f,f...->...",c,features(raw,len(c)),optimize=True) for c in coefs]
    return np.stack(anchor+eq)

def fit(raw,target,taps,lam):
    # Exact inherited objective: combined calibration features, pooled across
    # weights, drives, streams, repeats; no labels or test input.
    x=features(raw,taps)[:,2].reshape(taps,-1).T
    y=np.broadcast_to(target[:,None],raw.shape[2:]).reshape(-1)
    scale=max(float(np.sqrt(np.mean(y*y))),1e-12)
    X=x/scale;Y=y/scale
    aug=np.vstack((X,np.sqrt(len(X)*lam)*np.eye(taps)))
    rhs=np.concatenate((Y,np.zeros(taps)))
    coef,_,rank,sv=np.linalg.lstsq(aug,rhs,rcond=None)
    assert rank==taps and np.all(np.isfinite(coef))
    coef.setflags(write=False)
    return coef,dict(taps=taps,lambda_=lam,scale_a=scale,calibration_rows=len(X),
        singular_values=sv.tolist(),condition=float(sv[0]/sv[-1]),
        calibration_rmse_a=float(np.sqrt(np.mean((x@coef-y)**2))),
        sha256=digest(coef),coefficients=coef.tolist())

def verify_causality():
    assert inherited_causality()
    rg=np.random.default_rng(170170)
    raw=rg.normal(size=(9,3,2,8,8,6))
    for taps in (8,16):
        assert np.array_equal(features(raw,taps),inherited_features(raw,taps))
    coefs=[rg.normal(size=taps) for taps in (8,16,24,32)]
    assert np.array_equal(decide(raw,coefs[:2]),inherited_decide(raw,coefs[:2]))
    for taps in (8,16,24,32):
        f=features(raw,taps)
        for lag in range(taps//8):
            block=f[8*lag:8*(lag+1)]
            if lag==0:assert np.array_equal(block,raw[1:])
            else:
                assert np.all(block[...,:lag]==0)
                assert np.array_equal(block[...,lag:],raw[1:,...,:-lag])
        short=features(raw[...,:1],taps)
        assert np.all(short[8:]==0)
    impulse=np.zeros_like(raw);impulse[1,2,0,0,0,1]=1
    for lag in range(4):
        v=features(impulse,32)[8*lag:8*(lag+1)]
        assert np.count_nonzero(v)==1 and v[0,2,0,0,0,1+lag]==1
    expected=decide(raw,coefs)
    for cut in range(1,raw.shape[-1]):
        changed=raw.copy();changed[...,cut:]+=rg.normal(size=changed[...,cut:].shape)*100
        assert np.array_equal(expected[...,:cut],decide(changed,coefs)[...,:cut])
    changed=raw.copy();changed[...,0,:]+=1000
    assert np.array_equal(expected[...,1:,:],decide(changed,coefs)[...,1:,:])
    target=rg.normal(size=(2,8,6))
    for taps in (8,16,24,32):
        c,info=fit(raw,target,taps,.003)
        assert not c.flags.writeable and digest(c)==info["sha256"]
        if taps<=16:
            old,old_info=inherited_fit(raw,target,taps,.003)
            assert np.array_equal(c,old) and info==old_info
        h=digest(c)
        decide(changed,[c])
        assert digest(c)==h
    return True

def write_csv(name,rows):
    with (OUT/name).open("w",newline="") as f:
        wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)

def group_analysis(groups):
    bykey={(g["on_ps"],g["lo_mw"],g["fc_ghz"],g["readout"],g["drive_mw"]):g for g in groups}
    pairs=[]
    for on,lo,fc in SETTINGS:
        for method in methods(on):
            a,b=(bykey[on,lo,fc,method,d] for d in (.1,1.))
            pairs.append(dict(candidate="C2",on_ps=on,gap_ps=0,response_ps=5,lo_mw=lo,fc_ghz=fc,readout=method,
                cadence_gsymbol_s=1000/on,combined_worst_low=a["combined_worst"],combined_worst_high=b["combined_worst"],
                maximin=min(a["combined_worst"],b["combined_worst"]),
                passes_both_drives=a["confirmed_combined_pass"] and b["confirmed_combined_pass"]))
    return pairs

PINS={
    (42,2.,120,"ridge8"):"d1ec822076cdf6f244270482226b9dd5b1fe3ced04dc73c154a8d16bb63c72a2",
    (42,2.,120,"ridge16"):"b8d9df37a73688d153ba724dc1768aa83171be426f468aa4643f276a1654cba7",
    (42,2.,120,"ridge16_strong"):"3a5d95a7fe8b123ea863ebe2e7e619163706283353949a06f8477740c51201a1",
    (42,3.,120,"ridge8"):"a9cfe09852a7c78536690183bd151809a0d9a923386fe93c79be80722a4274b6",
    (42,3.,120,"ridge16"):"7c05c69ac3e19e7486aaebe801d3e08bcb64299a6605a18c2e771145c5916174",
    (42,3.,120,"ridge16_strong"):"64616dc6c2b2ca901fb46562b7edbc86841f5304452de742ea60f0397629d7aa",
    (40,3.,120,"ridge16"):"07cce3e02fb413ca6f6617bfb4e7e7dd0eb50e4ef1f5eb6d8187732bc8c55d4a",
    (40,3.,120,"ridge16_midlow"):"bf7ad3f46dfe183e3cffeee2d5373008e9ecd2b7dd76a4ec97f2df57f1df4e3b",
    (41,3.,80,"ridge16"):"601beea1759c1d60d761be880cde11c30cb6db2603ec2ade67c10ec881a59430",
    (41,3.,80,"ridge16_midlow"):"1ccfbaa45af3fb4aea0effb527a8c834e5e3a1b6b190d84a1dd8116034c26c9b",
    (41,3.,120,"ridge16"):"c6cbb9a4f6c13bf23449f4980822321d1dfeda942ff34a359c4b0597240314ca",
    (41,3.,120,"ridge16_midlow"):"31b1dc98ef9c78f51b3ca0b5d8f8eac6369485a8db4c9d5c24af7fe85f0049ce",
}

def prepare_coefficients(weights):
    fixed={}; evidence=[]
    archived={n:json.loads(Path("results/opa-nl-"+n+"/coefficients.json").read_text()) for n in ("014","015","016")}
    def frozen(on,lo,fc,method):
        source_method=method.removeprefix("frozen_")
        records=[]
        for n in (("014","015","016") if on==42 else ("016",)):
            matches=[r for r in archived[n] if (r["candidate"],r["on_ps"],r["gap_ps"],r["response_ps"],r["lo_mw"],r["fc_ghz"],r["readout"])==
                     ("C2",on,0,5,lo,fc,source_method)]
            assert len(matches)==1
            record=matches[0]
            c=np.asarray(record["coefficients"],dtype="<f8")
            assert c.shape==(taps_for(method),) and np.all(np.isfinite(c))
            assert digest(c)==record["sha256"]==PINS[on,lo,fc,source_method]
            records.append(record)
        assert all(r["coefficients"]==records[-1]["coefficients"] for r in records)
        c.setflags(write=False)
        evidence.append(dict(records[-1],readout=method,source="archived_NL014_NL015_NL016" if on==42 else "archived_NL016",
                             source_readout=source_method))
        return c
    for on,lo,fc in SETTINGS:
        if on==42:
            fixed[on,lo,fc]=tuple(frozen(on,lo,fc,m) for m in methods(on)[4:])
    assert len(evidence)==6
    z,w,_,noise,seeds,_,_=make_data(weights,CAL_DOMAINS,512)
    for on in (40,41):
        receivers=tuple((lo,fc) for dur,lo,fc in SETTINGS if dur==on)
        raw,_,end,_,_,_,_=run_case(z,w,noise,seeds,CASES["C2"],on,0,5,grids(on)[-1],CAL_DOMAINS,receivers)
        for lo,fc in receivers:
            vectors=[]
            for method in methods(on)[4:]:
                if method.startswith("frozen_"):
                    vectors.append(frozen(on,lo,fc,method));continue
                taps,lam=FRESH[method]
                c,info=fit(raw[lo,fc],hybrid(end,lo)[0],taps,lam)
                vectors.append(c)
                evidence.append(dict(candidate="C2",on_ps=on,gap_ps=0,response_ps=5,lo_mw=lo,fc_ghz=fc,
                                     readout=method,domains=list(CAL_DOMAINS),source="NL017_calibration",**info))
            fixed[on,lo,fc]=tuple(vectors)
        del raw
    assert set(fixed)==set(SETTINGS) and len(evidence)==30
    assert sum(r["source"]=="NL017_calibration" for r in evidence)==18
    assert all(not c.flags.writeable for vectors in fixed.values() for c in vectors)
    assert all(len(fixed[on,lo,fc])==len(methods(on))-4 for on,lo,fc in SETTINGS)
    for record in evidence:
        record["lag_block_l2_norms"]=[float(np.linalg.norm(record["coefficients"][i:i+8]))
                                      for i in range(0,len(record["coefficients"]),8)]
    return fixed,evidence

def main():
    start=time.monotonic(); OUT.mkdir(parents=True,exist_ok=True)
    prior={}
    for exp in ("opa-nl-016","opa-nl-015","opa-nl-014","opa-nl-013","opa-nl-012","opa-nl-011","opa-nl-010","opa-nl-009","opa-nl-003"):
        root=Path("results")/exp
        manifest_path=root/"provenance.json"
        prior[manifest_path]=sha(manifest_path)
        manifest=json.loads(manifest_path.read_text())["files"]
        for name,v in manifest.items():
            if exp=="opa-nl-003" and name!="weights.json":continue
            p=root/name;prior[p]=sha(p)
            if prior[p]!=v["sha256"]:raise ValueError("archive mismatch")
    weights=[r for r in json.loads(Path("results/opa-nl-003/weights.json").read_text()) if r["kind"]=="absorber"]
    with (OUT/"nl016_seed_analysis.json").open("w") as out:
        subprocess.run([sys.executable,"research/analyze_nl016.py"],stdout=out,check=True)
    assert json.loads((OUT/"nl016_seed_analysis.json").read_text())["verified"] is True
    assert len(weights)==10 and len({(r["seed"],r["drive_mw"]) for r in weights})==10
    # Pin the actual five NL003 archived absorber seeds, not NL002 training seeds.
    assert all({r["seed"] for r in weights if r["drive_mw"]==d}=={1301,1302,1303,1304,1305} for d in (.1,1.))
    prior_domains=set(range(100,132))|set(range(10004,10009))|set(range(10014,10019))|{1,2,3,4,11,12,13,14,15,24,25,26,34,35,36,44,45,46,54,55,56,64,65,66,67,74,75,76,77,84,85,86,87,88,94,95,96,97,98,999}
    prior_domains.update(range(10104,10109));prior_domains.update(range(10114,10119))
    prior_domains.update(range(10204,10209));prior_domains.update(range(10214,10219))
    prior_domains.update(range(10304,10309));prior_domains.update(range(10314,10319))
    prior_domains.update(range(10404,10409));prior_domains.update(range(10414,10419))
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
    z,w,_,noise,seeds,_,_=make_data(weights,CAL_DOMAINS,512)
    pilot_start=time.monotonic()
    run_case(z[...,:1],w,noise[...,:1],seeds,CASES["C2"],41,0,5,grids(41)[-1],CAL_DOMAINS,tuple((lo,fc) for dur,lo,fc in SETTINGS if dur==41))
    pilot_seconds=time.monotonic()-pilot_start
    step_budget=sum(256*round(on/dt) for _,on,_,_ in TIMINGS for dt in grids(on))+sum(64*round(on/grids(on)[-1]) for on in (40,41))
    # Conservative timing estimate: all symbol steps priced at the two-receiver fine-grid pilot.
    estimated_seconds=pilot_seconds*(3*256*3+2*64)
    print("Pilot seconds",pilot_seconds,"step budget",step_budget,
          "conservative estimated seconds",estimated_seconds,flush=True)
    # Finish and persist every fit before generating exploratory test examples.
    fixed_all,coefficient_records=prepare_coefficients(weights)
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
    passes=[p for p in pairs if p["passes_both_drives"]]
    candidates=[p for p in passes if p["on_ps"]<42]
    control=[p for p in pairs if p["on_ps"]==42]
    positive_controls=[p for p in control if p["readout"]=="ridge16"]
    assert len(positive_controls)==2
    control_ok=all(p["passes_both_drives"] for p in positive_controls)
    fastest=[p for p in candidates if p["on_ps"]==min(q["on_ps"] for q in candidates)] if candidates else []
    pareto=[p for p in candidates if not any(q["on_ps"]==p["on_ps"] and q["readout"]==p["readout"]
        and q["lo_mw"]<=p["lo_mw"] and q["maximin"]>=p["maximin"]
        and (q["lo_mw"]<p["lo_mw"] or q["maximin"]>p["maximin"]) for q in candidates)]
    ranked=sorted(candidates,key=lambda p:(p["on_ps"],p["lo_mw"],p["fc_ghz"],
        taps_for(p["readout"]),
        -p["maximin"],READOUTS.index(p["readout"])))
    # Among equally complex readouts use larger margin, then fixed method order.
    proposed=ranked[0] if control_ok and ranked else None
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
    expected_seed_keys={("exploratory","C2",on,0,5,lo,fc,method,drive,seed) for on,lo,fc in SETTINGS for method,drive,seed in itertools.product(methods(on),(.1,1.),range(1301,1306))}
    expected_paired_keys={k+(anchor,rep) for k in expected_seed_keys if k[-3] not in ANCHORS for anchor in paired_anchors(k[2],k[-3]) for rep in range(REPEATS)}
    checks["frozen_file_unchanged"]=sha(OUT/"coefficients.json")==frozen_file_hash
    checks.update(paired_marginals=paired_ok and paired_keys==expected_paired_keys,counts=len(rows)==500 and len(groups)==100 and len(audits)==9 and len(conv)==6 and len(resolution_groups)==300 and len(resolution_rows)==1500 and len(pairs)==50 and len(coefficient_records)==30 and len(paired_readouts)==11680,
        paired_counts=all(sum(r[k] for k in ('both_correct','equalizer_only','anchor_only','neither'))==N for r in paired_readouts),
        unique_keys=set(seed_index)==expected_seed_keys and {tuple(r[k] for k in keys)+(r["seed"],r["resolution_level"]) for r in resolution_rows}=={k+(level,) for k in expected_seed_keys for level in range(3)},
        frozen_coefficients=coefficient_hashes=={(panel,v["on_ps"],v["response_ps"],level,v["lo_mw"],v["fc_ghz"],v["readout"],v["sha256"]) for v in coefficient_records for level in range(3) for panel in PANELS},
        optical_balance=all(r["balance"]<1e-6 and r["mvm_excess"]<1e-9 and r["q_min"]>=-1e-10 and r["q_max"]<=1+1e-10 for r in audits),
        hybrid=all(r["hybrid_error"]<1e-15 for r in audits),
        aggregate_energy_balance=all(abs(r["input_fj"]+r["initial_fj"]-r["reflection_fj"]-r["drop_fj"]-r["absorption_fj"]-r["final_fj"])/(1+r["input_fj"]+r["initial_fj"])<1e-6 for r in resolution_rows),
        unique_group_keys=len({tuple(r[k] for k in keys)+(r["resolution_level"],) for r in resolution_groups})==300,
        first_symbol=all(r["first_symbol_error"]<1e-12 for r in audits),
        convergence=all(r["field_error"]<FIELD_TOL and r["clean_current_error"]<CURRENT_TOL
            and r["waveform_grid_error"]<FIELD_TOL and r["noisy_current_error"]<NOISY_TOL and r["peak_error_mw"]<DIODE_TOL for r in conv),
        finite=all(np.isfinite(v) for r in resolution_rows+audits+conv for v in r.values() if isinstance(v,(int,float))),
        archive_immutable=all(sha(p)==v for p,v in prior.items()))
    checks={k:bool(v) for k,v in checks.items()}
    result=dict(experiment="OPA-NL-017",checks=checks,failures=[k for k,v in checks.items() if not v],
        rows=len(rows),groups=len(groups),calibration_domains=CAL_DOMAINS,test_domains=TEST_DOMAINS,examples_per_seed_panel=N,resolution_groups=len(resolution_groups),
        control_passed=control_ok,control_pairs=control,fastest_exploratory_passes=fastest,pareto_exploratory=pareto,
        ranked_exploratory_candidates=ranked,proposed_confirmation_candidate=proposed,stationary_noise_regression=noise_regression,
        all_common_drive_pairs=pairs,partition_current_error=partition_det,partition_covariance_error=partition_cov,
        common_exploratory_passes=passes,combined_passing_groups=sum(g["confirmed_combined_pass"] for g in groups),
        ambiguous_groups=sum(not g["numerically_stable_gate"] for g in groups),
        tolerances=dict(field=FIELD_TOL,current=CURRENT_TOL,noisy=NOISY_TOL,diode_mw=DIODE_TOL),
        convergence=conv,segment_regression_current_error=err_current,segment_regression_covariance_error=err_cov,
        pilot_seconds=pilot_seconds,conservative_estimated_seconds=estimated_seconds,step_budget=step_budget,elapsed_seconds=time.monotonic()-start,
        limitations=["Piecewise midpoint current and PSD; exact segment-level covariance and common Gaussian latents, not Brownian path coupling.",
          "All five receiver settings evaluated at aligned dt <= .0625 ps; groups with gate disagreement excluded from confirmed passes.",
          "Single exploratory panel; numerical passing gates do not independently confirm a new cadence. A failed frozen control prevents promotion.",
          "Hypothetical electrical PSD and symbol-held optical field noise; no measured receiver, BER, hardware throughput or wall-plug claim."])
    # Aggregate exact paired gains per drive/setting/readout, not independent trials.
    from collections import defaultdict
    totals=defaultdict(lambda:[0,0,0,0])
    for r in paired_readouts:
        k=tuple(r[name] for name in ("on_ps","lo_mw","fc_ghz","drive_mw","readout","anchor"))
        for i,name in enumerate(("both_correct","equalizer_only","anchor_only","neither")):
            totals[k][i]+=r[name]
    paired_summary=[]
    for k,(both,eq,base,neither) in sorted(totals.items()):
        paired_summary.append(dict(zip(("on_ps","lo_mw","fc_ghz","drive_mw","readout","anchor"),k),
            both_correct=both,equalizer_only=eq,anchor_only=base,neither=neither,
            net_correct=eq-base,accuracy_delta=(eq-base)/(both+eq+base+neither)))
    coefficient_summary=[dict(on_ps=r["on_ps"],lo_mw=r["lo_mw"],fc_ghz=r["fc_ghz"],
        readout=r["readout"],source=r["source"],sha256=r["sha256"],
        taps=r["taps"],lambda_=r["lambda_"],l2_norm=float(np.linalg.norm(r["coefficients"])),
        lag0_l2=r["lag_block_l2_norms"][0],
        lag1_l2=r["lag_block_l2_norms"][1] if r["taps"]>=16 else "",
        lag2_l2=r["lag_block_l2_norms"][2] if r["taps"]>=24 else "",
        lag3_l2=r["lag_block_l2_norms"][3] if r["taps"]>=32 else "",condition=r["condition"],
        calibration_rmse_a=r["calibration_rmse_a"]) for r in coefficient_records]
    checks["paired_summary_counts"]=len(paired_summary)==292 and all(sum(r[k] for k in ("both_correct","equalizer_only","anchor_only","neither"))==81920 for r in paired_summary)
    result["matched_history_comparisons"]=[r for r in paired_summary if r["readout"].startswith(("ridge24","ridge32")) and r["anchor"] not in ANCHORS]
    result["matched_recalibration_comparisons"]=[r for r in paired_summary if r["anchor"].startswith("frozen_")]
    checks["matched_comparison_counts"]=len(result["matched_history_comparisons"])==36 and len(result["matched_recalibration_comparisons"])==12
    result["checks"]=checks
    result["failures"]=[k for k,v in checks.items() if not v]
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
