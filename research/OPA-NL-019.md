# OPA-NL-019 — Noise-aware margin-oriented receiver exploration at 42 ps

Status: executed; all four margin contrasts improved over matched fresh Ridge16, but none meets exact 96% robustness target. No candidate advances. Exact archive pending.
Basis: [NL018](OPA-NL-018.md), run 44387159815, exact archive merge 5860106e9ce2c437b0e747a9c91700720ab114e0.

## Source audit and diagnosis

Independent full archived CSV inspection verified 480 primary rows, 1440 resolution rows, 96 primary groups, 288 resolution groups, 24 two-panel tuples, 12 coefficient links, 8960 paired raw rows and 224 summaries. Exact expected keys, both contingency marginals, totals, repeat minima, primary/fine identity, seed/group gates, middle/fine agreement and all panel-drive tuple gates matched. Reproducible Python audit research/analyze_nl018.py additionally checks byte hashes, vector digests and NL017 identity; must run successfully before any NL019 data generation; not yet executed. No prior test labels may be used for fitting.

All six low-drive endpoint groups (primary and both controls across A/B) have unfiltered and clean minima 1.0, electrical-only gates pass, diode peaks below 2 mW. Combined noise is the failing arm, not clean filtering or stationary eligibility. This isolates the modeled combined-noise condition, not a causal allocation of errors to separate physical noise sources. All six limiting seed rows are 1304; same repeat index 3 is limiting in both panels for all three endpoints. Four other seeds pass each of those six groups. Do not discard seed1304 or repeat3. Across settings same panel draws are paired, not independent replication of a limiting repeat.

| panel | ps | LO | GHz | readout | electrical worst | combined worst | seed1304 repeat counts (0..7) |
|---|---:|---:|---:|---|---:|---:|---|
| A | 41 | 3 | 80 | frozen_ridge16_midlow | .9619140625 | .94677734375 | 1950,1942,1958,1939,1953,1973,1948,1961 |
| B | 41 | 3 | 80 | frozen_ridge16_midlow | .95751953125 | .94189453125 | 1956,1961,1958,1929,1948,1944,1952,1963 |
| A | 42 | 2 | 120 | ridge16 | .9716796875 | .95458984375 | 1968,1962,1965,1955,1966,1980,1962,1980 |
| B | 42 | 2 | 120 | ridge16 | .96337890625 | .947265625 | 1978,1969,1968,1940,1960,1965,1969,1975 |
| A | 42 | 3 | 120 | ridge16 | .97265625 | .9560546875 | 1973,1963,1965,1958,1969,1981,1963,1981 |
| B | 42 | 3 | 120 | ridge16 | .96435546875 | .9482421875 | 1980,1973,1970,1942,1961,1967,1971,1977 |

Panel B 42/3/120 low combined seed minima 1301..1305: .96826171875,.9755859375,.96435546875,.9482421875,.97412109375. Mean first/last eight accuracies over five seeds .971484375/.972265625; at 42/2/120 .97109375/.972265625; at 41/3/80 .966015625/.965625. These are descriptive startup diagnostics, not evidence for discarding boundaries; all startup examples remain in denominators. NL017 protocol requested these diagnostics; if already archived (fields present in NL018), retain and verify raw values rather than reconstructing from aggregate results. Mean electrical variance ratios panel B 41/3/80 .6328203991646928, 42/2/120 .363342858223343, 42/3/120 .364254431305109; mean clean target RMSE 1.2161448658164922e-6/1.231797275595734e-6/1.496286281343865e-6 A. Max sampled low-drive peaks 1.5481745715410673/1.0398255141066504/1.5486785781364851 mW. Conditional mean signal+LO electrical lower bounds 16.512677009658585/11.512677009658585/16.512677009658585 mW at 20% assumed efficiency, not total power. Extended history net effect at most 14 of 81920 matched decisions in NL018. Therefore fix 16 taps; investigate objective rather than more history or more speed.

## Fixed experimental design

Exploratory only; no new confirmation claim even if every gate passes. Settings exactly (42 ps,2 mW LO,120 GHz) and (42 ps,3 mW LO,120 GHz). Same C2, zero gap, 5 ps response, five archived absorber weights seeds1301..1305, .1/1 mW drive, inherited optical loss/phase and PSD, same 8 segments/symbol, causal features (current eight and previous eight, zero padding per stream), no bias, no threshold tuning, sign decision >0. Both frozen ordinary Ridge16 comparators must be reported even if they fail; they are historical references, not required to pass for an exploratory improvement claim. No 41 or 40 ps tests. No changed hardware/noise parameters.

