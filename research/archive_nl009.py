"""Verify exact NL009 ZIP and CI-emitted science hashes; archive without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

RUN=44197189683
ARTIFACT=14381707815
ZIP_SHA="acc3645d4eefcf394d8706ab738271479af5d2fea29161c1a1385dd93b2ce158"
ZIP_SIZE=11597063
EXPECTED={
    "confirmation.csv":(11751,"2deb92245b6d39eadd272940c59f3bf64482bd2cd84b87f6117bc46e598e5a57"),
    "convergence.csv":(21545,"7acdb70f5b9cc1476349fded74f38618dfa40b00f20fd3e8c40eb7febc317757"),
    "environment-lock.txt":(9532,"a413f375d4a3097d7cb7c9922da7288e15ad77026afdcb11d8f6945375ee8c4c"),
    "installed-packages.json":(68543,"f8bf20346f3dcd14fac94e7b91949ca983197c352d906a00e6b8152b0acf60f6"),
    "metrics.csv":(1211560,"2804cdee60535b5257c9d042fcf9e22afa968a9aabe8f4e7b1139d4022699408"),
    "positions.csv":(19589090,"c0350e8e0bba66a9509d9e8b9fb74f40f32a1e7030ab29bc97d863a5b61221bd"),
    "references.csv":(3171,"76b276ea5bdb893cc8046bc6104d0ec35f00984c3d8489da4267fa1bae467bcb"),
    "result.json":(78787,"4112bdcc6cf1516276e79ca2bab35d44071e47cbc093f0c8f446be5e5d712544"),
    "summary.csv":(83570,"0080bd63396467cb2875b67db06122c9a6357255b03c91d699dd81d3e7e0fcc3"),
    "traces.csv":(19536455,"d15fd3ebf40abe8ce80ad1a671dbbd5e4b624a89364237b73a27ad8d18dc0bab"),
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
    if (report["experiment"]!="OPA-NL-009" or len(report["checks"])!=19
        or not all(v is True for v in report["checks"].values()) or report["failures"]
        or report["rows"]!=3600 or report["configurations"]!=720
        or len(report["references"])!=30 or len(report["stream_passes"])!=124
        or report["confirmation_count"]!=110 or len(report["boundaries"])!=34
        or report["screens"]!=[{"candidate":"C1","drive_mw":0.1,"history":"cold","passed":24,"tested":60},{"candidate":"C1","drive_mw":0.1,"history":"stream","passed":24,"tested":60},{"candidate":"C1","drive_mw":1,"history":"cold","passed":32,"tested":60},{"candidate":"C1","drive_mw":1,"history":"stream","passed":21,"tested":60},{"candidate":"C2","drive_mw":0.1,"history":"cold","passed":20,"tested":60},{"candidate":"C2","drive_mw":0.1,"history":"stream","passed":20,"tested":60},{"candidate":"C2","drive_mw":1,"history":"cold","passed":32,"tested":60},{"candidate":"C2","drive_mw":1,"history":"stream","passed":24,"tested":60},{"candidate":"C3","drive_mw":0.1,"history":"cold","passed":18,"tested":60},{"candidate":"C3","drive_mw":0.1,"history":"stream","passed":18,"tested":60},{"candidate":"C3","drive_mw":1,"history":"cold","passed":26,"tested":60},{"candidate":"C3","drive_mw":1,"history":"stream","passed":17,"tested":60}]):
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
    return (json.dumps(dict(experiment="OPA-NL-009",workflow_run_id=RUN,
        job_id=134441768784,artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,
        artifact_bytes=ZIP_SIZE,head_sha="87612b67d1ae336feceb6b39287b9aee2d6827a7",
        merge_sha="38ff11d68be7d6eff5b93cf7f39f2d6fb8182503",pull_request=158,
        verification="Raw ZIP pinned to GitHub metadata; CRC and all ten file hashes pinned to CI stdout; staged bytes compared to verified ZIP.",
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
    print("Verified exact NL009 evidence and provenance.")

if __name__=="__main__":
    main()
