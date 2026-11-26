# OPA-G-004B — archived analysis

Source [original report](../ci-originals/opa-g-004b/45849783504-15132527500/result.json), [results](../ci-originals/opa-g-004b/45849783504-15132527500/results.csv), [provenance](../ci-originals/opa-g-004b/45849783504-15132527500/archive-provenance.json). Run 45849783504, artifact 15132527500, archive PR #284. Original results CSV blob f12ce439f146bdf23ad2beb3ac1861b72a91c9af matches manifest, all 768 rows read. 18/18 numerical checks; 27648 cost rows reported. Three repeats of the same 7808 heldout geometries, not 23424 independent geometries. Per scenario 23424 classifications, 13566 electronic guards, 9858 optical pairs, 49116 sides. Counts below sum the three repeats without treating them as independent geometries.

| Scenario | Policy | FP | FN | Fallback / optical | Quality gate |
|---|---|---:|---:|---:|---|
| scale_only | raw | 471 | 1105 | 0/9858 | False |
| scale_only | uniform_q99_any | 0 | 0 | 4319/9858 | True |
| scale_only | uniform_q99_min | 0 | 0 | 4163/9858 | True |
| scale_only | geometry_q99_any | 0 | 0 | 4338/9858 | True |
| scale_only | geometry_q99_min | 0 | 0 | 4179/9858 | True |
| scale_only | geometry_max_min | 0 | 0 | 4217/9858 | True |
| scale_only | all_optical_fallback | 0 | 0 | 9858/9858 | True |
| scale_only | electronic_only | 0 | 0 | 0/0 | True |
| large_scale | raw | 813 | 1110 | 0/9858 | False |
| large_scale | uniform_q99_any | 0 | 0 | 6525/9858 | True |
| large_scale | uniform_q99_min | 0 | 0 | 5264/9858 | True |
| large_scale | geometry_q99_any | 0 | 0 | 6675/9858 | True |
| large_scale | geometry_q99_min | 0 | 0 | 5310/9858 | True |
| large_scale | geometry_max_min | 0 | 0 | 5490/9858 | True |
| large_scale | all_optical_fallback | 0 | 0 | 9858/9858 | True |
| large_scale | electronic_only | 0 | 0 | 0/0 | True |
| noise_only | raw | 947 | 1118 | 0/9858 | False |
| noise_only | uniform_q99_any | 5 | 7 | 5277/9858 | False |
| noise_only | uniform_q99_min | 5 | 7 | 4701/9858 | False |
| noise_only | geometry_q99_any | 4 | 7 | 5274/9858 | False |
| noise_only | geometry_q99_min | 4 | 7 | 4699/9858 | False |
| noise_only | geometry_max_min | 0 | 1 | 4914/9858 | False |
| noise_only | all_optical_fallback | 0 | 0 | 9858/9858 | True |
| noise_only | electronic_only | 0 | 0 | 0/0 | True |
| combined | raw | 1668 | 1115 | 0/9858 | False |
| combined | uniform_q99_any | 3 | 0 | 8831/9858 | False |
| combined | uniform_q99_min | 3 | 0 | 6618/9858 | False |
| combined | geometry_q99_any | 1 | 1 | 8429/9858 | False |
| combined | geometry_q99_min | 1 | 3 | 6395/9858 | False |
| combined | geometry_max_min | 0 | 0 | 6605/9858 | True |
| combined | all_optical_fallback | 0 | 0 | 9858/9858 | True |
| combined | electronic_only | 0 | 0 | 0/0 | True |

## Boundary bottleneck

Combined geometry_max_min: 6605/9858 optical fallback (67.0%), 3253 optical decisions without fallback (13.9% of all inputs); zero observed FP/FN. By panel fallback/optical: uniform 721/1665, translated 330/1161, boundary 4988/4992, scene_like 566/2040. Noise-only geometry_max_min fails on boundary repeat 1: one FN among 896 hits, 1571/1664 fallback, threshold 0.016624428627034393. All other nontrivial noise policies also fail. No common nontrivial qualified policy across all four scenarios. Do not select a scenario-specific policy on unknown hardware or tune on these heldout outcomes. All-optical fallback is a correctness control, not acceleration.

## Conditional partial energy analysis

Cost CSV blob e990ae2c79c1c0aa72872f2862a44387d3ffcecb agrees with provenance metadata, but connector returned no file content for the 3.89 MB file. The following is a separate arithmetic reconstruction from the original accuracy rows and the documented G-004B formula and assumption grid, NOT an independent audit of cost CSV values. For combined geometry_max_min, 12 heldout panel/repeat rows × 72 assumptions: 198 positive, 666 negative, 0 zero remaining overhead budgets; extrema -4409.994 to 960.692 pJ/input. This is a grid count, not probability or system ranking. Equal-quality conditional CPU reference is N*CPU; remaining budget = (N-F)*CPU - N*guard - S*(side + 1e12*static/(1e9*utilization)). For pooled combined counts N=23424, F=6605, S=49116, assuming CPU=100 pJ, guard=1 pJ, side=10 pJ, static=.01 W and full utilization, remaining budget is 676156 pJ in aggregate (28.87 pJ/input). At 10% utilization it becomes negative. This is an illustrative reconstruction, not measured energy; missing costs include memory/DMA, actual conversion, aggregation, calibration, tuning, host, cooling. GPU unmeasured.

## Decision

Do not claim a robust matched optical accelerator or proceed to physical integration. Before a qualified BVH comparison, use a new frozen workload and independent noise draws to evaluate a preregistered conservative policy; include an electronic-only baseline and all-fallback control. The previous heldout set is now historical diagnostic evidence, not fresh validation. See [follow-up protocol](../../research/OPA-G-004B2.md). Negative results remain publishable. No physical energy, latency or rendering benefit established.
