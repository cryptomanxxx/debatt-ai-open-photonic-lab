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

## Initial observed results — 17 November 2026

[Experiment run 44184657895](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44184657895),
job 134397995866, source PR 150, artifact 14373622549.
All 14 implementation checks passed; no implementation failures.
2990 seed rows, 598 labeled groups and 30 references were reported.
The initial analysis uses the CI-emitted JSON, not the raw CSV
files. Full per-seed, transfer and stability analysis follows
verified archival.

### Mechanism isolation

| Mode | Passing groups / 10 |
|---|---:|
| full | 7/10 |
| amplitude_only | 6/10 |
| phase_only | 0/10 |
| linear | 0/10 |
| no_bleaching | 2/10 |
| no_shift | 4/10 |
| no_bleaching_no_shift | 0/10 |

19/70 mechanism groups pass. For the three previously successful
weak-family drive/candidate combinations:

| Mode | W1 at 1 mW worst % | W2 at .1 mW worst % | W3 at .1 mW worst % |
|---|---:|---:|---:|
| full | 99.560547 | 99.560547 | 96.484375 |
| amplitude_only | 99.462891 | 97.705078 | 89.013672 |
| phase_only | 27.392578 | 57.958984 | 58.300781 |
| linear | 31.494141 | 45.654297 | 45.654297 |
| no_bleaching | 97.558594 | 99.023438 | 93.847656 |
| no_shift | 36.035156 | 48.876953 | 41.796875 |
| no_bleaching_no_shift | 31.494141 | 45.654297 | 39.306641 |

The full model replicates all three prior weak passes on fresh
inputs. W1 and W2 pass with constant low-power phase and
varying amplitude, and independently pass when saturable
absorption is removed in the physical TCMT model. W2 without
bleaching has 100% clean and projected accuracy, mean receiver
accuracy 99.742432% and worst repeat 99.023438%. W1 without
bleaching has 100% clean accuracy, minimum projected accuracy
99.853516% and worst repeat 97.558594%. W3 falls below 95% in
both of these individual controls at its nominal point, though
the full model passes. W1/W2/W3 all fail when the nonlinear
shift is removed at their nominal successful drive. All weak
nominal candidates fail at the opposite drive.

None of the ten phase-only groups passes the receiver screen.
W2 and W3 at .1 mW have 100% pre-receiver clean accuracy but
only 53.564453% and 53.515625% minimum clean projected accuracy
at the fixed receiver phase, respectively. W1 at 1 mW has
99.316406% minimum clean accuracy but only 27.197266% projected
accuracy. Thus phase-only failure is strongly linked to coherent
projection in these cases; it does not rule out alternative
phase alignment, retraining or optical interferometric circuits.
Do not optimize receiver phase on these test labels.

Both strong reference cavities S1/S2 are perfect at both
drives for full, amplitude_only and no_shift; neither passes
without bleaching. All linear and combined no_bleaching_no_shift
groups fail. The latter is not a linear physical control for W3
because b=.1 remains. All 70 mechanism groups have a stable
parent/physical cavity. The diagnostic phase and amplitude
maps are not independent physical cavities.

The successful physical no_bleaching controls establish that
saturable absorption is not required for these selected
conditional stationary models. They retain unbleached linear
loss and the hypothetical nonlinear detuning term, and W3
variants retain competing nonlinear absorption. The successful
amplitude-only controls separately demonstrate that variation of
the output phase is not necessary for W1/W2 with these frozen
weights. They do not establish a material-specific Kerr
coefficient or demonstrate a physical amplitude-only version
of the no-bleaching cavity: that combined diagnostic was not
tested in this experiment.

### Detuning/shift tolerance

| Candidate | Physical mode | .1 mW pass/tested | 1 mW pass/tested |
|---|---|---:|---:|
| W2 | full | 21/66 | 7/66 |
| W2 | no_bleaching | 19/66 | 7/66 |
| W3 | full | 17/66 | 1/66 |
| W3 | no_bleaching | 16/66 | 1/66 |

