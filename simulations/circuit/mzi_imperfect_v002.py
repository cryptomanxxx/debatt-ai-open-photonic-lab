"""OPA-MZI-002: how hardware imperfections limit a 2x2 MZI matrix multiplier.

Circuit-level model building on OPA-MZI-001. For Haar-random 2x2 unitary
targets it compares two ways of setting the phases:

  naive       settings computed for ideal hardware (program_unitary)
  calibrated  settings computed for the actual, characterized hardware
              (program_unitary_hw)

and measures the relative Frobenius error after removing a common gain
(uniform loss is reported separately as insertion loss).

Scenarios:
  A. coupler splitting errors (same and opposite sign in the two couplers)
  B. extra loss in one internal arm (e.g. the phase shifter), and balanced loss
  C. random phase noise on all four phase shifters
  D. phase-setting resolution (DAC bits over 0..2 pi)
  E. a combined fabrication scenario with per-chip random coupler errors

Error is translated into "effective bits" = log2(1 / error), a rough guide to
the weight precision a neural-network layer would see.
"""
import json
import math
from pathlib import Path
import sys

import numpy as np
import scipy

from mzi import (haar_unitary, program_unitary, program_unitary_hw,
                 programmed_matrix_hw, reachable_top_power_range, shape_error)

OUT = Path("results/opa-mzi-002")
SEED = 20261111
N_TARGETS = 300
N_NOISE_TARGETS = 200
N_NOISE_DRAWS = 20
N_CHIPS = 200
EXACT = 1e-9

rng = np.random.default_rng(SEED)
targets = [haar_unitary(2, rng) for _ in range(N_TARGETS)]
checks, failures = {}, []


def check(name, ok, detail):
    checks[name] = {"passed": bool(ok), "detail": detail}
    if not ok:
        failures.append(name)


def stats(values):
    v = np.asarray(values, dtype=float)
    return {"mean": float(v.mean()), "median": float(np.median(v)),
            "p95": float(np.percentile(v, 95)), "max": float(v.max())}


def bits(err):
    return float(math.log2(1 / err)) if err > 0 else None


def insertion_loss_db(m):
    """Average power transmission over both inputs, in dB."""
    return float(-10 * np.log10(np.vdot(m, m).real / 2))


# A. Coupler splitting errors -------------------------------------------------
coupler_rows = []
for delta in (0.0, 0.005, 0.01, 0.02, 0.05):
    for pattern in (("same", +1), ("opposite", -1)):
        if delta == 0.0 and pattern[0] == "opposite":
            continue
        hw = {"split1": 0.5 + delta, "split2": 0.5 + pattern[1] * delta}
        lo, hi = reachable_top_power_range(hw["split1"], hw["split2"])
        naive, calibrated, in_range = [], [], []
        for u in targets:
            naive.append(shape_error(programmed_matrix_hw(program_unitary(u), hw), u))
            calibrated.append(shape_error(
                programmed_matrix_hw(program_unitary_hw(u, hw), hw), u))
            in_range.append(lo <= abs(u[0, 0]) ** 2 <= hi)
        naive, calibrated, in_range = map(np.array, (naive, calibrated, in_range))
        coupler_rows.append({
            "delta": delta, "pattern": pattern[0], "hardware": hw,
            "reachable_top_power": [lo, hi],
            # max/min top-port power over theta; null means full extinction is reachable
            "top_port_extinction_ratio_db": (10 * math.log10(hi / lo)) if lo > 0 else None,
            "predicted_reachable_fraction": hi - lo,
            "observed_exact_fraction": float((calibrated < EXACT).mean()),
            "naive_error": stats(naive),
            "calibrated_error": stats(calibrated),
            "calibrated_in_range_max_error": float(calibrated[in_range].max()),
            "calibrated_never_worse": bool((calibrated <= naive + 1e-12).all()),
        })

ideal_row = coupler_rows[0]
check("ideal_hardware_exact",
      ideal_row["naive_error"]["max"] < EXACT and ideal_row["calibrated_error"]["max"] < EXACT,
      "naive and calibrated errors on ideal couplers are below 1e-9")
