# OPA-NL-018 — Independent frozen-coefficient confirmation at 41 ps

Status: executed; primary failed both low-drive panels, both positive controls failed panel B low drive. No promotion. Exact archive pending.
Basis: [NL017](OPA-NL-017.md), run 44350128879, archive merge e2a1ad51991966e6ff06bc02f6db45f15b9b7a34.

## Raw archive audit and diagnosis

Retrieved full NL017 primary and resolution CSVs, paired CSV (large Git blob), groups, tuples and coefficient records. Independent exact-key checks covered 500 primary seed rows, 1500 resolution rows, 100 primary groups, 300 resolution groups, 50 common-drive tuples, 30 coefficient links, 11680 paired rows and 292 summaries; both contingency marginals, repeat minima, seed/group gates, middle/fine agreement and summary effects all matched. Python reproducible audit research/analyze_nl017.py must run successfully before any new test generation; not yet executed.

Selected frozen Ridge16 Midlow (41 ps, LO3, 80 GHz) low-drive unfiltered and clean minima 1, electrical worst .96484375, combined .95263671875, high-drive combined .99365234375. Limiting seed 1304 repeat counts 1951,1954,1968,1961,1953,1964,1962,1951 (threshold 1946). Five decisions margin; same frozen vector failed NL016 at 1942/2048 (.9482421875). Mean electrical noise variance ratio .6310681136185214, clean target RMSE 1.2263689466648093e-6 A; optical memory maximum .004445353406986622 sqrt(mW); sampled low-drive diode peak 1.5499652029994557 mW; mean conditional signal+LO laser electrical lower bound 16.514778087227597 mW assuming 20% efficiency, not total system power. Frozen ordinary Ridge16 at same setting low-drive electrical .966796875, combined .951171875; relative variance .5752591368758952, RMSE 1.6750335428209009e-6 A. Fresh Ridge24 Midlow low .95263671875, high .99462890625; fresh Ridge32 Midlow low .9521484375, high .99462890625. Neither required for primary pass. Fresh Ridge32 Midlow block L2 norms current 1.035770539434775, lag1 .13527243778710438, lag2 .031319526621740305, lag3 .019690721136157708; relative norms .1306/.0302/.0190, not signal energy or causal contribution. Condition numbers fresh Midlow 16/24/32 at 41/80: 34.619990701559566/36.94418983859128/38.16688070405791. Calibration RMSE 1.308497420418276e-5/1.3071375760961564e-5/1.3068578386672164e-5 A. Matched history effects mixed and at most 21/81920 net decisions, no independent-trial significance claim.

At 40/3/120 low drive all eight ridge methods have clean minima 1 and electrical gates pass; combined all fail, best .9453125 (1936/2048), limiting seed1304. At 40 ps all 12 groups meet unfiltered threshold per drive; clean 11 low/9 high, electrical 8/9, combined 0/9. At 41 ps all 24 meet unfiltered; clean 22/20, electrical 16/19, combined 16/19. At 42 ps all 14 meet unfiltered; clean 12/10, electrical 6/10, combined 4/10. Low-drive combined noise remains limiting. No further history tuning based on NL017 test labels.

## Prespecified endpoints

Primary: 41 ps, LO3 mW, 80 GHz, frozen_ridge16_midlow (NL016 vector, NL017 ranked candidate). Supporting endpoints at same setting: frozen_ridge16, fresh NL017 ridge16, ridge16_midlow, ridge24_midlow, ridge32_midlow (all now frozen). Four anchors included. Supporting methods selected to compare ordinary vs weaker regularization, original vs refreshed calibration, and longer history, not to rescue primary. No 40 ps experiment or 120 GHz candidate in NL018. Two positive controls: 42 ps LO2/3 mW 120 GHz frozen ordinary Ridge16; include original seven methods at each control. Both controls must pass both drives in both panels before promotion. Report primary and every supporting endpoint independently; if primary fails, report failure explicitly, no substitution or repeat-until-pass. Even if supporting endpoints pass, do not promote primary cadence claim in this protocol. If primary passes both independent panels and both controls pass, report new numerical confirmation 24.3902439024 Gsymbol/s under these model assumptions, explicitly preserve NL016 failure and finite-panel limitation. Otherwise confirmed baseline 23.8095238095 Gsymbol/s remains. No new physical claims.

