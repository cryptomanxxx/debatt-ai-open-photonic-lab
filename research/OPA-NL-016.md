# OPA-NL-016 — Exploratory 41 and 40 ps finite-response sweep

Status: executed; 40 and 41 ps failed all common-drive gates; both frozen 42 ps Ridge16 controls passed. Exact archive pending.
Basis: [OPA-NL-015](OPA-NL-015.md), archived source run 44321189432, archive merge 9de7408bf32a8f332c7dbdb0b22ffc0b64cb16b2.

## Archived raw-data diagnosis

Fetched the full primary and resolution CSVs and paired raw CSV using Git blob retrieval. Independently checked all 14560 paired contingency rows for unique keys, 2048 total decisions and both marginals against the 980 primary seed rows. Recomputed 364 paired summaries; checked 2940 resolution seed rows, 588 resolution groups, 196 primary groups, 49 two-panel tuples, coefficient links, repeat minima, seed/group gates and middle/fine agreement. All passed. Reproducible Python audit in research/analyze_nl015.py must execute successfully before NL016 test generation; this new Python script itself has not yet been executed.

At 42 ps/2 mW LO/120 GHz/0.1 mW drive, panel A seed 1304 Ridge8 repeat counts 1979,1974,1962,1968,1958,1942,1968,1961; Ridge16 1985,1982,1973,1975,1966,1947,1979,1973. Repeat index 5 is limiting: 1942 vs 1947 with threshold 1946. Both clean accuracies 1, electrical-only worst .9697265625/.97412109375. Same model weights and matched draws. Both panels at this setting Ridge8 vs end: net 8047 of 163840 repeated matched decisions (+4.9114990234375 pp); Ridge16 vs end net 8489 (+5.1812744140625 pp); Ridge16 vs Ridge8 net 442 (+.269775390625 pp), from 709 equalizer-only and 267 anchor-only. Repeated decisions are not independent statistical samples.

At the same setting, low-drive across ten panel/seed rows mean electrical variance ratio relative to end: Ridge8 .3636261808737231, Ridge16 .36623567259241385, strong .25892936482265616. Mean clean target RMSE A: 1.3002394546727771e-6, 1.2317714470209858e-6, 3.05660210709693e-6. Worst combined .9482421875, .95068359375, .93701171875, respectively; clean minima 1,1,.990234375. Stronger regularization reduces variance but worsens signal reconstruction and decisions. 3 mW LO Ridge16 improves worst to .9521484375, modest gain at additional conditional LO electrical lower bound 5 mW (20% assumed conversion). Mean signal-plus-LO lower bound at low drive 11.514895220511395 mW for LO2 vs 16.514895220511395 for LO3; not total receiver or measured wall-plug power. At 42 ps, max optical memory field .004173670304344526 sqrt(mW) at low drive; cannot infer memory is absent from perfect clean classification. Seed 1304 is diagnostic, never use test labels or data for fitting.

## Hypotheses and fixed sweep

H1: with 5 ps material response, zero gap, Ridge16 can reach 41 ps (24.3902439024 Gsymbol/s) and possibly 40 ps (25 Gsymbol/s) on new exploratory inputs. H2: intermediate regularization between ordinary .01 and strong .1 can improve the current-reconstruction/noise tradeoff. H3: modestly wider modeled electrical bandwidth can improve recovery but may increase noise and cannot imply physical receiver feasibility.

New settings: Cartesian product on_ps in (40,41), LO mW in (2,3), fc GHz in (80,120,160), giving 12 settings. Frozen 42 ps/2 mW/120 GHz positive control plus 42 ps/3 mW/120 GHz frozen margin control; preserve both from NL015. At new settings fit exactly 5 causal equalizers using original NL012 pooled combined-current target (no labels): ridge8 (.01), ridge16 (.01), ridge16_strong (.1), ridge16_midlow (.003), ridge16_mid (.03). .003 is a weaker regularizer, .03 intermediate; naming is relative to .01 baseline. Keep 4 anchors end/eighth/quarter/half, for nine readouts at every new setting. At controls use original seven readouts only; no new fitting at 42 ps, no transfer of new coefficients to controls. Compare new .003/.03 against ordinary ridge16 and anchors; no test-based refit or selection of lambda. 160 GHz is a hypothetical model parameter; no ADC/bandwidth feasibility claim. Keep 2 mW sampled diode cap, no LO beyond 3 mW. C2, same frozen NL003 weights, five seeds 1301..1305 each .1/1 mW, unchanged response and PSD, optical loss/phase, no changes to physics. No 39 ps or faster trial.

## Frozen controls