At each setting exactly eight readouts: end, eighth_mean, quarter_mean, half_mean, frozen_ridge16, fresh_ridge16, margin16_balanced, margin16_low. Frozen ordinary pins from NL018 (identical NL014–017):
- 42 ps/2 mW/120 GHz: b8d9df37a73688d153ba724dc1768aa83171be426f468aa4643f276a1654cba7
- 42 ps/3 mW/120 GHz: 7c05c69ac3e19e7486aaebe801d3e08bcb64299a6605a18c2e771145c5916174
Fresh ordinary Ridge16 uses identical inherited combined-current regression objective, lambda .01, fit on fresh calibration pool. The two proposed methods use the same calibration features and known labels, but optimize a smooth classification margin instead of reconstructing clean target current. No seed-specific coefficient vectors; each setting uses one vector across seeds, drives and panels. All vectors persisted read-only before test data generation. No test-based selection, refitting, or excluding failures.

## Prespecified margin objective

Let X be combined arm causal 16-feature rows from calibration raw, shape (10 weight/drive groups,8 repeats,8 streams,64 symbols,16 features), flattened with group identity preserved. For each setting use inherited clean target current t from hybrid(end,lo); shared scalar s=max(RMS(t),1e-12 A) from all calibration groups. x=X/s, signed label y in {-1,+1} from balanced calibration examples, broadcast across repeats exactly. For each group g define L_g(c)=mean(logaddexp(0,-y*x@c/0.10)). Temperature .10 dimensionless; no learned intercept or bias. Objective J(c)=sum_g w_g L_g(c)+.01||c||²/2. Balanced weights w_g=.1 each. Low-weighted variant w_g=.16 per low-drive group and .04 per high-drive group (total .8/.2), all five seeds equal within drive. No extra seed1304 weight; avoid overfitting the known worst seed. Fit from zero vector using deterministic scipy.optimize.minimize L-BFGS-B analytic gradient, maxiter 500, ftol 1e-12, gtol 1e-8, maxls 50. Stable sigmoid via scipy.special.expit, logaddexp for loss. Require success, finite coefficients, gradient infinity norm <=1e-5, strictly lower objective than zero, record iterations/status/objective/gradient and exact weights, scale, SHA-256. Reject on optimizer failure, no silent alternate optimizer. Synthetic gradient finite difference regression central step 1e-6, abs error <1e-6; verify label broadcast and weight normalization, causality, no cross-stream carry. Positive scalar changes do not alter sign; report normalized coefficient direction and norm, do not infer physical noise suppression from coefficient scale alone. Ordinary Ridge16 fits clean-target regression on same noisy inputs and same scale, not a noise-free baseline. No covariance claim or explicit decomposition objective; this is noise-aware supervised margin training on the combined arm.

## Data and gates

Calibration domains 10704..10708, 512 balanced examples per seed/drive (8 streams x64), 8 repeats, 40960 rows per setting. Single exploratory panel domains 10714..10718, 2048 examples per seed/drive (8 streams x256), 8 repeats. Disjoint from all prior domains including NL018 A 10604..10608/B 10614..10618. Same paired underlying draws across settings/readouts/grids within panel; test inputs only after complete coefficient persistence. All 2048 examples including startup retained. Same three aligned grids finest .0625 ps, inherited tolerances, 95% unfiltered/clean/combined worst-repeat accuracy, stationary eligibility, 2 mW sampled diode cap, middle/fine electrical and combined group gate agreement. No change to existing pass_gate. Report electrical-only and combined accuracies, first/last eight, min signed current, normalized noise variance, calibration objective and all seed/repeat counts. A stricter *exploratory robustness target* is combined worst >=.96 at both drives, with all inherited gates; this is not a new replacement gate. Report all methods at both drives and all five seeds, no averaging to conceal failures.

## Counts, pairing and interpretation

2 settings x8 methods x2 drives x5 seeds=160 primary rows, 480 resolution rows, 32 primary groups, 96 resolution groups, 16 common-drive tuples, 8 coefficient records (2 frozen, 6 freshly fitted), 3 optical audits and 2 convergence comparisons (one timing, two receivers). At each setting pair each of four coefficient readouts against all four anchors (16); fresh_ridge16 vs frozen_ridge16 (1); both margin methods vs fresh_ridge16 and frozen_ridge16 (4); margin16_low vs margin16_balanced (1). Total 22 pairs per setting x2 settings x2 drives x5 seeds x8 repeats=3520 paired raw rows, 88 summaries (81920 decisions each). Record exact both-correct, method-only, anchor-only, neither, both marginals and net; no independent-sample significance claims. Require exact coverage, archive immutability, vector digest at all grids, all physics/numerical checks inherited. Compare matched margin methods vs fresh ordinary to isolate objective under identical calibration data; fresh vs frozen indicates calibration effect.

