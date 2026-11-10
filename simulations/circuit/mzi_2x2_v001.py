"""OPA-MZI-001: an ideal 2x2 MZI as a programmable matrix multiplier.

Circuit-level transfer-matrix model; no FDTD. Checks that:

1. the MZI transfer matrix equals its closed form and is unitary,
2. the internal phase theta sets the power splitting as sin^2(theta/2),
3. theta, phi and an output phase screen can be programmed to realize any
   2x2 unitary (1000 Haar-random targets plus the degenerate bar/cross cases),
4. the programmed circuit multiplies an input field vector by that matrix,
5. a real 2x2 weight matrix (rotation) can be applied to real inputs, as in a
   neural-network layer.

Ideal, lossless 50:50 couplers at a single wavelength. Fabrication errors,
loss and detection are left to OPA-MZI-002.
"""
import json
from pathlib import Path
import sys

import numpy as np

from mzi import (haar_unitary, mzi, mzi_analytic, phase_screen,
                 program_unitary, programmed_matrix)

OUT = Path("results/opa-mzi-001")
SEED = 20261110
N_RANDOM = 1000
TOLERANCE = 1e-12

rng = np.random.default_rng(SEED)
checks = {}

# 1. Closed form and unitarity over random settings.
angles = rng.uniform(0, 2 * np.pi, size=(N_RANDOM, 2))
closed_form_error = max(
    np.abs(mzi(t, f) - mzi_analytic(t, f)).max() for t, f in angles)
unitarity_error = max(
    np.abs(mzi(t, f).conj().T @ mzi(t, f) - np.eye(2)).max() for t, f in angles)
checks["closed_form_max_abs_error"] = float(closed_form_error)
checks["unitarity_max_abs_error"] = float(unitarity_error)

# 2. Power splitting for light entering the top port.
thetas = np.linspace(0, np.pi, 13)
splitting = []
for t in thetas:
    out = mzi(t, 0.0) @ np.array([1, 0], dtype=complex)
    p_top, p_bottom = abs(out) ** 2
    splitting.append({
        "theta_rad": float(t),
        "power_top": float(p_top),
        "power_bottom": float(p_bottom),
        "expected_power_top": float(np.sin(t / 2) ** 2),
    })
checks["splitting_max_abs_error"] = float(max(
    abs(row["power_top"] - row["expected_power_top"]) for row in splitting))
checks["splitting_max_power_conservation_error"] = float(max(
    abs(row["power_top"] + row["power_bottom"] - 1) for row in splitting))

# 3. Programming arbitrary unitaries.
targets = [haar_unitary(2, rng) for _ in range(N_RANDOM)]
degenerate = {
    "identity": np.eye(2, dtype=complex),
    "swap": np.array([[0, 1], [1, 0]], dtype=complex),
    "diagonal_phases": phase_screen(0.7, -1.9),
    "anti_diagonal_phases": phase_screen(2.1, 0.4) @ np.array([[0, 1], [1, 0]]),
    "hadamard": np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2),
}
# Targets a tiny angle away from the bar and cross states, where theta must be
# recovered without losing the small matrix entries to rounding.
near_edge = {}
for eps in (1e-12, 1e-8, 1e-6, 1e-4):
    c, s_ = np.cos(eps), np.sin(eps)
    near_edge[f"near_bar_rotation_{eps:g}"] = np.array([[c, -s_], [s_, c]], dtype=complex)
    near_edge[f"near_cross_{eps:g}"] = np.array([[s_, c], [c, -s_]], dtype=complex)
degenerate.update(near_edge)
targets += list(degenerate.values())
program_errors, settings = [], []
for u in targets:
    params = program_unitary(u)
    program_errors.append(np.abs(programmed_matrix(*params) - u).max())
    settings.append(params)
