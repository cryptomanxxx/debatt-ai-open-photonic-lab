"""Audit archived NL018 evidence and report descriptive paired effects."""
import csv
import hashlib
import itertools
import json
import math
import struct
from collections import defaultdict
from pathlib import Path

ROOT = Path("results/opa-nl-018")
KEY = ("panel", "candidate", "on_ps", "gap_ps", "response_ps", "lo_mw", "fc_ghz", "readout", "drive_mw")
SETTINGS = ((41,3.,80),(42,2.,120),(42,3.,120))
ANCHORS = ("end","eighth_mean","quarter_mean","half_mean")
CONTROL = ANCHORS+("ridge8","ridge16","ridge16_strong")
CANDIDATE = ANCHORS+("frozen_ridge16","frozen_ridge16_midlow","ridge16","ridge16_midlow",
                     "ridge24_midlow","ridge32_midlow")
METHODS = tuple(dict.fromkeys(CONTROL+CANDIDATE))
RIDGES = tuple(m for m in METHODS if m not in ANCHORS)

def methods(on):
    return CONTROL if on==42 else CANDIDATE

def anchors(on,method):
    if on==42:return ANCHORS+(("ridge8",) if method=="ridge16" else ())
    extra={"frozen_ridge16_midlow":("frozen_ridge16",),"ridge16":("frozen_ridge16",),
           "ridge16_midlow":("frozen_ridge16_midlow",),"ridge24_midlow":("ridge16_midlow",),
           "ridge32_midlow":("ridge16_midlow","ridge24_midlow")}
    return ANCHORS+extra.get(method,())

def taps(method):
    return 8 if method=="ridge8" else 24 if method.startswith("ridge24") else 32 if method.startswith("ridge32") else 16

SEEDS = tuple(range(1301, 1306))
PANELS = ("A","B")
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
    require(manifest["experiment"] == "OPA-NL-018" and manifest["workflow_run_id"] == 44387159815
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
            == (480, 1440, 96, 288, 8960, 24, 12), "row counts")
    source_records=json.loads(Path("results/opa-nl-017/coefficients.json").read_text())
    source={(r["candidate"],r["on_ps"],r["gap_ps"],r["response_ps"],r["lo_mw"],r["fc_ghz"],r["readout"]):r for r in source_records}
    coeff = {}
    for r in records:
        k = (r["candidate"], r["on_ps"], r["gap_ps"], r["response_ps"], r["lo_mw"], r["fc_ghz"], r["readout"])
        v = r["coefficients"]
        require(k not in coeff and len(v) == taps(k[-1]) and r["taps"]==len(v) and all(math.isfinite(x) for x in v), "coefficient key")
        require(hashlib.sha256(struct.pack("<" + "d"*len(v), *v)).hexdigest() == r["sha256"], "coefficient digest")
        require(len(r["lag_block_l2_norms"])==len(v)//8 and all(math.isclose(n,math.sqrt(sum(x*x for x in v[i:i+8])),rel_tol=1e-12,abs_tol=1e-15) for i,n in zip(range(0,len(v),8),r["lag_block_l2_norms"])), "lag block norms")
        require(k in source and source[k]["sha256"]==r["sha256"] and source[k]["coefficients"]==v, "frozen NL017 identity")
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
        counts = [int(r[f"combined_correct_r{i}"]) for i in range(8)]
        require(all(0 <= n <= N for n in counts) and min(counts)/N == float(r["combined_worst"]), "repeat counts")
        for arm in ("electrical", "combined"):
            passed = (flag(r,"stationary_eligible") and float(r["unfiltered_accuracy"]) >= .95
                      and float(r["clean_filtered_accuracy"]) >= .95 and float(r[arm+"_worst"]) >= .95
                      and float(r[arm+"_peak_diode_mw"]) <= 2)
            require(flag(r,arm+"_pass") == passed, "seed gate")
    require(set(ri) == {k+(seed,level) for k in expected for seed in SEEDS for level in range(3)}, "resolution coverage")
    primary = {key(r)+(int(r["seed"]),):r for r in rows}
    require(len(primary)==480 and all(r==ri[k+(2,)] for k,r in primary.items()), "primary identity")
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
            suffix=panel+("_low" if drive==.1 else "_high")
            require(float(p["combined_worst_"+suffix])==float(g["combined_worst"])
                    and flag(p,"passed_"+suffix)==flag(g,"confirmed_combined_pass"), "drive panel pair")
            selected.append(g)
        require(float(p["maximin"])==min(float(g["combined_worst"]) for g in selected)
                and flag(p,"passes_both_drives_both_panels")==all(flag(g,"confirmed_combined_pass") for g in selected), "common-drive gate")
    require(seen=={k[1:-1] for k in expected}, "pair coverage")
    aggregate = defaultdict(lambda:[0,0,0,0])
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
    require(seen=={k+(seed,anchor,rep) for k in expected if k[-2] in RIDGES
                   for seed in SEEDS for anchor in anchors(k[2],k[-2]) for rep in range(8)}, "paired coverage")
    # Recompute every archived paired summary from the full raw contingency table.
    summaries=read("paired_summary.csv")
    require(len(summaries)==224, "paired summary count")
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
                     "clean_target_rmse_a","first8_combined_accuracy","last8_combined_accuracy",
                     "combined_peak_diode_mw","signal_plus_lo_electric_lower_mw","max_optical_memory_field"):
            entry[name]=stats(float(r[name]) for r in rr)
        if k[-2] in RIDGES:
            entry["paired"]={}
            for anchor in anchors(k[2],k[-2]):
                both,eq,base,neither=aggregate[k+(anchor,)]
                entry["paired"][anchor]=dict(both_correct=both,equalizer_only=eq,anchor_only=base,neither=neither,
                                             net_correct=eq-base,accuracy_delta=(eq-base)/(both+eq+base+neither))
        summary.append(entry)
    require(len(summary)==96,"summary group coverage")
    print(json.dumps(dict(verified=True,source_run=44387159815,primary_rows=len(rows),
                          resolution_rows=len(resolution),paired_rows=len(paired),groups=summary,
                          note="Descriptive matched counts, not independent observations or measured power."),
                     indent=2,allow_nan=False))


if __name__=="__main__":
    main()
