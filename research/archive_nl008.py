"""Verify exact NL008 ZIP and CI-emitted science hashes; archive without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

RUN=44192685431
ARTIFACT=14377357687
ZIP_SHA="27dfe96872e4a15292cdf9b65befdb4d305d63ed2ef3bba6046972c404882c01"
ZIP_SIZE=544319
EXPECTED={
    "convergence.csv":(13238,"7f3980600cb1f656bf45cfc975e12563c962cba8962705b6d911d7c554819e56"),
    "metrics.csv":(640492,"56609122a1d57c1ed24c70a88a8de868124b7d8e421cef9f4e6c36a52f0a2347"),
    "references.csv":(6128,"00e1ab54c4f272e959dc591c8ab7dd83d117afce03e7be6edf2acd085262b403"),
    "result.json":(67638,"c9bc6754f9876cd3b76008854b14553fb936d74b2ad9df17f950db61a6e930af"),
    "summary.csv":(48145,"f6b05f2c05904d4283a14bd93db57f8b2132fbcbe96ac56887cf57b41ca49152"),
    "traces.csv":(1477480,"9df23487a4bf53827794306a1a3858b8031ed318107a273ba568a56c793f6ee0"),
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
    if (report["experiment"]!="OPA-NL-008" or len(report["checks"])!=14
        or not all(report["checks"].values()) or report["failures"]
        or report["rows"]!=2160 or report["configurations"]!=432
        or len(report["references"])!=60 or len(report["stream_passes"])!=85
        or report["screens"]!=[{"candidate":"C1","drive_mw":0.1,"history":"cold","passed":10,"tested":18},{"candidate":"C1","drive_mw":0.1,"history":"stream","passed":10,"tested":18},{"candidate":"C1","drive_mw":1,"history":"cold","passed":12,"tested":18},{"candidate":"C1","drive_mw":1,"history":"stream","passed":11,"tested":18},{"candidate":"C2","drive_mw":0.1,"history":"cold","passed":10,"tested":18},{"candidate":"C2","drive_mw":0.1,"history":"stream","passed":10,"tested":18},{"candidate":"C2","drive_mw":1,"history":"cold","passed":12,"tested":18},{"candidate":"C2","drive_mw":1,"history":"stream","passed":10,"tested":18},{"candidate":"C3","drive_mw":0.1,"history":"cold","passed":10,"tested":18},{"candidate":"C3","drive_mw":0.1,"history":"stream","passed":10,"tested":18},{"candidate":"C3","drive_mw":1,"history":"cold","passed":12,"tested":18},{"candidate":"C3","drive_mw":1,"history":"stream","passed":10,"tested":18},{"candidate":"L1","drive_mw":0.1,"history":"cold","passed":12,"tested":18},{"candidate":"L1","drive_mw":0.1,"history":"stream","passed":10,"tested":18},{"candidate":"L1","drive_mw":1,"history":"cold","passed":2,"tested":18},{"candidate":"L1","drive_mw":1,"history":"stream","passed":0,"tested":18},{"candidate":"L2","drive_mw":0.1,"history":"cold","passed":10,"tested":18},{"candidate":"L2","drive_mw":0.1,"history":"stream","passed":10,"tested":18},{"candidate":"L2","drive_mw":1,"history":"cold","passed":2,"tested":18},{"candidate":"L2","drive_mw":1,"history":"stream","passed":0,"tested":18},{"candidate":"H1","drive_mw":0.1,"history":"cold","passed":0,"tested":18},{"candidate":"H1","drive_mw":0.1,"history":"stream","passed":0,"tested":18},{"candidate":"H1","drive_mw":1,"history":"cold","passed":6,"tested":18},{"candidate":"H1","drive_mw":1,"history":"stream","passed":4,"tested":18}]):
        raise ValueError("unexpected report")

def read_zip(path):
    raw=path.read_bytes()
    if len(raw)!=ZIP_SIZE or sha(raw)!=ZIP_SHA:
        raise ValueError("ZIP identity mismatch")
    with zipfile.ZipFile(path) as z:
        info=z.infolist()
        if len(info)!=len(NAMES) or {i.filename for i in info}!=NAMES:
            raise ValueError("unexpected ZIP entries")
        if any(i.is_dir() or stat.S_ISLNK(i.external_attr>>16) or i.file_size>3_000_000 for i in info):
            raise ValueError("invalid ZIP entry")
        if z.testzip() is not None:
            raise ValueError("CRC failure")
        files={i.filename:z.read(i) for i in info}
    verify_science(files)
    return files

def manifest(files):
    return (json.dumps(dict(experiment="OPA-NL-008",workflow_run_id=RUN,
        job_id=134426029605,artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,
        artifact_bytes=ZIP_SIZE,head_sha="9f6e5bc6b0050a1c1b1a3199fd8f14b763e4b2af",
        merge_sha="af513980c76e1b1cbc818217d1ce239d7adf333f",pull_request=154,
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
    print("Verified exact NL008 evidence and provenance.")

if __name__=="__main__":
    main()