## Frozen coefficients

| ps | LO mW | GHz | NL017 record name | SHA-256 |
|---:|---:|---:|---|---|
| 42 | 2 | 120 | ridge8 | d1ec822076cdf6f244270482226b9dd5b1fe3ced04dc73c154a8d16bb63c72a2 |
| 42 | 2 | 120 | ridge16 | b8d9df37a73688d153ba724dc1768aa83171be426f468aa4643f276a1654cba7 |
| 42 | 2 | 120 | ridge16_strong | 3a5d95a7fe8b123ea863ebe2e7e619163706283353949a06f8477740c51201a1 |
| 42 | 3 | 120 | ridge8 | a9cfe09852a7c78536690183bd151809a0d9a923386fe93c79be80722a4274b6 |
| 42 | 3 | 120 | ridge16 | 7c05c69ac3e19e7486aaebe801d3e08bcb64299a6605a18c2e771145c5916174 |
| 42 | 3 | 120 | ridge16_strong | 64616dc6c2b2ca901fb46562b7edbc86841f5304452de742ea60f0397629d7aa |
| 41 | 3 | 80 | frozen_ridge16 | 601beea1759c1d60d761be880cde11c30cb6db2603ec2ade67c10ec881a59430 |
| 41 | 3 | 80 | frozen_ridge16_midlow | 1ccfbaa45af3fb4aea0effb527a8c834e5e3a1b6b190d84a1dd8116034c26c9b |
| 41 | 3 | 80 | ridge16 | fdeef8acb756cabab7a51b810bca05c1f9bcda13aef5d2fcf0e846032d015bd2 |
| 41 | 3 | 80 | ridge16_midlow | 85bfe077ef078c092d167d01de7da03fe6437e6c3471966bcf07e0411442ce7d |
| 41 | 3 | 80 | ridge24_midlow | 2cefade2cb63f46157250fb12323d142e64be4a7b1d8e28df850f549837b6397 |
| 41 | 3 | 80 | ridge32_midlow | 62b09935444429e7f7b64e66d38d221f28f5efa818159a62cf59ce218fd522fa |

All twelve vectors sourced from NL017 archive; frozen_ridge16 and frozen_ridge16_midlow additionally exactly match NL016 respective original names; six controls match NL014/NL015/NL016. Exact keys, tap counts, little-endian float64 byte digest, finite, read-only, persist before test generation; verify at every grid and unchanged archive hashes. No calibration, fit, threshold changes, labels for fitting, or candidate selection in NL018. Reuse NL017 causal features for 8/16/24/32 and inherited anchors; run deterministic feature/causality and numerical regressions but no actual coefficient fitting (synthetic fit regression may be omitted or isolated, never used for endpoints).

## Frozen simulation design

C2, zero gap, 5 ps response, unchanged five NL003 absorber weights seeds 1301..1305 at .1/1 mW, unchanged hybrid loss/phase, optical field noise and electrical PSD. Panel A domains 10604..10608, panel B 10614..10618, disjoint from all previous domains including NL017 10504..10508 and 10514..10518. Same paired draws across receiver settings/readouts/grids within panel, independent streams and repeats, 2048 balanced examples per seed/drive/panel (eight streams x256), eight noise repetitions, no startup exclusion. Same 95% unfiltered/clean/combined worst-repeat gates, stationary eligibility, sampled diode cap 2 mW, three aligned resolutions finest <=.0625 ps, middle/fine electrical and combined gate agreement. Same inherited tolerances and checks including archive audit, optical balance, causal history, convergence, exact paired marginals and coefficient immutability.

## Counts and reporting

