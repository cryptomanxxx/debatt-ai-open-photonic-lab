"""Evaluate one pinned SiEPIC EBeam four-port PDK S model; never classify it as measured."""
import csv
import hashlib
import json
import math
import re
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "components/comparison/lib005-bdc-audit.json"
OUT = ROOT / "results/opa-lib-005-d1"
C = 299792458.0

def check(ok, label):
    if not ok:
        raise ValueError(label)

def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def load():
    p = json.loads(CONFIG.read_text())
    source = (ROOT / p["source_manifest"]).read_bytes()
    check(git_blob(source) == p["source_manifest_git_blob_sha1"], "source manifest identity")
    m = json.loads(source)
    check(m["experiment"] == "OPA-LIB-005-C", "source experiment identity")
    check(m["upstream_revision"] == p["source_pdk_revision"], "source revision match")
    candidate = next(v for v in m["upstream_sources"] if v["key"] == p["source_file_key"])
    url = m["upstream_raw_base"] + urllib.parse.quote(candidate["path"], safe="/")
    with urllib.request.urlopen(url, timeout=30) as response:
        raw = response.read(100_001)
    check(len(raw) <= 100_000 and git_blob(raw) == candidate["git_blob_sha1"], "pinned upstream model identity")
    return p, m, candidate, raw.decode("utf-8")

def parse(text):
    rows = text.strip().splitlines()
    check(len(rows) == 16 * 53, "16 blocks each 51 samples")
    samples = np.zeros((51, 4, 4), dtype=np.complex128)
    raw_amp = np.zeros((51, 4, 4), dtype=float)
    raw_phase = np.zeros((51, 4, 4), dtype=float)
    frequencies = None
    seen = set()
    for k in range(16):
        start = k * 53
        label = re.fullmatch(r"\('port ([1-4])','TE',1,'port ([1-4])',1,'transmission'\)", rows[start])
        check(label is not None and rows[start + 1] == "(51,3)", "four-port format")
        out, inp = (int(label[1]) - 1, int(label[2]) - 1)
        check((out, inp) not in seen, "duplicate port entry")
        seen.add((out, inp))
        triplets = np.asarray([[float(v) for v in line.split()] for line in rows[start + 2:start + 53]], dtype=float)
        check(triplets.shape == (51, 3) and np.isfinite(triplets).all(), "valid triple rows")
        check((triplets[:, 1] >= 0).all() and np.all(np.diff(triplets[:, 0]) > 0), "magnitude and frequency")
        if frequencies is None:
            frequencies = triplets[:, 0]
        else:
            check(np.array_equal(frequencies, triplets[:, 0]), "common frequency grid")
        raw_amp[:, out, inp] = triplets[:, 1]
        raw_phase[:, out, inp] = triplets[:, 2]
        samples[:, out, inp] = triplets[:, 1] * np.exp(1j * triplets[:, 2])
    check(len(seen) == 16 and frequencies is not None, "full S matrix")
    return frequencies, samples, raw_amp, raw_phase

