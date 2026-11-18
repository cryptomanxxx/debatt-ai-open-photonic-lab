"""Verify exact NL019 ZIP and CI-emitted science hashes; archive without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

RUN=44409237897
ARTIFACT=14475309037
ZIP_SHA="17a7ed1175c4fdee87539eadd7e9999f4f7d54c9ce55556be656cf0029672d40"
ZIP_SIZE=169652
EXPECTED={
    "coefficient_summary.csv":(5040,"037d31d118d2678ab9a72290c0e3230eee78a3b9ae3a319156b92b0749fc7a1f"),
    "coefficients.json":(18708,"26e559ffc97b599a0b1447074cac7a79bae78ac641303e679c171285faa90f2f"),
    "common_drive_pairs.csv":(1702,"80de2144897f2c3e8a1dd46492b510d75d293f4c3b74fe8caf6c47ace20777dc"),
    "convergence.csv":(564,"39ead66b8bdbe7133ea131e40ad61ee8722864898883cafcf2d1d5698bdccbf1"),
    "environment-lock.txt":(9532,"a413f375d4a3097d7cb7c9922da7288e15ad77026afdcb11d8f6945375ee8c4c"),
    "installed-packages.json":(68543,"f8bf20346f3dcd14fac94e7b91949ca983197c352d906a00e6b8152b0acf60f6"),
    "metrics.csv":(114716,"80dc7dbb47e16c104b8c9dbaa121848425b68c29d390709a5cc62f41e9831565"),
    "nl018_seed_analysis.json":(357919,"e02922abfd7032c94853a060b624075c5b956c7c6e5c818a7683979d7b690a21"),
    "optical_audit.csv":(577,"92a3a64e2fdc561e4056b4d945fcba818c148b9376b3faf606fc10ca67628a0c"),
    "paired_readouts.csv":(380139,"baaf6ce24d37dcb3b3cc68240d69b93e2b0bdcd37b2e05d3eca9083807abd89d"),
    "paired_summary.csv":(8177,"45f08211233e8f9435ee27c30610c9ae39a8128789e82d9d6c03790bcc76195d"),
    "resolution_groups.csv":(14058,"f0405cbb509685c453f9d022401b28da445c930b7de6c48966d4ae2adbcd372d"),
    "resolution_metrics.csv":(341550,"86e353a0d126047bba74f69130879623af2bf9bea7c8108270b5bd89650e20a2"),
    "result.json":(26954,"eb025c626ac0d1d915d2a2c483681a6a4f87952793d5aff9d6493741bfd8b271"),
    "summary.csv":(5911,"d1e4223b6092772d4443248cdf6993a6a584b4c8dcf8a3ff5b54eae49c453e2b"),
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
    contrasts=report["margin_contrasts"]
    expected=[
        (42,2.,120,"margin16_balanced",.95751953125,1.,.00244140625,417),
        (42,2.,120,"margin16_low",.958984375,1.,.00390625,452),
        (42,3.,120,"margin16_balanced",.95849609375,1.,.0029296875,436),
        (42,3.,120,"margin16_low",.9599609375,1.,.00439453125,469),
    ]
    fields=("on_ps","lo_mw","fc_ghz","readout","combined_worst_low","combined_worst_high",
            "low_worst_delta_vs_fresh","low_net_vs_fresh")
    if (report["experiment"]!="OPA-NL-019" or len(report["checks"])!=30
        or not all(v is True for v in report["checks"].values()) or report["failures"]
        or report["rows"]!=160 or report["groups"]!=32
        or report["resolution_groups"]!=96
        or report["combined_passing_groups"]!=20 or report["ambiguous_groups"]!=0
        or len(report["all_common_drive_pairs"])!=16
        or len(report["common_exploratory_passes"])!=8
        or any(p["robustness_target_met"] for p in report["all_common_drive_pairs"])
        or report["independent_confirmation_passed"] is not False
        or report["historical_cadence_gsymbol_s"]!=1000/42
        or report["ranked_qualifying_candidates"]!=[]
        or report["proposed_confirmation_candidate"] is not None
        or [tuple(p[k] for k in fields) for p in contrasts]!=expected
        or report["primary_contrast"]!=contrasts[0]
        or any(p["qualifies"] or p["robustness_target_met"] or not p["passes_both_drives"]
               or p["limiting_seed_repeats"]!=[{"seed":1303,"repeats":[3]}] for p in contrasts)
        or len(report["historical_references"])!=2
        or not all(p["passes_both_drives"] for p in report["historical_references"])
        or len(report["matched_margin_comparisons"])!=16
        or len(report["matched_recalibration_comparisons"])!=4
        or len(report["matched_weighting_comparisons"])!=4
        or report["margin_gradient_error"]>=1e-6
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
    return (json.dumps(dict(experiment="OPA-NL-019",workflow_run_id=RUN,
        job_id=135172718163,artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,
        artifact_bytes=ZIP_SIZE,head_sha="3ea0d1ede9610f42a3c06ebf2602b82d909dc437",
        merge_sha="76e6f4af6edd18450e1001cb6a81e569a2f532db",pull_request=199,
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
    print("Verified exact NL019 evidence and provenance.")

if __name__=="__main__":
    main()
