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

## Initial observed results — 17 November 2026

[Experiment run 44179461645](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44179461645),
job 134379675713, artifact 14371092957, PR 146. All 14
implementation checks passed, with no failures. Maximum normalized
steady-state equation residual is 2.54616929392e-14 and maximum
absolute port balance error is 5.55111512313e-16, below the
preregistered tolerances. These checks validate numerical
consistency of the assumed equations, not a physical cavity.

| Reference endpoint pair (Tlow, Thigh) | Low-drive pass/tested | High-drive pass/tested |
|---|---:|---:|
| (.1,.4) | 19/72 | 20/72 |
| (.15,.85) | 22/72 | 16/72 |
| (.373,.4) | 2/72 | 1/72 |
| Total | 43/216 | 37/216 |

80/432 groups pass (18.52%). The weak reference endpoint family
(.373,.4) has three passing drive/configuration groups out of
144, compared with zero of 108 groups at absolute depth .027 in
NL004 and zero of 90 in NL005. This is a new conditional
numerical result, not a demonstration of a measured 2.7-point
device. The endpoint parameters describe an on-resonance
reference without competing nonlinear loss or detuning shift;
the actual complex transfer may have substantially different
transmission contrast and phase. The grids and mechanisms differ
across experiments, so pass fractions are not directly comparable
as yields. The aggregate report cannot identify the three weak
passing tuples or whether any is common to both drives. Full
transfer and ablation analysis is required before assigning a
mechanism to their performance. No reduction of physical
activation power is established.

### Stability and independent bistability diagnostic

All 216 tested cavity configurations pass the conservative
uniqueness/stability audit (ambiguous_cavities=0). This is
conditional on the instantaneous single-mode closure, the
0–4 mW range, the stationary-fold check, and sampled grid
and classifier inputs. It does not establish stability with
finite carrier recovery, thermal dynamics or other modes.

The separately specified stress case (ns=.1, sa=20, b=d=h=0,
tau_ext=10 ps, Us=.3 fJ) has three steady-state roots at
incident power 1.55685 mW, of which two are locally stable.
It verifies that the implementation can recognize bistability;
it is not a passing classifier configuration or a measured
device. No history-dependent branch selection was used.

### Independent distributed references

All 30 reference rows (NL005 A/B/C, both drives, five seeds)
have 100% clean and receiver accuracy, including worst repeat
on fresh domain-44 inputs and noise domains 45/46.
Each drive/reference has 81,920 correct sample/repeat outcomes
from 10,240 distinct held-out inputs and eight simulated noise
repeats. The six groups are paired across references; these
are not independent physical measurements or a measured BER.

| Drive mW | Reference | Mean receiver (%) | Worst repeat (%) | Output uW | Min signed field sqrt(mW) | Peak diode mW |
|---:|---|---:|---:|---:|---:|---:|
| 0.1 | A | 100.000000 | 100.000000 | 1.252570 | 0.021730 | 0.063932 |
| 0.1 | B | 100.000000 | 100.000000 | 0.528032 | 0.010235 | 0.060592 |
| 0.1 | C | 100.000000 | 100.000000 | 2.096747 | 0.023061 | 0.067156 |
| 1 | A | 100.000000 | 100.000000 | 3.002775 | 0.009488 | 0.080580 |
| 1 | B | 100.000000 | 100.000000 | 6.046877 | 0.039270 | 0.086197 |
| 1 | C | 100.000000 | 100.000000 | 14.822827 | 0.046426 | 0.101053 |

Candidate B now has perfect accuracy on the new draws;
its previous NL005 low-drive worst repeat was 99.951172%.
This is replication on new samples, not a modified transfer.
The references use direct distributed RK4 and are not cavity
candidates. No conclusion about the best resonator or its
comparison to these references follows from aggregate counts.

### Archive and remaining work

