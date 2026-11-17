"""Verify and stage exact OPA-SYS-003 evidence, never execute artifact content."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

EXPECTED = {
    "environment-lock.txt": (9532, "a413f375d4a3097d7cb7c9922da7288e15ad77026afdcb11d8f6945375ee8c4c"),
    "installed-packages.json": (68543, "f8bf20346f3dcd14fac94e7b91949ca983197c352d906a00e6b8152b0acf60f6"),
    "coherent.csv": (516, "eef6ce11b18b68d02665e6720afd2b8f44a0bf2ac9a8d7fd70b40791b28ad304"),
    "link.csv": (48176, "333d7a7b3c52cfa38c432e739a01df4cb16b214941de671206e24215fa5f00d3"),
    "receiver.csv": (65145, "b6cc40c0303bd44acc56fb12c4ca2515f9be3cce2022d5e481fa188d774ba52f"),
    "result.json": (9412, "36b097e753ca23cd0ed655d3901171e7ab9d309522ef8c0d1e0fec9838ff45bf"),
}
PROVENANCE = {
    "experiment": "OPA-SYS-003",
    "workflow_run_id": 44110377779,
    "job_id": 134134278802,
    "artifact_id": 14341345457,
    "artifact_sha256": "a8fca83090e05522b5d2f82843dc36d758ff00c75f950fff8805b404dc3b7a44",
    "artifact_bytes": 37403,
    "head_sha": "1b99e0765e231029c645faa1079b955393e48fb6",
    "merge_sha": "663fec27c434433d87862b1cf9ae397339c29967",
    "pull_request": 113,
    "source_url": "https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44110377779/job/134134278802",
    "artifact_url": "https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44110377779/artifacts/14341345457",
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
    print("Verified six exact OPA-SYS-003 evidence files.")

if __name__ == "__main__":
    main()
