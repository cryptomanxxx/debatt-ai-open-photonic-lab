"""Verify exact NL007 ZIP and CI-emitted science hashes; archive without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

RUN=44184657895
ARTIFACT=14373622549
ZIP_SHA="ec9518b1703f1d2a4275ed84b680d394cb746a4a3a4a201acb76671aee29905e"
ZIP_SIZE=820638
EXPECTED={
    "cavity_audit.csv":(51464,"b045d4be5bd71ad14360d3f9e35ce9c9b64cf080c50214c797cf3a6bc86a0367"),
    "metrics.csv":(830341,"2fc2dfddbb49e273d376e80eb0752f474157cbc66ca7cf71e3b2a8069a180e49"),
    "references.csv":(4087,"c1ba21477a5a43f9dc6ef536ee0253cd2642e0ef26c6d9b27900e8d1880b5e31"),
    "result.json":(48202,"f5392d9ec0958c13f4147ab32ef2ed7a0095fbedf0dd3ca65d835eabe7a048fb"),
    "summary.csv":(64039,"516652479f1641fcd2c758199ac58bcf359efe9a0bc0e17d5c1bcc847e090f95"),
    "transfer.csv":(2629442,"daf25c9120f8eb243414cd9d9f2390f5b75fba2b2af99da3e5415d2a2f388ac5"),
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
    if (report["experiment"]!="OPA-NL-007" or len(report["checks"])!=14
        or not all(report["checks"].values()) or report["failures"]
        or report["rows"]!=2990 or report["configurations"]!=598
        or len(report["references"])!=30 or len(report["mechanism"])!=70
        or sum(r["screen_pass"] for r in report["mechanism"])!=19
        or report["tolerance_screens"]!=[{"candidate":"W2","mode":"full","drive_mw":0.1,"passed":21,"tested":66},{"candidate":"W2","mode":"full","drive_mw":1,"passed":7,"tested":66},{"candidate":"W2","mode":"no_bleaching","drive_mw":0.1,"passed":19,"tested":66},{"candidate":"W2","mode":"no_bleaching","drive_mw":1,"passed":7,"tested":66},{"candidate":"W3","mode":"full","drive_mw":0.1,"passed":17,"tested":66},{"candidate":"W3","mode":"full","drive_mw":1,"passed":1,"tested":66},{"candidate":"W3","mode":"no_bleaching","drive_mw":0.1,"passed":16,"tested":66},{"candidate":"W3","mode":"no_bleaching","drive_mw":1,"passed":1,"tested":66}]):
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
    return (json.dumps(dict(experiment="OPA-NL-007",workflow_run_id=RUN,
        job_id=134397995866,artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,
        artifact_bytes=ZIP_SIZE,head_sha="faf95d30563bc326002648cd56e5ed1a40da9301",
        merge_sha="389a0a41856cbfb643a6a681c39a5e7a55226cc3",pull_request=150,
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
    print("Verified exact NL007 evidence and provenance.")

if __name__=="__main__":
    main()
