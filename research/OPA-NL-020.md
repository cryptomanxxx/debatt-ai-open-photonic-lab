# OPA-NL-020 — Robust margin optimization at 42 ps

Status: preregistered proposal; no NL020 data generated or experiment run. Basis: exact NL019 archive merge f7a5a1469a86f5617ce2dc83796fe9abd845fcc8, source run 44409237897, [NL019](OPA-NL-019.md).

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
