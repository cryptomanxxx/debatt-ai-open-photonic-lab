# OPA-G-004B2 — Prospective robustness validation: archived analysis

[Original report](../ci-originals/opa-g-004b2/45858488663-15136519355/result.json), [selection](../ci-originals/opa-g-004b2/45858488663-15136519355/selection.json), [results CSV](../ci-originals/opa-g-004b2/45858488663-15136519355/results.csv), [workload manifest](../ci-originals/opa-g-004b2/45858488663-15136519355/workload-manifest.json), [provenance](../ci-originals/opa-g-004b2/45858488663-15136519355/archive-provenance.json). Original run 45858488663, artifact 15136519355, archive PR #287. All 4200 CSV rows read; blob SHA 4dcc2754d8de45d7cfbc16b51afa7ad720d074d1 matches archive metadata. Result, selection and manifest blob SHAs also match. Workload CSV (3767085 bytes) content was not returned by connector; its blob metadata matches, but independent rechecking of individual geometry and disjointness was not performed. The executed experiment reports successful disjointness and roundtrip checks; manifest records 9856 distinct represented pairs per split, 29568 total. Near-parallel and dynamic-range panels are correlated transformations; scene-like pairs share rays/boxes. Distinct tuples do not imply independent statistical samples.

## Outcome

Five numerical checks passed and scientific_gate=true. The development-selected candidate max_min_125 (1.25 × calibration maximum minimum-side residual) had zero FP/FN and matched compiled CPU on all five scenarios, six panels, ten repeats in heldout. This is 300 panel/repeat/scenario rows, 492800 classifications of 9856 represented pairs repeated under five modeled scenarios and ten draws; not 492800 independent geometries. Selection was recorded before heldout optical evaluation. No post-hoc switching. Development worst-scenario fallback 70.1051%; heldout 71.0972%. CPU reference zero observed errors throughout calibration/development/heldout. Each heldout scenario contains 98560 classifications, 61100 electronic guards, 37460 optical-stage tests and 189920 side evaluations.

| Heldout scenario | FP | FN | Fallback / optical | Optical decisions without fallback | Optical decisions / all pairs |
|---|---:|---:|---:|---:|---:|
| scale_only | 0 | 0 | 16084/37460 | 21376 | 21.69% |
| large_scale | 0 | 0 | 21339/37460 | 16121 | 16.36% |
| noise_only | 0 | 0 | 19153/37460 | 18307 | 18.57% |
| combined | 0 | 0 | 26633/37460 | 10827 | 10.99% |
| drift_quantization | 0 | 0 | 25842/37460 | 11618 | 11.79% |

Combined fallback by panel: uniform 3171/5890, translated 1316/3700, boundary 16640/16640, scene-like 2583/6130, near-parallel 894/2550, dynamic-range 2029/2550. Worst individual panel/repeat fallback = 100%. Even the successful policy offers no optical decision on the combined boundary panel. Raw combined errors sum to 7343 FP and 2143 FN; fallback removes all observed errors. In drift/quantization the ideal quantized operand boundary decision alone yields 3910 FP and 1220 FN over repeats relative to original labels; not physical DAC ENOB. The unquantized ideal floating side evaluation also misses one near-parallel hit per repeat in the fixed scenarios; do not identify floating arithmetic with the exact oracle.

## Candidate comparison

| Policy | Development eligible | Heldout diagnostic eligible | Heldout worst scenario fallback |
|---|---|---|---:|
| max_min | no | no | 67.67% |
| max_min_125 | yes (selected) | yes | 71.10% |
| max_min_150 | yes | yes | 74.14% |
| max_min_200 | yes | yes | 79.58% |
| side_max | yes | no | 89.13% |

All nonzero final errors in original CSV: max_min development drift_quantization repeat 0 near_parallel one FN; heldout noise_only repeat 1 boundary one FP and repeat 7 dynamic_range one FN; side_max heldout noise_only repeat 1 boundary one FP. Larger max-min policies are diagnostics, not independently selected confirmations. All-fallback and electronic-only controls have zero errors but do not establish optical utility.

## Decision and limitations

The preregistered finite-sample pairwise simulation gate passed. Advance to [G-004C BVH protocol](../../research/OPA-G-004C.md), not physical fabrication or a performance claim. Preserve max_min_125 without retuning on BVH evaluation. The optical model is normalized, with scenario/repeat-specific calibration, no hardware drift characterization, no measured timing or energy. A single missed bounding node can discard the nearest triangle; scene-level correctness must be measured independently. The 100% boundary fallback and small total optical-only fraction are important constraints. No GPU measurements or system-level energy ranking.
