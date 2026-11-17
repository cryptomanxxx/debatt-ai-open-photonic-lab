"""Verify and stage exact OPA-SYS-006 evidence, never execute artifact content."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

EXPECTED = {
    "derating.csv": (1283, "63800fa43613d30a6b74ec48164b8b58bd89a3bc7ba859dd8560ab0aef351b09"),
    "environment-lock.txt": (9532, "a413f375d4a3097d7cb7c9922da7288e15ad77026afdcb11d8f6945375ee8c4c"),
    "installed-packages.json": (68543, "f8bf20346f3dcd14fac94e7b91949ca983197c352d906a00e6b8152b0acf60f6"),
    "learning_curves.csv": (851461, "451775ec1b1c5855fdee259cbaf4c2fdd1e36656fdaf487a86081989334085a9"),
    "metrics.csv": (15743, "5f32bfe98c6b31ab85823726cc26a712ee2c4b1f948c8c4dca7464d6ed5b4100"),
    "paired_deploy.csv": (3861, "bb5a8c759b7bff55f2164b1e20dd76964821238299d831801b35290f54b43604"),
    "result.json": (34950, "46f3945cfa427a0377814260e1af39fea7946f8fd3b4320d6189b0217aa9aab5"),
}
PROVENANCE = {
    "experiment": "OPA-SYS-006",
    "workflow_run_id": 44125011406,
    "job_id": 134186489630,
    "artifact_id": 14347985409,
    "artifact_sha256": "dbf45cf71e8d3d1faaafb171badba61f6156b6345be28b8de1370c06eb47187e",
    "artifact_bytes": 220764,
    "head_sha": "a44a5fd40c396b54e84104592b415b76038f3930",
    "merge_sha": "05179f672d0428b5828149638c1a129deeb68ab0",
    "pull_request": 123,
    "source_url": "https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44125011406/job/134186489630",
    "artifact_url": "https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44125011406/artifacts/14347985409",
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
    print("Verified seven exact OPA-SYS-006 evidence files.")

if __name__ == "__main__":
    main()
