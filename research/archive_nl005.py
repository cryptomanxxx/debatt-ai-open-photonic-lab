"""Verify exact NL005 ZIP and CI-emitted science hashes; archive without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

RUN=44173789666
ARTIFACT=14368328417
ZIP_SHA="245f80ef6e95de5a7dcc736811028d1389fd973a6fb5b284039bd1092d758d00"
ZIP_SIZE=203565
EXPECTED={
    "convergence.csv":(12946,"1297febecd6abae2bc979c55f6b8f3fbaa7beec65fdb7b0751cbafe1f8edcad7"),
    "metrics.csv":(215781,"fab95aa2fa84cc1added98d5ef8ecbd1d2b1ffad7e4acbcf3632cd4a3407ca96"),
    "references.csv":(2737,"2b2bc7b827b831895bb17947e13086d23f1005a7985749e0709b6a6191affc3e"),
    "result.json":(9857,"682786db7b4655c4060e605165a290aa8911f9f7bf615c41dc97079a79c0c6b3"),
    "summary.csv":(17495,"5b1cb821d36d3f4881b992564c2fbfefcf60f6c6601d608165610a0b2abc4523"),
    "transfer.csv":(699701,"0cb0f3b30ed3c2fdb675cc1f5026aa4ce93eb4a80061a1546e0e743895aefa1d"),
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
    if report["experiment"]!="OPA-NL-005" or len(report["checks"])!=15 or not all(report["checks"].values()) or report["failures"] or report["rows"]!=1350 or report["configurations"]!=270 or len(report["references"])!=20 or report["screens"]!=[{"drive_mw":0.1,"low":0.1,"high":0.4,"passed":19,"tested":45},{"drive_mw":0.1,"low":0.15,"high":0.85,"passed":26,"tested":45},{"drive_mw":0.1,"low":0.373,"high":0.4,"passed":0,"tested":45},{"drive_mw":1,"low":0.1,"high":0.4,"passed":19,"tested":45},{"drive_mw":1,"low":0.15,"high":0.85,"passed":22,"tested":45},{"drive_mw":1,"low":0.373,"high":0.4,"passed":0,"tested":45}]:
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
    return (json.dumps(dict(experiment="OPA-NL-005",workflow_run_id=RUN,
        job_id=134359706201,artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,
        artifact_bytes=ZIP_SIZE,head_sha="fa0e08d42990c8d147ed15f66c8abc52562da322",
        merge_sha="d34b307aad33c9c5a12db65cc012a1a831ba6146",pull_request=142,
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
    print("Verified exact NL005 evidence and provenance.")

if __name__=="__main__":
    main()
