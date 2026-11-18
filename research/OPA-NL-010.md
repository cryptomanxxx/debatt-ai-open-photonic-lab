# OPA-NL-010 — Dynamic balanced optical receiver

Status: proposed protocol for review, not implemented or run.
Parent: [NL009](OPA-NL-009.md), [verified evidence](../results/opa-nl-009/provenance.json), experiment run 44197189683, archive run 44277660202, archive merge 174355d7bd5239b20d1d467fb42a68378cc26dda.

## NL009 paired archive analysis

Pair all 720 summary rows by candidate, response_ps, on_ps, gap_ps and drive_mw, using archived screen_pass and five seeds per group.

| On ps | Both pass | Cold only | Stream only | Neither |
|---:|---:|---:|---:|---:|
| 10 | 0 | 0 | 0 | 36 |
| 15 | 0 | 0 | 0 | 36 |
| 20 | 0 | 0 | 0 | 36 |
| 25 | 0 | 0 | 1 | 35 |
| 30 | 6 | 4 | 0 | 26 |
| 35 | 13 | 5 | 0 | 18 |
| 40 | 20 | 8 | 0 | 8 |
| 45 | 23 | 7 | 0 | 6 |
| 50 | 25 | 5 | 0 | 6 |
| 200 | 36 | 0 | 0 | 0 |
| Total | 123 | 29 | 1 | 207 |

At .1 mW: 62 both, 0 cold-only, 0 stream-only, 118 neither. At 1 mW: 61 both, 29 cold-only, 1 stream-only, 89 neither. The stream-only case is C2, 25 ps on, 20 ps gap, instantaneous response, 1 mW. Group gate transitions are not causal isolation of a particular mechanism; no implication that individual scores always worsen. The .1 mW groups may have nonzero memory despite unchanged gate status. Different drive-specific frozen networks confound direct comparisons.

All 110 confirmation rows pass; maxima of field_error, energy_error and max_balance are respectively 6.523036175843058e-9 sqrt(mW), 2.179226496884468e-8 and 8.201298210240525e-10. These are numerical checks, not physical validation.

C2 35 ps, instantaneous response, zero gap: at 1 mW cold worst repeat 100%, stream 96.6796875%, maximum stream-cold classifier field difference .041808187 sqrt(mW). At .1 mW cold 96.875%, stream 97.0703125%. C2 40 ps, 5 ps response, zero gap: at 1 mW both worst repeats 100% despite max memory .038180851 sqrt(mW). At .1 mW cold 97.265625%, stream 97.4609375%. Do not infer memory-free operation from perfect accuracy. The archived metrics, positions and traces exceed connector retrieval limits; seed/position/trace-level analysis is deferred to a local or CI analysis script, not represented as completed.

## Question and scope

Can a causal balanced homodyne receiver retain the inherited accuracy gate at the fastest sampled common-drive NL009 timings when bandwidth, integration and temporally correlated electrical noise are modeled together? This is a conditional receiver model, not measured hardware. Preserve NL009 TCMT parameters and NL003 frozen weights, no retraining, adaptive sampling, equalization or threshold selection on test labels.

Primary C2 timings (on, gap, material response in ps): (35,0,0), (40,0,5), (50,0,5), (200,0,50). Add C1 (30,20,0), (35,20,5), C2 (30,0,0) as below-boundary diagnostic. Seven predefined candidate/timing cases. Both drives .1/1 mW, five frozen seeds per drive, fresh balanced jittered XOR 512 samples per seed/drive, eight independent 64-symbol streams, label-blind shuffle, eight noise repeats. Reserve fresh RNG domains after auditing earlier code; paired inputs and noise innovations across receiver conditions. Include cold optical resets only as separate diagnostics; primary stream carries cavity and receiver state. Do not infer throughput from a cold reset.

## Continuous signal and balanced detection

Generate the complex activation drop waveform using the NL009 TCMT RHS with the same rectangular excitation, including gap evolution, fixed 1 dB attenuation and frozen second MVM at each integration time. Receiver input e(t) is the complex classifier field in sqrt(mW), not end-of-slot samples interpolated into pulses. Convert to sqrt(W), apply 3 dB signal-only loss and fixed 15 degree phase, LO at hybrid input. Use NL003 ideal hybrid and responsivity R=.9 A/W:

    Pplus/minus = |e_W(t) +/- sqrt(P_LO)|^2 / 2
    I(t) = R*(Pplus-Pminus)

Check power conservation at all evaluated times. Track both diode powers before filtering, not merely decision sample power; 2 mW is the inherited hypothetical cap. Use LO .1 and 1 mW; phase/loss fixed. This is an electrical bandwidth abstraction, no optical filter, ADC, timing jitter, phase-lock or material calibration.

## Electrical filter and integration

