# OPA-NL-018 — Independent frozen-coefficient confirmation at 41 ps

Status: proposed protocol; no NL018 test inputs generated or simulations run.
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
