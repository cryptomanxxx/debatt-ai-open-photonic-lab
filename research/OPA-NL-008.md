# OPA-NL-008 — Dynamic optical activation and intersymbol memory

Status: preregistered numerical experiment; results pending CI.
Builds on [NL006](OPA-NL-006.md) and the
[full NL007 analysis](OPA-NL-007.md). The six candidate
tuples are post-hoc selections from the archived NL007
no-bleaching sweep, tested here on independent inputs.

## Physical model and candidates

Use the same symmetric two-port single-mode TCMT convention
as NL006. All candidates have fixed unbleached linear loss
ns=1/sqrt(.373)-1, no saturable absorption, external energy
lifetime tau=10 ps, and hypothetical energy scale Us=3 fJ.
The energy scale now describes the saturation of nonlinear
detuning, not absorber bleaching. b is dimensionless
competing nonlinear loss per normalized stored energy.

| Candidate | b | d | h | Selection |
|---|---:|---:|---:|---|
| C1 | 0 | -.8 | 1 | Best common-drive worst accuracy |
| C2 | 0 | -.8 | .8 | Common-drive |
| C3 | 0 | -.7 | .8 | Common-drive |
| L1 | 0 | -.8 | 1.5 | Perfect low-drive W2 |
| L2 | .1 | -.8 | 1.5 | Perfect low-drive W3 |
| H1 | .1 | -.8 | .5 | Sole high-drive W3 pass |

Let a be the complex intracavity amplitude in sqrt(fJ),
s the incident signed coherent envelope in sqrt(mW),
U=abs(a)^2, x=U/Us, k=1/tau, c=sqrt(k/2).
For response time tr>0:

    da/dt = k*(-(1+ns+b*x)/2 + i*(d+h*q))*a + c*s
    dq/dt = (x/(1+x)-q)/tr

For tr=0 use q=x/(1+x) directly in the field RHS at
each RK stage (no integrated material state). The shift
model is phenomenological; it does not establish a Kerr,
carrier or thermal response. q is dimensionless and
does not have a separately modeled energy reservoir.

Drop field c*a; reflected field s-c*a; internal absorbed
power k*(ns+b*x)*U. The energy identity is

    dU/dt = abs(s)^2 - abs(s-c*a)^2 - abs(c*a)^2
            - k*(ns+b*x)*U.

The additional 1 dB output attenuation follows the drop
port and is excluded from the cavity energy balance.
Transient drop power can exceed instantaneous incident
power due to stored energy, so do not apply the NL007
static pointwise input/output passivity inequality.
Test the integrated cavity energy balance instead and
verify the second MVM remains a contraction.

## Dynamic protocol

Cartesian grid per candidate: on duration 10, 50, 200 ps;
zero-input gap 0 or 20 ps; hypothetical material response
time 0, 5, 50 ps. Both drive scales .1 and 1 mW, using
five frozen absorber weight sets per drive from NL003.

Fresh balanced jittered XOR test domain 64, 128 samples
per seed and drive, explicitly shuffled using domain 65
independent of labels. Arrange into 16 parallel independent
eight-symbol streams, each initially empty. Same order
and inputs across all candidate and timing conditions.
The signed input envelope from the first MVM is held
constant throughout each on interval, then zero in the gap.

Two paired histories:
- cold: reset both field and material state before each
  symbol, a diagnostic independent-pulse limit; discarded
  residual energy is outside the modeled segment, and this
  is not a physically cost-free reset.
- stream: carry field and material state through the gap
  and all subsequent symbols without resets.

Sample the complex drop field at the end of the on interval,
before the gap. Apply the extra 1 dB attenuation, then
the frozen second MVM. Do not optimize the sample time
or phase on test labels. Compare to a directly solved
stationary reference on identical inputs. Record maximum
absolute difference between stream and cold output fields
and versus stationary output; include first-stream symbol
traces of the complex classifier output. The eight-symbol
streams bound the investigated memory horizon.

