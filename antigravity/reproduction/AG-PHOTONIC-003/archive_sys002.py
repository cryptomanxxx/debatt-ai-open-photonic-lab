"""Verify and stage exact OPA-SYS-002 evidence, never execute artifact content."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

EXPECTED = {
    "corrected_feasible.json": (676681, "7eba2c260f328b9535f4302f05db1257ae55ccee1d7b8902d6be2ae65d811392"),
    "environment-lock.txt": (9532, "a413f375d4a3097d7cb7c9922da7288e15ad77026afdcb11d8f6945375ee8c4c"),
    "installed-packages.json": (68543, "f8bf20346f3dcd14fac94e7b91949ca983197c352d906a00e6b8152b0acf60f6"),
    "original_feasible.json": (466644, "229f81ef16c0d37d57e4eabf519d1faee121da46a6a9ced89d6fd5610ccf30c7"),
    "paired_changes.csv": (4957111, "e0b86a090e520ff20d4d5a173d65199efea5e2badba44d8c076c35bca51d6fa7"),
    "result.json": (24149, "b15741f443e59dbca8a4032c2550a6d9556f749a534ee3ccbd81602749d672b9"),
}
PROVENANCE = {
    "experiment": "OPA-SYS-002",
    "workflow_run_id": 44106677587,
    "job_id": 134121047274,
    "artifact_id": 14337483644,
    "artifact_sha256": "9f4441e22cc2f7547ed8f4c9f2df5e904d35e20ce3ebfd5d7f031147d4a48a06",
    "artifact_bytes": 218777,
    "head_sha": "1e9776b3c705b0cd6d4e279d93e10855b39bcf24",
    "merge_sha": "43783b2c535a4fa304fa5aa9d3ae232a552bc41e",
    "pull_request": 110,
    "source_url": "https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44106677587/job/134121047274",
    "artifact_url": "https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44106677587/artifacts/14337483644",
    "verification": "Original ZIP digest and CRC independently checked before pinning; archive workflow verifies run identity and all six exact extracted bytes before and after Git staging.",
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
    print("Verified six exact OPA-SYS-002 evidence files.")

if __name__ == "__main__":
    main()
