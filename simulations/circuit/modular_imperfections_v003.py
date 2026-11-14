"""OPA-MOD-003: explicit SVD meshes with static errors and noisy coherent readout.

One wavelength; hypothetical errors and normalized detector units, not hardware data.
"""
import json
from pathlib import Path
import sys

import numpy as np

from mesh import clements_decompose, mesh_matrix, _null_right, _null_left
from mzi import mzi, mzi_hw, program_unitary
from modular_power_budget_v002 import workload, N, SIZES, transmission

OUT = Path("results/opa-mod-003")
TOL = 1e-9
TRIALS = 8
SEED = 303
SCENARIOS = {
    "ideal": (0., 0., 0., 0., 0., None),
    "phase_only": (0.01, 0., 0., 0., 0., None),
    "coupler_only": (0., 0.005, 0., 0., 0., None),
    "arm_loss_only": (0., 0., 0.02, 0., 0., None),
    "read_noise_only": (0., 0., 0., 0., 1e-5, None),
    "quantization_only": (0., 0., 0., 0., 0., 12),
    "combined_low": (0.005, 0.002, 0.01, 0.002, 1e-6, 16),
    "combined_high": (0.02, 0.01, 0.05, 0.01, 1e-5, 12),
}
# Fixed MOD-002 scenario, and ideal loss control.
LOSSES = {
    "lossless": (0., 0., 0., 0., 0.),
    "moderate": (0.08, 0.015, 0.2, 2., 2.5),
}


def fast_decompose(target):
    """Same Clements algorithm as mesh.py, with 2-row/column updates."""
    u = np.array(target, dtype=complex, copy=True)
    n = len(u)
    right, left = [], []
    for i in range(n-1):
        if i % 2 == 0:
            for j in range(i+1):
                row, col = n-1-j, i-j
                t, p = _null_right(u, row, col)
                u[:, col:col+2] = u[:, col:col+2] @ mzi(t,p).conj().T
                right.append((col,t,p))
        else:
            for j in range(1,i+2):
                row, col = n+j-i-2, j-1
                t,p = _null_left(u,row,col)
                u[row-1:row+1,:] = mzi(t,p) @ u[row-1:row+1,:]
                left.append((row-1,t,p))
    d = np.diag(u).copy()
    moved = []
    for m,t,p in reversed(left):
        block = mzi(t,p).conj().T @ np.diag(d[m:m+2])
        t2,p2,a,b = program_unitary(block)
        d[m:m+2] = np.exp(1j*np.array([a,b]))
        moved.append((m,t2,p2))
    return right+moved, np.angle(d)


def random_mesh(mesh, rng):
    ops, phases = mesh
    # Static independent draws, shared across all input vectors and scenarios.
    return rng.standard_normal((len(ops),6)), rng.standard_normal(len(phases))


def blocks_for(mesh, draws, phase_sigma, split_sigma, arm_sigma):
    ops, phases = mesh
    z, screen = draws
    settings = np.asarray(ops, dtype=float).reshape(-1,3)
    t = settings[:,1]+phase_sigma*z[:,0]
    p = settings[:,2]+phase_sigma*z[:,1]
    r1 = np.clip(0.5+split_sigma*z[:,2],0,1)
    r2 = np.clip(0.5+split_sigma*z[:,3],0,1)
    loss = arm_sigma*z[:,4]
    a = np.exp(1j*t)*10**(-np.maximum(loss,0)/20)
    d = 10**(-np.maximum(-loss,0)/20)
    c1,s1,c2,s2 = np.sqrt(r1),np.sqrt(1-r1),np.sqrt(r2),np.sqrt(1-r2)
    ep = np.exp(1j*p)
    blocks = np.empty((len(ops),2,2),dtype=complex)
    blocks[:,0,0] = (c2*a*c1-s2*d*s1)*ep
    blocks[:,0,1] = 1j*(c2*a*s1+s2*d*c1)
    blocks[:,1,0] = 1j*(s2*a*c1+c2*d*s1)*ep
    blocks[:,1,1] = -s2*a*s1+c2*d*c1
    return settings[:,0].astype(int),blocks,np.exp(1j*(phases+phase_sigma*screen))


def propagate(mesh, field, draws, phase_sigma, split_sigma, arm_sigma):
    indices,blocks,screen = blocks_for(mesh,draws,phase_sigma,split_sigma,arm_sigma)
    f = np.array(field,dtype=complex,copy=True)
    for m,block in zip(indices,blocks):
        f[m:m+2] = block @ f[m:m+2]
    return screen[:,None]*f


def prepare(w, b):
    tiles = []
    for i in range(0,len(w),b):
        for j in range(0,len(w),b):
            u,s,vh = np.linalg.svd(w[i:i+b,j:j+b],full_matrices=False)
            scale = float(s.max())
            a = s/scale if scale else np.zeros_like(s)
            tiles.append((i,j,fast_decompose(vh),fast_decompose(u),a,scale))
    return tiles


