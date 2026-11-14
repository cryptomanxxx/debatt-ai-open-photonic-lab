"""OPA-MOD-004: static phase correction and measured scalar gain calibration.

Local phase metrology is modeled as an oracle plus measurement uncertainty.
Electronic correction uses noisy optical calibration probes, not test labels.
No full digital residual matrix is used in inference.
"""
import json
from pathlib import Path
import sys

import numpy as np

from modular_power_budget_v002 import workload, N, SIZES
from modular_imperfections_v003 import (
    prepare, propagate, random_mesh, scalar_loss, quantize_real, error,
    SCENARIOS, LOSSES,
)

OUT = Path("results/opa-mod-004")
SEED = 404
TRIALS = 8
TOL = 1e-9
CAL_COUNT = 32
TEST_COUNT = 32
GAIN_LIMIT = 4.0
PHASE_MEAS_SIGMA = 0.001
METHODS = ("uncalibrated", "local_phase", "global_gain", "tile_gain",
           "local_phase_global_gain", "local_phase_tile_gain")
CASES = ("random_signed", "orthogonal", "rank_one", "ill_conditioned")
SCENE_NAMES = ("ideal", "combined_low", "combined_high")


def hardware(tiles, rng):
    out = []
    for _,_,v,u,a,_ in tiles:
        dv,du = random_mesh(v,rng),random_mesh(u,rng)
        ev = (rng.normal(size=dv[0].shape),rng.normal(size=dv[1].shape))
        eu = (rng.normal(size=du[0].shape),rng.normal(size=du[1].shape))
        out.append((dv,du,rng.normal(size=len(a)),ev,eu))
    return out


def corrected_draw(draw, measurement_error, phase_sigma, local):
    # A measured phase offset is subtracted from the commanded setting.
    # Keep actual coupler and loss draws unchanged; only phases are corrected.
    if not local or phase_sigma == 0:
        return draw
    z,screen = draw
    ez,es = measurement_error
    residual = z.copy()
    residual[:,:2] = -PHASE_MEAS_SIGMA/phase_sigma*ez[:,:2]
    return residual, -PHASE_MEAS_SIGMA/phase_sigma*es


def fit_gain(measured, target):
    # Bounded positive least-squares gain, identity fallback for no signal.
    den = float(np.vdot(measured,measured).real)
    if den == 0:
        return 1.0
    return float(np.clip(np.vdot(measured,target).real/den,0.,GAIN_LIMIT))


def fields(tiles, hw, b, x, params, loss, local, noise_draws):
    phase,split,arm,atten,noise,bits = params
    k = N//b
    norm = np.sqrt(k*np.sum(x*x,axis=0))
    norm = np.where(norm>0,norm,1.)
    t = scalar_loss(b,loss)
    launched = np.zeros(x.shape[1])
    detected = np.zeros_like(launched)
    measured, noiseless, raw = [], [], []
    clips = 0
    for (i,j,v,u,a,scale),(dv,du,da,ev,eu),dn in zip(tiles,hw,noise_draws):
        f = x[j:j+b]/norm
        launched += np.sum(abs(f)**2,axis=0)
        f = propagate(v,f,corrected_draw(dv,ev,phase,local),phase,split,arm)
        f = np.clip(a*(1+atten*da),0,1)[:,None]*f
        f = np.sqrt(t)*propagate(u,f,corrected_draw(du,eu,phase,local),phase,split,arm)
        detected += np.sum(abs(f)**2,axis=0)
        gain = scale*norm/np.sqrt(t)
        q,c = quantize_real(f.real+noise*dn,bits)
        clips += c
        measured.append(gain*q)
        noiseless.append(gain*f.real)
        raw.append(f)
    return measured,noiseless,detected,launched,clips


def sum_tiles(tiles, values, x, b, gains):
    y = np.zeros_like(x)
    for (i,*_),v,g in zip(tiles,values,gains):
        y[i:i+b] += g*v
    return y


