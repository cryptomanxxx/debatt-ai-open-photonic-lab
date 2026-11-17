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
