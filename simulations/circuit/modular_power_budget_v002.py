"""OPA-MOD-002: conditional optical signal power budgets for tiled SVD and QR.

Scalar, uniform per-column loss model, not electromagnetic or detector simulation.
All powers are fractions of a common total launched signal power of one.
"""
import json
from pathlib import Path
import sys

import numpy as np

OUT = Path("results/opa-mod-002")
N, SEED = 128, 101
SIZES = (128, 64, 32, 16, 8)
TOL = 1e-10


def transmission(db):
    return 10.0 ** (-db / 10.0)


def workload():
    # Match MOD-001's RNG sequence and first eight input vectors.
    rng = np.random.default_rng(SEED)
    q, _ = np.linalg.qr(rng.normal(size=(N, N)))
    v, _ = np.linalg.qr(rng.normal(size=(N, N)))
    cases = {
        "random_signed": rng.normal(size=(N, N)) / np.sqrt(N),
        "orthogonal": q,
        "identity": np.eye(N),
        "zero": np.zeros((N, N)),
        "rank_one": np.outer(q[:, 0], v[:, 0]),
        "ill_conditioned": (q * np.geomspace(1, 1e-10, N)) @ v.T,
    }
    return cases, rng.normal(size=(N, 8))


def prepare(w, x, b, method):
    """Return per-tile encoded fields, ideal optical outputs and electronic gains."""
    tiles = []
    n = len(w)
    for i in range(0, n, b):
        for j in range(0, n, b):
            block = w[i:i+b, j:j+b]
            xj = x[j:j+b]
            if method == "svd":
                u, s, vh = np.linalg.svd(block, full_matrices=False)
                scale = float(s.max())
                a = s / scale if scale else np.zeros_like(s)
                encoded = xj
                optical = u @ (a[:, None] * (vh @ xj))
            else:
                q, r = np.linalg.qr(block)
                encoded = r @ xj
                optical = q @ encoded
                scale = 1.0
            tiles.append((i, encoded, optical, scale))
    return tiles


def budget(tiles, w, x, b, method, scenario):
    n = len(w)
    k = n // b
    # SVD: each x block is replicated k times by ideal passive fan-out.
    # QR: each R*x block is encoded independently after digital preprocessing.
    # Normalize both to the same total optical power, not per-tile laser power.
    total_encoded = sum(np.sum(abs(e)**2, axis=0) for _, e, _, _ in tiles)
    normalization = np.sqrt(np.where(total_encoded > 0, total_encoded, 1.0))
    active = total_encoded > 0
    meshes = 2 if method == "svd" else 1
    stages = int(np.log2(k)) if method == "svd" else 0
    # Uniform column-equivalent loss includes bypass paths by assumption.
    mesh_db = meshes * b * (scenario["mzi_column_db"] + scenario["waveguide_column_db"])
    splitter_db = stages * scenario["splitter_excess_db"]
    interface_db = scenario["interface_db"] + (scenario["modular_link_db"] if k > 1 else 0)
    attenuator_excess_db = scenario["attenuator_excess_db"] if method == "svd" else 0
    hardware_db = mesh_db + splitter_db + interface_db + attenuator_excess_db
    t = transmission(hardware_db)
    launched = np.zeros(x.shape[1])
    ideal_out = np.zeros_like(launched)
    detected = np.zeros_like(launched)
    reconstructed = np.zeros_like(x)
    fractions = []
    for i, encoded, optical, scale in tiles:
        pin = np.sum(abs(encoded / normalization)**2, axis=0)
        pout = np.sum(abs(optical / normalization)**2, axis=0)
        field = np.sqrt(t) * optical / normalization
        pdet = np.sum(abs(field)**2, axis=0)
        launched += pin
        ideal_out += pout
        detected += pdet
        fractions.append(pdet)
        reconstructed[i:i+b] += scale * field * normalization / np.sqrt(t)
    ref = w @ x
    error = np.linalg.norm(reconstructed-ref) / (np.linalg.norm(ref) or 1.0)
    # Equal detected total signal power of one arbitrary unit, not equal SNR.
    # Null if any vector has exactly zero detected signal.
    required = [float(1/p) if p > 0 else None for p in detected]
    # Account for the splitter's ideal 1/k branch allocation only once.
    return {
        "tile_size": b, "method": method, "tiles": k*k,
        "mesh_columns_per_tile": meshes*b, "fanout_per_input": k if method == "svd" else None,
        "mesh_loss_db": mesh_db, "splitter_excess_loss_db": splitter_db,
        "ideal_split_per_branch_db": float(10*np.log10(k)) if method == "svd" else None,
        "interface_loss_db": interface_db, "attenuator_excess_loss_db": attenuator_excess_db,
        "uniform_hardware_loss_db": hardware_db, "uniform_hardware_transmission": t,
        "launched_power_per_vector": launched.tolist(),
        "ideal_optical_output_power_per_vector": ideal_out.tolist(),
        "detected_signal_power_per_vector": detected.tolist(),
        "mean_detected_signal_power": float(detected.mean()),
        "minimum_tile_signal_power_per_vector": np.min(fractions, axis=0).tolist(),
        "launch_units_for_unit_total_detected_signal_per_vector": required,
        "gain_corrected_forward_error": float(error),
        "launch_normalization_error": float(np.max(abs(launched-active.astype(float)))),
        "passive_excess": float(max(0, np.max(ideal_out-launched), np.max(detected-ideal_out))),
        "power_accounting_error": float(np.max(abs(detected-t*ideal_out))),
    }


