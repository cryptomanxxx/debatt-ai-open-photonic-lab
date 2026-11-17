# OPA-SYS-005 — booster reference planes and gain selection

Compare three policies on the same 330,960 configurations, with SYS004
receiver and laser-limit corrections enabled in all policies. A fourth
evaluation invokes the untouched SYS004 evaluator for exact comparison.

- Legacy: unchanged SYS004 passive-first, then maximum gain.
- Fixed max: corrected booster accounting, passive first, then maximum gain.
- Optimized: same corrected accounting, choose minimum total source plus
  amplifier electrical power from passive and integer 1 dB gain points
  through nominal maximum (25 dB), including exact maximum. Since other
  system costs and throughput are unchanged for a fixed configuration,
  this minimizes the modeled system power among these points.

The fixed-max vs optimized comparison isolates gain policy. Legacy vs
fixed-max combines reference-plane, booster-count and saturation changes;
do not attribute that difference solely to gain.

## Optical accounting

Place the booster after pump rejection and comb spectral roll-off.
Separate upstream and downstream loss. Given required receive signal
power and received ASE, invert only downstream attenuation to obtain
booster signal output; divide by gain and invert upstream loss to
obtain source requirement. Use the same approximate noise figure and
receiver equations as SYS004. Include in-band ASE in saturation:
N_lambda * (signal output + ASE output). Count one booster per comb,
or per independent-laser bank (one central bank or one per tile).
Passive path has no amplifier or ASE. Retain the full in-band optical
output / WPE electrical proxy, not SYS003's incremental lower bound.

If pump threshold forces excess comb light, assume ideal attenuation
before the booster and charge the entire pump electricity. Record
discarded surplus per comb output bank. This is conditional on fixed
conversion efficiency and ideal attenuator, not a demonstrated device.
No claim of real saturation behavior, out-of-band ASE, gain-dependent
noise figure, detector linearity, LO cost or fabrication readiness.

## Checks and outputs

Require exact SYS004 legacy records and archived rejection counts;
independent SNR, source launch, booster signal/ASE, saturation and
power checks on all feasible corrected records; passive zero ASE
and zero amplifier cost; optimized optical cost no higher than fixed
max for every feasible fixed-max configuration; original and prior
stage bytes unchanged. Preserve all previously archived results.

Outputs: result.json, paired_changes.csv, three full feasible lists,
counts per architecture/precision and gain histograms, best >=6-bit
comb if any. Include actual selected gain, per-booster output,
receiver signal/ASE and source/booster costs. No convergence test.
The nominal optical model remains conditional; a negative result is
scientifically valid. The remaining six roadmap tracks are deferred.

Run from repository root:
```sh
python simulations/circuit/ag003_gain_sweep_v005.py
```
