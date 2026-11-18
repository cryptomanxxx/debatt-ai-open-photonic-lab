# OPA-NL-014 — Exploratory finite-response cadence boundary

Status: implemented and executed; initial report analysis complete, exact archive pending.
Basis: [NL013](OPA-NL-013.md), archived run 44304216745, archive merge 7e58791b33d78f12e2fbe83eb017e2630441af97.

## NL013 raw-data diagnosis

Read all 420 primary seed rows, 1260 resolution seed rows, 84 groups and 6240 paired rows from the archive. All 6240 unique paired keys and both correctness marginals match the primary seed repeat counts, each contingency totals 2048. The analysis below is descriptive; repeats reuse input examples and weights. A reproducible audit is provided in research/analyze_nl013.py and must execute before NL014.

At 45 ps, 5 ps material response, 1 mW LO, 60 GHz, low drive, across both panels and five seeds (80 repeat rows per comparison, 163840 decisions):
 
| Comparison | Both correct | Equalizer only | Anchor only | Neither | Net correct | Mean accuracy gain pp |
|---|---:|---:|---:|---:|---:|---:|
| Ridge8 vs end | 153669 | 5927 | 2046 | 2198 | 3881 | 2.3687744140625 |
| Ridge16 vs end | 153840 | 6069 | 1875 | 2056 | 4194 | 2.559814453125 |
| Ridge16 vs Ridge8 | 159442 | 467 | 154 | 3777 | 313 | 0.1910400390625 |

Low-drive worst repeat across both panels: end .92724609375, eighth .9375, Ridge8 .95654296875, Ridge16 .9599609375, strong .9384765625. All have clean accuracy 1 except strong (.9951171875). Electrical-only minima: .94482421875, .96142578125, .97412109375, .9755859375, .95654296875 respectively. Thus noise and readout distortion both matter; strong regularization lowers variance but fails combined gate. Mean seed-level electrical noise variance ratio relative to same end readout: eighth .5533426257, Ridge8 .6324931956, Ridge16 .6374316627, strong .4523543037. Ridge8 range .6195439374–.6486415296. At 50 ps/20 GHz/1 mW LO, low drive Ridge8 variance ratio rises to 1.4577489510 while classification improves vs end; variance ratio is not SNR or an energy metric.

At 45 ps/1 mW LO, low-drive sampled combined diode peak max .5286664048 mW; high drive .6211369204 mW. At 2 mW LO maxima 1.0403566774 and 1.1669824241 mW. Conditional average seed-level laser electric lower bounds (20% efficiency): low/high 6.5124404971/20.1244049707 mW at LO 1 mW and 11.5124404971/25.1244049707 mW at LO 2 mW. These exclude receiver and other system power. Ridge8 first/last-eight mean-accuracy minima .947265625/.951171875 at low drive; these are descriptive subwindows, not the preregistered full-stream gate. No dropped startup symbols.

## Scientific question

Determine whether 44, 43 or 42 ps zero-gap symbols with 5 ps response can pass the inherited combined-noise quality gate, and distinguish receiver bandwidth/noise effects from optical memory. 45 ps is the confirmed reference, not a newly optimized endpoint. 40 ps remains outside this sweep; NL012 at 40/5 did not reach the common-drive threshold even with equalization. Do not extrapolate to 25 Gsymbol/s.

## Prespecified exploratory grid

C2 only, unchanged NL003 absorber weights (seeds 1301–1305 for each drive .1/1 mW), unchanged optical loss, phase, nonlinear dynamics, receiver PSD, cap and stationary conditions. All candidate durations 42,43,44 ps at response 5 ps, zero gap; LO 1,2,3 mW; cutoff 40,60,80,120 GHz. All seven NL012 readouts: end, eighth, quarter, half, Ridge8 (.01), Ridge16 (.01), Ridge16 strong (.1). Prioritize Ridge8 at 1 mW, then Ridge16 at 1 mW; higher LO references test noise margin, not automatic superiority. No retuning penalty, thresholds, feature definitions or optical weights after data generation. Full factorial candidate settings = 36 receiver tuples. One additional 45 ps/1 mW/60 GHz control with all seven methods and exact frozen NL013/NL012 coefficients, no refit of control. Candidate coefficients trained only on independent calibration streams at finest grid using original NL012 current-target fitting (not class labels); pooled five seeds and both drives, eight combined repeats, 512 examples per seed/drive. Freeze and hash all 108 new coefficient vectors before candidate test; three archived control vectors, read-only, exact hashes from NL013. Use identical calibration domains across candidate settings, independent from tests. No fitting on test data or selection of calibration examples. No hardware claim.