def main():
    cases, x = workload()
    # Hypothetical sensitivity grid; not measured or foundry-calibrated.
    scenarios = [
        {"name": "ideal", "mzi_column_db": 0., "waveguide_column_db": 0.,
         "splitter_excess_db": 0., "interface_db": 0., "modular_link_db": 0.,
         "attenuator_excess_db": 0.},
    ]
    for mzi in (0.01, 0.04, 0.08, 0.16):
        for link in (0., 2., 6., 12.):
            scenarios.append({
                "name": f"mzi_{mzi}_link_{link}",
                "mzi_column_db": mzi, "waveguide_column_db": 0.015,
                "splitter_excess_db": 0.2, "interface_db": 2.,
                "modular_link_db": link, "attenuator_excess_db": 0.5,
            })
    rows = []
    for name, w in cases.items():
        for b in SIZES:
            for method in ("svd", "qr"):
                tiles = prepare(w, x, b, method)
                for scenario in scenarios:
                    rows.append({"case": name, "scenario": scenario["name"],
                                 **budget(tiles, w, x, b, method, scenario)})
    # Compare only within each method, same workload and scenario.
    baseline = {(r["case"], r["method"], r["scenario"]): r
                for r in rows if r["tile_size"] == N}
    for r in rows:
        ref = baseline[r["case"], r["method"], r["scenario"]]
        p0 = ref["mean_detected_signal_power"]
        p = r["mean_detected_signal_power"]
        r["mean_signal_ratio_to_monolithic"] = p/p0 if p0 > 0 else None
    summary = []
    for scenario in scenarios:
        for method in ("svd", "qr"):
            group = [r for r in rows if r["case"] == "random_signed"
                     and r["method"] == method and r["scenario"] == scenario["name"]]
            summary.append({"scenario": scenario["name"], "method": method,
                            "random_signed_tile_results": [
                                {"tile_size": r["tile_size"],
                                 "mean_detected_signal_power": r["mean_detected_signal_power"],
                                 "mean_signal_ratio_to_monolithic": r["mean_signal_ratio_to_monolithic"]}
                                for r in group]})
    # Independent closed-form checks: uniform loss, normalized passive splitting,
    # and identity's unit signal for SVD when there is no splitting.
    ideal_identity = baseline["identity", "svd", "ideal"]
    known = budget(prepare(np.eye(8), np.ones((8, 1)), 4, "svd"),
                   np.eye(8), np.ones((8, 1)), 4, "svd", {
                       "mzi_column_db": 0., "waveguide_column_db": 0.,
                       "splitter_excess_db": 0., "interface_db": 0.,
                       "modular_link_db": 0., "attenuator_excess_db": 0.})
    checks = {
        "all_cases": len(rows) == len(cases)*len(SIZES)*2*len(scenarios),
        "power_normalization": all(r["launch_normalization_error"] < TOL for r in rows),
        "passivity": all(r["passive_excess"] < TOL for r in rows),
        "power_accounting": all(r["power_accounting_error"] < TOL for r in rows),
        "mathematical_equivalence_after_ideal_gain": all(r["gain_corrected_forward_error"] < TOL for r in rows),
        "identity_monolithic_unit_signal": abs(ideal_identity["mean_detected_signal_power"]-1) < TOL,
        "identity_two_way_fanout_half_signal": abs(known["mean_detected_signal_power"]-0.5) < TOL,
        "db_conversion": abs(transmission(10)-0.1) < TOL,
        "zero_svd_has_no_signal": all(r["mean_detected_signal_power"] == 0 for r in rows if r["case"] == "zero"),
        "adverse_and_favorable_scenarios": (
            any(r["mean_signal_ratio_to_monolithic"] > 1 for r in rows
                if r["case"] == "random_signed" and r["method"] == "svd" and r["tile_size"] < N)
            and any(r["mean_signal_ratio_to_monolithic"] < 1 for r in rows
                    if r["case"] == "random_signed" and r["method"] == "svd" and r["tile_size"] < N)),
    }
    report = {
        "experiment": "OPA-MOD-002", "seed": SEED, "n": N,
        "numpy_version": np.__version__, "python_version": sys.version.split()[0],
        "vectors_per_case": x.shape[1], "checks": checks,
        "failures": [k for k,v in checks.items() if not v],
        "scenarios": scenarios, "random_signed_summary": summary, "results": rows,
        "limitations": [
            "All losses are hypothetical scalar power losses, not measured component data. Equal loss per column including bypass is a simplifying assumption.",
            "SVD uses passive fan-out of each input block, including ideal 1/k power per branch via normalization; splitter excess loss is additional. QR encodes R*x electronically and independently; its optical normalization is different and excludes electronic costs.",
            "SVD singular-value attenuation is actual block- and input-dependent amplitude attenuation. Additional attenuator excess loss is separate.",
            "Total signal power sums optical outputs before electronic gain and accumulation. It is not final output power, equal SNR, equal numerical accuracy under noise, or energy efficiency.",
            "Unit detected signal target is a normalized aggregate, not a detector sensitivity specification. Minimum tile power is reported but zero tiles can be intentional.",
            "Gain correction assumes noiseless coherent field readout, exact known loss and unlimited electronic precision. Local oscillator, modulation, DAC/ADC, laser efficiency, timing and communication energy are excluded.",
            "One wavelength, forward pass only. No thermal drift, phase noise, wavelength-dependent loss or explicit MZI path simulation. No manufacturing or hardware superiority claim.",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    (OUT / "result.json").write_text(text, encoding="utf-8")
    print(text)
    if report["failures"]:
        raise SystemExit("OPA-MOD-002 failed: " + ", ".join(report["failures"]))


if __name__ == "__main__":
    main()
