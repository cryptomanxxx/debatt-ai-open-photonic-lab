"""OPA-NL-003: independent XOR and conditional balanced homodyne receiver."""
import csv
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np
from nonlinear_activation_v002 import dataset, forward, train, transfer, contract, WIDTH, STEPS, BATCH

OUT = Path("results/opa-nl-003")
SEEDS = (1301,1302,1303,1304,1305)
DRIVES = (.1,1.)
LO = (.01,.1,1.)
BW = (.1,1.,7.)  # GHz equivalent noise bandwidth, not symbol rate
LOSS = (0.,3.)
PHASE = (0.,15.)
ABS_NOISE = (0.,.0031622776601683794,.01) # sqrt(mW)
Q = 1.602176634e-19
R = .9
TIA = 15e-12 # total differential input referred A/sqrt(Hz)
RIN = 10**(-145/10)
CMRR = 20.
WPE = .20
DIODE_CAP_MW = 2. # hypothetical, not a measured limit
REPEATS = 8

def constructive():
    # s=x1+x2. Opposite signs |s|<=.4, same signs |s|>=1.6.
    # g(s)=tanh(k*(1+s))+tanh(k*(1-s)), even and decreasing for s>0.
    w=np.zeros((WIDTH,3))
    w[:3]=[[1,1,1],[-1,-1,1],[0,0,1]]
    k=1/np.linalg.norm(w,2)
    w*=k
    g=lambda s: np.tanh(k*(1+s))+np.tanh(k*(1-s))
    threshold=(g(.4)+g(1.6))/2
    v=np.zeros((1,WIDTH))
    v[0,:3]=[1,1,-threshold/np.tanh(k)]
    v=contract(v)
    bound=float((g(.4)-g(1.6))/2*v[0,0])
    return [w,v],bound

def receiver(e_mw,lo_mw,bw_ghz,loss_db,phase_deg):
    # Signal complex-field amplitude in sqrt(mW), at MVM output.
    # LO power at hybrid input; signal-only downstream loss.
    e=e_mw*np.sqrt(10**(-loss_db/10))*np.exp(1j*np.deg2rad(phase_deg))
    ps=abs(e)**2*1e-3
    pl=lo_mw*1e-3
    b=bw_ghz*1e9
    # ideal lossless 50:50 coupler with phase-aligned LO
    pplus=abs(e*np.sqrt(1e-3)+np.sqrt(pl))**2/2
    pminus=abs(e*np.sqrt(1e-3)-np.sqrt(pl))**2/2
    current=R*(pplus-pminus)
    shot=2*Q*R*(ps+pl)*b
    thermal=np.full_like(ps,TIA**2*b)
    # Approximate residual LO common-mode RIN; no signal RIN/ASE.
    rin=np.full_like(ps,(R*pl)**2*RIN*10**(-CMRR/10)*b)
    sigma=np.sqrt(shot+thermal+rin)
    return current,sigma,ps,pplus,pminus,shot,thermal,rin

def rng(seed,domain):
    return np.random.default_rng(np.random.SeedSequence([seed,domain]))

def accuracy(e,y):
    return float(np.mean((e>0)==y))

