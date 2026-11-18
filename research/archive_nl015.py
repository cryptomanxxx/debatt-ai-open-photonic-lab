"""Verify exact NL015 ZIP and CI-emitted science hashes; archive without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

RUN=44321189432
ARTIFACT=14437276291
ZIP_SHA="da2b2834f27301c25bf155573086dfcf01b332c6a351729a80204b096fc27dce"
ZIP_SIZE=685440
EXPECTED={
    "coefficient_summary.csv":(3538,"e13d33489dcb66f920e9eadb1ac79df358478c8dfd861a77345011ec7a3a150a"),
    "coefficients.json":(27568,"692fa64e8ffeddbb0f8d6f834da5bf100b2809bd13e03459692e0e959db1f36a"),
    "convergence.csv":(3043,"7da0ac82d7bb8c3cf4e0b5733d5ca35d0a7c5e5b5546ef1c815b397bc9fdd04b"),
    "environment-lock.txt":(9532,"a413f375d4a3097d7cb7c9922da7288e15ad77026afdcb11d8f6945375ee8c4c"),
    "installed-packages.json":(68543,"f8bf20346f3dcd14fac94e7b91949ca983197c352d906a00e6b8152b0acf60f6"),
    "metrics.csv":(638659,"66233d21f1adc0c3e053e96e6d82c113c2aeb6e3a45d049b9ad5350cf695c33b"),
    "nl014_seed_analysis.json":(1032395,"5ecca0b85f289fb7ae7882aa2a4ea736c4c3d076917bf33b6b321dd463ccb033"),
    "optical_audit.csv":(3528,"5206fd0045c4fb340bd7d7990a1265f1debaaa94b7a700b152970776b4d93cae"),
    "paired_readouts.csv":(1381890,"faa15e0cd72f90fc0364ce694629deda556640e878d546dbf5a6faeda0975190"),
    "paired_summary.csv":(27537,"0955ba5f0fbc32287aa61768b72d7c560a102de79ba9c8434b610fd6f791d7b6"),
    "resolution_groups.csv":(82192,"bf692237ce8d2373b892ee26462f01e33a70f1cf55e021e644262c9a11a1319c"),
    "resolution_metrics.csv":(1911648,"846706c1b31276966a9ecceab75f278dff51bcd79ab60059596b2075cd34b1b3"),
    "result.json":(58849,"513c9651069fe1a26ee34969718d9ab8b114959becba396711f32deb2d6a8924"),
    "summary.csv":(34231,"3a696920e6b936d4f7847efb0705ae1ef9b74598d4db9dad5037b63b97940c7b"),
    "two_panel_pairs.csv":(7079,"25c6709ae66f370eb81b124bfd1d7ac20c09520f3e462bd9bac3a5fa43abb0e2"),
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
    if (report["experiment"]!="OPA-NL-015" or len(report["checks"])!=24
        or not all(v is True for v in report["checks"].values()) or report["failures"]
        or report["rows"]!=980 or report["groups"]!=196
        or report["resolution_groups"]!=588
        or report["combined_passing_groups"]!=90 or report["ambiguous_groups"]!=0
        or len(report["common_confirmed_passes"])!=7
        or len(report["all_panel_pairs"])!=49
        or len(report["fastest_confirmed_endpoints"])!=2
        or any(p["on_ps"]!=42 or p["readout"]!="ridge16" or not p["confirmed_both_panels"] for p in report["fastest_confirmed_endpoints"])
        or report["control_passed"] is not True
        or report["primary_confirmed"] is not False
        or report["secondary_confirmed"] is not True
        or report["primary_endpoint"]["maximin"]!=.9482421875
        or report["secondary_endpoint"]["maximin"]!=.95068359375
        or len(report["convergence"])!=16):
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
    return (json.dumps(dict(experiment="OPA-NL-015",workflow_run_id=RUN,
        job_id=134860496443,artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,
        artifact_bytes=ZIP_SIZE,head_sha="22860166d0ef7cfd22823dd3feb7518281aa6615",
        merge_sha="f551aeda2ee06ab86e5cf327f6c32ae463f5f0b2",pull_request=183,
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
    print("Verified exact NL015 evidence and provenance.")

if __name__=="__main__":
    main()
