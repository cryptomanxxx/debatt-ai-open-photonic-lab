"""Audit archived NL019 evidence and report descriptive paired effects."""
import csv
import hashlib
import itertools
import json
import math
import struct
from collections import defaultdict
from pathlib import Path

ROOT = Path("results/opa-nl-019")
KEY = ("panel", "candidate", "on_ps", "gap_ps", "response_ps", "lo_mw", "fc_ghz", "readout", "drive_mw")
SETTINGS = ((42,2.,120),(42,3.,120))
ANCHORS = ("end","eighth_mean","quarter_mean","half_mean")
METHODS = ANCHORS+("frozen_ridge16","fresh_ridge16","margin16_balanced","margin16_low")
RIDGES = METHODS[4:]

def methods(on):
    require(on==42,"timing")
    return METHODS

def anchors(on,method):
    require(on==42,"timing")
    extra={"fresh_ridge16":("frozen_ridge16",),
           "margin16_balanced":("fresh_ridge16","frozen_ridge16"),
           "margin16_low":("fresh_ridge16","frozen_ridge16","margin16_balanced")}
    return ANCHORS+extra.get(method,())

def taps(method):
    return 16

SEEDS = tuple(range(1301, 1306))
PANELS = ("exploratory",)
N = 2048


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(name):
    with (ROOT / name).open(newline="") as f:
        return list(csv.DictReader(f))


def key(r):
    return tuple(r[k] if k in ("panel", "candidate", "readout") else float(r[k]) for k in KEY)


def flag(r, name):
    require(r[name] in ("True", "False"), "invalid flag")
    return r[name] == "True"


def stats(values):
    v = list(values)
    require(bool(v) and all(math.isfinite(x) for x in v), "empty or nonfinite")
    return dict(min=min(v), mean=sum(v)/len(v), max=max(v))


