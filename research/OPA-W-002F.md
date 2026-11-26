# OPA-W-002F — Adaptive calibration performance analysis

Status: archived W-002E summaries inspected; independent row-level audit pending CI. No source rerun or new policy. See [W-002E](OPA-W-002E.md).

## Observed source evidence

[Original report](../results/ci-originals/opa-w-002e/45905192736-15157223437/result.json), [summary](../results/ci-originals/opa-w-002e/45905192736-15157223437/summary.csv), [development selection](../results/ci-originals/opa-w-002e/45905192736-15157223437/development.csv), and [provenance](../results/ci-originals/opa-w-002e/45905192736-15157223437/archive-provenance.json). Original run 45905192736, artifact 15157223437, SHA-256 c48d503dc640f32ad330c22f9a5d422afe8bbf2816861848497126a638de81fe. Six original files, 14,693,556 bytes, merged in PR 322 and Git blob identities verified.

Matched fixed baseline: 816/5184 trajectories meet worst-state SER <= 0.001; mean SER 0.124734. Each trajectory has 32768 readings, 2048 per state; the point criterion permits at most two errors per state.

| References | Cadence (steps) | Always passes | Adaptive passes | Always mean SER | Adaptive mean SER | Extra read fraction |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 1 | 635 | 611 | 0.098980 | 0.086341 | 0.0625 |
| 4 | 4 | 440 | 486 | 0.111248 | 0.100751 | 0.015625 |
| 4 | 16 | 464 | 654 | 0.141253 | 0.129545 | 0.00390625 |
| 16 | 1 | 798 | 698 | 0.075251 | 0.073599 | 0.25 |
| 16 | 4 | 549 | 588 | 0.088018 | 0.085593 | 0.0625 |
| 16 | 16 | 538 | 650 | 0.124816 | 0.121031 | 0.015625 |

Adaptive reduces mean SER relative to always at all six matched acquisition costs but passes fewer trajectories at cadence 1 for both reference counts. No corrected method exceeds fixed baseline pass count. At 16 references and cadence 1, adaptive reduces mean SER by about 41% relative to fixed but passes only 698 trajectories, versus 798 for always and 816 for fixed. Development selected gate 2 for (4,4) and gate 3 elsewhere by minimizing total symbol errors. A mean-error objective does not enforce the worst-state threshold; this is a plausible contributor, not a demonstrated causal explanation. Correlated reference offsets and stale estimates remain model mechanisms requiring separate analysis. No physical reliability probability follows.

## Independent aggregate audit

[Audit source](../simulations/memory/audit_adaptive_v006.py) and [tests](../simulations/memory/test_audit_adaptive.py). Verify source identity and all six file sizes, SHA-256 and Git blob SHA-1; all 18 development candidate records and the frozen selection rule; exact coverage of 5184 trajectory keys and 12 policy records each; error count arithmetic, allowable rate bounds and grid, point decisions, identical baseline summaries across policies, reference read accounting and zero-enabled identity. Compare recomputed policy summaries with original JSON and CSV.

Match adaptive against always at the same trajectory, reference count and cadence (31,104 comparisons). Count adaptive-only pass, always-only pass, both pass and both fail, lower/higher mean trajectory SER, lower SER with higher worst-state SER, and lower SER with lost point pass. Export paired means and stratify by each of six scenario parameters plus joint common drift and correlated reference mismatch. All strata descriptive and equal-trajectory weighted. No post-hoc policy selection. Export policy_summary.csv, matched.csv, strata.csv and result.json, plus environment records, to original archive workflow.

## Limits and next research gate

The archived W-002E rows retain aggregate SER, BER and worst-state SER, not state identities, confusion matrices, chronological error counts or raw observations. The audit cannot identify which physical state failed or reconstruct the estimator. Do not invent these details. If further numerical work is needed, preregister a state-resolved replay/diagnostic with pinned source and environment, retain per-state/per-step error counts and reference diagnostics, distinguish replay from original evidence, and evaluate any new tail-aware policy on fresh held-out seeds. A policy tuned on the current held-out results must not be presented as independently validated. The empirical state distribution, retention, read disturb, energy and physical addressing constraints remain missing. No W-003 release or material qualification. Preserve [OPA-M comparison contract](OPA-W-001.md).