Settings exactly (41,3,80), (42,2,120), (42,3,120). Candidate ten methods (four anchors + six frozen ridge methods); controls seven each. 24 method/settings x two panels x two drives x five seeds = 480 primary rows, 1440 resolution rows, 96 primary groups, 288 resolution groups, 24 two-panel/both-drive tuples, 12 coefficient records, 12 optical audits, eight convergence comparisons. Candidate pair comparisons six ridge methods x four anchors =24, plus six matched comparisons: frozen_ridge16_midlow vs frozen_ridge16; ridge16 vs frozen_ridge16; ridge16_midlow vs frozen_ridge16_midlow; ridge24_midlow vs ridge16_midlow; ridge32_midlow vs ridge16_midlow; ridge32_midlow vs ridge24_midlow. Controls each original 13 pairs. Total (30+26)*2 panels*10 seed-drive*8 repeats=8960 paired rows, 224 panel-specific paired summaries (each 81920 decisions). Report per panel all four drive-panel minima, all gates, first/last eight, noise decomposition, lag norms, exact paired counts, failure reasons, primary/supporting and controls separately. All 24 tuples retained. No aggregate averaging to conceal a failed panel. Feature rate at 41 ps 195.1219512195 Gsegment/s, not physical ADC feasibility. Model-based estimates — not experimentally validated; no physical BER, wall-plug power, hardware throughput or general AI accuracy claim.

## Executed results — 2026-11-18

[Successful run 44387159815](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44387159815), job 135094871000, source head 3695dcc663f08fe6a7d04def6735b383fe2aab06, CI merge 4ca87bc2fef0e2f0fe600513d8bf8ce11186fd80, final merge bf16e0daa3760df2473ab42730b32442c5120520. All 27 implementation checks passed, including corrected full NL017 archive audit, causal regression, immutable vectors, matched marginal counts, endpoint coverage and numerical convergence. 480 primary rows, 1440 resolution rows, 96 groups, 288 resolution groups, 24 two-panel tuples, 12 coefficient records, 8960 paired rows, 224 panel-specific summaries, 12 optical audits and 8 convergence comparisons. Runtime 632.875267275 s. 36/96 passing groups, 0/24 two-panel/both-drive tuples, zero ambiguous groups, zero changed group or seed gates across all eight comparisons. A successful implementation run is not a positive scientific outcome.

### Primary and control outcomes

Frozen Ridge16 Midlow 41 ps/3 mW/80 GHz: A low .94677734375 (1939/2048, seven short), high .9921875; B low .94189453125 (1929/2048, seventeen short), high .99560546875. Both low-drive panels fail, both high-drive panels pass. The same frozen vector passed only NL017 among NL016, NL017 and both NL018 panels. No independent confirmation of 24.3902439024 Gsymbol/s. No supporting endpoint passes both panels/drives; all five fail both low-drive panels. Ridge24 Midlow has best low-drive minima of the six ridge methods in both panels (.94921875 and .943359375), still fails; no replacement of primary permitted.

Both positive controls pass panel A both drives and panel B high drive but fail panel B low drive. At 42 ps/2 mW/120 GHz ordinary Ridge16 A low .95458984375 (1955/2048), B low .947265625 (1940/2048, six short); at LO3 A low .9560546875 (1958/2048), B low .9482421875 (1942/2048, four short). Thus control comparability gate fails. Preserve historical NL015 independent confirmation at 23.8095238095 Gsymbol/s under its prespecified panels, but now explicitly qualify that it did not generalize to all new NL018 panels. No universally robust 42 ps claim, no invalidation of the historical archived run, no promotion, no rerunning until pass. This result is evidence of sensitivity to new input/noise realizations and motivates margin-oriented receiver investigation. Raw seed-level inspection needed to distinguish clean reconstruction, electrical noise, optical noise, sampled peaks and panel/seed effects; do not infer a noise mechanism solely from aggregate gate failures.

### All 24 two-panel tuples

