"""Verify exact NL001 ZIP and CI-emitted science hashes; archive without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

RUN=44153775276
ARTIFACT=14360875814
ZIP_SHA="effb57fcb56dfb8433951bff8ff3d381f8e6bfaab31c51d54c0340751c4c9cc3"
ZIP_SIZE=102722
EXPECTED={
    "learning_curves.csv":(134304,"e51c1fcc9d8c3ccca76bfb2317170d7b0b2f3f5ca1a5e7c45c2f05d29595013f"),
    "metrics.csv":(33826,"2bc49f22ccf3e9f37dd7900a8e34c05662c07f38a16ab50345d07d66f077b4c9"),
    "result.json":(100589,"55fcef08ad90b353f01fda09360f53c2b6f6bac5bb3605dc6d7f44109f659abe"),
    "transfer.csv":(137437,"d3a56fa723878f988ab2a99761ca0183546d173ab199e6457cee1b1f5bc2f05e"),
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
    if report["experiment"]!="OPA-NL-001" or not all(report["checks"].values()) or report["failures"] or report["hypothesis_pass"] is not False:
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
    return (json.dumps(dict(experiment="OPA-NL-001",workflow_run_id=RUN,
        job_id=134289115091,artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,
        artifact_bytes=ZIP_SIZE,head_sha="eaf191ad531beaee8b87df5048f151fbc5f6a81b",
        merge_sha="c662cd33e824a9b794faa5d0b745d20a4ae5db91",pull_request=127,
        verification="Raw ZIP pinned to GitHub metadata; CRC and four science-file hashes pinned to CI stdout; environment hashes derived from verified ZIP; staged bytes compared to verified ZIP.",
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
    print("Verified exact NL001 evidence and provenance.")

if __name__=="__main__":
    main()
