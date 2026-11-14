"""OPA-MOD-007: nonlinear multilayer classification, hybrid optical forward.

Digital straight-through backward; no physical or energy-performance claims.
"""
import csv
import json
from pathlib import Path
import sys

import numpy as np

from modular_power_budget_v002 import N
from modular_imperfections_v003 import prepare, SCENARIOS, LOSSES
from modular_calibration_v004 import hardware
from modular_training_v006 import optical, CAL_COUNT

OUT = Path("results/opa-mod-007")
SEEDS = (707, 708, 709)
DEPTHS = (2, 3)
SIZES = (16, 64, 128)
SCENES = ("combined_low", "combined_high")
CLASSES = 4
STEPS = 32
BATCH = 64
LR = 0.12
TEST_COUNT = 256
TOL = 1e-9


def init(rng, depth):
    # Square layers compatible with MOD-003/004, last four-class readout
    # is a fixed electronic selection of the first four output coordinates.
    return [rng.normal(size=(N,N))/np.sqrt(N) for _ in range(depth)]


def forward(weights, x, multiply=None):
    activations = [x]
    for i,w in enumerate(weights):
        z = w @ activations[-1] if multiply is None else multiply(i,w,activations[-1])
        activations.append(np.tanh(z) if i < len(weights)-1 else z)
    return activations


def loss_and_delta(logits, labels):
    z = logits[:CLASSES]
    shifted = z - z.max(axis=0,keepdims=True)
    logsum = np.log(np.exp(shifted).sum(axis=0))
    loss = float(np.mean(logsum-shifted[labels,np.arange(len(labels))]))
    p = np.exp(shifted-logsum)
    p[labels,np.arange(len(labels))] -= 1
    delta = np.zeros_like(logits)
    delta[:CLASSES] = p / len(labels)
    return loss, delta


def gradients(weights, activations, labels):
    loss, delta = loss_and_delta(activations[-1],labels)
    grads = []
    for i in reversed(range(len(weights))):
        grads.append(delta @ activations[i].T)
        if i:
            delta = (weights[i].T @ delta)*(1-activations[i]**2)
    return loss, list(reversed(grads))


def metric(logits, labels):
    loss,_ = loss_and_delta(logits,labels)
    return loss, float(np.mean(np.argmax(logits[:CLASSES],axis=0)==labels))


def dataset(seed):
    rng = np.random.default_rng(seed)
    # Nonlinear teacher with a low-dimensional informative subspace;
    # independent Gaussian samples and balanced-in-expectation class logits.
    teacher = rng.normal(size=(16,8))
    readout = rng.normal(size=(CLASSES,16))
    def sample(count):
        x = rng.normal(size=(N,count))
        y = np.argmax(readout @ np.tanh(teacher @ x[:8]/np.sqrt(8)),axis=0)
        return x,y
    train,ytrain = sample(1024)
    test,ytest = sample(TEST_COUNT)
    probes = rng.normal(size=(N,CAL_COUNT))
    batches = [rng.choice(train.shape[1],BATCH,replace=False) for _ in range(STEPS)]
    return train,ytrain,test,ytest,probes,batches


def gradient_control():
    rng = np.random.default_rng(700)
    w = init(rng,3)
    x = rng.normal(size=(N,8))
    y = rng.integers(CLASSES,size=8)
    _,g = gradients(w,forward(w,x),y)
    errors = []
    for i in range(len(w)):
        direction = rng.normal(size=w[i].shape)
        direction /= np.linalg.norm(direction)
        eps = 1e-5
        plus = [v.copy() for v in w]
        minus = [v.copy() for v in w]
        plus[i] += eps*direction
        minus[i] -= eps*direction
        fd = (metric(forward(plus,x)[-1],y)[0]-metric(forward(minus,x)[-1],y)[0])/(2*eps)
        errors.append(float(abs(fd-np.sum(g[i]*direction))))
    return max(errors)


def train_model(w0, data, multiply, record):
    train,ytrain,_,_,_,batches = data
    w = [v.copy() for v in w0]
    for step,ids in enumerate(batches):
        x,y = train[:,ids],ytrain[ids]
        a = forward(w,x,None if multiply is None else multiply(step))
        loss,g = gradients(w,a,y)
        record(step,loss)
        w = [v-LR*d for v,d in zip(w,g)]
    return w


