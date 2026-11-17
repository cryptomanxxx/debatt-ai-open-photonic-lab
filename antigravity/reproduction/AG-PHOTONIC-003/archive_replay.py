"""Verify and archive the exact six files from AG003 replay run 44090316677."""
import argparse
from pathlib import Path
from import_snapshot import import_snapshot, verify
from compare_replay import compare, load

EXPECTED = {
    "build.log": (5360, "a62686f6015c160e0b5c710ca96808552128b2afce2e95e0aedb6c55d7f11bb4"),
    "exit-code.txt": (2, "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"),
    "comparison.json": (1120, "e65201bb934472da544d9319a67718ca636d67d250211f4dfb575710999c250c"),
    "image-id.txt": (72, "6256d1182c27b7440d0d3ffa11d229b2864730f49985f676147fddc186ae0a8a"),
    "replay-report.json": (84102, "8b04701ef60f1d15e2dca541d0d2179225805224e93afda27a041e5d169b5ef7"),
    "replay.log": (144, "7ec1a52f134d0e8ba3aa8386a92b344bd30cf5d4cf7d064dbd25d73d7fe83041"),
}

def validate(source, original):
    verify(source, EXPECTED)
    verify(original)
    result = compare(load(original / "report.json"), load(source / "replay-report.json"))
    if result != load(source / "comparison.json"):
        raise ValueError("Recorded comparison does not match recomputation")
    if not result["structured_match"] or not result["dependency_versions_match"]:
        raise ValueError("Replay did not match")
    if (source / "exit-code.txt").read_bytes() != b"0\n":
        raise ValueError("Nonzero exit code")
    return result

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--original", required=True, type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    result = validate(a.source, a.original)
    if a.output:
        import_snapshot(a.source, a.output, EXPECTED)
    print(result["comparison_counts"])
    print("Exact replay artifact verified; scientific validation remains pending.")

if __name__ == "__main__":
    main()
