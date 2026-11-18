"""Verify exact NL011 ZIP and CI-emitted science hashes; archive without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

RUN=44288710042
ARTIFACT=14421271696
ZIP_SHA="89ce5da2a5000e58dc67fcd121ee2e0d7801d5048af9806ebdf3033ab47e19b2"
ZIP_SIZE=2132487
EXPECTED={
    "common_drive_pairs.csv":(60161,"42161cd1b4fd25a154122ed76ed556c26912b17bbf5b6e40bf9b169140d0b545"),
    "convergence.csv":(2900,"6d8d5ddd57adfb3d1de6772bf0cc9c94e9225b23563a6f233772fe054bf23f50"),
    "environment-lock.txt":(9532,"a413f375d4a3097d7cb7c9922da7288e15ad77026afdcb11d8f6945375ee8c4c"),
    "installed-packages.json":(68543,"f8bf20346f3dcd14fac94e7b91949ca983197c352d906a00e6b8152b0acf60f6"),
    "metrics.csv":(3886298,"c7653a450de8086dad1ea1a62b9505fbe4bef415a52cc287327dc72db4c7558f"),
    "optical_audit.csv":(3239,"8101af1d24c8f56a1aa52a5452397ebebec3b8f5fdb322c9f5fa880c919087d2"),
    "resolution_groups.csv":(602360,"5aee4e2f7f3a3d6285ef1492c236fb13650bc0349e1f277d1cbe550544866af8"),
    "resolution_metrics.csv":(11643868,"120405888197f98f391ac721bfbfa672bbcb594e5a5398b3b8bd87f8fc7eed5a"),
    "result.json":(112323,"6f151b9a5bde339c5c9dbc50376033f49fe2699bdbc99a43865e4cc220cb27b3"),
    "summary.csv":(249461,"f9676e69634a19df7a5b2f3ace6009a5e8b81ba393ac21cf00a1b780e07c1646"),
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
    if (report["experiment"]!="OPA-NL-011" or len(report["checks"])!=17
        or not all(v is True for v in report["checks"].values()) or report["failures"]
        or report["rows"]!=7680 or report["groups"]!=1536
        or report["resolution_groups"]!=4608
        or report["combined_confirmed_groups"]!=328 or report["ambiguous_groups"]!=0
        or len(report["common_confirmed_passes"])!=108
        or len(report["fastest_common_confirmed_passes"])!=35
        or len(report["convergence"])!=16):
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
    return (json.dumps(dict(experiment="OPA-NL-011",workflow_run_id=RUN,
        job_id=134748083271,artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,
        artifact_bytes=ZIP_SIZE,head_sha="eed16eda29886fc22c043aa4a1c435f9950493b2",
        merge_sha="a4937e9f3582fac93ce9a8e74cb6d1e68cace360",pull_request=167,
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
    print("Verified exact NL011 evidence and provenance.")

if __name__=="__main__":
    main()
