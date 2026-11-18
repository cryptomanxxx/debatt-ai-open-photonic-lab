"""Verify exact NL013 ZIP and CI-emitted science hashes; archive without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

RUN=44304216745
ARTIFACT=14428427620
ZIP_SHA="32b8cf14f8e0e2bda8930308eceebefebde6472eb7a383156c37d17a414d5404"
ZIP_SIZE=390041
EXPECTED={
    "coefficients.json":(11493,"4b151f3ad6010ead2f38f874797e7f7f9bd9e2eb77b42d5243e499c89fb0ed45"),
    "convergence.csv":(1570,"041548cde5145eed2564db0abe8e981c3bf82051672b68043080c5cf4e223820"),
    "environment-lock.txt":(9532,"a413f375d4a3097d7cb7c9922da7288e15ad77026afdcb11d8f6945375ee8c4c"),
    "installed-packages.json":(68543,"f8bf20346f3dcd14fac94e7b91949ca983197c352d906a00e6b8152b0acf60f6"),
    "metrics.csv":(264879,"c35e5817afb03e60a23f1c91d9a1592dc36e7abb00b79d6903f6738e4727bd44"),
    "nl012_seed_analysis.json":(1187136,"f33b74d791be1e328d36d2d627d027e66e78e9c3ebd176268b6fef48e378f595"),
    "optical_audit.csv":(1765,"c854b7ddb99556db07641ce8718eb7c0b3d3711a6bc334aad9207a4959dc5228"),
    "paired_readouts.csv":(589446,"457171d6c30be0744e5b0fc4d8da662e1bdd0ab9686d226d169baefcbd6c6119"),
    "resolution_groups.csv":(34840,"a6a87d2369d3f06e810d2c7af0276ca6d76bb71926cfdde07e7e9bbde77e2a96"),
    "resolution_metrics.csv":(792541,"965475d8a82ec156d5d986ba00b23f8b58f2a0015e97d957fc1642789eb1d079"),
    "result.json":(24059,"08f99f9c0a19bf0941a5c7cb1c7b2402656752f824728e463ca1bf30f3d48c31"),
    "summary.csv":(13662,"95a34a09a561b82ef6e25601350bcd71834d5e30a4a5e7bbd9784422d81f5f04"),
    "two_panel_pairs.csv":(3016,"978b15b4a9a232c9d56998355e2b40e0f98233219cfc24bdb8dfbcaa7c526c44"),
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
    if (report["experiment"]!="OPA-NL-013" or len(report["checks"])!=23
        or not all(v is True for v in report["checks"].values()) or report["failures"]
        or report["rows"]!=420 or report["groups"]!=84
        or report["resolution_groups"]!=252
        or report["combined_confirmed_groups"]!=44 or report["ambiguous_groups"]!=0
        or len(report["common_confirmed_passes"])!=7
        or len(report["all_panel_pairs"])!=21
        or len(report["convergence"])!=8
        or report["primary_endpoint"]["confirmed_both_panels"] is not True
        or report["secondary_endpoint"]["confirmed_both_panels"] is not True
        or report["primary_endpoint"]["maximin"]!=0.9599609375
        or report["secondary_endpoint"]["maximin"]!=0.95654296875):
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
    return (json.dumps(dict(experiment="OPA-NL-013",workflow_run_id=RUN,
        job_id=134801555451,artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,
        artifact_bytes=ZIP_SIZE,head_sha="542c01c13097e43fcd710c03d9a4f9f26128b72a",
        merge_sha="ae17ffa92215be5afcfe6bf571180c868c680064",pull_request=175,
        verification="Raw ZIP pinned to GitHub metadata; CRC and all thirteen file hashes pinned to CI stdout; staged bytes compared to verified ZIP.",
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
    print("Verified exact NL013 evidence and provenance.")

if __name__=="__main__":
    main()
