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

## Observed results — 2026-11-17

[CI run 44118436433](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44118436433)
passed all ten checks, including exact SYS004 baseline reproduction
and independent accounting checks on 5,147 feasible corrected records
(2,389 fixed-max plus 2,758 optimized, not unique links).
Artifact 14343438072 was downloaded and independently verified:
ZIP size 1,190,343 bytes, SHA-256
6045ee657ecab9e8045631ec713887e9194393028ba044100aa7803b12b15753,
CRC passed, seven extracted files pinned in archive_sys005.py.
Permanent archive pending explicit workflow.

| Architecture / bits | Legacy | Corrected fixed-max | Optimized |
|---|---:|---:|---:|
| MZI / 4 | 83 | 470 | 554 |
| MZI / 6 | 0 | 0 | 51 |
| MRR / 4 | 164 | 773 | 853 |
| MRR / 6 | 0 | 0 | 37 |
| Hybrid / 4 | 144 | 649 | 702 |
| Hybrid / 6 | 0 | 0 | 64 |
| Independent laser / 4 | 226 | 226 | 226 |
| Independent laser / 6 | 182 | 182 | 182 |
| Independent laser / 8 | 82 | 82 | 82 |
| SingleWave / 4 | 5 | 7 | 7 |
| Total | 886 | 2,389 | 2,758 |

Independent ZIP inspection confirmed unique keys in each list, no
removed legacy or corrected fixed-max keys, and 1,872 additional
optimized keys relative to legacy (369 relative to corrected fixed-max).
The CSV contains 76,050 changed records. The corrected fixed-max model
adds 1,503 feasible keys; optimizing gain adds a further 369, of which
152 are six-bit comb candidates. No eight-bit comb candidate passes.
Optimized transitions from legacy optical rejection: 1,872 feasible,
2,627 throughput-limited, 857 endurance-limited. All other rejection
categories unchanged.

| Best system proxy TOPS/W | Legacy | Fixed-max | Optimized |
|---|---:|---:|---:|
| Hybrid 4-bit | 1.6749 | 2.2421 | 2.2481 |
| MZI 4-bit | 1.5716 | 1.9172 | 1.9407 |
| MRR 4-bit | 0.6918 | 1.2327 | 1.3002 |
| Hybrid 6-bit | — | — | 1.2428 |
| MZI 6-bit | — | — | 0.8899 |
| MRR 6-bit | — | — | 0.3800 |
| Independent laser 6-bit | 1.5405 | 1.5405 | 1.5405 |
| Independent laser 8-bit | 0.6359 | 0.6359 | 0.6359 |

Best overall optimized candidate is Hybrid, distributed, eight pumps
and combs, eight wavelengths, 16x16 mesh, eight tiles, TFLN, four bits:
23 dB gain, 488.467 TOPS, 217.283 W, 2.2481 TOPS/W. Not a matched
training comparison. Assumed electronic reference is 3.5 TOPS/W.

### First six-bit comb candidates

The 152 new six-bit comb keys select gains from 14 to 19 dB:
14:16, 15:18, 16:49, 17:51, 18:8, 19:10.
Pump launch spans 115.195–495.223 mW per pump;
in-band booster output spans 108.153–249.742 mW per booster.
These are conditional analytical passes, not measured precision.

Best six-bit comb candidate: distributed Hybrid, eight pumps,
eight combs, eight wavelengths, 8x8 mesh, eight tiles, Pockels TFLN.
Selected gain 14 dB; 347.727 mW optical per pump; 246.177 mW in-band
output per booster against 250 mW assumed saturation limit.
Total path loss 25.8759 dB (4 upstream, 21.8759 downstream).
Receiver signal 0.199783 mW, ASE 0.000003995 mW.
122.117 sustained TOPS; 98.256 W system proxy; 120.05 mm²;
1.2428 TOPS/W system and 5.9548 TOPS/W chip-only.
Laser electricity 13.909 W; booster proxy 19.694 W; total optical
electricity 33.603 W. Memory 31.674 W; cooling 12.816 W.
The best candidate sits within about 1.53% of the modeled booster
saturation cap; omitted out-of-band ASE, saturation dynamics and
real component tolerances could invalidate the pass.
The best independent-laser six-bit system proxy remains 1.5405 TOPS/W.
No candidate beats the assumed electronic reference.

## Next bounded investigation

Archive exact evidence first. Then independently test convergence of
six-bit comb and six/eight-bit independent-laser candidates against
matched digital controls, with explicit mapping from receiver noise
to numerical errors, paired seeds and sensitivity to saturation margin,
noise and precision. Retain idealized training controls separately;
do not claim hardware accuracy from nominal SNR. A compact toy task
does not establish performance on large language models. Preserve
the original evidence and all stage baselines. Remaining topology,
detector/LO and workload assumptions should be clearly identified in
the final report rather than silently treated as validated.
