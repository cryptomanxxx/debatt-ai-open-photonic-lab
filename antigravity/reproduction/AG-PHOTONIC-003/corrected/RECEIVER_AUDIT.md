# OPA-SYS-003 — receiver and source diagnostic

SYS002 showed 147 new analytically feasible comb configurations, all 4-bit.
The next experiment isolates receiver and source assumptions before another
architecture sweep. No changes to original or stage-one evaluator.

## Observed issues in source

- Receiver uses fixed B_rx/B_opt=0.2 for ASE beats even when modulation rate
  and optical bandwidth differ. Nominal 10 GHz modulation gives B_rx=7 GHz;
  if optical bandwidth is 50 GHz, the ratio is 0.14, not 0.2.
- RIN ceiling includes an assumed 20 dB common-mode rejection and rejects
  the final 5% of the mathematical margin. This is not a measured CMRR.
- Independent laser bank total is compared with a single-pump power limit.
- Booster saturation uses modeled signal output but omits ASE and does not
  consistently account for its upstream reference plane.
- Balanced coherent readout requires explicit LO power, shot noise and
  electrical cost; the legacy per-PD signal-current formula has no LO.
  Balanced direct detection is not interchangeable with coherent detection.

## Diagnostic design

432 receiver cases: bits 4/6/8/12, symbol rate 5/10/25 GHz, CMRR
0/10/20/30 dB, optical bandwidth 25/50/100 GHz, received ASE 0/1/10 uW.
Independent numerical root reproduces legacy quadratic at its assumed
ratio and margin, and checks SNR at each finite root. Explicit rectangular
bandwidth remains an approximation, not a complete ASE spectral integral.

288 fixed-reference-plane link cases: comb versus independent laser,
15/20/25/30 dB downstream loss, 8/16 wavelengths, 1/4 rings per pump
(comb only), 4/6/8 bits, gain 0/10/20/25 dB. Report per-source and bank
power, threshold floor, in-band output signal+ASE saturation and lower
bound on electrical power needed for incremental amplification. Comb
bank denotes one pump feeding the specified branches, not whole chip.
Assume no extra upstream loss besides explicit coupling/splitting.
Threshold surplus, out-of-band ASE, amplifier idle power and actual
optical filter response are not modeled.

12 ideal coherent receiver controls: 4/6/8/12 bits, total LO at hybrid
0.1/1/10 mW. Difference current 2R sqrt(Ps Plo); shot noise from total
incident signal and LO; TIA noise as assumed input-referred differential
noise. Omit RIN, imbalance, saturation, ASE and phase tracking deliberately;
LO electrical cost is a lower bound excluding distribution. This is not
a replacement for the legacy receiver or a claim of achievable ENOB.

Results: result.json, receiver.csv, link.csv, coherent.csv. No convergence,
full architecture feasibility or measured system efficiency inference.
Next: analyze results, validate receiver topology and amplifier parameters,
then make attributable model corrections. Preserve SYS002 evidence.

## Observed results — 2026-11-17

[CI run 44110377779](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44110377779)
completed with 9/9 checks. Original ZIP 37403 bytes, SHA-256
a8fca83090e05522b5d2f82843dc36d758ff00c75f950fff8805b404dc3b7a44,
independently verified against GitHub metadata, ZIP CRC and extracted
file digests. Six evidence files are pinned by archive_sys003.py.
Permanent Git archive is pending the explicit archive workflow.

### Link-only pass counts

| Bits | Comb | Independent lasers |
|---:|---:|---:|
| 4 | 37/64 | 26/32 |
| 6 | 6/64 | 12/32 |
| 8 | 0/64 | 6/32 |

A pass means required receiver SNR, per-source optical limit and in-band
amplifier saturation are satisfied under the diagnostic assumptions.
No complete accelerator is tested here. No unamplified comb 6-bit case
passes; all six passing cases use 10 or 20 dB gain and 15 or 20 dB
downstream loss, as detailed below.

| Downstream loss dB | Lines | Rings/pump | Gain dB | Pump optical mW | Booster optical output mW per ring |
|---:|---:|---:|---:|---:|---:|
| 15 | 8 | 1 | 10 | 76.950 | 54.478 |
| 15 | 8 | 1 | 20 | 42.376 | 174.866 |
| 15 | 8 | 4 | 10 | 353.400 | 54.478 |
| 15 | 8 | 4 | 20 | 194.617 | 174.866 |
| 15 | 16 | 1 | 10 | 153.899 | 108.956 |
| 20 | 8 | 1 | 10 | 217.025 | 153.644 |

For the 15 dB, 8-line, 1-ring case, the 10 dB gain scenario has
0.38475 W pump electricity and 0.49030 W lower-bound amplifier
electricity, versus 0.21188 and 1.73118 W respectively at 20 dB gain.
Higher gain reduces pump power but increases the combined lower bound
from 0.87505 to 1.94306 W. Four-ring cases require one amplifier per
ring under this illustration: multiply the per-ring amplifier bound
by four before adding the shared pump electricity. These bounds are
not chip/system power predictions.

### Nominal receiver diagnostic

At 10 GHz, CMRR 20 dB, 50 GHz optical bandwidth, explicit ratio 7/50=0.14:

| Bits | Target dB | No ASE mW | 1 uW ASE mW | 10 uW ASE mW |
|---:|---:|---:|---:|---:|
| 4 | 29.35 | 0.042008 | 0.488077 | 4.827479 |
| 6 | 41.39 | 0.182009 | 7.774094 | 77.396846 |
| 8 | 53.43 | 1.019059 | 130.268852 | 1297.459698 |
| 12 | 77.51 | no finite root | no finite root | no finite root |

At six bits and 1 uW received ASE, legacy requires 11.08847 mW;
the diagnostic requires 7.77409 mW (about 29.9% lower). No-ASE roots
agree. Nominal RIN ceiling is 66.549 dB, which rules out 12 bits in
this convention but not six or eight bits. Mathematical roots do not
imply a PD/TIA can operate at those powers. No detector saturation,
real spectrum, or modulation-depth limit is included.

### Ideal coherent control

At six bits, LO 0.1/1/10 mW yields signal requirements
0.082618/0.015408/0.009258 mW and LO electrical lower bounds
0.0005/0.005/0.05 W per receiver. The ideal 1 mW LO control reduces
the required signal relative to the legacy no-ASE result, but the
two current conventions are not a calibrated matched comparison.
LO distribution, total shot noise including other channels, residual
RIN, amplifier ASE, phase tracking and saturation must be addressed
before any architecture-level claim.

### Next attributable model correction

Implement a separate stage-two evaluator on top of SYS002, first
changing only receiver bandwidth/RIN-margin and independent-laser
power-limit accounting in individually switchable variants. Explicitly
document bandwidth and source reference planes; compare same keys and
rejection transitions. Treat amplifier gain/saturation and coherent LO
as separate hypotheses requiring explicit topology and noise/power
validation. Do not directly insert ideal coherent control into the
legacy model or treat link-only passes as full-system feasibility.
Check the six passing comb scenarios against actual path losses,
throughput, area, endurance and eventually convergence.
