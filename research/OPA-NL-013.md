# OPA-NL-013 — Independent confirmation of 22.222 Gsymbol/s with frozen electronic readout

Status: implemented and executed; initial report analysis complete, original archive pending.
Source: [NL012](OPA-NL-012.md), [archived provenance](../results/opa-nl-012/provenance.json), run 44296016894, archive run 44299293097, merge 528844e14359d5db4aa3d44182915b9f22632c0a.

## Archived NL012 diagnosis

Read all 1008 group rows, 504 common-drive pairs and 216 coefficient records. The connector returns empty content for metrics.csv (3.08 MB) and paired_readouts.csv (5.62 MB), including line-range requests. At protocol time the full seed and paired analysis was pending. The successful NL013 run subsequently executed research/analyze_nl012.py as a mandatory preflight; its full audit output is included in the original NL013 artifact.

| Drive mW | Groups | Clean gate | Electrical gate | Confirmed combined |
|---:|---:|---:|---:|---:|
| .1 | 504 | 405 | 274 | 173 |
| 1 | 504 | 324 | 318 | 318 |
| Total | 1008 | 729 | 592 | 491 |

Clean gate includes stationary eligibility and unfiltered threshold. Maximum sampled combined diode peak 1.7020183718197541 mW; no cap failures. At 40/5 ps, low/high drive clean 81/57, electrical 13/54, combined 0/54 (126 groups per drive). At 45/5 ps clean 102/87, electrical 82/87, combined 40/87. At 50/5 ps clean 120/105, electrical 106/105, combined 93/105. At 40/0 ps clean 102/75, electrical 73/72, combined 40/72. Thus at 40 ps finite response, low-drive noise remains a key limitation; no assertion of causality from drive alone since frozen weights differ.

| Method | Clean | Electrical | Combined |
|---|---:|---:|---:|
| End | 123 | 87 | 65 |
| Eighth | 108 | 82 | 53 |
| Quarter | 78 | 50 | 35 |
| Half | 12 | 3 | 0 |
| Ridge8 | 144 | 132 | 125 |
| Ridge16 | 144 | 133 | 126 |
| Ridge16 strong | 120 | 105 | 87 |

Each method has 144 groups across all timings and drives; counts are grid-dependent. Both ordinary ridge methods pass all clean gates; the stronger penalty does not necessarily improve classification. No direct noise-amplification claim without seed metrics.

### Prespecified settings and NL012 reference results

At 45 ps / 5 ps, LO 1 mW, cutoff 60 GHz:

| Method | Worst .1 mW | Worst 1 mW | Both confirmed |
|---|---:|---:|---|
| End | 92.187500% | 99.902344% | no |
| Eighth | 93.652344% | 98.632812% | no |
| Quarter | 92.480469% | 93.066406% | no |
| Half | 83.496094% | 73.437500% | no |
| Ridge8 | 95.800781% | 100% | yes |
| Ridge16 | 96.386719% | 100% | yes |
| Ridge16 strong | 94.335938% | 99.707031% | no |

Ridge8 vs Ridge16 difference 0.5859375 percentage points in low-drive worst-repeat maxima for this matched setting (difference of minima, not paired correctness). The corresponding coefficients have L2 norms .9523355 and .9546129; augmented-fit condition numbers 20.636 and 24.855; calibration current RMSE 7.7771 and 7.6951 microampere. These do not directly quantify output noise. Ridge16 previous-symbol coefficients are comparatively small; that motivates testing Ridge8, not removing taps or changing coefficients in confirmation. At 45/5 ps, LO 2 mW / cutoff 60 GHz, Ridge8 gives 96.484375% / 100%, Ridge16 97.0703125% / 100%. At 50/5 ps LO 1 mW / cutoff 20 GHz, end 95.703125% / 99.70703125%, Ridge8 97.4609375% / 100%, Ridge16 97.8515625% / 100%.

## Confirmatory question and immutable settings

