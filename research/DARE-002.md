# DARE-002 · Offline state machine (initial prototype)

Date: 2026-11-28. Status: initial implementation and 20 synthetic regression tests submitted for review; execution evidence pending. Live readiness remains blocked per [DARE-001](DARE-001.md).

## Scope

The standard-library Python [decision engine](../dare/state_machine.py) returns advisory labels only. No network, subprocess, model invocation, credentials, GitHub mutation adapter or deployment. The [fixtures](../dare/test_state_machine.py) cover task approval, dependencies, cycles, single-agent lease, current-head CI and review, human merge, bounded retries, cost and pause gates, duplicate/out-of-order observations and archive dependency checks.

Run locally in an existing authorized environment:
```sh
python -m unittest discover -s dare -p 'test_*.py' -v
```

No new CI workflow or photonic experiment dispatch is requested. Record actual test output and source revision before declaring the test gate passed.

## Model and boundaries

Task observations are synthetic trusted snapshots with monotonically increasing per-task sequence numbers. A new head invalidates CI/review evidence. Unknown or exhausted quota, unverified zero cost, or non-disabled paid fallback blocks recommendations to implement, correct or request merge. Global/task stop takes precedence. Selection is lexical by task ID among actionable recommendations; dependencies must be merged and archive-verified. A lease blocks new execution recommendations. The retry ceiling is three; actual retry accounting is not implemented. The sole merge-related recommendation requests human approval, never performs merge.

JSON snapshot/restore demonstrates preservation of modeled state across a simulated restart; it is not durable atomic storage, a trusted external event log or a concurrency lock. Archive verification is a synthetic Boolean, not a byte-level manifest validator. Scope approval and cost verification are synthetic inputs, not verified permissions, freshness, or provider billing controls. No action may be inferred authorized by these labels. The initial prototype deliberately treats skipped CI as not passed; applicability, complete check inventory, evidence freshness, event authenticity, typed schema, atomic persistence and recovery require further implementation and tests. No real-time runtime limits, lease expiry, actual file scope verification or orchestration integration yet.

## Acceptance and follow-up

Require deterministic replay and all specified tests passing before claiming the initial software screen. The full DARE-002 gate remains open: add explicit CI applicability/completeness and trusted evidence freshness, lease lifecycle and retry accounting, strict schema validation, archive manifest checks, durable state and more adversarial fixtures. Preserve original test evidence. DARE-003 and all live execution remain unauthorized by this document.

Zero Additional Cost Policy applies unchanged. No paid fallback or autonomous merge is permitted.
