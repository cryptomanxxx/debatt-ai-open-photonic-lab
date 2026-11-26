"""OPA-G-002: independently derived six side tests, exact arithmetic."""
import csv
import json
from fractions import Fraction
from itertools import permutations, product
from pathlib import Path

import numpy as np

from ray_box_v001 import face_oracle, quantized, workloads, BITS

OUT = Path(__file__).resolve().parents[2] / "results" / "opa-g-002"


def side_test(o, d, lower, upper):
    """Return closed forward-ray classification, six signed products or fewer.

    Reflect negative direction axes so all active directions are positive.
    For each ordered pair i,j, require exit_i >= entry_j. With positive
    denominators, this is a two-product sum with no division.
    Parallel axes and the forward half-line are handled explicitly.
    """
    o, d, lower, upper = [
        tuple(Fraction(float(x)) for x in v)
        for v in (o, d, lower, upper)
    ]
    active = []
    for x, v, a, b in zip(o, d, lower, upper):
        if a > b:
            raise ValueError("unordered box")
        if v == 0:
            if not a <= x <= b:
                return False, (), "parallel_reject"
            continue
        if v < 0:
            x, v, a, b = -x, -v, -b, -a
        active.append((a-x, b-x, v))
    if any(exit_ < 0 for _, exit_, _ in active):
        return False, (), "behind_reject"
    sides = tuple(
        exit_i * v_j - entry_j * v_i
        for (_, exit_i, v_i), (entry_j, _, v_j) in permutations(active, 2)
    )
    return all(s >= 0 for s in sides), sides, "side_test"


def compare(name, cases, reference):
    predictions = [side_test(*case) for case in cases]
    tp = sum(t and p[0] for t,p in zip(reference,predictions))
    tn = sum(not t and not p[0] for t,p in zip(reference,predictions))
    fp = sum(not t and p[0] for t,p in zip(reference,predictions))
    fn = sum(t and not p[0] for t,p in zip(reference,predictions))
    # A strict comparator is intentionally a diagnostic, not our reference.
    strict_fn = sum(t and p[0] and any(s == 0 for s in p[1])
                    for t,p in zip(reference,predictions))
    return dict(workload=name, samples=len(cases), tp=tp, tn=tn, fp=fp, fn=fn,
                strict_extra_misses=strict_fn,
                six_side_cases=sum(len(p[1]) == 6 for p in predictions),
                boundary_cases=sum(any(s == 0 for s in p[1]) for p in predictions),
                precheck_rejects=sum(p[2] != "side_test" for p in predictions))


def main():
    tests = {}
    rows = []
    rng = np.random.default_rng(20261127)
    # General boxes, including all sign octants, translated and degenerate.
    cases = []
    for _ in range(4096):
        lo = rng.integers(-512,513,3)/256
        hi = lo + rng.integers(0,513,3)/256
        o = rng.integers(-1024,1025,3)/256
        d = rng.integers(-256,257,3)/256
        cases.append((o,d,lo,hi))
    # Exhaustive small integer ray directions and origins, fixed unit box.
    lo,hi = (-1,-1,-1),(1,1,1)
    grid = [(o,d,lo,hi) for o in product(range(-2,3),repeat=3)
            for d in product((-1,0,1),repeat=3)]
    controls = [
        ((-2,0,0),(1,1,1),lo,hi,True),
        ((2,0,0),(1,0,0),lo,hi,False),
        ((-2,0,0),(1,0,0),(0,0,0),(0,0,0),True),
        ((0,0,0),(0,0,0),lo,hi,True),
        ((2,0,0),(0,0,0),lo,hi,False),
    ]
    for i,(*case,expected) in enumerate(controls):
        tests[f"control_{i}"] = side_test(*case)[0] == face_oracle(*case) == expected
    for name, group in [("translated",cases),("integer_grid",grid),*workloads()]:
        truth = [face_oracle(*case) for case in group]
        row = compare(name, group, truth)
        rows.append(dict(precision="exact", **row))
        tests[name+"_exact"] = row["fp"] == row["fn"] == 0
        if name in ("uniform","near_face"):
            for bits in BITS:
                rounded = [quantized(case,bits) for case in group]
                rounded_truth = [face_oracle(*case) for case in rounded]
                row = compare(name,rounded,rounded_truth)
                tests[f"{name}_{bits}_rounded_equivalence"] = row["fp"] == row["fn"] == 0
                rows.append(dict(precision=str(bits), **compare(name,rounded,truth)))
    tests["strict_boundary_diagnostic"] = any(r["strict_extra_misses"] > 0 for r in rows)
    tests["six_side_path_exercised"] = any(r["six_side_cases"] > 0 for r in rows)
    result = dict(experiment="opa-g-002", seed=20261127, checks=tests,
                  passed=all(tests.values()), rows=rows,
                  limitations=["Independent algebraic reconstruction; supplementary note not verified",
                               "Exact rational arithmetic, not optical simulation",
                               "Explicit forward/parallel guards, inclusive boundary convention",
                               "No measured performance, energy or rendering claims"])
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    with (OUT/"results.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(result,indent=2))
    if not result["passed"]:
        raise SystemExit("OPA-G-002 gate failed")


if __name__ == "__main__":
    main()