89/528 tolerance groups pass: 46/264 full and 43/264
no_bleaching. Low-drive no_bleaching groups account for
35/132; high-drive no_bleaching groups for 8/132. W3 has
passing no-bleaching points away from the nominal condition
or at the other drive, despite failure of its nominal low-drive
no-bleaching control. Aggregate counts cannot locate the points,
establish a continuous tolerance interval, identify shared
two-drive tuples, or determine which failures are caused by
stability. Mechanism and tolerance cases overlap; do not
treat their combined 108 passes as unique device designs.

### Independent distributed references

| Drive mW | Reference | Min clean % | Mean receiver % | Worst repeat % |
|---:|---|---:|---:|---:|
| 0.1 | A | 100.000000 | 100.000000 | 100.000000 |
| 0.1 | B | 100.000000 | 99.996338 | 99.951172 |
| 0.1 | C | 100.000000 | 100.000000 | 100.000000 |
| 1 | A | 100.000000 | 99.998779 | 99.951172 |
| 1 | B | 100.000000 | 100.000000 | 100.000000 |
| 1 | C | 100.000000 | 100.000000 | 100.000000 |

All 30 paired references have 100% clean accuracy; all meet
the nominal accuracy screen. These are fresh domain-54 samples
with independent domain-55/56 noise, not independent physical
measurements.

### Archive and next analysis

ZIP: 820638 bytes, SHA-256
ec9518b1703f1d2a4275ed84b680d394cb746a4a3a4a201acb76671aee29905e.
The archival helper pins all six CI-emitted science-file hashes
and validates the exact ZIP, CRC, report counts and staged
bytes. ZIP verification awaits the manual archive workflow.
The original evidence is not yet permanently archived.

After archival, map the pass/fail grid and separate stability,
clean projection and receiver limitations. Identify contiguous
sampled detuning/shift neighborhoods and any common-drive
tuples without interpolating or claiming continuous tolerance.
Compare full and no_bleaching matched points, actual transmission
and phase swing, signed margins, parent energy and relaxation.
Select any next hypotheses explicitly as post-hoc and validate
them with fresh draws. A physical model needs measured
nonlinear index response, coupling/linewidth, loss and finite
response dynamics; no hardware, power or throughput advantage
has been demonstrated.

## Full archived analysis

Archive PR 152, merge 1a22483b5da34c21b76b5db7e32a84ffea6694c2, workflow 44189964563.
Read [summary](../results/opa-nl-007/summary.csv),
[metrics](../results/opa-nl-007/metrics.csv),
[cavity audit](../results/opa-nl-007/cavity_audit.csv),
[transfer](../results/opa-nl-007/transfer.csv),
[references](../results/opa-nl-007/references.csv) and
[provenance](../results/opa-nl-007/provenance.json).
Counts: 598 groups, 2990 seed rows, 299 labeled audits,
19435 transfer samples and 30 reference rows.
These analyses are post-hoc; archived evidence is unchanged.

### Numerical eligibility and failure decomposition

All 299 labeled cavity/parent audits are stable, with no
rejected stability cases. Maximum normalized residual
4.643277e-15; port balance error 4.440892e-16.
Maximum modeled diode power .122941396 mW. Minimum local
relaxation rates across audits range .044874261 to
.409341327 /ps. These are instantaneous-model quantities,
not physical bandwidth or symbol-rate measurements.

| Candidate | Mode | Drive mW | Clean >=95% | Clean and projected >=95% | Screen pass | Perfect worst repeat |
|---|---|---:|---:|---:|---:|---:|
| W2 | full | 0.1 | 37/66 | 28/66 | 21/66 | 6/66 |
| W2 | full | 1 | 14/66 | 7/66 | 7/66 | 6/66 |
| W2 | no_bleaching | 0.1 | 36/66 | 26/66 | 19/66 | 5/66 |
| W2 | no_bleaching | 1 | 13/66 | 7/66 | 7/66 | 5/66 |
| W3 | full | 0.1 | 34/66 | 22/66 | 17/66 | 3/66 |
| W3 | full | 1 | 5/66 | 1/66 | 1/66 | 0/66 |
| W3 | no_bleaching | 0.1 | 33/66 | 21/66 | 16/66 | 2/66 |
| W3 | no_bleaching | 1 | 4/66 | 1/66 | 1/66 | 0/66 |