checks["programming_max_abs_error"] = float(max(program_errors))
examples = {
    name: dict(zip(("theta", "phi", "a", "b"), program_unitary(u)))
    for name, u in degenerate.items() if name not in near_edge
}
checks["near_edge_programming_max_abs_error"] = float(max(
    np.abs(programmed_matrix(*program_unitary(u)) - u).max()
    for u in near_edge.values()))

# 4. Matrix-vector multiplication with programmed circuits.
mvm_errors = []
for u in targets[:N_RANDOM]:
    x = rng.standard_normal(2) + 1j * rng.standard_normal(2)
    y_circuit = programmed_matrix(*program_unitary(u)) @ x
    mvm_errors.append(np.abs(y_circuit - u @ x).max() / np.abs(x).max())
checks["matrix_vector_max_relative_error"] = float(max(mvm_errors))

# 5. A real weight matrix: rotation by 30 degrees applied to real inputs.
angle = np.deg2rad(30)
weights = np.array([[np.cos(angle), -np.sin(angle)],
                    [np.sin(angle), np.cos(angle)]], dtype=complex)
rotation_params = program_unitary(weights)
inputs = np.array([[1.0, 0.0], [0.0, 1.0], [0.6, 0.8], [-0.3, 0.5]])
rotation_outputs = []
for x in inputs:
    y = programmed_matrix(*rotation_params) @ x.astype(complex)
    rotation_outputs.append({
        "input": x.tolist(),
        "output_field": [[float(v.real), float(v.imag)] for v in y],
        "expected": (weights.real @ x).tolist(),
        "detected_power": (abs(y) ** 2).tolist(),
    })
checks["real_weight_max_abs_error"] = float(max(
    np.abs(programmed_matrix(*rotation_params) @ x - weights @ x).max()
    for x in inputs))

# Sensitivity check: the same settings on hardware whose couplers split 48:52
# instead of 50:50 must give an error far above the tolerance; otherwise the
# checks above could not detect a wrong model.
sensitivity_error = max(
    np.abs(programmed_matrix(*settings[i], split=0.48) - targets[i]).max()
    for i in range(N_RANDOM))
if sensitivity_error <= 1e3 * TOLERANCE:
    raise SystemExit("Sensitivity check failed: a 48:52 coupler went undetected")

failures = [name for name, value in checks.items() if value > TOLERANCE]
report = {
    "experiment": "OPA-MZI-001",
    "goal": "Show that an ideal 2x2 MZI with an output phase screen is a "
            "programmable 2x2 unitary matrix multiplier",
    "model": "Transfer-matrix circuit model; ideal lossless 50:50 couplers; single wavelength",
    "numpy_version": np.__version__,
    "python_version": sys.version.split()[0],
    "seed": SEED,
    "random_targets": N_RANDOM,
    "tolerance": TOLERANCE,
    "checks": checks,
    "failures": failures,
    "sensitivity_48_52_coupler_max_abs_error": float(sensitivity_error),
    "splitting_sweep": splitting,
    "degenerate_case_settings": examples,
    "rotation_30deg": {
        "settings": dict(zip(("theta", "phi", "a", "b"), rotation_params)),
        "samples": rotation_outputs,
    },
    "limitations": [
        "Ideal 50:50 couplers, lossless phase shifters and waveguides",
        "Single wavelength; no dispersion",
        "One MZI realizes only 2x2 unitary matrices; general NxN matrices need a "
        "mesh (Reck/Clements) and, for non-unitary weights, an SVD with attenuators",
        "Photodetectors measure power |y|^2, not the complex field; reading signed "
        "outputs needs coherent detection or an encoding scheme",
        "No fabrication errors, thermal crosstalk or phase-shifter calibration",
    ],
}
OUT.mkdir(parents=True, exist_ok=True)
text = json.dumps(report, indent=2) + "\n"
(OUT / "result.json").write_text(text, encoding="utf-8")
print(text)
if failures:
    raise SystemExit("OPA-MZI-001 failed checks: " + ", ".join(failures))
