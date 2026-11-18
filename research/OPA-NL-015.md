# OPA-NL-015 — Independent frozen-coefficient confirmation at 42 ps

Status: preregistered proposal; no new simulations or test data generated.
Basis: [NL014](OPA-NL-014.md), run 44311554574, archive merge c027a1717add3d50c73f39654859dd1aacfb1999.

## Source review and diagnosis

All 962 paired summary records were inspected for totals (81920 matched decisions each), net counts and accuracy delta identity; all passed. Reviewed all 518 primary groups, 1554 resolution groups, 259 common-drive pairs and 111 coefficient records. The connector cannot return the three >1 MB raw CSV files; full raw-row verification must run in CI using research/analyze_nl014.py before any new test generation. Do not claim the 38480 raw rows were individually re-audited here.

At 42 ps/2 mW LO/120 GHz, low drive Ridge8 vs end: both correct 74136, equalizer only 5242, anchor only 1291, neither 1251, net +3951 (4.822998046875 pp). Ridge16 vs end net +4148 (5.0634765625 pp); Ridge16 vs Ridge8 both 79247, eq only 328, anchor only 131, neither 2214, net +197 (.240478515625 pp). At 1 mW Ridge8 vs end net +4482, Ridge16 vs Ridge8 +215; at 3 mW Ridge8 vs end +3881, Ridge16 vs Ridge8 +193. Descriptive repeated matched decisions, not independent samples.

42 ps/120 GHz Ridge8 low-drive electrical-only worst .96484375/.97265625/.97265625 at LO 1/2/3 mW; combined worst .94677734375/.95361328125/.9541015625; clean all 1. Ridge16 combined .9501953125/.958984375/.96044921875. At 2 mW/80 GHz Ridge8 .94970703125 (1945 correct, one below minimum passing count), Ridge16 .955078125. The primary low-drive difficulty is combined noise despite clean classification; this does not prove optical memory is absent. Sampled high-drive diode peak at 1/2/3 mW LO .6204389745/1.1660995608/1.7011361610 mW, below 2 mW cap; 3 mW leaves less headroom. No measured receiver or power. LO-only electrical lower bounds 5/10/15 mW at assumed 20% efficiency. At 42 ps/2 mW/120 GHz Ridge8/Ridge16 coefficient norms .913672905/.917073667, augmented condition 19.07178778/22.68991608, calibration RMSE 10.778994/10.624350 microA. These are calibration diagnostics, not measured ADC precision.

## Fixed endpoints and interpretation

Primary: 42 ps, 2 mW LO, 120 GHz, Ridge8 (NL014 .95361328125).
Secondary: same setting Ridge16 (.958984375).
Prespecified supporting endpoints: 42 ps/1 mW/120 GHz Ridge16 (minimum passing count .9501953125), 42 ps/2 mW/80 GHz Ridge16 (.955078125), 42 ps/3 mW/120 GHz Ridge16 (.96044921875) and Ridge8 (.9541015625), 43 ps/1 mW/120 GHz Ridge8 (.95556640625) and Ridge16 (.9580078125), 44 ps/1 mW/80 GHz Ridge8 (.9599609375) and Ridge16 (.96337890625). 45 ps/1 mW/60 GHz both ordinary ridge methods are frozen positive controls. Include all seven readouts at every setting, even previously failing anchors and comparators. Do not relabel an exploratory failure as a primary success or silently rescue a failed primary with a supporting result. Report each endpoint independently. If either control fails, flag comparability; do not promote a new speed claim. If primary fails but secondary passes, state explicitly that only Ridge16 confirmed at primary setting. Supporting endpoints may establish their own numerical pass but cannot substitute for the primary. No 41/40 ps exploration in this confirmation.

## Frozen design

C2, zero gap, 5 ps response, unchanged five NL003 absorber seeds 1301–1305 for both .1/1 mW drive, same NL013/014 optical loss/phase/dynamics and electrical PSD. Settings exactly [[42,1,120],[42,2,80],[42,2,120],[42,3,120],[43,1,120],[44,1,80],[45,1,60]] (on_ps, LO mW, cutoff GHz). No fitting, calibration, selection or coefficient changes during NL015. All 21 vectors from NL014 archive, including 45 ps controls originally from NL012, read-only float64 little-endian. Verify exact record key, vector length, finite values, SHA-256 before and at every resolution; control also matches NL013 and NL012.