The projected column is a diagnostic, not an extra
preregistered gate. No stability or diode-cap failures
explain the tolerance screen failures; classification and
receiver accuracy are limiting. The phase-only mechanism
results identify a coherent-projection issue, not a general
impossibility of phase-based computing.

### Complete discrete tolerance grid

Column order h = 0, 0.5, 0.8, 1, 1.2, 1.5.
P means perfect worst repeat, + means other screen pass,
. means fail. Each row reports six independently evaluated
points, not interpolated intervals.

| d | W2 full .1 | W2 full 1 | W2 no bleaching .1 | W2 no bleaching 1 | W3 full .1 | W3 full 1 | W3 no bleaching .1 | W3 no bleaching 1 |
|---:|---|---|---|---|---|---|---|---|
| -0.8 | `..++PP` | `.PPP..` | `..+++P` | `.PPP..` | `..+++P` | `.+....` | `..+++P` | `.+....` |
| -0.7 | `..++PP` | `.PP...` | `..++PP` | `.PP...` | `..++PP` | `......` | `..+++P` | `......` |
| -0.6 | `..++PP` | `.P....` | `..++PP` | `.+....` | `..++++` | `......` | `..++++` | `......` |
| -0.55 | `..++++` | `.+....` | `..++++` | `.+....` | `..++++` | `......` | `..++++` | `......` |
| -0.5 | `..+++.` | `......` | `..+++.` | `......` | `...+..` | `......` | `......` | `......` |
| -0.45 | `..++..` | `......` | `......` | `......` | `......` | `......` | `......` | `......` |
| -0.4 | `......` | `......` | `......` | `......` | `......` | `......` | `......` | `......` |
| -0.3 | `......` | `......` | `......` | `......` | `......` | `......` | `......` | `......` |
| -0.2 | `......` | `......` | `......` | `......` | `......` | `......` | `......` | `......` |
| 0 | `......` | `......` | `......` | `......` | `......` | `......` | `......` | `......` |
| 0.2 | `......` | `......` | `......` | `......` | `......` | `......` | `......` | `......` |

At low drive W2 no_bleaching passes every sampled point
in the rectangle d=-.8,-.7,-.6,-.55 and h=.8,1,1.2,1.5
(16/16), and three additional points at d=-.5.
W3 no_bleaching has the same 16/16 passing rectangle
but no passing points at d=-.5. At high drive, W2 passes
seven sampled points and W3 only one. No h=0 tolerance
case passes. No positive or zero detuning case passes.
There is no evidence of a continuous tolerance interval
between these discrete points or robustness to other
unvaried parameters.

Matched full/no_bleaching comparisons: all 43 passing
no_bleaching groups also pass full; three additional
full groups pass (W2 low drive two, W3 low drive one).
No no_bleaching-only passing point was observed.

### Common-drive candidates

W2 full and no_bleaching share the same three passing
(d,h) tuples at both drives. W3 has none. Unlike NL006,
the expanded signed detuning sweep therefore identifies
weak reference-family tuples that pass both drives without
saturable absorption. Drive-specific frozen weights remain
different; this is not a single network operating over a
tenfold dynamic range. None is perfect at both drives.

| d | h | Full .1 worst % | Full 1 worst % | No bleaching .1 worst % | No bleaching 1 worst % |
|---:|---:|---:|---:|---:|---:|
| -0.8 | 0.8 | 99.414063 | 100.000000 | 99.267578 | 100.000000 |
| -0.8 | 1 | 99.902344 | 100.000000 | 99.902344 | 100.000000 |
| -0.7 | 0.8 | 99.658203 | 100.000000 | 99.609375 | 100.000000 |

### Selected physical no-bleaching metrics

