"""Verify exact NL003 ZIP and CI-emitted science hashes; archive without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

RUN=44163676304
ARTIFACT=14364861512
ZIP_SHA="aa85eab11f7af5c5bd52a147b241083f85c622038e8d0a7991470e3c61e19ba6"
ZIP_SIZE=117695
EXPECTED={
    "learning_curves.csv":(62977,"2b96e1fc4397b7c93a01503daa40bd05e741ace6ffb567f6ee34aa739945c776"),
    "paired.csv":(3537,"8d7b06d356a1e5b074ee0341fefb9a9cf0d695c9dc906d1e6b0f27d124706cb5"),
    "receiver.csv":(534663,"8a5f0f49c7a86fb619abbb4468868f2da5f95b37b1a5c09b921e6ef347c8d7c5"),
    "references.csv":(450,"9ddf8cd1c1e3a3f0251ecf684db1bd2fa58f6aea8c33af9e0f57bef36e390af3"),
    "result.json":(28598,"32af85955f35d1b773efc429d3998677624c91b32dcf2ab75892fec02c166287"),
    "weights.json":(59049,"b3b81b98d1b2eb39b978437e4b9bcb9b6300ec941bdea2dee7082235af9203df"),
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
    if report["experiment"]!="OPA-NL-003" or not all(report["checks"].values()) or report["failures"] or report["digital_constructive_preflight"] is not True or report["gates"] != {"absorber_0.1":True,"absorber_1.0":True,"softsat_0.1":False,"softsat_1.0":True} or report["receiver_rows"] != 2160:
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
    return (json.dumps(dict(experiment="OPA-NL-003",workflow_run_id=RUN,
        job_id=134324031154,artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,
        artifact_bytes=ZIP_SIZE,head_sha="796d6e3874aed72394e9d3ede22a607e9c998e46",
        merge_sha="cab346fd1821f3d23da6ea08222bc8feb1a24abd",pull_request=134,
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
    print("Verified exact NL003 evidence and provenance.")

if __name__=="__main__":
    main()
