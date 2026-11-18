# OPA-NL-011 — Receiver bandwidth, local oscillator and late integration

Status: implemented and executed; initial CI-report analysis below, raw archive pending.
Parent: [NL010 protocol and initial results](OPA-NL-010.md), [verified archive](../results/opa-nl-010/provenance.json), experiment run 44283625212, archive run 44285931563, archive merge 565d2af6aeab01f48a45a93efb2eac59c7e690c1.

## Detailed NL010 archive analysis

Read all 336 primary summary rows and 1680 primary seed rows. Join by candidate, on_ps, gap_ps, response_ps, lo_mw, fc_ghz, readout and drive_mw; five seeds per key. The minimum combined_worst and all-seed combined_pass agree with summary for every group. Counts below use inherited screen, not a new gate.

| Drive mW | Groups | Stationary eligible and unfiltered >=95% | Also clean filtered >=95% | Electrical pass | Combined pass |
|---:|---:|---:|---:|---:|---:|
| .1 | 168 | 168 | 52 | 19 | 13 |
| 1 | 168 | 168 | 34 | 31 | 31 |
| Total | 336 | 336 | 86 | 50 | 44 |

Maximum sampled combined diode power .6242026019729476 mW, no group exceeds the hypothetical 2 mW cap. Six electrical-only passes fail combined noise, all at .1 mW; zero combined-only passes. Filtering dominates gate attrition across this sampled grid, not necessarily at the optimum. Low drive is more noise-limited among clean-passing configurations; high drive exhibits substantial deterministic filter error. Different frozen drive-specific networks confound attribution to drive alone.

| Cutoff GHz | Clean pass /56 | Electrical pass | Combined pass |
|---:|---:|---:|---:|
| 1 | 0 | 0 | 0 |
| 5 | 8 | 8 | 6 |
| 10 | 10 | 8 | 7 |
| 20 | 16 | 10 | 10 |
| 40 | 24 | 12 | 10 |
| 80 | 28 | 12 | 11 |

LO paired comparisons (.1 versus 1 mW), holding timing, drive, cutoff and readout fixed: 20 both, 0 low-only, 4 high-only, 144 neither. End versus half_mean readout: 12 both, 14 end-only, 6 half_mean-only, 136 neither. Counts depend on the sampled grid and include the long 200 ps control; they do not identify a universal best setting.

### Best observed shared receiver settings by timing

Rank by maximin combined_worst across both drives, including failing groups; ties use first archive order. This is retrospective selection, not independent validation.

| Candidate | On/gap/response ps | LO mW | Cutoff GHz | Readout | Worst .1 mW | Worst 1 mW |
|---|---|---:|---:|---|---:|---:|
| C2 | 30/0/0 | 1 | 80 | end | 80.273438% | 71.875000% |
| C2 | 35/0/0 | 1 | 80 | end | 86.914063% | 88.867188% |
| C2 | 40/0/5 | 1 | 40 | end | 89.843750% | 90.820313% |
| C2 | 50/0/5 | 1 | 20 | end | 95.117188% | 99.414063% |
| C2 | 200/0/50 | 1 | 5 | end | 97.851563% | 100% |
| C1 | 30/20/0 | 1 | 40 | end | 82.812500% | 88.085938% |
| C1 | 35/20/5 | 1 | 40 | end | 87.500000% | 98.632813% |

At 25 Gsymbol/s (C2 40 ps, response 5 ps), 1 mW drive, LO 1 mW, cutoff 80 GHz, end readout: clean minimum 98.6328125%, electrical worst 96.875%, combined worst 95.8984375%, peak .6195079184175071 mW. Only this single drive group passes at 25 Gsymbol/s. At .1 mW the best tested combined worst is 89.84375% (40 GHz, LO 1 mW, end), despite perfect clean minimum; the low-drive optimum does not match the high-drive optimum.

