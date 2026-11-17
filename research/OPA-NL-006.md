# OPA-NL-006 — Resonantly enhanced optical activation

Status: preregistered conditional single-resonance temporal coupled-mode
model, not a calibrated photonic crystal cavity or measured device.
Builds on [NL005](OPA-NL-005.md) and the frozen NL003 weights.

## Motivation and primary evidence

Liu et al., [Light: Science & Applications 15, 128 (2026)](https://doi.org/10.1038/s41377-025-02175-4),
Fig. 2, experimentally demonstrate a graphene/silicon photonic crystal
cavity with 4 fJ incident pulse-energy half-saturation threshold and
approximately 1.05 ps pump-probe FWHM. Slow light and resonant
enhancement contribute to the low threshold. These measured quantities
are **not** the intracavity saturation energy or external energy
lifetime in this experiment. The article also reports wavelength-tuned
nonlinear transfer shapes. No absolute complex transfer fit, modal
overlap, cavity coupling or recovery calibration is claimed here.

The model uses the single-resonance energy-normalized coupled-mode
framework of Fan, Suh and Joannopoulos,
[JOSA A 20, 569–572 (2003)](https://doi.org/10.1364/JOSAA.20.000569).
We choose a symmetric two-port resonant-tunneling topology without
a direct cross-port transmission path. The assumed instantaneous
nonlinear rate laws below are not derived from either paper.

## Physical normalization

Let a be the cavity amplitude in sqrt(fJ), U=|a|^2 in fJ,
s the incident field in sqrt(mW), and t in ps (1 mW=1 fJ/ps).
Let k=1/tau_ext be the sum of the external energy decay rates,
with k1=k2=k/2. Use x=U/Us and dimensionless rates g and delta:
    
    g(x)=1+ns+sa/(1+x)+b*x
    delta(x)=d+h*x/(1+x)
    da/dt=k*(-g/2+i*delta)*a+sqrt(k/2)*s

ns is nonsaturable intrinsic loss relative to external coupling;
sa is the unbleached saturable loss; b is nonlinear loss slope
per normalized intracavity energy (phenomenological TPA-like
loss, not a bulk TPA coefficient); d is signed laser detuning,
h a hypothetical saturating resonance shift. All loss terms
are nonnegative. No direct relation between NL005 local guided
power Psat and Us is assumed.

At steady state:

    F(x)=x*((g/2)^2+delta^2)=0.5*Pin*tau_ext/Us
    Hdrop=0.5/(g/2-i*delta)
    Hreflect=1-0.5/(g/2-i*delta)
    Pabs/Pin=0.5*(g-1)/((g/2)^2+delta^2)

The phase convention is fixed by these port relations. A separate
1 dB output loss is applied as in NL005. No phase correction is fitted
to the test data. Power balance of the cavity before this loss
requires |Hdrop|^2+|Hreflect|^2+Pabs/Pin=1. U is stored energy,
not a circulating power or material intensity; those require
geometry, modal volume and overlap.

For zero detuning, shift and nonlinear loss, select the endpoint
pair Tlow,Thigh by ns=1/sqrt(Thigh)-1 and
sa=1/sqrt(Tlow)-1/sqrt(Thigh). These reproduce the hypothetical
NL005 low/high transmission limits, not its full curve. For
nonzero detuning, shift or nonlinear loss they are reference
parameters, not actual transmission limits.

## All-root and stability audit

Write F as N(x)/(1+x)^2, and find positive real stationary points
from N'(x)*(1+x)-2*N(x)=0. Divide the nonnegative domain into
monotone intervals and bisect every intersecting interval for each
actual input power and transfer grid point. Because g>=1,
every root satisfies x<=4*target. A separate stress case
(ns=.1, sa=20, b=d=h=0) must exhibit three roots, two stable,
at a target between the two folds. This is a numerical diagnostic,
not a candidate device.

For instantaneous material response the real 2x2 field Jacobian,
in radial/tangential coordinates and normalized time k*t, is

    J=[[-g/2-x*g', -delta],
       [delta+2*x*delta', -g/2]]

Trace=-g-x*g', determinant=F'(x). Require negative trace and
positive determinant (1e-9 numerical margin). Check against
finite differences. Convert the maximum eigenvalue real part
to inverse ps using k; this is a local linear relaxation estimate
under instantaneous closure, not a measured material recovery rate.

Always record root counts and stability. The lowest root is used
only for a deterministic diagnostic field when ambiguous;
no history-dependent branch choice or test-label selection.
Reject all candidate configurations with any stationary fold
whose incident power lies in the 0–4 mW study range, or with
nonunique or unstable grid/sample roots. This is a conservative
screen, not proof of stability for a full carrier/thermal model.
Check analytic linear transfer, linear energy and stability,
endpoint limits, normalized equation residual <1e-10,
port balance <1e-12, clean passivity and frozen archive hashes.

## Preregistered sweep

- Endpoint pairs (.1,.4), (.15,.85), (.373,.4).
- External energy lifetime 2,10,50 ps.
- Hypothetical intracavity saturation energy .3,3 fJ.
- Relative nonlinear loss slope 0,.1.
- Signed normalized detuning -.5,0,.5.
- Saturating normalized detuning shift 0,1.

216 distinct cavity configurations, 432 drive/configuration
groups, 2160 seed-level evaluations. Five archived absorber weight
sets per drive (.1 and 1 mW), fresh balanced jittered XOR test
domain 44 (2048 inputs), paired independent noise domains 45/46
(eight repeats). Same nominal NL003 receiver and absolute real
activation noise as NL005. Solve the actual per-channel powers
directly rather than interpolate between possible branches.
Compare the three post-hoc NL005 distributed candidates A/B/C
on identical independent inputs/noise using direct 128-step RK4
propagation (30 reference rows).

The unchanged accuracy/diode screen requires all five seeds
clean and worst-repeat receiver accuracy >=95% and diode peak
<=2 mW. Add the conservative cavity uniqueness/stability gate.
No retraining or post-hoc phase alignment. Report output field
margin, power, peak internal energy, input power, root counts,
and passive energy balance. Transfer audit uses 0 and 512
logarithmic positive power points through 4 mW; export every
eighth point (65 per cavity, 14040 total), plus 216 cavity audit
rows. All failures preserved; a failed scientific screen is not
a failed implementation check.

## Interpretation and next steps

A larger tau_ext can reduce the incident power needed to
reach a given U, but the loaded energy lifetime is tau_ext/g
and the local nonlinear relaxation differs from both. The external
lifetime sweep is not a throughput sweep. The model does not
simulate pulses, finite material recovery, free carriers, thermal
detuning, multimode coupling, dispersion, fabrication variation
or explicit slow-light geometry. No comparison with the measured
4 fJ pulse threshold, or claim of lower energy than NL005, is
valid without matching physical reference planes and material
parameters. After archive analysis, investigate independently
calibrated cavity coupling, field overlap, recovery and pulse
dynamics, and separately retrain weak nonlinear candidates.