Apply the inherited absolute activation-output noise with
fresh domain 66 and receiver draws domain 67, eight repeats.
Same nominal receiver (.1 mW LO, 1 GHz ENBW, 3 dB loss,
15 degree phase). This is a conditional noise diagnostic,
not a model of receiver impulse response, integration,
bandwidth matching or independent noise at the tested
cadence. No physical bit rate or throughput claim.
Report clean real-field and clean projected accuracy,
mean receiver accuracy, worst repeat, minimum projected
margin and peak sampled noisy diode power.

## Integration and checks

Fixed-step RK4, input constant within each on/gap segment,
coarse .5 ps and fine .25 ps (adjust steps to segment end).
Integrate reflected/drop/absorbed powers with the same
RK4 stage quadrature. Incident energy is exact for the
rectangular envelope. For each slot and channel check
abs(Ein+Uinitial-Erefl-Edrop-Eabs-Ufinal) divided by
(1+Ein+Uinitial), with fJ units. Report max over both
histories and resolutions. Accumulate energy terms
including slot initial and final stored energy separately;
their sum is not a wall-plug energy budget. For cold
history initial energy is zero; final energy at a reset
is explicitly recorded. For stream history the slot
boundary terms telescope, except initial/final stream
state. No hidden loss is assumed at the segment boundaries.

Compare fine/coarse complex sampled activation fields
(max absolute difference <1e-5 sqrt(mW)) and aggregate
energy terms (normalized difference <1e-5). Require
slot balance <1e-6, sampled q within [0,1] to numerical
tolerance, and passive second MVM. Independent analytic
linear step, differential energy identity, and long
constant excitation (1500 ps) versus NL006 steady solver
for four signed input amplitudes and all response times.
Use inherited stationary eligibility: no folds within
0–4 mW, unique stable instantaneous roots at the 513-point
grid and all actual inputs. This does not prove finite-
response dynamical stability; the time-domain tests are
bounded trajectories, not a global stability theorem.

Screen all five seeds: eligible stationary parent,
clean pre-receiver accuracy >=95%, worst noisy repeat
>=95%, peak sampled diode <=2 mW. Keep science failures
separate from implementation failures. Smaller test set
than NL007, so do not directly compare perfect-accuracy
fractions or interpret them as BER or hardware yield.

6 candidates x 18 timing cases = 108 convergence audits;
432 labeled groups including both drives and histories;
2160 seed-level metrics; 60 paired stationary reference
rows; 8640 first-stream symbol trace rows. Check counts,
weight count, first-symbol equality, cold memory zero,
finite results and prior archive hashes/immutability.
All earlier research artifacts remain unchanged.

## Limits and next steps

No spatial pulse propagation or dispersion, no measured
nonlinear coefficient, mode volume or geometry, no
material-specific recovery law, no dynamic receiver,
no continuous cadence guarantee. Rectangular envelopes
have idealized abrupt transitions. Before moving to
material calibration, identify candidate/timing windows
and failure modes, check longer streams and independent
step-size convergence where needed. Retain the combined
no-bleaching amplitude-only diagnostic as separate
follow-up, not a physical cavity. Do not infer energy
savings from stored optical energy or signal duration.

## Initial observed results — 17 November 2026

[Experiment run 44192685431](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44192685431),
job 134426029605, source PR 154, artifact 14377357687.
All 14 implementation checks passed. No implementation failures.
The report contains 2160 seed rows, 432 groups and 60 paired
stationary references. This initial analysis uses the CI-emitted
JSON report, not yet the raw archived CSVs.

| Numerical diagnostic | Observed maximum |
|---|---:|
| Long-step stationary field error (sqrt(mW)) | 9.03010273e-12 |
| Normalized slot energy imbalance | 3.91443012e-7 |
| Fine/coarse sampled field difference (sqrt(mW)) | 1.42437945e-7 |
| Normalized fine/coarse aggregate energy difference | 5.24195381e-7 |

### Accuracy screens

Each cell is passing groups out of 18 independently labeled
timing combinations; cold resets are diagnostics.