Exact ZIP metadata: 661,907 bytes, SHA-256
64eda82d93c4b08e11059d685ba183279fd98efbdf108980f1012d86c93b1dad.
The archive helper pins all six science-file hashes emitted
by CI, verifies raw ZIP identity, CRC, report counts, stability
summary and staged bytes, and records environment metadata
and provenance. Actual ZIP-byte verification awaits the manual
archive workflow. Initial analysis uses CI stdout only.

After archival, analyze all 2160 seed metrics, 432 grouped
configurations, 216 cavity audits, 14040 transfer samples and
30 references. Identify the three weak passing configurations,
their actual transmission/phase variation and common-drive
intersection; stratify by external lifetime, internal saturation
energy, nonlinear loss, detuning and shift. Compare signed
margin, output, peak cavity energy and local relaxation to
paired distributed references. Distinguish post-hoc diagnostic
ablations from the original screen and validate new hypotheses
on independent data. Do not equate stored energy or external
lifetime with measured pulse threshold, local intensity,
throughput or system energy. Calibration remains outstanding.

## Full archived cavity analysis

Archive PR 148, merge 1e1d886c7c3767c8287d1c7324f52bb38768636f, workflow 44181484363.
Sources: [summary](../results/opa-nl-006/summary.csv),
[metrics](../results/opa-nl-006/metrics.csv),
[cavity audit](../results/opa-nl-006/cavity_audit.csv),
[transfer](../results/opa-nl-006/transfer.csv),
[references](../results/opa-nl-006/references.csv) and
[provenance](../results/opa-nl-006/provenance.json).
Read all 432 groups, 2160 seed metrics, 216 audits, 14040
transfer rows and 30 references. The original archive is
unchanged. All comparisons below are post-hoc analysis of
the preregistered sweep, not new experimental measurements.

### Marginal pass counts

| Parameter | Value | Low drive pass/tested | High drive pass/tested |
|---|---:|---:|---:|
| tau_ext_ps | 2 | 8/72 | 15/72 |
| tau_ext_ps | 10 | 17/72 | 17/72 |
| tau_ext_ps | 50 | 18/72 | 5/72 |
| usat_fj | 0.3 | 24/108 | 13/108 |
| usat_fj | 3 | 19/108 | 24/108 |
| tpa | 0 | 24/108 | 25/108 |
| tpa | 0.1 | 19/108 | 12/108 |
| detuning | -0.5 | 25/72 | 16/72 |
| detuning | 0 | 12/72 | 13/72 |
| detuning | 0.5 | 6/72 | 8/72 |
| shift | 0 | 29/108 | 31/108 |
| shift | 1 | 14/108 | 6/108 |

60/216 low-drive and 45/216 high-drive groups meet the clean
accuracy threshold; 17 and 8 further groups fail the receiver
screen respectively. All modeled diode powers are below 2 mW
(maximum .139579 mW). The maximum recorded clean passivity
excess is negative (-.013897 mW). 15 low-drive and 26 high-drive
groups have perfect worst-repeat accuracy. Longer external
lifetimes help some low-drive cases but hurt high-drive pass
counts in this particular grid. These are conditional counts,
not material yield or monotone causal effects.

### Common component tuples

11/216 distinct tuples pass at both drives; 69 pass at least
one drive. Six are perfect at both. All common tuples have
zero competing nonlinear loss. No weak endpoint tuple passes
both drives. The two drives use separate frozen weight sets.

