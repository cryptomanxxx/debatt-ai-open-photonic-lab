# OPA-NL-020 — Robust margin optimization at 42 ps

Status: executed; all four robust methods meet the exploratory 96% target but fail strict worst-repeat improvement over fresh Margin16 Low. No robust candidate advances. Exact archive pending. Basis: exact NL019 archive merge f7a5a1469a86f5617ce2dc83796fe9abd845fcc8, source run 44409237897, [NL019](OPA-NL-019.md).

## Raw evidence audit and rationale

Full independent CSV inspection verified 160 primary rows, 480 resolution rows, 32 groups, 96 resolution groups, 16 both-drive tuples, eight coefficient links, 3520 paired contingency rows and 88 summaries. Exact keys, both marginals, repeat minima, primary/fine identity, numerical gates and normalized noise variance matched. The new reproducible research/analyze_nl019.py additionally checks byte hashes, vector digests and optimizer records; must execute successfully before NL020 data generation. Not yet executed.

Low-drive worst repeat counts at 42 ps/120 GHz (each denominator 2048):

| LO | seed | frozen Ridge16 | fresh Ridge16 | balanced | low | low vs fresh net /16384 |
|---:|---:|---:|---:|---:|---:|---:|
|2|1301|1979|1978|1995|1994|131|
|2|1302|2008|2008|2016|2016|28|
|2|1303|1957|1956|1961|1964|77|
|2|1304|1954|1956|1982|1984|198|
|2|1305|1976|1977|1983|1982|18|
|3|1301|1981|1981|1997|1998|133|
|3|1302|2008|2008|2018|2018|28|
|3|1303|1957|1958|1963|1966|80|
|3|1304|1956|1957|1983|1987|205|
|3|1305|1980|1978|1990|1986|23|

All five seed minima improve under both margin objectives relative to matched fresh Ridge16; low-weighted gains on seed1304 are +28/2048 and +30/2048, with +198 and +205 matched net. All four margin candidates limited by seed1303 repeat3; best LO3 low misses 96% by one decision (1966 vs 1967). No advancement. At LO3 seed1303 fresh counts [1965,1978,1975,1958,1978,1973,1997,1976], low [1985,1989,1990,1966,1985,1981,1989,1995]; seed1304 fresh [1975,1962,1974,1987,1981,1957,1970,1981], low [2007,1994,1996,2012,2001,1987,2000,1995]. No special weighting of either seed in NL020.

At LO3 low drive, fresh Ridge16 electrical-only worst .974609375, balanced .97314453125, low .9716796875; all clean minima 1.0. Combined worst improves even though electrical-only worst slightly decreases. Mean normalized electrical variance relative to end anchor .4344221051055799, .4447539990431368, .44359511247544975 respectively; raw ratios .36633602211780686,1.1671894324383392,1.4461267153649804. Coefficient norms .9182984573982136,1.6199840647354007,1.805551159121834; previous-symbol block relative norms .10517613214570379,.2181219458325103,.2304133172255779. Cosines vs fresh 1,.9602925684367603,.9590000936152193. LO2 analogous previous-symbol fractions .10443823765984978,.21674407431818285,.2288603969493172. This supports a changed decision direction and greater relative history norm, not reduced electrical noise or proof of causal mechanism. First/last eight mean combined accuracy LO3 fresh .976953125/.978515625, low .983984375/.979296875; keep all startup examples. Optimizers converged in 32–36 iterations, gradient infinity norms 9.226924460158797e-8 to 5.509156098216985e-7. Do not compare objective values across different group weighting as if they were the same loss.

## Fixed design

