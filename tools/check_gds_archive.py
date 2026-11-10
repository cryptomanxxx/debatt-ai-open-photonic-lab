"""Check the GDS archive in gds/ (see gds/README.md).

Every release folder must contain a provenance.json with the required fields,
a valid status, generator information, and a SHA-256 checksum for every GDS
file in the folder. The script fails if a checksum does not match, a GDS file
has no checksum, or a listed file is missing.

With --base <git-ref>, releases are also checked for immutability: every file
that exists under a release folder at the base revision must still exist and
be byte-identical. New release folders may be added. The top-level
gds/README.md is not a release and may change.

Uses only the Python standard library and git.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO / "gds"
REQUIRED = ("design", "version", "date", "status", "pdk", "generator", "released_to", "files")
STATUSES = {"exploratory", "drc-clean", "submitted", "fabricated"}
GENERATOR_FIELDS = ("script", "commit", "environment")


def nonempty_str(value):
    return isinstance(value, str) and value.strip() != ""


def check_generator(name, gen):
    """Either script + commit + environment, or an explicit 'external' explanation."""
    if not isinstance(gen, dict):
        return [f"{name}: 'generator' must be an object"]
    if "external" in gen:
        if not nonempty_str(gen["external"]):
            return [f"{name}: 'generator.external' must explain where the file came from "
                    f"and why it cannot be regenerated from this repository"]
        return []
    missing = [f for f in GENERATOR_FIELDS if not nonempty_str(gen.get(f))]
    if missing:
        return [f"{name}: 'generator' needs non-empty {', '.join(missing)} "
                f"(or an 'external' explanation)"]
    return []


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
    if "generator" in prov:
        errors += check_generator(folder.name, prov["generator"])
    listed = prov.get("files", {})
    if not isinstance(listed, dict) or not listed:
        errors.append(f"{folder.name}: 'files' must list at least one file and its sha256")
        listed = {}
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


def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], check=True,
                          capture_output=True).stdout


def check_immutable(base):
    """Files under release folders at `base` must be unchanged in the working tree."""
    errors = []
    # -z: NUL-separated, unquoted paths (default output quotes non-ASCII names).
    listing = git("ls-tree", "-r", "-z", "--name-only", base, "--", "gds/").split(b"\0")
    for path in (p.decode("utf-8") for p in listing if p):
        parts = Path(path).parts
        if len(parts) < 3:            # gds/README.md and other top-level files
            continue
        current = REPO / path
        if not current.is_file():
            errors.append(f"{path}: released file was deleted (releases are frozen)")
            continue
        if current.read_bytes() != git("show", f"{base}:{path}"):
            errors.append(f"{path}: released file was modified (releases are frozen; "
                          f"add a new release folder instead)")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", help="git ref to check release immutability against")
    args = parser.parse_args()
    releases = [p for p in sorted(ROOT.iterdir()) if p.is_dir()] if ROOT.is_dir() else []
    errors = [e for folder in releases for e in check_release(folder)]
    if args.base:
        errors += check_immutable(args.base)
    for e in errors:
        print("ERROR:", e)
    print(f"checked {len(releases)} release folder(s)"
          f"{' against ' + args.base if args.base else ''}, {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
