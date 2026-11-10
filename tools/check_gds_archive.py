"""Check the GDS archive in gds/ (see gds/README.md).

Every release folder must contain a provenance.json with the required fields,
a valid status, and a SHA-256 checksum for every GDS file in the folder. The
script fails if a checksum does not match, a GDS file has no checksum, or a
listed file is missing. It uses only the Python standard library.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent / "gds"
REQUIRED = ("design", "version", "date", "status", "pdk", "generator", "released_to", "files")
STATUSES = {"exploratory", "drc-clean", "submitted", "fabricated"}


def check_release(folder):
    errors = []
    prov_path = folder / "provenance.json"
    if not prov_path.is_file():
        return [f"{folder.name}: missing provenance.json"]
    try:
        prov = json.loads(prov_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{folder.name}: provenance.json is not valid JSON ({exc})"]
    for key in REQUIRED:
        if key not in prov:
            errors.append(f"{folder.name}: provenance.json lacks '{key}'")
    if prov.get("status") not in STATUSES:
        errors.append(f"{folder.name}: status must be one of {sorted(STATUSES)}")
    listed = prov.get("files", {})
    for gds in sorted(folder.glob("*.gds")) + sorted(folder.glob("*.oas")):
        if gds.name not in listed:
            errors.append(f"{folder.name}: {gds.name} has no checksum in provenance.json")
    for name, expected in listed.items():
        path = folder / name
        if not path.is_file():
            errors.append(f"{folder.name}: listed file {name} is missing")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            errors.append(f"{folder.name}: {name} sha256 {actual} != recorded {expected}")
    return errors


def main():
    releases = [p for p in sorted(ROOT.iterdir()) if p.is_dir()] if ROOT.is_dir() else []
    errors = [e for folder in releases for e in check_release(folder)]
    for e in errors:
        print("ERROR:", e)
    print(f"checked {len(releases)} release folder(s), {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
