"""Restore MOD-007 scientific outputs exactly; Python standard library only."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def verify(data, digest, name):
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f"SHA-256 mismatch: {name}")


def recover():
    p = json.loads((HERE / "provenance.json").read_text())
    chunks = []
    for part in p["report_parts"]:
        data = (HERE / part["file"]).read_bytes()
        if len(data) != part["bytes"]:
            raise ValueError(f"Incorrect length: {part['file']}")
        if hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest() != part["git_blob_sha"]:
            raise ValueError(f"Git blob mismatch: {part['file']}")
        chunks.append(data)
    raw = b"".join(chunks)
    if len(raw) != p["report_bytes"]:
        raise ValueError("Incorrect report length")
    verify(raw, p["report_sha256"], "result.json")
    report = json.loads(raw)
    outputs = {"result.json": raw}
    for filename, key in (("metrics.csv", "rows"), ("learning_curves.csv", "curves"),
                          ("comparisons.csv", "comparisons"), ("layer_errors.csv", "layer_errors")):
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=list(report[key][0]))
        writer.writeheader()
        writer.writerows(report[key])
        outputs[filename] = stream.getvalue().encode("utf-8")
    for filename, data in outputs.items():
        verify(data, p["artifact_files"][filename], filename)
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="Restore into folder without overwriting files")
    args = parser.parse_args()
    outputs = recover()
    if args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        if any((args.output_dir / name).exists() for name in outputs):
            raise FileExistsError("Output files already exist")
        for name, data in outputs.items():
            with (args.output_dir / name).open("xb") as f:
                f.write(data)
    print("Verified exact SHA-256 of all five scientific outputs:", ", ".join(outputs))


if __name__ == "__main__":
    main()
