"""Verify exact NL016 ZIP and CI-emitted science hashes; archive without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

RUN=44334443261
ARTIFACT=14441791865
ZIP_SHA="3651a19dec08defbed0e1a5a3f47e821ebd9917482dfd235b9cceae33bfb5d6b"
ZIP_SIZE=842705
EXPECTED={
    "coefficient_summary.csv":(11057,"9b941d4406d87810928680b4ca0a30fca9fdd61bfe85b42338c5500dd254fb64"),
    "coefficients.json":(90339,"956d699c71f327a905cd092f7fa3e7e9d5044ba4bb88adad4251d8a1ca8b0703"),
    "common_drive_pairs.csv":(10816,"bfecf20eeb446cec21f20f4a013014432e2d1f90e77a0786cc8c487fce84ba3e"),
    "convergence.csv":(1278,"d3f94531214625ded5015e3d237cbd53745c8e18e14e6e8eb3600a2efb8b9f73"),
    "environment-lock.txt":(9532,"a413f375d4a3097d7cb7c9922da7288e15ad77026afdcb11d8f6945375ee8c4c"),
    "installed-packages.json":(68543,"f8bf20346f3dcd14fac94e7b91949ca983197c352d906a00e6b8152b0acf60f6"),
    "metrics.csv":(820420,"185a516994a107d466391bff553cd27103c45f04237bfab80a878ad8f1b4b9b7"),
    "nl015_seed_analysis.json":(394420,"5f644a6ef676bdcf9a0281a272d289c9d367a8bb0a4722e0db1c761e8e27dfbd"),
    "optical_audit.csv":(1445,"d1002ce63d3ba3ddb75bf0faccb6e496052cc2cc615e1d117001289163472206"),
    "paired_readouts.csv":(2490340,"88fccdc3a6ad4a6c265debf275945e6b090d97dab0bc352493039484029cda36"),
    "paired_summary.csv":(45859,"e9ea048607c484de9d40fc1f696780af7d292cc3f863e01cf696d42ac9e2f77e"),
    "resolution_groups.csv":(108893,"76abe96b8bee206bc5a2238f916efb04ef2ba54f8c2639871a18c0f6c58df9b1"),
    "resolution_metrics.csv":(2456731,"a4c12a7f2349a4f503a5a52461101aef14eb4778d487b9661ebe3d2755165db4"),
    "result.json":(56177,"2b0cfe9d381469d91d01b3309a24fabd623388d4c0a142ff177a258474aabf3b"),
    "summary.csv":(45017,"5e666c49a7539dc9f21f1bb310b9761b7fc6bf265b59c123d215834a7edf71fa"),
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
    if (report["experiment"]!="OPA-NL-016" or len(report["checks"])!=25
        or not all(v is True for v in report["checks"].values()) or report["failures"]
        or report["rows"]!=1220 or report["groups"]!=244
        or report["resolution_groups"]!=732
        or report["combined_passing_groups"]!=88 or report["ambiguous_groups"]!=0
        or len(report["common_exploratory_passes"])!=2
        or len(report["all_common_drive_pairs"])!=122
        or report["fastest_exploratory_passes"]
        or report["ranked_exploratory_candidates"]
        or report["proposed_confirmation_candidate"] is not None
        or report["control_passed"] is not True
        or {(p["on_ps"],p["lo_mw"],p["fc_ghz"],p["readout"],p["maximin"])
            for p in report["common_exploratory_passes"]} != {
                (42,2.,120,"ridge16",.95068359375),(42,3.,120,"ridge16",.95263671875)}
        or any(p["on_ps"]<42 and p["passes_both_drives"] for p in report["all_common_drive_pairs"])
        or len(report["convergence"])!=6
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
    return (json.dumps(dict(experiment="OPA-NL-016",workflow_run_id=RUN,
        job_id=134907416490,artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,
        artifact_bytes=ZIP_SIZE,head_sha="2fb0289227c2fbc5896d1b25762fd20f2f1af38d",
        merge_sha="4ce7f78b488a067128f9696a35f5cc4242d39aee",pull_request=187,
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
    print("Verified exact NL016 evidence and provenance.")

if __name__=="__main__":
    main()