check("calibration_never_worse",
      all(r["calibrated_never_worse"] for r in coupler_rows),
      "calibrated error <= naive error for every target and coupler error")
check("in_range_targets_exact",
      max(r["calibrated_in_range_max_error"] for r in coupler_rows) < EXACT,
      "every target inside the analytic reachable range is realized to 1e-9")
fraction_ok = []
for r in coupler_rows:
    p = r["predicted_reachable_fraction"]
    sigma = math.sqrt(max(p * (1 - p), 1e-12) / N_TARGETS)
    fraction_ok.append(abs(r["observed_exact_fraction"] - p) <= 3 * sigma + 1 / N_TARGETS)
check("reachable_fraction_matches_theory", all(fraction_ok),
      "observed fraction of exactly realized targets is within 3 sigma of the "
      "analytic reachable range (|u00|^2 is uniform for Haar targets)")
for pattern in ("same", "opposite"):
    series = [r["naive_error"]["mean"] for r in coupler_rows
              if r["pattern"] == pattern or r["delta"] == 0.0]
    check(f"naive_error_grows_with_delta_{pattern}",
          all(a < b for a, b in zip(series, series[1:])),
          f"mean naive error increases with coupler error ({pattern} sign)")

# B. Internal-arm loss ---------------------------------------------------------
loss_rows = []
loss_cases = [(0.0, 0.0), (0.1, 0.0), (0.3, 0.0), (1.0, 0.0), (3.0, 0.0), (1.0, 1.0)]
for top, bottom in loss_cases:
    hw = {"loss_top_db": top, "loss_bottom_db": bottom}
    naive, calibrated, il = [], [], []
    for u in targets[:100]:
        m_naive = programmed_matrix_hw(program_unitary(u), hw)
        naive.append(shape_error(m_naive, u))
        calibrated.append(shape_error(
            programmed_matrix_hw(program_unitary_hw(u, hw), hw), u))
        il.append(insertion_loss_db(m_naive))
    loss_rows.append({
        "loss_top_db": top, "loss_bottom_db": bottom,
        "naive_error": stats(naive), "calibrated_error": stats(calibrated),
        "mean_insertion_loss_db": float(np.mean(il)),
    })
check("no_loss_exact", loss_rows[0]["calibrated_error"]["max"] < EXACT,
      "0 dB arm loss leaves the matrix exact")
check("balanced_loss_exact", loss_rows[-1]["calibrated_error"]["max"] < EXACT,
      "equal loss in both arms only reduces power; shape error stays below 1e-9")
imbalanced = [r["calibrated_error"]["mean"] for r in loss_rows[:-1]]
check("imbalanced_loss_error_grows", all(a < b for a, b in zip(imbalanced, imbalanced[1:])),
      "shape error increases with arm-loss imbalance")

# C. Phase noise --------------------------------------------------------------
noise_rows = []
ideal_settings = [np.array(program_unitary(u)) for u in targets[:N_NOISE_TARGETS]]
for sigma in (1e-3, 3e-3, 1e-2, 3e-2, 1e-1):
    errors = []
    for u, p in zip(targets[:N_NOISE_TARGETS], ideal_settings):
        for _ in range(N_NOISE_DRAWS):
            noisy = p + rng.normal(0, sigma, 4)
            errors.append(shape_error(programmed_matrix_hw(noisy), u))
    noise_rows.append({"sigma_rad": sigma, "error": stats(errors),
                       "error_over_sigma": float(np.mean(errors) / sigma),
                       "effective_bits_median": bits(float(np.median(errors)))})
small = [r["error_over_sigma"] for r in noise_rows if r["sigma_rad"] <= 1e-2]
check("phase_noise_linear_regime", max(small) / min(small) < 1.1,
      "mean error / sigma is constant within 10 % for sigma <= 0.01 rad")

# D. Phase-setting resolution -------------------------------------------------
dac_rows = []
for nbits in (4, 6, 8, 10, 12):
    step = 2 * np.pi / 2 ** nbits
    errors = [shape_error(programmed_matrix_hw(np.round(p / step) * step), u)
              for u, p in zip(targets[:N_NOISE_TARGETS], ideal_settings)]
    dac_rows.append({"dac_bits": nbits, "step_rad": step, "error": stats(errors),
                     "effective_bits_median": bits(float(np.median(errors)))})