def gain_sets(tiles, w, xcal, measured, b):
    # Known programmed tile targets, independent of held-out vectors.
    targets = [w[i:i+b,j:j+b]@xcal[j:j+b] for i,j,*_ in tiles]
    base = sum_tiles(tiles,measured,xcal,b,[1.]*len(tiles))
    global_gain = fit_gain(base,w@xcal)
    tile_gains = [fit_gain(m,t) for m,t in zip(measured,targets)]
    return {"none":[1.]*len(tiles),"global":[global_gain]*len(tiles),"tile":tile_gains}


def cost(b, method):
    k = N//b
    tiles = k*k
    local = method.startswith("local_phase")
    global_gain = "global_gain" in method
    tile_gain = "tile_gain" in method
    # Two MZI meshes per tile, two phase settings per MZI and b screen phases.
    phase_parameters = tiles*2*b*b if local else 0
    return {
        "phase_offsets_requiring_local_access":phase_parameters,
        "gain_calibration_input_vectors":CAL_COUNT if global_gain or tile_gain else 0,
        "gain_calibration_real_output_samples":CAL_COUNT*(tiles*b if tile_gain else N) if global_gain or tile_gain else 0,
        "stored_extra_gain_coefficients":tiles if tile_gain else int(global_gain),
        "extra_inference_gain_multiplications_per_vector":tiles*b if tile_gain else N if global_gain else 0,
        "phase_measurement_shots":None if local else 0,
    }