A new exploratory experiment, not a repeat of NL019 or independent confirmation. Same C2, 42 ps, zero gap, 5 ps response, settings LO2/LO3 mW and 120 GHz, same five archived absorber weights, .1/1 mW, inherited optics, PSD, causal 16 taps, no intercept, fixed sign threshold, unchanged 95% gates and 96% advancement target. No 41/40 ps. No extra history. Exactly ten readouts per setting: four anchors (end,eighth_mean,quarter_mean,half_mean), frozen_fresh_ridge16 (NL019 fresh Ridge16), frozen_margin16_low (NL019 low), fresh_ridge16, margin16_low, robust16_softmax, robust16_repeat. Frozen pins (all six listed for provenance; only fresh Ridge16 and margin16_low used):
- LO 2: fresh_ridge16 — 14ece62bd1ae78e44a5e3dafdad65812ea842176cab03e0447985a8222026f2e
- LO 2: margin16_balanced — 9678ac635923c10ac38f3ee42367757249c17be4499351fede9d3c8aab84c005
- LO 2: margin16_low — 18cf11e4e6c904ae8e1e04449c1bf9f90f0b99c43826116a869dc5f92f65f6d4
- LO 3: fresh_ridge16 — 658ad54e42916effde948d7e0141e4517c64906c4c705033ac47bd914d9626eb
- LO 3: margin16_balanced — fc9d604aeb9f23cdac4864b379075d373cc697fabb8b684d1b12c36e1e758e99
- LO 3: margin16_low — 0e7e248644f97810db177da4dabc09b6ef7f581bfb46129d85457df45d23e0ef

Fresh Ridge16 and margin16_low follow NL019 exactly using the new shared calibration pool. Freeze all eight newly fitted and four archived coefficient records before any test data generation; total twelve. All methods use identical test data per setting/grid. No prior test labels or inputs in fit, no seed-specific vector, no label-dependent inference. Report all methods.

## Prespecified robust objectives

Reuse NL019 scaled calibration arrays X[g,r,s,t,f], signed labels Y[g,r,s,t], g=10 seed/drive groups, r=8 noise repeats, s=8 streams, t=64 symbols, f=16. Scale from pooled clean target RMS, floor 1e-12 A. Signed logits Y*(X@c)/.10. Individual logistic loss logaddexp(0,-logit), regularization .01||c||²/2. Group base weights p_g=.16 low/.04 high, equal across seeds within drive. For robust16_softmax compute mean loss L_g over repeats/streams/symbols. Objective tau*log(sum_g p_g*exp(L_g/tau)) + regularization, tau=.05. For robust16_repeat compute L_gr over streams/symbols only; weights p_g/8 per repeat; same tau=.05 and regularization. Stable scipy.special.logsumexp(log(p)+L/tau); gradient weighted average of individual loss gradients with softmax weights exp(log(p)+L/tau-logsumexp), plus .01*c. All groups/repeats have nonzero base weights. No special treatment of known failing seed or repeat. This tests smooth worst-group and worst-group/repeat risk, not a guarantee of maximin accuracy. Compare against fresh margin16_low to isolate risk aggregation change; frozen margin comparator tests new calibration effect. Identical temperature, regularization and optimizer settings to NL019 (zero start, L-BFGS-B analytic gradient, maxiter500, ftol1e-12, gtol1e-8, maxls50; success, finite nonzero vector, gradient inf <=1e-5, strictly decreased objective). Record each calibration cell loss, initial/final objectives, normalized effective weights, seed/drive/repeat identities, iterations/status/gradient and vector SHA. Synthetic central-difference step1e-6 error <1e-6, exact axis checks, equal-loss softmax reduces to base weights, shifted losses yield shift-invariant weights, permutation invariance across cells, no cross-stream history. No tuning tau/weights/optimizer based on test outcome. No fallback optimizer.

## Data, counts and gates

Calibration domains 10804..10808, 512 balanced examples per group, 8 repeats, 40960 rows per setting. Single exploratory test panel 10814..10818, 2048 balanced examples/group, 8 repeats. Explicitly disjoint from all prior domains including NL019. Same three aligned grids and tolerances, no discarded startup, same numerical gates and sampled diode cap 2 mW. Expected 200 primary,600 resolution,40 primary groups,120 resolution groups,20 both-drive tuples,12 coefficient records,3 optical audits,2 convergence comparisons. Pair each of six coefficient methods with four anchors (24 pairs per setting); fresh Ridge16 vs frozen fresh Ridge16; fresh low vs fresh Ridge16 and frozen low; both robust vs fresh low, frozen low and fresh Ridge16; robust repeat vs robust softmax. Total 34 pairs per setting x2 settings x2 drives x5 seeds x8 repeats=5440 paired raw rows,136 summaries each 81920 decisions. Verify exact keys and marginals, group/repeat minima, immutable vector hashes, archive and all inherited physics checks. Report normalized direction/noise, clean/electrical/combined diagnostics, all seed/repeat counts, calibration risk weights, matched gains. No inference of measured energy or BER.

