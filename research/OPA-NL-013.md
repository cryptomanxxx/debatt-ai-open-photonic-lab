# OPA-NL-013 — Independent confirmation of 22.222 Gsymbol/s with frozen electronic readout

Status: proposed protocol, not implemented or executed.
Source: [NL012](OPA-NL-012.md), [archived provenance](../results/opa-nl-012/provenance.json), run 44296016894, archive run 44299293097, merge 528844e14359d5db4aa3d44182915b9f22632c0a.

## Archived NL012 diagnosis

Read all 1008 group rows, 504 common-drive pairs and 216 coefficient records. The connector returns empty content for metrics.csv (3.08 MB) and paired_readouts.csv (5.62 MB), including line-range requests. Full seed and paired analysis is pending execution of research/analyze_nl012.py against the archive; do not claim those files were analyzed here.

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