def analyse():
    config, manifest, candidate, text = load()
    freq, S, amp, phase = parse(text)
    wavelengths_nm = C / freq * 1e9
    check(1499 < wavelengths_nm[-1] < 1501 and 1599 < wavelengths_nm[0] < 1601, "wavelength band")
    singular = np.linalg.svd(S, compute_uv=False)
    max_sigma = singular[:, 0]
    # Passive linear S (power-normalized) must have ||S||_2 <= 1.
    tolerance = 1e-9
    nonpassive = max_sigma > 1.0 + tolerance
    col_total = np.sum(np.abs(S) ** 2, axis=1)
    # For input ports 1,2: through paths to opposite side ports 3,4.
    transmitted = col_total[:, :2] - np.sum(np.abs(S[:, :2, :2]) ** 2, axis=1)
    reflected = np.sum(np.abs(S[:, :2, :2]) ** 2, axis=1)
    split = np.stack([
        np.abs(S[:, 2, 0]) ** 2 / (np.abs(S[:, 2, 0]) ** 2 + np.abs(S[:, 3, 0]) ** 2),
        np.abs(S[:, 3, 1]) ** 2 / (np.abs(S[:, 2, 1]) ** 2 + np.abs(S[:, 3, 1]) ** 2),
    ], axis=1)
    check(np.isfinite(split).all() and np.isfinite(singular).all(), "finite spectral measures")
    # Unwrapped phase difference between the two right-going outputs, input port 1.
    # This is a model phase-difference proxy, not physical group delay.
    phase_difference = np.unwrap(np.angle(S[:, 2, 0] / S[:, 3, 0]))
    reciprocity_errors = np.max(np.abs(S - np.swapaxes(S, 1, 2)), axis=(1, 2))
    center = int(np.argmin(abs(wavelengths_nm - 1550)))
    check(0 <= center < 51 and abs(wavelengths_nm[center] - 1550) < 2, "nominal near 1550 sample")
    records = []
    for k in range(len(freq)):
        records.append({
            "frequency_hz": float(freq[k]),
            "wavelength_nm": float(wavelengths_nm[k]),
            "sigma_max": float(max_sigma[k]),
            "nonpassive_screen": bool(nonpassive[k]),
            "reciprocity_max_abs_field": float(reciprocity_errors[k]),
            "input1_collected_power": float(col_total[k, 0]),
            "input2_collected_power": float(col_total[k, 1]),
            "input1_rightward_power": float(transmitted[k, 0]),
            "input2_rightward_power": float(transmitted[k, 1]),
            "input1_leftward_power": float(reflected[k, 0]),
            "input2_leftward_power": float(reflected[k, 1]),
            "input1_bar_split": float(split[k, 0]),
            "input2_cross_split": float(split[k, 1]),
            "input1_output_phase_difference_rad": float(phase_difference[k]),
        })
    # Independent passivity lower bound: each squared column norm <= sigma_max^2.
    check(np.all(col_total <= max_sigma[:, None] ** 2 + 1e-8), "norm versus singular values")
    check(len(records) == 51 and np.all(np.isfinite(phase_difference)), "final spectral rows")
    model_ok = bool(not nonpassive.any())
    report = {
        "experiment": config["experiment"],
        "component": config["component"],
        "source": {"repository": manifest["upstream_repo"], "revision": manifest["upstream_revision"],
                   "path": candidate["path"], "git_blob_sha1": candidate["git_blob_sha1"],
                   "source_kind": config["source_kind"]},
        "model_interpretation": {"power_assumption": config["power_assumption"],
                                 "phase_assumption": config["phase_assumption"],
                                 "port_assumption": config["port_assumption"]},
        "samples": 51,
        "complex_values": int(S.size),
        "wavelength_range_nm": [float(min(wavelengths_nm)), float(max(wavelengths_nm))],
        "center": records[center],
        "passivity": {
            "criterion": "largest singular value <= 1+1e-9 for each frequency if power-normalized",
            "max_sigma_global": float(np.max(max_sigma)),
            "min_sigma_max": float(np.min(max_sigma)),
            "nonpassive_frequencies": int(nonpassive.sum()),
            "all_samples_pass_conditional_screen": model_ok,
            "conditional_numerical_usage": "passivity_screen_only" if model_ok else "quarantined_nonpassive",
        },
        "reciprocity": {"max_abs_field_disagreement": float(np.max(reciprocity_errors)),
                        "not_independent_device_measurement": True},
        "power": {"input1_collected_range": list(map(float, (min(col_total[:,0]), max(col_total[:,0])))),
                  "input1_rightward_range": list(map(float, (min(transmitted[:,0]), max(transmitted[:,0])))),
                  "input1_leftward_range": list(map(float, (min(reflected[:,0]), max(reflected[:,0])))),
                  "input1_split_range": list(map(float, (min(split[:,0]), max(split[:,0]))))},
        "phase": {"input1_output_phase_difference_rad_range": list(map(float, (min(phase_difference), max(phase_difference)))),
                  "model_only": True, "group_delay_not_reported": True},
        "scope": {"exact_gds_model_equivalence": config["exact_cell_geometry_match"],
                  "measured_complex_s": config["measured_complex_s"],
                  "fabrication_qualified": config["fabrication_qualified"],
                  "calibration_eligible": config["calibration_eligible"],
                  "missing": config["requires"]},
        "checks": {"upstream_blob_identity": True, "all_816_complex_entries": True,
                   "wavelength_consistency": True, "full_singular_spectrum": True,
                   "crosscheck_column_norms": True, "right_and_left_power_separation": True,
                   "phase_proxy_explicit": True, "no_measured_or_qualified_claim": True},
        "limitations": [
            "The upstream optical model is not independently proven to be an experiment of the exact GDS geometry.",
            "Phase is interpreted as radians solely to test the upstream tabulation; phase convention and reference planes are unknown.",
            "Singular-value passivity is conditional on native field coefficients being appropriately power-normalized.",
            "Collected four-port power does not measure external radiation or propagation loss independently.",
            "No group delay, EO bandwidth, real silicon fabrication measurements or calibration are inferred.",
            "The measured Twente TFLN results and nonpassive Luxtelligence directional-coupler fit are separate evidence.",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    with (OUT / "spectral-audit.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    print(json.dumps(report, indent=2, allow_nan=False))

if __name__ == "__main__":
    analyse()
