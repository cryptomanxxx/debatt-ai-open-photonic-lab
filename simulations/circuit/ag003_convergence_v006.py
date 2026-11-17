"""OPA-SYS-006: paired toy training under explicit receiver-noise proxies."""
import csv
import hashlib
import json
import math
from pathlib import Path
import sys
import numpy as np
from ag003_receiver_audit_v003 import load, snr

ROOT = Path("antigravity/reproduction/AG-PHOTONIC-003")
BASE = Path("results/opa-sys-005")
OUT = Path("results/opa-sys-006")
SEEDS = (42, 137, 2025)
EPOCHS = 120
BATCH = 64
LR = .008
TARGET = .90
# Original AG003 task, optimizer and dimensions; independent training code.
# Fixed preselected best system efficiency representative in each group.
GROUPS = ("Hybrid:4", "Hybrid:6", "MZI:6", "MRR:6",
          "IndepLaser_MZI:6", "IndepLaser_MZI:8")

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def quant(x, bits):
    if bits >= 32:
        return x
    maximum = float(np.max(np.abs(x)))
    if maximum == 0:
        return x
    scale = maximum / (2**(bits-1)-1)
    return (np.rint(x/scale)*scale).astype(x.dtype)

def mm(a,b,bits,sigma,drift,rng):
    y = quant(a,bits) @ quant(b,bits)
    if sigma or drift:
        rms = float(np.sqrt(np.mean(y*y)))
        y = y + (sigma*rng.standard_normal(y.shape)+drift)*rms
    return quant(y.astype(a.dtype),bits)

def initial(seed, dtype):
    rng = np.random.default_rng(seed+999)
    return [rng.normal(0,np.sqrt(2/8),(8,128)).astype(dtype),
            np.zeros(128,dtype=dtype),
            rng.normal(0,np.sqrt(2/128),(128,6)).astype(dtype),
            np.zeros(6,dtype=dtype)]

def forward(x,w,config,rng):
    bits,sigma,drift=config
    z=mm(x,w[0],bits,sigma,drift,rng)+w[1]
    h=np.maximum(z,0)
    y=mm(h,w[2],bits,sigma,drift,rng)+w[3]
    return z,h,y

def loss_delta(y,labels):
    z=y-y.max(axis=1,keepdims=True)
    exp=np.exp(z)
    p=exp/exp.sum(axis=1,keepdims=True)
    loss=float(np.mean(np.log(exp.sum(axis=1))-z[np.arange(len(labels)),labels]))
    p[np.arange(len(labels)),labels]-=1
    return loss,p/len(labels)

def grads(x,labels,w,config,rng):
    z,h,y=forward(x,w,config,rng)
    loss,d=loss_delta(y,labels)
    dz=mm(d,w[2].T,*config,rng)*(z>0)
    return loss,[x.T@dz,dz.sum(axis=0),h.T@d,d.sum(axis=0)]

def stream(seed,domain,epoch=0,batch=0):
    return np.random.default_rng(np.random.SeedSequence([seed,domain,epoch,batch]))

def evaluate(x,y,w,config,seed,epoch):
    # Same held-out noise stream for hybrid and digital-deploy comparisons.
    _,_,logits=forward(x,w,config,stream(seed,3,epoch))
    loss,_=loss_delta(logits,y)
    return loss,float(np.mean(logits.argmax(axis=1)==y))

def train(seed,data,batches,config,dtype):
    x,y,v,vy=data
    x=x.astype(dtype);v=v.astype(dtype)
    w=initial(seed,dtype)
    m=[np.zeros_like(p) for p in w]
    s=[np.zeros_like(p) for p in w]
    curves=[]
    t=0
    for ep,perm in enumerate(batches,1):
        losses=[]
        for k,start in enumerate(range(0,len(x),BATCH)):
            ids=perm[start:start+BATCH]
            loss,g=grads(x[ids],y[ids],w,config,stream(seed,2,ep,k))
            losses.append(loss)
            t+=1
            for i in range(len(w)):
                m[i]=.9*m[i]+.1*g[i]
                s[i]=.999*s[i]+.001*g[i]*g[i]
                w[i]-=LR*(m[i]/(1-.9**t))/(np.sqrt(s[i]/(1-.999**t))+1e-8)
        vl,acc=evaluate(v,vy,w,config,seed,ep)
        curves.append(dict(epoch=ep,train_loss=float(np.mean(losses)),val_loss=vl,val_acc=acc))
    # Require target at final epoch and record first sustained 5-epoch hit.
    hit=next((i+1 for i in range(EPOCHS-4) if all(c["val_acc"]>=TARGET for c in curves[i:i+5])),None)
    return w,curves,hit

