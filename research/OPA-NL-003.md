# OPA-NL-003 — Low-power optical activation and receiver modeling

Status: preregistered conditional circuit experiment, not physical receiver validation.
Builds on [NL002](OPA-NL-002.md) and [SYS003](../results/opa-sys-003/README.md).
NL002's composite gate failed; the archived results remain unchanged.

## Independent numerical test

Five new seeds 1301–1305, independent train/test draws (1024/2048),
same balanced jittered XOR and launched coherent reference as NL002.
Reuse its projected Adam training (1500 updates, batch 64, final
electronic logit scale 16), passive 8x3 and 1x8 contractions, original
absorber and behavioral softsat. Compare .1 and 1 mW drive at 1 dB
activation excess loss. For each fit, train a loss-matched linear
control and evaluate a same-weight linear ablation as in NL002.
Store weights, margins, learning curves and all receiver evaluations.
No intermediate O/E/O. Electronic training and final coherent readout.

### Constructive electronic tanh preflight

Use hidden rows k*(1,1,1), k*(-1,-1,1), k*(0,0,1), zeros elsewhere,
with k the reciprocal spectral norm of the unscaled matrix.
Let s=x1+x2; opposite-sign boxes have |s|<=.4, same-sign boxes
have |s|>=1.6. The even function
g(s)=tanh(k*(1+s))+tanh(k*(1-s)) decreases strictly for s>0
because sech²(k*(1+s)) < sech²(k*(1-s)).
Set h=(g(.4)+g(1.6))/2. Output coefficients proportional to
(1,1,-h/tanh(k)), scaled to norm <=1. The signed output margin
on the entire jitter domain is at least (g(.4)-g(1.6))/2
times the positive output scaling. Verify analytically and on a
41x41 grid in each of four boxes. Compare separately to independently
trained tanh; its performance is reported, not used to replace NL002's
failed preflight. Constructive reference must achieve >=99% each seed.

## Balanced homodyne receiver

Signal field E in sqrt(mW) at MVM output; after downstream loss
L and phase offset phi, convert to sqrt(W). LO power Plo in W at
the ideal lossless 50:50 hybrid, phase zero. Two photodiode powers:

    Pplus/minus = |E_rx +/- sqrt(Plo)|² / 2
    I_diff = R*(Pplus-Pminus)
           = 2*R*sqrt(Plo)*Re(E_rx)
    var_shot = 2*q*R*(Ps+Plo)*B
    var_TIA = i_TIA²*B
    var_RIN = (R*Plo)²*RIN*10^(-CMRR/10)*B

Independent Gaussian current noise with sum of variances; B is
equivalent noise bandwidth, not measured bit or symbol rate.
This extends the ideal coherent control in SYS003 with approximate
residual LO common-mode RIN, downstream signal loss and phase offset.
No ASE, signal RIN, clipping model, dark current, actual hybrid excess
loss, phase tracking, ADC or waveform bandwidth validation.
TIA density is total differential input-referred noise, not per diode.

Assume R=.9 A/W, i_TIA=15 pA/sqrt(Hz), RIN=-145 dB/Hz,
CMRR=20 dB, laser WPE=.20 (same illustrative nominal values as AG003
where applicable). Hypothetical peak per-diode cap 2 mW is only a
screen, not a calibrated saturation curve. LO power is at the hybrid;
report LO/WPE and (signal launch+LO)/WPE as electrical lower bounds
assuming lossless source distribution, excluding electronics.
Absolute activation-output noise in sqrt(mW) is applied before
the second MVM; its draws and receiver draws are domain-separated
and paired across policies and receiver settings. Distinguish
normalized .01 noise comparison (not combined with absolute noise)
from fixed absolute .00316227766 and .01 sqrt(mW) perturbations.
Noise is illustrative, not a physical noise calibration.
Passivity checked on clean optical fields only.

## Sweep and gates

- 45 trained models (5 tanh, 20 nonlinear, 20 matched linear);
  5 constructive reference entries; 50 weight records.
