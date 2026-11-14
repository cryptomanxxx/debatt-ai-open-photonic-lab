"""OPA-MOD-001: ideal mathematical equivalence of tiled photonic layers.

Factor-level models at N=128, explicit Clements reconstruction at N<=8.
No physical loss, noise, timing, energy or hardware training claims.
"""
import json
from pathlib import Path
import sys

import numpy as np

from mesh import svd_layer, layer_matrix, clements_decompose, mesh_matrix

OUT = Path("results/opa-mod-001")
N = 128
SEED = 101
TOL = 1e-10
SIZES = (128, 64, 32, 16, 8)


def error(actual, expected):
    # Absolute residual for zero reference, relative otherwise.
    denominator = np.linalg.norm(expected)
    return float(np.linalg.norm(actual - expected) / (denominator if denominator else 1.0))


def factors(w, method):
    if method == "svd":
        u, s, vh = np.linalg.svd(w, full_matrices=False)
        scale = float(s.max())
        a = s / scale if scale else np.zeros_like(s)
        return u, a, vh, scale
    q, r = np.linalg.qr(w)
    return q, r


def apply(f, x, method, backward=False):
    if method == "svd":
        u, a, vh, scale = f
        if backward:
            return scale * (vh.conj().T @ (a[:, None] * (u.conj().T @ x)))
        return scale * (u @ (a[:, None] * (vh @ x)))
    q, r = f
    return r.conj().T @ (q.conj().T @ x) if backward else q @ (r @ x)


def tiled(w, x, delta, b, method):
    n = w.shape[0]
    y = np.zeros_like(x, dtype=np.result_type(w, x))
    z = np.zeros_like(delta, dtype=np.result_type(w, delta))
    reconstructed = np.zeros_like(w)
    for i in range(0, n, b):
        for j in range(0, n, b):
            si, sj = slice(i, i+b), slice(j, j+b)
            f = factors(w[si, sj], method)
            y[si] += apply(f, x[sj], method)
            z[sj] += apply(f, delta[si], method, backward=True)
            reconstructed[si, sj] = apply(f, np.eye(b, dtype=w.dtype), method)
    return y, z, reconstructed


def counts(n, b, method):
    k = n // b
    tiles = k*k
    meshes = 2 if method == "svd" else 1
    return {
        "tiles": tiles,
        "unitary_meshes": tiles * meshes,
        "mzi_components": tiles * meshes * b*(b-1)//2,
        "unitary_phase_settings": tiles * meshes * b*b,
        "attenuators": tiles*b if method == "svd" else 0,
        "mesh_columns_per_tile": meshes*b,
        "electronic_triangular_multiplications_per_vector": tiles*b*(b+1)//2 if method == "qr" else 0,
        "electronic_triangular_additions_per_vector": tiles*b*(b-1)//2 if method == "qr" else 0,
        "electronic_output_scale_multiplications_per_vector": tiles*b if method == "svd" else 0,
        "electronic_accumulation_additions_per_vector": n*(k-1),
        "tile_input_elements_per_vector": tiles*b,
        "tile_output_elements_per_vector": tiles*b,
    }


def main():
    rng = np.random.default_rng(SEED)
    q, _ = np.linalg.qr(rng.normal(size=(N, N)))
    v, _ = np.linalg.qr(rng.normal(size=(N, N)))
    cases = {
        "random_signed": rng.normal(size=(N,N))/np.sqrt(N),
        "orthogonal": q,
        "identity": np.eye(N),
        "zero": np.zeros((N,N)),
        "rank_one": np.outer(q[:,0], v[:,0]),
        "ill_conditioned": (q * np.geomspace(1, 1e-10, N)) @ v.T,
    }
    x = rng.normal(size=(N, 8))
    delta = rng.normal(size=(N, 8))
    rows = []
    for name, w in cases.items():
        y_ref, z_ref = w @ x, w.T @ delta
        for b in SIZES:
            for method in ("svd", "qr"):
                y, z, matrix = tiled(w, x, delta, b, method)
                rows.append({
                    "case": name, "tile_size": b, "method": method,
                    "forward_error": error(y, y_ref),
                    "backward_error": error(z, z_ref),
                    "matrix_error": error(matrix, w),
                    "adjoint_identity_error": float(abs(np.vdot(y, delta)-np.vdot(x,z)) /
                        max(1.0, abs(np.vdot(y,delta)), abs(np.vdot(x,z)))),
                })
    # Explicit component-level checks are separate from factor-level scaling.
    explicit = []
    for b in (4, 8):
        for name, w in {
            "signed": rng.normal(size=(b,b)),
            "identity": np.eye(b),
            "zero": np.zeros((b,b)),
            "rank_one": np.outer(rng.normal(size=b), rng.normal(size=b)),
        }.items():
            layer = svd_layer(w)
            actual = layer_matrix(layer)
            q, r = np.linalg.qr(w)
            qr = mesh_matrix(*clements_decompose(q)) @ r
            explicit.append({"size": b, "case": name,
                             "svd_error": error(actual, w),
                             "qr_error": error(qr, w),
                             "svd_mzi_count": sum(len(layer[key][0]) for key in ("in_mesh","out_mesh"))})
    keys = ("forward_error", "backward_error", "matrix_error", "adjoint_identity_error")
    checks = {
        "factor_equivalence": all(np.isfinite(r[k]) and r[k] < TOL for r in rows for k in keys),
        "explicit_mesh_equivalence": all(np.isfinite(r[k]) and r[k] < TOL for r in explicit for k in ("svd_error","qr_error")),
        "explicit_mesh_counts": all(r["svd_mzi_count"] == r["size"]*(r["size"]-1) for r in explicit),
        "all_cases_present": len(rows) == len(cases)*len(SIZES)*2,
        "resource_counts": all(counts(N,b,"svd")["mzi_components"] == 2*counts(N,b,"qr")["mzi_components"] for b in SIZES),
    }
    report = {
        "experiment": "OPA-MOD-001", "seed": SEED, "n": N,
        "numpy_version": np.__version__, "python_version": sys.version.split()[0],
        "tolerance": TOL, "vectors_per_case": x.shape[1],
        "error_definition": "Relative Frobenius norm, absolute norm for zero reference; adjoint identity normalized by max(1, magnitudes)",
        "checks": checks, "failures": [k for k,v in checks.items() if not v],
        "factor_level_results": rows, "explicit_mesh_results": explicit,
        "resources": [{"tile_size": b, "method": m, **counts(N,b,m)} for b in SIZES for m in ("svd","qr")],
        "limitations": [
            "Ideal real-valued reference weights; coherent signed-field encoding and readout assumed.",
            "128-dimensional comparisons use dense algebraic unitary factors, not explicit MZI decomposition. Explicit component reconstruction is tested only at sizes 4 and 8.",
            "SVD attenuation amplitudes are normalized by each tile's largest singular value; electronic scaling precedes accumulation. QR uses electronic triangular preprocessing (postprocessing for adjoint).",
            "Counts are structural per-vector arithmetic and scalar payloads, not measured throughput, physical interface count or energy. No fan-out loss, conversion noise or communication timing modeled.",
            "Backward calculation is the mathematical adjoint with electronic operations included, not a demonstration of hardware training.",
            "No physical superiority claim; loss and component errors are deferred to later experiments."
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    result = json.dumps(report, indent=2, allow_nan=False) + "\n"
    (OUT / "result.json").write_text(result, encoding="utf-8")
    print(result)
    if report["failures"]:
        raise SystemExit("OPA-MOD-001 failed: " + ", ".join(report["failures"]))


if __name__ == "__main__":
    main()