At 28.571 Gsymbol/s the best shared setting has clean minima 100% and 90.234375%, electrical worst 88.0859375% and 89.2578125%, combined worst 86.9140625% and 88.8671875% at .1/1 mW. No tested high-drive clean filter group passes at that timing. At 20 Gsymbol/s (C2 50 ps) the common passing setting has clean minima 100% and 99.8046875%, electrical worst 97.8515625% and 99.609375%, combined worst 95.1171875% and 99.4140625%; sampled diode maxima .5287398875911969 and .6199470948431993 mW. Minimum clean signed current margins 3.933717617300618e-6 and -8.446582004241557e-7 A. First-eight combined accuracy minima 97.0703125% and 98.4375%, last-eight minima 96.2890625% and 99.609375%; these are across seed-level mean-repeat window metrics, not worst-repeat windows.

The 1.64 MB resolution_metrics.csv could not be assumed accessible through the connector; this analysis uses primary rows and prior verified CI convergence, not a new seed-level resolution audit.

## Preregistered experiment

Question: can fixed causal receiver settings preserve the all-five-seed combined-noise gate at nominal 25–30 Gsymbol/s at both drives? No retraining, phase fitting, threshold fitting, adaptive windows or feedback using test labels. Preserve NL010 C2 parameters, frozen drive-specific NL003 weights, TCMT waveform, optical losses and 15 degree phase. Focus on zero-gap C2; no claim about C1 or other architectures.

Primary timing grid (on ps, material response ps): (35,0), (35,5), (37.5,5), (40,5), (45,5), (50,5). Include (40,0) to separate timing and response at matched on duration. Add 200 ps / 50 ps long control. All zero gap. 35–40 ps cover 25–28.571 Gsymbol/s; 30 Gsymbol/s is an aspirational target outside this grid, not a tested speed. Instantaneous closure is diagnostic, not a measured material response.

Receiver grid: cutoff 20,30,40,60,80,120 GHz; LO .1,1,2,3 mW; readout end-of-on, mean over final 1/8, final 1/4, final 1/2 of on interval. All means normalized by their physical window duration. Include original NL010 .1/1 mW, 20/40/80 GHz, end/half_mean as paired anchor subset. Higher LO is a hypothetical sensitivity test, not a recommendation: detector cap remains 2 mW per diode, and signal plus LO laser lower-bound power increases. No higher LO beyond 3 mW in this study. Report measured-in-model peak, not assume cap compliance. No new optical gain or modified noise coefficients in primary grid.

Eight timing cases x six cutoffs x four LO x four readouts x two drives x five seeds = 7680 primary seed rows; 1536 groups. Each row includes separate clean, electrical and combined arms. Fresh independently generated balanced jittered XOR (512 examples per seed/drive, eight independent 64-symbol streams), five frozen seeds, eight noise repeats. Audit domains against NL001–010, reserve 94–98 for dataset, permutation, optical offsets, initial receiver state and segment innovations only if unused. Pair data and noise across receiver settings, resolutions and drives. Keep frozen seeds and no label-based selection.

## Receiver implementation and verification

Reuse NL010 causal single pole and exact joint segment covariance, including signal-dependent shot PSD, total differential TIA and residual LO RIN; inherited real symbol-held optical noise in combined arm only. Use common segment Gaussian latents (distributional coupling, not Brownian-path identity). Partition each on interval at fractions 1/2, 3/4, 7/8, 1; carry state through all segments and symbols. Compute each window from the same trajectory via duration-weighted segment means, not separate noise draws per readout. Use integer grid alignment for all readout boundaries: choose dt per timing as on/(8*n), with n=ceil(on/(8*.25)), then halve twice; record actual dt and exact durations. Compare all cases at coarse, half and quarter dt (<=.25, <=.125, <=.0625 ps). Preserve NL010 tolerances unless a reviewed preregistration amendment changes them. Gate disagreement across two finest resolutions flagged and excluded from confirmed passes; report all differences, no silent omission. Validate arbitrary segment partition and recombined covariance against independent stepwise state/mean recurrence, nonuniform duration-weighted readout windows, analytic constant/step response and stationary noise, matched NL010 anchors on same synthetic waveform, exact first-symbol optical cold/stream equality, energy and passivity, hybrid conservation and diode peak at both sides of optical-offset discontinuities. Validate complete grid and row counts (23040 resolution rows if all three resolutions), finite values, frozen weight and prior archive hashes. Budget runtime/memory with pilot; if necessary deterministic partitions by timing, preserve paired RNG and check exact global keys before aggregating. No science failure fails CI.

