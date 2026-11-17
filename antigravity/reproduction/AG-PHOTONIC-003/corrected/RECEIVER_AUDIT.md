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
