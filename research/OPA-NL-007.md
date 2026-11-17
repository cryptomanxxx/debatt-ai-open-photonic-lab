# OPA-NL-007 — Nonlinear resonance shift and mechanism isolation

Status: preregistered numerical experiment, results pending CI.
Builds on the [archived NL006 cavity analysis](OPA-NL-006.md)
and [NL005 distributed references](OPA-NL-005.md).
The weak endpoint family passed three drive/configuration
groups in NL006, but its actual complex transmission
varied much more than the nominal absorption depth.
All three matched zero-shift controls failed. The next question
is whether amplitude variation, phase variation, or their
combination supports the frozen classifier, and whether
saturable absorption is necessary in the assumed cavity.

## Candidate definitions

Use the same symmetric two-port TCMT model, energy normalization,
port accounting, and all-root solver as NL006. No new physical
material parameter is inferred. Tuples below give the reference
endpoint pair, external lifetime in ps, hypothetical internal
saturation energy in fJ, normalized nonlinear loss b,
signed detuning d, and saturating shift h.

| Candidate | Tlow/Thigh | tau_ext | Us | b | d | h |
|---|---|---:|---:|---:|---:|---:|
| W1 | .373/.4 | 2 | 3 | 0 | -.5 | 1 |
| W2 | .373/.4 | 10 | 3 | 0 | -.5 | 1 |
| W3 | .373/.4 | 10 | 3 | .1 | -.5 | 1 |
| S1 | .1/.4 | 10 | .3 | 0 | 0 | 0 |
| S2 | .15/.85 | 10 | .3 | 0 | 0 | 0 |

W1–W3 were selected from the weak passing groups; S1/S2 are
strong endpoint references perfect at both drives in NL006.
All are tested at both drives, not just the previously
successful drive. These are post-hoc selected hypotheses,
tested on fresh independent inputs.

## Mechanism ablations

Let H(P) be the complex drop-port coefficient from NL006,
H0=H(0), and a_out=sqrt(10^(-.1))*H(P)*a_in.
Define seven modes:

- full: unchanged physical TCMT.
- amplitude_only: abs(H(P))*exp(i*arg(H0)).
- phase_only: abs(H0)*exp(i*arg(H(P))).
- linear: H0.
- no_bleaching: set ns_new=ns+sa and sa_new=0, retaining
  the unbleached loss at zero power; keep b,d,h unchanged.
- no_shift: set h=0, retain all loss terms.
- no_bleaching_no_shift: combine these physical controls.

The first three altered complex-transfer controls are
behavioral ablations (amplitude_only, phase_only, linear),
not independently realizable cavity models. They are passive
scalar maps but do not have their own reflection, absorption,
energy or stability solution. Their archived parent energy
and stability belong to the underlying full cavity. The three
physical controls re-solve the actual TCMT equations and
maintain port energy balance. In particular no_bleaching
does not mean zero absorption: it preserves linear loss and
any competing nonlinear loss. A nonzero h still assumes an
independent hypothetical nonlinear index response; this
experiment does not show such a material exists.

Use the low-power phase/amplitude, not an optimized reference
phase or fitted gain. Phase remains relative to the fixed
coherent receiver. Constant phase shifts are not equivalent
to removal of the complete coherent readout phase offset.
Report pre-receiver real-field accuracy and clean projected
accuracy at the fixed receiver phase, in addition to noisy
receiver accuracy and signed margins.

## Detuning tolerance

For W2/W3, evaluate both full and no_bleaching physical
models on a fixed Cartesian grid:

- d = -.8, -.7, -.6, -.55, -.5, -.45, -.4, -.3, -.2, 0, .2.
- h = 0, .5, .8, 1, 1.2, 1.5.

These are normalized to the external energy decay rate,
not wavelengths or measured drift. Do not tune h or d
from test labels. Repeated nominal points are intentionally
included in both families to verify exact replay. The sweep
tests discrete points only, not a continuous fabrication
tolerance or a measured thermal drift range.

## Evaluation protocol and checks

35 mechanism cases plus 264 tolerance cases = 299 labeled
cases (including four repeated nominal cases across the two
families and other repeated physical parameters); 598 groups
across both drives, 2990 seed-level rows, five frozen NL003
absorber weights per drive, fresh balanced jittered XOR test
domain 54 (2048 inputs per seed), paired independent noise
domains 55/56, eight repeats. Same nominal receiver and
absolute activation noise as NL006. Evaluate all actual
per-channel powers directly, plus 513-point transfer grid
through 4 mW. Archive 65 samples per case (19435 rows),
299 parent/physical cavity audit rows and 30 paired distributed
reference rows A/B/C from NL005. Transfer and per-seed swing
metrics exclude the extra 1 dB output loss.

Reject parent/physical models with folds in the 0–4 mW
range, nonunique roots or unstable sampled points. For all
five seeds require clean pre-receiver accuracy and worst
noisy repeat >=95%, modeled peak diode power <=2 mW, and
the inherited stability gate. For behavioral ablations
this gate is only a diagnostic eligibility condition,
not proof of their physical stability. Preserve failures.
The result reports mechanism groups and tolerance totals
separately; do not interpret the combined count as a unique
device count or yield.

Independent implementation checks: amplitude and phase
ablation identities; constant complex gain; analytic
constant-loss linear limit; zero-power matching after
removing bleaching; normalized root residual <1e-10;
physical parent port balance <1e-12; passive scalar maps
and clean MVM chain; counts, frozen weights, references,
finite margins, archived source hashes and nominal replay.
Scientific screen failures are not implementation failures.

No retraining, no pulse or carrier dynamics, no measured
material parameters, no claim of physical power savings,
throughput or fabrication readiness. If the no_bleaching
control works, follow up with a material-specific nonlinear
index and loss calibration and dynamic cavity validation.
If phase_only fails, that does not exclude other trained
weights or phase-to-amplitude architectures.