def main():
    prior=Path("results/opa-nl-002/result.json")
    before=hashlib.sha256(prior.read_bytes()).hexdigest()
    if before!="f8bcd3bccb91123d9654d9f5ea16e7825df596ed36b186f303ecbd0be02f7786":
        raise ValueError("NL002 archive digest mismatch")
    wref,bound=constructive()
    checks={"analytic_positive_bound":bool(bound>0)}
    grid=np.linspace(-.2,.2,41)
    test=np.array([(a+u,b+v,1.) for a,b in itertools.product((-1.,1.),repeat=2)
                   for u,v in itertools.product(grid,repeat=2)]).T
    ygrid=test[0]*test[1]<0
    fg=forward(wref,test,"tanh",1.,0.,1.)[-1].ravel()
    checks["constructive_grid_margin"]=bool(np.min((2*ygrid.astype(int)-1)*fg)>=bound-1e-12)
    # Independent receiver identities, sign reversal, variance monotonicity.
    e=np.array([-.03,0.,.03])
    i,s,p,pp,pm,*_=receiver(e,.1,1.,0.,0.)
    checks["hybrid_power_conservation"]=bool(np.allclose(pp+pm,p+.1e-3,rtol=1e-12,atol=1e-18))
    checks["homodyne_signed_current"]=bool(np.allclose(i,2*R*e*np.sqrt(.1)*1e-3,atol=1e-18))
    checks["bandwidth_scaling"]=bool(np.allclose(receiver(e,.1,7.,0.,0.)[1],np.sqrt(7)*s))
    checks["zero_signal_zero_mean"]=bool(i[1]==0 and s[1]>0)
    checks["phase_projection"]=bool(np.allclose(receiver(e,.1,1.,0.,90.)[0],0,atol=1e-17))
    rows=[];refs=[];weights=[];curves=[];paired=[]
    for seed in SEEDS:
        x,y=dataset(seed,11,1024);xt,yt=dataset(seed,12,2048)
        rg=rng(seed,13)
        w0=[contract(rg.normal(size=(WIDTH,3))*.4),contract(rg.normal(size=(1,WIDTH))*.4)]
        batches=[rg.choice(len(y),BATCH,replace=False) for _ in range(STEPS)]
        draw=rng(seed,14).normal(size=(REPEATS,WIDTH,len(yt)))
        rxdraw=rng(seed,15).normal(size=(REPEATS,len(yt)))
        trained,h=train(w0,x,y,batches,"tanh",1.,0.,1.)
        for name,w in (("constructive",wref),("trained",trained)):
            f=forward(w,xt,"tanh",1.,0.,1.)[-1].ravel()
            refs.append(dict(seed=seed,policy=name,accuracy=accuracy(f,yt),
                min_margin=float(np.min((2*yt-1)*f))))
            weights.append(dict(seed=seed,kind="tanh_"+name,drive_mw=1.,
                w1=w[0].tolist(),w2=w[1].tolist()))
        curves.extend(dict(seed=seed,kind="tanh",drive_mw=1.,step=s,ce=c) for s,c in h)
        for kind,drive in itertools.product(("absorber","softsat"),DRIVES):
            w,h=train(w0,x,y,batches,kind,drive,1.,1.)
            weights.append(dict(seed=seed,kind=kind,drive_mw=drive,w1=w[0].tolist(),w2=w[1].tolist()))
            curves.extend(dict(seed=seed,kind=kind,drive_mw=drive,step=s,ce=c) for s,c in h)
            z,a,_,f=forward(w,xt,kind,drive,1.,1.)
            f=f.ravel()
            eclean=f*np.sqrt(drive)
            ztrain=w[0]@x
            atrain=transfer(ztrain,kind,drive,1.)[0]
            gain=float(np.sqrt(np.sum(atrain**2)/np.sum(ztrain**2)))
            wl,h=train(w0,x,y,batches,"linear",drive,1.,gain)
            weights.append(dict(seed=seed,kind="matched_"+kind,drive_mw=drive,w1=wl[0].tolist(),w2=wl[1].tolist()))
            curves.extend(dict(seed=seed,kind="matched_"+kind,drive_mw=drive,step=s,ce=c) for s,c in h)
            fl=forward(wl,xt,"linear",drive,1.,gain)[-1].ravel()
            fa=forward(w,xt,"linear",drive,1.,gain)[-1].ravel()
            paired.append(dict(seed=seed,kind=kind,drive_mw=drive,
                clean_accuracy=accuracy(f,yt),matched_accuracy=accuracy(fl,yt),
                ablation_accuracy=accuracy(fa,yt),matched_gain=gain,
                normalized_noise_accuracy=accuracy(f[None,:]+.01*np.einsum("ij,rjn->rin",w[1],draw)[:,0,:],yt),
                launch_mw=float(drive*np.mean(np.sum(xt**2,axis=0))),
                output_mean_uw=float(np.mean(eclean**2)*1000),
                output_min_uw=float(np.min(eclean**2)*1000),
                min_signed_field_sqrt_mw=float(np.min((2*yt-1)*eclean)),
                passivity_excess_mw=float(max(np.max(v-u) for u,v in zip(
                    [drive*np.sum(xt**2,axis=0),drive*np.sum(z**2,axis=0),drive*np.sum(a**2,axis=0)],
                    [drive*np.sum(z**2,axis=0),drive*np.sum(a**2,axis=0),eclean**2])))))
            for an,lo,bw,loss,phase in itertools.product(ABS_NOISE,LO,BW,LOSS,PHASE):
                # Fixed absolute activation-output noise; same draws across cases.
                e=eclean[None,:]+an*np.einsum("ij,rjn->rin",w[1],draw)[:,0,:]
                current,sigma,ps,pp,pm,shot,thermal,rin=receiver(e,lo,bw,loss,phase)
                sensed=current+sigma*rxdraw
                margin=(2*yt-1)*current/sigma
                # Empirical errors include 8 paired realizations per example.
                rows.append(dict(seed=seed,kind=kind,drive_mw=drive,abs_noise_sqrt_mw=an,
                    lo_mw=lo,bw_ghz=bw,downstream_loss_db=loss,phase_deg=phase,
                    accuracy=accuracy(sensed,yt),
                    worst_repeat_accuracy=float(np.min(np.mean((sensed>0)==yt,axis=1))),
                    pre_receiver_accuracy=accuracy(e,yt),
                    min_signed_current_sigma=float(np.min(margin)),
                    mean_signal_uw=float(np.mean(ps)*1e6),
                    min_signal_uw=float(np.min(ps)*1e6),
                    peak_diode_mw=float(max(np.max(pp),np.max(pm))*1e3),
                    diode_cap_pass=bool(max(np.max(pp),np.max(pm))*1e3<=DIODE_CAP_MW),
                    mean_shot_a2=float(np.mean(shot)),mean_tia_a2=float(np.mean(thermal)),
                    mean_rin_a2=float(np.mean(rin)),
                    lo_electric_lower_mw=lo/WPE,
                    signal_plus_lo_electric_lower_mw=(drive*np.mean(np.sum(xt**2,axis=0))+lo)/WPE))
        print("completed seed",seed,flush=True)
    checks.update(rows=len(rows)==2160,paired=len(paired)==20,refs=len(refs)==10,
        weights=len(weights)==50,curves=len(curves)==1395,
        finite=all(np.isfinite(r["min_signed_current_sigma"]) for r in rows),
        passive=all(r["passivity_excess_mw"]<=1e-9 for r in paired),
        norm=all(np.linalg.norm(np.array(w[k]),2)<=1+1e-12 for w in weights for k in ("w1","w2")),
        prior_immutable=hashlib.sha256(prior.read_bytes()).hexdigest()==before)
    digital=all(r["accuracy"]>=.99 for r in refs if r["policy"]=="constructive")
    # Fixed predeclared receiver point: 0.1 mW LO, 1 GHz ENBW,
    # 3 dB downstream loss, 15 deg phase offset, .003162 sqrt(mW) noise.
    nominal=[r for r in rows if r["lo_mw"]==.1 and r["bw_ghz"]==1.
        and r["downstream_loss_db"]==3. and r["phase_deg"]==15.
        and r["abs_noise_sqrt_mw"]==ABS_NOISE[1]]
    gates={}
    for kind,drive in itertools.product(("absorber","softsat"),DRIVES):
        rr=[r for r in nominal if r["kind"]==kind and r["drive_mw"]==drive]
        pp=[r for r in paired if r["kind"]==kind and r["drive_mw"]==drive]
        gates[f"{kind}_{drive}"]=bool(digital and len(rr)==5 and all(
            r["worst_repeat_accuracy"]>=.95 and r["diode_cap_pass"] for r in rr)
            and all(r["clean_accuracy"]>=.95 and
            r["clean_accuracy"]-r["matched_accuracy"]>=.15 and
            r["clean_accuracy"]-r["ablation_accuracy"]>=.15 for r in pp))
    result=dict(experiment="OPA-NL-003",checks=checks,failures=[k for k,v in checks.items() if not v],
        analytic_margin_bound=bound,digital_constructive_preflight=digital,refs=refs,
        nominal=nominal,gates=gates,paired=paired,receiver_rows=len(rows),
        assumptions=dict(responsivity_a_w=R,tia_pa_rt_hz=TIA*1e12,rin_db_hz=-145,
            cmrr_db=CMRR,wpe=WPE,diode_cap_mw=DIODE_CAP_MW,repeats=REPEATS),
        limitations=["Conditional static field model and ideal balanced hybrid, not measured hardware.",
            "TIA is total differential noise; residual LO RIN approximation, no ASE or signal RIN.",
            "Gaussian independent sample approximation, no pulse waveform, timing, ADC, phase-lock energy or bandwidth validation.",
            "Absolute activation noise hypothetical; noise power excluded from clean passivity.",
            "LO and signal laser electrical lower bound assumes lossless distribution and fixed WPE.",
            "Constructive electronic tanh reference does not validate a physical optical tanh device.",
            "No optical backward pass, material calibration or system efficiency claim."])
    OUT.mkdir(parents=True,exist_ok=True)
    for name,data in (("receiver",rows),("paired",paired),("references",refs),("learning_curves",curves)):
        with (OUT/(name+".csv")).open("w",newline="") as f:
            wr=csv.DictWriter(f,fieldnames=list(data[0]));wr.writeheader();wr.writerows(data)
    (OUT/"weights.json").write_text(json.dumps(weights,indent=2,allow_nan=False)+"\n")
    (OUT/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,allow_nan=False))
    for p in sorted(OUT.iterdir()):
        if p.is_file(): print(p.name,p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest())
    if result["failures"]: raise SystemExit("implementation checks failed")

if __name__=="__main__":main()
