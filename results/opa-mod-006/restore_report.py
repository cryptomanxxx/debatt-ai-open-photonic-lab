"""Restore the exact MOD-006 JSON and CSV outputs; standard library only."""
import argparse
import base64
import csv
import hashlib
import io
import json
import lzma
from pathlib import Path

HERE = Path(__file__).resolve().parent


def verify(data, digest, name):
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f"SHA-256 mismatch: {name}")


def recover():
    p = json.loads((HERE / "provenance.json").read_text())
    parts = []
    for part in p["report_parts"]:
        data = (HERE / part["file"]).read_bytes()
        if len(data) != part["bytes"]:
            raise ValueError(f"Wrong length: {part['file']}")
        git_data = f"blob {len(data)}\0".encode() + data
        if hashlib.sha1(git_data).hexdigest() != part["git_blob_sha"]:
            raise ValueError(f"Git blob mismatch: {part['file']}")
        parts.append(data)
    compressed = base64.b64decode(b"".join(parts), validate=True)
    verify(compressed, p["compressed_sha256"], "compressed report")
    raw = lzma.decompress(compressed)
    if len(raw) != p["report_bytes"]:
        raise ValueError("Wrong report length")
    verify(raw, p["report_sha256"], "result.json")
    report = json.loads(raw)
    outputs = {"result.json": raw}
    for filename, key in (("metrics.csv", "rows"),
                          ("learning_curves.csv", "curves"),
                          ("comparisons.csv", "comparisons")):
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
    parser.add_argument("--output-dir", type=Path, help="New or existing output folder; never overwrite files")
    args = parser.parse_args()
    outputs = recover()
    if args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        if any((args.output_dir / filename).exists() for filename in outputs):
            raise FileExistsError("Output files already exist")
        for filename, data in outputs.items():
            with (args.output_dir / filename).open("xb") as f:
                f.write(data)
    print("Verified exact SHA-256 of all four outputs:", ", ".join(outputs))


if __name__ == "__main__":
    main()