def optical_factory(b, hw, params, local, probes, seed, diag):
    def for_step(step):
        def multiply(layer,w,x):
            # Independent receiver noise by layer and step, paired across policies.
            rng = np.random.default_rng(np.random.SeedSequence([seed,step,layer]))
            y,d = optical(w,x,b,hw[layer],params,LOSSES["moderate"],local,probes,rng)
            diag.append(d)
            return y
        return multiply
    return for_step


def main():
    rows,curves,comparisons,controls,layer_errors = [],[],[],[],[]
    baselines = []
    grad_error = gradient_control()
    if grad_error >= 1e-7:
        raise RuntimeError("Digital gradient finite-difference check failed")
    for seed in SEEDS:
        data = dataset(seed)
        _,_,test,ytest,probes,_ = data
        for depth in DEPTHS:
            w0 = init(np.random.default_rng(seed+depth*10000),depth)
            initial_loss,initial_acc = metric(forward(w0,test)[-1],ytest)
            def record(step,loss):
                curves.append(dict(seed=seed,depth=depth,tile_size=0,scenario="digital",
                                   method="digital",step=step,train_loss=loss))
            digital = train_model(w0,data,None,record)
            ce,acc = metric(forward(digital,test)[-1],ytest)
            rows.append(dict(seed=seed,depth=depth,tile_size=0,scenario="digital",
                             method="digital",initial_loss=initial_loss,initial_accuracy=initial_acc,
                             test_loss=ce,test_accuracy=acc,digital_weight_loss=ce,
                             digital_weight_accuracy=acc,passive_excess=0.,clips=0,
                             calibration_vectors=0,mean_detected_power=None))
            baselines.append((seed,depth,data,w0,digital,initial_loss,initial_acc))
    if not all(np.isfinite(r["test_loss"]) and r["test_loss"] < r["initial_loss"] for r in rows):
        raise RuntimeError("Digital baseline preflight failed")
    print("Digital preflight:", [(r["seed"],r["depth"],r["initial_loss"],r["test_loss"],r["test_accuracy"]) for r in rows],flush=True)
    if "--digital-only" in sys.argv:
        return 0
    for seed,depth,data,w0,digital,initial_loss,initial_acc in baselines:
        _,_,test,ytest,probes,_ = data
        for b in SIZES:
            hw = [hardware(prepare(w,b),np.random.default_rng(
                  np.random.SeedSequence([seed,b,layer]))) for layer,w in enumerate(w0)]
            diag = []
            ideal = optical_factory(b,hw,SCENARIOS["ideal"],False,probes,seed,diag)
            expected = forward(w0,test[:,:8])
            actual = forward(w0,test[:,:8],ideal(999))
            controls.append(max(float(np.max(abs(a-e))) for a,e in zip(actual,expected)))
            for scene in SCENES:
                for local in (False,True):
                    label = "calibrated" if local else "uncalibrated"
                    diag = []
                    factory = optical_factory(b,hw,SCENARIOS[scene],local,probes,seed,diag)
                    def record(step,loss):
                        curves.append(dict(seed=seed,depth=depth,tile_size=b,scenario=scene,
                                           method="hybrid_"+label,step=step,train_loss=loss))
                    hybrid = train_model(w0,data,factory,record)
                    train_diag = list(diag)
                    pair = []
                    for method,w in (("digital_deploy_"+label,digital),("hybrid_"+label,hybrid)):
                        diag.clear()
                        ideal_a = forward(w,test)
                        a = forward(w,test,factory(999))
                        ce,acc = metric(a[-1],ytest)
                        dc,da = metric(ideal_a[-1],ytest)
                        history = (train_diag if method.startswith("hybrid") else [])+list(diag)
                        row = dict(seed=seed,depth=depth,tile_size=b,scenario=scene,method=method,
                                   initial_loss=initial_loss,initial_accuracy=initial_acc,
                                   test_loss=ce,test_accuracy=acc,digital_weight_loss=dc,
                                   digital_weight_accuracy=da,
                                   passive_excess=max(d["passive_excess"] for d in history),
                                   clips=sum(d["clips"] for d in history),
                                   calibration_vectors=sum(d["calibration_vectors"] for d in history),
                                   mean_detected_power=float(np.mean([d["mean_detected_power"] for d in diag])))
                        rows.append(row)
                        pair.append(row)
                        for layer,(ref,obs) in enumerate(zip(ideal_a[1:],a[1:]),1):
                            layer_errors.append(dict(seed=seed,depth=depth,tile_size=b,scenario=scene,
                                method=method,layer=layer,relative_activation_error=float(
                                    np.linalg.norm(obs-ref)/max(np.linalg.norm(ref),1e-30))))
                    comparisons.append(dict(seed=seed,depth=depth,tile_size=b,scenario=scene,
                        calibration=label,digital_deploy_loss=pair[0]["test_loss"],
                        hybrid_loss=pair[1]["test_loss"],delta_loss=pair[1]["test_loss"]-pair[0]["test_loss"],
                        digital_deploy_accuracy=pair[0]["test_accuracy"],hybrid_accuracy=pair[1]["test_accuracy"],
                        delta_accuracy=pair[1]["test_accuracy"]-pair[0]["test_accuracy"]))
    groups = len(SEEDS)*len(DEPTHS)*len(SIZES)*len(SCENES)
    checks = {
        "digital_gradient_finite_difference": grad_error<1e-7,
        "digital_preflight": all(r["test_loss"]<r["initial_loss"] for r in rows if r["method"]=="digital"),
        "ideal_multilayer_forward": max(controls)<TOL,
        "all_rows": len(rows)==len(SEEDS)*len(DEPTHS)+groups*4,
        "all_curves": len(curves)==STEPS*(len(SEEDS)*len(DEPTHS)+groups*2),
        "all_pairs": len(comparisons)==groups*2,
        "all_layer_errors": len(layer_errors)==len(SEEDS)*sum(DEPTHS)*len(SIZES)*len(SCENES)*4,
        "finite_metrics": all(np.isfinite(r["test_loss"]) and np.isfinite(r["digital_weight_loss"])
                              and 0<=r["test_accuracy"]<=1 for r in rows)
                          and all(np.isfinite(r["train_loss"]) for r in curves)
                          and all(np.isfinite(r["relative_activation_error"]) for r in layer_errors),
        "passivity": all(r["passive_excess"]<TOL for r in rows),
        "calibration_accounting": all(r["calibration_vectors"]==r["depth"]*CAL_COUNT*(
            STEPS+1 if r["method"]=="hybrid_calibrated" else 1 if r["method"]=="digital_deploy_calibrated" else 0)
            for r in rows),
    }
    report = dict(experiment="OPA-MOD-007",numpy_version=np.__version__,
        config=dict(n=N,depths=DEPTHS,tile_sizes=SIZES,seeds=SEEDS,scenarios=SCENES,
                    steps=STEPS,batch=BATCH,learning_rate=LR,classes=CLASSES,
                    train_count=1024,test_count=TEST_COUNT,calibration_count=CAL_COUNT),
        assumptions=["Synthetic nonlinear classification, not a real dataset.",
          "Square optical layers, electronic tanh, first four final outputs used as class logits.",
          "Digital straight-through gradients ignore optical programming derivatives.",
          "Fixed independent static errors per layer, hypothetical receiver noise and loss.",
          "Independent Gaussian calibration probes for each programming event; phase oracle from MOD-004.",
          "No optical backward, hardware measurement, latency or energy claim.",
          "Layer errors measure cumulative activation differences, not isolated layer errors."],
        checks=checks,gradient_max_abs_error=grad_error,ideal_max_abs_error=max(controls),
        rows=rows,curves=curves,comparisons=comparisons,layer_errors=layer_errors)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    for name,records in (("metrics",rows),("learning_curves",curves),
                         ("comparisons",comparisons),("layer_errors",layer_errors)):
        with (OUT/(name+".csv")).open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    print(json.dumps(checks,indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
