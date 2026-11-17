"""OPA-NL-001: passive saturable absorption between coherent linear layers.

Field model, not electromagnetic simulation or fabricated hardware.
"""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np

OUT = Path("results/opa-nl-001")
SEEDS = (707, 708, 709)
N = 128
STEPS = 32
BATCH = 64
LR = .12
# Hypothetical power-domain parameters; not fitted to a specific device.
PSAT_MW = 1.
T_LOW, T_HIGH = .15, .85
DRIVES = (.1, 1., 10.)
LOSSES = (0., 1., 3.)
NOISE = (0., .01, .03)
# Fixed global input scaling from train set only, with no per-example rescaling.

def stream(seed, domain):
    return np.random.default_rng(np.random.SeedSequence([seed,domain]))

def contract(w):
    # Passive matrix represented by normalized SVD, no gain or per-vector scaling.
    return w/max(1.,float(np.linalg.norm(w,2)))

def absorber(e,psat,loss):
    # e is complex field in sqrt(mW); P=|e|^2 in mW.
    # Saturable loss decreases monotonically as input power rises.
    p=np.abs(e)**2
    t=10**(-loss/10)*(T_HIGH-(T_HIGH-T_LOW)/(1+p/psat))
    return e*np.sqrt(t)

def activation(z,drive,loss,kind):
    if kind=="linear":
        return z,np.ones_like(z)
    if kind=="tanh":
        a=np.tanh(z)
        return a,1-a*a
    # Real coherent signed amplitude (phase 0/pi), zero bias.
    # Derivative for real field; no detection/re-encoding.
    q=drive*z*z/PSAT_MW
    l=10**(-loss/10)
    t=l*(T_HIGH-(T_HIGH-T_LOW)/(1+q))
    dt_dz=l*(T_HIGH-T_LOW)*2*drive*z/PSAT_MW/(1+q)**2
    return z*np.sqrt(t),np.sqrt(t)+z*dt_dz/(2*np.sqrt(t))

def loss_delta(logits,y):
    z=logits[:4]-logits[:4].max(axis=0)
    ex=np.exp(z);den=ex.sum(axis=0)
    loss=float(np.mean(np.log(den)-z[y,np.arange(len(y))]))
    p=ex/den;p[y,np.arange(len(y))]-=1
    d=np.zeros_like(logits);d[:4]=p/len(y)
    return loss,d

def forward(w,x,kind,drive,loss,noise,draw):
    # Both optical layers are contractions. Fixed scalar input drive
    # is applied at launch; no normalization or gain between layers.
    z=w[0]@x
    a,der=activation(z,drive,loss,kind)
    # Field perturbation in normalized units, hypothetical fixed absolute scale.
    a=a+noise*draw
    logits=w[1]@a
    return z,a,der,logits

def train(w0,data,kind,drive,loss,noise,seed):
    x,y,xt,yt,batches=data
    w=[v.copy() for v in w0]
    curve=[]
    for step,idx in enumerate(batches):
        draw=stream(seed,100+step).normal(size=(N,len(idx)))
        z,a,der,logits=forward(w,x[:,idx],kind,drive,loss,noise,draw)
        ce,d=loss_delta(logits,y[idx])
        g2=d@a.T;g1=((w[1].T@d)*der)@x[:,idx].T
        # Projected electronic SGD; no claim of optical weight updates.
        w=[contract(w[0]-LR*g1),contract(w[1]-LR*g2)]
        curve.append(ce)
    return w,curve

def metric(w,data,kind,drive,loss,noise,seed):
    _,_,x,y,_=data
    draw=stream(seed,999).normal(size=(N,x.shape[1]))
    z,a,_,logits=forward(w,x,kind,drive,loss,noise,draw)
    ce,_=loss_delta(logits,y)
    # Physical optical powers only for the passive absorber, without noise.
    e0=np.sqrt(drive)*x
    e1=np.sqrt(drive)*z
    e2=absorber(e1,PSAT_MW,loss) if kind=="absorber" else None
    power={}
    if e2 is not None:
        e3=w[1]@e2
        totals=[np.sum(abs(e)**2,axis=0) for e in (e0,e1,e2,e3)]
        power=dict(launch_mean_mw=float(totals[0].mean()),
            activation_input_mean_mw=float(totals[1].mean()),
            activation_output_mean_mw=float(totals[2].mean()),
            second_mvm_output_mean_mw=float(totals[3].mean()),
            activation_input_peak_channel_mw=float(np.max(abs(e1)**2)),
            activation_loss_db=float(-10*np.log10(totals[2].sum()/totals[1].sum())),
            max_passivity_excess_mw=float(max(np.max(b-a) for a,b in zip(totals,totals[1:]))))
    return dict(loss=ce,accuracy=float(np.mean(logits[:4].argmax(axis=0)==y)),**power)

def controls():
    e=np.linspace(-5,5,1001)
    complex_e=e*np.exp(1j*.71)
    a=absorber(e,PSAT_MW,1.)
    ac=absorber(complex_e,PSAT_MW,1.)
    real,der=activation(e,1.,1.,"absorber")
    eps=1e-5
    fd=(activation(e+eps,1.,1.,"absorber")[0]-activation(e-eps,1.,1.,"absorber")[0])/(2*eps)
    return dict(field_passive=bool(np.all(abs(ac)<=abs(complex_e)+1e-12)),
        odd_signed_field=bool(np.allclose(a,-a[::-1])),
        phase_equivariant=bool(np.allclose(ac,a*np.exp(1j*.71))),
        field_mapping=bool(np.allclose(real,a)),
        derivative=bool(np.max(abs(fd-der))<1e-8),
        nonlinear=bool(abs(absorber(np.array([2.]),1.,0.)[0]-2*absorber(np.array([1.]),1.,0.)[0])>.01),
        zero_input=bool(absorber(np.array([0j]),1.,0.)[0]==0))

