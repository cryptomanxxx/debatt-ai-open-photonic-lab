# OPA-NL-012 — Fixed causal receiver equalization and noise-aware readout

Status: implemented and executed; initial CI-report analysis below, raw archive pending.
Parent: [NL011](OPA-NL-011.md), [verified archive](../results/opa-nl-011/provenance.json), run 44288710042, archive run 44292291745, archive merge dcb3e5ef2aae0327e354923a7c7ac8d0f9370af3.

## Archived NL011 diagnosis

All 1536 summary rows and 768 common-drive pairs read directly from archive. Join by candidate/on/gap/response/LO/cutoff/readout/drive; both-drive minima, maximin and confirmed flags match all 768 pair rows. The 3.89 MB primary metrics file returned empty content through connector; seed-level analysis and conditional total laser-power Pareto analysis remain pending. Run the accompanying archive-analysis script against the verified local archive before NL012 execution.

| Drive mW | Groups | Stationary and unfiltered pass | Also clean filtered pass | Electrical pass | Combined confirmed |
|---:|---:|---:|---:|---:|---:|
| .1 | 768 | 768 | 456 | 179 | 108 |
| 1 | 768 | 768 | 248 | 227 | 220 |
| Total | 1536 | 1536 | 704 | 406 | 328 |

78 electrical-only passes fail combined gate, 71 at .1 mW and 7 at 1 mW. No combined-only passes; no sampled combined diode cap failures; maximum 1.7111708421426945 mW. Different drive-specific frozen weights confound causal attribution to drive alone.

| On/response ps | Clean low/high | Electrical low/high | Combined low/high |
|---|---|---|---|
| 35/0 | 40/0 | 0/0 | 0/0 |
| 35/5 | 12/0 | 0/0 | 0/0 |
| 37.5/5 | 32/0 | 0/0 | 0/0 |
| 40/5 | 52/12 | 0/6 | 0/4 |
| 45/5 | 68/44 | 31/39 | 0/38 |
| 50/5 | 88/68 | 50/68 | 35/67 |
| 40/0 | 68/28 | 18/18 | 0/15 |
| 200/50 | 96/96 | 80/96 | 73/96 |

Each timing/drive has 96 groups. At 45 ps, 31 low-drive groups pass electrical but none combined; at 40 ps finite response no low-drive electrical pass. At 35–37.5 ps no high-drive clean filtered pass.

| On/response ps | LO mW / cutoff GHz | Drive | Clean min | Electrical worst | Combined worst |
|---|---|---:|---:|---:|---:|
| 45/5 | 3 / 30 | .1 | 100% | 96.484375% | 94.53125% |
| 45/5 | 3 / 30 | 1 | 99.609375% | 98.4375% | 97.65625% |
| 40/5 | 3 / 40 | .1 | 100% | 92.3828125% | 90.625% |
| 40/5 | 3 / 40 | 1 | 91.796875% | 91.015625% | 90.8203125% |
| 40/0 | 3 / 40 | .1 | 100% | 96.09375% | 93.9453125% |
| 40/0 | 3 / 40 | 1 | 98.4375% | 96.2890625% | 95.5078125% |
| 50/5 | 1 / 20 | .1 | 100% | 97.8515625% | 95.5078125% |
| 50/5 | 1 / 20 | 1 | 99.8046875% | 99.609375% | 99.609375% |

All rows end readout; first six are retrospectively selected maximin settings, final two independent NL010 anchor replication. At 45 ps low drive the clean and electrical gates already pass; equalization is not guaranteed to fix optical noise. At 40 ps low drive the electrical gate fails despite perfect clean classification, whereas high drive also has deterministic filter error. Explicitly compare noise-aware averaging with inverse-like equalization, which may amplify noise.

Across all timing/drive/cutoff/readout settings, LO .1/1/2/3 mW gives 59/88/90/91 combined passes (384 groups each); clean passes 176 each. Paired 1 versus 3 mW: 88 both, 0 first-only, 3 second-only, 293 neither. End versus eighth_mean: 80 both, 21 end-only, 18 eighth-only, 265 neither. End/eighth/quarter/half combined counts 101/98/81/48, each out of 384. These grid-dependent counts are not universal performance rankings. LO-only electrical lower bounds at assumed 20% efficiency are 5/10/15 mW for 1/2/3 mW LO; no hardware power claim.

