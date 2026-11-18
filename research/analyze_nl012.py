"""Verify NL012 archive and summarize paired outcomes without changing evidence."""
import csv
import hashlib
import json
import math
import struct
from collections import defaultdict
from pathlib import Path

ROOT = Path("results/opa-nl-012")
KEY = ("candidate", "on_ps", "gap_ps", "response_ps", "lo_mw", "fc_ghz", "readout", "drive_mw")
ANCHORS = ("end", "eighth_mean", "quarter_mean", "half_mean")
RIDGES = ("ridge8", "ridge16", "ridge16_strong")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(name):
    with (ROOT / name).open(newline="") as f:
        return list(csv.DictReader(f))


def key(r):
    return tuple(r[k] if k in ("candidate", "readout") else float(r[k]) for k in KEY)


def flag(r, name):
    require(r[name] in ("True", "False"), "bad boolean")
    return r[name] == "True"


def stats(v):
    v = list(v)
    require(bool(v) and all(math.isfinite(x) for x in v), "nonfinite or empty")
    return dict(min=min(v), mean=sum(v)/len(v), max=max(v))


def main():
    manifest = json.loads((ROOT / "provenance.json").read_text())
    require(manifest["experiment"] == "OPA-NL-012" and manifest["workflow_run_id"] == 44296016894
            and len(manifest["files"]) == 13, "wrong archive")
    for name, info in manifest["files"].items():
        raw = (ROOT / name).read_bytes()
        require(len(raw) == info["bytes"] and hashlib.sha256(raw).hexdigest() == info["sha256"], name)
    metrics = read("metrics.csv")
    groups = read("summary.csv")
    pairs = read("common_drive_pairs.csv")
    paired = read("paired_readouts.csv")
    coefs = json.loads((ROOT / "coefficients.json").read_text())
    require((len(metrics), len(groups), len(pairs), len(paired), len(coefs)) ==
            (5040, 1008, 504, 69120, 216), "row counts")
    coeff = {}
    for c in coefs:
        k = (c["candidate"], float(c["on_ps"]), float(c["gap_ps"]), float(c["response_ps"]),
             float(c["lo_mw"]), float(c["fc_ghz"]), c["readout"])
        v = c["coefficients"]
        require(k not in coeff and len(v) == (8 if k[-1] == "ridge8" else 16)
                and all(math.isfinite(x) for x in v), "coefficient identity")
        require(hashlib.sha256(struct.pack("<" + "d"*len(v), *v)).hexdigest() == c["sha256"], "coefficient bytes")
        coeff[k] = c
    byseed = {}
    grouped = defaultdict(list)
    for r in metrics:
        k = key(r)
        sk = k + (int(r["seed"]),)
        require(sk not in byseed and int(r["resolution_level"]) == 2, "seed key")
        byseed[sk] = r
        grouped[k].append(r)
        require(r["coefficient_sha256"] == (coeff[k[:-1]]["sha256"] if k[-2] in RIDGES else ""), "coefficient link")
        counts = [int(r[f"combined_correct_r{i}"]) for i in range(8)]
        require(all(0 <= n <= 1024 for n in counts) and min(counts)/1024 == float(r["combined_worst"]), "repeat counts")
        for arm in ("electrical", "combined"):
            expected = (flag(r, "stationary_eligible") and float(r["unfiltered_accuracy"]) >= .95
                        and float(r["clean_filtered_accuracy"]) >= .95 and float(r[arm+"_worst"]) >= .95
                        and float(r[arm+"_peak_diode_mw"]) <= 2)
            require(flag(r, arm+"_pass") == expected, "seed gate")
        require(math.isclose(float(r["signal_plus_lo_electric_lower_mw"]),
                             (float(r["launch_mw"])+float(r["lo_mw"]))/.2, rel_tol=1e-12), "laser bound")
    gm = {key(g): g for g in groups}
    require(len(gm) == len(groups) == len(grouped) and set(gm) == set(grouped), "group keys")
    for k,g in gm.items():
        rows = grouped[k]
        require(len(rows) == 5 and len({r["seed"] for r in rows}) == 5, "seed coverage")
        for src,dst,fn in (
            ("unfiltered_accuracy","unfiltered_min",min),
            ("clean_filtered_accuracy","clean_min",min),
            ("combined_peak_diode_mw","combined_peak_diode_mw",max),
            ("electrical_worst","electrical_worst",min),
            ("combined_worst","combined_worst",min),
        ):
            require(fn(float(r[src]) for r in rows) == float(g[dst]), "group metric "+dst)
        for name in ("stationary_eligible","electrical_pass","combined_pass"):
            require(all(flag(r,name) for r in rows) == flag(g,name), "group gate "+name)
        require(flag(g,"confirmed_combined_pass") == (flag(g,"combined_pass") and flag(g,"numerically_stable_gate")), "confirmed gate")
    seen = set()
    for p in pairs:
        k = key(dict(p, drive_mw=".1"))[:-1]
        require(k not in seen, "duplicate common pair")
        seen.add(k)
        low, high = gm[k+(.1,)], gm[k+(1.,)]
        a,b = float(low["combined_worst"]),float(high["combined_worst"])
        require((a,b,min(a,b)) == tuple(float(p[n]) for n in ("combined_worst_low","combined_worst_high","maximin"))
                and flag(p,"confirmed_both") == (flag(low,"confirmed_combined_pass") and flag(high,"confirmed_combined_pass")), "common pair")
    require(seen == {k[:-1] for k in gm if k[-1] == .1}, "common coverage")
    contingency = defaultdict(lambda: [0,0,0,0])
    seen = set()
    for p in paired:
        k = key(p)
        seed, rep = int(p["seed"]),int(p["repeat"])
        anchor = p["anchor"]
        require(k[-2] in RIDGES and anchor in ANCHORS and 0 <= rep < 8
                and int(p["resolution_level"]) == 2, "paired method")
        pk = k+(seed,anchor,rep)
        require(pk not in seen, "duplicate paired row")
        seen.add(pk)
        a = byseed[k+(seed,)]
        b = byseed[k[:-2]+(anchor,k[-1],seed)]
        n = [int(p[x]) for x in ("both_correct","equalizer_only","anchor_only","neither")]
        require(min(n) >= 0 and sum(n) == 1024, "contingency count")
        require(n[0]+n[1] == int(a[f"combined_correct_r{rep}"])
                and n[0]+n[2] == int(b[f"combined_correct_r{rep}"]), "paired marginals")
        ck = k+(anchor,)
        for i,v in enumerate(n):
            contingency[ck][i] += v
    expected = {k+(seed,anchor,rep) for k in grouped if k[-2] in RIDGES
                for seed in (int(r["seed"]) for r in grouped[k])
                for anchor in ANCHORS for rep in range(8)}
    require(seen == expected, "paired coverage")
    report = []
    for k,rows in sorted(grouped.items()):
        entry = dict(zip(KEY,k))
        entry.update(combined_worst=float(gm[k]["combined_worst"]),
                     confirmed=flag(gm[k],"confirmed_combined_pass"),
                     noise_amplification=stats(float(r["electrical_noise_amplification"]) for r in rows),
                     clean_target_rmse_a=stats(float(r["clean_target_rmse_a"]) for r in rows),
                     laser_lower_mw=stats(float(r["signal_plus_lo_electric_lower_mw"]) for r in rows))
        if k[-2] in RIDGES:
            c = coeff[k[:-1]]
            entry.update(coefficient_l2=math.sqrt(sum(x*x for x in c["coefficients"])),
                         coefficient_condition=c["condition"], coefficient_sha256=c["sha256"])
            entry["paired"] = {}
            for anchor in ANCHORS:
                both,eq,base,neither = contingency[k+(anchor,)]
                entry["paired"][anchor] = dict(both_correct=both,equalizer_only=eq,anchor_only=base,
                                               neither=neither,net_correct=eq-base,
                                               accuracy_delta=(eq-base)/(both+eq+base+neither))
        report.append(entry)
    print(json.dumps(dict(source_run=44296016894,verified=True,groups=report,
                          paired_rows=len(paired),seed_rows=len(metrics),
                          note="Descriptive matched counts; repeats share input examples. No independent-observation significance or measured power claim."),
                     indent=2,allow_nan=False))


if __name__ == "__main__":
    main()
