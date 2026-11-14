# OPA-ID-002 — Inverse-designed symmetric 1×2 splitter

[Successful CI job](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/43616022779/job/132511275395) · [PR #53](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/pull/53) · [Method](../../simulations/meep/OPA-ID-002.md)

All 10 mandatory checks and all three research targets passed. Runtime 395 s. Generic 2D Ez dielectric model (index 1.8 in air), wavelength 1550 nm, 2.4 × 2.4 µm design region, 625 material weights. Six accepted ascent steps at 30 px/µm; the seventh attempted step was rejected. Independent evaluation at 30 and 60 px/µm. Maximum full-gradient-normalized directional error across 12 comparisons: 3.9143e-6.

## Independent fine-resolution measurements (60 px/µm)

| Design | Total guided-mode transmission | Reflected mode power | Each output (incident mode normalized) |
|---|---:|---:|---:|
| Initial | 77.9574% | 0.026875% | 38.9787% |
| Optimized continuous | 98.1834% | 0.055542% | 49.0917% |
| Thresholded | 87.6899% | 0.608561% | 43.8450% |

Continuous optimization gains 20.2260 percentage points in transmission over the initial seed. Coarse/fine optimized transmission differs by 0.07204 percentage points. Fine-resolution optimized relative output imbalance is 2.79525e-13 (dimensionless). Unaccounted modal power is 1.76105%, not independently measured radiation. Direct thresholding at 0.5 reduces transmission by 10.4935 percentage points; fabrication constraints must be addressed in subsequent design work.

The earlier run 43614272898 failed the mandatory symmetry check. The accepted run explicitly symmetrizes the seed and every projected candidate; it verifies symmetry of initial, optimized and thresholded weights. No acceptance tolerances were relaxed.

## Original files

- [result.json](result.json): full report, 12 directional checks, seven optimization records, six measurement rows and all three sets of 625 weights.
- [gradient_checks.csv](gradient_checks.csv)
- [optimization_history.csv](optimization_history.csv)
- [measurements.csv](measurements.csv)
- [optimized_density.csv](optimized_density.csv): original 25 × 25 continuous density grid.
- [environment-lock.txt](environment-lock.txt)
- [provenance.json](provenance.json): source IDs and SHA-256 checksums.

Six files are byte-identical to the original artifact. The installed package inventory is recorded by hash only and remains in the original CI ZIP until expiration (2027-02-12).

## Limits

These are single-wavelength numerical results for local band-1 mode overlaps, normalized to a straight input reference. Finite monitor spans and evanescent overlap may affect the measured power. The thresholded material grid is not a fabrication-ready layout. No 3D, foundry, broadband, hardware, or novelty claim is made.
