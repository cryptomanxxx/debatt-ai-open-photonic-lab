# DARE-002D · Adversarial audit and recovery

Date: 2026-11-28. Status: 51/51 baseline tests passed; nine additional fixtures submitted, execution pending. No live authorization.

## Baseline evidence

[Original output](evidence/dare-002c/baseline-51.log) and [provenance](evidence/dare-002c/provenance.json) record the isolated local Python 3.13.5 execution of all six Python files from merge commit ea94673f72941d70f2510fdf0b34162362d1f8ab. All six Git blob hashes matched before execution. Exit code 0; 51 tests in 0.042 s. Not a CI run. Previous evidence remains unchanged.

## Static adversarial review and remediation

- A valid immediate predecessor archive could hide an invalid older dependency. [GuardedGate](../dare/guarded_gate.py) recursively checks approved, non-stopped dependencies and their archive evidence, with cycle rejection.
- Unknown task IDs and malformed evidence could raise errors instead of returning a conservative recommendation. The guarded interface returns a block for specified input exceptions.
- A reserved correction lacked a reconciliation path. The new offline recovery method requires matching task, head and attempt, a newer sequence, fresh observation, confirmed worker stop, reconciliation and explicit operator approval. It preserves retry count and stop flags, invalidates cost and checks, and writes the candidate snapshot before replacing in-memory state. Ambiguous save errors stop the in-memory engine and propagate; operator intervention and disk reconciliation are required before restarting. No autonomous release or retry.
- Legacy advisory interfaces remain callable; this is not a security sandbox. Any future integration must exclusively use a reviewed guarded interface, with no direct mutation adapter until authorized.

## Validation

[Nine new tests](../dare/test_guarded_gate.py) exercise missing transitive archives, revoked dependencies, malformed evidence, unknown tasks, successful recovery, rejected recovery evidence, persisted stop and simulated write failure. Run all 60 tests with `python -m unittest discover -s dare -p 'test_*.py' -v` offline and archive actual output and source identities. Static findings and proposed corrections are not yet independently verified by these new fixtures.

## Remaining gates

Single trusted writer, synthetic operator confirmations and timestamps only. No authenticated worker termination, atomic reservation persistence, external monotonic sequence authority, rollback prevention, durable stop on ambiguous post-replace failure, or authenticated archive manifests. Fresh review evidence may still be replayed after recovery when the head is unchanged; a future gate must bind observations to reconciliation epoch and sequence, not simply timestamp. Cost verification remains synthetic. No real worker, network, Codex or GitHub mutation adapter. Full DARE-002 gate remains open. Next: execute and archive all 60 tests, address recovery epoch and durable stop/reservation requirements, then evaluate mock-only exit criteria before read-only shadow orchestration. Zero Additional Cost Policy unchanged.