| ps | LO mW | GHz | method | A low | A high | B low | B high | all gates |
|---:|---:|---:|---|---:|---:|---:|---:|---|
| 41 | 3 | 80 | end | 0.9033203125 | 0.9775390625 | 0.91015625 | 0.9794921875 | fail |
| 41 | 3 | 80 | eighth_mean | 0.9208984375 | 0.92724609375 | 0.92041015625 | 0.93798828125 | fail |
| 41 | 3 | 80 | quarter_mean | 0.892578125 | 0.82373046875 | 0.89697265625 | 0.841796875 | fail |
| 41 | 3 | 80 | half_mean | 0.7939453125 | 0.65771484375 | 0.7998046875 | 0.65380859375 | fail |
| 41 | 3 | 80 | frozen_ridge16 | 0.9462890625 | 0.99072265625 | 0.93994140625 | 0.9931640625 | fail |
| 41 | 3 | 80 | frozen_ridge16_midlow | 0.94677734375 | 0.9921875 | 0.94189453125 | 0.99560546875 | fail |
| 41 | 3 | 80 | ridge16 | 0.94677734375 | 0.99072265625 | 0.93896484375 | 0.994140625 | fail |
| 41 | 3 | 80 | ridge16_midlow | 0.94873046875 | 0.99169921875 | 0.94189453125 | 0.99560546875 | fail |
| 41 | 3 | 80 | ridge24_midlow | 0.94921875 | 0.99169921875 | 0.943359375 | 0.9951171875 | fail |
| 41 | 3 | 80 | ridge32_midlow | 0.94873046875 | 0.99169921875 | 0.94287109375 | 0.9951171875 | fail |
| 42 | 2 | 120 | end | 0.8896484375 | 0.990234375 | 0.896484375 | 0.9921875 | fail |
| 42 | 2 | 120 | eighth_mean | 0.92578125 | 0.96337890625 | 0.93017578125 | 0.97119140625 | fail |
| 42 | 2 | 120 | quarter_mean | 0.916015625 | 0.88623046875 | 0.9150390625 | 0.89892578125 | fail |
| 42 | 2 | 120 | half_mean | 0.8291015625 | 0.7080078125 | 0.82861328125 | 0.69921875 | fail |
| 42 | 2 | 120 | ridge8 | 0.94775390625 | 0.99609375 | 0.94384765625 | 0.998046875 | fail |
| 42 | 2 | 120 | ridge16 | 0.95458984375 | 0.99560546875 | 0.947265625 | 0.99755859375 | fail |
| 42 | 2 | 120 | ridge16_strong | 0.9365234375 | 0.984375 | 0.9365234375 | 0.98974609375 | fail |
| 42 | 3 | 120 | end | 0.89111328125 | 0.990234375 | 0.8974609375 | 0.9921875 | fail |
| 42 | 3 | 120 | eighth_mean | 0.927734375 | 0.9638671875 | 0.9326171875 | 0.97119140625 | fail |
| 42 | 3 | 120 | quarter_mean | 0.916015625 | 0.88671875 | 0.9169921875 | 0.8984375 | fail |
| 42 | 3 | 120 | half_mean | 0.828125 | 0.70751953125 | 0.828125 | 0.69970703125 | fail |
| 42 | 3 | 120 | ridge8 | 0.9482421875 | 0.99609375 | 0.9443359375 | 0.998046875 | fail |
| 42 | 3 | 120 | ridge16 | 0.9560546875 | 0.99560546875 | 0.9482421875 | 0.99755859375 | fail |
| 42 | 3 | 120 | ridge16_strong | 0.9365234375 | 0.98486328125 | 0.93701171875 | 0.98974609375 | fail |

### Matched comparisons

Each row contains 81920 matched repeated decisions within one panel and drive. Net is equalizer-only minus anchor-only; descriptive counts, not independent observations. Extended-history net ranges -14 to 13, max absolute 14 (0.01708984375 percentage points). Ridge24 Midlow gains 11 and 7 low-drive decisions versus matched Ridge16 Midlow in A/B; Ridge32 Midlow +13/-7. Frozen Midlow vs ordinary Ridge16 loses 14/23 low-drive aggregate decisions but gains 22/27 at high drive; better worst-case margin is not the same as better aggregate accuracy. Refreshed calibration vectors (frozen before NL018) gain 1 to 20 decisions across all eight comparisons, insufficient to restore gates. No substantial or consistent extended-history rescue.

