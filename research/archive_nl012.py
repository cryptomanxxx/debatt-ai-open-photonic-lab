"""Verify exact NL012 ZIP and CI-emitted science hashes; archive without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

RUN=44296016894
ARTIFACT=14425195090
ZIP_SHA="1744fb578163f69d8a35b5fd35a1a0354cecbef3146d7177fc1bb1c28f8e5daf"
ZIP_SIZE=2838736
EXPECTED={
    "coefficients.json":(276005,"e4489c8cb9c2e54a82d30757f9013d6101bc0b53bb39a9ac7469fafabd9f8b2b"),
    "common_drive_pairs.csv":(38619,"eaa2e9b41831eb5229f08ac93cad81304a8ed0c0b1e5b62e715048a7dac6023e"),
    "convergence.csv":(1470,"2e7240e721e66c478e978de48980a4756ddd9c8392ae89b8502746418ca5680a"),
    "environment-lock.txt":(9532,"a413f375d4a3097d7cb7c9922da7288e15ad77026afdcb11d8f6945375ee8c4c"),
    "installed-packages.json":(68543,"f8bf20346f3dcd14fac94e7b91949ca983197c352d906a00e6b8152b0acf60f6"),
    "metrics.csv":(3083512,"b0ca5f7462ec191db95e40d3b31bef02b2fe7b8f397a3e850886a5e5225966d1"),
    "nl011_seed_analysis.json":(1853165,"6db9fbf17eeb231daad192382dd3c891f2a60d842c17638b2d93e5a9ad2b947b"),
    "optical_audit.csv":(1605,"355c780e15af912c87b8523b241de630de0fb9d6342308b726ea8dbd56bcb129"),
    "paired_readouts.csv":(5621846,"e2078e5181dda7daa9eaaf9d5d7f83fc3caf084a887c736535c8835a3487b59b"),
    "resolution_groups.csv":(370940,"c803000998785c0b70b65c3b49a52ac536457f23d9f0fdfc8d80094ac0734bf6"),
    "resolution_metrics.csv":(9240088,"cc50dac7b838971a68d6ef56f72f7c33a75e6a8169546c15aa0c13705ede68c9"),
    "result.json":(156517,"6127456671b807ecb7b583a5f0f30c92631dbc71fc781f341474ccdbf10990a7"),
    "summary.csv":(147629,"0b2b4416082188fb2be56d50bf3b70bf0f29792c23a4b15e1e1fa6259e93cdd4"),
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
    if (report["experiment"]!="OPA-NL-012" or len(report["checks"])!=22
        or not all(v is True for v in report["checks"].values()) or report["failures"]
        or report["rows"]!=5040 or report["groups"]!=1008
        or report["resolution_groups"]!=3024
        or report["combined_confirmed_groups"]!=491 or report["ambiguous_groups"]!=0
        or len(report["common_confirmed_passes"])!=173
        or len(report["fastest_common_confirmed_passes"])!=40
        or len(report["convergence"])!=8):
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
    return (json.dumps(dict(experiment="OPA-NL-012",workflow_run_id=RUN,
        job_id=134773246258,artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,
        artifact_bytes=ZIP_SIZE,head_sha="ab30ce5c9a89a13fb6d2299884ba6f4c5e899cc6",
        merge_sha="0c4b52d836daeb8307a74985ce79f9ad9a416f34",pull_request=171,
        verification="Raw ZIP pinned to GitHub metadata; CRC and all thirteen file hashes pinned to CI stdout; staged bytes compared to verified ZIP.",
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
    print("Verified exact NL012 evidence and provenance.")

if __name__=="__main__":
    main()
