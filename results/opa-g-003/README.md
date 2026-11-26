# OPA-G-003 — CI result analysis

[Original CI run](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/45810482156) · [artifact](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/45810482156/artifacts/15111277146) · [provenance](provenance.json).

10/10 checks passed, 17 scenarios, three repeats, 15663 rays per repeat, 1224 CSV rows. Each scenario has 46989 ray classifications, of which 37881 bypass optical computation by electronic guards; 9108 reach the optical stage, with 47700 side tests. Counts below sum the three repeats and four workloads, selecting the zero threshold or the per-repeat calibration_q99 threshold; repeated thresholds are not independent trials. The near_face workload has zero optical side tests: all 12288 classifications across repeats are handled by guards. It does not validate near-zero optical margins.

| Scenario | Raw FP | Raw FN | q99 hybrid FP | q99 hybrid FN | q99 fallback rays |
|---|---:|---:|---:|---:|---:|
| scale_0.05 | 0 | 1008 | 0 | 0 | 1314 |
| scale_0.15 | 0 | 1008 | 0 | 0 | 1398 |
| scale_0.3 | 0 | 1008 | 0 | 0 | 1722 |
| scale_0.6 | 21 | 1014 | 0 | 0 | 2877 |
| bias_0.002 | 47 | 351 | 0 | 0 | 2273 |
| bias_0.01 | 169 | 35 | 1 | 0 | 4568 |
| bias_0.03 | 545 | 211 | 0 | 0 | 6596 |
| phase_0.05 | 0 | 0 | 0 | 0 | 1413 |
| phase_0.15 | 18 | 0 | 0 | 0 | 1683 |
| phase_0.3 | 78 | 0 | 0 | 0 | 2607 |
| loss_0.25 | 60 | 0 | 0 | 0 | 2157 |
| loss_1.0 | 174 | 0 | 3 | 0 | 3999 |
| loss_3.0 | 474 | 0 | 3 | 0 | 6165 |
| noise_0.001 | 2 | 571 | 0 | 2 | 1440 |
| noise_0.005 | 15 | 565 | 0 | 8 | 1905 |
| noise_0.02 | 58 | 617 | 0 | 1 | 3397 |
| combined | 156 | 803 | 4 | 0 | 5477 |

Combined scenario: q99 mean 0.148693; separate uniform-operand validation mean coverage 0.990641. Fallback 5477/46989 (11.66% of all rays) or 5477/9108 (60.13% of optical-stage rays); 959 to 4 errors (99.58% reduction). Residual false negatives in noise-only scenarios show q99 is not a guaranteed safety bound.

| Combined threshold | Hybrid FP | Hybrid FN | Fallback |
|---|---:|---:|---:|
| 0 | 156 | 803 | 0 |
| 0.005 | 145 | 772 | 279 |
| 0.02 | 107 | 670 | 1154 |
| 0.05 | 43 | 317 | 2668 |
| 0.1 | 8 | 0 | 4623 |
| per-repeat q99 | 4 | 0 | 5477 |

No hardware, energy, timing or GPU superiority claim. Calibration and numerical roundoff at exact zero must be isolated before interpreting scale-only misses as physical nonlinearity. Next recommended G-003 refinement: targeted nonzero optical margins on both sides of zero, exact tangency, separate electronic guard precision, compare ideal floating and exact truth, diagnose calibration offset/roundoff and evaluate an implementable conservative confidence receiver with held-out geometric workloads. Report optical-stage denominators separately; include guard and fallback costs later. Do not start a matched GPU performance claim before closing these gaps.

Archive complete for scientific result files: [original JSON](result.json) and [original CSV](results.csv) match the recorded original Git blob IDs. CSV was uploaded in PR #269 and rechecked in main after merge (202499 bytes, 1224 data rows). Environment files remain in the CI artifact with recorded checksums; they are not permanently archived here. The table above is a derived summary, not original CSV.
