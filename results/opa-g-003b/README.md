# OPA-G-003B — Archived boundary readout results

Derived analysis of the [immutable original archive](../ci-originals/opa-g-003b/45833451176-15122739938/archive-provenance.json), not replacement data or a rerun. [Original CSV](../ci-originals/opa-g-003b/45833451176-15122739938/results.csv), [JSON](../ci-originals/opa-g-003b/45833451176-15122739938/result.json), [CI](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/45833451176). Archived CSV Git blob 961559ddba32ece4625ce2331d8004fe578d3d04 matches the manifest. 47/47 checks passed, 2236 rows, 1664 calibration and 1664 disjoint held-out rays. All held-out rays reach optics; 896 hits and 768 misses, including 128 exact tangencies (hits). Three repeats reuse the same geometric test set, hence 4992 classifications per scenario/policy, 2688 hits and 2304 misses, not 4992 independent geometric samples. All counts below sum disjoint exponent/sign/axis strata within each scenario, stage and policy, then sum the three repeats. Do not sum alternative policies as independent trials.

## Numerical controls

Float ideal: zero FP and FN on 1664 rays, including tangencies; epsilon diagnostic also zero, with 128 exact fallback calls. Uniform guard audit: 2865 rejects, 1231 optical; historical near_face: 2089 accepts, 2007 rejects, zero optical. These controls do not establish precision on arbitrary represented coordinates or physical guard circuitry.

## Calibration effects without fallback

| Scenario | Raw FP | Raw FN | Gain-only FP | Gain-only FN | Affine FP | Affine FN | Affine tangent FN / 384 |
|---|---:|---:|---:|---:|---:|---:|---:|
| scale_only | 528 | 876 | 528 | 876 | 528 | 1183 | 261 |
| large_scale | 648 | 1044 | 648 | 1044 | 938 | 1044 | 183 |
| noise_only | 950 | 1152 | 950 | 1152 | 950 | 1151 | 202 |
| combined | 854 | 1598 | 854 | 1598 | 827 | 1613 | 237 |

Positive gain alone leaves sign decisions unchanged. Affine offset can worsen boundary errors. In the scale-only setting 1450 of 1711 affine errors are nonzero-margin cases (528 FP + 922 FN); tangency alone cannot explain the problem. Raw optical error can include receiver cancellation and sine nonlinearity; this study does not independently attribute their contributions. The ideal float result does not license a tolerance in physical decisions.

## Confidence policies

Each cell gives FP / FN / fallback count, denominator 4992 optical rays. Uniform-side q99 is the historical residual calibration; geometric-ray q99 uses separate geometry calibration. The two window policies share identical noisy receiver values.

| Scenario | Uniform any-side | Uniform min-window | Geometry any-side | Geometry min-window |
|---|---|---|---|---|
| scale_only | 0 / 0 / 4204 | 0 / 0 / 4204 | 0 / 0 / 3624 | 0 / 0 / 3624 |
| large_scale | 0 / 0 / 4961 | 0 / 0 / 4961 | 0 / 0 / 4429 | 0 / 0 / 4429 |
| noise_only | 10 / 12 / 4545 | 10 / 12 / 4544 | 13 / 12 / 4540 | 13 / 12 / 4539 |
| combined | 0 / 0 / 4992 | 0 / 0 / 4992 | 2 / 10 / 4884 | 2 / 15 / 4868 |

Combined geometry min-window: 97.52% fallback, 15 missed hits (15/2688), two false hits (2/2304). Relative to geometry any-side, 16 fewer fallback calls but five additional missed hits. Uniform q99 achieves zero observed errors only by falling back on every combined-stress ray. Geometry q99 held-out ray-margin coverage ranges 99.04–99.34% across combined repeats (take one value per repeat; repeated CSV coverage fields are not independent). Coverage is not classification accuracy or a bound on missed hits. Noise-only leaves false negatives under both thresholds. The synthetic boundary-heavy dataset is intentionally difficult; fallback fractions are not directly comparable to G-003's mixed workloads.

## Gate decision

Numerical boundary study complete; robust optical acceptance is NOT demonstrated. No fixed optical policy is promoted to a qualified system baseline. Preserve both negative and positive results. Proceed to [G-004 protocol](../../research/OPA-G-004.md) for a matched electronic baseline and conditional cost/accuracy study, not a claim of acceleration. A separate held-out representative workload and zero-observed-FN screen are required before comparative ranking; failed settings remain reported. Include a fully electronic fallback baseline, and do not credit an all-fallback case with optical acceleration. Physical calibration, receiver precision and timing/energy measurements remain open.
