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
