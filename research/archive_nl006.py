"""Verify exact NL006 ZIP and CI-emitted science hashes; archive without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

RUN=44179461645
ARTIFACT=14371092957
ZIP_SHA="64eda82d93c4b08e11059d685ba183279fd98efbdf108980f1012d86c93b1dad"
ZIP_SIZE=661907
EXPECTED={
    "cavity_audit.csv":(29445,"75b6f680d494678e99703106110db15eec31560079f295e15944ac530c50cdf1"),
    "metrics.csv":(414371,"cca7e3ea2eb13cc302cd98c8ef52b26feb34b82250bf063d950bbf0df8fbc68d"),
    "references.csv":(3237,"9089d38a1b501ccbcecc3e774ee341731004e65e740bd2908b82dc0d33d17f03"),
    "result.json":(12137,"f3d38aa94570bda20696cb80f107c00c47248d1662efd5e4285353580f33c720"),
    "summary.csv":(32738,"14cd95304c4ca6770964c2210e07237934fee256a4de2bd01e4cc5559acca6d4"),
    "transfer.csv":(1892463,"ac132b78098089e3db745c794a6ec6ed14e74321bff0a4be68eb1b5593b4d3a1"),
}
NAMES=set(EXPECTED)|{"environment-lock.txt","installed-packages.json"}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def verify_science(files):
    if set(files)!=NAMES:
        raise ValueError("unexpected evidence names")
    for name,(size,digest) in EXPECTED.items():
        if (len(files[name]),sha(files[name]))!=(size,digest):
            raise ValueError("CI science hash mismatch: "+name)
    report=json.loads(files["result.json"])
    if report["experiment"]!="OPA-NL-006" or len(report["checks"])!=14 or not all(report["checks"].values()) or report["failures"] or report["rows"]!=2160 or report["configurations"]!=432 or len(report["references"])!=30 or report["ambiguous_cavities"]!=0 or report["stress"]!={"input_mw":1.55685,"roots":3,"stable_roots":2} or report["screens"]!=[{"drive_mw":0.1,"low":0.1,"high":0.4,"passed":19,"tested":72},{"drive_mw":0.1,"low":0.15,"high":0.85,"passed":22,"tested":72},{"drive_mw":0.1,"low":0.373,"high":0.4,"passed":2,"tested":72},{"drive_mw":1,"low":0.1,"high":0.4,"passed":20,"tested":72},{"drive_mw":1,"low":0.15,"high":0.85,"passed":16,"tested":72},{"drive_mw":1,"low":0.373,"high":0.4,"passed":1,"tested":72}]:
        raise ValueError("unexpected report")

def read_zip(path):
    raw=path.read_bytes()
    if len(raw)!=ZIP_SIZE or sha(raw)!=ZIP_SHA:
        raise ValueError("ZIP identity mismatch")
    with zipfile.ZipFile(path) as z:
        info=z.infolist()
        if len(info)!=len(NAMES) or {i.filename for i in info}!=NAMES:
            raise ValueError("unexpected ZIP entries")
        if any(i.is_dir() or stat.S_ISLNK(i.external_attr>>16) or i.file_size>2_000_000 for i in info):
            raise ValueError("invalid ZIP entry")
        if z.testzip() is not None:
            raise ValueError("CRC failure")
        files={i.filename:z.read(i) for i in info}
    verify_science(files)
    return files

def manifest(files):
    return (json.dumps(dict(experiment="OPA-NL-006",workflow_run_id=RUN,
        job_id=134379675713,artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,
        artifact_bytes=ZIP_SIZE,head_sha="6d04f42b7c547a4dc7753145208cc83dc1e6b062",
        merge_sha="686bec5a961bd9567514ee0cc8a25a34823fa4e5",pull_request=146,
        verification="Raw ZIP pinned to GitHub metadata; CRC and six science-file hashes pinned to CI stdout; environment hashes derived from verified ZIP; staged bytes compared to verified ZIP.",
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
    print("Verified exact NL006 evidence and provenance.")

if __name__=="__main__":
    main()