| ps | LO | GHz | Readout | SHA-256 |
|---:|---:|---:|---|---|
| 45 | 1 | 60 | ridge8 | 1f21ed5381aefa68f2ac7ec8eae6189b4332c93d07bcf4977c7ebb433985d08d |
| 45 | 1 | 60 | ridge16 | 1cf055e0bb853b437070171a1ee9135716f61a760a2421dca1e9ca6da57f794f |
| 45 | 1 | 60 | ridge16_strong | 64db2504804993c2f4a9db888957f186179b09807b45c4e468c31c376b7e0623 |
| 42 | 1 | 120 | ridge8 | 8ff2392c01ef3d900656ef7bacc5c91ae3cbd43030bd19853debcf35774eaf38 |
| 42 | 1 | 120 | ridge16 | 8083ad4f4df21728961a3d6a47978eac4442da489ac503c62f9f6fbcd79c7dc6 |
| 42 | 1 | 120 | ridge16_strong | 73aa894f0296e979488de713a095473eb1ed0b88fd1f3d9fc2da12fd49f583fb |
| 42 | 2 | 80 | ridge8 | 977f8efe82adac1460a991acfbc368b7ca9d447394e3ffc5b9941e54f03acb72 |
| 42 | 2 | 80 | ridge16 | b9a77b8ffcd8f44adf5641a2b520047551badf5919952c6e3f208c55707f34e5 |
| 42 | 2 | 80 | ridge16_strong | cc6cd0e7bec0ea243c4c65712222bfb495d88aa484f03a64561ace7474dcc6cb |
| 42 | 2 | 120 | ridge8 | d1ec822076cdf6f244270482226b9dd5b1fe3ced04dc73c154a8d16bb63c72a2 |
| 42 | 2 | 120 | ridge16 | b8d9df37a73688d153ba724dc1768aa83171be426f468aa4643f276a1654cba7 |
| 42 | 2 | 120 | ridge16_strong | 3a5d95a7fe8b123ea863ebe2e7e619163706283353949a06f8477740c51201a1 |
| 42 | 3 | 120 | ridge8 | a9cfe09852a7c78536690183bd151809a0d9a923386fe93c79be80722a4274b6 |
| 42 | 3 | 120 | ridge16 | 7c05c69ac3e19e7486aaebe801d3e08bcb64299a6605a18c2e771145c5916174 |
| 42 | 3 | 120 | ridge16_strong | 64616dc6c2b2ca901fb46562b7edbc86841f5304452de742ea60f0397629d7aa |
| 43 | 1 | 120 | ridge8 | 4587a1d132905c1146571a30ae95445b98e2248acd6126890b842379694689bc |
| 43 | 1 | 120 | ridge16 | 53e68864b7f3d3b977ef688d51048ed9a8f7bca3c74305def3bfa7b3b65867e0 |
| 43 | 1 | 120 | ridge16_strong | cb5bfb069bd34d64711cb61fc241de789bb243937ae7ef71682acb319381307b |
| 44 | 1 | 80 | ridge8 | 91f2ae9ca9d6c4233c4f1e7f9029042d12fe19999a646776a52e4350fca3dbac |
| 44 | 1 | 80 | ridge16 | c34a3edca8d249b296fd10e67a8f1f4a26c0292c3159161ee4b9d5561bd81629 |
| 44 | 1 | 80 | ridge16_strong | 1a426eb8eb84da37a6c4ac294203284aea19f8be040ed3cf4b802bb5b439581a |

Two disjoint new test panels A domains 10304–10308, B 10314–10318, audit against all earlier RNG domains including NL014 calibration 10204–10208 and test 10214–10218. Same five domains per setting/resolution within each panel; common underlying draws across settings and arms, independent streams and repeats. 2048 balanced examples per seed/drive/panel, eight streams of 256, eight noise repetitions, no discarded startup symbols. Same trained weights, new data and noise, not independently trained models or physical measurements.

## Counts and numerical gates

7 settings x 7 readouts x 2 drives x 5 seeds x 2 panels = 980 primary seed rows, 196 primary groups, 49 two-panel common-drive tuples, 2940 resolution seed rows, 588 resolution groups, 21 frozen vectors, 14560 paired rows (7 x 13 x 10 x 8 x 2), 24 timing-level optical audits and 16 convergence comparisons (four durations x two panels x three grids / two comparisons). Run full NL014 audit before generating test inputs; pin all archive files and check unchanged afterwards. Retain NL013/014 exact causal features, stationary eligibility, unfiltered and clean >=.95, every combined repeat >=.95 (1946/2048), sampled diode <=2 mW, all five seeds per drive in both panels; agreement of middle/fine electrical and combined group gates. Same numerical tolerances and three aligned grids. Exact expected key sets, counts, paired marginals and sums, coefficient links, energy/hybrid/partition/stationary regressions and convergence; scientific failure is not implementation failure. Report all outcomes, seed/group gate changes, first/last-eight, optical memory, sampled peaks, conditional laser lower bounds, noise variance ratios, clean RMSE and paired effects. No significance claim for repeated decisions.

## Decision

Confirm 42 ps / 23.8095238095 Gsymbol/s only for explicitly passing frozen endpoints, and only if both positive controls pass. At 42 ps aggregate eight-segment rate 190.476 Gsegment/s, not measured ADC performance. No hardware throughput, BER, general AI accuracy or wall-plug claim. If 42 ps fails, report failure and evaluate the prespecified slower supporting endpoints without post-hoc retuning. Any future 41/40 ps sweep is a separate exploratory protocol, not part of this test.