Primary gate remains all five seeds stationary eligible, unfiltered and clean filtered accuracy >=95%, worst of eight combined-noise repeats >=95%, sampled combined diode peak <=2 mW. Electrical-only gate separate. Output all primary and resolution groups, seed metrics, first/last eight windows, signed current margins, optical memory, electrical noise variance/lag, sampled peaks and energy terms. Rank common-drive confirmed tuples by sampled cadence and report all ties; for each timing also report maximin worst-repeat accuracy regardless of gate and reason for gate failures. Report LO electrical lower bound LO/.20, signal laser launch average/.20 and sum as conditional lower bounds excluding electronics, distribution and phase lock; no total efficiency claim. Compare readouts using paired groups and same trajectory. No adaptive equalization in NL011; if late windows and increased LO fail, a separately preregistered causal equalizer or alternative receiver architecture may follow, with independent calibration data and held-out tests.

## Independent follow-up

Any passing receiver setting selected from NL011 is exploratory on its test grid. Confirm it in a subsequent experiment with independently generated inputs/noise and longer streams before presenting it as robust. No measured hardware speed, BER, energy advantage, device feasibility or general AI accuracy established.

## Initial results — 18 November 2026

Source [experiment run 44288710042](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44288710042), job 134748083271, PR 167, artifact 14421271696. All 17 implementation checks passed. 7680 primary seed rows, 1536 primary groups, 23040 resolution rows and 4608 resolution groups, 24 optical audits and 16 convergence comparisons. Runtime 587.726 seconds. This analysis uses the CI-emitted JSON report; full raw CSV analysis and independent archive verification remain pending.

328/1536 combined groups passed and were numerically confirmed. 108/768 common-drive tuples pass at both drives, of which 35 are C2 50 ps on, 5 ps response (20 Gsymbol/s) and 73 are the 200 ps / 50 ps control (5 Gsymbol/s). No tested faster timing passed at both drives. No ambiguous group and zero changes in seed/group gate status across all 16 comparisons. The 328 passing drive groups imply 216 both-drive-group members and 112 passing single-drive groups, but the JSON subset does not identify which drive for those 112. Counts are not comparable as an effectiveness ratio to NL010's different grid and independent data.

### Best maximin receiver settings by timing (all ties)

| On ps | Response ps | LO mW | Cutoff GHz | Readout | Worst .1 mW | Worst 1 mW | Both pass |
|---:|---:|---:|---:|---|---:|---:|---|
| 35 | 0 | 2 | 80 | end | 88.085938% | 88.281250% | no |
| 35 | 0 | 3 | 80 | end | 88.085938% | 88.281250% | no |
| 35 | 5 | 2 | 80 | end | 83.398438% | 83.203125% | no |
| 35 | 5 | 3 | 80 | end | 83.398438% | 83.203125% | no |
| 37.5 | 5 | 3 | 60 | end | 87.500000% | 87.890625% | no |
| 40 | 5 | 3 | 40 | end | 90.625000% | 90.820313% | no |
| 45 | 5 | 3 | 30 | end | 94.531250% | 97.656250% | no |
| 50 | 5 | 2 | 120 | quarter_mean | 96.093750% | 99.804688% | yes |
| 50 | 5 | 3 | 20 | end | 96.093750% | 99.609375% | yes |
| 50 | 5 | 3 | 80 | eighth_mean | 96.093750% | 100.000000% | yes |
| 50 | 5 | 3 | 120 | quarter_mean | 96.093750% | 99.804688% | yes |
| 40 | 0 | 3 | 40 | end | 93.945313% | 95.507813% | no |
| 200 | 50 | 2 | 40 | quarter_mean | 98.632813% | 100.000000% | yes |
| 200 | 50 | 3 | 40 | quarter_mean | 98.632813% | 100.000000% | yes |