Primary contrast robust16_softmax vs fresh margin16_low at LO2 low drive; secondary repeat risk and LO3. Advancement requires all implementation checks, both drives pass existing gates, maximin >=.96, low-drive worst strictly better than matched fresh margin16_low, positive low-drive matched net vs fresh margin16_low. Rank qualifying robust methods by lower LO, higher maximin, then softmax before repeat. No rounding, no rerun-until-pass. If none qualifies, report no robust candidate and reconsider objective or longer symbol duration before any new preregistered study. Only a qualifying candidate can be proposed for separately preregistered frozen two-panel confirmation. Historical NL015 23.81 Gsymbol/s remains qualified by NL018 failures; no new speed promotion, physical throughput, ADC feasibility, measured BER or wall-plug claim.

## Executed results — 2026-11-19

[Successful run 44492281387](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44492281387), job 135450777884, head 2e672fd323a887728594f85fa13d5a711ec0d5fe, CI merge a5876d4a3f12d7d882cf3f0c4234b10cfd079fcf, final merge cbb721cf6e408a8d0c3cfae16c202c2f14400db5. All 32 implementation checks passed, including the mandatory NL019 raw audit, gradient regressions (robust 3.8899905518974265e-10), optimizer and risk cell coverage, paired marginals, immutable vectors and prior archives. 200 primary rows, 600 resolution rows, 40 primary groups, 120 resolution groups, 20 common-drive tuples, 12 coefficient records, 5440 paired rows, 136 summaries, 3 optical audits, 2 convergence comparisons. Runtime 192.44995623900002 s. 28/40 groups pass, 12/20 both-drive passes, 8/20 reach 96% (all four margin references and four robust configurations), zero ambiguous groups or changed seed/group gates. No independent confirmation.

### All twenty tuples

| LO mW | readout | low worst | high worst | both drives pass | 96% target |
|---:|---|---:|---:|---|---|
| 2 | end | 0.89208984375 | 0.99072265625 | no | no |
| 2 | eighth_mean | 0.92431640625 | 0.97021484375 | no | no |
| 2 | quarter_mean | 0.91552734375 | 0.89404296875 | no | no |
| 2 | half_mean | 0.83154296875 | 0.69091796875 | no | no |
| 2 | frozen_fresh_ridge16 | 0.955078125 | 0.99755859375 | yes | no |
| 2 | frozen_margin16_low | 0.96337890625 | 0.99951171875 | yes | yes |
| 2 | fresh_ridge16 | 0.955078125 | 0.9970703125 | yes | no |
| 2 | margin16_low | 0.96337890625 | 0.99951171875 | yes | yes |
| 2 | robust16_softmax | 0.962890625 | 0.99951171875 | yes | yes |
| 2 | robust16_repeat | 0.962890625 | 0.99951171875 | yes | yes |
| 3 | end | 0.89404296875 | 0.9912109375 | no | no |
| 3 | eighth_mean | 0.92578125 | 0.97021484375 | no | no |
| 3 | quarter_mean | 0.916015625 | 0.89453125 | no | no |
| 3 | half_mean | 0.83154296875 | 0.69091796875 | no | no |
| 3 | frozen_fresh_ridge16 | 0.9560546875 | 0.99755859375 | yes | no |
| 3 | frozen_margin16_low | 0.9638671875 | 0.99951171875 | yes | yes |
| 3 | fresh_ridge16 | 0.95654296875 | 0.9970703125 | yes | no |
| 3 | margin16_low | 0.96337890625 | 0.99951171875 | yes | yes |
| 3 | robust16_softmax | 0.962890625 | 0.99951171875 | yes | yes |
| 3 | robust16_repeat | 0.962890625 | 0.99951171875 | yes | yes |

### Prespecified robust contrasts

| LO mW | readout | low worst delta vs fresh margin | net vs fresh margin /81920 | limiting seed/repeat | qualifies |
|---:|---|---:|---:|---|---|
| 2 | robust16_softmax | -0.00048828125 | 4 | 1303/1 | no |
| 2 | robust16_repeat | -0.00048828125 | 4 | 1303/1 | no |
| 3 | robust16_softmax | -0.00048828125 | 12 | 1303/1 | no |
| 3 | robust16_repeat | -0.00048828125 | 14 | 1303/1 | no |

