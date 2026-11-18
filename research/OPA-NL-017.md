# OPA-NL-017 — Causal extended-history receiver exploration

Status: proposed protocol; no NL017 simulations or new test inputs generated.
Basis: [OPA-NL-016](OPA-NL-016.md), source run 44334443261, archive merge 36f86e24a594e8b5a4af18f80189919d4d241edd.

## Raw archive diagnosis

Retrieved full primary, resolution and paired CSVs including large Git blobs. Independently checked 24160 distinct paired keys, each 2048 decisions, both marginals against 1220 primary seed records; all 604 paired summaries, 3660 resolution rows, 732 resolution groups, 244 primary groups, 122 common-drive pairs, coefficient links, repeat minima, both seed and group gates and middle/fine agreement. All passed. Reproducible Python audit research/analyze_nl016.py must execute successfully before new inputs; this Python implementation is not yet run.

All 54 groups per timing/drive meet unfiltered threshold at 40 and 41 ps. Low-drive clean passes 48/54 at both timings, electrical passes 24/54 (40 ps) and 26/54 (41 ps), combined passes 0/54 each. At high drive clean passes 38/54 and 40/54, electrical/combined passes 36/54 and 40/54 respectively. Thus low drive combined-noise failures dominate; not every setting has adequate clean reconstruction.

At LO3/120 GHz/.1 mW, both ordinary Ridge16 and Midlow have unfiltered and clean minima 1. At 40 ps ordinary Ridge16 electrical worst .9609375, combined .93994140625, mean relative electrical variance .39506952518652855, mean clean target RMSE 1.5907664545053224e-6 A. Midlow electrical .95849609375, combined .94189453125, variance .43072494076778584, RMSE 1.200740401639124e-6 A. At 41 ps ordinary Ridge16 electrical .966796875, combined .9462890625, variance .37792549477031834, RMSE 1.5358733775241805e-6 A; Midlow electrical .96533203125, combined .9482421875, variance .4122333406163934, RMSE 1.1539778241643868e-6 A. Optical memory field maxima .0046612126453277215 and .0042799348107470684 sqrt(mW), respectively. Max sampled diode at these low-drive settings 1.545808817324227/1.5462333561891968 mW; mean conditional signal+LO laser electric lower bound 16.511445169590793 mW under 20% efficiency, not measured total power.

At 40/120, 41/80, 41/120 (LO3, low drive), Ridge16 vs Ridge8 net +219,+197,+231 of 81920 repeated decisions; Midlow vs Ridge16 net -10,-50,-41 (equalizer-only 216,197,156; anchor-only 226,247,197). Therefore Midlow improves worst-case but not aggregate paired accuracy at those settings. No significance claim. Limiting seed 1304; 40/120 Midlow eight counts 1945,1939,1929,1950,1942,1933,1954,1942; 41/80 1964,1952,1942,1959,1954,1943,1962,1949; 41/120 1960,1951,1942,1960,1959,1944,1967,1959. Threshold 1946. Never fit to this seed's test data or labels. Previous-symbol coefficient L2 norms .11665774072252642/.1216205817150885/.11763894614853748 vs current-symbol .9873913763353874/1.0420972703637519/.9734155799841171. Previous history contributes but these norms do not prove additional history is useful. Material response 5 ps and sampled memory does not establish dependence beyond one previous symbol. Longer history is a falsifiable exploratory hypothesis, not established solution.

## Hypotheses and fixed design

Test whether causal current plus two or three previous symbols improves combined-noise performance without changing physics. New methods Ridge24 and Ridge32 with lambda .003 and .01, using eight segment means per symbol, zero padding at stream start, no cross-stream history or future samples. Same pooled combined-current calibration objective as NL016 (no labels); current target is noiseless hybrid endpoint. Fit at finest grid only, save immutable coefficients before generating exploratory inputs. Compare against freshly calibrated matched Ridge16 .003/.01 at the same new calibration domains to isolate history length, and archived NL016 Ridge16 .003/.01 as additional frozen comparators. Do not introduce alternative noise-aware objective in this experiment; that would confound the history comparison. Retain four anchors. No per-seed fit. No changes to material, optical noise, receiver PSD, weights, LO cap, or gate.

Candidate settings (40,3,120), (41,3,80), (41,3,120) in ps/mW/GHz, chosen from NL016 maxima. Each has 12 methods: four anchors, archived ridge16 and ridge16_midlow (names frozen_ridge16 and frozen_ridge16_midlow), fresh ridge16 and ridge16_midlow, ridge24 and ridge24_midlow, ridge32 and ridge32_midlow. Controls (42,2,120),(42,3,120) use original seven methods only, six frozen vectors from NL015/NL016. Both ordinary Ridge16 controls must pass for any candidate promotion. No new fit at controls. All new methods use same raw samples, current target and draws. Implement generalized feature extraction with exact order current eight means, lag1 eight, lag2 eight, lag3 eight; first k missing symbols padded zero. Validate equality to inherited 8/16 feature extraction, impulse and arbitrary future perturbation causality, stream isolation and zero padding for every lag, no wrap-around, read-only fitted vectors and hash equality across grids. Fit rank/finite checks and calibration diagnostics. Record actual taps, history=(taps/8-1)*on, feature rate=8*1000/on; no claim of hardware implementation.