def main():
    cases,_ = workload()
    rng = np.random.default_rng(SEED)
    # Independent probe sets, fixed across sizes and hardware draws.
    xcal = rng.normal(size=(N,CAL_COUNT))
    xtest = rng.normal(size=(N,TEST_COUNT))
    rows = []
    for name in CASES:
        w = cases[name]
        for b in SIZES:
            tiles = prepare(w,b)
            for trial in range(TRIALS):
                hw = hardware(tiles,rng)
                nc = [rng.normal(size=(b,CAL_COUNT)) for _ in tiles]
                nt = [rng.normal(size=(b,TEST_COUNT)) for _ in tiles]
                for scene in SCENE_NAMES:
                    params = SCENARIOS[scene]
                    for local in (False,True):
                        cal,_,_,_,_ = fields(tiles,hw,b,xcal,params,LOSSES["moderate"],local,nc)
                        test,static,det,launch,clips = fields(tiles,hw,b,xtest,params,LOSSES["moderate"],local,nt)
                        gains = gain_sets(tiles,w,xcal,cal,b)
                        for kind,gs in gains.items():
                            method = ("local_phase" if local else "uncalibrated") if kind=="none" else (
                                ("local_phase_" if local else "")+kind+"_gain")
                            y = sum_tiles(tiles,test,xtest,b,gs)
                            # Global gain costs N multiplies: commute scalar with accumulation.
                            rows.append({
                                "case":name,"tile_size":b,"trial":trial,"scenario":scene,"method":method,
                                "heldout_error":error(y,w@xtest),
                                "heldout_static_error":error(sum_tiles(tiles,static,xtest,b,gs),w@xtest),
                                "calibration_error":error(sum_tiles(tiles,cal,xcal,b,gs),w@xcal),
                                "mean_detected_signal_power":float(det.mean()),
                                "passive_excess":float(max(0.,np.max(det-launch))),
                                "launch_error":float(np.max(abs(launch-1))),
                                "clipped_samples":clips,
                                "gain_min":float(min(gs)),"gain_max":float(max(gs)),
                                "gain_mean":float(np.mean(gs)),
                                "gains_at_upper_limit":int(sum(g==GAIN_LIMIT for g in gs)),
                            })
    summary = []
    for name in CASES:
        for b in SIZES:
            for scene in SCENE_NAMES:
                for method in METHODS:
                    group = [r for r in rows if (r["case"],r["tile_size"],r["scenario"],r["method"])==(name,b,scene,method)]
                    errs = [r["heldout_error"] for r in group]
                    summary.append({"case":name,"tile_size":b,"scenario":scene,"method":method,
                                    "median_heldout_error":float(np.median(errs)),
                                    "p90_heldout_error":float(np.percentile(errs,90)),
                                    "max_heldout_error":float(max(errs)),
                                    "fraction_below_one_percent":float(np.mean(np.array(errs)<0.01)),
                                    "median_static_error":float(np.median([r["heldout_static_error"] for r in group]))})
    # Independent exact checks for gain fitting and local correction.
    a = np.array([[1.,-2.],[3.,4.]])
    z = np.ones((2,6))
    screen = np.ones(3)
    corrected = corrected_draw((z,screen),(np.zeros_like(z),np.zeros_like(screen)),0.02,True)
    checks = {
        "all_configurations":len(rows)==len(CASES)*len(SIZES)*TRIALS*len(SCENE_NAMES)*len(METHODS),
        "ideal_control":all(r["heldout_error"]<TOL for r in rows if r["scenario"]=="ideal"),
        "passivity":all(r["passive_excess"]<TOL for r in rows),
        "equal_launch":all(r["launch_error"]<TOL for r in rows),
        "bounded_gains":all(0<=r["gain_min"]<=r["gain_max"]<=GAIN_LIMIT for r in rows),
        "exact_gain_fit":abs(fit_gain(a/2,a)-2)<TOL,
        "gain_limit_and_zero":fit_gain(a/10,a)==GAIN_LIMIT and fit_gain(a*0,a)==1.,
        "exact_phase_offset_removal":np.all(corrected[0][:,:2]==0) and np.all(corrected[1]==0) and np.array_equal(corrected[0][:,2:],z[:,2:]),
        "separate_probe_sets":not np.array_equal(xcal,xtest),
        "finite_errors":all(np.isfinite(r["heldout_error"]) for r in rows),
    }
    report = {
        "experiment":"OPA-MOD-004","seed":SEED,"workload_seed":101,"n":N,
        "numpy_version":np.__version__,"python_version":sys.version.split()[0],
        "trials":TRIALS,"calibration_vectors":CAL_COUNT,"heldout_vectors":TEST_COUNT,
        "phase_measurement_sigma_rad":PHASE_MEAS_SIGMA,"max_extra_gain":GAIN_LIMIT,
        "scenario_parameters":{s:SCENARIOS[s] for s in SCENE_NAMES},
        "loss_parameters":LOSSES["moderate"],"methods":METHODS,
        "checks":{k:bool(v) for k,v in checks.items()},
        "failures":[k for k,v in checks.items() if not v],
        "cost_proxies":[{"tile_size":b,"method":m,**cost(b,m)} for b in SIZES for m in METHODS],
        "summary":summary,"results":rows,
        "limitations":[
            "Local phase correction assumes access to each actual static phase offset plus independent Gaussian metrology error; it is an oracle-assisted feasibility bound, not a demonstrated hardware calibration protocol.",
            "Coupler, differential arm loss and attenuator errors remain in the optical network. Gain fitting can compensate amplitude bias but cannot recover arbitrary matrix shape or lost photons.",
            "Global gain is a single electronic scalar after accumulation; tile gain is one scalar per tile before accumulation. No digital residual matrix, inverse matrix or full electronic replacement of the optical calculation.",
            "Gain fit uses 32 noisy calibration probes and known programmed targets; held-out probes and receiver noise are independent. Paired methods share hardware and receiver draws.",
            "Same MOD-003 hypothetical component/receiver parameters and fixed total launched signal power. New seeds and probes; baseline is paired within this experiment, not identical to archived MOD-003 trials.",
            "Cost proxies count phase settings, gain probe samples and extra arithmetic, not measured time, energy or physical access circuits. Local metrology shot count is unknown.",
            "SVD forward only, no active coupler optimization, global mesh phase optimization, thermal drift, QR, training or physical validation. Eight hardware draws are not yield statistics.",
        ],
    }
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({"experiment":report["experiment"],"checks":report["checks"],"failures":report["failures"],"configurations":len(rows)}))
    if report["failures"]:
        raise SystemExit("OPA-MOD-004 failed: "+", ".join(report["failures"]))


if __name__=="__main__":
    main()
