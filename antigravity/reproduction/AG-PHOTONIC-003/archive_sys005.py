"""Verify and stage exact OPA-SYS-005 evidence, never execute artifact content."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

EXPECTED = {
    "environment-lock.txt": (9532, "a413f375d4a3097d7cb7c9922da7288e15ad77026afdcb11d8f6945375ee8c4c"),
    "fixed_max_feasible.json": (5250237, "0513fa6f27163353c2faa7f9cb531573cf683b032400d9ffb998e581bf2d5817"),
    "installed-packages.json": (68543, "f8bf20346f3dcd14fac94e7b91949ca983197c352d906a00e6b8152b0acf60f6"),
    "legacy_feasible.json": (1276755, "3d93eeccf35e2470e9392214c97ce9df40077e468a5c46717af306c068847a4f"),
    "optimized_feasible.json": (6046779, "2bd63d2dccba1a92d9902cf0e94a0e0c1ad70e2239793e94ddee82a4372d6b07"),
    "paired_changes.csv": (11538491, "8c4bd980489c9f8f2c508eb35f55760ced5bd61cdf46ca65d2b1f6d4eb5ca8d2"),
    "result.json": (76589, "a40fe903f7fdfc95844f04385024ab266692b9ee754969fb0c27fd93aedc28a5"),
}
PROVENANCE = {
    "experiment": "OPA-SYS-005",
    "workflow_run_id": 44118436433,
    "job_id": 134162925300,
    "artifact_id": 14343438072,
    "artifact_sha256": "6045ee657ecab9e8045631ec713887e9194393028ba044100aa7803b12b15753",
    "artifact_bytes": 1190343,
    "head_sha": "418d7d745e2c903a1e2b85b5c3c501a39be014a4",
    "merge_sha": "1d3a17257d5302043e43fc42f5b69a43e2f1bffa",
    "pull_request": 120,
    "source_url": "https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44118436433/job/134162925300",
    "artifact_url": "https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44118436433/artifacts/14343438072",
    "verification": "Original ZIP digest and CRC independently checked before pinning; archive workflow verifies run identity and all seven exact extracted bytes before and after Git staging.",
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
    print("Verified seven exact OPA-SYS-005 evidence files.")

if __name__ == "__main__":
    main()
