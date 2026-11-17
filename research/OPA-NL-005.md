# OPA-NL-005 — Distributed saturable absorber propagation

Status: preregistered conditional physical compact model, not a calibrated material/device.
Builds on [NL004](OPA-NL-004.md) and the archived NL003 weights.

## Evidence and model choice

Primary sources rechecked 17 November 2026:

- Reep et al., [Scientific Reports 15, 9399 (2025)](https://doi.org/10.1038/s41598-025-93051-z), section 3.1 and Fig. 2: 75 um SOI graphene absorber, 1550 nm, 5 ps sech-squared pulses. Reported saturation powers 67.5 and 287 mW at -2 and -3 V; modulation depths 1.3 and 2.7%. Power is peak power before the input grating. Each grating contributes approximately 5.5 dB. Silicon two-photon absorption competes with graphene bleaching. Applying the nominal input grating factor 10^(-5.5/10) gives approximately 19.0 and 80.9 mW peak power immediately after coupling, not measured local CW saturation powers. Neither value calibrates our equation. The reported modulation depth definition must be resolved from supplementary measurements.
- Liu et al., [Light: Science & Applications 15, 128 (2026)](https://doi.org/10.1038/s41377-025-02175-4), Fig. 2: graphene/silicon photonic crystal cavity, 4 fJ half-saturation pulse-energy threshold, 1.05 ps pump-probe FWHM, return within 2 ps; slow-light and resonant enhancement. No conversion to CW Psat or exponential recovery lifetime is justified by these numbers. The study also uses Kerr-induced resonance shifts, not captured by a straight-waveguide propagation model.
- Chen et al., [Nature Communications 15, 9047 (2024)](https://doi.org/10.1038/s41467-024-53371-6), Fig. 3: MoTe2 butt-coupled waveguide absorbers with pulsed excitation and normalized transmission; alternative material candidate, not evidence for absolute C-band coherent transmission at our operating point.

The main article text is accessible; raw absolute complex transfer data and calibrated local CW parameters have not been obtained. The present experiment therefore models competing loss mechanisms without claiming a material fit. Slow-light enhancement and cavity coupling require a separate model; a reduced effective saturation scale is only a sensitivity parameter here.

## Propagation model

Let P be local guided power in mW, u=z/L normalized position. For illustrative length L=75 um:
dP/du = -P[A+B/(1+P/Psat)+C P].
A=-ln(Thigh), B=ln(Thigh/Tlow), C is integrated TPA coefficient in inverse mW. A/L and B/L are power-attenuation coefficients per length; C/L is a guided-power nonlinear loss coefficient, not bulk beta without modal area. Phase obeys dphi/du=phi_max P/(Psat+P). The phase law is hypothetical, not a measured Kerr coefficient. A and B are nonnegative; C>=0. At C=0, the transmission limits are Tlow and Thigh. For C>0, Thigh is the bleached linear-loss limit in the absence of TPA, not the actual asymptotic transmission. Extra fixed 1 dB loss is applied after propagation, as in NL004.

Use RK4 on log(P/P_in) and phase, preserving positive transmission. At zero power evaluate the limiting transmission without division by zero. Precompute transfer at 0 plus 2048 logarithmically spaced powers from 1e-12 to 4 mW. Compare 32/64/128 steps and independent geometric midpoint interpolation against direct 128-step integration. Require max fine error <1e-6 and midpoint interpolation error <1e-4 in transmission and phase radians. Verify all actual inference powers lie within the grid. Independently test Beer-Lambert, analytic linear-plus-TPA, low/high limits and phase equivariance.

## Preregistered sweep

Three endpoint pairs (Tlow,Thigh): (.1,.4) selected NL004 reference; (.15,.85) original NL003; (.373,.4) illustrative weak absolute depth .027, not measured graphene. Psat=.03,.1,.3,1,3 mW; integrated C=0,.1,1 /mW; maximum integrated phase=0,10,30 degrees. 135 propagation configurations per drive. At both drives .1 and 1 mW, use all five archived NL003 absorber weight sets (10 total), with new balanced XOR test domain 34 and independent paired noise domains 35/36. 2048 samples per seed, eight repeated draws. Same nominal receiver as NL003/004 (.1 mW LO, 1 GHz ENBW, 3 dB loss, 15 degree offset, absolute real activation noise .00316227766 sqrt(mW)). Compare original NL003 and selected NL004 lumped zero-phase reference on the same draws. No retraining or test-set tuning.

1350 seed-level rows, 270 grouped configurations, 20 reference rows, 135 convergence records and 8775 sampled transfer points. Descriptive screen unchanged: all five seeds clean and worst-repeat receiver accuracy >=95%, peak diode <=2 mW. Record output power, signed field margin, diode peak and clean passivity. Preserve all failures and prior archived evidence. Scientific failure does not fail CI; implementation checks do.

## Next steps

Analyze whether distributed attenuation invalidates the lumped reference, and sensitivity to competing TPA. Obtain absolute complex transmission and pulse-reference data, then fit device-specific parameters with uncertainty; separately investigate retraining for weak measured nonlinearities. No cavity, time-domain recovery, pulse-shape propagation or actual throughput validation in this experiment. No measured material calibration, fabrication readiness or system energy claim.

## Initial observed results — 17 November 2026

[Experiment run 44173789666](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44173789666),
job 134359706201, artifact 14368328417. All 15 implementation
checks passed. Maximum observed 64-to-128-step difference:
4.17764889349e-9; maximum geometric-midpoint interpolation
difference: 7.06007106743e-6, both below the preregistered
limits (1e-6 and 1e-4). These are numerical convergence checks
in transmission/phase radians, not physical model validation.

| Endpoint pair (Tlow, Thigh) | Low-drive pass/tested | High-drive pass/tested |
|---|---:|---:|
| (.1,.4) | 19/45 | 19/45 |
| (.15,.85) | 26/45 | 22/45 |
| (.373,.4) | 0/45 | 0/45 |
| Total | 45/135 | 41/135 |

86 of 270 configurations pass the original screen (31.85%).
The endpoint pairs refer to transmission limits without competing
TPA, before the extra 1 dB loss. With TPA, they are not actual
asymptotic transmission limits. Stronger-depth families contain
passing distributed propagation configurations at both drives;
the weak-depth family fails for every tested tuple. The aggregate
counts do not identify whether individual TPA>0 or phase>0 tuples
pass, nor whether the same tuple passes at both drives. No continuous
feasible range or material yield can be inferred. The frozen weights
were trained on the original lumped behavioral transfer; retraining
could change these conclusions.

### Paired lumped references on independent test inputs

All 20 reference rows have 100% clean accuracy. Mean receiver
accuracy, worst seed/repeat, mean pre-receiver output, minimum
signed real output field and peak modeled diode power:

| Drive mW | Reference | Mean receiver (%) | Worst repeat (%) | Output uW | Min signed field sqrt(mW) | Peak diode mW |
|---:|---|---:|---:|---:|---:|---:|
| 0.1 | NL003 | 99.997559 | 99.951172 | 0.605474 | 0.009973 | 0.061623 |
| 0.1 | NL004 | 100.000000 | 100.000000 | 0.684373 | 0.013409 | 0.061301 |
| 1 | NL003 | 100.000000 | 100.000000 | 24.696931 | 0.092201 | 0.117148 |
| 1 | NL004 | 100.000000 | 100.000000 | 6.651222 | 0.039782 | 0.087922 |

NL003 low-drive reference has two incorrect sample/repeat
outcomes out of 81,920 (seeds 1301 and 1303, one each).
NL004 low-drive and both high-drive references have zero errors.
Each drive/reference uses 10,240 held-out inputs with eight
paired simulated noise repeats, not 81,920 independent
hardware measurements. These references are lumped transfer
functions, not distributed candidates or a material fit.

### Archive and remaining work

Exact ZIP metadata: 203,565 bytes, SHA-256
245f80ef6e95de5a7dcc736811028d1389fd973a6fb5b284039bd1092d758d00.
The archive helper pins all six science-file hashes emitted
by CI, verifies raw ZIP identity, CRC, report counts and staged
bytes, and records environment metadata and provenance.
Actual ZIP-byte verification awaits manual archive execution.
Initial analysis uses CI stdout only. Full parameter-level
analysis of the 1350 metrics, 270 grouped configurations,
135 convergence rows and 8775 transfer samples follows archival.

Next identify passing TPA/phase combinations, common tuples,
comparison with the paired lumped references and practical
transmission curves within the tested power range. No calibrated
graphene parameters, cavity dynamics, throughput, hardware
performance or system energy advantage established.
