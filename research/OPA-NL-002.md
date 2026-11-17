# OPA-NL-002 — XOR and useful optical nonlinearity

Status: preregistered numerical compact-model experiment. Builds on
[NL001](OPA-NL-001.md) and its [negative archived result](../results/opa-nl-001/result.json).
No new material parameters or measured device claims.

## Question and encoding

Can a passive signed-field nonlinear layer solve a task that cannot
be solved by an affine field transformation and a final sign threshold?
XOR labels the opposite-sign quadrants as 1. Four equally represented
corners (-1,-1), (-1,+1), (+1,-1), (+1,+1) are jittered independently
by uniform +/-0.2 per coordinate. A single affine threshold cannot
correctly classify all four exact corners: its maximum is 75%.
Do not apply that exact-corner bound to arbitrary noisy test draws.

An odd activation without bias cannot represent an even XOR decision
on antipodal inputs. Add a constant coherent reference of normalized
amplitude 1 at launch, not between layers. Its optical power is
explicitly counted. Real amplitudes use relative phase 0/pi.
The model uses a passive 8x3 matrix contraction, eight elementwise
activators and a passive 1x8 output contraction. Rectangular matrices
can be embedded in larger passive SVD networks with unused ports.
No intermediate detection, electronic gain, bias injection or
renormalization. The final readout assumes a coherent phase reference;
a square-law intensity detector alone does not recover field sign.
The final receiver and its LO are not modeled or energy-accounted.

## Transfer functions

Reuse NL001's absorber exactly: Tlow=.15, Thigh=.85, Psat=1 mW.
Compare a behavioral amplitude compressor, softsat:

    Eout = sqrt(.85 * 10^(-L/10)) E / sqrt(1 + |E|^2 / 1 mW)

This transfer preserves phase by assumption and is passive, with
bounded output amplitude. It is not a measured device model.
Both nonlinear functions are compared against electronic tanh and
linear controls. For each nonlinear fit and drive/loss point,
derive a constant scalar transmission from its training fields:

    t = sqrt(sum(|a|^2) / sum(|z|^2))

Train a new linear network with this frozen gain using identical
initialization and batches. Also replace the activation by the same
gain without retraining nonlinear weights (shape ablation).
Matching is aggregate on the nonlinear training fields, not equal
power at each sample or after retraining.

## Protocol

- Five independent seed pairs (1201–1205), 1024 balanced training
  and 2048 balanced independent test samples per seed.
- 1500 fixed minibatch updates, batch 64, projected electronic Adam,
  learning rate .025; two matrix spectral norms <=1.
- Fixed electronic final logit scale 16 for training across all
  policies. Report raw scale-1 and scale-16 test cross-entropy.
  Positive scalar readout cannot change the zero-threshold class.
  No intermediate electronic scaling.
- Drive .1/1/10 mW per unit squared input amplitude, extra loss
  0/1/3 dB, held-out normalized additive field noise 0/.01/.03.
  Noise is injected at activation output during evaluation only,
  paired across policies. Train noiselessly.
- Two references plus 18 nonlinear fits and 18 matched linear
  fits per seed; 190 trained models total. 90 same-weight
  ablations; 840 evaluation rows, 5890 sampled training updates,
  1120 exact-corner rows and 90 loss matches.
- Digital preflight: tanh >=99% on every noiseless test seed.
  If this fails, neither optical candidate can pass the research gate.
- Each nominal optical candidate (1 mW, 1 dB, .01 noise) must attain
  >=95% on every test seed, beat both its matched linear fit and
  shape ablation by >=15 percentage points on every seed, and solve
  all four noiseless exact corners on every seed.
  Evaluate gates without selecting the best sweep point.
  A negative scientific result is valid and not a CI failure.

Report signed field margins, both cross-entropies, matrix norms,
launch power including reference channel, activation input/output,
output signal power and peak activation input channel power.
Passivity accounts for noiseless fields only; perturbations are not
a physical noise source model. No wall-plug energy, bandwidth,
physical MZI routing, WDM, fabrication or optical training claims.
No change to NL001 source or archived results.

