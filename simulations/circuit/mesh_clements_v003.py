"""OPA-MZI-003: a 4x4 Clements MZI mesh as an optical neural-network layer.

Circuit-level model building on OPA-MZI-001 and -002.

A. Clements decomposition: any N x N unitary is realized exactly by
   N(N-1)/2 MZIs in N columns (checked for N = 2..16).
B. SVD layer: any 4x4 weight matrix W = U diag(s) V^dagger is realized as
   mesh - attenuators - mesh, with the scale max(s) applied electronically.
C. Error scaling: random coupler errors and phase noise in every MZI, for
   N = 2, 4, 8, with naive settings and with global (whole-mesh) calibration.
D. A toy classifier: a linear 4-class layer trained digitally on synthetic
   4-feature data, then run on ideal and on imperfect photonic hardware.

Inputs are encoded as field amplitudes (negative values as a pi phase) and
outputs are read with coherent detection, i.e. the complex field. A
power-only readout (|y|^2) is reported as a diagnostic.
"""
import json
import math
from pathlib import Path
import sys

import numpy as np
import scipy

from mesh import (calibrate_mesh, clements_decompose, layer_matrix, mesh_columns,
                  mesh_matrix, svd_layer)
from mzi import haar_unitary, shape_error

OUT = Path("results/opa-mzi-003")
SEED = 20261112
EXACT = 1e-12

rng = np.random.default_rng(SEED)
checks, failures = {}, []


def check(name, ok, detail):
    checks[name] = {"passed": bool(ok), "detail": detail}
    if not ok:
        failures.append(name)


def stats(values):
    v = np.asarray(values, dtype=float)
    return {"mean": float(v.mean()), "median": float(np.median(v)), "min": float(v.min()),
            "p95": float(np.percentile(v, 95)), "max": float(v.max())}


def bits(err):
    return float(math.log2(1 / err)) if err > 0 else None


def random_hw(n_mzi, split_sigma, loss_top_db=0.0):
    return [{"split1": float(np.clip(rng.normal(0.5, split_sigma), 0.01, 0.99)),
             "split2": float(np.clip(rng.normal(0.5, split_sigma), 0.01, 0.99)),
             "loss_top_db": loss_top_db} for _ in range(n_mzi)]


# A. Clements decomposition ----------------------------------------------------
decomposition = []
for n, count in ((2, 100), (3, 100), (4, 100), (8, 50), (16, 10)):
    errors, n_mzi, depth = [], set(), set()
    for _ in range(count):
        u = haar_unitary(n, rng)
        ops, phases = clements_decompose(u)
        errors.append(np.abs(mesh_matrix(ops, phases) - u).max())
        n_mzi.add(len(ops))
        depth.add(max(mesh_columns(ops, n)) + 1)
    decomposition.append({"n": n, "targets": count, "max_abs_error": float(max(errors)),
                          "mzi_count": sorted(n_mzi), "columns": sorted(depth)})
check("decomposition_exact", all(r["max_abs_error"] < EXACT for r in decomposition),
      "every Haar-random unitary for N = 2..16 is reconstructed to 1e-12")