dac_means = [r["error"]["mean"] for r in dac_rows]
ratios = [a / b for a, b in zip(dac_means, dac_means[1:])]
check("dac_error_quarters_per_two_bits", all(2.5 < r < 6.0 for r in ratios),
      "each 2 extra DAC bits reduce mean error by about 4x (between 2.5x and 6x)")

# E. Combined fabrication scenario --------------------------------------------
SPLIT_SIGMA = 0.01
ARM_LOSS_DB = 0.2
PHASE_SIGMA = 0.005
DAC_BITS = 10
step = 2 * np.pi / 2 ** DAC_BITS


def deploy(params):
    """Quantize to the DAC grid, then add phase noise."""
    return np.round(np.asarray(params) / step) * step + rng.normal(0, PHASE_SIGMA, 4)


naive, calibrated = [], []
for i in range(N_CHIPS):
    hw = {"split1": float(np.clip(rng.normal(0.5, SPLIT_SIGMA), 0.01, 0.99)),
          "split2": float(np.clip(rng.normal(0.5, SPLIT_SIGMA), 0.01, 0.99)),
          "loss_top_db": ARM_LOSS_DB}
    u = targets[i % N_TARGETS]
    naive.append(shape_error(programmed_matrix_hw(deploy(program_unitary(u)), hw), u))
    calibrated.append(shape_error(
        programmed_matrix_hw(deploy(program_unitary_hw(u, hw)), hw), u))
combined = {
    "assumptions": {
        "coupler_split_sigma": SPLIT_SIGMA, "top_arm_loss_db": ARM_LOSS_DB,
        "phase_noise_sigma_rad": PHASE_SIGMA, "dac_bits": DAC_BITS,
        "chips": N_CHIPS,
        "calibration": "hardware characterized exactly before programming",
    },
    "naive_error": stats(naive),
    "calibrated_error": stats(calibrated),
    "naive_effective_bits_median": bits(float(np.median(naive))),
    "calibrated_effective_bits_median": bits(float(np.median(calibrated))),
}
check("calibration_helps_combined",
      combined["calibrated_error"]["median"] < combined["naive_error"]["median"],
      "calibration lowers the median error in the combined scenario")

report = {
    "experiment": "OPA-MZI-002",
    "goal": "Quantify how coupler errors, arm loss, phase noise and phase resolution "
            "limit a 2x2 MZI matrix multiplier, with and without calibration",
    "model": "Transfer-matrix circuit model; single wavelength",
    "error_metric": "Relative Frobenius error ||g*M - U|| / ||U|| after removing the "
                    "best common real gain g; effective bits = log2(1/error)",
    "numpy_version": np.__version__,
    "scipy_version": scipy.__version__,
    "python_version": sys.version.split()[0],
    "seed": SEED,
    "targets": N_TARGETS,
    "checks": checks,
    "failures": failures,
    "A_coupler_errors": coupler_rows,
    "B_arm_loss": loss_rows,
    "C_phase_noise": noise_rows,
    "D_dac_resolution": dac_rows,
    "E_combined": combined,
    "limitations": [
        "Single 2x2 MZI; errors in meshes accumulate and can partly be corrected "
        "by other MZIs (OPA-MZI-003)",
        "Calibration assumes the coupler splits and losses are known exactly; real "
        "calibration estimates them from measurements and has its own error",
        "Single wavelength; coupler splitting and phase both depend on wavelength",
        "No thermal crosstalk between phase shifters, no drift over time",
        "Detection noise and the power-only readout of photodetectors are not modelled",
        "Effective bits is a rough guide; it is not the same as quantized-weight "
        "precision in a trained network",
    ],
}
OUT.mkdir(parents=True, exist_ok=True)
text = json.dumps(report, indent=2) + "\n"
(OUT / "result.json").write_text(text, encoding="utf-8")
print(text)
if failures:
    raise SystemExit("OPA-MZI-002 failed checks: " + ", ".join(failures))
