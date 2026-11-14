"""OPA-MOD-006: hybrid training with explicit tiled optical forward passes.

Synthetic linear regression; digital backward surrogate, not optical backprop.
"""
import csv
import json
from pathlib import Path
import sys

import numpy as np

from modular_power_budget_v002 import N
from modular_imperfections_v003 import prepare, SCENARIOS, LOSSES
from modular_calibration_v004 import hardware, fields, gain_sets, sum_tiles

OUT = Path("results/opa-mod-006")
SEEDS = (606, 607, 608)
SIZES = (16, 64, 128)
SCENES = ("combined_low", "combined_high")
STEPS = 16
BATCH = 32
LR = 0.5
CAL_COUNT = 32
TEST_COUNT = 128
TOL = 1e-9


def mse(y, target):
    return float(np.mean((y-target)**2))


def optical(w, x, b, hw, params, loss, local, xcal, rng):
    tiles = prepare(w, b)
    def read(probes):
        noise = [rng.normal(size=(b, probes.shape[1])) for _ in tiles]
        return fields(tiles, hw, b, probes, params, loss, local, noise)
    if local:
        cal, _, _, _, _ = read(xcal)
        gains = gain_sets(tiles, w, xcal, cal, b)["tile"]
    else:
        gains = [1.] * len(tiles)
    measured, _, detected, launched, clips = read(x)
    y = sum_tiles(tiles, measured, x, b, gains)
    diagnostics = {
        "passive_excess": float(max(0., np.max(detected-launched))),
        "mean_detected_power": float(detected.mean()),
        "clips": int(clips),
        "calibration_vectors": CAL_COUNT if local else 0,
    }
    return y, diagnostics


def update(w, x, y, target):
    # Gradient of half summed output squared error averaged over examples,
    # treating programmed W as the effective linear operator (straight-through).
    return w - LR * ((y-target) @ x.T / x.shape[1])


