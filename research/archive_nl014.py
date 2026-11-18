"""Verify exact NL014 ZIP and CI-emitted science hashes; archive without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

RUN=44311554574
ARTIFACT=14430539359
ZIP_SHA="4b0232f70758d1739776f70fcbf88c0934baf23b9d94cb8bfb47e1fcb3a24d4e"
ZIP_SIZE=1515177
EXPECTED={
    "coefficient_summary.csv":(18292,"721a639ee366a2cc853a494995eb85592d1d1f5c4dce7b5cbf42058f393ef2e4"),
    "coefficients.json":(145795,"0f1ef370dd30ffa87cfa5084af14aa3eabaeca6c3bf57a40c54e5f5a6e116f26"),
    "common_drive_pairs.csv":(23817,"47d06d7a43f158c2da5c3cfdeaccca1d4de57fc6ec28c512294e413f6f740a63"),
    "convergence.csv":(1706,"06893235bd88f631cf20982ef808dd8495d3c3346c2ddc9785308c13399e0e0e"),
    "environment-lock.txt":(9532,"a413f375d4a3097d7cb7c9922da7288e15ad77026afdcb11d8f6945375ee8c4c"),
    "installed-packages.json":(68543,"f8bf20346f3dcd14fac94e7b91949ca983197c352d906a00e6b8152b0acf60f6"),
    "metrics.csv":(1716997,"471898ab3963c915fc95fab3a211152a3dcd2d9207ddd850a98340bcc1f836cd"),
    "nl013_seed_analysis.json":(83849,"f2353f1df4a5c48533ae0b3d8495b378ff0d87305252eb2e0871f03e338addf1"),
    "optical_audit.csv":(1957,"1d0930cdf3487c2ceb858801b5aaf35dc0849fe854d2f78c1b4e37526a863814"),
    "paired_readouts.csv":(4070427,"6628a1365773212c6141d968ac82d4f2308f54696d36173ef418a9ad18e345c7"),
    "paired_summary.csv":(70290,"5969df6b9e54bb331bb3e476f5a5fac02c9c6280ca5eebb04bf00c114521694a"),
    "resolution_groups.csv":(234681,"29c47b52e776f0bc687011893d894887e1dbeda7109c1e2f44a3844d3e19921c"),
    "resolution_metrics.csv":(5143033,"988decc0b67d364b6ef499574a5f901146ffb8456698ed6a4533c376396d14e1"),
    "result.json":(138783,"79bb33d76c23b1467721795caf3e66f213d8291a4bf9b4ae482f9bdb5313bdb8"),
    "summary.csv":(95998,"f46fc0288cd612ec97dbb377117d0769858d40c1d408b70e6fc153010a171c53"),
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
    if (report["experiment"]!="OPA-NL-014" or len(report["checks"])!=24
        or not all(v is True for v in report["checks"].values()) or report["failures"]
        or report["rows"]!=2590 or report["groups"]!=518
        or report["resolution_groups"]!=1554
        or report["combined_passing_groups"]!=238 or report["ambiguous_groups"]!=0
        or len(report["common_exploratory_passes"])!=62
        or len(report["all_common_drive_pairs"])!=259
        or len(report["fastest_exploratory_passes"])!=12
        or any(p["on_ps"]!=42 or not p["passes_both_drives"] for p in report["fastest_exploratory_passes"])
        or report["control_passed"] is not True
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
    return (json.dumps(dict(experiment="OPA-NL-014",workflow_run_id=RUN,
        job_id=134826805814,artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,
        artifact_bytes=ZIP_SIZE,head_sha="ff5c11607025c403b542a0b5b7d1ccd6a73235a0",
        merge_sha="c44d7d518dcc334182e776207f7cf8d84f1a6aab",pull_request=179,
        verification="Raw ZIP pinned to GitHub metadata; CRC and all fifteen file hashes pinned to CI stdout; staged bytes compared to verified ZIP.",
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
    print("Verified exact NL014 evidence and provenance.")

if __name__=="__main__":
    main()
