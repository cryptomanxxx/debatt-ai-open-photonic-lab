"""OPA-G-001: forward ray / closed AABB, numerical input quantization only."""
import csv
import json
from fractions import Fraction
from pathlib import Path

import numpy as np

BITS = (2, 4, 6, 8, 12, 16)
SEED = 20261126
N = 4096
OUT = Path(__file__).resolve().parents[2] / "results" / "opa-g-001"


def slab(o, d, lower, upper):
    """Float64 slab reference; zero direction is a stationary point."""
    near, far = 0.0, float("inf")
    for x, v, a, b in zip(o, d, lower, upper):
        if v == 0:
            if not a <= x <= b:
                return False
        else:
            t1, t2 = (a - x) / v, (b - x) / v
            near, far = max(near, min(t1, t2)), min(far, max(t1, t2))
            if near > far:
                return False
    return True


def face_oracle(o, d, lower, upper):
    """Independent exact rational face enumeration on represented inputs."""
    o, d, lower, upper = [tuple(map(lambda x: Fraction(float(x)), v))
                           for v in (o, d, lower, upper)]
    def inside(p):
        return all(a <= x <= b for x, a, b in zip(p, lower, upper))
    if inside(o):
        return True
    for axis in range(3):
        if d[axis] == 0:
            continue
        for face in (lower[axis], upper[axis]):
            t = (face - o[axis]) / d[axis]
            if t >= 0 and inside(tuple(x + t * v for x, v in zip(o, d))):
                return True
    return False


def quantized(case, bits):
    """Unbounded signed fixed-point grid, round-to-nearest ties-to-even."""
    scale = 2 ** bits
    return tuple(np.rint(np.asarray(v) * scale) / scale for v in case)


def workloads():
    rng = np.random.default_rng(SEED)
    lower = np.full(3, -1.0)
    upper = np.full(3, 1.0)
    # Dyadic samples avoid accidental exact-boundary floating arithmetic.
    for name in ("uniform", "near_face"):
        cases = []
        for _ in range(N):
            if name == "uniform":
                o = rng.integers(-768, 769, size=3) / 256
                d = rng.integers(-256, 257, size=3) / 256
                if not np.any(d):
                    d[0] = 1
            else:
                # Forward ray parallel to y; exact near-edge label.
                o = np.array([-2., 1 + rng.integers(-128, 129) / 65536,
                              rng.integers(-256, 257) / 256])
                d = np.array([1., 0., 0.])
            cases.append((o, d, lower, upper))
        yield name, cases


def checks():
    lo, hi = (-1, -1, -1), (1, 1, 1)
    cases = [
        ("parallel_hit", (-2, 0, 0), (1, 0, 0), lo, hi, True),
        ("parallel_miss", (-2, 2, 0), (1, 0, 0), lo, hi, False),
        ("inside", (0, 0, 0), (0, 1, 0), lo, hi, True),
        ("negative_direction", (2, 0, 0), (-1, 0, 0), lo, hi, True),
        ("behind", (2, 0, 0), (1, 0, 0), lo, hi, False),
        ("tangent", (-2, 1, 1), (1, 0, 0), lo, hi, True),
        ("corner", (-2, 0, 0), (1, 1, 1), lo, hi, True),
        ("degenerate_plane", (-2, 0, 0), (1, 0, 0), (0,-1,-1), (0,1,1), True),
        ("degenerate_point", (-2, 0, 0), (1, 0, 0), (0,0,0), (0,0,0), True),
        ("stationary_inside", (0,0,0), (0,0,0), lo, hi, True),
        ("stationary_outside", (2,0,0), (0,0,0), lo, hi, False),
        ("near_miss", (-2, 1+2**-16, 0), (1,0,0), lo, hi, False),
    ]
    report = {}
    for name, o, d, a, b, expected in cases:
        report[name] = bool(slab(o,d,a,b) == face_oracle(o,d,a,b) == expected)
    # Both error signs are possible under input rounding.
    for name, case, expected, proxy in [
        ("false_positive_control", ((-2,1+1/16,0),(1,0,0),lo,hi), False, True),
        ("false_negative_control", ((-2,1+1/16,0),(1,-1/16,0),lo,hi), True, False),
    ]:
        # The second control uses an off-grid origin beyond the rounded box;
        # replace with a direction rounding to zero while origin stays outside.
        if name == "false_negative_control":
            case = ((-2,0,0),(1/16,0,0),lo,hi)
        report[name] = bool(face_oracle(*case) == expected and
                            face_oracle(*quantized(case,2)) == proxy)
    return report


def main():
    tests = checks()
    rows = []
    for name, cases in workloads():
        truth = [face_oracle(*case) for case in cases]
        tests[name+"_reference_agreement"] = all(slab(*case) == ref
                                                    for case, ref in zip(cases,truth))
        for bits in BITS:
            # Use exact classification on quantized inputs to isolate input
            # quantization from floating arithmetic and optical imperfections.
            pred = [face_oracle(*quantized(case,bits)) for case in cases]
            tp = sum(a and b for a,b in zip(truth,pred))
            tn = sum(not a and not b for a,b in zip(truth,pred))
            fp = sum(not a and b for a,b in zip(truth,pred))
            fn = sum(a and not b for a,b in zip(truth,pred))
            tests[f"{name}_{bits}_accounting"] = tp+tn+fp+fn == N
            rows.append(dict(workload=name, fractional_bits=bits, samples=N,
                             tp=tp, tn=tn, fp=fp, fn=fn,
                             false_positive_rate=fp/(fp+tn) if fp+tn else None,
                             false_negative_rate=fn/(fn+tp) if fn+tp else None,
                             accuracy=(tp+tn)/N))
        tests[name+"_16bit_identity"] = rows[-1]["fp"] == rows[-1]["fn"] == 0
    OUT.mkdir(parents=True, exist_ok=True)
    result = dict(experiment="opa-g-001", seed=SEED, samples_per_workload=N,
                  checks=tests, passed=all(tests.values()), rows=rows,
                  limitations=["Synthetic dyadic coordinates and fixed unit box",
                               "Fractional bits, not total hardware word width or ENOB",
                               "Exact rational oracle on represented inputs; no optical physics",
                               "No throughput, energy or GPU/VR performance measurements"])
    (OUT / "result.json").write_text(json.dumps(result, indent=2)+"\n")
    with (OUT / "results.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit("OPA-G-001 reference or accounting check failed")


if __name__ == "__main__":
    main()