def error(y, ref):
    norm = np.linalg.norm(ref)
    return float(np.linalg.norm(y-ref)/(norm if norm else 1.))


def scalar_loss(b, loss):
    mzi_db,wg_db,split_db,link_db,interface_and_attenuator_db = loss
    k = N//b
    db = 2*b*(mzi_db+wg_db)+np.log2(k)*split_db
    db += interface_and_attenuator_db+(link_db if k>1 else 0.)
    return transmission(db)


def quantize_real(x,bits):
    if bits is None:
        return x,0
    # Shared fixed signed field range [-1,+1]; no per-tile AGC.
    clipped = int(np.count_nonzero(abs(x)>1))
    levels = 2**(bits-1)-1
    return np.rint(np.clip(x,-1,1)*levels)/levels,clipped


def evaluate(tiles,w,x,b,scenario,draws,loss):
    phase,split,arm,atten,noise,bits = scenario
    k = N//b
    norm = np.sqrt(k*np.sum(abs(x)**2,axis=0))
    norm = np.where(norm>0,norm,1.)
    t = scalar_loss(b,loss)
    ref = w@x
    static = np.zeros_like(x,dtype=complex)
    read = np.zeros_like(x)
    launched = np.zeros(x.shape[1])
    detected = np.zeros_like(launched)
    clipped = 0
    for (i,j,vh,u,a,scale),(dv,du,da,dn) in zip(tiles,draws):
        f = x[j:j+b]/norm
        launched += np.sum(abs(f)**2,axis=0)
        f = propagate(vh,f,dv,phase,split,arm)
        # Multiplicative attenuation setting variation, bounded passive amplitude.
        f = np.clip(a*(1+atten*da),0,1)[:,None]*f
        f = np.sqrt(t)*propagate(u,f,du,phase,split,arm)
        detected += np.sum(abs(f)**2,axis=0)
        gain = scale*norm/np.sqrt(t)
        static[i:i+b] += gain*f
        q,c = quantize_real(f.real+noise*dn,bits)
        clipped += c
        read[i:i+b] += gain*q
    return {
        "static_complex_error": error(static,ref),
        "static_real_error": error(static.real,ref),
        "readout_error": error(read,ref),
        "imaginary_leakage": error(static.imag,np.zeros_like(ref))/(np.linalg.norm(ref) or 1.),
        "mean_detected_signal_power": float(detected.mean()),
        "passive_excess": float(max(0.,np.max(detected-launched))),
        "launch_error": float(np.max(abs(launched-(np.sum(abs(x)**2,axis=0)>0)))),
        "clipped_samples": clipped,
    }


def make_draws(tiles,x,rng):
    return [(random_mesh(v,rng),random_mesh(u,rng),
             rng.standard_normal(len(a)),rng.standard_normal((len(a),x.shape[1])))
            for _,_,v,u,a,_ in tiles]