## Preregistered NL012 question

Can a fixed, causal linear receiver readout, calibrated on independent data and frozen before held-out evaluation, achieve a shared-drive confirmed gate at 45 ps (22.222 Gsymbol/s), then 40 ps (25 Gsymbol/s), with finite 5 ps material response? Preserve C2, frozen NL003 weights, TCMT, phase/loss, noise model and diode cap. No retraining of optical network, threshold fitting, decision feedback, future samples, or test-label optimization. This is an electronic receiver extension, not all-optical computing.

Timing grid: C2 zero gap, on 40, 45, 50 ps, material response 5 ps; 40 ps instantaneous response diagnostic separately. LO 1,2,3 mW; cutoff 20,30,40,60,80,120 GHz. Retain four NL011 readout anchors (end, eighth, quarter, half means). Add three calibrated causal linear methods: current-symbol eight segment means; current plus previous symbol eight means each; same 16 features with stronger regularization. Four anchors plus three equalizers, four timings x 3 LO x 6 cutoff x 7 methods x 2 drives x 5 seeds = 5040 primary rows, 1008 groups; three resolutions = 15120 rows. No 28.57 Gsymbol/s claim in this study.

All eight segment means obtained from one causal receiver trajectory via NL010 exact joint endpoint/mean covariance per segment, using aligned time grids. Preserve state across symbols, reset only between independent streams. Use previous-symbol features only if available; at first symbol use zero padding, not a future sample or label. Include first-symbol outcomes in all accuracy gates, report first-eight and last-eight diagnostics. Derive all four anchor readouts from same trajectory (end state, means of last one/two/four segments).

## Calibration, fixed coefficients and held-out evaluation

Fresh RNG domains, audit all prior uses including NL011 94–98 before assigning. Reserve 104–108 for calibration inputs, permutation, optical noise, receiver initialization and segment innovations; 114–118 for corresponding disjoint test streams, only if confirmed unused. For each frozen seed/drive/timing/LO/cutoff, generate 512 calibration examples (eight streams of 64), and 1024 independent held-out examples (eight streams of 128), eight noise repeats each. Balance labels and pair inputs/noise across receiver methods, LO, cutoff and resolutions; no cross-drive mixing of weights. Fit a *single shared receiver coefficient vector for both drives* per timing/LO/cutoff/method, pooling calibration rows across all five seeds and both drives with equal weighting. Do not fit on test data or use test labels for feature scaling. Calibration may use known optical reference current, not XOR labels: target instantaneous clean balanced hybrid current at end of symbol, with inherited loss and phase. Preserve zero decision threshold and no intercept. Normalize features and target by one common positive current scale (RMS calibration target with explicit positive floor 1e-12 A); this does not alter threshold or relative drive weighting. Use noisy combined-arm calibration features from all eight repeats, target repeated clean reference. Minimize mean squared error plus lambda times squared coefficient norm; lambda fixed at 0.01 for 8- and 16-feature methods, 0.1 for strongly regularized 16-feature method. Solve via augmented least squares (sqrt(n*lambda) identity appended), no test-set tuning. Freeze calibration on finest grid; apply same coefficients to all three held-out resolutions. Report coefficient arrays and hashes, training domain identities, singular values/condition numbers, calibration RMSE, noise amplification (variance of equalized electrical-only residual relative to end anchor, same test trajectory), and clean target error. Do not infer hardware realizability from coefficient fit.

## Verification

Use aligned on/(8*n) dt, halve twice; n=ceil(on/(8*.25)). Preserve NL010/011 convergence tolerances, compare optical fields, sampled diode peaks and raw decision currents for all readouts including equalizers; flag group gate differences between two finest levels, report all comparisons. Verify synthetic identity/end-anchor, exact multi-segment joint covariance versus independent stepwise recurrence, constant/step response, stationary noise and previous-feature chronology; perturb future samples and labels and assert earlier decisions unchanged. Test zero-padding and no cross-stream contamination. Verify coefficient freeze, calibration/test domain disjointness, no test labels in fitting interface, identical coefficient hashes at all resolutions, complete keys and counts, finite values, all archive hashes, energy balance and sampled diode cap. Pilot runtime/memory and deterministic partition if needed; all rows required. No scientific failure fails CI.

