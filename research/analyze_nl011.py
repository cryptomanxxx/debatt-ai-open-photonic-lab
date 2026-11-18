"""Audit exact NL011 archive and emit seed-derived summaries; never modify archive.

Run from repository root: python research/analyze_nl011.py > /tmp/nl011-analysis.json
"""
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path("results/opa-nl-011")
KEY = ("candidate", "on_ps", "gap_ps", "response_ps", "lo_mw", "fc_ghz", "readout", "drive_mw")


def read(name):
    with (ROOT / name).open(newline="") as f:
        return list(csv.DictReader(f))


def key(row):
    return tuple(row[k] for k in KEY)


def truth(row, name):
    if row[name] not in ("True", "False"):
        raise ValueError(f"invalid flag: {name}")
    return row[name] == "True"


def stats(values):
    values = list(values)
    if not values or not all(math.isfinite(v) for v in values):
        raise ValueError("missing/nonfinite metric")
    return dict(min=min(values), mean=sum(values)/len(values), max=max(values))


def main():
    manifest = json.loads((ROOT / "provenance.json").read_text())
    if manifest["experiment"] != "OPA-NL-011" or manifest["workflow_run_id"] != 44288710042:
        raise ValueError("wrong source")
    for name, v in manifest["files"].items():
        raw = (ROOT / name).read_bytes()
        if len(raw) != v["bytes"] or hashlib.sha256(raw).hexdigest() != v["sha256"]:
            raise ValueError(f"archive mismatch: {name}")
    rows, summary, pairs = read("metrics.csv"), read("summary.csv"), read("common_drive_pairs.csv")
    if (len(rows), len(summary), len(pairs)) != (7680, 1536, 768):
        raise ValueError("row counts")
    grouped = defaultdict(list)
    for row in rows:
        grouped[key(row)].append(row)
    if len(grouped) != len(summary) or len({key(r) for r in summary}) != len(summary):
        raise ValueError("group keys")
    derived = {}
    for g in summary:
        k = key(g)
        v = grouped[k]
        if len(v) != 5 or len({r["seed"] for r in v}) != 5:
            raise ValueError("seed coverage")
        for source, target, fn in (
            ("unfiltered_accuracy", "unfiltered_min", min),
            ("clean_filtered_accuracy", "clean_min", min),
            ("electrical_worst", "electrical_worst", min),
            ("combined_worst", "combined_worst", min),
            ("combined_peak_diode_mw", "combined_peak_diode_mw", max),
        ):
            if fn(float(r[source]) for r in v) != float(g[target]):
                raise ValueError(f"group mismatch {k}: {target}")
        for flag in ("stationary_eligible", "electrical_pass", "combined_pass"):
            if all(truth(r, flag) for r in v) != truth(g, flag):
                raise ValueError(f"gate mismatch {k}: {flag}")
        for r in v:
            lo = float(r["lo_mw"])
            launch = float(r["launch_mw"])
            if not math.isclose(float(r["signal_plus_lo_electric_lower_mw"]), (launch+lo)/.2, rel_tol=1e-12):
                raise ValueError("conditional power formula")
        derived[k] = dict(
            power_mw=stats(float(r["signal_plus_lo_electric_lower_mw"]) for r in v),
            clean_margin_a=stats(float(r["min_clean_signed_current_a"]) for r in v),
            combined_margin_a=stats(float(r["min_combined_signed_current_a"]) for r in v),
            electrical_noise_variance_a2=stats(float(r["electrical_noise_variance_a2"]) for r in v),
            first8=stats(float(r["first8_combined_accuracy"]) for r in v),
            last8=stats(float(r["last8_combined_accuracy"]) for r in v),
        )
    bykey = {key(g): g for g in summary}
    candidates = []
    seen = set()
    for p in pairs:
        k = tuple(p[x] for x in KEY[:-1])
        if k in seen:
            raise ValueError("duplicate pair")
        seen.add(k)
        low, high = k+("0.1",), k+("1.0",)
        # CSV writer may spell integer-valued drive as 1 rather than 1.0.
        if high not in bykey:
            high = k+("1",)
        a, b = bykey[low], bykey[high]
        if (float(p["combined_worst_low"]) != float(a["combined_worst"])
                or float(p["combined_worst_high"]) != float(b["combined_worst"])
                or float(p["maximin"]) != min(float(a["combined_worst"]), float(b["combined_worst"]))
                or truth(p, "confirmed_both") != (truth(a, "confirmed_combined_pass") and truth(b, "confirmed_combined_pass"))):
            raise ValueError("pair mismatch")
        candidates.append(dict(pair=p, low=derived[low], high=derived[high],
                               worst_accuracy=float(p["maximin"]),
                               worst_drive_seed_power_mw=max(derived[low]["power_mw"]["max"], derived[high]["power_mw"]["max"])))
    # Within each optical timing only; no false power comparison across cadence.
    frontier = []
    for c in candidates:
        p = c["pair"]
        peers = [x for x in candidates if all(x["pair"][k] == p[k] for k in KEY[:4])]
        if not any(x["worst_accuracy"] >= c["worst_accuracy"]
                   and x["worst_drive_seed_power_mw"] <= c["worst_drive_seed_power_mw"]
                   and (x["worst_accuracy"] > c["worst_accuracy"]
                        or x["worst_drive_seed_power_mw"] < c["worst_drive_seed_power_mw"]) for x in peers):
            frontier.append(c)
    print(json.dumps(dict(source_run=44288710042, rows=len(rows), groups=len(summary), pairs=len(pairs),
                          note="Conditional laser-only lower bounds; no ADC, receiver, distribution or phase control.",
                          frontier=frontier, all_pairs=candidates), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
