# OPA-W-002B — Archived multilevel sensitivity analysis

Status: source panel inspection complete; independent confusion audit implementation pending CI. This is a read-only analysis of [W-002A](OPA-W-002A.md), not a new material simulation.

## Source and observed results

[Original CI report](../results/ci-originals/opa-w-002a/45900743025-15156101360/result.json), [panel data](../results/ci-originals/opa-w-002a/45900743025-15156101360/panels.csv) and [provenance](../results/ci-originals/opa-w-002a/45900743025-15156101360/archive-provenance.json). Source run 45900743025, artifact 15156101360, SHA-256 24864a7e0a125c59f55937e07796db6c1231c97c5cd08f61f59e751970cbe896. Six original files, 19,618,953 expanded bytes, archived via PR 314. No rerun.

All 3,600 panels have valid calibration. Source report and inspection of all 3,600 panel CSV rows agree on 1,800/1,800 binary and 275/1,800 four-bit point passes; 1,525 four-bit failures. The screen is observed worst-state SER <= 0.001. The 225 distinct parameter combinations per bit depth each have eight seeds; 15 four-bit combinations pass all eight, including three ideal ADC controls. These are descriptive counts, not reliability estimates.

| Four-bit slice | Passing panels | Total |
| --- | ---: | ---: |
| ADC 6 bits | 59 | 600 |
| ADC 8 bits | 106 | 600 |
| ADC 12 bits | 110 | 600 |
| Drift sigma 0 | 146 | 600 |
| Drift sigma 0.005 | 91 | 600 |
| Drift sigma 0.02 | 38 | 600 |

All-eight passing combinations: at zero drift, program/read sigma pairs (0,0), (0,0.002), (0.002,0), (0.002,0.002) pass for all three ADC settings; (0,0.005) passes for 8 and 12 bits. At drift sigma 0.005 only (0,0) with 12-bit ADC passes all eight. None at drift sigma 0.02. All sigmas in normalized full-scale units. The small gain from 8 to 12 bits in this particular grid does not establish optimal ADC precision or hardware cost. Correlated draws across settings and a common drift per panel preclude independent-panel probability inference.

## Independent audit

[Audit implementation](../simulations/memory/audit_multilevel_v002.py) verifies the archive identity, six files against size, SHA-256 and Git blob SHA-1, full factorial panel coverage, every confusion count (468,000 rows), per-state count, Hamming BER, SER, worst-state SER, point classification and agreement with source pass totals. It exports combinations.csv with per-combination pass count, worst seed/state SER and equal-seed mean SER/BER. No source simulation imports or modification. CI execution and new archive are pending. It does not independently reconstruct calibration thresholds, raw draws or confidence bounds; those remain source outputs.

## Next gate

Do not advance to physical cell qualification or addressable array design on this point screen. Next isolate fixed-threshold drift versus a separately calibrated reference-assisted correction, explicitly charging reference/read overhead and testing held-out drift and programming variation; preregister a comparison and retain negative results. Larger independent write and drift samples and state-specific uncertainty are needed before statistical qualification. Empirical GSSe state distributions, retention law, disturb, endurance, energy and process access remain missing. OPA-M's traffic comparison contract remains unchanged.
