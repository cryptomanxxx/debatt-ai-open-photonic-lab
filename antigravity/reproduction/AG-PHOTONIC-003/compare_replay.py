"""Compare archived and replayed AG003 structured output without importing agent code."""
import argparse
import json
import math
from pathlib import Path

SECTIONS = ("equations_and_conventions", "parameter_provenance",
            "analytic_sweep_summary", "physical_verification",
            "rankings_and_pareto_candidates")
RUNTIME_PATHS = {
    ("physical_verification", "circuit_transfer_matrix_sim", "runtime_s"),
    ("physical_verification", "nn_training_convergence_sim", "runtime_s"),
}

def compare(original, replay):
    differences = []
    counts = {"matched": 0, "numeric_within_tolerance": 0, "runtime_ignored": 0}
    def diff(path, reason, a, b):
        differences.append({"path": "/".join(map(str, path)), "reason": reason,
                            "original": a, "replay": b})
    def walk(a, b, path):
        if path in RUNTIME_PATHS:
            counts["runtime_ignored"] += 1
            return
        if type(a) is not type(b):
            diff(path, "type", a, b)
        elif isinstance(a, dict):
            for k in sorted(a.keys() | b.keys()):
                if k not in a or k not in b:
                    diff(path + (k,), "missing_key", k in a, k in b)
                else:
                    walk(a[k], b[k], path + (k,))
        elif isinstance(a, list):
            if len(a) != len(b):
                diff(path, "list_length", len(a), len(b))
            for i, (x, y) in enumerate(zip(a, b)):
                walk(x, y, path + (i,))
        elif isinstance(a, float):
            if not math.isfinite(a) or not math.isfinite(b):
                diff(path, "nonfinite", str(a), str(b))
            elif a == b:
                counts["matched"] += 1
            elif math.isclose(a, b, rel_tol=1e-8, abs_tol=1e-10):
                counts["numeric_within_tolerance"] += 1
            else:
                diff(path, "numeric", a, b)
        elif a == b:
            counts["matched"] += 1
        else:
            diff(path, "value", a, b)
    for section in SECTIONS:
        if section not in original or section not in replay:
            diff((section,), "missing_section", section in original, section in replay)
        else:
            walk(original[section], replay[section], (section,))
    expected_env = original["environment"]
    actual_env = replay["environment"]
    versions = {k: {"original": expected_env[k], "replay": actual_env[k],
                    "match": expected_env[k] == actual_env[k]}
                for k in ("python", "numpy", "pandas")}
    return {"schema_version": 1, "experiment": "AG-PHOTONIC-003",
            "structured_match": not differences,
            "dependency_versions_match": all(v["match"] for v in versions.values()),
            "versions": versions,
            "comparison_counts": counts,
            "difference_count": len(differences), "differences": differences,
            "numeric_tolerance": {"relative": 1e-8, "absolute": 1e-10},
            "scope": list(SECTIONS),
            "excluded": ["environment (versions reported separately)", "narrative findings",
                         "limitations prose", "two explicit runtime_s fields"],
            "scientific_validation": False,
            "note": "Matching output is replay evidence, not independent validation of physics."}

def load(path):
    def reject(value):
        raise ValueError("Nonfinite JSON constant")
    return json.loads(path.read_text(), parse_constant=reject)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original", type=Path, required=True)
    p.add_argument("--replay", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = compare(load(a.original), load(a.replay))
    a.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "differences"}, indent=2))
    return 0 if result["structured_match"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