- 20 nonlinear seed/drive cases x 3 absolute-noise levels x 3 LO
  powers (.01/.1/1 mW) x 3 ENBW (.1/1/7 GHz) x 2 downstream
  losses (0/3 dB) x 2 phase offsets (0/15 degrees) = 2160 rows.
- Eight paired noise realizations per test example per row.
  Report mean classification accuracy and worst realization accuracy,
  minimum signed current-to-noise ratio, mean and minimum signal
  power, peak diode power and noise variances. Gaussian samples are
  a conditional approximation, not measured receiver BER.
- Nominal receiver point fixed before running: LO .1 mW, ENBW 1 GHz,
  3 dB downstream loss, 15 degrees phase offset, absolute activation
  noise .00316227766 sqrt(mW). For each kind/drive separately require
  constructive digital preflight, >=95% clean and worst realization
  accuracy on every seed, >=15 percentage points improvement over
  both clean linear controls on every seed, and diode cap pass.
  The priority low-drive absorber is not guaranteed to pass.
- Negative scientific outcomes are valid; implementation checks
  validate identities, dimensions, finite values, passive norms and
  archived NL002 immutability.

Artifacts: receiver.csv, paired.csv, references.csv, learning_curves.csv,
weights.json, result.json; hashes emitted for archival.

No fabricated chip, device bandwidth, physical receiver validation,
system energy advantage or optical backpropagation is claimed.

## Initial observed results (17 November 2026)

[Run 44163676304](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44163676304),
job 134324031154, artifact 14364861512. All 16 implementation checks
passed. Constructive digital preflight passed with 100% on each
of five independent seeds and an analytic normalized signed-field
margin lower bound of .0765285956 across the jitter boxes.
Independently trained tanh scored 100%, 99.8046875%, 100%, 100%,
100% on seeds 1301–1305 respectively. This does not alter the
failed NL002 composite gate.

At the fixed nominal receiver point (.1 mW LO, 1 GHz ENBW,
3 dB downstream loss, 15-degree phase offset, .00316227766
sqrt(mW) absolute activation-output noise), three of four
preregistered candidate/drive gates pass:

| Metric | Absorber .1 mW | Absorber 1 mW | Softsat .1 mW | Softsat 1 mW |
|---|---:|---:|---:|---:|
| Mean receiver accuracy (%) | 99.998779 | 100 | 59.591064 | 100 |
| Worst seed/repeat accuracy (%) | 99.951172 | 100 | 50.439453 | 100 |
| Clean accuracy (%) | 100 | 100 | 57.861328 | 100 |
| Pre-receiver accuracy with absolute noise (%) | 100 | 100 | 59.394531 | 100 |
| Matched linear clean accuracy (%) | 57.978516 | 47.607422 | 46.142578 | 40.517578 |
| Same-weight ablation clean accuracy (%) | 49.980469 | 50.761719 | 48.115234 | 45.410156 |
| Minimum clean paired gain vs matched (pp) | 25 | 37.451172 | -5.810547 | 50 |
| Minimum clean paired gain vs ablation (pp) | 50 | 25 | -.292969 | 50 |
| Mean signal launch (mW) | .303216 | 3.032156 | .303216 | 3.032156 |
| Mean clean MVM output (uW) | .604620 | 24.654142 | .128520 | 33.813549 |
| Min clean MVM output over seeds/examples (uW) | .100153 | 8.798384 | 2.331919e-9 | 15.760399 |
| Mean received signal incl. activation noise (uW) | .307940 | 12.361319 | .069513 | 16.952192 |
| Min signed current/sigma | .649695 | 68.321248 | -18.481749 | 93.406447 |
| Peak modeled diode power (mW) | .061696 | .117038 | .057349 | .120617 |
| Signal+LO source electrical lower bound (mW) | 2.016078 | 15.660781 | 2.016078 | 15.660781 |
| Original NL003 gate | PASS | PASS | FAIL | PASS |