Primary endpoint: independently confirm C2, zero gap, 45 ps on, 5 ps response, LO 1 mW, cutoff 60 GHz, Ridge16 with exactly the NL012 coefficient bytes. Secondary endpoint: same setting with Ridge8, to assess whether the cheaper readout also clears the identical gate. Secondary high-LO reference: 45/5, LO 2 mW, 60 GHz, all seven methods. Positive control: 50/5, LO 1 mW, 20 GHz, all seven methods. Include all four unequalized anchors and strong ridge comparator at every setting; no other timing/LO/cutoff, no model re-fit, no selection or tuning on test data. 25 Gsymbol/s finite response remains a later exploratory problem.

Pin these nine little-endian float64 coefficient SHA-256 digests (in Ridge8, Ridge16, Ridge16 strong order):

| On/response, LO, cutoff | Ridge8 | Ridge16 | Strong |
|---|---|---|---|
| 45/5, 1, 60 | 1f21ed5381aefa68f2ac7ec8eae6189b4332c93d07bcf4977c7ebb433985d08d | 1cf055e0bb853b437070171a1ee9135716f61a760a2421dca1e9ca6da57f794f | 64db2504804993c2f4a9db888957f186179b09807b45c4e468c31c376b7e0623 |
| 45/5, 2, 60 | 6b5dd601fc801b904deedb05b7784d9ae1955cfbccc61532147d7c6f3f3b15c3 | 1e462161c94f12ad8dd2ed6a6bc317f3073fae0da125141fd8d395bc9159e8cb | 06d73bfc95e3e1b6fd05367104509cf61c5f191a5a96a0c6e169f51b318aef9a |
| 50/5, 1, 20 | 84b210baa61ecac14b3b0b0a28e705c018d91b971a1114a458d7b613a1796e8e | 83faf818f67ccc216a7a8102b5908f9ac354a5c3a71affe5d571bf9a95d2fba4 | 094e3cdae57127e28438151cde43dc54632d2889718cf182bc8726cd10d34c4d |

Verify full NL012 manifest hashes, coefficient archive identity, each fixed key and digest, readonly arrays and unchanged hashes at all resolutions. Preserve original frozen NL003 weights, optical dynamics, signal-only 3 dB loss, phase, PSD, held optical offsets, stationary receiver initialization and diode cap. No calls to fit during NL013. Retain exact eight-segment moments and common latent pairing; no cross-stream history or future samples. Prior implementation audit script must pass before simulation.

## Independent panels and test design

Two disjoint panels A/B; each five existing frozen seeds per drive, eight streams of 256 symbols (2048 examples per seed/drive/panel), eight independent noise repeats. Balanced bounded-jitter XOR dataset, same ordering and underlying random draws across matched settings and arms within panel. Use five fresh RNG domains per panel: 10104–10108 and 10114–10118, subject to prior code audit; record identities. No reused NL012 calibration or test draws. New examples/noise but same optical weight sets; not independent trained models or physical devices. No calibration, additional training, threshold adjustment, early stopping, retuning or dropping first symbols. Zero-pad previous-symbol features independently per stream. Use end/eighth/quarter/half and frozen Ridge8/16/strong decisions on the identical trajectories. Report per-panel outcomes, do not pool to rescue a failed panel.

Counts: 3 receiver settings x 7 methods x 2 drives x 5 seeds x 2 panels = 420 finest-resolution seed rows; 84 panel-specific groups; 1260 resolution rows / 252 resolution groups over three aligned grids. 21 common-drive method/setting tuples with two-panel confirmation. Finest-resolution exact paired equalizer vs each of four anchors: 3 x 3 x 4 x 10 x 2 x 8 = 5760 repeat contingency rows; additionally Ridge16 vs Ridge8 480 repeat contingency rows. Include exact combined correct counts per repeat, first/last-eight, raw clean-reference RMSE, noise variance ratio vs end, coefficient digest and conditional laser bounds. Report individual panel results and all failures, no multiple-comparison claims of significance.

