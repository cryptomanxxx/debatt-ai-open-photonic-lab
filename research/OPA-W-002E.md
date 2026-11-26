# OPA-W-002E — Adaptive photonic memory calibration

Status: implementation pending CI and review. [W-002D original audit](../results/ci-originals/opa-w-002d/45904372717-15157980225/result.json) verified 32,400 paired comparisons. It found reference-dependent improvements and regressions, but modeled no chronological drift. This new experiment is a conditional sensitivity study, not a GSSe material fit or retention prediction.

## Frozen design

Use the W-002A 16-state codebook on [0.2,0.8], natural binary labels, independently generated zero-drift calibration data (256 writes/readings per state), frozen midpoint thresholds, and 32 held-out programmed cells per state retained for 64 chronological steps. At each step read each cell once. Add independent receiver noise, clip and quantize with the existing ADC model. Data common drift, independent reference mismatch and reference-only correlated mismatch follow separate Gaussian AR(1) processes starting at zero, with coefficient 0.95 and innovation sigma equal to the selected stationary sigma times sqrt(1-0.95^2). These are assumed dimensionless time steps, not seconds. Persistent programming errors are independent between cells. Reference programming error is shared between calibration and later reads. Reference-only common mismatch can fool any gate relying on reference agreement.

Sweep programming and read sigma independently over 0,0.005,0.01; common drift and independent reference mismatch sigma independently over 0,0.005,0.02; reference-only correlated mismatch sigma over 0,0.01; ADC 8 and 12 bits. This is 324 scenarios per seed. Development seeds 21001–21004 and held-out seeds 22001–22016 are disjoint and distinct from W-002A/C. Standardized draws are reused across parameter settings and methods; no independence across scenarios or repeated reads is implied.

## Policies

- Fixed: original frozen thresholds, no correction or reference acquisition.
- Always: acquire 4 or 16 references every 1, 4 or 16 steps, eight readings per reference, subtract mean reference change relative to its separate zero-drift calibration. If any acquired reference clips, disable correction until next acquisition. Hold the most recent correction between acquisitions.
- Adaptive: same acquisition schedule and clip rule, but enable correction only if abs(mean reference change) exceeds gate times max(0.002, sample standard deviation of per-reference changes / sqrt(n)). This heuristic uncertainty is not a calibrated confidence interval, especially under correlated mismatch. The gate uses no data labels, future measurements, true drift or scenario parameters at runtime.

For each reference count/cadence pair select gate from 1,2,3 solely by minimizing total development symbol errors, breaking ties in favor of the larger gate. Freeze before evaluating held-out trajectories. Retain all six hardware options and both correction policies, not just the winner. Test labels are used only for scoring. No tuning on test outcomes; any later tuning requires fresh held-out seeds.

## Outputs and acceptance

1,296 development trajectories and 5,184 held-out trajectories, with 62,208 paired policy rows (12 per held-out trajectory). Each trajectory has 32,768 data readings, 2,048 per state. Export development candidate losses, selected gates, held-out errors, worst-state SER, BER, rescued/regressed point decisions, enabled steps, actual/residual mean absolute drift and acquisition counts. Point criterion remains observed worst-state SER <= 0.001 across the entire trajectory. No positive gain is required for execution success. Unit tests cover ideal, seed separation, no future-data dependence, reference disagreement and clipping.

Acquisition cost is 8*n*ceil(64/cadence) reference reads plus 8*n initial calibration reads. Adaptive gating does not reduce scheduled acquisition counts; it only changes whether correction is applied. Dynamic read energy, physical acquisition time, retention and area remain unknown. No statistical qualification, hardware efficiency or W-003 release follows from a point pass.

## Reproduction

[Source](../simulations/memory/adaptive_calibration_v005.py) and [tests](../simulations/memory/test_adaptive_calibration.py) run in the locked CI environment. Preserve development.csv, heldout.csv, summary.csv, result.json and environment records via original archive. Next audit paired results and compare adaptive against always at the same acquisition cost; assess correlated mismatch separately. Physical state distributions, retention, read disturb, energy and addressing constraints remain open. The [OPA-M contract](OPA-W-001.md) remains unchanged.
