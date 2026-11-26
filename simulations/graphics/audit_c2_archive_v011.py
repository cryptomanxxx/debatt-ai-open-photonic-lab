"""C3A stage 1: independent archive integrity and traversal-accounting audit.

Read only the frozen C2 originals. No simulation or hardware timing.
"""
import csv
import hashlib
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path
from fractions import Fraction
import argparse

SCENARIOS = ("scale_only", "large_scale", "noise_only", "combined", "drift_quantization")
POLICIES = ("electronic_only", "all_optical_fallback", "raw", "max_min_125")
FILES = {"audit.csv", "calibration.json", "environment-lock.txt", "installed-packages.json",
         "labels.json", "node-results.csv", "result.json", "results.csv", "workload.json"}
KEY = ("scenario", "repeat", "scene", "ray", "policy")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def key(row):
    return tuple(row[k] for k in KEY)


def audit(root):
    manifest = json.loads((root / "archive-provenance.json").read_text())
    require(set(manifest["files"]) == FILES, "manifest file set")
    total = 0
    for name, metadata in manifest["files"].items():
        data = (root / name).read_bytes()
        total += len(data)
        require(len(data) == metadata["bytes"], name + ": bytes")
        require(hashlib.sha256(data).hexdigest() == metadata["sha256"], name + ": SHA256")
        require(hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
                == metadata["git_blob_sha1"], name + ": git blob")
    require(total == manifest["expanded_bytes"], "expanded bytes")
    result = json.loads((root / "result.json").read_text())
    for name in ("workload", "labels"):
        require(result[name + "_sha256"] == manifest["files"][name + ".json"]["sha256"],
                name + ": frozen digest")
    workload = json.loads((root / "workload.json").read_text())
    scenes = {s["name"]: s for s in workload["scenes"]}
    labels = json.loads((root / "labels.json").read_text())
    label_map = {(l["scene"], str(l["ray"])): l for l in labels}
    require(len(label_map) == len(labels), "duplicate label")
    require(set(label_map) == {(name, str(i)) for name, s in scenes.items()
                              for i in range(len(s["rays"]))}, "label coverage")
    eligible = {k for k, l in label_map.items() if not l["excluded"]}
    require(len(eligible) == 249 and len(labels) == 250, "eligible/excluded counts")
    expected = {(s, str(r), scene, ray, p) for s, r, (scene, ray), p in
                itertools.product(SCENARIOS, range(10), eligible, POLICIES)}
    seen = set()
    aggregate = defaultdict(Counter)
    panels = defaultdict(Counter)
    node_count = 0
    summary = {(r["scenario"], r["policy"]): r for r in result["summary"]}
    require(len(summary) == len(result["summary"]) == 20, "summary keys")
    with (root / "results.csv").open(newline="") as rf, (root / "node-results.csv").open(newline="") as nf:
        groups = iter(itertools.groupby(csv.DictReader(nf), key=key))
        for row in csv.DictReader(rf):
            k = key(row)
            require(k in expected and k not in seen, f"invalid/duplicate ray {k}")
            seen.add(k)
            group = next(groups, None)
            require(group is not None and group[0] == k, f"missing/misordered node group {k}")
            nodes = list(group[1])
            node_count += len(nodes)
            scene = scenes[k[2]]
            topology = scene["nodes"]
            visited, accepted, tested = [], [], []
            counts = Counter()
            stack = [0]
            for n in nodes:
                i = int(n["node"])
                require(bool(stack) and i == stack.pop() and 0 <= i < len(topology)
                        and i not in visited, f"invalid traversal {k}/{i}")
                visited.append(i)
                exact, cpu, raw, decision, fallback = (int(n[f]) for f in
                                                        ("exact", "cpu", "raw", "decision", "fallback"))
                require(all(x in (0, 1) for x in (exact, cpu, raw, decision, fallback)), f"boolean {k}/{i}")
                counts["node_fp"] += decision == 1 and exact == 0
                counts["node_fn"] += decision == 0 and exact == 1
                counts["raw_fp"] += raw == 1 and exact == 0
                counts["raw_fn"] += raw == 0 and exact == 1
                if k[4] != "electronic_only":
                    optical = int(n["guard"]) == 0
                    counts["optical"] += optical
                    counts["guards"] += not optical
                    counts["fallback"] += fallback
                    require(not fallback or optical, f"fallback outside optics {k}/{i}")
                else:
                    require(not fallback and decision == cpu, f"electronic policy {k}/{i}")
                if decision:
                    accepted.append(i)
                    node = topology[i]
                    if node["children"]:
                        stack.extend(reversed(node["children"]))
                    else:
                        counts["leaves"] += 1
                        tested.extend(node["primitives"])
            require(not stack, f"incomplete traversal {k}")
            for name, ids in (("visited", visited), ("accepted", accepted), ("tested", tested)):
                require(json.loads(row[name + "_ids"]) == ids, f"{name} IDs {k}")
            counts.update(nodes=len(visited), accepted=len(accepted), triangles=len(tested))
            for field in ("nodes", "accepted", "triangles", "leaves", "node_fp", "node_fn",
                          "raw_fp", "raw_fn", "guards", "optical", "fallback"):
                require(counts[field] == int(row[field]), f"{field} {k}")
            require(int(row["driven_operands"]) == 4 * int(row["sides"]), f"operand count {k}")
            label = label_map[k[2:4]]
            require(int(row["exact_id"]) == label["exact_id"], f"exact ID {k}")
            if label["exact_t"] is not None:
                require(Fraction(row["exact_t"]) == Fraction(label["exact_t"]), f"exact t {k}")
            a = aggregate[k[0], k[4]]
            a["rays"] += 1
            for field in summary[k[0], k[4]]:
                if field not in ("scenario", "policy", "rays"):
                    a[field] += int(row[field])
            panels[k[0], k[1], k[2], k[4]].update(
                optical=counts["optical"], fallback=counts["fallback"])
        require(next(groups, None) is None, "extra node groups")
    require(seen == expected and len(seen) == result["rows"] == 49800, "ray coverage")
    require(node_count == result["node_rows"] == 664870, "node coverage")
    for k, s in summary.items():
        for field, value in s.items():
            if field not in ("scenario", "policy"):
                require(aggregate[k][field] == value, f"summary {k}/{field}")
    rates = {k: Fraction(c["fallback"], c["optical"]) for k, c in panels.items()
             if k[3] == "max_min_125" and c["optical"]}
    worst = max(rates.values())
    worst_panels = [{"scenario": k[0], "repeat": int(k[1]), "scene": k[2],
                     **panels[k]} for k in sorted(rates) if rates[k] == worst]
    require(worst == 1, "worst panel fallback")
    return {"stage": "C3A archive accounting only", "passed": True, "files": len(FILES),
            "bytes": total, "rays": len(seen), "nodes": node_count,
            "worst_fallback_fraction": str(worst), "worst_panels": worst_panels,
            "geometry_audit": "not_run", "compiled_benchmark": "not_run",
            "energy": "not_measured"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit(args.archive)
    except Exception as exc:
        report = {"stage": "C3A archive accounting only", "passed": False,
                  "error": str(exc), "geometry_audit": "not_run", "compiled_benchmark": "not_run"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