def main():
    rows, curves, controls = [], [], []
    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        teacher = rng.normal(size=(N,N))/np.sqrt(N)
        w0 = rng.normal(size=(N,N))*0.05/np.sqrt(N)
        train = rng.normal(size=(N,256))
        test = rng.normal(size=(N,TEST_COUNT))
        xcal = rng.normal(size=(N,CAL_COUNT))
        batches = [rng.choice(train.shape[1], BATCH, replace=False) for _ in range(STEPS)]
        target = teacher @ test
        initial = mse(w0@test,target)
        digital = w0.copy()
        for step, ids in enumerate(batches):
            x = train[:,ids]
            y = digital @ x
            curves.append(dict(seed=seed,tile_size=0,scenario="digital",
                               method="digital",step=step,train_mse=mse(y,teacher@x)))
            digital = update(digital,x,y,teacher@x)
        digital_mse = mse(digital@test,target)
        rows.append(dict(seed=seed,tile_size=0,scenario="digital",method="digital",
                         initial_test_mse=initial,test_mse=digital_mse,
                         digital_weight_mse=digital_mse,passive_excess=0.,
                         mean_detected_power=None,clips=0,calibration_vectors=0))
        for b in SIZES:
            hw = hardware(prepare(w0,b),np.random.default_rng(seed*1000+b))
            # Actual ideal forward control, including scalar loss compensation.
            for loss in LOSSES.values():
                ideal, d = optical(w0,test[:,:8],b,hw,SCENARIOS["ideal"],loss,
                                   False,xcal,np.random.default_rng(seed))
                controls.append(float(np.max(abs(ideal-w0@test[:,:8]))))
            for scene in SCENES:
                params = SCENARIOS[scene]
                for local in (False,True):
                    label = "calibrated" if local else "uncalibrated"
                    w = w0.copy()
                    diag = []
                    for step, ids in enumerate(batches):
                        x = train[:,ids]
                        y,d = optical(w,x,b,hw,params,LOSSES["moderate"],local,xcal,
                                      np.random.default_rng(seed*10000+step))
                        diag.append(d)
                        curves.append(dict(seed=seed,tile_size=b,scenario=scene,
                                           method="hybrid_"+label,step=step,
                                           train_mse=mse(y,teacher@x)))
                        w = update(w,x,y,teacher@x)
                    # Same held-out input, hardware and receiver-noise seed
                    # for both policies; calibration never uses test labels.
                    for method, weights in (("digital_deploy_"+label,digital),
                                            ("hybrid_"+label,w)):
                        y,d = optical(weights,test,b,hw,params,LOSSES["moderate"],local,xcal,
                                      np.random.default_rng(seed*10000+999))
                        history = (diag if method.startswith("hybrid") else []) + [d]
                        rows.append(dict(seed=seed,tile_size=b,scenario=scene,method=method,
                                         initial_test_mse=initial,test_mse=mse(y,target),
                                         digital_weight_mse=mse(weights@test,target),
                                         passive_excess=max(v["passive_excess"] for v in history),
                                         mean_detected_power=d["mean_detected_power"],
                                         clips=sum(v["clips"] for v in history),
                                         calibration_vectors=sum(v["calibration_vectors"] for v in history)))
    comparisons = []
    for seed in SEEDS:
        for b in SIZES:
            for scene in SCENES:
                for label in ("calibrated","uncalibrated"):
                    selected = {r["method"]:r for r in rows if
                                (r["seed"],r["tile_size"],r["scenario"])==(seed,b,scene)}
                    base = selected["digital_deploy_"+label]["test_mse"]
                    hybrid = selected["hybrid_"+label]["test_mse"]
                    comparisons.append(dict(seed=seed,tile_size=b,scenario=scene,
                                            calibration=label,baseline_mse=base,
                                            hybrid_mse=hybrid,delta_mse=hybrid-base))
    checks = {
        "ideal_forward_matches_digital": max(controls)<TOL,
        "all_results": len(rows)==len(SEEDS)*(1+len(SIZES)*len(SCENES)*4),
        "all_curves": len(curves)==len(SEEDS)*STEPS*(1+len(SIZES)*len(SCENES)*2),
        "all_comparisons": len(comparisons)==len(SEEDS)*len(SIZES)*len(SCENES)*2,
        "finite_metrics": all(np.isfinite(r["test_mse"]) and np.isfinite(r["digital_weight_mse"])
                              for r in rows) and all(np.isfinite(r["train_mse"]) for r in curves),
        "passivity": all(r["passive_excess"]<TOL for r in rows),
        "digital_training_learns": all(r["test_mse"]<r["initial_test_mse"]
                                      for r in rows if r["method"]=="digital"),
        "calibration_accounting": all(r["calibration_vectors"] ==
            (CAL_COUNT*(STEPS+1) if r["method"]=="hybrid_calibrated" else
             CAL_COUNT if r["method"]=="digital_deploy_calibrated" else 0) for r in rows),
    }
    # Scientific outcome is not a blocking check: negative results are valid.
    report = dict(experiment="OPA-MOD-006", numpy_version=np.__version__,
                  config=dict(n=N,seeds=SEEDS,tile_sizes=SIZES,scenarios=SCENES,
                              steps=STEPS,batch=BATCH,learning_rate=LR,
                              calibration_count=CAL_COUNT,test_count=TEST_COUNT),
                  assumptions=["Synthetic noiseless linear teacher; no nonlinear network or real dataset.",
                               "Explicit SVD/MZI forward; fixed chip errors reused across reprogramming.",
                               "Digital straight-through backward and electronic weight updates.",
                               "Calibrated policy uses MOD-004 local phase oracle and per-program tile gain probes.",
                               "Read noise and loss hypothetical; no energy, runtime or hardware advantage claim.",
                               "No measured phase programming, drift, endurance or backward-pass energy."],
                  checks=checks,ideal_max_abs_error=max(controls),rows=rows,
                  comparisons=comparisons,curves=curves)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    for name, records in (("metrics",rows),("learning_curves",curves),("comparisons",comparisons)):
        with (OUT/(name+".csv")).open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    print(json.dumps(checks,indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