## Frozen coefficient pins

| ps | LO | GHz | source method | SHA-256 |
|---:|---:|---:|---|---|
| 42 | 2 | 120 | ridge8 | d1ec822076cdf6f244270482226b9dd5b1fe3ced04dc73c154a8d16bb63c72a2 |
| 42 | 2 | 120 | ridge16 | b8d9df37a73688d153ba724dc1768aa83171be426f468aa4643f276a1654cba7 |
| 42 | 2 | 120 | ridge16_strong | 3a5d95a7fe8b123ea863ebe2e7e619163706283353949a06f8477740c51201a1 |
| 42 | 3 | 120 | ridge8 | a9cfe09852a7c78536690183bd151809a0d9a923386fe93c79be80722a4274b6 |
| 42 | 3 | 120 | ridge16 | 7c05c69ac3e19e7486aaebe801d3e08bcb64299a6605a18c2e771145c5916174 |
| 42 | 3 | 120 | ridge16_strong | 64616dc6c2b2ca901fb46562b7edbc86841f5304452de742ea60f0397629d7aa |
| 40 | 3 | 120 | ridge16 | 07cce3e02fb413ca6f6617bfb4e7e7dd0eb50e4ef1f5eb6d8187732bc8c55d4a |
| 40 | 3 | 120 | ridge16_midlow | bf7ad3f46dfe183e3cffeee2d5373008e9ecd2b7dd76a4ec97f2df57f1df4e3b |
| 41 | 3 | 80 | ridge16 | 601beea1759c1d60d761be880cde11c30cb6db2603ec2ade67c10ec881a59430 |
| 41 | 3 | 80 | ridge16_midlow | 1ccfbaa45af3fb4aea0effb527a8c834e5e3a1b6b190d84a1dd8116034c26c9b |
| 41 | 3 | 120 | ridge16 | c6cbb9a4f6c13bf23449f4980822321d1dfeda942ff34a359c4b0597240314ca |
| 41 | 3 | 120 | ridge16_midlow | 31b1dc98ef9c78f51b3ca0b5d8f8eac6369485a8db4c9d5c24af7fe85f0049ce |

Verify candidates against NL016 archive; controls against NL014/NL015/NL016, exact keys, little-endian float64 vectors, finite, read-only. All archive file hashes checked and unchanged. Calibration domains 10504..10508, 512 examples per weight, 8 streams ×64, eight repeats; test 10514..10518, 2048 examples per weight, 8 streams ×256, eight repeats. Disjoint from all earlier domains including NL016 10404..10408,10414..10418. Same frozen five NL003 absorber seeds 1301..1305 at .1 and 1 mW. C2, zero gap, 5 ps response, unchanged hybrid loss/phase and noise model. Same 95% thresholds and stationary eligibility, 2 mW sampled diode cap, aligned three grids finest <=.0625 ps, middle/fine electrical and combined group agreement, inherited tolerances. No discarded startup. Report first/last eight accuracy, lag-block norms, calibration condition/RMSE, clean/noise decomposition, sampled peaks and conditional laser power. No post-hoc retuning.

## Counts and matched comparisons

3*12+2*7=50 method/settings; 500 primary seed rows, 100 groups, 50 common-drive tuples, 1500 resolution rows, 300 resolution groups, 9 optical audits, 6 convergence comparisons. 30 coefficient records (18 fresh, 12 frozen). At candidates every eight ridge methods vs four anchors (32 comparisons), fresh Ridge16 variants vs same-lambda frozen (2), Ridge24 and Ridge32 variants vs matching fresh Ridge16 (4), Ridge32 variants vs matching Ridge24 (2): 40 unique pairs per candidate. Controls original 13 pairs each. (3*40+2*13)*10*8=11680 paired raw rows, 292 aggregate paired summaries. Verify exact keys, both marginals, counts and summary identities, coefficient provenance and all inherited regression/energy/causality checks. Keep all failures. Report separately matched fresh history comparisons, frozen-to-fresh calibration differences, and exploratory gate outcomes. Repeated decisions are not independent observations.

## Decision

If any candidate passes both drives and both frozen positive controls pass, propose independent confirmation with disjoint panels and immutable coefficients; rank faster cadence, lower LO, lower cutoff, fewer taps, greater worst-case margin, then fixed method order. No new confirmed cadence from this exploratory sweep. If no extended-history improvement, investigate alternative noise-aware calibration or optical/matched receiver architecture in a separately preregistered experiment; avoid repeatedly tuning against existing test labels. Confirmed baseline 23.8095238095 Gsymbol/s. 25 Gsymbol/s and 200 Gsegment/s aggregate feature rate are modeled, not measured throughput or ADC feasibility. No physical BER, system power, or general AI accuracy claim.