| comparison class | panel | drive mW | method | anchor | equalizer-only | anchor-only | net |
|---|---|---:|---|---|---:|---:|---:|
| history | A | 0.1 | ridge24_midlow | ridge16_midlow | 64 | 53 | 11 |
| history | A | 0.1 | ridge32_midlow | ridge16_midlow | 86 | 73 | 13 |
| history | A | 0.1 | ridge32_midlow | ridge24_midlow | 38 | 36 | 2 |
| history | A | 1 | ridge24_midlow | ridge16_midlow | 5 | 6 | -1 |
| history | A | 1 | ridge32_midlow | ridge16_midlow | 6 | 6 | 0 |
| history | A | 1 | ridge32_midlow | ridge24_midlow | 1 | 0 | 1 |
| history | B | 0.1 | ridge24_midlow | ridge16_midlow | 59 | 52 | 7 |
| history | B | 0.1 | ridge32_midlow | ridge16_midlow | 56 | 63 | -7 |
| history | B | 0.1 | ridge32_midlow | ridge24_midlow | 24 | 38 | -14 |
| history | B | 1 | ridge24_midlow | ridge16_midlow | 2 | 2 | 0 |
| history | B | 1 | ridge32_midlow | ridge16_midlow | 2 | 3 | -1 |
| history | B | 1 | ridge32_midlow | ridge24_midlow | 0 | 1 | -1 |
| regularization | A | 0.1 | frozen_ridge16_midlow | frozen_ridge16 | 217 | 231 | -14 |
| regularization | A | 1 | frozen_ridge16_midlow | frozen_ridge16 | 23 | 1 | 22 |
| regularization | B | 0.1 | frozen_ridge16_midlow | frozen_ridge16 | 216 | 239 | -23 |
| regularization | B | 1 | frozen_ridge16_midlow | frozen_ridge16 | 27 | 0 | 27 |
| recalibration | A | 0.1 | ridge16 | frozen_ridge16 | 26 | 15 | 11 |
| recalibration | A | 0.1 | ridge16_midlow | frozen_ridge16_midlow | 59 | 46 | 13 |
| recalibration | A | 1 | ridge16 | frozen_ridge16 | 4 | 0 | 4 |
| recalibration | A | 1 | ridge16_midlow | frozen_ridge16_midlow | 5 | 1 | 4 |
| recalibration | B | 0.1 | ridge16 | frozen_ridge16 | 36 | 25 | 11 |
| recalibration | B | 0.1 | ridge16_midlow | frozen_ridge16_midlow | 57 | 37 | 20 |
| recalibration | B | 1 | ridge16 | frozen_ridge16 | 6 | 0 | 6 |
| recalibration | B | 1 | ridge16_midlow | frozen_ridge16_midlow | 3 | 2 | 1 |

### Numerical checks and limitations

Maximum field error 3.155498361620598e-10 sqrt(mW), waveform error 3.293827741600215e-9 sqrt(mW), clean current 2.2451061796875497e-8 A, noisy current 2.245704031517441e-8 A, sampled peak 0.000001425337539551208 mW. All within inherited tolerances. No grid-gate changes. Hypothetical model only; no measured hardware throughput, BER, ADC feasibility, general AI performance or wall-plug power.

### Archive and next decision

Artifact 14467183137, ZIP 344108 bytes, SHA-256 5056ec8c3e7ffb398184c320b653ca4c4c200510fac76c58d9eb8f2f2ec9276d. Manual archive workflow verifies source identity, CRC, all fifteen original hashes and staged bytes; negative outcomes are explicitly pinned. After merge of exact archive, audit all 8960 paired rows, inspect limiting seeds/repeats and compare noise decomposition across NL016–NL018, including both failed controls. Next research direction is a separately preregistered exploratory noise-aware receiver calibration objective with a robustness margin, not merely longer history or rerunning the same failed confirmation. Fix the objective, noise assumptions, settings, controls, thresholds and disjoint calibration/test domains before execution. Evaluate 42 ps robustness before pursuing 41/40 ps promotion; no changes to the 95% quality gate, no fitting on any previous test data or labels. Specific design to follow raw audit.
