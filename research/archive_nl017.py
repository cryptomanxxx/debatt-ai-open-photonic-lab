"""Verify exact NL017 ZIP and CI-emitted science hashes; archive without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

RUN=44350128879
ARTIFACT=14448662570
ZIP_SHA="f66c6fb132af365fb4f96cf938891eb58314ad65c92a553e1df6a0ae065a571d"
ZIP_SIZE=411265
EXPECTED={
    "coefficient_summary.csv":(6955,"bd2a07ca284ed7f37441d6c9d2dcad4211202a2ea2b61ee04e215913da344b35"),
    "coefficients.json":(54350,"1431009ec272e1c1c28b060a07a375d5cc735a833a63dd8241c076b4d96b01be"),
    "common_drive_pairs.csv":(4689,"df9f1c5ab372b311e38ebdb1b2f0ba392ece44ca96699c76921e6f1fcf87905a"),
    "convergence.csv":(1283,"a749c26c60667ac663222bb9337e48e935fc8a747b80491ca9fc87830b394b7c"),
    "environment-lock.txt":(9532,"a413f375d4a3097d7cb7c9922da7288e15ad77026afdcb11d8f6945375ee8c4c"),
    "installed-packages.json":(68543,"f8bf20346f3dcd14fac94e7b91949ca983197c352d906a00e6b8152b0acf60f6"),
    "metrics.csv":(338717,"5dc06056dd92ee932e1083408baf03d0adac94f520cf45a25379e1f4e1379180"),
    "nl016_seed_analysis.json":(523636,"49c42f434c773fb0eb9ff6c1be1c127b2191ad8ac6681a3951d2b07ce7d81800"),
    "optical_audit.csv":(1440,"e8f8ec622e1dcbbb251fe9fca9e14c3d23983440c458fab847425301e59fa2f2"),
    "paired_readouts.csv":(1266396,"4bb967a1c26c3087633e47210adb28faa0f6c9cd84abfd3f4a6673eb2d7a73c4"),
    "paired_summary.csv":(22486,"cbebe3b9dc2f7c03d9a6ba2f8ad414718b70faa4d8eb568052e35c63e92cbcc0"),
    "resolution_groups.csv":(46025,"ffbfb0e0988d74f9a02819fe779d7c93383e10bfdb3058f399b397f118e95497"),
    "resolution_metrics.csv":(1013150,"9775cc8ca6b5be1b05931e1303b5785a407d0a5b030bf4a076d21fb23e985161"),
    "result.json":(68610,"607d2b25bca45f9ad53333e9a78f5bc315d65d204540918cea62c117597106b0"),
    "summary.csv":(18477,"033ecc7045519a4e68056718e9560712c84978ea1a99797fc0369f8b46e23654"),
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
    if (report["experiment"]!="OPA-NL-017" or len(report["checks"])!=26
        or not all(v is True for v in report["checks"].values()) or report["failures"]
        or report["rows"]!=500 or report["groups"]!=100
        or report["resolution_groups"]!=300
        or report["combined_passing_groups"]!=58 or report["ambiguous_groups"]!=0
        or len(report["common_exploratory_passes"])!=20
        or len(report["all_common_drive_pairs"])!=50
        or len(report["fastest_exploratory_passes"])!=16
        or len(report["ranked_exploratory_candidates"])!=16
        or report["control_passed"] is not True
        or any(p["on_ps"]!=41 or not p["passes_both_drives"] for p in report["fastest_exploratory_passes"])
        or any(p["on_ps"]==40 and p["passes_both_drives"] for p in report["all_common_drive_pairs"])
        or report["proposed_confirmation_candidate"]!=report["ranked_exploratory_candidates"][0]
        or (report["proposed_confirmation_candidate"]["on_ps"],report["proposed_confirmation_candidate"]["lo_mw"],
            report["proposed_confirmation_candidate"]["fc_ghz"],report["proposed_confirmation_candidate"]["readout"],
            report["proposed_confirmation_candidate"]["maximin"])!=(41,3.,80,"frozen_ridge16_midlow",.95263671875)
        or len(report["matched_history_comparisons"])!=36 or len(report["matched_recalibration_comparisons"])!=12
        or len(report["convergence"])!=6
        or any(p["changed_group_gates"] or p["changed_seed_gates"] for p in report["convergence"])):
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
    return (json.dumps(dict(experiment="OPA-NL-017",workflow_run_id=RUN,
        job_id=134963287020,artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,
        artifact_bytes=ZIP_SIZE,head_sha="eb312013bb8e63035d4aed471ad14f73dfa523a9",
        merge_sha="d06cbd17b2cc52953e4bf1dc0b7ad586401ac11d",pull_request=191,
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
    print("Verified exact NL017 evidence and provenance.")

if __name__=="__main__":
    main()