def gradient_check():
    rng=stream(17,1)
    w=initial(17,np.float64)
    x=rng.normal(size=(12,8))
    y=rng.integers(0,6,12)
    cfg=(32,0.,0.)
    _,g=grads(x,y,w,cfg,rng)
    errs=[]
    for i,p in enumerate(w):
        d=rng.normal(size=p.shape);d/=np.linalg.norm(d)
        e=1e-5
        plus=[v.copy() for v in w];minus=[v.copy() for v in w]
        plus[i]+=e*d;minus[i]-=e*d
        lp=loss_delta(forward(x,plus,cfg,rng)[2],y)[0]
        lm=loss_delta(forward(x,minus,cfg,rng)[2],y)[0]
        errs.append(abs((lp-lm)/(2*e)-np.sum(g[i]*d)))
    return float(max(errs))

def main():
    sys.dont_write_bytecode=True
    verify=load("ag003_verify",ROOT/"import_snapshot.py")
    originals=verify.verify(ROOT/"original")
    frozen=[ROOT/"corrected/physics_model.py",ROOT/"stage2/physics_model.py",
            ROOT/"stage3/physics_model.py",BASE/"result.json",BASE/"optimized_feasible.json"]
    hashes={str(p):digest(p) for p in frozen}
    params=load("params",ROOT/"original/params.py")
    stage=load("ag003_stage3",ROOT/"stage3/physics_model.py")
    original=load("ag003_train",ROOT/"original/train_sim.py")
    provenance=json.loads((BASE/"provenance.json").read_text())
    archive_ok=all((BASE/n).stat().st_size==d["bytes"] and digest(BASE/n)==d["sha256"]
                   for n,d in provenance["files"].items())
    candidates=json.loads((BASE/"optimized_feasible.json").read_text())
    report=json.loads((BASE/"result.json").read_text())
    by_group=report["variants"]["optimized"]["best_by_arch_bits"]
    selected={k:by_group[k] for k in GROUPS}
    # Also choose maximum saturation headroom among six-bit comb candidates,
    # tie-break by source headroom then system efficiency.
    comb=[r for r in candidates if r["config"]["bits"]==6 and
          r["config"]["arch_type"] in ("MZI","MRR","Hybrid")]
    def headroom(r):
        d=r["gain_details"]
        return (1-d["booster_output_mw"]/d["saturation_limit_mw"],
                1-d["source_bank_mw"]/d["source_limit_mw"],r["metrics"]["eta_sys_topsw"])
    selected["comb6_headroom"]=max(comb,key=headroom)
    o=params.OPTICAL_PARAMS
    v=lambda k:o[k].val
    b=.7*params.SYSTEM_PARAMS["f_mod_ghz"].val*1e9
    band=v("comb_channel_spacing_ghz")*1e9
    cases={"digital_fp32":(32,0.,0.),"digital_fp64":(32,0.,0.)}
    for bits in (4,6,8):
        cases[f"quant_only_{bits}"]=(bits,0.,0.)
        cases[f"legacy_noise_{bits}"]=(bits,{4:.12,6:.05,8:.03}[bits],{4:.02,6:.01,8:.005}[bits])
    cases["legacy_high_drift"]=(6,.45,.15)
    links={}
    roots=True
    derating=[]
    for name,r in selected.items():
        d=r["gain_details"];cfg=r["config"]
        actual,terms=snr(d["rx_signal_mw"]*1e-3,v("pd_responsivity"),b,
            v("tia_noise_pa_rt_hz"),v("laser_rin_db_hz"),20.,
            d["rx_ase_mw"]*1e-3,band,params.Q_E)
        target=10**(r["metrics"]["target_snr_db"]/10)
        roots &= math.isclose(actual,target,rel_tol=1e-9)
        # Conditional normalized RMS receiver error, not a calibrated signed
        # optical transfer. Equal nominal SNR yields equal error proxy.
        sigma=1/math.sqrt(actual)
        links[name]=dict(candidate=r,snr_db=10*math.log10(actual),
            rms_noise=sigma,noise_terms_a2=terms,headroom=headroom(r)[0])
        # Quantized operands and output PLUS receiver noise: explicitly
        # separate converter and receiver errors, not measured total ENOB.
        for scale,drift,label in ((1.,0.,"nominal"),(3.,.01,"stress"),(10.,.05,"severe")):
            cases[name+"/"+label]=(cfg["bits"],sigma*scale,drift)
        for factor in (1.,.95,.90,.80):
            rr=stage.evaluate_config(**cfg,corrected_receiver=True,corrected_laser_limit=True,
                gain_policy="optimized",param_overrides={"amp_psat_mw":v("amp_psat_mw")*factor})
            derating.append(dict(candidate=name,saturation_factor=factor,feasible=rr["feasible"],
                reason=rr["reject_reason"],gain_db=rr.get("gain_details",{}).get("gain_db"),
                eta_sys_topsw=rr.get("metrics",{}).get("eta_sys_topsw")))
    rows=[];curves=[];pairs=[]
    for seed in SEEDS:
        # Reuse original teacher dataset; batch order has its own RNG and
        # is identical for every precision/noise case. No test-set tuning.
        data=original.make_dataset(seed)
        batches=[stream(seed,1,ep).permutation(len(data[0])) for ep in range(1,EPOCHS+1)]
        digital=None
        for name,cfg in cases.items():
            dtype=np.float64 if name=="digital_fp64" else np.float32
            w,history,hit=train(seed,data,batches,cfg,dtype)
            if name=="digital_fp32":
                digital=[p.copy() for p in w]
            last=history[-1]
            deploy_loss,deploy_acc=evaluate(data[2].astype(dtype),data[3],
                [p.astype(dtype) for p in digital],cfg,seed,EPOCHS)
            clean_loss,clean_acc=evaluate(data[2].astype(dtype),data[3],w,(32,0.,0.),seed,EPOCHS)
            row=dict(case=name,seed=seed,bits=cfg[0],noise_std=cfg[1],drift=cfg[2],
                final_val_acc=last["val_acc"],final_val_loss=last["val_loss"],
                final_train_loss=last["train_loss"],first_five_epoch_target=hit,
                converged=last["val_acc"]>=TARGET and hit is not None,
                digital_deploy_acc=deploy_acc,digital_deploy_loss=deploy_loss,
                clean_weight_acc=clean_acc,clean_weight_loss=clean_loss)
            rows.append(row)
            curves.extend(dict(case=name,seed=seed,**c) for c in history)
            pairs.append(dict(case=name,seed=seed,delta_vs_deploy=last["val_acc"]-deploy_acc))
            print(f"{seed} {name}: {last['val_acc']:.4f}",flush=True)
    summaries={}
    for name in cases:
        rr=[r for r in rows if r["case"]==name]
        summaries[name]=dict(mean_accuracy=float(np.mean([r["final_val_acc"] for r in rr])),
            min_accuracy=min(r["final_val_acc"] for r in rr),
            std_accuracy=float(np.std([r["final_val_acc"] for r in rr])),
            converged_all_seeds=all(r["converged"] for r in rr),
            mean_digital_deploy_acc=float(np.mean([r["digital_deploy_acc"] for r in rr])))
    err=gradient_check()
    checks=dict(archive_hashes=archive_ok,selected_from_archive=all(r in candidates for r in selected.values()),
        candidate_count=len(candidates)==2758 and len(comb)==152,
        receiver_roots=roots,gradient_finite_difference=err<1e-7,
        fp32_dtype=all(p.dtype==np.float32 for p in initial(42,np.float32)),
        ideal_matmul=np.array_equal(mm(np.eye(2),np.eye(2),32,0.,0.,stream(42,2)),np.eye(2)),
        paired_runs=len(rows)==len(cases)*len(SEEDS),
        complete_curves=len(curves)==len(rows)*EPOCHS,
        finite=all(math.isfinite(c["val_loss"]) and math.isfinite(c["train_loss"]) for c in curves),
        digital_learns=all(summaries[n]["mean_accuracy"]>.8 for n in ("digital_fp32","digital_fp64")),
        original_immutable=verify.verify(ROOT/"original")==originals,
        prior_stages_immutable=all(digest(Path(p))==h for p,h in hashes.items()))
    OUT.mkdir(parents=True,exist_ok=True)
    for name,records in (("metrics",rows),("learning_curves",curves),("paired_deploy",pairs),("derating",derating)):
        with (OUT/(name+".csv")).open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(records[0]))
            writer.writeheader();writer.writerows(records)
    result=dict(experiment="OPA-SYS-006",checks=checks,failures=[k for k,v in checks.items() if not v],
        seeds=SEEDS,epochs=EPOCHS,batch_size=BATCH,learning_rate=LR,target=TARGET,
        runs=len(rows),gradient_error=err,source_hashes=hashes,selected=links,
        summaries=summaries,derating=derating,
        limitations=["Original synthetic teacher task, 8-128-6 student; not a Transformer.",
            "Analog RMS error is conditional on normalized receiver SNR, not measured circuit transfer.",
            "Per-tensor dynamic quantization assumes ideal scaling, no calibration cost.",
            "Electronic ReLU, softmax, weight gradients and Adam; noisy backward activation MVM is a proxy.",
            "Architecture differences at equal bits/SNR are not resolved; no wavelength, mesh, tile or MRR-specific training simulation.",
            "Stress multipliers and common bias are assumptions, not measured drift; no out-of-band ASE or correlated noise.",
            "Derating is a separate re-optimized link feasibility test, not coupled to numerical training.",
            "No extrapolation of toy epochs or energy to system workload; no measured efficiency or matched electronic benchmark."])
    (OUT/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,allow_nan=False))
    if result["failures"]:
        raise SystemExit("failed checks: "+", ".join(result["failures"]))

if __name__=="__main__":
    main()