The low-drive absorber has exactly one incorrect receiver
classification among 81,920 paired sample/noise outcomes,
on seed 1304. Its pre-receiver classification is perfect on
these draws. These are eight repeated noise draws on each of
10,240 held-out examples, not 81,920 independent inputs or a
measured BER. Worst modeled signed current/sigma is only .65;
do not infer a robust universal error guarantee from the mean
accuracy. Low-drive softsat fails already in clean classification.
All modeled peak diode powers remain below the hypothetical cap
at this point; this is not experimental saturation validation.

Low-drive absorber reduces signal launch 90% relative to
1 mW drive. The modeled signal-plus-LO electrical source lower
bound is about 87.1% lower (2.016 vs 15.661 mW), conditional on
20% WPE and lossless source delivery; this excludes all electronics,
phase locking, actual distribution, thermal and control costs.
No total system energy advantage or physical operating speed is
established. The receiver ENBW is not symbol rate.
Each drive is independently trained. The normalized activation
noise comparison is separate from absolute-noise receiver cases.

## Evidence and remaining analysis

Source ZIP metadata: 117,695 bytes; SHA-256
aa85eab11f7af5c5bd52a147b241083f85c622038e8d0a7991470e3c61e19ba6.
The archive helper pins all six science-file sizes and digests
emitted in CI, verifies exact ZIP identity, CRC and staged bytes
including environment metadata and provenance. The actual raw ZIP
verification is pending manual archive workflow execution.
The initial analysis above is computed from the full nominal and
paired rows in CI stdout, not the entire 2,160-row receiver CSV.
After archival, analyze worst-seed accuracy across the full LO,
noise, bandwidth, loss and phase grid; compare source-power
tradeoffs and retain weights for physical-mechanism research.
Material response, dynamics and phase still require independent
calibration before any device-level feasibility conclusion.

## Complete archived receiver sweep analysis

Source: [receiver.csv](../results/opa-nl-003/receiver.csv),
[result.json](../results/opa-nl-003/result.json) and
[provenance](../results/opa-nl-003/provenance.json), archived by
PR 136, merge 7df2ed4c1251442f543f1bed1e3a48721fb5e0d9.
Archive workflow 44166191166 verified the raw ZIP and staged bytes.
Grouped all 2160 rows into 432 unique parameter configurations with
five seeds each. Derived [configuration summary](OPA-NL-003-sweep.csv)
records mean accuracy across equal-sized seeds, minimum worst-repeat
accuracy over seeds, mean pre-receiver accuracy, minimum signed
current/sigma, peak diode power, cap status and mean source electrical
lower bound. This is descriptive post-hoc analysis, not a change
to the original four preregistered gates.

| Candidate/drive | Configurations | All seeds/repeats perfect | Worst repeat >=95% and diode cap | Worst repeat across sweep |
|---|---:|---:|---:|---:|
| Absorber .1 mW | 108 | 43 | 104 | 91.3574% |
| Absorber 1 mW | 108 | 108 | 108 | 100% |
| Softsat .1 mW | 108 | 0 | 0 | 49.6582% |
| Softsat 1 mW | 108 | 108 | 108 | 100% |

Every one of 2160 rows passes the assumed 2 mW per-diode cap;
maximum observed peak is .808155 mW (softsat 1 mW). This cap is
not a calibrated saturation limit.

### Low-drive absorber: LO/ENBW tradeoff

Fixed nominal absolute activation-output noise .00316227766 sqrt(mW),
3 dB downstream signal loss and 15-degree relative phase offset.
Each cell shows mean accuracy / worst seed-repeat accuracy (%).

| LO mW | .1 GHz | 1 GHz | 7 GHz | Mean signal+LO electrical lower bound mW |
|---|---:|---:|---:|---:|
| .01 | 99.998779 / 99.951172 | 99.965820 / 99.853516 | 97.344971 / 95.947266 | 1.566078 |
| .1 | 100 / 100 | 99.998779 / 99.951172 | 99.980469 / 99.902344 | 2.016078 |
| 1 | 100 / 100 | 100 / 100 | 99.998779 / 99.951172 | 6.516078 |

