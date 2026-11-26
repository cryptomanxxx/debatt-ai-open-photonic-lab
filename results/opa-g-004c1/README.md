# OPA-G-004C1 — Electronic BVH: archived analysis

[Original report](../ci-originals/opa-g-004c1/45862577503-15137988857/result.json), [per-ray results](../ci-originals/opa-g-004c1/45862577503-15137988857/results.csv), [discrepancies](../ci-originals/opa-g-004c1/45862577503-15137988857/discrepancies.csv), [frozen scenes](../ci-originals/opa-g-004c1/45862577503-15137988857/scenes.json), [provenance](../ci-originals/opa-g-004c1/45862577503-15137988857/archive-provenance.json). Original run 45862577503, artifact 15137988857, archive PR #290. All four scientific data files were retrieved; Git blob IDs and byte lengths agree with archive metadata (results.csv 71630 bytes, 250 rows; scenes.json 118488 bytes). The discrepancy CSV contains only its header. The scene SHA-256 recorded by the experiment agrees with the archive manifest. This is inspection of original evidence, not an independent rerun or local cryptographic verification.

## Scientific gate

10/10 numerical checks passed; scientific_gate=true. Three 48-triangle scenes and a six-triangle boundary scene contain 150 triangles, 96 BVH nodes and 250 rays in total. 249 rays were eligible, 140 hits and 109 misses. Boundary ray 6 is excluded because of coplanarity with primitive IDs 0, 1, 5; no classification credit for this ray. All eligible nearest-hit IDs and full ordered lists of visited nodes, accepted nodes and tested triangles agree between exact and compiled-kernel traversals. All recorded hit distance errors are zero at the report's FP64 comparison precision; exact rational t values are not necessarily exactly representable in FP64. No triangle or box audit discrepancies reported. The whole traversal is Python calling C kernels, not a fully compiled BVH timing reference.

| Scene | Eligible rays | Hits | Misses | Brute force triangle tests | BVH triangle tests | BVH box tests | Accepted boxes | Triangle test reduction |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| distributed | 80 | 40 | 40 | 3840 | 375 | 924 | 547 | 90.23% |
| clustered | 80 | 53 | 27 | 3840 | 897 | 1416 | 967 | 76.64% |
| anisotropic | 80 | 41 | 39 | 3840 | 564 | 962 | 629 | 85.31% |
| boundary_controls | 9 | 6 | 3 | 54 | 33 | 21 | 17 | 38.89% |
| Total | 249 | 140 | 109 | 11574 | 1869 | 3323 | 2160 | 83.85% |

The BVH eliminates 9705 triangle tests relative to brute force (6.19× fewer triangle tests), at the cost of 3323 box tests; 1163 visited boxes reject. Counts exclude the counterfactual all-node/all-triangle reference audit. The clustered scene visits more nodes and tests more triangles, illustrating sensitivity to overlap. No nearest-distance pruning. Counts are not timings, energy measurements, or evidence that a photonic implementation is faster. A ray parameter t is not Euclidean distance for unnormalized directions.

## Next step

C1 passes the finite synthetic correctness gate. Proceed to [C2 frozen hybrid protocol](../../research/OPA-G-004C.md). Use fresh evaluation scenes and independent calibration, not C1 as prospective validation data. Keep max_min_125 fixed, reuse the exact oracle and compiled kernels, independently check electronic guards and fallback on all possible nodes, and distinguish node errors from final nearest-hit errors. Do not equate correctness of this electronic baseline with correctness of the optical model. No GPU or optical measurement, no change to fabrication priorities.
