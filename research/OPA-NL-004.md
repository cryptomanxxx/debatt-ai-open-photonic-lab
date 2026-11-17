# OPA-NL-004 — Saturable absorber physical requirements envelope

Status: preregistered conditional compact-model screen, not a calibrated material simulation.
Builds on [NL003](OPA-NL-003.md). The first step toward a physical
component is to determine its required transmission, saturation and phase
characteristics. Full material fitting remains blocked by missing
reference-plane, waveform and complex-transmission data.

## Primary experimental literature and limitations

| Source | Reported experimental quantities | Why not directly a CW device model |
|---|---|---|
| [Femto-joule threshold reconfigurable all-optical nonlinear activators for picosecond pulsed optical neural networks](https://doi.org/10.1038/s41377-025-02175-4) | Graphene/silicon photonic crystal cavity; 4 fJ pulse-energy threshold at 50% saturation; pump-probe response FWHM about 1.05 ps, return within 2 ps | Pulse energy is not power; cavity enhancement, pulse shape and complex transmission required |
| [Ultrafast Silicon/Graphene Optical Nonlinear Activator for Neuromorphic Computing](https://doi.org/10.1002/adom.202401686) | 5.49 mW threshold, 93.6 ps response, reported 0.51 pJ activation | Threshold is not automatically the half-saturation parameter of our equation; phase and reference plane not established here |
| [Ultrafast and energy-efficient all-optical switching with graphene-loaded deep-subwavelength plasmonic waveguides](https://doi.org/10.1038/s41566-019-0547-7) | 35 fJ switching energy, 260 fs switching time; 30 by 20 nm plasmonic waveguide | Switching experiment, not a calibrated signed-field activation |
| [Graphene absorber on an SOI chip for active and passive mode locking of lasers](https://doi.org/10.1038/s41598-025-93051-z) | 75 um device, -2 V: reported 1.3% modulation depth and 67.5 mW saturation power; -3 V: 2.7% and 287 mW | Input pulse peak power before chip coupling; about 5.5 dB loss per grating; silicon two-photon absorption also observed; bias and measurement normalization matter |

These quantities are from accessible primary article abstracts and
indexed article passages, checked 2026-11-17. Full article access for
the cavity and SOI studies was blocked by publisher/browser checks.
No digitized curves or complete supplementary data have been verified.
The source-specific modulation-depth conventions must be established
before fitting absolute transmission. Do not equate pump-probe FWHM
with a single exponential lifetime, threshold with Psat, or pulse
energy divided by response time with a measured CW saturation power.

The prior OPA model assumed Tlow=.15, Thigh=.85, Psat=1 mW and
phase-preserving amplitude transmission. These are hypothetical,
not measured graphene constants.

## Preregistered static requirements screen

For signed/complex field E in sqrt(mW), q=|E|²/Psat:
T=10^(-1/10)*(Thigh-DeltaT/(1+q)).
Eout=E*sqrt(T)*exp(i*phi_max*q/(1+q)).
DeltaT is absolute power-transmission difference before the common
1 dB excess loss. Phase is a hypothetical intensity-dependent phase,
not a fitted material dispersion. T must be between zero and one.

Sweep Psat=.01,.03,.1,.3,1,3,10,30,100 mW; DeltaT=.013,.027,.1,.3,.5,.7;
Thigh=.4,.85 (exclude DeltaT>=Thigh); phi_max=0,10,30 degrees.
The small depth cases are illustrative weak nonlinearities motivated
by reported percent-scale modulation, not reproductions of the SOI
measurement. No parameter tuple is designated a physical device.
There are 270 valid transfer combinations per drive.

Use all ten archived NL003 absorber weight sets (five seeds per
drive .1 and 1 mW). Verify archived weights, result and receiver hashes
against provenance. No weight updates or selection. New held-out
domain 24, 2048 balanced jittered XOR inputs per seed, independent
noise domains 25/26 and eight paired noise repeats. The original
behavioral tuple (1,.7,.85,0) is retained as comparison at each drive.
Use NL003 nominal receiver (.1 mW LO, 1 GHz ENBW, 3 dB loss, 15 deg
offset, .00316227766 sqrt(mW) real activation-output noise). Complex
activation phase is propagated through the second real matrix.
No retraining in this experiment; future retraining must be separately
reported and not confused with frozen-weight transfer.

2700 seed-level rows, 540 configurations. Descriptive screen:
all five seeds >=95% clean and worst-repeat receiver accuracy,
and all modeled diode peaks <=2 mW. This is a requirements screen,
not a new claim of optical advantage or physical feasibility.
Report all rows, including failures, without tuning on test data.

## Separate illustrative dynamics

Use a lumped normalized bleaching state b in [0,1]:
db/dt = (q(1-b)-b)/tau. Constant-power exact solution:
b(t+dt)=q/(1+q)+(b(t)-q/(1+q))*exp(-(1+q)*dt/tau).
At zero power, recovery is exponential with time constant tau.
A fresh state starts at zero; apply a half-period rectangular
on interval then a half-period off interval. Sweep q=.1,1,10,
tau=1,10,100 ps, period=10,100,1000 ps (27 cases).
Report fraction of steady state reached and residual fraction.
These are hypothetical state dynamics, separate from the static
XOR classifier; no pulse train, cavity lifetime, propagation,
carrier heating, phase recovery or data-rate validation is modeled.

Implementation checks: baseline transfer equality, phase
equivariance, equilibrium, exact-step semigroup, dark recovery,
counts, clean passivity, finite fields and archive immutability.
Artifacts: metrics.csv, summary.csv, transfer_checks.csv,
dynamics.csv, result.json plus locked environment; emit hashes.

## Next step after this screen

Obtain full measured transmission and phase curves, coupled power
or calibrated pulse energy/shape, geometry/modal overlap, linear
and nonlinear propagation loss, bias and recovery measurements.
Select a physical platform only when comparable reference planes
and units are established. Fit a device-specific propagation or
cavity rate model with uncertainty and independent validation;
then perform frozen deployment and separate retraining. No physical
model calibration, fabrication readiness, energy advantage or
actual activation bandwidth established by NL004.

## Initial observed results — 17 November 2026

[Experiment run 44169138855](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44169138855),
job 134343269714, artifact 14366547319. All 13 implementation checks
passed, including equivalence to the original behavioral absorber,
phase equivariance, exact-state equilibrium/semigroup/dark recovery,
counts, passivity, finite fields and immutable NL003 evidence.

| Drive (mW) | Configurations screened | All-seed screen pass | Fail |
|---|---:|---:|---:|
| .1 | 270 | 30 | 240 |
| 1 | 270 | 32 | 238 |
| Total | 540 | 62 | 478 |

The screen requires >=95% clean and worst-repeat receiver accuracy
for every seed and peak modeled diode power <=2 mW. 11.48% of the
tested configurations pass. This fraction describes a discrete
hypothetical grid, not a probability over materials or a yield
prediction. Frozen weights were trained on the original behavioral
transfer; failures do not demonstrate that separate retraining
or alternative architectures cannot work.

The baseline tuple (Psat=1 mW, DeltaT=.7, Thigh=.85, phi=0 degrees)
passes for every seed at both drives with 100% clean, mean receiver
and worst-repeat receiver accuracy on fresh domain-24 test inputs
and independent domains 25/26 for noise. At .1 mW there are
81,920 correct sample/repeat outcomes out of 81,920 (10,240 distinct
held-out inputs, eight receiver/activation noise repeats); same
count at 1 mW. These are repeated simulated outcomes, not a
measured BER or evidence of independent 81,920 physical inputs.

| Seed | .1 mW output mean (uW) | 1 mW output mean (uW) | .1 mW peak input per channel (mW) | 1 mW peak input per channel (mW) |
|---|---:|---:|---:|---:|
| 1301 | .641673 | 27.933094 | .291529 | 2.838915 |
| 1302 | .552743 | 23.573097 | .287577 | 2.127249 |
| 1303 | .576889 | 21.087714 | .290993 | 1.951717 |
| 1304 | .605004 | 22.299626 | .285229 | 2.182471 |
| 1305 | .632170 | 27.991379 | .290848 | 2.793078 |

The per-channel activation input peak is not the global drive
scale or aggregate optical launch. The minimum signed real
output margin among seeds is .009870 sqrt(mW) at low drive and
.092708 sqrt(mW) at high drive. Peak modeled per-diode power
is .061798 mW and .117038 mW respectively, below the hypothetical
cap. No physical diode saturation or measured throughput is
established. The receiver uses the NL003 nominal assumptions.

## Evidence archival and remaining analysis

Exact source ZIP metadata: 150,226 bytes, SHA-256
d5f3aafe2b46ec73f8fd8bf5484e93639b710c1684ebd5c3de96602c79fe7ee9.
The archive helper pins all five science-file sizes and SHA-256
digests from CI stdout and verifies raw ZIP identity, CRC, names,
report counts and staged bytes, including environment and provenance.
Actual ZIP verification awaits execution of the manual archive
workflow. The initial observations above use CI stdout only;
the detailed 540-row summary and 2700-row metrics are not yet
permanently archived or analyzed here.

After archival, identify minimum tested DeltaT, successful Psat
ranges, high-transmission and phase sensitivity, worst-seed
margins, and the intersection of passing component tuples between
drives. Analyze the 27 illustrative recovery cases separately.
Do not interpret an isolated grid pass as a continuous feasible
interval. No calibrated material, actual activation rate or
material-level feasibility conclusion follows from this screen.
