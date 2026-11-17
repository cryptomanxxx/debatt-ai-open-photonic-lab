"""Verify exact NL004 ZIP and CI-emitted science hashes; archive without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

RUN=44169138855
ARTIFACT=14366547319
ZIP_SHA="d5f3aafe2b46ec73f8fd8bf5484e93639b710c1684ebd5c3de96602c79fe7ee9"
ZIP_SIZE=150226
EXPECTED={
    "dynamics.csv":(2888,"d1219ebf464996cce0ca0c499beecc449ff8458ac9acf21466c0f5d6c7ab7095"),
    "metrics.csv":(434889,"0f31485b1af3c2a6e58c95dd01bc86d38d502c8cd4f34d0749d7b56b3a898f37"),
    "result.json":(5825,"aa8afb042598d536809658aeb72421f115c58557c812bd9692c7d90c25273178"),
    "summary.csv":(34710,"1e6819893ebfbd5a44580fd9f22c6efc8624bacc584d2838d88918c891858e22"),
    "transfer_checks.csv":(6716,"d42b450265e94d610656cc428c405b49a8e48cdebfec75f60a2dac99940dd9af"),
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
    if report["experiment"]!="OPA-NL-004" or len(report["checks"])!=13 or not all(report["checks"].values()) or report["failures"] or report["rows"]!=2700 or report["configurations"]!=540 or report["screens"]!=[{"drive_mw":.1,"passed":30,"tested":270},{"drive_mw":1,"passed":32,"tested":270}]:
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
    return (json.dumps(dict(experiment="OPA-NL-004",workflow_run_id=RUN,
        job_id=134343269714,artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,
        artifact_bytes=ZIP_SIZE,head_sha="cd29f8ecffc30a145cab8166d649a408c7622901",
        merge_sha="38e894d8bfde4cf5bfee8154eb794b100a90d0e3",pull_request=138,
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
    print("Verified exact NL004 evidence and provenance.")

if __name__=="__main__":
    main()
