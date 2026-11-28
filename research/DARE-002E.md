# DARE-002E · Recovery integrity and offline qualification

Date: 2026-11-28. Status: 60/60 existing tests verified; checkpoint implementation and six new fixtures pending execution. Offline exit gate remains open.

## Baseline evidence

[Original output](evidence/dare-002d/baseline-60.log) and [provenance](evidence/dare-002d/provenance.json) record an isolated local Python 3.13.5 run against eight files from merge commit 261d80e5bfc3a82c2f241883097cee193a3ecd1e. All eight local Git blob hashes matched fetched source hashes. Exit 0; 60 tests in 0.059 s. This is not a CI run. Prior archives unchanged.

## Implementation

[Checkpoint](../dare/checkpoint.py) reads validated persisted state for each recommendation. Cost and review inputs carry a sequence matching the current task sequence; older or unsequenced evidence is discarded. Recovery advances the sequence and invalidates cost state, so earlier evidence envelopes cannot release a recovered task. A persistent pending marker is created and synced before saving reservations, recovery or a stop. A surviving marker blocks new recommendations and transactions until manual reconciliation. Reservations are persisted before success is returned. No automatic marker removal on restart, execution, or resume.

[Six new fixtures](../dare/test_checkpoint.py) cover persisted reservation, rejection of old evidence after recovery, interrupted save and restart, persistent stop, missing state and unsequenced evidence. Run all 66 tests offline: `python -m unittest discover -s dare -p 'test_*.py' -v`. Archive original output and source identities before claiming a pass.

## Offline qualification checklist

| Criterion | Current evidence |
| --- | --- |
| Deterministic replay, duplicate/stale events | Prior tests passed; new sequence tests pending |
| Dependency cycles, archive integrity | Prior tests passed |
| Unknown/exhausted quota, paid fallback | Prior synthetic tests passed |
| Stop and recovery | Prior tests passed; new durable transaction tests pending |
| All current fixtures pass | Pending 66-test run |
| Threat model and interface boundary | Partial; trusted synthetic inputs and single writer only |
| Read-only shadow evaluation protocol | Must be separately specified and approved |

No automatic phase advancement. Before shadow evaluation, verify full suite and review the threat model; use archived or explicitly authorized read-only metadata, no mutations or paid services. Report false-ready and missed-blocker rates against human decisions, including unknown evidence.

## Limitations

Sequence binding is not authentication: trusted callers must not relabel old evidence, reset sequences or directly modify snapshots. No external monotonic authority, rollback protection or concurrent-writer guarantee. Marker and snapshot require a trusted local POSIX filesystem; failure before marker durability or after unlink/directory sync is not proven crash-safe. Stop on any ambiguous error and reconcile disk state before restart. No live worker, provider billing verification, automatic restart or mandatory sandbox. Legacy interfaces remain callable for tests; future shadow adapter must use only the qualified read-only interface. The full DARE-002 gate is not passed, and no new live capability is authorized. Zero Additional Cost Policy unchanged.
