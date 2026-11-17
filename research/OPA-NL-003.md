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