Calibration domains 10204–10208; exploratory test domains 10214–10218, subject to audit against all earlier RNG call sites and seed domains. Same five domains per setting and all three resolutions, independent streams/repeats, common underlying draws for matched conditions. Test 2048 balanced examples per seed/drive, eight streams of 256 symbols, eight noise repeats, same ordering across all settings including control. One exploratory test panel only; do not call a passing candidate independently confirmed. A later preregistered frozen-coefficient experiment must use new domains and at least two panels. Do not reuse NL013 panels or candidate calibration data.

## Exact planned counts

37 receiver settings x 7 methods x 2 drives x 5 seeds = 2590 finest seed rows, 518 primary groups, 259 common-drive tuples. Three aligned grids yield 7770 resolution seed rows and 1554 resolution groups. 111 coefficient records (108 fitted, 3 archived); 37 x (3 x 4 + 1) x 10 x 8 = 38480 finest paired rows, including Ridge16 vs Ridge8. Four timing-level optical audit sets x 3 grids = 12 audits; 8 convergence comparisons. Candidate calibration only, no control refit. Pilot estimate runtime/memory and maintain 180-minute CI budget; split by timing if necessary without changing grid, frozen coefficients or test domains. Preserve full provenance.

## Gates, analysis and next decision

Retain NL013 stationary eligibility, unfiltered and clean >=.95, every combined repeat >=.95 (1946 of 2048), peak sampled diode <=2 mW, all five seeds per drive, agreement of middle/fine group gates for combined and electrical arms. Numerical tolerances identical to NL012/013, record all group/seed disagreements. Audit exact paired counts and marginals, causal segment features, archive identity/immutability, fixed coefficient digests, optical conservation, hybrid and stationary noise identities, finite outputs, exact keys and complete grid. Scientific failures are valid results, not implementation failures. Report clean/electrical/combined failure attribution per seed/group, first/last-eight metrics, conditional laser power, noise variance ratios, coefficient norms, clean target RMSE and exact paired gains. Record sampled optical memory and diode peak; no claim of continuous-time peak bound. Include all failures; no significance claim for repeated decisions. Aggregate segment rate at 44/43/42 ps is 181.818/186.047/190.476 Gsegment/s respectively, with 8 or 16 weighted terms. Model does not establish implementation bandwidth, ADC feasibility, BER, AI throughput, total energy, or physical hardware performance.

Ranking fixed before execution: report fastest passing common-drive timing; within each timing list all passing settings, Pareto compare optical LO power and worst-repeat accuracy separately by method, with lower-complexity Ridge8 preferred at matched LO if both pass. Bandwidth and total receiver cost remain unmodeled; do not claim an energy optimum. If no 42–44 ps passes, report boundary failure and examine optical margin/noise redesign rather than retrying the same test panel. If control fails, flag comparability and do not promote candidate results to a confirmed advance. If any candidate passes, preregister an independent frozen-coefficient test before asserting new confirmed cadence. 

## Executed results — 2026-11-18

[Successful run 44311554574](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44311554574), job 134826805814, source head ff5c11607025c403b542a0b5b7d1ccd6a73235a0, CI merge c44d7d518dcc334182e776207f7cf8d84f1a6aab, final merge 636719d5e3bee326d0d6f2e9e3eb1830d495d304. All 24 implementation checks passed, including mandatory complete NL013 audit, frozen-file integrity, exact seed and paired keys/marginals and unchanged archived evidence. Report verifies 2590 primary rows, 7770 resolution rows, 518 primary groups, 1554 resolution groups, 259 common-drive pairs, 111 coefficient records, 38480 paired rows, 12 optical audits and 8 convergence comparisons. Elapsed 823.064710146 seconds. 238/518 combined passing groups, 62/259 common-drive tuples (60 new candidates + two frozen controls), no ambiguous groups. Zero seed or group gate changes in all eight convergence comparisons. No change to the underlying optical model or gates.

### Prespecified sweep outcomes