| Tlow | Thigh | tau ext ps | Us fJ | b | d | h | Low worst % | High worst % |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.1 | 0.4 | 2 | 0.3 | 0 | -0.5 | 1 | 97.607422 | 97.900391 |
| 0.1 | 0.4 | 10 | 0.3 | 0 | -0.5 | 0 | 100.000000 | 100.000000 |
| 0.1 | 0.4 | 10 | 0.3 | 0 | 0 | 0 | 100.000000 | 100.000000 |
| 0.1 | 0.4 | 50 | 3 | 0 | -0.5 | 0 | 99.853516 | 100.000000 |
| 0.1 | 0.4 | 50 | 3 | 0 | 0 | 0 | 100.000000 | 100.000000 |
| 0.1 | 0.4 | 50 | 3 | 0 | 0.5 | 0 | 97.851563 | 99.951172 |
| 0.15 | 0.85 | 2 | 0.3 | 0 | -0.5 | 0 | 98.486328 | 100.000000 |
| 0.15 | 0.85 | 2 | 0.3 | 0 | 0 | 0 | 99.951172 | 100.000000 |
| 0.15 | 0.85 | 10 | 0.3 | 0 | 0 | 0 | 100.000000 | 100.000000 |
| 0.15 | 0.85 | 50 | 3 | 0 | -0.5 | 0 | 100.000000 | 100.000000 |
| 0.15 | 0.85 | 50 | 3 | 0 | 0 | 0 | 100.000000 | 100.000000 |

### Weak reference endpoint family: matched resonance-shift control

All three passing weak (.373,.4) groups have Us=3 fJ, d=-.5,
h=1. Label them W1–W3 below, in archived summary order.
With h=0 and every other parameter and test draw fixed,
all three fail. This matched sweep comparison establishes
the importance of the assumed intensity-dependent detuning
in these particular configurations. It does not isolate
amplitude modulation from phase modulation, because detuning
changes both. It also does not establish a specific Kerr,
carrier, thermal or graphene mechanism. The nominal .027
endpoint depth is not the actual resonant transmission swing.

| Candidate | Drive mW | tau ext ps | b | Clean min % | Mean receiver % | Worst % | Matched h=0 worst % |
|---|---:|---:|---:|---:|---:|---:|---:|
| W1 | 1 | 2 | 0 | 100.000000 | 99.947510 | 99.609375 | 35.888672 |
| W2 | 0.1 | 10 | 0 | 100.000000 | 99.915771 | 99.609375 | 48.925781 |
| W3 | 0.1 | 10 | 0.1 | 100.000000 | 98.873291 | 97.021484 | 42.333984 |

| Candidate | Mean output uW | Min signed field sqrt(mW) | Peak per-channel input mW | Peak stored fJ | Peak diode mW | Min local relaxation rate /ps |
|---|---:|---:|---:|---:|---:|---:|
| W1 | 27.928299 | 0.037491 | 2.850272 | 4.372373 | 0.089011 | 0.293866 |
| W2 | 1.706864 | 0.012042 | 0.294937 | 2.248729 | 0.060337 | 0.058773 |
| W3 | 1.440618 | 0.009905 | 0.294937 | 2.057128 | 0.059007 | 0.063550 |

W3 tolerates b=.1 at low drive with reduced margin relative
to W2. All three have perfect clean accuracy but none is
perfect after noise. The independent distributed A/B/C
references remain perfect at both drives; the weak candidates
do not outperform them in accuracy. W1's mean output exceeds
the paired high-drive reference C (14.822827 uW), while W2
and W3 fall below low-drive C (2.096747 uW). Output power alone
does not determine the signed receiver margin or efficiency.
The peak stored energies are not incident pulse energies.
The local relaxation rates are from the instantaneous
Jacobian over the full evaluated range, not measured recovery
or a validated symbol rate.

### Actual sampled transfer variation

Use the archived subsampled transfer rows only; no interpolation.
Restrict the sample range to powers at or below the maximum
actual per-channel input for each candidate. This is a sampled
envelope including zero, not the distribution of actual
classifier inputs or an exact continuous extremum.
Transmission before the additional 1 dB output loss.

| Candidate | Last sampled input mW within peak | T min % | T max % | Sample swing pp | Phase min deg | Phase max deg |
|---|---:|---:|---:|---:|---:|---:|
| W1 | 2.151392 | 27.166788 | 38.644560 | 11.477772 | -31.413967 | 1.833595 |
| W2 | 0.245487 | 27.166788 | 37.468278 | 10.301490 | -31.413967 | -8.439711 |
| W3 | 0.245487 | 27.166788 | 34.754119 | 7.587331 | -31.413967 | -9.325755 |

