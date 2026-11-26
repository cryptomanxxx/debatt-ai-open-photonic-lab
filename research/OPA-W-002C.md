# OPA-W-002C — Reference-assisted photonic memory drift compensation

Status: implementation pending CI and review. The [W-002B archived audit](../results/ci-originals/opa-w-002b/45901981581-15156087522/result.json) verified six original files, 3,600 panels and 468,000 confusion rows. Four-bit storage passed the point screen in 275/1,800 panels; binary passed all 1,800. These are historical sensitivity results, not physical reliability. See [W-002B](OPA-W-002B.md).

## Frozen paired protocol

Use the W-002A 16-state intensity codebook, independent calibration and test writes, 512 writes/state, eight reads/write, same programming/read sigma grid, common drift sigma and ADC grid. Use 16 new seeds (11001–11016), not the historical eight. Each of 3,600 four-bit test panels has one uncorrected baseline and nine paired compensation settings: 1, 4 or 16 reference cells, crossed with independent reference mismatch sigma 0, 0.005 or 0.02 in normalized full-scale units. The resulting 32,400 paired comparisons reuse exactly the same data readings and frozen calibration thresholds within each panel. Do not compare the new baseline directly to the historical 15.3% as if the seeds were matched.

Reference cells have nominal transmission 0.5 and independent persistent programming variation. Measure each reference eight times during zero-drift calibration and eight times at validation. Each reference experiences the data common drift plus its own hypothetical Gaussian offset with the selected mismatch sigma. Estimate common drift from the mean difference between reference ADC readings at validation and calibration. Subtract this estimate from quantized data readings before decoding. The estimator never sees data labels, the actual drift draw or validation data statistics. Quantization and clipping occur before correction; lost information cannot be restored. All reference counts use nested subsets of the same standardized draws, and mismatch settings reuse those draws. No independent-panel probability claim.

For every pair retain actual, estimated and residual drift, clipped reads, SER, natural binary BER, worst-state SER and both point decisions. The screen remains observed worst-state SER <= 0.001. Record rescued, regressed, both-pass and both-fail cases, with net gain = rescued minus regressed. No positive gain required for execution success. Ideal controls must yield zero error and zero estimated drift.

## Reference overhead and limitations

Each panel contains 65,536 data reads; additional reference reads per acquisition are 8, 32 or 128, plus a separate calibration acquisition of the same size. Export both counts, incremental read fraction and useful read fraction. This is a hypothetical acquisition schedule, not an array throughput model: drift is constant for the entire panel. More frequent acquisitions would incur larger overhead; the model has no physical acquisition time. If reference and data read energy were equal, dynamic read energy would grow by the count ratio; actual reference write energy, read energy, calibration/control power and hardware latency are unknown. No measured area, retention, endurance or material fit.

## Reproduction

[Source](../simulations/memory/drift_compensation_v003.py), [tests](../simulations/memory/test_drift_compensation.py). The registry invokes both in the existing locked CI environment. Preserve baseline.csv, paired.csv, summary.csv, result.json and environment records through the original archive workflow.

Before W-003, analyze matched gains and regressions, acquisition cadence and reference mismatch; obtain empirical state distributions, retention and addressing constraints. No array release or physical qualification follows automatically. The [OPA-M comparison contract](OPA-W-001.md) remains unchanged.