def main():
    cases,x = workload()
    # Nonzero dense and structured workloads; zero reference is tested separately.
    selected = ("random_signed","orthogonal","rank_one","ill_conditioned")
    rows = []
    rng = np.random.default_rng(SEED)
    # Explicit optimized decomposition compared to original implementation.
    validation = []
    for n in (2,4,8):
        z = rng.normal(size=(n,n))+1j*rng.normal(size=(n,n))
        q,_ = np.linalg.qr(z)
        mesh = fast_decompose(q)
        draws = random_mesh(mesh,rng)
        actual = propagate(mesh,np.eye(n),draws,0,0,0)
        validation.append(max(error(actual,q),
                              error(actual,mesh_matrix(*clements_decompose(q)))))
    # Nonideal vectorized block formula versus the established component model.
    mesh = fast_decompose(q)
    draws = random_mesh(mesh,rng)
    _, blocks, _ = blocks_for(mesh,draws,0.02,0.01,0.05)
    component_errors = []
    for (_,t,p),z,block in zip(mesh[0],draws[0],blocks):
        loss = 0.05*z[4]
        hw = {"split1":float(np.clip(0.5+0.01*z[2],0,1)),
              "split2":float(np.clip(0.5+0.01*z[3],0,1)),
              "loss_top_db":max(0.,loss),"loss_bottom_db":max(0.,-loss)}
        component_errors.append(error(block,mzi_hw(t+0.02*z[0],p+0.02*z[1],hw)))
    for name in selected:
        w = cases[name]
        for b in SIZES:
            tiles = prepare(w,b)
            for trial in range(TRIALS):
                # Pair all scenarios and loss conditions using identical draws.
                draws = make_draws(tiles,x,rng)
                for scenario,params in SCENARIOS.items():
                    for loss_name,loss in LOSSES.items():
                        rows.append({"case":name,"tile_size":b,"trial":trial,
                                     "scenario":scenario,"loss":loss_name,
                                     **evaluate(tiles,w,x,b,params,draws,loss)})
    zero = np.zeros((N,N))
    tiles = prepare(zero,16)
    zero_test = evaluate(tiles,zero,x,16,SCENARIOS["combined_high"],
                         make_draws(tiles,x,rng),LOSSES["moderate"])
    # Zero scale is an electronic gate: a zero block is exactly zero by design.
    groups = []
    for name in selected:
        for b in SIZES:
            for scenario in SCENARIOS:
                for loss in LOSSES:
                    group = [r for r in rows if (r["case"],r["tile_size"],r["scenario"],r["loss"])==(name,b,scenario,loss)]
                    groups.append({"case":name,"tile_size":b,"scenario":scenario,"loss":loss,
                                   **{metric: {"median":float(np.median([r[metric] for r in group])),
                                               "p90":float(np.percentile([r[metric] for r in group],90)),
                                               "max":float(max(r[metric] for r in group))}
                                      for metric in ("static_complex_error","static_real_error","readout_error","mean_detected_signal_power")}})
    checks = {
        "optimized_decomposition_matches_reference": max(validation)<TOL,
        "all_configurations": len(rows)==len(selected)*len(SIZES)*TRIALS*len(SCENARIOS)*len(LOSSES),
        "ideal_reconstruction": all(r["readout_error"]<TOL and r["static_complex_error"]<TOL for r in rows if r["scenario"]=="ideal"),
        "passivity": all(r["passive_excess"]<TOL for r in rows),
        "equal_launch": all(r["launch_error"]<TOL for r in rows),
        "readout_only_static_ideal": all(r["static_complex_error"]<TOL for r in rows if r["scenario"] in ("read_noise_only","quantization_only")),
        "nonzero_phase_error": any(r["static_complex_error"]>1e-4 for r in rows if r["scenario"]=="phase_only"),
        "zero_weight_gate": zero_test["readout_error"]==0 and zero_test["mean_detected_signal_power"]==0,
        "vectorized_nonideal_component_matches_reference": max(component_errors)<TOL,
        "quantizer_clipping_and_endpoints": quantize_real(np.array([-2.,0.,2.]),12)[1]==2 and np.array_equal(quantize_real(np.array([-2.,0.,2.]),12)[0],np.array([-1.,0.,1.])),
    }
    report = {
        "experiment":"OPA-MOD-003","seed":SEED,"workload_seed":101,"n":N,
        "numpy_version":np.__version__,"python_version":sys.version.split()[0],
        "trials":TRIALS,"vectors_per_trial":x.shape[1],
        "scenario_fields":["phase_sigma_rad","coupler_power_fraction_sigma","differential_arm_loss_sigma_db","attenuator_relative_amplitude_sigma","read_noise_sigma_normalized_real_field","adc_bits"],
        "scenarios":SCENARIOS,"loss_fields":["mzi_column_db","waveguide_column_db","splitter_excess_db","modular_link_db","interface_plus_attenuator_db"],
        "losses":LOSSES,"checks":checks,"failures":[k for k,v in checks.items() if not v],
        "decomposition_validation_errors":validation,"max_component_validation_error":max(component_errors),"zero_test":zero_test,"summary":groups,"results":rows,
        "limitations":[
            "Explicit Clements components at all sizes; ideal settings, no calibration. Static independent Gaussian errors reused across eight inputs and paired scenarios; eight hardware draws are a small sensitivity sample, not yield statistics.",
            "MOD-002 scalar uniform column losses are retained, plus nonnegative differential arm loss as extra loss. No wavelength dependence, thermal correlations or layout-level propagation.",
            "Fixed total launched signal power per input; passive fan-out normalized once. Known common loss corrected exactly, not differential loss or phase errors.",
            "Real coherent quadrature readout with fixed full-scale normalized field ±1, additive independent Gaussian field noise and symmetric uniform quantization. Not a calibrated detector, shot noise, ENOB or ADC energy model.",
            "Only SVD forward pass; QR, gradients and training deferred. Exact electronic scaling and summation, no communication or power cost. No claim of physical superiority.",
            "Same reference matrix and eight probes as MOD-002. Errors are relative Frobenius norms, absolute when reference is zero. Imaginary leakage normalized by reference norm.",
        ],
    }
    OUT.mkdir(parents=True,exist_ok=True)
    text=json.dumps(report,indent=2,allow_nan=False)+"\n"
    (OUT/"result.json").write_text(text,encoding="utf-8")
    # Avoid duplicating the large report in logs; CI Print result archives it.
    print(json.dumps({"experiment":report["experiment"],"checks":checks,"failures":report["failures"],"configurations":len(rows)}))
    if report["failures"]:
        raise SystemExit("OPA-MOD-003 failed: "+", ".join(report["failures"]))


if __name__=="__main__":
    main()
