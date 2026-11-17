# OPA-SYS-001 — independent AG003 accounting audit

Status: completed, 11/11 numerical checks passed. [CI run 44103015958](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44103015958). [Exact report](result.json), [45 sensitivity cases](sensitivity.csv), [provenance](provenance.json).

## Findings

- Fixed historical MZI configuration: nominal modeled path loss 28.0308998699 dB; reduced-loss case 18.6308998699 dB; decrease 9.4 dB. This repairs the missing nominal comparison in the original validation, without asserting nominal feasibility. Coupler loss is upstream and excluded from this path; phase, splitter excess and other terms remain.
- CFG-0100 independent laser candidate: 488.467080745 TOPS, 317.083760914 W system proxy, 1.540498572 TOPS/W. The original rounded launch power was used, not a new receiver model. System proxy includes a cooling multiplier, not an independently modeled host.
- HBM 122.11677 W, laser 71.6784 W, converters/drivers 40.70559 W, cooling proxy 41.35875 W, electronic compute 26.33143 W. Break-even power at the assumed 3.5 TOPS/W reference is 139.562 W. 
- Overlap latency 19.78368 us versus serial sum 35.88980736 us; this is an arithmetic bound, not a scheduler result.
- Comb pump fanout: original required line-power formula overcounts the ideal fanout by N for N equal comb branches per pump. The threshold-floor expression in the original code has the same duplicated factor and must be corrected separately. Single branch unchanged. For 4 branches, the illustrative required pump changes from 2075.9169 to 518.9792 mW; this alone does not establish feasibility.

## Conditional scenarios

Six of 45 exceed the assumed electronic reference. All six use 25% of original HBM energy per byte (1 pJ/byte). No scenario with 50% or 100% crosses it.

| Loss reduction (dB) | Laser WPE | System W | TOPS/W |
|---:|---:|---:|---:|
| 6 | 50% | 137.610 | 3.54965 |
| 9 | 30% | 136.246 | 3.58518 |
| 9 | 50% | 133.479 | 3.65951 |
| 12 | 20% | 134.529 | 3.63095 |
| 12 | 30% | 132.795 | 3.67835 |
| 12 | 50% | 131.408 | 3.71717 |

50% laser efficiency is outside the original 12–30% range; 1 pJ/byte is below the original nominal uncertainty range of 2.5–8 pJ/byte. Loss reductions are hypothetical aggregate changes, not demonstrated component improvements. All scenarios hold throughput and receiver target fixed, without recalculating accuracy or device feasibility. The 3.5 TOPS/W reference is an assumption, not a measured GPU comparison.

## Archive

ZIP SHA-256 and CRC checked against the GitHub artifact. Report, CSV and environment lock are archived byte-identically (Git blob IDs verified). The installed-package inventory remains in the original artifact, recorded by hash in provenance; it is not yet committed.

## Next work

Preserve original and replay bytes. Introduce a separate corrected model, first fixing pump fanout in both required-line and threshold paths with tests for one/multiple branches and power conservation. Compare against the unchanged original on identical configuration keys, then examine other audit issues (receiver, amplifier, timing and convergence) before a final architecture recommendation. The six other roadmap tracks remain planned until AG003 is completed.