All four robust candidates clear 96%, with low worst 1972/2048 and high worst 2047/2048. Fresh margin reference is 1973/2048 at both LO settings, so each robust candidate loses one worst-repeat decision despite positive aggregate net (+4,+4,+12,+14). No qualifying candidate under original protocol. Best frozen NL019 margin LO3 is 1974/2048 low and 2047/2048 high; LO2 is 1973/2048 low. Both frozen margin vectors reach 96% on new data, but NL019 itself missed that target and neither is an NL020 advancement candidate. No retroactive promotion or claim of independent two-panel confirmation. All four robust endpoints limited by seed1303 repeat1; seed-level improvement vs fresh needs raw audit. Comparing NL019 and NL020 absolute minima is confounded by different test draws. At matched low-drive inputs, fresh margin vs fresh ridge gains +497/+499 decisions at LO2/3; robust gains +501/+511 or +513 vs fresh ridge, but -16/-3/-1 vs frozen margin (LO2 both -16, LO3 softmax -3 and repeat -1). Recalibrating margin loses 20/15 net compared with frozen at low drive. Repeat vs softmax gives 0/+2 net at low drive, 0 at high. Fresh margin and both robust methods share 81917/81920 correct high-drive decisions at each setting, not error-free. The incremental robust-risk benefit is small and does not improve maximin. Descriptive paired repeated decisions only; no independent-trial significance claim.

### Exact matched counts

