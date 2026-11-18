# OPA-NL-012 — Fixed causal receiver equalization and noise-aware readout

Status: proposed protocol, not implemented or executed.
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