| Candidate | .1 mW cold | .1 mW stream | 1 mW cold | 1 mW stream |
|---|---:|---:|---:|---:|
| C1 | 10/18 | 10/18 | 12/18 | 11/18 |
| C2 | 10/18 | 10/18 | 12/18 | 10/18 |
| C3 | 10/18 | 10/18 | 12/18 | 10/18 |
| L1 | 12/18 | 10/18 | 2/18 | 0/18 |
| L2 | 10/18 | 10/18 | 2/18 | 0/18 |
| H1 | 0/18 | 0/18 | 6/18 | 4/18 |

98/216 cold groups and 85/216 stream groups pass, total
183/432. All 85 successful stream groups use on durations
of 50 or 200 ps. No 10 ps stream group passes. Cold
aggregates cannot establish which individual timing cases
pass, nor distinguish history losses from gains; that
requires the archived summary and metrics files.

### Stream timing breakdown

Each timing row has 12 candidate/drive groups.

| On ps | Response ps | Gap ps | Pass/12 | Perfect/12 |
|---:|---:|---:|---:|---:|
| 10 | 0 | 0 | 0/12 | 0/12 |
| 10 | 0 | 20 | 0/12 | 0/12 |
| 10 | 5 | 0 | 0/12 | 0/12 |
| 10 | 5 | 20 | 0/12 | 0/12 |
| 10 | 50 | 0 | 0/12 | 0/12 |
| 10 | 50 | 20 | 0/12 | 0/12 |
| 50 | 0 | 0 | 8/12 | 4/12 |
| 50 | 0 | 20 | 8/12 | 6/12 |
| 50 | 5 | 0 | 8/12 | 4/12 |
| 50 | 5 | 20 | 8/12 | 5/12 |
| 50 | 50 | 0 | 0/12 | 0/12 |
| 50 | 50 | 20 | 1/12 | 0/12 |
| 200 | 0 | 0 | 9/12 | 5/12 |
| 200 | 0 | 20 | 9/12 | 5/12 |
| 200 | 5 | 0 | 9/12 | 5/12 |
| 200 | 5 | 20 | 9/12 | 5/12 |
| 200 | 50 | 0 | 8/12 | 5/12 |
| 200 | 50 | 20 | 8/12 | 5/12 |

By duration: 0/72 at 10 ps, 33/72 at 50 ps, 52/72 at
200 ps. There are 49/216 perfect stream groups.
The 50 ps no-gap condition has a nominal envelope cadence
of 20 Gsymbols/s, not a validated hardware rate or receiver
bandwidth. The fixed 1 GHz noise diagnostic cannot establish
operation at this cadence.

### Common-drive stream cases

30 candidate/timing tuples pass at both drives; the
frozen network weights differ between drives. All common-drive
tuples are from C1/C2/C3.

| Candidate | On ps | Response ps | Gap ps | .1 mW worst % | 1 mW worst % |
|---|---:|---:|---:|---:|---:|
| C1 | 50 | 0 | 0 | 100.000000 | 99.218750 |
| C1 | 50 | 0 | 20 | 100.000000 | 100.000000 |
| C1 | 200 | 0 | 0 | 99.218750 | 100.000000 |
| C1 | 200 | 0 | 20 | 99.218750 | 100.000000 |
| C1 | 50 | 5 | 0 | 99.218750 | 100.000000 |
| C1 | 50 | 5 | 20 | 99.218750 | 100.000000 |
| C1 | 200 | 5 | 0 | 99.218750 | 100.000000 |
| C1 | 200 | 5 | 20 | 99.218750 | 100.000000 |
| C1 | 200 | 50 | 0 | 99.218750 | 100.000000 |
| C1 | 200 | 50 | 20 | 99.218750 | 100.000000 |
| C2 | 50 | 0 | 0 | 98.437500 | 100.000000 |
| C2 | 50 | 0 | 20 | 98.437500 | 100.000000 |
| C2 | 200 | 0 | 0 | 98.437500 | 100.000000 |
| C2 | 200 | 0 | 20 | 98.437500 | 100.000000 |
| C2 | 50 | 5 | 0 | 98.437500 | 100.000000 |
| C2 | 50 | 5 | 20 | 98.437500 | 100.000000 |
| C2 | 200 | 5 | 0 | 98.437500 | 100.000000 |
| C2 | 200 | 5 | 20 | 98.437500 | 100.000000 |
| C2 | 200 | 50 | 0 | 97.656250 | 100.000000 |
| C2 | 200 | 50 | 20 | 97.656250 | 100.000000 |
| C3 | 50 | 0 | 0 | 98.437500 | 99.218750 |
| C3 | 50 | 0 | 20 | 98.437500 | 100.000000 |
| C3 | 200 | 0 | 0 | 98.437500 | 100.000000 |
| C3 | 200 | 0 | 20 | 98.437500 | 100.000000 |
| C3 | 50 | 5 | 0 | 98.437500 | 98.437500 |
| C3 | 50 | 5 | 20 | 98.437500 | 100.000000 |
| C3 | 200 | 5 | 0 | 98.437500 | 100.000000 |
| C3 | 200 | 5 | 20 | 98.437500 | 100.000000 |
| C3 | 200 | 50 | 0 | 98.437500 | 100.000000 |
| C3 | 200 | 50 | 20 | 98.437500 | 100.000000 |