check("decomposition_mzi_count",
      all(r["mzi_count"] == [r["n"] * (r["n"] - 1) // 2] for r in decomposition),
      "each N x N mesh uses exactly N(N-1)/2 MZIs")
check("decomposition_rectangular",
      all(r["columns"] == [r["n"]] for r in decomposition if r["n"] > 2),
      "each mesh fits in N columns (Clements rectangular layout)")

# B. SVD layer --------------------------------------------------------------------
svd_errors = []
for _ in range(200):
    w = rng.standard_normal((4, 4))
    svd_errors.append(np.abs(layer_matrix(svd_layer(w)) - w).max() / np.abs(w).max())
check("svd_layer_exact", max(svd_errors) < EXACT,
      "200 random real 4x4 weight matrices realized as mesh-attenuators-mesh to 1e-12")
edge_weights = {"zero": np.zeros((4, 4)), "rank_one": np.outer([1, 2, 0, -1], [0.5, 0, 1, 1]),
                "identity": np.eye(4), "diagonal": np.diag([3.0, -1.0, 0.0, 0.25])}
edge_errors = {name: float(np.abs(layer_matrix(svd_layer(w)) - w).max())
               for name, w in edge_weights.items()}
check("svd_layer_edge_cases",
      all(np.isfinite(e) and e < EXACT for e in edge_errors.values()),
      "zero, rank-one, identity and diagonal weight matrices are realized to 1e-12")

# C. Error scaling with mesh size ----------------------------------------------
scaling = []
for n, count in ((2, 60), (4, 40), (8, 20)):
    targets = [haar_unitary(n, rng) for _ in range(count)]
    programs = [clements_decompose(u) for u in targets]
    k = n * (n - 1) // 2
    for split_sigma in (0.005, 0.01, 0.02):
        naive, calibrated = [], []
        for u, (ops, phases) in zip(targets, programs):
            hw = random_hw(k, split_sigma)
            naive.append(shape_error(mesh_matrix(ops, phases, hw=hw), u))
            cal_ops, cal_phases = calibrate_mesh(u, ops, phases, hw)
            calibrated.append(shape_error(mesh_matrix(cal_ops, cal_phases, hw=hw), u))
        scaling.append({"n": n, "mzis": k, "error_source": "coupler_split",
                        "sigma": split_sigma, "naive_error": stats(naive),
                        "calibrated_error": stats(calibrated),
                        "calibrated_never_worse": bool(all(
                            c <= a + 1e-12 for a, c in zip(naive, calibrated)))})
    noisy = []
    for u, (ops, phases) in zip(targets, programs):
        for _ in range(10):
            jitter = [(m, t + rng.normal(0, 0.01), p + rng.normal(0, 0.01))
                      for m, t, p in ops]
            noisy.append(shape_error(mesh_matrix(
                jitter, phases + rng.normal(0, 0.01, n)), u))
    scaling.append({"n": n, "mzis": k, "error_source": "phase_noise", "sigma": 0.01,
                    "error": stats(noisy)})

check("calibration_never_worse_mesh",
      all(r["calibrated_never_worse"] for r in scaling if "calibrated_never_worse" in r),
      "global calibration never increases the error of any mesh")
coupler_1pct = [r["naive_error"]["mean"] for r in scaling
                if r["error_source"] == "coupler_split" and r["sigma"] == 0.01]
check("naive_error_grows_with_n", all(a < b for a, b in zip(coupler_1pct, coupler_1pct[1:])),
      "with 1 % coupler spread, naive error increases from N = 2 to 4 to 8")
noise_series = [r["error"]["mean"] for r in scaling if r["error_source"] == "phase_noise"]
check("phase_noise_error_grows_with_n",
      all(a < b for a, b in zip(noise_series, noise_series[1:])),
      "with 0.01 rad phase noise, error increases from N = 2 to 4 to 8")

# D. Toy classifier ---------------------------------------------------------------
N_CLASSES, N_FEATURES = 4, 4
means = rng.normal(0, 1, (N_CLASSES, N_FEATURES))
means *= 2.0 / np.linalg.norm(means, axis=1, keepdims=True)


def sample(per_class):
    x = np.concatenate([m + rng.normal(0, 0.8, (per_class, N_FEATURES)) for m in means])
    y = np.repeat(np.arange(N_CLASSES), per_class)
    return x, y


x_train, y_train = sample(200)
x_test, y_test = sample(250)
onehot = np.eye(N_CLASSES)[y_train]
design = np.hstack([x_train, np.ones((len(x_train), 1))])
coef = np.linalg.solve(design.T @ design + 1e-3 * np.eye(N_FEATURES + 1), design.T @ onehot)
weights, bias = coef[:N_FEATURES].T, coef[N_FEATURES]       # scores = W x + b


def accuracy(matrix, power_readout=False):
    fields = x_test.astype(complex) @ np.asarray(matrix).T
    scores = np.abs(fields) ** 2 if power_readout else fields.real + bias
    return float((scores.argmax(axis=1) == y_test).mean())


digital = accuracy(weights)
layer = svd_layer(weights)
ideal_optical = accuracy(layer_matrix(layer))
ideal_predictions_match = bool(np.array_equal(
    (x_test @ weights.T + bias).argmax(1),
    ((x_test.astype(complex) @ layer_matrix(layer).T).real + bias).argmax(1)))

SPLIT_SIGMA, ARM_LOSS_DB, PHASE_SIGMA, DAC_BITS, N_CHIPS = 0.01, 0.2, 0.005, 10, 20
step = 2 * np.pi / 2 ** DAC_BITS


def deploy(ops, phases):
    q = lambda v: np.round(v / step) * step + rng.normal(0, PHASE_SIGMA)
    return [(m, q(t), q(p)) for m, t, p in ops], np.array([q(v) for v in phases])


def deployed_layer(in_prog, out_prog):
    return {**layer, "in_mesh": deploy(*in_prog), "out_mesh": deploy(*out_prog)}


u_svd, _, vh_svd = np.linalg.svd(weights.astype(complex))
naive_acc, calibrated_acc, naive_err, calibrated_err = [], [], [], []
for _ in range(N_CHIPS):
    hw_in = random_hw(6, SPLIT_SIGMA, ARM_LOSS_DB)
    hw_out = random_hw(6, SPLIT_SIGMA, ARM_LOSS_DB)
    naive_layer = deployed_layer(layer["in_mesh"], layer["out_mesh"])
    m_naive = layer_matrix(naive_layer, hw_in, hw_out)
    cal_in = calibrate_mesh(vh_svd, *layer["in_mesh"], hw_in)
    cal_out = calibrate_mesh(u_svd, *layer["out_mesh"], hw_out)
    m_cal = layer_matrix(deployed_layer(cal_in, cal_out), hw_in, hw_out)
    naive_acc.append(accuracy(m_naive))
    calibrated_acc.append(accuracy(m_cal))
    naive_err.append(shape_error(m_naive, weights))
    calibrated_err.append(shape_error(m_cal, weights))

classifier = {
    "task": "4 Gaussian classes in 4 dimensions (centers at radius 2, sigma 0.8), "
            "800 training and 1000 test points; linear least-squares classifier",
    "digital_accuracy": digital,
    "ideal_optical_accuracy": ideal_optical,
    "ideal_optical_predictions_identical": ideal_predictions_match,
    "power_readout_accuracy_ideal_optics": accuracy(layer_matrix(layer), power_readout=True),
    "hardware_assumptions": {"coupler_split_sigma": SPLIT_SIGMA,
                             "top_arm_loss_db": ARM_LOSS_DB,
                             "phase_noise_sigma_rad": PHASE_SIGMA, "dac_bits": DAC_BITS,
                             "chips": N_CHIPS, "attenuators": "ideal"},
    "naive": {"accuracy": stats(naive_acc), "weight_error": stats(naive_err),
              "effective_bits_median": bits(float(np.median(naive_err)))},
    "calibrated": {"accuracy": stats(calibrated_acc), "weight_error": stats(calibrated_err),
                   "effective_bits_median": bits(float(np.median(calibrated_err)))},
}
check("classifier_task_meaningful", digital > 0.8,
      "the digital classifier reaches more than 80 % test accuracy")
check("ideal_optics_matches_digital", ideal_predictions_match and ideal_optical == digital,
      "ideal photonic layer gives exactly the digital predictions")
check("calibration_helps_classifier",
      np.median(calibrated_err) < np.median(naive_err),
      "calibration lowers the median weight error of the imperfect layer")

report = {
    "experiment": "OPA-MZI-003",
    "goal": "Realize N x N unitaries and a 4x4 neural-network weight matrix with "
            "Clements MZI meshes, and measure how errors scale with mesh size",
    "model": "Transfer-matrix circuit model; single wavelength; coherent input "
             "encoding and coherent detection",
    "numpy_version": np.__version__,
    "scipy_version": scipy.__version__,
    "python_version": sys.version.split()[0],
    "seed": SEED,
    "checks": checks,
    "failures": failures,
    "A_decomposition": decomposition,
    "B_svd_layer_max_relative_error": float(max(svd_errors)),
    "B_svd_layer_edge_case_max_abs_error": edge_errors,
    "C_error_scaling": scaling,
    "D_classifier": classifier,
    "limitations": [
        "Global calibration assumes every coupler and loss is known exactly; real "
        "meshes are calibrated from measurements",
        "Attenuators for the singular values are ideal",
        "Coherent input encoding and coherent (field) detection are assumed; a "
        "power-only readout changes the decisions (see power_readout_accuracy)",
        "Single wavelength, no thermal crosstalk, no drift, no detector noise",
        "Toy synthetic task; it shows the mechanism, not real-world accuracy",
    ],
}
OUT.mkdir(parents=True, exist_ok=True)
text = json.dumps(report, indent=2) + "\n"
(OUT / "result.json").write_text(text, encoding="utf-8")
print(text)
if failures:
    raise SystemExit("OPA-MZI-003 failed checks: " + ", ".join(failures))
