# OPA-W-002D — Archived drift compensation trade-offs

Status: archived W-002C summary inspected; independent row-level audit implementation pending CI. No source rerun or new estimator. See [W-002C protocol](OPA-W-002C.md).

## Observed source results

[Original report](../results/ci-originals/opa-w-002c/45903062662-15156368734/result.json), [summary](../results/ci-originals/opa-w-002c/45903062662-15156368734/summary.csv) and [provenance](../results/ci-originals/opa-w-002c/45903062662-15156368734/archive-provenance.json). Source run 45903062662, artifact 15156368734, SHA-256 f20271f78a3d7e85b6d56d771c4f333eccd390f4f744f8ea7ab349509dce199b. Six original files, 9,098,195 bytes, merged in PR 318. Git blob identities match the manifest.

The matched baseline passes 554/3600 panels (15.39%). Source results below use the same panels, observed worst-state SER <= 0.001. Reference mismatch is a hypothetical additive sigma in full-scale units.

| References | Mismatch sigma | Corrected passes | Rescued | Regressed | Net gain |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 | 687 | 210 | 77 | 133 |
| 1 | 0.005 | 571 | 159 | 142 | 17 |
| 1 | 0.02 | 221 | 49 | 382 | -333 |
| 4 | 0 | 803 | 272 | 23 | 249 |
| 4 | 0.005 | 689 | 214 | 79 | 135 |
| 4 | 0.02 | 419 | 97 | 232 | -135 |
| 16 | 0 | 831 | 294 | 17 | 277 |
| 16 | 0.005 | 773 | 259 | 40 | 219 |
| 16 | 0.02 | 589 | 167 | 132 | 35 |

At zero mismatch four references achieve 249/277 (89.9%) of the sixteen-reference net gain with one quarter of the incremental reads per acquisition. Sixteen references increase passing panels by 50% relative to the baseline, but only 23.08% of all panels pass. At high mismatch one and four references degrade the point screen; sixteen give a small positive net gain but regress 132 baseline passes. No universal reference count can be recommended from these results. The scenario grid is not a physical distribution, and reference count is not an empirically validated policy.

## Independent read-only audit

[Audit source](../simulations/memory/audit_drift_v004.py) verifies identity, all six original file sizes and hashes, factorial coverage of 3,600 baseline and 32,400 paired records, matched baseline values, count-based SER/BER arithmetic, worst-state SER bounds and grid, classification, drift and acquisition bookkeeping, and agreement with both source summaries. The source does not retain per-state confusion matrices or raw draws; worst-state values and the actual estimator cannot be independently reconstructed. The audit checks consistency, not a second simulation.

Aggregate matched outcomes by reference count and mismatch; stratify by each of programming sigma, read sigma, drift sigma and ADC precision; export 2,025 parameter combinations with 16 seeds each. Compute mean absolute residual and mean SER difference with equal panel weighting. Retain all regressions. For each fixed mismatch, compare the no-correction baseline and the three reference counts by nondominance in pass count (maximize), regressions (minimize) and extra reads (minimize) at the original cadence. This is a descriptive frontier on existing data, not held-out policy selection.

## Conditional cadence cost

For D=65,536 data reads, reference count n and block size B, extra reference reads R=8*n*ceil(D/B). Sweep B=256,1024,4096,65536 and n=0,1,4,16; assume reference-to-data dynamic read energy ratios q=0.5,1,2,10. Dynamic read energy ratio is 1+q*R/D, excluding separate calibration, writes, control, optical power overhead and idle energy. For example, 16 references every 256 data reads require 32,768 extra reads (50% overhead); the original cadence requires only 128 (0.195%). This does not predict accuracy under more frequent acquisition, because the source has one constant drift per panel. No hardware throughput or joules inferred.

Outputs: summary.csv, strata.csv, combinations.csv, frontier.csv, cost.csv and result.json plus CI environment records; registered for original archive. Execution pending CI.

## Next gate

Design a separate chronological drift model with common drift, independent and correlated reference mismatch, frozen calibration, reference acquisition cadence and independent held-out trajectories. Compare fixed, reference-assisted and causally gated correction; account for reference acquisition, never use actual drift or true labels to choose at runtime. Preregister a policy using independent development data and evaluate negative outcomes on untouched seeds. This is still a hypothetical model; empirical GSSe state distributions, retention, read disturb, energy, addressing and process access remain missing. No physical qualification or W-003 release. Preserve the [OPA-M comparison contract](OPA-W-001.md).