Single-pole causal unity-DC-gain low-pass, H(f)=1/(1+i*f/fc), dy/dt=2*pi*fc*(I-y) in seconds. Sweep fc=1,5,10,20,40,80 GHz. Distinguish fc from one-sided ENBW pi*fc/2. Use exact exponential state transition for piecewise constant midpoint current, or a verified equivalent convergent method. State persists throughout on/gap and across symbols. Two fixed readouts: end-of-on filtered sample and average of filtered output over final half of on interval. Integrate continuously, including receiver noise. No gap samples used for decisions; gap evolves receiver state. Fixed zero threshold and initial zero mean signal filter state, independent streams. Record initial-state convention and first/last eight-symbol metrics. No claim beyond 64 symbols.

For deterministic current input, exact piecewise constant segment of length dt has decay a=exp(-lambda*dt), end state a*y+(1-a)*I, integral I*dt+(y-I)*(1-a)/lambda. Use ps-to-s conversion explicitly. Compare .25 and .125 ps on all primary waveforms, with .0625 ps at detected gate boundaries and controls if needed; no interpolation of outcomes. Use shared nested noise innovations or exact joint state/integral covariance for stochastic convergence, not independent draws at each dt.

## Noise model

Use inherited shot, total differential TIA and residual LO RIN assumptions from NL003 (Q, R, TIA=15 pA/sqrt(Hz), RIN=-145 dB/Hz, CMRR=20 dB). One-sided local current PSD S_I(t)=2*Q*R*(P_signal(t)+P_LO)+TIA^2+(R*P_LO)^2*RIN*10^(-CMRR/10), units A^2/Hz. Gaussian diffusion with two-sided intensity S_I/2 through the same causal filter, not independent per-symbol noise. For constant S over a step, exact OU increment variance S*lambda/4*(1-a^2); stationary variance S*pi*fc/2. For integration use exact joint Gaussian increments for end state and integrated state (or a numerically verified convergent approximation); verify covariance and positive semidefiniteness against analytic formulas. Initialize noise at LO-only stationary variance for each independent stream, zero deterministic current. PSD is conditional on clean midpoint optical power; explicitly distinguish hypothetical optical-noise extension.

Retain a separate paired optical-noise sensitivity arm: inherited absolute activation-field perturbations at each channel with .003162 sqrt(mW) scale (confirm exact NL006 NOISE), held over on interval, zero in gap, projected by frozen second MVM; same draws across configurations. Apply before detector, include its contribution to diode power and shot PSD in that arm. This is a hypothetical symbol-held optical noise model, not a measured optical PSD. Do not double count inherited independent 1 GHz receiver draws. Clean filter, electrical-noise-only and combined-noise results reported separately.

## Counts and criteria

7 timing cases x 2 LO x 6 cutoff x 2 readouts x 2 drives x 5 seeds = 1680 primary seed rows, each with separate clean, electrical-only and combined noise statistics (or three explicitly labeled rows per seed, 5040 rows; choose and document before implementation). Primary pass per timing/LO/cutoff/readout/drive is all five seeds: stationary eligibility, clean unfiltered end-of-on real classifier accuracy >=95%, clean filtered accuracy >=95%, worst of eight combined-noise repeats >=95%, max combined diode <=2 mW. Report electrical-only gate separately. No cherry-picking cutoff or readout as a general result; list all combinations and common-drive tuples. Report nominal cadence 1/(on+gap), cutoff, ENBW, integration window, mean/worst accuracy, signed current margins, noise variance and lag correlations, diode peaks, optical memory and first/last position metrics. Science failures do not fail CI.

## Implementation verification

Before running: verify all NL009 archive hashes and NL003 weights; add reproducible CI-side analysis of NL009 large CSVs (paired counts, signed margins and first/last position summaries, trace coverage); preserve originals. Validate constant and stepped signal against analytic causal filter, numerical integration against exact segment integral, hybrid power conservation, phase/sign checks, analytic stationary noise variance and lag covariance, joint integration covariance, nested-resolution consistency, no resets within streams, gap handling and all first-symbol equality where appropriate. Use deterministic fixed RNG seeds and statistical tolerances specified before sampling; test noise implementation with independent synthetic long sequences, not classification success. Validate dt convergence of waveform, filtered current and integrated decision, diode peaks and gate agreement at boundary; document tolerances in implementation PR. Test no-noise high-cutoff limit toward instantaneous receiver (finite cutoff not exact), and low-cutoff memory counterexample. Check finite values, expected unique keys, archive immutability, passive MVM and inherited TCMT energy balance. Budget runtime/memory; stream waveform chunks or deterministic partitions, no silent omissions.

No hardware rate, BER, measured receiver parameters, wall-plug advantage or general AI performance established. Future material/receiver calibration and system power accounting remain separate tasks.