| ps | LO | GHz | method | SHA-256 |
|---:|---:|---:|---|---|
| 42 | 2 | 120 | ridge8 | d1ec822076cdf6f244270482226b9dd5b1fe3ced04dc73c154a8d16bb63c72a2 |
| 42 | 2 | 120 | ridge16 | b8d9df37a73688d153ba724dc1768aa83171be426f468aa4643f276a1654cba7 |
| 42 | 2 | 120 | ridge16_strong | 3a5d95a7fe8b123ea863ebe2e7e619163706283353949a06f8477740c51201a1 |
| 42 | 3 | 120 | ridge8 | a9cfe09852a7c78536690183bd151809a0d9a923386fe93c79be80722a4274b6 |
| 42 | 3 | 120 | ridge16 | 7c05c69ac3e19e7486aaebe801d3e08bcb64299a6605a18c2e771145c5916174 |
| 42 | 3 | 120 | ridge16_strong | 64616dc6c2b2ca901fb46562b7edbc86841f5304452de742ea60f0397629d7aa |

Check exact archive identity, vector key/length/finite values and SHA-256, read-only float64, same vectors at each grid, matching NL014/NL015. Both ordinary Ridge16 frozen controls must pass on fresh exploratory panel before promoting any candidate to a later confirmation proposal. Ridge8 control at 42 ps is a negative/mixed comparator, not a required positive control.

## Calibration, test, gates and counts

Calibration domains 10404..10408, 512 examples per weight, eight streams of 64 and eight repeats; test domains 10414..10418, 2048 examples per weight, eight streams of 256 and eight repeats. Audit disjointness against every prior domain, including NL015 A/B 10304..10308 and 10314..10318; same underlying draws across settings/grid and arms in each partition. Fit at finest aligned grid once, save immutable coefficient artifact before any exploratory test generation. Same 10 weights per partition; no new training. Use unchanged 95% thresholds (1946/2048 minimum per combined repeat), stationary eligibility, unfiltered and clean thresholds, diode limit, three aligned grids with finest <=.0625 ps, middle/fine electrical and combined group agreement, inherited numerical tolerances. No relaxed gates, discarded startup, post-hoc retuning, physical hardware claim.

Expected 122 readout-setting combinations (12*9+2*7), 1220 primary seed rows, 244 primary groups, 122 common-drive tuples, 3660 resolution seed rows, 732 resolution groups, 66 coefficient records (60 newly fit, six frozen), nine timing-level optical audits and six convergence comparisons. Paired comparisons: each new setting has five ridge methods vs four anchors (20) plus ridge16 vs ridge8 (1) and two new ridge variants vs ridge16 (2), total 23; each control retains original 13 pairs. Thus (12*23+2*13)*10*8=24160 paired rows and 604 paired summary records. Verify exact key sets, both marginals, summary counts, coefficient hashes, archive immutability, inherited causal/energy/hybrid/partition/stationary tests. Report failure reasons, all seed/group gate changes, startup/last-eight, optical memory, clean RMSE, relative noise variance, sampled peak and conditional laser lower bound. Report paired improvements descriptively, not significance. Scientific failure is not implementation failure. Include every result, even failed controls and candidates.

## Decision

If a candidate at 40 or 41 ps passes all numerical gates and both frozen Ridge16 controls pass, label it exploratory and preregister independent confirmation with new domains and immutable coefficients before any new speed claim. Select by faster cadence first, then lower LO, then lower cutoff, then simpler readout/taps; report margin and all passing alternatives. A marginal pass is not proof of robust hardware operation. If both timings fail, inspect clean/optical and combined-noise failure mechanisms and consider a different causal receiver architecture; do not simply lower threshold or keep tuning on exploratory labels. If control fails, report comparability failure and do not promote. Confirmed baseline remains 23.8095238095 Gsymbol/s. 40 ps implies aggregate 200 Gsegment/s eight-segment feature rate, not measured ADC capability. No measured energy, BER, general AI accuracy or hardware throughput claim.

## Executed results — 2026-11-18

[Successful run 44334443261](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44334443261), job 134907416490, source head 2fb0289227c2fbc5896d1b25762fd20f2f1af38d, CI merge 4ce7f78b488a067128f9696a35f5cc4242d39aee, final merge 7c68af667245631c9d1ecd3d384af9f2d6ac8113. All 25 implementation checks passed, including the mandatory full NL015 archive audit, coefficient links, paired marginals and summary counts, frozen archive integrity and numerical regressions. 1220 primary rows, 3660 resolution seed rows, 244 primary groups, 732 resolution groups, 122 common-drive tuples, 66 coefficient records, 24160 paired rows, 604 paired summaries, nine optical audits and six convergence comparisons. Runtime 560.89905126 s. 88/244 passing groups, only 2/122 common-drive tuples (both controls); zero ambiguous groups and zero seed/group gate changes across all six comparisons. No candidate proposed for confirmation.

### Scientific outcomes

