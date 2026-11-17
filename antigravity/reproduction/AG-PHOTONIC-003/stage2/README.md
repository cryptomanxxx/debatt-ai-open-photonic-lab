# OPA-SYS-004 — isolated receiver and laser-limit corrections

Stage 1 (SYS002) and original bytes remain unchanged. Stage 2 has two
independent flags, off by default:

- corrected_receiver: replace fixed ASE beat bandwidth ratio 0.2 with
  electrical noise bandwidth divided by assumed optical bandwidth
  (channel spacing); use the actual RIN asymptotic feasibility condition
  rather than the arbitrary 5% safety margin. The same legacy current
  convention, CMRR and noise terms remain. This is not a calibrated
  receiver or coherent receiver model.
- corrected_laser_limit: for IndepLaser_MZI only, compare the aggregate
  optical bank power with N_lambda times the single-source limit.
  This is equivalent to comparing each equally loaded laser with its
  own limit. Aggregate bank power, WPE accounting and BOM remain unchanged.

Four variants (both off, receiver only, laser only, both on) evaluate
the same 330,960 unique configuration keys (1,323,840 variant evaluations).
An additional 330,960 reference evaluations directly compare the
unchanged stage-one evaluator against both-off stage two. Require exact
agreement of full baseline feasible records and rejection counts with
the archived SYS002 evidence. Compare 108 receiver roots independently
against the SYS003 numerical solver; require laser-only controls outside
independent laser architecture to be unchanged. Original hashes and
stage-one bytes must remain unchanged.

Outputs: result.json, paired_changes.csv and four full feasible lists.
Results grouped by architecture and bits; report best >=6-bit comb
candidate if any, without convergence claims. Rank on existing rounded
system-efficiency metric only.

The six conditional SYS003 links motivate further gain and path-loss
work but are not inserted directly here. The original fixed maximum
gain policy, saturation model, optical reference planes, LO omission,
detector saturation omission, SingleWave comb treatment, timing and
other assumptions remain. Subsequent experiments must address those
separately. A negative result is valid; no guarantee of six-bit comb
feasibility. No matched hardware or AI training benchmark.

Run from repository root:
```sh
python simulations/circuit/ag003_receiver_sweep_v004.py
```

## Observed results — 2026-11-17

[CI run 44113634095](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44113634095)
passed 10/10 checks, including exact baseline candidates and rejection
counts, 108 independent receiver roots and original/stage-one immutability.
Artifact 14340214791 (482695 bytes) was independently downloaded, ZIP SHA-256
matched GitHub metadata, CRC passed, and all eight extracted file digests
were recorded in archive_sys004.py. [Permanent archive](../../../../results/opa-sys-004/) complete.

| Architecture | Baseline | Receiver only | Laser only | Combined |
|---|---:|---:|---:|---:|
| MZI | 83 | 83 | 83 | 83 |
| MRR | 119 | 164 | 119 | 164 |
| Hybrid | 144 | 144 | 144 | 144 |
| SingleWave_MZI | 5 | 5 | 5 | 5 |
| IndepLaser_MZI | 121 | 121 | 490 | 490 |
| Total | 472 | 517 | 841 | 886 |

Independent inspection of all four feasible lists found unique keys,
no removed baseline keys, and combined exactly equal to the union
of receiver-only and laser-only feasible keys. The new sets do not overlap.
Of 414 new candidates, 45 are 4-bit MRR, 135 are 4-bit independent laser,
152 are 6-bit independent laser, and 82 are 8-bit independent laser.
All 82 eight-bit candidates are unamplified. Combined contains 622 four-bit,
182 six-bit, and 82 eight-bit configurations; no twelve-bit candidate.
There are 391 comb candidates, all four-bit. The paired CSV contains
75,320 changed records (not a complete list of all configurations).

Combined changes 1,227 optical-link-budget rejections: 414 become feasible,
558 fail minimum throughput and 255 fail endurance. No other rejection
categories change. Receiver-only adds 45, laser-only adds 369.

| Architecture/precision | Best baseline TOPS/W | Best combined TOPS/W |
|---|---:|---:|
| MZI 4-bit | 1.5329 | 1.5716 |
| MRR 4-bit | 0.6471 | 0.6918 |
| Hybrid 4-bit | 1.6279 | 1.6749 |
| Independent laser 4-bit | 2.0842 | 2.1361 |
| Independent laser 6-bit | 1.5405 | 1.5405 |
| Independent laser 8-bit | none | 0.6359 |

Best combined overall: distributed independent laser, 8 wavelengths,
16x16 mesh, 8 tiles, Pockels TFLN, 4 bits; 488.467 TOPS, 228.677 W
system proxy, 64 lasers, 733.73 mW per bank (91.72 mW per laser).
Best six-bit remains original CFG-0100. Best newly feasible six-bit
candidate: distributed independent laser, 16 wavelengths, 8x8 mesh,
16 tiles, Pockels TFLN; 1.5381 TOPS/W, 485.452 TOPS, 315.614 W,
319.30 mm² versus 487.04 mm² for the original six-bit leader.
Best eight-bit: distributed independent laser, 8 wavelengths,
8x8 mesh, 16 tiles, Pockels TFLN; 244.234 TOPS, 384.088 W,
0.6359 TOPS/W, 2508.30 mW per bank (313.54 mW per laser),
128 lasers. No amplifier. None of these best system proxies exceeds
the assumed 3.5 TOPS/W electronic baseline; no matched measured comparison.

All feasible results are conditional on legacy workload, receiver and
power assumptions, not hardware feasibility or demonstrated training.
Nominal precision is not validated end-to-end ENOB. Earlier toy
convergence results do not independently establish convergence here.

## Next experiment

Test gain selection and consistent signal/ASE reference planes separately
from the two SYS004 changes. Start with explicit per-booster signal and
ASE output, saturation including in-band ASE, threshold-floor surplus
and source/booster topology; compare gain choices including passive
and fixed-maximum controls. Reconcile the six SYS003 conditional
six-bit links with actual candidate path losses. Preserve the combined
SYS004 baseline. Do not treat ideal coherent LO or gain optimization
as a validated architecture before checking the assumptions and
accounting. Independent-laser eight-bit candidates merit subsequent
convergence testing, even if comb candidates remain infeasible.

Next stage: [OPA-SYS-005 gain policy experiment](../stage3/README.md), pending CI.
