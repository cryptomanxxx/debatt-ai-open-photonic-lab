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
