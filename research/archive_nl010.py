"""Verify exact NL010 ZIP and CI-emitted science hashes; archive without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

RUN=44283625212
ARTIFACT=14418487339
ZIP_SHA="e1647c33b2e3b6d85c7f7f26cdd31d18c869285c899c9ef567a5c5dc196fa80e"
ZIP_SIZE=475556
EXPECTED={
    "convergence.csv":(2309,"fc97f85c50d69b6e10514a9996c9c48a0f07e28d8c67695c393481785fc47957"),
    "environment-lock.txt":(9532,"a413f375d4a3097d7cb7c9922da7288e15ad77026afdcb11d8f6945375ee8c4c"),
    "installed-packages.json":(68543,"f8bf20346f3dcd14fac94e7b91949ca983197c352d906a00e6b8152b0acf60f6"),
    "metrics.csv":(548932,"2af4bc97232590421695a9e810f68bbfdc9cf8479d94a73b25348d53bc95446c"),
    "optical_audit.csv":(2577,"e4319a62122d6c92060b4154d2449f8814920328d11510cb94d34316c19e7580"),
    "resolution_groups.csv":(91416,"67a0888cdba0ab2b8c3bae9908ad020fc9c4fe589b6ec8267409217ab46a7fa7"),
    "resolution_metrics.csv":(1640536,"1c1b0f6ce2d6051dd577d1461f724bd473a855ed07f52ece77a0499a334c7251"),
    "result.json":(14910,"1c0ded061ee4e979efa9a919d9f9a036d10ec58c9f9db3bcc9918b2df2bd5f57"),
    "summary.csv":(34621,"324c098cbadb962104efd78305ee83d819affe70405d2977049ab9cdd7ae5f89"),
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
    if (report["experiment"]!="OPA-NL-010" or len(report["checks"])!=13
        or not all(v is True for v in report["checks"].values()) or report["failures"]
        or report["rows"]!=1680 or report["groups"]!=336
        or report["resolution_groups"]!=1008
        or report["combined_confirmed_groups"]!=44 or report["ambiguous_groups"]!=0
        or len(report["common_confirmed_passes"])!=13 or len(report["convergence"])!=14):
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
    return (json.dumps(dict(experiment="OPA-NL-010",workflow_run_id=RUN,
        job_id=134730602845,artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,
        artifact_bytes=ZIP_SIZE,head_sha="f2e818606a84963f665267797c4f6b72bf9b86a1",
        merge_sha="002d41a4f078d3800cd452503c29226b6dc4ac8f",pull_request=163,
        verification="Raw ZIP pinned to GitHub metadata; CRC and all nine file hashes pinned to CI stdout; staged bytes compared to verified ZIP.",
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
    print("Verified exact NL010 evidence and provenance.")

if __name__=="__main__":
    main()
