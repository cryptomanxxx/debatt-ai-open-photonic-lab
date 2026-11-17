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

## Observed results — 17 November 2026

[Experiment run 44153775276](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44153775276),
job 134289115091, artifact 14360875814. All 12 implementation checks
passed; the preregistered scientific hypothesis failed. 174 metric rows,
2,784 recorded training updates, 1,449 transfer points. Source ZIP
metadata: 102,722 bytes, SHA-256
effb57fcb56dfb8433951bff8ff3d381f8e6bfaab31c51d54c0340751c4c9cc3.
Four science-file hashes are independently pinned from job stdout.
The archive workflow must verify the actual raw ZIP digest and CRC,
then all staged files; environment metadata hashes derive from that ZIP.
No claim that this workflow has already run.

### Matched training, three-seed means

| Case | Mean accuracy | Worst seed | Cross-entropy |
|---|---:|---:|---:|
| Linear | 67.71% | 61.72% | 0.98449 |
| Electronic tanh | 64.06% | 60.16% | 1.05165 |
| Nominal absorber | 59.11% | 56.64% | 1.19952 |
| Highest observed absorber mean (10 mW drive, 0 dB extra loss, 0.03 noise) | 65.10% | 60.16% | 1.06168 |

Nominal absorber is below linear accuracy by 11.72, 8.98, 5.08
percentage points on seeds 707,708,709 respectively. Loss is higher
on all three. Relative to tanh, accuracy is lower by 7.81, 3.52,
3.52 points, failing the five-point tolerance on seed 707.
Mean nominal tanh-deployment accuracy is 64.71%, loss 1.15518;
it outperforms matched nominal absorber training under this short
protocol, without proving a general training strategy.

### Noiseless absorber sweep, matched training

| Drive per unit squared amplitude | 0 dB extra loss | 1 dB | 3 dB |
|---|---:|---:|---:|
| 0.1 mW | 54.69% | 52.21% | 47.40% |
| 1 mW | 61.85% | 58.85% | 54.69% |
| 10 mW | 64.45% | 63.28% | 60.29% |

Higher drive makes the absorber more transmissive but also closer to
linear at high field. The highest observed mean is a post-hoc
descriptive observation, not an independent validation or a recommended
operating point. It requires about 1,279 mW aggregate launched signal
power across 128 channels under the chosen normalization.

### Nominal optical power (means across seeds and examples)

| Plane | Signal power |
|---|---:|
| First MVM launch | 127.9115 mW |
| First MVM output / absorber input | 29.2093 mW |
| Absorber output / second MVM input | 9.2385 mW |
| Second MVM output | 2.4069 mW |

Mean aggregate absorber loss 5.0001 dB (mean of per-seed ratios in dB).
Only approximately 1.88% of mean launch power remains in final
modeled signal outputs. These are noiseless field powers for the
trained weights, not system electricity, and matrix contractions
include mathematical singular-value attenuation. No laser WPE,
packaging, actual MZI insertion loss or receiver energy is counted.

### Interpretation and next research gate

Preserve the negative outcome. Even electronic tanh underperforms
linear in this protocol; 32 projected SGD updates and the specific
teacher task do not establish a benefit of nonlinearity. The
saturating transmission is a small-signal suppressor, not tanh.
The comparison also confounds nonlinear shape with optical attenuation
and output logit scale. Do not conclude that all optical activations
are inferior, or optimize on the held-out observations.

Before choosing a material mechanism, preregister a new controlled
study (proposed OPA-NL-002): a task that provably needs nonlinear
features (e.g. balanced XOR), a longer fixed training schedule,
independent test seeds, matched linear loss controls at each drive,
and separately reported fixed electronic final readout scaling
versus raw field readout. Validate the digital nonlinear reference
first, retain contraction/passivity and separate launch-power
accounting. Compare an alternative sign-preserving saturating
transfer model; do not claim a realizable device from its shape.
Only after demonstrating useful numerical nonlinearity pursue
calibrated phase, dynamics, bandwidth, material and WDM models.
No physical optical cascade has yet been verified.