Run in locked circuit environment from repository root:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python simulations/circuit/nonlinear_activation_v002.py
```

Artifacts: result.json, metrics.csv, learning_curves.csv,
truth_table.csv, loss_matches.csv; emitted SHA-256 for archival.

## Initial observed results — 17 November 2026

[Experiment run 44157326386](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44157326386),
job 134301579784, artifact 14361432237. All 12 implementation checks
passed. Digital preflight is false and both nominal pass_gate flags are
false. The full preregistered hypothesis therefore failed; do not
retroactively change the gate. However both nominal optical candidates
classified all 2048 held-out examples correctly on each of five seeds
at drive 1 mW, extra loss 1 dB and normalized field noise std .01.
This is 10,240/10,240 correct per candidate, not a physical experiment.

The CI stdout includes nominal rows and gates only, not the full 840
metrics or exact-corner rows. The following values are derived from
those nominal rows. Full reference accuracy, matched linear margins,
ablation results, truth tables and sweep comparisons require the
verified full artifact, and are not asserted here.

| Nominal metric | Absorber | Softsat |
|---|---:|---:|
| Accuracy, all five seeds | 100% | 100% |
| Raw cross-entropy, mean | .616841 | .609439 |
| Scale-16 cross-entropy, mean | .079100 | .065099 |
| Minimum signed margin across seeds/examples | .094577 | .082325 |
| Mean launched optical signal incl. reference (mW) | 3.027539 | 3.027539 |
| Mean activation input (mW) | 2.733689 | 2.562842 |
| Mean activation output (mW) | 1.141907 | .799634 |
| Mean final signal output (mW) | .025585 | .031519 |
| Max activation channel input across seeds (mW) | 2.940993 | 2.934872 |
| Aggregate activation loss from ratio of mean powers (dB) | 3.791186 | 5.058306 |

All power values are conditional noiseless signal powers, not
electrical power, and not comparable directly to NL001's 128-channel
launch. Softsat has higher mean final output despite higher activation
loss because learned passive matrix contractions differ. No general
mechanism ranking follows. The final readout scale 16 is electronic
and does not increase the modeled optical output.

### Evidence and next step

Source ZIP metadata: 209,386 bytes, SHA-256
d30f10458d6780136368778e1ba287849dfbb0cf301c68186c3f917e44f2a431.
Five science-file hashes pinned from CI stdout. The new archive
workflow verifies the actual ZIP digest, CRC, exact entries, five
science hashes and all staged bytes including environment metadata
and provenance. Workflow has not yet run. Do not claim independent
byte verification until it succeeds.

After archival, compute per-seed digital preflight metrics, paired
nominal differences to both matched linear and same-weight ablation,
exact corner results, noise and power sweep. Report each criterion
separately while retaining original failed composite gate. Diagnose
why tanh preflight failed before designing a new independently
preregistered experiment. Candidate directions include a constructive
XOR reference, optimizer/contraction diagnostics, and independent
seeds; no post-hoc rescue of NL002. Only then proceed to calibrated
material mechanisms. No measured hardware or energy advantage.

## Full archived-evidence analysis

Source: [immutable archived metrics](../results/opa-nl-002/result.json),
[truth table](../results/opa-nl-002/truth_table.csv),
[learning curves](../results/opa-nl-002/learning_curves.csv) and
[provenance](../results/opa-nl-002/provenance.json).
Archive workflow 44159838370 verified raw ZIP and staged bytes;
PR 132 merged as bdb771786c3776ae0034e1e0fdfa5535d83c79de.
All 840 rows and 1,120 corner records were inspected by grouping.

### Nominal criterion decomposition

| Criterion | Absorber | Softsat |
|---|---:|---:|
| Mean test accuracy | 100% | 100% |
| Worst seed accuracy | 100% | 100% |
| Matched linear mean accuracy | 48.1934% | 43.8477% |
| Same-weight linear ablation mean accuracy | 50.8008% | 49.8242% |
| Minimum paired improvement vs matched linear (points) | 47.3145 | 49.9512 |
| Minimum paired improvement vs ablation (points) | 44.5801 | 43.3105 |
| Exact corners correct | 20/20 | 20/20 |
| Optical-specific criteria | pass | pass |
| Original composite gate | FAIL | FAIL |

The digital preflight remains false. No gate is retroactively changed.
A positive result for nonlinear shape under this model is not proof
of superiority over optimized electronic inference.

### Digital preflight diagnosis

| Seed | Tanh noiseless test accuracy | Incorrect / 2048 | Minimum signed margin |
|---|---:|---:|---:|
| 1201 | 100% | 0 | .000092 |
| 1202 | 99.9512% | 1 | -.001734 |
| 1203 | 100% | 0 | .039050 |
| 1204 | 100% | 0 | .027121 |
| 1205 | 98.2910% | 35 | -.017114 |

All 20 exact tanh corners are correct. The sole preflight failure is
seed 1205 below 99%, not inability of tanh to represent XOR.
Seed 1205 sampled minibatch CE at steps 500/1000/1500 is
.173916/.313165/.311372; these are different batches, not a fixed
validation trajectory. Both final matrix spectral norms are one
for every tanh seed within numerical tolerance. The small margins,
fixed final readout scale and constrained optimizer are plausible
contributors, not proven causes. No checkpoint weights were archived,
so exact causal diagnosis cannot be inferred from these metrics.

### Power/noise sweep

Mean accuracy at 1 dB extra loss and normalized field noise .01:

| Drive (mW/unit squared amplitude) | Absorber | Softsat | Aggregate launch (mW) |
|---|---:|---:|---:|
| .1 | 100% | 69.8242% | .302754 |
| 1 | 100% | 100% | 3.027539 |
| 10 | 100% | 100% | 30.275390 |

At .1 mW absorber: 20/20 corners, matched linear mean 46.8359%,
ablation mean 48.9258%, minimum paired improvements 43.9453 and
49.7070 points. Mean final signal .000591492 mW (0.591492 uW),
maximum activation input per channel .286874 mW. At noise .03
and 1 dB, mean accuracy 98.5449%, worst seed 97.4121%.
At .1 mW/3 dB/.03, mean 95.8691%, worst 93.8965%.
At 1 mW/1 dB/.03 both candidates remain 100% on every seed.
Across 27 drive/loss/noise combinations each, absorber achieves
all-seed perfection in 19 and softsat in 18. At .1 mW/1 dB/.01
softsat worst seed 63.5254%, 15/20 corners, mean final signal
.064686 uW. At 10 mW/1 dB/.01 softsat mean final signal 400.523 uW.

The low-drive absorber is a promising follow-up, not a preregistered
success or demonstrated physical operating point. Each drive/loss
case is separately trained. Relative to nominal it reduces launch
power by 90% while reducing final signal power from 25.585 to
0.591 uW (about 43 times); the readout and LO are unmodeled.
Noise is normalized, not fixed absolute optical noise or measured
receiver noise; .01 corresponds to a different absolute field
perturbation at each drive. No energy/bit or electrical power claim.

### Proposed NL003: independent constructive reference and receiver-aware test

Before selecting a material, preregister a fresh XOR experiment with
independent seeds and an analytic tanh construction. For inputs
(x1,x2,1), use hidden rows proportional to (1,1,1), (-1,-1,1),
(0,0,1), remaining rows zero; contract the matrix by its spectral
norm. Use output coefficients proportional to (1,1,-c) with c
chosen analytically between same-sign and opposite-sign responses
over the entire +/-0.2 jitter boxes; normalize output norm.
Verify the interval bound and compare trained tanh against that
constructive reference. Do not alter NL002. Test fixed absolute
field noise in sqrt(mW) separately from normalized noise, report
minimum received power and margins, and add an explicit idealized
coherent readout noise model with declared LO and bandwidth
assumptions. Keep electronic readout and optical power separate.
No device-specific feasibility claim until independently calibrated
material response, phase and dynamics are available.