C1 at 50 ps, zero gap and 5 ps response passes both drives:
99.218750% and 100% worst repeat. At 50 ps, 20 ps gap and
instantaneous response both are perfect. Neither demonstrates
physical 20 Gbaud or a single network working at both powers.
For C1 at 50 ps and 5 ps response, maximum stream-cold
classifier field difference at .1/1 mW is respectively
.002965690/.030126220 sqrt(mW) without gaps and
.001111021/.006269989 sqrt(mW) with 20 ps gaps. This is
direct evidence of history sensitivity in the conditional
model even when the accuracy gate passes. A gap does not
necessarily improve accuracy. The maximum deviations are
from possibly different samples and seeds.

L1 and L2 each have ten perfect low-drive stream groups
and no passing high-drive stream group. H1 passes four
high-drive stream groups (200 ps, response 0 or 5 ps,
both gaps), none at low drive. The stationary reference
for H1 low drive has perfect clean accuracy but fails
the receiver gate. L1/L2 high-drive stationary references
fail the gate, so their failures cannot be attributed
solely to temporal memory.

### Stationary reference comparison

| Candidate | Drive mW | Min clean % | Worst repeat % |
|---|---:|---:|---:|
| C1 | 0.1 | 100.000000 | 99.218750 |
| C1 | 1 | 100.000000 | 100.000000 |
| C2 | 0.1 | 100.000000 | 98.437500 |
| C2 | 1 | 100.000000 | 100.000000 |
| C3 | 0.1 | 100.000000 | 98.437500 |
| C3 | 1 | 100.000000 | 100.000000 |
| L1 | 0.1 | 100.000000 | 100.000000 |
| L1 | 1 | 3.125000 | 0.000000 |
| L2 | 0.1 | 100.000000 | 100.000000 |
| L2 | 1 | 0.000000 | 0.000000 |
| H1 | 0.1 | 100.000000 | 81.250000 |
| H1 | 1 | 100.000000 | 96.875000 |

The 128-sample test per seed is smaller than NL007; perfect
classification is not a physical BER estimate. No retraining,
phase optimization or timing selection on held-out labels
was done in the experiment. Identifying promising conditions
from this completed sweep is post-hoc.

### Archive and follow-up

Source ZIP 544319 bytes; SHA-256
27dfe96872e4a15292cdf9b65befdb4d305d63ed2ef3bba6046972c404882c01.
The manual archive workflow pins this ZIP, verifies CRC,
six CI-emitted science hashes, report counts and exact
staged bytes. The raw ZIP has not yet been verified by
that workflow. Permanent archive follows review.

After archival, compare paired cold and stream groups
including failures, examine the signed projected margins
and sampled complex-field traces, and quantify energy
accounting and convergence across timing cases. Resolve
the 10–50 ps transition on independent data and longer
sequences. A future dynamic receiver must account for
integration, bandwidth, phase and correlated noise at
the selected cadence. Material calibration remains open;
the saturating index response is hypothetical, not a
measured material law. No hardware speed or wall-plug
energy advantage has been established.
