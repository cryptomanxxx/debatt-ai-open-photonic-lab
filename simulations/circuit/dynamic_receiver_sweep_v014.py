"""OPA-NL-014: exploratory finite-response cadence sweep with a frozen control."""
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

OUT=Path("results/opa-nl-014")
SETTINGS=tuple(itertools.product((42,43,44),(1.,2.,3.),(40,60,80,120)))+((45,1.,60),)
TIMINGS=tuple(("C2",on,0,5) for on in (42,43,44,45))
READOUTS=("end","eighth_mean","quarter_mean","half_mean","ridge8","ridge16","ridge16_strong")
FRACTIONS=(0.,.125,.25,.5,1.,1.,1.)
CAL_DOMAINS=(10204,10205,10206,10207,10208)
TEST_DOMAINS=(10214,10215,10216,10217,10218)
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

from dynamic_receiver_sweep_v013 import run_case, make_data, decide, digest, verify_causality, load_fixed
from dynamic_receiver_sweep_v012 import fit, verify_eight_segments

def write_csv(name,rows):
    with (OUT/name).open("w",newline="") as f:
        wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)

def group_analysis(groups):
    bykey={(g["on_ps"],g["lo_mw"],g["fc_ghz"],g["readout"],g["drive_mw"]):g for g in groups}
    pairs=[]
    for on,lo,fc in SETTINGS:
        for method in READOUTS:
            a,b=(bykey[on,lo,fc,method,d] for d in (.1,1.))
            pairs.append(dict(candidate="C2",on_ps=on,gap_ps=0,response_ps=5,lo_mw=lo,fc_ghz=fc,readout=method,
                cadence_gsymbol_s=1000/on,combined_worst_low=a["combined_worst"],combined_worst_high=b["combined_worst"],
                maximin=min(a["combined_worst"],b["combined_worst"]),
                passes_both_drives=a["confirmed_combined_pass"] and b["confirmed_combined_pass"]))
    return pairs

def prepare_coefficients(weights):
    # Preserve the exact frozen control; candidate fits consume calibration inputs only.
    archived,records=load_fixed()
    fixed={(45,1.,60):archived[45,1.,60]}
    evidence=[dict(r,source="archived_NL013_NL012") for r in records
              if (r["on_ps"],r["lo_mw"],r["fc_ghz"])==(45,1.,60)]
    nl013=json.loads(Path("results/opa-nl-013/coefficients.json").read_text())
    for record in evidence:
        matches=[r for r in nl013 if (r["on_ps"],r["lo_mw"],r["fc_ghz"],r["readout"])==
                 (45,1.,60,record["readout"])]
        assert len(matches)==1 and matches[0]["sha256"]==record["sha256"]
        assert digest(matches[0]["coefficients"])==record["sha256"]
    z,w,_,noise,seeds,_,_=make_data(weights,CAL_DOMAINS,512)
    for on in (42,43,44):
        receivers=tuple((lo,fc) for dur,lo,fc in SETTINGS if dur==on)
        raw,_,end,_,_,_,_=run_case(z,w,noise,seeds,CASES["C2"],on,0,5,grids(on)[-1],CAL_DOMAINS,receivers)
        for lo,fc in receivers:
            fits=[fit(raw[lo,fc],hybrid(end,lo)[0],taps,lam) for taps,lam in ((8,.01),(16,.01),(16,.1))]
            fixed[on,lo,fc]=tuple(c for c,_ in fits)
            for method,(_,info) in zip(READOUTS[4:],fits):
                evidence.append(dict(candidate="C2",on_ps=on,gap_ps=0,response_ps=5,lo_mw=lo,fc_ghz=fc,
                                     readout=method,domains=list(CAL_DOMAINS),source="NL014_calibration",**info))
        del raw
    assert set(fixed)==set(SETTINGS) and len(evidence)==111
    assert all(not c.flags.writeable for vectors in fixed.values() for c in vectors)
    return fixed,evidence

