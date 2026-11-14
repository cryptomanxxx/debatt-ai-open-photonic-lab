"""Reassemble and verify the exact CI report; output is opt-in."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="optional destination for exact JSON")
    args = parser.parse_args()
    provenance = json.loads((HERE / "provenance.json").read_text())
    paths = sorted((HERE / "report-parts").glob("part-*.txt"))
    expected = [f"part-{i:02d}.txt" for i in range(provenance["report_parts"])]
    if [p.name for p in paths] != expected:
        raise SystemExit("missing or unexpected report parts")
    parts = [p.read_bytes() for p in paths]
    if any(len(p) != provenance["part_bytes"] for p in parts[:-1]):
        raise SystemExit("incorrect part length")
    data = b"".join(parts)
    if len(data) != provenance["report_bytes"] or hashlib.sha256(data).hexdigest() != provenance["report_sha256"]:
        raise SystemExit("report checksum mismatch")
    report = json.loads(data)
    if report["experiment"] != "OPA-MOD-005" or len(report["results"]) != 11520 or len(report["scenarios"]) != 288 or report["failures"] or not all(report["checks"].values()):
        raise SystemExit("unexpected report content")
    if args.output is not None:
        with args.output.open("xb") as f:
            f.write(data)
    print(json.dumps({"verified_sha256": provenance["report_sha256"], "checks": report["checks"], "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
