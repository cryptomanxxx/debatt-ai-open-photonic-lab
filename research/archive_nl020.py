"""Verify exact NL020 ZIP and CI-emitted science hashes; archive without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

RUN=44492281387
ARTIFACT=14513522210
ZIP_SHA="299ba43c879ca6f80213c6946a0fb64194b5f5268dc5ab0b2021244193834e85"
ZIP_SIZE=197602
EXPECTED={
    "coefficient_summary.csv":(7499,"c7603a65231911d6d12f03d0a64f4db52279ea0fcd978b70ec3e73ce8bebd940"),
    "coefficients.json":(83869,"b12092535c28f5d1edb94436c3571e023c23708842046ea83c60342b36a7fec3"),
    "common_drive_pairs.csv":(2198,"eca1ec054dc0554bdcdd6541df168d1ff34c65d4c7ccf078f1b539bb748fd973"),
    "convergence.csv":(564,"2933d60c1f6f8c3a9c510998fd62dc8b94ccf1aa958235bc5cbde59e935c576b"),
    "environment-lock.txt":(9532,"a413f375d4a3097d7cb7c9922da7288e15ad77026afdcb11d8f6945375ee8c4c"),
    "installed-packages.json":(68543,"f8bf20346f3dcd14fac94e7b91949ca983197c352d906a00e6b8152b0acf60f6"),
    "metrics.csv":(144819,"5e672ef87ff685ebd09c53a40b36d84a990bb947a0e5a028992e6bfff4dcd067"),
    "nl019_seed_analysis.json":(160387,"2cd4ad49d52f6ceabf86973601aea65b110a4038c49b52dffccdab307ddfcca4"),
    "optical_audit.csv":(574,"4f452e20ffe5fe5496e5c3012756a164d79860e1f762b72fbd219221a2244a29"),
    "paired_readouts.csv":(597933,"d7a4595cf55b5467a26185ca7b48b09e150be28abea97b97890c6af1ac3bfe23"),
    "paired_summary.csv":(12685,"8384ea153082cc760cfdcb04a3c0d29dde90bf9f45a54a14d35d7c2a5182d827"),
    "resolution_groups.csv":(18080,"0d70a960195943a93688aa17b71051bf57ce250fadee42ad2283c6c446490b64"),
    "resolution_metrics.csv":(431965,"7cb12a7264ab7910cf54c61e88635b7660f13e3fcd84e7faeef2d1fc5312936e"),
    "result.json":(37290,"4dfff6adef00832238344b41d0bef4f458a730c02be19affac2171645579b6a3"),
    "summary.csv":(7349,"df381a7db8213c7d4ebcc628807573a9399d666819df2508df8ace0cf563fbce"),
}
NAMES=set(EXPECTED)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def verify_science(files):
    if set(files)!=NAMES:
        raise ValueError("unexpected evidence names")
    for name,(size,digest) in EXPECTED.items():
        if (len(files[name]),sha(files[name]))!=(size,digest):
            raise ValueError("CI science hash mismatch: "+name)
    report=json.loads(files["result.json"])
    contrasts=report["robust_contrasts"]
    expected=[
        (42,2.,120,"robust16_softmax",.962890625,.99951171875,-.00048828125,4),
        (42,2.,120,"robust16_repeat",.962890625,.99951171875,-.00048828125,4),
        (42,3.,120,"robust16_softmax",.962890625,.99951171875,-.00048828125,12),
        (42,3.,120,"robust16_repeat",.962890625,.99951171875,-.00048828125,14),
    ]
    fields=("on_ps","lo_mw","fc_ghz","readout","combined_worst_low","combined_worst_high",
            "low_worst_delta_vs_fresh_margin","low_net_vs_fresh_margin")
    pairs=report["all_common_drive_pairs"]
    if (report["experiment"]!="OPA-NL-020" or len(report["checks"])!=32
        or not all(v is True for v in report["checks"].values()) or report["failures"]
        or report["rows"]!=200 or report["groups"]!=40
        or report["resolution_groups"]!=120
        or report["combined_passing_groups"]!=28 or report["ambiguous_groups"]!=0
        or len(pairs)!=20
        or len(report["common_exploratory_passes"])!=12
        or sum(p["robustness_target_met"] for p in pairs)!=8
        or [(p["lo_mw"],p["combined_worst_low"],p["combined_worst_high"]) for p in pairs if p["readout"]=="frozen_margin16_low"]!=[(2.,.96337890625,.99951171875),(3.,.9638671875,.99951171875)]
        or [(p["lo_mw"],p["combined_worst_low"],p["combined_worst_high"]) for p in pairs if p["readout"]=="margin16_low"]!=[(2.,.96337890625,.99951171875),(3.,.96337890625,.99951171875)]
        or report["independent_confirmation_passed"] is not False
        or report["historical_cadence_gsymbol_s"]!=1000/42
        or report["ranked_qualifying_candidates"]!=[]
        or report["proposed_confirmation_candidate"] is not None
        or [tuple(p[k] for k in fields) for p in contrasts]!=expected
        or report["primary_contrast"]!=contrasts[0]
        or any(p["qualifies"] or not p["robustness_target_met"] or not p["passes_both_drives"]
               or p["limiting_seed_repeats"]!=[{"seed":1303,"repeats":[1]}] for p in contrasts)
        or len(report["historical_references"])!=4
        or not all(p["passes_both_drives"] for p in report["historical_references"])
        or len(report["matched_robust_comparisons"])!=24
        or len(report["matched_recalibration_comparisons"])!=8
        or len(report["matched_margin_comparisons"])!=4
        or len(report["matched_risk_comparisons"])!=4
        or report["margin_gradient_error"]>=1e-6 or report["robust_gradient_error"]>=1e-6
        or len(report["convergence"])!=2
        or any(p["changed_group_gates"] or p["changed_seed_gates"] for p in report["convergence"])):
        raise ValueError("unexpected report")

def read_zip(path):
    raw=path.read_bytes()
    if len(raw)!=ZIP_SIZE or sha(raw)!=ZIP_SHA:
        raise ValueError("ZIP identity mismatch")
    with zipfile.ZipFile(path) as z:
        info=z.infolist()
        if len(info)!=len(NAMES) or {i.filename for i in info}!=NAMES:
            raise ValueError("unexpected ZIP entries")
        if any(i.is_dir() or stat.S_ISLNK(i.external_attr>>16) or i.file_size!=EXPECTED[i.filename][0] for i in info):
            raise ValueError("invalid ZIP entry")
        if z.testzip() is not None:
            raise ValueError("CRC failure")
        files={i.filename:z.read(i) for i in info}
    verify_science(files)
    return files

def manifest(files):
    return (json.dumps(dict(experiment="OPA-NL-020",workflow_run_id=RUN,
        job_id=135450777884,artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,
        artifact_bytes=ZIP_SIZE,head_sha="2e672fd323a887728594f85fa13d5a711ec0d5fe",
        merge_sha="a5876d4a3f12d7d882cf3f0c4234b10cfd079fcf",pull_request=203,
        verification="Raw ZIP pinned to GitHub metadata; CRC and all fifteen file hashes pinned to CI stdout; staged bytes compared to verified ZIP.",
        files={n:dict(bytes=len(b),sha256=sha(b)) for n,b in files.items()}),
        indent=2,sort_keys=True)+"\n").encode()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--zip",required=True,type=Path)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--output",type=Path)
    g.add_argument("--staged",type=Path)
    a=p.parse_args()
    files=read_zip(a.zip)
    files["provenance.json"]=manifest(files)
    if a.output:
        a.output.mkdir(parents=True,exist_ok=False)
        for name,b in files.items():
            (a.output/name).write_bytes(b)
    else:
        if {p.name for p in a.staged.iterdir()}!=set(files):
            raise ValueError("staged names mismatch")
        for name,b in files.items():
            if (a.staged/name).read_bytes()!=b:
                raise ValueError("staged bytes mismatch: "+name)
    for name,b in sorted(files.items()):
        print(name,len(b),sha(b))
    print("Verified exact NL020 evidence and provenance.")

if __name__=="__main__":
    main()
