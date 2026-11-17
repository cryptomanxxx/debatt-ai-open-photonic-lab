"""OPA-NL-002: balanced noisy XOR, passive coherent field cascade."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from nonlinear_activation_v001 import activation, contract, absorber

OUT=Path("results/opa-nl-002")
SEEDS=(1201,1202,1203,1204,1205)
DRIVES=(.1,1.,10.)
LOSSES=(0.,1.,3.)
STEPS=1500
BATCH=64
LR=.025
READOUT=16.
WIDTH=8
NOISE=(0.,.01,.03)
CORNERS=np.array([[-1,-1,1,1],[-1,1,-1,1]],dtype=float)

def dataset(seed,domain,n):
    rng=np.random.default_rng(np.random.SeedSequence([seed,domain]))
    ids=np.tile(np.arange(4),n//4)
    rng.shuffle(ids)
    # bounded jitter keeps quadrant labels exact, equally represented
    x=CORNERS[:,ids]+rng.uniform(-.2,.2,(2,n))
    y=(x[0]*x[1]<0).astype(int)
    # explicit coherent constant reference launched with inputs
    return np.vstack([x,np.ones(n)]),y

def transfer(z,kind,drive,loss,t=1.):
    if kind=="absorber":
        return activation(z,drive,loss,"absorber")
    if kind=="softsat":
        # Behavioral passive amplitude compression, not a device equation.
        q=drive*z*z
        a=np.sqrt(.85*10**(-loss/10))
        return a*z/np.sqrt(1+q),a/(1+q)**1.5
    if kind=="tanh":
        a=np.tanh(z)
        return a,1-a*a
    return z*t,np.full_like(z,t)

def forward(w,x,kind,drive,loss,t,noise=None):
    z=w[0]@x
    a,d=transfer(z,kind,drive,loss,t)
    if noise is not None:
        a=a+noise
    return z,a,d,w[1]@a

def ce_grad(f,y,scale):
    # signed coherent final field readout; no square-law classification
    s=scale*f.ravel()
    ce=np.mean(np.logaddexp(0,s)-y*s)
    p=1/(1+np.exp(-np.clip(s,-60,60)))
    return float(ce),((p-y)*scale/len(y))[None,:]

def train(w0,x,y,batches,kind,drive,loss,t):
    w=[v.copy() for v in w0]
    m=[np.zeros_like(v) for v in w];v=[a.copy() for a in m]
    curve=[]
    for step,idx in enumerate(batches,1):
        z,a,d,f=forward(w,x[:,idx],kind,drive,loss,t)
        ce,delta=ce_grad(f,y[idx],READOUT)
        g=[((w[1].T@delta)*d)@x[:,idx].T,delta@a.T]
        for i in range(2):
            m[i]=.9*m[i]+.1*g[i]
            v[i]=.999*v[i]+.001*g[i]**2
            w[i]=contract(w[i]-LR*(m[i]/(1-.9**step))/(np.sqrt(v[i]/(1-.999**step))+1e-8))
        if step==1 or step%50==0:
            curve.append((step,ce))
    return w,curve

def evaluate(w,x,y,kind,drive,loss,t,draw,noise):
    z,a,d,f=forward(w,x,kind,drive,loss,t,draw*noise)
    clean=transfer(z,kind,drive,loss,t)[0]
    powers=[drive*np.sum(q*q,axis=0) for q in (x,z,clean,w[1]@clean)]
    return dict(accuracy=float(np.mean((f.ravel()>0)==y)),
        raw_ce=ce_grad(f,y,1.)[0],scaled_ce=ce_grad(f,y,READOUT)[0],
        min_signed_margin=float(np.min((2*y-1)*f.ravel())),
        launch_mw=float(powers[0].mean()),reference_launch_mw=drive,
        activation_input_mw=float(powers[1].mean()),activation_output_mw=float(powers[2].mean()),
        output_mw=float(powers[3].mean()),peak_channel_mw=float(drive*np.max(z*z)),
        passivity_excess_mw=float(max(np.max(b-a) for a,b in zip(powers,powers[1:]))),
        spectral_norms=[float(np.linalg.norm(q,2)) for q in w])

def main():
    prior=Path("results/opa-nl-001/result.json")
    before=hashlib.sha256(prior.read_bytes()).hexdigest()
    rows=[];curves=[];truth=[];matches=[];checks={}
    # An affine classifier cannot label all four XOR corners correctly.
    # Enumerate all distinct affine labelings on the square via sign
    # patterns of integer coefficients including threshold ties.
    labels=(CORNERS[0]*CORNERS[1]<0)
    linmax=max(np.mean((a*CORNERS[0]+b*CORNERS[1]+c>0)==labels)
        for a in range(-3,4) for b in range(-3,4) for c in range(-6,7))
    checks["linear_corner_bound"]=bool(linmax==.75)
    e=np.linspace(-3,3,501);eps=1e-5
    for kind in ("absorber","softsat"):
        a,d=transfer(e,kind,1.,1.)
        fd=(transfer(e+eps,kind,1.,1.)[0]-transfer(e-eps,kind,1.,1.)[0])/(2*eps)
        checks[kind+"_derivative"]=bool(np.max(abs(d-fd))<1e-8)
        checks[kind+"_passive_odd"]=bool(np.all(abs(a)<=abs(e)+1e-12) and np.allclose(a,-a[::-1]))
    for seed in SEEDS:
        x,y=dataset(seed,1,1024);xt,yt=dataset(seed,2,2048)
        rng=np.random.default_rng(np.random.SeedSequence([seed,3]))
        w0=[contract(rng.normal(size=(WIDTH,3))*.4),contract(rng.normal(size=(1,WIDTH))*.4)]
        batches=[rng.choice(len(y),BATCH,replace=False) for _ in range(STEPS)]
        draw=np.random.default_rng(np.random.SeedSequence([seed,4])).normal(size=(WIDTH,len(yt)))
        def run(kind,drive,loss,t,w=None):
            if w is None:
                w,h=train(w0,x,y,batches,kind,drive,loss,t)
                curves.extend(dict(seed=seed,kind=kind,drive=drive,loss=loss,step=s,ce=c) for s,c in h)
            for n in NOISE:
                r=evaluate(w,xt,yt,kind,drive,loss,t,draw,n)
                rows.append(dict(seed=seed,kind=kind,drive_mw=drive,loss_db=loss,noise=n,linear_field_gain=t,**r))
            z,a,d,f=forward(w,np.vstack([CORNERS,np.ones(4)]),kind,drive,loss,t)
            truth.extend(dict(seed=seed,kind=kind,drive_mw=drive,loss_db=loss,x1=float(CORNERS[0,i]),x2=float(CORNERS[1,i]),target=int(labels[i]),field=float(f[0,i]),pred=int(f[0,i]>0)) for i in range(4))
            return w
        run("tanh",1.,0.,1.)
        run("linear",1.,0.,1.)
        for drive in DRIVES:
            for loss in LOSSES:
                for kind in ("absorber","softsat"):
                    w=run(kind,drive,loss,1.)
                    # Scalar attenuation matched on TRAINING fields of
                    # the trained nonlinear model, frozen before test.
                    z=w[0]@x
                    a=transfer(z,kind,drive,loss)[0]
                    t=float(np.sqrt(np.sum(a*a)/np.sum(z*z)))
                    matches.append(dict(seed=seed,kind=kind,drive_mw=drive,loss_db=loss,
                        field_gain=t,training_power_ratio=t*t))
                    run("matched_"+kind,drive,loss,t)
                    # Same weights with activation replaced by scalar:
                    # isolates shape without retraining.
                    run("ablate_"+kind,drive,loss,t,w=w)
        print("completed seed",seed,flush=True)
    checks.update(rows=len(rows)==5*56*3,curves=len(curves)==5*38*31,
        truth=len(truth)==5*56*4,matches=len(matches)==90,
        finite=all(np.isfinite(r["scaled_ce"]) and np.isfinite(r["output_mw"]) for r in rows),
        passivity=all(r["passivity_excess_mw"]<1e-9 and max(r["spectral_norms"])<=1+1e-12 for r in rows),
        prior_immutable=hashlib.sha256(prior.read_bytes()).hexdigest()==before)
    # Preregistered digital preflight and optical outcome; failure is scientific.
    def select(kind,drive,loss,noise):
        return [r for r in rows if (r["kind"],r["drive_mw"],r["loss_db"],r["noise"])==(kind,drive,loss,noise)]
    digital=select("tanh",1.,0.,0.)
    digital_pass=all(r["accuracy"]>=.99 for r in digital)
    nominal={}
    for kind in ("absorber","softsat"):
        a=select(kind,1.,1.,.01)
        b={r["seed"]:r for r in select("matched_"+kind,1.,1.,.01)}
        c={r["seed"]:r for r in select("ablate_"+kind,1.,1.,.01)}
        corners=[r for r in truth if r["kind"]==kind and r["drive_mw"]==1 and r["loss_db"]==1]
        nominal[kind]=dict(pass_gate=bool(digital_pass and all(r["accuracy"]>=.95 and
            r["accuracy"]-b[r["seed"]]["accuracy"]>=.15 and r["accuracy"]-c[r["seed"]]["accuracy"]>=.15
            for r in a) and all(r["target"]==r["pred"] for r in corners)),rows=a)
    report=dict(experiment="OPA-NL-002",checks=checks,failures=[k for k,v in checks.items() if not v],
        digital_preflight=digital_pass,linear_corner_bound=float(linmax),nominal=nominal,
        seeds=SEEDS,steps=STEPS,readout_scale=READOUT,rows=rows,loss_matches=matches,
        limitations=["Bounded synthetic XOR; independent train/test draws, not large AI training.",
            "Coherent signed amplitude and constant input reference; final phase-sensitive readout assumed.",
            "Two passive matrix contractions, no intermediate O/E/O, no actual mesh layout.",
            "Softsat is a behavioral amplitude compression function, not a calibrated device.",
            "Electronic projected Adam; fixed final electronic scale used in training for all policies.",
            "Matched attenuation is fitted on training fields of nonlinear weights, not pointwise equal loss.",
            "Noiseless power budget excludes hypothetical additive noise, receiver LO and electrical costs.",
            "No bandwidth, phase distortion, WDM, measured energy or physical cascade claim."])
    OUT.mkdir(parents=True,exist_ok=True)
    for name,records in (("metrics",rows),("learning_curves",curves),("truth_table",truth),("loss_matches",matches)):
        with (OUT/(name+".csv")).open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(records[0]))
            writer.writeheader();writer.writerows(records)
    (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(dict(experiment=report["experiment"],checks=checks,digital_preflight=digital_pass,nominal=nominal),indent=2))
    for p in sorted(OUT.iterdir()):
        if p.is_file(): print(p.name,p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest())
    if report["failures"]:raise SystemExit("implementation checks failed")

if __name__=="__main__":
    main()