Primary inherited gate: all five seeds stationary eligible, clean unfiltered optical accuracy >=95%, clean receiver decision accuracy >=95%, worst of eight combined-noise repeats >=95%, sampled combined diode peak <=2 mW. Report electrical-only gate separately. Use same 1024 held-out examples for all paired comparisons, with exact counts and no dropping first symbols. Compare equalizer vs each unequalized anchor at identical timing/LO/cutoff/drive/seed/repeat. Report all common-drive confirmed ties, maximin rankings and failure causes. A longer stream and new data change difficulty relative to NL011, so cross-experiment improvements cannot be ascribed solely to equalization.

Report LO and signal laser lower bounds at assumed 20% efficiency, tap counts (8 or 16), sampling requirement (8 means per symbol), and arithmetic count (8 or 16 weighted terms per decision); do not claim receiver electrical power without calibrated ADC/filter/compute model. A 25 Gsymbol/s eight-segment readout implies 200 Gsegment/s aggregate segment rate, not necessarily a single ADC specification. Digital implementation may erase photonic energy advantages; analog alternatives are a separate study. No hardware rate, BER, general AI accuracy or total efficiency established.

A passing exploratory grid point requires subsequent independent confirmation before robust claims. If no gain, report null result and consider optical noise/margin redesign rather than unbounded LO increases.

## Implementation clarification (before execution)

NL001 uses seed-domain training draws 100+step, so the tentative 104–108 and 114–118 reservations overlap that earlier domain family. Use 10004–10008 and 10014–10018 instead, after inspecting NL001–011 RNG call sites. All other preregistered settings remain unchanged. The archive audit runs before calibration; coefficients are saved in a separate JSON artifact. No numerical outcome was used to choose domains.

## Initial results — 18 November 2026

Source [experiment run 44296016894](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44296016894), job 134773246258, PR 171, artifact 14425195090. All 22 implementation checks passed, including full NL011 seed audit. 5040 primary seed rows, 1008 primary groups, 15120 resolution rows, 3024 resolution groups; eight convergence comparisons. Runtime 526.188 seconds. The successful run also produced the preregistered coefficients and paired-readout evidence; the full raw files are not yet archived or independently analyzed here. These results come from the CI-emitted report.

491/1008 combined groups confirmed; 173/504 common-drive tuples pass at both drives. No ambiguous groups, no seed or group gate changes across all eight resolution comparisons. 40 common-drive tuples at 40 ps with instantaneous material closure (25 Gsymbol/s); 40 at 45 ps with 5 ps material response (22.222 Gsymbol/s); 93 at 50 ps with 5 ps response (20 Gsymbol/s); zero at 40 ps with 5 ps response. 145 passing single-drive groups (491 - 2*173) not classified by drive from this report subset. The fastest finite-response result improves nominal cadence by 11.111% relative to the prior 20 Gsymbol/s confirmation. Instantaneous closure is a diagnostic, not physically validated material speed.

### Best maximin settings by timing (all ties)

| On ps | Response ps | LO mW | Cutoff GHz | Readout | Worst .1 mW | Worst 1 mW | Both pass |
|---:|---:|---:|---:|---|---:|---:|---|
| 40 | 5 | 3 | 120 | ridge16 | 93.750000% | 98.632813% | no |
| 45 | 5 | 2 | 60 | ridge16 | 97.070313% | 100.000000% | yes |
| 45 | 5 | 2 | 120 | ridge16 | 97.070313% | 100.000000% | yes |
| 45 | 5 | 3 | 60 | ridge16 | 97.070313% | 100.000000% | yes |
| 45 | 5 | 3 | 120 | ridge16 | 97.070313% | 100.000000% | yes |
| 50 | 5 | 2 | 40 | ridge16 | 98.339844% | 100.000000% | yes |
| 50 | 5 | 2 | 80 | ridge16 | 98.339844% | 100.000000% | yes |
| 50 | 5 | 2 | 120 | ridge16 | 98.339844% | 100.000000% | yes |
| 50 | 5 | 3 | 40 | ridge16 | 98.339844% | 100.000000% | yes |
| 50 | 5 | 3 | 60 | ridge16 | 98.339844% | 100.000000% | yes |
| 50 | 5 | 3 | 80 | ridge16 | 98.339844% | 100.000000% | yes |
| 50 | 5 | 3 | 120 | ridge16 | 98.339844% | 100.000000% | yes |
| 40 | 0 | 2 | 60 | ridge16 | 96.777344% | 99.707031% | yes |
| 40 | 0 | 3 | 60 | ridge16 | 96.777344% | 99.707031% | yes |