def main():
    start=time.monotonic(); OUT.mkdir(parents=True,exist_ok=True)
    prior={}
    for exp in ("opa-nl-013","opa-nl-012","opa-nl-011","opa-nl-010","opa-nl-009","opa-nl-003"):
        root=Path("results")/exp
        manifest_path=root/"provenance.json"
        prior[manifest_path]=sha(manifest_path)
        manifest=json.loads(manifest_path.read_text())["files"]
        for name,v in manifest.items():
            if exp=="opa-nl-003" and name!="weights.json":continue
            p=root/name;prior[p]=sha(p)
            if prior[p]!=v["sha256"]:raise ValueError("archive mismatch")
    weights=[r for r in json.loads(Path("results/opa-nl-003/weights.json").read_text()) if r["kind"]=="absorber"]
    with (OUT/"nl013_seed_analysis.json").open("w") as out:
        subprocess.run([sys.executable,"research/analyze_nl013.py"],stdout=out,check=True)
    assert len(weights)==10 and len({(r["seed"],r["drive_mw"]) for r in weights})==10
    # Pin the actual five NL003 archived absorber seeds, not NL002 training seeds.
    assert all({r["seed"] for r in weights if r["drive_mw"]==d}=={1301,1302,1303,1304,1305} for d in (.1,1.))
    prior_domains=set(range(100,132))|set(range(10004,10009))|set(range(10014,10019))|{1,2,3,4,11,12,13,14,15,24,25,26,34,35,36,44,45,46,54,55,56,64,65,66,67,74,75,76,77,84,85,86,87,88,94,95,96,97,98,999}
    prior_domains.update(range(10104,10109));prior_domains.update(range(10114,10119))
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
    run_case(z[...,:1],w,noise[...,:1],seeds,CASES["C2"],44,0,5,grids(44)[-1],CAL_DOMAINS,tuple((lo,fc) for dur,lo,fc in SETTINGS if dur==44))
    pilot_seconds=time.monotonic()-pilot_start
    step_budget=sum(256*round(on/dt) for _,on,_,_ in TIMINGS for dt in grids(on))+sum(64*round(on/grids(on)[-1]) for on in (42,43,44))
    # Conservative timing estimate: all symbol steps priced at the 12-receiver fine-grid pilot.
    estimated_seconds=pilot_seconds*(4*256*3+3*64)
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
    candidates=[p for p in passes if p["on_ps"]<45]
    control=[p for p in pairs if p["on_ps"]==45]
    control_ok=all(p["passes_both_drives"] for p in control if p["readout"] in ("ridge8","ridge16"))
    fastest=[p for p in candidates if p["on_ps"]==min(q["on_ps"] for q in candidates)] if candidates else []
    pareto=[p for p in candidates if not any(q["on_ps"]==p["on_ps"] and q["readout"]==p["readout"]
        and q["lo_mw"]<=p["lo_mw"] and q["maximin"]>=p["maximin"]
        and (q["lo_mw"]<p["lo_mw"] or q["maximin"]>p["maximin"]) for q in candidates)]
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
    expected_seed_keys={("exploratory","C2",on,0,5,lo,fc,method,drive,seed) for (on,lo,fc),method,drive,seed in itertools.product(SETTINGS,READOUTS,(.1,1.),range(1301,1306))}
    expected_paired_keys={k+(anchor,rep) for k in expected_seed_keys if k[-3] in READOUTS[4:] for anchor in READOUTS[:4]+(("ridge8",) if k[-3]=="ridge16" else ()) for rep in range(REPEATS)}
    checks["frozen_file_unchanged"]=sha(OUT/"coefficients.json")==frozen_file_hash
    checks.update(paired_marginals=paired_ok and paired_keys==expected_paired_keys,counts=len(rows)==2590 and len(groups)==518 and len(audits)==12 and len(conv)==8 and len(resolution_groups)==1554 and len(resolution_rows)==7770 and len(pairs)==259 and len(coefficient_records)==111 and len(paired_readouts)==38480,
        paired_counts=all(sum(r[k] for k in ('both_correct','equalizer_only','anchor_only','neither'))==N for r in paired_readouts),
        unique_keys=set(seed_index)==expected_seed_keys and {tuple(r[k] for k in keys)+(r["seed"],r["resolution_level"]) for r in resolution_rows}=={k+(level,) for k in expected_seed_keys for level in range(3)},
        frozen_coefficients=coefficient_hashes=={(panel,v["on_ps"],v["response_ps"],level,v["lo_mw"],v["fc_ghz"],v["readout"],v["sha256"]) for v in coefficient_records for level in range(3) for panel in PANELS},
        optical_balance=all(r["balance"]<1e-6 and r["mvm_excess"]<1e-9 and r["q_min"]>=-1e-10 and r["q_max"]<=1+1e-10 for r in audits),
        hybrid=all(r["hybrid_error"]<1e-15 for r in audits),
        aggregate_energy_balance=all(abs(r["input_fj"]+r["initial_fj"]-r["reflection_fj"]-r["drop_fj"]-r["absorption_fj"]-r["final_fj"])/(1+r["input_fj"]+r["initial_fj"])<1e-6 for r in resolution_rows),
        unique_group_keys=len({tuple(r[k] for k in keys)+(r["resolution_level"],) for r in resolution_groups})==1554,
        first_symbol=all(r["first_symbol_error"]<1e-12 for r in audits),
        convergence=all(r["field_error"]<FIELD_TOL and r["clean_current_error"]<CURRENT_TOL
            and r["waveform_grid_error"]<FIELD_TOL and r["noisy_current_error"]<NOISY_TOL and r["peak_error_mw"]<DIODE_TOL for r in conv),
        finite=all(np.isfinite(v) for r in resolution_rows+audits+conv for v in r.values() if isinstance(v,(int,float))),
        archive_immutable=all(sha(p)==v for p,v in prior.items()))
    checks={k:bool(v) for k,v in checks.items()}
    result=dict(experiment="OPA-NL-014",checks=checks,failures=[k for k,v in checks.items() if not v],
        rows=len(rows),groups=len(groups),calibration_domains=CAL_DOMAINS,test_domains=TEST_DOMAINS,examples_per_seed_panel=N,resolution_groups=len(resolution_groups),
        control_passed=control_ok,control_pairs=control,fastest_exploratory_passes=fastest,pareto_exploratory=pareto,stationary_noise_regression=noise_regression,
        all_common_drive_pairs=pairs,partition_current_error=partition_det,partition_covariance_error=partition_cov,
        common_exploratory_passes=passes,combined_passing_groups=sum(g["confirmed_combined_pass"] for g in groups),
        ambiguous_groups=sum(not g["numerically_stable_gate"] for g in groups),
        tolerances=dict(field=FIELD_TOL,current=CURRENT_TOL,noisy=NOISY_TOL,diode_mw=DIODE_TOL),
        convergence=conv,segment_regression_current_error=err_current,segment_regression_covariance_error=err_cov,
        pilot_seconds=pilot_seconds,conservative_estimated_seconds=estimated_seconds,step_budget=step_budget,elapsed_seconds=time.monotonic()-start,
        limitations=["Piecewise midpoint current and PSD; exact segment-level covariance and common Gaussian latents, not Brownian path coupling.",
          "All 37 receiver settings evaluated at aligned dt <= .0625 ps; groups with gate disagreement excluded from confirmed passes.",
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
        l2_norm=float(np.linalg.norm(r["coefficients"])),condition=r["condition"],
        calibration_rmse_a=r["calibration_rmse_a"]) for r in coefficient_records]
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