| Symbol ps | Gsymbol/s | Passing common-drive tuples | Best maximin | Best setting |
|---:|---:|---:|---:|---|
| 42 | 23.80952 | 12/84 | 0.96044921875 | ridge16, LO 3 mW, 120 GHz |
| 43 | 23.25581 | 22/84 | 0.96435546875 | ridge16, LO 3 mW, 120 GHz |
| 44 | 22.72727 | 26/84 | 0.96826171875 | ridge16, LO 3 mW, 80 GHz |
| 45 | 22.22222 | 2/7 | 0.9658203125 | ridge16, LO 1 mW, 60 GHz |

Frozen 45 ps control passes both ordinary ridge methods (Ridge8 low/high .9619140625/1, Ridge16 .9658203125/1). Fastest passing exploratory cadence 23.8095238095 Gsymbol/s (42 ps, 7.142857% faster than 45 ps); all 12 passing settings shown below. These are single-panel exploratory passes, not independent confirmation.

| LO mW | Cutoff GHz | Readout | Worst low | Worst high |
|---:|---:|---|---:|---:|
| 1 | 120 | ridge16 | 0.9501953125 | 0.99609375 |
| 2 | 40 | ridge16 | 0.9501953125 | 0.99609375 |
| 2 | 60 | ridge16 | 0.953125 | 0.99609375 |
| 2 | 80 | ridge16 | 0.955078125 | 0.99609375 |
| 2 | 120 | ridge8 | 0.95361328125 | 0.9970703125 |
| 2 | 120 | ridge16 | 0.958984375 | 0.99609375 |
| 3 | 40 | ridge16 | 0.95068359375 | 0.99609375 |
| 3 | 60 | ridge16 | 0.955078125 | 0.99609375 |
| 3 | 80 | ridge8 | 0.951171875 | 0.99609375 |
| 3 | 80 | ridge16 | 0.955078125 | 0.99609375 |
| 3 | 120 | ridge8 | 0.9541015625 | 0.9970703125 |
| 3 | 120 | ridge16 | 0.96044921875 | 0.99609375 |

At 42 ps, the sole passing 1 mW LO setting is Ridge16/120 GHz (.9501953125, only 1946/2048 in the worst repeat: minimum passing integer count). Lowest-LO passing Ridge8 is 2 mW/120 GHz (.95361328125). At matched 2 mW/120 GHz, Ridge16 gives .958984375; at 2 mW/80 GHz it gives .955078125, useful bandwidth comparison. Increasing Ridge8 LO from 2 to 3 mW at 120 GHz improves maximin only .00048828125 (one decision of 2048); no inferential significance. Best 42 ps Ridge16 at 3 mW/120 GHz .96044921875. At 43 ps Ridge8/1 mW/120 GHz .95556640625; at 44 ps Ridge8/1 mW/80 GHz .9599609375, tied with 120 GHz. These lower-power alternatives merit consideration. Compare LO power and accuracy only; bandwidth and receiver implementation costs are not included in Pareto dominance. Full pair results retained in original artifact.

### Numerical checks and limitations

Maximum field error 3.13417662609896e-10 sqrt(mW), common-grid waveform error 3.2195978727973877e-9 sqrt(mW), clean current error 2.245725778978586e-8 A, noisy current error 2.246581502150487e-8 A, sampled peak error 0.0000011889235347339877 mW. All within inherited tolerances. No physical hardware validation, measured energy, general AI throughput or BER claim. 42 ps eight-segment receiver requires 190.476 Gsegment/s aggregate, a theoretical feature rate rather than measured ADC performance. LO-only electric lower bounds 5/10/15 mW under 20% assumed efficiency; no total system power claim. At 40 ps finite response NL012 failed common-drive gate; no extrapolation to 25 Gsymbol/s.

### Archive and next steps

Original artifact 14430539359, ZIP 1515177 bytes, SHA-256 4b0232f70758d1739776f70fcbf88c0934baf23b9d94cb8bfb47e1fcb3a24d4e. Manual workflow pins all fifteen original file hashes and staged bytes. Detailed per-seed and paired analysis follows archival. For NL015 propose preregistered independent frozen-coefficient confirmation with two new panels, prioritizing 42 ps/2 mW/120 GHz Ridge8 and Ridge16, 42 ps/1 mW/120 GHz Ridge16 (threshold-sensitive), lower-bandwidth 42 ps/2 mW/80 GHz Ridge16, 43 ps/1 mW/120 GHz Ridge8 and 45 ps frozen control. Final settings and exact pins must be specified after archive review, before generating new test data. Separate any future 41–40 ps exploration from confirmation.