Reducing LO from .1 to .01 mW lowers its own optical/electrical
power 90%, but lowers the combined signal+LO source electrical
lower bound only 22.32% (2.016078 to 1.566078 mW).
Relative to 1 mW signal drive and .1 mW LO (15.660781 mW),
the latter lower bound is 90% smaller. These are assumed source
power bounds at 20% WPE, not system power or energy per operation.

For each LO/ENBW pair, worst accuracy over all 12 combinations of
activation noise, loss and phase (and all seeds/repeats):

| LO mW | .1 GHz | 1 GHz | 7 GHz |
|---|---:|---:|---:|
| .01 | 96.9238% | 96.2891% | 91.3574% |
| .1 | 96.8262% | 96.9238% | 96.4355% |
| 1 | 96.9727% | 96.8262% | 96.6797% |

Eight of nine LO/ENBW pairs pass the descriptive 95% robustness
screen over all twelve stress combinations. The sole failing pair
is .01 mW LO / 7 GHz, at .01 sqrt(mW) activation noise for all four
loss/phase combinations. Worst repeats for these four are 94.4824%,
94.3359%, 91.7969%, 91.3574% at (0 dB,0 deg), (0 dB,15 deg),
(3 dB,0 deg), (3 dB,15 deg). All nominal-noise and zero-noise
configurations pass the screen.

### Activation-noise bottleneck

| Absolute noise sqrt(mW) | Perfect configurations | >=95% worst-repeat configurations | Worst repeat |
|---|---:|---:|---:|
| 0 | 31/36 | 36/36 | 96.5332% |
| .00316227766 | 12/36 | 36/36 | 95.9473% |
| .01 | 0/36 | 32/36 | 91.3574% |

At high absolute activation noise, mean pre-receiver classification
accuracy for the low-drive absorber is 97.957764%. At 3 dB loss,
15 degrees and 7 GHz ENBW, increasing LO .01 -> .1 -> 1 mW
raises mean accuracy 93.520508 -> 97.451172 -> 97.863770%.
This approaches the pre-receiver accuracy; LO cannot generally
restore information already lost through activation-field errors.
Noise can occasionally flip a wrong sign to a right sign, so
pre-receiver accuracy is not a strict upper bound on finite-sample
receiver accuracy.

### Recommended operating points for further numerical research

- Low-source-power option: .1 mW drive, .01 mW LO, 1 GHz ENBW.
  Nominal mean 99.965820%, worst repeat 99.853516%; across tested
  stress combinations worst 96.2891%, all 12 pass 95%.
- Wider receiver ENBW option: .1 mW drive, .1 mW LO, 7 GHz ENBW.
  Nominal mean 99.980469%, worst repeat 99.902344%; across tested
  stress combinations worst 96.4355%, all 12 pass 95%.
- Conservative comparison: 1 mW absorber drive, .01 mW LO;
  all tested ENBW/loss/phase/noise configurations perfect.
  Higher optical launch is a tradeoff, not proof of superior hardware.

These are post-hoc selections on a finite tested grid. Do not
interpret ENBW as actual symbol rate or assume optimality outside
the grid. Fixed static phase offsets do not model drift or tracking.
No measured BER, independent error-rate confidence claim or physical
device throughput follows from repeated noise draws on the same
held-out examples.

## Proposed NL004 — material-calibrated saturable absorber model

Advance the priority nonlinear track using the archived NL003 weights
as frozen reference; preserve original results. First establish
primary-source material/device parameters and distinguish measured
guided-mode CW transmission from pulse fluence, peak intensity,
free-space measurements and nominal launched power. Candidate
graphene or other integrated absorber mechanisms must have traceable
wavelength, geometry, modal overlap, nonsaturable loss, saturation
scale, recovery dynamics and phase response, or explicitly identified
missing quantities. Do not assign an arbitrary 1 mW saturation power
to a real device. A rate-equation/propagation model should compare
steady-state transfer, transient response and phase preservation
against the NL003 behavioral transfer, with independent convergence
and passive power checks. Include frozen-weight deployment and
separately reported retraining, measured-parameter uncertainty,
downstream receiver and explicit energy/throughput limitations.
Receiver ENBW is not evidence of absorber recovery speed. Actual
fabrication and optical measurements remain separate milestones.