40 ps (25 Gsymbol/s): 0/54 common-drive passes. Best Ridge16 Midlow, LO3 mW, 120 GHz, low .94189453125 (1929/2048; 17 below threshold), high .98828125. 41 ps (24.3902439024 Gsymbol/s): 0/54 common-drive passes. Best Ridge16 Midlow, LO3 mW, 80 and 120 GHz tie at low .9482421875 (1942/2048; four below threshold); high .99365234375 and .99462890625 respectively. The confirmed 42 ps references pass: LO2/120 GHz Ridge16 low .95068359375 (1947/2048), high .99755859375; LO3/120 GHz Ridge16 low .95263671875 (1951/2048), high .99755859375. Both ordinary Ridge8 controls fail low drive as expected from NL015. No new confirmed cadence; baseline remains 23.8095238095 Gsymbol/s. Green CI is not a scientific pass.

### Best result by method at each exploratory timing

| ps | readout | LO mW | GHz | low | high | maximin |
|---:|---|---:|---:|---:|---:|---:|
| 40 | ridge8 | 3 | 160 | 0.9365234375 | 0.986328125 | 0.9365234375 |
| 40 | ridge16 | 3 | 160 | 0.94091796875 | 0.986328125 | 0.94091796875 |
| 40 | ridge16_midlow | 3 | 120 | 0.94189453125 | 0.98828125 | 0.94189453125 |
| 40 | ridge16_mid | 3 | 120 | 0.9345703125 | 0.982421875 | 0.9345703125 |
| 40 | ridge16_strong | 3 | 160 | 0.92333984375 | 0.96826171875 | 0.92333984375 |
| 41 | ridge8 | 3 | 120 | 0.94189453125 | 0.99267578125 | 0.94189453125 |
| 41 | ridge16 | 3 | 80 | 0.94677734375 | 0.99267578125 | 0.94677734375 |
| 41 | ridge16_midlow | 3 | 80 | 0.9482421875 | 0.99365234375 | 0.9482421875 |
| 41 | ridge16_mid | 3 | 120 | 0.943359375 | 0.9912109375 | 0.943359375 |
| 41 | ridge16_strong | 3 | 160 | 0.9306640625 | 0.98193359375 | 0.9306640625 |

Midlow (.003) improves best observed maximin over ordinary Ridge16 (.01) by .0009765625 at 40 ps and .00146484375 at 41 ps; these are best-over-setting descriptive comparisons, not a matched causal estimate of changing lambda. Mid (.03) and Strong (.1) underperform ordinary Ridge16 on this criterion. No variant passes. At 41 ps, Midlow LO3 at 80/120 GHz ties in worst low-drive count; 160 GHz is slightly worse. At 40 ps 120 GHz outperforms 80/160 GHz in best maximin. H1 not supported at threshold; H2 weaker regularization looks promising but not sufficient, intermediate .03 not an improvement in best maximin; H3 no evidence that 160 GHz solves the gate. Full paired comparisons, seed-level clean/noise/optical memory and matched regularization diagnosis must follow archive merge; do not infer specific causation from aggregate winners.

### Best result by cutoff

| ps | GHz | best method | LO mW | maximin |
|---:|---:|---|---:|---:|
| 40 | 80 | ridge16_midlow | 3 | 0.939453125 |
| 40 | 120 | ridge16_midlow | 3 | 0.94189453125 |
| 40 | 160 | ridge16 | 3 | 0.94091796875 |
| 41 | 80 | ridge16_midlow | 3 | 0.9482421875 |
| 41 | 120 | ridge16_midlow | 3 | 0.9482421875 |
| 41 | 160 | ridge16_midlow | 3 | 0.94775390625 |

### Convergence and scope

Maximum field error 3.8926947290475945e-10 sqrt(mW), waveform 3.2543464668535975e-9 sqrt(mW), clean current 3.317732073988312e-8 A, noisy current 3.318469559912421e-8 A, sampled peak 0.000001689466457177602 mW. All within preregistered tolerances. Neither gate disagreement nor failed control explains the scientific failure. Results are finite-panel simulations with hypothetical receiver PSD and fixed weights, not physical throughput, BER, ADC feasibility, wall-plug power or general AI accuracy.

### Archive and next research decision

Original artifact 14441791865, ZIP 842705 bytes, SHA-256 3651a19dec08defbed0e1a5a3f47e821ebd9917482dfd235b9cceae33bfb5d6b. Manual workflow verifies all fifteen original files, CRC, source identity and staged bytes. No independent confirmation experiment for failed candidates. After archiving, audit the full raw rows and diagnose clean/unfiltered vs electrical/combined failures, per-seed and per-repeat margins, coefficient norms and paired effects. Consider a separately preregistered causal receiver redesign (e.g. additional temporal history or a noise-aware objective), while retaining frozen controls, same 5 ps response, same power limits and 95% thresholds; do not optimize repeatedly on NL016 test labels. Choice of architecture contingent on raw analysis, not yet preregistered.