def main():
    manifest = json.loads((ROOT / "provenance.json").read_text())
    require(manifest["experiment"] == "OPA-NL-019" and manifest["workflow_run_id"] == 44409237897
            and len(manifest["files"]) == 15, "archive identity")
    for name, info in manifest["files"].items():
        raw = (ROOT / name).read_bytes()
        require(len(raw) == info["bytes"] and hashlib.sha256(raw).hexdigest() == info["sha256"], name)
    rows = read("metrics.csv")
    resolution = read("resolution_metrics.csv")
    groups = read("summary.csv")
    resolution_groups = read("resolution_groups.csv")
    paired = read("paired_readouts.csv")
    pairs = read("common_drive_pairs.csv")
    records = json.loads((ROOT / "coefficients.json").read_text())
    require((len(rows), len(resolution), len(groups), len(resolution_groups), len(paired), len(pairs), len(records))
            == (160, 480, 32, 96, 3520, 16, 8), "row counts")
    source_records=json.loads(Path("results/opa-nl-018/coefficients.json").read_text())
    source={(r["candidate"],r["on_ps"],r["gap_ps"],r["response_ps"],r["lo_mw"],r["fc_ghz"],r["readout"]):r for r in source_records}
    coeff = {}
    for r in records:
        k = (r["candidate"], r["on_ps"], r["gap_ps"], r["response_ps"], r["lo_mw"], r["fc_ghz"], r["readout"])
        v = r["coefficients"]
        require(k not in coeff and len(v) == taps(k[-1]) and r["taps"]==len(v) and all(math.isfinite(x) for x in v), "coefficient key")
        require(hashlib.sha256(struct.pack("<" + "d"*len(v), *v)).hexdigest() == r["sha256"], "coefficient digest")
        require(len(r["lag_block_l2_norms"])==len(v)//8 and all(math.isclose(n,math.sqrt(sum(x*x for x in v[i:i+8])),rel_tol=1e-12,abs_tol=1e-15) for i,n in zip(range(0,len(v),8),r["lag_block_l2_norms"])), "lag block norms")
        norm=math.sqrt(sum(x*x for x in v))
        require(norm>0 and math.isclose(norm,r["l2_norm"],rel_tol=1e-12),"coefficient norm")
        require(len(r["normalized_direction"])==16 and all(math.isclose(x/norm,y,rel_tol=1e-12,abs_tol=1e-15) for x,y in zip(v,r["normalized_direction"])),"normalized direction")
        if k[-1]=="frozen_ridge16":
            old=k[:-1]+("ridge16",)
            require(old in source and source[old]["sha256"]==r["sha256"] and source[old]["coefficients"]==v,"frozen NL018 identity")
        else:
            require(r["domains"]==list(range(10704,10709)) and r["calibration_rows"]==40960 and r["source"]=="NL019_calibration","calibration identity")
        if k[-1].startswith("margin"):
            require(r["optimizer_success"] is True and r["optimizer_status"]==0 and 0<=r["gradient_inf"]<=1e-5 and r["objective_final"]<r["objective_initial"] and r["temperature"]==.1 and r["lambda_"]==.01,"optimizer")
            triples=list(zip(r["calibration_group_seeds"],r["calibration_group_drives"],r["group_weights"]))
            require(len(triples)==10 and {(seed,drive) for seed,drive,w in triples}==set(itertools.product(SEEDS,(.1,1.))),"calibration groups")
            require(all(w==(.1 if k[-1]=="margin16_balanced" else .16 if drive==.1 else .04) for seed,drive,w in triples),"group weights")
        coeff[k] = r
    expected = {(p, "C2", on, 0, 5, lo, fc, m, d) for p, (on,lo,fc), m, d
                in itertools.product(PANELS, SETTINGS, METHODS, (.1,1.)) if m in methods(on)}
    ri = {}
    grouped = defaultdict(list)
    for r in resolution:
        k = key(r)
        seed, level = int(r["seed"]), int(r["resolution_level"])
        rk = k+(seed,level)
        require(rk not in ri and k in expected and seed in SEEDS and level in range(3), "resolution seed key")
        ri[rk] = r
        grouped[k+(level,)].append(r)
        require(r["coefficient_sha256"] == (coeff[k[1:-1]]["sha256"] if k[-2] in RIDGES else ""), "coefficient link")
        norm=float(r["coefficient_l2_norm"])
        expected_norm=coeff[k[1:-1]]["l2_norm"] if k[-2] in RIDGES else 1.
        require(math.isclose(norm,expected_norm,rel_tol=1e-12),"row norm")
        for normalized,raw in (("normalized_electrical_noise_variance_a2","electrical_noise_variance_a2"),("normalized_electrical_noise_amplification","electrical_noise_amplification")):
            require(math.isclose(float(r[normalized]),float(r[raw])/norm**2,rel_tol=1e-12,abs_tol=1e-20),"normalized noise")
        counts = [int(r[f"combined_correct_r{i}"]) for i in range(8)]
        require(all(0 <= n <= N for n in counts) and min(counts)/N == float(r["combined_worst"]), "repeat counts")
        for arm in ("electrical", "combined"):
            passed = (flag(r,"stationary_eligible") and float(r["unfiltered_accuracy"]) >= .95
                      and float(r["clean_filtered_accuracy"]) >= .95 and float(r[arm+"_worst"]) >= .95
                      and float(r[arm+"_peak_diode_mw"]) <= 2)
            require(flag(r,arm+"_pass") == passed, "seed gate")
    require(set(ri) == {k+(seed,level) for k in expected for seed in SEEDS for level in range(3)}, "resolution coverage")
    primary = {key(r)+(int(r["seed"]),):r for r in rows}
    require(len(primary)==160 and all(r==ri[k+(2,)] for k,r in primary.items()), "primary identity")
    rg = {}
    for g in resolution_groups:
        k = key(g)+(int(g["resolution_level"]),)
        require(k not in rg and k in grouped, "resolution group key")
        rg[k] = g
        rr = grouped[k]
        require(len(rr)==5, "group seed count")
        for src,dst,fn in (("unfiltered_accuracy","unfiltered_min",min),
                           ("clean_filtered_accuracy","clean_min",min),
                           ("combined_peak_diode_mw","combined_peak_diode_mw",max),
                           ("electrical_worst","electrical_worst",min),
                           ("combined_worst","combined_worst",min)):
            require(fn(float(r[src]) for r in rr)==float(g[dst]), "group metric "+dst)
        for name in ("stationary_eligible","electrical_pass","combined_pass"):
            require(all(flag(r,name) for r in rr)==flag(g,name), "group gate "+name)
    require(set(rg)==set(grouped), "group coverage")
    gm = {}
    for g in groups:
        k = key(g)
        require(k not in gm and k in expected, "primary group key")
        gm[k] = g
        require(all(g[n]==v for n,v in rg[k+(2,)].items()), "primary group identity")
        stable = all(flag(rg[k+(1,)],arm+"_pass")==flag(g,arm+"_pass") for arm in ("electrical","combined"))
        require(flag(g,"numerically_stable_gate")==stable
                and flag(g,"confirmed_combined_pass")== (stable and flag(g,"combined_pass")), "confirmed group")
    require(set(gm)==expected, "primary groups coverage")
    seen = set()
    for p in pairs:
        k = (p["candidate"],float(p["on_ps"]),float(p["gap_ps"]),float(p["response_ps"]),
             float(p["lo_mw"]),float(p["fc_ghz"]),p["readout"])
        require(k not in seen, "duplicate pair")
        seen.add(k)
        selected=[]
        for panel,drive in itertools.product(PANELS,(.1,1.)):
            g=gm[(panel,)+k+(drive,)]
            suffix="low" if drive==.1 else "high"
            require(float(p["combined_worst_"+suffix])==float(g["combined_worst"]), "drive pair")
            selected.append(g)
        require(float(p["maximin"])==min(float(g["combined_worst"]) for g in selected)
                and flag(p,"passes_both_drives")==all(flag(g,"confirmed_combined_pass") for g in selected)
                and flag(p,"robustness_target_met")== (flag(p,"passes_both_drives") and float(p["maximin"])>=.96), "common-drive gate")
    require(seen=={k[1:-1] for k in expected}, "pair coverage")
    aggregate = defaultdict(lambda:[0,0,0,0])
    seed_aggregate = defaultdict(lambda:[0,0,0,0])
    seen = set()
    for r in paired:
        k=key(r)
        seed,rep=int(r["seed"]),int(r["repeat"])
        anchor=r["anchor"]
        pk=k+(seed,anchor,rep)
        require(pk not in seen and k[-2] in RIDGES and anchor in anchors(k[2],k[-2])
                and 0<=rep<8 and int(r["resolution_level"])==2, "paired key")
        seen.add(pk)
        a=primary[k+(seed,)]
        b=primary[k[:-2]+(anchor,k[-1],seed)]
        n=[int(r[x]) for x in ("both_correct","equalizer_only","anchor_only","neither")]
        require(min(n)>=0 and sum(n)==N and n[0]+n[1]==int(a[f"combined_correct_r{rep}"])
                and n[0]+n[2]==int(b[f"combined_correct_r{rep}"]), "paired marginals")
        for i,v in enumerate(n):
            aggregate[k+(anchor,)][i]+=v
            seed_aggregate[k+(anchor,seed)][i]+=v
    require(seen=={k+(seed,anchor,rep) for k in expected if k[-2] in RIDGES
                   for seed in SEEDS for anchor in anchors(k[2],k[-2]) for rep in range(8)}, "paired coverage")
    # Recompute every archived paired summary from the full raw contingency table.
    summaries=read("paired_summary.csv")
    require(len(summaries)==88, "paired summary count")
    observed=set()
    for r in summaries:
        k=(r["panel"],"C2",float(r["on_ps"]),0.,5.,float(r["lo_mw"]),float(r["fc_ghz"]),
           r["readout"],float(r["drive_mw"]),r["anchor"])
        require(k in aggregate and k not in observed, "summary key")
        observed.add(k)
        both,eq,base,neither=aggregate[k]
        require([both,eq,base,neither]==[int(r[n]) for n in
                ("both_correct","equalizer_only","anchor_only","neither")], "summary counts")
        require(int(r["net_correct"])==eq-base and float(r["accuracy_delta"])==(eq-base)/(both+eq+base+neither),
                "summary effect")
    require(observed==set(aggregate), "summary coverage")
    summary=[]
    for k in sorted(expected):
        rr=[r for r in rows if key(r)==k]
        entry=dict(zip(KEY,k))
        entry["seeds"]=[dict(seed=int(r["seed"]),combined_worst=float(r["combined_worst"]),electrical_worst=float(r["electrical_worst"]),repeat_correct=[int(r[f"combined_correct_r{i}"]) for i in range(8)]) for r in rr]
        for name in ("combined_worst","clean_filtered_accuracy","electrical_worst","electrical_noise_amplification",
                     "normalized_electrical_noise_amplification","normalized_electrical_noise_variance_a2","clean_target_rmse_a","first8_combined_accuracy","last8_combined_accuracy",
                     "combined_peak_diode_mw","signal_plus_lo_electric_lower_mw","max_optical_memory_field"):
            entry[name]=stats(float(r[name]) for r in rr)
        if k[-2] in RIDGES:
            rec=coeff[k[1:-1]]
            fresh=coeff[k[1:-2]+("fresh_ridge16",)]
            entry["coefficient"]={n:rec[n] for n in ("sha256","l2_norm","normalized_direction","lag_block_l2_norms")}
            entry["coefficient"]["cosine_vs_fresh"]=sum(x*y for x,y in zip(rec["normalized_direction"],fresh["normalized_direction"]))
            entry["paired"]={}
            for anchor in anchors(k[2],k[-2]):
                both,eq,base,neither=aggregate[k+(anchor,)]
                entry["paired"][anchor]=dict(both_correct=both,equalizer_only=eq,anchor_only=base,neither=neither,
                                             net_correct=eq-base,accuracy_delta=(eq-base)/(both+eq+base+neither),
                                             seed_net={str(seed):seed_aggregate[k+(anchor,seed)][1]-seed_aggregate[k+(anchor,seed)][2] for seed in SEEDS})
        summary.append(entry)
    require(len(summary)==32,"summary group coverage")
    report=json.loads((ROOT/"result.json").read_text())
    require(len(report["checks"])==30 and all(v is True for v in report["checks"].values()) and not report["failures"] and report["proposed_confirmation_candidate"] is None and report["ranked_qualifying_candidates"]==[],"result identity")
    print(json.dumps(dict(verified=True,source_run=44409237897,primary_rows=len(rows),
                          resolution_rows=len(resolution),paired_rows=len(paired),groups=summary,
                          note="Descriptive matched counts, not independent observations or measured power."),
                     indent=2,allow_nan=False))


if __name__=="__main__":
    main()
