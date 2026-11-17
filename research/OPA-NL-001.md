# OPA-NL-001 — passive optical nonlinear activation

Status: initial compact-model experiment, not measured or foundry-calibrated.
Builds on [MOD-007](../results/opa-mod-007/README.md) and
[AG003](../antigravity/reproduction/AG-PHOTONIC-003/FINAL_REPORT.md).
Reuses MOD-007's synthetic dataset, three seeds, 128 channels and 32
minibatch updates, not its calibrated mesh model or its archived scores.
The new matched controls use passive matrix contractions and projected
electronic SGD; scores are not directly comparable to MOD-007.

## Physical hypothesis

A signed coherent input field (real amplitude, phase 0 or pi) can
pass through a passive intensity-dependent absorber and then a second
coherent MVM without a detector, ADC, electronic activation or DAC
between them, in a conditional static field model.

For field E in sqrt(mW), P=|E|², define

    T(P) = 10^(-L/10) [Thigh - (Thigh-Tlow)/(1+P/Psat)]
    Eout = E sqrt(T(P))

This is a phenomenological saturable transmission law, not an exact
material propagation equation. It preserves sign and phase by assumption,
is odd on real fields, and is passive (0 <= T <= 1). It suppresses small
signals more strongly than large signals. It is NOT tanh or ReLU.
No electronic bias or optical auxiliary pump is assumed.
Complex nonlinear phase, saturation dynamics, wavelength cross-talk
and real MZI decomposition/routing are outside this first model.

Both matrices are spectral-norm contractions, representable in
principle by passive SVD optics. No per-vector or intermediate
renormalization, digital gain or optical amplification. A single fixed
input RMS scale is estimated using training inputs only. Optical launch
field is sqrt(drive_mW)*x, and the second MVM receives the actual
attenuated output field. Readout uses a fixed conversion back to
normalized units; no hidden gain between layers.

## Preregistered protocol

- 3 MOD-007 seeds (707,708,709); same teacher, data, batch order, weights
  and noise streams for matched policies.
- Linear and electronic tanh references; both share the passive matrix
  norm constraints (tanh is an ideal mathematical reference, not a
  physical electronic interface model).
- Saturable absorber: Psat=1 mW, Tlow=0.15, Thigh=0.85; assumed,
  not extracted from any paper. Sweep drive 0.1/1/10 mW per unit squared
  amplitude, extra insertion loss 0/1/3 dB, normalized additive
  field noise 0/0.01/0.03. Noise is illustrative, not measured.
- Matched training with analytical real derivative and electronic
  projected SGD versus deploying the same tanh-trained weights;
  no optical backpropagation.
- 29 cases × 3 seeds = 87 matched training cases (plus three tanh
  reference fits); two readout policies per case = 174 metric rows;
  2784 training-curve rows and 1449 transfer samples.
- Nominal hypothesis (drive=1, loss=1, noise=.01): on every seed,
  matched absorber must improve both accuracy and cross-entropy
  relative to linear, and remain within five percentage points of
  tanh accuracy. A failed hypothesis is valid and not a CI failure.
- Verify phase equivariance, signed field, passivity, analytic
  derivative, mapping, nonlinearity, finite metrics and row counts.
  Report launch/activation/output optical powers and loss, including
  actual per-channel peak input; noiseless power accounting separate
  from additive noise. Bandwidth and electrical energy unknown.

## Literature motivation (not parameter calibration)

- Liu et al., *Femto-joule threshold reconfigurable all-optical
  nonlinear activators for picosecond pulsed optical neural networks*,
  Light: Science & Applications (2026),
  https://doi.org/10.1038/s41377-025-02175-4 .
  Demonstrates graphene/silicon cavity saturable absorption and
  wavelength-dependent nonlinear responses. Pulsed energy thresholds
  do not directly specify CW saturation power in this model.
- Yan et al., *A complete photonic integrated neuron for nonlinear
  all-optical computing*, Nature Computational Science (2025),
  https://doi.org/10.1038/s43588-025-00866-x .
  Reports Kerr-based integrated nonlinear neuron on SiN; distinct
  architecture and mechanism from this compact absorber model.
- Fu et al., *Passive all-optical nonlinear neuron activation via PPLN
  nanophotonic waveguides*, https://arxiv.org/abs/2504.18145 ;
  alternative second-order frequency-conversion mechanism relevant
  to later lithium-niobate integration, not modeled here.

Run from repository root in the locked circuit environment:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python simulations/circuit/nonlinear_activation_v001.py
```

Artifacts: metrics.csv, learning_curves.csv, transfer.csv, result.json.
Script emits exact file sizes and SHA-256 for later evidence archival.
No fabricated chip, measured bandwidth, validated optical cascade,
energy advantage or LLM result is claimed.
