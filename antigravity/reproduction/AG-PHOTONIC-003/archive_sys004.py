"""Verify and stage exact OPA-SYS-004 evidence, never execute artifact content."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

EXPECTED = {
    "environment-lock.txt": (9532, "a413f375d4a3097d7cb7c9922da7288e15ad77026afdcb11d8f6945375ee8c4c"),
    "installed-packages.json": (68543, "f8bf20346f3dcd14fac94e7b91949ca983197c352d906a00e6b8152b0acf60f6"),
    "baseline_feasible.json": (676681, "7eba2c260f328b9535f4302f05db1257ae55ccee1d7b8902d6be2ae65d811392"),
    "combined_feasible.json": (1276755, "3d93eeccf35e2470e9392214c97ce9df40077e468a5c46717af306c068847a4f"),
    "laser_only_feasible.json": (1212564, "16d9b1a64f9cd598842a9d89258058a0524608d0f4616e0c103e1d07271c0ef8"),
    "paired_changes.csv": (12696485, "d7be0b9ec2d900dbdf4df0819be61334b06fc9dc0863cdbea7b96a98e7342b66"),
    "receiver_only_feasible.json": (740872, "507e512c30391e3e499ec0ccdd264725685ed372c8adc615d4465ddde07d97a9"),
    "result.json": (64645, "98a77c96b6549b825b995c75e4cb513386fde5589c400089e13891d199633cc8"),
}
PROVENANCE = {
    "experiment": "OPA-SYS-004",
    "workflow_run_id": 44113634095,
    "job_id": 134145734488,
    "artifact_id": 14340214791,
    "artifact_sha256": "1bd2c6b94eb2acbb0a2b51cdc7f1b8ee26bd4dba075f8cb12e75d589dd821ef3",
    "artifact_bytes": 482695,
    "head_sha": "a9e88dc885d48e596f5684631a5468caabcc1f28",
    "merge_sha": "625b408c2d9b883a679a35940dbb3f80fac24b14",
    "pull_request": 116,
    "source_url": "https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44113634095/job/134145734488",
    "artifact_url": "https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44113634095/artifacts/14340214791",
    "verification": "Original ZIP digest and CRC independently checked before pinning; archive workflow verifies run identity and all eight exact extracted bytes before and after Git staging.",
    "files": {name: {"bytes": size, "sha256": digest} for name, (size, digest) in EXPECTED.items()},
}

def provenance_bytes():
    return (json.dumps(PROVENANCE, indent=2, sort_keys=True) + "\n").encode()

def verify(source, staged=False):
    if source.is_symlink() or not source.is_dir():
        raise ValueError("invalid source directory")
    names = set(EXPECTED) | ({"provenance.json"} if staged else set())
    if {p.name for p in source.iterdir()} != names:
        raise ValueError("unexpected or missing evidence files")
    for name, (size, digest) in EXPECTED.items():
        p = source / name
        if p.is_symlink() or not p.is_file() or p.stat().st_size != size:
            raise ValueError(f"invalid evidence file: {name}")
        if hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            raise ValueError(f"hash mismatch: {name}")
    if staged:
        p = source / "provenance.json"
        if p.is_symlink() or not p.is_file() or p.read_bytes() != provenance_bytes():
            raise ValueError("provenance mismatch")

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--staged", action="store_true")
    args = p.parse_args()
    if args.staged and args.output:
        p.error("--staged and --output are mutually exclusive")
    verify(args.source, staged=args.staged)
    if args.output:
        args.output.mkdir(parents=False, exist_ok=False)
        try:
            for name in EXPECTED:
                shutil.copyfile(args.source / name, args.output / name)
            (args.output / "provenance.json").write_bytes(provenance_bytes())
            verify(args.output, staged=True)
        except Exception:
            shutil.rmtree(args.output)
            raise
    print("Verified eight exact OPA-SYS-004 evidence files.")

if __name__ == "__main__":
    main()