## Gate and numerical controls

Per panel: all five seeds, stationary eligible, unfiltered and clean classification >=95%, every combined repeat >=95% (at least 1946/2048), combined sampled diode peak <=2 mW. Report electrical-only gate separately. Require both drives and both panels to meet gate with agreement between middle and fine resolutions; no pooled rescue or selecting only best panel. Report coarse/middle/fine errors, retain NL011/012 tolerances; report seed and group gate changes, flag any middle/fine group disagreement. Audit optical balance and phase/hybrid identities, stationary noise and eight-segment regression, finite outputs, exact keys, coefficient hashes, causality, independent domains, paired count consistency and archive immutability. All scientific failures are valid results and do not fail CI if implementation checks pass. Implementation failures do fail CI. Run a small pilot to check runtime/memory.

Report LO-only lower bounds at assumed 20% conversion efficiency (5 mW / 10 mW), plus conditional signal laser lower bounds; not total energy. At 45 ps eight means imply 177.778 Gsegment/s aggregate sampling/integration rate. Ridge8 has eight weighted terms per decision, Ridge16 sixteen and previous-symbol storage. Do not claim half total power, ADC performance or hardware feasibility. Independent confirmation remains conditional numerical evidence for this XOR model and frozen weights, not measured hardware, general AI accuracy or BER. If primary fails, report nonconfirmation; no post hoc coefficient search. If secondary passes, prioritize lower-complexity hardware analysis; if not, retain Ridge16. Only after this test consider preregistered NL014 finite-response 42–44 ps exploration and optical margin/noise redesign.

## Executed results — 2026-11-18

[Successful run 44304216745](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44304216745), job 134801555451, source head 542c01c13097e43fcd710c03d9a4f9f26128b72a, CI merge ae17ffa92215be5afcfe6bf571180c868c680064, final merge e733d41bd87fca72abbcf9630b86e01914dc9b59. The initial run failed on an incorrect seed assertion; the corrected run pins the actual NL003 seeds 1301–1305. No model or protocol parameters changed. All 23 implementation checks passed, 420 primary seed rows, 84 groups, 252 resolution groups (1260 resolution seed rows), 6240 paired rows, 21 two-panel pairs. The full NL012 audit passed, including 69120 paired rows. Simulation elapsed 1029.236788019 s. 44/84 groups confirmed, 7/21 tuples confirmed across both panels and drives, zero ambiguous groups. All eight convergence comparisons had zero changed seed and group gates.

### All prespecified outcomes

Worst combined repeat across five seeds per panel/drive; percentages rounded for display. Confirmed requires all four panel/drive groups and numerical gates, not only accuracy.

