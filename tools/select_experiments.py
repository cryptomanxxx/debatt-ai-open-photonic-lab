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
REGISTRY_PATH = "simulations/experiments.json"
REGISTRY = REPO / REGISTRY_PATH
DEFAULT_LOCK = "simulations/meep/opa-fdtd-linux-64.lock.txt"
SCRIPT_RE = re.compile(r"^simulations/[^/]+/[^/]+_v\d{3}\.py$")
IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_]\w*)", re.M)
PATH_RE = re.compile(r"""["']((?:results|simulations|layout)/[^"'\s]+)["']""")
REQUIRED = {"id": str, "name": str, "script": str, "result_dir": str, "artifact": str,
            "timeout_minutes": int, "deps": list}


def load(path=REGISTRY):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def matches(path, patterns):
    return any(path == p or fnmatch.fnmatch(path, p) for p in patterns)


def select_changed(reg, changed, base_reg=None):
    changed = [c.replace("\\", "/") for c in changed]
    registry_changed = REGISTRY_PATH in changed
    # Compare semantic entries, not formatting or ordering. Without a trusted
    # baseline, retain the conservative full non-heavy regression.
    entry_changes = set()
    policy_changed = registry_changed and base_reg is None
    shared_policy_changed = False
    if registry_changed and base_reg is not None:
        old = {e["id"]: e for e in base_reg["experiments"]}
        entry_changes = {e["id"] for e in reg["experiments"]
                         if old.get(e["id"]) != e}
        removed = set(old) - {e["id"] for e in reg["experiments"]}
        # Any global policy change or removal triggers conservative regression.
        # Ignore only the documentation field and the experiment list itself.
        policy = lambda r: {k: v for k, v in r.items()
                            if k not in ("experiments", "_doc")}
        policy_changed = bool(removed) or policy(reg) != policy(base_reg)
        shared_policy_changed = reg["shared"] != base_reg["shared"]
    machinery_patterns = set(reg["machinery"])
    shared_patterns = set(reg["shared"])
    if base_reg is not None:
        machinery_patterns.update(base_reg["machinery"])
        shared_patterns.update(base_reg["shared"])
    machinery = policy_changed or any(
        c != REGISTRY_PATH and matches(c, machinery_patterns) for c in changed)
    # Preserve generic shared dependencies. The original default lock is
    # shared only by experiments that actually use it.
    shared = any(c != DEFAULT_LOCK and matches(c, shared_patterns)
                 for c in changed)
    return [e for e in reg["experiments"]
            if shared or shared_policy_changed or (machinery and not e.get("heavy"))
            or e["id"] in entry_changes
            or any(matches(c, [e["script"], e.get("lock", DEFAULT_LOCK)] + e["deps"])
                   for c in changed)]


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
        if "lock" in e:
            lock = e["lock"]
            if (not isinstance(lock, str) or lock not in e["deps"]
                    or not re.fullmatch(r"simulations/meep/[A-Za-z0-9_-]+\.lock\.txt", lock)):
                errors.append(f"{e['id']}: custom lock must be a simulations/meep lock file listed in deps")
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
             "run": e.get("run", f"python {e['script']}"),
             "lock": e.get("lock", DEFAULT_LOCK)} for e in selected]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--changed", nargs="*", metavar="FILE")
    group.add_argument("--changed-from", metavar="LIST", help="file with one changed path per line")
    group.add_argument("--ids")
    group.add_argument("--check", action="store_true")
    parser.add_argument("--github-output", action="store_true")
    parser.add_argument("--registry", default=str(REGISTRY))
    parser.add_argument("--base-registry", help="Registry at the same merge base as the PR diff")
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
        base_reg = load(args.base_registry) if args.base_registry else None
        selected = select_changed(reg, changed, base_reg)
    m = matrix(selected)
    serial = [e for e in m if e["id"] not in ("opa-id-003", "opa-mod-007")]
    parallel = [e for e in m if e["id"] == "opa-id-003"]
    mod007 = [e for e in m if e["id"] == "opa-mod-007"]
    print("selected:", ", ".join(e["id"] for e in m) or "none")
    if args.github_output:
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
            out.write(f"matrix={json.dumps({'include': m})}\n")
            out.write(f"serial_matrix={json.dumps({'include': serial})}\n")
            out.write(f"serial_any={'true' if serial else 'false'}\n")
            out.write(f"id003_any={'true' if parallel else 'false'}\n")
            out.write(f"id003_lock={parallel[0]['lock'] if parallel else ''}\n")
            out.write(f"mod007_any={'true' if mod007 else 'false'}\n")
            out.write(f"mod007_lock={mod007[0]['lock'] if mod007 else ''}\n")
            out.write(f"any={'true' if m else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