Prespecified primary exploratory contrast margin16_balanced vs fresh_ridge16 at 42/2/120 low drive; secondary margin16_low same setting, both methods at 42/3/120, high-drive tradeoffs. Report absolute worst accuracy difference, paired net and limiting seeds/repeats. Advancement criterion for a candidate: both drives pass all inherited gates, maximin >=.96, low-drive worst strictly higher than matched fresh Ridge16 and positive low-drive net vs fresh Ridge16. Among qualifying new margin methods rank lower LO first, higher maximin second, fewer ties by balanced before low. If none qualify report no robust candidate; no repeat-until-pass and no speed promotion. If any qualify, separately preregister independent two-panel frozen confirmation with unchanged weights and physics. Historical NL015 23.81 Gsymbol/s confirmation remains qualified by NL018 failures. No physical BER, measured power, ADC feasibility, general AI performance or hardware throughput claim.

## Executed results — 2026-11-18

[Successful run 44409237897](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44409237897), job 135172718163, source head 3ea0d1ede9610f42a3c06ebf2602b82d909dc437, CI merge 76e6f4af6edd18450e1001cb6a81e569a2f532db, final merge 391709e2d50208f3ef6cf1a65e1e1152062c72e6. All 30 implementation checks passed, including mandatory NL018 audit, analytic gradient regression (max finite-difference error 4.1237524506243517e-10), optimizer checks, exact paired marginals and coefficient immutability. 160 primary rows, 480 resolution rows, 32 primary groups, 96 resolution groups, 16 common-drive tuples, 8 coefficient records, 3520 paired raw rows, 88 summaries, 3 optical audits and 2 convergence comparisons. Runtime 189.936796388 s. 20/32 passing groups, 8/16 both-drive passes (all coefficient methods), no numerical ambiguity or grid-gate changes. No independent confirmation.

### All 16 tuples

| LO mW | method | combined worst low | combined worst high | both drives pass | 96% target |
|---:|---|---:|---:|---|---|
| 2 | end | 0.8974609375 | 0.9921875 | no | no |
| 2 | eighth_mean | 0.923828125 | 0.97265625 | no | no |
| 2 | quarter_mean | 0.916015625 | 0.890625 | no | no |
| 2 | half_mean | 0.82861328125 | 0.7119140625 | no | no |
| 2 | frozen_ridge16 | 0.9541015625 | 0.9970703125 | yes | no |
| 2 | fresh_ridge16 | 0.955078125 | 0.9970703125 | yes | no |
| 2 | margin16_balanced | 0.95751953125 | 1 | yes | no |
| 2 | margin16_low | 0.958984375 | 1 | yes | no |
| 3 | end | 0.8994140625 | 0.9921875 | no | no |
| 3 | eighth_mean | 0.9248046875 | 0.97265625 | no | no |
| 3 | quarter_mean | 0.91650390625 | 0.89111328125 | no | no |
| 3 | half_mean | 0.8291015625 | 0.7109375 | no | no |
| 3 | frozen_ridge16 | 0.955078125 | 0.9970703125 | yes | no |
| 3 | fresh_ridge16 | 0.95556640625 | 0.9970703125 | yes | no |
| 3 | margin16_balanced | 0.95849609375 | 1 | yes | no |
| 3 | margin16_low | 0.9599609375 | 1 | yes | no |

### Prespecified contrasts

| LO mW | method | low worst delta vs fresh | net correct vs fresh (81920 low-drive decisions) | limiting seed/repeat | qualifies |
|---:|---|---:|---:|---|---|
| 2 | margin16_balanced | 0.00244140625 | 417 | 1303/3 | no |
| 2 | margin16_low | 0.00390625 | 452 | 1303/3 | no |
| 3 | margin16_balanced | 0.0029296875 | 436 | 1303/3 | no |
| 3 | margin16_low | 0.00439453125 | 469 | 1303/3 | no |

The primary contrast (balanced LO2) improves worst accuracy by 5/2048, +417 net matched correct decisions. Best exploratory method is Margin16 Low LO3, worst 1966/2048=.9599609375; target requires ceil(.96*2048)=1967 correct. Exactly one decision short; do not round to a pass. Both drives pass 95%, but all four fail the 96% advancement criterion. All four improve both worst and aggregate low-drive accuracy relative to matched fresh Ridge16, with best +9/2048 worst and +469/81920 net (+.572509765625 percentage points); objective change effect under shared calibration data is larger than recalibration alone (+10/-8 net at low drive). Weighting low drive vs balanced yields +35/+33 net at LO2/3 and +3/2048 worst at both settings. All four margin methods correctly classify all 81920 combined decisions per setting at high drive in this finite panel (each +29 net relative to either Ridge16). No physical error-free or BER claim. Limiting seed shifts to 1303 repeat3 for all four margin endpoints; whether seed1304 improved within the same panel requires raw seed-level comparison, not inference from the limiting seed alone.

### Exact matched counts