def main():
    # Import exact MOD-007 dataset and calibration constant rather than
    # trusting a duplicated RNG sequence. No expensive mesh run.
    from modular_multilayer_v007 import dataset as mod_dataset
    checks=controls();rows=[];curves=[];transfer=[]
    for drive in DRIVES:
        for loss in LOSSES:
            for x in np.linspace(-4,4,161):
                y,d=activation(np.array([x]),drive,loss,"absorber")
                transfer.append(dict(drive_mw=drive,loss_db=loss,input_field=x,
                    output_field=float(y[0]),input_mw=drive*x*x,
                    output_mw=drive*y[0]**2,derivative=float(d[0])))
    for seed in SEEDS:
        x,y,xt,yt,_,batches=mod_dataset(seed)
        # Fixed input amplitude normalization from training only.
        scale=float(np.sqrt(np.mean(x*x)))
        data=x/scale,y,xt/scale,yt,batches
        rng=np.random.default_rng(seed+20000)
        w0=[contract(rng.normal(size=(N,N))/np.sqrt(N)) for _ in range(2)]
        digital,curve=train(w0,data,"tanh",1.,0.,0.,seed)
        for kind,drive,loss,noise in [("linear",1.,0.,0.),("tanh",1.,0.,0.)]+[
            ("absorber",d,l,n) for d in DRIVES for l in LOSSES for n in NOISE]:
            w,h=train(w0,data,kind,drive,loss,noise,seed)
            for policy,weights in (("matched_training",w),("tanh_deploy",digital)):
                result=metric(weights,data,kind,drive,loss,noise,seed)
                rows.append(dict(seed=seed,kind=kind,drive_mw=drive,loss_db=loss,noise_std=noise,
                    policy=policy,**result))
            curves.extend(dict(seed=seed,kind=kind,drive_mw=drive,loss_db=loss,
                noise_std=noise,step=i+1,loss=v) for i,v in enumerate(h))
        print("completed seed",seed,flush=True)
    passive=[r for r in rows if r["kind"]=="absorber"]
    checks.update(row_count=len(rows)==174,curve_count=len(curves)==2784,
        transfer_count=len(transfer)==1449,
        finite=all(np.isfinite(r["loss"]) and np.isfinite(r["accuracy"]) for r in rows),
        passive_chain=all(r["max_passivity_excess_mw"]<1e-9 for r in passive))
    # Scientific outcome: report, not a CI gate. Preselected nominal
    # candidate: drive=1, loss=1, noise=0.01. No post-hoc winner claims.
    nominal=[r for r in rows if r["kind"]=="absorber" and r["drive_mw"]==1
        and r["loss_db"]==1 and r["noise_std"]==.01 and r["policy"]=="matched_training"]
    linear=[r for r in rows if r["kind"]=="linear" and r["policy"]=="matched_training"]
    tanh=[r for r in rows if r["kind"]=="tanh" and r["policy"]=="matched_training"]
    byseed=lambda rs:{r["seed"]:r for r in rs}
    lb,tb=byseed(linear),byseed(tanh)
    comparison=[dict(seed=r["seed"],delta_accuracy_vs_linear=r["accuracy"]-lb[r["seed"]]["accuracy"],
        delta_accuracy_vs_tanh=r["accuracy"]-tb[r["seed"]]["accuracy"],
        delta_loss_vs_linear=r["loss"]-lb[r["seed"]]["loss"]) for r in nominal]
    result=dict(experiment="OPA-NL-001",checks=checks,failures=[k for k,v in checks.items() if not v],
        seeds=SEEDS,steps=STEPS,psat_mw=PSAT_MW,transmission_low=T_LOW,transmission_high=T_HIGH,
        rows=rows,nominal_comparison=comparison,
        hypothesis_pass=all(r["delta_loss_vs_linear"]<0 and r["delta_accuracy_vs_linear"]>0
            and r["delta_accuracy_vs_tanh"]>=-.05 for r in comparison),
        limitations=["Hypothetical static saturable absorber, not fitted to a device or measured bandwidth.",
            "Coherent signed field; assumes real passive contractions and ideal phase preservation.",
            "No intermediate detection or re-encoding in modeled absorber path; no actual optical routing.",
            "Electronic training and final readout; no physical backward pass.",
            "Power values are conditional ideal field powers, not wall-plug energy; no laser, driver, coupling or thermal budget.",
            "Single wavelength only; no WDM cross-saturation, carrier dynamics or phase distortion.",
            "Noise is an illustrative field perturbation, excluded from noiseless passivity accounting.",
            "Synthetic MOD-007 data; 32 updates, three seeds; not LLM training or hardware speed."])
    OUT.mkdir(parents=True,exist_ok=True)
    for name,records in (("metrics",rows),("learning_curves",curves),("transfer",transfer)):
        with (OUT/(name+".csv")).open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in records for k in r)))
            writer.writeheader();writer.writerows(records)
    (OUT/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,allow_nan=False))
    for p in sorted(OUT.glob("*")):
        if p.is_file():print(p.name,p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest())
    if result["failures"]:raise SystemExit("implementation checks failed")

if __name__=="__main__":
    main()
