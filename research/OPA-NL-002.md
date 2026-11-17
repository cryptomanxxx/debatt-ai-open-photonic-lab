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