| contrast | LO mW | drive mW | method | anchor | both correct | method only | anchor only | neither | net |
|---|---:|---:|---|---|---:|---:|---:|---:|---:|
| margin | 2 | 0.1 | margin16_balanced | fresh_ridge16 | 79173 | 816 | 399 | 1532 | 417 |
| margin | 2 | 0.1 | margin16_balanced | frozen_ridge16 | 79171 | 818 | 391 | 1540 | 427 |
| margin | 2 | 0.1 | margin16_low | fresh_ridge16 | 79175 | 849 | 397 | 1499 | 452 |
| margin | 2 | 0.1 | margin16_low | frozen_ridge16 | 79173 | 851 | 389 | 1507 | 462 |
| margin | 2 | 1 | margin16_balanced | fresh_ridge16 | 81891 | 29 | 0 | 0 | 29 |
| margin | 2 | 1 | margin16_balanced | frozen_ridge16 | 81891 | 29 | 0 | 0 | 29 |
| margin | 2 | 1 | margin16_low | fresh_ridge16 | 81891 | 29 | 0 | 0 | 29 |
| margin | 2 | 1 | margin16_low | frozen_ridge16 | 81891 | 29 | 0 | 0 | 29 |
| margin | 3 | 0.1 | margin16_balanced | fresh_ridge16 | 79243 | 810 | 374 | 1493 | 436 |
| margin | 3 | 0.1 | margin16_balanced | frozen_ridge16 | 79248 | 805 | 377 | 1490 | 428 |
| margin | 3 | 0.1 | margin16_low | fresh_ridge16 | 79250 | 836 | 367 | 1467 | 469 |
| margin | 3 | 0.1 | margin16_low | frozen_ridge16 | 79254 | 832 | 371 | 1463 | 461 |
| margin | 3 | 1 | margin16_balanced | fresh_ridge16 | 81891 | 29 | 0 | 0 | 29 |
| margin | 3 | 1 | margin16_balanced | frozen_ridge16 | 81891 | 29 | 0 | 0 | 29 |
| margin | 3 | 1 | margin16_low | fresh_ridge16 | 81891 | 29 | 0 | 0 | 29 |
| margin | 3 | 1 | margin16_low | frozen_ridge16 | 81891 | 29 | 0 | 0 | 29 |
| recalibration | 2 | 0.1 | fresh_ridge16 | frozen_ridge16 | 79523 | 49 | 39 | 2309 | 10 |
| recalibration | 2 | 1 | fresh_ridge16 | frozen_ridge16 | 81891 | 0 | 0 | 29 | 0 |
| recalibration | 3 | 0.1 | fresh_ridge16 | frozen_ridge16 | 79572 | 45 | 53 | 2250 | -8 |
| recalibration | 3 | 1 | fresh_ridge16 | frozen_ridge16 | 81891 | 0 | 0 | 29 | 0 |
| weighting | 2 | 0.1 | margin16_low | margin16_balanced | 79958 | 66 | 31 | 1865 | 35 |
| weighting | 2 | 1 | margin16_low | margin16_balanced | 81920 | 0 | 0 | 0 | 0 |
| weighting | 3 | 0.1 | margin16_low | margin16_balanced | 80025 | 61 | 28 | 1806 | 33 |
| weighting | 3 | 1 | margin16_low | margin16_balanced | 81920 | 0 | 0 | 0 | 0 |

These are descriptive paired repeated decisions, not independent trials. Numerical convergence maxima: field 3.259453156966816e-10 sqrt(mW), waveform 3.3112918765590872e-9 sqrt(mW), clean current 2.211397207051765e-8 A, noisy current 2.2116101075172513e-8 A, peak 8.964327140592587e-7 mW. All within inherited tolerances. No changed seed or group gates.

### Archive and next decision

Artifact 14475309037, ZIP 169652 bytes, SHA-256 17a7ed1175c4fdee87539eadd7e9999f4f7d54c9ce55556be656cf0029672d40. Manual archive workflow pins exact source, ZIP CRC, all fifteen original hashes and staged bytes, including no qualifying candidate. After merge of exact archive, audit all 3520 paired rows, coefficient directions/norms and optimizer results, seed1303/1304 repeat profiles, clean/electrical/combined arms and normalized noise diagnostics. Do not promote the best near-miss or rerun NL019 until pass. A separately preregistered exploratory objective refinement is a possible next research direction: improve worst-group margin on calibration only while keeping all five seeds and both drives, and compare matched fresh/frozen objectives. Specify design and new disjoint domains after raw audit, no threshold relaxation, no fitting prior test inputs or labels, no speed promotion. Historical NL015 23.81 Gsymbol/s confirmation remains qualified by NL018 robustness failures. No physical throughput, measured BER, wall-plug power or ADC feasibility claim.