Post-hoc selection: all common-drive tuples, plus the
low-drive perfect W2/W3 point (-.8,1.5), and W3's sole
high-drive pass (-.8,.5). Energy is maximum stored cavity
energy over the five seeds. Swing is maximum per-seed
actual-input transmission/phase range, before extra 1 dB
loss, not a continuous extremum. Signed projected field
is minimum across all seeds and samples. Relaxation is
minimum local rate over the evaluated parent/physical
model domain.

| Candidate | d | h | Drive mW | Worst % | Mean output uW | Min projected field sqrt(mW) | Peak stored fJ | Max swing pp | Max phase swing deg | Min rate /ps |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| W2 | -0.8 | 0.8 | 0.1 | 99.267578 | 0.316635 | 0.003648 | 1.541704 | 7.249583 | 11.497654 | 0.066472 |
| W2 | -0.8 | 0.8 | 1 | 100.000000 | 26.159797 | 0.046035 | 21.034577 | 17.672764 | 37.384613 | 0.066472 |
| W2 | -0.8 | 1 | 0.1 | 99.902344 | 0.587293 | 0.006461 | 1.696724 | 9.897098 | 16.151272 | 0.057045 |
| W2 | -0.8 | 1 | 1 | 100.000000 | 43.639427 | 0.010996 | 21.165791 | 18.219545 | 49.632530 | 0.057045 |
| W2 | -0.7 | 0.8 | 0.1 | 99.609375 | 0.482009 | 0.004536 | 1.755103 | 8.427327 | 14.225725 | 0.062821 |
| W2 | -0.7 | 0.8 | 1 | 100.000000 | 28.661140 | 0.016299 | 21.347445 | 15.752757 | 40.631378 | 0.062821 |
| W2 | -0.8 | 1.5 | 0.1 | 100.000000 | 2.146677 | 0.014881 | 2.076313 | 16.379914 | 31.507451 | 0.048372 |
| W3 | -0.8 | 1.5 | 0.1 | 100.000000 | 1.826222 | 0.013422 | 1.899025 | 13.352097 | 29.924716 | 0.053584 |
| W3 | -0.8 | 0.5 | 1 | 95.556641 | 5.979914 | -0.001578 | 11.958049 | 4.770919 | 22.873520 | 0.081868 |

Five of 66 W2 low-drive and five of 66 high-drive
no_bleaching points are perfect; two of 66 W3 low-drive
points are perfect, none at high drive. A perfect W2
low-drive point need not be suitable at high drive.
The W3 high-drive passing point has a negative minimum
projected field despite passing the 95% noisy screen:
the gate does not require every individual bit correct.

The distributed A/B/C references remain strong independent
controls; do not infer power or efficiency superiority
from this classification experiment. All physical no_bleaching
models retain unbleached linear loss; W3 retains competing
nonlinear absorption. The nonlinear shift is still a
hypothetical saturating function of stored energy.

### NL008 proposed: dynamic validity of non-bleaching cavities

Prioritize a bounded time-domain TCMT test of the W2
no_bleaching common-drive candidate d=-.8,h=1, its two
other common-drive tuples, the perfect low-drive point
(-.8,1.5), and W3 as a competing-loss stress case.
These are selected after observing NL007; use independent
test draws. Preserve the same physical port normalization
and test the steady-state limit against the existing
all-root solver. Introduce a state q for finite index
response, dq/dt=(x/(1+x)-q)/tau_response with detuning
d+h*q, while x=|a|^2/Us. Treat the instantaneous limit
separately. Integrate the complex cavity field, track
incident/reflected/transmitted/absorbed energy and stored
energy, and check integrated energy balance and timestep
convergence. Compare isolated pulses and sequences with
different preceding symbols and gaps; report transient
settling, intersymbol memory, sampled coherent output
and classification accuracy with a preregistered sampling
rule. Do not infer a bit rate from the stationary Jacobian.
This phenomenological response model is not calibrated
Kerr, thermal or carrier physics. A future material model
must replace the assumed saturating shift with measured
or independently justified nonlinear index, mode volume,
coupling, loss and response time.

Also retain the untested combined no_bleaching amplitude-only
diagnostic and independently fixed receiver phase controls
as follow-up mechanism checks; neither is a physical
independent cavity. Do not optimize on held-out labels.
