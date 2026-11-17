"""Verify exact NL002 ZIP and CI-emitted science hashes; archive without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

RUN=44157326386
ARTIFACT=14361432237
ZIP_SHA="d30f10458d6780136368778e1ba287849dfbb0cf301c68186c3f917e44f2a431"
ZIP_SIZE=209386
EXPECTED={
    "learning_curves.csv":(294230,"e0f740dbe67e28e1d0a56c0b5b010e33dbf8063a2b53dd866b956a44251ea070"),
    "loss_matches.csv":(5590,"7399de1cc895d081de977377279ba60c23f2cfc48ff889dd3933024884bfe74d"),
    "metrics.csv":(229594,"82af55479c27366ca3035b1c8e4cba4a773f62a587a6264e3170fb4b097e79a6"),
    "result.json":(627346,"f8bcd3bccb91123d9654d9f5ea16e7825df596ed36b186f303ecbd0be02f7786"),
    "truth_table.csv":(69166,"e2c070f9e5b8c857c35d3734e96bb33e73ad4e4db4d6f723ee29e08b314e291f"),
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
    if report["experiment"]!="OPA-NL-002" or not all(report["checks"].values()) or report["failures"] or report["digital_preflight"] is not False or any(v["pass_gate"] for v in report["nominal"].values()):
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
    return (json.dumps(dict(experiment="OPA-NL-002",workflow_run_id=RUN,
        job_id=134301579784,artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,
        artifact_bytes=ZIP_SIZE,head_sha="05dc522733c10f58a72b85d7cbbb611373e6814f",
        merge_sha="2547e8a4cab48450fea40a93877e8a3da378c94e",pull_request=130,
        verification="Raw ZIP pinned to GitHub metadata; CRC and five science-file hashes pinned to CI stdout; environment hashes derived from verified ZIP; staged bytes compared to verified ZIP.",
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
    print("Verified exact NL002 evidence and provenance.")

if __name__=="__main__":
    main()