| Candidate | Sample input mW | Transmission % | Phase deg | Stored energy fJ |
|---|---:|---:|---:|---:|
| W1 | 0.000000 | 27.166788 | -31.413967 | 0.000000 |
| W1 | 0.028012 | 27.481062 | -30.902059 | 0.030791 |
| W1 | 0.096832 | 28.259448 | -29.615073 | 0.109456 |
| W1 | 0.334733 | 30.938269 | -24.913630 | 0.414242 |
| W1 | 0.848612 | 35.591229 | -14.716308 | 1.208125 |
| W1 | 2.933525 | 38.293498 | 7.084167 | 4.493397 |
| W1 | 4.000000 | 37.447932 | 11.747814 | 5.991669 |
| W2 | 0.000000 | 27.166788 | -31.413967 | 0.000000 |
| W2 | 0.028012 | 28.750846 | -28.786990 | 0.161071 |
| W2 | 0.096832 | 32.514236 | -21.861870 | 0.629682 |
| W2 | 0.334733 | 38.424148 | -2.726609 | 2.572365 |
| W2 | 0.848612 | 37.250196 | 12.562575 | 6.322189 |
| W2 | 2.933525 | 32.717037 | 24.668253 | 19.195249 |
| W2 | 4.000000 | 31.830622 | 26.440111 | 25.464498 |
| W3 | 0.000000 | 27.166788 | -31.413967 | 0.000000 |
| W3 | 0.028012 | 28.599128 | -28.721685 | 0.160221 |
| W3 | 0.096832 | 31.720499 | -21.823992 | 0.614310 |
| W3 | 0.334733 | 34.801665 | -4.253804 | 2.329852 |
| W3 | 0.848612 | 30.949434 | 8.734844 | 5.252809 |
| W3 | 2.933525 | 22.230858 | 17.167041 | 13.042955 |
| W3 | 4.000000 | 20.061305 | 17.867754 | 16.049044 |

The low-power transmission is about 27.17% in these detuned
cases, not .373. W1/W2/W3 have sampled swings of roughly
11.48, 10.30 and 7.59 percentage points, respectively,
within the classifier peak-input envelope. Their sampled
phase excursions are also significant. Therefore the weak
reference endpoint result must not be interpreted as a
classifier operating with only 2.7 percentage points of
actual transmission swing. High-power roll-off is visible
even without b due to detuning past resonance; b additionally
reduces transmission. All sampled configurations pass the
instantaneous uniqueness/stability gate; across all 216
audits the minimum relaxation rate ranges from .008975 to
.589904 /ps, not a device clock specification.

### NL007 next experiment: mechanism isolation and detuning tolerance

Before introducing a calibrated material or geometry, perform
a preregistered independent-data diagnostic of the three
weak candidates and strong common reference tuples. Separate
the full complex transfer H(P) into amplitude-only with
constant low-power phase, phase-only with constant low-power
amplitude, and linear frozen complex gain controls. These
are numerical ablations, not independent physical components.
Also switch off saturable loss at fixed unbleached loss and
switch off nonlinear detuning separately, preserving passive
port accounting for the physical TCMT variants. Compare
signed field margin, accuracy and noise with the same frozen
weights and independent paired draws. Evaluate a finer
signed detuning and shift sweep around W2/W3, including
calibration drift and zero nonlinear shift, without choosing
phase alignment from test labels. Keep actual transmission
range, cavity stored energy, and incident power separate.
Retain independent reference curves and root/stability gates.

Only after isolating the mechanism should we pursue finite
material response and pulsed TCMT, with measured coupling,
linewidth, nonlinear shift and recovery where available.
Neither the weak-family success nor these proposed ablations
establishes a fabricated weak-absorption device, a reduction
in physical activation energy, or a throughput advantage.
