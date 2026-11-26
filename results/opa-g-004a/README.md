# OPA-G-004A — Archived electronic baseline analysis

Derived from [original results.csv](../ci-originals/opa-g-004a/45841325612-15128251841/results.csv), [manifest](../ci-originals/opa-g-004a/45841325612-15128251841/workload-manifest.json) and [provenance](../ci-originals/opa-g-004a/45841325612-15128251841/archive-provenance.json). Original run 45841325612; archive PR #281. 99/99 checks passed, 23,424 unique pairs, 12 panels, 1,008 timed repetitions. CSV blob c5a684109f2a848ec531bd7416b41bb1ea031620 matches provenance. No rerun or modification of original outputs.

Both FP64 methods have zero observed FP/FN across all 23,424 pairs. NumPy FP32 has boundary FP counts 241/236/242 on calibration/development/heldout respectively (709 total); no FN. On heldout boundary 242/768 misses are incorrectly accepted, 225 input-rounding FP and 17 arithmetic FP on rounded inputs. These counts are separate comparisons, not generally additive. No other FP32 errors observed. Full heldout boundary contains 896 hits and 768 misses; smaller prefixes are ordered by construction and are not representative subsamples.

| Heldout panel | Batch | NumPy FP64 tests/s | Compiled FP64 tests/s | Compiled p50 / p95 (us) |
|---|---:|---:|---:|---:|
| uniform | 2048 | 7,720,174 | 152,517,128 | 13.428 / 18.840 |
| translated | 2048 | 7,893,560 | 167,115,463 | 12.255 / 14.728 |
| boundary | 1664 | 7,137,740 | 118,891,112 | 13.996 / 17.070 |
| scene_like | 2048 | 7,896,330 | 174,179,282 | 11.758 / 12.143 |

Full-panel batch/p50 throughput; not steady-state GPU or renderer throughput. Intel Xeon 6975P-C shared CI runner, single calling thread, resident inputs, includes dispatch and output allocation, no DMA, no CPU power instrumentation. Compiled FP64 is the stronger tested matched-quality CPU baseline. Zero observed errors on these represented inputs does not establish universal correctness. GPU and energy unmeasured. Use exact archived workload in [G-004B](../../research/OPA-G-004B.md), not regenerated examples; do not infer CPU energy from runtime alone.
