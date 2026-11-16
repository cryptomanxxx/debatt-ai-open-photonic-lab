"""Merge complete MOD-007 shards without changing scientific parameters."""
import itertools
import json
import math
from pathlib import Path
import sys
import modular_multilayer_v007 as mod

def merge(root):
    reports = []
    for seed, depth, size in itertools.product(mod.SEEDS, mod.DEPTHS, mod.SIZES):
        p = root / f"mod007-{seed}-{depth}-{size}" / "result.json"
        r = json.loads(p.read_text())
        cfg = r["config"]
        if (cfg["seeds"], cfg["depths"], cfg["tile_sizes"]) != ([seed], [depth], [size]):
            raise ValueError("Wrong shard identity")
        if not r["checks"] or not all(r["checks"].values()):
            raise ValueError("Failed shard")
        reports.append(r)
    result = reports[0].copy()
    result["config"] = dict(result["config"], seeds=mod.SEEDS, depths=mod.DEPTHS, tile_sizes=mod.SIZES)
    for key in ("rows", "curves", "comparisons", "layer_errors"):
        digital, optical = {}, []
        for r in reports:
            if r["numpy_version"] != result["numpy_version"] or r["assumptions"] != result["assumptions"]:
                raise ValueError("Inconsistent shard provenance")
            for row in r[key]:
                if row.get("method") == "digital":
                    identity = (row["seed"], row["depth"], row.get("step"))
                    if identity in digital:
                        for k, v in row.items():
                            old = digital[identity][k]
                            if isinstance(v, float):
                                if not math.isclose(v, old, rel_tol=1e-9, abs_tol=1e-12):
                                    raise ValueError("Digital baseline mismatch")
                            elif v != old:
                                raise ValueError("Digital baseline mismatch")
                    else:
                        digital[identity] = row
                else:
                    optical.append(row)
        result[key] = list(digital.values()) + optical
    for key, count in (("rows",150), ("curves",2496), ("comparisons",72), ("layer_errors",360)):
        if len(result[key]) != count:
            raise ValueError(f"Wrong {key} count")
    result["gradient_max_abs_error"] = max(r["gradient_max_abs_error"] for r in reports)
    result["ideal_max_abs_error"] = max(r["ideal_max_abs_error"] for r in reports)
    result["checks"] = {k: all(r["checks"][k] for r in reports) for k in result["checks"]}
    return result

if __name__ == "__main__":
    sys.exit(mod.write_report(merge(Path(sys.argv[1]))))