The closest finite-response point above 20 Gsymbol/s is 45 ps, 5 ps response, LO 3 mW, cutoff 30 GHz, end readout: 94.53125% and 97.65625% worst repeat at .1/1 mW. The low-drive deficit is .46875 percentage points (three additional correct classifications would meet the 487/512 threshold; 484/512 observed versus 487/512 required). At 40 ps, 5 ps response, best common-drive accuracy is 90.625%; instantaneous closure at the same duration gives 93.9453125%, still below threshold. Do not present instantaneous closure as measured material speed. The best 35 ps finite-response result is 83.203125%. Maximin rankings include failures and are retrospective, not independently validated.

### Receiver tradeoff at 20 Gsymbol/s

Among the 35 common-drive passing tuples at 50 ps, LO counts (.1,1,2,3 mW) are 0,11,12,12; readout counts (end,eighth_mean,quarter_mean,half_mean) are 9,14,12,0. The original 1 mW / 20 GHz / end setting passes again on independent NL011 draws (low-drive worst 95.5078125%, clean 100%, electrical-only worst 97.8515625%, sampled low-drive peak .5268138641566373 mW). Its exact high-drive accuracy is not in this JSON subset. The best maximin accuracy is 96.09375% shared by four settings; the lowest LO among these is 2 mW, 120 GHz, quarter_mean, giving 96.09375% and 99.8046875% at .1/1 mW. At assumed 20% laser conversion efficiency, LO-only electrical power lower bounds are 5,10,15 mW for 1,2,3 mW LO. This does not include signal launch, receiver electronics, distribution, ADC or phase control. More LO does not necessarily improve the limiting rate. A conditional power-accuracy Pareto analysis needs the full seed CSV.

### Numerical evidence and limits

Maximum endpoint error 5.911444476124354e-10 sqrt(mW), common-grid waveform error 3.1684383104613736e-9 sqrt(mW), clean decision error 2.8801995021032864e-8 A, noisy decision error 2.8806896928810664e-8 A, sampled diode peak error 1.7515214043584137e-6 mW. Partition regression current/covariance errors 1.4907779871675686e-19 A and 1.3728045331342105e-14 relative. Stationary long-sequence variance ratio 1.0012673236303482, lag 0.28528539589534957 versus expected 0.28460954333602934, mean variance ratio 1.0033964410261738. These verify numerical implementation, not device behavior. No measured hardware rate, BER, energy efficiency or general AI accuracy established.

### Archive and follow-up

Original ZIP 2132487 bytes, SHA-256 89ce5da2a5000e58dc67fcd121ee2e0d7801d5048af9806ebdf3033ab47e19b2. The manual archive workflow pins run, artifact, ZIP and ten original file hashes and verifies staged bytes. After archival, analyze all 1536 groups, 768 common-drive pairs and seed metrics: clean versus electrical versus combined gate attrition by timing and drive, sampled diode failures, paired LO/readout effects and conditional power tradeoffs. Do not infer global gate counts or causes from the passing subset. NL012 should investigate a fixed causal equalizer or alternative receive filter only after this diagnosis; independently calibrate on separate inputs, freeze coefficients before held-out testing, include unequalized anchors and noise-amplification/power costs. An independent longer-stream confirmation of a low-LO 20 Gsymbol/s anchor and a prespecified 45 ps neighborhood is also useful. No new protocol approved here.