| contrast | LO mW | drive mW | method | anchor | both correct | method only | anchor only | neither | net |
|---|---:|---:|---|---|---:|---:|---:|---:|---:|
| robust | 2 | 0.1 | robust16_repeat | fresh_ridge16 | 79166 | 840 | 339 | 1575 | 501 |
| robust | 2 | 0.1 | robust16_repeat | frozen_margin16_low | 79891 | 115 | 131 | 1783 | -16 |
| robust | 2 | 0.1 | robust16_repeat | margin16_low | 79973 | 33 | 29 | 1885 | 4 |
| robust | 2 | 0.1 | robust16_softmax | fresh_ridge16 | 79160 | 846 | 345 | 1569 | 501 |
| robust | 2 | 0.1 | robust16_softmax | frozen_margin16_low | 79897 | 109 | 125 | 1789 | -16 |
| robust | 2 | 0.1 | robust16_softmax | margin16_low | 79980 | 26 | 22 | 1892 | 4 |
| robust | 2 | 1 | robust16_repeat | fresh_ridge16 | 81885 | 32 | 1 | 2 | 31 |
| robust | 2 | 1 | robust16_repeat | frozen_margin16_low | 81915 | 2 | 1 | 2 | 1 |
| robust | 2 | 1 | robust16_repeat | margin16_low | 81917 | 0 | 0 | 3 | 0 |
| robust | 2 | 1 | robust16_softmax | fresh_ridge16 | 81885 | 32 | 1 | 2 | 31 |
| robust | 2 | 1 | robust16_softmax | frozen_margin16_low | 81915 | 2 | 1 | 2 | 1 |
| robust | 2 | 1 | robust16_softmax | margin16_low | 81917 | 0 | 0 | 3 | 0 |
| robust | 3 | 0.1 | robust16_repeat | fresh_ridge16 | 79232 | 837 | 324 | 1527 | 513 |
| robust | 3 | 0.1 | robust16_repeat | frozen_margin16_low | 79955 | 114 | 115 | 1736 | -1 |
| robust | 3 | 0.1 | robust16_repeat | margin16_low | 80027 | 42 | 28 | 1823 | 14 |
| robust | 3 | 0.1 | robust16_softmax | fresh_ridge16 | 79226 | 841 | 330 | 1523 | 511 |
| robust | 3 | 0.1 | robust16_softmax | frozen_margin16_low | 79954 | 113 | 116 | 1737 | -3 |
| robust | 3 | 0.1 | robust16_softmax | margin16_low | 80030 | 37 | 25 | 1828 | 12 |
| robust | 3 | 1 | robust16_repeat | fresh_ridge16 | 81887 | 30 | 1 | 2 | 29 |
| robust | 3 | 1 | robust16_repeat | frozen_margin16_low | 81915 | 2 | 2 | 1 | 0 |
| robust | 3 | 1 | robust16_repeat | margin16_low | 81917 | 0 | 0 | 3 | 0 |
| robust | 3 | 1 | robust16_softmax | fresh_ridge16 | 81887 | 30 | 1 | 2 | 29 |
| robust | 3 | 1 | robust16_softmax | frozen_margin16_low | 81915 | 2 | 2 | 1 | 0 |
| robust | 3 | 1 | robust16_softmax | margin16_low | 81917 | 0 | 0 | 3 | 0 |
| recalibration | 2 | 0.1 | fresh_ridge16 | frozen_fresh_ridge16 | 79473 | 32 | 35 | 2380 | -3 |
| recalibration | 2 | 0.1 | margin16_low | frozen_margin16_low | 79894 | 108 | 128 | 1790 | -20 |
| recalibration | 2 | 1 | fresh_ridge16 | frozen_fresh_ridge16 | 81886 | 0 | 4 | 30 | -4 |
| recalibration | 2 | 1 | margin16_low | frozen_margin16_low | 81915 | 2 | 1 | 2 | 1 |
| recalibration | 3 | 0.1 | fresh_ridge16 | frozen_fresh_ridge16 | 79525 | 31 | 41 | 2323 | -10 |
| recalibration | 3 | 0.1 | margin16_low | frozen_margin16_low | 79943 | 112 | 127 | 1738 | -15 |
| recalibration | 3 | 1 | fresh_ridge16 | frozen_fresh_ridge16 | 81888 | 0 | 4 | 28 | -4 |
| recalibration | 3 | 1 | margin16_low | frozen_margin16_low | 81915 | 2 | 2 | 1 | 0 |
| margin | 2 | 0.1 | margin16_low | fresh_ridge16 | 79170 | 832 | 335 | 1583 | 497 |
| margin | 2 | 1 | margin16_low | fresh_ridge16 | 81885 | 32 | 1 | 2 | 31 |
| margin | 3 | 0.1 | margin16_low | fresh_ridge16 | 79235 | 820 | 321 | 1544 | 499 |
| margin | 3 | 1 | margin16_low | fresh_ridge16 | 81887 | 30 | 1 | 2 | 29 |
| risk | 2 | 0.1 | robust16_repeat | robust16_softmax | 79994 | 12 | 12 | 1902 | 0 |
| risk | 2 | 1 | robust16_repeat | robust16_softmax | 81917 | 0 | 0 | 3 | 0 |
| risk | 3 | 0.1 | robust16_repeat | robust16_softmax | 80058 | 11 | 9 | 1842 | 2 |
| risk | 3 | 1 | robust16_repeat | robust16_softmax | 81917 | 0 | 0 | 3 | 0 |

Numerical convergence maxima: field 3.198547123054762e-10 sqrt(mW), waveform 3.2553626278645155e-9 sqrt(mW), clean current 2.207321409593982e-8 A, noisy current 2.2075803204310877e-8 A, peak 0.0000012278704368817728 mW. No gate changes.

### Archive and next decision

Artifact 14513522210, ZIP 197602 bytes, SHA-256 299ba43c879ca6f80213c6946a0fb64194b5f5268dc5ab0b2021244193834e85. Manual archive helper pins run/head/ZIP and fifteen exact science file hashes plus staged bytes. After verified archive merge, audit all 5440 paired rows, 12 vectors, seed/repeat profiles and effective risk weights, normalized electrical variance, clean/electrical/combined arms. Investigate whether the fixed risk temperature actually reallocates enough weight and whether direction changes are material; do not tune from old test labels or select a new objective by test-only sweep. Under original protocol no robust candidate qualifies. Reconsider objective or symbol period after raw audit; a separately preregistered new study may assess the established margin baseline with independent panels, but this is a new decision, not retroactive NL020 advancement. Historical NL015 23.81 Gsymbol/s confirmation remains qualified by NL018 failures. No physical throughput, BER, ADC feasibility or measured power claim.
