# OPA-W-002H — Tail-aware photonic memory calibration

Status: implementation pending CI and review. [W-002G diagnostic replay](../results/ci-originals/opa-w-002g/45907209371-15158531611/result.json) reproduced all 62,208 archived policy rows. Its [state summary](../results/ci-originals/opa-w-002g/45907209371-15158531611/state_summary.csv) shows that the interior levels have higher aggregate symbol error than the two edge levels for all thirteen configurations. For 16 references and cadence 1, adaptive compensation reduced state 2 errors from 1,449,348 (fixed) to 905,933 out of 10,616,832 reads, yet the number of trajectories with more than two state 2 errors increased from 4,194 to 4,261. This motivates prioritizing trajectory-level worst-state performance rather than mean errors. The model's two edge levels have one decision boundary, while interior levels have two; this is a model property, not evidence of physical state-specific vulnerability.

## Frozen design

Retain the W-002E trajectory generator, all 324 scenarios, 64 steps, 32 retained cells per state and six reference-count/cadence combinations (4 or 16 references, every 1, 4 or 16 steps). Verify the original generator and multilevel decoder source blobs. Use new development seeds 31001–31004 and new held-out seeds 32001–32016, distinct from earlier experiments. No prior held-out observations are used to fit a policy. The same scenarios and random draws are matched across methods; trajectories across scenarios are correlated. No material or physical time calibration.

Compare fixed thresholds (zero reference reads), always correction, the original frozen W-002E adaptive gate (2 for 4 references/cadence 4, 3 otherwise), and tail-aware correction at matched acquisition cost. Keep all six configurations.

At acquisition, compute mean reference change m and uncertainty proxy u=max(0.002, sample standard deviation/sqrt(n)). Apply offset = gain * sign(m) * max(0, abs(m)-gate*u). Reject any clipped acquisition. Between acquisitions, either hold the offset or multiply it by 0.95^age. The proxy is not a calibrated confidence interval. Reference-only correlated drift is unidentifiable from reference agreement. Runtime uses only scheduled present/past reference observations, never data labels, future measurements, true drift or scenario parameters.

For each hardware configuration test 13 candidate triples: gate 1/2/3, gain 0.5/1, hold or age decay 0.95, plus zero gain with no correction. The zero gain candidate still incurs the scheduled reference reads. Select lexicographically by maximizing the number of development trajectories passing worst-state SER <= 0.001, minimizing regressions relative to fixed, minimizing the sum of maximum state error counts, then minimizing total symbol errors. Break exact ties by ascending numeric candidate tuple. Freeze all selections before scoring held-out data. No held-out retuning or selection of a winning configuration.

## Evaluation and outputs

1,296 development trajectories and 5,184 held-out trajectories; 31,104 matched configuration rows, each retaining all four policy metrics. Count mean SER, BER counts, worst-state errors, point passes, rescued and regressed trajectories, residual drift and exact reference acquisition reads; aggregate per-state errors, failing trajectories and new failures. Each trajectory has 32,768 reads and 2,048 reads per state; at most two errors per state meets the existing numerical point criterion. A positive gain is not required for execution success.

Archive development.csv, heldout.csv, summary.csv, state_summary.csv, result.json and two environment files. [Implementation](../simulations/memory/tail_calibration_v008.py), [tests](../simulations/memory/test_tail_calibration.py). Test future-data invariance, clipping, zero correction, decay, seed separation and objective precedence. All reference-assisted policies incur 8*n*(64/cadence) acquisition reads and 8*n initial calibration reads. No hardware joules, latency or retention inferred. The strict target remains a descriptive point screen, not statistical qualification.

## Next gate

Archive original results, audit matched held-out outcomes and determine if the new objective improves the point screen without unacceptable mean-error degradation. If no useful envelope exists, report that negative result; do not tune on test data. Material distributions, retention, read disturb, energy, addressing and fabrication constraints remain missing. No W-003 release or physical qualification.
