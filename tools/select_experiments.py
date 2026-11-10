"""Choose which registered experiments a change affects, and check the registry.

The experiments that run in CI are listed in simulations/experiments.json and
run by .github/workflows/experiments.yml. This script

    --changed FILE...   prints the experiments whose script, deps or shared
                        files changed (all non-heavy ones if the CI machinery
                        itself changed)
    --ids ID,ID|all     prints the named experiments, or all of them
    --check             fails if the registry is inconsistent: an experiment
                        script (*_vNNN.py under simulations/) without an entry,
                        a missing file, a duplicate id or result folder, or a
                        local module or repository file the script uses that
                        is not in its deps

With --github-output, the selection is written as the `matrix` and `any`
outputs of a GitHub Actions step. Standard library only.
"""
import argparse
import fnmatch
import json
import os
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parent.parent
REGISTRY = REPO / "simulations" / "experiments.json"
SCRIPT_RE = re.compile(r"^simulations/[^/]+/[^/]+_v\d{3}\.py$")
IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_]\w*)", re.M)
PATH_RE = re.compile(r"""["']((?:results|simulations|layout)/[^"'\s]+)["']""")
REQUIRED = {"id": str, "name": str, "script": str, "result_dir": str, "artifact": str,
            "timeout_minutes": int, "deps": list}


def load(path=REGISTRY):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def matches(path, patterns):
    return any(path == p or fnmatch.fnmatch(path, p) for p in patterns)


def select_changed(reg, changed):
    changed = [c.replace("\\", "/") for c in changed]
    if any(matches(c, reg["machinery"]) for c in changed):
        return [e for e in reg["experiments"] if not e.get("heavy")]
    shared = any(matches(c, reg["shared"]) for c in changed)
    return [e for e in reg["experiments"]
            if shared or any(matches(c, [e["script"]] + e["deps"]) for c in changed)]


def select_ids(reg, ids):
    if ids.strip() == "all":
        return list(reg["experiments"])
    wanted = [i.strip() for i in ids.split(",") if i.strip()]
    by_id = {e["id"]: e for e in reg["experiments"]}
    unknown = [i for i in wanted if i not in by_id]
    if unknown:
        raise SystemExit(f"unknown experiment id(s): {', '.join(unknown)}")
    return [by_id[i] for i in wanted]


def check(reg, repo=REPO):
    errors = []
    for key in ("shared", "machinery", "experiments"):
        if not isinstance(reg.get(key), list):
            errors.append(f"registry: '{key}' must be a list")
    if errors:
        return errors
    exps = reg["experiments"]
    for e in exps:
        for key, kind in REQUIRED.items():
            if not isinstance(e.get(key), kind) or isinstance(e.get(key), bool):
                errors.append(f"{e.get('id', '?')}: '{key}' must be a {kind.__name__}")
    if errors:
        return errors
    for key in ("id", "result_dir", "artifact", "script"):
        values = [e[key] for e in exps]
        errors += [f"duplicate {key} '{v}'" for v in sorted({v for v in values if values.count(v) > 1})]
    registered = {e["script"] for e in exps}
    for f in sorted((repo / "simulations").glob("*/*.py")):
        rel = f.relative_to(repo).as_posix()
        if SCRIPT_RE.match(rel) and rel not in registered:
            errors.append(f"{rel}: experiment script has no entry in simulations/experiments.json")
    for p in reg["shared"]:
        if not (repo / p).is_file():
            errors.append(f"shared file '{p}' does not exist")
    mods = {}
    for f in (repo / "simulations").glob("*/*.py"):
        rel = f.relative_to(repo).as_posix()
        if not SCRIPT_RE.match(rel):
            mods.setdefault(f.stem, rel)
    for e in exps:
        script = repo / e["script"]
        if not script.is_file():
            errors.append(f"{e['id']}: script '{e['script']}' does not exist")
            continue
        for d in e["deps"]:
            hit = any(repo.glob(d)) if any(c in d for c in "*?[") else (repo / d).is_file()
            if not hit:
                errors.append(f"{e['id']}: dep '{d}' matches no file")
        text = script.read_text(encoding="utf-8")
        covered = [e["script"]] + e["deps"] + reg["shared"]
        for name in sorted(set(IMPORT_RE.findall(text))):
            if name in mods and not matches(mods[name], covered):
                errors.append(f"{e['id']}: imports '{name}' ({mods[name]}) but it is not in deps")
        for path in sorted(set(PATH_RE.findall(text))):
            path = path.rstrip("/")
            if path.startswith(e["result_dir"]) or not (repo / path).is_file():
                continue                      # its own output, a folder or a pattern
            if not matches(path, covered):
                errors.append(f"{e['id']}: reads '{path}' but it is not in deps")
    return errors


def matrix(selected):
    return [{"id": e["id"], "name": e["name"], "result_dir": e["result_dir"],
             "artifact": e["artifact"], "timeout": e["timeout_minutes"],
             "run": e.get("run", f"python {e['script']}")} for e in selected]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--changed", nargs="*", metavar="FILE")
    group.add_argument("--changed-from", metavar="LIST", help="file with one changed path per line")
    group.add_argument("--ids")
    group.add_argument("--check", action="store_true")
    parser.add_argument("--github-output", action="store_true")
    parser.add_argument("--registry", default=str(REGISTRY))
    args = parser.parse_args(argv)
    reg = load(args.registry)
    if args.check:
        errors = check(reg)
        for e in errors:
            print("ERROR:", e)
        print(f"{len(reg['experiments'])} experiment(s), {len(errors)} error(s)")
        return 1 if errors else 0
    if args.ids is not None:
        selected = select_ids(reg, args.ids)
    else:
        changed = args.changed if args.changed is not None else \
            [l for l in Path(args.changed_from).read_text().splitlines() if l.strip()]
        selected = select_changed(reg, changed)
    m = matrix(selected)
    print("selected:", ", ".join(e["id"] for e in m) or "none")
    if args.github_output:
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
            out.write(f"matrix={json.dumps({'include': m})}\n")
            out.write(f"any={'true' if m else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
