# OPA-G-004C2 — Archived hybrid BVH analysis

## Evidence and scope

Original [CI run 45865605446](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/45865605446), attempt 1, job 140067595332, artifact 15140012141, archived in PR #295 without rerunning the experiment. [Provenance](../ci-originals/opa-g-004c2/45865605446-15140012141/archive-provenance.json), [summary](../ci-originals/opa-g-004c2/45865605446-15140012141/result.json), [ray results](../ci-originals/opa-g-004c2/45865605446-15140012141/results.csv), [node results](../ci-originals/opa-g-004c2/45865605446-15140012141/node-results.csv), [workload](../ci-originals/opa-g-004c2/45865605446-15140012141/workload.json), [labels](../ci-originals/opa-g-004c2/45865605446-15140012141/labels.json), [calibration](../ci-originals/opa-g-004c2/45865605446-15140012141/calibration.json), [audit](../ci-originals/opa-g-004c2/45865605446-15140012141/audit.csv).

Archive manifest records source head 8025d4e2f63218a04497280cd2204176292318c2, executed commit 4324e6280ac828eef6d7134377c90e36486a2704, executed tree 5db91591d09834fa6bc4d38a04f342ea4ede3055, ZIP 5587563 bytes, SHA-256 8b0033363602a3fa6ce47c6ff5bf8c87244f6352aaba2c3795029738ed00c82a, expanded 59987288 bytes. C2-only bounded expansion exception used after PR #294; earlier attempts failed on multiple artifacts and expansion limits, not scientific correctness. All nine original files retained. Large data read by exact Git blob IDs rather than the Contents API: results.csv 11150626 bytes (936fd67eab4b0d5f29dcf5c87a393cc0b61ed6a5), node-results.csv 47642003 bytes (80f6f5a9412cdbd495d28d3e65022f5682627241), workload.json 1060469 bytes (737b63c1bbd8fc0a94c5b84aa5d8d3242c117337). Retrieved text lengths agree with manifest byte lengths. The 49800 ray rows have unique scenario/repeat/scene/ray/policy keys; recomputed counts for rays, final FP/FN, wrong ID, distance failures, node FP/FN, visits, triangles, guards, optical, fallback, sides, driven operands and extra/missing visits agree with all 20 summary rows. Recounted all 664870 node rows by scenario/policy, decision vs exact label and fallback; these counts also agree. Audit CSV is header-only. This is a count audit of original evidence, not independent geometry/oracle recomputation, cryptographic rehash of all nine files, or a new simulation. Environment files are covered by archive provenance, not independently analyzed here.

## Workload and quality

6/6 implementation checks and scientific_gate=true. Three fresh 48-triangle scenes (80 rays each), six-triangle translated boundary fixture (10 rays). 249 eligible rays: 145 hits, 104 misses; one coplanar exclusion in translated boundary. Counts by scene: distributed 41/39, clustered 57/23, anisotropic 41/39, boundary 6/3. Calibration seed 20261403, six geometry panels retained 9856 pairs (2048 uniform, 2048 translated, 1664 boundary, 2048 scene_like, 1024 near_parallel, 1024 dynamic_range); manifest reports 60462 unique historical pairs considered. Exact represented pair disjointness reported by experiment, not statistical independence; translated boundary is correlated with C1. Ten repeats in five scenarios give 12450 selected-policy ray evaluations, not 12450 distinct rays. Same applies to 174850 selected-policy node decisions.

Electronic only, all-optical fallback and max_min_125 pass node and final gates; raw fails both. Hybrid exactly matches counts of visits (34970), accepted nodes (22880), leaves (6640), triangle tests (19920) per scenario of ten repeats, with no extra/missing visits or triangles reported. Zero observed final FP/FN, wrong IDs, distance tolerance failures and node FP/FN for hybrid; finite synthetic workload only.

| Scenario | Guards | Optical-stage nodes | Fallback | Optical decisions without fallback | Fallback / optical | Optical decisions / all nodes |
|---|---:|---:|---:|---:|---:|---:|
| scale_only | 3680 | 31290 | 8520 | 22770 | 27.23% | 65.11% |
| large_scale | 3680 | 31290 | 16217 | 15073 | 51.83% | 43.10% |
| noise_only | 3680 | 31290 | 11554 | 19736 | 36.93% | 56.44% |
| combined | 3680 | 31290 | 23181 | 8109 | 74.08% | 23.19% |
| drift_quantization | 3680 | 31290 | 23090 | 8200 | 73.79% | 23.45% |
| Total | 18400 | 156450 | 82562 | 73888 | 52.77% | 42.26% |

All optical-stage nodes incur optical work, including fallback: 181820 side tests and 727280 driven operands per scenario; total 909100 sides and 3636400 operands. Total triangle tests 99600. Worst scene/repeat fallback 935/952 (98.21%), large_scale anisotropic repeats 0 and 1, from 200 selected-policy scenario/repeat/scene groups. This worst group is not the pooled worst scenario.

| Raw scenario | Node FP | Node FN | Final FN | Wrong final ID | Nearest primitive not tested |
|---|---:|---:|---:|---:|---:|
| scale_only | 636 | 530 | 246 | 0 | 246 |
| large_scale | 819 | 586 | 205 | 0 | 205 |
| noise_only | 59 | 948 | 421 | 0 | 421 |
| combined | 2083 | 1070 | 433 | 5 | 438 |
| drift_quantization | 1168 | 1780 | 536 | 6 | 542 |

Raw final FP zero; distance failures 5 and 6 in combined and drift respectively, overlapping wrong-ID cases. Raw visits differ because wrong decisions alter traversal; no speed ranking of raw. Raw classifications on the hybrid's actual visited nodes are a separate diagnostic: 3791 FP and 26850 FN summed across scenarios, not the raw traversal error count. Calibration thresholds (dimensionless, ten repeats) range scale 0.0042706–0.0043053, large 0.0690435–0.0699301, noise 0.0209166–0.0263095, combined 0.1146021–0.3185076, drift 0.0953936–0.3205975. No retuning.

## Conditional implications for C3

For one scenario let N=34970 visited nodes, F=fallback, S=181820 sides, T=19920 triangles. With equal shared traversal and triangle costs, electronic box energy N*e_box versus hybrid F*e_box + N*e_guard + S*e_side + E_other. Here e_guard means incremental electronic preprocessing per visited node (including nodes sent to optics); e_side must include four operand drives/conversions, optical readout and dynamic source allocation without double counting. E_other includes incremental memory, static source/LO, tuning, aggregation, scheduling, transfer and calibration as applicable. Shared costs cancel only when demonstrably matched. Break-even requires S*e_side + E_other < (N-F)*e_box - N*e_guard. This is not a measured energy advantage.

At illustrative e_box=100 pJ, e_guard=1 pJ and zero other overhead, maximum side budget in pJ is scale 14.355, large 10.122, noise 12.686, combined 6.292, drift 6.342. These are optimistic ceilings, not device targets verified by measurements; any positive omitted overhead reduces them. Raw excluded from matched ranking. All-optical fallback is a correctness/overhead control.

Next: [C3 protocol](../../research/OPA-G-004C3.md), independent archival count verification in CI and a compiled whole-BVH CPU benchmark before conditional system accounting. No measured optical timing, GPU or physical energy. No fabrication readiness claim.