At 45 ps the best shared-drive result is 97.0703125% and 100% worst repeat at .1/1 mW, with Ridge16, LO 2 or 3 mW and cutoff 60 or 120 GHz. The 2 mW / 60 GHz setting is a lower-LO, lower-cutoff member of these ties, not a measured energy optimum. At 40 ps finite response the best result is 93.75% / 98.6328125% with Ridge16, LO 3 mW, cutoff 120 GHz; no shared pass. At 40 ps instantaneous response, best 96.77734375% / 99.70703125% with Ridge16, LO 2 or 3 mW, cutoff 60 GHz. At 50 ps finite response, best 98.33984375% / 100%. All are retrospective maxima on the sampled grid, not independent confirmation of selected settings.

### Common-drive passes by method

| On/response ps | End | Eighth | Quarter | Half | Ridge8 | Ridge16 | Ridge16 strong | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 40/5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 45/5 | 0 | 0 | 0 | 0 | 18 | 18 | 4 | 40 |
| 50/5 | 11 | 17 | 14 | 0 | 18 | 18 | 15 | 93 |
| 40/0 | 0 | 0 | 0 | 0 | 17 | 18 | 5 | 40 |

Each method/timing has 18 shared LO/cutoff tuples. At 45 ps both Ridge8 and Ridge16 pass all 18 receiver settings; no unequalized readout passes any, on identical held-out trajectories. This supports a model-specific benefit of equalization without relying on cross-experiment comparisons. Stronger regularization passes only four. At 45 ps LO 1 mW also passes at every cutoff for both Ridge8 and Ridge16. Best reported low-drive worst among these is Ridge16 at 60 GHz, 96.38671875%; exact high-drive value is not included in the passing subset. LO-only electrical lower bound at assumed 20% efficiency is 5 mW for 1 mW LO, 10 mW for 2 mW, 15 mW for 3 mW. Eight segment means per symbol at 45 ps imply 177.778 Gsegment/s aggregate rate; Ridge8/16 require eight/sixteen weighted terms per decision. Receiver/ADC, distribution and phase-lock costs are not modeled; cannot claim energy efficiency. Paired per-repeat correctness and seed-level noise amplification need raw analysis before ranking methods by accuracy gain or noise reduction.

### Numerical verification

Maximum endpoint difference 3.874585396872041e-10 sqrt(mW), common-grid waveform difference 3.231376433874881e-9 sqrt(mW), clean decision difference 2.49810265303004e-8 A, noisy decision difference 2.4984369511655462e-8 A, sampled peak difference 1.4617213190959433e-6 mW. Eight-segment partition current/covariance errors 1.8973538018496328e-19 A and 1.4052147573268e-14 relative; segment regression errors 1.3552527156068805e-19 A and 4.574024407557909e-15 relative. All frozen-coefficient and paired-count checks passed. These validate numerical consistency, not physical hardware, BER or general AI accuracy.

### Archive and next steps

Original ZIP 2838736 bytes, SHA-256 1744fb578163f69d8a35b5fd35a1a0354cecbef3146d7177fc1bb1c28f8e5daf. Manual workflow pins run, artifact, raw ZIP and thirteen original file hashes and verifies staged bytes. Includes NL011 seed audit, coefficient records and paired readouts. After archival inspect all 1008 groups and 504 common-drive pairs, verify seed-level gates, analyze paired equalizer versus anchor outcomes, coefficient norms/conditioning, noise amplification, power and low-complexity tradeoffs. For NL013 prioritize independently confirming a prespecified 45 ps, 5 ps material-response, LO 1 mW Ridge8/Ridge16 anchor using frozen NL012 coefficients and longer independent streams; investigate 42–44 ps finite-response settings only in a separately preregistered exploratory sweep. The 40 ps finite-response shortfall motivates optical margin/noise redesign or improved readout rather than interpreting the instantaneous result as hardware performance. No new protocol approved here.