| On ps | LO mW | Cutoff GHz | Method | A low % | A high % | B low % | B high % | Confirmed |
|---:|---:|---:|---|---:|---:|---:|---:|---|
| 45 | 1 | 60 | end | 92.72461 | 99.80469 | 92.72461 | 99.80469 | no |
| 45 | 1 | 60 | eighth_mean | 93.75000 | 98.97461 | 93.99414 | 98.53516 | no |
| 45 | 1 | 60 | quarter_mean | 92.62695 | 93.26172 | 93.01758 | 93.01758 | no |
| 45 | 1 | 60 | half_mean | 85.69336 | 72.50977 | 85.05859 | 72.16797 | no |
| 45 | 1 | 60 | ridge8 | 95.65430 | 99.95117 | 95.70313 | 99.95117 | yes |
| 45 | 1 | 60 | ridge16 | 95.99609 | 100.00000 | 96.09375 | 99.95117 | yes |
| 45 | 1 | 60 | ridge16_strong | 94.18945 | 99.75586 | 93.84766 | 99.75586 | no |
| 45 | 2 | 60 | end | 93.65234 | 99.80469 | 93.99414 | 99.85352 | no |
| 45 | 2 | 60 | eighth_mean | 94.43359 | 99.12109 | 94.72656 | 98.68164 | no |
| 45 | 2 | 60 | quarter_mean | 92.96875 | 93.45703 | 93.35938 | 93.06641 | no |
| 45 | 2 | 60 | half_mean | 85.74219 | 72.70508 | 85.15625 | 72.02148 | no |
| 45 | 2 | 60 | ridge8 | 96.24023 | 100.00000 | 96.19141 | 99.95117 | yes |
| 45 | 2 | 60 | ridge16 | 96.48438 | 100.00000 | 96.53320 | 99.95117 | yes |
| 45 | 2 | 60 | ridge16_strong | 94.58008 | 99.80469 | 94.48242 | 99.80469 | no |
| 50 | 1 | 20 | end | 95.84961 | 99.70703 | 95.55664 | 99.70703 | yes |
| 50 | 1 | 20 | eighth_mean | 94.43359 | 97.11914 | 94.92188 | 97.02148 | no |
| 50 | 1 | 20 | quarter_mean | 92.52930 | 87.06055 | 92.48047 | 87.54883 | no |
| 50 | 1 | 20 | half_mean | 83.20313 | 66.50391 | 82.27539 | 66.06445 | no |
| 50 | 1 | 20 | ridge8 | 97.16797 | 100.00000 | 97.26563 | 100.00000 | yes |
| 50 | 1 | 20 | ridge16 | 97.50977 | 100.00000 | 97.55859 | 100.00000 | yes |
| 50 | 1 | 20 | ridge16_strong | 94.28711 | 99.95117 | 93.99414 | 99.95117 | no |

Primary Ridge16 at 45 ps, 1 mW LO, 60 GHz passes with maximin 0.9599609375; secondary Ridge8 passes with 0.95654296875. Difference of minima 0.341796875 percentage points (not paired effect). Both retain frozen NL012 coefficients. At 2 mW LO the respective minima are 0.96484375 and 0.9619140625; additional LO power gives modest improvement in this model, not a hardware efficiency measurement. Positive control 50 ps end passes (0.95556640625). No unequalized 45 ps anchor or strong ridge comparator passes both panels/drives. Both conventional ridge methods pass all three settings. New data and noise, longer streams, same trained weights and numerical model: this is independent test-data confirmation, not independent physical measurement. Ridge8 eliminates previous-symbol feature storage and halves weighted terms, not proven receiver energy. At 45 ps the eight-segment requirement remains 177.778 Gsegment/s aggregate. LO-only lower bound 5 mW at assumed 20% efficiency, not total power.

### Numerical checks

Maximum field error 2.1446598254698828e-10 sqrt(mW), common-grid waveform error 3.2667557060022432e-9 sqrt(mW), clean current error 7.719785223071242e-9 A, noisy current error 7.720644230408075e-9 A, sampled peak error 9.84716165275401e-7 mW. Partition current and covariance errors 1.8973538018496328e-19 A and 1.4052147573268e-14 relative. Segment errors 1.3552527156068805e-19 A and 4.574024407557909e-15 relative. Stationary variance ratio 1.0012673236303482, lag 0.28528539589534957 vs 0.28460954333602934 expected, mean variance ratio 1.0033964410261738. Numerical consistency only; no measured hardware, BER, general AI accuracy or wall-plug claim.

### Archival and next steps

Artifact 14428427620, exact ZIP 390041 bytes, SHA-256 32b8cf14f8e0e2bda8930308eceebefebde6472eb7a383156c37d17a414d5404. Manual archive workflow verifies original ZIP, all thirteen CI-emitted hashes and staged bytes. After archive inspect per-seed and paired outcomes, NL012 noise amplification and power bounds. Preserve 45 ps Ridge8 as confirmed reference. NL014 should be separately preregistered as exploratory 42–44 ps finite-response optimization with 45 ps control, not an extension of the NL013 confirmation. The 40 ps finite-response result remains unconfirmed; no claim of 25 Gsymbol/s hardware operation.
